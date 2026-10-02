from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "inspect-aura-hd.py"
SPEC = importlib.util.spec_from_file_location("inspect_aura_hd", SCRIPT)
assert SPEC and SPEC.loader
inspect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect)

KNOWN_PAYLOAD = bytes.fromhex(
    "1c 0b 00 00 07 00 00 08 04 06 0a 02 00 09 01 00 "
    "03 00 02 02 02 02 b0 03 e8 00 00 02 01 02 00 03 "
    "06 02 01 03 00 01 00"
)


def mbr_entry(ptype: int, start_lba: int, sectors: int) -> bytes:
    entry = bytearray(16)
    entry[4] = ptype
    entry[8:12] = start_lba.to_bytes(4, "little")
    entry[12:16] = sectors.to_bytes(4, "little")
    return bytes(entry)


def build_image(path: Path) -> tuple[int, int, int]:
    p1_lba, p2_lba, p3_lba = 2048, 3072, 4096
    with path.open("wb") as f:
        f.truncate(4 * 1024 * 1024)

    with path.open("r+b") as f:
        mbr = bytearray(512)
        mbr[446:462] = mbr_entry(0x83, p1_lba, 1024)
        mbr[462:478] = mbr_entry(0x83, p2_lba, 1024)
        mbr[478:494] = mbr_entry(0x0C, p3_lba, 2048)
        mbr[510:512] = b"\x55\xaa"
        f.seek(0)
        f.write(mbr)

        header = b"HW CONFIG " + b"v1.7\x00" + bytes([len(KNOWN_PAYLOAD)])
        assert len(header) == 16
        f.seek(inspect.HWCONFIG_OFFSET)
        f.write(header + KNOWN_PAYLOAD)

        for lba, label in ((p1_lba, b"rootfs"), (p2_lba, b"recoveryfs")):
            sb = bytearray(1024)
            sb[56:58] = b"\x53\xef"
            sb[120 : 120 + len(label)] = label
            f.seek(lba * 512 + 1024)
            f.write(sb)

        fat = bytearray(512)
        fat[71:82] = b"KOBOeReader"
        fat[82:90] = b"FAT32   "
        f.seek(p3_lba * 512)
        f.write(fat)

    return p1_lba * 512, p2_lba * 512, p3_lba * 512


class InspectAuraHDTests(unittest.TestCase):
    def test_known_hwconfig_decodes_as_e606c0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            with image.open("rb") as f:
                hw = inspect.parse_hwconfig(f)
            self.assertIsNotNone(hw)
            assert hw is not None
            self.assertTrue(hw["is_aura_hd_e606c0"])
            self.assertEqual(hw["version"], "v1.7")
            self.assertEqual(hw["payload_size"], 39)
            self.assertEqual(hw["fields"]["bPCB"], 28)
            self.assertEqual(hw["decoded"]["bPCB"], "E606C0")
            self.assertEqual(hw["decoded"]["bDisplayResolution"], "1440x1080")
            self.assertEqual(hw["decoded"]["bFrontLight_LED_Driver"], "SY7201")

    def test_full_synthetic_disk_is_identified(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            p1, p2, p3 = build_image(image)
            result = inspect.inspect_source(str(image), {"name": "synthetic"}, True)
            self.assertTrue(result["readable"])
            self.assertTrue(result["aura_hd"])
            self.assertTrue(result["mbr"]["valid"])
            parts = result["mbr"]["partitions"]
            self.assertEqual([p["offset"] for p in parts], [p1, p2, p3])
            self.assertEqual([p["label"] for p in parts], ["rootfs", "recoveryfs", "KOBOeReader"])
            self.assertEqual(result["pre_p1_size"], p1)
            with image.open("rb") as f:
                expected = hashlib.sha256(f.read(p1)).hexdigest()
            self.assertEqual(result["pre_p1_sha256"], expected)

    def test_wrong_pcb_is_not_aura_hd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            with image.open("r+b") as f:
                f.seek(inspect.HWCONFIG_OFFSET + 16)
                f.write(b"\x1b")
            result = inspect.inspect_source(str(image), {}, False)
            self.assertFalse(result["aura_hd"])


if __name__ == "__main__":
    unittest.main()
