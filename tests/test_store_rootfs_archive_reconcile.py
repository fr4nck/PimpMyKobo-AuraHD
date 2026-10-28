"""L08-H synthetic archive-to-export equivalence tests, with no TAR extraction."""
from io import BytesIO
import hashlib
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from rootfs_archive_reconcile import (
    RootfsArchiveError, compare_tar_archive_to_snapshot,
)
from rootfs_snapshot_audit import scan_rootfs_snapshot
from rootfs_evidence_contract import verify_snapshot_evidence


def arm_shared():
    return bytes((127, 69, 76, 70, 1, 1, 1)) + (
        b"\x00" * 9) + (
        b"\x03\x00\x28\x00\x01\x00\x00\x00") + (
        b"\x00" * 12) + (
        b"\x00\x00\x00\x05") + (
        b"\x34\x00") + (b"\x00" * 10)


def build_archive(records):
    """Create entirely in-memory TAR.GZ from tuples (kind, path, value)."""
    stream = BytesIO()
    with tarfile.open(mode="w:gz", fileobj=stream) as out:
        for kind, path, data in records:
            info = tarfile.TarInfo(path)
            info.mtime = 0
            if kind == "directory":
                info.type = tarfile.DIRTYPE
                out.addfile(info)
            elif kind == "file":
                info.size = len(data)
                out.addfile(info, BytesIO(data))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = data
                out.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = data
                out.addfile(info)
            else:
                raise AssertionError(kind)
    return stream.getvalue()


def sample(root):
    (root / "lib").mkdir()
    (root / "usr" / "lib").mkdir(parents=True)
    (root / "lib" / "libc.so.6").write_bytes(arm_shared())
    # real symlink integration is tested separately (permission dependent)
    return scan_rootfs_snapshot(root, source_id="synthetic-tar-fixture")


def original():
    return build_archive([("file", "lib/libc.so.6", arm_shared())])


class TarReconciliationTests(unittest.TestCase):
    def test_compare_bytes_to_extracted_content(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = sample(root)
            raw = original()
            report = compare_tar_archive_to_snapshot(
                raw, snapshot,
                expected_archive_sha256=hashlib.sha256(raw).hexdigest())
            self.assertTrue(verify_snapshot_evidence(snapshot)[
                "observation_digest_consistent"])
        self.assertEqual(report["verdict"], "scoped_content_match")
        self.assertEqual(report["matched"], ("lib/libc.so.6",))
        self.assertEqual(report["content_mismatch"], ())
        self.assertTrue(report["expected_archive_digest_matched"])
        self.assertGreater(report["archive_decompressed_bytes_checked"], 0)
        self.assertEqual(report["library_bytes_inspected"], len(arm_shared()))
        for key in ("archive_is_original_ext4_image",
                    "original_image_hash_verified",
                    "archive_origin_authenticated",
                    "export_matches_original_image", "hardware_verified",
                    "runtime_compatible", "launchable"):
            self.assertIs(report[key], False, key)

    def test_conventional_tar_dot_root_is_accepted(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
            data = build_archive([
                ("directory", "./", ""),
                ("directory", "./lib/", ""),
                ("file", "./lib/libc.so.6", arm_shared())])
            # tarfile commonly prefixes archive paths with "./".
            r = compare_tar_archive_to_snapshot(data, snapshot)
        self.assertEqual(r["verdict"], "scoped_content_match")

    def test_file_bytes_differ_without_mutating_snapshot(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
            raw = build_archive([("file", "lib/libc.so.6",
                                  arm_shared() + b"edited")])
            result = compare_tar_archive_to_snapshot(raw, snapshot)
        self.assertEqual(result["verdict"], "mismatch")
        self.assertEqual(result["content_mismatch"], ("lib/libc.so.6",))
        self.assertEqual(result["matched"], ())
        self.assertFalse(result["launchable"])

    def test_missing_archive_and_export_are_different(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
            missing = compare_tar_archive_to_snapshot(
                build_archive([]), snapshot)
            unexpected = compare_tar_archive_to_snapshot(
                build_archive([
                    ("file", "lib/libc.so.6", arm_shared()),
                    ("file", "usr/lib/libz.so.1", b"other")]), snapshot)
        self.assertEqual(missing["missing_from_archive"], ("lib/libc.so.6",))
        self.assertEqual(unexpected["missing_from_export"],
                         ("usr/lib/libz.so.1",))
        self.assertEqual(unexpected["verdict"], "mismatch")

    def test_incomplete_directory_is_not_complete_evidence(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "lib").mkdir()
            (root / "lib" / "libc.so.6").write_bytes(arm_shared())
            snapshot = scan_rootfs_snapshot(root, source_id="partial")
            result = compare_tar_archive_to_snapshot(original(), snapshot)
        self.assertEqual(result["verdict"], "partial_scope")
        self.assertFalse(result["snapshot_full_scope"])

    def test_symlink_name_and_target_observed_but_never_followed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            sample(root)
            try:
                (root / "lib" / "libc.so").symlink_to("libc.so.6")
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation not allowed on host")
            snapshot = scan_rootfs_snapshot(root, source_id="symlink-fixture")
            matching = build_archive([
                ("file", "lib/libc.so.6", arm_shared()),
                ("symlink", "lib/libc.so", "libc.so.6")])
            result = compare_tar_archive_to_snapshot(matching, snapshot)
            changed = build_archive([
                ("file", "lib/libc.so.6", arm_shared()),
                ("symlink", "lib/libc.so", "libfoo.so")])
            mismatch = compare_tar_archive_to_snapshot(changed, snapshot)
        self.assertEqual(result["verdict"], "scoped_content_match")
        self.assertEqual(len(result["matched"]), 2)
        self.assertEqual(mismatch["content_mismatch"], ("lib/libc.so",))

    def test_bad_archive_names_duplicates_hardlinks_are_rejected(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        archives = (
            (build_archive([("file", "../lib/libevil.so", b"evil")]),
             "unsafe_archive_member"),
            (build_archive([("file", "/lib/libevil.so", b"evil")]),
             "unsafe_archive_member"),
            (build_archive([("file", "lib/libc.so.6", arm_shared()),
                            ("file", "lib/libc.so.6", arm_shared())]),
             "duplicate_archive_library"),
            (build_archive([("hardlink", "lib/libc.so.6", "lib/other.so")]),
             "unsupported_archive_library_kind"),
            (build_archive([("file", "lib/bad name.so", b"x")]),
             "invalid_archive_library_name"),
        )
        for raw, reason in archives:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(RootfsArchiveError, reason):
                    compare_tar_archive_to_snapshot(raw, snapshot)

    def test_corrupted_tar_and_digest_rejected(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        for raw, reason, expected in (
            (b"", "invalid_archive_size", None),
            (b"not-gzip", "unreadable_rootfs_archive", None),
            (original(), "expected_archive_digest_mismatch", "0" * 64),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(RootfsArchiveError, reason):
                    compare_tar_archive_to_snapshot(
                        raw, snapshot, expected_archive_sha256=expected)

    def test_gzip_crc_and_truncated_footer_are_rejected(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        valid = original()
        corrupted = bytearray(valid)
        corrupted[-8] ^= 0xFF  # gzip CRC32 footer
        for raw in (valid[:-6], bytes(corrupted)):
            with self.subTest(length=len(raw)):
                with self.assertRaisesRegex(
                        RootfsArchiveError, "unreadable_rootfs_archive"):
                    compare_tar_archive_to_snapshot(raw, snapshot)

    def test_reject_concatenated_gzip_and_trailing_bytes(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        valid = original()
        for suffix in (valid, b"extra bytes", b"\\x00"):
            raw = valid + suffix
            with self.subTest(suffix_length=len(suffix)):
                with self.assertRaisesRegex(
                        RootfsArchiveError, "gzip_trailing_data"):
                    compare_tar_archive_to_snapshot(raw, snapshot)

    def test_validation_crosses_compressed_chunk_boundary(self):
        # An unrelated TAR entry must still be decompressed and CRC-checked,
        # even though it is outside lib/ and usr/lib/.
        noise = b"".join(
            hashlib.sha256(i.to_bytes(4, "little")).digest()
            for i in range(4096))
        raw = build_archive([
            ("file", "lib/libc.so.6", arm_shared()),
            ("file", "share/opaque-data.bin", noise)])
        self.assertGreater(len(raw), 65536)
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
            result = compare_tar_archive_to_snapshot(raw, snapshot)
        self.assertEqual(result["verdict"], "scoped_content_match")
        self.assertGreater(result["archive_decompressed_bytes_checked"],
                           len(noise))

    def test_bounded_decompressed_stream(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        import rootfs_archive_reconcile as module
        with patch.object(module, "MAX_GZIP_UNCOMPRESSED_BYTES", 80):
            with self.assertRaisesRegex(RootfsArchiveError,
                                        "gzip_uncompressed_size_limit"):
                compare_tar_archive_to_snapshot(original(), snapshot)

    def test_tampered_snapshot_rejected_before_comparison(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        snapshot["libraries"][0]["sha256"] = "f" * 64
        with self.assertRaisesRegex(RootfsArchiveError,
                                    "invalid_snapshot_evidence"):
            compare_tar_archive_to_snapshot(original(), snapshot)

    def test_tiny_archive_limit_fail_closed(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
        import rootfs_archive_reconcile as module
        with patch.object(module, "MAX_ARCHIVE_BYTES", 8):
            with self.assertRaisesRegex(
                    RootfsArchiveError, "invalid_archive_size"):
                compare_tar_archive_to_snapshot(original(), snapshot)

    def test_no_disk_access_when_comparing_reports_and_archive_bytes(self):
        with TemporaryDirectory() as temp:
            snapshot = sample(Path(temp))
            raw = original()
        with patch("builtins.open", side_effect=AssertionError("disk open")):
            with patch("os.open", side_effect=AssertionError("disk open")):
                r = compare_tar_archive_to_snapshot(raw, snapshot)
        self.assertEqual(r["verdict"], "scoped_content_match")
        self.assertFalse(r["hardware_verified"])


if __name__ == "__main__":
    unittest.main()
