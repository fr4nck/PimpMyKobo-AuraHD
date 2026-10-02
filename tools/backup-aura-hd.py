#!/usr/bin/env python3
"""Read-only backup of a positively identified Kobo Aura HD / E606C0 microSD.

The SOURCE (disk, partition or image) is only ever opened with mode "rb".
The only place this tool writes is the destination directory explicitly
given by the user. It never mounts, formats, repartitions or restores.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, BinaryIO, Callable

TOOL_NAME = "backup-aura-hd"
TOOL_VERSION = "0.1.0"
MANIFEST_SCHEMA_VERSION = 1
FINGERPRINT_ALGORITHM = "pmkb-target-v1"
MANIFEST_NAME = "backup-manifest.json"
SUMS_NAME = "SHA256SUMS"
CHUNK = 4 * 1024 * 1024  # multiple of 512: every source read stays sector-aligned
SPACE_MARGIN = 16 * 1024 * 1024
PROGRESS_STEP = 64 * 1024 * 1024
WINDOWS_DRIVE_RE = re.compile(r"^\\\\[.?]\\PhysicalDrive(\d+)$", re.IGNORECASE)

EXIT_COMPLETE = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
EXIT_INTERRUPTED = 130

COMPONENT_FILES = {
    "pre_p1": "pre-p1.bin",
    "p1_rootfs": "p1-rootfs.img",
    "p2_recoveryfs": "p2-recoveryfs.img",
    "p3_userdata": "p3-userdata.img",
}

FR = {
    "title": "PimpMyKobo-AuraHD — sauvegarde (la source est uniquement lue)",
    "refused": "REFUS DE SAUVEGARDE",
    "plan": "Plan de sauvegarde",
    "dry_run": "Simulation (--dry-run) : aucun fichier n'a été créé.",
    "complete": "SAUVEGARDE COMPLÈTE ET VÉRIFIÉE",
    "failed": "SAUVEGARDE ÉCHOUÉE — NE PAS L'UTILISER COMME RÉFÉRENCE",
    "interrupted": "SAUVEGARDE INTERROMPUE — INCOMPLÈTE",
    "destination": "Destination",
    "fingerprint": "Empreinte cible",
    "not_included": "P3 KOBOeReader non sauvegardée (utiliser --include-userdata)",
}

EN = {
    "title": "PimpMyKobo-AuraHD — backup (the source is only read)",
    "refused": "BACKUP REFUSED",
    "plan": "Backup plan",
    "dry_run": "Dry run (--dry-run): no file was created.",
    "complete": "BACKUP COMPLETE AND VERIFIED",
    "failed": "BACKUP FAILED — DO NOT USE IT AS A REFERENCE",
    "interrupted": "BACKUP INTERRUPTED — INCOMPLETE",
    "destination": "Destination",
    "fingerprint": "Target fingerprint",
    "not_included": "P3 KOBOeReader not backed up (use --include-userdata)",
}


def _load_inspector() -> Any:
    """Reuse the qualified inspect-aura-hd.py parsing code without duplicating it."""
    path = Path(__file__).resolve().with_name("inspect-aura-hd.py")
    spec = importlib.util.spec_from_file_location("pmkb_inspect_aura_hd", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inspector = _load_inspector()
read_at = inspector.read_at
SECTOR_SIZE = inspector.SECTOR_SIZE


class Refusal(Exception):
    """Raised before any destination write when the backup must not start."""

    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def human_size(value: int | None) -> str:
    return inspector.human_size(value)


def open_source(source: str) -> BinaryIO:
    """The ONLY way this tool opens the source: read-only, unbuffered."""
    return open(source, "rb", buffering=0)


def disk_free(path: Path) -> int:
    return shutil.disk_usage(path).free


# ---------------------------------------------------------------------------
# Source identification
# ---------------------------------------------------------------------------

def source_kind(source: str) -> str:
    if os.name == "nt" and WINDOWS_DRIVE_RE.match(source):
        return "windows_physical_drive"
    try:
        mode = os.stat(source).st_mode
    except OSError:
        return "unknown"
    if stat.S_ISBLK(mode):
        return "block_device"
    if stat.S_ISREG(mode):
        return "image_file"
    return "other"


def windows_disk_size(source: str) -> int | None:
    match = WINDOWS_DRIVE_RE.match(source)
    if not match or os.name != "nt":
        return None
    number = int(match.group(1))
    for item in inspector.windows_candidates():
        meta = item.get("metadata", {})
        if meta.get("number") == number and isinstance(meta.get("size"), int):
            return meta["size"]
    return None


def identify_source(source: str) -> dict[str, Any]:
    """Run the qualified inspector, then apply the stricter backup preconditions."""
    kind = source_kind(source)
    metadata: dict[str, Any] = {}
    size_from = None
    if kind == "windows_physical_drive":
        size = windows_disk_size(source)
        if size:
            metadata["size"] = size
            size_from = "Get-Disk"

    result = inspector.inspect_source(source, metadata, True)
    reasons: list[str] = []
    if not result.get("opened"):
        raise Refusal([f"source cannot be opened read-only: {result.get('error')}"])
    reasons.extend(result.get("errors", []))

    hw = result.get("hwconfig")
    if not hw:
        reasons.append("no HW CONFIG block at 0x80000")
    elif not hw.get("is_aura_hd_e606c0"):
        reasons.append(
            f"HWCONFIG not confirmed as v1.7 / 39 bytes / PCB 28 "
            f"(got {hw.get('version')!r}, {hw.get('payload_size')} bytes, PCB {hw.get('fields', {}).get('bPCB')})"
        )

    mbr = result.get("mbr", {})
    if not mbr.get("valid"):
        reasons.append("MBR is not valid: " + "; ".join(mbr.get("errors", []) or ["unknown"]))
    parts = {p["number"]: p for p in mbr.get("partitions", [])}
    if sorted(parts) != [1, 2, 3]:
        reasons.append(f"expected exactly MBR partitions P1, P2, P3; found {sorted(parts)}")

    warnings = list(result.get("warnings", []))
    if not reasons:
        p1, p2, p3 = parts[1], parts[2], parts[3]
        if not (p1["offset"] < p2["offset"] < p3["offset"]):
            reasons.append("partitions are not ordered P1 < P2 < P3 on the medium")
        if (p1.get("filesystem"), p1.get("label")) != ("ext", "rootfs"):
            reasons.append(f"P1 is not an ext filesystem labelled 'rootfs' ({p1.get('filesystem')}, {p1.get('label')!r})")
        if (p2.get("filesystem"), p2.get("label")) != ("ext", "recoveryfs"):
            reasons.append(f"P2 is not an ext filesystem labelled 'recoveryfs' ({p2.get('filesystem')}, {p2.get('label')!r})")
        if not str(p3.get("filesystem", "")).startswith("FAT"):
            reasons.append(f"P3 is not a FAT filesystem ({p3.get('filesystem')})")
        elif p3.get("label") != "KOBOeReader":
            warnings.append(f"P3 FAT label is {p3.get('label')!r}, not 'KOBOeReader'")
        for p in (p1, p2):
            if p["type"] != 0x83:
                warnings.append(f"P{p['number']} MBR type is 0x{p['type']:02X}, not 0x83")
        pre_size = p1["offset"]
        minimum = inspector.HWCONFIG_OFFSET + inspector.HWCONFIG_HEADER_SIZE + inspector.HWCONFIG_V17_PAYLOAD_SIZE
        if pre_size < minimum:
            reasons.append(f"P1 starts at {pre_size}, inside the HWCONFIG area")
        if pre_size > inspector.MAX_BOOT_HASH_SIZE:
            reasons.append(f"P1 starts beyond {inspector.MAX_BOOT_HASH_SIZE} bytes; pre-P1 area is implausible")
        if result.get("pre_p1_size") != pre_size or not result.get("pre_p1_sha256"):
            reasons.append("pre-P1 area could not be hashed during identification")

    if reasons:
        raise Refusal(reasons)

    source_size = result.get("source_size")
    if source_size is not None and size_from is None:
        size_from = "inspector"
    if source_size is None:
        # Size not determinable: prove the medium really extends to the end of P3.
        with open_source(source) as handle:
            last = read_at(handle, parts[3]["end"] - SECTOR_SIZE, SECTOR_SIZE)
        if len(last) != SECTOR_SIZE:
            raise Refusal(["source size unknown and the last sector of P3 is not readable"])
        size_from = "unknown (last sector of P3 verified readable)"

    return {
        "inspection": result,
        "kind": kind,
        "source_size": source_size,
        "size_from": size_from,
        "partitions": parts,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Destination checks
# ---------------------------------------------------------------------------

def nearest_existing(path: Path) -> Path:
    current = path
    while not current.exists():
        if current.parent == current:
            break
        current = current.parent
    return current


def _sysfs_block(dev: int) -> str | None:
    node = f"/sys/dev/block/{os.major(dev)}:{os.minor(dev)}"
    return os.path.realpath(node) if os.path.exists(node) else None


def _mount_info(path: Path) -> tuple[str, str] | None:
    """(fstype, mount source) of the mount containing *path*, from /proc/self/mountinfo."""
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    target = str(path.resolve())
    best: tuple[int, str, str] | None = None
    for line in lines:
        left, _, right = line.partition(" - ")
        fields = left.split()
        tail = right.split()
        if len(fields) < 5 or len(tail) < 2:
            continue
        mount_point = fields[4].replace("\\040", " ")
        if target == mount_point or target.startswith(mount_point.rstrip("/") + "/"):
            if best is None or len(mount_point) > best[0]:
                best = (len(mount_point), tail[0], tail[1])
    return (best[1], best[2]) if best else None


def _mount_source_device(path: Path) -> int | None:
    """Device number backing *path* (btrfs, overlay...) when it is a /dev block device."""
    info = _mount_info(path)
    if info is None or not info[1].startswith("/dev/"):
        return None
    try:
        st = os.stat(info[1])
    except OSError:
        return None
    return st.st_rdev if stat.S_ISBLK(st.st_mode) else None


def destination_on_source(source: str, kind: str, destination: Path) -> str:
    """Return not_applicable / not_on_source / on_source / undetermined."""
    existing = nearest_existing(destination)
    if kind == "image_file":
        return "not_applicable"
    if kind == "block_device" and hasattr(os, "major"):
        source_sys = _sysfs_block(os.stat(source).st_rdev)
        dev = os.stat(existing).st_dev
        dest_sys = _sysfs_block(dev) if os.major(dev) != 0 else None
        if dest_sys is None:
            info = _mount_info(existing)
            if info is not None and info[0] in ("tmpfs", "ramfs"):
                return "not_on_source"  # RAM-backed filesystem, cannot live on the card
            mount_dev = _mount_source_device(existing)
            dest_sys = _sysfs_block(mount_dev) if mount_dev is not None else None
        if source_sys is None or dest_sys is None:
            return "undetermined"
        if dest_sys == source_sys or dest_sys.startswith(source_sys + "/"):
            return "on_source"
        return "not_on_source"
    if kind == "windows_physical_drive":
        number = int(WINDOWS_DRIVE_RE.match(source).group(1))  # type: ignore[union-attr]
        drive = os.path.splitdrive(str(existing.resolve()))[0]
        if not re.match(r"^[A-Za-z]:$", drive):
            return "undetermined"
        command = [
            "powershell", "-NoProfile", "-Command",
            f"$ErrorActionPreference='Stop'; (Get-Partition -DriveLetter {drive[0]}).DiskNumber",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
            dest_disk = int(completed.stdout.strip())
        except (OSError, subprocess.SubprocessError, ValueError):
            return "undetermined"
        return "on_source" if dest_disk == number else "not_on_source"
    return "undetermined"


# ---------------------------------------------------------------------------
# Manifest / fingerprint
# ---------------------------------------------------------------------------

def build_fingerprint(identity: dict[str, Any], hwconfig_raw: bytes) -> dict[str, Any]:
    inspection = identity["inspection"]
    partitions = [
        {"number": p["number"], "type": p["type"], "start_lba": p["start_lba"], "sectors": p["sectors"]}
        for p in sorted(identity["partitions"].values(), key=lambda x: x["number"])
    ]
    stable = {
        "algorithm": FINGERPRINT_ALGORITHM,
        "pre_p1_size": inspection["pre_p1_size"],
        "pre_p1_sha256": inspection["pre_p1_sha256"],
        "hwconfig_sha256": hashlib.sha256(hwconfig_raw).hexdigest(),
        "partitions": partitions,
    }
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {
        **stable,
        "fingerprint_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_form": "sha256 of sorted-key compact JSON of the other fields of this object",
        "source_size": identity["source_size"],
        "source_size_in_digest": False,
        "notes": [
            "Derived only from bytes read on the source: pre-P1 area (MBR, U-Boot, HWCONFIG...), "
            "HWCONFIG block and MBR geometry. Device names are never part of it.",
            "It identifies CONTENT, not a physical card: a bit-exact clone has the same fingerprint.",
            "Any later write to the pre-P1 area (firmware update, new U-Boot/kernel) changes it.",
            "It is not proven unique between two Aura HD units; it must not be the only safety check of a future restore.",
        ],
    }


def describe_identity(identity: dict[str, Any]) -> dict[str, Any]:
    inspection = identity["inspection"]
    hw = inspection["hwconfig"]
    fields = hw["fields"]
    decoded = hw["decoded"]

    def value(name: str) -> dict[str, Any]:
        return {"raw": fields.get(name), "decoded": decoded.get(name)}

    return {
        "aura_hd_e606c0": True,
        "identity": hw["identity"],
        "hwconfig": {
            "offset": hw["offset"],
            "version": hw["version"],
            "payload_size": hw["payload_size"],
            "pcb": value("bPCB"),
            "ram_size": value("bRamSize"),
            "ram_type": value("bRamType"),
            "cpu": value("bCPU"),
            "cpu_freq": value("bCPUFreq"),
            "display_resolution": value("bDisplayResolution"),
            "fields": fields,
        },
    }


def describe_mbr(identity: dict[str, Any], sector0: bytes) -> dict[str, Any]:
    parts = [identity["partitions"][n] for n in (1, 2, 3)]
    roles = {1: "rootfs", 2: "recoveryfs", 3: "userdata"}
    gaps = []
    for left, right in zip(parts, parts[1:]):
        if right["offset"] > left["end"]:
            gaps.append({"after": f"P{left['number']}", "offset": left["end"], "size": right["offset"] - left["end"]})
    size = identity["source_size"]
    return {
        "signature_valid": True,
        "sector0_sha256": hashlib.sha256(sector0).hexdigest(),
        "partitions": [
            {
                "number": p["number"], "role": roles[p["number"]],
                "boot_indicator": p["boot_indicator"], "type": p["type"], "type_hex": f"0x{p['type']:02X}",
                "start_lba": p["start_lba"], "sectors": p["sectors"],
                "offset": p["offset"], "size": p["size"], "end": p["end"],
                "filesystem": p.get("filesystem"), "label": p.get("label"),
            }
            for p in parts
        ],
        "gaps_not_backed_up": gaps,
        "unpartitioned_tail_bytes": (size - parts[-1]["end"]) if size is not None else None,
    }


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    part = path.with_name(path.name + ".part")
    with open(part, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part, path)


# ---------------------------------------------------------------------------
# Copy / verification
# ---------------------------------------------------------------------------

def hash_source_range(handle: BinaryIO, offset: int, size: int) -> str:
    h = hashlib.sha256()
    cursor, remaining = offset, size
    while remaining:
        length = min(CHUNK, remaining)
        chunk = read_at(handle, cursor, length)
        if len(chunk) != length:
            raise OSError(f"short source read at offset {cursor}")
        h.update(chunk)
        cursor += length
        remaining -= length
    return h.hexdigest()


def readback_sha256(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def _drop_destination_cache(handle: Any) -> None:
    # Best effort on the DESTINATION file only, so that the read-back hits the disk.
    if hasattr(os, "posix_fadvise"):
        try:
            os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
        except OSError:
            pass


def copy_component(
    handle: BinaryIO,
    component: dict[str, Any],
    destination: Path,
    reread: bool,
    progress: Callable[[str, int, int], None],
) -> None:
    final = destination / component["file"]
    part = destination / (component["file"] + ".part")
    component["status"] = "in_progress"
    if final.exists() or part.exists():
        raise FileExistsError(f"refusing to overwrite {final.name}")

    h = hashlib.sha256()
    cursor, remaining, written = component["offset"], component["size"], 0
    with open(part, "xb") as out:
        while remaining:
            length = min(CHUNK, remaining)
            chunk = read_at(handle, cursor, length)
            if len(chunk) != length:
                raise OSError(f"short source read at offset {cursor}: {len(chunk)}/{length} bytes")
            out.write(chunk)
            h.update(chunk)
            cursor += length
            remaining -= length
            written += length
            progress(component["label"], written, component["size"])
        out.flush()
        os.fsync(out.fileno())
        _drop_destination_cache(out)
    component["bytes_written"] = written
    component["sha256_stream"] = h.hexdigest()
    if reread:
        component["sha256_source_reread"] = hash_source_range(handle, component["offset"], component["size"])
    dest_sha, dest_size = readback_sha256(part)
    component["sha256_destination"] = dest_sha
    component["destination_size"] = dest_size

    problems = []
    if dest_size != component["size"]:
        problems.append(f"destination size {dest_size} != expected {component['size']}")
    if dest_sha != component["sha256_stream"]:
        problems.append("destination SHA-256 differs from the bytes read from the source")
    if reread and component["sha256_source_reread"] != component["sha256_stream"]:
        problems.append("second read of the source range gave a different SHA-256 (unstable reader?)")
    if component.get("expected_sha256") and component["expected_sha256"] != component["sha256_stream"]:
        problems.append("source pre-P1 area changed since identification")

    if problems:
        failed = destination / (component["file"] + ".FAILED")
        os.replace(part, failed)
        component["file"] = failed.name
        component["status"] = "failed"
        component["error"] = "; ".join(problems)
        return
    os.replace(part, final)
    component["sha256"] = dest_sha
    component["status"] = "verified"


def _fsync_dir(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(path, os.O_RDONLY)  # destination directory, never the source
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def make_progress(enabled: bool) -> Callable[[str, int, int], None]:
    state: dict[str, int] = {}

    def report(label: str, done: int, total: int) -> None:
        if not enabled:
            return
        last = state.get(label, -1)
        if done == total or last < 0 or done - last >= PROGRESS_STEP:
            state[label] = done
            percent = 100 * done // total if total else 100
            print(f"{label}: {human_size(done)} / {human_size(total)} ({percent} %)", file=sys.stderr, flush=True)

    return report


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def plan_components(identity: dict[str, Any], include_userdata: bool) -> list[dict[str, Any]]:
    parts = identity["partitions"]
    inspection = identity["inspection"]
    components = [
        {"name": "pre_p1", "label": "pre-P1 (MBR/U-Boot/HWCONFIG)", "offset": 0,
         "size": parts[1]["offset"], "required": True,
         "expected_sha256": inspection["pre_p1_sha256"]},
        {"name": "p1_rootfs", "label": "P1 rootfs", "offset": parts[1]["offset"],
         "size": parts[1]["size"], "required": True},
        {"name": "p2_recoveryfs", "label": "P2 recoveryfs", "offset": parts[2]["offset"],
         "size": parts[2]["size"], "required": True},
        {"name": "p3_userdata", "label": "P3 KOBOeReader", "offset": parts[3]["offset"],
         "size": parts[3]["size"], "required": include_userdata},
    ]
    for component in components:
        component["file"] = COMPONENT_FILES[component["name"]]
        component["status"] = "pending" if component["required"] else "not_requested"
    return components


def run_backup(
    source: str,
    destination: Path,
    *,
    include_userdata: bool = False,
    reread: bool = True,
    dry_run: bool = False,
    allow_unverified_destination: bool = False,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Identify, check, then copy. Raises Refusal before writing anything."""
    progress = progress or (lambda *_: None)
    identity = identify_source(source)
    components = plan_components(identity, include_userdata)
    requested = [c for c in components if c["required"]]
    needed = sum(c["size"] for c in requested) + SPACE_MARGIN

    destination = destination.expanduser()
    reasons: list[str] = []
    try:
        dest_abs = destination.resolve()
    except OSError as exc:
        raise Refusal([f"destination path cannot be resolved: {exc}"])
    if dest_abs.exists():
        if not dest_abs.is_dir():
            reasons.append(f"destination exists and is not a directory: {dest_abs}")
        elif any(dest_abs.iterdir()):
            reasons.append(f"destination directory is not empty (collision refused): {dest_abs}")
    if identity["kind"] == "image_file":
        try:
            if Path(source).resolve() == dest_abs:
                reasons.append("destination is the source image itself")
        except OSError:
            pass
    on_source = destination_on_source(source, identity["kind"], dest_abs)
    if on_source == "on_source":
        reasons.append("destination is located on the source medium")
    elif on_source == "undetermined" and not allow_unverified_destination:
        reasons.append(
            "cannot determine whether the destination is on the source medium "
            "(re-run with --allow-unverified-destination only if you are sure it is not)"
        )
    free = disk_free(nearest_existing(dest_abs))
    if free < needed:
        reasons.append(f"not enough free space at destination: need {needed} bytes, {free} available")
    if reasons:
        raise Refusal(reasons)

    inspection = identity["inspection"]
    with open_source(source) as handle:
        sector0 = read_at(handle, 0, SECTOR_SIZE)
        hw = inspection["hwconfig"]
        hwconfig_raw = read_at(handle, hw["offset"], inspector.HWCONFIG_HEADER_SIZE + hw["payload_size"])

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "created_utc": utc_now(),
        "completed_utc": None,
        "status": "dry_run" if dry_run else "in_progress",
        "complete": False,
        "source": {
            "path_at_backup_time": source,
            "path_is_identity": False,
            "kind": identity["kind"],
            "size": identity["source_size"],
            "size_from": identity["size_from"],
        },
        "identification": describe_identity(identity),
        "mbr": describe_mbr(identity, sector0),
        "destination": {"path": str(dest_abs), "on_source_check": on_source,
                        "required_bytes": needed, "free_bytes_before": free},
        "options": {"include_userdata": include_userdata, "source_reread": reread},
        "components": components,
        "target_fingerprint": build_fingerprint(identity, hwconfig_raw),
        "identity_recheck": None,
        "warnings": identity["warnings"],
        "errors": [],
    }
    if dry_run:
        return manifest

    dest_abs.mkdir(parents=True, exist_ok=True)
    manifest_path = dest_abs / MANIFEST_NAME
    write_json_atomic(manifest_path, manifest)
    try:
        with open_source(source) as handle:
            for component in requested:
                try:
                    copy_component(handle, component, dest_abs, reread, progress)
                except (OSError, ValueError) as exc:
                    component["status"] = "failed"
                    component["error"] = str(exc)
                write_json_atomic(manifest_path, manifest)
                if component["status"] != "verified":
                    manifest["errors"].append(f"{component['name']}: {component.get('error')}")
                    break
            for component in requested:
                if component["status"] == "pending":
                    component["status"] = "not_started"
            if all(c["status"] == "verified" for c in requested):
                after = hash_source_range(handle, 0, components[0]["size"])
                matches = after == inspection["pre_p1_sha256"]
                manifest["identity_recheck"] = {"pre_p1_sha256_after_copy": after, "matches": matches}
                if not matches:
                    manifest["errors"].append("pre-P1 area changed during the backup (card swapped or modified?)")
    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        manifest["errors"].append("interrupted by user")
        for component in requested:
            if component["status"] in ("pending", "in_progress"):
                component["status"] = "interrupted" if component["status"] == "in_progress" else "not_started"
        write_json_atomic(manifest_path, manifest)
        raise

    verified = [c for c in requested if c["status"] == "verified"]
    with open(dest_abs / SUMS_NAME, "w", encoding="utf-8", newline="\n") as sums:
        for component in verified:
            sums.write(f"{component['sha256']} *{component['file']}\n")
        sums.flush()
        os.fsync(sums.fileno())
    complete = (
        len(verified) == len(requested)
        and bool(manifest["identity_recheck"] and manifest["identity_recheck"]["matches"])
        and not manifest["errors"]
    )
    manifest["complete"] = complete
    manifest["status"] = "complete" if complete else "failed"
    manifest["completed_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    _fsync_dir(dest_abs)
    return manifest


def print_summary(manifest: dict[str, Any], lang: dict[str, str]) -> None:
    print(f"{lang['destination']}: {manifest['destination']['path']}")
    for c in manifest["components"]:
        if c["status"] == "not_requested":
            print(f"  - {lang['not_included']}")
            continue
        sha = c.get("sha256") or c.get("sha256_destination") or ""
        print(f"  - {c['label']}: {c['status']} — {c['file']} {c['size']:,} bytes {sha}")
        if c.get("error"):
            print(f"      {c['error']}")
    print(f"{lang['fingerprint']}: {manifest['target_fingerprint']['fingerprint_sha256']}")
    for warning in manifest.get("warnings", []):
        print(f"  WARNING: {warning}")
    for error in manifest.get("errors", []):
        print(f"  ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only backup of a confirmed Kobo Aura HD / E606C0 microSD or full-disk image."
    )
    parser.add_argument("source", help=r"Raw device (\\.\PhysicalDriveN, /dev/sdX) or full-disk image. Opened read-only.")
    parser.add_argument("destination", help="Backup directory to create (must not exist or be empty).")
    parser.add_argument("--include-userdata", action="store_true",
                        help="Also back up P3 KOBOeReader (whole partition, can be ~30 GB).")
    parser.add_argument("--single-pass", action="store_true",
                        help="Do not re-read each source range a second time to compare SHA-256.")
    parser.add_argument("--dry-run", action="store_true", help="Identify and check only; create nothing.")
    parser.add_argument("--allow-unverified-destination", action="store_true",
                        help="Proceed when it cannot be determined whether the destination is on the source.")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Print only the JSON manifest/result on stdout (progress goes to stderr).")
    parser.add_argument("--quiet", action="store_true", help="No progress output.")
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    args = parser.parse_args(argv)
    lang = FR if args.lang == "fr" else EN
    for stream in (sys.stdout, sys.stderr):
        # A Windows console/pipe may not be UTF-8: never crash on a Unicode path.
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    if not args.json_output:
        print(lang["title"])
    try:
        manifest = run_backup(
            args.source, Path(args.destination),
            include_userdata=args.include_userdata, reread=not args.single_pass,
            dry_run=args.dry_run, allow_unverified_destination=args.allow_unverified_destination,
            progress=make_progress(not args.quiet),
        )
    except Refusal as refusal:
        if args.json_output:
            print(json.dumps({"schema_version": MANIFEST_SCHEMA_VERSION, "tool": TOOL_NAME,
                              "status": "refused", "complete": False, "reasons": refusal.reasons},
                             indent=2))
        else:
            print(lang["refused"])
            for reason in refusal.reasons:
                print(f"  - {reason}")
        return EXIT_REFUSED
    except KeyboardInterrupt:
        if args.json_output:
            print(json.dumps({"schema_version": MANIFEST_SCHEMA_VERSION, "tool": TOOL_NAME,
                              "status": "interrupted", "complete": False}, indent=2))
        else:
            print(lang["interrupted"])
        return EXIT_INTERRUPTED

    if args.json_output:
        print(json.dumps(manifest, indent=2))  # ASCII-escaped: safe on any console encoding
    else:
        if manifest["status"] == "dry_run":
            print(lang["plan"])
        print_summary(manifest, lang)
        if manifest["status"] == "dry_run":
            print(lang["dry_run"])
        else:
            print(lang["complete"] if manifest["complete"] else lang["failed"])
    if manifest["status"] == "dry_run" or manifest["complete"]:
        return EXIT_COMPLETE
    return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
