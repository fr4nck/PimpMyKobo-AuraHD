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
        for name in ("etc/init.d/rcS", "usr/bin/pmkb-check-offline", "usr/bin/pmkb-check-onboard",
                     "usr/bin/pmkb-reader", "bin/kobo_config.sh"):
            result = subprocess.run(["sh", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)

    def test_onboard_mount_required_missing_or_stale_table_refused(self):
        guard = ROOT / "usr/bin/pmkb-check-onboard"
        def run(mounts_path):
            return subprocess.run(["sh", str(guard), str(mounts_path)], capture_output=True).returncode
        with tempfile.TemporaryDirectory() as temporary:
            mounts = Path(temporary) / "mounts"
            self.assertNotEqual(0, run(mounts))  # missing mounts table
            mounts.write_text("", encoding="utf-8")
            self.assertNotEqual(0, run(mounts))  # empty: no mount at all
            mounts.write_text("/dev/mmcblk0p1 / ext4 ro 0 0\n", encoding="utf-8")
            self.assertNotEqual(0, run(mounts))  # mounted, but not at /mnt/onboard
            mounts.write_text("/dev/mmcblk0p3 /mnt/onboard vfat ro,noatime,nodiratime,utf8 0 0\n", encoding="utf-8")
            self.assertEqual(0, run(mounts))
            mounts.write_text("/dev/mmcblk0p3 /mnt/onboard-backup vfat ro 0 0\n", encoding="utf-8")
            self.assertNotEqual(0, run(mounts))  # similarly named mountpoint must not match


class RootfsSourceContractTests(unittest.TestCase):
    """Static ordering checks on the overlay sources; nothing here is executed."""

    def test_rcS_creates_onboard_directory_before_mounting_it(self):
        lines = (ROOT / "etc/init.d/rcS").read_text(encoding="utf-8").splitlines()
        mkdir_lines = [i for i, line in enumerate(lines) if "mkdir -p /mnt/onboard" in line]
        mount_lines = [i for i, line in enumerate(lines) if "mount" in line and "/mnt/onboard" in line
                       and "mkdir" not in line]
        self.assertTrue(mkdir_lines, "rcS must create /mnt/onboard before mounting it")
        self.assertTrue(mount_lines, "rcS must mount /mnt/onboard")
        self.assertLess(mkdir_lines[0], mount_lines[0])

    def test_pmkb_reader_reverifies_onboard_mount_before_launching_koreader(self):
        lines = (ROOT / "usr/bin/pmkb-reader").read_text(encoding="utf-8").splitlines()
        guard_lines = [i for i, line in enumerate(lines) if "pmkb-check-onboard" in line]
        exec_lines = [i for i, line in enumerate(lines) if line.strip().startswith("exec ")]
        self.assertTrue(guard_lines, "pmkb-reader must re-check the onboard mount before launching")
        self.assertTrue(exec_lines)
        self.assertLess(guard_lines[0], exec_lines[0])
