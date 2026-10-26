"""TB0: compile and run the offline C11 whiteboard stroke journal on host.

No firmware, physical media, network, external packages or image artifacts.
GitHub Actions compiles only on Python 3.11 (Linux and Windows) to save CI.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "experimental" / "whiteboard-v0"
SOURCE = ROOT / "tests" / "whiteboard_model_tests.c"


class WhiteboardModelC11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("GITHUB_ACTIONS") == "true" and sys.version_info[:2] != (3, 11):
            raise unittest.SkipTest("single Python version per OS runs this C11 proof")
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        if compiler is None:
            raise unittest.SkipTest("C11 compiler unavailable; no native PASS")
        temporary = tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-")
        cls.addClassCleanup(temporary.cleanup)
        cls.binary = Path(temporary.name) / ("whiteboard.exe" if os.name == "nt"
                                             else "whiteboard")
        built = subprocess.run(
            [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-pedantic", "-I", str(HEADER), str(SOURCE),
             "-o", str(cls.binary)],
            capture_output=True, text=True, timeout=45, check=False,
        )
        if built.returncode != 0:
            raise AssertionError("whiteboard C11 build FAILED:\n"
                                 + built.stdout + built.stderr)

    def test_host_render_and_dirty_rectangles(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-render-") as d:
            binary = Path(d) / ("whiteboard-render.exe" if os.name == "nt"
                                else "whiteboard-render")
            native = ROOT / "experimental" / "native-ui"
            result = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(ROOT / "tests" / "whiteboard_render_tests.c"),
                 "-o", str(binary)],
                capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outcome = subprocess.run([str(binary)], capture_output=True,
                                     text=True, timeout=10, check=False)
            self.assertEqual(outcome.returncode, 0, outcome.stdout + outcome.stderr)
            self.assertRegex(outcome.stdout,
                             r"WHITEBOARD RENDER: \d+ assertions PASS, 0 FAIL")

    def test_bounded_journal_and_undo_redo(self):
        run = subprocess.run([str(self.binary)], capture_output=True,
                             text=True, timeout=10, check=False)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        match = re.fullmatch(
            r"WHITEBOARD TB0: (\d+) assertions PASS, 0 FAIL", run.stdout.strip()
        )
        self.assertIsNotNone(match, run.stdout)
        self.assertGreaterEqual(int(match.group(1)), 200)


if __name__ == "__main__":
    unittest.main()
