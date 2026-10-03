import importlib.util
import os
import struct
import tempfile
import unittest
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

    def test_empty_root_and_special_file_are_refused(self):
        self.assertEqual('failed', audit.audit(self.root)['status'])
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.root / 'bin/pipe')
            self.assertIn('not a regular file', '\n'.join(audit.audit(self.root)['errors']))
        for path in ('/dev/sdb', '/proc', '/sys', '/', r'\\.\PhysicalDrive2'):
            with self.assertRaises(ValueError): audit.audit(path)
