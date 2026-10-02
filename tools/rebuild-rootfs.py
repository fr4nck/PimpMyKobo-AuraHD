#!/usr/bin/env python3
"""Local-only preflight for rebuilding an Aura HD rootfs image.

This tool deliberately performs no filesystem construction yet. It validates a
PMKB backup manifest and its local P2 image while refusing physical/block-device
paths by construction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

CHUNK = 4 * 1024 * 1024
SUPPORTED_BACKUP_SCHEMA = 1
PHYSICALDRIVE_RE = re.compile(r"^\\\\[.?]\\PhysicalDrive\d+$", re.I)


def looks_like_device(value: str) -> bool:
    raw = value.strip().replace("/", "\\")
    if PHYSICALDRIVE_RE.match(raw):
        return True
    unix = value.strip().replace("\\", "/")
    return unix == "/dev" or unix.startswith("/dev/")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("backup manifest root must be an object")
    return value


def _components(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("components")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _component(manifest: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((x for x in _components(manifest) if x.get("name") == name), None)


def _partitions(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    # backup-aura-hd v1 records geometry under mbr.partitions. Keep the direct
    # form temporarily accepted for early synthetic manifests.
    mbr = manifest.get("mbr")
    value = mbr.get("partitions") if isinstance(mbr, dict) else manifest.get("partitions")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _partition(manifest: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next((x for x in _partitions(manifest) if x.get("number") == number), None)


def _is_e606c0(manifest: dict[str, Any]) -> bool:
    ident = manifest.get("identification")
    if isinstance(ident, dict):
        if ident.get("aura_hd_e606c0") is True:
            return True
        hw = ident.get("hwconfig")
        if isinstance(hw, dict):
            pcb = hw.get("pcb")
            if isinstance(pcb, dict) and pcb.get("raw") == 28 and pcb.get("decoded") == "E606C0":
                return True
    return manifest.get("device") == "E606C0"


def _component_hash(component: dict[str, Any]) -> str | None:
    # The verified destination hash is authoritative for backup-aura-hd v1.
    for key in ("sha256_destination", "sha256", "sha256_stream"):
        value = component.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
            return value.lower()
    return None


def preflight(manifest_path: Path, recovery_path: Path, output_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for label, path in (("manifest", manifest_path), ("recovery", recovery_path), ("output", output_path)):
        if looks_like_device(str(path)):
            errors.append(f"{label} path is a physical/block device and is forbidden")
    if errors:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "ok": False, "errors": errors, "warnings": warnings}

    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "ok": False,
                "errors": [f"cannot read backup manifest: {exc}"], "warnings": warnings}

    if manifest.get("schema_version") != SUPPORTED_BACKUP_SCHEMA:
        errors.append(f"unsupported backup schema: {manifest.get('schema_version')!r}")
    if manifest.get("complete") is not True or manifest.get("status") not in ("complete", "ok"):
        errors.append("backup manifest is not complete")
    if not _is_e606c0(manifest):
        errors.append("backup manifest does not identify E606C0")

    p1 = _partition(manifest, 1)
    p1_component = _component(manifest, "p1_rootfs")
    p1_size = p1.get("size") if p1 else None
    if not isinstance(p1_size, int) and p1_component:
        p1_size = p1_component.get("size")
    if not isinstance(p1_size, int) or p1_size <= 0:
        errors.append("backup manifest has no valid P1 size")

    recovery = _component(manifest, "p2_recoveryfs")
    if recovery is None:
        legacy = manifest.get("recovery")
        recovery = legacy if isinstance(legacy, dict) else None
    if recovery is None or recovery.get("status", "verified") != "verified":
        errors.append("backup manifest has no verified P2 recovery component")
    else:
        expected_size = recovery.get("size")
        expected_sha = _component_hash(recovery)
        if not isinstance(expected_size, int) or expected_size <= 0:
            errors.append("backup manifest has no valid recovery size")
        if expected_sha is None:
            errors.append("backup manifest has no valid recovery SHA-256")
        try:
            if not recovery_path.is_file():
                errors.append("recovery input is not a regular file")
            else:
                actual_size = recovery_path.stat().st_size
                if isinstance(expected_size, int) and actual_size != expected_size:
                    errors.append("recovery size does not match backup manifest")
                if expected_sha is not None and sha256_file(recovery_path) != expected_sha:
                    errors.append("recovery SHA-256 does not match backup manifest")
        except OSError as exc:
            errors.append(f"cannot read recovery input: {exc}")

    if output_path.exists():
        errors.append("output already exists; implicit overwrite is forbidden")
    elif isinstance(p1_size, int):
        try:
            if shutil.disk_usage(output_path.parent).free < p1_size:
                errors.append("insufficient free space for rootfs image")
        except OSError as exc:
            errors.append(f"cannot determine destination free space: {exc}")

    result: dict[str, Any] = {
        "schema_version": 1,
        "tool": "rebuild-rootfs",
        "status": "failed" if errors else "ready",
        "ok": False,
        "errors": errors,
        "warnings": warnings,
    }
    if not errors:
        result.update({
            "rootfs_size": p1_size,
            "backup_manifest_sha256": sha256_file(manifest_path),
            "target_fingerprint": manifest.get("target_fingerprint"),
            "recovery_sha256": _component_hash(recovery or {}),
            "note": "Preflight passed; filesystem construction is not implemented in this commit.",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local inputs for a future Aura HD rootfs rebuild")
    parser.add_argument("backup_manifest")
    parser.add_argument("recovery_image")
    parser.add_argument("output_image")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = preflight(Path(args.backup_manifest), Path(args.recovery_image), Path(args.output_image))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PimpMyKobo-AuraHD — rebuild-rootfs preflight")
        print("LOCAL FILES ONLY — physical/block devices are forbidden.")
        if result["status"] == "ready":
            print(f"READY: validated local inputs; planned P1 size = {result['rootfs_size']:,} bytes")
            print("No image was created by this preflight version.")
        else:
            print("REFUSED:")
            for error in result["errors"]:
                print(f"  - {error}")
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
