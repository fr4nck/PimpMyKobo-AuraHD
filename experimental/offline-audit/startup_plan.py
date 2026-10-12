"""Inert startup plan and synthetic trace; no hardware executor or I/O."""
from sysfs_snapshot import validate_snapshot_json

STEPS = (
    ("identify_devices", "Describe identities from synthetic metadata.", (), ()),
    ("prepare_nodes", "Describe node preparation after identity resolution.",
     ("device_bindings_and_types",), ("device_wait_policy", "permissions_policy")),
    ("prepare_framebuffer", "Describe framebuffer preparation without choosing a mode.",
     ("framebuffer_geometry", "panel_ready"), ("framebuffer_preparation",)),
    ("prepare_profile", "Describe a temporary profile independent of Nickel.",
     ("p3_read_only", "temporary_profile", "nickel_independent_settings"), ()),
    ("consider_reader_launch", "Describe the possibility of direct reader launch.",
     ("runtime_and_environment", "offline_launch_check"),
     ("diagnostic_policy", "reader_exit_policy", "watchdog_policy",
      "physical_trial_contract")),
)
STEP_IDS = tuple(step[0] for step in STEPS)
PRECONDITIONS = tuple(key for step in STEPS for key in step[2])
DECISIONS = tuple(key for step in STEPS for key in step[3])
HARDWARE_EVIDENCE = (
    "boot_chain_and_snapshot_authenticity",
    "device_driver_bindings_and_input_capabilities",
    "framebuffer_geometry_and_actual_refresh",
    "touch_coordinates_and_response",
    "mcu_probe_and_actual_frontlight",
    "watchdog_power_usb_and_radio_state",
)


def default_scenario():
    """No actual decision or hardware prerequisite is inferred."""
    return {
        "schema_version": 1,
        "scope": "synthetic_scenario",
        "preconditions": {key: "unknown" for key in PRECONDITIONS},
        "decisions": {key: "unresolved" for key in DECISIONS},
        "failure_at": None,
    }


def _valid_scenario(scenario):
    if type(scenario) is not dict or set(scenario) != {
        "schema_version", "scope", "preconditions", "decisions", "failure_at"
    }:
        return False
    if type(scenario["schema_version"]) is not int or scenario["schema_version"] != 1:
        return False
    if type(scenario["scope"]) is not str or scenario["scope"] != "synthetic_scenario":
        return False
    preconditions, decisions = scenario["preconditions"], scenario["decisions"]
    if type(preconditions) is not dict or set(preconditions) != set(PRECONDITIONS):
        return False
    if type(decisions) is not dict or set(decisions) != set(DECISIONS):
        return False
    if not all(type(value) is str and value in {
        "unknown", "assumed_satisfied", "assumed_failed"
    } for value in preconditions.values()):
        return False
    if not all(type(value) is str and value in {
        "unresolved", "assumed_resolved"
    } for value in decisions.values()):
        return False
    failure = scenario["failure_at"]
    return failure is None or (type(failure) is str and failure in STEP_IDS)


def plan_startup(snapshot_json, scenario=None):
    """Return descriptions and an optional assumed trace, never instructions.

    Assumptions can exercise all model branches. They cannot resolve a real
    decision, establish hardware evidence or authorize reader launch.
    """
    if scenario is None:
        scenario = default_scenario()
    report = {
        "schema_version": 1,
        "tool": "pmkb-inert-startup-plan",
        "scope": "synthetic_planning_only",
        "status": "refused",
        "plan_executable": False,
        "launch_performed": False,
        "hardware_verified": False,
        "boot_qualified": False,
        "physical_restore_eligible": False,
        "snapshot_coherent": False,
        "checked_preconditions": [],
        "scenario_preconditions": {},
        "scenario_decisions": {},
        "real_decisions_unresolved": list(DECISIONS),
        "hardware_evidence_missing": list(HARDWARE_EVIDENCE),
        "plan": [],
        "trace": [],
        "not_reached": list(STEP_IDS),
        "blockers": [],
        "errors": [],
    }
    if not _valid_scenario(scenario):
        report["errors"] = [{"code": "invalid_scenario"}]
        return report

    snapshot = validate_snapshot_json(snapshot_json)
    report["snapshot_coherent"] = snapshot["snapshot_coherent"]
    report["scenario_preconditions"] = dict(scenario["preconditions"])
    report["scenario_decisions"] = dict(scenario["decisions"])
    if not snapshot["snapshot_coherent"]:
        report["errors"] = list(snapshot["errors"])
        report["trace"] = [{"step": "identify_devices",
                            "outcome": "snapshot_refused", "performed": False}]
        report["not_reached"] = list(STEP_IDS[1:])
        return report

    report["checked_preconditions"] = [
        {"name": "snapshot_metadata", "state": "checked",
         "scope": "synthetic_metadata_only"},
    ]
    identity_passed = False
    for index, (step, description, preconditions, decisions) in enumerate(STEPS):
        blockers = [
            {"kind": "precondition", "name": key,
             "state": scenario["preconditions"][key]}
            for key in preconditions
            if scenario["preconditions"][key] != "assumed_satisfied"
        ] + [
            {"kind": "decision", "name": key,
             "state": scenario["decisions"][key]}
            for key in decisions
            if scenario["decisions"][key] != "assumed_resolved"
        ]
        if step == "prepare_nodes" and not identity_passed:
            blockers.append({"kind": "dependency", "name": "identify_devices",
                             "state": "not_passed"})
        report["not_reached"] = list(STEP_IDS[index + 1:])
        if blockers:
            report["status"] = "blocked"
            report["blockers"] = blockers
            report["trace"].append({"step": step, "outcome": "blocked",
                                    "performed": False})
            return report

        entry = {
            "step": step,
            "description": description,
            "depends_on": list(STEP_IDS[index - 1:index]) if index else [],
            "required_preconditions": list(preconditions),
            "required_decisions": list(decisions),
            "performed": False,
        }
        if step == "prepare_nodes":
            entry["synthetic_identities"] = snapshot["identified"]
        report["plan"].append(entry)
        if scenario["failure_at"] == step:
            report["status"] = "simulated_failure"
            report["trace"].append({"step": step, "outcome": "simulated_failure",
                                    "performed": False})
            return report

        report["trace"].append({
            "step": step,
            "outcome": "metadata_checked" if index == 0 else "assumed_pass",
            "performed": False,
        })
        if step == "identify_devices":
            identity_passed = True

    report["status"] = "simulation_complete"
    return report
