#!/usr/bin/env python3
"""Read-only verifier for a Kobo Aura HD recoveryfs tree."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import stat
import tarfile
import zlib
from pathlib import Path
from typing import Any, BinaryIO

CHUNK = 4 * 1024 * 1024
TAR_END_SIZE = 1024
MD5_RE = re.compile(r"^([0-9a-fA-F]{32})\s+([ *])(.+)$")
UBOOT_MAGIC = 0x27051956
JSON_SCHEMA_VERSION = 1

FR = {
    "title": "PimpMyKobo-AuraHD — vérification recoveryfs en lecture seule",
    "readonly": "AUCUNE ÉCRITURE : le recovery est uniquement lu.",
    "root": "Recovery",
    "missing_root": "Le chemin fourni n'est pas un répertoire lisible.",
    "manifest": "Manifeste fs.md5sum",
    "manifest_ok": "fichiers conformes",
    "archives": "Archives usine tar+gzip",
    "artifacts": "Fichiers E606C0",
    "hashes": "SHA-256",
    "ok": "OK", "missing": "ABSENT", "bad": "ERREUR", "partial": "PARTIEL",
    "summary_ok": "RECOVERY COHÉRENT POUR LES CONTRÔLES EFFECTUÉS",
    "summary_bad": "RECOVERY INCOHÉRENT — AU MOINS UNE ANOMALIE A ÉTÉ DÉTECTÉE",
    "summary_partial": "RECOVERY PARTIELLEMENT VÉRIFIÉ — NE PAS LE CONSIDÉRER VALIDÉ",
    "summary_incomplete": "VÉRIFICATION INCOMPLÈTE",
    "incomplete": "INCOMPLET",
    "unreadable_one": "1 fichier n'a pas pu être lu avec les droits actuels.",
    "unreadable_many": "{count} fichiers n'ont pas pu être lus avec les droits actuels.",
    "no_corruption": "Aucune corruption n'a été détectée parmi les fichiers vérifiés.",
    "rerun_hint": "Relancez avec les droits nécessaires pour obtenir un verdict complet.",
    "skipped_md5": "fs.md5sum n'a pas été vérifié (--skip-md5).",
    "also_incomplete": "La vérification est en outre incomplète :",
    "root_hint": "Certains fichiers sont illisibles. Relancez éventuellement avec les droits root/administrateur.",
}

EN = {
    "title": "PimpMyKobo-AuraHD — read-only recoveryfs verification",
    "readonly": "NO WRITES: the recovery tree is only read.",
    "root": "Recovery",
    "missing_root": "The supplied path is not a readable directory.",
    "manifest": "fs.md5sum manifest",
    "manifest_ok": "matching files",
    "archives": "Factory tar+gzip archives",
    "artifacts": "E606C0 files",
    "hashes": "SHA-256",
    "ok": "OK", "missing": "MISSING", "bad": "ERROR", "partial": "PARTIAL",
    "summary_ok": "RECOVERY IS CONSISTENT FOR THE CHECKS PERFORMED",
    "summary_bad": "RECOVERY IS INCONSISTENT — AT LEAST ONE ANOMALY WAS DETECTED",
    "summary_partial": "RECOVERY WAS ONLY PARTIALLY VERIFIED — DO NOT TREAT IT AS VALIDATED",
    "summary_incomplete": "VERIFICATION INCOMPLETE",
    "incomplete": "INCOMPLETE",
    "unreadable_one": "1 file could not be read with the current privileges.",
    "unreadable_many": "{count} files could not be read with the current privileges.",
    "no_corruption": "No corruption was detected among the files that were verified.",
    "rerun_hint": "Re-run with the required privileges to obtain a complete verdict.",
    "skipped_md5": "fs.md5sum was not verified (--skip-md5).",
    "also_incomplete": "Verification is also incomplete:",
    "root_hint": "Some files are unreadable. Re-run with root/administrator rights if appropriate.",
}


def digest_stream(handle: BinaryIO, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    while True:
        chunk = handle.read(CHUNK)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def digest_file(path: Path, algorithm: str) -> str:
    with path.open("rb") as handle:
        return digest_stream(handle, algorithm)


def safe_member(root: Path, relative: str) -> Path | None:
    rel = Path(relative)
    if rel.is_absolute():
        return None
    root_resolved = root.resolve(strict=False)
    candidate = (root / rel).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def stat_regular_file(path: Path) -> tuple[bool, int | None, str | None]:
    try:
        st = path.stat()
    except FileNotFoundError:
        return False, None, "missing"
    except PermissionError as exc:
        return False, None, f"permission denied: {exc}"
    except OSError as exc:
        return False, None, str(exc)
    if not stat.S_ISREG(st.st_mode):
        return False, None, "not a regular file"
    return True, st.st_size, None


def _is_permission_error(error: str | None) -> bool:
    return bool(error) and str(error).startswith("permission denied")


def safe_critical_path(root: Path, relative: str) -> tuple[Path | None, str | None]:
    path = safe_member(root, relative)
    if path is None:
        return None, f"unsafe path: {relative}"
    return path, None


def _gzip_tail_and_size(path: Path) -> tuple[int, bytes]:
    """Read the complete gzip stream, forcing CRC32/ISIZE validation."""
    total = 0
    tail = b""
    with gzip.open(path, "rb") as gz:
        while True:
            chunk = gz.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            tail = (tail + chunk)[-TAR_END_SIZE:]
    return total, tail


def validate_tar_gzip(path: Path) -> dict[str, Any]:
    """Validate gzip CRC/size, tar EOF markers, members and regular-file payloads."""
    result: dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "ok": False,
        "members": 0,
        "regular_files": 0,
        "payload_bytes": 0,
    }
    exists, size, stat_error = stat_regular_file(path)
    result["exists"] = exists
    if not exists:
        result["error"] = stat_error or "missing"
        result["unreadable"] = _is_permission_error(stat_error)
        return result
    result["compressed_bytes"] = size

    try:
        uncompressed_bytes, tail = _gzip_tail_and_size(path)
        result["uncompressed_bytes"] = uncompressed_bytes
        if uncompressed_bytes < TAR_END_SIZE or tail != b"\x00" * TAR_END_SIZE:
            raise tarfile.ReadError("tar end marker missing or truncated")

        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive:
                result["members"] += 1
                if not member.isfile():
                    continue
                result["regular_files"] += 1
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise tarfile.ReadError(f"cannot read member: {member.name}")
                while True:
                    chunk = extracted.read(CHUNK)
                    if not chunk:
                        break
                    result["payload_bytes"] += len(chunk)

        if result["members"] == 0:
            raise tarfile.ReadError("archive contains no members")
        if result["regular_files"] == 0:
            raise tarfile.ReadError("archive contains no regular files")
        result["ok"] = True
    except (OSError, EOFError, gzip.BadGzipFile, tarfile.TarError, zlib.error) as exc:
        result["error"] = str(exc)
        result["unreadable"] = isinstance(exc, PermissionError)
    return result


def _decode_gnu_escaped_name(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "r":
                out.append("\r")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_manifest(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
    except PermissionError:
        raise
    except OSError as exc:
        return entries, [str(exc)]

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        if not raw_line.strip():
            continue
        escaped = raw_line.startswith("\\")
        line = raw_line[1:] if escaped else raw_line
        match = MD5_RE.match(line)
        if not match:
            errors.append(f"line {lineno}: unsupported manifest entry")
            continue
        expected = match.group(1).lower()
        relative = match.group(3)
        if escaped:
            relative = _decode_gnu_escaped_name(relative)
        if relative.startswith("./"):
            relative = relative[2:]
        entries.append((expected, relative))
    return entries, errors


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest, unsafe = safe_critical_path(root, "fs.md5sum")
    result: dict[str, Any] = {
        "path": str(manifest or (root / "fs.md5sum")),
        "exists": False,
        "ok": False,
        "checked": 0,
        "matched": 0,
        "missing": [],
        "mismatched": [],
        "unreadable": [],
        "invalid_entries": [],
    }
    if unsafe:
        result["invalid_entries"].append(unsafe)
        result["error"] = unsafe
        return result
    assert manifest is not None
    exists, _, stat_error = stat_regular_file(manifest)
    result["exists"] = exists
    if not exists:
        if stat_error and stat_error not in ("missing", "not a regular file"):
            result["unreadable"].append({"path": "fs.md5sum", "error": stat_error})
        result["error"] = stat_error or "missing"
        return result

    try:
        entries, parse_errors = parse_manifest(manifest)
    except PermissionError as exc:
        result["unreadable"].append({"path": "fs.md5sum", "error": str(exc)})
        result["error"] = f"permission denied: {exc}"
        return result
    result["invalid_entries"].extend(parse_errors)
    for expected, relative in entries:
        path = safe_member(root, relative)
        if path is None:
            result["invalid_entries"].append(f"unsafe path: {relative}")
            continue
        result["checked"] += 1
        exists, _, stat_error = stat_regular_file(path)
        if not exists:
            if stat_error in ("missing", "not a regular file"):
                result["missing"].append(relative)
            else:
                result["unreadable"].append({"path": relative, "error": stat_error})
            continue
        try:
            actual = digest_file(path, "md5")
        except OSError as exc:
            result["unreadable"].append({"path": relative, "error": str(exc)})
            continue
        if actual == expected:
            result["matched"] += 1
        else:
            result["mismatched"].append(
                {"path": relative, "expected": expected, "actual": actual}
            )

    result["ok"] = bool(entries) and not (
        result["missing"] or result["mismatched"] or result["unreadable"] or result["invalid_entries"]
    )
    return result


def validate_legacy_uimage(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "ok": False}
    exists, size, error = stat_regular_file(path)
    result["exists"] = exists
    result["size"] = size
    if not exists:
        result["error"] = error or "missing"
        result["unreadable"] = _is_permission_error(error)
        return result
    if not size:
        result["error"] = "empty file"
        return result

    try:
        with path.open("rb") as handle:
            header = handle.read(64)
            if len(header) != 64:
                raise ValueError("uImage header is shorter than 64 bytes")
            magic = int.from_bytes(header[0:4], "big")
            if magic != UBOOT_MAGIC:
                raise ValueError(f"invalid uImage magic 0x{magic:08X}")
            header_crc = int.from_bytes(header[4:8], "big")
            data_size = int.from_bytes(header[12:16], "big")
            data_crc = int.from_bytes(header[24:28], "big")

            crc_header = bytearray(header)
            crc_header[4:8] = b"\x00\x00\x00\x00"
            actual_header_crc = zlib.crc32(crc_header) & 0xFFFFFFFF
            if actual_header_crc != header_crc:
                raise ValueError(
                    f"uImage header CRC mismatch: expected 0x{header_crc:08X}, got 0x{actual_header_crc:08X}"
                )
            minimum_size = 64 + data_size
            if size < minimum_size:
                raise ValueError(
                    f"uImage size mismatch: header declares {data_size} data bytes, file is only {size} bytes"
                )

            crc = 0
            remaining = data_size
            while remaining:
                chunk = handle.read(min(CHUNK, remaining))
                if not chunk:
                    raise ValueError("truncated uImage data")
                crc = zlib.crc32(chunk, crc)
                remaining -= len(chunk)
            crc &= 0xFFFFFFFF
            if crc != data_crc:
                raise ValueError(
                    f"uImage data CRC mismatch: expected 0x{data_crc:08X}, got 0x{crc:08X}"
                )

            padding = handle.read()
            if any(padding):
                raise ValueError("non-zero bytes found after declared uImage payload")

        result.update({
            "ok": True,
            "magic": f"0x{magic:08X}",
            "data_size": data_size,
            "padding_bytes": len(padding),
            "header_crc": f"0x{header_crc:08X}",
            "data_crc": f"0x{data_crc:08X}",
        })
    except (OSError, ValueError) as exc:
        result["error"] = str(exc)
        result["unreadable"] = isinstance(exc, PermissionError)
    return result


def find_artifacts(root: Path) -> dict[str, Any]:
    ntx_path, unsafe = safe_critical_path(root, "upgrade/ntx508")
    result: dict[str, Any] = {
        "directory": str(ntx_path or (root / "upgrade/ntx508")),
        "exists": False,
        "files": {},
        "other_candidates": [],
        "warnings": [],
        "ok": False,
    }
    if unsafe:
        result["error"] = unsafe
        return result
    assert ntx_path is not None
    try:
        result["exists"] = ntx_path.is_dir()
    except OSError as exc:
        result["error"] = str(exc)
        return result
    if not result["exists"]:
        result["error"] = "missing directory"
        return result

    try:
        uboot_candidates = sorted(
            path for path in ntx_path.glob("u-boot_mddr_512-E606C0-*.bin")
            if safe_member(root, str(path.relative_to(root))) is not None
        )
    except (OSError, ValueError) as exc:
        result["error"] = str(exc)
        return result

    uboot_items: list[dict[str, Any]] = []
    for path in uboot_candidates:
        exists, size, error = stat_regular_file(path)
        item: dict[str, Any] = {
            "path": str(path),
            "exists": exists,
            "size": size,
            "ok": bool(exists and size and size > 0),
        }
        if error:
            item["error"] = error
            item["unreadable"] = _is_permission_error(error)
        if exists and size == 0:
            item["error"] = "empty file"
        uboot_items.append(item)
    result["files"]["uboot_candidates"] = uboot_items
    valid_uboot = [item for item in uboot_items if item.get("ok")]
    if len(valid_uboot) == 1:
        result["selected_uboot"] = valid_uboot[0]
    elif len(valid_uboot) > 1:
        result["selected_uboot"] = None
        result["warnings"].append(
            "multiple non-empty E606C0 U-Boot variants found; no RAM variant selected automatically"
        )
    else:
        result["selected_uboot"] = None

    kernel_path, kernel_unsafe = safe_critical_path(root, "upgrade/ntx508/uImage-E606C0")
    if kernel_unsafe or kernel_path is None:
        kernel = {
            "path": str(root / "upgrade/ntx508/uImage-E606C0"),
            "exists": False,
            "ok": False,
            "error": kernel_unsafe,
        }
    else:
        kernel = validate_legacy_uimage(kernel_path)
    result["files"]["kernel"] = kernel

    try:
        result["other_candidates"] = sorted(
            path.name for path in ntx_path.iterdir()
            if path.is_file() and (path.name.startswith("u-boot") or path.name.startswith("uImage"))
        )
    except OSError as exc:
        result["inventory_error"] = str(exc)

    result["ok"] = bool(valid_uboot) and kernel.get("ok", False) and not result.get("inventory_error")
    return result


def hash_selected(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path in paths:
        try:
            relative = str(path.relative_to(root))
        except ValueError:
            relative = str(path)
        safe = safe_member(root, relative)
        item: dict[str, Any] = {"path": str(path), "exists": False}
        if safe is None:
            item["error"] = "unsafe path"
            output.append(item)
            continue
        exists, size, error = stat_regular_file(safe)
        item["exists"] = exists
        item["size"] = size
        if not exists:
            item["error"] = error or "missing"
            item["unreadable"] = _is_permission_error(error)
            output.append(item)
            continue
        try:
            item["sha256"] = digest_file(safe, "sha256")
        except OSError as exc:
            item["error"] = str(exc)
            item["unreadable"] = isinstance(exc, PermissionError)
        output.append(item)
    return output


def inspect_recovery(root: Path, verify_md5: bool, include_hashes: bool) -> dict[str, Any]:
    root = root.resolve(strict=False)
    result: dict[str, Any] = {
        "schema_version": JSON_SCHEMA_VERSION,
        "root": str(root),
        "is_directory": False,
        "read_only_tool": True,
        "partial": not verify_md5,
        "errors": [],
        "warnings": [],
    }
    try:
        result["is_directory"] = root.is_dir()
    except OSError as exc:
        result["errors"].append(str(exc))
    if not result["is_directory"]:
        result["ok"] = False
        result["status"] = "error"
        result["error"] = "not_a_directory"
        return result

    archives: list[Path] = []
    archive_results: list[dict[str, Any]] = []
    for rel in ("upgrade/fs.tgz", "upgrade/db.tgz"):
        path, unsafe = safe_critical_path(root, rel)
        if unsafe or path is None:
            archive_results.append({
                "path": str(root / rel), "exists": False, "ok": False, "error": unsafe
            })
            continue
        archives.append(path)
        archive_results.append(validate_tar_gzip(path))
    result["archives"] = archive_results
    result["artifacts"] = find_artifacts(root)
    result["warnings"].extend(result["artifacts"].get("warnings", []))
    result["manifest"] = verify_manifest(root) if verify_md5 else {
        "skipped": True, "ok": False, "partial": True
    }

    hashes_ok = True
    if include_hashes:
        hash_paths = list(archives)
        for item in result["artifacts"].get("files", {}).get("uboot_candidates", []):
            if item.get("ok") and item.get("path"):
                hash_paths.append(Path(item["path"]))
        kernel = result["artifacts"].get("files", {}).get("kernel", {})
        if kernel.get("path"):
            hash_paths.append(Path(kernel["path"]))
        result["sha256"] = hash_selected(hash_paths, root)
        hashes_ok = all(item.get("sha256") and not item.get("error") for item in result["sha256"])

    checks_ok = (
        len(result["archives"]) == 2
        and all(item.get("ok") for item in result["archives"])
        and result["artifacts"].get("ok", False)
        and (result["manifest"].get("ok", False) if verify_md5 else True)
        and hashes_ok
    )
    result["checks_ok"] = checks_ok
    if not verify_md5:
        result["warnings"].append("fs.md5sum verification was skipped; result is partial")
    classify_recovery(result, verify_md5)
    return result


def classify_recovery(result: dict[str, Any], verify_md5: bool) -> None:
    """Split failures into positive inconsistencies and checks that could not run.

    status "ok": every mandatory check passed.
    status "incomplete": nothing inconsistent was found, but at least one mandatory
    check could not be performed (unreadable file, --skip-md5). Never OK.
    status "inconsistent": at least one check positively failed. It always wins
    over "incomplete", so missing rights or --skip-md5 cannot mask a corruption.
    """
    inconsistencies: list[str] = []
    incomplete: list[str] = []
    unreadable: set[str] = set()

    def unreadable_item(path: str, reason: str) -> None:
        unreadable.add(path)
        incomplete.append(f"{path}: {reason}")

    for item in result["archives"]:
        if item.get("ok"):
            continue
        if item.get("unreadable"):
            unreadable_item(item["path"], item.get("error") or "unreadable")
        else:
            inconsistencies.append(f"{item['path']}: {item.get('error') or 'invalid archive'}")

    artifacts = result["artifacts"]
    if not artifacts.get("ok"):
        files = artifacts.get("files", {})
        directory_error = artifacts.get("error")
        if directory_error:
            if directory_error == "missing directory" or directory_error.startswith("unsafe path"):
                inconsistencies.append(f"{artifacts['directory']}: {directory_error}")
            else:
                incomplete.append(f"{artifacts['directory']}: {directory_error}")
        if artifacts.get("inventory_error"):
            incomplete.append(f"{artifacts['directory']}: {artifacts['inventory_error']}")
        if not directory_error:
            uboots = files.get("uboot_candidates", [])
            if not any(item.get("ok") for item in uboots):
                unreadable_uboots = [item for item in uboots if item.get("unreadable")]
                if unreadable_uboots:
                    for item in unreadable_uboots:
                        unreadable_item(item["path"], item.get("error") or "unreadable")
                else:
                    inconsistencies.append("no valid u-boot_mddr_512-E606C0-*.bin found")
            kernel = files.get("kernel", {})
            if kernel and not kernel.get("ok"):
                if kernel.get("unreadable"):
                    unreadable_item(kernel["path"], kernel.get("error") or "unreadable")
                else:
                    inconsistencies.append(f"{kernel['path']}: {kernel.get('error') or 'invalid uImage'}")

    manifest = result["manifest"]
    if not verify_md5:
        incomplete.append("fs.md5sum verification skipped (--skip-md5)")
    elif not manifest.get("ok"):
        for relative in manifest.get("missing", []):
            inconsistencies.append(f"fs.md5sum: missing {relative}")
        for item in manifest.get("mismatched", []):
            inconsistencies.append(f"fs.md5sum: MD5 mismatch {item['path']}")
        for entry in manifest.get("invalid_entries", []):
            inconsistencies.append(f"fs.md5sum: {entry}")
        for item in manifest.get("unreadable", []):
            unreadable_item(item["path"], item.get("error") or "unreadable")
        if not manifest.get("exists") and not manifest.get("unreadable") and not manifest.get("invalid_entries"):
            inconsistencies.append(f"fs.md5sum: {manifest.get('error') or 'missing'}")
        elif (
            manifest.get("exists")
            and manifest.get("checked", 0) == 0
            and not manifest.get("invalid_entries")
            and not manifest.get("unreadable")
        ):
            inconsistencies.append("fs.md5sum: manifest contains no entries")

    for item in result.get("sha256", []):
        if item.get("sha256") and not item.get("error"):
            continue
        if item.get("unreadable"):
            unreadable_item(item["path"], item.get("error") or "unreadable")
        else:
            inconsistencies.append(f"sha256 {item['path']}: {item.get('error') or 'not computed'}")

    if not result.get("checks_ok") and not inconsistencies and not incomplete:
        # Conservative fallback: an unclassified failure is never reported as OK.
        inconsistencies.append("unclassified check failure")

    if inconsistencies:
        status = "inconsistent"
    elif incomplete:
        status = "incomplete"
    else:
        status = "ok"

    result["status"] = status
    result["ok"] = status == "ok"
    result["partial"] = bool(incomplete)
    result["inconsistencies"] = inconsistencies
    result["incomplete_checks"] = incomplete
    result["unreadable_count"] = len(unreadable)


def human_size(value: int | None) -> str:
    if value is None:
        return "?"
    units = ["B", "KiB", "MiB", "GiB"]
    n = float(value)
    for unit in units:
        if n < 1024 or unit == units[-1]:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return str(value)


def print_human(result: dict[str, Any], lang: dict[str, str], show_hashes: bool) -> None:
    print(lang["title"])
    print(lang["readonly"])
    print(f"{lang['root']}: {result['root']}")
    print()

    if not result.get("is_directory"):
        print(f"{lang['bad']}: {lang['missing_root']}")
        return

    manifest = result["manifest"]
    print(f"{lang['manifest']}:")
    if manifest.get("skipped"):
        print(f"  {lang['partial']}: SKIPPED")
    elif manifest.get("ok"):
        print(f"  {lang['ok']}: {manifest.get('matched', 0)}/{manifest.get('checked', 0)} {lang['manifest_ok']}")
    else:
        only_unreadable = manifest.get("unreadable") and not (
            manifest.get("missing") or manifest.get("mismatched") or manifest.get("invalid_entries")
        )
        label = lang["incomplete"] if only_unreadable else lang["bad"]
        print(
            f"  {label}: matched={manifest.get('matched', 0)} checked={manifest.get('checked', 0)} "
            f"missing={len(manifest.get('missing', []))} mismatched={len(manifest.get('mismatched', []))} "
            f"unreadable={len(manifest.get('unreadable', []))} invalid={len(manifest.get('invalid_entries', []))}"
        )
        if manifest.get("unreadable"):
            print(f"  {lang['root_hint']}")

    print(f"{lang['archives']}:")
    for item in result["archives"]:
        name = Path(item["path"]).name
        if item.get("ok"):
            print(
                f"  {name}: {lang['ok']} — {item.get('members', 0)} entries, "
                f"{human_size(item.get('compressed_bytes'))} compressed, "
                f"{human_size(item.get('uncompressed_bytes'))} uncompressed, "
                f"{human_size(item.get('payload_bytes'))} regular-file payload"
            )
        else:
            state = lang["missing"] if item.get("error") == "missing" else lang["bad"]
            print(f"  {name}: {state} {item.get('error', '')}")

    print(f"{lang['artifacts']}:")
    uboot_items = result["artifacts"].get("files", {}).get("uboot_candidates", [])
    for item in uboot_items:
        name = Path(item["path"]).name
        state = lang["ok"] if item.get("ok") else lang["bad"]
        print(f"  uboot: {state} — {name} ({item.get('size', '?')} bytes)")
    if not uboot_items:
        print(f"  uboot: {lang['missing']}")
    kernel = result["artifacts"].get("files", {}).get("kernel", {})
    if kernel:
        name = Path(kernel["path"]).name
        state = lang["ok"] if kernel.get("ok") else lang["bad"]
        suffix = f" — {kernel.get('error')}" if kernel.get("error") else ""
        padding = f", padding={kernel.get('padding_bytes')}" if kernel.get("ok") else ""
        print(f"  kernel: {state} — {name} ({kernel.get('size', '?')} bytes{padding}){suffix}")

    if show_hashes and result.get("sha256"):
        print(f"{lang['hashes']}:")
        for item in result["sha256"]:
            if item.get("sha256"):
                print(f"  {item['sha256']}  {item['path']}")
            else:
                print(f"  {lang['bad']}  {item['path']}  {item.get('error', '')}")

    for warning in result.get("warnings", []):
        print(f"{lang['partial']}: {warning}")

    print()
    status = result.get("status")
    unreadable_count = result.get("unreadable_count", 0)
    skipped = bool(result.get("manifest", {}).get("skipped"))
    if status == "ok":
        print(lang["summary_ok"])
    elif status == "incomplete":
        print(lang["summary_incomplete"])
        print()
        if unreadable_count:
            print(
                lang["unreadable_one"] if unreadable_count == 1
                else lang["unreadable_many"].format(count=unreadable_count)
            )
        if skipped:
            print(lang["skipped_md5"])
        print(lang["no_corruption"])
        print()
        if unreadable_count:
            print(lang["rerun_hint"])
        if skipped:
            print(lang["summary_partial"])
    else:
        print(lang["summary_bad"])
        for item in result.get("inconsistencies", []):
            print(f"  - {item}")
        if result.get("incomplete_checks"):
            print(lang["also_incomplete"])
            for item in result["incomplete_checks"]:
                print(f"  - {item}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only verifier for a mounted or extracted Kobo Aura HD recoveryfs tree."
    )
    parser.add_argument("recovery", help="Path to the root of mounted/extracted recoveryfs")
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--hash-files", action="store_true",
        help="Also compute SHA-256 for fs.tgz, db.tgz, all valid E606C0 U-Boot candidates and kernel.",
    )
    parser.add_argument(
        "--skip-md5", action="store_true",
        help="Skip fs.md5sum verification. The result will be marked partial and will not return OK.",
    )
    args = parser.parse_args()

    result = inspect_recovery(Path(args.recovery), not args.skip_md5, args.hash_files)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result, FR if args.lang == "fr" else EN, args.hash_files)

    if result.get("ok"):
        return 0
    if result.get("error") == "not_a_directory":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
