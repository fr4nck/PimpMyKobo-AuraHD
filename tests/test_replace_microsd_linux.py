import copy
import hashlib
import importlib.util
import io
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "replace_microsd_linux",
    ROOT / "tools" / "replace-microsd-linux.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

REAL_MANIFEST = json.loads(
    (ROOT / "live" / "pmkb-qualification" / "candidate.json").read_text(encoding="utf-8")
)


def synthetic_manifest():
    pre = bytearray(512)
    pre[510:512] = b"\x55\xaa"

    def entry(number, ptype, start, size):
        offset = 446 + (number - 1) * 16
        pre[offset] = 0
        pre[offset + 4] = ptype
        struct.pack_into("<I", pre, offset + 8, start // 512)
        struct.pack_into("<I", pre, offset + 12, size // 512)

    entry(1, 0x83, 512, 1024)
    entry(2, 0x83, 1536, 1024)
    entry(3, 0x0C, 2560, 4096)
    p2 = b"R" * 1024
    manifest = {
        "image_name": "candidate.img",
        "image_size": 1024,
        "image_sha256": hashlib.sha256(b"P" * 1024).hexdigest(),
        "disk": {"size": 6656, "partition_table": "dos", "sector_size": 512},
        "pre_p1": {
            "offset": 0,
            "size": 512,
            "sha256": hashlib.sha256(pre).hexdigest(),
        },
        "partitions": [
            {"number": 1, "offset": 512, "size": 1024, "role": "rootfs"},
            {
                "number": 2,
                "offset": 1536,
                "size": 1024,
                "role": "recoveryfs",
                "sha256": hashlib.sha256(p2).hexdigest(),
            },
            {"number": 3, "offset": 2560, "size": 4096, "role": "KOBOeReader"},
        ],
    }
    return manifest, bytes(pre), p2


class ReplacementMicroSdTests(unittest.TestCase):
    def test_real_manifest_supports_capacity_independent_target_layout(self):
        manifest = copy.deepcopy(REAL_MANIFEST)
        two_gib = 2 * 1024**3
        layout = mod.target_layout(manifest, two_gib)
        self.assertEqual(manifest["partitions"][2]["offset"], layout["p3_offset"])
        self.assertGreaterEqual(layout["p3_size"], mod.MIN_P3_BYTES)
        self.assertLess(layout["unused_tail"], 1024)
        self.assertEqual(0, layout["p3_sectors"] % 2)

    def test_default_minimum_rejects_too_small_card(self):
        with self.assertRaises(mod.ReplacementError):
            mod.target_layout(REAL_MANIFEST, 1024**3)

    def test_small_synthetic_layout_can_be_calculated_for_tests(self):
        manifest, _pre, _p2 = synthetic_manifest()
        layout = mod.target_layout(manifest, 8192, min_p3_bytes=1024)
        self.assertEqual(2560, layout["p3_offset"])
        self.assertEqual(5120, layout["p3_size"])
        self.assertEqual(10, layout["p3_sectors"])
        self.assertEqual(512, layout["unused_tail"])
        # KiB block count requires an even sector count, so target_layout trims one.
        # Re-run with an aligned size to validate the production invariant.
        layout = mod.target_layout(manifest, 8704, min_p3_bytes=1024)
        self.assertEqual(6144, layout["p3_size"])
        self.assertEqual(12, layout["p3_sectors"])

    def test_patch_pre_p1_changes_only_p3_length_field(self):
        manifest, pre, _p2 = synthetic_manifest()
        layout = mod.target_layout(manifest, 8704, min_p3_bytes=1024)
        patched = mod.patch_pre_p1(pre, manifest, layout)
        p3_entry = 446 + 2 * 16
        self.assertEqual(pre[:p3_entry + 12], patched[:p3_entry + 12])
        self.assertEqual(pre[p3_entry + 16:], patched[p3_entry + 16:])
        self.assertEqual(
            layout["p3_sectors"],
            struct.unpack_from("<I", patched, p3_entry + 12)[0],
        )
        self.assertEqual(b"\x55\xaa", patched[510:512])

    def test_target_looks_like_donor_uses_indispensable_regions_only(self):
        manifest, pre, p2 = synthetic_manifest()
        disk = bytearray(8192)
        disk[:len(pre)] = pre
        p2_spec = manifest["partitions"][1]
        disk[p2_spec["offset"]:p2_spec["offset"] + len(p2)] = p2
        self.assertTrue(mod.target_looks_like_donor(io.BytesIO(disk), len(disk), manifest))
        disk[p2_spec["offset"]] ^= 0x01
        self.assertFalse(mod.target_looks_like_donor(io.BytesIO(disk), len(disk), manifest))

    def test_target_fingerprint_binds_size_front_and_tail(self):
        a = io.BytesIO(b"A" * (2 * mod.FINGERPRINT_WINDOW + 512))
        b = io.BytesIO(b"A" * (2 * mod.FINGERPRINT_WINDOW + 511) + b"B")
        self.assertNotEqual(
            mod.target_fingerprint(a, len(a.getvalue())),
            mod.target_fingerprint(b, len(b.getvalue())),
        )

    def test_fat_command_is_bounded_to_p3_offset_and_size(self):
        manifest, _pre, _p2 = synthetic_manifest()
        layout = mod.target_layout(manifest, 8704, min_p3_bytes=1024)
        command = mod.mkfs_fat_command(Path("/dev/sdz"), layout, "/sbin/mkfs.fat")
        self.assertEqual("/sbin/mkfs.fat", command[0])
        self.assertIn("--offset", command)
        self.assertEqual(
            str(layout["p3_start_sector"]),
            command[command.index("--offset") + 1],
        )
        self.assertEqual(str(layout["p3_kib"]), command[-1])
        self.assertEqual("/dev/sdz", command[-2])
        self.assertIn(mod.FAT_LABEL, command)

    def test_verify_fat32_accepts_expected_bpb(self):
        manifest, _pre, _p2 = synthetic_manifest()
        layout = mod.target_layout(manifest, 8704, min_p3_bytes=1024)
        disk = bytearray(8704)
        sector = memoryview(disk)[layout["p3_offset"]:layout["p3_offset"] + 512]
        struct.pack_into("<H", sector, 11, 512)
        struct.pack_into("<I", sector, 28, layout["p3_start_sector"])
        struct.pack_into("<H", sector, 19, 0)
        struct.pack_into("<I", sector, 32, layout["p3_sectors"])
        sector[71:82] = b"KOBOEREADER"
        sector[82:90] = b"FAT32   "
        sector[510:512] = b"\x55\xaa"
        result = mod.verify_fat32(io.BytesIO(disk), layout)
        self.assertEqual("fat32", result["filesystem"])
        self.assertEqual("KOBOEREADER", result["label"])

    def test_confirmation_binds_target_and_plan(self):
        plan = {"target_path": "/dev/sdz"}
        phrase = mod.replacement_confirmation("a" * 64, plan)
        self.assertEqual("EFFACER /dev/sdz CREER PMKB aaaaaaaa", phrase)

    def test_backend_never_needs_to_write_source_card(self):
        source = (ROOT / "tools" / "replace-microsd-linux.py").read_text(encoding="utf-8")
        self.assertIn("restore.LinuxDisk(device, False)", source)
        self.assertIn('"source_card_write_attempted": False', source)
        self.assertIn('"source_card_write_required": False', source)
        self.assertNotIn("source_card_write_attempted=True", source)


if __name__ == "__main__":
    unittest.main()
