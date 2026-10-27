"""L08-M: correlate ELF dependencies with archive-backed rootfs metadata.

All inputs are caller-supplied bytes/reports. The archive is first verified
against the L08-E snapshot, then shallow library bytes are inspected without
extraction. Names are resolved only within lib/ and usr/lib/; no dynamic
loader path resolution, symbol resolution or target execution is performed.
"""
from io import BytesIO
import hashlib
import re
import tarfile

from arm_elf_runtime_metadata import (
    ArmRuntimeMetadataError, MAX_ELF_BYTES, MAX_LIBRARY_BYTES_TOTAL,
    compare_required_version_nodes, inspect_arm_runtime_metadata,
)
from arm_elf_symbol_resolution import (
    ArmSymbolResolutionError, compare_required_symbols,
)
from rootfs_archive_reconcile import (
    MAX_ARCHIVE_BYTES, MAX_CANDIDATES, MAX_LIBRARY_BYTES,
    RootfsArchiveError, _library_path, _member_path,
    compare_tar_archive_to_snapshot,
)
from rootfs_evidence_contract import RootfsEvidenceError, verify_snapshot_evidence
from rootfs_snapshot_aliases import (
    RootfsAliasError, resolve_snapshot_aliases,
)

MAX_GRAPH_OBJECTS = 32
MAX_GRAPH_DEPTH = 8
MAX_GRAPH_EDGES = 256
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_HEADER_STATES = frozenset((
    "direct_arm_header_observed_only",
    "alias_to_arm_header_observed_only",
))
_GRAPH_SUCCESS = frozenset((
    "metadata_observed_in_archive_only",
    "metadata_already_observed",
))


class ArmArchiveRuntimeEvidenceError(ValueError):
    """Stable refusal code; this module never authorizes installation."""


def _library_bytes_from_archive(archive_bytes):
    """Read bounded *.so* payloads from TAR in memory; never extract to disk."""
    found, seen, total = {}, set(), 0
    try:
        with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r|gz") as source:
            for member in source:
                relative = _member_path(member.name)
                path = _library_path(relative)
                if path is None:
                    continue
                if path in seen:
                    raise ArmArchiveRuntimeEvidenceError("duplicate_archive_library")
                seen.add(path)
                if member.issym():
                    continue
                if not member.isreg():
                    raise ArmArchiveRuntimeEvidenceError("unsupported_archive_library_kind")
                if type(member.size) is not int or member.size < 0 or member.size > MAX_LIBRARY_BYTES:
                    raise ArmArchiveRuntimeEvidenceError("archive_library_size_limit")
                total += member.size
                if total > MAX_LIBRARY_BYTES_TOTAL or len(found) >= MAX_CANDIDATES:
                    raise ArmArchiveRuntimeEvidenceError("archive_library_metadata_limit")
                stream = source.extractfile(member)
                if stream is None:
                    raise ArmArchiveRuntimeEvidenceError("archive_library_unreadable")
                with stream:
                    payload = stream.read(member.size + 1)
                if len(payload) != member.size:
                    raise ArmArchiveRuntimeEvidenceError("archive_library_truncated")
                found[path] = payload
    except ArmArchiveRuntimeEvidenceError:
        raise
    except (RootfsArchiveError, tarfile.TarError, EOFError, OSError,
            UnicodeError, OverflowError) as exc:
        raise ArmArchiveRuntimeEvidenceError("archive_library_scan_failed") from exc
    return found


def _resolve_needed(name, snapshot, snapshot_index, archive_matched, library_bytes):
    try:
        finding = resolve_snapshot_aliases((name,), snapshot)["findings"][0]
    except (RootfsAliasError, TypeError, ValueError) as exc:
        raise ArmArchiveRuntimeEvidenceError("invalid_alias_evidence") from exc
    state = finding["state"]
    chain = finding["observed_path_chain"]
    target = finding["observed_target"]
    if state not in _HEADER_STATES:
        return {"state": state, "alias_state": state, "target": target,
                "chain": chain, "payload": None, "finding": finding}
    if not chain or any(path not in archive_matched for path in chain):
        return {"state": "archive_alias_chain_not_matched",
                "alias_state": state, "target": target, "chain": chain,
                "payload": None, "finding": finding}
    row = snapshot_index.get(target)
    if (row is None or row.get("state") != "arm_eabi5_shared_header" or
            row.get("sha256") != finding["observed_sha256"]):
        return {"state": "snapshot_target_header_mismatch",
                "alias_state": state, "target": target, "chain": chain,
                "payload": None, "finding": finding}
    payload = library_bytes.get(target)
    if payload is None:
        return {"state": "archive_library_bytes_unavailable",
                "alias_state": state, "target": target, "chain": chain,
                "payload": None, "finding": finding}
    if hashlib.sha256(payload).hexdigest() != row["sha256"]:
        return {"state": "archive_library_digest_mismatch",
                "alias_state": state, "target": target, "chain": chain,
                "payload": None, "finding": finding}
    return {"state": "metadata_input_observed_only", "alias_state": state,
            "target": target, "chain": chain, "payload": payload,
            "finding": finding}


def _metadata_summary(name, role, target, payload, metadata):
    return {
        "name": name, "role": role, "archive_path": target,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "soname": metadata["soname"],
        "elf_type": metadata["identity"]["type"],
        "interpreter": metadata["identity"]["interpreter"],
        "needed": metadata["needed"],
        "rpath": metadata["rpath"], "runpath": metadata["runpath"],
        "version_requirements": metadata["version_requirements"],
        "version_definitions": metadata["version_definitions"],
        "warnings": metadata["warnings"],
    }


def _resolve_interpreter(candidate_metadata, snapshot, snapshot_index,
                         archive_matched, library_bytes):
    path = candidate_metadata["identity"]["interpreter"]
    if path is None:
        return {"path": None, "state": "not_declared", "metadata": None,
                "payload": None, "target": None}
    if not path.startswith("/"):
        return {"path": path, "state": "invalid_interpreter_path",
                "metadata": None, "payload": None, "target": None}
    relative = path[1:]
    if not ((relative.startswith("lib/") and "/" not in relative[4:]) or
            (relative.startswith("usr/lib/") and "/" not in relative[8:])):
        return {"path": path, "state": "outside_scanned_directories",
                "metadata": None, "payload": None, "target": None}
    name = relative.rsplit("/", 1)[-1]
    resolution = _resolve_needed(name, snapshot, snapshot_index,
                                 archive_matched, library_bytes)
    if not resolution["chain"] or resolution["chain"][0] != relative:
        return {"path": path, "state": "interpreter_path_not_exactly_observed",
                "metadata": None, "payload": None, "target": None}
    if resolution["state"] != "metadata_input_observed_only":
        return {"path": path, "state": resolution["state"],
                "metadata": None, "payload": None,
                "target": resolution["target"]}
    try:
        metadata = inspect_arm_runtime_metadata(resolution["payload"])
    except ArmRuntimeMetadataError as exc:
        return {"path": path, "state": "interpreter_metadata_rejected",
                "reason": str(exc), "metadata": None, "payload": None,
                "target": resolution["target"]}
    if metadata["identity"]["type"] != "ET_DYN":
        return {"path": path, "state": "interpreter_not_et_dyn",
                "metadata": metadata, "payload": resolution["payload"],
                "target": resolution["target"]}
    return {"path": path, "state": "interpreter_metadata_observed_only",
            "metadata": metadata, "payload": resolution["payload"],
            "target": resolution["target"]}


def _symbol_report_from_matched_archive(payload, metadata, library_map):
    """Audit direct DT_NEEDED using ONLY providers from the matched archive.

    Report names/version metadata, never hardware or loader compatibility.
    """
    providers = {name: library_map[name]
                 for name in metadata["needed"] if name in library_map}
    try:
        return compare_required_symbols(payload, providers)
    except ArmSymbolResolutionError as exc:
        return {
            "schema": "pmkb-elf-symbol-version-audit-v1",
            "scope": "archive_backed_symbol_metadata_only",
            "verdict": "comparison_refused",
            "reason": str(exc),
            "symbol_versions_verified": False,
            "dynamic_symbol_resolution_verified": False,
            "runtime_compatible": False,
            "hardware_verified": False,
            "launchable": False,
        }


def inspect_arm_archive_dependency_graph(candidate, archive_bytes, snapshot, *,
                                         expected_candidate_sha256=None,
                                         expected_archive_sha256=None,
                                         expected_audit_sha256=None,
                                         expected_source_id=None):
    """Inspect bounded direct/transitive DT_NEEDED edges from a matched TAR.

    A complete graph means only that names and ELF metadata were observed in
    the two shallow scanned folders. It does not prove loader search order,
    versioned symbol presence, transitive closure outside that scope, ABI or
    hardware compatibility.
    """
    if type(candidate) is not bytes or not 52 <= len(candidate) <= MAX_ELF_BYTES:
        raise ArmArchiveRuntimeEvidenceError("invalid_candidate_size")
    if (expected_candidate_sha256 is not None and
            (type(expected_candidate_sha256) is not str or
             _SHA.fullmatch(expected_candidate_sha256) is None)):
        raise ArmArchiveRuntimeEvidenceError("invalid_expected_candidate_digest")
    candidate_sha = hashlib.sha256(candidate).hexdigest()
    if expected_candidate_sha256 is not None and candidate_sha != expected_candidate_sha256:
        raise ArmArchiveRuntimeEvidenceError("expected_candidate_digest_mismatch")
    try:
        snapshot_evidence = verify_snapshot_evidence(
            snapshot, expected_audit_sha256=expected_audit_sha256,
            expected_source_id=expected_source_id)
        candidate_metadata = inspect_arm_runtime_metadata(candidate)
        archive = compare_tar_archive_to_snapshot(
            archive_bytes, snapshot,
            expected_archive_sha256=expected_archive_sha256)
    except (RootfsEvidenceError, RootfsArchiveError, ArmRuntimeMetadataError,
            TypeError, KeyError, ValueError) as exc:
        raise ArmArchiveRuntimeEvidenceError("input_evidence_rejected") from exc

    common = {
        "schema": "pmkb-arm-archive-dependency-graph-v1",
        "scope": "archive_matched_shallow_rootfs_static_metadata_only",
        "candidate_sha256_measured": candidate_sha,
        "caller_candidate_digest_matched": expected_candidate_sha256 is not None,
        "archive_sha256_measured": archive["source_archive_sha256_measured"],
        "caller_archive_digest_matched": archive["expected_archive_digest_matched"],
        "snapshot_audit_sha256": snapshot_evidence["observation_digest"],
        "snapshot_source_id": snapshot_evidence["source_id"],
        "candidate_metadata": candidate_metadata,
        "archive_verdict": archive["verdict"],
        "archive_matched_paths": archive["matched"],
        "archive_content_mismatch": archive["content_mismatch"],
        "archive_missing_from_export": archive["missing_from_export"],
        "archive_missing_from_source": archive["missing_from_archive"],
        "image_authenticated_as_kobo_p1": False,
        "archive_origin_authenticated": False,
        "symbol_versions_verified": False,
        "transitive_dependencies_verified": False,
        "runtime_compatible": False,
        "hardware_verified": False,
        "launchable": False,
    }
    if archive["verdict"] != "scoped_content_match":
        return {
            **common,
            "verdict": "archive_mismatch" if archive["verdict"] == "mismatch"
                       else "archive_partial_scope",
            "dependency_graph_available": False,
            "dependency_graph_complete_in_scanned_scope": None,
            "interpreter": {"path": candidate_metadata["identity"]["interpreter"],
                            "state": "not_evaluated_due_to_archive_verdict"},
            "dependency_edges": (), "library_objects": (),
            "version_node_reports": (),
            "dependency_symbol_reports": (),
            "interpreter_symbol_report": {
                "state": "not_evaluated_due_to_archive_verdict",
                "comparison": None, "launchable": False,
            },
            "candidate_symbol_report": {
                "verdict": "not_evaluated_due_to_archive_verdict",
                "symbol_versions_verified": False,
                "runtime_compatible": False,
                "hardware_verified": False,
                "launchable": False,
            },
        }

    try:
        library_bytes = _library_bytes_from_archive(archive_bytes)
    except ArmArchiveRuntimeEvidenceError:
        raise
    archive_matched = set(archive["matched"])
    snapshot_index = {row["path"]: row for row in snapshot["libraries"]}
    interpreter = _resolve_interpreter(
        candidate_metadata, snapshot, snapshot_index,
        archive_matched, library_bytes)

    queue = [(name, "<executable>", 1) for name in candidate_metadata["needed"]]
    if interpreter["state"] == "interpreter_metadata_observed_only":
        queue.extend((name, "PT_INTERP:" + interpreter["path"], 1)
                     for name in interpreter["metadata"]["needed"])
    processed, edges, objects, library_map = {}, [], [], {}
    object_bytes, metadata_by_name = {}, {}
    limit_hit = False

    while queue:
        name, parent_name, depth = queue.pop(0)
        if len(edges) >= MAX_GRAPH_EDGES:
            limit_hit = True
            break
        if name in processed:
            previous = processed[name]
            state = ("metadata_already_observed"
                     if previous["state"] == "metadata_observed_in_archive_only"
                     else previous["state"])
            edges.append({"from": parent_name, "needed": name, "state": state,
                          "archive_path": previous.get("target")})
            continue
        if depth > MAX_GRAPH_DEPTH:
            processed[name] = {"state": "dependency_depth_limit", "target": None}
            edges.append({"from": parent_name, "needed": name,
                          "state": "dependency_depth_limit", "archive_path": None})
            limit_hit = True
            continue
        if len(objects) >= MAX_GRAPH_OBJECTS:
            processed[name] = {"state": "dependency_object_limit", "target": None}
            edges.append({"from": parent_name, "needed": name,
                          "state": "dependency_object_limit", "archive_path": None})
            limit_hit = True
            continue
        resolved = _resolve_needed(
            name, snapshot, snapshot_index, archive_matched, library_bytes)
        target, payload = resolved["target"], resolved["payload"]
        if resolved["state"] != "metadata_input_observed_only":
            processed[name] = {"state": resolved["state"], "target": target}
            edges.append({"from": parent_name, "needed": name,
                          "state": resolved["state"], "archive_path": target,
                          "alias_state": resolved["alias_state"]})
            continue
        try:
            metadata = inspect_arm_runtime_metadata(payload)
        except ArmRuntimeMetadataError as exc:
            state = "library_metadata_rejected"
            processed[name] = {"state": state, "target": target}
            edges.append({"from": parent_name, "needed": name, "state": state,
                          "archive_path": target, "reason": str(exc)})
            continue
        if metadata["identity"]["type"] != "ET_DYN":
            state = "library_not_et_dyn"
        elif metadata["soname"] is not None and metadata["soname"] != name:
            state = "library_soname_mismatch"
        else:
            state = "metadata_observed_in_archive_only"
        processed[name] = {"state": state, "target": target}
        edges.append({"from": parent_name, "needed": name, "state": state,
                      "archive_path": target, "alias_state": resolved["alias_state"]})
        if state != "metadata_observed_in_archive_only":
            continue
        summary = _metadata_summary(name, "dependency", target, payload, metadata)
        objects.append(summary)
        object_bytes[name] = payload
        metadata_by_name[name] = metadata
        library_map[name] = payload
        for child in metadata["needed"]:
            queue.append((child, name, depth + 1))

    version_reports = []
    comparison_inputs = [("<executable>", candidate)]
    comparison_inputs.extend((name, object_bytes[name]) for name in object_bytes)
    if interpreter["state"] == "interpreter_metadata_observed_only":
        comparison_inputs.append(("<PT_INTERP:" + interpreter["path"] + ">",
                                  interpreter["payload"]))
    for label, payload in comparison_inputs:
        try:
            comparison = compare_required_version_nodes(payload, library_map)
            version_reports.append({"object": label, "comparison": comparison})
        except ArmRuntimeMetadataError as exc:
            version_reports.append({"object": label, "state": "comparison_refused",
                                    "reason": str(exc)})

    # Check candidate and all parsed dependent objects independently.
    # A complete name graph does not imply symbol/ABI compatibility.
    candidate_symbol_report = _symbol_report_from_matched_archive(
        candidate, candidate_metadata, library_map)
    dependency_symbol_reports = []
    for name, payload in object_bytes.items():
        dependency_symbol_reports.append({
            "object": name,
            "archive_path": processed[name]["target"],
            "comparison": _symbol_report_from_matched_archive(
                payload, metadata_by_name[name], library_map),
            "launchable": False,
        })
    interpreter_symbol_report = {
        "state": interpreter["state"],
        "comparison": (
            _symbol_report_from_matched_archive(
                interpreter["payload"], interpreter["metadata"], library_map)
            if interpreter["state"] == "interpreter_metadata_observed_only"
            else None),
        "launchable": False,
    }

    interpreter_state_ok = interpreter["state"] in (
        "not_declared", "interpreter_metadata_observed_only")
    edges_ok = all(edge["state"] in _GRAPH_SUCCESS for edge in edges)
    graph_complete = (None if candidate_metadata["scope"] == "static_elf_identity_only"
                      else bool(edges_ok and interpreter_state_ok and not limit_hit))
    return {
        **common,
        "verdict": "metadata_graph_observed" if graph_complete else "metadata_graph_partial",
        "dependency_graph_available": True,
        "dependency_graph_complete_in_scanned_scope": graph_complete,
        "dependency_graph_depth_limit": MAX_GRAPH_DEPTH,
        "dependency_graph_object_limit": MAX_GRAPH_OBJECTS,
        "dependency_graph_edge_limit": MAX_GRAPH_EDGES,
        "interpreter": {
            "path": interpreter["path"], "state": interpreter["state"],
            "archive_path": interpreter.get("target"),
            "soname": (interpreter["metadata"]["soname"]
                       if interpreter.get("metadata") else None),
            "needed": (interpreter["metadata"]["needed"]
                       if interpreter.get("metadata") else ()),
            "launchable": False,
        },
        "dependency_edges": tuple(edges),
        "library_objects": tuple(objects),
        "version_node_reports": tuple(version_reports),
        "candidate_symbol_report": candidate_symbol_report,
        "dependency_symbol_reports": tuple(dependency_symbol_reports),
        "interpreter_symbol_report": interpreter_symbol_report,
        "symbol_audited_dependency_objects": len(dependency_symbol_reports),
        "library_objects_inspected": len(objects),
        "library_bytes_inspected": sum(len(x) for x in object_bytes.values()),
        "unresolved_names": tuple(sorted(
            name for name, item in processed.items()
            if item["state"] not in _GRAPH_SUCCESS)),
    }
