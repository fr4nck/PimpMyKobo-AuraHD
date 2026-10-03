import importlib.util
import os
import struct
import tempfile
import unittest
from unittest import mock
from pathlib import Path

spec = importlib.util.spec_from_file_location('arm_audit', Path(__file__).resolve().parents[1] / 'tools/audit-arm-runtime.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def binary(needed=None, interpreter=None):
    data = bytearray(512)
    data[:7] = b'\x7fELF\x01\x01\x01'
    count = 1 + bool(needed) + bool(interpreter)
    struct.pack_into('<HHIIIIIHHHHHH', data, 16, 3, 40, 1, 0, 52, 0, 0x5000000, 52, 32, count, 0, 0, 0)
    struct.pack_into('<IIIIIIII', data, 52, 1, 0, 0x1000, 0, 512, 512, 5, 4096)
    pos = 84
    if needed:
        struct.pack_into('<IIIIIIII', data, pos, 2, 200, 0x1000 + 200, 0, 32, 32, 4, 4)
        for i, pair in enumerate(((5, 0x1000 + 300), (10, len(needed) + 1), (1, 0), (0, 0))):
            struct.pack_into('<iI', data, 200 + i * 8, *pair)
        data[300:300 + len(needed) + 1] = needed.encode() + b'\0'
        pos += 32
    if interpreter:
        text = interpreter.encode() + b'\0'
        struct.pack_into('<IIIIIIII', data, pos, 3, 350, 0, 0, len(text), len(text), 4, 1)
        data[350:350 + len(text)] = text
    return bytes(data)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ('bin', 'lib', 'opt/koreader/libs'):
            (self.root / directory).mkdir(parents=True)

    def test_transitive_dependencies_and_hashes_without_mutation(self):
        (self.root / 'bin/reader').write_bytes(binary('libreader.so', '/lib/ld.so'))
        (self.root / 'lib/ld.so').write_bytes(binary())
        (self.root / 'opt/koreader/libs/libreader.so').write_bytes(binary('libc.so'))
        (self.root / 'lib/libc.so').write_bytes(binary())
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = audit.audit(self.root)
        self.assertEqual('ok', report['status'], report)
        self.assertEqual(4, len(report['elf_files']))
        self.assertFalse(report['physical_restore_eligible'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        (self.root / 'lib/libc.so').unlink()
        self.assertIn('libc.so', '\n'.join(audit.audit(self.root)['errors']))

    def test_invalid_first_library_and_search_paths_fail_closed(self):
        (self.root / 'bin/reader').write_bytes(binary('libc.so'))
        (self.root / 'opt/koreader/libs/libc.so').write_bytes(b'not ELF')
        (self.root / 'lib/libc.so').write_bytes(binary())
        self.assertEqual('failed', audit.audit(self.root)['status'])
        data = bytearray(binary('/lib'))
        struct.pack_into('<i', data, 216, 29)
        (self.root / 'bin/reader').write_bytes(data)
        self.assertIn('RPATH/RUNPATH', '\n'.join(audit.audit(self.root)['errors']))

    def test_wrong_architecture_truncation_and_invalid_string_table(self):
        data = bytearray(binary('libc.so'))
        struct.pack_into('<H', data, 18, 62)
        with self.assertRaises(ValueError): audit.elf(data)
        with self.assertRaises(ValueError): audit.elf(binary()[:80])
        data = bytearray(binary('libc.so'))
        struct.pack_into('<I', data, 204, 0xffffffff)
        with self.assertRaises(ValueError): audit.elf(data)

    @unittest.skipUnless(os.name == 'posix', 'POSIX guest symlink fixtures')
    def test_absolute_guest_links_cycles_and_escape(self):
        (self.root / 'lib/real.so').write_bytes(binary())
        (self.root / 'lib/alias.so').symlink_to('/lib/real.so')
        self.assertEqual(self.root / 'lib/real.so', audit.target(self.root, '/lib/alias.so'))
        (self.root / 'lib/cycle.so').symlink_to('cycle.so')
        with self.assertRaises(ValueError): audit.target(self.root, '/lib/cycle.so')
        (self.root / 'lib/escape.so').symlink_to('../../outside')
        with self.assertRaises(ValueError): audit.target(self.root, '/lib/escape.so')
        self.assertEqual('failed', audit.audit(self.root)['status'])

    def test_unreadable_subtree_is_reported_instead_of_silently_skipped(self):
        def walk(*args, **kwargs):
            kwargs['onerror'](PermissionError('synthetic inaccessible directory'))
            return iter(())
        with mock.patch.object(audit.os, 'walk', side_effect=walk):
            report = audit.audit(self.root)
        self.assertEqual('failed', report['status'])
        self.assertIn('rootfs traversal', '\n'.join(report['errors']))

    def test_empty_root_and_special_file_are_refused(self):
        self.assertEqual('failed', audit.audit(self.root)['status'])
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.root / 'bin/pipe')
            self.assertIn('not a regular file', '\n'.join(audit.audit(self.root)['errors']))
        for path in ('/dev/sdb', '/proc', '/sys', '/', r'\\.\PhysicalDrive2'):
            with self.assertRaises(ValueError): audit.audit(path)


@unittest.skipUnless(os.name == 'posix', 'POSIX permissions required for bootstrap contract')
class BootstrapTests(unittest.TestCase):
    # Keep the runtime fixtures, with a synthetic offline execution chain.
    def setUp(self):
        RuntimeTests.setUp(self)
        for guest in audit.BOOT_ELFS:
            path = self.root / guest.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(binary())
            path.chmod(0o755)
        for guest in audit.BOOT_SCRIPTS:
            path = self.root / guest.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        (self.root / 'etc/inittab').write_text('\n'.join(audit.BOOT_ACTIONS) + '\n')
        (self.root / 'opt/koreader/reader.lua').write_text('-- synthetic Lua fixture\n')

    def test_bootstrap_contract_is_opt_in_and_does_not_mutate_files(self):
        before = {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        self.assertFalse(audit.audit(self.root)['bootstrap_checked'])
        report = audit.audit(self.root, check_bootstrap=True)
        self.assertEqual('ok', report['status'], report)
        self.assertTrue(report['bootstrap_checked'])
        self.assertEqual(10, len(report['bootstrap_files']))
        self.assertFalse(report['hardware_qualified'])
        self.assertFalse(report['physical_restore_eligible'])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                                  for p in before})

    def test_missing_boot_files_fail_even_when_other_elfs_are_valid(self):
        for guest in (*audit.BOOT_ELFS, *audit.BOOT_SCRIPTS, '/etc/inittab', '/opt/koreader/reader.lua'):
            path = self.root / guest.lstrip('/')
            data = path.read_bytes()
            mode = path.stat().st_mode
            path.unlink()
            with self.subTest(guest=guest):
                self.assertEqual('ok', audit.audit(self.root)['status'])
                report = audit.audit(self.root, check_bootstrap=True)
                self.assertEqual('failed', report['status'])
                self.assertTrue(any(error.startswith(guest + ':') for error in report['errors']))
            path.write_bytes(data)
            path.chmod(mode)

    def test_execute_bits_interpreters_and_line_endings(self):
        reader = self.root / 'usr/bin/pmkb-reader'
        reader.chmod(0o644)
        self.assertIn('no execute bit', '\n'.join(audit.audit(self.root, True)['errors']))
        reader.chmod(0o755)
        for data in (b'#!/bin/sh\r\nexit 0\r\n', b'#!/missing/sh\n', b'exit 0\n', b''):
            with self.subTest(data=data):
                reader.write_bytes(data)
                self.assertEqual('failed', audit.audit(self.root, True)['status'])
        reader.write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.root / 'bin/sh').write_bytes(b'not an ARM shell')
        self.assertIn('/bin/sh:', '\n'.join(audit.audit(self.root, True)['errors']))

    def test_inittab_rejects_missing_duplicate_and_extra_actions(self):
        path = self.root / 'etc/inittab'
        for actions in (audit.BOOT_ACTIONS[:1], (*audit.BOOT_ACTIONS, '::once:/usr/bin/nickel'),
                        (*audit.BOOT_ACTIONS, audit.BOOT_ACTIONS[1])):
            path.write_text('\n'.join(actions))
            self.assertIn('inittab differs', '\n'.join(audit.audit(self.root, True)['errors']))
        path.write_text('# comment\n\n' + '\n'.join(audit.BOOT_ACTIONS))
        self.assertEqual('ok', audit.audit(self.root, True)['status'])

    def test_busybox_guest_absolute_links_are_validated(self):
        for guest in ('/sbin/init', '/bin/sh'):
            path = self.root / guest.lstrip('/')
            path.unlink()
            path.symlink_to('/bin/busybox')
        report = audit.audit(self.root, True)
        self.assertEqual('ok', report['status'], report)
        (self.root / 'bin/busybox').chmod(0o644)
        self.assertTrue(any('/sbin/init: bootstrap executable' in e
                            for e in audit.audit(self.root, True)['errors']))


class StorageTests(unittest.TestCase):
    def setUp(self):
        RuntimeTests.setUp(self)
        (self.root / 'bin/reader').write_bytes(binary())

    def test_missing_mountpoint_fails_only_when_requested(self):
        self.assertEqual('ok', audit.audit(self.root)['status'])
        self.assertFalse(audit.audit(self.root)['storage_checked'])
        report = audit.audit(self.root, check_storage=True)
        self.assertEqual('failed', report['status'])
        self.assertTrue(report['errors'][0].startswith('/mnt:'))
        (self.root / 'mnt').mkdir()
        report = audit.audit(self.root, check_storage=True)
        self.assertTrue(report['errors'][0].startswith('/mnt/onboard:'))
        self.assertFalse((self.root / 'mnt/onboard').exists())

    def test_valid_empty_directory_does_not_claim_p3_is_mounted(self):
        (self.root / 'mnt/onboard').mkdir(parents=True)
        report = audit.audit(self.root, check_storage=True)
        self.assertEqual('ok', report['status'], report)
        self.assertTrue(report['storage']['onboard_empty'])
        self.assertFalse(report['storage']['mount_verified'])
        self.assertFalse(report['physical_restore_eligible'])
        self.assertEqual(['/mnt', '/mnt/onboard'],
                         [item['path'] for item in report['storage']['directories']])

    def test_file_in_place_of_either_directory_is_refused(self):
        reparse = mock.Mock(st_mode=audit.stat.S_IFDIR | 0o755, st_file_attributes=0x400)
        with mock.patch.object(Path, 'lstat', return_value=reparse):
            result, errors = audit.storage(self.root)
            self.assertTrue(errors)
            self.assertIsNone(result['onboard_empty'])
        (self.root / 'mnt').write_text('keep')
        self.assertEqual('failed', audit.audit(self.root, check_storage=True)['status'])
        self.assertEqual('keep', (self.root / 'mnt').read_text())
        (self.root / 'mnt').unlink()
        (self.root / 'mnt').mkdir()
        (self.root / 'mnt/onboard').write_text('keep')
        self.assertEqual('failed', audit.audit(self.root, check_storage=True)['status'])
        self.assertEqual('keep', (self.root / 'mnt/onboard').read_text())

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink fixture')
    def test_linked_mountpoint_or_parent_is_refused_without_following(self):
        outside = self.root / 'outside'
        outside.mkdir()
        for relative in ('mnt', 'mnt/onboard'):
            path = self.root / relative
            if relative == 'mnt/onboard':
                (self.root / 'mnt').mkdir()
            for link in (str(outside), '/absent-guest-directory', 'absent-relative'):
                path.symlink_to(link, target_is_directory=True)
                result, errors = audit.storage(self.root)
                self.assertTrue(errors, (relative, link))
                self.assertIsNone(result['onboard_empty'])
                path.unlink()
        self.assertEqual([], list(outside.iterdir()))

    def test_underlying_books_are_reported_without_names_or_mutation(self):
        (self.root / 'mnt/onboard').mkdir(parents=True)
        book = self.root / 'mnt/onboard/private title.epub'
        book.write_bytes(b'synthetic book')
        before = (book.read_bytes(), book.stat().st_mode, book.stat().st_mtime_ns)
        report = audit.audit(self.root, check_storage=True)
        self.assertEqual('ok', report['status'], report)
        self.assertFalse(report['storage']['onboard_empty'])
        self.assertNotIn('private title', str(report['storage']))
        self.assertEqual(before, (book.read_bytes(), book.stat().st_mode, book.stat().st_mtime_ns))
