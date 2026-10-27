"""L08-F: pure snapshot alias resolution, no physical Kobo access."""
import hashlib
import os
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from rootfs_snapshot_audit import scan_rootfs_snapshot
from rootfs_snapshot_aliases import (
    resolve_snapshot_aliases, RootfsAliasError, MAX_ALIAS_HOPS,
)

DIGEST = "f" * 64


def fixture(*records):
    return {
        "schema": "pmkb-rootfs-snapshot-audit-v1",
        "scope": "extracted_directory_observation_only",
        "hardware_verified": False,
        "launchable": False,
        "provenance": {"source_id": "synthetic", "source_hash_verified": False,
                       "declared_source_sha256": None},
        "libraries": tuple(records),
    }


def link(path, target):
    return {"path": path, "soname_candidate": path.rsplit("/", 1)[-1],
            "state": "symlink_unresolved", "link_target": target}


def library(path):
    return {"path": path, "soname_candidate": path.rsplit("/", 1)[-1],
            "state": "arm_eabi5_shared_header", "sha256": DIGEST,
            "identity": {"machine": "EM_ARM", "arm_eabi": 5,
                         "type": "ET_DYN", "launchable": False}}


def shared_elf():
    data = bytearray(52)
    data[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", data, 16, 3, 40, 1)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<H", data, 40, 52)
    return bytes(data)


class SnapshotAliasTests(unittest.TestCase):
    def test_direct_header_and_no_runtime_claim(self):
        result = resolve_snapshot_aliases(("libc.so.6",),
                                         fixture(library("lib/libc.so.6")))
        finding, = result["findings"]
        self.assertEqual(finding["state"], "direct_arm_header_observed_only")
        self.assertEqual(finding["observed_path_chain"], ("lib/libc.so.6",))
        self.assertEqual(finding["observed_sha256"], DIGEST)
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["launchable"])
        self.assertFalse(result["runtime_compatible"])
        self.assertFalse(result["source_hash_verified"])
        self.assertFalse(finding["launchable"])

    def test_relative_chain_resolves_within_fixture(self):
        result = resolve_snapshot_aliases(
            ("libc.so.6",),
            fixture(link("lib/libc.so.6", "libc-2.19.so"),
                    library("lib/libc-2.19.so")))
        finding, = result["findings"]
        self.assertEqual(finding["state"], "alias_to_arm_header_observed_only")
        self.assertEqual(finding["observed_path_chain"],
                         ("lib/libc.so.6", "lib/libc-2.19.so"))
        self.assertEqual(finding["observed_target"], "lib/libc-2.19.so")
        self.assertEqual(finding["observed_sha256"], DIGEST)

    def test_absolute_alias_is_rooted_inside_snapshot_not_host(self):
        result = resolve_snapshot_aliases(
            ("libfoo.so.1",),
            fixture(link("usr/lib/libfoo.so.1", "/lib/libfoo-1.so"),
                    library("lib/libfoo-1.so")))
        finding, = result["findings"]
        self.assertEqual(finding["state"], "alias_to_arm_header_observed_only")
        self.assertEqual(finding["observed_target"], "lib/libfoo-1.so")

    def test_relative_usr_lib_parent_walk_stays_inside_rootfs(self):
        result = resolve_snapshot_aliases(
            ("libfoo.so.1",),
            fixture(link("usr/lib/libfoo.so.1", "../../lib/libfoo-1.so"),
                    library("lib/libfoo-1.so")))
        finding, = result["findings"]
        self.assertEqual(finding["state"], "alias_to_arm_header_observed_only")
        self.assertEqual(finding["observed_target"], "lib/libfoo-1.so")
        self.assertFalse(result["source_hash_verified"])

    def test_reject_malformed_needed_input(self):
        for names in (["libc.so.6"], ("../libc.so.6",),
                      ("libc.so.6", "libc.so.6")):
            with self.subTest(names=names):
                with self.assertRaisesRegex(RootfsAliasError,
                                            "invalid_snapshot_or_needed"):
                    resolve_snapshot_aliases(names, fixture())

    def test_nested_subdirectory_is_outside_scan(self):
        r = resolve_snapshot_aliases(
            ("libx.so",), fixture(link("lib/libx.so", "/usr/lib/arm/libx.so")))
        self.assertEqual(r["findings"][0]["state"], "alias_target_not_scanned")

    def test_missing_scanned_target_is_unknown(self):
        r = resolve_snapshot_aliases(
            ("libx.so",), fixture(link("lib/libx.so", "libx-99.so")))
        self.assertEqual(r["findings"][0]["state"], "alias_target_not_observed")

    def test_escaping_links_are_rejected_and_never_followed(self):
        for target in ("../../etc/passwd", "/../../outside.so", "//host/path",
                       "C:\\windows", "bad\x00file", ""):
            with self.subTest(target=target):
                r = resolve_snapshot_aliases(
                    ("libfoo.so",), fixture(link("lib/libfoo.so", target)))
                self.assertEqual(r["findings"][0]["state"], "unsafe_alias_target")
                self.assertIsNone(r["findings"][0]["observed_sha256"])

    def test_cycles_and_hop_limit_do_not_loop(self):
        cycle = fixture(link("lib/liba.so", "libb.so"),
                        link("lib/libb.so", "liba.so"))
        r = resolve_snapshot_aliases(("liba.so",), cycle)
        self.assertEqual(r["findings"][0]["state"], "alias_cycle")
        many = [link("lib/lib%d.so" % i, "lib%d.so" % (i + 1))
                for i in range(MAX_ALIAS_HOPS + 1)]
        many.append(library("lib/lib%d.so" % (MAX_ALIAS_HOPS + 1)))
        r = resolve_snapshot_aliases(("lib0.so",), fixture(*many))
        self.assertEqual(r["findings"][0]["state"], "alias_hop_limit")

    def test_ambiguous_names_never_select_random_library(self):
        r = resolve_snapshot_aliases(
            ("libc.so.6",),
            fixture(library("lib/libc.so.6"), library("usr/lib/libc.so.6")))
        finding, = r["findings"]
        self.assertEqual(finding["state"], "ambiguous_export_name")
        self.assertIsNone(finding["observed_sha256"])

    def test_invalid_or_forged_reports_are_refused(self):
        valid = fixture(library("lib/libc.so.6"))
        forged = dict(valid, hardware_verified=True)
        for sample in (forged, dict(valid, launchable=True),
                       dict(valid, provenance={"source_hash_verified": True}),
                       dict(valid, libraries=(library("lib/libc.so.6"),) * 2),
                       fixture({"path": "lib/libc.so.6",
                                "soname_candidate": "libc.so.6",
                                "state": []})):
            with self.subTest(sample=repr(sample)[:90]):
                with self.assertRaises(RootfsAliasError):
                    resolve_snapshot_aliases(("libc.so.6",), sample)

    def test_identity_only_not_shared_library(self):
        wrong = library("lib/libc.so.6")
        wrong["state"] = "arm_eabi5_not_shared_object"
        r = resolve_snapshot_aliases(("libc.so.6",), fixture(wrong))
        self.assertEqual(r["findings"][0]["state"], "nonmatching_library_header")
        self.assertIsNone(r["findings"][0]["observed_sha256"])

    def test_scan_integrates_with_real_temp_directory_only(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "lib"
            folder.mkdir()
            content = shared_elf()
            (folder / "libc-2.19.so").write_bytes(content)
            try:
                os.symlink("libc-2.19.so", folder / "libc.so.6")
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation not allowed on host")
            scan = scan_rootfs_snapshot(td, source_id="fixture-only")
        result = resolve_snapshot_aliases(("libc.so.6",), scan)
        finding, = result["findings"]
        self.assertEqual(finding["state"], "alias_to_arm_header_observed_only")
        self.assertEqual(finding["observed_sha256"],
                         hashlib.sha256(content).hexdigest())
        self.assertFalse(result["hardware_verified"])

    def test_empty_needed_remains_non_launchable(self):
        r = resolve_snapshot_aliases((), fixture())
        self.assertEqual(r["findings"], ())
        self.assertFalse(r["launchable"])


if __name__ == "__main__":
    unittest.main()
