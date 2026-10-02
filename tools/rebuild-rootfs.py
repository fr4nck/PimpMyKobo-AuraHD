#!/usr/bin/env python3
"""PimpMyKobo-AuraHD: safe front-end for rebuilding a local rootfs image.

V1 intentionally stops before filesystem construction.  Its job is to validate
that inputs are local files produced by PMKB and to establish a hard boundary:
this tool never accepts a physical/block device as an input or output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

CHUNK = 4 * 1024 * 1024
SUPPORTED_BACKUP_SCHEMA = 1
PHYSICALDRIVE_RE = re.compile(r"^\\\\[.?]\\PhysicalDrive\d+$", re.I)


def looks_like_device(value: str) -> bool:
    """Conservatively reject paths that denote physical/block devices."""
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


def _find_partition(manifest: dict[str, Any], number: int) -> dict[str, Any] | None:
    parts = manifest.get("partitions")
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict) and part.get("number") == number:
                return part
    return None


def preflight(manifest_path: Path, recovery_path: Path, output_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for label, path in (("manifest", manifest_path), ("recovery", recovery_path), ("output", output_path)):
        if looks_like_device(str(path)):
            errors.append(f"{label} path is a physical/block device and is forbidden")

    if errors:
        return {"status": "failed", "ok": False, "errors": errors, "warnings": warnings}

    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "failed", "ok": False, "errors": [f"cannot read backup manifest: {exc}"], "warnings": warnings}

    schema = manifest.get("schema_version")
    if schema != SUPPORTED_BACKUP_SCHEMA:
        errors.append(f"unsupported backup schema: {schema!r}")

    if manifest.get("complete") is not True and manifest.get("status") != "ok":
        errors.append("backup manifest is not complete")

    identity = manifest.get("device") or manifest.get("identification")
    if isinstance(identity, dict):
        identity = identity.get("model") or identity.get("pcb") or identity.get("device")
    if identity not in ("E606C0", "Kobo Aura HD / Dragon / E606C0"):
        errors.append("backup manifest does not identify E606C0")

    p1 = _find_partition(manifest, 1)
    if not p1 or not isinstance(p1.get("size"), int) or p1["size"] <= 0:
        errors.append("backup manifest has no valid P1 size")

    recovery_record = manifest.get("recovery")
    if not isinstance(recovery_record, dict):
        recovery_record = manifest.get("components", {}).get("recovery") if isinstance(manifest.get("components"), dict) else None
    if not isinstance(recovery_record, dict):
        errors.append("backup manifest has no recovery component")
    else:
        expected_size = recovery_record.get("size")
        expected_sha = recovery_record.get("sha256")
        try:
            st = recovery_path.stat()
            if not recovery_path.is_file():
                errors.append("recovery input is not a regular file")
            else:
                if isinstance(expected_size, int) and st.st_size != expected_size:
                    errors.append("recovery size does not match backup manifest")
                if isinstance(expected_sha, str):
                    actual_sha = sha256_file(recovery_path)
                    if actual_sha.lower() != expected_sha.lower():
                        errors.append("recovery SHA-256 does not match backup manifest")
                else:
                    errors.append("backup manifest has no recovery SHA-256")
        except OSError as exc:
            errors.append(f"cannot read recovery input: {exc}")

    if output_path.exists():
        errors.append("output already exists; implicit overwrite is forbidden")
    else:
        parent = output_path.parent
        try:
            usage = shutil.disk_usage(parent)
            if p1 and isinstance(p1.get("size"), int) and usage.free < p1["size"]:
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
        result["rootfs_size"] = p1["size"]
        result["backup_manifest_sha256"] = sha256_file(manifest_path)
        result["source_fingerprint"] = manifest.get("source_fingerprint")
        result["note"] = "Preflight passed; filesystem construction is intentionally not implemented in this safety-first commit."
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate inputs for a future local-only Aura HD rootfs rebuild")
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
