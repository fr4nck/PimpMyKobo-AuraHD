"""Host-only regression tests for PMKB system ZIP (all data synthetic)."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "pack-pmkb-system.py"
SPEC = importlib.util.spec_from_file_location("pack_pmkb_system", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pack)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CompactSystemBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pmkb-bundle-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Deliberately tiny fixtures, never real or redistributable Kobo bytes.
        self.bytes_pre = b"A" * 512
        self.bytes_p1 = b"B" * 1024
        self.bytes_p2 = b"C" * 1536
        self.pre = self.write("pre.bin", self.bytes_pre)
        self.p1 = self.write("p1.img", self.bytes_p1)
        self.p2 = self.write("p2.img", self.bytes_p2)
        self.manifest = self.root / "candidate.json"
        self.meta = {
            "schema": 1,
            "project": "PimpMyKobo-AuraHD",
            "model": "Kobo Aura HD E606C0",
            "head": "a" * 40,
            "image_name": "synthetic-first-boot.img",
            "image_size": 1024,
            "image_sha256": digest(self.bytes_p1),
            "disk": {"size": 7168, "partition_table": "dos", "sector_size": 512},
            "pre_p1": {"offset": 0, "size": 512, "sha256": digest(self.bytes_pre)},
            "partitions": [
                {"number": 1, "offset": 512, "size": 1024, "role": "rootfs"},
                {"number": 2, "offset": 1536, "size": 1536,
                 "role": "recoveryfs", "sha256": digest(self.bytes_p2)},
                {"number": 3, "offset": 3072, "size": 4096, "role": "KOBOeReader"},
            ],
        }
        self.save_manifest()
        self.bundle = self.root / "system.zip"

    def write(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.write_bytes(data)
        return path

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.meta, sort_keys=True), encoding="utf-8")

    def build(self, destination: Path | None = None) -> dict:
        return pack.build(
            self.pre, self.p1, self.p2, self.manifest,
            destination if destination is not None else self.bundle,
        )

    def test_roundtrip_verified_and_p3_excluded(self):
        made = self.build()
        checked = pack.verify(self.bundle, self.manifest)
        self.assertEqual("PASS", made["status"])
        self.assertEqual("PASS", checked["status"])
        self.assertFalse(made["hardware_qualified"])
        self.assertFalse(made["device_write_attempted"])
        self.assertFalse(made["p3_included"])
        self.assertEqual(512 + 1024 + 1536, checked["uncompressed_system_size"])
        self.assertEqual(digest(self.bundle.read_bytes()), checked["package_sha256"])
        with zipfile.ZipFile(self.bundle) as archive:
            self.assertEqual(
                set(pack.ENTRIES) | {pack.MANIFEST_ENTRY},
                set(archive.namelist()),
            )
            self.assertEqual(self.bytes_pre, archive.read(pack.ENTRY_PRE))
            self.assertEqual(self.bytes_p1, archive.read(pack.ENTRY_P1))
            self.assertEqual(self.bytes_p2, archive.read(pack.ENTRY_P2))
            payload = json.loads(archive.read(pack.MANIFEST_ENTRY))
            self.assertFalse(payload["p3_included"])
            self.assertFalse(payload["write_authorized"])
            self.assertEqual("recreate-on-target-separately", payload["p3_policy"])
            self.assertEqual("a" * 40, payload["candidate_head"])

    def test_same_inputs_produce_identical_zip_bytes(self):
        self.build()
        other = self.root / "repeat.zip"
        self.build(other)
        self.assertEqual(digest(self.bundle.read_bytes()), digest(other.read_bytes()))

    def test_bad_sha_rejects_without_output_or_leftover(self):
        self.p2.write_bytes(b"D" * len(self.bytes_p2))
        with self.assertRaisesRegex(pack.BundleError, "SHA-256 mismatch"):
            self.build()
        self.assertFalse(self.bundle.exists())
        self.assertFalse(list(self.root.glob(".pmkb-bundle-*.tmp")))

    def test_wrong_size_rejected_before_creating_archive(self):
        self.p1.write_bytes(self.bytes_p1[:-1])
        with self.assertRaisesRegex(pack.BundleError, "size mismatch"):
            self.build()
        self.assertFalse(self.bundle.exists())

    def test_existing_output_is_not_overwritten(self):
        self.bundle.write_bytes(b"previous")
        with self.assertRaisesRegex(pack.BundleError, "overwrite"):
            self.build()
        self.assertEqual(b"previous", self.bundle.read_bytes())

    def test_wrong_candidate_geometry_is_rejected(self):
        self.meta["partitions"][2]["offset"] += 512
        self.save_manifest()
        with self.assertRaisesRegex(pack.BundleError, "noncontiguous"):
            self.build()
        self.assertFalse(self.bundle.exists())

    def test_bundle_rejected_if_reference_manifest_changes(self):
        self.build()
        self.meta["head"] = "b" * 40
        self.save_manifest()
        with self.assertRaisesRegex(pack.BundleError, "pinned candidate"):
            pack.verify(self.bundle, self.manifest)

    def test_archive_with_unexpected_member_is_rejected(self):
        self.build()
        with zipfile.ZipFile(self.bundle, "a") as archive:
            archive.writestr("../unexpected.txt", b"payload")
        with self.assertRaisesRegex(pack.BundleError, "unknown, duplicate or missing"):
            pack.verify(self.bundle, self.manifest)

    def test_corrupted_member_is_rejected(self):
        self.build()
        altered = self.root / "altered.zip"
        with zipfile.ZipFile(self.bundle) as original, zipfile.ZipFile(altered, "w") as target:
            for name in original.namelist():
                payload = original.read(name)
                if name == pack.ENTRY_P2:
                    payload = b"X" + payload[1:]
                target.writestr(name, payload)
        with self.assertRaisesRegex(pack.BundleError, "uncompressed SHA-256 mismatch"):
            pack.verify(altered, self.manifest)

    def test_archive_symlink_member_is_rejected(self):
        self.build()
        altered = self.root / "symlink.zip"
        with zipfile.ZipFile(self.bundle) as original, zipfile.ZipFile(altered, "w") as target:
            for name in original.namelist():
                info = pack.zip_info(name)
                if name == pack.ENTRY_P2:
                    info.external_attr = 0o120777 << 16
                target.writestr(info, original.read(name))
        with self.assertRaisesRegex(pack.BundleError, "symlink forbidden"):
            pack.verify(altered, self.manifest)

    def test_symlink_input_refused_where_supported(self):
        alias = self.root / "alias.bin"
        try:
            alias.symlink_to(self.pre)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not supported in this environment")
        with self.assertRaisesRegex(pack.BundleError, "symbolic link forbidden"):
            pack.build(alias, self.p1, self.p2, self.manifest, self.bundle)
        self.assertFalse(self.bundle.exists())

    def test_device_paths_are_rejected(self):
        with self.assertRaisesRegex(pack.BundleError, "device/UNC paths"):
            pack.regular(Path("/dev/not-a-real-device"))
        with self.assertRaisesRegex(pack.BundleError, "device/UNC paths"):
            pack.regular(Path("PhysicalDrive42"))

    def test_cli_roundtrip_returns_json_pass(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = pack.main([
                "build", "--pre-p1", str(self.pre), "--p1", str(self.p1),
                "--p2", str(self.p2), "--manifest", str(self.manifest),
                "--output", str(self.bundle),
            ])
        self.assertEqual(0, code)
        self.assertEqual("PASS", json.loads(buffer.getvalue())["status"])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = pack.main([
                "verify", "--package", str(self.bundle),
                "--manifest", str(self.manifest),
            ])
        self.assertEqual(0, code)
        self.assertFalse(json.loads(buffer.getvalue())["hardware_qualified"])


if __name__ == "__main__":
    unittest.main()
