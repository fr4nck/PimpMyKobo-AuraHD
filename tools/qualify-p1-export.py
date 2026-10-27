#!/usr/bin/env python3
"""L08-K read-only backup P1 to exported rootfs verification.

Use only canonical P1 bytes from a backup validated by the existing PMKB
verifier. No physical devices, writes, mounts, or ARM program execution.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "experimental" / "store-v0"
if str(STORE) not in sys.path:
    sys.path.insert(0, str(STORE))

from ext4_export_provenance import Ext4ExportError, MAX_IMAGE_BYTES, compare_ext4_image_to_snapshot
from rootfs_snapshot_audit import RootfsSnapshotError, scan_rootfs_snapshot

P1_FILENAME = "p1-rootfs.img"
CHUNK = 65536
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class P1ExportGateError(ValueError):
    """Stable refusal code with no installation/boot implications."""


def _load_backup_verifier():
    path = ROOT / "tools" / "verify-backup-aura-hd.py"
    spec = importlib.util.spec_from_file_location("pmkb_backup_verifier_l08k", path)
    if spec is None or spec.loader is None:
        raise P1ExportGateError("backup_verifier_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fingerprint(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns)


def _read_regular_image(path):
    """Read a bounded host regular file, never raw /dev or a symlink."""
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise P1ExportGateError("p1_image_unavailable") from exc
    if not stat.S_ISREG(before.st_mode) or not 2048 <= before.st_size <= MAX_IMAGE_BYTES:
        raise P1ExportGateError("invalid_p1_regular_image")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise P1ExportGateError("p1_open_refused") from exc
    try:
        if _fingerprint(os.fstat(fd)) != _fingerprint(before):
            raise P1ExportGateError("p1_image_changed")
        parts, total = [], 0
        while True:
            part = os.read(fd, CHUNK)
            if not part:
                break
            total += len(part)
            if total > MAX_IMAGE_BYTES:
                raise P1ExportGateError("p1_image_size_limit")
            parts.append(part)
        if total != before.st_size or _fingerprint(os.fstat(fd)) != _fingerprint(before):
            raise P1ExportGateError("p1_image_changed")
    except OSError as exc:
        raise P1ExportGateError("p1_read_failed") from exc
    finally:
        os.close(fd)
    try:
        if _fingerprint(os.lstat(path)) != _fingerprint(before):
            raise P1ExportGateError("p1_image_changed")
    except OSError as exc:
        raise P1ExportGateError("p1_image_changed") from exc
    return b"".join(parts)


def _verified_p1(verification):
    if (type(verification) is not dict or
            verification.get("status") != "valid" or
            verification.get("ok") is not True):
        raise P1ExportGateError("backup_not_valid")
    components = verification.get("components")
    if type(components) is not list:
        raise P1ExportGateError("invalid_backup_verification")
    selected = [x for x in components if type(x) is dict and x.get("name") == "p1_rootfs"]
    if len(selected) != 1:
        raise P1ExportGateError("invalid_backup_verification")
    p1 = selected[0]
    sha = p1.get("sha256_recomputed")
    if (p1.get("result") != "valid" or p1.get("file") != P1_FILENAME or
            type(sha) is not str or _SHA.fullmatch(sha) is None):
        raise P1ExportGateError("p1_not_verified")
    return sha


def qualify_p1_export(backup_dir, export_dir, *, source_id="backup-p1-local"):
    """Check backup consistency, P1 bytes, then the shallow export inventory."""
    if type(source_id) is not str:
        raise P1ExportGateError("invalid_source_id")
    backup = Path(backup_dir)
    if backup.is_symlink() or not backup.is_dir():
        raise P1ExportGateError("invalid_backup_directory")
    try:
        verified = _load_backup_verifier().verify_backup(backup)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise P1ExportGateError("backup_verification_failed") from exc
    expected_sha = _verified_p1(verified)
    image = _read_regular_image(backup / P1_FILENAME)
    if hashlib.sha256(image).hexdigest() != expected_sha:
        raise P1ExportGateError("verified_backup_p1_hash_mismatch")
    snapshot = scan_rootfs_snapshot(
        export_dir, source_id=source_id, declared_source_sha256=expected_sha)
    match = compare_ext4_image_to_snapshot(
        image, snapshot, expected_image_sha256=expected_sha,
        expected_audit_sha256=snapshot["audit_sha256"],
        expected_source_id=source_id)
    return {
        "schema": "pmkb-p1-export-readonly-gate-v1",
        "scope": "verified_backup_files_to_shallow_export_only",
        "verdict": match["verdict"],
        "backup_files_consistent_with_manifest": True,
        "backup_manifest_authenticated": False,
        "p1_sha256_measured": match["image_sha256_measured"],
        "export_audit_sha256_measured": match["snapshot_observation_sha256"],
        "image_to_export_link_verified_for_scanned_scope":
            match["image_to_export_link_verified_for_scanned_scope"],
        "matched": match["matched"],
        "content_mismatch": match["content_mismatch"],
        "missing_from_image": match["missing_from_image"],
        "missing_from_export": match["missing_from_export"],
        "image_libraries_inspected": match["image_libraries_inspected"],
        "image_library_bytes_inspected": match["image_library_bytes_inspected"],
        "image_authenticated_as_kobo_p1": False,
        "whole_rootfs_verified": False,
        "filesystem_metadata_integrity_verified": False,
        "hardware_verified": False,
        "runtime_compatible": False,
        "launchable": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="PMKB read-only offline P1/export check")
    parser.add_argument("backup_dir", help="verified backup directory, never a device")
    parser.add_argument("export_dir", help="pre-existing extracted rootfs directory")
    parser.add_argument("--source-id", default="backup-p1-local")
    args = parser.parse_args(argv)
    try:
        report = qualify_p1_export(args.backup_dir, args.export_dir, source_id=args.source_id)
    except (P1ExportGateError, RootfsSnapshotError, Ext4ExportError,
            OSError, TypeError, ValueError) as exc:
        print(json.dumps({
            "schema": "pmkb-p1-export-readonly-gate-v1",
            "verdict": "refused", "reason": str(exc),
            "hardware_verified": False, "launchable": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["verdict"] == "scoped_image_export_match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
