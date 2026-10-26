"""L06-C: bounded read-only installed-app catalogue in a synthetic test root.

An entry means "manifest present and consistent", not that code is trusted,
executable on the Kobo, network-authorized, or safe to launch.
"""

import os
from pathlib import Path
import stat

from install_contract import _test_root
from manifest_contract import MAX_MANIFEST_BYTES, ManifestError, _app_id, read_manifest
from pending_cleanup_contract import PENDING_PREFIX, pending_removals
from uninstall_contract import MAX_TREE_ENTRIES, _is_link_or_junction

MAX_CATALOG_APPS = 64


class CatalogError(ValueError):
    """Stable rejection reason for ambiguous or unreadable test catalogues."""


def _ordinary_directory(path):
    return (not _is_link_or_junction(path) and path.is_dir() and
            stat.S_ISDIR(path.lstat().st_mode))


def _entrypoint_present(app, name):
    current = app
    parts = name.split("/")
    try:
        for part in parts[:-1]:
            current = current / part
            if not _ordinary_directory(current):
                return False
        entry = current / parts[-1]
        return (not _is_link_or_junction(entry) and entry.is_file() and
                stat.S_ISREG(entry.lstat().st_mode) and entry.stat().st_size > 0)
    except OSError:
        return False


def read_catalog(test_root):
    """Return sorted installed metadata and pending quarantine names, no writes.

    All installed entries are checked before returning anything. Network flags
    remain declarations; this function cannot grant access or start a program.
    """
    root = _test_root(test_root)
    apps, user_data = root / "apps", root / "data"
    for directory in (apps, user_data):
        if _is_link_or_junction(directory) or (directory.exists() and
                not _ordinary_directory(directory)):
            raise CatalogError("unsafe_catalog_root")
    pending = pending_removals(root)
    if not apps.exists():
        return {"scope": "synthetic_read_only", "installed": (),
                "cleanup_pending": pending}

    names = []
    seen = set()
    try:
        with os.scandir(apps) as iterator:
            for count, item in enumerate(iterator, 1):
                if count > MAX_TREE_ENTRIES:
                    raise CatalogError("catalog_too_large")
                name = item.name
                if (item.is_symlink() or _is_link_or_junction(Path(item.path)) or
                        not item.is_dir(follow_symlinks=False)):
                    raise CatalogError("unsafe_catalog_entry")
                if name.startswith(PENDING_PREFIX):
                    if name not in pending:
                        raise CatalogError("catalog_changed")
                    continue
                if name.startswith(".pmkb-stage-"):
                    raise CatalogError("installation_incomplete")
                if not _app_id(name):
                    raise CatalogError("unexpected_catalog_entry")
                folded = name.casefold()
                if folded in seen:
                    raise CatalogError("ambiguous_app_id")
                seen.add(folded)
                names.append(name)
                if len(names) > MAX_CATALOG_APPS:
                    raise CatalogError("too_many_installed_apps")
    except OSError as exc:
        raise CatalogError("catalog_unreadable") from exc

    installed = []
    for app_id in sorted(names):
        app = apps / app_id
        manifest = app / "manifest.json"
        try:
            if (_is_link_or_junction(manifest) or not manifest.is_file() or
                    not stat.S_ISREG(manifest.lstat().st_mode) or
                    manifest.stat().st_size > MAX_MANIFEST_BYTES):
                raise CatalogError("invalid_installed_manifest")
            with manifest.open("rb") as source:
                raw = source.read(MAX_MANIFEST_BYTES + 1)
            document = read_manifest(raw, available_dependencies=names,
                                     allow_network=True)
        except (ManifestError, OSError) as exc:
            raise CatalogError("invalid_installed_manifest") from exc
        if document["id"] != app_id:
            raise CatalogError("installed_id_mismatch")
        if not _entrypoint_present(app, document["entrypoint"]):
            raise CatalogError("invalid_installed_entrypoint")
        installed.append({"id": app_id, "name": document["name"],
                          "version": document["version"],
                          "entrypoint": document["entrypoint"],
                          "network_declared": document["network"],
                          "state": "installed_unverified"})

    return {"scope": "synthetic_read_only", "installed": tuple(installed),
            "cleanup_pending": pending}
