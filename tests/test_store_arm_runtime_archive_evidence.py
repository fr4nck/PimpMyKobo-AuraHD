"""L08-M: bounded dependency graph from archive-matched synthetic ELF files."""
from io import BytesIO
import hashlib
import os
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from arm_runtime_archive_evidence import (
    ArmArchiveRuntimeEvidenceError, inspect_arm_archive_dependency_graph,
)
from rootfs_snapshot_audit import scan_rootfs_snapshot
from test_store_arm_elf_runtime_metadata import build_elf


def make_archive(files, links=None):
    output = BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for path, data in files.items():
            info = tarfile.TarInfo(path)
            info.size = len(data)
            info.mtime = 0
            archive.addfile(info, BytesIO(data))
        for path, target in (links or {}).items():
            info = tarfile.TarInfo(path)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            info.mtime = 0
            archive.addfile(info)
    return output.getvalue()


def make_snapshot(files, links=None):
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "lib").mkdir()
        (root / "usr" / "lib").mkdir(parents=True)
        for path, data in files.items():
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        for path, target in (links or {}).items():
            destination = root / path
            try:
                destination.symlink_to(target)
            except (OSError, NotImplementedError):
                raise unittest.SkipTest("symlinks unavailable on this host")
        return scan_rootfs_snapshot(root, source_id="l08m-synthetic")


def run_graph(candidate, files, links=None, *, archive_files=None,
              expected_candidate_sha256=None):
    snapshot = make_snapshot(files, links)
    archive = make_archive(files if archive_files is None else archive_files, links)
    return inspect_arm_archive_dependency_graph(
        candidate, archive, snapshot,
        expected_candidate_sha256=expected_candidate_sha256,
        expected_archive_sha256=hashlib.sha256(archive).hexdigest(),
        expected_audit_sha256=snapshot["audit_sha256"],
        expected_source_id="l08m-synthetic")


class ArmArchiveDependencyGraphTests(unittest.TestCase):
    def test_observes_direct_and_transitive_edges_and_version_nodes(self):
        executable = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        libc = build_elf(kind=3, needed="libm.so.6", soname="libc.so.6",
                         verneed="GLIBC_2.4", verdef="GLIBC_2.4")
        libm = build_elf(kind=3, soname="libm.so.6", verdef="GLIBC_2.4")
        files = {"lib/libc.so.6": libc, "lib/libm.so.6": libm}
        result = run_graph(executable, files)
        self.assertEqual(result["archive_verdict"], "scoped_content_match")
        self.assertTrue(result["dependency_graph_complete_in_scanned_scope"])
        edges = {(e["from"], e["needed"], e["state"])
                 for e in result["dependency_edges"]}
        self.assertIn(("<executable>", "libc.so.6",
                       "metadata_observed_in_archive_only"), edges)
        self.assertIn(("libc.so.6", "libm.so.6",
                       "metadata_observed_in_archive_only"), edges)
        reports = {r["object"]: r["comparison"] for r in result["version_node_reports"]}
        self.assertTrue(reports["<executable>"]["all_required_version_nodes_observed"])
        self.assertTrue(reports["libc.so.6"]["all_required_version_nodes_observed"])
        self.assertFalse(result["transitive_dependencies_verified"])
        self.assertFalse(result["symbol_versions_verified"])
        self.assertFalse(result["runtime_compatible"])
        self.assertFalse(result["launchable"])

    def test_missing_library_is_unresolved_not_claimed_available(self):
        executable = build_elf(needed="libmissing.so")
        result = run_graph(executable, {})
        self.assertEqual(result["archive_verdict"], "scoped_content_match")
        self.assertFalse(result["dependency_graph_complete_in_scanned_scope"])
        self.assertEqual(result["dependency_edges"][0]["state"],
                         "not_observed_in_scanned_directories")
        self.assertEqual(result["unresolved_names"], ("libmissing.so",))

    def test_archive_mismatch_blocks_dependency_graph(self):
        executable = build_elf(needed="libc.so.6")
        libc = build_elf(kind=3, soname="libc.so.6")
        changed = libc + b"changed"
        result = run_graph(executable, {"lib/libc.so.6": libc},
                           archive_files={"lib/libc.so.6": changed})
        self.assertEqual(result["archive_verdict"], "mismatch")
        self.assertEqual(result["verdict"], "archive_mismatch")
        self.assertFalse(result["dependency_graph_available"])
        self.assertIsNone(result["dependency_graph_complete_in_scanned_scope"])

    def test_symlink_alias_reads_the_matched_target_not_the_link(self):
        executable = build_elf(needed="libc.so.6")
        libc = build_elf(kind=3, soname="libc.so.6", verdef="GLIBC_2.4")
        files = {"lib/libc-2.19.so": libc}
        result = run_graph(executable, files,
                           {"lib/libc.so.6": "libc-2.19.so"})
        edge = result["dependency_edges"][0]
        self.assertEqual(edge["state"], "metadata_observed_in_archive_only")
        self.assertEqual(edge["archive_path"], "lib/libc-2.19.so")
        self.assertEqual(edge["alias_state"], "alias_to_arm_header_observed_only")

    def test_pt_interp_is_observed_separately_from_launchability(self):
        executable = build_elf(needed="libc.so.6", interpreter="/lib/ld-linux.so.3")
        libc = build_elf(kind=3, soname="libc.so.6")
        loader = build_elf(kind=3, soname="ld-linux.so.3")
        result = run_graph(executable, {
            "lib/libc.so.6": libc,
            "lib/ld-linux.so.3": loader,
        })
        self.assertEqual(result["interpreter"]["state"],
                         "interpreter_metadata_observed_only")
        self.assertEqual(result["interpreter"]["archive_path"],
                         "lib/ld-linux.so.3")
        self.assertFalse(result["interpreter"]["launchable"])
        self.assertFalse(result["hardware_verified"])

    def test_missing_version_node_is_reported_even_if_graph_is_observed(self):
        executable = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        libc = build_elf(kind=3, soname="libc.so.6", verdef="GLIBC_2.17")
        result = run_graph(executable, {"lib/libc.so.6": libc})
        self.assertTrue(result["dependency_graph_complete_in_scanned_scope"])
        comparison = result["version_node_reports"][0]["comparison"]
        self.assertFalse(comparison["all_required_version_nodes_observed"])
        self.assertEqual(comparison["binary_version_requirements"][0]["state"],
                         "required_version_nodes_missing")
        self.assertFalse(result["symbol_versions_verified"])

    def test_dependency_depth_is_bounded(self):
        executable = build_elf(needed="lib0.so")
        files = {}
        for index in range(9):
            name = "lib%d.so" % index
            child = "lib%d.so" % (index + 1) if index < 8 else None
            files["lib/" + name] = build_elf(
                kind=3, needed=child, soname=name)
        result = run_graph(executable, files)
        self.assertFalse(result["dependency_graph_complete_in_scanned_scope"])
        self.assertIn("dependency_depth_limit",
                      {edge["state"] for edge in result["dependency_edges"]})
        self.assertFalse(result["transitive_dependencies_verified"])

    def test_candidate_digest_mismatch_is_refused(self):
        executable = build_elf(needed="libc.so.6")
        with self.assertRaisesRegex(
                ArmArchiveRuntimeEvidenceError,
                "expected_candidate_digest_mismatch"):
            run_graph(executable, {}, expected_candidate_sha256="f" * 64)

    def test_malformed_library_metadata_does_not_become_a_match(self):
        executable = build_elf(needed="libc.so.6")
        # Header still identifies ARM EABI5, but the dynamic table lacks DT_NULL.
        malformed = bytearray(build_elf(kind=3, soname="libc.so.6"))
        struct.pack_into("<I", malformed, 256, 0x7FFFFFFF)
        result = run_graph(executable, {"lib/libc.so.6": bytes(malformed)})
        self.assertFalse(result["dependency_graph_complete_in_scanned_scope"])
        self.assertEqual(result["dependency_edges"][0]["state"],
                         "library_metadata_rejected")

    def test_crc_corruption_is_rejected(self):
        executable = build_elf(needed="libc.so.6")
        libc = build_elf(kind=3, soname="libc.so.6")
        snapshot = make_snapshot({"lib/libc.so.6": libc})
        archive = bytearray(make_archive({"lib/libc.so.6": libc}))
        archive[-8] ^= 1
        with self.assertRaisesRegex(
                ArmArchiveRuntimeEvidenceError, "input_evidence_rejected"):
            inspect_arm_archive_dependency_graph(
                executable, bytes(archive), snapshot)

    def test_archive_graph_is_memory_only(self):
        executable = build_elf(needed="libc.so.6")
        libc = build_elf(kind=3, soname="libc.so.6")
        snapshot = make_snapshot({"lib/libc.so.6": libc})
        archive = make_archive({"lib/libc.so.6": libc})
        with patch("builtins.open", side_effect=AssertionError("host file read")):
            with patch("os.open", side_effect=AssertionError("host file read")):
                result = inspect_arm_archive_dependency_graph(
                    executable, archive, snapshot)
        self.assertTrue(result["dependency_graph_complete_in_scanned_scope"])
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["launchable"])


if __name__ == "__main__":
    unittest.main()
