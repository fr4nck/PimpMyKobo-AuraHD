"""Assemble a compact Aura HD E606C0 card image for an emulator (files only).

Profile "virtual-qemu": distinct from the physical replacement profile of
tools/replace-microsd-linux.py (PR #7), whose P3 minimum stays 1 GiB. Here P3
may be smaller because QEMU needs a power-of-two card, not a real userstore.

The output is a NEW regular file: PRE-P1 copied unchanged except the four MBR
bytes holding the P3 size, P1/P2 copied byte for byte with SHA-256 checked
before and after the copy, and a fresh empty FAT32 "KOBOeReader" volume
written in pure Python. No device, mount, subprocess or network access.
Nothing here boots or qualifies the image on hardware.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile

_SPEC = importlib.util.spec_from_file_location(
    "pmkb_boot_region", Path(__file__).resolve().with_name("boot_region.py"))
BR = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BR)

PROFILE = "virtual-qemu"
SECTOR = 512
MBR_P3_SIZE_OFFSET = 446 + 2 * 16 + 12
MIN_P3_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
FAT_LABEL = b"KOBOeReader"
RESERVED_SECTORS = 32
NUM_FATS = 2
FAT32_MIN_CLUSTERS = 65525
FAT32_EOC = 0x0FFFFFFF
CHUNK = 4 * 1024 * 1024


class CardError(ValueError):
    pass


def fat32_geometry(total_sectors):
    """FAT32 layout following Microsoft fatgen103 sizing."""
    if type(total_sectors) is not int or total_sectors <= RESERVED_SECTORS:
        raise CardError("invalid FAT32 sector count")
    per_cluster = 1 if total_sectors <= 532480 else 8
    per_fat_unit = (256 * per_cluster + NUM_FATS) // 2
    fat_sectors = -(-(total_sectors - RESERVED_SECTORS) // per_fat_unit)
    data_start = RESERVED_SECTORS + NUM_FATS * fat_sectors
    clusters = (total_sectors - data_start) // per_cluster
    if not FAT32_MIN_CLUSTERS <= clusters < 0x0FFFFFF5 or \
            fat_sectors * SECTOR // 4 < clusters + 2:
        raise CardError("size does not give a valid FAT32 cluster count")
    return {"total_sectors": total_sectors, "sectors_per_cluster": per_cluster,
            "fat_sectors": fat_sectors, "data_start": data_start,
            "clusters": clusters}


def fat32_structures(total_sectors, hidden_sectors, volume_id):
    """Return [(byte offset in the volume, bytes)] for an empty FAT32 volume.

    Every other byte of the volume must be zero (fresh sparse file)."""
    geo = fat32_geometry(total_sectors)
    boot = bytearray(SECTOR)
    boot[0:3] = b"\xeb\x58\x90"
    boot[3:11] = b"MSWIN4.1"
    struct.pack_into("<HBHBHHBHHHII", boot, 11, SECTOR, geo["sectors_per_cluster"],
                     RESERVED_SECTORS, NUM_FATS, 0, 0, 0xF8, 0, 63, 255,
                     hidden_sectors, total_sectors)
    struct.pack_into("<IHHIHH", boot, 36, geo["fat_sectors"], 0, 0, 2, 1, 6)
    struct.pack_into("<BBBI", boot, 64, 0x80, 0, 0x29, volume_id)
    boot[71:82] = FAT_LABEL
    boot[82:90] = b"FAT32   "
    boot[510:512] = b"\x55\xaa"
    info = bytearray(SECTOR)
    struct.pack_into("<I", info, 0, 0x41615252)
    struct.pack_into("<III", info, 484, 0x61417272, geo["clusters"] - 1, 3)
    struct.pack_into("<I", info, 508, 0xAA550000)
    fat_head = struct.pack("<III", 0x0FFFFFF8, FAT32_EOC, FAT32_EOC)
    label = FAT_LABEL + bytes([0x08]) + bytes(10) + struct.pack("<HHHI", 0, 0x0021, 0, 0)
    writes = [(0, bytes(boot)), (SECTOR, bytes(info)),
              (6 * SECTOR, bytes(boot)), (7 * SECTOR, bytes(info)),
              (geo["data_start"] * SECTOR, label)]
    for index in range(NUM_FATS):
        writes.append(((RESERVED_SECTORS + index * geo["fat_sectors"]) * SECTOR, fat_head))
    return geo, writes


def verify_fat32(handle, offset, total_sectors, hidden_sectors):
    """Independent read-back of the empty volume; returns failed check ids."""
    def read(at, size):
        handle.seek(offset + at)
        data = handle.read(size)
        return data if len(data) == size else b"\0" * size

    failed = []
    boot = read(0, SECTOR)
    bps, spc, rsvd, nfats, root16, tot16, media, fat16 = struct.unpack_from("<HBHBHHBH", boot, 11)
    hidden, tot32, fat32, _, _, root_cluster, fsinfo, backup = struct.unpack_from(
        "<IIIHHIHH", boot, 28)
    try:
        geo = fat32_geometry(total_sectors)
    except CardError:
        return ["fat32_geometry"]
    if not (boot[510:512] == b"\x55\xaa" and boot[82:90] == b"FAT32   " and
            (bps, spc, rsvd, nfats, root16, tot16, media, fat16) ==
            (SECTOR, geo["sectors_per_cluster"], RESERVED_SECTORS, NUM_FATS, 0, 0, 0xF8, 0) and
            (hidden, tot32, fat32, root_cluster, fsinfo, backup) ==
            (hidden_sectors, total_sectors, geo["fat_sectors"], 2, 1, 6)):
        failed.append("fat32_boot_sector")
    if boot[71:82] != FAT_LABEL or boot[66] != 0x29:
        failed.append("fat32_label")
    if read(6 * SECTOR, SECTOR) != boot or read(7 * SECTOR, SECTOR) != read(SECTOR, SECTOR):
        failed.append("fat32_backup")
    info = read(SECTOR, SECTOR)
    if struct.unpack_from("<I", info, 0)[0] != 0x41615252 or \
            struct.unpack_from("<III", info, 484) != (0x61417272, geo["clusters"] - 1, 3) or \
            struct.unpack_from("<I", info, 508)[0] != 0xAA550000:
        failed.append("fat32_fsinfo")
    fat_bytes = geo["fat_sectors"] * SECTOR
    first = read(RESERVED_SECTORS * SECTOR, fat_bytes)
    second = read((RESERVED_SECTORS + geo["fat_sectors"]) * SECTOR, fat_bytes)
    head = struct.pack("<III", 0x0FFFFFF8, FAT32_EOC, FAT32_EOC)
    if first != second or first[:12] != head or any(first[12:]):
        failed.append("fat32_tables")
    root = read(geo["data_start"] * SECTOR, geo["sectors_per_cluster"] * SECTOR)
    if root[:11] != FAT_LABEL or root[11] != 0x08 or any(root[32:]):
        failed.append("fat32_root_label")
    return failed


def _regular(path, role):
    try:
        info = os.stat(path)
    except OSError as error:
        raise CardError("%s: %s" % (role, error.strerror)) from None
    if not stat.S_ISREG(info.st_mode):
        raise CardError("%s: only regular image files are accepted" % role)
    return info.st_size


def _sha256_range(handle, offset, length):
    digest = hashlib.sha256()
    handle.seek(offset)
    while length:
        data = handle.read(min(CHUNK, length))
        if not data:
            raise CardError("short read while hashing")
        digest.update(data)
        length -= len(data)
    return digest.hexdigest()


def _is_sha256(value):
    return type(value) is str and len(value) == 64 and \
        all(c in "0123456789abcdef" for c in value)


def compose(pre_p1, p1, p2, output, *, expected_p2_sha256, p3_bytes=None,
            expected_p1_sha256=BR.SEALED_P1_SHA256):
    """Create `output` (must not exist). Returns a report; raises CardError."""
    if not (_is_sha256(expected_p1_sha256) and _is_sha256(expected_p2_sha256)):
        raise CardError("expected SHA-256 values must be 64 lowercase hex digits")
    output = Path(output)
    if os.path.lexists(output):
        raise CardError("output already exists; nothing is overwritten")
    if not output.parent.is_dir():
        raise CardError("output directory does not exist")
    if output.parent.resolve().parts[1:2] in (("dev",), ("proc",), ("sys",)):
        raise CardError("output must be an ordinary file outside /dev, /proc and /sys")
    geometry = ((p1, BR.P1_START, BR.P1_SECTORS, expected_p1_sha256, "p1"),
                (p2, BR.P2_START, BR.P2_SECTORS, expected_p2_sha256, "p2"))
    if _regular(pre_p1, "pre_p1") != BR.REGION_SIZE:
        raise CardError("pre_p1: size differs from P1 start x 512")
    with open(pre_p1, "rb") as handle:
        region = handle.read(BR.REGION_SIZE)
    analysis = BR.analyze_region(region)
    if analysis["status"] != "consistent_unverified":
        failed = [c["id"] for c in analysis["checks"] if c["result"] == "FAIL"]
        raise CardError("pre_p1 refused by boot_region: %s" % ", ".join(failed))
    checks = []
    sources = {}
    for path, _, sectors, expected, role in geometry:
        if _regular(path, role) != sectors * SECTOR:
            raise CardError("%s: size differs from its partition" % role)
        with open(path, "rb") as handle:
            handle.seek(1080)
            if handle.read(2) != b"\x53\xef":
                raise CardError("%s: no ext superblock magic" % role)
            before = _sha256_range(handle, 0, sectors * SECTOR)
        if before != expected:
            raise CardError("%s: SHA-256 differs from the expected value" % role)
        sources[role] = before
        checks.append({"id": role + "_sha256_before", "result": "PASS"})
    plan = BR.virtual_card_plan(p3_bytes=p3_bytes)
    p3_sectors = plan["mbr_p3_sectors"]
    if p3_sectors * SECTOR < MIN_P3_BYTES or plan["total_bytes"] > MAX_TOTAL_BYTES:
        raise CardError("virtual P3 must be >= 64 MiB and the card <= 2 GiB")
    geo, writes = fat32_structures(p3_sectors, BR.P3_START, int.from_bytes(
        hashlib.sha256((sources["p1"] + sources["p2"]).encode()).digest()[:4], "little"))
    patched = bytearray(region)
    struct.pack_into("<I", patched, MBR_P3_SIZE_OFFSET, p3_sectors)
    changed = [i for i in range(SECTOR) if patched[i] != region[i]]
    size_field = slice(MBR_P3_SIZE_OFFSET, MBR_P3_SIZE_OFFSET + 4)
    p3_offset = BR.P3_START * SECTOR
    descriptor, temporary = tempfile.mkstemp(prefix=".pmkb-virtual-", dir=str(output.parent))
    try:
        with os.fdopen(descriptor, "w+b") as card:
            card.truncate(plan["total_bytes"])
            card.write(patched)
            for path, start, sectors, _, _ in geometry:
                card.seek(start * SECTOR)
                with open(path, "rb") as source:
                    remaining = sectors * SECTOR
                    while remaining:
                        data = source.read(min(CHUNK, remaining))
                        if not data:
                            raise CardError("short read while copying")
                        card.write(data)
                        remaining -= len(data)
            for at, data in writes:
                card.seek(p3_offset + at)
                card.write(data)
            card.flush()
            os.fsync(card.fileno())
            card.seek(0)
            after_region = card.read(BR.REGION_SIZE)
            outside = after_region[:size_field.start] + after_region[size_field.stop:]
            identical = outside == region[:size_field.start] + region[size_field.stop:] and \
                after_region[size_field] == patched[size_field]
            checks.append({"id": "pre_p1_only_p3_size_changed",
                           "result": "PASS" if identical else "FAIL"})
            for path, start, sectors, _, role in geometry:
                after = _sha256_range(card, start * SECTOR, sectors * SECTOR)
                checks.append({"id": role + "_sha256_after",
                               "result": "PASS" if after == sources[role] else "FAIL"})
            fat_failed = verify_fat32(card, p3_offset, p3_sectors, BR.P3_START)
            checks.extend({"id": check, "result": "FAIL"} for check in fat_failed)
            checks.append({"id": "fat32_volume", "result": "FAIL" if fat_failed else "PASS"})
            reread = BR.analyze_region(after_region)
            checks.append({"id": "pre_p1_reanalysis", "result": "PASS" if
                           reread["status"] == "consistent_unverified" else "FAIL"})
            image_sha = _sha256_range(card, 0, plan["total_bytes"])
        if any(c["result"] == "FAIL" for c in checks):
            raise CardError("post-copy verification failed: %s" % ", ".join(
                c["id"] for c in checks if c["result"] == "FAIL"))
        try:
            os.link(temporary, output)  # fails instead of replacing a new file
        except FileExistsError:
            raise CardError("output appeared during assembly; nothing is overwritten") from None
    finally:
        os.unlink(temporary)
    return {
        "status": "assembled_unverified_boot", "profile": PROFILE,
        "output": str(output), "image_sha256": image_sha,
        "total_bytes": plan["total_bytes"], "p1_sha256": sources["p1"],
        "p2_sha256": sources["p2"], "pre_p1_changed_bytes": changed,
        "p3": {"offset": p3_offset, "sectors": p3_sectors, "label": FAT_LABEL.decode(),
               "sectors_per_cluster": geo["sectors_per_cluster"],
               "clusters": geo["clusters"]},
        "checks": checks, "boot_verified": False, "hardware_verified": False,
        "physical_profile_untouched": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pre_p1")
    parser.add_argument("p1", help="sealed %s" % BR.SEALED_P1_NAME)
    parser.add_argument("p2")
    parser.add_argument("output", help="new image file; never overwritten")
    parser.add_argument("--expected-p2-sha256", required=True)
    parser.add_argument("--p3-mib", type=int, help="P3 size in MiB (default: fill 1 GiB)")
    args = parser.parse_args(argv)
    try:
        report = compose(args.pre_p1, args.p1, args.p2, args.output,
                         expected_p2_sha256=args.expected_p2_sha256,
                         p3_bytes=None if args.p3_mib is None else args.p3_mib * 1024 * 1024)
    except (CardError, ValueError) as error:
        report = {"status": "refused", "profile": PROFILE, "error": str(error),
                  "boot_verified": False}
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["status"] != "refused" else 1


if __name__ == "__main__":
    sys.exit(main())
