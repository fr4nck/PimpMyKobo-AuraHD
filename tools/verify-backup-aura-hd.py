#!/usr/bin/env python3
"""Offline, read-only verifier for a backup produced by backup-aura-hd.py.

No Kobo needs to be connected. Every file of the backup directory is opened
with mode "rb" only; nothing is created, renamed or modified.

A "valid" verdict proves that the files are consistent with their manifest.
It proves neither their authenticity nor that they can be restored on a
given card.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

TOOL_NAME = "verify-backup-aura-hd"
TOOL_VERSION = "0.1.0"
RESULT_SCHEMA_VERSION = 1
SUPPORTED_MANIFEST_SCHEMAS = (1,)
CHUNK = 4 * 1024 * 1024
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SUMS_LINE_RE = re.compile(r"^([0-9a-fA-F]{64}) ([ *])(.+)$")

EXIT_VALID = 0
EXIT_INCOMPLETE = 1
EXIT_INCONSISTENT = 2
EXIT_INVALID = 3

MANIFEST_STATUSES = ("in_progress", "complete", "failed", "interrupted")
COMPONENT_STATUSES = ("pending", "in_progress", "verified", "failed", "interrupted",
                      "not_started", "not_requested")
MANDATORY = ("pre_p1", "p1_rootfs", "p2_recoveryfs")
EXPECTED_LABELS = {"p1_rootfs": ("ext", "rootfs"), "p2_recoveryfs": ("ext", "recoveryfs")}

FR = {
    "title": "PimpMyKobo-AuraHD — vérification hors ligne d'une sauvegarde (lecture seule)",
    "dir": "Sauvegarde",
    "valid": "SAUVEGARDE VALIDE — FICHIERS COHÉRENTS AVEC LE MANIFESTE",
    "incomplete": "SAUVEGARDE INCOMPLÈTE, INTERROMPUE OU DÉCLARÉE ÉCHOUÉE — NE PAS L'UTILISER COMME RÉFÉRENCE",
    "inconsistent": "SAUVEGARDE INCOHÉRENTE OU CORROMPUE",
    "invalid": "MANIFESTE INVALIDE OU DOSSIER INUTILISABLE",
    "components": "Composants",
    "fingerprint": "Empreinte cible",
    "fp_ok": "recalculée depuis pre-p1.bin, concorde avec le manifeste",
    "fp_bad": "NE CONCORDE PAS avec le manifeste",
    "fp_na": "non vérifiable",
    "sums": "SHA256SUMS",
    "declared": "Valeurs seulement déclarées (non relues)",
    "limit": "Cette vérification prouve la cohérence des fichiers avec le manifeste ; "
             "elle ne prouve ni leur authenticité, ni leur aptitude à être restaurés sur une carte donnée.",
}
EN = {
    "title": "PimpMyKobo-AuraHD — offline backup verification (read-only)",
    "dir": "Backup",
    "valid": "BACKUP VALID — FILES CONSISTENT WITH THE MANIFEST",
    "incomplete": "BACKUP INCOMPLETE, INTERRUPTED OR RECORDED AS FAILED — DO NOT USE IT AS A REFERENCE",
    "inconsistent": "BACKUP INCONSISTENT OR CORRUPTED",
    "invalid": "INVALID MANIFEST OR UNUSABLE DIRECTORY",
    "components": "Components",
    "fingerprint": "Target fingerprint",
    "fp_ok": "recomputed from pre-p1.bin, matches the manifest",
    "fp_bad": "DOES NOT MATCH the manifest",
    "fp_na": "not verifiable",
    "sums": "SHA256SUMS",
    "declared": "Values only declared (not re-read)",
    "limit": "This check proves the files are consistent with the manifest; "
             "it proves neither their authenticity nor that they can be restored on a given card.",
}


def _load(filename: str, name: str) -> Any:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse the producer's constants and fingerprint algorithm, and the qualified parsers.
backup = _load("backup-aura-hd.py", "pmkb_backup_aura_hd")
inspector = backup.inspector


class InvalidManifest(Exception):
    pass


# ---------------------------------------------------------------------------
# Read-only file helpers (mode "rb" only)
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> tuple[str, int]:
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


def safe_file(root: Path, name: Any) -> tuple[Path | None, str | None]:
    """Resolve a manifest file name inside *root*, refusing anything that could escape it."""
    if not isinstance(name, str) or not name:
        return None, "file name missing or not a string"
    if name in (".", "..") or "/" in name or "\\" in name or ":" in name or not SAFE_NAME_RE.match(name):
        return None, f"unsafe file name {name!r} (path, traversal or unexpected characters)"
    candidate = root / name
    try:
        st = os.lstat(candidate)
    except FileNotFoundError:
        return candidate, None
    except OSError as exc:
        return None, f"{name}: {exc}"
    if stat.S_ISLNK(st.st_mode):
        return None, f"{name} is a symbolic link (refused)"
    try:
        candidate.resolve().relative_to(root)
    except (OSError, ValueError):
        return None, f"{name} resolves outside the backup directory"
    return candidate, None


def regular_file_size(path: Path) -> int | None:
    try:
        st = os.lstat(path)
    except OSError:
        return None
    return st.st_size if stat.S_ISREG(st.st_mode) else None


# ---------------------------------------------------------------------------
# Manifest structure
# ---------------------------------------------------------------------------

def load_manifest(root: Path) -> dict[str, Any]:
    path, problem = safe_file(root, backup.MANIFEST_NAME)
    if problem or path is None:
        raise InvalidManifest(problem or "unsafe manifest path")
    if regular_file_size(path) is None:
        raise InvalidManifest(f"{backup.MANIFEST_NAME} is missing or not a regular file")
    try:
        with open(path, "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidManifest(f"{backup.MANIFEST_NAME} is not readable JSON: {exc}")
    if not isinstance(data, dict):
        raise InvalidManifest("manifest top level is not a JSON object")
    version = data.get("schema_version")
    if type(version) is not int or version not in SUPPORTED_MANIFEST_SCHEMAS:
        raise InvalidManifest(
            f"unsupported manifest schema_version {version!r} (supported: {list(SUPPORTED_MANIFEST_SCHEMAS)})"
        )
    if data.get("tool") != backup.TOOL_NAME:
        raise InvalidManifest(f"manifest was not produced by {backup.TOOL_NAME} (tool={data.get('tool')!r})")
    checks = [
        ("status", str), ("complete", bool), ("components", list), ("options", dict),
        ("target_fingerprint", dict), ("mbr", dict), ("identification", dict), ("source", dict),
    ]
    for key, kind in checks:
        if not isinstance(data.get(key), kind):
            raise InvalidManifest(f"manifest field {key!r} missing or not a {kind.__name__}")
    if data["status"] not in MANIFEST_STATUSES:
        raise InvalidManifest(f"unexpected manifest status {data['status']!r}")
    for key in ("include_userdata", "source_reread"):
        if not isinstance(data["options"].get(key), bool):
            raise InvalidManifest(f"options.{key} missing or not a boolean")
    names = []
    for item in data["components"]:
        if not isinstance(item, dict):
            raise InvalidManifest("a component is not a JSON object")
        for key, kind in (("name", str), ("file", str), ("status", str), ("required", bool)):
            if not isinstance(item.get(key), kind):
                raise InvalidManifest(f"component field {key!r} missing or invalid")
        for key in ("offset", "size"):
            if type(item.get(key)) is not int or item[key] < 0:
                raise InvalidManifest(f"component {item['name']}: {key} missing or invalid")
        if item["status"] not in COMPONENT_STATUSES:
            raise InvalidManifest(f"component {item['name']}: unexpected status {item['status']!r}")
        names.append(item["name"])
    if sorted(names) != sorted(backup.COMPONENT_FILES):
        raise InvalidManifest(f"unexpected component set {names}")
    return data


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_component(root: Path, comp: dict[str, Any], options: dict[str, Any],
                     report: dict[str, Any]) -> dict[str, Any]:
    name, status = comp["name"], comp["status"]
    canonical = backup.COMPONENT_FILES[name]
    out: dict[str, Any] = {
        "name": name, "required": comp["required"], "declared_status": status,
        "file": comp["file"], "expected_size": comp["size"], "result": "not_valid",
    }
    bad, incomplete = report["inconsistencies"], report["incomplete_checks"]

    expected_required = True if name in MANDATORY else options["include_userdata"]
    if comp["required"] != expected_required:
        bad.append(f"{name}: required={comp['required']} contradicts options.include_userdata")

    if not comp["required"]:
        if status != "not_requested":
            bad.append(f"{name}: not required but status is {status!r}")
        if regular_file_size(root / canonical) is not None:
            report["warnings"].append(f"{canonical} is present although it was not requested")
        out["result"] = "not_requested"
        return out

    if status != "verified":
        incomplete.append(f"{name}: recorded as {status!r}" + (f" ({comp['error']})" if comp.get("error") else ""))
        if regular_file_size(root / canonical) is not None:
            report["warnings"].append(f"{canonical} exists but the manifest does not record it as verified: not trusted")
        out["result"] = "not_verified"
        return out

    # From here the manifest claims a verified component: prove it.
    start = len(bad)
    if comp["file"] != canonical:
        bad.append(f"{name}: verified component points to {comp['file']!r} instead of {canonical!r}")
        return out
    path, problem = safe_file(root, comp["file"])
    if problem or path is None:
        bad.append(f"{name}: {problem}")
        return out
    size = regular_file_size(path)
    if size is None:
        bad.append(f"{name}: file {comp['file']} is missing or not a regular file")
        return out
    out["actual_size"] = size
    if size != comp["size"]:
        bad.append(f"{name}: {comp['file']} is {size} bytes, manifest expects {comp['size']} (truncated or altered)")
    for key in ("bytes_written", "destination_size"):
        if comp.get(key) != comp["size"]:
            bad.append(f"{name}: recorded {key}={comp.get(key)!r} contradicts size {comp['size']}")
    try:
        digest, read = sha256_file(path)
    except OSError as exc:
        incomplete.append(f"{name}: cannot read {comp['file']}: {exc}")
        out["result"] = "unreadable"
        return out
    out["sha256_recomputed"] = digest
    if read != size:
        bad.append(f"{name}: file size changed while reading")

    recorded = {key: comp.get(key) for key in ("sha256", "sha256_destination", "sha256_stream")}
    for key, value in recorded.items():
        if not isinstance(value, str) or not SHA256_RE.match(value):
            bad.append(f"{name}: recorded {key} missing or malformed")
        elif value != digest:
            bad.append(f"{name}: recomputed SHA-256 differs from recorded {key}")
    reread = comp.get("sha256_source_reread")
    if options["source_reread"]:
        if not isinstance(reread, str) or not SHA256_RE.match(reread):
            bad.append(f"{name}: source re-read was enabled but sha256_source_reread is missing")
        elif reread != digest:
            bad.append(f"{name}: recorded sha256_source_reread differs from the file")
    elif reread is not None:
        bad.append(f"{name}: --single-pass backup but a sha256_source_reread is recorded")
    if name == "pre_p1" and comp.get("expected_sha256") != digest:
        bad.append("pre_p1: file differs from the pre-P1 hash recorded at identification")

    out["result"] = "valid" if len(bad) == start else "not_valid"
    return out


def verify_sums(root: Path, manifest: dict[str, Any], components: list[dict[str, Any]],
                report: dict[str, Any]) -> dict[str, Any]:
    finished = manifest["status"] in ("complete", "failed")
    expected = {c["file"]: c.get("sha256_recomputed") for c in components
                if c["declared_status"] == "verified" and c["required"]}
    result: dict[str, Any] = {"present": False, "entries": {}, "matches": False}
    path, problem = safe_file(root, backup.SUMS_NAME)
    if problem or path is None:
        report["inconsistencies"].append(f"SHA256SUMS: {problem}")
        return result
    if regular_file_size(path) is None:
        if finished:
            report["inconsistencies"].append("SHA256SUMS is missing although the backup finished")
        else:
            report["incomplete_checks"].append("SHA256SUMS absent (backup did not finish)")
        return result
    result["present"] = True
    try:
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        report["inconsistencies"].append(f"SHA256SUMS unreadable: {exc}")
        return result
    entries: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = SUMS_LINE_RE.match(line)
        if not match:
            report["inconsistencies"].append(f"SHA256SUMS line {lineno}: unsupported format")
            continue
        digest, file_name = match.group(1).lower(), match.group(3)
        if safe_file(root, file_name)[1]:
            report["inconsistencies"].append(f"SHA256SUMS line {lineno}: unsafe name {file_name!r}")
            continue
        if file_name in entries:
            report["inconsistencies"].append(f"SHA256SUMS: duplicate entry for {file_name}")
        entries[file_name] = digest
    result["entries"] = entries
    for file_name, digest in entries.items():
        if file_name not in expected:
            report["inconsistencies"].append(f"SHA256SUMS lists {file_name}, which is not a verified component")
        elif expected[file_name] is not None and digest != expected[file_name]:
            report["inconsistencies"].append(f"SHA256SUMS hash for {file_name} differs from the file")
    for file_name in expected:
        if file_name not in entries:
            report["inconsistencies"].append(f"SHA256SUMS does not list verified component {file_name}")
    result["matches"] = set(entries) == set(expected) and all(
        expected[f] is not None and entries[f] == expected[f] for f in entries if f in expected
    )
    return result


def verify_pre_p1_metadata(root: Path, manifest: dict[str, Any], components: list[dict[str, Any]],
                           report: dict[str, Any]) -> dict[str, Any]:
    """Re-derive MBR, HWCONFIG and target fingerprint from pre-p1.bin."""
    bad = report["inconsistencies"]
    pre = next(c for c in components if c["name"] == "pre_p1")
    declared_fp = manifest["target_fingerprint"]
    result: dict[str, Any] = {"verifiable": False, "declared": declared_fp.get("fingerprint_sha256")}
    if pre["result"] != "valid":
        result["reason"] = "pre-p1.bin is not a valid verified component"
        return result

    path = root / backup.COMPONENT_FILES["pre_p1"]
    with open(path, "rb") as handle:
        mbr = inspector.parse_mbr(handle, None)
        try:
            hw = inspector.parse_hwconfig(handle)
        except (OSError, ValueError) as exc:
            hw = None
            bad.append(f"pre-p1.bin: HWCONFIG unreadable: {exc}")
        sector0 = inspector.read_at(handle, 0, inspector.SECTOR_SIZE)
        hw_raw = b""
        if hw:
            hw_raw = inspector.read_at(handle, hw["offset"], inspector.HWCONFIG_HEADER_SIZE + hw["payload_size"])

    if not hw or not hw.get("is_aura_hd_e606c0"):
        bad.append("pre-p1.bin does not contain a confirmed HWCONFIG v1.7 / 39 bytes / PCB 28")
        result["reason"] = "HWCONFIG not confirmed in pre-p1.bin"
        return result
    if not mbr.get("valid"):
        bad.append("pre-p1.bin does not contain a valid MBR: " + "; ".join(mbr.get("errors", [])))
        result["reason"] = "MBR invalid in pre-p1.bin"
        return result
    parts = {p["number"]: p for p in mbr["partitions"]}
    if sorted(parts) != [1, 2, 3]:
        bad.append(f"pre-p1.bin MBR has partitions {sorted(parts)}, expected P1, P2, P3")
        result["reason"] = "unexpected partitions in pre-p1.bin"
        return result

    # MBR geometry re-read from pre-p1.bin versus the manifest.
    mbr_decl = manifest["mbr"]
    if mbr_decl.get("sector0_sha256") != hashlib.sha256(sector0).hexdigest():
        bad.append("mbr.sector0_sha256 differs from sector 0 of pre-p1.bin")
    declared_parts = {p.get("number"): p for p in mbr_decl.get("partitions", []) if isinstance(p, dict)}
    for number, part in parts.items():
        decl = declared_parts.get(number, {})
        for key in ("type", "start_lba", "sectors", "offset", "size"):
            if decl.get(key) != part[key]:
                bad.append(f"mbr P{number}.{key}: manifest {decl.get(key)!r}, pre-p1.bin {part[key]!r}")
    if pre["expected_size"] != parts[1]["offset"]:
        bad.append("pre_p1 size differs from the P1 offset read in pre-p1.bin")
    by_name = {c["name"]: c for c in manifest["components"]}
    for name, number in (("p1_rootfs", 1), ("p2_recoveryfs", 2), ("p3_userdata", 3)):
        comp = by_name[name]
        if (comp["offset"], comp["size"]) != (parts[number]["offset"], parts[number]["size"]):
            bad.append(f"{name}: offset/size differ from P{number} in the MBR of pre-p1.bin")

    # HWCONFIG re-read versus the declared identification.
    hw_decl = manifest["identification"].get("hwconfig", {})
    for key in ("version", "payload_size", "offset"):
        if hw_decl.get(key) != hw[key]:
            bad.append(f"identification.hwconfig.{key}: manifest {hw_decl.get(key)!r}, pre-p1.bin {hw[key]!r}")
    if hw_decl.get("fields") != hw["fields"]:
        bad.append("identification.hwconfig.fields differ from the HWCONFIG of pre-p1.bin")

    # Target fingerprint, recomputed with the producer's own algorithm.
    identity = {
        "inspection": {"pre_p1_size": parts[1]["offset"], "pre_p1_sha256": pre["sha256_recomputed"]},
        "partitions": parts,
        "source_size": manifest["source"].get("size"),
    }
    recomputed = backup.build_fingerprint(identity, hw_raw)
    result.update({"verifiable": True, "recomputed": recomputed["fingerprint_sha256"], "fields": {}})
    if declared_fp.get("algorithm") != backup.FINGERPRINT_ALGORITHM:
        bad.append(f"unsupported fingerprint algorithm {declared_fp.get('algorithm')!r}")
    for key in ("pre_p1_size", "pre_p1_sha256", "hwconfig_sha256", "partitions"):
        same = declared_fp.get(key) == recomputed[key]
        result["fields"][key] = "matches" if same else "differs"
        if not same:
            bad.append(f"target_fingerprint.{key} differs from the value recomputed from pre-p1.bin")
    stable = {k: declared_fp.get(k) for k in ("algorithm", "pre_p1_size", "pre_p1_sha256", "hwconfig_sha256", "partitions")}
    internal = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
    if declared_fp.get("fingerprint_sha256") != internal:
        bad.append("target_fingerprint.fingerprint_sha256 does not match its own declared fields")
    result["matches"] = declared_fp.get("fingerprint_sha256") == recomputed["fingerprint_sha256"]
    if not result["matches"]:
        bad.append("target fingerprint recomputed from pre-p1.bin differs from the manifest")
    return result


def verify_labels(root: Path, manifest: dict[str, Any], components: list[dict[str, Any]],
                  report: dict[str, Any]) -> dict[str, Any]:
    """Re-read filesystem labels from the partition images that are valid."""
    labels: dict[str, Any] = {}
    declared = {p.get("number"): p for p in manifest["mbr"].get("partitions", []) if isinstance(p, dict)}
    for comp, number in zip(components[1:], (1, 2, 3)):
        if comp["result"] != "valid":
            continue
        with open(root / comp["file"], "rb") as handle:
            found = inspector.detect_filesystem(handle, 0)
        labels[comp["name"]] = found
        decl = declared.get(number, {})
        if (decl.get("filesystem"), decl.get("label")) != (found["filesystem"], found["label"]):
            report["inconsistencies"].append(
                f"{comp['name']}: filesystem/label re-read as {found['filesystem']}/{found['label']!r}, "
                f"manifest says {decl.get('filesystem')}/{decl.get('label')!r}"
            )
        expected = EXPECTED_LABELS.get(comp["name"])
        if expected and (found["filesystem"], found["label"]) != expected:
            report["inconsistencies"].append(f"{comp['name']}: image is not {expected[0]} labelled {expected[1]!r}")
    return labels


def verify_backup(root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "backup_dir": str(root),
        "status": "invalid",
        "ok": False,
        "invalid_reasons": [],
        "inconsistencies": [],
        "incomplete_checks": [],
        "warnings": [],
        "scope": "Consistency of the files with their manifest only: not authenticity, "
                 "not suitability for restoring a given card, not the whole card (selected components only).",
    }
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        report["invalid_reasons"].append(f"backup directory not accessible: {exc}")
        return report
    report["backup_dir"] = str(root)
    if not root.is_dir():
        report["invalid_reasons"].append("backup path is not a directory")
        return report
    try:
        manifest = load_manifest(root)
    except InvalidManifest as exc:
        report["invalid_reasons"].append(str(exc))
        return report

    report["manifest"] = {
        "schema_version": manifest["schema_version"], "tool_version": manifest.get("tool_version"),
        "status": manifest["status"], "complete": manifest["complete"],
        "created_utc": manifest.get("created_utc"), "completed_utc": manifest.get("completed_utc"),
        "options": manifest["options"],
    }
    by_name = {c["name"]: c for c in manifest["components"]}
    components = [verify_component(root, by_name[name], manifest["options"], report)
                  for name in backup.COMPONENT_FILES]
    report["components"] = components
    report["sha256sums"] = verify_sums(root, manifest, components, report)
    report["fingerprint"] = verify_pre_p1_metadata(root, manifest, components, report)
    report["labels_reread"] = verify_labels(root, manifest, components, report)

    # Never trust complete: true on its own.
    required = [c for c in components if c["required"]]
    all_valid = all(c["result"] == "valid" for c in required)
    recheck = manifest.get("identity_recheck")
    recheck_ok = isinstance(recheck, dict) and recheck.get("matches") is True
    if manifest["complete"]:
        if manifest["status"] != "complete":
            report["inconsistencies"].append(f"complete: true contradicts status {manifest['status']!r}")
        if not all_valid:
            report["inconsistencies"].append("complete: true but not every requested component re-verifies")
        if not recheck_ok:
            report["inconsistencies"].append("complete: true but identity_recheck does not match")
        if manifest.get("errors"):
            report["inconsistencies"].append("complete: true but the manifest records errors")
    else:
        if manifest["status"] == "complete":
            report["inconsistencies"].append("status 'complete' contradicts complete: false")
        report["incomplete_checks"].append(f"backup recorded as {manifest['status']!r}, complete: false")
        if recheck is not None and not recheck_ok:
            report["incomplete_checks"].append("identity_recheck recorded a pre-P1 change during the backup")
    if isinstance(recheck, dict) and recheck_ok:
        pre = components[0]
        if pre.get("sha256_recomputed") and recheck.get("pre_p1_sha256_after_copy") != pre["sha256_recomputed"]:
            report["inconsistencies"].append("identity_recheck hash differs from pre-p1.bin")

    known = {backup.MANIFEST_NAME, backup.SUMS_NAME, *backup.COMPONENT_FILES.values()}
    try:
        entries = sorted(os.listdir(root))
    except OSError as exc:
        entries = []
        report["warnings"].append(f"cannot list backup directory: {exc}")
    report["leftovers"] = [n for n in entries if n.endswith((".part", ".FAILED"))]
    for name in report["leftovers"]:
        report["warnings"].append(f"{name}: leftover of an unfinished or failed copy, never treated as valid")
    for name in entries:
        if name not in known and name not in report["leftovers"]:
            report["warnings"].append(f"{name}: not part of the backup format, ignored")

    report["declared_only"] = {
        "source": manifest["source"],
        "source_size": manifest["source"].get("size"),
        "timestamps": {"created_utc": manifest.get("created_utc"), "completed_utc": manifest.get("completed_utc")},
        "sha256_stream_and_source_reread": "compared with the files, but the source itself is not re-read",
        "identity_recheck": recheck,
        "p3_label": "only declared unless p3-userdata.img was backed up",
    }

    if report["inconsistencies"]:
        report["status"] = "inconsistent"
    elif report["incomplete_checks"]:
        report["status"] = "incomplete"
    else:
        report["status"] = "valid"
    report["ok"] = report["status"] == "valid"
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_human(report: dict[str, Any], lang: dict[str, str]) -> None:
    print(lang["title"])
    print(f"{lang['dir']}: {report['backup_dir']}")
    print()
    status = report["status"]
    if status == "invalid":
        print(lang["invalid"])
        for reason in report["invalid_reasons"]:
            print(f"  - {reason}")
        return
    print(f"{lang['components']}:")
    for comp in report.get("components", []):
        sha = comp.get("sha256_recomputed", "")
        print(f"  - {comp['name']}: {comp['result']} ({comp['declared_status']}) {comp['file']} {sha}")
    fp = report.get("fingerprint", {})
    if fp.get("verifiable"):
        state = lang["fp_ok"] if fp.get("matches") else lang["fp_bad"]
        print(f"{lang['fingerprint']}: {fp.get('recomputed')} — {state}")
    else:
        print(f"{lang['fingerprint']}: {lang['fp_na']} ({fp.get('reason', '?')})")
    sums = report.get("sha256sums", {})
    print(f"{lang['sums']}: {'OK' if sums.get('matches') else ('absent' if not sums.get('present') else 'ERROR')}")
    print(f"{lang['declared']}: source path, source size, timestamps, identity_recheck")
    for warning in report["warnings"]:
        print(f"  WARNING: {warning}")
    print()
    print(lang[status])
    for item in report["inconsistencies"]:
        print(f"  - {item}")
    for item in report["incomplete_checks"]:
        print(f"  - {item}")
    print()
    print(lang["limit"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline, read-only verification of a backup made by backup-aura-hd.py."
    )
    parser.add_argument("backup_dir", help="Directory containing backup-manifest.json")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Print only the JSON report on stdout (ASCII-escaped).")
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    report = verify_backup(Path(args.backup_dir))
    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print_human(report, FR if args.lang == "fr" else EN)
    return {
        "valid": EXIT_VALID, "incomplete": EXIT_INCOMPLETE,
        "inconsistent": EXIT_INCONSISTENT, "invalid": EXIT_INVALID,
    }[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
