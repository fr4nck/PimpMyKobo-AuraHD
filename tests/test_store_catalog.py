"""Read-only synthetic catalog tests; no external files or Kobo partitions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "experimental/store-v0"
sys.path.insert(0, str(ROOT))
from catalog_contract import CatalogError, read_catalog
from install_contract import MARKER_CONTENT, MARKER_NAME

BASE = {"manifest_version": 1, "id": "org.pmkb.demo", "name": "Demo",
        "version": "0.1.0", "target": "dragon", "runtime": "pmkb-ui-v0",
        "entrypoint": "bin/demo", "dependencies": [], "network": False}


class SyntheticCatalogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pmkb-catalog-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / MARKER_NAME).write_bytes(MARKER_CONTENT)
        user_data = self.root / "data" / "org.pmkb.demo"
        user_data.mkdir(parents=True)
        (user_data / "notes.txt").write_text("KEEP", encoding="utf-8")
        self.note = user_data / "notes.txt"

    def add_app(self, app_id="org.pmkb.demo", **changes):
        app = self.root / "apps" / app_id
        app.mkdir(parents=True)
        document = dict(BASE, id=app_id, **changes)
        (app / "manifest.json").write_text(json.dumps(document), encoding="utf-8")
        entry = app / "bin" / "demo"
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_bytes(b"program contents (never executed)")
        return app

    def kept(self):
        self.assertEqual("KEEP", self.note.read_text(encoding="utf-8"))

    def test_no_apps_and_read_only(self):
        self.assertEqual({"scope": "synthetic_read_only", "installed": (),
                          "cleanup_pending": ()}, read_catalog(self.root))
        self.assertFalse((self.root / "apps").exists())
        self.kept()

    def test_one_app_metadata_only(self):
        app = self.add_app()
        result = read_catalog(self.root)
        self.assertEqual(({"id": "org.pmkb.demo", "name": "Demo",
                           "version": "0.1.0", "entrypoint": "bin/demo",
                           "network_declared": False,
                           "state": "installed_unverified"},), result["installed"])
        self.assertEqual((), result["cleanup_pending"])
        self.assertTrue(app.exists())
        self.kept()

    def test_multiple_sorted_apps_and_dependencies(self):
        self.add_app("org.pmkb.zebra", dependencies=["org.pmkb.alpha"])
        self.add_app("org.pmkb.alpha")
        self.assertEqual(["org.pmkb.alpha", "org.pmkb.zebra"],
                         [app["id"] for app in read_catalog(self.root)["installed"]])
        self.kept()

    def test_network_flag_is_declarative_only(self):
        self.add_app(network=True)
        with patch("subprocess.run", side_effect=AssertionError("command")):
            result = read_catalog(self.root)
        self.assertIs(result["installed"][0]["network_declared"], True)
        self.kept()

    def test_cleanup_pending_is_separate_and_non_destructive(self):
        self.add_app()
        pending = self.root / "apps" / ".pmkb-remove-interrupted"
        pending.mkdir()
        (pending / "remnant").write_text("DO NOT REMOVE", encoding="utf-8")
        result = read_catalog(self.root)
        self.assertEqual((pending.name,), result["cleanup_pending"])
        self.assertEqual("org.pmkb.demo", result["installed"][0]["id"])
        self.assertEqual("DO NOT REMOVE", (pending / "remnant").read_text())
        self.kept()

    def test_staging_directory_is_not_reported_installed(self):
        self.add_app()
        (self.root / "apps" / ".pmkb-stage-interrupted").mkdir()
        with self.assertRaisesRegex(CatalogError, "installation_incomplete"):
            read_catalog(self.root)
        self.kept()

    def test_unexpected_app_name_and_file_are_rejected(self):
        for name, directory in (("invalid", True), ("note.txt", False)):
            with self.subTest(name=name):
                path = self.root / "apps" / name
                path.parent.mkdir(exist_ok=True)
                if directory:
                    path.mkdir()
                else:
                    path.write_text("not app")
                with self.assertRaises(CatalogError):
                    read_catalog(self.root)
                if directory:
                    path.rmdir()
                else:
                    path.unlink()
        self.kept()

    def test_invalid_or_mismatched_manifest_refused(self):
        app = self.add_app()
        (app / "manifest.json").write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(CatalogError, "invalid_installed_manifest"):
            read_catalog(self.root)
        doc = dict(BASE, id="org.pmkb.another")
        (app / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(CatalogError, "installed_id_mismatch"):
            read_catalog(self.root)
        self.kept()

    def test_missing_dependency_cannot_be_misrepresented_installed(self):
        self.add_app(dependencies=["org.pmkb.missing"])
        with self.assertRaisesRegex(CatalogError, "invalid_installed_manifest"):
            read_catalog(self.root)
        self.kept()

    def test_invalid_entrypoint_missing_or_empty(self):
        app = self.add_app()
        (app / "bin" / "demo").unlink()
        with self.assertRaisesRegex(CatalogError, "invalid_installed_entrypoint"):
            read_catalog(self.root)
        (app / "bin" / "demo").write_bytes(b"")
        with self.assertRaisesRegex(CatalogError, "invalid_installed_entrypoint"):
            read_catalog(self.root)
        self.kept()

    def test_bounded_app_count(self):
        # 65 valid dirs exceed the frugal 64-app catalogue budget.
        for i in range(65):
            (self.root / "apps" / ("org.pmkb.app%03d" % i)).mkdir(parents=True)
        with self.assertRaisesRegex(CatalogError, "too_many_installed_apps"):
            read_catalog(self.root)
        self.kept()

    def test_unreadable_apps_reports_failure(self):
        (self.root / "apps").mkdir()
        real_scan = os.scandir
        def fails_for_apps(path):
            if Path(path) == self.root / "apps":
                raise OSError("fixture")
            return real_scan(path)
        with patch("catalog_contract.os.scandir", side_effect=fails_for_apps):
            with self.assertRaisesRegex(ValueError, "unreadable"):
                read_catalog(self.root)
        self.kept()

    def test_invalid_root_marker_refused(self):
        (self.root / MARKER_NAME).unlink()
        with self.assertRaisesRegex(ValueError, "test_root_required"):
            read_catalog(self.root)
        self.kept()

    @unittest.skipIf(os.name == "nt", "unprivileged Windows symlink restricted")
    def test_app_and_manifest_symlinks_refused(self):
        apps = self.root / "apps"
        apps.mkdir()
        foreign = self.root / "somewhere"
        foreign.mkdir()
        (apps / "org.pmkb.demo").symlink_to(foreign, target_is_directory=True)
        with self.assertRaisesRegex(CatalogError, "unsafe_catalog_entry"):
            read_catalog(self.root)
        (apps / "org.pmkb.demo").unlink()
        app = self.add_app()
        (app / "manifest.json").unlink()
        (app / "manifest.json").symlink_to(self.note)
        with self.assertRaisesRegex(CatalogError, "invalid_installed_manifest"):
            read_catalog(self.root)
        self.kept()

    @unittest.skipIf(os.name == "nt", "unprivileged Windows symlink restricted")
    def test_symlink_entrypoint_parent_refused(self):
        app = self.add_app()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "demo").write_bytes(b"X")
        (app / "bin" / "demo").unlink()
        (app / "bin").rmdir()
        (app / "bin").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(CatalogError, "invalid_installed_entrypoint"):
            read_catalog(self.root)
        self.kept()

    @unittest.skipIf(os.name == "nt", "unprivileged Windows symlink restricted")
    def test_apps_or_data_symlink_refused(self):
        (self.root / "apps").symlink_to(self.root / "data", target_is_directory=True)
        with self.assertRaisesRegex(CatalogError, "unsafe_catalog_root"):
            read_catalog(self.root)
        (self.root / "apps").unlink()
        (self.root / "data").rename(self.root / "saved_data")
        (self.root / "data").symlink_to(self.root / "saved_data", target_is_directory=True)
        with self.assertRaisesRegex(CatalogError, "unsafe_catalog_root"):
            read_catalog(self.root)
        self.assertEqual("KEEP", (self.root / "saved_data" / "org.pmkb.demo" / "notes.txt").read_text())


if __name__ == "__main__":
    unittest.main()
