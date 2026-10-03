import errno
import json
import os
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from test_import_legacy_backup import load, legacy
import test_prepare_p1_restore as plan_fixtures

mod = load("restore_linux", "restore-p1-linux.py")


class RecordingHandle:
    def __init__(self, handle, test):
        self.handle = handle
        self.test = test

    def __getattr__(self, name):
        return getattr(self.handle, name)

    def write(self, data):
        events = [json.loads(line) for line in self.test.journal.read_text().splitlines()]
        self.test.assertEqual("writing_p1", events[-1]["phase"])
        offset = self.handle.tell()
        self.test.assertGreaterEqual(offset, self.test.plan_data["p1_offset"])
        self.test.assertLessEqual(offset + len(data), self.test.plan_data["p1_offset"] + self.test.plan_data["p1_size"])
        self.test.writes.append((offset, len(data)))
        if self.test.write_error:
            # Model a failure after one actual partial write to a synthetic file.
            self.handle.write(data[:512])
            raise self.test.write_error
        return self.handle.write(data[:512])  # Exercise partial-write handling.


class LinuxRestoreTests(unittest.TestCase):
    setUp = plan_fixtures.PrepareP1Tests.setUp
    setup_plan = plan_fixtures.PrepareP1Tests.setup_plan

    def fixture(self):
        self.setup_plan()
        result = plan_fixtures.prepare.prepare(*self.args)
        self.assertEqual("prepared", result["status"], result)
        self.plan_data = result
        self.journal = self.root / "restore.journal.jsonl"
        self.device = self.root / "fake-device.img"
        self.device.write_bytes(self.target.read_bytes())
        self.writes = []
        self.write_error = None
        self.flush_error = None
        self.after_flush = None
        self.before_write_recheck = None
        self.device_size = self.device.stat().st_size
        self.args_run = (self.plan, self.manifest, self.report, self.rootfs, self.target,
                         self.acquisition, self.output, self.args[6], self.journal)
        test = self

        class FakeDisk:
            def __init__(self, path, writable):
                test.assertEqual(test.device, path)
                self.identity = {"path": str(path), "partition_devices": ["8:32", "8:33"]}
                self.handle = RecordingHandle(path.open("r+b" if writable else "rb", buffering=0), test)
                self.writable = writable

            def size(self):
                return test.device_size

            def recheck(self):
                if test.before_write_recheck:
                    test.before_write_recheck()

            def flush_and_invalidate(self):
                if test.flush_error:
                    raise test.flush_error
                os.fsync(self.handle.fileno())
                if test.after_flush:
                    test.after_flush()

            def close(self):
                self.handle.close()

        self.fake_disk = FakeDisk

    def run_fake(self, write=False, **kwargs):
        with (mock.patch.object(mod, "require_native_linux"),
              mock.patch.object(mod, "LinuxDisk", self.fake_disk),
              mock.patch.object(mod, "inspect_device", return_value={"partition_devices": ["8:32"]}),
              mock.patch.object(mod, "persistent_storage"),
              mock.patch.object(mod, "check_staged_filesystem", return_value={"exit_code": 0, "fixture": "synthetic mocked filesystem check"}),
              mock.patch.object(mod, "durable_directory")):
            return mod.execute(*self.args_run, device=self.device, check_device=not write,
                               write_p1=write, ack_linux_live=True,
                               authorize_plan_sha256=legacy.digest(self.plan) if write else None, **kwargs)

    def test_default_local_mode_never_opens_device_or_journal(self):
        self.fixture()
        with mock.patch.object(mod, "LinuxDisk", side_effect=AssertionError("device opened")):
            result = mod.execute(*self.args_run, device=Path("/dev/sdb"))
        self.assertEqual("local_ready", result["status"], result)
        self.assertFalse(self.journal.exists())
        self.assertEqual([], self.writes)

    def test_missing_or_wrong_authorization_refuses_before_device_access(self):
        self.fixture()
        for token in (None, "0" * 64):
            with mock.patch.object(mod, "LinuxDisk", side_effect=AssertionError("opened")):
                result = mod.execute(*self.args_run, write_p1=True, device=self.device,
                                     authorize_plan_sha256=token)
            self.assertEqual("refused", result["status"])
        self.assertFalse(self.journal.exists())

    def test_read_only_physical_check_creates_no_journal_or_write(self):
        self.fixture()
        before = self.device.read_bytes()
        result = self.run_fake()
        self.assertEqual("device_ready_read_only", result["status"], result)
        self.assertEqual(before, self.device.read_bytes())
        self.assertEqual([], self.writes)
        self.assertFalse(self.journal.exists())

    def test_success_only_writes_p1_with_durable_intent_and_rollback(self):
        self.fixture()
        original = self.device.read_bytes()
        result = self.run_fake(write=True)
        self.assertEqual("ok", result["status"], result)
        offset = self.plan_data["p1_offset"]; end = offset + self.plan_data["p1_size"]
        after = self.device.read_bytes()
        self.assertEqual(original[:offset], after[:offset])
        self.assertEqual(original[end:], after[end:])
        self.assertEqual(self.rootfs.read_bytes(), after[offset:end])
        self.assertEqual(original[offset:end], Path(result["rollback"]).read_bytes())
        self.assertEqual(original, self.target.read_bytes())
        self.assertEqual(["local_verified", "writing_p1", "verified"],
                         [json.loads(line)["phase"] for line in self.journal.read_text().splitlines()])
        self.assertTrue(result["outside_p1_unchanged"])
        self.assertEqual(legacy.PROVENANCE, result["input_provenance"])
        self.assertFalse(result["physical_restore_eligible"])

    def test_wrong_capacity_or_any_target_byte_refuses_without_write(self):
        self.fixture()
        self.device_size -= 512
        self.assertEqual("refused", self.run_fake()["status"])
        self.device_size += 512
        for offset in (0, self.plan_data["p1_offset"], self.device_size - 1):
            before = self.device.read_bytes()
            with self.device.open("r+b") as handle:
                handle.seek(offset); handle.write(b"?" if before[offset] != 63 else b"!")
            self.assertEqual("refused", self.run_fake()["status"])
            self.device.write_bytes(before)
        self.assertEqual([], self.writes)

    def test_plan_mutation_refused_even_with_new_authorization_token(self):
        self.fixture()
        self.plan_data["p1_offset"] += 512
        self.plan.write_text(json.dumps(self.plan_data))
        result = self.run_fake(write=True)
        self.assertEqual("refused", result["status"])
        self.assertEqual([], self.writes)

    def test_busy_device_refuses_without_writes(self):
        self.fixture()
        with (mock.patch.object(mod, "require_native_linux"),
              mock.patch.object(mod, "LinuxDisk", side_effect=OSError(errno.EBUSY, "busy"))):
            result = mod.execute(*self.args_run, device=self.device, check_device=True)
        self.assertEqual("refused", result["status"])
        self.assertFalse(result["device_write_attempted"])

    def test_interrupted_or_failed_write_keeps_rollback_and_reports_partial(self):
        for error in (OSError("write failure"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.fixture()
                self.write_error = error
                result = self.run_fake(write=True)
                self.assertEqual("failed", result["status"], result)
                self.assertTrue(result["p1_may_be_partial"])
                self.assertTrue(Path(str(self.journal) + ".original-p1.img").exists())
                self.assertEqual("failed", json.loads(self.journal.read_text().splitlines()[-1])["phase"])
                # New fixture for the next subcase; no automatic rollback/retry.
                self.tearDown_fixture()

    def tearDown_fixture(self):
        self.temp.cleanup()
        self.setUp()

    def test_flush_failure_is_never_success(self):
        self.fixture(); self.flush_error = OSError("flush failure")
        result = self.run_fake(write=True)
        self.assertEqual("failed", result["status"])
        self.assertTrue(result["p1_may_be_partial"])

    def test_postwrite_p1_or_preserved_region_corruption_is_detected(self):
        for offset in (0, 9961472, 9961472 + 8192):
            self.fixture()
            def corrupt():
                with self.device.open("r+b") as handle:
                    handle.seek(offset); handle.write(b"CORRUPTION")
            self.after_flush = corrupt
            result = self.run_fake(write=True)
            self.assertEqual("failed", result["status"], result)
            self.assertTrue(result["p1_may_be_partial"])
            self.tearDown_fixture()

    def test_target_change_immediately_before_write_is_refused(self):
        self.fixture()
        def corrupt():
            with self.device.open("r+b") as handle:
                handle.seek(0); handle.write(b"CORRUPTION")
        self.before_write_recheck = corrupt
        result = self.run_fake(write=True)
        self.assertEqual("refused", result["status"], result)
        self.assertEqual([], self.writes)

    def test_staged_replacement_tamper_is_refused_before_write(self):
        self.fixture()
        real_digest = mod.legacy.digest
        def tamper(path):
            if str(path).endswith(".original-p1.img"):
                Path(str(self.journal) + ".replacement.img").write_bytes(b"bad")
            return real_digest(path)
        with mock.patch.object(mod.legacy, "digest", side_effect=tamper):
            result = self.run_fake(write=True)
        self.assertEqual("refused", result["status"], result)
        self.assertEqual([], self.writes)

    def test_journal_failure_before_write_intent_never_writes(self):
        self.fixture()
        real_append = mod.append_event
        def fail(journal, **event):
            if event["phase"] == "writing_p1":
                raise OSError("journal full")
            return real_append(journal, **event)
        with mock.patch.object(mod, "append_event", side_effect=fail):
            result = self.run_fake(write=True)
        self.assertEqual("refused", result["status"])
        self.assertFalse(result["device_write_attempted"])
        self.assertEqual([], self.writes)

    def test_all_sidecar_collisions_are_refused_without_overwrite(self):
        self.fixture()
        for name in (str(self.journal), str(self.journal) + ".replacement.img", str(self.journal) + ".original-p1.img"):
            path = Path(name); path.write_bytes(b"keep")
            result = self.run_fake(write=True)
            self.assertEqual("refused", result["status"])
            self.assertEqual(b"keep", path.read_bytes()); path.unlink()
        self.assertEqual([], self.writes)

    def test_staged_filesystem_failure_prevents_device_open(self):
        self.fixture()
        with (mock.patch.object(mod, "require_native_linux"),
              mock.patch.object(mod, "inspect_device", return_value={"partition_devices": []}),
              mock.patch.object(mod, "persistent_storage"),
              mock.patch.object(mod, "check_staged_filesystem", side_effect=ValueError("e2fsck failed")),
              mock.patch.object(mod, "LinuxDisk", side_effect=AssertionError("device opened"))):
            result = mod.execute(*self.args_run, device=self.device, write_p1=True,
                                 ack_linux_live=True, authorize_plan_sha256=legacy.digest(self.plan))
        self.assertEqual("refused", result["status"])
        self.assertEqual([], self.writes)


class FilesystemCheckTests(unittest.TestCase):
    def test_only_read_only_flags_are_passed_to_fsck(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.img"; path.write_bytes(b"fixture")
            with (mock.patch.object(mod.shutil, "which", return_value="/usr/sbin/e2fsck"),
                  mock.patch.object(mod.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="clean")) as run):
                mod.check_staged_filesystem(path)
            self.assertEqual(["/usr/sbin/e2fsck", "-f", "-n", str(path.resolve())], run.call_args.args[0])
            self.assertEqual(b"fixture", path.read_bytes())

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("mke2fs") and shutil.which("e2fsck"), "real local e2fsprogs backend")
    def test_real_synthetic_ext4_passes_unchanged_and_corruption_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "local-ext4.img"
            with path.open("xb") as out: out.truncate(8 * 1024 * 1024)
            subprocess.run(["mke2fs", "-q", "-t", "ext4", "-F", str(path)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            before = legacy.digest(path)
            self.assertEqual(0, mod.check_staged_filesystem(path)["exit_code"])
            self.assertEqual(before, legacy.digest(path))
            with path.open("r+b") as out: out.seek(1024 + 56); out.write(b"XX")
            with self.assertRaises(ValueError): mod.check_staged_filesystem(path)


class LinuxEnvironmentTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "linux", "Linux ioctl/cache API")
    def test_cache_invalidation_follows_sync_and_queries_use_correct_abi(self):
        import fcntl
        disk = object.__new__(mod.LinuxDisk)
        disk.handle = mock.Mock(); disk.handle.fileno.return_value = 123
        order = []
        def ioctl(fd, request, buffer=None, mutate=False):
            self.assertEqual(123, fd)
            if request == 0x1261:
                order.append("invalidate")
                return 0
            expected = {0x80081272: ("Q", 31914983424), 0x1268: ("i", 512), 0x125E: ("i", 0)}
            fmt, value = expected[request]
            self.assertTrue(mutate)
            buffer[:] = mod.struct.pack(fmt, value)
            return 0
        with mock.patch.object(fcntl, "ioctl", side_effect=ioctl), mock.patch.object(mod.os, "fsync", side_effect=lambda fd: order.append("sync")):
            self.assertEqual(31914983424, disk.size())
            self.assertEqual(512, disk.sector_size())
            self.assertEqual(0, disk.ioctl_int(0x125E, "i"))
            disk.flush_and_invalidate()
        self.assertEqual(["sync", "invalidate"], order)

    def test_container_and_separate_mount_namespace_are_refused(self):
        with (mock.patch.object(mod.sys, "platform", "linux"),
              mock.patch.object(mod.platform, "release", return_value="6.6"),
              mock.patch.object(mod.platform, "machine", return_value="x86_64"),
              mock.patch.object(mod.os, "geteuid", return_value=0, create=True)):
            with mock.patch.object(Path, "exists", return_value=True):
                with self.assertRaisesRegex(ValueError, "container"):
                    mod.require_native_linux(True)
            with mock.patch.object(Path, "exists", return_value=False), mock.patch.object(mod.os, "readlink", side_effect=["mnt:[1]", "mnt:[2]"]):
                with self.assertRaisesRegex(ValueError, "namespace"):
                    mod.require_native_linux(True)

    @unittest.skipUnless(sys.platform == "linux", "Linux mount storage metadata")
    def test_ram_network_and_target_storage_are_refused(self):
        info = SimpleNamespace(st_dev=os.makedev(8, 1))
        identity = {"partition_devices": ["8:32", "8:33"]}
        for fs in ("tmpfs", "overlay", "nfs", "fuseblk"):
            with mock.patch.object(Path, "stat", return_value=info), mock.patch.object(Path, "read_text", return_value=f"1 0 8:1 / /mnt rw - {fs} /dev/sda1 rw\n"):
                with self.assertRaises(ValueError): mod.persistent_storage(Path("/mnt"), identity)
        with mock.patch.object(Path, "stat", return_value=info), mock.patch.object(Path, "read_text", return_value="1 0 8:1 / /mnt rw - ext4 /dev/sda1 rw\n"):
            mod.persistent_storage(Path("/mnt"), identity)
        with mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_dev=os.makedev(8, 33))):
            with self.assertRaisesRegex(ValueError, "outside"): mod.persistent_storage(Path("/mnt"), identity)

    def test_windows_wsl_unacknowledged_and_nonroot_are_refused(self):
        for system, release, root, ack in (("win32", "Windows", 0, True),
                ("linux", "6.6-microsoft-standard-WSL2", 0, True),
                ("linux", "6.6", 1000, True), ("linux", "6.6", 0, False)):
            with (mock.patch.object(mod.sys, "platform", system),
                  mock.patch.object(mod.platform, "release", return_value=release),
                  mock.patch.object(mod.platform, "machine", return_value="x86_64"),
                  mock.patch.object(mod.os, "geteuid", return_value=root, create=True)):
                with self.assertRaises(ValueError):
                    mod.require_native_linux(ack)

    @unittest.skipUnless(sys.platform == "linux", "Linux device metadata and flags")
    def test_exclusive_open_flags_and_descriptor_identity(self):
        identity = {"path": "/dev/sdz", "rdev": os.makedev(8, 32)}
        handle = mock.Mock()
        with (mock.patch.object(mod, "inspect_device", return_value=identity),
              mock.patch.object(mod.os, "open", return_value=123) as opened,
              mock.patch.object(mod.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=identity["rdev"])),
              mock.patch.object(mod.os, "fdopen", return_value=handle),
              mock.patch.object(mod.LinuxDisk, "sector_size", return_value=512),
              mock.patch.object(mod.LinuxDisk, "ioctl_int", return_value=0)):
            for writable in (False, True):
                disk = mod.LinuxDisk(Path("/dev/sdz"), writable)
                flags = opened.call_args.args[1]
                self.assertTrue(flags & os.O_EXCL)
                self.assertTrue(flags & os.O_NOFOLLOW)
                self.assertEqual(os.O_RDWR if writable else os.O_RDONLY, flags & os.O_ACCMODE)
                disk.close()

    @unittest.skipUnless(sys.platform == "linux", "Linux descriptor checks")
    def test_descriptor_substitution_wrong_sector_and_readonly_media_are_refused(self):
        identity = {"path": "/dev/sdz", "rdev": os.makedev(8, 32)}
        with (mock.patch.object(mod, "inspect_device", return_value=identity),
              mock.patch.object(mod.os, "open", return_value=123),
              mock.patch.object(mod.os, "close") as closed,
              mock.patch.object(mod.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(8, 33)))):
            with self.assertRaisesRegex(ValueError, "changed"):
                mod.LinuxDisk(Path("/dev/sdz"), True)
            closed.assert_called_once_with(123)
        for sector, readonly in ((4096, 0), (512, 1)):
            handle = mock.Mock()
            with (mock.patch.object(mod, "inspect_device", return_value=identity),
                  mock.patch.object(mod.os, "open", return_value=123),
                  mock.patch.object(mod.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=identity["rdev"])),
                  mock.patch.object(mod.os, "fdopen", return_value=handle),
                  mock.patch.object(mod.LinuxDisk, "sector_size", return_value=sector),
                  mock.patch.object(mod.LinuxDisk, "ioctl_int", return_value=readonly)):
                with self.assertRaises(ValueError): mod.LinuxDisk(Path("/dev/sdz"), True)
                handle.close.assert_called_once()


@unittest.skipUnless(sys.platform == "linux", "synthetic Linux sysfs/proc metadata")
class MetadataTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.sys = self.root / "sys"; self.proc = self.root / "proc"
        self.node = self.sys / "devices/usb1/1-1/block/sdz"
        self.node.mkdir(parents=True)
        (self.node / "dev").write_text("8:32\n"); (self.node / "removable").write_text("1\n")
        (self.node / "holders").mkdir()
        self.child = self.node / "sdz1"; self.child.mkdir()
        (self.child / "partition").write_text("1"); (self.child / "dev").write_text("8:33")
        (self.child / "holders").mkdir()
        usb = self.sys / "bus/usb"; usb.mkdir(parents=True)
        (self.node.parents[1] / "subsystem").symlink_to(usb, target_is_directory=True)
        (self.sys / "dev/block").mkdir(parents=True)
        (self.sys / "dev/block/8:32").symlink_to(self.node, target_is_directory=True)
        (self.proc / "self").mkdir(parents=True)
        self.mountinfo = self.proc / "self/mountinfo"; self.mountinfo.write_text("")
        self.swaps = self.proc / "swaps"; self.swaps.write_text("Filename Type Size Used Priority\n")
        self.real_stat = Path.stat; self.real_resolve = Path.resolve

    def inspect(self):
        def file_stat(path, *args, **kwargs):
            if str(path) in ("/dev/sdz", "/dev/sdz1"):
                return SimpleNamespace(st_mode=stat.S_IFBLK, st_rdev=os.makedev(8, 32 if path.name == "sdz" else 33))
            return self.real_stat(path, *args, **kwargs)
        def resolve(path, *args, **kwargs):
            return path if str(path) == "/dev/sdz" else self.real_resolve(path, *args, **kwargs)
        with mock.patch.object(Path, "stat", file_stat), mock.patch.object(Path, "resolve", resolve):
            return mod.inspect_device(Path("/dev/sdz"), self.sys, self.proc)

    def test_unused_usb_disk_allowed(self):
        self.assertEqual(["8:32", "8:33"], self.inspect()["partition_devices"])

    def test_mounted_partition_swap_and_holders_refused(self):
        self.mountinfo.write_text("1 0 8:33 / /media/kobo rw - vfat /dev/sdz1 rw\n")
        with self.assertRaisesRegex(ValueError, "mounted"):
            self.inspect()
        self.mountinfo.write_text("")
        self.swaps.write_text("Filename Type Size Used Priority\n/dev/sdz1 partition 1 0 -2\n")
        with self.assertRaisesRegex(ValueError, "swap"):
            self.inspect()
        self.swaps.write_text("Filename Type Size Used Priority\n")
        (self.child / "holders/dm-0").mkdir()
        with self.assertRaisesRegex(ValueError, "holders"):
            self.inspect()

    def test_internal_disk_partition_nonusb_and_missing_metadata_refused(self):
        (self.node / "removable").write_text("0")
        with self.assertRaises(ValueError): self.inspect()
        (self.node / "removable").write_text("1")
        (self.node / "partition").write_text("1")
        with self.assertRaises(ValueError): self.inspect()
        (self.node / "partition").unlink()
        (self.node.parents[1] / "subsystem").unlink()
        with self.assertRaises(ValueError): self.inspect()
