"""L08-I end-to-end synthetic ARM/archive/export evidence tests."""
import copy
import hashlib
from io import BytesIO
import os
from pathlib import Path
import struct
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
import arm_runtime_evidence as module
from arm_runtime_evidence import (
    inspect_arm_runtime_evidence, ArmRuntimeEvidenceError,
)
from rootfs_snapshot_audit import scan_rootfs_snapshot


def shared_elf():
    raw = bytearray(52)
    raw[:7] = bytes((127, 69, 76, 70, 70 - 69, 1, 1))
    struct.pack_into("<HHI", raw, 16, 3, 40, 1)
    struct.pack_into("<I", raw, 36, 5 << 24)
    struct.pack_into("<H", raw, 40, 52)
    return bytes(raw)


def executable(interpreter=None):
    raw = bytearray(512)
    raw[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", raw, 16, 2, 40, 1)
    struct.pack_into("<I", raw, 28, 52)
    struct.pack_into("<I", raw, 36, 5 << 24)
    struct.pack_into("<HHH", raw, 40, 52, 32, 3 if interpreter else 2)
    # PT_LOAD at offset 192 and PT_DYNAMIC at 224.
    struct.pack_into("<IIIIIIII", raw, 52, 1, 192, 0x1000, 0, 128, 128, 4, 4)
    struct.pack_into("<IIIIIIII", raw, 84, 2, 224, 0x1020, 0, 32, 32, 4, 4)
    struct.pack_into("<II", raw, 224, 5, 0x1050)
    struct.pack_into("<II", raw, 232, 10, 32)
    struct.pack_into("<II", raw, 240, 1, 1)
    struct.pack_into("<II", raw, 248, 0, 0)
    raw[272:304] = b"\x00libc.so.6\x00".ljust(32, b"\x00")
    if interpreter is not None:
        name = interpreter.encode("ascii") + b"\x00"
        struct.pack_into("<IIIIIIII", raw, 116, 3, 352, 0, 0,
                         len(name), len(name), 4, 4)
        raw[352:352 + len(name)] = name
    return bytes(raw)


def tar_gzip(records):
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path, value in records:
            info = tarfile.TarInfo(path)
            info.mtime = 0
            if isinstance(value, str):
                info.type = tarfile.SYMTYPE
                info.linkname = value
                archive.addfile(info)
            else:
                info.size = len(value)
                archive.addfile(info, BytesIO(value))
    return buffer.getvalue()


def observed(files=None, *, complete=True):
    files = files if files is not None else {"lib/libc.so.6": shared_elf()}
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "lib").mkdir()
        if complete:
            (root / "usr" / "lib").mkdir(parents=True)
        for path, data in files.items():
            full = root / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
        return scan_rootfs_snapshot(root, source_id="l08i-synthetic")


def sample():
    files = {"lib/libc.so.6": shared_elf()}
    return executable(), tar_gzip(tuple(files.items())), observed(files)


class ArmRuntimeEvidenceTests(unittest.TestCase):
    def test_correlates_dt_needed_to_matching_archive_without_launch_claim(self):
        candidate, archive, snapshot = sample()
        result = inspect_arm_runtime_evidence(
            candidate, archive, snapshot,
            expected_candidate_sha256=hashlib.sha256(candidate).hexdigest(),
            expected_archive_sha256=hashlib.sha256(archive).hexdigest(),
            expected_audit_sha256=snapshot["audit_sha256"],
            expected_source_id="l08i-synthetic")
        self.assertEqual(result["archive_verdict"], "scoped_content_match")
        self.assertEqual(result["needed_count"], 1)
        self.assertEqual(result["header_matches_in_supplied_archive"], 1)
        self.assertEqual(result["needed"][0]["needed"], "libc.so.6")
        self.assertEqual(result["needed"][0]["state"],
                         "header_matched_in_supplied_archive_only")
        self.assertEqual(result["needed"][0]["observed_target"],
                         "lib/libc.so.6")
        self.assertEqual(result["interpreter"]["state"], "not_declared")
        self.assertTrue(result["caller_candidate_digest_matched"])
        self.assertTrue(result["caller_archive_digest_matched"])
        for key in ("image_hash_verified", "image_to_export_link_verified",
                    "archive_origin_authenticated", "loader_abi_verified",
                    "symbol_versions_verified", "transitive_dependencies_verified",
                    "hardware_verified", "runtime_compatible", "launchable"):
            self.assertIs(result[key], False, key)

    def test_missing_dependency_is_unknown_not_asserted_absent_on_kobo(self):
        candidate = executable()
        snapshot = observed({})
        archive = tar_gzip(())
        result = inspect_arm_runtime_evidence(candidate, archive, snapshot)
        self.assertEqual(result["archive_verdict"], "scoped_content_match")
        self.assertEqual(result["needed"][0]["alias_state"],
                         "not_observed_in_scanned_directories")
        self.assertEqual(result["needed"][0]["state"],
                         "alias_or_header_unresolved")
        self.assertEqual(result["header_matches_in_supplied_archive"], 0)

    def test_partial_directory_disables_correlated_header(self):
        candidate, archive, _ = sample()
        snapshot = observed(complete=False)
        result = inspect_arm_runtime_evidence(candidate, archive, snapshot)
        self.assertEqual(result["archive_verdict"], "partial_scope")
        self.assertEqual(result["needed"][0]["state"], "archive_not_matching")
        self.assertFalse(result["snapshot_full_scope"])

    def test_archive_content_mismatch_never_qualifies_header(self):
        candidate, _, snapshot = sample()
        mismatched = tar_gzip((("lib/libc.so.6", b"changed-file"),))
        result = inspect_arm_runtime_evidence(candidate, mismatched, snapshot)
        self.assertEqual(result["archive_verdict"], "mismatch")
        self.assertEqual(result["needed"][0]["state"], "archive_not_matching")

    def test_rootfs_observation_forgery_rejected(self):
        candidate, archive, snapshot = sample()
        forged = copy.deepcopy(snapshot)
        forged["libraries"][0]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ArmRuntimeEvidenceError,
                                    "invalid_snapshot_evidence"):
            inspect_arm_runtime_evidence(candidate, archive, forged)
        with self.assertRaisesRegex(ArmRuntimeEvidenceError,
                                    "invalid_snapshot_evidence"):
            inspect_arm_runtime_evidence(
                candidate, archive, snapshot, expected_source_id="other")

    def test_expected_digest_mismatch_and_format_are_rejected(self):
        candidate, archive, snapshot = sample()
        for kwargs, error in (
            ({"expected_candidate_sha256": "0" * 64},
             "expected_candidate_digest_mismatch"),
            ({"expected_candidate_sha256": "not-a-sha"},
             "invalid_expected_candidate_digest"),
            ({"expected_archive_sha256": "0" * 64},
             "invalid_archive_evidence"),
            ({"expected_audit_sha256": "0" * 64},
             "invalid_snapshot_evidence"),
        ):
            with self.subTest(reason=error):
                with self.assertRaisesRegex(ArmRuntimeEvidenceError, error):
                    inspect_arm_runtime_evidence(
                        candidate, archive, snapshot, **kwargs)

    def test_gzip_crc_corruption_is_rejected(self):
        candidate, archive, snapshot = sample()
        corrupted = bytearray(archive)
        corrupted[-8] ^= 1
        with self.assertRaisesRegex(ArmRuntimeEvidenceError,
                                    "invalid_archive_evidence"):
            inspect_arm_runtime_evidence(candidate, bytes(corrupted), snapshot)

    def test_malformed_elf_and_size_limit_fail_closed(self):
        candidate, archive, snapshot = sample()
        bad = bytearray(candidate)
        struct.pack_into("<H", bad, 18, 62)  # x86_64, not EM_ARM
        with self.assertRaisesRegex(ArmRuntimeEvidenceError,
                                    "invalid_arm_elf"):
            inspect_arm_runtime_evidence(bytes(bad), archive, snapshot)
        with patch.object(module, "MAX_CANDIDATE_BYTES", 128):
            with self.assertRaisesRegex(ArmRuntimeEvidenceError,
                                        "invalid_arm_candidate_size"):
                inspect_arm_runtime_evidence(candidate, archive, snapshot)

    def test_interpreter_observed_at_exact_declared_path(self):
        binary = executable("/lib/ld-linux.so.3")
        files = {"lib/libc.so.6": shared_elf(),
                 "lib/ld-linux.so.3": shared_elf()}
        result = inspect_arm_runtime_evidence(
            binary, tar_gzip(tuple(files.items())), observed(files))
        self.assertEqual(result["interpreter"]["state"],
                         "header_matched_in_supplied_archive_only")
        self.assertEqual(result["interpreter"]["observed_target"],
                         "lib/ld-linux.so.3")
        self.assertFalse(result["loader_abi_verified"])

    def test_interpreter_unknown_or_out_of_scope_remains_unknown(self):
        candidate = executable("/lib/ld-linux.so.3")
        _, archive, snapshot = sample()
        missing = inspect_arm_runtime_evidence(candidate, archive, snapshot)
        self.assertEqual(missing["interpreter"]["state"],
                         "not_observed_at_declared_path")
        other = inspect_arm_runtime_evidence(
            executable("/opt/ld-linux.so.3"), archive, snapshot)
        self.assertEqual(other["interpreter"]["state"],
                         "outside_scanned_directories")

    def test_snapshot_library_symlink_is_observed_not_executed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "lib").mkdir()
            (root / "usr" / "lib").mkdir(parents=True)
            (root / "lib" / "libc-2.19.so").write_bytes(shared_elf())
            try:
                os.symlink("libc-2.19.so", root / "lib" / "libc.so.6")
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation unavailable on host")
            snapshot = scan_rootfs_snapshot(root, source_id="l08i-synthetic")
        archive = tar_gzip((
            ("lib/libc-2.19.so", shared_elf()),
            ("lib/libc.so.6", "libc-2.19.so")))
        report = inspect_arm_runtime_evidence(executable(), archive, snapshot)
        finding = report["needed"][0]
        self.assertEqual(finding["state"],
                         "header_matched_in_supplied_archive_only")
        self.assertEqual(finding["alias_state"],
                         "alias_to_arm_header_observed_only")
        self.assertEqual(finding["observed_path_chain"],
                         ("lib/libc.so.6", "lib/libc-2.19.so"))

    def test_compare_phase_never_opens_host_files_or_executes(self):
        candidate, archive, snapshot = sample()
        with patch("builtins.open", side_effect=AssertionError("disk open")):
            with patch("os.open", side_effect=AssertionError("disk open")):
                result = inspect_arm_runtime_evidence(
                    candidate, archive, snapshot)
        self.assertEqual(result["header_matches_in_supplied_archive"], 1)
        self.assertFalse(result["launchable"])


if __name__ == "__main__":
    unittest.main()
