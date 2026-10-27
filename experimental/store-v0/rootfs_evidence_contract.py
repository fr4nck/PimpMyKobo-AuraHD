"""L08-G: pure consistency check of a rootfs observation report.

The SHA-256 only covers an already-created report. It is NOT a signature,
an attestation of an original disk/image, or proof of availability on Kobo.
No filesystem, subprocess, network, or device operations are performed.
"""
import hashlib
import json
import re

from rootfs_snapshot_audit import (
    MAX_CANDIDATES, MAX_LIBRARY_BYTES, MAX_TOTAL_BYTES, SEARCH_DIRECTORIES,
)

_SCHEMA = "pmkb-rootfs-snapshot-audit-v1"
_OUTPUT_SCHEMA = "pmkb-rootfs-evidence-check-v1"
_SCOPE = "extracted_directory_observation_only"
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_SOURCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)
_REASONS = re.compile(r"[a-z_]{1,80}\Z", re.ASCII)
_DIRECTORY_STATES = frozenset((
    "not_present_in_export", "not_scanned_missing_parent",
    "not_scanned_parent_non_directory", "not_scanned_non_directory",
    "scanned_nonrecursive",
))
_IDENTITY_FIELDS = frozenset((
    "arm_eabi", "interpreter", "format", "machine", "type",
    "scope", "launchable",
))
_REPORT_FIELDS = frozenset((
    "schema", "scope", "provenance", "audit_sha256", "directories",
    "libraries", "bytes_inspected", "launchable", "hardware_verified",
))


class RootfsEvidenceError(ValueError):
    """Stable reason code; no trust/evaluation granted on success."""


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _valid_identity(value, expected_type):
    if type(value) is not dict or set(value) != _IDENTITY_FIELDS:
        return False
    interpreter = value["interpreter"]
    return (value["arm_eabi"] == 5 and type(value["arm_eabi"]) is int and
            value["format"] == "ELF32-LE" and
            value["machine"] == "EM_ARM" and
            value["type"] == expected_type and
            value["scope"] == "identity_only_unverified" and
            value["launchable"] is False and
            (interpreter is None or
             (type(interpreter) is str and 1 <= len(interpreter) <= 256
              and interpreter.startswith("/") and "\x00" not in interpreter)))


def _check_records(snapshot):
    dirs, libs = snapshot["directories"], snapshot["libraries"]
    if (type(dirs) is not tuple or len(dirs) != len(SEARCH_DIRECTORIES) or
            type(libs) is not tuple or len(libs) > MAX_CANDIDATES):
        raise RootfsEvidenceError("invalid_observation_collections")
    scanned = set()
    for expected, row in zip(SEARCH_DIRECTORIES, dirs):
        if (type(row) is not dict or
                set(row) != {"path", "state"} or
                row["path"] != expected or
                type(row["state"]) is not str or
                row["state"] not in _DIRECTORY_STATES):
            raise RootfsEvidenceError("invalid_observation_directories")
        if row["state"] == "scanned_nonrecursive":
            scanned.add(expected)
    seen = set()
    bytes_total = 0
    for row in libs:
        if type(row) is not dict:
            raise RootfsEvidenceError("invalid_observation_entry")
        path, name, state = (
            row.get("path"), row.get("soname_candidate"), row.get("state"))
        if (type(name) is not str or _NAME.fullmatch(name) is None or
                ".so" not in name or
                type(path) is not str or
                path not in ("lib/" + name, "usr/lib/" + name) or
                path in seen or
                path.rsplit("/", 1)[0] not in scanned or
                type(state) is not str):
            raise RootfsEvidenceError("invalid_observation_entry")
        seen.add(path)
        if state == "symlink_unresolved":
            if (set(row) != {"path", "soname_candidate", "state", "link_target"} or
                    type(row["link_target"]) is not str or
                    len(row["link_target"]) > 512):
                raise RootfsEvidenceError("invalid_symlink_observation")
            continue
        common = {"path", "soname_candidate", "state", "size", "sha256"}
        if (type(row.get("size")) is not int or
                not 0 <= row["size"] <= MAX_LIBRARY_BYTES or
                not _sha(row.get("sha256"))):
            raise RootfsEvidenceError("invalid_file_observation")
        bytes_total += row["size"]
        if bytes_total > MAX_TOTAL_BYTES:
            raise RootfsEvidenceError("invalid_observation_size")
        if state == "elf_identity_unverified":
            if (set(row) != common | {"reason"} or
                    type(row.get("reason")) is not str or
                    _REASONS.fullmatch(row["reason"]) is None):
                raise RootfsEvidenceError("invalid_file_observation")
        elif state in ("arm_eabi5_shared_header", "arm_eabi5_not_shared_object"):
            expected_type = ("ET_DYN" if state == "arm_eabi5_shared_header"
                             else "ET_EXEC")
            if (set(row) != common | {"identity"} or
                    not _valid_identity(row.get("identity"), expected_type)):
                raise RootfsEvidenceError("invalid_file_observation")
        else:
            raise RootfsEvidenceError("invalid_file_observation")
    if (type(snapshot["bytes_inspected"]) is not int or
            snapshot["bytes_inspected"] != bytes_total):
        raise RootfsEvidenceError("invalid_observation_size")
    return bytes_total


def verify_snapshot_evidence(snapshot, *, expected_audit_sha256=None,
                             expected_source_id=None):
    """Check internal data consistency and optionally caller-provided anchors.

    Matching caller-provided values is not cryptographic authentication;
    the trusted origin of those anchors must be established independently.
    """
    if (type(snapshot) is not dict or set(snapshot) != _REPORT_FIELDS or
            snapshot["schema"] != _SCHEMA or
            snapshot["scope"] != _SCOPE or
            snapshot["launchable"] is not False or
            snapshot["hardware_verified"] is not False):
        raise RootfsEvidenceError("invalid_snapshot_report")
    origin = snapshot["provenance"]
    if (type(origin) is not dict or
            set(origin) != {"source_id", "declared_source_sha256",
                            "source_hash_verified"} or
            type(origin["source_id"]) is not str or
            _SOURCE.fullmatch(origin["source_id"]) is None or
            origin["source_hash_verified"] is not False or
            (origin["declared_source_sha256"] is not None and
             not _sha(origin["declared_source_sha256"]))):
        raise RootfsEvidenceError("invalid_provenance")
    if not _sha(snapshot["audit_sha256"]):
        raise RootfsEvidenceError("invalid_audit_digest")
    if expected_audit_sha256 is not None and not _sha(expected_audit_sha256):
        raise RootfsEvidenceError("invalid_expected_digest")
    if (expected_source_id is not None and
            (type(expected_source_id) is not str or
             _SOURCE.fullmatch(expected_source_id) is None)):
        raise RootfsEvidenceError("invalid_expected_source")
    total = _check_records(snapshot)
    document = {"directories": snapshot["directories"],
                "libraries": snapshot["libraries"]}
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("ascii")
    actual = hashlib.sha256(encoded).hexdigest()
    if actual != snapshot["audit_sha256"]:
        raise RootfsEvidenceError("audit_digest_mismatch")
    if expected_audit_sha256 is not None and actual != expected_audit_sha256:
        raise RootfsEvidenceError("expected_digest_mismatch")
    if (expected_source_id is not None and
            origin["source_id"] != expected_source_id):
        raise RootfsEvidenceError("expected_source_mismatch")
    return {
        "schema": _OUTPUT_SCHEMA,
        "scope": "internal_snapshot_consistency_only",
        "observation_digest": actual,
        "observation_digest_consistent": True,
        "caller_digest_matches": (expected_audit_sha256 is not None),
        "caller_source_matches": (expected_source_id is not None),
        "record_count": len(snapshot["libraries"]),
        "bytes_declared": total,
        "source_id": origin["source_id"],
        "declared_source_sha256": origin["declared_source_sha256"],
        "image_hash_verified": False,
        "source_provenance_authenticated": False,
        "export_matches_source_image": False,
        "hardware_verified": False,
        "runtime_compatible": False,
        "launchable": False,
    }
