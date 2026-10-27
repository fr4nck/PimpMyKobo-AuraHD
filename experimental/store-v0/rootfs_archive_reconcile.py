"""L08-H: compare a supplied rootfs TAR.GZ archive with an L08-E report.

Inert, in-memory, no extraction, filesystem paths, subprocess or device access.
A match links only archive bytes with observed exported file hashes inside
two shallow folders. It does NOT prove image origin, ext4 extraction,
authenticity, or executable ABI compatibility on a real Kobo.
"""
from io import BytesIO
import hashlib
import re
import tarfile

from rootfs_evidence_contract import (
    RootfsEvidenceError, verify_snapshot_evidence,
)
from rootfs_snapshot_audit import (
    MAX_CANDIDATES, MAX_LIBRARY_BYTES, MAX_TOTAL_BYTES, SEARCH_DIRECTORIES,
)

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_TAR_MEMBERS = 40000
MAX_TOTAL_DECLARED_BYTES = 768 * 1024 * 1024
MAX_PATH_LENGTH = 256
MAX_LINK_LENGTH = 512
CHUNK = 65536
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)


class RootfsArchiveError(ValueError):
    """Stable failure code for malformed or inconsistent source observations."""


def _member_path(raw):
    """Canonicalize a TAR entry name; never resolve it on the host."""
    if type(raw) is not str or len(raw) > MAX_PATH_LENGTH or "\x00" in raw:
        raise RootfsArchiveError("unsafe_archive_member")
    if raw in (".", "./"):
        return "."  # conventional TAR root-directory record
    name = raw[2:] if raw.startswith("./") else raw
    name = name[:-1] if name.endswith("/") else name
    if not name or name.startswith("/") or "\\" in name:
        raise RootfsArchiveError("unsafe_archive_member")
    segments = name.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise RootfsArchiveError("unsafe_archive_member")
    return name


def _library_path(name):
    for parent in SEARCH_DIRECTORIES:
        prefix = parent + "/"
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            if "/" not in suffix and ".so" in suffix:
                if _NAME.fullmatch(suffix) is None:
                    raise RootfsArchiveError("invalid_archive_library_name")
                return name
    return None


def _archive_inventory(raw):
    """Read only selected TAR members; never call extract or extractall."""
    observed = {}
    total_declared, total_read, members_seen = 0, 0, 0
    try:
        with tarfile.open(fileobj=BytesIO(raw), mode="r|gz") as source:
            for member in source:
                members_seen += 1
                if members_seen > MAX_TAR_MEMBERS:
                    raise RootfsArchiveError("archive_member_limit")
                if type(member.size) is not int or member.size < 0:
                    raise RootfsArchiveError("invalid_archive_member_size")
                total_declared += member.size
                if total_declared > MAX_TOTAL_DECLARED_BYTES:
                    raise RootfsArchiveError("archive_declared_size_limit")
                relative = _member_path(member.name)
                library = _library_path(relative)
                if library is None:
                    continue
                if library in observed:
                    raise RootfsArchiveError("duplicate_archive_library")
                if len(observed) >= MAX_CANDIDATES:
                    raise RootfsArchiveError("archive_library_count_limit")
                if member.issym():
                    if (type(member.linkname) is not str or
                            len(member.linkname) > MAX_LINK_LENGTH):
                        raise RootfsArchiveError("invalid_archive_symlink")
                    observed[library] = {
                        "type": "symlink", "link_target": member.linkname,
                    }
                elif member.isreg():
                    if member.size > MAX_LIBRARY_BYTES:
                        raise RootfsArchiveError("archive_library_size_limit")
                    stream = source.extractfile(member)
                    if stream is None:
                        raise RootfsArchiveError("invalid_archive_library")
                    digest, count = hashlib.sha256(), 0
                    with stream:
                        while True:
                            block = stream.read(CHUNK)
                            if not block:
                                break
                            count += len(block)
                            total_read += len(block)
                            if (count > MAX_LIBRARY_BYTES or
                                    total_read > MAX_TOTAL_BYTES):
                                raise RootfsArchiveError("archive_library_size_limit")
                            digest.update(block)
                    if count != member.size:
                        raise RootfsArchiveError("truncated_archive_library")
                    observed[library] = {
                        "type": "regular", "size": count,
                        "sha256": digest.hexdigest(),
                    }
                else:
                    # This includes hard links and special files; no dereference.
                    raise RootfsArchiveError("unsupported_archive_library_kind")
    except (tarfile.TarError, EOFError, OSError, UnicodeError, OverflowError) as exc:
        raise RootfsArchiveError("unreadable_rootfs_archive") from exc
    return observed, members_seen, total_read


def compare_tar_archive_to_snapshot(archive_bytes, snapshot, *,
                                    expected_archive_sha256=None):
    """Compare independently provided archive bytes against snapshot hashes.

    The optional caller-provided expected digest is merely compared, not
    authenticated, and does not prove a relation to P1 or another image.
    """
    if type(archive_bytes) is not bytes or not (
            1 <= len(archive_bytes) <= MAX_ARCHIVE_BYTES):
        raise RootfsArchiveError("invalid_archive_size")
    if (expected_archive_sha256 is not None and
            (type(expected_archive_sha256) is not str or
             _SHA256.fullmatch(expected_archive_sha256) is None)):
        raise RootfsArchiveError("invalid_expected_archive_digest")
    try:
        evidence = verify_snapshot_evidence(snapshot)
    except (RootfsEvidenceError, TypeError, KeyError, ValueError) as exc:
        raise RootfsArchiveError("invalid_snapshot_evidence") from exc
    archive_sha = hashlib.sha256(archive_bytes).hexdigest()
    if (expected_archive_sha256 is not None and
            archive_sha != expected_archive_sha256):
        raise RootfsArchiveError("expected_archive_digest_mismatch")
    source, members_seen, bytes_read = _archive_inventory(archive_bytes)
    export = {r["path"]: r for r in snapshot["libraries"]}
    matched, mismatched, missing_export, missing_archive = [], [], [], []
    for path in sorted(set(source) | set(export)):
        original = source.get(path)
        observed = export.get(path)
        if original is None:
            missing_archive.append(path)
        elif observed is None:
            missing_export.append(path)
        elif original["type"] == "symlink":
            if (observed["state"] == "symlink_unresolved" and
                    observed["link_target"] == original["link_target"]):
                matched.append(path)
            else:
                mismatched.append(path)
        elif (observed["state"] != "symlink_unresolved" and
              observed["size"] == original["size"] and
              observed["sha256"] == original["sha256"]):
            matched.append(path)
        else:
            mismatched.append(path)
    full_scope = all(
        row["state"] == "scanned_nonrecursive"
        for row in snapshot["directories"])
    if mismatched or missing_export or missing_archive:
        verdict = "mismatch"
    elif not full_scope:
        verdict = "partial_scope"
    else:
        verdict = "scoped_content_match"
    return {
        "schema": "pmkb-rootfs-tar-reconcile-v1",
        "scope": "archive_vs_extracted_observations_only",
        "verdict": verdict,
        "source_archive_sha256_measured": archive_sha,
        "expected_archive_digest_matched": expected_archive_sha256 is not None,
        "snapshot_audit_sha256": evidence["observation_digest"],
        "tar_members_seen": members_seen,
        "library_bytes_inspected": bytes_read,
        "matched": tuple(matched),
        "content_mismatch": tuple(mismatched),
        "missing_from_export": tuple(missing_export),
        "missing_from_archive": tuple(missing_archive),
        "snapshot_full_scope": full_scope,
        "archive_is_original_ext4_image": False,
        "original_image_hash_verified": False,
        "archive_origin_authenticated": False,
        "export_matches_original_image": False,
        "hardware_verified": False,
        "runtime_compatible": False,
        "launchable": False,
    }
