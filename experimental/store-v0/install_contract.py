"""PMKB L06-B2c: test-root-only, transactional extraction of .pmkb ZIP bytes.

Not a Kobo installer. No execution, network, persistent app service or
modification of physical media is provided by this module.
"""

import hashlib
from io import BytesIO
import os
from pathlib import Path
import shutil
import tempfile
from zipfile import BadZipFile, ZipFile
import zlib

from archive_contract import (MAX_FILE_BYTES, MAX_TOTAL_BYTES,
                              inspect_archive)

MARKER_NAME = ".pmkb-synthetic-root"
MARKER_CONTENT = b"PMKB-STORE-SYNTHETIC-ROOT-V1\n"
CHUNK_BYTES = 65536


class InstallError(ValueError):
    """Refusal or failed extraction; str(error) is a stable reason code."""


def _test_root(path):
    """Require an already-created, marked directory under the OS temp root."""
    try:
        root = Path(path)
        tmp = Path(tempfile.gettempdir()).resolve()
        real = root.resolve()
        if (root.is_symlink() or not root.is_dir() or
                real == tmp or not real.is_relative_to(tmp)):
            raise InstallError("test_root_required")
        marker = root / MARKER_NAME
        if (marker.is_symlink() or not marker.is_file() or
                marker.stat().st_size != len(MARKER_CONTENT) or
                marker.read_bytes() != MARKER_CONTENT):
            raise InstallError("test_root_required")
    except (TypeError, OSError, ValueError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError("test_root_required") from exc
    return root


def _safe_directory(path):
    # Never follow a pre-existing apps or data symlink.
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError("unsafe_install_root")


def install_archive(data, test_root, *, available_dependencies=(),
                    allow_network=False):
    """Install code at test_root/apps/APP_ID; never write to test_root/data.

    Requires a marked OS-temp directory. Returns an in-memory SHA256 inventory.
    A fresh staging directory is populated and published by a single rename.
    This does not permit concurrent untrusted filesystem mutation or upgrades.
    """
    root = _test_root(test_root)
    inspection = inspect_archive(data,
                                 available_dependencies=available_dependencies,
                                 allow_network=allow_network)
    app_id = inspection["manifest"]["id"]
    apps, user_data = root / "apps", root / "data"
    _safe_directory(apps)
    _safe_directory(user_data)
    final = apps / app_id
    if os.path.lexists(final):
        raise InstallError("already_installed")
    apps.mkdir(mode=0o700, exist_ok=True)
    _safe_directory(apps)

    stage = Path(tempfile.mkdtemp(prefix=".pmkb-stage-", dir=str(apps)))
    hashes = {}
    total = 0
    try:
        with ZipFile(BytesIO(data), "r") as archive:
            for member in archive.infolist():
                if member.orig_filename != member.filename:
                    raise InstallError("archive_changed")
                if member.is_dir():
                    continue  # implicit file parents are created when needed
                name = member.orig_filename
                if name not in inspection["members"]:
                    raise InstallError("archive_changed")
                destination = stage.joinpath(*name.split("/"))
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                digest = hashlib.sha256()
                actual = 0
                with archive.open(member, "r") as source, destination.open("xb") as output:
                    while True:
                        chunk = source.read(CHUNK_BYTES)
                        if not chunk:
                            break  # ZIP stream checks CRC when fully read
                        actual += len(chunk)
                        total += len(chunk)
                        if actual > member.file_size or actual > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                            raise InstallError("payload_too_large")
                        output.write(chunk)
                        digest.update(chunk)
                if actual != member.file_size:
                    raise InstallError("payload_size_mismatch")
                hashes[name] = digest.hexdigest()
        if (total != inspection["declared_unpacked_bytes"] or
                tuple(sorted(hashes)) != inspection["members"]):
            raise InstallError("payload_size_mismatch")
        if os.path.lexists(final):
            raise InstallError("already_installed")
        os.rename(stage, final)  # same filesystem: publish only a complete tree
        return {"id": app_id, "version": inspection["manifest"]["version"],
                "files": hashes, "total_bytes": total,
                "code_directory": final}
    except (BadZipFile, EOFError, OSError, RuntimeError, zlib.error) as exc:
        raise InstallError("payload_io_or_crc") from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)
