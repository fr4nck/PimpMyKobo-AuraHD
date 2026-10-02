import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rebuild_rootfs", ROOT / "tools" / "rebuild-rootfs.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)


class RebuildRootfsPreflightTests(unittest.TestCase):
    def test_rejects_linux_devices(self):
        self.assertTrue(mod.looks_like_device("/dev/sdb"))
        self.assertTrue(mod.looks_like_device("/dev/mmcblk0p2"))

    def test_rejects_windows_physical_drive(self):
        self.assertTrue(mod.looks_like_device(r"\\.\PhysicalDrive2"))

    def test_regular_paths_are_not_devices(self):
        self.assertFalse(mod.looks_like_device("backup/recovery.img"))
        self.assertFalse(mod.looks_like_device("C:/Users/Test/recovery.img"))

    def _fixture(self, root: Path):
        recovery = root / "récovery image.bin"
        recovery.write_bytes(b"recovery-test-data")
        sha = mod.sha256_file(recovery)
        manifest = root / "backup manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1,
            "complete": True,
            "device": "E606C0",
            "source_fingerprint": "synthetic-test-fingerprint",
            "partitions": [{"number": 1, "size": 1024}, {"number": 2, "size": len(recovery.read_bytes())}],
            "recovery": {"size": len(recovery.read_bytes()), "sha256": sha},
        }), encoding="utf-8")
        return manifest, recovery

    def test_valid_synthetic_inputs_reach_ready_without_creating_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, recovery = self._fixture(root)
            output = root / "new rootfs.img"
            result = mod.preflight(manifest, recovery, output)
            self.assertEqual("ready", result["status"])
            self.assertFalse(result["ok"])
            self.assertFalse(output.exists())

    def test_bad_recovery_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, recovery = self._fixture(root)
            recovery.write_bytes(b"changed")
            result = mod.preflight(manifest, recovery, root / "out.img")
            self.assertEqual("failed", result["status"])
            self.assertTrue(any("SHA-256" in e or "size" in e for e in result["errors"]))

    def test_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, recovery = self._fixture(root)
            output = root / "out.img"
            output.write_bytes(b"do not overwrite")
            result = mod.preflight(manifest, recovery, output)
            self.assertEqual("failed", result["status"])
            self.assertEqual(b"do not overwrite", output.read_bytes())

    def test_preflight_never_opens_inputs_for_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, recovery = self._fixture(root)
            real_open = Path.open

            def guarded_open(path, mode="r", *args, **kwargs):
                if Path(path) in (manifest, recovery) and any(flag in mode for flag in ("w", "a", "+")):
                    raise AssertionError("input opened for writing")
                return real_open(path, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", guarded_open):
                result = mod.preflight(manifest, recovery, root / "out.img")
            self.assertEqual("ready", result["status"])


if __name__ == "__main__":
    unittest.main()
