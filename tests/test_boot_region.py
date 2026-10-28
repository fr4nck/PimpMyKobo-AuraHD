"""Synthetic PRE-P1 regions only: no Kobo dump, U-Boot, kernel or waveform."""
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib
from contextlib import redirect_stdout

SOURCE = Path(__file__).resolve().parents[1] / "experimental/boot-region/boot_region.py"
SPEC = importlib.util.spec_from_file_location("pmkb_boot_region", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

BASE = 0x70000000  # SYNTHETIC; mirrors the documented i.MX50 CSD0 hypothesis
UBOOT_LOAD = BASE + 0x7800000


def put_ivt(region, offset, entry, self_ptr, boot_data, start, length, plugin):
    region[offset:offset + 4] = MOD.IVT_HEADER
    struct.pack_into("<5I", region, offset + 4, entry, 0, 0, boot_data, self_ptr)
    data_offset = offset + boot_data - self_ptr
    struct.pack_into("<3I", region, data_offset, start, length, plugin)
    return data_offset


def put_uimage(region, payload, *, load=BASE + 0x8000, entry=None, os_=5, arch=2):
    header = struct.pack(">7I4B32s", MOD.UIMAGE_MAGIC, 0, 1364428800, len(payload),
                         load, load if entry is None else entry,
                         zlib.crc32(payload) & 0xFFFFFFFF, os_, arch, 2, 0,
                         b"SYNTHETIC-2.6.35.3")
    hcrc = zlib.crc32(header) & 0xFFFFFFFF
    header = header[:4] + struct.pack(">I", hcrc) + header[8:]
    start = MOD.UIMAGE_OFFSET
    region[start:start + 64 + len(payload)] = header + payload


def synthetic_region(*, plugin=True):
    region = bytearray(MOD.REGION_SIZE)
    for index, (status, kind, start, sectors) in enumerate((
            (0, 0x83, MOD.P1_START, MOD.P1_SECTORS),
            (0, 0x83, MOD.P2_START, MOD.P2_SECTORS),
            (0, 0x0B, MOD.P3_START, 61267968))):
        entry = 446 + index * 16
        region[entry] = status
        region[entry + 4] = kind
        struct.pack_into("<II", region, entry + 8, start, sectors)
    region[510:512] = b"\x55\xaa"
    hw = MOD.HWCFG_OFFSET
    region[hw:hw + 16] = b"HW CONFIG v1.7\0" + bytes([39])
    region[hw + 16] = 28
    if plugin:
        # ROM plug-in in IRAM, then the SDRAM IVT copied with the card prefix.
        data = put_ivt(region, 0x400, 0xF8006000, 0xF8006000 - 0, 0xF8006020,
                       0xF8006000, 0x1000, 1)
        main = data + 12
        put_ivt(region, main, UBOOT_LOAD + 0x1000, UBOOT_LOAD + main,
                UBOOT_LOAD + main + 0x20, UBOOT_LOAD, 0x40000, 0)
    else:
        put_ivt(region, 0x400, UBOOT_LOAD + 0x1000, UBOOT_LOAD + 0x400,
                UBOOT_LOAD + 0x420, UBOOT_LOAD, 0x40000, 0)
    zimage = bytearray(0x300000)
    struct.pack_into("<III", zimage, 0x24, MOD.ZIMAGE_MAGIC, 0, len(zimage))
    put_uimage(region, bytes(zimage))
    region[MOD.WAVEFORM_OFFSET:MOD.WAVEFORM_OFFSET + 4] = MOD.WAVEFORM_MAGIC
    return region


def results(report):
    return {check["id"]: check["result"] for check in report["checks"]}


class BootRegionTests(unittest.TestCase):
    def test_synthetic_region_is_consistent_but_never_a_boot_proof(self):
        for plugin in (True, False):
            with self.subTest(plugin=plugin):
                report = MOD.analyze_region(bytes(synthetic_region(plugin=plugin)))
                self.assertEqual("consistent_unverified", report["status"], report["checks"])
                self.assertFalse(report["boot_verified"])
                self.assertFalse(report["hardware_verified"])
                self.assertEqual("UNQUALIFIED", results(report)["u_boot_handoff"])
                self.assertEqual(plugin, report["fields"]["uboot"]["rom_plugin"])
                uimage = report["fields"]["uimage"]
                self.assertEqual((BASE + 0x8000, BASE + 0x8000),
                                 (uimage["load"], uimage["entry"]))
                self.assertEqual(("linux", "arm", "kernel", "none"),
                                 (uimage["os"], uimage["arch"], uimage["type"], uimage["comp"]))
                self.assertEqual({"start": 0, "end": 0x300000}, uimage["zimage"])
                self.assertEqual(28, report["fields"]["hwconfig"]["pcb"])

    def test_each_corruption_is_refused_with_its_own_check(self):
        cases = (
            ("mbr_signature", lambda r: r.__setitem__(slice(510, 512), b"\0\0")),
            ("mbr_p1", lambda r: struct.pack_into("<I", r, 446 + 8, MOD.P1_START + 1)),
            ("mbr_p2", lambda r: r.__setitem__(462 + 4, 0x0B)),
            ("mbr_p3", lambda r: r.__setitem__(478 + 4, 0x83)),
            ("mbr_p3", lambda r: struct.pack_into("<I", r, 478 + 8, MOD.P3_START + 8)),
            ("mbr_p4_unused", lambda r: r.__setitem__(494 + 4, 0x83)),
            ("hwconfig_magic", lambda r: r.__setitem__(MOD.HWCFG_OFFSET, 0)),
            ("hwconfig_bounds", lambda r: r.__setitem__(MOD.HWCFG_OFFSET + 15, 0)),
            ("hwconfig_pcb_e606c0", lambda r: r.__setitem__(MOD.HWCFG_OFFSET + 16, 11)),
            ("ivt_first", lambda r: r.__setitem__(0x400, 0)),
            ("uimage_magic", lambda r: r.__setitem__(MOD.UIMAGE_OFFSET, 0)),
            ("uimage_header_crc", lambda r: r.__setitem__(MOD.UIMAGE_OFFSET + 32, 0x55)),
            ("uimage_data_crc", lambda r: r.__setitem__(MOD.UIMAGE_OFFSET + 64 + 9, 1)),
            ("waveform_magic", lambda r: r.__setitem__(MOD.WAVEFORM_OFFSET, 0)),
        )
        for check, corrupt in cases:
            with self.subTest(check=check):
                region = synthetic_region()
                corrupt(region)
                report = MOD.analyze_region(bytes(region))
                self.assertEqual("refused", report["status"])
                self.assertEqual("FAIL", results(report)[check])

    def test_uimage_header_fields_are_bounded_and_typed(self):
        payload = bytes(0x1000)
        for check, kwargs in (
                ("uimage_linux_arm_kernel", {"arch": 3}),
                ("uimage_load_entry", {"load": BASE - 0x8000}),
                ("uimage_load_entry", {"entry": BASE + 0x8000 + 0x1000})):
            with self.subTest(check=check, kwargs=kwargs):
                region = synthetic_region()
                region[MOD.UIMAGE_OFFSET:MOD.WAVEFORM_OFFSET] = bytes(
                    MOD.WAVEFORM_OFFSET - MOD.UIMAGE_OFFSET)
                put_uimage(region, payload, **kwargs)
                report = MOD.analyze_region(bytes(region))
                self.assertEqual("FAIL", results(report)[check])
                self.assertEqual("refused", report["status"])

    def test_kernel_above_128mib_is_flagged_not_refused(self):
        region = synthetic_region()
        region[MOD.UIMAGE_OFFSET:MOD.WAVEFORM_OFFSET] = bytes(
            MOD.WAVEFORM_OFFSET - MOD.UIMAGE_OFFSET)
        put_uimage(region, bytes(0x1000), load=BASE + 0x9000000)
        report = MOD.analyze_region(bytes(region))
        self.assertEqual("UNQUALIFIED", results(report)["uimage_first_128mib"])
        self.assertEqual("consistent_unverified", report["status"])

    def test_uimage_size_cannot_reach_the_waveform(self):
        region = synthetic_region()
        too_big = MOD.WAVEFORM_OFFSET - MOD.UIMAGE_OFFSET - 64 + 1
        struct.pack_into(">I", region, MOD.UIMAGE_OFFSET + 12, too_big)
        report = MOD.analyze_region(bytes(region))
        self.assertEqual("FAIL", results(report)["uimage_payload_bounds"])
        self.assertNotIn("uimage_data_crc", results(report))

    def test_uboot_must_stay_below_hwconfig_and_inside_ram(self):
        region = synthetic_region(plugin=False)
        struct.pack_into("<I", region, 0x420 + 4, MOD.HWCFG_OFFSET + 1)  # length
        self.assertEqual("FAIL", results(MOD.analyze_region(bytes(region)))["uboot_extent"])
        region = synthetic_region(plugin=False)
        struct.pack_into("<I", region, 0x404, UBOOT_LOAD + 0x40000)  # entry past image
        self.assertEqual("FAIL", results(MOD.analyze_region(bytes(region)))["uboot_extent"])
        region = synthetic_region(plugin=False)
        report = MOD.analyze_region(bytes(region), ram_base=0x80000000)
        self.assertEqual("FAIL", results(report)["uboot_extent"])
        region = synthetic_region(plugin=False)
        struct.pack_into("<I", region, 0x410, 0xFFFFFFF0)  # boot data outside image
        self.assertEqual("FAIL", results(MOD.analyze_region(bytes(region)))["ivt_first"])

    def test_main_ivt_must_not_be_another_plugin(self):
        region = synthetic_region()
        struct.pack_into("<I", region, 0x44C + 8, 1)
        self.assertEqual("FAIL", results(MOD.analyze_region(bytes(region)))["uboot_extent"])

    def test_plugin_without_following_ivt_is_refused(self):
        region = synthetic_region()
        data = 0x420
        region[data + 12:data + 16] = b"\0\0\0\0"
        report = MOD.analyze_region(bytes(region))
        self.assertEqual("FAIL", results(report)["ivt_main_after_plugin"])

    def test_wrong_types_and_sizes_fail_closed_without_exceptions(self):
        for value, kwargs in ((bytearray(MOD.REGION_SIZE), {}), (None, {}),
                              ("x", {}), (bytes(MOD.REGION_SIZE), {"ram_base": True}),
                              (bytes(MOD.REGION_SIZE), {"ram_base": 0x70000001}),
                              (bytes(MOD.REGION_SIZE), {"ram_base": 0xF0000000})):
            report = MOD.analyze_region(value, **kwargs)
            self.assertEqual("FAIL", results(report)["input"])
        for size in (0, MOD.REGION_SIZE - 1, MOD.REGION_SIZE + 1):
            report = MOD.analyze_region(bytes(size))
            self.assertEqual(["region_size"], list(results(report)))
        report = MOD.analyze_region(bytes(MOD.REGION_SIZE))
        self.assertEqual("refused", report["status"])

    def test_virtual_card_keeps_p1_and_fits_one_gib(self):
        plan = MOD.virtual_card_plan()
        self.assertEqual(1 << 30, plan["total_bytes"])
        segments = {s["source"]: s for s in plan["segments"]}
        self.assertEqual((9961472, 268435968), (segments["p1"]["offset"], segments["p1"]["length"]))
        self.assertEqual(278397440, segments["p2"]["offset"])
        self.assertEqual(546833408, segments["fresh_fat32"]["offset"])
        self.assertTrue(segments["p1"]["change"].startswith("none"))
        self.assertEqual(0, segments["unpartitioned"]["length"])
        self.assertEqual(plan["mbr_p3_sectors"] * 512, segments["fresh_fat32"]["length"])
        ends = [s["offset"] + s["length"] for s in plan["segments"]]
        starts = [s["offset"] for s in plan["segments"][1:]]
        self.assertTrue(all(e <= s for e, s in zip(ends, starts)))
        small = MOD.virtual_card_plan(p3_bytes=64 * 1024 * 1024)
        self.assertEqual(1 << 30, small["total_bytes"])
        for bad in (True, 1024, 64 * 1024 * 1024 + 1):
            with self.assertRaises(ValueError):
                MOD.virtual_card_plan(p3_bytes=bad)

    def test_pure_api_does_not_open_files_or_run_processes(self):
        region = bytes(synthetic_region())
        with patch("builtins.open", side_effect=AssertionError("file I/O")), \
             patch("subprocess.run", side_effect=AssertionError("subprocess")):
            self.assertEqual("consistent_unverified", MOD.analyze_region(region)["status"])
            MOD.virtual_card_plan()

    @patch.object(MOD, "P1_SECTORS", 8)  # keep the synthetic P1 tiny
    def test_cli_reads_images_and_requires_the_sealed_p1_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pre = Path(tmp, "pre.img")
            pre.write_bytes(bytes(synthetic_region()))
            p1 = Path(tmp, "p1.img")
            with p1.open("wb") as handle:
                handle.truncate(8 * 512)
                handle.seek(1080)
                handle.write(b"\x53\xef")
            before = pre.read_bytes(), p1.stat().st_size
            out = io.StringIO()
            with redirect_stdout(out):
                code = MOD.main([str(pre), "--p1", str(p1)])
            report = json.loads(out.getvalue())
            self.assertEqual(1, code)
            self.assertEqual("refused", report["status"])
            p1_checks = {c["id"]: c["result"] for c in report["p1"]["checks"]}
            self.assertEqual({"size": "PASS", "ext_magic": "PASS",
                              "sealed_sha256": "FAIL"}, p1_checks)
            self.assertEqual(before, (pre.read_bytes(), p1.stat().st_size))
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(0, MOD.main([str(pre)]))
            with self.assertRaises(ValueError):
                MOD.main([tmp])
        if os.path.exists("/dev/null"):
            with self.assertRaises(ValueError):
                MOD.main(["/dev/null"])


if __name__ == "__main__":
    unittest.main()
