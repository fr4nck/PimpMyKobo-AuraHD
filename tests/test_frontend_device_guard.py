import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'experimental/offline-rootfs'


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh') and Path('/dev/null').is_char_device(),
                     'POSIX shell and local character fixture required')
class FrontendDeviceGuardTests(unittest.TestCase):
    """Execute only the real rcS guard body with synthetic sysfs and /dev paths."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.inputs = root / 'sys/class/input'
        self.misc = root / 'sys/class/misc'
        self.devices = root / 'dev'
        for folder in (self.inputs, self.misc / 'ntx_io', self.devices / 'input'):
            folder.mkdir(parents=True)
        (self.misc / 'ntx_io/dev').write_text('10:190\n', encoding='ascii')
        for name in ('fb0', 'ntx_io'):
            (self.devices / name).symlink_to('/dev/null')
        self.event('event7', 'zForce-ir-touch')
        source = (ROOT / 'etc/init.d/rcS').read_text(encoding='utf-8')
        start = '# PMKB_FRONTEND_GUARD_BEGIN'
        end = '# PMKB_FRONTEND_GUARD_END'
        self.assertEqual(1, source.count(start))
        self.assertEqual(1, source.count(end))
        body = source.split(start, 1)[1].split(end, 1)[0]
        self.script = 'set -eu\n' + body + '\npmkb_check_frontend_devices "$1" "$2" "$3"\n'

    def event(self, number, name, character=True):
        event_dir = self.inputs / number / 'device'
        event_dir.mkdir(parents=True, exist_ok=True)
        (event_dir / 'name').write_text(name + '\n', encoding='utf-8')
        node = self.devices / 'input' / number
        if node.exists() or node.is_symlink():
            node.unlink()
        if character:
            node.symlink_to('/dev/null')  # stat only, never open or write /dev
        else:
            node.write_text('not a character node', encoding='ascii')

    def run_gate(self):
        return subprocess.run(['sh', '-c', self.script, 'sh', str(self.inputs), str(self.devices), str(self.misc)],
                              capture_output=True, text=True)

    def test_recognizes_renumbered_touch_and_unrelated_event0(self):
        self.event('event0', 'gpio-keys')
        result = self.run_gate()
        self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_missing_or_wrong_named_touch(self):
        (self.inputs / 'event7/device/name').write_text('gpio-keys\n', encoding='utf-8')
        self.assertNotEqual(0, self.run_gate().returncode)
        (self.inputs / 'event7/device/name').unlink()
        self.assertNotEqual(0, self.run_gate().returncode)

    def test_rejects_missing_non_character_or_duplicate_touch(self):
        (self.devices / 'input/event7').unlink()
        self.assertNotEqual(0, self.run_gate().returncode)
        self.event('event7', 'zForce-ir-touch', character=False)
        self.assertNotEqual(0, self.run_gate().returncode)
        self.event('event7', 'zForce-ir-touch')
        self.event('event3', 'zForce-ir-touch')
        self.assertNotEqual(0, self.run_gate().returncode)

    def test_frontlight_and_framebuffer_nodes_required(self):
        (self.devices / 'ntx_io').unlink()
        self.assertNotEqual(0, self.run_gate().returncode)
        (self.devices / 'ntx_io').write_text('not a character device', encoding='ascii')
        self.assertNotEqual(0, self.run_gate().returncode)
        (self.devices / 'ntx_io').unlink()
        (self.devices / 'ntx_io').symlink_to('/dev/null')
        (self.misc / 'ntx_io/dev').unlink()
        self.assertNotEqual(0, self.run_gate().returncode)
        (self.misc / 'ntx_io/dev').write_text('10:190\n', encoding='ascii')
        (self.devices / 'fb0').unlink()
        self.assertNotEqual(0, self.run_gate().returncode)

    def test_guard_order_and_shell_syntax(self):
        source = (ROOT / 'etc/init.d/rcS').read_text(encoding='utf-8')
        self.assertLess(source.index('for entry in /sys/class/*/*/dev'),
                        source.index('pmkb_check_frontend_devices /sys/class/input /dev /sys/class/misc'))
        self.assertLess(source.index('pmkb_check_frontend_devices /sys/class/input /dev /sys/class/misc'),
                        source.index('mount -t vfat'))
        result = subprocess.run(['sh', '-n', str(ROOT / 'etc/init.d/rcS')], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_non_numeric_event_suffix_cannot_impersonate_touch(self):
        self.event('eventbad', 'zForce-ir-touch')
        self.assertEqual(0, self.run_gate().returncode)
        (self.inputs / 'event7/device/name').write_text('keyboard\n', encoding='utf-8')
        self.assertNotEqual(0, self.run_gate().returncode)

if __name__ == '__main__':
    unittest.main()
