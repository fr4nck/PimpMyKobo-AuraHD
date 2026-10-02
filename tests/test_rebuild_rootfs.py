import hashlib
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
    def test_non_linux_backend_returns_without_tool_lookup(self):
        for platform in ("win32", "darwin"):
            with self.subTest(platform=platform):
                with mock.patch.object(mod.sys, "platform", platform), mock.patch.object(
                    mod.shutil, "which", side_effect=AssertionError("unexpected tool lookup")
                ) as which:
                    errors = mod.require_linux_backend()
                self.assertEqual(
                    ["rootfs construction requires Linux (native, WSL2, VM, or live USB)"],
                    errors,
                )
                which.assert_not_called()

    def test_rejects_linux_devices(self):
        self.assertTrue(mod.looks_like_device("/dev/sdb"))
        self.assertTrue(mod.looks_like_device("/dev/mmcblk0p2"))

    def test_rejects_windows_physical_drive(self):
        self.assertTrue(mod.looks_like_device(r"\\.\PhysicalDrive2"))

    def test_regular_paths_are_not_devices(self):
        self.assertFalse(mod.looks_like_device("backup/recovery.img"))
        self.assertFalse(mod.looks_like_device("C:/Users/Test/recovery.img"))

    def _fixture(self, root: Path):
        recovery = root / "p2-récupération.img"
        recovery.write_bytes(b"recovery-test-data")
        digest = hashlib.sha256(recovery.read_bytes()).hexdigest()
        manifest = root / "backup manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "tool": "backup-aura-hd", "status": "complete", "complete": True,
            "identification": {"aura_hd_e606c0": True, "hwconfig": {"pcb": {"raw": 28, "decoded": "E606C0"}}},
            "mbr": {"partitions": [{"number": 1, "size": 1024}, {"number": 2, "size": len(recovery.read_bytes())}]},
            "components": [
                {"name": "p1_rootfs", "file": "p1-rootfs.img", "size": 1024, "status": "verified", "sha256_destination": "1" * 64},
                {"name": "p2_recoveryfs", "file": "p2-recoveryfs.img", "size": len(recovery.read_bytes()), "status": "verified", "sha256_destination": digest},
            ],
            "target_fingerprint": {"algorithm": "pmkb-target-v1", "sha256": "2" * 64},
        }), encoding="utf-8")
        return manifest, recovery

    def test_backup_v1_manifest_reaches_ready_without_creating_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); output = root / "new rootfs.img"
            result = mod.preflight(manifest, recovery, output)
            self.assertEqual("ready", result["status"]); self.assertFalse(result["ok"]); self.assertFalse(output.exists())

    def test_incomplete_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8")); data["complete"] = False; data["status"] = "failed"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual("failed", mod.preflight(manifest, recovery, root / "out.img")["status"])

    def test_unverified_recovery_component_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root)
            data = json.loads(manifest.read_text(encoding="utf-8")); data["components"][1]["status"] = "failed"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual("failed", mod.preflight(manifest, recovery, root / "out.img")["status"])

    def test_bad_recovery_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); recovery.write_bytes(b"changed")
            self.assertEqual("failed", mod.preflight(manifest, recovery, root / "out.img")["status"])

    def test_existing_output_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); output = root / "out.img"; output.write_bytes(b"do not overwrite")
            self.assertEqual("failed", mod.preflight(manifest, recovery, output)["status"])
            self.assertEqual(b"do not overwrite", output.read_bytes())

    def test_preflight_never_opens_inputs_for_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); real_open = Path.open
            def guarded_open(path, mode="r", *args, **kwargs):
                if Path(path) in (manifest, recovery) and any(flag in mode for flag in ("w", "a", "+")):
                    raise AssertionError("input opened for writing")
                return real_open(path, mode, *args, **kwargs)
            with mock.patch.object(Path, "open", guarded_open):
                self.assertEqual("ready", mod.preflight(manifest, recovery, root / "out.img")["status"])

    def test_non_linux_build_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); output = root / "out.img"
            with mock.patch.object(mod.sys, "platform", "win32"):
                result = mod.build_rootfs(manifest, recovery, output)
            self.assertEqual("failed", result["status"]); self.assertFalse(output.exists()); self.assertFalse((root / "out.img.part").exists())

    def test_missing_backend_tool_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root); output = root / "out.img"
            with mock.patch.object(mod.sys, "platform", "linux"), mock.patch.object(mod.shutil, "which", return_value=None):
                result = mod.build_rootfs(manifest, recovery, output)
            self.assertEqual("failed", result["status"]); self.assertFalse(output.exists())

    def test_build_never_invokes_disk_or_mount_commands(self):
        forbidden = {"dd", "mount", "umount", "diskpart", "blockdev"}
        seen = []
        def fake_run(argv, **kwargs):
            seen.append(Path(argv[0]).name)
            raise RuntimeError("stop synthetic build")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest, recovery = self._fixture(root)
            with mock.patch.object(mod.sys, "platform", "linux"), mock.patch.object(mod.shutil, "which", return_value="/usr/bin/tool"), mock.patch.object(mod.subprocess, "run", side_effect=fake_run):
                mod.build_rootfs(manifest, recovery, root / "out.img")
        self.assertFalse(forbidden.intersection(seen))


if __name__ == "__main__":
    unittest.main()
