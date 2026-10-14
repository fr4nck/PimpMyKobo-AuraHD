"""PMKB Notes: host-only UI contract and safety guardrails (no browser dependency)."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "experimental" / "notes-v01"

class NotesStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.nodes = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = {"tag": tag, "attrs": attrs, "ancestors": list(self.stack)}
        if "id" in attrs:
            self.nodes[attrs["id"]] = node
        if tag not in {"input", "meta", "link", "br", "img"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()

class TestNotesHostAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (APP / "index.html").read_text(encoding="utf-8")
        cls.browser = (APP / "notes-app.js").read_text(encoding="utf-8")
        cls.core = (APP / "notes-core.js").read_text(encoding="utf-8")

    def test_normative_notes_density_and_feedback_placement(self):
        nodes = NotesStructure(self.html).nodes
        save = nodes["save-now"]
        status = nodes["save-status"]
        self.assertIs(save["ancestors"][-1], status["ancestors"][-1])
        self.assertEqual(save["ancestors"][-1]["attrs"]["class"], "save-control")
        self.assertEqual(status["tag"], "span")
        self.assertEqual(status["attrs"]["role"], "status")
        self.assertIn("hidden", status["attrs"])
        self.assertNotIn("Notes locales chargées", self.browser)
        self.assertEqual(save["attrs"]["aria-describedby"], "save-status")
        error = nodes["notes-error"]["attrs"]
        self.assertIn("hidden", error)
        self.assertEqual(error["role"], "alert")
        for name in ("backup-reminder", "backup-result", "export-json", "import-button"):
            with self.subTest(name=name):
                self.assertTrue(any(n["attrs"].get("id") == "notes-drawer"
                                    for n in nodes[name]["ancestors"]))
        self.assertNotIn("Enregistré dans ce navigateur · exporter pour sauvegarder", self.browser)
        self.assertIn("--field-number:7ch", self.html)
        self.assertIn("--field-font:22ch", self.html)
        self.assertIn("select:focus-visible", self.html)

    def test_ux_rule_and_ci_are_durable(self):
        policy = (ROOT / "docs" / "notes-ux-policy.md").read_text(encoding="utf-8")
        self.assertIn("ADR-005-formulaires-densite-informationnelle.md", policy)
        self.assertIn("docs/notes-ux-policy.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        ci = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("tests/test_notes_app.cjs", ci)
        self.assertIn("feat/pmkb-notes-v02-typography-drawer", ci)

    def test_entire_editor_header_is_limited_to_two_rows(self):
        nodes = NotesStructure(self.html).nodes
        title_parent = nodes["note-title"]["ancestors"][-1]
        self.assertIn(title_parent, nodes["tab-text"]["ancestors"])
        self.assertIn(title_parent, nodes["tab-sketch"]["ancestors"])
        self.assertIn(title_parent, nodes["export-txt"]["ancestors"])
        self.assertIn(title_parent, nodes["export-png"]["ancestors"])
        self.assertIn("hidden", nodes["export-png"]["attrs"])
        self.assertNotIn("<header>", self.html)
        self.assertIn("flex-wrap:nowrap", self.html)
        self.assertTrue(any(n["attrs"].get("id") == "more-menu"
                            for n in nodes["sketch-tools"]["ancestors"]))
        self.assertEqual(nodes["toolbar-new"]["attrs"]["aria-label"], "Nouvelle note")
        self.assertEqual(nodes["open-notes"]["attrs"]["aria-label"], "Mes notes")
        self.assertTrue(any(n["attrs"].get("id") == "more-menu"
                            for n in nodes["quit-notes"]["ancestors"]))
        self.assertIn('.save-control:has(#save-status:not([hidden]))', self.html)

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
            'id="font-size"', 'id="open-fonts"',
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
        self.assertIn('id="font-options" class="type-panel"', self.html)
        self.assertIn('aria-controls="font-options" aria-expanded="false"', self.html)
        self.assertIn('id="font-size" type="number" min="12" max="36"', self.html)
        self.assertIn('class="type-controls"', self.html)
        self.assertIn('function toggleTypography(open)', self.browser)
        self.assertIn('fontPanel.hidden=!open', self.browser)
        self.assertIn('lineHeight:C.typography(item.typography).lineHeight', self.browser)
        self.assertIn("mise en forme d'un passage", self.html)
        self.assertNotIn('id="font-lineheight"', self.html)
        self.assertNotIn('class="type-grid"', self.html)
        self.assertNotIn('fontLineheight.addEventListener', self.browser)
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
