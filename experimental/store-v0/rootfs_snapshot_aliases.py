"""PMKB L08-F: resolve library symlink aliases in existing snapshot metadata only.

No filesystem operations, no host path dereference, no execution or downloads.
An observed ARM ELF header does NOT establish ABI/runtime or Kobo compatibility.
"""
import re

from rootfs_snapshot_audit import RootfsSnapshotError, compare_needed_to_snapshot

MAX_ALIAS_HOPS = 8
MAX_SNAPSHOT_RECORDS = 512
MAX_LINK_LENGTH = 512
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._+@-]{0,127}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_STATES = frozenset(("symlink_unresolved", "arm_eabi5_shared_header",
                     "arm_eabi5_not_shared_object", "elf_identity_unverified"))


class RootfsAliasError(ValueError):
    """Stable refusal reason for malformed or untrusted snapshot metadata."""


def _index(snapshot):
    if (type(snapshot) is not dict or
            snapshot.get("schema") != "pmkb-rootfs-snapshot-audit-v1" or
            snapshot.get("scope") != "extracted_directory_observation_only" or
            snapshot.get("hardware_verified") is not False or
            snapshot.get("launchable") is not False or
            type(snapshot.get("provenance")) is not dict or
            snapshot["provenance"].get("source_hash_verified") is not False or
            type(snapshot.get("libraries")) is not tuple or
            len(snapshot["libraries"]) > MAX_SNAPSHOT_RECORDS):
        raise RootfsAliasError("invalid_snapshot_report")
    indexed = {}
    for rec in snapshot["libraries"]:
        if type(rec) is not dict:
            raise RootfsAliasError("invalid_snapshot_entry")
        path, name, state = (rec.get("path"), rec.get("soname_candidate"),
                             rec.get("state"))
        if (type(path) is not str or type(name) is not str or
                _NAME.fullmatch(name) is None or
                path not in ("lib/" + name, "usr/lib/" + name) or
                state not in _STATES or path in indexed):
            raise RootfsAliasError("invalid_snapshot_entry")
        if state == "symlink_unresolved":
            if (type(rec.get("link_target")) is not str or
                    len(rec["link_target"]) > MAX_LINK_LENGTH):
                raise RootfsAliasError("invalid_snapshot_entry")
        elif state == "arm_eabi5_shared_header":
            identity = rec.get("identity")
            sha = rec.get("sha256")
            if (type(identity) is not dict or
                    identity.get("machine") != "EM_ARM" or
                    identity.get("arm_eabi") != 5 or
                    identity.get("type") != "ET_DYN" or
                    identity.get("launchable") is not False or
                    type(sha) is not str or _SHA.fullmatch(sha) is None):
                raise RootfsAliasError("invalid_snapshot_entry")
        indexed[path] = rec
    return indexed


def _link_destination(origin, target):
    """Interpret links in snapshot-root POSIX namespace, never on host."""
    if (not target or len(target) > MAX_LINK_LENGTH or
            "\x00" in target or "\\" in target or
            target.startswith("//")):
        return None
    components = [] if target.startswith("/") else origin.split("/")[:-1]
    for part in target.lstrip("/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not components:
                return None
            components.pop()
        elif _NAME.fullmatch(part) is not None:
            components.append(part)
        else:
            return None
    return "/".join(components)


def resolve_snapshot_aliases(needed, snapshot):
    """Compare DT_NEEDED names with a read-only, pre-scanned rootfs inventory.

    All resolution is IN MEMORY. 'resolved' means an observed ELF header
    with the right ARM identity, not an actual runtime dependency check.
    """
    try:
        baseline = compare_needed_to_snapshot(needed, snapshot)
    except (RootfsSnapshotError, TypeError, AttributeError) as exc:
        raise RootfsAliasError("invalid_snapshot_or_needed") from exc
    indexed = _index(snapshot)
    results = []
    for item in baseline["findings"]:
        name = item["needed"]
        candidates = [x for x in ("lib/" + name, "usr/lib/" + name)
                      if x in indexed]
        state, final_path, digest, chain = None, None, None, []
        if len(candidates) > 1:
            state = "ambiguous_export_name"
            chain = list(candidates)
        elif not candidates:
            state = "not_observed_in_scanned_directories"
        else:
            current = candidates[0]
            seen = set()
            hops = 0
            while True:
                chain.append(current)
                record = indexed.get(current)
                if record is None:
                    state = ("alias_target_not_scanned"
                             if not (current.startswith("lib/") or
                                     current.startswith("usr/lib/"))
                             else "alias_target_not_observed")
                    break
                if record["state"] != "symlink_unresolved":
                    if record["state"] == "arm_eabi5_shared_header":
                        state = ("alias_to_arm_header_observed_only"
                                 if hops else "direct_arm_header_observed_only")
                        final_path = current
                        digest = record["sha256"]
                    else:
                        state = "nonmatching_library_header"
                    break
                if current in seen:
                    state = "alias_cycle"
                    break
                if hops == MAX_ALIAS_HOPS:
                    state = "alias_hop_limit"
                    break
                seen.add(current)
                target = _link_destination(current, record["link_target"])
                if target is None:
                    state = "unsafe_alias_target"
                    break
                current = target
                hops += 1
        results.append({
            "needed": name, "state": state, "observed_path_chain": tuple(chain),
            "observed_target": final_path, "observed_sha256": digest,
            "launchable": False, "hardware_verified": False,
        })
    return {
        "scope": "snapshot_symlink_metadata_only",
        "findings": tuple(results), "alias_hop_limit": MAX_ALIAS_HOPS,
        "source_hash_verified": False,
        "runtime_compatible": False,
        "hardware_verified": False,
        "launchable": False,
    }
