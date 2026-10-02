#!/usr/bin/env python3
"""Build a local Aura HD rootfs image from a verified PMKB backup.

The construction backend is deliberately Linux-only and operates on local files.
Physical/block-device paths are rejected. No restore operation exists here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHUNK = 4 * 1024 * 1024
SUPPORTED_BACKUP_SCHEMA = 1
PHYSICALDRIVE_RE = re.compile(r"^\\\\[.?]\\PhysicalDrive\d+$", re.I)
REQUIRED_TOOLS = ("mke2fs", "debugfs", "e2fsck")


def looks_like_device(value: str) -> bool:
    raw = value.strip().replace("/", "\\")
    if PHYSICALDRIVE_RE.match(raw):
        return True
    unix = value.strip().replace("\\", "/")
    return unix == "/dev" or unix.startswith("/dev/")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
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
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "ok": False, "errors": [f"cannot read backup manifest: {exc}"], "warnings": warnings}
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
                if isinstance(expected_size, int) and recovery_path.stat().st_size != expected_size:
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
    result: dict[str, Any] = {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed" if errors else "ready", "ok": False, "errors": errors, "warnings": warnings}
    if not errors:
        result.update({"rootfs_size": p1_size, "backup_manifest_sha256": sha256_file(manifest_path), "target_fingerprint": manifest.get("target_fingerprint"), "recovery_sha256": _component_hash(recovery or {})})
    return result


def require_linux_backend() -> list[str]:
    errors = []
    if sys.platform != "linux":
        errors.append("rootfs construction requires Linux (native, WSL2, VM, or live USB)")
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool) is None:
            errors.append(f"required Linux tool not found: {tool}")
    return errors


def run_checked(argv: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)


def build_rootfs(manifest_path: Path, recovery_path: Path, output_path: Path) -> dict[str, Any]:
    result = preflight(manifest_path, recovery_path, output_path)
    if result["status"] != "ready":
        return result
    backend_errors = require_linux_backend()
    if backend_errors:
        result.update(status="failed", errors=backend_errors)
        return result
    p1_size = int(result["rootfs_size"])
    part = output_path.with_name(output_path.name + ".part")
    rebuild_manifest = output_path.with_name(output_path.name + ".rebuild.json")
    if part.exists() or rebuild_manifest.exists():
        result.update(status="failed", errors=["temporary output or rebuild manifest already exists; refusing collision"])
        return result
    log: list[str] = []
    try:
        with part.open("xb") as handle:
            handle.truncate(p1_size)
        mk = run_checked(["mke2fs", "-q", "-t", "ext4", "-F", "-L", "rootfs", str(part)])
        log.append(mk.stdout)
        with tempfile.TemporaryDirectory(prefix="pmkb-rebuild-") as td:
            td_path = Path(td)
            fs_tgz = td_path / "fs.tgz"
            md5sum = td_path / "fs.md5sum"
            for source, dest in (("/upgrade/fs.tgz", fs_tgz), ("/upgrade/fs.md5sum", md5sum)):
                run_checked(["debugfs", "-R", f"dump -p {source} {dest}", str(recovery_path)])
                if not dest.is_file() or dest.stat().st_size == 0:
                    raise RuntimeError(f"required recovery artifact missing or empty: {source}")
            root = td_path / "root"
            root.mkdir()
            with tarfile.open(fs_tgz, "r:gz") as tf:
                members = tf.getmembers()
                if not members:
                    raise RuntimeError("fs.tgz is empty")
                for member in members:
                    name = member.name.replace("\\", "/")
                    p = Path(name)
                    if p.is_absolute() or ".." in p.parts:
                        raise RuntimeError(f"unsafe archive path: {member.name}")
                    if member.ischr() or member.isblk():
                        raise RuntimeError(f"device node requires privileged metadata path not supported safely in V1: {member.name}")
                    if member.issym() or member.islnk():
                        target = Path(member.linkname.replace("\\", "/"))
                        if target.is_absolute() or ".." in target.parts:
                            raise RuntimeError(f"unsafe archive link: {member.name}")
                tf.extractall(root, members=members, filter="data")
            run_checked(["debugfs", "-w", "-R", f"rdump {root} /", str(part)])
        fsck = subprocess.run(["e2fsck", "-f", "-n", str(part)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log.append(fsck.stdout)
        if fsck.returncode not in (0, 1):
            raise RuntimeError(f"e2fsck rejected rebuilt image (exit {fsck.returncode})")
        if part.stat().st_size != p1_size:
            raise RuntimeError("rebuilt image size changed unexpectedly")
        digest = sha256_file(part)
        os.replace(part, output_path)
        report = {
            "schema_version": 1,
            "tool": "rebuild-rootfs",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "complete": True,
            "device": "E606C0",
            "backup_manifest_sha256": result["backup_manifest_sha256"],
            "target_fingerprint": result.get("target_fingerprint"),
            "recovery_sha256": result.get("recovery_sha256"),
            "rootfs_size": p1_size,
            "rootfs_sha256": digest,
            "checks": {"size": True, "filesystem": True, "recovery_artifacts": True},
            "warnings": ["V1 rejects recovery archives containing device nodes; ownership fidelity is not yet independently verified."],
            "errors": [],
        }
        rebuild_manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    except (OSError, subprocess.CalledProcessError, RuntimeError, tarfile.TarError) as exc:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "complete": False, "ok": False, "errors": [str(exc)], "warnings": [], "temporary_output": str(part) if part.exists() else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild a local Aura HD rootfs image from a verified PMKB backup")
    parser.add_argument("backup_manifest")
    parser.add_argument("recovery_image")
    parser.add_argument("output_image")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--build", action="store_true", help="perform Linux-only local image construction")
    args = parser.parse_args()
    paths = (Path(args.backup_manifest), Path(args.recovery_image), Path(args.output_image))
    result = build_rootfs(*paths) if args.build else preflight(*paths)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PimpMyKobo-AuraHD — rebuild-rootfs")
        print("LOCAL FILES ONLY — physical/block devices are forbidden.")
        if result["status"] == "ready":
            print(f"READY: local inputs validated; planned P1 size = {result['rootfs_size']:,} bytes")
            print("Use --build under Linux/WSL2 to construct the local image.")
        elif result["status"] == "ok":
            print(f"OK: rebuilt image {args.output_image} ({result['rootfs_size']:,} bytes)")
            print(f"SHA-256: {result['rootfs_sha256']}")
        else:
            print("REFUSED/FAILED:")
            for error in result.get("errors", []):
                print(f"  - {error}")
    return 0 if result["status"] in ("ready", "ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
