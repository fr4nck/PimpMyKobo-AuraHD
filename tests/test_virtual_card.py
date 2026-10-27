"""Synthetic virtual-card assembly: miniature P1/P2, no Kobo data or device."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pmkb_virtual_card", ROOT / "experimental/boot-region/virtual_card.py")
VC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VC)
BR = VC.BR
TBR_SPEC = importlib.util.spec_from_file_location(
    "pmkb_test_boot_region", ROOT / "tests/test_boot_region.py")
TBR = importlib.util.module_from_spec(TBR_SPEC)
TBR_SPEC.loader.exec_module(TBR)

MINI = 64  # sectors per synthetic P1/P2; real geometry is 524289
P3_BYTES = 64 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ext_image(seed):
    data = bytearray(bytes([seed]) * (MINI * 512))
    data[1080:1082] = b"\x53\xef"
    return bytes(data)


class VirtualCardTests(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        for name, value in (("P1_SECTORS", MINI), ("P2_START", BR.P1_START + MINI),
                            ("P2_SECTORS", MINI), ("P3_START", BR.P1_START + 2 * MINI)):
            stack.enter_context(patch.object(BR, name, value))
        stack.enter_context(patch.object(TBR, "MOD", BR))
        tmp = stack.enter_context(tempfile.TemporaryDirectory())
        self.dir = Path(tmp)
        self.region = bytes(TBR.synthetic_region())
        self.p1_data, self.p2_data = ext_image(0x11), ext_image(0x22)
        self.pre = self.write("pre.img", self.region)
        self.p1 = self.write("p1.img", self.p1_data)
        self.p2 = self.write("p2.img", self.p2_data)

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def compose(self, name="card.img", **kwargs):
        options = {"expected_p2_sha256": sha(self.p2_data),
                   "expected_p1_sha256": sha(self.p1_data), "p3_bytes": P3_BYTES}
        options.update(kwargs)
        return VC.compose(self.pre, self.p1, self.p2, self.dir / name, **options)

    def assert_refused(self, message, **kwargs):
        before = sorted(os.listdir(self.dir))
        with self.assertRaisesRegex(VC.CardError, message):
            self.compose(**kwargs)
        self.assertEqual(before, sorted(os.listdir(self.dir)))  # no output, no temp

    def test_assembles_byte_exact_card_with_fresh_fat32(self):
        inputs = [p.read_bytes() for p in (self.pre, self.p1, self.p2)]
        with patch("subprocess.run", side_effect=AssertionError("subprocess")):
            report = self.compose()
        self.assertEqual("assembled_unverified_boot", report["status"])
        self.assertFalse(report["boot_verified"])
        self.assertTrue(all(c["result"] == "PASS" for c in report["checks"]), report["checks"])
        self.assertEqual(128 * 1024 * 1024, report["total_bytes"])
        card = (self.dir / "card.img").read_bytes()
        self.assertEqual(report["image_sha256"], sha(card))
        self.assertTrue(set(report["pre_p1_changed_bytes"]) <= set(range(490, 494)))
        self.assertTrue(report["pre_p1_changed_bytes"])
        self.assertEqual(self.region[:490] + self.region[494:],
                         card[:490] + card[494:BR.REGION_SIZE])
        self.assertEqual(P3_BYTES // 512, struct.unpack_from("<I", card, 490)[0])
        p1_at, p2_at = BR.P1_START * 512, BR.P2_START * 512
        self.assertEqual(self.p1_data, card[p1_at:p1_at + MINI * 512])
        self.assertEqual(self.p2_data, card[p2_at:p2_at + MINI * 512])
        p3_at = BR.P3_START * 512
        self.assertEqual(b"KOBOeReader", card[p3_at + 71:p3_at + 82])
        self.assertEqual(BR.P3_START, struct.unpack_from("<I", card, p3_at + 28)[0])
        self.assertFalse(any(card[p3_at + P3_BYTES:]))
        self.assertEqual(inputs, [p.read_bytes() for p in (self.pre, self.p1, self.p2)])
        self.assertEqual(["card.img", "p1.img", "p2.img", "pre.img"], sorted(os.listdir(self.dir)))

    def test_assembly_is_reproducible(self):
        first = self.compose("a.img")["image_sha256"]
        self.assertEqual(first, self.compose("b.img")["image_sha256"])

    def test_existing_output_is_never_overwritten(self):
        self.write("card.img", b"keep")
        self.assert_refused("already exists")
        self.assertEqual(b"keep", (self.dir / "card.img").read_bytes())

    def test_sha256_contracts_before_copy(self):
        self.assert_refused("p1: SHA-256", expected_p1_sha256=BR.SEALED_P1_SHA256)
        self.assert_refused("p2: SHA-256", expected_p2_sha256="0" * 64)
        self.assert_refused("64 lowercase hex", expected_p2_sha256="A" * 64)
        self.assert_refused("64 lowercase hex", expected_p1_sha256=None)

    def test_input_files_are_validated(self):
        self.write("p1.img", self.p1_data[:-512])
        self.assert_refused("p1: size")
        self.write("p1.img", b"\0" * (MINI * 512))
        self.assert_refused("p1: no ext superblock")
        self.write("p1.img", self.p1_data)
        bad = bytearray(self.region)
        bad[BR.UIMAGE_OFFSET + 64 + 9] ^= 1
        self.write("pre.img", bytes(bad))
        self.assert_refused("uimage_data_crc")
        self.write("pre.img", self.region[:-1])
        self.assert_refused("pre_p1: size")
        with self.assertRaisesRegex(VC.CardError, "regular"):
            VC.compose(self.dir, self.p1, self.p2, self.dir / "x.img",
                       expected_p2_sha256=sha(self.p2_data))
        with self.assertRaisesRegex(VC.CardError, "output directory"):
            self.compose(name="missing/card.img")
        if os.path.isdir("/dev"):
            with self.assertRaisesRegex(VC.CardError, "outside /dev"):
                VC.compose(self.pre, self.p1, self.p2, "/dev/pmkb-virtual-test.img",
                           expected_p2_sha256=sha(self.p2_data))
            self.assertFalse(os.path.lexists("/dev/pmkb-virtual-test.img"))

    def test_virtual_profile_bounds(self):
        self.assert_refused(">= 64 MiB", p3_bytes=48 * 1024 * 1024)
        self.assert_refused("<= 2 GiB", p3_bytes=3 * 1024 * 1024 * 1024)
        self.assertLess(VC.MIN_P3_BYTES, 1024 * 1024 * 1024)  # physical profile keeps 1 GiB

    def test_failed_read_back_publishes_nothing(self):
        with patch.object(VC, "verify_fat32", return_value=["fat32_tables"]):
            self.assert_refused("fat32_tables")

    def inject(self, card_offset, data):
        """Fault injection: one extra write at an absolute card offset."""
        original = VC.fat32_structures

        def corrupted(*args):
            geo, writes = original(*args)
            return geo, writes + [(card_offset - BR.P3_START * 512, data)]
        return patch.object(VC, "fat32_structures", corrupted)

    def test_post_copy_read_back_catches_corruption(self):
        for check, offset, data in (
                ("pre_p1_only_p3_size_changed", 100, b"X"),
                ("pre_p1_only_p3_size_changed", 490, b"\x01"),
                ("p1_sha256_after", BR.P1_START * 512 + 4000, b"X"),
                ("p2_sha256_after", BR.P2_START * 512 + 4000, b"X"),
                ("pre_p1_reanalysis", BR.UIMAGE_OFFSET + 64 + 9, b"\x07")):
            with self.subTest(check=check, offset=offset), self.inject(offset, data):
                self.assert_refused(check)

    def test_output_created_during_assembly_is_not_overwritten(self):
        target = self.dir / "card.img"
        real_mkstemp = VC.tempfile.mkstemp

        def racing_mkstemp(**kwargs):
            target.write_bytes(b"other")
            return real_mkstemp(**kwargs)
        with patch.object(VC.tempfile, "mkstemp", racing_mkstemp):
            with self.assertRaisesRegex(VC.CardError, "appeared during assembly"):
                self.compose()
        self.assertEqual(b"other", target.read_bytes())
        self.assertEqual(["card.img", "p1.img", "p2.img", "pre.img"], sorted(os.listdir(self.dir)))

    def test_fat32_verifier_detects_corruption(self):
        sectors = P3_BYTES // 512
        geo, writes = VC.fat32_structures(sectors, 7, 1)
        clean = bytearray(P3_BYTES)
        for at, data in writes:
            clean[at:at + len(data)] = data
        self.assertEqual([], VC.verify_fat32(io.BytesIO(bytes(clean)), 0, sectors, 7))
        fat2 = (VC.RESERVED_SECTORS + geo["fat_sectors"]) * 512
        root = geo["data_start"] * 512
        for check, offset in (("fat32_boot_sector", 13), ("fat32_label", 71),
                              ("fat32_backup", 6 * 512 + 3), ("fat32_fsinfo", 512 + 488),
                              ("fat32_tables", fat2 + 40), ("fat32_root_label", root + 64)):
            with self.subTest(check=check):
                broken = bytearray(clean)
                broken[offset] ^= 0x01
                self.assertIn(check, VC.verify_fat32(io.BytesIO(bytes(broken)), 0, sectors, 7))
        both = bytearray(clean)
        for fat in (VC.RESERVED_SECTORS, VC.RESERVED_SECTORS + geo["fat_sectors"]):
            both[fat * 512 + 20] = 0x05  # same stray cluster entry in both FATs
        self.assertIn("fat32_tables", VC.verify_fat32(io.BytesIO(bytes(both)), 0, sectors, 7))
        self.assertIn("fat32_boot_sector", VC.verify_fat32(io.BytesIO(bytes(clean)), 0, sectors, 8))
        for bad in (True, 32, 60000):
            with self.assertRaises(VC.CardError):
                VC.fat32_geometry(bad)

    def test_cli_requires_the_sealed_p1(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = VC.main([str(self.pre), str(self.p1), str(self.p2),
                            str(self.dir / "card.img"),
                            "--expected-p2-sha256", sha(self.p2_data), "--p3-mib", "64"])
        report = json.loads(out.getvalue())
        self.assertEqual((1, "refused"), (code, report["status"]))
        self.assertIn("p1: SHA-256", report["error"])
        self.assertFalse((self.dir / "card.img").exists())


if __name__ == "__main__":
    unittest.main()
