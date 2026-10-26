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

    def test_synthetic_touch_dispatcher(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-touch-") as d:
            binary = Path(d) / ("whiteboard-touch.exe" if os.name == "nt"
                                else "whiteboard-touch")
            native = ROOT / "experimental" / "native-ui"
            result = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(ROOT / "tests" / "whiteboard_touch_tests.c"),
                 "-o", str(binary)],
                capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outcome = subprocess.run([str(binary)], capture_output=True,
                                     text=True, timeout=10, check=False)
            self.assertEqual(outcome.returncode, 0, outcome.stdout + outcome.stderr)
            self.assertRegex(outcome.stdout,
                             r"WHITEBOARD TOUCH: \d+ assertions PASS, 0 FAIL")

    def test_streaming_chunks_keep_continuity(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-stream-") as d:
            binary = Path(d) / ("whiteboard-stream.exe" if os.name == "nt"
                                else "whiteboard-stream")
            native = ROOT / "experimental" / "native-ui"
            result = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(ROOT / "tests" / "whiteboard_stream_tests.c"),
                 "-o", str(binary)],
                capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outcome = subprocess.run([str(binary)], capture_output=True,
                                     text=True, timeout=10, check=False)
            self.assertEqual(outcome.returncode, 0, outcome.stdout + outcome.stderr)
            self.assertRegex(outcome.stdout,
                             r"WHITEBOARD STREAM: \d+ assertions PASS, 0 FAIL")

    def test_pixels_match_journal_after_interruption(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-coherence-") as d:
            binary = Path(d) / ("whiteboard-coherence.exe" if os.name == "nt"
                                else "whiteboard-coherence")
            native = ROOT / "experimental" / "native-ui"
            build = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(ROOT / "tests" / "whiteboard_coherence_tests.c"),
                 "-o", str(binary)], capture_output=True,
                text=True, timeout=45, check=False)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            outcome = subprocess.run([str(binary)], capture_output=True,
                                     text=True, timeout=10, check=False)
            self.assertEqual(outcome.returncode, 0, outcome.stdout + outcome.stderr)
            self.assertRegex(outcome.stdout,
                             r"WHITEBOARD COHERENCE: \d+ assertions PASS, 0 FAIL")

    def test_demo_pgm_is_deterministic(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-demo-") as d:
            binary = Path(d) / ("wb-demo.exe" if os.name == "nt" else "wb-demo")
            native = ROOT / "experimental" / "native-ui"
            build = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(HEADER / "whiteboard_host_demo.c"), "-o", str(binary)],
                capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            first = subprocess.run([str(binary)], capture_output=True,
                                   timeout=10, check=False)
            second = subprocess.run([str(binary)], capture_output=True,
                                    timeout=10, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            header = b"P5\n320 480\n255\n"
            self.assertTrue(first.stdout.startswith(header))
            pixels = first.stdout[len(header):]
            self.assertEqual(len(pixels), 320 * 480)
            self.assertEqual(pixels[20 * 320 + 20], 0)
            self.assertEqual(pixels[130 * 320 + 120], 0)
            self.assertEqual(pixels[150 * 320 + 100], 136)
            self.assertEqual(pixels[400 * 320 + 300], 255)

    def test_launcher_ready_app_lifecycle(self):
        compiler = next((shutil.which(name) for name in ("cc", "gcc", "clang")
                         if shutil.which(name)), None)
        with tempfile.TemporaryDirectory(prefix="pmkb-whiteboard-app-") as d:
            binary = Path(d) / ("whiteboard-app.exe" if os.name == "nt" else "whiteboard-app")
            native = ROOT / "experimental" / "native-ui"
            built = subprocess.run(
                [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-I", str(HEADER), "-I", str(native),
                 str(native / "pmkb_surface.c"),
                 str(ROOT / "tests" / "whiteboard_app_tests.c"),
                 "-o", str(binary)], capture_output=True, text=True,
                timeout=45, check=False)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(binary)], capture_output=True,
                                 text=True, timeout=10, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertRegex(run.stdout, r"WHITEBOARD APP: \d+ assertions PASS, 0 FAIL")

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
