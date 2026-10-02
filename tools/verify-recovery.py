#!/usr/bin/env python3
"""
verify-recovery.py - read-only verifier for a Kobo Aura HD recoveryfs tree.

The source directory is NEVER opened for writing. The tool checks the recovery
manifest, fully reads the factory tar+gzip archives and validates the expected
Aura HD E606C0-specific boot artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
from typing import Any, BinaryIO

CHUNK = 4 * 1024 * 1024
MD5_RE = re.compile(r"^([0-9a-fA-F]{32})\s+([ *])(.+)$")

FR = {
    "title": "PimpMyKobo-AuraHD — vérification recoveryfs en lecture seule",
    "readonly": "AUCUNE ÉCRITURE : le recovery est uniquement lu.",
    "root": "Recovery",
    "missing_root": "Le chemin fourni n'est pas un répertoire.",
    "manifest": "Manifeste fs.md5sum",
    "manifest_ok": "fichiers conformes",
    "archives": "Archives usine tar+gzip",
    "artifacts": "Fichiers E606C0",
    "hashes": "SHA-256",
    "ok": "OK",
    "missing": "ABSENT",
    "bad": "ERREUR",
    "summary_ok": "RECOVERY COHÉRENT POUR LES CONTRÔLES EFFECTUÉS",
    "summary_bad": "RECOVERY INCOMPLET OU INCOHÉRENT",
    "root_hint": "Certains fichiers sont illisibles. Relancez éventuellement avec les droits root/administrateur.",
}

EN = {
    "title": "PimpMyKobo-AuraHD — read-only recoveryfs verification",
    "readonly": "NO WRITES: the recovery tree is only read.",
    "root": "Recovery",
    "missing_root": "The supplied path is not a directory.",
    "manifest": "fs.md5sum manifest",
    "manifest_ok": "matching files",
    "archives": "Factory tar+gzip archives",
    "artifacts": "E606C0 files",
    "hashes": "SHA-256",
    "ok": "OK",
    "missing": "MISSING",
    "bad": "ERROR",
    "summary_ok": "RECOVERY IS CONSISTENT FOR THE CHECKS PERFORMED",
    "summary_bad": "RECOVERY IS INCOMPLETE OR INCONSISTENT",
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


def validate_tar_gzip(path: Path) -> dict[str, Any]:
    """Fully stream a .tgz without extracting anything to disk."""
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "ok": False,
        "members": 0,
        "regular_files": 0,
        "payload_bytes": 0,
    }
    if not result["exists"]:
        result["error"] = "missing"
        return result

    try:
        result["compressed_bytes"] = path.stat().st_size
        with tarfile.open(path, mode="r|gz") as archive:
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
        result["ok"] = True
    except (OSError, EOFError, tarfile.TarError) as exc:
        result["error"] = str(exc)
    return result


def parse_manifest(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
    except OSError as exc:
        return entries, [str(exc)]

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line
        if not line.strip():
            continue
        # GNU md5sum prefixes escaped filenames with a backslash.
        if line.startswith("\\"):
            line = line[1:]
        match = MD5_RE.match(line)
        if not match:
            errors.append(f"line {lineno}: unsupported manifest entry")
            continue
        expected = match.group(1).lower()
        relative = match.group(3)
        relative = relative.replace("\\n", "\n").replace("\\\\", "\\")
        if relative.startswith("./"):
            relative = relative[2:]
        entries.append((expected, relative))
    return entries, errors


def safe_member(root: Path, relative: str) -> Path | None:
    """Reject absolute paths, traversal and symlinks escaping the recovery tree."""
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


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest = root / "fs.md5sum"
    result: dict[str, Any] = {
        "path": str(manifest),
        "exists": manifest.is_file(),
        "ok": False,
        "checked": 0,
        "matched": 0,
        "missing": [],
        "mismatched": [],
        "unreadable": [],
        "invalid_entries": [],
    }
    if not manifest.is_file():
        result["error"] = "missing"
        return result

    entries, parse_errors = parse_manifest(manifest)
    result["invalid_entries"].extend(parse_errors)

    for expected, relative in entries:
        path = safe_member(root, relative)
        if path is None:
            result["invalid_entries"].append(f"unsafe path: {relative}")
            continue
        result["checked"] += 1
        if not path.is_file():
            result["missing"].append(relative)
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
        result["missing"]
        or result["mismatched"]
        or result["unreadable"]
        or result["invalid_entries"]
    )
    return result


def find_artifacts(root: Path) -> dict[str, Any]:
    ntx = root / "upgrade" / "ntx508"
    expected = {
        "uboot": "u-boot_mddr_512-E606C0-K4X2G323PC.bin",
        "kernel": "uImage-E606C0",
    }
    result: dict[str, Any] = {"directory": str(ntx), "exists": ntx.is_dir(), "files": {}}
    for key, name in expected.items():
        path = ntx / name
        item: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if path.is_file():
            try:
                item["size"] = path.stat().st_size
            except OSError as exc:
                item["error"] = str(exc)
        result["files"][key] = item

    if ntx.is_dir():
        try:
            result["other_candidates"] = sorted(
                p.name
                for p in ntx.iterdir()
                if p.is_file() and (p.name.startswith("u-boot") or p.name.startswith("uImage"))
            )
        except OSError as exc:
            result["inventory_error"] = str(exc)
    else:
        result["other_candidates"] = []

    result["ok"] = result["exists"] and all(
        item.get("exists") and not item.get("error") for item in result["files"].values()
    ) and not result.get("inventory_error")
    return result


def hash_selected(paths: list[Path]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path in paths:
        item: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if path.is_file():
            try:
                item["size"] = path.stat().st_size
                item["sha256"] = digest_file(path, "sha256")
            except OSError as exc:
                item["error"] = str(exc)
        output.append(item)
    return output


def inspect_recovery(root: Path, verify_md5: bool, include_hashes: bool) -> dict[str, Any]:
    root = root.resolve(strict=False)
    result: dict[str, Any] = {
        "root": str(root),
        "is_directory": root.is_dir(),
        "read_only_tool": True,
    }
    if not root.is_dir():
        result["ok"] = False
        result["error"] = "not_a_directory"
        return result

    archives = [root / "upgrade" / "fs.tgz", root / "upgrade" / "db.tgz"]
    result["archives"] = [validate_tar_gzip(path) for path in archives]
    result["artifacts"] = find_artifacts(root)
    result["manifest"] = verify_manifest(root) if verify_md5 else {"skipped": True, "ok": True}

    hashes_ok = True
    if include_hashes:
        artifact_paths = [
            root / "upgrade" / "ntx508" / "u-boot_mddr_512-E606C0-K4X2G323PC.bin",
            root / "upgrade" / "ntx508" / "uImage-E606C0",
        ]
        result["sha256"] = hash_selected(archives + artifact_paths)
        hashes_ok = all(item.get("sha256") and not item.get("error") for item in result["sha256"])

    result["ok"] = (
        all(item.get("ok") for item in result["archives"])
        and result["artifacts"].get("ok", False)
        and result["manifest"].get("ok", False)
        and hashes_ok
    )
    return result


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
        print("  SKIPPED")
    elif manifest.get("ok"):
        print(
            f"  {lang['ok']}: {manifest.get('matched', 0)}/{manifest.get('checked', 0)} {lang['manifest_ok']}"
        )
    else:
        print(
            f"  {lang['bad']}: matched={manifest.get('matched', 0)} checked={manifest.get('checked', 0)} "
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
                f"{human_size(item.get('payload_bytes'))} file payload"
            )
        else:
            state = lang["missing"] if item.get("error") == "missing" else lang["bad"]
            print(f"  {name}: {state} {item.get('error', '')}")

    print(f"{lang['artifacts']}:")
    for key, item in result["artifacts"]["files"].items():
        name = Path(item["path"]).name
        if item.get("exists") and not item.get("error"):
            print(f"  {key}: {lang['ok']} — {name} ({item.get('size', '?')} bytes)")
        else:
            print(f"  {key}: {lang['missing']} — {name}")

    if show_hashes and result.get("sha256"):
        print(f"{lang['hashes']}:")
        for item in result["sha256"]:
            if item.get("sha256"):
                print(f"  {item['sha256']}  {item['path']}")
            else:
                print(f"  {lang['bad']}  {item['path']}  {item.get('error', '')}")

    print()
    print(lang["summary_ok"] if result.get("ok") else lang["summary_bad"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only verifier for a mounted or extracted Kobo Aura HD recoveryfs tree."
    )
    parser.add_argument("recovery", help="Path to the root of mounted/extracted recoveryfs")
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--hash-files",
        action="store_true",
        help="Also compute SHA-256 for fs.tgz, db.tgz, E606C0 U-Boot and kernel.",
    )
    parser.add_argument(
        "--skip-md5",
        action="store_true",
        help="Skip verification of recoveryfs/fs.md5sum.",
    )
    args = parser.parse_args()

    result = inspect_recovery(Path(args.recovery), not args.skip_md5, args.hash_files)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result, FR if args.lang == "fr" else EN, args.hash_files)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
