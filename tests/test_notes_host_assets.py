"""PMKB Notes: host-only UI contract and safety guardrails (no browser dependency)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "experimental" / "notes-v01"

class TestNotesHostAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (APP / "index.html").read_text(encoding="utf-8")
        cls.browser = (APP / "notes-app.js").read_text(encoding="utf-8")
        cls.core = (APP / "notes-core.js").read_text(encoding="utf-8")

    def test_standalone_ui_has_editing_and_optional_sketch(self):
        for marker in (
            'src="notes-core.js"', 'src="notes-app.js"',
            'id="note-title"', 'id="note-text"', 'id="note-list"',
            'id="tab-text"', 'id="tab-sketch"', 'id="sketch"',
            'data-tool="pen"', 'data-tool="eraser"', 'data-width="2"',
            'data-width="5"', 'data-width="11"',
            'id="undo"', 'id="redo"', 'id="clear-sketch"',
            'id="export-txt"', 'id="export-json"', 'id="export-png"',
            'id="import-file"', 'id="new-note"', 'id="delete-note"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.html)
        self.assertIn("touch-action:none", self.html)

    def test_v02_distraction_free_drawer_and_typography(self):
        for marker in (
            'id="notes-drawer"', 'id="drawer-backdrop"',
            'id="open-notes"', 'aria-expanded="false"',
            'id="close-drawer"', 'id="toolbar-new"',
            'id="font-options"', 'id="font-family"',
            'id="font-size"', 'id="font-lineheight"',
            'id="font-file"', 'id="import-font"',
            'id="sketch-tools"', 'class="more-actions"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.html)
        self.assertIn('nav id="notes-drawer" aria-label="Mes notes" hidden', self.html)
        self.assertIn('function toggleDrawer(open)', self.browser)
        self.assertIn('function applyTypography()', self.browser)
        self.assertIn('function changeTypography()', self.browser)
        self.assertIn('new FontFace(family,bytes)', self.browser)
        self.assertIn('window.crypto.subtle.digest("SHA-256",bytes)', self.browser)
        self.assertIn('fontSignature(new Uint8Array(bytes))!==ext', self.browser)
        self.assertIn('file.size>2000000', self.browser)
        self.assertIn('loadedFonts=new Map()', self.browser)
        self.assertIn('refs.text.style.fontFamily=', self.browser)
        self.assertIn('function typography(value)', self.core)
        self.assertNotIn('localStorage.setItem("font-', self.browser)
        self.assertNotIn('indexedDB', self.browser)

    def test_no_external_code_or_network_transport(self):
        for value in (
            "http://", "https://", "<iframe", "<link rel=\"stylesheet\"",
            "serviceWorker", "WebSocket(", "XMLHttpRequest(",
            "navigator.sendBeacon", "eval(", "innerHTML",
        ):
            with self.subTest(value=value):
                self.assertNotIn(value, self.html + self.core + self.browser)
        self.assertNotIn(".fetch(", self.browser)
        self.assertNotIn("window.fetch(", self.browser)
        self.assertNotIn("pmkb-reader", self.core + self.browser)
        self.assertNotIn("/dev/", self.core + self.browser)

    def test_only_browser_local_saving_with_explicit_backup(self):
        self.assertIn("localStorage.getItem(STORAGE)", self.browser)
        self.assertIn("localStorage.setItem(STORAGE,value)", self.browser)
        self.assertIn('download("PMKB-Notes-sauvegarde.json"', self.browser)
        self.assertIn("C.decode(await file.text())", self.browser)
        self.assertIn("window.confirm(", self.browser)
        self.assertIn("book=C.upsert(book,note)", self.browser)
        self.assertIn('refs.canvas.addEventListener("pointerdown",down)', self.browser)
        self.assertIn("AUCUN ACCÈS KOBO", self.html)

if __name__ == "__main__":
    unittest.main()
