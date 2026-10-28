"""Read-only qualification of the Aura HD E606C0 PRE-P1 boot region.

Decodes the structures that the i.MX50 ROM, U-Boot and Linux consume from the
raw area before P1: MBR geometry, Netronix HWCONFIG, i.MX IVT/plug-in chain,
U-Boot uImage header and the Netronix waveform marker. It also plans a compact
virtual card that keeps P1 byte-identical for an emulator.

analyze_region() and virtual_card_plan() are pure: no file, device, network or
subprocess access. main() only opens regular files read-only. Nothing here
certifies a boot, U-Boot behaviour, kernel registers or E-Ink hardware.
"""
import argparse
import hashlib
import json
import os
import stat
import struct
import sys
import zlib

SECTOR = 512
# PMKB reference geometry (docs/partition-layout-fr.md).
P1_START, P1_SECTORS = 19456, 524289
P2_START, P2_SECTORS = 543745, 524289
P3_START = P2_START + P2_SECTORS
REGION_SIZE = P1_START * SECTOR
HWCFG_OFFSET = 0x80000
UIMAGE_OFFSET = 0x100000
WAVEFORM_OFFSET = 0x700000
WAVEFORM_MAGIC = b"\xff\xf5\xaf\xff"
IVT_OFFSET = 0x400
IVT_HEADER = b"\xd1\x00\x20\x40"
UIMAGE_MAGIC = 0x27051956
UIMAGE_HEADER = 64
ZIMAGE_MAGIC = 0x016F2818
RAM_SIZE = 512 * 1024 * 1024
# i.MX50 CSD0 base used by the Aura HD U-Boot IVT and the QEMU board model;
# an inference until read from the device's own U-Boot/ATAG_MEM.
DEFAULT_RAM_BASE = 0x70000000
SEALED_P1_NAME = "PMKB-FIRST-BOOT-1-0b00d858.img"
SEALED_P1_SHA256 = "7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c"
FAT32_TYPES = (0x0B, 0x0C)
UIMAGE_OS = {5: "linux"}
UIMAGE_ARCH = {2: "arm"}
UIMAGE_TYPE = {2: "kernel"}
UIMAGE_COMP = {0: "none", 1: "gzip", 2: "bzip2", 3: "lzma", 4: "lzo"}


class _Report:
    def __init__(self):
        self.checks = []
        self.fields = {}

    def add(self, check_id, ok, detail, *, unqualified=False):
        result = "UNQUALIFIED" if unqualified else ("PASS" if ok else "FAIL")
        self.checks.append({"id": check_id, "result": result, "detail": detail})
        return ok


def _u32le(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _mbr(report, data):
    if not report.add("mbr_signature", data[510:512] == b"\x55\xaa",
                      "0x55AA at bytes 510-511"):
        return
    entries = []
    for index in range(4):
        raw = data[446 + index * 16:462 + index * 16]
        start, sectors = struct.unpack_from("<II", raw, 8)
        entries.append({"status": raw[0], "type": raw[4],
                        "start_sector": start, "sectors": sectors})
    report.fields["partitions"] = entries
    expected = ((P1_START, P1_SECTORS, (0x83,)), (P2_START, P2_SECTORS, (0x83,)))
    for number, (entry, (start, sectors, types)) in enumerate(zip(entries, expected), 1):
        report.add("mbr_p%d" % number,
                   entry["status"] in (0, 0x80) and entry["type"] in types and
                   entry["start_sector"] == start and entry["sectors"] == sectors,
                   "P%d type 0x83 start %d sectors %d" % (number, start, sectors))
    p3 = entries[2]
    report.add("mbr_p3", p3["status"] in (0, 0x80) and p3["type"] in FAT32_TYPES and
               p3["start_sector"] == P3_START and p3["sectors"] > 0 and
               p3["start_sector"] + p3["sectors"] <= 1 << 32,
               "P3 FAT32 start %d, non-empty" % P3_START)
    report.add("mbr_p4_unused", not any(data[494:510]), "fourth entry empty")


def _hwconfig(report, data):
    block = data[HWCFG_OFFSET:HWCFG_OFFSET + SECTOR]
    if not report.add("hwconfig_magic", block[:10] == b"HW CONFIG ",
                      "'HW CONFIG ' at 0x80000"):
        return
    version = block[10:15].split(b"\0", 1)[0].decode("ascii", "replace")
    size = block[15]
    report.fields["hwconfig"] = {"version": version, "payload_size": size,
                                 "pcb": block[16] if size else None}
    report.add("hwconfig_bounds", 0 < size <= SECTOR - 16,
               "declared payload fits its sector")
    report.add("hwconfig_pcb_e606c0", size > 0 and block[16] == 28,
               "bPCB 28 = E606C0 (not an ARM machine ID)")


def _ivt(data, offset, limit):
    if offset < 0 or offset + 0x20 > limit or data[offset:offset + 4] != IVT_HEADER:
        return None
    entry, _, dcd, boot_data, self_ptr = struct.unpack_from("<5I", data, offset + 4)
    if not self_ptr <= boot_data <= self_ptr + (limit - offset) - 12:
        return None
    data_offset = offset + boot_data - self_ptr
    start, length, plugin = struct.unpack_from("<3I", data, data_offset)
    return {"card_offset": offset, "entry": entry, "dcd": dcd, "self": self_ptr,
            "boot_data_offset": data_offset, "start": start, "length": length,
            "plugin": plugin}


def _uboot(report, data, ram_base):
    first = _ivt(data, IVT_OFFSET, HWCFG_OFFSET)
    if not report.add("ivt_first", first is not None,
                      "IVT D1 00 20 40 at 0x400 with in-image boot data"):
        return
    chain = [first]
    main = first
    if first["plugin"] == 1:
        main = _ivt(data, first["boot_data_offset"] + 12, HWCFG_OFFSET)
        if not report.add("ivt_main_after_plugin", main is not None,
                          "main IVT follows the ROM plug-in boot data"):
            return
        chain.append(main)
    report.fields["uboot_ivt"] = chain
    begin = main["card_offset"] - (main["self"] - main["start"])
    end = begin + main["length"]
    ram_end = ram_base + RAM_SIZE
    ok = (main["plugin"] == 0 and main["self"] >= main["start"] and
          0 <= begin <= main["card_offset"] and main["length"] > 0 and
          end <= HWCFG_OFFSET and
          ram_base <= main["start"] and main["start"] + main["length"] <= ram_end and
          main["start"] <= main["entry"] < main["start"] + main["length"])
    report.fields["uboot"] = {"card_begin": begin, "card_end": end,
                              "load": main["start"], "entry": main["entry"],
                              "rom_plugin": first["plugin"] == 1}
    report.add("uboot_extent", ok,
               "main image below HWCONFIG, loaded and entered inside declared RAM")


def _uimage(report, data, ram_base):
    header = data[UIMAGE_OFFSET:UIMAGE_OFFSET + UIMAGE_HEADER]
    fields = struct.unpack(">7I4B32s", header)
    magic, hcrc, timestamp, size, load, entry, dcrc, os_, arch, type_, comp, name = fields
    if not report.add("uimage_magic", magic == UIMAGE_MAGIC, "0x27051956 at 0x100000"):
        return
    zeroed = header[:4] + b"\0\0\0\0" + header[8:]
    report.add("uimage_header_crc", zlib.crc32(zeroed) & 0xFFFFFFFF == hcrc,
               "header CRC32 with ih_hcrc zeroed")
    payload_end = UIMAGE_OFFSET + UIMAGE_HEADER + size
    fits = report.add("uimage_payload_bounds", 0 < size and payload_end <= WAVEFORM_OFFSET,
                      "payload ends before the waveform at 0x700000")
    payload = data[UIMAGE_OFFSET + UIMAGE_HEADER:payload_end] if fits else b""
    if fits:
        report.add("uimage_data_crc", zlib.crc32(payload) & 0xFFFFFFFF == dcrc,
                   "payload CRC32")
    info = {"size": size, "load": load, "entry": entry, "timestamp": timestamp,
            "os": UIMAGE_OS.get(os_, os_), "arch": UIMAGE_ARCH.get(arch, arch),
            "type": UIMAGE_TYPE.get(type_, type_), "comp": UIMAGE_COMP.get(comp, comp),
            "name": name.split(b"\0", 1)[0].decode("ascii", "replace")}
    report.add("uimage_linux_arm_kernel", (os_, arch, type_) == (5, 2, 2),
               "ih_os linux, ih_arch arm, ih_type kernel")
    if fits and comp == 0 and len(payload) >= 0x30 and _u32le(payload, 0x24) == ZIMAGE_MAGIC:
        z_start, z_end = _u32le(payload, 0x28), _u32le(payload, 0x2C)
        info["zimage"] = {"start": z_start, "end": z_end}
        report.add("zimage_size", z_start < z_end and z_end - z_start <= size,
                   "zImage end-start within ih_size")
    report.fields["uimage"] = info
    in_ram = ram_base <= load < ram_base + RAM_SIZE and load <= entry < load + size
    report.add("uimage_load_entry", in_ram, "ih_load/ih_ep inside declared RAM and payload")
    # booting.rst: zImage should sit in the first 128 MiB of RAM. Advisory:
    # a fixed-zreladdr 2.6.35 zImage may still relocate itself.
    report.add("uimage_first_128mib", True,
               "load within first 128 MiB (booting.rst recommendation)",
               unqualified=not (in_ram and load - ram_base < 128 * 1024 * 1024))


def analyze_region(region, *, ram_base=DEFAULT_RAM_BASE):
    """Decode a complete PRE-P1 region (bytes); never authorizes any write."""
    report = _Report()
    result = {"status": "refused", "scope": "pre_p1_bytes_only",
              "boot_verified": False, "hardware_verified": False,
              "ram_base_assumed": ram_base, "checks": report.checks,
              "fields": report.fields}
    if type(region) is not bytes or type(ram_base) is not int or \
            not 0 <= ram_base <= (1 << 32) - RAM_SIZE or ram_base % 4096:
        report.add("input", False, "bytes region and 4 KiB-aligned 32-bit RAM base")
        return result
    if not report.add("region_size", len(region) == REGION_SIZE,
                      "%d bytes = P1 start x 512" % REGION_SIZE):
        return result
    _mbr(report, region)
    _hwconfig(report, region)
    # Extents are bounded by the next structure: U-Boot < HWCONFIG < uImage < waveform.
    _uboot(report, region, ram_base)
    _uimage(report, region, ram_base)
    report.add("waveform_magic",
               region[WAVEFORM_OFFSET:WAVEFORM_OFFSET + 4] == WAVEFORM_MAGIC,
               "Netronix ff f5 af ff at 0x700000; length/format not decoded")
    report.add("u_boot_handoff", False,
               "machine ID, ATAG/DTB pointer and cmdline need U-Boot code or a boot log",
               unqualified=True)
    if all(c["result"] != "FAIL" for c in report.checks):
        result["status"] = "consistent_unverified"
    return result


def virtual_card_plan(*, p3_bytes=None, power_of_two=True):
    """Layout of a compact emulator card that copies P1/P2 unchanged."""
    p3_offset = P3_START * SECTOR
    if p3_bytes is None:
        total = 1 << 30
        p3_bytes = total - p3_offset
    elif type(p3_bytes) is not int or p3_bytes < 32 * 1024 * 1024 or p3_bytes % SECTOR:
        raise ValueError("P3 must be a sector multiple of at least 32 MiB (FAT32)")
    end = p3_offset + p3_bytes
    total = 1 << (end - 1).bit_length() if power_of_two else end
    return {
        "total_bytes": total,
        "mbr_p3_sectors": p3_bytes // SECTOR,
        "segments": [
            {"offset": 0, "length": REGION_SIZE, "source": "pre_p1",
             "change": "MBR P3 size only"},
            {"offset": P1_START * SECTOR, "length": P1_SECTORS * SECTOR,
             "source": "p1", "change": "none: byte-identical, verify SHA-256 after copy"},
            {"offset": P2_START * SECTOR, "length": P2_SECTORS * SECTOR,
             "source": "p2", "change": "none"},
            {"offset": p3_offset, "length": p3_bytes, "source": "fresh_fat32",
             "change": "new empty KOBOeReader volume, no user data"},
            {"offset": end, "length": total - end, "source": "unpartitioned",
             "change": "zero padding for a power-of-two SD size"},
        ],
        "run_requirements": ["machine imx50-kobo-aura-hd, 512 MiB",
                             "U-Boot from this card's own PRE-P1 (not distributed)",
                             "disk opened read-only or in snapshot mode"],
        "boot_verified": False,
    }


def _regular_file(path):
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("%s: only regular image files are accepted" % path)
    return info.st_size


def _partition_image(path, sectors, sealed):
    size = _regular_file(path)
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        magic = handle.read(1082)[1080:1082]
        handle.seek(0)
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    sha = digest.hexdigest()
    checks = [{"id": "size", "result": "PASS" if size == sectors * SECTOR else "FAIL",
               "detail": "%d bytes" % (sectors * SECTOR)},
              {"id": "ext_magic", "result": "PASS" if magic == b"\x53\xef" else "FAIL",
               "detail": "ext superblock magic"}]
    if sealed:
        checks.append({"id": "sealed_sha256",
                       "result": "PASS" if sha == SEALED_P1_SHA256 else "FAIL",
                       "detail": SEALED_P1_NAME})
    return {"sha256": sha, "size": size, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pre_p1", help="PRE-P1 region image (9,961,472 bytes)")
    parser.add_argument("--p1", help="P1 image expected to be the sealed FIRST BOOT")
    parser.add_argument("--p2", help="P2 recoveryfs image")
    args = parser.parse_args(argv)
    if _regular_file(args.pre_p1) != REGION_SIZE:
        report = analyze_region(b"")
    else:
        with open(args.pre_p1, "rb") as handle:
            report = analyze_region(handle.read(REGION_SIZE + 1))
    if args.p1:
        report["p1"] = _partition_image(args.p1, P1_SECTORS, True)
    if args.p2:
        report["p2"] = _partition_image(args.p2, P2_SECTORS, False)
    report["virtual_card_plan"] = virtual_card_plan()
    failed = [c for part in ("p1", "p2") if part in report
              for c in report[part]["checks"] if c["result"] == "FAIL"]
    if failed:
        report["status"] = "refused"
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["status"] == "consistent_unverified" else 1


if __name__ == "__main__":
    sys.exit(main())
