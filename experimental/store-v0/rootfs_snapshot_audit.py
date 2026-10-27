"""PMKB Store L08-E: bounded, read-only audit of an EXTRACTED rootfs snapshot.

Reads selected library files from a caller-supplied host directory only.
No mounts, extraction, firmware downloads, execution, or filesystem writes.
The export's provenance is DECLARED, not authenticated by this audit.
Symlinks are recorded but never followed or considered resolved.
"""
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import re
import stat

from arm_elf_preflight import ArmPreflightError, inspect_arm_elf
from arm_elf_dependencies import inspect_arm_dependencies

SEARCH_DIRECTORIES = ("lib", "usr/lib")
MAX_ENTRIES_PER_DIRECTORY = 2048
MAX_CANDIDATES = 512
MAX_LIBRARY_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 96 * 1024 * 1024
_CHUNK = 65536
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)


class RootfsSnapshotError(ValueError):
    """Stable refusal code for snapshot probes; never authorizes execution."""


def _fingerprint(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns)


def _safe_root(root):
    try:
        directory = Path(root)
        if directory.is_symlink() or not directory.is_dir():
            raise RootfsSnapshotError("snapshot_directory_required")
        resolved = directory.resolve(strict=True)
        if resolved == Path(resolved.anchor).resolve():
            raise RootfsSnapshotError("filesystem_root_refused")
        return directory
    except (TypeError, ValueError, OSError) as exc:
        if isinstance(exc, RootfsSnapshotError):
            raise
        raise RootfsSnapshotError("snapshot_directory_required") from exc


def _read_regular(path, before, total):
    if before.st_size > MAX_LIBRARY_BYTES:
        raise RootfsSnapshotError("library_size_limit")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            current = os.fstat(stream.fileno())
            if not stat.S_ISREG(current.st_mode) or _fingerprint(current) != _fingerprint(before):
                raise RootfsSnapshotError("snapshot_changed")
            chunks = []
            length = 0
            while True:
                chunk = stream.read(_CHUNK)
                if not chunk:
                    break
                length += len(chunk)
                if length > MAX_LIBRARY_BYTES or total[0] + length > MAX_TOTAL_BYTES:
                    raise RootfsSnapshotError("library_size_limit")
                chunks.append(chunk)
            after_fd = os.fstat(stream.fileno())
        after_path = path.lstat()
        if (_fingerprint(after_fd) != _fingerprint(before) or
                _fingerprint(after_path) != _fingerprint(before) or
                length != before.st_size):
            raise RootfsSnapshotError("snapshot_changed")
    except (OSError, ValueError) as exc:
        if isinstance(exc, RootfsSnapshotError):
            raise
        raise RootfsSnapshotError("snapshot_read_failed") from exc
    total[0] += length
    return b"".join(chunks)


def _file_record(path, logical_path, st, total):
    name = path.name
    if not _NAME.fullmatch(name):
        raise RootfsSnapshotError("invalid_library_filename")
    if stat.S_ISLNK(st.st_mode):
        try:
            target = os.readlink(path)
            if _fingerprint(path.lstat()) != _fingerprint(st):
                raise RootfsSnapshotError("snapshot_changed")
        except (OSError, ValueError) as exc:
            if isinstance(exc, RootfsSnapshotError):
                raise
            raise RootfsSnapshotError("snapshot_read_failed") from exc
        return {"path": logical_path, "soname_candidate": name,
                "state": "symlink_unresolved", "link_target": target}
    if not stat.S_ISREG(st.st_mode):
        raise RootfsSnapshotError("unsupported_library_file")
    data = _read_regular(path, st, total)
    record = {"path": logical_path, "soname_candidate": name,
              "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    try:
        identity = inspect_arm_elf(data)
    except ArmPreflightError as exc:
        record.update(state="elf_identity_unverified", reason=str(exc))
    else:
        record["identity"] = identity
        record["state"] = ("arm_eabi5_shared_header" if
                           identity["type"] == "ET_DYN" else
                           "arm_eabi5_not_shared_object")
    return record


def scan_rootfs_snapshot(root, *, source_id, declared_source_sha256=None):
    """Inspect direct children of lib/ and usr/lib/ in an immutable export.

    Library names outside these two directories remain unknown. The
    snapshot may be a synthetic fixture or a caller-provided export; this
    function does not establish that it came from a particular Kobo.
    """
    if type(source_id) is not str or not _ID.fullmatch(source_id):
        raise RootfsSnapshotError("invalid_source_identifier")
    if (declared_source_sha256 is not None and
            (type(declared_source_sha256) is not str or
             not _SHA256.fullmatch(declared_source_sha256))):
        raise RootfsSnapshotError("invalid_declared_hash")
    base = _safe_root(root)
    records, directories, total = [], [], [0]
    for relative in SEARCH_DIRECTORIES:
        parts = relative.split("/")
        blocked_parent = None
        for depth in range(1, len(parts)):
            ancestor = base.joinpath(*parts[:depth])
            try:
                parent_info = ancestor.lstat()
            except FileNotFoundError:
                blocked_parent = "not_scanned_missing_parent"
                break
            except OSError as exc:
                raise RootfsSnapshotError("snapshot_read_failed") from exc
            if not stat.S_ISDIR(parent_info.st_mode):
                blocked_parent = "not_scanned_parent_non_directory"
                break
        if blocked_parent is not None:
            directories.append({"path": relative, "state": blocked_parent})
            continue
        folder = base.joinpath(*parts)
        try:
            info = folder.lstat()
        except FileNotFoundError:
            directories.append({"path": relative, "state": "not_present_in_export"})
            continue
        except OSError as exc:
            raise RootfsSnapshotError("snapshot_read_failed") from exc
        if not stat.S_ISDIR(info.st_mode):
            directories.append({"path": relative, "state": "not_scanned_non_directory"})
            continue
        try:
            with os.scandir(folder) as entries:
                listed = list(islice(entries, MAX_ENTRIES_PER_DIRECTORY + 1))
            if len(listed) > MAX_ENTRIES_PER_DIRECTORY:
                raise RootfsSnapshotError("directory_entry_limit")
            for entry in sorted(listed, key=lambda x: x.name):
                name = entry.name
                if ".so" not in name:
                    continue
                if len(records) >= MAX_CANDIDATES:
                    raise RootfsSnapshotError("library_count_limit")
                path = folder / name
                st = path.lstat()
                records.append(_file_record(path, relative + "/" + name, st, total))
            if _fingerprint(folder.lstat()) != _fingerprint(info):
                raise RootfsSnapshotError("snapshot_changed")
        except (OSError, ValueError) as exc:
            if isinstance(exc, RootfsSnapshotError):
                raise
            raise RootfsSnapshotError("snapshot_read_failed") from exc
        directories.append({"path": relative, "state": "scanned_nonrecursive"})
    document = {"directories": directories, "libraries": records}
    encoded = json.dumps(document, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("ascii")
    return {
        "schema": "pmkb-rootfs-snapshot-audit-v1",
        "scope": "extracted_directory_observation_only",
        "provenance": {"source_id": source_id,
                       "declared_source_sha256": declared_source_sha256,
                       "source_hash_verified": False},
        "audit_sha256": hashlib.sha256(encoded).hexdigest(),
        "directories": tuple(directories),
        "libraries": tuple(records),
        "bytes_inspected": total[0],
        "launchable": False,
        "hardware_verified": False,
    }


def compare_needed_to_snapshot(needed, snapshot):
    """Name and ELF-header comparison; never a runtime ABI availability claim."""
    if (type(needed) is not tuple or len(needed) > 32 or
            any(type(n) is not str or not _NAME.fullmatch(n) for n in needed) or
            len(set(needed)) != len(needed)):
        raise RootfsSnapshotError("invalid_needed_names")
    if (type(snapshot) is not dict or
            snapshot.get("schema") != "pmkb-rootfs-snapshot-audit-v1" or
            snapshot.get("scope") != "extracted_directory_observation_only" or
            snapshot.get("launchable") is not False or
            type(snapshot.get("libraries")) is not tuple):
        raise RootfsSnapshotError("invalid_snapshot_report")
    findings = []
    for name in needed:
        matches = [item for item in snapshot["libraries"]
                   if item.get("soname_candidate") == name]
        verified = [item for item in matches
                    if item.get("state") == "arm_eabi5_shared_header"]
        if len(matches) > 1:
            state = "ambiguous_export_name"
        elif len(verified) == 1:
            state = "arm_header_observed_only"
        elif matches and matches[0].get("state") == "symlink_unresolved":
            state = "unresolved_symlink"
        elif matches:
            state = "nonmatching_library_header"
        else:
            state = "not_observed_in_scanned_directories"
        findings.append({"needed": name, "state": state,
                         "observed_paths": tuple(item["path"] for item in matches),
                         "observed_hashes": tuple(item["sha256"] for item in verified),
                         "launchable": False})
    return {"scope": "snapshot_names_and_elf_headers_only",
            "findings": tuple(findings), "launchable": False,
            "hardware_verified": False}


def inspect_elf_against_rootfs_snapshot(elf_bytes, root, *,
                                       source_id, declared_source_sha256=None):
    """Combine L08-C dependency decoding with a bounded read-only scan."""
    elf = inspect_arm_dependencies(elf_bytes)
    snapshot = scan_rootfs_snapshot(
        root, source_id=source_id,
        declared_source_sha256=declared_source_sha256)
    return {"elf": elf, "snapshot": snapshot,
            "comparison": compare_needed_to_snapshot(elf["needed"], snapshot),
            "launchable": False, "hardware_verified": False}
