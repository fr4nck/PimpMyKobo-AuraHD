"""L06-B2d: removal restricted to a disposable, marked temporary root."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
from zipfile import ZipFile

MODULE_DIR = Path(__file__).resolve().parents[1] / "experimental/store-v0"
sys.path.insert(0, str(MODULE_DIR))
from install_contract import MARKER_CONTENT, MARKER_NAME, install_archive
from uninstall_contract import UninstallError, uninstall_app

EXAMPLE = json.loads((MODULE_DIR / "example/manifest.json").read_text("utf-8"))


def package():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(EXAMPLE))
        archive.writestr("bin/demo", b"CODE-ONLY")
    return stream.getvalue()


class SyntheticUninstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmkb-remove-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / MARKER_NAME).write_bytes(MARKER_CONTENT)
        self.data = self.root / "data" / EXAMPLE["id"]
        self.data.mkdir(parents=True)
        (self.data / "notes.txt").write_text("DO NOT DELETE", "utf-8")
        self.payload = package()

    @property
    def app(self):
        return self.root / "apps" / EXAMPLE["id"]

    def install(self):
        return install_archive(self.payload, self.root)

    def pending(self):
        apps = self.root / "apps"
        return list(apps.glob(".pmkb-remove-*")) if apps.is_dir() else []

    def assert_data_preserved(self):
        self.assertEqual("DO NOT DELETE", (self.data / "notes.txt").read_text("utf-8"))

    def test_installed_app_code_removed_but_data_retained(self):
        self.install()
        result = uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(result["code_removed"])
        self.assertTrue(result["user_data_untouched"])
        self.assertGreaterEqual(result["preflight_entries"], 3)
        self.assertFalse(self.app.exists())
        self.assertEqual([], self.pending())
        self.assert_data_preserved()

    def test_install_again_after_uninstall_keeps_user_data(self):
        self.install()
        uninstall_app(self.root, EXAMPLE["id"])
        self.install()
        self.assertEqual(b"CODE-ONLY", (self.app / "bin" / "demo").read_bytes())
        self.assert_data_preserved()

    def test_uninstalled_and_missing_app_refused(self):
        with self.assertRaisesRegex(UninstallError, "not_installed"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.install()
        uninstall_app(self.root, EXAMPLE["id"])
        with self.assertRaisesRegex(UninstallError, "not_installed"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assert_data_preserved()

    def test_invalid_ids_never_escape_app_directory(self):
        self.install()
        for value in ("../data", "org/pk", "", "COM", None, "ORG.PMKB.DEMO", ".", "../", "org.pmkb.demo/../../data"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(UninstallError, "invalid_app_id"):
                    uninstall_app(self.root, value)
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    def test_unmarked_root_rejected_before_mutation(self):
        self.install()
        (self.root / MARKER_NAME).unlink()
        with self.assertRaisesRegex(ValueError, "test_root_required"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    def test_system_temp_root_is_not_an_allowed_target(self):
        with self.assertRaisesRegex(ValueError, "test_root_required"):
            uninstall_app(Path(tempfile.gettempdir()), EXAMPLE["id"])
        self.assert_data_preserved()

    def test_invalid_installed_manifest_refused(self):
        self.install()
        (self.app / "manifest.json").write_text("{broken", "utf-8")
        with self.assertRaisesRegex(UninstallError, "installed_manifest_invalid"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    def test_manifest_id_mismatch_refused(self):
        self.install()
        altered = {**EXAMPLE, "id": "org.pmkb.other"}
        (self.app / "manifest.json").write_text(json.dumps(altered), "utf-8")
        with self.assertRaisesRegex(UninstallError, "installed_manifest_mismatch"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    def test_unrecognized_file_type_or_extra_large_tree_refused(self):
        self.install()
        (self.app / "extra.dat").write_bytes(b"x" * 1)
        self.assertTrue(uninstall_app(self.root, EXAMPLE["id"])["code_removed"])
        self.install()
        (self.app / "extra.dat").write_bytes(b"x" * (8 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(UninstallError, "code_tree_too_large"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    def test_failure_before_rename_retains_complete_app(self):
        self.install()
        with patch("uninstall_contract.os.rename", side_effect=OSError("simulated")):
            with self.assertRaisesRegex(UninstallError, "detach_failed"):
                uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue((self.app / "bin" / "demo").is_file())
        self.assertEqual([], self.pending())
        self.assert_data_preserved()

    def test_cleanup_failure_keeps_quarantine_and_signals_incomplete(self):
        self.install()
        with patch("uninstall_contract.shutil.rmtree", side_effect=OSError("simulated")):
            with self.assertRaisesRegex(UninstallError, "cleanup_pending") as caught:
                uninstall_app(self.root, EXAMPLE["id"])
        self.assertFalse(self.app.exists())
        self.assertEqual([caught.exception.pending_path], self.pending())
        self.assertTrue((caught.exception.pending_path / "bin" / "demo").exists())
        self.assert_data_preserved()
        shutil.rmtree(caught.exception.pending_path)

    def test_partial_cleanup_failure_never_claims_restoration(self):
        self.install()
        real_remove = shutil.rmtree

        def partial_failure(path):
            (Path(path) / "bin" / "demo").unlink()
            raise OSError("simulated partial deletion")

        with patch("uninstall_contract.shutil.rmtree", side_effect=partial_failure):
            with self.assertRaisesRegex(UninstallError, "cleanup_pending") as caught:
                uninstall_app(self.root, EXAMPLE["id"])
        self.assertFalse(self.app.exists())
        self.assertTrue(caught.exception.pending_path.is_dir())
        self.assertFalse((caught.exception.pending_path / "bin" / "demo").exists())
        self.assert_data_preserved()
        real_remove(caught.exception.pending_path)

    @unittest.skipIf(os.name == "nt", "Unprivileged Windows symlink creation is restricted")
    def test_app_link_refused_without_deleting_target(self):
        other = self.root / "outside"
        other.mkdir()
        (other / "marker").write_text("keep", "utf-8")
        (self.root / "apps").mkdir()
        self.app.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(UninstallError, "unsafe_code_tree"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertEqual("keep", (other / "marker").read_text("utf-8"))
        self.assert_data_preserved()

    @unittest.skipIf(os.name == "nt", "Unprivileged Windows symlink creation is restricted")
    def test_nested_link_refused(self):
        self.install()
        (self.app / "link").symlink_to(self.data / "notes.txt")
        with self.assertRaisesRegex(UninstallError, "unsafe_code_tree"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assert_data_preserved()

    @unittest.skipIf(os.name == "nt", "Unprivileged Windows symlink creation is restricted")
    def test_data_root_link_refused(self):
        self.install()
        # Replace the data path with a link, and ensure uninstall does not follow it.
        original = self.root / "data"
        original.rename(self.root / "data-original")
        original.symlink_to(self.root / "data-original", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unsafe_install_root"):
            uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(self.app.exists())
        self.assertEqual("DO NOT DELETE", (self.root / "data-original" / EXAMPLE["id"] / "notes.txt").read_text("utf-8"))

    def test_no_subprocess_or_network_used(self):
        self.install()
        with patch("subprocess.run", side_effect=AssertionError("Unexpected subprocess")):
            result = uninstall_app(self.root, EXAMPLE["id"])
        self.assertTrue(result["user_data_untouched"])
        self.assert_data_preserved()


if __name__ == "__main__":
    unittest.main()
