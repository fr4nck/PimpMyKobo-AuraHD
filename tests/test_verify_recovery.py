from __future__ import annotations

import gzip
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "verify-recovery.py"
SPEC = importlib.util.spec_from_file_location("verify_recovery", SCRIPT)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def build_recovery(root: Path) -> None:
    (root / "upgrade" / "ntx508").mkdir(parents=True)
    sample = b"recovery sample\n"
    (root / "sample.txt").write_bytes(sample)
    (root / "fs.md5sum").write_text(f"{md5(sample)}  sample.txt\n", encoding="utf-8")

    for name, payload in (("fs.tgz", b"factory rootfs" * 100), ("db.tgz", b"factory database" * 50)):
        with gzip.open(root / "upgrade" / name, "wb") as gz:
            gz.write(payload)

    (root / "upgrade" / "ntx508" / "u-boot_mddr_512-E606C0-K4X2G323PC.bin").write_bytes(
        b"u-boot synthetic"
    )
    (root / "upgrade" / "ntx508" / "uImage-E606C0").write_bytes(b"kernel synthetic")


class VerifyRecoveryTests(unittest.TestCase):
    def test_complete_recovery_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            result = verify.inspect_recovery(root, True, True)
            self.assertTrue(result["ok"])
            self.assertTrue(result["manifest"]["ok"])
            self.assertTrue(all(item["ok"] for item in result["archives"]))
            self.assertTrue(result["artifacts"]["ok"])
            self.assertEqual(len(result["sha256"]), 4)

    def test_manifest_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "sample.txt").write_text("modified\n", encoding="utf-8")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertEqual(len(result["manifest"]["mismatched"]), 1)

    def test_corrupt_factory_archive_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "fs.tgz").write_bytes(b"not gzip")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertFalse(result["archives"][0]["ok"])

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


if __name__ == "__main__":
    unittest.main()
