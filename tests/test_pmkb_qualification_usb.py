import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pmkb_qualification_usb", ROOT / "tools" / "pmkb-qualification-usb.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

MANIFEST = json.loads((ROOT / "live" / "pmkb-qualification" / "candidate.json").read_text(encoding="utf-8"))


class QualificationUsbTests(unittest.TestCase):
    def expected_sfdisk(self, disk="/dev/sdz"):
        return {
            "partitiontable": {
                "label": "dos",
                "sectorsize": 512,
                "partitions": [
                    {"node": f"{disk}1", "start": 19456, "size": 524289},
                    {"node": f"{disk}2", "start": 543745, "size": 524289},
                    {"node": f"{disk}3", "start": 1068034, "size": 61265918},
                ],
            }
        }

    def test_manifest_is_pinned_to_frozen_candidate(self):
        self.assertEqual(268435968, MANIFEST["image_size"])
        self.assertEqual("7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c", MANIFEST["image_sha256"])
        self.assertEqual("fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a", MANIFEST["partitions"][1]["sha256"])

    def test_validate_layout_accepts_exact_aura_hd_geometry(self):
        parts = mod.validate_layout("/dev/sdz", self.expected_sfdisk(), MANIFEST)
        self.assertEqual([1, 2, 3], [p.number for p in parts])
        self.assertEqual(9961472, parts[0].offset)
        self.assertEqual(278397440, parts[1].offset)
        self.assertEqual(546833408, parts[2].offset)

    def test_validate_layout_rejects_one_sector_shift(self):
        data = self.expected_sfdisk()
        data["partitiontable"]["partitions"][1]["start"] += 1
        with self.assertRaises(mod.QualificationError):
            mod.validate_layout("/dev/sdz", data, MANIFEST)

    def test_hash_region_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "blob"
            p.write_bytes(b"A" * 10 + b"B" * 20 + b"C" * 10)
            self.assertEqual(mod.hashlib.sha256(b"B" * 20).hexdigest(), mod.sha256_region(p, 10, 20))

    def test_confirmation_phrase_is_candidate_specific(self):
        self.assertEqual("ECRIRE P1 7980fec1", mod.confirmation_phrase(MANIFEST))

    def test_wsl_is_refused_for_physical_write(self):
        with mock.patch.object(mod.platform, "release", return_value="6.18.33.2-microsoft-standard-WSL2"):
            with self.assertRaises(mod.QualificationError):
                mod.ensure_supported_write_host()

    def test_regular_file_is_never_accepted_as_physical_write_target(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "not-a-device"
            p.write_bytes(b"")
            with self.assertRaises(mod.QualificationError):
                mod.ensure_block_device(str(p))

    def test_write_opens_only_partition_path_not_whole_disk(self):
        target = mod.Target(
            disk_path="/dev/sdz",
            size=MANIFEST["disk"]["size"],
            model="reader",
            serial="serial",
            partitions=(
                mod.Partition(1, "/dev/sdz1", 9961472, 268435968),
                mod.Partition(2, "/dev/sdz2", 278397440, 268435968),
                mod.Partition(3, "/dev/sdz3", 546833408, 31368150016),
            ),
        )
        self.assertEqual("/dev/sdz1", target.partition(1).path)
        self.assertNotEqual(target.disk_path, target.partition(1).path)


if __name__ == "__main__":
    unittest.main()
