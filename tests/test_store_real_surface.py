"""D4b: same-repository, shallow SHA-pinned PR #30 real-surface CI test.

Only GitHub Actions Python 3.11. No full clone, third-party libraries,
firmware, local computer or Kobo access. Two sources are Git-hash checked.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
NATIVE = REPO / "experimental/store-v0/native"
REV = "e2907a19920100ef2a32ec6587e724ccb5116bc7"
SOURCE_HASHES = {
    "pmkb_ui.h": "1adcc6656007183c6eee23da4c76d9f3eff3c12d",
    "pmkb_surface.c": "946c1d90e9c8c9feca54f36678959323327806b4",
    "pmkb_backend.c": "cc1f227d32021582f65c386f9804af2b8c8cc33d",
    "pmkb_launcher_bridge.h": "74e6339b87b205029c5a6917ddf27cfe08b2695c",
    "pmkb_launcher_bridge.c": "92f26693efc1d67743d1b8816812c37f14d3003c",
    "pmkb_calculator_ui.h": "8dcb297446516c016fc090d3440cede7853f47a3",
    "pmkb_calculator.h": "2a9c03c1fa29c427b8e69f25da5503deea84fe8d",
}


def git_hash(data):
    return hashlib.sha1(("blob %d\0" % len(data)).encode("ascii") + data).hexdigest()


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true" and sys.version_info[:2] == (3, 11),
    "real PR30 cross-branch qualification: Actions Python 3.11 only",
)
class RealSurfaceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = next((shutil.which(x) for x in ("cc", "gcc", "clang")
                         if shutil.which(x)), None)
        if not compiler:
            raise unittest.SkipTest("host C11 compiler missing, no native PASS")
        temporary = tempfile.TemporaryDirectory(prefix="pmkb-real-surface-")
        cls.addClassCleanup(temporary.cleanup)
        root = Path(temporary.name)
        ui = root / "native-ui"
        ui.mkdir()
        fetched = subprocess.run(
            ["git", "-c", "protocol.version=2", "fetch", "--no-tags",
             "--depth=1", "--filter=blob:none", "origin", REV],
            cwd=REPO, capture_output=True, text=True, timeout=45, check=False)
        if fetched.returncode:
            raise AssertionError("pinned PR30 shallow fetch failed: " + fetched.stderr[-1200:])
        for name, sha in SOURCE_HASHES.items():
            result = subprocess.run(
                ["git", "show", REV + ":experimental/native-ui/" + name],
                cwd=REPO, capture_output=True, timeout=30, check=False)
            if result.returncode or git_hash(result.stdout) != sha:
                raise AssertionError("source unavailable or SHA mismatch: " + name)
            (ui / name).write_bytes(result.stdout)
        cls.executable = root / ("real-store.exe" if os.name == "nt" else "real-store")
        built = subprocess.run([
            compiler, "-std=c11", "-O2", "-Wall", "-Wextra",
            "-Werror", "-pedantic", "-I", str(ui), "-I", str(NATIVE),
            str(ui / "pmkb_surface.c"),
            str(NATIVE / "pmkb_store_page.c"),
            str(NATIVE / "pmkb_store_paint.c"),
            str(NATIVE / "test_store_real_surface.c"),
            "-o", str(cls.executable)],
            capture_output=True, text=True, timeout=45, check=False)
        if built.returncode:
            raise AssertionError("real PMKB-UI build FAILED: " + built.stdout + built.stderr)

        cls.presenter = root / ("store-present.exe" if os.name == "nt"
                                 else "store-present")
        presentation = subprocess.run([
            compiler, "-std=c11", "-O2", "-Wall", "-Wextra",
            "-Werror", "-pedantic", "-I", str(ui), "-I", str(NATIVE),
            str(ui / "pmkb_surface.c"),
            str(ui / "pmkb_backend.c"),
            str(NATIVE / "pmkb_store_page.c"),
            str(NATIVE / "pmkb_store_paint.c"),
            str(NATIVE / "test_store_present_contract.c"),
            "-o", str(cls.presenter)],
            capture_output=True, text=True, timeout=45, check=False)
        if presentation.returncode:
            raise AssertionError("real PMKB backend + Store build FAILED: "
                                 + presentation.stdout + presentation.stderr)

        cls.launcher_executable = root / ("store-launcher.exe" if os.name == "nt"
                                         else "store-launcher")
        launcher = subprocess.run([
            compiler, "-std=c11", "-O2", "-Wall", "-Wextra",
            "-Werror", "-pedantic", "-I", str(ui), "-I", str(NATIVE),
            str(ui / "pmkb_surface.c"),
            str(ui / "pmkb_backend.c"),
            str(ui / "pmkb_launcher_bridge.c"),
            str(NATIVE / "pmkb_store_page.c"),
            str(NATIVE / "pmkb_store_paint.c"),
            str(NATIVE / "test_store_launcher_isolation.c"),
            "-o", str(cls.launcher_executable)],
            capture_output=True, text=True, timeout=45, check=False)
        if launcher.returncode:
            raise AssertionError("real launcher/Store C11 compilation FAILED: "
                                 + launcher.stdout + launcher.stderr)

    def test_real_surface_framebuffer_and_invariants(self):
        outcome = subprocess.run(
            [str(self.executable)], capture_output=True, text=True,
            timeout=30, check=False)
        self.assertEqual(0, outcome.returncode, outcome.stderr)
        print(outcome.stdout.strip())  # native redraw metrics in CI logs
        self.assertRegex(outcome.stdout,
                         r"PMKB REAL UI STORE: \d+ assertions PASS, 0 FAIL")


    def test_real_backend_presentation_and_dirty_rectangles(self):
        outcome = subprocess.run([str(self.presenter)], capture_output=True,
                                 text=True, timeout=30, check=False)
        self.assertEqual(0, outcome.returncode, outcome.stderr)
        print(outcome.stdout.strip())
        self.assertRegex(outcome.stdout,
                         r"PMKB REAL STORE PRESENT: \d+ assertions PASS, 0 FAIL")


    def test_real_launcher_isolation(self):
        """Real Launcher bridge + fake Notes/Calc lifecycle, isolated Store."""
        result = subprocess.run(
            [str(self.launcher_executable)], capture_output=True, text=True,
            timeout=30, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        print(result.stdout.strip())
        self.assertRegex(
            result.stdout,
            r"PMKB REAL LAUNCHER ISOLATION: \d+ assertions PASS, 0 FAIL")


if __name__ == "__main__":
    unittest.main()
