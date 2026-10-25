"""PMKB Store L06-B1: bounded, read-only ZIP member preflight.

All input is bytes. No extraction, installation, filesystem writes, network,
execution, or trust in the target Kobo is implied by a successful inspection.
"""

from io import BytesIO
import stat
import unicodedata
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile

from manifest_contract import MAX_MANIFEST_BYTES, read_manifest

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 128
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 24 * 1024 * 1024
MAX_PATH_CHARS = 200
_RESERVED_NAMES = frozenset(("CON", "PRN", "AUX", "NUL")) | frozenset(
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
)


class ArchiveError(ValueError):
    """A rejected ZIP archive; the message is a stable reason code."""


def _check_path(filename, directory):
    path = filename[:-1] if directory else filename
    if (not path or len(filename) > MAX_PATH_CHARS or
            unicodedata.normalize("NFC", filename) != filename or
            filename.startswith("/") or
            any(c in '\\<>:"|?*' or unicodedata.category(c).startswith("C")
                for c in filename)):
        raise ArchiveError("unsafe_member_path")
    parts = path.split("/")
    if any(not part or part in (".", "..") or
           part.endswith((" ", ".")) or len(part) > 100 or
           part.split(".", 1)[0].upper() in _RESERVED_NAMES
           for part in parts):
        raise ArchiveError("unsafe_member_path")
    return path


def inspect_archive(data, *, available_dependencies=(), allow_network=False):
    """Inspect one in-memory ZIP candidate and return a manifest and member names.

    Does not authenticate archive contents or extract payloads. Caller must
    revalidate members while streaming and install transactionally in L06-B2.
    """
    if type(data) is not bytes or not data or len(data) > MAX_ARCHIVE_BYTES:
        raise ArchiveError("invalid_archive_size")
    try:
        with ZipFile(BytesIO(data), "r") as zf:
            infos = zf.infolist()
            if not infos or len(infos) > MAX_MEMBERS:
                raise ArchiveError("invalid_member_count")
            names = {}
            files = set()
            total = 0
            for item in infos:
                is_dir = item.is_dir()
                path = _check_path(item.filename, is_dir)
                key = path.casefold()
                if key in names:
                    raise ArchiveError("duplicate_member")
                names[key] = (path, is_dir)
                if item.flag_bits & 1:
                    raise ArchiveError("encrypted_member")
                if item.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                    raise ArchiveError("unsupported_compression")
                kind = stat.S_IFMT(item.external_attr >> 16) if item.create_system == 3 else 0
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ArchiveError("unsupported_member_type")
                if kind == stat.S_IFDIR and not is_dir:
                    raise ArchiveError("unsupported_member_type")
                if kind == stat.S_IFREG and is_dir:
                    raise ArchiveError("unsupported_member_type")
                if is_dir and item.file_size != 0:
                    raise ArchiveError("unsupported_member_type")
                if item.file_size > MAX_FILE_BYTES or item.file_size < 0:
                    raise ArchiveError("member_too_large")
                total += item.file_size
                if total > MAX_TOTAL_BYTES:
                    raise ArchiveError("archive_too_large")
                if not is_dir:
                    files.add(path)
            # Reject a regular file that is also another member's parent.
            for key, (path, _) in names.items():
                parts = key.split("/")
                for i in range(1, len(parts)):
                    parent = names.get("/".join(parts[:i]))
                    if parent is not None and not parent[1]:
                        raise ArchiveError("member_parent_is_file")
            if "manifest.json" not in files:
                raise ArchiveError("missing_manifest")
            manifest_info = zf.getinfo("manifest.json")
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise ArchiveError("manifest_too_large")
            with zf.open(manifest_info, "r") as source:
                manifest_bytes = source.read(MAX_MANIFEST_BYTES + 1)
            manifest = read_manifest(manifest_bytes,
                                     available_dependencies=available_dependencies,
                                     allow_network=allow_network)
            if manifest["entrypoint"] not in files:
                raise ArchiveError("missing_entrypoint")
            if zf.getinfo(manifest["entrypoint"]).file_size == 0:
                raise ArchiveError("empty_entrypoint")
            return {"manifest": manifest, "members": tuple(sorted(files)),
                    "declared_unpacked_bytes": total}
    except (BadZipFile, EOFError, OSError, RuntimeError, NotImplementedError) as exc:
        raise ArchiveError("invalid_archive") from exc
