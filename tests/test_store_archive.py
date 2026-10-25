"""L06-B1: synthetic in-memory archives, no installers or disk extraction."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, ZipInfo

MODULE_DIR = Path(__file__).resolve().parents[1] / "experimental/store-v0"
sys.path.insert(0, str(MODULE_DIR))
from archive_contract import ArchiveError, inspect_archive, MAX_ARCHIVE_BYTES
from manifest_contract import ManifestError

SAMPLE = json.loads((MODULE_DIR / "example/manifest.json").read_text("utf-8"))


def package(*, manifest=None, members=None, compression=ZIP_STORED):
    manifest = SAMPLE if manifest is None else manifest
    members = [("bin/demo", b"demo")] if members is None else members
    destination = BytesIO()
    with ZipFile(destination, "w", compression=compression) as zipfile:
        zipfile.writestr("manifest.json", json.dumps(manifest).encode())
        for path, content in members:
            zipfile.writestr(path, content)
    return destination.getvalue()


class ArchiveContractTests(unittest.TestCase):
    def reject(self, reason, content):
        with self.assertRaises(ArchiveError) as caught:
            inspect_archive(content)
        self.assertEqual(str(caught.exception), reason)

    def test_valid_package_and_no_extraction(self):
        raw = package(members=[("bin/", b""), ("bin/demo", b"demo"),
                               ("assets/logo.png", b"PNG")], compression=ZIP_DEFLATED)
        before = raw
        result = inspect_archive(raw)
        self.assertEqual(before, raw)
        self.assertEqual("org.pmkb.demo", result["manifest"]["id"])
        self.assertEqual(("assets/logo.png", "bin/demo", "manifest.json"), result["members"])
        self.assertEqual(len(b"demo") + len(b"PNG") + len(json.dumps(SAMPLE).encode()),
                         result["declared_unpacked_bytes"])

    def test_invalid_archive_input_and_size(self):
        for value in (None, b"", b"invalid zip", bytearray(package()), b"x" * (MAX_ARCHIVE_BYTES + 1)):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ArchiveError):
                    inspect_archive(value)

    def test_traversal_and_absolute_and_windows_separators(self):
        for path in ("../escape", "bin/../escape", "/bin/demo", "C:/bin/demo",
                     "bin\\demo", "bin//demo", "bin/./demo", "bin/x.", "bin/evil:name"):
            with self.subTest(path=path):
                # ZipInfo(path) normalizes os.sep on Windows: write a raw ZIP
                # member name instead of accidentally constructing a duplicate.
                archive_name = path
                if "\\" in path:
                    archive_name = ZipInfo("bin/demo")
                    archive_name.filename = path
                    archive_name.orig_filename = path
                raw = package(members=[(archive_name, b"data"), ("bin/demo", b"demo")])
                if "\\" in path:
                    with ZipFile(BytesIO(raw), "r") as zipfile:
                        self.assertIn(
                            path, [item.orig_filename for item in zipfile.infolist()])
                self.reject("unsafe_member_path", raw)

    def test_windows_zip_name_normalization_does_not_bypass_preflight(self):
        # Build an entry with a raw backslash before the archive is read.
        name = "bin\\demo"
        entry = ZipInfo("bin/demo")
        entry.filename = name
        entry.orig_filename = name
        raw = package(members=[(entry, b"demo")])
        # Force the same ZipInfo normalization as the Windows runner.
        with patch("zipfile.os.sep", "\\"):
            with ZipFile(BytesIO(raw), "r") as zipfile:
                self.assertEqual(
                    ["manifest.json", "bin/demo"], zipfile.namelist())
                self.assertIn(name, [
                    item.orig_filename for item in zipfile.infolist()])
            self.reject("unsafe_member_path", raw)

    def test_collision_ignoring_case(self):
        raw = package(members=[("bin/demo", b"demo"), ("BIN/DEMO", b"other")])
        self.reject("duplicate_member", raw)

    def test_duplicate_identical_names(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.reject("duplicate_member", package(members=[("bin/demo", b"x"), ("bin/demo", b"y")]))

    def test_symlinks_and_devices_rejected(self):
        for kind in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFIFO):
            entry = ZipInfo("bin/demo")
            entry.create_system = 3
            entry.external_attr = ((kind | 0o777) << 16)
            with self.subTest(kind=kind):
                self.reject("unsupported_member_type", package(members=[(entry, b"target")]))

    def test_missing_manifest(self):
        output = BytesIO()
        with ZipFile(output, "w") as z:
            z.writestr("bin/demo", b"demo")
        self.reject("missing_manifest", output.getvalue())

    def test_missing_empty_or_directory_entrypoint(self):
        self.reject("missing_entrypoint", package(members=[("elsewhere", b"data")]))
        self.reject("empty_entrypoint", package(members=[("bin/demo", b"")]))
        self.reject("missing_entrypoint", package(members=[("bin/demo/", b"")]))

    def test_member_count_limit(self):
        self.reject("invalid_member_count", package(members=[("bin/demo", b"demo")] +
            [("assets/file%03d" % i, b"x") for i in range(127)]))

    def test_member_size_limit(self):
        self.reject("member_too_large", package(members=[("bin/demo", b"x" * (8 * 1024 * 1024 + 1))],
                                                     compression=ZIP_DEFLATED))

    def test_manifest_size_cap_and_corrupted_zip(self):
        too_large = package(manifest={**SAMPLE, "name": "X" * 4096})
        self.reject("manifest_too_large", too_large)
        raw = package()
        self.reject("invalid_archive", raw[:20])

    def test_noncanonical_unicode_and_windows_style_names(self):
        for path in ("bin/cafe\u0301", "assets/NUL.txt", "assets/LPT1", "assets/space "):
            with self.subTest(path=path):
                self.reject("unsafe_member_path", package(members=[("bin/demo", b"demo"), (path, b"test")]))

    def test_member_parent_file_conflict(self):
        self.reject("member_parent_is_file", package(members=[("bin", b"x"), ("bin/demo", b"demo")]))

    def test_manifest_rejects_incompatible_target_and_permission(self):
        bad = {**SAMPLE, "target": "clara-hd"}
        with self.assertRaisesRegex(ManifestError, "unsupported_target"):
            inspect_archive(package(manifest=bad))
        bad = {**SAMPLE, "network": True}
        with self.assertRaisesRegex(ManifestError, "network_not_granted"):
            inspect_archive(package(manifest=bad))
        result = inspect_archive(package(manifest=bad), allow_network=True)
        self.assertTrue(result["manifest"]["network"])

    def test_no_host_file_or_process_access_during_inspection(self):
        raw = package()
        with patch("builtins.open", side_effect=AssertionError("file access")), \
             patch("subprocess.run", side_effect=AssertionError("process")):
            result = inspect_archive(raw)
        self.assertEqual("bin/demo", result["manifest"]["entrypoint"])


if __name__ == "__main__":
    unittest.main()
