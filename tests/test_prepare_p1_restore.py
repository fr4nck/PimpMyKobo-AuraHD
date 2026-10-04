import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from test_import_legacy_backup import load, legacy
import test_restore_rootfs as fixtures

simulation = fixtures.mod

prepare = load("prepare", "prepare-p1-restore.py")


class PrepareP1Tests(unittest.TestCase):
    setUp = fixtures.RestoreSimulationTests.setUp

    def setup_plan(self):
        result = simulation.simulate(*self.paths, accept_legacy_import=True)
        self.assertEqual("ok", result["status"], result)
        self.acquisition = self.root / "acquisition.json"
        sha = legacy.digest(self.target)
        self.acquisition.write_text(json.dumps({
            "schema_version": 1, "tool": "read-only-full-card-acquisition", "status": "ok",
            "complete": True, "errors": [], "source_open_mode": "rb",
            "image_size": self.target.stat().st_size, "image_sha256": sha,
            "source_stream_sha256": sha, "source_reread_sha256": sha,
            "checks": {key: True for key in ("mbr_hwconfig", "historical_prefix_p2",
                "exact_physical_length", "destination_readback", "whole_source_reread")}}))
        self.plan = self.root / "plan.json"
        self.args = (self.manifest, self.report, self.rootfs, self.target, self.acquisition,
                     self.output, Path(str(self.output) + ".simulation.json"), self.plan)

    def test_plan_preserves_all_inputs_and_never_authorizes_write(self):
        self.setup_plan()
        before = {p: legacy.digest(p) for p in self.args[:-1]}
        real_open = Path.open
        def guarded(path, mode="r", *args, **kwargs):
            if path != self.plan:
                self.assertFalse(any(flag in mode for flag in "wax+"))
            return real_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, "open", guarded):
            result = prepare.prepare(*self.args)
        self.assertEqual("prepared", result["status"], result)
        self.assertFalse(result["write_authorized"])
        self.assertFalse(result["physical_restore_eligible"])
        self.assertEqual(legacy.PROVENANCE, result["input_provenance"])
        self.assertEqual("rebuild-rootfs", result["candidate_source"]["tool"])
        self.assertEqual(result["candidate_source"]["report_sha256"],
                         result["evidence_sha256"]["rootfs_report"])
        self.assertEqual(legacy.digest(self.output), result["simulation_sha256"])
        self.assertEqual(before, {p: legacy.digest(p) for p in before})

    def test_acquisition_incomplete_or_different_is_refused(self):
        self.setup_plan()
        original = self.acquisition.read_text()
        for key, value in (("complete", False), ("source_reread_sha256", "0" * 64),
                           ("source_open_mode", "r+b"), ("image_size", 1), ("checks", None)):
            data = json.loads(original); data[key] = value
            self.acquisition.write_text(json.dumps(data))
            self.assertEqual("refused", prepare.prepare(*self.args)["status"])
            self.assertFalse(self.plan.exists())

    def test_simulated_image_changed_is_refused(self):
        self.setup_plan()
        with self.output.open("r+b") as handle:
            handle.seek(100); handle.write(b"changed")
        self.assertEqual("refused", prepare.prepare(*self.args)["status"])
        self.assertFalse(self.plan.exists())

    def test_forged_simulation_hash_cannot_hide_outside_p1_changes(self):
        self.setup_plan()
        with self.output.open("r+b") as handle:
            handle.seek(100); handle.write(b"changed")
        report = json.loads(self.args[6].read_text())
        report["output_sha256"] = legacy.digest(self.output)
        self.args[6].write_text(json.dumps(report))
        self.assertEqual("refused", prepare.prepare(*self.args)["status"])

    def test_simulation_producer_contract_cannot_be_changed(self):
        self.setup_plan()
        original = json.loads(self.args[6].read_text())
        for key, value in (("rootfs_report_tool", "build-koreader-rootfs"),
                           ("rootfs_report_sha256", "0" * 64),
                           ("write_authorized", True), ("physical_restore_eligible", True)):
            changed = dict(original); changed[key] = value
            self.args[6].write_text(json.dumps(changed))
            with self.subTest(key=key):
                self.assertEqual("refused", prepare.prepare(*self.args)["status"])
                self.assertFalse(self.plan.exists())

    def test_existing_plan_is_not_overwritten(self):
        self.setup_plan(); self.plan.write_text("keep")
        self.assertEqual("refused", prepare.prepare(*self.args)["status"])
        self.assertEqual("keep", self.plan.read_text())

    def test_raw_devices_refused_without_open(self):
        self.setup_plan()
        for index in range(len(self.args)):
            args = list(self.args); args[index] = Path("/dev/sdb")
            with mock.patch.object(Path, "open", side_effect=AssertionError("opened")):
                # All arguments must be screened before any evidence read.
                result = prepare.prepare(*args)
            self.assertEqual("refused", result["status"])


@unittest.skipUnless(sys.platform == "linux" and all(shutil.which(t) for t in
                    ("mke2fs", "debugfs", "dumpe2fs", "e2fsck", "fakeroot")),
                    "Linux e2fsprogs/fakeroot backend not available")
class KoreaderPlanIntegrationTests(unittest.TestCase):
    def test_real_koreader_build_simulation_prepare_and_seal(self):
        import test_build_koreader_rootfs as builder
        from test_import_legacy_backup import make_pre, imported_manifest
        live = load("live_plan_contract", "restore-p1-linux.py")
        fixture = builder.BuildRootfsLinuxBuildTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.root
        recovery = fixture.make_reference_recovery()
        candidate = root / "candidate.img"
        size = recovery.stat().st_size + 512
        built = builder.mod.build_rootfs(builder.make_koreader_dir(root),
                                        builder.make_runtime_dir(root), recovery, candidate, size)
        self.assertEqual("experimental", built["status"], built)
        pre = root / "pre.bin"
        make_pre(pre, size, recovery.stat().st_size, 8192)
        manifest = root / "legacy.json"
        imported_manifest(pre, recovery, manifest)
        target = root / "full.img"
        target.write_bytes(pre.read_bytes() + bytes(size) + recovery.read_bytes() + b"P3!!" * 2048 + b"tail")
        original_sha = legacy.digest(target)
        report = Path(str(candidate) + ".koreader-build.json")
        output = root / "simulated.img"
        simulated = simulation.simulate(manifest, report, candidate, target, output, accept_legacy_import=True)
        self.assertEqual("ok", simulated["status"], simulated)
        self.assertEqual("build-koreader-rootfs", simulated["rootfs_report_tool"])
        self.assertEqual("clean", simulated["filesystem_validation"]["e2fsck"])
        acquisition = root / "acquisition.json"
        acquisition.write_text(json.dumps({
            "schema_version": 1, "tool": "read-only-full-card-acquisition", "status": "ok",
            "complete": True, "errors": [], "source_open_mode": "rb",
            "image_size": target.stat().st_size, "image_sha256": original_sha,
            "source_stream_sha256": original_sha, "source_reread_sha256": original_sha,
            "checks": {key: True for key in ("mbr_hwconfig", "historical_prefix_p2",
                "exact_physical_length", "destination_readback", "whole_source_reread")}}))
        plan = root / "plan.json"
        args = (manifest, report, candidate, target, acquisition, output,
                Path(str(output) + ".simulation.json"), plan)
        result = prepare.prepare(*args)
        self.assertEqual("prepared", result["status"], result)
        self.assertEqual("build-koreader-rootfs", result["candidate_source"]["tool"])
        self.assertEqual(built["rootfs_sha256"], result["replacement_sha256"])
        self.assertEqual(legacy.digest(output), result["simulation_sha256"])
        self.assertEqual(original_sha, legacy.digest(target))
        loaded, sealed_sha = live.validate_sealed_plan(plan, candidate, legacy.digest(plan))
        self.assertEqual(result, loaded)
        self.assertEqual(legacy.digest(plan), sealed_sha)
        self.assertFalse(loaded["write_authorized"])
        self.assertFalse(loaded["physical_restore_eligible"])
        with self.assertRaises(ValueError):
            live.validate_sealed_plan(plan, candidate, "0" * 64)
        # A renamed producer cannot inherit the legacy rebuild contract.
        data = json.loads(report.read_text()); data["tool"] = "rebuild-rootfs"
        report.write_text(json.dumps(data))
        refused = prepare.prepare(*args[:-1], root / "forged-plan.json")
        self.assertEqual("refused", refused["status"])
        self.assertFalse((root / "forged-plan.json").exists())
