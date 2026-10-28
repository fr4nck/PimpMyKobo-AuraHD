"""KOReader first-run cover preference: host-only fixtures."""
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "experimental/offline-rootfs/usr/bin/pmkb-cover-init"
READER = ROOT / "experimental/offline-rootfs/usr/bin/pmkb-reader"
BUILDER = ROOT / "tools/build-koreader-rootfs.py"


class ContractTests(unittest.TestCase):
    def test_startup_order(self):
        lines = READER.read_text(encoding="utf-8").splitlines()
        def pos(command):
            return next(i for i, line in enumerate(lines) if line.strip() == command)
        self.assertLess(pos('mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"'),
                        pos('/usr/bin/pmkb-cover-init'))
        self.assertLess(pos('/usr/bin/pmkb-cover-init'), pos('/usr/bin/pmkb-check-onboard'))
        self.assertLess(pos('/usr/bin/pmkb-check-onboard'),
                        pos('exec ./luajit reader.lua /mnt/onboard'))

    def test_builder_scans_required_script(self):
        source = BUILDER.read_text(encoding="utf-8")
        self.assertEqual(2, source.count('"usr/bin/pmkb-cover-init"'))
        self.assertTrue(INIT.read_bytes().startswith(b"#!/bin/sh\n"))

    @unittest.skipUnless(shutil.which("sh"), "POSIX shell required")
    def test_shell_syntax(self):
        for source in (INIT, READER):
            result = subprocess.run(["sh", "-n", str(source)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)


@unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "POSIX shell required")
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pmkb-cover-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cfg = self.root / "config"
        self.cfg.mkdir()
        self.settings = self.cfg / "koreader" / "settings.reader.lua"

    def invoke(self, cfg=None, no_env=False):
        env = os.environ.copy()
        env.pop("XDG_CONFIG_HOME", None)
        if not no_env:
            env["XDG_CONFIG_HOME"] = str(cfg if cfg is not None else self.cfg)
        return subprocess.run(["sh", str(INIT)], cwd=self.root, env=env,
                              capture_output=True, text=True, timeout=10).returncode

    def test_initializes_ignored_cover_without_overwriting(self):
        self.assertEqual(0, self.invoke())
        expected = ('return {\n    ["ignore_power_sleepcover"] = true,\n'
                    '    ["ignore_open_sleepcover"] = false,\n}\n')
        self.assertEqual(expected, self.settings.read_text(encoding="utf-8"))
        self.assertEqual(0, stat.S_IMODE(self.settings.stat().st_mode) & 0o077)
        self.assertEqual(0, self.invoke())
        self.assertEqual(expected, self.settings.read_text(encoding="utf-8"))

    def test_preserves_existing_user_preference(self):
        self.settings.parent.mkdir()
        choice = 'return { ["ignore_power_sleepcover"] = false, ["lastfile"] = "book.epub", }\n'
        self.settings.write_text(choice, encoding="utf-8")
        self.assertEqual(0, self.invoke())
        self.assertEqual(choice, self.settings.read_text(encoding="utf-8"))

    def test_preserves_existing_malformed_regular_file(self):
        self.settings.parent.mkdir()
        self.settings.write_bytes(b"corrupt-user-file")
        self.assertEqual(0, self.invoke())
        self.assertEqual(b"corrupt-user-file", self.settings.read_bytes())

    def test_symlink_file_refused(self):
        self.settings.parent.mkdir()
        target = self.root / "target"
        target.write_bytes(b"untouched")
        self.settings.symlink_to(target)
        self.assertNotEqual(0, self.invoke())
        self.assertEqual(b"untouched", target.read_bytes())

    def test_symlink_directory_refused(self):
        target = self.root / "other"
        target.mkdir()
        (self.cfg / "koreader").symlink_to(target, target_is_directory=True)
        self.assertNotEqual(0, self.invoke())
        self.assertEqual([], list(target.iterdir()))

    def test_invalid_configuration_refused(self):
        self.assertNotEqual(0, self.invoke(no_env=True))
        self.assertNotEqual(0, self.invoke(self.root / "missing"))
        bad = self.root / "file"
        bad.write_bytes(b"keep")
        self.assertNotEqual(0, self.invoke(bad))
        self.assertEqual(b"keep", bad.read_bytes())

    def test_existing_directory_as_settings_refused(self):
        self.settings.mkdir(parents=True)
        self.assertNotEqual(0, self.invoke())


if __name__ == "__main__":
    unittest.main()
