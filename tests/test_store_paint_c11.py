"""L06-D4a C11 callback adapter test, no PMKB-UI merge or device access."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "experimental" / "store-v0" / "native"


class StorePaintC11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        if not compiler:
            raise unittest.SkipTest("No C11 host compiler; painting tests NOT executed")
        temporary = tempfile.TemporaryDirectory(prefix="pmkb-paint-")
        cls.addClassCleanup(temporary.cleanup)
        cls.binary = Path(temporary.name) / ("paint.exe" if os.name == "nt" else "paint")
        result = subprocess.run([
            compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2",
            str(ROOT / "pmkb_store_page.c"), str(ROOT / "pmkb_store_paint.c"),
            str(ROOT / "test_store_paint.c"), "-o", str(cls.binary)
        ], text=True, capture_output=True, timeout=30, check=False)
        if result.returncode:
            raise AssertionError("C11 compilation failed:\n" + result.stdout + result.stderr)

    def test_surface_contract_callbacks(self):
        run = subprocess.run([str(self.binary)], capture_output=True,
                             text=True, timeout=10, check=False)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertRegex(run.stdout, r"PMKB STORE PAINT: \d+ assertions PASS, 0 FAIL")

    def test_no_ui_link_required(self):
        """The mocked surface implements PR #30 signatures without importing its tree."""
        code = (ROOT / "pmkb_store_paint.c").read_text(encoding="utf-8")
        self.assertNotIn("pmkb_surface_present", code)
        self.assertNotIn("pmkb_app_host_launch", code)
        self.assertNotIn("malloc(", code)
        self.assertNotIn("system(", code)


if __name__ == "__main__":
    unittest.main()
