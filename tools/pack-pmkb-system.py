#!/usr/bin/env python3
"""Build or verify a private, host-only PMKB system bundle (no P3, no /dev).

The bundle is NOT a writable disk image or an authorization to restore one.
Input components must come from an independently verified Kobo backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import BinaryIO

CHUNK = 1024 * 1024
MANIFEST_ENTRY = "pmkb-system.json"
ENTRY_PRE = "system/pre-p1.bin"
ENTRY_P1 = "system/p1-first-boot.img"
ENTRY_P2 = "system/p2-recoveryfs.img"
ENTRIES = (ENTRY_PRE, ENTRY_P1, ENTRY_P2)
FORMAT = "pmkb-system-bundle"
SCHEMA = 1
MAX_METADATA = 16384


class BundleError(ValueError):
    """Refusal of an unsafe, unsupported or inconsistent bundle."""


def sha_ok(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def regular(path: Path) -> Path:
    raw = str(path).replace("\\", "/").lower()
    if raw.startswith(("//", "/dev/")) or raw == "/dev" or "physicaldrive" in raw:
        raise BundleError("device/UNC paths are forbidden")
    if path.is_symlink():
        raise BundleError(f"symbolic link forbidden: {path}")
    resolved = path.resolve(strict=True)
    if str(resolved).replace("\\", "/").lower().startswith("/dev/"):
        raise BundleError("device path forbidden")
    if not stat.S_ISREG(path.stat().st_mode):
        raise BundleError(f"regular file required: {path}")
    return path


def manifest_data(path: Path) -> tuple[dict, str]:
    regular(path)
    raw = path.read_bytes()
    if len(raw) > MAX_METADATA:
        raise BundleError("candidate manifest too large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise BundleError("candidate manifest invalid") from exc
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise BundleError("candidate manifest schema invalid")
    if data.get("project") != "PimpMyKobo-AuraHD" or data.get("model") != "Kobo Aura HD E606C0":
        raise BundleError("candidate device mismatch")
    if not isinstance(data.get("head"), str) or re.fullmatch(r"[0-9a-f]{40}", data["head"]) is None:
        raise BundleError("candidate commit identity invalid")
    disk = data.get("disk")
    pre = data.get("pre_p1")
    parts = data.get("partitions")
    if not isinstance(disk, dict) or not isinstance(pre, dict) or not isinstance(parts, list) or len(parts) != 3:
        raise BundleError("candidate geometry missing")
    if disk.get("sector_size") != 512 or disk.get("partition_table") != "dos":
        raise BundleError("unsupported sector/partition table")
    if not all(isinstance(x, dict) for x in parts):
        raise BundleError("invalid partition records")
    if [x.get("number") for x in parts] != [1, 2, 3]:
        raise BundleError("unexpected partition sequence")
    if [x.get("role") for x in parts] != ["rootfs", "recoveryfs", "KOBOeReader"]:
        raise BundleError("unexpected partition roles")
    lengths = [pre.get("size"), *(p.get("size") for p in parts)]
    offsets = [pre.get("offset"), *(p.get("offset") for p in parts)]
    if any(type(n) is not int or n < 0 or n % 512 for n in lengths + offsets):
        raise BundleError("invalid partition offsets/sizes")
    if min(lengths) == 0 or offsets[0] != 0:
        raise BundleError("empty partition or nonzero disk prefix")
    for index in range(3):
        if offsets[index + 1] != offsets[index] + lengths[index]:
            raise BundleError("noncontiguous system geometry")
    if type(disk.get("size")) is not int or disk["size"] != offsets[3] + lengths[3]:
        raise BundleError("source disk length differs from partition geometry")
    if data.get("image_size") != lengths[1]:
        raise BundleError("candidate P1 size mismatch")
    if not all(sha_ok(x) for x in (pre.get("sha256"), data.get("image_sha256"), parts[1].get("sha256"))):
        raise BundleError("candidate integrity hashes invalid")
    return data, hashlib.sha256(raw).hexdigest()


def sources(data: dict) -> dict[str, dict]:
    return {
        ENTRY_PRE: {"size": data["pre_p1"]["size"], "sha256": data["pre_p1"]["sha256"]},
        ENTRY_P1: {"size": data["image_size"], "sha256": data["image_sha256"]},
        ENTRY_P2: {"size": data["partitions"][1]["size"], "sha256": data["partitions"][1]["sha256"]},
    }


def zip_info(name: str, *, compression: int = zipfile.ZIP_DEFLATED) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = compression
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise BundleError("input changed into nonregular file")
        for block in iter(lambda: source.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def transfer(path: Path, output: BinaryIO, expected: dict) -> None:
    regular(path)
    if path.stat().st_size != expected["size"]:
        raise BundleError(f"{path}: size mismatch")
    digest = hashlib.sha256()
    remaining = expected["size"]
    with path.open("rb") as source:
        original = os.fstat(source.fileno())
        if not stat.S_ISREG(original.st_mode) or original.st_size != remaining:
            raise BundleError("input changed during opening")
        while remaining:
            block = source.read(min(CHUNK, remaining))
            if not block:
                raise BundleError("input truncated during packaging")
            output.write(block)
            digest.update(block)
            remaining -= len(block)
        final = os.fstat(source.fileno())
        if (final.st_size, final.st_mtime_ns) != (original.st_size, original.st_mtime_ns):
            raise BundleError("input modified during packaging")
        if source.read(1):
            raise BundleError("input grew during packaging")
    if digest.hexdigest() != expected["sha256"]:
        raise BundleError(f"{path}: SHA-256 mismatch")


def payload_manifest(data: dict, candidate_sha: str) -> dict:
    return {
        "format": FORMAT,
        "schema": SCHEMA,
        "model": data["model"],
        "candidate_head": data["head"],
        "candidate_manifest_sha256": candidate_sha,
        "original_disk_size": data["disk"]["size"],
        "sector_size": 512,
        "p3_offset": data["partitions"][2]["offset"],
        "p3_included": False,
        "p3_policy": "recreate-on-target-separately",
        "components": sources(data),
        "write_authorized": False,
        "hardware_qualified": False,
    }


def verify(package: Path, candidate_manifest: Path) -> dict:
    regular(package)
    data, candidate_sha = manifest_data(candidate_manifest)
    expected = payload_manifest(data, candidate_sha)
    try:
        with zipfile.ZipFile(package, "r") as archive:
            entries = archive.infolist()
            names = [item.filename for item in entries]
            if len(names) != len(ENTRIES) + 1 or set(names) != set(ENTRIES) | {MANIFEST_ENTRY}:
                raise BundleError("unknown, duplicate or missing archive members")
            for item in entries:
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise BundleError("archive symlink forbidden")
                if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise BundleError("unsupported compression")
                limit = MAX_METADATA if item.filename == MANIFEST_ENTRY else expected["components"][item.filename]["size"]
                if item.file_size > limit:
                    raise BundleError("archive member exceeds declared size")
            if archive.getinfo(MANIFEST_ENTRY).file_size > MAX_METADATA:
                raise BundleError("oversized bundle manifest")
            raw_metadata = archive.read(MANIFEST_ENTRY)
            try:
                metadata = json.loads(raw_metadata)
            except (ValueError, UnicodeError) as exc:
                raise BundleError("bundle metadata invalid") from exc
            if metadata != expected:
                raise BundleError("bundle manifest differs from pinned candidate")
            for name in ENTRIES:
                spec = expected["components"][name]
                info = archive.getinfo(name)
                if info.file_size != spec["size"]:
                    raise BundleError(f"{name}: unexpected uncompressed size")
                digest = hashlib.sha256()
                size = 0
                with archive.open(name, "r") as handle:
                    for block in iter(lambda: handle.read(CHUNK), b""):
                        size += len(block)
                        if size > spec["size"]:
                            raise BundleError("uncompressed size exceeds expected")
                        digest.update(block)
                if size != spec["size"] or digest.hexdigest() != spec["sha256"]:
                    raise BundleError(f"{name}: uncompressed SHA-256 mismatch")
    except (OSError, EOFError, zipfile.BadZipFile, RuntimeError) as exc:
        raise BundleError(f"archive could not be verified: {exc}") from exc
    return {
        "status": "PASS",
        "package_sha256": digest_file(package),
        "package_size": package.stat().st_size,
        "uncompressed_system_size": sum(x["size"] for x in expected["components"].values()),
        "p3_included": False,
        "hardware_qualified": False,
        "device_write_attempted": False,
    }


def build(pre_p1: Path, p1: Path, p2: Path, candidate_manifest: Path, output: Path) -> dict:
    data, candidate_sha = manifest_data(candidate_manifest)
    expected = payload_manifest(data, candidate_sha)
    source_files = {ENTRY_PRE: pre_p1, ENTRY_P1: p1, ENTRY_P2: p2}
    for name, path in source_files.items():
        regular(path)
        if path.stat().st_size != expected["components"][name]["size"]:
            raise BundleError(f"{path}: size mismatch")
    if output.exists() or output.is_symlink():
        raise BundleError("refusing to overwrite existing output")
    if not output.parent.is_dir() or str(output.resolve()).replace("\\", "/").startswith("/dev/"):
        raise BundleError("invalid output directory")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w+b", dir=output.parent, prefix=".pmkb-bundle-", suffix=".tmp", delete=False) as temp:
            temp_name = temp.name
            with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
                for name in ENTRIES:
                    with archive.open(zip_info(name), "w", force_zip64=True) as entry:
                        transfer(source_files[name], entry, expected["components"][name])
                metadata = json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
                archive.writestr(zip_info(MANIFEST_ENTRY, compression=zipfile.ZIP_STORED), metadata)
            temp.flush()
            os.fsync(temp.fileno())
        report = verify(Path(temp_name), candidate_manifest)
        # Linking instead of replacing prevents races/overwriting existing packages.
        os.link(temp_name, output)
        return report
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("build", help="Build private system-only ZIP from local files")
    create.add_argument("--pre-p1", type=Path, required=True)
    create.add_argument("--p1", type=Path, required=True)
    create.add_argument("--p2", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    check = actions.add_parser("verify", help="Verify ZIP against pinned candidate manifest")
    check.add_argument("--package", type=Path, required=True)
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "build":
            result = build(args.pre_p1, args.p1, args.p2, args.manifest, args.output)
        else:
            result = verify(args.package, args.manifest)
    except (BundleError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc), "hardware_qualified": False, "device_write_attempted": False}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
