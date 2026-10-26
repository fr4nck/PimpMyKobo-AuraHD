"""L06-D1: bounded, inert snapshot for a future PMKB-UI Store view.

No UI, app launching, network, background daemon, installation or writes.
The only filesystem access in snapshot_store_view is read_catalog(test_root).
"""

import json

from catalog_contract import read_catalog

SCHEMA = "pmkb-store-view-v1"
MAX_VIEW_BYTES = 32768
MAX_VIEW_APPS = 64
MAX_PENDING = 512
_FIELDS = frozenset(("id", "name", "version", "entrypoint",
                     "network_declared", "state"))


class StoreViewError(ValueError):
    """Invalid input catalogue or oversized read-only UI snapshot."""


def encode_store_view(catalog):
    """Convert already-validated local metadata to display-only UTF-8 JSON.

    No entrypoint is serialized: even a future native client must not infer
    executable permissions from this snapshot. Names are labels, not HTML.
    """
    if type(catalog) is not dict or catalog.get("scope") != "synthetic_read_only":
        raise StoreViewError("invalid_view_source")
    entries = catalog.get("installed")
    pending = catalog.get("cleanup_pending")
    if (type(entries) not in (tuple, list) or len(entries) > MAX_VIEW_APPS or
            type(pending) not in (tuple, list) or len(pending) > MAX_PENDING):
        raise StoreViewError("invalid_view_source")
    if (any(type(item) is not str or not item.startswith(".pmkb-remove-") or
            len(item) > 200 or "/" in item or "\\" in item for item in pending) or
            len(set(pending)) != len(pending)):
        raise StoreViewError("invalid_view_source")
    rows = []
    seen = set()
    for item in entries:
        if type(item) is not dict or set(item) != _FIELDS:
            raise StoreViewError("invalid_view_source")
        app_id = item["id"]
        name = item["name"]
        version = item["version"]
        if (type(app_id) is not str or not (3 <= len(app_id) <= 120) or
                type(name) is not str or not (1 <= len(name) <= 80) or
                type(version) is not str or not (1 <= len(version) <= 24) or
                type(item["entrypoint"]) is not str or
                type(item["network_declared"]) is not bool or
                item["state"] != "installed_unverified" or
                app_id.casefold() in seen):
            raise StoreViewError("invalid_view_source")
        seen.add(app_id.casefold())
        rows.append({"id": app_id, "label": name, "version": version,
                     "network_declared": item["network_declared"],
                     "state": "installed_unverified", "launchable": False})
    rows.sort(key=lambda row: row["id"])
    output = {"schema": SCHEMA, "scope": "synthetic_read_only",
              "items": rows, "cleanup_pending_count": len(pending)}
    # ASCII wire avoids codec and terminal ambiguity; JSON decoding restores UTF-8.
    data = json.dumps(output, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")
    if len(data) > MAX_VIEW_BYTES:
        raise StoreViewError("view_too_large")
    return data


def snapshot_store_view(test_root):
    """Read a marked synthetic root once, then produce an inert view snapshot."""
    return encode_store_view(read_catalog(test_root))
