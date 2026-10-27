#!/usr/bin/env python3
"""Host-only, temporary-directory checkpoint for native PMKB Notes.

This module deliberately has no CLI or physical P3 adapter. It accepts only
an existing directory below tempfile.gettempdir(), not a device or mount
chosen by the user. It retains an earlier validated snapshot during replace.
Actual Kobo durability and restore-into-C11 are NOT implemented.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

MAX_JSON = 3_000_000
MAGIC = b"PMKB-NOTES-CHECKPOINT-V1\n"
MAX_FRAME = MAX_JSON + len(MAGIC) + 80
CURRENT = "notes-current.chk"
PREVIOUS = "notes-previous.chk"
NOTE_ID = re.compile(r"pmkb_[0-9]{6}\Z")
UTC_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{3})?Z\Z")
FRAME_HEADER = re.compile(rb"([0-9]{1,7}) ([0-9a-f]{64})\Z")
TITLE_WHITESPACE = frozenset(
    list(range(9, 14)) + [32, 0x85, 0xA0, 0x1680] +
    list(range(0x2000, 0x200B)) +
    [0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF]
)


class CheckpointError(ValueError):
    """Malformed or unsafe host checkpoint; never treat as an empty book."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CheckpointError("duplicate_json_key")
        result[key] = value
    return result


def _bad_constant(_value):
    raise CheckpointError("nonfinite_json_constant")


def _units(value):
    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeError as exc:
        raise CheckpointError("invalid_unicode") from exc


def _timestamp(value):
    if not isinstance(value, str) or not UTC_STAMP.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_native_snapshot(payload):
    """Require the strict, currently representable C11 pmkb-notes-v1 subset."""
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_JSON:
        raise CheckpointError("snapshot_size")
    try:
        notebook = json.loads(payload.decode("utf-8"),
                              object_pairs_hook=_unique_pairs,
                              parse_constant=_bad_constant)
    except (ValueError, UnicodeError) as exc:
        raise CheckpointError("snapshot_json_invalid") from exc
    if not isinstance(notebook, dict) or set(notebook) != {"format", "notes"}:
        raise CheckpointError("invalid_notebook_fields")
    if notebook["format"] != "pmkb-notes-v1":
        raise CheckpointError("invalid_notebook_format")
    notes = notebook["notes"]
    if not isinstance(notes, list) or len(notes) > 100:
        raise CheckpointError("invalid_note_count")
    ids = set()
    for note in notes:
        if not isinstance(note, dict) or set(note) != {
            "id", "title", "text", "strokes", "typography", "created", "updated"
        }:
            raise CheckpointError("invalid_note_fields")
        note_id = note["id"]
        if not isinstance(note_id, str) or not NOTE_ID.fullmatch(note_id) or note_id == "pmkb_000000":
            raise CheckpointError("invalid_note_id")
        if note_id in ids:
            raise CheckpointError("duplicate_note_id")
        ids.add(note_id)
        title, body = note["title"], note["text"]
        if not isinstance(title, str) or not isinstance(body, str):
            raise CheckpointError("invalid_note_text")
        if "\x00" in title or "\x00" in body:
            raise CheckpointError("nul_in_native_text")
        if not any(ord(ch) not in TITLE_WHITESPACE for ch in title):
            raise CheckpointError("blank_title")
        if _units(title) > 100 or _units(body) > 120_000:
            raise CheckpointError("note_text_limit")
        if note["strokes"] != []:
            raise CheckpointError("sketches_not_supported_by_native_model")
        typography = note["typography"]
        if not isinstance(typography, dict) or set(typography) != {
            "font", "size", "lineHeight"
        } or typography["font"] != "mono" or type(typography["size"]) is not int or typography["size"] != 17 or type(typography["lineHeight"]) not in (int, float) or typography["lineHeight"] != 1.6:
            raise CheckpointError("native_typography_not_supported")
        if not _timestamp(note["created"]) or not _timestamp(note["updated"]):
            raise CheckpointError("invalid_note_timestamp")
    return notebook


def _host_directory(directory):
    root = Path(directory)
    try:
        st = root.lstat()
        resolved = root.resolve(strict=True)
        temporary = Path(tempfile.gettempdir()).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise CheckpointError("missing_host_directory") from exc
    if not stat.S_ISDIR(st.st_mode) or resolved == temporary or temporary not in resolved.parents:
        raise CheckpointError("not_a_host_test_directory")
    return root


def _unpack(data):
    if not data.startswith(MAGIC) or len(data) > MAX_FRAME:
        raise CheckpointError("invalid_checkpoint_header")
    body = data[len(MAGIC):]
    end = body.find(b"\n")
    if end < 0 or end > 74:
        raise CheckpointError("invalid_checkpoint_header")
    match = FRAME_HEADER.fullmatch(body[:end])
    if not match:
        raise CheckpointError("invalid_checkpoint_header")
    size = int(match.group(1))
    payload = body[end + 1:]
    if size != len(payload) or hashlib.sha256(payload).hexdigest().encode("ascii") != match.group(2):
        raise CheckpointError("checkpoint_sha_or_size_mismatch")
    validate_native_snapshot(payload)
    return payload


def _pack(payload):
    validate_native_snapshot(payload)
    digest = hashlib.sha256(payload).hexdigest().encode("ascii")
    return MAGIC + str(len(payload)).encode("ascii") + b" " + digest + b"\n" + payload


def _read_slot(path):
    try:
        st = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_FRAME:
        raise CheckpointError("unsafe_checkpoint_file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CheckpointError("checkpoint_open_refused") from exc
    with os.fdopen(fd, "rb") as stream:
        actual = os.fstat(stream.fileno())
        if not stat.S_ISREG(actual.st_mode) or actual.st_size > MAX_FRAME:
            raise CheckpointError("unsafe_checkpoint_file")
        if os.name == "posix" and (st.st_dev, st.st_ino) != (actual.st_dev, actual.st_ino):
            raise CheckpointError("checkpoint_changed_during_open")
        data = stream.read(MAX_FRAME + 1)
    return _unpack(data)


def _sync_directory(root):
    # Windows Python does not expose a portable directory fsync contract.
    if os.name != "posix":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(root, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _staged_file(root, data):
    fd, filename = tempfile.mkstemp(prefix=".pmkb-notes-", suffix=".stage", dir=root)
    path = Path(filename)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return path
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def load_checkpoint(directory):
    """Read-only: latest valid file, or previous if current missing/corrupt."""
    root = _host_directory(directory)
    failed_current = False
    for name in (CURRENT, PREVIOUS):
        try:
            content = _read_slot(root / name)
        except CheckpointError:
            if name == CURRENT:
                failed_current = True
                continue
            raise CheckpointError("both_checkpoints_unusable")
        if content is not None:
            return {
                "payload": content,
                "sha256": hashlib.sha256(content).hexdigest(),
                "source": "current" if name == CURRENT else "previous",
                "recovery_required": name == PREVIOUS,
                "physical_p3_verified": False,
                "native_import_verified": False,
            }
        if name == CURRENT:
            failed_current = True
    raise CheckpointError("no_recoverable_checkpoint" if not failed_current else "no_recoverable_checkpoint")


def save_checkpoint(directory, payload, *, expected_current_sha256=None,
                    before_publish=None):
    """Single-writer HOST TEST ONLY; never persists to a physical Kobo.

    An update requires the digest of the current payload (optimistic guard).
    This is not a transactional concurrency primitive, nor a P3 driver.
    """
    root = _host_directory(directory)
    frame = _pack(payload)
    current_path, previous_path = root / CURRENT, root / PREVIOUS
    current = _read_slot(current_path)
    previous = _read_slot(previous_path)
    if current is None and previous is not None:
        raise CheckpointError("recovery_required_before_next_save")
    digest = hashlib.sha256(current).hexdigest() if current is not None else None
    if expected_current_sha256 != digest:
        raise CheckpointError("stale_snapshot_or_missing_expected_digest")
    new_stage = old_stage = None
    try:
        new_stage = _staged_file(root, frame)
        if current is not None:
            old_stage = _staged_file(root, _pack(current))
        if before_publish is not None:
            before_publish()  # fault injection in tests, before any rename
        if _read_slot(current_path) != current or _read_slot(previous_path) != previous:
            raise CheckpointError("checkpoint_changed_before_publish")
        if old_stage is not None:
            os.replace(old_stage, previous_path)
            old_stage = None
            _sync_directory(root)
        os.replace(new_stage, current_path)
        new_stage = None
        _sync_directory(root)
        if _read_slot(current_path) != payload:
            raise CheckpointError("checkpoint_readback_failed")
        return {
            "status": "host_snapshot_verified",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "previous_retained": current is not None,
            "physical_p3_verified": False,
            "native_import_verified": False,
            "notes_ui_saved": False,
        }
    finally:
        for stage in (old_stage, new_stage):
            if stage is not None:
                stage.unlink(missing_ok=True)
