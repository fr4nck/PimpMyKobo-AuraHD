"""L08-K tests: read-only P1 verification uses synthetic images only."""
import hashlib
import importlib.util
from io import StringIO
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pmkb_qualify_p1_export", ROOT / "tools" / "qualify-p1-export.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

from test_store_ext4_export_provenance import fake_ext4, arm_shared


def fixture(root, *, data=None):
    backup = root / "backup"
    export = root / "export"
    backup.mkdir()
    (export / "lib").mkdir(parents=True)
    (export / "usr" / "lib").mkdir(parents=True)
    image = fake_ext4()
    (backup / "p1-rootfs.img").write_bytes(image)
    (export / "lib" / "libc.so.6").write_bytes(
        arm_shared() if data is None else data)
    return backup, export, hashlib.sha256(image).hexdigest()


def fake_verifier(sha, *, valid=True, filename="p1-rootfs.img"):
    return SimpleNamespace(verify_backup=lambda _root: {
        "status": "valid" if valid else "incomplete",
        "ok": valid,
        "components": [{"name": "p1_rootfs", "result": "valid",
                        "file": filename, "sha256_recomputed": sha}],
    })


class P1ExportReadOnlyTests(unittest.TestCase):
    def test_scoped_match_remains_unverified_on_physical_device(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                result = gate.qualify_p1_export(backup, export)
        self.assertEqual(result["verdict"], "scoped_image_export_match")
        self.assertEqual(result["matched"], ("lib/libc.so.6",))
        self.assertEqual(result["p1_sha256_measured"], sha)
        self.assertTrue(result["backup_files_consistent_with_manifest"])
        self.assertTrue(result["image_to_export_link_verified_for_scanned_scope"])
        for field in ("backup_manifest_authenticated",
                      "image_authenticated_as_kobo_p1",
                      "whole_rootfs_verified",
                      "filesystem_metadata_integrity_verified",
                      "hardware_verified", "runtime_compatible", "launchable"):
            self.assertFalse(result[field], field)

    def test_export_mismatch_blocks_scoped_match(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td), data=arm_shared() + b"changed")
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                result = gate.qualify_p1_export(backup, export)
        self.assertEqual(result["verdict"], "mismatch")
        self.assertEqual(result["content_mismatch"], ("lib/libc.so.6",))
        self.assertFalse(result["image_to_export_link_verified_for_scanned_scope"])

    def test_incomplete_backup_stops_before_p1_read(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha, valid=False)):
                with patch.object(gate, "_read_regular_image",
                                  side_effect=AssertionError("read was attempted")):
                    with self.assertRaisesRegex(
                            gate.P1ExportGateError, "backup_not_valid"):
                        gate.qualify_p1_export(backup, export)

    def test_manifest_hash_mismatch_refused(self):
        with TemporaryDirectory() as td:
            backup, export, _sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier("f" * 64)):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "verified_backup_p1_hash_mismatch"):
                    gate.qualify_p1_export(backup, export)

    def test_component_not_canonical_is_refused(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha, filename="another.img")):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "p1_not_verified"):
                    gate.qualify_p1_export(backup, export)

    def test_p1_symlink_refused(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            p1 = backup / "p1-rootfs.img"
            target = backup / "target.img"
            p1.rename(target)
            try:
                p1.symlink_to(target.name)
            except (OSError, NotImplementedError):
                self.skipTest("host symlink unsupported")
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "invalid_p1_regular_image"):
                    gate.qualify_p1_export(backup, export)

    def test_backup_directory_symlink_refused_before_verification(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            link = Path(td) / "link"
            try:
                link.symlink_to(backup, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("host symlink unsupported")
            with patch.object(gate, "_load_backup_verifier",
                              side_effect=AssertionError("verifier ran")):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "invalid_backup_directory"):
                    gate.qualify_p1_export(link, export)

    def test_non_regular_image_is_rejected(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            p1 = backup / "p1-rootfs.img"
            p1.unlink()
            p1.mkdir()
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "invalid_p1_regular_image"):
                    gate.qualify_p1_export(backup, export)

    def test_image_size_bounded_without_large_allocation(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "MAX_IMAGE_BYTES", 1024):
                with patch.object(gate, "_load_backup_verifier",
                                  return_value=fake_verifier(sha)):
                    with self.assertRaisesRegex(
                            gate.P1ExportGateError, "invalid_p1_regular_image"):
                        gate.qualify_p1_export(backup, export)

    def test_nonexistent_export_is_refused(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                with self.assertRaisesRegex(
                        gate.RootfsSnapshotError, "snapshot_directory_required"):
                    gate.qualify_p1_export(backup, export / "missing")

    def test_comparison_does_not_modify_input_files(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            before = (backup / "p1-rootfs.img").stat()
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                with patch.object(Path, "write_bytes",
                                  side_effect=AssertionError("write attempted")):
                    with patch.object(Path, "write_text",
                                      side_effect=AssertionError("write attempted")):
                        with patch("os.replace",
                                   side_effect=AssertionError("rename attempted")):
                            result = gate.qualify_p1_export(backup, export)
            after = (backup / "p1-rootfs.img").stat()
            self.assertEqual(result["verdict"], "scoped_image_export_match")
            self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
            self.assertFalse((backup / "qualification.json").exists())

    def test_real_backup_verifier_rejects_missing_manifest_without_p1_scan(self):
        # Unlike fixture tests, this invokes the real verifier adapter.
        with TemporaryDirectory() as td:
            backup = Path(td) / "empty-backup"
            export = Path(td) / "export"
            backup.mkdir()
            export.mkdir()
            with patch.object(gate, "_read_regular_image",
                              side_effect=AssertionError("extra P1 read")):
                with self.assertRaisesRegex(
                        gate.P1ExportGateError, "backup_not_valid"):
                    gate.qualify_p1_export(backup, export)

    def test_cli_refusal_is_machine_readable(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha, valid=False)):
                captured = StringIO()
                with redirect_stdout(captured):
                    result = gate.main([str(backup), str(export)])
        self.assertEqual(result, 2)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["verdict"], "refused")
        self.assertEqual(out["reason"], "backup_not_valid")
        self.assertFalse(out["launchable"])

    def test_cli_scoped_match_returns_zero_without_claiming_hardware(self):
        with TemporaryDirectory() as td:
            backup, export, sha = fixture(Path(td))
            with patch.object(gate, "_load_backup_verifier",
                              return_value=fake_verifier(sha)):
                captured = StringIO()
                with redirect_stdout(captured):
                    result = gate.main([str(backup), str(export)])
        self.assertEqual(result, 0)
        out = json.loads(captured.getvalue())
        self.assertTrue(out["image_to_export_link_verified_for_scanned_scope"])
        self.assertFalse(out["hardware_verified"])


if __name__ == "__main__":
    unittest.main()
