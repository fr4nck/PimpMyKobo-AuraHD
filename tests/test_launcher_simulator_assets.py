"""Host-only V0.4 visual provenance tests; Python stdlib only."""
import hashlib
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "experimental" / "launcher-v0" / "assets" / "v02"
SIM = ROOT / "experimental" / "launcher-v0"


def png_header(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"Invalid PNG: {path}")
    width, height, depth, color = struct.unpack(">IIBB", data[16:26])
    return data, (width, height, depth, color)


class ArtIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ASSETS / "MANIFEST-validated.json").read_text())

    def test_original_bytes_unchanged(self):
        original = self.manifest["original"]
        path = ASSETS / "source" / original["filename"]
        data, header = png_header(path)
        self.assertEqual(len(data), original["size_bytes"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), original["sha256"])
        self.assertEqual(header[:2], tuple(original["dimensions"]))

    def test_approved_png_palette_and_hashes(self):
        for item in self.manifest["assets"]:
            with self.subTest(item=item["file"]):
                path = ASSETS / "optimise" / item["file"]
                data, header = png_header(path)
                self.assertEqual(len(data), item["size_bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
                self.assertEqual(header, (
                    *item["dimensions"],item["png_bit_depth"],item["png_color_type"]
                ))
        default = (ASSETS / "optimise" / "PMKB-V0.2-16gris.png").read_bytes()
        self.assertEqual(len(default), 250757)

    def test_local_preview_uses_exact_original_asset(self):
        html = (SIM / "simulator.html").read_text(encoding="utf-8")
        script = (SIM / "simulator.js").read_text(encoding="utf-8")
        self.assertIn('src="assets/v02/optimise/PMKB-V0.2-16gris.png"', html)
        self.assertIn('src="simulator.js"', html)
        self.assertIn('id="dynamic-status"', html)
        self.assertIn('id="dock-shortcuts"', html)
        self.assertIn('id="system-controls"', html)
        self.assertIn('id="dock-picks"', html)
        self.assertIn('class="tile-skin"', script)
        self.assertIn('function needsInversion(', script)
        self.assertIn('function renderDock()', script)
        self.assertIn('function dockChoice(', script)
        self.assertIn("SIMULATION PC", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("serviceWorker", script)


if __name__ == "__main__":
    unittest.main()
