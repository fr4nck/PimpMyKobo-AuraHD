"""L06-B2e: synthetic read-only inspection; never purge a pending removal."""
import json
import os
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

MODULE_DIR = Path(__file__).resolve().parents[1] / "experimental/store-v0"
sys.path.insert(0, str(MODULE_DIR))
from install_contract import MARKER_CONTENT, MARKER_NAME, install_archive
from uninstall_contract import UninstallError, uninstall_app
from pending_cleanup_contract import pending_removals

EXAMPLE = json.loads((MODULE_DIR / "example/manifest.json").read_text("utf-8"))


def package():
    output = BytesIO()
    with ZipFile(output, "w") as zipfile:
        zipfile.writestr("manifest.json", json.dumps(EXAMPLE))
        zipfile.writestr("bin/demo", b"DEMO")
    return output.getvalue()


class PendingCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmkb-cleanup-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / MARKER_NAME).write_bytes(MARKER_CONTENT)
        self.data = self.root / "data" / EXAMPLE["id"]
        self.data.mkdir(parents=True)
        (self.data / "notes.txt").write_text("PRESERVE", encoding="utf-8")
        self.payload = package()

    def assert_preserved(self):
        self.assertEqual(
            "PRESERVE", (self.data / "notes.txt").read_text(encoding="utf-8"))

    def test_without_apps_directory_returns_empty(self):
        self.assertEqual((), pending_removals(self.root))
        self.assertFalse((self.root / "apps").exists())
        self.assert_preserved()

    def test_ordinary_installed_application_is_not_pending(self):
        install_archive(self.payload, self.root)
        self.assertEqual((), pending_removals(self.root))
        self.assertTrue((self.root / "apps" / EXAMPLE["id"]).is_dir())
        self.assert_preserved()

    def test_failed_purge_remains_visible_without_cleanup(self):
        install_archive(self.payload, self.root)
        with patch("uninstall_contract.shutil.rmtree",
                   side_effect=OSError("simulated failure")):
            with self.assertRaisesRegex(UninstallError, "cleanup_pending") as caught:
                uninstall_app(self.root, EXAMPLE["id"])
        quarantine = caught.exception.pending_path
        with patch("uninstall_contract.shutil.rmtree",
                   side_effect=AssertionError("inventory attempted removal")):
            self.assertEqual((quarantine.name,), pending_removals(self.root))
        self.assertTrue((quarantine / "bin" / "demo").is_file())
        self.assert_preserved()

    def test_partial_purge_is_reported_not_mistaken_for_success(self):
        install_archive(self.payload, self.root)

        def partial_delete(folder):
            (Path(folder) / "bin" / "demo").unlink()
            raise OSError("partial cleanup")

        with patch("uninstall_contract.shutil.rmtree",
                   side_effect=partial_delete):
            with self.assertRaisesRegex(UninstallError, "cleanup_pending") as caught:
                uninstall_app(self.root, EXAMPLE["id"])
        self.assertEqual((caught.exception.pending_path.name,),
                         pending_removals(self.root))
        self.assertFalse((caught.exception.pending_path / "bin" / "demo").exists())
        self.assert_preserved()

    def test_multiple_quarantines_sorted_and_unrelated_entries_ignored(self):
        apps = self.root / "apps"
        apps.mkdir()
        (apps / ".pmkb-remove-z").mkdir()
        (apps / ".pmkb-remove-a").mkdir()
        (apps / ".pmkb-stage-unrelated").mkdir()
        (apps / "other.app").mkdir()
        self.assertEqual((".pmkb-remove-a", ".pmkb-remove-z"),
                         pending_removals(self.root))
        self.assertTrue((apps / ".pmkb-stage-unrelated").is_dir())
        self.assert_preserved()

    def test_matching_regular_file_is_refused_without_deletion(self):
        apps = self.root / "apps"
        apps.mkdir()
        suspicious = apps / ".pmkb-remove-file"
        suspicious.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(UninstallError, "unsafe_pending_entry"):
            pending_removals(self.root)
        self.assertEqual("keep", suspicious.read_text(encoding="utf-8"))
        self.assert_preserved()

    def test_invalid_test_root_is_refused(self):
        (self.root / MARKER_NAME).unlink()
        with self.assertRaisesRegex(ValueError, "test_root_required"):
            pending_removals(self.root)
        self.assert_preserved()

    def test_inventory_is_bounded(self):
        apps = self.root / "apps"
        apps.mkdir()
        for number in range(513):
            (apps / ("unrelated-%03d" % number)).mkdir()
        with self.assertRaisesRegex(UninstallError,
                                    "pending_inventory_too_large"):
            pending_removals(self.root)
        self.assert_preserved()

    def test_unreadable_directory_is_not_silent(self):
        (self.root / "apps").mkdir()
        with patch("pending_cleanup_contract.os.scandir",
                   side_effect=OSError("read error")):
            with self.assertRaisesRegex(UninstallError,
                                        "pending_inventory_unreadable"):
                pending_removals(self.root)
        self.assert_preserved()

    @unittest.skipIf(os.name == "nt", "Windows unprivileged symlinks unavailable")
    def test_matching_symlink_is_refused_without_following(self):
        apps = self.root / "apps"
        apps.mkdir()
        (apps / ".pmkb-remove-linked").symlink_to(
            self.data, target_is_directory=True)
        with self.assertRaisesRegex(UninstallError, "unsafe_pending_entry"):
            pending_removals(self.root)
        self.assert_preserved()

    @unittest.skipIf(os.name == "nt", "Windows unprivileged symlinks unavailable")
    def test_apps_symlink_is_refused(self):
        (self.root / "apps").symlink_to(
            self.root / "data", target_is_directory=True)
        with self.assertRaisesRegex(UninstallError, "unsafe_install_root"):
            pending_removals(self.root)
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
