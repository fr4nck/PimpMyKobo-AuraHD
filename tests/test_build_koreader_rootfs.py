import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_koreader_rootfs", ROOT / "tools" / "build-koreader-rootfs.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

from test_rebuild_rootfs import KOBO_LIKE_FEATURES  # noqa: E402  (shared ext4 fixture constants)


def make_koreader_dir(root: Path, *, with_reader: bool = True, with_luajit: bool = True) -> Path:
    d = root / "koreader-release"
    d.mkdir()
    if with_reader:
        (d / "reader.lua").write_text("-- stand-in reader.lua, not real KOReader\n", encoding="utf-8")
    if with_luajit:
        luajit = d / "luajit"
        luajit.write_bytes(b"\x7fELF-stand-in-arm-luajit")
        os.chmod(luajit, 0o755)
    libs = d / "libs"
    libs.mkdir()
    (libs / "libfoo.so").write_bytes(b"stand-in-lib-bytes")
    return d


def make_runtime_dir(root: Path, *, name: str = "runtime") -> Path:
    d = root / name
    (d / "bin").mkdir(parents=True)
    busybox = d / "bin" / "busybox"
    busybox.write_bytes(b"\x7fELF-stand-in-arm-busybox")
    os.chmod(busybox, 0o755)
    return d


class PlanRootfsTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def test_rejects_linux_device_paths(self):
        report, manifest = mod.plan_rootfs(Path("/dev/sdb"), make_runtime_dir(self.root))
        self.assertEqual("failed", report["status"])
        self.assertIn("koreader path is a physical/block device and is forbidden", report["errors"])
        self.assertEqual({}, manifest)

    def test_rejects_windows_physical_drive(self):
        report, _ = mod.plan_rootfs(make_koreader_dir(self.root), Path(r"\\.\PhysicalDrive3"))
        self.assertEqual("failed", report["status"])
        self.assertIn("runtime path is a physical/block device and is forbidden", report["errors"])

    def test_requires_existing_directories(self):
        report, _ = mod.plan_rootfs(self.root / "missing-koreader", self.root / "missing-runtime")
        self.assertEqual("failed", report["status"])
        self.assertIn("koreader input is not a directory", report["errors"])
        self.assertIn("runtime input is not a directory", report["errors"])

    def test_successful_plan_merges_overlay_koreader_and_runtime(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("assembled", report["status"], report)
        self.assertEqual([], report["errors"])
        for expected in ("etc/init.d/rcS", "etc/inittab", "usr/bin/pmkb-check-offline",
                         "usr/bin/pmkb-check-onboard", "usr/bin/pmkb-reader", "bin/kobo_config.sh",
                         "opt/koreader/reader.lua", "opt/koreader/luajit",
                         "opt/koreader/libs/libfoo.so", "bin/busybox",
                         "opt/koreader/defaults.custom.lua"):
            self.assertIn(expected, manifest, expected)
        self.assertEqual("file", manifest["opt/koreader/luajit"]["kind"])
        if os.name == "posix":
            # Windows chmod does not expose real POSIX exec bits; mode fidelity
            # for externally-sourced files is only meaningful on a POSIX host.
            self.assertEqual(0o755, manifest["bin/busybox"]["mode"])
        self.assertGreater(report["apparent_size"], 0)
        self.assertEqual(len(manifest), report["entries"])

    def test_overlay_scripts_are_forced_executable_regardless_of_source_mode(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        _report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual(0o755, manifest["etc/init.d/rcS"]["mode"])
        self.assertEqual(0o755, manifest["usr/bin/pmkb-reader"]["mode"])

    def test_missing_reader_lua_is_reported(self):
        koreader = make_koreader_dir(self.root, with_reader=False)
        runtime = make_runtime_dir(self.root)
        report, _ = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertIn("required entry point missing after assembly: /opt/koreader/reader.lua", report["errors"])

    def test_missing_luajit_is_reported(self):
        koreader = make_koreader_dir(self.root, with_luajit=False)
        runtime = make_runtime_dir(self.root)
        report, _ = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertIn("required entry point missing after assembly: /opt/koreader/luajit", report["errors"])

    def test_file_collision_between_runtime_and_overlay_is_refused(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        (runtime / "bin" / "kobo_config.sh").write_text("#!/bin/sh\necho clash\n", encoding="utf-8")
        report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("path collision" in e and "bin/kobo_config.sh" in e for e in report["errors"]), report["errors"])
        self.assertEqual({}, manifest)

    def test_directories_merge_across_sources_without_collision(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        # "etc" already exists (from the overlay's etc/init.d, etc/inittab); runtime
        # adding a new file under the same directory must not be treated as a clash.
        (runtime / "etc").mkdir()
        (runtime / "etc" / "runtime.conf").write_text("ok\n", encoding="utf-8")
        report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("assembled", report["status"], report)
        self.assertEqual("dir", manifest["etc"]["kind"])
        self.assertEqual("file", manifest["etc/runtime.conf"]["kind"])

    def test_content_referencing_nickel_is_flagged(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        (runtime / "bin" / "legacy-helper").write_text("#!/bin/sh\n# calls Nickel helpers\n", encoding="utf-8")
        report, _ = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("Nickel" in hit for hit in report["nickel_scan"]), report["nickel_scan"])
        self.assertTrue(any("unexpected Nickel" in e for e in report["errors"]), report["errors"])

    def test_path_named_like_nickel_is_flagged(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        (runtime / "etc").mkdir()
        (runtime / "etc" / "nickel_conf.lua").write_text("return {}\n", encoding="utf-8")
        report, _ = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("nickel_conf.lua" in hit for hit in report["nickel_scan"]), report["nickel_scan"])

    def test_json_output_is_stable_and_serializable(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        report, _ = mod.plan_rootfs(koreader, runtime)
        json.dumps(report)  # must not raise
        self.assertFalse(report["physical_restore_eligible"])
        self.assertFalse(report["hardware_qualified"])


class ReaderProfileTests(unittest.TestCase):
    """Covers the demonstrated-necessary KOReader defaults profile integration."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def test_profile_is_required_and_has_the_demonstrated_necessary_settings(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("assembled", report["status"], report)
        self.assertIn(mod.READER_PROFILE_REL, manifest)
        content = mod.READER_PROFILE_FILE.read_text(encoding="utf-8")
        self.assertIn("KOBO_LIGHT_ON_START = -1", content)
        self.assertIn("KOBO_SYNC_BRIGHTNESS_WITH_NICKEL = false", content)

    def test_profile_is_excluded_from_nickel_content_scan_despite_its_name(self):
        # KOBO_SYNC_BRIGHTNESS_WITH_NICKEL legitimately contains "NICKEL";
        # this file is first-party/reviewed like the overlay, not external
        # content, so it must not itself trigger a scan hit.
        content = mod.READER_PROFILE_FILE.read_text(encoding="utf-8")
        self.assertIn("NICKEL", content)
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        report, _manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("assembled", report["status"], report)
        self.assertEqual([], report["nickel_scan"])
        dest = self.root / "assembled"
        dest.mkdir()
        build_manifest: dict = {}
        mod._copy_tree(mod.OVERLAY_ROOT, dest, build_manifest, {}, write=True, force_mode=0o755)
        mod._add_skeleton_dirs(build_manifest, dest, write=True)
        mod._place_reader_profile(dest, build_manifest, write=True)
        mod._copy_tree(koreader, dest, build_manifest, {}, base="opt/koreader", write=True)
        mod._copy_tree(runtime, dest, build_manifest, {}, write=True)
        self.assertEqual([], mod.scan_tree_for_nickel(dest))

    def test_koreader_provided_profile_collides_instead_of_silently_overriding(self):
        koreader = make_koreader_dir(self.root)
        (koreader / "defaults.custom.lua").write_text(
            "return { KOBO_SYNC_BRIGHTNESS_WITH_NICKEL = true }\n", encoding="utf-8")
        report, manifest = mod.plan_rootfs(koreader, make_runtime_dir(self.root))
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("defaults.custom.lua" in e for e in report["errors"]), report["errors"])
        self.assertEqual({}, manifest)

    def test_missing_profile_file_fails_closed(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        with mock.patch.object(mod, "READER_PROFILE_FILE", self.root / "absent.lua"):
            report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("defaults.custom.lua is missing" in e for e in report["errors"]), report["errors"])
        self.assertEqual({}, manifest)


class ScanTreeForNickelTests(unittest.TestCase):
    """Covers the integration entry point other local tools call post-merge."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def materialize(self) -> Path:
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        dest = self.root / "assembled"
        dest.mkdir()
        manifest: dict = {}
        mod._copy_tree(mod.OVERLAY_ROOT, dest, manifest, {}, write=True, force_mode=0o755)
        mod._add_skeleton_dirs(manifest, dest, write=True)
        mod._copy_tree(koreader, dest, manifest, {}, base="opt/koreader", write=True)
        mod._copy_tree(runtime, dest, manifest, {}, write=True)
        return dest

    def test_overlays_own_nickel_comment_is_not_a_false_positive_once_merged(self):
        # usr/bin/pmkb-reader legitimately documents bypassing Nickel paths; a
        # naive re-scan of the merged tree would otherwise always flag it.
        tree = self.materialize()
        self.assertIn("Nickel", (tree / "usr/bin/pmkb-reader").read_text(encoding="utf-8"))
        hits = mod.scan_tree_for_nickel(tree)
        self.assertEqual([], hits)

    def test_external_nickel_reference_in_merged_tree_is_still_flagged(self):
        tree = self.materialize()
        (tree / "opt/koreader/nickel_conf.lua").write_text("return {}\n", encoding="utf-8")
        hits = mod.scan_tree_for_nickel(tree)
        self.assertTrue(any("nickel_conf.lua" in hit for hit in hits), hits)

    def test_external_content_reference_in_merged_tree_is_still_flagged(self):
        tree = self.materialize()
        (tree / "opt" / "koreader" / "legacy-helper").write_text(
            "#!/bin/sh\n# calls Nickel helpers\n", encoding="utf-8")
        hits = mod.scan_tree_for_nickel(tree)
        self.assertTrue(any("legacy-helper" in hit and "Nickel" in hit for hit in hits), hits)


@unittest.skipUnless(os.name == "posix", "symlink creation semantics are POSIX-specific")
class PlanRootfsSymlinkTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def test_symlinks_are_recorded_without_being_followed(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        (runtime / "bin" / "sh").symlink_to("busybox")
        report, manifest = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("assembled", report["status"], report)
        self.assertEqual({"kind": "symlink", "target": "busybox"}, manifest["bin/sh"])

    def test_symlink_colliding_with_overlay_file_is_refused(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        (runtime / "bin" / "kobo_config.sh").symlink_to("busybox")
        report, _ = mod.plan_rootfs(koreader, runtime)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("kobo_config.sh" in e for e in report["errors"]), report["errors"])


class BuildRootfsPreflightTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def test_non_linux_backend_returns_without_tool_lookup(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        recovery = self.root / "recovery.img"
        recovery.write_bytes(b"not-a-real-image")
        with mock.patch.object(mod.sys, "platform", "win32"), mock.patch.object(
            mod.shutil, "which", side_effect=AssertionError("unexpected tool lookup")
        ):
            report = mod.build_rootfs(koreader, runtime, recovery, self.root / "out.img", 4096)
        self.assertEqual("failed", report["status"])
        self.assertIn("rootfs construction requires Linux (native, WSL2, VM, or live USB)", report["errors"])

    def test_build_rejects_device_output_path(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        recovery = self.root / "recovery.img"
        recovery.write_bytes(b"x")
        report = mod.build_rootfs(koreader, runtime, recovery, Path(r"\\.\PhysicalDrive1"), 4096)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("physical/block device" in e for e in report["errors"]), report["errors"])

    def test_build_propagates_assembly_failure(self):
        koreader = make_koreader_dir(self.root, with_reader=False)
        runtime = make_runtime_dir(self.root)
        recovery = self.root / "recovery.img"
        recovery.write_bytes(b"x")
        report = mod.build_rootfs(koreader, runtime, recovery, self.root / "out.img", 4096)
        self.assertEqual("failed", report["status"])
        self.assertIn("required entry point missing after assembly: /opt/koreader/reader.lua", report["errors"])

    def test_build_refuses_existing_output(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        recovery = self.root / "recovery.img"
        recovery.write_bytes(b"x")
        output = self.root / "out.img"
        output.write_bytes(b"already-there")
        report = mod.build_rootfs(koreader, runtime, recovery, output, 4096)
        self.assertEqual("failed", report["status"])
        self.assertIn("output already exists; implicit overwrite is forbidden", report["errors"])


@unittest.skipUnless(sys.platform == "linux" and all(shutil.which(t) for t in mod._rebuild.REQUIRED_TOOLS),
                     "Linux e2fsprogs/fakeroot backend not available")
class BuildRootfsLinuxBuildTests(unittest.TestCase):
    """Real end-to-end build with fakeroot, mke2fs, debugfs and e2fsck."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def make_reference_recovery(self) -> Path:
        tree = self.root / "reference-tree"
        tree.mkdir()
        (tree / "marker").write_text("recovery\n", encoding="utf-8")
        recovery = self.root / "recovery.img"
        with open(recovery, "xb") as handle:
            handle.truncate(4 * 1024 * 1024)
        conf = self.root / "empty.conf"
        conf.write_text("[defaults]\n\n[fs_types]\n\tpmkb = {\n\t}\n", encoding="utf-8")
        subprocess.run(["mke2fs", "-q", "-F", "-T", "pmkb", "-L", "recoveryfs", "-b", "1024", "-I", "256",
                        "-O", "none," + KOBO_LIKE_FEATURES, "-d", str(tree), str(recovery)],
                       check=True, capture_output=True, env={**os.environ, "MKE2FS_CONFIG": str(conf)})
        return recovery

    def test_real_build_produces_verified_image(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        recovery = self.make_reference_recovery()
        output = self.root / "out" / "p1-koreader.img"
        output.parent.mkdir()
        size = 4 * 1024 * 1024 + 512
        calls = []
        real_run = subprocess.run

        def recording_run(argv, *args, **kwargs):
            calls.append(list(argv))
            return real_run(argv, *args, **kwargs)

        with mock.patch.object(mod.subprocess, "run", side_effect=recording_run):
            report = mod.build_rootfs(koreader, runtime, recovery, output, size)
        self.assertEqual("experimental", report["status"], report)
        self.assertTrue(report["complete"])
        self.assertFalse(report["physical_restore_eligible"])
        self.assertFalse(report["hardware_qualified"])
        self.assertEqual(size, output.stat().st_size)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), report["rootfs_sha256"])
        self.assertFalse(Path(str(output) + ".part").exists())
        self.assertTrue(Path(str(output) + ".koreader-build.json").is_file())
        self.assertEqual(0, subprocess.run(["e2fsck", "-f", "-n", str(output)], capture_output=True).returncode)
        for argv in calls:
            tool = Path(argv[0]).name
            self.assertNotIn(tool, {"dd", "mount", "umount", "losetup", "blockdev", "diskpart"})
            if tool == "debugfs":
                self.assertNotIn("-w", argv)
            self.assertFalse(any(a.startswith("/dev/") for a in argv), argv)

    def test_real_build_detects_tampering_after_the_fact(self):
        koreader = make_koreader_dir(self.root)
        runtime = make_runtime_dir(self.root)
        recovery = self.make_reference_recovery()
        output = self.root / "out.img"
        size = 4 * 1024 * 1024 + 512
        report = mod.build_rootfs(koreader, runtime, recovery, output, size)
        self.assertEqual("experimental", report["status"], report)
        manifest = {"opt/koreader/reader.lua": {"kind": "file", "mode": 0o644,
                                                "sha256": "0" * 64, "size": 1}}
        with tempfile.TemporaryDirectory() as td:
            errors = mod._verify_built_image(output, manifest, Path(td))
        self.assertTrue(any("content differs" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
