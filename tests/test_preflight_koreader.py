import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_audit_arm_runtime as arm_fixtures

spec = importlib.util.spec_from_file_location('koreader_preflight', Path(__file__).resolve().parents[1] / 'tools/preflight-koreader.py')
pre = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pre)


class InputTests(unittest.TestCase):
    def test_cli_does_not_create_peer_bytecode_or_any_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('preflight-koreader.py', 'audit-arm-runtime.py', 'rebuild-rootfs.py'):
                (root / name).write_bytes((Path(pre.__file__).parent / name).read_bytes())
            before = sorted(p.name for p in root.iterdir())
            result = subprocess.run([sys.executable, str(root / 'preflight-koreader.py'), str(root / 'missing')],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertEqual(before, sorted(p.name for p in root.iterdir()))

    def test_devices_special_filesystems_and_missing_inputs_fail(self):
        for source in ('/dev/sdb', r'\\.\PhysicalDrive2', '/proc', '/sys', '/', 'missing-rootfs'):
            report = pre.preflight(source)
            self.assertEqual('FAIL', report['status'], source)
            self.assertFalse(report['device_write_attempted'])
            self.assertFalse(report['physical_restore_eligible'])
            self.assertFalse(report['hardware_qualified'])
            self.assertEqual({'UNQUALIFIED'}, {c['status'] for c in report['hardware'].values()})

    def test_image_without_backend_keeps_content_unqualified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.ext4'
            path.write_bytes(b'synthetic placeholder')
            with mock.patch.object(pre.shutil, 'which', return_value=None):
                report = pre.preflight(path)
            self.assertEqual('UNQUALIFIED', report['status'])
            self.assertIsNone(report['offline_checks_satisfied'])
            for name in pre.CONTENT:
                self.assertEqual('UNQUALIFIED', report['checks'][name]['status'])
            self.assertEqual(b'synthetic placeholder', path.read_bytes())

    @unittest.skipUnless(os.name == 'posix' and all(shutil.which(t) for t in ('mke2fs', 'dumpe2fs', 'e2fsck')),
                         'local ext filesystem backend required')
    def test_real_empty_ext_image_is_checked_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rootfs.ext4'
            with path.open('wb') as stream:
                stream.truncate(4 * 1024 * 1024)
            subprocess.run(['mke2fs', '-q', '-F', '-t', 'ext4', '-L', 'rootfs', str(path)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            before = path.read_bytes()
            report = pre.preflight(path)
            self.assertEqual('PASS', report['checks']['filesystem']['status'], report)
            self.assertEqual('UNQUALIFIED', report['status'])
            self.assertEqual(before, path.read_bytes())
            self.assertFalse(report['hardware_qualified'])

    def test_image_calls_existing_backend_and_only_read_only_fsck(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.ext4'
            path.write_bytes(b'synthetic placeholder')
            for code in (0, 4):
                with (mock.patch.object(pre.shutil, 'which', return_value='/tool'),
                      mock.patch.object(pre.rebuild, 'read_ext_parameters', return_value={'label': 'rootfs'}) as params,
                      mock.patch.object(pre.subprocess, 'run', return_value=mock.Mock(returncode=code, stdout='fixture')) as run):
                    report = pre.preflight(path)
                params.assert_called_once_with(path)
                self.assertEqual(['e2fsck', '-f', '-n', str(path)], run.call_args.args[0])
                self.assertEqual('PASS' if code == 0 else 'FAIL', report['checks']['filesystem']['status'])
                self.assertEqual('UNQUALIFIED', report['checks']['koreader_presence']['status'])
                self.assertFalse(report['hardware_qualified'])


@unittest.skipUnless(os.name == 'posix', 'POSIX bootstrap fixture')
class TreeTests(unittest.TestCase):
    def setUp(self):
        arm_fixtures.BootstrapTests.setUp(self)
        (self.root / 'mnt/onboard').mkdir(parents=True)

    def qualified_signatures(self):
        # A scanner result is injected only to exercise aggregate verdicts.
        return mock.patch.object(pre, 'nickel', return_value=pre.item('PASS', 'Synthetic scanner evidence'))

    def test_all_available_static_checks_pass_hardware_never_does(self):
        before = {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        with self.qualified_signatures():
            report = pre.preflight(self.root)
        self.assertEqual('PASS', report['status'], report)
        self.assertTrue(report['offline_checks_satisfied'])
        self.assertEqual({'UNQUALIFIED'}, {c['status'] for c in report['hardware'].values()})
        self.assertEqual('UNQUALIFIED', report['checks']['image_integrity']['status'])
        self.assertFalse(report['checks']['image_integrity']['applicable'])
        self.assertFalse(report['hardware_qualified'])
        self.assertFalse(report['physical_restore_eligible'])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in before})

    def test_bootstrap_failure(self):
        (self.root / 'etc/inittab').write_text('::once:/usr/bin/nickel\n')
        with self.qualified_signatures():
            report = pre.preflight(self.root)
        self.assertEqual('FAIL', report['status'])
        self.assertEqual('FAIL', report['checks']['bootstrap_and_execute_bits']['status'])

    def test_runtime_failure(self):
        (self.root / 'opt/koreader/luajit').write_bytes(b'\x7fELFbroken')
        with self.qualified_signatures():
            report = pre.preflight(self.root)
        self.assertEqual('FAIL', report['status'])
        self.assertEqual('FAIL', report['checks']['runtime_and_dynamic_dependencies']['status'])
        self.assertEqual('FAIL', report['checks']['koreader_presence']['status'])

    def test_storage_failure(self):
        (self.root / 'mnt/onboard').rmdir()
        with self.qualified_signatures():
            report = pre.preflight(self.root)
        self.assertEqual('FAIL', report['status'])
        self.assertEqual('FAIL', report['checks']['onboard_structure']['status'])
        self.assertFalse((self.root / 'mnt/onboard').exists())

    def test_missing_scanner_is_unqualified_and_not_success(self):
        with mock.patch.object(pre.Path, 'is_file', return_value=False):
            report = pre.preflight(self.root)
        self.assertEqual('UNQUALIFIED', report['checks']['nickel_signatures']['status'])
        self.assertEqual('UNQUALIFIED', report['status'])
        self.assertIsNone(report['offline_checks_satisfied'])

    def test_optional_builder_scanner_is_reused_on_the_post_merge_tree(self):
        # scan_tree_for_nickel (not the pre-merge _copy_tree/_scan_for_nickel
        # pair) is the builder's dedicated entry point for an already
        # assembled directory like the one preflight is given here.
        builder = mock.Mock()
        builder.scan_tree_for_nickel.return_value = []
        with (mock.patch.object(pre.Path, 'is_file', return_value=True),
              mock.patch.object(pre, 'peer', return_value=builder)):
            result = pre.nickel(self.root)
        self.assertEqual('PASS', result['status'])
        builder.scan_tree_for_nickel.assert_called_once_with(self.root)
        builder.scan_tree_for_nickel.return_value = ['/opt/koreader/defaults.lua: Nickel reference']
        with (mock.patch.object(pre.Path, 'is_file', return_value=True),
              mock.patch.object(pre, 'peer', return_value=builder)):
            self.assertEqual('FAIL', pre.nickel(self.root)['status'])
