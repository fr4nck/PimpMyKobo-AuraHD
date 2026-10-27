"""L08-I: correlate ARM ELF metadata with a supplied TAR and rootfs report.

Pure, bounded, memory-only diagnostics. Matching bytes and ELF headers do not
prove provenance of a Kobo image, loader behavior, ABI or runtime availability.
"""
import hashlib
import re

from arm_elf_dependencies import inspect_arm_dependencies
from arm_elf_preflight import ArmPreflightError
from rootfs_archive_reconcile import (
    RootfsArchiveError, compare_tar_archive_to_snapshot,
)
from rootfs_evidence_contract import (
    RootfsEvidenceError, verify_snapshot_evidence,
)
from rootfs_snapshot_aliases import (
    RootfsAliasError, resolve_snapshot_aliases,
)

MAX_CANDIDATE_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_HEADER_STATES = frozenset((
    "direct_arm_header_observed_only",
    "alias_to_arm_header_observed_only",
))


class ArmRuntimeEvidenceError(ValueError):
    """Stable error code; this module grants no permissions."""


def _candidate_digest(candidate, expected_digest):
    if (type(candidate) is not bytes or
            not 52 <= len(candidate) <= MAX_CANDIDATE_BYTES):
        raise ArmRuntimeEvidenceError("invalid_arm_candidate_size")
    if (expected_digest is not None and
            (type(expected_digest) is not str or
             _SHA256.fullmatch(expected_digest) is None)):
        raise ArmRuntimeEvidenceError("invalid_expected_candidate_digest")
    digest = hashlib.sha256(candidate).hexdigest()
    if expected_digest is not None and digest != expected_digest:
        raise ArmRuntimeEvidenceError("expected_candidate_digest_mismatch")
    return digest


def _classify_alias(finding, accepted_paths, archive_matched, indexed):
    """Accept only fully matched chains ending in an observed ARM ELF header."""
    chain = finding["observed_path_chain"]
    target = finding["observed_target"]
    digest = finding["observed_sha256"]
    if not archive_matched:
        state = "archive_not_matching"
    elif finding["state"] not in _HEADER_STATES:
        state = "alias_or_header_unresolved"
    elif (not chain or not target or target not in accepted_paths or
          any(path not in accepted_paths for path in chain)):
        state = "library_not_matched_in_archive"
    elif (target not in indexed or
          indexed[target].get("state") != "arm_eabi5_shared_header" or
          indexed[target].get("sha256") != digest):
        state = "library_header_digest_inconsistent"
    else:
        state = "header_matched_in_supplied_archive_only"
    return {
        "state": state,
        "alias_state": finding["state"],
        "observed_path_chain": chain,
        "observed_target": target,
        "observed_sha256": digest,
        "runtime_compatible": False,
        "launchable": False,
    }


def _interpreter_observation(path, snapshot, accepted, archive_matched, indexed):
    if path is None:
        return {"path": None, "state": "not_declared",
                "observed_target": None, "launchable": False}
    # Only shallow lib/ and usr/lib/ are within the L08-E/H inventory.
    relative = path[1:]
    parent, sep, name = relative.rpartition("/")
    if (not path.startswith("/") or not sep or
            parent not in ("lib", "usr/lib") or ".so" not in name):
        return {"path": path, "state": "outside_scanned_directories",
                "observed_target": None, "launchable": False}
    try:
        alias = resolve_snapshot_aliases((name,), snapshot)["findings"][0]
    except RootfsAliasError as exc:
        raise ArmRuntimeEvidenceError("invalid_interpreter_evidence") from exc
    checked = _classify_alias(alias, accepted, archive_matched, indexed)
    if (not alias["observed_path_chain"] or
            alias["observed_path_chain"][0] != relative):
        state = "not_observed_at_declared_path"
    else:
        state = checked["state"]
    return {"path": path, "state": state,
            "observed_target": checked["observed_target"],
            "alias_state": checked["alias_state"],
            "launchable": False}


def inspect_arm_runtime_evidence(candidate, archive_bytes, snapshot, *,
                                 expected_candidate_sha256=None,
                                 expected_archive_sha256=None,
                                 expected_audit_sha256=None,
                                 expected_source_id=None):
    """Link supplied evidence: ELF -> DT_NEEDED -> aliases -> TAR ↔ export.

    All expected values are caller-supplied comparisons, not authentication.
    No host filesystem access, extraction, process execution or device writes.
    """
    candidate_sha = _candidate_digest(candidate, expected_candidate_sha256)
    try:
        elf = inspect_arm_dependencies(candidate)
    except (ArmPreflightError, ValueError) as exc:
        raise ArmRuntimeEvidenceError("invalid_arm_elf") from exc
    try:
        evidence = verify_snapshot_evidence(
            snapshot, expected_audit_sha256=expected_audit_sha256,
            expected_source_id=expected_source_id)
    except (RootfsEvidenceError, TypeError, KeyError, ValueError) as exc:
        raise ArmRuntimeEvidenceError("invalid_snapshot_evidence") from exc
    try:
        archive = compare_tar_archive_to_snapshot(
            archive_bytes, snapshot,
            expected_archive_sha256=expected_archive_sha256)
    except (RootfsArchiveError, TypeError, KeyError, ValueError) as exc:
        raise ArmRuntimeEvidenceError("invalid_archive_evidence") from exc

    archive_matched = archive["verdict"] == "scoped_content_match"
    accepted = frozenset(archive["matched"])
    indexed = {row["path"]: row for row in snapshot["libraries"]}
    try:
        aliases = resolve_snapshot_aliases(elf["needed"], snapshot)
    except (RootfsAliasError, TypeError, ValueError) as exc:
        raise ArmRuntimeEvidenceError("invalid_alias_evidence") from exc

    findings = []
    for finding in aliases["findings"]:
        record = _classify_alias(finding, accepted, archive_matched, indexed)
        record["needed"] = finding["needed"]
        findings.append(record)
    interpreter = _interpreter_observation(
        elf["identity"]["interpreter"], snapshot, accepted,
        archive_matched, indexed)
    matching_headers = sum(
        item["state"] == "header_matched_in_supplied_archive_only"
        for item in findings)
    return {
        "schema": "pmkb-arm-runtime-evidence-v1",
        "scope": "caller_supplied_archive_export_and_elf_metadata_only",
        "candidate_sha256_measured": candidate_sha,
        "caller_candidate_digest_matched": expected_candidate_sha256 is not None,
        "archive_sha256_measured": archive["source_archive_sha256_measured"],
        "caller_archive_digest_matched": archive["expected_archive_digest_matched"],
        "snapshot_audit_sha256": evidence["observation_digest"],
        "snapshot_source_id": evidence["source_id"],
        "archive_verdict": archive["verdict"],
        "snapshot_full_scope": archive["snapshot_full_scope"],
        "needed": tuple(findings),
        "interpreter": interpreter,
        "needed_count": len(findings),
        "header_matches_in_supplied_archive": matching_headers,
        "image_hash_verified": False,
        "image_to_export_link_verified": False,
        "archive_origin_authenticated": False,
        "loader_abi_verified": False,
        "symbol_versions_verified": False,
        "transitive_dependencies_verified": False,
        "hardware_verified": False,
        "runtime_compatible": False,
        "launchable": False,
    }
