import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import test_rebuild_rootfs as rebuild_tests

from test_import_legacy_backup import load, legacy, make_pre, imported_manifest

mod = load("restore", "restore-rootfs.py")


class RestoreSimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pre = self.root / "pré P1.bin"
        self.p2 = self.root / "recovery.img"
        self.manifest = self.root / "legacy.json"
        self.report = self.root / "rebuild.json"
        self.rootfs = self.root / "P1 rebuilt.img"
        self.target = self.root / "disque source.img"
        self.output = self.root / "new disk.img"
        make_pre(self.pre, 4096, 4096, 4096)
        data = bytearray(4096)
        for offset, size, value in ((1028, 4, 3), (1080, 2, 0xEF53),
                                    (1100, 4, 1), (1112, 2, 128), (1120, 4, 0x40)):
            data[offset:offset + size] = value.to_bytes(size, "little")
        self.p2.write_bytes(data)
        imported_manifest(self.pre, self.p2, self.manifest)
        self.rootfs.write_bytes(b"new P1" + bytes(4090))
        # Unit fixture has synthetic report claims, not a filesystem. A separate
        # Linux integration test uses an actual e2fsprogs-built image and report.
        self.report.write_text(json.dumps({
            "schema_version": 1, "tool": "rebuild-rootfs", "status": "ok", "complete": True,
            "device": "E606C0", "errors": [], "physical_restore_eligible": False,
            "input_provenance": legacy.PROVENANCE, "target_fingerprint": None,
            "backup_manifest_sha256": legacy.digest(self.manifest),
            "recovery_sha256": legacy.digest(self.p2), "rootfs_sha256": legacy.digest(self.rootfs),
            "rootfs_size": 4096, "checks": {"size": True, "ext4_parameters": True, "e2fsck": "clean",
                "metadata": {"entries": 1, "verified": 1}, "content": {"files": 1, "verified": 1},
                "fs_md5sum": {"present": False}},
        }), encoding="utf-8")
        self.target.write_bytes(self.pre.read_bytes() + b"old!" * 1024 + self.p2.read_bytes() + b"P3!!" * 1024 + b"trailing bytes")
        self.paths = (self.manifest, self.report, self.rootfs, self.target, self.output)

    def preflight(self):
        return mod.preflight(*self.paths, accept_legacy_import=True)

    def simulate(self):
        return mod.simulate(*self.paths, accept_legacy_import=True)

    def test_default_plan_only_reads_all_inputs_and_creates_nothing(self):
        before = {p: legacy.digest(p) for p in self.paths[:-1]}
        real_open = Path.open
        def guarded(path, mode="r", *args, **kwargs):
            self.assertFalse(any(f in mode for f in "wax+"))
            return real_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, "open", guarded), mock.patch.object(subprocess, "run", side_effect=AssertionError("external command")):
            result = self.preflight()
        self.assertEqual("ready", result["status"], result)
        self.assertFalse(result["complete"])
        self.assertFalse(self.output.exists())
        self.assertFalse(Path(str(self.output) + ".part").exists())
        self.assertEqual(before, {p: legacy.digest(p) for p in before})

    def test_simulation_only_replaces_p1_in_a_new_copy(self):
        before = self.target.read_bytes()
        inputs = {p.resolve() for p in (*self.paths[:-1], self.pre, self.p2)}
        real_open = Path.open
        def guarded(path, mode="r", *args, **kwargs):
            if Path(path).resolve() in inputs and any(f in mode for f in "wax+"):
                raise AssertionError("input opened for writing")
            return real_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, "open", guarded), mock.patch.object(subprocess, "run", side_effect=AssertionError("external command")):
            result = self.simulate()
        self.assertEqual("ok", result["status"], result)
        offset = result["p1_offset"]; end = offset + result["p1_size"]
        after = self.output.read_bytes()
        self.assertEqual(before[:offset], after[:offset])
        self.assertEqual(before[end:], after[end:])
        self.assertEqual(self.rootfs.read_bytes(), after[offset:end])
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(result["preserved_before"], result["preserved_after"])
        self.assertFalse(result["physical_restore_eligible"])
        self.assertEqual(legacy.PROVENANCE, result["input_provenance"])
        self.assertFalse(Path(str(self.output) + ".part").exists())
        saved = json.loads(Path(str(self.output) + ".simulation.json").read_text())
        self.assertEqual(result, saved)

    def test_legacy_opt_in_is_required(self):
        result = mod.simulate(*self.paths)
        self.assertEqual("refused", result["status"])
        self.assertFalse(self.output.exists())

    def test_devices_are_refused_before_open(self):
        for device in ("/dev/sdb", r"\\.\PhysicalDrive2", r"\\?\GLOBALROOT\Device\Harddisk0"):
            for index in range(5):
                paths = list(self.paths); paths[index] = Path(device)
                with self.subTest(device=device, index=index), mock.patch.object(Path, "open", side_effect=AssertionError("opened")):
                    result = mod.preflight(*paths, accept_legacy_import=True)
                self.assertEqual("refused", result["status"], result)

    @unittest.skipUnless(sys.platform == "linux", "Linux special-file checks")
    def test_device_alias_and_fifo_are_refused_before_open(self):
        alias = self.root / "alias"; alias.symlink_to("/dev/zero")
        fifo = self.root / "fifo"; os.mkfifo(fifo)
        for path in (alias, fifo):
            with mock.patch.object(Path, "open", side_effect=AssertionError("opened")):
                result = mod.preflight(self.manifest, self.report, self.rootfs, path, self.output, accept_legacy_import=True)
            self.assertEqual("refused", result["status"], result)

    def test_output_collisions_and_aliases_never_overwrite(self):
        for path in (self.output, Path(str(self.output) + ".part"), Path(str(self.output) + ".simulation.json")):
            path.write_bytes(b"keep")
            self.assertEqual("refused", self.preflight()["status"])
            self.assertEqual(b"keep", path.read_bytes()); path.unlink()
        paths = (*self.paths[:-1], self.target)
        before = legacy.digest(self.target)
        self.assertEqual("refused", mod.simulate(*paths, accept_legacy_import=True)["status"])
        self.assertEqual(before, legacy.digest(self.target))

    def test_bad_geometry_bounds_prefix_and_p2_are_refused(self):
        before = self.target.read_bytes()
        for offset in (510, 446 + 8, 0x80010, 9961472 + 4096 + 20):
            changed = bytearray(before); changed[offset] ^= 1; self.target.write_bytes(changed)
            self.assertEqual("refused", self.preflight()["status"])
            self.target.write_bytes(before)
        self.target.write_bytes(before[:-4096])
        self.assertEqual("refused", self.preflight()["status"])

    def test_wrong_rootfs_hash_size_and_unqualified_evidence_are_refused(self):
        before = self.rootfs.read_bytes()
        self.rootfs.write_bytes(b"x" + before[1:])
        self.assertEqual("refused", self.preflight()["status"])
        self.rootfs.write_bytes(before + b"x")
        self.assertEqual("refused", self.preflight()["status"])
        self.rootfs.write_bytes(before)
        self.pre.write_bytes(b"tampered")
        self.assertEqual("refused", self.preflight()["status"])

    def make_koreader_report(self):
        ext4 = {"label": "rootfs", "block_size": 1024, "inode_size": 128,
                "blocks": 4, "unused_tail_bytes": 0, "features": ["extent"]}
        report = {
            "schema_version": 1, "tool": "build-koreader-rootfs", "status": "experimental",
            "complete": True, "errors": [], "physical_restore_eligible": False,
            "hardware_qualified": False, "device": "E606C0",
            "rootfs_size": self.rootfs.stat().st_size,
            "rootfs_sha256": legacy.digest(self.rootfs), "ext4": ext4,
        }
        self.report.write_text(json.dumps(report))
        # This unit fixture has no filesystem. Real filesystem coverage is below.
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(mod, "read_candidate_ext4", return_value=dict(ext4)).start()
        mock.patch.object(mod.rebuild, "read_ext_parameters", return_value=dict(ext4)).start()
        mock.patch.object(mod.shutil, "which", return_value="/usr/sbin/e2fsck").start()
        return report

    def test_build_koreader_report_is_typed_and_ext4_is_rechecked_read_only(self):
        report_data = self.make_koreader_report()
        with mock.patch.object(mod.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="clean")) as run:
            result = self.preflight()
        self.assertEqual("ready", result["status"], result)
        self.assertEqual("build-koreader-rootfs", result["rootfs_report_tool"])
        self.assertFalse(result["write_authorized"])
        self.assertEqual("revalidated_locally_read_only_e2fsck", result["checks"]["filesystem_checks"])
        self.assertEqual(["/usr/sbin/e2fsck", "-f", "-n", str(self.rootfs.resolve())], run.call_args.args[0])
        self.assertEqual("clean", result["filesystem_validation"]["e2fsck"])
        for key, value in (("tool", "forged-tool"), ("device", "N905"),
                           ("rootfs_sha256", "0" * 64), ("rootfs_size", 1),
                           ("complete", False), ("errors", ["failure"]),
                           ("physical_restore_eligible", True), ("hardware_qualified", True),
                           ("status", "ok")):
            bad = dict(report_data); bad[key] = value
            self.report.write_text(json.dumps(bad))
            with self.subTest(key=key):
                self.assertEqual("refused", self.preflight()["status"])
        self.report.write_text(json.dumps(report_data))
        self.rootfs.write_bytes(b"different image" + bytes(4096 - len(b"different image")))
        self.assertEqual("refused", self.preflight()["status"])

    def test_koreader_ext4_report_and_recovery_must_match_actual_image(self):
        report = self.make_koreader_report()
        for key, value in (("label", "recoveryfs"), ("block_size", 4096),
                           ("inode_size", 256), ("blocks", 5),
                           ("unused_tail_bytes", 512), ("features", ["extent", "64bit"])):
            bad = copy.deepcopy(report); bad["ext4"][key] = value
            self.report.write_text(json.dumps(bad))
            with self.subTest(key=key):
                self.assertEqual("refused", self.preflight()["status"])
        self.report.write_text(json.dumps(report))
        for key, value in (("block_size", 4096), ("inode_size", 256), ("features", [])):
            reference = dict(report["ext4"]); reference[key] = value
            with mock.patch.object(mod.rebuild, "read_ext_parameters", return_value=reference):
                self.assertEqual("refused", self.preflight()["status"])

    def test_build_koreader_report_refuses_failed_or_unavailable_read_only_e2fsck(self):
        self.make_koreader_report()
        for code in (1, 4, 8):
            with mock.patch.object(mod.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout="bad fs")):
                self.assertEqual("refused", self.preflight()["status"])
        with mock.patch.object(mod.shutil, "which", return_value=None):
            self.assertEqual("refused", self.preflight()["status"])
        with mock.patch.object(mod.rebuild, "read_ext_parameters", side_effect=subprocess.CalledProcessError(1, "dumpe2fs")):
            self.assertEqual("refused", self.preflight()["status"])

    def test_inconsistent_unsigned_reports_are_refused(self):
        original = json.loads(self.report.read_text())
        for mutate in (lambda d: d.update(complete=False), lambda d: d.update(physical_restore_eligible=True),
                       lambda d: d.update(backup_manifest_sha256="0" * 64),
                       lambda d: d["checks"].update(e2fsck="unclean"),
                       lambda d: d["checks"]["metadata"].update(verified=0),
                       lambda d: d["checks"]["metadata"].update(verified=True),
                       lambda d: d["checks"].update(fs_md5sum={"present": True, "entries": 1, "matched": 0}),
                       lambda d: d.update(input_provenance={"kind": "native"})):
            data = copy.deepcopy(original); mutate(data)
            self.report.write_text(json.dumps(data))
            self.assertEqual("refused", self.preflight()["status"])

    def test_insufficient_space_refuses_before_creation(self):
        with mock.patch.object(mod.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(100, 100, 0)):
            self.assertEqual("refused", self.simulate()["status"])
        self.assertFalse(self.output.exists())

    def test_copy_corruption_keeps_part_and_never_publishes(self):
        real_hash_region = mod.hash_region
        def corrupt(handle, offset, size):
            value = real_hash_region(handle, offset, size)
            return "0" * 64 if Path(handle.name) == Path(str(self.output) + ".part") and offset == 0 else value
        with mock.patch.object(mod, "hash_region", side_effect=corrupt):
            result = self.simulate()
        self.assertEqual("failed", result["status"], result)
        self.assertFalse(self.output.exists())
        self.assertTrue(Path(str(self.output) + ".part").exists())

    def test_source_change_is_detected_after_copy(self):
        real_preflight = mod.preflight
        def mutate(*args, **kwargs):
            result = real_preflight(*args, **kwargs)
            with self.target.open("r+b") as handle:
                handle.seek(9961472); handle.write(b"changed")
            return result
        with mock.patch.object(mod, "preflight", side_effect=mutate):
            result = self.simulate()
        self.assertEqual("failed", result["status"], result)
        self.assertFalse(self.output.exists())

    def test_cli_plan_defaults_to_no_creation(self):
        with mock.patch.object(sys, "argv", ["restore", *(str(p) for p in self.paths), "--accept-legacy-import"]), mock.patch("builtins.print"):
            self.assertEqual(0, mod.main())
        self.assertFalse(self.output.exists())

    def test_io_failure_and_interruption_never_publish(self):
        before = legacy.digest(self.target)
        for exception, status in ((OSError("disk I/O failure"), "failed"), (KeyboardInterrupt(), "interrupted")):
            with mock.patch.object(mod.os, "fsync", side_effect=exception):
                result = self.simulate()
            self.assertEqual(status, result["status"], result)
            self.assertFalse(result["complete"])
            self.assertFalse(self.output.exists())
            self.assertEqual(before, legacy.digest(self.target))
            part = Path(str(self.output) + ".part")
            self.assertTrue(part.exists()); part.unlink()

    def test_concurrent_publication_collision_does_not_overwrite(self):
        real_link = os.link
        def publish(source, destination):
            Path(destination).write_bytes(b"created concurrently")
            return real_link(source, destination)
        with mock.patch.object(mod.os, "link", side_effect=publish):
            result = self.simulate()
        self.assertEqual("failed", result["status"], result)
        self.assertEqual(b"created concurrently", self.output.read_bytes())
        self.assertTrue(Path(str(self.output) + ".part").exists())


@unittest.skipUnless(sys.platform == "linux" and all(shutil.which(t) for t in rebuild_tests.mod.REQUIRED_TOOLS),
                     "Linux e2fsprogs/fakeroot backend not available")
class RestoreSimulationIntegrationTests(unittest.TestCase):
    def test_real_synthetic_import_rebuild_and_disk_image_simulation(self):
        fixture = rebuild_tests.RebuildRootfsLinuxBuildTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        manifest, recovery, recovery_sha = fixture.make_inputs(historical_root=True)
        pre = fixture.root / "pre.bin"
        make_pre(pre, rebuild_tests.P1_SIZE, recovery.stat().st_size, 8192)
        imported_manifest(pre, recovery, manifest)
        rootfs = fixture.root / "rootfs.img"
        report = rebuild_tests.mod.build_rootfs(manifest, recovery, rootfs, accept_legacy_import=True)
        self.assertEqual("ok", report["status"], report)
        target = fixture.root / "synthetic disk.img"
        target.write_bytes(pre.read_bytes() + bytes(rebuild_tests.P1_SIZE) + recovery.read_bytes() + b"P3!!" * 2048 + b"tail")
        before = target.read_bytes()
        output = fixture.root / "simulated disk.img"
        result = mod.simulate(manifest, Path(str(rootfs) + ".rebuild.json"), rootfs, target, output, accept_legacy_import=True)
        self.assertEqual("ok", result["status"], result)
        offset = result["p1_offset"]; end = offset + result["p1_size"]
        after = output.read_bytes()
        self.assertEqual(before[:offset] + rootfs.read_bytes() + before[end:], after)
        self.assertEqual(before, target.read_bytes())
        self.assertEqual(recovery_sha, legacy.digest(recovery))
        self.assertFalse(result["physical_restore_eligible"])


if __name__ == "__main__":
    unittest.main()
