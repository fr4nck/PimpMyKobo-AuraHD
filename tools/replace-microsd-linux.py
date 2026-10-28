#!/usr/bin/env python3
"""Build a replacement Kobo Aura HD microSD from a read-only donor card.

The normal repair flow is deliberately split in three phases:
1. capture only the indispensable Kobo data from the original card (read-only);
2. qualify a different target card and prepare a reviewable plan;
3. after an explicit plan-SHA authorization, create the replacement card.

The donor is never opened writable. The target is always an explicitly named
whole removable USB block device on native Linux Live.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable

SECTOR_SIZE = 512
MIN_P3_BYTES = 1024 * 1024 * 1024
FINGERPRINT_WINDOW = 1024 * 1024
FAT_LABEL = "KOBOeReader"


def _load_restore_backend():
    path = Path(__file__).with_name("restore-p1-linux.py")
    spec = importlib.util.spec_from_file_location("pmkb_restore_for_replacement", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("restore-p1-linux.py non chargeable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


restore = _load_restore_backend()


class ReplacementError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ReplacementError(f"{path}: racine JSON invalide")
    return data


def load_manifest(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    required = {"image_name", "image_size", "image_sha256", "disk", "pre_p1", "partitions"}
    missing = sorted(required - data.keys())
    if missing:
        raise ReplacementError("manifest incomplet: " + ", ".join(missing))
    if data["disk"].get("sector_size") != SECTOR_SIZE or data["disk"].get("partition_table") != "dos":
        raise ReplacementError("manifest: géométrie disque non supportée")
    parts = data["partitions"]
    if not isinstance(parts, list) or [int(p.get("number", 0)) for p in parts] != [1, 2, 3]:
        raise ReplacementError("manifest: P1/P2/P3 attendues")
    p1, p2, p3 = parts
    for part in parts:
        if type(part.get("offset")) is not int or type(part.get("size")) is not int:
            raise ReplacementError("manifest: offset/taille de partition invalide")
        if part["offset"] % SECTOR_SIZE or part["size"] % SECTOR_SIZE:
            raise ReplacementError("manifest: partitions non alignées sur 512 octets")
    if p2["offset"] != p1["offset"] + p1["size"] or p3["offset"] != p2["offset"] + p2["size"]:
        raise ReplacementError("manifest: P1/P2/P3 système non contiguës")
    pre = data["pre_p1"]
    if pre.get("offset") != 0 or pre.get("size") != p1["offset"] or not _is_sha256(pre.get("sha256")):
        raise ReplacementError("manifest: PRE-P1 invalide")
    if not _is_sha256(p2.get("sha256")) or not _is_sha256(data.get("image_sha256")):
        raise ReplacementError("manifest: empreinte P1/P2 invalide")
    if int(data["image_size"]) != p1["size"]:
        raise ReplacementError("manifest: taille candidat différente de P1")
    return data


def geometry(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    p1, p2, p3 = manifest["partitions"]
    return p1, p2, p3


def target_layout(manifest: dict[str, Any], target_size: int,
                  *, min_p3_bytes: int = MIN_P3_BYTES) -> dict[str, int]:
    _p1, _p2, p3 = geometry(manifest)
    if type(target_size) is not int or target_size <= 0:
        raise ReplacementError("capacité cible invalide")
    if target_size % SECTOR_SIZE:
        raise ReplacementError("capacité cible non alignée sur 512 octets")
    if min_p3_bytes <= 0 or min_p3_bytes % SECTOR_SIZE:
        raise ReplacementError("minimum P3 invalide")
    if target_size <= p3["offset"]:
        raise ReplacementError("carte cible trop petite pour les zones système Kobo")
    remaining_sectors = (target_size - p3["offset"]) // SECTOR_SIZE
    # mkfs.fat BLOCK-COUNT is expressed in KiB; keep an even sector count.
    p3_sectors = (remaining_sectors // 2) * 2
    if p3_sectors > 0xFFFFFFFF:
        raise ReplacementError("P3 dépasse la limite MBR 32 bits")
    p3_size = p3_sectors * SECTOR_SIZE
    if p3_size < min_p3_bytes:
        minimum = p3["offset"] + min_p3_bytes
        raise ReplacementError(
            f"carte cible trop petite: {target_size} octets; minimum {minimum} octets"
        )
    return {
        "target_size": target_size,
        "sector_size": SECTOR_SIZE,
        "p3_offset": p3["offset"],
        "p3_start_sector": p3["offset"] // SECTOR_SIZE,
        "p3_size": p3_size,
        "p3_sectors": p3_sectors,
        "p3_kib": p3_size // 1024,
        "unused_tail": target_size - (p3["offset"] + p3_size),
        "minimum_target_size": p3["offset"] + min_p3_bytes,
    }


def _mbr_entry(data: bytes | bytearray, number: int) -> dict[str, int]:
    if number not in (1, 2, 3, 4) or len(data) < SECTOR_SIZE:
        raise ReplacementError("MBR invalide")
    offset = 446 + (number - 1) * 16
    return {
        "offset": offset,
        "status": data[offset],
        "type": data[offset + 4],
        "start_sector": struct.unpack_from("<I", data, offset + 8)[0],
        "size_sectors": struct.unpack_from("<I", data, offset + 12)[0],
    }


def patch_pre_p1(pre_p1: bytes, manifest: dict[str, Any],
                 layout: dict[str, int]) -> bytes:
    if len(pre_p1) != manifest["pre_p1"]["size"]:
        raise ReplacementError("PRE-P1 staged: taille invalide")
    if pre_p1[510:512] != b"\x55\xaa":
        raise ReplacementError("PRE-P1 staged: signature MBR absente")
    p1, p2, p3 = geometry(manifest)
    expected = (
        (1, p1["offset"] // SECTOR_SIZE, p1["size"] // SECTOR_SIZE),
        (2, p2["offset"] // SECTOR_SIZE, p2["size"] // SECTOR_SIZE),
    )
    for number, start, size in expected:
        entry = _mbr_entry(pre_p1, number)
        if entry["start_sector"] != start or entry["size_sectors"] != size:
            raise ReplacementError(f"PRE-P1 staged: géométrie P{number} inattendue")
        if entry["type"] != 0x83:
            raise ReplacementError(f"PRE-P1 staged: type P{number} inattendu")
    p3_entry = _mbr_entry(pre_p1, 3)
    if p3_entry["start_sector"] != p3["offset"] // SECTOR_SIZE:
        raise ReplacementError("PRE-P1 staged: départ P3 inattendu")
    if p3_entry["type"] not in (0x0B, 0x0C):
        raise ReplacementError("PRE-P1 staged: type FAT32 P3 inattendu")

    patched = bytearray(pre_p1)
    struct.pack_into("<I", patched, p3_entry["offset"] + 12, layout["p3_sectors"])
    return bytes(patched)


def _progress_text(label: str, done: int, total: int, started: float) -> str:
    percent = 100 if total <= 0 else min(100, int(done * 100 / total))
    mib = 1024 * 1024
    elapsed = max(time.monotonic() - started, 0.001)
    rate = (done / mib) / elapsed
    return (
        f"\r{label}: {percent:3d}% "
        f"({done / mib:.1f}/{total / mib:.1f} MiB, {rate:.1f} MiB/s)"
    )


def _show_progress(label: str, done: int, total: int, started: float,
                   *, stream=None) -> None:
    stream = sys.stdout if stream is None else stream
    stream.write(_progress_text(label, done, total, started))
    if done >= total:
        stream.write("\n")
    stream.flush()


def copy_range_with_progress(source: BinaryIO, destination: BinaryIO,
                             offset: int, size: int, label: str,
                             *, stream=None) -> str:
    source.seek(offset)
    remaining = size
    done = 0
    sha = hashlib.sha256()
    started = time.monotonic()
    last_percent = -1
    while remaining:
        data = source.read(min(restore.CHUNK, remaining))
        if not data:
            raise ReplacementError("lecture source interrompue")
        restore.write_all(destination, data)
        sha.update(data)
        done += len(data)
        remaining -= len(data)
        percent = 100 if size <= 0 else min(100, int(done * 100 / size))
        if percent != last_percent:
            _show_progress(label, done, size, started, stream=stream)
            last_percent = percent
    if size == 0:
        _show_progress(label, 0, 0, started, stream=stream)
    return sha.hexdigest()


def hash_region_with_progress(handle: BinaryIO, offset: int, size: int, label: str,
                              *, stream=None) -> str:
    handle.seek(offset)
    remaining = size
    done = 0
    sha = hashlib.sha256()
    started = time.monotonic()
    last_percent = -1
    while remaining:
        data = handle.read(min(restore.CHUNK, remaining))
        if not data:
            raise ReplacementError("relecture cible interrompue")
        sha.update(data)
        done += len(data)
        remaining -= len(data)
        percent = 100 if size <= 0 else min(100, int(done * 100 / size))
        if percent != last_percent:
            _show_progress(label, done, size, started, stream=stream)
            last_percent = percent
    if size == 0:
        _show_progress(label, 0, 0, started, stream=stream)
    return sha.hexdigest()


def _hash_region(handle: BinaryIO, offset: int, size: int) -> str:
    return restore.simulation.hash_region(handle, offset, size)


def donor_identity(handle: BinaryIO, size: int, manifest: dict[str, Any]) -> dict[str, Any]:
    p1, p2, p3 = geometry(manifest)
    if size < p3["offset"]:
        raise ReplacementError("carte donneuse trop petite")
    inspector = restore.legacy.load_inspector()
    mbr = inspector.parse_mbr(handle, size)
    hw = inspector.parse_hwconfig(handle)
    if not mbr.get("valid") or not hw or not hw.get("is_aura_hd_e606c0"):
        raise ReplacementError("la carte donneuse n'est pas identifiée Aura HD E606C0")
    parts = mbr.get("partitions") or []
    if len(parts) != 3:
        raise ReplacementError("carte donneuse: MBR à trois partitions attendu")
    if (
        parts[0]["offset"] != p1["offset"]
        or parts[0]["size"] != p1["size"]
        or parts[1]["offset"] != p2["offset"]
        or parts[1]["size"] != p2["size"]
        or parts[2]["offset"] != p3["offset"]
    ):
        raise ReplacementError("carte donneuse: géométrie système Kobo inattendue")
    if parts[0]["type"] != 0x83 or parts[1]["type"] != 0x83 or parts[2]["type"] not in (0x0B, 0x0C):
        raise ReplacementError("carte donneuse: types de partitions inattendus")

    pre_sha = hash_region_with_progress(
        handle, 0, manifest["pre_p1"]["size"], "Lecture originale PRE-P1"
    )
    p2_sha = hash_region_with_progress(
        handle, p2["offset"], p2["size"], "Lecture originale P2 recovery"
    )
    if pre_sha != manifest["pre_p1"]["sha256"]:
        raise ReplacementError("carte donneuse: PRE-P1/HWCONFIG ne correspond pas à la référence")
    if p2_sha != p2["sha256"]:
        raise ReplacementError("carte donneuse: P2 recovery ne correspond pas à la référence")
    return {
        "source_size": size,
        "pre_p1_sha256": pre_sha,
        "p2_sha256": p2_sha,
        "p3_type": parts[2]["type"],
        "hwconfig_identity": hw.get("identity"),
    }


def _prepare_stage_dir(stage_dir: Path) -> None:
    if stage_dir.is_symlink():
        raise ReplacementError("répertoire de staging symbolique refusé")
    if stage_dir.exists():
        if not stage_dir.is_dir():
            raise ReplacementError("staging n'est pas un répertoire")
        if any(stage_dir.iterdir()):
            raise ReplacementError("répertoire de staging non vide")
    else:
        stage_dir.mkdir(mode=0o700, parents=False)


def _write_stage_file(source: BinaryIO, destination: Path, offset: int, size: int,
                      label: str) -> str:
    with destination.open("xb") as out:
        digest = copy_range_with_progress(source, out, offset, size, label)
        out.flush()
        os.fsync(out.fileno())
    return digest


def capture_donor(manifest_path: Path, device: Path, stage_dir: Path,
                  *, ack_linux_live: bool = False) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    restore.require_native_linux(ack_linux_live)
    _prepare_stage_dir(stage_dir)
    required = manifest["pre_p1"]["size"] + manifest["partitions"][1]["size"] + 32 * 1024 * 1024
    if shutil.disk_usage(stage_dir).free < required:
        raise ReplacementError("espace Live insuffisant pour capturer PRE-P1 + P2")

    disk = None
    try:
        disk = restore.LinuxDisk(device, False)
        size = disk.size()
        identity = donor_identity(disk.handle, size, manifest)
        pre_path = stage_dir / "donor-pre-p1.img"
        p2_path = stage_dir / "donor-p2-recovery.img"
        pre_sha = _write_stage_file(
            disk.handle, pre_path, 0, manifest["pre_p1"]["size"],
            "Capture PRE-P1",
        )
        p2 = manifest["partitions"][1]
        p2_sha = _write_stage_file(
            disk.handle, p2_path, p2["offset"], p2["size"],
            "Capture P2 recovery",
        )
        if pre_sha != manifest["pre_p1"]["sha256"] or p2_sha != p2["sha256"]:
            raise ReplacementError("capture donneuse incohérente après relecture")
        if _sha256_file(pre_path) != pre_sha or _sha256_file(p2_path) != p2_sha:
            raise ReplacementError("capture donneuse: relecture des fichiers staged échouée")

        result = {
            "schema_version": 1,
            "tool": "capture-kobo-donor",
            "status": "captured",
            "complete": True,
            "source_open_mode": "read-only",
            "source_device": str(device),
            "source_size": size,
            "model": "Kobo Aura HD E606C0",
            "pre_p1": {
                "file": pre_path.name,
                "size": pre_path.stat().st_size,
                "sha256": pre_sha,
            },
            "p2": {
                "file": p2_path.name,
                "size": p2_path.stat().st_size,
                "sha256": p2_sha,
            },
            "p3_type": identity["p3_type"],
            "source_untouched": True,
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
        stage_manifest = stage_dir / "donor.json"
        with stage_manifest.open("x", encoding="utf-8") as out:
            out.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            out.flush()
            os.fsync(out.fileno())
        return result
    finally:
        if disk is not None:
            disk.close()


def load_stage(stage_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    data = _read_json(stage_dir / "donor.json")
    if (
        data.get("schema_version") != 1
        or data.get("tool") != "capture-kobo-donor"
        or data.get("status") != "captured"
        or data.get("complete") is not True
        or data.get("source_open_mode") != "read-only"
        or data.get("source_untouched") is not True
    ):
        raise ReplacementError("staging donneuse invalide")
    pre = data.get("pre_p1")
    p2 = data.get("p2")
    if not isinstance(pre, dict) or not isinstance(p2, dict):
        raise ReplacementError("staging donneuse incomplet")
    pre_path = stage_dir / str(pre.get("file"))
    p2_path = stage_dir / str(p2.get("file"))
    restore.legacy.regular(pre_path)
    restore.legacy.regular(p2_path)
    expected_p2 = manifest["partitions"][1]
    if (
        pre_path.stat().st_size != manifest["pre_p1"]["size"]
        or p2_path.stat().st_size != expected_p2["size"]
        or _sha256_file(pre_path) != manifest["pre_p1"]["sha256"]
        or _sha256_file(p2_path) != expected_p2["sha256"]
        or pre.get("sha256") != manifest["pre_p1"]["sha256"]
        or p2.get("sha256") != expected_p2["sha256"]
    ):
        raise ReplacementError("staging donneuse différent de la référence")
    data["_pre_path"] = pre_path
    data["_p2_path"] = p2_path
    return data


def validate_candidate(candidate: Path, manifest: dict[str, Any]) -> str:
    restore.legacy.regular(candidate)
    if candidate.stat().st_size != manifest["image_size"]:
        raise ReplacementError("candidat PMKB: taille inattendue")
    digest = _sha256_file(candidate)
    if digest != manifest["image_sha256"]:
        raise ReplacementError("candidat PMKB: SHA-256 inattendu")
    return digest


def target_fingerprint(handle: BinaryIO, size: int) -> str:
    h = hashlib.sha256()
    h.update(struct.pack("<Q", size))
    first = min(FINGERPRINT_WINDOW, size)
    handle.seek(0)
    h.update(handle.read(first))
    if size > first:
        last = min(FINGERPRINT_WINDOW, size)
        handle.seek(size - last)
        h.update(handle.read(last))
    return h.hexdigest()


def target_looks_like_donor(handle: BinaryIO, size: int,
                            manifest: dict[str, Any]) -> bool:
    p2 = manifest["partitions"][1]
    if size < p2["offset"] + p2["size"]:
        return False
    try:
        return (
            _hash_region(handle, 0, manifest["pre_p1"]["size"]) == manifest["pre_p1"]["sha256"]
            and _hash_region(handle, p2["offset"], p2["size"]) == p2["sha256"]
        )
    except (OSError, ValueError):
        return False


def build_plan(manifest: dict[str, Any], stage: dict[str, Any], candidate_sha: str,
               device_identity: dict[str, Any], target_size: int,
               fingerprint: str) -> dict[str, Any]:
    layout = target_layout(manifest, target_size)
    return {
        "schema_version": 1,
        "tool": "prepare-replacement-microsd",
        "status": "prepared",
        "write_authorized": False,
        "model": "Kobo Aura HD E606C0",
        "target_path": device_identity["path"],
        "target_major_minor": device_identity["major_minor"],
        "target_size": target_size,
        "target_fingerprint_sha256": fingerprint,
        "candidate_sha256": candidate_sha,
        "pre_p1_sha256": manifest["pre_p1"]["sha256"],
        "p2_sha256": manifest["partitions"][1]["sha256"],
        "donor_stage_sha256": _sha256_file(Path(stage["_pre_path"]).parent / "donor.json"),
        "layout": layout,
        "p3": {
            "filesystem": "fat32",
            "label": FAT_LABEL,
            "type": int(stage["p3_type"]),
        },
        "source_card_write_required": False,
        "limitations": [
            "The source card is read-only and must be retained.",
            "The replacement target will be erased after explicit authorization.",
            "Hardware boot remains unqualified until the Kobo boots this card.",
        ],
    }


def prepare_target_plan(manifest_path: Path, candidate: Path, stage_dir: Path,
                        device: Path, plan_path: Path,
                        *, ack_linux_live: bool = False) -> tuple[dict[str, Any], str]:
    manifest = load_manifest(manifest_path)
    stage = load_stage(stage_dir, manifest)
    candidate_sha = validate_candidate(candidate, manifest)
    restore.require_native_linux(ack_linux_live)
    restore.legacy.reject_device(plan_path)
    if plan_path.exists() or plan_path.is_symlink():
        raise ReplacementError("plan cible déjà présent")

    disk = None
    try:
        disk = restore.LinuxDisk(device, False)
        size = disk.size()
        layout = target_layout(manifest, size)
        del layout
        if target_looks_like_donor(disk.handle, size, manifest):
            raise ReplacementError(
                "REFUS: la cible ressemble à la carte donneuse/originale; insérez une autre microSD"
            )
        fingerprint = target_fingerprint(disk.handle, size)
        plan = build_plan(manifest, stage, candidate_sha, disk.identity, size, fingerprint)
    finally:
        if disk is not None:
            disk.close()

    with plan_path.open("x", encoding="utf-8") as out:
        out.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        out.flush()
        os.fsync(out.fileno())
    return plan, _sha256_file(plan_path)


def replacement_confirmation(plan_sha256: str, plan: dict[str, Any]) -> str:
    if not _is_sha256(plan_sha256):
        raise ReplacementError("SHA-256 du plan invalide")
    return f"EFFACER {plan['target_path']} CREER PMKB {plan_sha256[:8]}"


def _load_plan(plan_path: Path, expected_sha256: str) -> dict[str, Any]:
    restore.legacy.regular(plan_path)
    if not _is_sha256(expected_sha256) or _sha256_file(plan_path) != expected_sha256:
        raise ReplacementError("plan cible différent du plan autorisé")
    plan = _read_json(plan_path)
    required = {
        "schema_version", "tool", "status", "write_authorized", "model",
        "target_path", "target_major_minor", "target_size",
        "target_fingerprint_sha256", "candidate_sha256", "pre_p1_sha256",
        "p2_sha256", "donor_stage_sha256", "layout", "p3",
        "source_card_write_required",
    }
    missing = sorted(required - plan.keys())
    if missing:
        raise ReplacementError("plan cible incomplet: " + ", ".join(missing))
    if (
        plan.get("schema_version") != 1
        or plan.get("tool") != "prepare-replacement-microsd"
        or plan.get("status") != "prepared"
        or plan.get("write_authorized") is not False
        or plan.get("source_card_write_required") is not False
        or plan.get("model") != "Kobo Aura HD E606C0"
    ):
        raise ReplacementError("contrat du plan cible invalide")
    if not all(_is_sha256(plan.get(key)) for key in (
        "target_fingerprint_sha256", "candidate_sha256", "pre_p1_sha256",
        "p2_sha256", "donor_stage_sha256",
    )):
        raise ReplacementError("empreintes du plan cible invalides")
    if not isinstance(plan.get("layout"), dict) or not isinstance(plan.get("p3"), dict):
        raise ReplacementError("géométrie du plan cible invalide")
    if type(plan.get("target_size")) is not int or plan["target_size"] <= 0:
        raise ReplacementError("capacité du plan cible invalide")
    return plan


def mkfs_fat_command(device: Path, layout: dict[str, int],
                     executable: str = "mkfs.fat") -> list[str]:
    return [
        executable,
        "-F", "32",
        "-n", FAT_LABEL,
        "-S", str(SECTOR_SIZE),
        "-h", str(layout["p3_start_sector"]),
        "--offset", str(layout["p3_start_sector"]),
        "-I",
        str(device),
        str(layout["p3_kib"]),
    ]


def verify_fat32(handle: BinaryIO, layout: dict[str, int]) -> dict[str, Any]:
    handle.seek(layout["p3_offset"])
    sector = handle.read(SECTOR_SIZE)
    if len(sector) != SECTOR_SIZE or sector[510:512] != b"\x55\xaa":
        raise ReplacementError("P3 FAT32: secteur de boot invalide")
    bytes_per_sector = struct.unpack_from("<H", sector, 11)[0]
    hidden = struct.unpack_from("<I", sector, 28)[0]
    total16 = struct.unpack_from("<H", sector, 19)[0]
    total32 = struct.unpack_from("<I", sector, 32)[0]
    total = total16 or total32
    fs_type = sector[82:90].decode("ascii", errors="replace")
    label = sector[71:82].decode("ascii", errors="replace").rstrip()
    if (
        bytes_per_sector != SECTOR_SIZE
        or hidden != layout["p3_start_sector"]
        or total != layout["p3_sectors"]
        or fs_type.strip().upper() != "FAT32"
        or label.upper() != FAT_LABEL.upper()
    ):
        raise ReplacementError(
            f"P3 FAT32 incohérente: bps={bytes_per_sector} hidden={hidden} "
            f"total={total} type={fs_type!r} label={label!r}"
        )
    return {
        "filesystem": "fat32",
        "label": label,
        "bytes_per_sector": bytes_per_sector,
        "hidden_sectors": hidden,
        "total_sectors": total,
    }


def execute_replacement(plan_path: Path, expected_plan_sha256: str,
                        manifest_path: Path, candidate: Path, stage_dir: Path,
                        device: Path, *, authorize_plan_sha256: str,
                        ack_linux_live: bool = False,
                        run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1,
        "tool": "replace-microsd-linux",
        "status": "refused",
        "complete": False,
        "device_write_attempted": False,
        "source_card_write_attempted": False,
        "errors": [],
    }
    disk = None
    try:
        if authorize_plan_sha256 != expected_plan_sha256:
            raise ReplacementError("autorisation explicite liée au SHA-256 du plan requise")
        plan = _load_plan(plan_path, expected_plan_sha256)
        manifest = load_manifest(manifest_path)
        stage = load_stage(stage_dir, manifest)
        candidate_sha = validate_candidate(candidate, manifest)
        donor_manifest = stage_dir / "donor.json"
        expected_p3 = {
            "filesystem": "fat32",
            "label": FAT_LABEL,
            "type": int(stage["p3_type"]),
        }
        if (
            candidate_sha != plan.get("candidate_sha256")
            or plan.get("pre_p1_sha256") != manifest["pre_p1"]["sha256"]
            or plan.get("p2_sha256") != manifest["partitions"][1]["sha256"]
            or plan.get("donor_stage_sha256") != _sha256_file(donor_manifest)
            or plan.get("p3") != expected_p3
        ):
            raise ReplacementError("candidat/donneuse différents du plan autorisé")
        restore.require_native_linux(ack_linux_live)

        disk = restore.LinuxDisk(device, True)
        size = disk.size()
        if str(device.resolve()) != plan["target_path"]:
            raise ReplacementError("chemin cible différent du plan")
        if size != plan["target_size"]:
            raise ReplacementError("capacité cible différente du plan")
        if target_fingerprint(disk.handle, size) != plan["target_fingerprint_sha256"]:
            raise ReplacementError("la microSD cible a changé depuis la préparation du plan")
        if target_looks_like_donor(disk.handle, size, manifest):
            raise ReplacementError("REFUS: la cible ressemble à la carte donneuse/originale")

        layout = target_layout(manifest, size)
        if layout != plan["layout"]:
            raise ReplacementError("géométrie cible différente du plan")
        restore.check_staged_filesystem(candidate)

        pre_bytes = Path(stage["_pre_path"]).read_bytes()
        patched_pre = patch_pre_p1(pre_bytes, manifest, layout)
        expected_pre_sha = hashlib.sha256(patched_pre).hexdigest()
        p1, p2, _p3 = geometry(manifest)

        result["device_write_attempted"] = True
        disk.handle.seek(0)
        restore.write_all(disk.handle, patched_pre)
        with candidate.open("rb") as source:
            disk.handle.seek(p1["offset"])
            if copy_range_with_progress(
                source, disk.handle, 0, p1["size"], "Écriture P1 PMKB"
            ) != candidate_sha:
                raise ReplacementError("P1 candidate modifiée pendant l'écriture")
        with Path(stage["_p2_path"]).open("rb") as source:
            disk.handle.seek(p2["offset"])
            if copy_range_with_progress(
                source, disk.handle, 0, p2["size"], "Écriture P2 recovery"
            ) != manifest["partitions"][1]["sha256"]:
                raise ReplacementError("P2 staged modifiée pendant l'écriture")
        disk.flush_and_invalidate()
        disk.recheck()

        executable = shutil.which("mkfs.fat", path="/usr/sbin:/usr/bin:/sbin:/bin")
        if not executable:
            raise ReplacementError("mkfs.fat absent du Live")
        command = mkfs_fat_command(Path(disk.identity["path"]), layout, executable)
        formatted = run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
        if formatted.returncode != 0:
            raise ReplacementError(
                f"création FAT32 P3 refusée (exit {formatted.returncode}): {formatted.stdout}"
            )
        disk.flush_and_invalidate()
        disk.recheck()
        if disk.size() != size:
            raise ReplacementError("capacité cible modifiée après formatage")

        if hash_region_with_progress(
            disk.handle, 0, manifest["pre_p1"]["size"], "Vérification PRE-P1"
        ) != expected_pre_sha:
            raise ReplacementError("PRE-P1/MBR différent après écriture")
        if hash_region_with_progress(
            disk.handle, p1["offset"], p1["size"], "Vérification P1 PMKB"
        ) != candidate_sha:
            raise ReplacementError("P1 différente après relecture")
        if hash_region_with_progress(
            disk.handle, p2["offset"], p2["size"], "Vérification P2 recovery"
        ) != manifest["partitions"][1]["sha256"]:
            raise ReplacementError("P2 recovery différente après relecture")

        inspector = restore.legacy.load_inspector()
        mbr = inspector.parse_mbr(disk.handle, size)
        parts = mbr.get("partitions") or []
        if not mbr.get("valid") or len(parts) != 3:
            raise ReplacementError("MBR cible invalide après écriture")
        if (
            parts[0]["offset"] != p1["offset"]
            or parts[0]["size"] != p1["size"]
            or parts[1]["offset"] != p2["offset"]
            or parts[1]["size"] != p2["size"]
            or parts[2]["offset"] != layout["p3_offset"]
            or parts[2]["size"] != layout["p3_size"]
        ):
            raise ReplacementError("géométrie MBR cible différente du plan")
        fat = verify_fat32(disk.handle, layout)

        result.update(
            status="ok",
            complete=True,
            plan_sha256=expected_plan_sha256,
            target=str(device),
            target_size=size,
            p1_sha256=candidate_sha,
            p2_sha256=manifest["partitions"][1]["sha256"],
            pre_p1_sha256=expected_pre_sha,
            p3=fat,
            p3_size=layout["p3_size"],
            unused_tail=layout["unused_tail"],
            source_card_write_attempted=False,
            source_card_required_during_write=False,
            hardware_boot="not_tested",
        )
    except (OSError, ValueError, TypeError, KeyError, ReplacementError, subprocess.SubprocessError) as exc:
        result.update(
            status="failed" if result["device_write_attempted"] else "refused",
            complete=False,
            errors=[str(exc)],
            target_may_be_partial=result["device_write_attempted"],
        )
    finally:
        if disk is not None:
            try:
                disk.close()
            except OSError as exc:
                result.update(status="failed", complete=False)
                result["errors"].append(f"fermeture cible échouée: {exc}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--ack-linux-live", action="store_true")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--capture-donor", action="store_true")
    modes.add_argument("--prepare-target", action="store_true")
    modes.add_argument("--write-target", action="store_true")
    parser.add_argument("--expected-plan-sha256")
    parser.add_argument("--authorize-plan-sha256")
    args = parser.parse_args()
    try:
        if args.capture_donor:
            result = capture_donor(
                args.manifest, args.device, args.stage_dir,
                ack_linux_live=args.ack_linux_live,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.candidate is None or args.plan is None:
            raise ReplacementError("--candidate et --plan sont requis pour la cible")
        if args.prepare_target:
            plan, sha = prepare_target_plan(
                args.manifest, args.candidate, args.stage_dir, args.device, args.plan,
                ack_linux_live=args.ack_linux_live,
            )
            print(json.dumps({"plan": plan, "plan_sha256": sha}, ensure_ascii=False, indent=2))
            return 0
        if not args.expected_plan_sha256 or not args.authorize_plan_sha256:
            raise ReplacementError(
                "--write-target exige --expected-plan-sha256 et --authorize-plan-sha256"
            )
        result = execute_replacement(
            args.plan, args.expected_plan_sha256,
            args.manifest, args.candidate, args.stage_dir, args.device,
            authorize_plan_sha256=args.authorize_plan_sha256,
            ack_linux_live=args.ack_linux_live,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["complete"] else 1
    except (ReplacementError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "refused", "complete": False, "errors": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
