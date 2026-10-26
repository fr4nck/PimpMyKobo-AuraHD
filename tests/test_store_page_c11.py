"""L06-D3: passive C11 e-ink page geometry and v1 JSON integration.

Use a compiler already installed on the host, never install a dependency.
No Kobo access, firmware, framebuffer, touch input or app execution.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
STORE = REPO / "experimental" / "store-v0"
NATIVE = STORE / "native"
sys.path.insert(0, str(STORE))
from store_view_contract import encode_store_view


def entry(app_id, label="Demo"):
    return {"id": app_id, "name": label, "version": "0.1.0",
            "entrypoint": "bin/demo", "network_declared": False,
            "state": "installed_unverified"}


def source(items=(), pending=()):
    return {"scope": "synthetic_read_only", "installed": items,
            "cleanup_pending": pending}


class NativeStorePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = next((shutil.which(cmd) for cmd in ("cc", "gcc", "clang")
                         if shutil.which(cmd)), None)
        if not compiler:
            raise unittest.SkipTest("C11 compiler unavailable; host C tests not executed")
        cls.temp = tempfile.TemporaryDirectory(prefix="pmkb-store-page-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / ("store_page.exe" if os.name == "nt"
                                           else "store_page")
        build = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-O2", "-DPMKB_STORE_WITH_PARSER",
             str(NATIVE / "pmkb_store_view.c"),
             str(NATIVE / "pmkb_store_page.c"),
             str(NATIVE / "test_store_page.c"), "-o", str(cls.binary)],
            capture_output=True, text=True, timeout=90, check=False)
        if build.returncode:
            raise AssertionError("C11 build failed:\n" + build.stdout + build.stderr)

    def invoke(self, data, width, height, page):
        return subprocess.run(
            [str(self.binary), "--stdin", str(width), str(height), str(page)],
            input=data, capture_output=True, timeout=10, check=False)

    def test_c11_layout_assertions(self):
        result = subprocess.run([str(self.binary)], capture_output=True,
                                text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("265 assertions PASS, 0 FAIL", result.stdout)

    def test_empty_is_single_static_page(self):
        result = self.invoke(encode_store_view(source()), 320, 480, 0)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("OK 0/1 0 0 0 0", result.stdout.decode().strip())

    def test_pagination_320x480(self):
        items = tuple(entry(f"org.pmkb.app{i:02d}") for i in range(64))
        pending = tuple(f".pmkb-remove-{i:03d}" for i in range(512))
        raw = encode_store_view(source(items, pending))
        for page, expected in ((0, "OK 0/13 5 64 512 0"),
                               (12, "OK 12/13 4 64 512 60")):
            with self.subTest(page=page):
                result = self.invoke(raw, 320, 480, page)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(expected, result.stdout.decode().strip())

    def test_pagination_1080x1440(self):
        raw = encode_store_view(source(tuple(entry(f"org.pmkb.app{i:02d}")
                                            for i in range(64))))
        for page, expected in ((0, "OK 0/6 12 64 0 0"),
                               (5, "OK 5/6 4 64 0 60")):
            with self.subTest(page=page):
                result = self.invoke(raw, 1080, 1440, page)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(expected, result.stdout.decode().strip())

    def test_pagination_1440x1080(self):
        raw = encode_store_view(source(tuple(entry(f"org.pmkb.app{i:02d}")
                                            for i in range(64))))
        for page, expected in ((0, "OK 0/8 9 64 0 0"),
                               (7, "OK 7/8 1 64 0 63")):
            with self.subTest(page=page):
                result = self.invoke(raw, 1440, 1080, page)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(expected, result.stdout.decode().strip())

    def test_unicode_label_and_inert_launch_flag(self):
        raw = encode_store_view(source((entry("org.pmkb.demo", "M\u00e9t\u00e9o \U0001f642"),)))
        self.assertEqual(0, self.invoke(raw, 1080, 1440, 0).returncode)
        fake_launch = raw.replace(b'"launchable":false', b'"launchable":true')
        self.assertEqual(3, self.invoke(fake_launch, 1080, 1440, 0).returncode)

    def test_rejects_trailing_input_and_unknown_schema(self):
        raw = encode_store_view(source())
        for broken in (raw + b" ", raw[:-1], b"not-json",
                       raw.replace(b"pmkb-store-view-v1", b"future-store-v2")):
            with self.subTest(data=broken[-30:]):
                self.assertEqual(3, self.invoke(broken, 320, 480, 0).returncode)

    def test_out_of_range_and_unknown_geometry(self):
        raw = encode_store_view(source((entry("org.pmkb.demo"),)))
        self.assertEqual(4, self.invoke(raw, 320, 480, 1).returncode)
        self.assertEqual(4, self.invoke(raw, 1080, 1080, 0).returncode)


if __name__ == "__main__":
    unittest.main()
