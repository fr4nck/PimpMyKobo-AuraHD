from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "verify-recovery.py"
SPEC = importlib.util.spec_from_file_location("verify_recovery", SCRIPT)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def make_tgz(path: Path, count: int = 5) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for index in range(count):
            data = (f"payload-{index}\n" * 100).encode()
            info = tarfile.TarInfo(f"file-{index}.txt")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def make_uimage(path: Path, payload: bytes = b"kernel synthetic") -> None:
    header = bytearray(64)
    header[0:4] = verify.UBOOT_MAGIC.to_bytes(4, "big")
    header[12:16] = len(payload).to_bytes(4, "big")
    header[24:28] = (zlib.crc32(payload) & 0xFFFFFFFF).to_bytes(4, "big")
    header[28] = 5
    header[29] = 2
    header[30] = 2
    header[31] = 0
    header[32:36] = b"test"
    header_crc = zlib.crc32(header) & 0xFFFFFFFF
    header[4:8] = header_crc.to_bytes(4, "big")
    path.write_bytes(bytes(header) + payload)


def build_recovery(root: Path) -> None:
    ntx = root / "upgrade" / "ntx508"
    ntx.mkdir(parents=True)
    sample = b"recovery sample\n"
    (root / "sample.txt").write_bytes(sample)
    (root / "fs.md5sum").write_text(
        f"{md5(sample)}  sample.txt\n", encoding="utf-8"
    )
    make_tgz(root / "upgrade" / "fs.tgz", 5)
    make_tgz(root / "upgrade" / "db.tgz", 2)
    (ntx / "u-boot_mddr_512-E606C0-K4X2G323PC.bin").write_bytes(
        b"u-boot synthetic"
    )
    make_uimage(ntx / "uImage-E606C0")


class VerifyRecoveryTests(unittest.TestCase):
    def test_complete_recovery_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            result = verify.inspect_recovery(root, True, True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["manifest"]["ok"])
            self.assertTrue(all(item["ok"] for item in result["archives"]))
            self.assertTrue(result["artifacts"]["ok"])

    def test_gzip_crc_corruption_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            data = bytearray(path.read_bytes())
            data[-8] ^= 0x01
            path.write_bytes(data)
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_truncated_archive_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            data = path.read_bytes()
            path.write_bytes(data[: max(20, len(data) // 2)])
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_trailing_garbage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            path.write_bytes(path.read_bytes() + b"garbage")
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_manifest_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "sample.txt").write_text("modified\n", encoding="utf-8")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertEqual(len(result["manifest"]["mismatched"]), 1)

    def test_manifest_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            outside = root.parent / "outside.txt"
            outside.write_bytes(b"outside")
            try:
                (root / "fs.md5sum").write_text(
                    f"{md5(b'outside')}  ../outside.txt\n", encoding="utf-8"
                )
                result = verify.inspect_recovery(root, True, False)
                self.assertFalse(result["ok"])
                self.assertTrue(result["manifest"]["invalid_entries"])
            finally:
                try:
                    outside.unlink()
                except FileNotFoundError:
                    pass

    def test_gnu_escaped_manifest_name_is_decoded_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            name = "a\\b"
            data = b"x"
            (root / name).write_bytes(data)
            (root / "fs.md5sum").write_text(
                "\\" + f"{md5(data)}  a\\\\b\n", encoding="utf-8"
            )
            result = verify.verify_manifest(root)
            self.assertTrue(result["ok"], result)

    def test_empty_uboot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (
                root
                / "upgrade"
                / "ntx508"
                / "u-boot_mddr_512-E606C0-K4X2G323PC.bin"
            ).write_bytes(b"")
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_different_e606c0_ram_variant_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            old = (
                root
                / "upgrade"
                / "ntx508"
                / "u-boot_mddr_512-E606C0-K4X2G323PC.bin"
            )
            new = old.with_name("u-boot_mddr_512-E606C0-OTHER-RAM.bin")
            old.rename(new)
            result = verify.inspect_recovery(root, True, False)
            self.assertTrue(result["artifacts"]["selected_uboot"]["path"].endswith(new.name))

    def test_bad_uimage_magic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "ntx508" / "uImage-E606C0").write_bytes(
                b"x" * 100
            )
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_bad_uimage_crc_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "ntx508" / "uImage-E606C0"
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_skip_md5_is_partial_and_never_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "fs.md5sum").unlink()
            result = verify.inspect_recovery(root, False, False)
            self.assertFalse(result["ok"])
            self.assertTrue(result["partial"])
            self.assertTrue(result["checks_ok"])

    def test_symlink_escape_for_critical_archive_is_rejected(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as out:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            path.unlink()
            external = Path(out) / "fs.tgz"
            make_tgz(external)
            try:
                path.symlink_to(external)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertFalse(result["archives"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
