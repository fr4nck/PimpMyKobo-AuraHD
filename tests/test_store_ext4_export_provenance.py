"""L08-J synthetic ext4 image and exported library evidence checks."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from ext4_export_provenance import compare_ext4_image_to_snapshot, Ext4ExportError
from rootfs_snapshot_audit import scan_rootfs_snapshot

BLOCK = 1024


def arm_shared():
    data = bytearray(52)
    data[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", data, 16, 3, 40, 1)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<H", data, 40, 52)
    return bytes(data)


def _directory(records):
    data = bytearray(BLOCK)
    offset = 0
    for i, (name, inode, kind) in enumerate(records):
        name = name.encode("ascii")
        length = (8 + len(name) + 3) & ~3
        if i == len(records) - 1:
            length = BLOCK - offset
        struct.pack_into("<IHBB", data, offset, inode, length, len(name), kind)
        data[offset + 8:offset + 8 + len(name)] = name
        offset += length
    return bytes(data)


def _inode(image, num, mode, size, *, block=None, link=None):
    off = 3 * BLOCK + (num - 1) * 128
    struct.pack_into("<H", image, off, mode)
    struct.pack_into("<I", image, off + 4, size)
    if link is not None:
        image[off + 40:off + 40 + len(link)] = link
    elif block is not None:
        struct.pack_into("<I", image, off + 32, 0x80000)
        struct.pack_into("<HHHHI", image, off + 40, 0xF30A, 1, 4, 0, 0)
        struct.pack_into("<IHHI", image, off + 52, 0, 1, 0, block)


def fake_ext4(*, symlink=False, extra=False):
    content = arm_shared()
    image = bytearray(128 * BLOCK)
    sb = BLOCK
    for offset, value in ((0, 32), (4, 128), (20, 1), (24, 0),
                          (32, 128), (40, 32), (96, 0x42), (100, 3)):
        struct.pack_into("<I", image, sb + offset, value)
    struct.pack_into("<H", image, sb + 56, 0xEF53)
    struct.pack_into("<H", image, sb + 58, 1)
    struct.pack_into("<H", image, sb + 88, 128)
    struct.pack_into("<I", image, 2 * BLOCK + 8, 3)
    root = [(".", 2, 2), ("..", 2, 2), ("lib", 11, 2), ("usr", 12, 2)]
    lib = [(".", 11, 2), ("..", 2, 2), ("libc.so.6", 14, 1)]
    if symlink:
        lib.append(("libalias.so.1", 15, 7))
    if extra:
        lib.append(("libextra.so", 16, 1))
    usr = [(".", 12, 2), ("..", 2, 2), ("lib", 13, 2)]
    usr_lib = [(".", 13, 2), ("..", 12, 2)]
    for block, records in ((20, root), (21, lib), (22, usr), (23, usr_lib)):
        image[block * BLOCK:(block + 1) * BLOCK] = _directory(records)
    image[24 * BLOCK:24 * BLOCK + len(content)] = content
    for num, block in ((2, 20), (11, 21), (12, 22), (13, 23)):
        _inode(image, num, 0o40755, BLOCK, block=block)
    _inode(image, 14, 0o100644, len(content), block=24)
    if symlink:
        _inode(image, 15, 0o120777, 9, link=b"libc.so.6")
    if extra:
        _inode(image, 16, 0o100644, len(content), block=24)
    return bytes(image)


def snapshot(image, *, lib_bytes=None, alias=False, complete=True, source_hash=None):
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "lib").mkdir()
        if complete:
            (root / "usr" / "lib").mkdir(parents=True)
        (root / "lib" / "libc.so.6").write_bytes(
            arm_shared() if lib_bytes is None else lib_bytes)
        if alias:
            try:
                (root / "lib" / "libalias.so.1").symlink_to("libc.so.6")
            except (OSError, NotImplementedError):
                raise unittest.SkipTest("symlinks unavailable")
        return scan_rootfs_snapshot(
            root, source_id="l08j-synthetic",
            declared_source_sha256=source_hash or hashlib.sha256(image).hexdigest())


def compare(image, snap):
    return compare_ext4_image_to_snapshot(
        image, snap, expected_image_sha256=hashlib.sha256(image).hexdigest())


class Ext4ExportTests(unittest.TestCase):
    def test_matches_scanned_scope_not_kobo_authentication(self):
        image = fake_ext4()
        out = compare(image, snapshot(image))
        self.assertEqual(out["verdict"], "scoped_image_export_match")
        self.assertEqual(out["matched"], ("lib/libc.so.6",))
        self.assertTrue(out["image_to_export_link_verified_for_scanned_scope"])
        self.assertFalse(out["filesystem_metadata_integrity_verified"])
        self.assertEqual(out["image_block_size"], 1024)
        for key in ("image_authenticated_as_kobo_p1", "source_provenance_authenticated",
                    "whole_rootfs_verified", "hardware_verified",
                    "runtime_compatible", "launchable"):
            self.assertIs(out[key], False, key)

    def test_export_mismatch(self):
        image = fake_ext4()
        out = compare(image, snapshot(image, lib_bytes=arm_shared() + b"x"))
        self.assertEqual(out["verdict"], "mismatch")
        self.assertEqual(out["content_mismatch"], ("lib/libc.so.6",))
        self.assertFalse(out["image_to_export_link_verified_for_scanned_scope"])

    def test_extra_image_library_is_not_ignored(self):
        image = fake_ext4(extra=True)
        out = compare(image, snapshot(image))
        self.assertEqual(out["missing_from_export"], ("lib/libextra.so",))
        self.assertEqual(out["verdict"], "mismatch")

    def test_symlink_target_is_compared_without_following(self):
        image = fake_ext4(symlink=True)
        out = compare(image, snapshot(image, alias=True))
        self.assertEqual(len(out["matched"]), 2)
        self.assertTrue(out["image_to_export_link_verified_for_scanned_scope"])

    def test_partial_export_not_full_proof(self):
        image = fake_ext4()
        out = compare(image, snapshot(image, complete=False))
        self.assertEqual(out["verdict"], "partial_scope")
        self.assertFalse(out["image_to_export_link_verified_for_scanned_scope"])

    def test_caller_hash_and_source_id_mismatch_rejected(self):
        image = fake_ext4()
        snap = snapshot(image)
        for keyword, reason in (
            ({"expected_image_sha256": "f" * 64}, "expected_image_digest_mismatch"),
            ({"expected_image_sha256": "bad"}, "invalid_expected_image_digest"),
            ({"expected_image_sha256": hashlib.sha256(image).hexdigest(),
              "expected_source_id": "different"}, "invalid_snapshot_evidence"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(Ext4ExportError, reason):
                    compare_ext4_image_to_snapshot(image, snap, **keyword)
        with self.assertRaisesRegex(Ext4ExportError, "snapshot_source_image_digest_mismatch"):
            compare(image, snapshot(image, source_hash="f" * 64))

    def test_bad_snapshot_observation_digest_rejected(self):
        image = fake_ext4()
        snap = copy.deepcopy(snapshot(image))
        snap["libraries"][0]["sha256"] = "f" * 64
        with self.assertRaisesRegex(Ext4ExportError, "invalid_snapshot_evidence"):
            compare(image, snap)

    def test_invalid_superblock_rejected(self):
        image = bytearray(fake_ext4())
        image[1024 + 56:1024 + 58] = b"\x00\x00"
        bad = bytes(image)
        with self.assertRaisesRegex(Ext4ExportError, "invalid_ext4_superblock"):
            compare(bad, snapshot(bad))

    def test_dirty_or_unsupported_features_rejected(self):
        for pos, value, fmt, reason in (
            (1024 + 58, 0, "<H", "unclean_ext4_image"),
            (1024 + 96, 0xC2, "<I", "unsupported_ext4_features"),
            (1024 + 100, 0x403, "<I", "unsupported_ext4_features"),
        ):
            image = bytearray(fake_ext4())
            struct.pack_into(fmt, image, pos, value)
            changed = bytes(image)
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(Ext4ExportError, reason):
                    compare(changed, snapshot(changed))

    def test_out_of_image_extent_rejected(self):
        image = bytearray(fake_ext4())
        pos = 3 * BLOCK + (14 - 1) * 128 + 60
        struct.pack_into("<I", image, pos, 9999)
        bad = bytes(image)
        with self.assertRaisesRegex(Ext4ExportError, "invalid_ext4_extent"):
            compare(bad, snapshot(bad))


    def test_inconsistent_block_and_inode_group_geometry_is_rejected(self):
        image = bytearray(fake_ext4())
        struct.pack_into("<I", image, 1024 + 40, 8)
        altered = bytes(image)
        with self.assertRaisesRegex(Ext4ExportError, "invalid_ext4_geometry"):
            compare(altered, snapshot(altered))

    def test_inode_table_must_fit_within_declared_image(self):
        image = bytearray(fake_ext4())
        struct.pack_into("<I", image, 2 * BLOCK + 8, 127)
        altered = bytes(image)
        with self.assertRaisesRegex(Ext4ExportError, "invalid_ext4_inode_table"):
            compare(altered, snapshot(altered))

    def test_malformed_directory_entries_and_dot_inode_are_rejected(self):
        for pos, fmt, value, reason in (
            (20 * BLOCK + 4, "<H", 4, "invalid_ext4_dirent"),
            (20 * BLOCK + 24, "<I", 1000, "invalid_ext4_dirent"),
            (20 * BLOCK, "<I", 11, "invalid_ext4_dot_entries"),
        ):
            with self.subTest(reason=reason, pos=pos):
                image = bytearray(fake_ext4())
                struct.pack_into(fmt, image, pos, value)
                altered = bytes(image)
                with self.assertRaisesRegex(Ext4ExportError, reason):
                    compare(altered, snapshot(altered))

    def test_overlapping_physical_extents_are_rejected(self):
        image = bytearray(fake_ext4())
        inode = 3 * BLOCK + (14 - 1) * 128
        struct.pack_into("<I", image, inode + 4, 2 * BLOCK)
        struct.pack_into("<H", image, inode + 42, 2)
        struct.pack_into("<IHHI", image, inode + 64, 1, 1, 0, 24)
        altered = bytes(image)
        with self.assertRaisesRegex(
                Ext4ExportError, "overlapping_ext4_physical_extents"):
            compare(altered, snapshot(altered))

    def test_comparator_never_reads_host_disk(self):
        image = fake_ext4()
        snap = snapshot(image)
        with patch("builtins.open", side_effect=AssertionError("host open")):
            with patch("os.open", side_effect=AssertionError("host open")):
                out = compare(image, snap)
        self.assertTrue(out["image_to_export_link_verified_for_scanned_scope"])

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("mke2fs"),
                         "real ext4 integration requires Linux e2fsprogs")
    def test_genuine_mke2fs_image_and_export(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            export = root / "export"
            (export / "lib").mkdir(parents=True)
            (export / "usr" / "lib").mkdir(parents=True)
            (export / "lib" / "libc.so.6").write_bytes(arm_shared())
            image_file = root / "rootfs.img"
            with image_file.open("xb") as fd:
                fd.truncate(8 * 1024 * 1024)
            conf = root / "mke2fs.conf"
            conf.write_text("[defaults]\n\n[fs_types]\n\tpmkb = {\n\t}\n",
                            encoding="utf-8")
            subprocess.run(
                ["mke2fs", "-q", "-F", "-T", "pmkb", "-L", "rootfs", "-b", "1024",
                 "-I", "256", "-O", "none,has_journal,extent,filetype,sparse_super,large_file,extra_isize",
                 "-d", str(export), str(image_file)],
                check=True, capture_output=True,
                env={**os.environ, "MKE2FS_CONFIG": str(conf)})
            image = image_file.read_bytes()
            scan = scan_rootfs_snapshot(
                export, source_id="l08j-real-ext4-fixture",
                declared_source_sha256=hashlib.sha256(image).hexdigest())
            result = compare(image, scan)
            self.assertEqual(result["verdict"], "scoped_image_export_match")
            self.assertFalse(result["image_authenticated_as_kobo_p1"])


if __name__ == "__main__":
    unittest.main()
