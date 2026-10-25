"""PMKB L06-B2d: synthetic-root-only removal of installed application code.

Never removes user data, touches device partitions, executes applications,
or claims crash-proof recovery. Local concurrent filesystem mutation is outside
this host-fixture contract.
"""

import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from archive_contract import MAX_FILE_BYTES, MAX_TOTAL_BYTES
from install_contract import _safe_directory, _test_root
from manifest_contract import MAX_MANIFEST_BYTES, ManifestError, _app_id, read_manifest

MAX_TREE_ENTRIES = 512


class UninstallError(ValueError):
    """Stable reason code; pending_path locates any incomplete cleanup."""

    def __init__(self, reason, *, pending_path=None):
        super().__init__(reason)
        self.pending_path = pending_path


def _is_link_or_junction(path):
    # Windows junction detection is supported where the host Python exposes it.
    junction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or (junction is not None and junction(path))


def _raise_walk_error(error):
    raise error


def _check_code_tree(app):
    """Refuse unsafe nested file types and unreasonable test-tree footprints."""
    count = 0
    total = 0
    try:
        for directory, dirs, files in os.walk(app, topdown=True,
                                              followlinks=False,
                                              onerror=_raise_walk_error):
            for name in dirs + files:
                path = Path(directory) / name
                if _is_link_or_junction(path):
                    raise UninstallError("unsafe_code_tree")
                item = path.lstat()
                if name in dirs:
                    if not stat.S_ISDIR(item.st_mode):
                        raise UninstallError("unsafe_code_tree")
                elif not stat.S_ISREG(item.st_mode):
                    raise UninstallError("unsafe_code_tree")
                else:
                    if item.st_size > MAX_FILE_BYTES:
                        raise UninstallError("code_tree_too_large")
                    total += item.st_size
                count += 1
                if count > MAX_TREE_ENTRIES or total > MAX_TOTAL_BYTES:
                    raise UninstallError("code_tree_too_large")
    except OSError as exc:
        raise UninstallError("code_tree_unreadable") from exc
    return count


def _validate_app_manifest(app, app_id):
    manifest_path = app / "manifest.json"
    try:
        if (_is_link_or_junction(manifest_path) or not manifest_path.is_file() or
                manifest_path.stat().st_size > MAX_MANIFEST_BYTES):
            raise UninstallError("installed_manifest_invalid")
        raw = manifest_path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        if type(obj) is not dict or type(obj.get("dependencies")) is not list:
            raise UninstallError("installed_manifest_invalid")
        # Dependencies were checked when installed. Validation here only checks
        # local manifest syntax and identity, not currently available apps.
        manifest = read_manifest(raw, available_dependencies=obj["dependencies"],
                                 allow_network=True)
    except (OSError, UnicodeError, ValueError, TypeError, ManifestError) as exc:
        if isinstance(exc, UninstallError):
            raise
        raise UninstallError("installed_manifest_invalid") from exc
    if manifest["id"] != app_id:
        raise UninstallError("installed_manifest_mismatch")


def uninstall_app(test_root, app_id):
    """Detach code atomically, then delete; never modify test_root/data.

    Rollback is guaranteed for failures BEFORE detach. Once detached, a purge
    error yields `cleanup_pending` with a quarantine path; it cannot promise
    restoration of files partially removed before the error.
    """
    if not _app_id(app_id):
        raise UninstallError("invalid_app_id")
    root = _test_root(test_root)
    apps, user_data = root / "apps", root / "data"
    _safe_directory(apps)
    _safe_directory(user_data)
    app = apps / app_id
    if not apps.is_dir() or not os.path.lexists(app):
        raise UninstallError("not_installed")
    if _is_link_or_junction(app) or not app.is_dir():
        raise UninstallError("unsafe_code_tree")
    entries = _check_code_tree(app)
    _validate_app_manifest(app, app_id)

    try:
        quarantine = Path(tempfile.mkdtemp(prefix=".pmkb-remove-", dir=str(apps)))
        quarantine.rmdir()  # reserve a collision-resistant, now-vacant name
    except OSError as exc:
        raise UninstallError("quarantine_prepare_failed") from exc

    try:
        os.rename(app, quarantine)  # atomic detach on the same filesystem
    except OSError as exc:
        raise UninstallError("detach_failed") from exc
    try:
        shutil.rmtree(quarantine)  # potentially non-atomic cleanup
    except OSError as exc:
        raise UninstallError("cleanup_pending", pending_path=quarantine) from exc
    return {"id": app_id, "code_removed": True,
            "user_data_untouched": True, "preflight_entries": entries}
