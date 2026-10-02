from __future__ import annotations

import builtins
import hashlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def mbr_entry(ptype: int, start_lba: int, sectors: int, boot: int = 0) -> bytes:
    entry = bytearray(16)
    entry[0] = boot
    entry[4] = ptype
    entry[8:12] = start_lba.to_bytes(4, "little")
    entry[12:16] = sectors.to_bytes(4, "little")
    return bytes(entry)


def build_image(
    path: Path,
    *,
    version: bytes = b"v1.7\x00",
    payload: bytes = KNOWN_PAYLOAD,
    image_size: int = 4 * 1024 * 1024,
) -> tuple[int, int, int]:
    p1_lba, p2_lba, p3_lba = 2048, 3072, 4096
    with path.open("wb") as f:
        f.truncate(image_size)
    with path.open("r+b") as f:
        mbr = bytearray(512)
        mbr[446:462] = mbr_entry(0x83, p1_lba, 1024)
        mbr[462:478] = mbr_entry(0x83, p2_lba, 1024)
        mbr[478:494] = mbr_entry(0x0C, p3_lba, 2048)
        mbr[510:512] = b"\x55\xaa"
        f.seek(0)
        f.write(mbr)
        header = b"HW CONFIG " + version + bytes([len(payload)])
        assert len(header) == 16
        f.seek(inspect.HWCONFIG_OFFSET)
        f.write(header + payload)
        for lba, label in ((p1_lba, b"rootfs"), (p2_lba, b"recoveryfs")):
            sb = bytearray(1024)
            sb[56:58] = b"\x53\xef"
            sb[120 : 120 + len(label)] = label
            f.seek(lba * 512 + 1024)
            f.write(sb)
        fat = bytearray(512)
        fat[71:82] = b"KOBOeReader "
        fat[82:90] = b"FAT32   "
        fat[510:512] = b"\x55\xaa"
        f.seek(p3_lba * 512)
        f.write(fat)
    return p1_lba * 512, p2_lba * 512, p3_lba * 512


class SectorAlignedReader:
    """Simulates Windows raw disks that reject unaligned low-level I/O."""

    def __init__(self, data: bytes):
        self._io = io.BytesIO(data)
        self.reads: list[tuple[int, int]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def fileno(self):
        raise AttributeError("no fileno")

    def tell(self):
        return self._io.tell()

    def seek(self, offset: int, whence: int = 0):
        if whence == 0 and offset % 512:
            raise OSError("unaligned seek")
        return self._io.seek(offset, whence)

    def read(self, size: int = -1) -> bytes:
        if self._io.tell() % 512:
            raise OSError("unaligned read position")
        if size != -1 and size % 512:
            raise OSError("unaligned read size")
        self.reads.append((self._io.tell(), size))
        return self._io.read(size)


class InspectAuraHDTests(unittest.TestCase):
    def test_known_hwconfig_decodes_as_confirmed_e606c0(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            with image.open("rb") as f:
                hw = inspect.parse_hwconfig(f)
            assert hw is not None
            self.assertTrue(hw["is_aura_hd_e606c0"])
            self.assertTrue(hw["format_confirmed"])
            self.assertEqual(hw["version"], "v1.7")
            self.assertEqual(hw["payload_size"], 39)
            self.assertEqual(hw["decoded"]["bPCB"], "E606C0")

    def test_full_synthetic_disk_is_identified_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            p1, p2, p3 = build_image(image)
            result = inspect.inspect_source(str(image), {"name": "synthetic"}, True)
            self.assertTrue(result["readable"])
            self.assertTrue(result["aura_hd"])
            self.assertTrue(result["mbr"]["valid"])
            self.assertEqual(result["source_size"], image.stat().st_size)
            parts = result["mbr"]["partitions"]
            self.assertEqual([p["offset"] for p in parts], [p1, p2, p3])
            self.assertEqual([p["label"] for p in parts], ["rootfs", "recoveryfs", "KOBOeReader"])
            with image.open("rb") as f:
                expected = hashlib.sha256(f.read(p1)).hexdigest()
            self.assertEqual(result["pre_p1_sha256"], expected)

    def test_full_inspection_works_with_sector_aligned_only_reader(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            p1, _, _ = build_image(image)
            reader = SectorAlignedReader(image.read_bytes())
            with mock.patch("builtins.open", return_value=reader):
                result = inspect.inspect_source("fake-physical-drive", {}, True)
            self.assertTrue(result["aura_hd"], result)
            self.assertEqual(result["source_size"], image.stat().st_size)
            self.assertEqual(result["pre_p1_size"], p1)
            self.assertTrue(reader.reads)
            self.assertTrue(all(pos % 512 == 0 for pos, _ in reader.reads))
            self.assertTrue(all(size == -1 or size % 512 == 0 for _, size in reader.reads))

    def test_pcb_28_with_unknown_hwconfig_format_is_not_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image, version=b"v0.1\x00", payload=b"\x1c")
            result = inspect.inspect_source(str(image), {}, False)
            self.assertFalse(result["aura_hd"])
            assert result["hwconfig"] is not None
            self.assertTrue(result["hwconfig"]["pcb_e606c0"])
            self.assertFalse(result["hwconfig"]["format_confirmed"])

    def test_partition_beyond_end_invalidates_confirmed_aura(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            with image.open("r+b") as f:
                mbr = bytearray(f.read(512))
                mbr[446:462] = mbr_entry(0x83, 100000, 1024)
                f.seek(0)
                f.write(mbr)
            result = inspect.inspect_source(str(image), {}, True)
            self.assertTrue(result["aura_hd"])
            self.assertFalse(result["mbr"]["valid"])
            self.assertTrue(result["errors"])
            self.assertFalse(result.get("pre_p1_sha256"))
            self.assertTrue(any("boot hash skipped" in w for w in result["warnings"]))

    def test_short_hwconfig_read_is_visible_as_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "short.img"
            image.write_bytes(b"\x00" * (inspect.HWCONFIG_OFFSET + 10))
            result = inspect.inspect_source(str(image), {}, False)
            self.assertTrue(any("HWCONFIG" in error for error in result["errors"]))

    def test_invalid_mbr_on_non_kobo_is_not_access_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "other.img"
            image.write_bytes(b"\x00" * (inspect.HWCONFIG_OFFSET + 4096))
            result = inspect.inspect_source(str(image), {}, False)
            self.assertFalse(result["aura_hd"])
            self.assertFalse(result["errors"], result)
            self.assertTrue(any("MBR:" in warning for warning in result["warnings"]))

    def test_invalid_boot_indicator_invalidates_mbr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            with image.open("r+b") as f:
                mbr = bytearray(f.read(512))
                mbr[446] = 0x7F
                f.seek(0)
                f.write(mbr)
            with image.open("rb") as f:
                mbr = inspect.parse_mbr(f, image.stat().st_size)
            self.assertFalse(mbr["valid"])
            self.assertTrue(any("boot indicator" in e for e in mbr["errors"]))

    def test_windows_candidates_handles_missing_powershell(self) -> None:
        diagnostics: list[str] = []
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("powershell")):
            self.assertEqual(inspect.windows_candidates(diagnostics), [])
        self.assertTrue(any("not found" in message.lower() for message in diagnostics))

    def test_windows_candidates_handles_timeout(self) -> None:
        diagnostics: list[str] = []
        timeout = subprocess.TimeoutExpired(cmd="powershell", timeout=15)
        with mock.patch("subprocess.run", side_effect=timeout):
            self.assertEqual(inspect.windows_candidates(diagnostics), [])
        self.assertTrue(any("timed out" in message.lower() for message in diagnostics))

    def test_inspection_never_requests_write_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "aura.img"
            build_image(image)
            original_open = builtins.open
            modes: list[str] = []

            def guarded_open(file, mode="r", *args, **kwargs):
                modes.append(mode)
                self.assertNotIn("w", mode)
                self.assertNotIn("a", mode)
                self.assertNotIn("+", mode)
                return original_open(file, mode, *args, **kwargs)

            with mock.patch("builtins.open", side_effect=guarded_open):
                result = inspect.inspect_source(str(image), {}, False)
            self.assertTrue(result["aura_hd"])
            self.assertTrue(modes)
            self.assertTrue(all(mode == "rb" for mode in modes))


if __name__ == "__main__":
    unittest.main()
