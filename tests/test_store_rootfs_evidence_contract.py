"""L08-G regression tests: evidence consistency is not source authentication."""
import copy
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
from rootfs_evidence_contract import RootfsEvidenceError, verify_snapshot_evidence


def mock_elf(kind=3):
    value = bytearray(52)
    value[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", value, 16, kind, 40, 1)
    struct.pack_into("<I", value, 36, 5 << 24)
    struct.pack_into("<H", value, 40, 52)
    return bytes(value)


def make_report(folder, source_id="fixture-source"):
    lib = Path(folder) / "lib"
    lib.mkdir()
    (lib / "libc.so.6").write_bytes(mock_elf())
    (lib / "libzbroken.so").write_bytes(b"not-an-elf")
    return scan_rootfs_snapshot(
        folder, source_id=source_id, declared_source_sha256="a" * 64)


class RootfsEvidenceContractTests(unittest.TestCase):
    def test_scan_produces_consistent_but_unauthenticated_evidence(self):
        with TemporaryDirectory() as td:
            snapshot = make_report(td)
            result = verify_snapshot_evidence(snapshot)
        self.assertTrue(result["observation_digest_consistent"])
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["bytes_declared"], len(mock_elf()) + len(b"not-an-elf"))
        self.assertEqual(result["observation_digest"], snapshot["audit_sha256"])
        self.assertEqual(result["declared_source_sha256"], "a" * 64)
        for field in ("image_hash_verified", "source_provenance_authenticated",
                      "export_matches_source_image", "hardware_verified",
                      "runtime_compatible", "launchable"):
            self.assertIs(result[field], False, field)
        self.assertIs(result["caller_digest_matches"], False)
        self.assertIs(result["caller_source_matches"], False)

    def test_explicit_anchors_are_comparisons_not_proof(self):
        with TemporaryDirectory() as td:
            snapshot = make_report(td)
        result = verify_snapshot_evidence(
            snapshot, expected_audit_sha256=snapshot["audit_sha256"],
            expected_source_id="fixture-source")
        self.assertTrue(result["caller_digest_matches"])
        self.assertTrue(result["caller_source_matches"])
        self.assertFalse(result["source_provenance_authenticated"])
        with self.assertRaisesRegex(RootfsEvidenceError, "expected_digest_mismatch"):
            verify_snapshot_evidence(snapshot, expected_audit_sha256="b" * 64)
        with self.assertRaisesRegex(RootfsEvidenceError, "expected_source_mismatch"):
            verify_snapshot_evidence(snapshot, expected_source_id="other")

    def test_tampered_sha_and_size_fail_closed(self):
        with TemporaryDirectory() as td:
            report = make_report(td)
        for mutate, reason in (
            (lambda s: s["libraries"][0].__setitem__("sha256", "f" * 64),
             "audit_digest_mismatch"),
            (lambda s: s["libraries"][0].__setitem__("size", 53),
             "invalid_observation_size"),
            (lambda s: s.__setitem__("audit_sha256", "f" * 64),
             "audit_digest_mismatch"),
        ):
            sample = copy.deepcopy(report)
            mutate(sample)
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(RootfsEvidenceError, reason):
                    verify_snapshot_evidence(sample)

    def test_missing_or_forged_provenance_fails_closed(self):
        with TemporaryDirectory() as td:
            report = make_report(td)
        for modify in (
            lambda r: r.__setitem__("launchable", True),
            lambda r: r.__setitem__("hardware_verified", True),
            lambda r: r["provenance"].__setitem__("source_hash_verified", True),
            lambda r: r["provenance"].__setitem__("declared_source_sha256", "bad"),
            lambda r: r["provenance"].__setitem__("source_id", "../escape"),
        ):
            sample = copy.deepcopy(report)
            modify(sample)
            with self.assertRaises(RootfsEvidenceError):
                verify_snapshot_evidence(sample)

    def test_source_id_change_is_not_authenticated_by_observation_digest(self):
        with TemporaryDirectory() as td:
            original = make_report(td)
        rewritten = copy.deepcopy(original)
        rewritten["provenance"]["source_id"] = "other-claimed-source"
        check = verify_snapshot_evidence(rewritten)
        self.assertTrue(check["observation_digest_consistent"])
        self.assertFalse(check["source_provenance_authenticated"])
        with self.assertRaisesRegex(RootfsEvidenceError,
                                    "expected_source_mismatch"):
            verify_snapshot_evidence(rewritten,
                                     expected_source_id="fixture-source")

    def test_mutated_symlink_target_is_detected_as_report_change(self):
        with TemporaryDirectory() as td:
            report = make_report(td)
            linkpath = Path(td) / "lib" / "libalias.so"
            try:
                os.symlink("libc.so.6", linkpath)
            except (OSError, NotImplementedError):
                self.skipTest("No symlink permission on host")
            report = scan_rootfs_snapshot(td, source_id="fixture-alias")
        self.assertTrue(verify_snapshot_evidence(report)[
            "observation_digest_consistent"])
        modified = copy.deepcopy(report)
        symlink = next(row for row in modified["libraries"]
                       if row["state"] == "symlink_unresolved")
        symlink["link_target"] = "libzbroken.so"
        with self.assertRaisesRegex(RootfsEvidenceError,
                                    "audit_digest_mismatch"):
            verify_snapshot_evidence(modified)

    def test_strict_record_and_directory_shapes(self):
        with TemporaryDirectory() as td:
            report = make_report(td)
        bad_cases = [
            (lambda s: s["libraries"][0].__setitem__(
                "state", "symlink_unresolved"), "invalid_symlink_observation"),
            (lambda s: s["libraries"][0].__setitem__(
                "path", "etc/passwd"), "invalid_observation_entry"),
            (lambda s: s["libraries"][0].__setitem__(
                "sha256", "not-sha256"), "invalid_file_observation"),
            (lambda s: s["libraries"][0].__setitem__(
                "identity", dict(s["libraries"][0]["identity"], launchable=True)),
             "invalid_file_observation"),
            (lambda s: s["directories"][0].__setitem__(
                "state", "not_scanned_non_directory"), "invalid_observation_entry"),
            (lambda s: s.__setitem__(
                "libraries", s["libraries"] * 513), "invalid_observation_collections"),
        ]
        for modify, reason in bad_cases:
            with self.subTest(reason=reason):
                sample = copy.deepcopy(report)
                modify(sample)
                with self.assertRaisesRegex(RootfsEvidenceError, reason):
                    verify_snapshot_evidence(sample)

    def test_bad_input_and_expected_anchors_are_refused(self):
        with TemporaryDirectory() as td:
            report = make_report(td)
        for kwargs, reason in (
            ({"expected_audit_sha256": "not-a-sha"}, "invalid_expected_digest"),
            ({"expected_source_id": "../parent"}, "invalid_expected_source"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(RootfsEvidenceError, reason):
                    verify_snapshot_evidence(report, **kwargs)
        with self.assertRaisesRegex(RootfsEvidenceError, "invalid_snapshot_report"):
            verify_snapshot_evidence({})
        self.assertEqual(
            verify_snapshot_evidence(report)["observation_digest"],
            hashlib.sha256(
                __import__("json").dumps(
                    {"directories": report["directories"],
                     "libraries": report["libraries"]},
                    ensure_ascii=True, sort_keys=True,
                    separators=(",", ":")).encode("ascii")).hexdigest())


if __name__ == "__main__":
    unittest.main()
