"""PMKB L06-B2e: read-only inventory of incomplete synthetic removals.

This is NOT a cleanup utility. It inspects only a marked test root in the
host temporary directory and never alters application code or user data.
"""

import os

from install_contract import _safe_directory, _test_root
from uninstall_contract import MAX_TREE_ENTRIES, UninstallError, _is_link_or_junction

PENDING_PREFIX = ".pmkb-remove-"


def pending_removals(test_root):
    """Return sorted quarantine directory *names*, not paths or app identities.

    Any unexpected matching file/link refuses the complete inventory rather
    than implying that it can be safely deleted. This is a synthetic signal,
    not evidence of an application's state after power loss on the Kobo.
    """
    root = _test_root(test_root)
    apps, user_data = root / "apps", root / "data"
    if _is_link_or_junction(apps) or _is_link_or_junction(user_data):
        raise UninstallError("unsafe_install_root")
    _safe_directory(apps)
    _safe_directory(user_data)
    if not apps.exists():
        return ()
    names = []
    try:
        with os.scandir(apps) as entries:
            for count, entry in enumerate(entries, 1):
                if count > MAX_TREE_ENTRIES:
                    raise UninstallError("pending_inventory_too_large")
                if not entry.name.startswith(PENDING_PREFIX):
                    continue
                junction = getattr(os.path, "isjunction", None)
                if (entry.name == PENDING_PREFIX or entry.is_symlink() or
                        (junction is not None and junction(entry.path)) or
                        not entry.is_dir(follow_symlinks=False)):
                    raise UninstallError("unsafe_pending_entry")
                names.append(entry.name)
    except OSError as exc:
        raise UninstallError("pending_inventory_unreadable") from exc
    return tuple(sorted(names))
