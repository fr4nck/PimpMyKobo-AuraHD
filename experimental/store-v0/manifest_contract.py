"""PMKB Store V0: pure validation of a tiny application manifest.

No archives are read, packages installed, commands run or network used here.
These checks are for a future Store and do not prove Kobo hardware support.
"""

import json
import re

MAX_MANIFEST_BYTES = 4096
TARGET = "dragon"
RUNTIME = "pmkb-ui-v0"
APP_ID = re.compile(r"[a-z][a-z0-9-]{0,30}(?:\.[a-z][a-z0-9-]{0,30})+")
VERSION = re.compile(r"(?:0|[1-9][0-9]{0,5})(?:\.(?:0|[1-9][0-9]{0,5})){2}")
ALLOWED = frozenset((
    "manifest_version", "id", "name", "version", "target", "runtime",
    "entrypoint", "dependencies", "network",
))


class ManifestError(ValueError):
    """Invalid or incompatible manifest; str(error) is a stable reason code."""


def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("duplicate_key")
        result[key] = value
    return result


def _invalid_constant(_):
    raise ManifestError("invalid_json")


def _app_id(value):
    return type(value) is str and len(value) <= 120 and APP_ID.fullmatch(value) is not None


def _safe_path(value):
    if type(value) is not str or len(value) > 160 or not value:
        return False
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    if "\\" in value or ":" in value or value.startswith("/"):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def read_manifest(data, *, available_dependencies=(), allow_network=False,
                  target=TARGET, runtime=RUNTIME):
    """Read a JSON manifest as bytes and check compatibility without I/O.

    Returns the validated document as a new dict. The caller must separately
    check archive members, symlinks, file hashes and installation policy.
    """
    if type(data) is not bytes or len(data) > MAX_MANIFEST_BYTES or not data:
        raise ManifestError("invalid_manifest_size")
    try:
        doc = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_unique,
                         parse_constant=_invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("invalid_json") from exc
    if type(doc) is not dict or set(doc) != ALLOWED:
        raise ManifestError("invalid_fields")
    if type(doc["manifest_version"]) is not int or doc["manifest_version"] != 1:
        raise ManifestError("unsupported_manifest_version")
    if not _app_id(doc["id"]):
        raise ManifestError("invalid_id")
    name = doc["name"]
    if (type(name) is not str or not name.strip() or len(name) > 80 or
            any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise ManifestError("invalid_name")
    if type(doc["version"]) is not str or not VERSION.fullmatch(doc["version"]):
        raise ManifestError("invalid_version")
    if doc["target"] != target or type(doc["target"]) is not str:
        raise ManifestError("unsupported_target")
    if doc["runtime"] != runtime or type(doc["runtime"]) is not str:
        raise ManifestError("unsupported_runtime")
    if not _safe_path(doc["entrypoint"]):
        raise ManifestError("invalid_entrypoint")
    deps = doc["dependencies"]
    if (type(deps) is not list or len(deps) > 16 or
            any(not _app_id(dep) for dep in deps) or len(set(deps)) != len(deps) or
            doc["id"] in deps):
        raise ManifestError("invalid_dependencies")
    if any(dep not in available_dependencies for dep in deps):
        raise ManifestError("missing_dependencies")
    if type(doc["network"]) is not bool:
        raise ManifestError("invalid_network_permission")
    if doc["network"] and allow_network is not True:
        raise ManifestError("network_not_granted")
    return dict(doc)
