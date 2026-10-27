"""L08-J: bounded, read-only image-bytes vs exported rootfs evidence.

Reads ext4 inode extents from bytes supplied by a caller, not a device.
Accepts only conservative ext4 features and direct depth-zero extents.
Neither a digest supplied by the caller nor a content match authenticates P1.
"""
import hashlib
import re
import struct

from rootfs_evidence_contract import RootfsEvidenceError, verify_snapshot_evidence
from rootfs_snapshot_audit import (
    MAX_CANDIDATES, MAX_ENTRIES_PER_DIRECTORY, MAX_LIBRARY_BYTES,
    MAX_TOTAL_BYTES, SEARCH_DIRECTORIES,
)

MAX_IMAGE_BYTES = 320 * 1024 * 1024
MAX_DIRECTORY_BYTES = 128 * 1024
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)
_EXTENTS_FLAG = 0x00080000
_INCOMPAT_SUPPORTED = 0x0002 | 0x0040 | 0x0200
_RO_COMPAT_SUPPORTED = 0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0040


class Ext4ExportError(ValueError):
    """Stable rejection code: no physical operations or execution."""


def _u16(raw, pos):
    return struct.unpack_from("<H", raw, pos)[0]


def _u32(raw, pos):
    return struct.unpack_from("<I", raw, pos)[0]


class _Ext4View:
    """Minimal fail-closed reader for traditional 32-bit ext4 extents."""

    def __init__(self, image):
        self.image = memoryview(image)
        if not 2048 <= len(image) <= MAX_IMAGE_BYTES:
            raise Ext4ExportError("invalid_image_size")
        sb = 1024
        if _u16(image, sb + 0x38) != 0xEF53:
            raise Ext4ExportError("invalid_ext4_superblock")
        power = _u32(image, sb + 0x18)
        if power > 2:
            raise Ext4ExportError("unsupported_ext4_block_size")
        self.block_size = 1024 << power
        self.first_block = _u32(image, sb + 0x14)
        self.blocks = _u32(image, sb + 0x04)
        self.inodes = _u32(image, sb)
        self.blocks_per_group = _u32(image, sb + 0x20)
        self.inodes_per_group = _u32(image, sb + 0x28)
        self.inode_size = _u16(image, sb + 0x58)
        if (self.first_block != (1 if self.block_size == 1024 else 0) or
                self.blocks <= self.first_block + 8 or
                self.blocks > len(image) // self.block_size or
                self.inodes < 2 or self.blocks_per_group == 0 or
                self.inodes_per_group == 0 or
                not 128 <= self.inode_size <= self.block_size or
                self.inode_size % 4):
            raise Ext4ExportError("invalid_ext4_geometry")
        incompat = _u32(image, sb + 0x60)
        ro_compat = _u32(image, sb + 0x64)
        if ((incompat & ~_INCOMPAT_SUPPORTED) or
                (ro_compat & ~_RO_COMPAT_SUPPORTED) or
                not (incompat & 0x0040)):
            raise Ext4ExportError("unsupported_ext4_features")
        if not (_u16(image, sb + 0x3A) & 1):
            raise Ext4ExportError("unclean_ext4_image")
        self.groups = (self.inodes + self.inodes_per_group - 1) // self.inodes_per_group
        block_groups = (self.blocks - self.first_block +
                        self.blocks_per_group - 1) // self.blocks_per_group
        if not 1 <= self.groups <= 8192 or self.groups != block_groups:
            raise Ext4ExportError("invalid_ext4_geometry")

    def _inode(self, number):
        if type(number) is not int or not 1 <= number <= self.inodes:
            raise Ext4ExportError("invalid_ext4_inode")
        group, index = divmod(number - 1, self.inodes_per_group)
        gd = (self.first_block + 1) * self.block_size + group * 32
        if gd + 32 > self.blocks * self.block_size:
            raise Ext4ExportError("invalid_ext4_group_descriptor")
        table_block = _u32(self.image, gd + 8)
        pos = table_block * self.block_size + index * self.inode_size
        table_blocks = (self.inodes_per_group * self.inode_size +
                        self.block_size - 1) // self.block_size
        if (table_block == 0 or table_block >= self.blocks or
                table_blocks > self.blocks - table_block or
                pos + self.inode_size > self.blocks * self.block_size):
            raise Ext4ExportError("invalid_ext4_inode_table")
        mode = _u16(self.image, pos)
        length = _u32(self.image, pos + 4)
        if (mode & 0xF000) == 0x8000:
            length |= _u32(self.image, pos + 108) << 32
        flags = _u32(self.image, pos + 32)
        return mode, length, flags, self.image[pos + 40:pos + 100]

    def _contents(self, inode, *, cap):
        mode, length, flags, pointers = self._inode(inode)
        kind = mode & 0xF000
        if kind not in (0x4000, 0x8000, 0xA000):
            raise Ext4ExportError("unsupported_ext4_inode_type")
        if length > cap:
            raise Ext4ExportError("ext4_file_size_limit")
        if kind == 0xA000 and length <= 60 and not (flags & _EXTENTS_FLAG):
            return kind, bytes(pointers[:length])
        if length == 0:
            return kind, b""
        if not (flags & _EXTENTS_FLAG):
            raise Ext4ExportError("unsupported_ext4_block_map")
        if kind == 0x4000 and (flags & 0x1000):
            raise Ext4ExportError("unsupported_ext4_indexed_directory")
        magic, entries, maximum, depth, _gen = struct.unpack_from("<HHHHI", pointers, 0)
        if magic != 0xF30A or depth != 0 or entries > maximum or maximum > 4:
            raise Ext4ExportError("unsupported_ext4_extent_tree")
        logical_blocks = (length + self.block_size - 1) // self.block_size
        data = bytearray(logical_blocks * self.block_size)
        previous_end = 0
        physical_ranges = []
        for i in range(entries):
            logical, count, high, low = struct.unpack_from("<IHHI", pointers, 12 + i * 12)
            physical = (high << 32) | low
            if (count == 0 or count >= 0x8000 or
                    logical < previous_end or logical >= logical_blocks or
                    count > logical_blocks - logical or
                    physical == 0 or physical + count > self.blocks):
                raise Ext4ExportError("invalid_ext4_extent")
            if any(physical < stop and physical + count > start_block
                   for start_block, stop in physical_ranges):
                raise Ext4ExportError("overlapping_ext4_physical_extents")
            physical_ranges.append((physical, physical + count))
            start = physical * self.block_size
            dest = logical * self.block_size
            n = count * self.block_size
            data[dest:dest + n] = self.image[start:start + n]
            previous_end = logical + count
        return kind, bytes(data[:length])

    def _directory(self, number):
        kind, data = self._contents(number, cap=MAX_DIRECTORY_BYTES)
        if kind != 0x4000 or len(data) % self.block_size:
            raise Ext4ExportError("invalid_ext4_directory")
        entries = {}
        for base in range(0, len(data), self.block_size):
            cursor = base
            while cursor < base + self.block_size:
                if cursor + 8 > base + self.block_size:
                    raise Ext4ExportError("invalid_ext4_dirent")
                inode, record_length, name_length, _type = struct.unpack_from(
                    "<IHBB", data, cursor)
                if (record_length < 8 or record_length % 4 or
                        cursor + record_length > base + self.block_size or
                        name_length > record_length - 8):
                    raise Ext4ExportError("invalid_ext4_dirent")
                name = data[cursor + 8:cursor + 8 + name_length]
                if inode:
                    if (not 1 <= inode <= self.inodes or _type > 7 or
                            not name or b"\x00" in name or b"/" in name or
                            name in entries or
                            (name in (b".", b"..") and _type != 2)):
                        raise Ext4ExportError("invalid_ext4_dirent")
                    entries[name] = inode
                    if len(entries) > MAX_ENTRIES_PER_DIRECTORY:
                        raise Ext4ExportError("ext4_directory_entry_limit")
                cursor += record_length
        if entries.get(b".") != number or b".." not in entries:
            raise Ext4ExportError("invalid_ext4_dot_entries")
        return entries

    def _folder(self, path):
        number = 2
        for part in path:
            child = self._directory(number).get(part.encode("ascii"))
            if child is None:
                return None
            if (self._inode(child)[0] & 0xF000) != 0x4000:
                raise Ext4ExportError("non_directory_ext4_path")
            number = child
        return number

    def inventory(self):
        rows, dirs, total = {}, [], 0
        for parent in SEARCH_DIRECTORIES:
            number = self._folder(parent.split("/"))
            if number is None:
                dirs.append((parent, "missing_in_image"))
                continue
            dirs.append((parent, "scanned_nonrecursive"))
            for name, inode in self._directory(number).items():
                if b".so" not in name:
                    continue
                try:
                    readable = name.decode("ascii")
                except UnicodeDecodeError as exc:
                    raise Ext4ExportError("invalid_ext4_library_name") from exc
                if _NAME.fullmatch(readable) is None:
                    raise Ext4ExportError("invalid_ext4_library_name")
                key = parent + "/" + readable
                if key in rows or len(rows) >= MAX_CANDIDATES:
                    raise Ext4ExportError("ext4_library_count_limit")
                kind, data = self._contents(inode, cap=MAX_LIBRARY_BYTES)
                if kind == 0xA000:
                    if len(data) > 512:
                        raise Ext4ExportError("ext4_symlink_size_limit")
                    rows[key] = {"type": "symlink",
                                 "link_target": data.decode("utf-8", "surrogateescape")}
                elif kind == 0x8000:
                    total += len(data)
                    if total > MAX_TOTAL_BYTES:
                        raise Ext4ExportError("ext4_library_total_limit")
                    rows[key] = {"type": "regular", "size": len(data),
                                 "sha256": hashlib.sha256(data).hexdigest()}
                else:
                    raise Ext4ExportError("unsupported_ext4_library_type")
        return rows, tuple(dirs), total


def compare_ext4_image_to_snapshot(image_bytes, snapshot, *,
                                   expected_image_sha256,
                                   expected_audit_sha256=None,
                                   expected_source_id=None):
    """Match measured ext4 bytes to an export; caller SHA is not authentication."""
    if type(image_bytes) is not bytes or not 2048 <= len(image_bytes) <= MAX_IMAGE_BYTES:
        raise Ext4ExportError("invalid_image_size")
    if type(expected_image_sha256) is not str or _SHA.fullmatch(expected_image_sha256) is None:
        raise Ext4ExportError("invalid_expected_image_digest")
    measured = hashlib.sha256(image_bytes).hexdigest()
    if measured != expected_image_sha256:
        raise Ext4ExportError("expected_image_digest_mismatch")
    try:
        evidence = verify_snapshot_evidence(
            snapshot, expected_audit_sha256=expected_audit_sha256,
            expected_source_id=expected_source_id)
    except (RootfsEvidenceError, TypeError, KeyError, ValueError) as exc:
        raise Ext4ExportError("invalid_snapshot_evidence") from exc
    if evidence["declared_source_sha256"] != measured:
        raise Ext4ExportError("snapshot_source_image_digest_mismatch")
    view = _Ext4View(image_bytes)
    source, directories, bytes_read = view.inventory()
    exported = {row["path"]: row for row in snapshot["libraries"]}
    matched, mismatch, missing_image, missing_export = [], [], [], []
    for path in sorted(set(source) | set(exported)):
        a, b = source.get(path), exported.get(path)
        if a is None:
            missing_image.append(path)
        elif b is None:
            missing_export.append(path)
        elif a["type"] == "symlink":
            if b["state"] == "symlink_unresolved" and b["link_target"] == a["link_target"]:
                matched.append(path)
            else:
                mismatch.append(path)
        elif (b["state"] != "symlink_unresolved" and
              b["size"] == a["size"] and b["sha256"] == a["sha256"]):
            matched.append(path)
        else:
            mismatch.append(path)
    image_full = all(state == "scanned_nonrecursive" for _, state in directories)
    export_full = all(row["state"] == "scanned_nonrecursive"
                      for row in snapshot["directories"])
    if mismatch or missing_image or missing_export:
        verdict = "mismatch"
    elif not image_full or not export_full:
        verdict = "partial_scope"
    else:
        verdict = "scoped_image_export_match"
    return {
        "schema": "pmkb-ext4-export-provenance-v1",
        "scope": "image_bytes_vs_shallow_lib_usr_lib_export_only",
        "verdict": verdict,
        "image_sha256_measured": measured,
        "caller_image_digest_matched": True,
        "snapshot_observation_sha256": evidence["observation_digest"],
        "snapshot_source_id": evidence["source_id"],
        "image_block_size": view.block_size,
        "image_directories": directories,
        "image_libraries_inspected": len(source),
        "image_library_bytes_inspected": bytes_read,
        "matched": tuple(matched),
        "content_mismatch": tuple(mismatch),
        "missing_from_image": tuple(missing_image),
        "missing_from_export": tuple(missing_export),
        "image_to_export_link_verified_for_scanned_scope": verdict == "scoped_image_export_match",
        "filesystem_metadata_integrity_verified": False,
        "image_authenticated_as_kobo_p1": False,
        "source_provenance_authenticated": False,
        "whole_rootfs_verified": False,
        "hardware_verified": False,
        "runtime_compatible": False,
        "launchable": False,
    }
