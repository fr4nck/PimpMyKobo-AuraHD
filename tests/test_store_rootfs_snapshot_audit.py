"""L08-E host-only extracted snapshot inspection; all filesystem fixtures are temporary."""
import hashlib
import os
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
import rootfs_snapshot_audit as audit


def shared_object(*, etype=3, machine=40):
    data = bytearray(52)
    data[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", data, 16, etype, machine, 1)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<HHH", data, 40, 52, 0, 0)
    return bytes(data)


def executable_needing_libc():
    data = bytearray(256)
    data[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", data, 16, 2, 40, 1)
    struct.pack_into("<I", data, 28, 52)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<HHH", data, 40, 52, 32, 2)
    struct.pack_into("<IIIIIIII", data, 52,
                     1, 128, 0x1000, 0, 128, 128, 4, 4)
    struct.pack_into("<IIIIIIII", data, 84,
                     2, 160, 0x1020, 0, 32, 32, 4, 4)
    for at, tag, value in ((160, 5, 0x1050), (168, 10, 16),
                           (176, 1, 1), (184, 0, 0)):
        struct.pack_into("<II", data, at, tag, value)
    data[208:224] = bytes((0,)) + b"libc.so.6" + bytes((0,)) + bytes(5)
    return bytes(data)


class SnapshotAuditTests(unittest.TestCase):
    def test_empty_snapshot_is_not_device_evidence(self):
        with TemporaryDirectory() as td:
            r = audit.scan_rootfs_snapshot(td, source_id="fixture-empty")
        self.assertFalse(r["hardware_verified"])
        self.assertFalse(r["launchable"])
        self.assertEqual(r["bytes_inspected"], 0)
        self.assertEqual(len(r["libraries"]), 0)
        self.assertEqual({row["path"]: row["state"] for row in r["directories"]},
                         {"lib": "not_present_in_export",
                          "usr/lib": "not_scanned_missing_parent"})

    def test_real_bytes_are_hashed_and_stable(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "lib"
            folder.mkdir()
            sample = shared_object()
            path = folder / "libc.so.6"
            path.write_bytes(sample)
            before = path.stat().st_mtime_ns
            a = audit.scan_rootfs_snapshot(td, source_id="fixture-01")
            b = audit.scan_rootfs_snapshot(td, source_id="fixture-01")
            after = path.stat().st_mtime_ns
        entry = a["libraries"][0]
        self.assertEqual(entry["sha256"], hashlib.sha256(sample).hexdigest())
        self.assertEqual(entry["path"], "lib/libc.so.6")
        self.assertEqual(entry["state"], "arm_eabi5_shared_header")
        self.assertEqual(entry["identity"]["arm_eabi"], 5)
        self.assertEqual(a["audit_sha256"], b["audit_sha256"])
        self.assertEqual(before, after)
        self.assertFalse(a["hardware_verified"])
        self.assertFalse(entry["identity"]["launchable"])

    def test_end_to_end_elf_comparison_remains_non_executable(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "usr" / "lib"
            folder.mkdir(parents=True)
            (folder / "libc.so.6").write_bytes(shared_object())
            r = audit.inspect_elf_against_rootfs_snapshot(
                executable_needing_libc(), td, source_id="fixture-02")
        self.assertEqual(r["elf"]["needed"], ("libc.so.6",))
        self.assertEqual(r["comparison"]["findings"][0]["state"],
                         "arm_header_observed_only")
        self.assertEqual(r["comparison"]["findings"][0]["observed_paths"],
                         ("usr/lib/libc.so.6",))
        self.assertFalse(r["hardware_verified"])
        self.assertFalse(r["launchable"])
        self.assertFalse(r["comparison"]["launchable"])

    def test_non_arm_library_does_not_match(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "lib"
            folder.mkdir()
            (folder / "libc.so.6").write_bytes(shared_object(machine=62))
            r = audit.scan_rootfs_snapshot(td, source_id="fixture-03")
        self.assertEqual(r["libraries"][0]["state"], "elf_identity_unverified")
        self.assertEqual(r["libraries"][0]["reason"], "not_arm")
        match = audit.compare_needed_to_snapshot(("libc.so.6",), r)
        self.assertEqual(match["findings"][0]["state"],
                         "nonmatching_library_header")

    def test_absent_name_is_unknown_even_in_scanned_directories(self):
        with TemporaryDirectory() as td:
            (Path(td) / "lib").mkdir()
            (Path(td) / "usr" / "lib").mkdir(parents=True)
            r = audit.scan_rootfs_snapshot(td, source_id="fixture-04")
        comparison = audit.compare_needed_to_snapshot(("libmissing.so.1",), r)
        self.assertEqual(comparison["findings"][0]["state"],
                         "not_observed_in_scanned_directories")
        self.assertFalse(comparison["hardware_verified"])

    def test_source_hash_is_declared_not_verified(self):
        with TemporaryDirectory() as td:
            r = audit.scan_rootfs_snapshot(
                td, source_id="fixture-hash",
                declared_source_sha256="a" * 64)
        self.assertEqual(r["provenance"]["declared_source_sha256"], "a" * 64)
        self.assertIs(r["provenance"]["source_hash_verified"], False)

    def test_deny_unsafe_root_and_provenance(self):
        with TemporaryDirectory() as td:
            for kwargs, reason in (
                ({"source_id": "../rootfs"}, "invalid_source_identifier"),
                ({"source_id": "fixture", "declared_source_sha256": "xyz"},
                 "invalid_declared_hash"),
            ):
                with self.subTest(reason=reason):
                    with self.assertRaisesRegex(audit.RootfsSnapshotError, reason):
                        audit.scan_rootfs_snapshot(td, **kwargs)
            with self.assertRaisesRegex(audit.RootfsSnapshotError,
                                        "snapshot_directory_required"):
                audit.scan_rootfs_snapshot(Path(td) / "missing",
                                           source_id="fixture")
        with self.assertRaisesRegex(audit.RootfsSnapshotError,
                                    "filesystem_root_refused"):
            audit.scan_rootfs_snapshot(Path.home().anchor, source_id="fixture")

    def test_reject_oversize_and_excess_candidates(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "lib"
            folder.mkdir()
            (folder / "liba.so").write_bytes(shared_object())
            with patch.object(audit, "MAX_LIBRARY_BYTES", 12):
                with self.assertRaisesRegex(audit.RootfsSnapshotError,
                                            "library_size_limit"):
                    audit.scan_rootfs_snapshot(td, source_id="fixture")
            (folder / "libb.so").write_bytes(shared_object())
            with patch.object(audit, "MAX_CANDIDATES", 1):
                with self.assertRaisesRegex(audit.RootfsSnapshotError,
                                            "library_count_limit"):
                    audit.scan_rootfs_snapshot(td, source_id="fixture")

    def test_duplicate_name_in_two_directories_is_ambiguous(self):
        with TemporaryDirectory() as td:
            for relative in ("lib", "usr/lib"):
                folder = Path(td) / relative
                folder.mkdir(parents=True)
                (folder / "libc.so.6").write_bytes(shared_object())
            r = audit.scan_rootfs_snapshot(td, source_id="fixture-double")
        comparison = audit.compare_needed_to_snapshot(("libc.so.6",), r)
        self.assertEqual(comparison["findings"][0]["state"],
                         "ambiguous_export_name")
        self.assertEqual(len(comparison["findings"][0]["observed_paths"]), 2)

    def test_symlink_is_not_followed_or_considered_verified(self):
        with TemporaryDirectory() as td:
            folder = Path(td) / "lib"
            folder.mkdir()
            target = Path(td) / "outside.so"
            target.write_bytes(shared_object())
            link = folder / "libc.so.6"
            try:
                os.symlink("../outside.so", link)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation not permitted on runner")
            result = audit.scan_rootfs_snapshot(td, source_id="fixture-symlink")
        self.assertEqual(result["bytes_inspected"], 0)
        self.assertEqual(result["libraries"][0]["state"], "symlink_unresolved")
        self.assertEqual(
            audit.compare_needed_to_snapshot(("libc.so.6",), result)[
                "findings"][0]["state"], "unresolved_symlink")

    def test_parent_directory_symlink_cannot_escape_scope(self):
        with TemporaryDirectory() as td:
            outside = Path(td) / "alternative-root"
            (outside / "lib").mkdir(parents=True)
            (outside / "lib" / "libescape.so").write_bytes(shared_object())
            try:
                os.symlink(outside, Path(td) / "usr", target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlink creation not permitted")
            result = audit.scan_rootfs_snapshot(td, source_id="fixture-parent")
        states = {row["path"]: row["state"] for row in result["directories"]}
        self.assertEqual(states["usr/lib"], "not_scanned_parent_non_directory")
        self.assertEqual(result["bytes_inspected"], 0)
        self.assertEqual(result["libraries"], ())

    def test_needed_input_rejected_if_not_canonical(self):
        with TemporaryDirectory() as td:
            r = audit.scan_rootfs_snapshot(td, source_id="fixture")
        for names in ((("libc.so.6", "libc.so.6")), ("../libc.so.6",),
                      ["libc.so.6"]):
            with self.subTest(names=names):
                with self.assertRaisesRegex(audit.RootfsSnapshotError,
                                            "invalid_needed_names"):
                    audit.compare_needed_to_snapshot(names, r)


if __name__ == "__main__":
    unittest.main()
