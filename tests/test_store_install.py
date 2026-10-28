"""L06-B2c: install only inside disposable OS temporary directories."""
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

MODULE_DIR = Path(__file__).resolve().parents[1] / "experimental/store-v0"
sys.path.insert(0, str(MODULE_DIR))
from archive_contract import ArchiveError
from manifest_contract import ManifestError
from install_contract import InstallError, MARKER_CONTENT, MARKER_NAME, install_archive

EXAMPLE = json.loads((MODULE_DIR / "example/manifest.json").read_text("utf-8"))


def package(*, manifest=None, files=None, compression=ZIP_STORED):
    doc = EXAMPLE if manifest is None else manifest
    members = [("assets/config.json", b"CONFIG"), ("bin/demo", b"DEMO-PAYLOAD-V1")]
    if files is not None:
        members = files
    output = BytesIO()
    with ZipFile(output, "w", compression=compression) as zf:
        zf.writestr("manifest.json", json.dumps(doc).encode("utf-8"))
        for name, value in members:
            zf.writestr(name, value)
    return output.getvalue()


class StoreInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pmkb-store-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / MARKER_NAME).write_bytes(MARKER_CONTENT)
        (self.root / "data" / "org.pmkb.demo").mkdir(parents=True)
        (self.root / "data" / "org.pmkb.demo" / "notes.txt").write_text("User note", "utf-8")

    def stages(self):
        apps = self.root / "apps"
        return list(apps.glob(".pmkb-stage-*")) if apps.exists() else []

    def assert_no_install(self):
        self.assertFalse((self.root / "apps" / "org.pmkb.demo").exists())
        self.assertEqual([], self.stages())
        self.assertEqual("User note", (self.root / "data" / "org.pmkb.demo" / "notes.txt").read_text("utf-8"))

    def test_install_with_crc_and_sha256_inventory(self):
        payload = package(compression=ZIP_DEFLATED)
        result = install_archive(payload, self.root)
        dest = self.root / "apps" / "org.pmkb.demo"
        self.assertEqual(dest, result["code_directory"])
        self.assertEqual("0.1.0", result["version"])
        self.assertEqual(b"DEMO-PAYLOAD-V1", (dest / "bin" / "demo").read_bytes())
        self.assertEqual("User note", (self.root / "data" / "org.pmkb.demo" / "notes.txt").read_text("utf-8"))
        self.assertEqual(hashlib.sha256(b"DEMO-PAYLOAD-V1").hexdigest(), result["files"]["bin/demo"])
        self.assertEqual(sum(len((dest / item).read_bytes()) for item in result["files"]), result["total_bytes"])
        self.assertEqual([], self.stages())

    def test_same_id_or_preexisting_symlink_never_overwritten(self):
        payload = package()
        install_archive(payload, self.root)
        with self.assertRaisesRegex(InstallError, "already_installed"):
            install_archive(payload, self.root)
        dest = self.root / "apps" / "org.pmkb.demo"
        self.assertEqual(b"DEMO-PAYLOAD-V1", (dest / "bin" / "demo").read_bytes())
        self.assertEqual([], self.stages())

    def test_unmarked_and_invalid_root_refused(self):
        (self.root / MARKER_NAME).unlink()
        with self.assertRaisesRegex(InstallError, "test_root_required"):
            install_archive(package(), self.root)
        self.assert_no_install()
        (self.root / MARKER_NAME).write_text("wrong marker", "utf-8")
        with self.assertRaisesRegex(InstallError, "test_root_required"):
            install_archive(package(), self.root)
        self.assert_no_install()

    def test_parent_os_temp_root_cannot_be_used(self):
        with self.assertRaisesRegex(InstallError, "test_root_required"):
            install_archive(package(), Path(tempfile.gettempdir()))
        self.assert_no_install()

    def test_data_directory_is_never_modified_even_on_failure(self):
        before = (self.root / "data" / "org.pmkb.demo" / "notes.txt").read_bytes()
        with self.assertRaises(ArchiveError):
            install_archive(package(files=[("../escape", b"X"), ("bin/demo", b"OK")]), self.root)
        self.assertEqual(before, (self.root / "data" / "org.pmkb.demo" / "notes.txt").read_bytes())
        self.assert_no_install()

    def test_corrupt_payload_crc_rolls_back_staging(self):
        raw = package(files=[("a.txt", b"SAFE"), ("bin/demo", b"DEMO-PAYLOAD-V1")])
        # Alter a stored member payload in-place, leaving ZIP directory & CRC intact.
        self.assertEqual(1, raw.count(b"DEMO-PAYLOAD-V1"))
        bad = raw.replace(b"DEMO-PAYLOAD-V1", b"DEMO-PAYLOAD-V2")
        with self.assertRaisesRegex(InstallError, "payload_io_or_crc"):
            install_archive(bad, self.root)
        self.assert_no_install()

    def test_publish_rename_failure_rolls_back_without_touching_data(self):
        # Simulate interruption at the final atomic publication boundary.
        with patch("install_contract.os.rename", side_effect=OSError("injected")):
            with self.assertRaisesRegex(InstallError, "payload_io_or_crc"):
                install_archive(package(), self.root)
        self.assert_no_install()

    def test_incompatible_manifest_and_network_do_not_write(self):
        with self.assertRaisesRegex(ManifestError, "unsupported_target"):
            install_archive(package(manifest={**EXAMPLE, "target": "other"}), self.root)
        with self.assertRaisesRegex(ManifestError, "network_not_granted"):
            install_archive(package(manifest={**EXAMPLE, "network": True}), self.root)
        self.assert_no_install()
        result = install_archive(package(manifest={**EXAMPLE, "network": True}), self.root,
                                 allow_network=True)
        self.assertEqual("org.pmkb.demo", result["id"])

    def test_invalid_members_before_writes(self):
        for member in ("../escape", "/absolute", "bin/../escape"):
            with self.subTest(member=member):
                with self.assertRaisesRegex(ArchiveError, "unsafe_member_path"):
                    install_archive(package(files=[("bin/demo", b"demo"), (member, b"bad")]), self.root)
                self.assert_no_install()

    @unittest.skipIf(os.name == "nt", "Windows unprivileged symlink creation is restricted")
    def test_preexisting_apps_symlink_refused(self):
        other = self.root / "elsewhere"
        other.mkdir()
        (self.root / "apps").symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(InstallError, "unsafe_install_root"):
            install_archive(package(), self.root)
        self.assertEqual([], list(other.iterdir()))

    @unittest.skipIf(os.name == "nt", "Windows unprivileged symlink creation is restricted")
    def test_data_symlink_refused_even_though_no_data_writes(self):
        import shutil
        shutil.rmtree(self.root / "data")
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "data").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(InstallError, "unsafe_install_root"):
            install_archive(package(), self.root)
        self.assertFalse((self.root / "apps" / "org.pmkb.demo").exists())

    @unittest.skipIf(os.name == "nt", "Windows unprivileged symlink creation is restricted")
    def test_preexisting_app_symlink_refused(self):
        apps = self.root / "apps"
        apps.mkdir()
        (apps / "org.pmkb.demo").symlink_to(self.root / "data", target_is_directory=True)
        with self.assertRaisesRegex(InstallError, "already_installed"):
            install_archive(package(), self.root)
        self.assertEqual([], self.stages())

    def test_empty_member_and_implicit_parent(self):
        raw = package(files=[("bin/demo", b"X"), ("empty.txt", b"")])
        result = install_archive(raw, self.root)
        self.assertEqual(b"", (result["code_directory"] / "empty.txt").read_bytes())
        self.assertTrue((result["code_directory"] / "bin").is_dir())

    def test_bad_root_type_fails_without_side_effects(self):
        with self.assertRaisesRegex(InstallError, "test_root_required"):
            install_archive(package(), None)
        self.assert_no_install()

    def test_rejects_existing_data_file_instead_of_directory(self):
        import shutil
        shutil.rmtree(self.root / "data")
        (self.root / "data").write_text("occupied", "utf-8")
        with self.assertRaisesRegex(InstallError, "unsafe_install_root"):
            install_archive(package(), self.root)
        self.assertFalse((self.root / "apps" / "org.pmkb.demo").exists())

    def test_no_subprocess_or_external_network(self):
        with patch("subprocess.run", side_effect=AssertionError("process")):
            result = install_archive(package(), self.root)
        self.assertTrue(result["code_directory"].is_dir())


if __name__ == "__main__":
    unittest.main()
