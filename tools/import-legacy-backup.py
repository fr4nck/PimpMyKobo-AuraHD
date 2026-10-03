#!/usr/bin/env python3
"""Qualify historical local files for reconstruction, never for physical restore."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT = "pmkb-legacy-rebuild-v1"
PROVENANCE = {
    "kind": "legacy/imported",
    "association": "declared_not_verified",
    "scope": "local_rootfs_reconstruction_only",
    "physical_restore_eligible": False,
}
WARNINGS = [
    "The association of pre-P1 and P2 with the same historical card is declared, not verified.",
    "P1/P3 contents, original card capacity and source reread were not verified.",
    "P2 verification covers file size, SHA-256 and ext4 superblock, not filesystem health or recovery artifacts; rebuild validates fs.tgz during construction.",
]


def load_inspector():
    spec = importlib.util.spec_from_file_location("legacy_inspector", Path(__file__).with_name("inspect-aura-hd.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def reject_device(path: Path) -> None:
    raw = str(path).replace("\\", "/").lower()
    if raw.startswith("//") or raw == "/dev" or raw.startswith("/dev/"):
        raise ValueError("device/UNC paths are forbidden")
    resolved = str(path.resolve()).replace("\\", "/").lower()
    if resolved.startswith("//") or resolved == "/dev" or resolved.startswith("/dev/"):
        raise ValueError("resolved device/UNC paths are forbidden")


def regular(path: Path) -> None:
    reject_device(path)
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"not a regular file: {path}")


def digest(path: Path) -> str:
    regular(path)
    h = hashlib.sha256()
    with path.open("rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("opened input is not a regular file")
        while chunk := handle.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def qualify(pre_p1: Path, recovery: Path, pre_sha: str, recovery_sha: str) -> dict[str, Any]:
    """Read only supplied regular files; expected hashes are historical declarations."""
    for value in (pre_sha, recovery_sha):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("expected SHA-256 must be 64 lowercase hexadecimal characters")
    for path, expected in ((pre_p1, pre_sha), (recovery, recovery_sha)):
        if digest(path) != expected:
            raise ValueError(f"SHA-256 mismatch: {path}")
    inspector = load_inspector()
    with pre_p1.open("rb") as handle:
        # This is a prefix, not a full card: do not claim a capacity/bounds check.
        mbr = inspector.parse_mbr(handle)
        hw = inspector.parse_hwconfig(handle)
    parts = mbr["partitions"]
    if not mbr["valid"] or [p["number"] for p in parts] != [1, 2, 3]:
        raise ValueError("invalid three-partition MBR")
    if [p["type"] for p in parts[:2]] != [0x83, 0x83] or parts[2]["type"] not in (0x0B, 0x0C):
        raise ValueError("unexpected Aura HD partition types")
    if pre_p1.stat().st_size != parts[0]["offset"]:
        raise ValueError("pre-P1 file size differs from P1 offset")
    if not hw or not hw["is_aura_hd_e606c0"]:
        raise ValueError("HWCONFIG does not confirm E606C0 v1.7/39")
    if recovery.stat().st_size != parts[1]["size"]:
        raise ValueError("P2 file size differs from MBR")
    with recovery.open("rb") as handle:
        handle.seek(1024)
        sb = handle.read(1024)
    if len(sb) != 1024 or sb[56:58] != b"\x53\xef":
        raise ValueError("P2 has no ext superblock")
    u16 = lambda offset: int.from_bytes(sb[offset:offset + 2], "little")
    u32 = lambda offset: int.from_bytes(sb[offset:offset + 4], "little")
    log_block = u32(24)
    inode = u16(88) if u32(76) else 128
    if log_block > 6:
        raise ValueError("invalid ext block size")
    block = 1024 << log_block
    blocks = u32(4) + ((u32(336) << 32) if u32(96) & 0x80 else 0)
    if not u32(96) & 0x40 or not 128 <= inode <= block or inode & (inode - 1):
        raise ValueError("invalid ext4 layout")
    if not blocks or blocks * block > recovery.stat().st_size:
        raise ValueError("ext4 filesystem exceeds P2 file")
    ext4 = {"block_size": block, "inode_size": inode, "blocks": blocks,
            "feature_masks": {"compat": u32(92), "incompat": u32(96), "ro_compat": u32(100)},
            "needs_recovery": bool(u32(96) & 4)}
    # beyond_end=False from the parser is not evidence about the absent card.
    for part in parts:
        part.pop("beyond_end", None)
    return {
        "schema_version": 1, "tool": "import-legacy-backup", "contract": CONTRACT,
        "status": "qualified", "complete": False, "qualified_for_rebuild": True,
        "provenance": dict(PROVENANCE), "device": "E606C0",
        "mbr": {"valid": True, "partitions": parts, "source_capacity_verified": False},
        "identification": {"aura_hd_e606c0": True, "hwconfig": hw},
        "components": [
            {"name": "pre_p1", "size": pre_p1.stat().st_size, "sha256": pre_sha, "status": "verified"},
            {"name": "p2_recoveryfs", "size": recovery.stat().st_size, "sha256": recovery_sha,
             "status": "verified", "ext4_superblock": ext4},
            {"name": "p1_rootfs", "status": "not_qualified"},
            {"name": "p3_userdata", "status": "not_qualified"},
        ],
        "checks": {"file_hashes": True, "mbr_geometry": True, "hwconfig": True,
                   "p2_size": True, "p2_ext4_superblock": True,
                   "p2_filesystem_health": "not_checked", "recovery_artifacts": "not_checked"},
        "warnings": list(WARNINGS), "errors": [],
    }


def validate_import(manifest: dict[str, Any], manifest_path: Path, recovery: Path) -> None:
    if manifest.get("contract") != CONTRACT or manifest.get("provenance") != PROVENANCE:
        raise ValueError("unsupported legacy provenance/contract")
    components = manifest.get("components")
    if not isinstance(components, list) or len(components) != 4:
        raise ValueError("invalid legacy components")
    pre, p2 = components[:2]
    if (not isinstance(pre, dict) or not isinstance(p2, dict)
            or not isinstance(pre.get("file"), str) or not isinstance(p2.get("file"), str)):
        raise ValueError("missing legacy pre-P1 evidence")
    pre_path = Path(pre["file"].replace("\\", "/"))
    reject_device(pre_path)
    pre_path = manifest_path.parent / pre_path
    expected = qualify(pre_path, recovery, pre.get("sha256"), p2.get("sha256"))
    if set(manifest) - set(expected) - {"created_utc"}:
        raise ValueError("unexpected fields in legacy contract (native fingerprint is forbidden)")
    for index in (0, 1):
        expected["components"][index]["file"] = components[index].get("file")
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"legacy qualification differs from current evidence: {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pre_p1", type=Path)
    parser.add_argument("recovery", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-pre-p1-sha256", required=True)
    parser.add_argument("--expected-p2-sha256", required=True)
    parser.add_argument("--declare-same-source", action="store_true", required=True,
                        help="declare historical association; this is not proof")
    args = parser.parse_args()
    try:
        reject_device(args.output)
        # Directory devices/aliases and symlink parents are rejected before creation.
        if not args.output.parent.is_dir():
            raise ValueError("output parent must exist")
        result = qualify(args.pre_p1, args.recovery, args.expected_pre_p1_sha256, args.expected_p2_sha256)
        for component, path in zip(result["components"], (args.pre_p1, args.recovery)):
            component["file"] = os.path.relpath(path.resolve(), args.output.parent.resolve()).replace("\\", "/")
        result["created_utc"] = datetime.now(timezone.utc).isoformat()
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "complete": False, "errors": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
