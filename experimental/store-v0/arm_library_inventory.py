"""L08-D: compare ARM ELF DT_NEEDED names with a declared synthetic inventory.

Pure, deterministic, bounded, no filesystem/device/network access.
Name matches never prove file presence, ABI compatibility or launchability.
Real Kobo libraries MUST NOT be inferred from synthetic fixture records.
"""
import json
import re

from arm_elf_dependencies import inspect_arm_dependencies

INVENTORY_SCHEMA = "pmkb-elf-libraries-v1"
INVENTORY_SCOPE = "synthetic_fixture"
MAX_INVENTORY_BYTES = 16384
MAX_LIBRARIES = 128
_SONAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)
_FIELDS = frozenset(("schema", "scope", "coverage", "libraries"))


class LibraryInventoryError(ValueError):
    """Machine-readable rejection reason for malformed library metadata."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LibraryInventoryError("duplicate_inventory_key")
        result[key] = value
    return result


def _bad_constant(_value):
    raise LibraryInventoryError("invalid_inventory_json")


def _valid_name(value):
    return type(value) is str and _SONAME.fullmatch(value) is not None


def read_library_inventory(raw):
    """Accept only strictly marked, synthetic metadata. Never access paths."""
    if type(raw) is not bytes or not (1 <= len(raw) <= MAX_INVENTORY_BYTES):
        raise LibraryInventoryError("invalid_inventory_size")
    try:
        source = json.loads(raw.decode("utf-8"),
                            object_pairs_hook=_unique_pairs,
                            parse_constant=_bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LibraryInventoryError("invalid_inventory_json") from exc
    if type(source) is not dict or set(source) != _FIELDS:
        raise LibraryInventoryError("invalid_inventory_fields")
    if source["schema"] != INVENTORY_SCHEMA:
        raise LibraryInventoryError("invalid_inventory_schema")
    if source["scope"] != INVENTORY_SCOPE:
        raise LibraryInventoryError("unsupported_inventory_scope")
    coverage = source["coverage"]
    if type(coverage) is not str or coverage not in ("partial", "complete"):
        raise LibraryInventoryError("invalid_inventory_coverage")
    names = source["libraries"]
    if type(names) is not list or len(names) > MAX_LIBRARIES:
        raise LibraryInventoryError("invalid_inventory_libraries")
    if any(not _valid_name(name) for name in names):
        raise LibraryInventoryError("invalid_library_name")
    if len({name.casefold() for name in names}) != len(names):
        raise LibraryInventoryError("duplicate_library_name")
    return {"scope": INVENTORY_SCOPE, "coverage": coverage,
            "libraries": tuple(sorted(names))}


def assess_needed_libraries(needed, inventory):
    """Compare names only. A match never grants launch or install permission.

    An omitted name is 'not_observed' for partial inventories. For a
    declared-complete *synthetic* inventory it is 'not_in_fixture'.
    Neither result describes real Kobo filesystem contents.
    """
    if (type(needed) is not tuple or len(needed) > 32 or
            any(not _valid_name(name) for name in needed) or
            len(set(needed)) != len(needed)):
        raise LibraryInventoryError("invalid_needed_names")
    if (type(inventory) is not dict or
            set(inventory) != {"scope", "coverage", "libraries"} or
            inventory["scope"] != INVENTORY_SCOPE or
            inventory["coverage"] not in ("partial", "complete") or
            type(inventory["libraries"]) is not tuple or
            len(inventory["libraries"]) > MAX_LIBRARIES or
            any(not _valid_name(name) for name in inventory["libraries"]) or
            len(set(inventory["libraries"])) != len(inventory["libraries"])):
        raise LibraryInventoryError("invalid_inventory_source")
    declared = set(inventory["libraries"])
    matched = tuple(sorted(set(needed) & declared))
    unmatched = tuple(sorted(set(needed) - declared))
    complete = inventory["coverage"] == "complete"
    return {
        "scope": INVENTORY_SCOPE,
        "comparison": "soname_only_no_abi_proof",
        "coverage": inventory["coverage"],
        "needed": tuple(sorted(needed)),
        "matched_in_fixture": matched,
        "not_in_fixture": unmatched if complete else (),
        "not_observed": () if complete else unmatched,
        "launchable": False,
    }


def inspect_elf_with_inventory(elf_bytes, inventory_bytes):
    """End-to-end inert ELF/declared-library comparison."""
    elf = inspect_arm_dependencies(elf_bytes)
    inventory = read_library_inventory(inventory_bytes)
    return {"elf": elf,
            "libraries": assess_needed_libraries(elf["needed"], inventory),
            "launchable": False,
            "scope": "synthetic_comparison_only"}
