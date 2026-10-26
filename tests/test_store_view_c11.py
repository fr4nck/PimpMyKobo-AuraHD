"""L06-D2: compile and exercise the dependency-free C11 reader on CI hosts.

No installer, Kobo access, network, or downloaded compiler. Skip explicitly
when no C11 compiler is already present on the runner.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "experimental" / "store-v0"
NATIVE = STORE / "native"
sys.path.insert(0, str(STORE))
from store_view_contract import encode_store_view


def item(app_id="org.pmkb.demo", label="Demo", network=False):
    return {"id": app_id, "name": label, "version": "0.1.0",
            "entrypoint": "bin/demo", "network_declared": network,
            "state": "installed_unverified"}


def catalog(items=(), pending=()):
    return {"scope": "synthetic_read_only", "installed": items,
            "cleanup_pending": pending}


class NativeStoreViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = next((shutil.which(cmd) for cmd in ("cc", "gcc", "clang")
                         if shutil.which(cmd)), None)
        if not compiler:
            raise unittest.SkipTest("no C11 compiler on CI host; native qualification not executed")
        cls.temp = tempfile.TemporaryDirectory(prefix="pmkb-native-store-view-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / ("pmkb_store_view.exe" if os.name == "nt"
                                           else "pmkb_store_view")
        build = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-O2", str(NATIVE / "pmkb_store_view.c"),
             str(NATIVE / "test_store_view.c"), "-o", str(cls.binary)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if build.returncode:
            raise AssertionError("C11 build failed:\n" + build.stdout + build.stderr)

    def run_c(self, data):
        return subprocess.run([str(self.binary), "--stdin"], input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=10, check=False)

    def test_c11_inprocess_assertions(self):
        result = subprocess.run([str(self.binary)], capture_output=True,
                                text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("39 assertions PASS, 0 FAIL", result.stdout)

    def test_consume_real_python_v1_snapshot(self):
        raw = encode_store_view(catalog((item(label="Météo 🙂", network=True),),
                                        (".pmkb-remove-fixture",)))
        result = self.run_c(raw)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OK 1 1 org.pmkb.demo", result.stdout.decode().strip())

    def test_empty_snapshot(self):
        result = self.run_c(encode_store_view(catalog()))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OK 0 0 -", result.stdout.decode().strip())

    def test_maximum_64_entries_and_pending_count(self):
        entries = tuple(item(f"org.pmkb.app{i:02d}") for i in range(64))
        pending = tuple(f".pmkb-remove-{i:03d}" for i in range(512))
        raw = encode_store_view(catalog(entries, pending))
        self.assertLessEqual(len(raw), 32768)
        result = self.run_c(raw)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OK 64 512 org.pmkb.app00", result.stdout.decode().strip())

    def test_invalid_launchable_and_trailing_data_rejected(self):
        valid = encode_store_view(catalog((item(),)))
        tampered = valid.replace(b'"launchable":false', b'"launchable":true')
        for invalid in (tampered, valid + b" ", valid[:-1], valid + b"\x00"):
            with self.subTest(raw=invalid[-16:]):
                self.assertEqual(3, self.run_c(invalid).returncode)


if __name__ == "__main__":
    unittest.main()
