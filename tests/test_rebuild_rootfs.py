import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
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



# Conservative ext4 layout, as an old Kobo mke2fs would produce: no metadata_csum/64bit.
KOBO_LIKE_FEATURES = ("has_journal,ext_attr,resize_inode,dir_index,filetype,extent,flex_bg,"
                      "sparse_super,large_file,huge_file,uninit_bg,dir_nlink,extra_isize")
P1_SIZE = 4 * 1024 * 1024 + 512  # deliberately not a multiple of the block size, like the real card


def _add(tf, name, kind, *, data=None, mode=0o755, uid=0, gid=0, linkname="", major=0, minor=0):
    info = tarfile.TarInfo(name)
    info.type, info.mode, info.uid, info.gid = kind, mode, uid, gid
    info.uname = info.gname = ""
    info.linkname, info.devmajor, info.devminor = linkname, major, minor
    if data is not None:
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    else:
        tf.addfile(info)


def build_fs_tgz(path: Path, *, bad_md5: bool = False, historical_root: bool = False) -> None:
    files = {
        "bin/busybox": (b"\x7fELF busybox\n" * 64, 0o755, 0, 0),
        "etc/inittab": (b"::sysinit:/etc/init.d/rcS\n", 0o644, 0, 0),
        "usr/bin/suid-tool": (b"suid\n", 0o4755, 0, 0),
        "home/user/note été.txt": (b"bonjour\n", 0o600, 1000, 1000),
    }
    md5 = [f"{hashlib.md5(d).hexdigest()}  ./{n}" for n, (d, *_rest) in files.items()]
    if bad_md5:
        md5[0] = "0" * 32 + md5[0][32:]
    if historical_root:
        md5.append(f"{hashlib.md5(files['bin/busybox'][0]).hexdigest()}  ./bin/ash")
    with tarfile.open(path, "w:gz", format=tarfile.GNU_FORMAT) as tf:
        if historical_root:
            _add(tf, "./", tarfile.DIRTYPE, uid=1000, gid=1000)
        for d in ("bin", "etc", "usr", "usr/bin", "dev", "proc", "home"):
            _add(tf, f"./{d}", tarfile.DIRTYPE)
        _add(tf, "./home/user", tarfile.DIRTYPE, mode=0o700, uid=1000, gid=1000)
        for name, (data, mode, uid, gid) in files.items():
            _add(tf, f"./{name}", tarfile.REGTYPE, data=data, mode=mode, uid=uid, gid=gid)
        _add(tf, "./bin/sh", tarfile.SYMTYPE, linkname="busybox", mode=0o777)
        _add(tf, "./usr/bin/vi", tarfile.SYMTYPE, linkname="../../bin/busybox", mode=0o777)
        _add(tf, "./etc/mtab", tarfile.SYMTYPE, linkname="/proc/mounts", mode=0o777)
        _add(tf, "./bin/long", tarfile.SYMTYPE, linkname="/" + "x" * 90, mode=0o777)
        _add(tf, "./bin/ash", tarfile.LNKTYPE, linkname="./bin/busybox", mode=0o755)
        _add(tf, "./dev/console", tarfile.CHRTYPE, mode=0o600, major=5, minor=1)
        _add(tf, "./dev/null", tarfile.CHRTYPE, mode=0o666, major=1, minor=3)
        _add(tf, "./dev/mmcblk0", tarfile.BLKTYPE, mode=0o660, major=179, minor=0, gid=6)
        _add(tf, "./dev/initctl", tarfile.FIFOTYPE, mode=0o600)
        _add(tf, "./fs.md5sum", tarfile.REGTYPE, data=("\n".join(md5) + "\n").encode(), mode=0o644)


@unittest.skipUnless(sys.platform == "linux" and all(shutil.which(t) for t in mod.REQUIRED_TOOLS),
                     "Linux e2fsprogs/fakeroot backend not available")
class RebuildRootfsLinuxBuildTests(unittest.TestCase):
    """Real end-to-end build with fakeroot, tar, mke2fs, debugfs and e2fsck."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def make_inputs(self, *, bad_md5: bool = False, historical_root: bool = False):
        tree = self.root / "p2tree"
        (tree / "upgrade").mkdir(parents=True)
        build_fs_tgz(tree / "upgrade" / "fs.tgz", bad_md5=bad_md5, historical_root=historical_root)
        recovery = self.root / "p2 récupération.img"
        with open(recovery, "xb") as handle:
            handle.truncate(8 * 1024 * 1024)
        conf = self.root / "empty.conf"
        conf.write_text("[defaults]\n\n[fs_types]\n\tpmkb = {\n\t}\n", encoding="utf-8")
        subprocess.run(["mke2fs", "-q", "-F", "-T", "pmkb", "-L", "recoveryfs", "-b", "1024", "-I", "256",
                        "-O", "none," + KOBO_LIKE_FEATURES, "-d", str(tree), str(recovery)],
                       check=True, capture_output=True, env={**os.environ, "MKE2FS_CONFIG": str(conf)})
        digest = hashlib.sha256(recovery.read_bytes()).hexdigest()
        manifest = self.root / "backup-manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "tool": "backup-aura-hd", "status": "complete", "complete": True,
            "identification": {"aura_hd_e606c0": True},
            "mbr": {"partitions": [{"number": 1, "size": P1_SIZE}, {"number": 2, "size": recovery.stat().st_size}]},
            "components": [
                {"name": "p1_rootfs", "size": P1_SIZE, "status": "verified", "sha256": "1" * 64},
                {"name": "p2_recoveryfs", "size": recovery.stat().st_size, "status": "verified", "sha256": digest},
            ],
            "target_fingerprint": {"algorithm": "pmkb-target-v1", "fingerprint_sha256": "2" * 64},
        }), encoding="utf-8")
        return manifest, recovery, digest

    def test_real_build_preserves_layout_metadata_and_content(self):
        manifest, recovery, digest = self.make_inputs()
        output = self.root / "out" / "p1 rootfs.img"
        output.parent.mkdir()
        calls = []
        real_run = subprocess.run

        def recording_run(argv, *args, **kwargs):
            calls.append(list(argv))
            return real_run(argv, *args, **kwargs)

        with mock.patch.object(mod.subprocess, "run", side_effect=recording_run):
            report = mod.build_rootfs(manifest, recovery, output)
        self.assertEqual("ok", report["status"], report)
        self.assertEqual(P1_SIZE, output.stat().st_size)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), report["rootfs_sha256"])
        self.assertFalse(Path(str(output) + ".part").exists())
        self.assertTrue(Path(str(output) + ".rebuild.json").is_file())
        # ext4 layout copied from the recovery superblock, never from host defaults.
        built = mod.read_ext_parameters(output)
        self.assertEqual(sorted(KOBO_LIKE_FEATURES.split(",")), built["features"])
        self.assertNotIn("metadata_csum", built["features"])
        self.assertNotIn("64bit", built["features"])
        self.assertEqual((1024, 256, "rootfs"), (built["block_size"], built["inode_size"], built["label"]))
        self.assertEqual(512, report["ext4"]["unused_tail_bytes"])
        checks = report["checks"]
        self.assertEqual(checks["metadata"]["entries"], checks["metadata"]["verified"])
        self.assertEqual(checks["content"]["files"], checks["content"]["verified"])
        self.assertEqual(4, checks["special_files"])
        self.assertEqual(4, checks["symlinks"])
        self.assertEqual((4, 4), (checks["fs_md5sum"]["entries"], checks["fs_md5sum"]["matched"]))
        self.assertEqual(0, subprocess.run(["e2fsck", "-f", "-n", str(output)], capture_output=True).returncode)
        # The recovery input is untouched; nothing but the .part output is ever written.
        self.assertEqual(digest, hashlib.sha256(recovery.read_bytes()).hexdigest())
        for argv in calls:
            tool = Path(argv[0]).name
            self.assertNotIn(tool, {"dd", "mount", "umount", "losetup", "blockdev", "diskpart"})
            if tool == "debugfs":
                self.assertNotIn("-w", argv)
            self.assertFalse(any(a.startswith("/dev/") for a in argv), argv)

    def test_md5_mismatch_fails_and_keeps_only_a_part_file(self):
        manifest, recovery, _ = self.make_inputs(bad_md5=True)
        output = self.root / "p1.img"
        report = mod.build_rootfs(manifest, recovery, output)
        self.assertEqual("failed", report["status"])
        self.assertTrue(any("fs.md5sum" in e for e in report["errors"]), report["errors"])
        self.assertFalse(output.exists())
        self.assertTrue(Path(str(output) + ".part").exists())

    def test_verification_detects_metadata_differences(self):
        manifest, recovery, _ = self.make_inputs()
        output = self.root / "p1.img"
        self.assertEqual("ok", mod.build_rootfs(manifest, recovery, output)["status"])
        with tarfile.open(self.root / "p2tree" / "upgrade" / "fs.tgz", "r:gz") as tf:
            entries, hashes, md5sum = mod._validate_archive(tf)
        entries["home/user"].uid = 0
        entries["dev/console"].devminor = 9
        with tempfile.TemporaryDirectory() as td:
            _, errors = mod.verify_image(output, entries, hashes, md5sum, Path(td))
        self.assertTrue(any("/home/user" in e and "owner" in e for e in errors), errors)
        self.assertTrue(any("/dev/console" in e and "device" in e for e in errors), errors)

    def test_legacy_build_preserves_declared_provenance_and_inputs(self):
        from test_import_legacy_backup import make_pre, imported_manifest, legacy
        manifest, recovery, digest = self.make_inputs()
        pre = self.root / "historical boot.bin"
        make_pre(pre, P1_SIZE, recovery.stat().st_size)
        pre_sha = legacy.digest(pre)
        imported_manifest(pre, recovery, manifest)
        output = self.root / "legacy rootfs.img"
        report = mod.build_rootfs(manifest, recovery, output)
        self.assertEqual("failed", report["status"])
        self.assertFalse(output.exists())
        report = mod.build_rootfs(manifest, recovery, output, accept_legacy_import=True)
        self.assertEqual("ok", report["status"], report)
        self.assertEqual("legacy/imported", report["input_provenance"]["kind"])
        self.assertFalse(report["physical_restore_eligible"])
        self.assertIsNone(report["target_fingerprint"])
        self.assertEqual(pre_sha, legacy.digest(pre))
        self.assertEqual(digest, legacy.digest(recovery))
        saved = json.loads(Path(str(output) + ".rebuild.json").read_text())
        self.assertFalse(saved["physical_restore_eligible"])

    def test_legacy_qualification_does_not_bypass_recovery_content_validation(self):
        from test_import_legacy_backup import make_pre, imported_manifest
        manifest, recovery, _ = self.make_inputs(bad_md5=True)
        pre = self.root / "boot.bin"
        make_pre(pre, P1_SIZE, recovery.stat().st_size)
        imported_manifest(pre, recovery, manifest)
        output = self.root / "legacy rootfs.img"
        report = mod.build_rootfs(manifest, recovery, output, accept_legacy_import=True)
        self.assertEqual("failed", report["status"], report)
        self.assertTrue(any("fs.md5sum" in e for e in report["errors"]))
        self.assertFalse(output.exists())

    def test_archive_root_owner_and_md5_hard_links_are_preserved(self):
        manifest, recovery, _ = self.make_inputs(historical_root=True)
        report = mod.build_rootfs(manifest, recovery, self.root / "root.img")
        self.assertEqual("ok", report["status"], report)
        checks = report["checks"]
        self.assertEqual(checks["metadata"]["entries"], checks["metadata"]["verified"])
        self.assertEqual((5, 5), (checks["fs_md5sum"]["entries"], checks["fs_md5sum"]["matched"]))

    def test_hard_link_content_and_inode_corruption_are_detected(self):
        manifest, recovery, _ = self.make_inputs(historical_root=True)
        image = self.root / "root.img"
        self.assertEqual("ok", mod.build_rootfs(manifest, recovery, image)["status"])
        # Change only the temporary output, never the recovery source.
        subprocess.run(["debugfs", "-w", "-R", "unlink /bin/ash", str(image)], check=True, capture_output=True)
        subprocess.run(["debugfs", "-w", "-R", "link /etc/inittab /bin/ash", str(image)], check=True, capture_output=True)
        with tarfile.open(self.root / "p2tree" / "upgrade" / "fs.tgz", "r:gz") as tf:
            entries, hashes, md5sum = mod._validate_archive(tf)
        with tempfile.TemporaryDirectory() as td:
            _, errors = mod.verify_image(image, entries, hashes, md5sum, Path(td))
        self.assertTrue(any("hard link does not share target inode" in e for e in errors), errors)
        self.assertTrue(any("/bin/ash: content differs" in e for e in errors), errors)
        self.assertTrue(any("fs.md5sum" in e for e in errors), errors)


class RebuildRootfsArchiveSafetyTests(unittest.TestCase):
    def _archive(self, members):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            for args, kwargs in members:
                _add(tf, *args, **kwargs)
        buf.seek(0)
        return tarfile.open(fileobj=buf, mode="r")

    def test_absolute_and_parent_symlink_targets_are_allowed(self):
        with self._archive([(("bin/sh", tarfile.SYMTYPE), {"linkname": "/bin/busybox"}),
                            (("usr/bin/vi", tarfile.SYMTYPE), {"linkname": "../../bin/busybox"})]) as tf:
            entries, _, _ = mod._validate_archive(tf)
        self.assertIn("usr/bin/vi", entries)

    def test_member_extracted_through_a_symlink_is_refused(self):
        with self._archive([(("etc", tarfile.SYMTYPE), {"linkname": "/etc"}),
                            (("etc/passwd", tarfile.REGTYPE), {"data": b"x"})]) as tf:
            with self.assertRaisesRegex(RuntimeError, "through a symlink"):
                mod._validate_archive(tf)

    def test_traversal_and_unsafe_hard_links_are_refused(self):
        for members in ([(("../evil", tarfile.REGTYPE), {"data": b"x"})],
                        [(("a", tarfile.LNKTYPE), {"linkname": "../outside"})]):
            with self.subTest(members=members), self._archive(members) as tf:
                with self.assertRaises(RuntimeError):
                    mod._validate_archive(tf)

    def test_chained_hard_links_get_expected_content_hashes(self):
        with self._archive([(("data", tarfile.REGTYPE), {"data": b"content"}),
                            (("first", tarfile.LNKTYPE), {"linkname": "data"}),
                            (("second", tarfile.LNKTYPE), {"linkname": "first"})]) as tf:
            _, hashes, _ = mod._validate_archive(tf)
        self.assertEqual({"data", "first", "second"}, set(hashes))
        self.assertEqual({hashlib.sha256(b"content").hexdigest()}, set(hashes.values()))

    def test_dangling_cyclic_and_non_regular_hard_links_are_refused(self):
        for members in ([(("a", tarfile.LNKTYPE), {"linkname": "missing"})],
                        [(("a", tarfile.LNKTYPE), {"linkname": "b"}),
                         (("b", tarfile.LNKTYPE), {"linkname": "a"})],
                        [(("dir", tarfile.DIRTYPE), {}), (("a", tarfile.LNKTYPE), {"linkname": "dir"})]):
            with self.subTest(members=members), self._archive(members) as tf:
                with self.assertRaisesRegex(RuntimeError, "hard link"):
                    mod._validate_archive(tf)

if __name__ == "__main__":
    unittest.main()
