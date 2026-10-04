#!/usr/bin/env python3
"""Simulate a P1 replacement in a NEW local disk-image file. No physical restore."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

CHUNK = 4 * 1024 * 1024


def load_peer(script: str):
    spec = importlib.util.spec_from_file_location(script.replace("-", "_"), Path(__file__).with_name(script))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


legacy = load_peer("import-legacy-backup.py")


def read_json(path: Path) -> dict[str, Any]:
    legacy.regular(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def hash_region(handle: BinaryIO, offset: int, size: int) -> str:
    handle.seek(offset)
    h = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = handle.read(min(CHUNK, remaining))
        if not chunk:
            raise ValueError("short disk-image read")
        h.update(chunk)
        remaining -= len(chunk)
    return h.hexdigest()


def validate_rootfs_report(report: dict[str, Any], report_path: Path, rootfs: Path,
                           p1_size: int) -> tuple[str, str]:
    """Validate a typed P1 producer report and independently check PMKB ext4."""
    digest = legacy.digest(rootfs)
    tool = report.get("tool")
    common = (type(report.get("schema_version")) is int and report.get("schema_version") == 1
              and report.get("complete") is True
              and report.get("errors") == [] and report.get("physical_restore_eligible") is False
              and report.get("hardware_qualified") is False and report.get("device") == "E606C0"
              and type(report.get("rootfs_size")) is int and report.get("rootfs_size") == p1_size
              and rootfs.stat().st_size == p1_size
              and report.get("rootfs_sha256") == digest)
    if not common:
        raise ValueError("rootfs build report is incomplete or inconsistent with E606C0 P1 image")
    if tool == "rebuild-rootfs":
        checks = report.get("checks", {})
        if (report.get("status") != "ok" or report.get("target_fingerprint") is not None
                or not isinstance(checks, dict) or checks.get("size") is not True
                or checks.get("ext4_parameters") is not True or checks.get("e2fsck") != "clean"):
            raise ValueError("rebuild-rootfs report has no successful size/ext4/e2fsck checks")
        return tool, digest
    if tool != "build-koreader-rootfs":
        raise ValueError("unsupported P1 producer report tool")
    if report.get("status") != "experimental":
        raise ValueError("build-koreader-rootfs report status is not experimental")
    ext4 = report.get("ext4")
    if (not isinstance(ext4, dict) or ext4.get("label") != "rootfs"
            or type(ext4.get("block_size")) is not int or ext4["block_size"] <= 0
            or type(ext4.get("inode_size")) is not int or ext4["inode_size"] <= 0):
        raise ValueError("build-koreader-rootfs report has invalid ext4 metadata")
    executable = shutil.which("e2fsck", path="/usr/sbin:/usr/bin:/sbin:/bin")
    if not executable:
        raise ValueError("e2fsck is required to revalidate build-koreader-rootfs images")
    checked = subprocess.run([executable, "-f", "-n", str(rootfs.resolve())],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, env={**os.environ, "LC_ALL": "C"})
    if checked.returncode != 0:
        raise ValueError(f"read-only e2fsck rejected PMKB P1 (exit {checked.returncode}): {checked.stdout}")
    return tool, digest


def preflight(manifest_path: Path, rebuild_path: Path, rootfs: Path, target: Path,
              output: Path, *, accept_legacy_import: bool = False,
              require_copy_space: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1, "tool": "restore-rootfs", "mode": "disk_image_simulation",
        "status": "refused", "complete": False, "physical_restore_eligible": False,
        "errors": [], "warnings": [],
    }
    try:
        if not accept_legacy_import:
            raise ValueError("this simulation requires --accept-legacy-import")
        for path in (manifest_path, rebuild_path, rootfs, target):
            legacy.regular(path)
        for path in (output, Path(str(output) + ".part"), Path(str(output) + ".simulation.json")):
            legacy.reject_device(path)
            if path.exists() or path.is_symlink():
                raise ValueError(f"output collision; no overwrite: {path}")
        if not output.parent.is_dir():
            raise ValueError("output parent must exist")
        manifest = read_json(manifest_path)
        if manifest.get("tool") != "import-legacy-backup":
            raise ValueError("simulation v1 accepts only the explicit legacy contract")
        components = manifest.get("components")
        if not isinstance(components, list) or len(components) != 4 or not isinstance(components[1], dict):
            raise ValueError("invalid legacy components")
        recovery_file = components[1].get("file")
        if not isinstance(recovery_file, str):
            raise ValueError("missing P2 evidence path")
        recovery = manifest_path.parent / recovery_file.replace("\\", "/")
        legacy.validate_import(manifest, manifest_path, recovery)
        parts = manifest["mbr"]["partitions"]
        p1, p2, p3 = parts
        size = target.stat().st_size
        inspector = legacy.load_inspector()
        with target.open("rb") as handle:
            mbr = inspector.parse_mbr(handle, size)
            hw = inspector.parse_hwconfig(handle)
            geometry = [{k: v for k, v in p.items() if k != "beyond_end"} for p in mbr["partitions"]]
            if not mbr["valid"] or geometry != parts or not hw or not hw["is_aura_hd_e606c0"]:
                raise ValueError("target disk-image geometry/HWCONFIG differs from qualified evidence")
            prefix_sha = hash_region(handle, 0, p1["offset"])
            p2_sha = hash_region(handle, p2["offset"], p2["size"])
            if prefix_sha != components[0]["sha256"] or p2_sha != components[1]["sha256"]:
                raise ValueError("target pre-P1/P2 differs from qualified evidence")
            # The entire complement of P1 includes gaps and trailing bytes too.
            suffix_sha = hash_region(handle, p1["end"], size - p1["end"])
            p3_sha = hash_region(handle, p3["offset"], p3["size"])
        rebuilt = read_json(rebuild_path)
        root_sha = legacy.digest(rootfs)
        checks = rebuilt.get("checks", {})
        report_tool = rebuilt.get("tool")
        if report_tool == "rebuild-rootfs":
            if (rebuilt.get("schema_version") != 1 or rebuilt.get("tool") != "rebuild-rootfs"
                or rebuilt.get("status") != "ok" or rebuilt.get("complete") is not True
                or rebuilt.get("device") != "E606C0" or rebuilt.get("errors") != []
                or rebuilt.get("backup_manifest_sha256") != legacy.digest(manifest_path)
                or rebuilt.get("recovery_sha256") != components[1]["sha256"]
                or rebuilt.get("rootfs_sha256") != root_sha
                or rebuilt.get("rootfs_size") != p1["size"] or rootfs.stat().st_size != p1["size"]
                or rebuilt.get("input_provenance") != legacy.PROVENANCE
                or rebuilt.get("physical_restore_eligible") is not False
                or rebuilt.get("target_fingerprint") is not None):
                raise ValueError("rebuilt image/report is inconsistent with the legacy evidence")
            if not isinstance(checks, dict) or checks.get("size") is not True or checks.get("ext4_parameters") is not True or checks.get("e2fsck") != "clean":
                raise ValueError("rebuild report has no successful size/ext4/e2fsck checks")
            for key, count in (("metadata", "entries"), ("content", "files")):
                check = checks.get(key, {})
                if not isinstance(check, dict) or type(check.get(count)) is not int or check[count] <= 0 or type(check.get("verified")) is not int or check["verified"] != check[count]:
                    raise ValueError(f"rebuild {key} verification is incomplete")
            md5 = checks.get("fs_md5sum", {})
            if not isinstance(md5, dict) or type(md5.get("present")) is not bool:
                raise ValueError("missing rebuild MD5 check")
            if md5["present"] and (type(md5.get("entries")) is not int or md5["entries"] <= 0 or type(md5.get("matched")) is not int or md5["matched"] != md5["entries"] or md5.get("missing") != [] or md5.get("mismatched") != []):
                raise ValueError("rebuild MD5 verification is incomplete")
            filesystem_check = "reported_by_rebuild_rootfs"
        elif report_tool == "build-koreader-rootfs":
            validate_rootfs_report(rebuilt, rebuild_path, rootfs, p1["size"])
            filesystem_check = "revalidated_locally_read_only_e2fsck"
        else:
            raise ValueError("unsupported P1 producer report tool")
        if require_copy_space and shutil.disk_usage(output.parent).free < size:
            raise ValueError("insufficient space for a full disk-image copy")
        result.update(
            status="ready", input_provenance=manifest["provenance"],
            disk_size=size, p1_offset=p1["offset"], p1_size=p1["size"], partitions=parts,
            rootfs_sha256=root_sha, target_sha256=legacy.digest(target),
            backup_manifest_sha256=legacy.digest(manifest_path), rootfs_report_sha256=legacy.digest(rebuild_path),
            rootfs_report_tool=report_tool,
            preserved_before={"pre_p1": prefix_sha, "suffix_after_p1": suffix_sha, "p2": p2_sha, "p3": p3_sha},
            checks={"target_geometry": True, "target_pre_p1_p2": True,
                    "rootfs_matches_build_report": True, "filesystem_checks": filesystem_check},
            warnings=[*manifest["warnings"], "Unsigned producer report: consistency checked; report authenticity and bootability are not established."],
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result["errors"] = [str(exc)]
    return result


def simulate(manifest_path: Path, rebuild_path: Path, rootfs: Path, target: Path,
             output: Path, *, accept_legacy_import: bool = False) -> dict[str, Any]:
    result = preflight(manifest_path, rebuild_path, rootfs, target, output, accept_legacy_import=accept_legacy_import)
    if result["status"] != "ready":
        return result
    part = Path(str(output) + ".part")
    try:
        # The source is always rb. Only the newly created clone is writable.
        copied = hashlib.sha256()
        with target.open("rb") as source, part.open("xb") as destination:
            while chunk := source.read(CHUNK):
                destination.write(chunk)
                copied.update(chunk)
        if copied.hexdigest() != result["target_sha256"] or part.stat().st_size != result["disk_size"]:
            raise ValueError("source disk-image changed during copy")
        replacement = hashlib.sha256()
        with rootfs.open("rb") as source, part.open("r+b") as destination:
            destination.seek(result["p1_offset"])
            remaining = result["p1_size"]
            while remaining:
                chunk = source.read(min(CHUNK, remaining))
                if not chunk:
                    raise ValueError("short rootfs read")
                destination.write(chunk)
                replacement.update(chunk)
                remaining -= len(chunk)
            if source.read(1) or replacement.hexdigest() != result["rootfs_sha256"]:
                raise ValueError("rootfs changed during replacement")
            destination.flush()
            os.fsync(destination.fileno())
        p1, p2, p3 = result["partitions"]
        with part.open("rb") as handle:
            after = {
                "pre_p1": hash_region(handle, 0, p1["offset"]),
                "suffix_after_p1": hash_region(handle, p1["end"], result["disk_size"] - p1["end"]),
                "p2": hash_region(handle, p2["offset"], p2["size"]),
                "p3": hash_region(handle, p3["offset"], p3["size"]),
            }
            p1_sha = hash_region(handle, p1["offset"], p1["size"])
        if after != result["preserved_before"] or p1_sha != result["rootfs_sha256"] or part.stat().st_size != result["disk_size"]:
            raise ValueError("P1 replacement or preserved disk-image regions failed verification")
        if legacy.digest(target) != result["target_sha256"]:
            raise ValueError("source disk-image changed during simulation")
        result.update(status="ok", complete=True, created_utc=datetime.now(timezone.utc).isoformat(),
                      preserved_after=after, output_sha256=legacy.digest(part), p1_sha256=p1_sha)
        result["checks"].update(p1_written_and_reread=True, outside_p1_unchanged=True, source_unchanged=True)
        # Publish without replacing a destination created concurrently (same FS).
        os.link(part, output)
        part.unlink()
        with Path(str(output) + ".simulation.json").open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, KeyboardInterrupt) as exc:
        result.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", complete=False,
                      errors=[str(exc) or "simulation interrupted"], temporary_output=str(part) if part.exists() else None)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("legacy_manifest", "rebuild_report", "rootfs", "disk_image", "output_image"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--accept-legacy-import", action="store_true")
    parser.add_argument("--simulate", action="store_true", help="create a new disk-image copy; default is a read-only plan")
    args = parser.parse_args()
    function = simulate if args.simulate else preflight
    result = function(args.legacy_manifest, args.rebuild_report, args.rootfs, args.disk_image,
                      args.output_image, accept_legacy_import=args.accept_legacy_import)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "interrupted":
        return 130
    return 0 if result["status"] in ("ready", "ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
