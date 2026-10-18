"""Inert, frugal /dev access candidate for synthetic E606C0 snapshots.

Reuses the strict sysfs snapshot contract; never opens paths, makes nodes,
runs commands, alters permissions, changes user IDs, or boots anything.
This Python module is a HOST-ONLY development aid, not a Kobo runtime.
"""
import re

from sysfs_snapshot import validate_snapshot_json

STRATEGIES = ("root_transitional", "nonroot_candidate")
MISSING_EVIDENCE = (
    "snapshot_authenticity_and_completeness",
    "actual_uid_gid_and_group_membership",
    "device_node_modes_and_owner",
    "framebuffer_mmap_and_ioctl_as_nonroot",
    "zforce_event_read_and_coordinates_as_nonroot",
    "ntx_io_open_flags_ioctl_permissions_and_side_effects",
    "button_event_identity_and_input_permissions",
    "power_suspend_watchdog_and_other_driver_dependencies",
    "runtime_RAM_CPU_and_battery_impact",
)


def _report():
    return {
        "status": "refused",
        "scope": "synthetic_access_planning_only",
        "hardware_verified": False,
        "permission_applied": False,
        "reader_started": False,
        "boot_qualified": False,
        "security_certified": False,
        "deployable": False,
        "added_resident_processes_on_kobo": 0,
        "runtime_ram_delta_measured": False,
        "snapshot_coherent": False,
        "strategy": None,
        "candidates": [],
        "errors": [],
        "evidence_missing": list(MISSING_EVIDENCE),
    }


def plan_device_access(snapshot_json, strategy="nonroot_candidate"):
    """Provide candidate node policies from verified *synthetic metadata* only.

    Proposals are not chmod/chown/mknod recipes and cannot certify root dropping.
    A short immutable role allowlist avoids fabricating button/event identities.
    """
    result = _report()
    if type(strategy) is not str or strategy not in STRATEGIES:
        result["errors"] = [{"code": "invalid_strategy"}]
        return result
    result["strategy"] = strategy

    validated = validate_snapshot_json(snapshot_json)
    if validated["status"] != "coherent":
        result["errors"] = list(validated["errors"])
        return result
    result["snapshot_coherent"] = True
    found = validated["identified"]
    touch_name = found["touch"]["sysfs_path"].rsplit("/", 1)[-1]
    # Belt-and-braces: never synthesize an unsafe /dev path from metadata.
    if not re.fullmatch(r"event(?:0|[1-9][0-9]{0,3})", touch_name):
        result["errors"] = [{"code": "invalid_touch_identity"}]
        return result

    # "rw" is a hypothesis for MXCFB and ntx ioctl paths, not a tested open().
    # "r" only for input: Linux evdev normally needs reads, not device writes.
    candidates = (
        ("display", "/dev/fb0", found["framebuffer"]["dev"], "rw", "0660"),
        ("touch", "/dev/input/" + touch_name, found["touch"]["dev"], "r", "0640"),
        ("frontlight", "/dev/ntx_io", found["frontlight_interface"]["dev"],
         "rw", "0660"),
    )
    for role, path, dev, access, mode in candidates:
        entry = {
            "role": role,
            "path": path,
            "node_type": "character",
            "declared_major_minor": list(dev),
            "access_hypothesis": access,
            "mode_candidate": mode if strategy == "nonroot_candidate" else None,
            "group_candidate": "pmkb-hw" if strategy == "nonroot_candidate" else None,
            "applied": False,
        }
        result["candidates"].append(entry)
    if strategy == "root_transitional":
        result["evidence_missing"].append("risk_acceptance_for_privileged_reader")
    result["status"] = "candidate_unverified"
    return result
