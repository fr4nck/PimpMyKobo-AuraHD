import os
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "experimental/offline-rootfs"


class ExperimentalContractTests(unittest.TestCase):
    def test_experimental_rootfs_cannot_enter_existing_recovery_pipeline(self):
        from test_restore_rootfs import RestoreSimulationTests
        fixture = RestoreSimulationTests("test_simulation_only_replaces_p1_in_a_new_copy")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        original = json.loads(fixture.report.read_text())
        for change in ({"tool": "pmkb-liberation-prototype"}, {"status": "experimental"}, {"complete": False}):
            fixture.report.write_text(json.dumps({**original, **change}))
            self.assertEqual("refused", fixture.preflight()["status"])
            self.assertFalse(fixture.output.exists())


@unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "POSIX shell required")
class OfflineGuardTests(unittest.TestCase):
    def test_loopback_only_required_unknown_and_missing_interfaces_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            guard = ROOT / "usr/bin/pmkb-check-offline"
            def run(path):
                return subprocess.run(["sh", str(guard), str(path)], capture_output=True).returncode
            self.assertNotEqual(0, run(root / "missing"))
            self.assertNotEqual(0, run(root))
            (root / "lo").mkdir()
            self.assertEqual(0, run(root))
            for name in ("eth0", "wlan0", "usb0", "unexpected interface", ".hidden"):
                (root / name).mkdir()
                self.assertNotEqual(0, run(root), name)
                (root / name).rmdir()
            (root / "dangling").symlink_to(root / "absent")
            self.assertNotEqual(0, run(root))

    def test_boot_sources_parse_without_running_any_mount_or_device_command(self):
        for name in ("etc/init.d/rcS", "usr/bin/pmkb-check-offline", "usr/bin/pmkb-reader", "bin/kobo_config.sh"):
            result = subprocess.run(["sh", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
