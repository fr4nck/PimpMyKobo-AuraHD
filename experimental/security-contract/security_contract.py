"""Pure security admission policy for SYNTHETIC PMKB V1 declarations.

This validates declared policy consistency, not configuration files, firmware,
runtime state, real network isolation or device security. No I/O of any kind.
"""
import json

FORMAT = "pmkb-security-declaration-v1"
MAX_JSON_CHARS = 131072
GATES = tuple("SEC-%02d" % i for i in range(1, 13))
GATE_STATES = ("claimed_met", "claimed_unmet", "unknown", "not_applicable")
KERNELS = ("historic-2.6.35.3", "6.12", "6.18", "unknown")
CONFIG_ENUMS = {
    "first_boot": ("preserved", "modified", "unknown"),
    "recovery": ("preserved", "modified", "unknown"),
    "rootfs": ("read_only", "read_write", "unknown"),
    "reader_privilege": ("unprivileged", "root", "unknown"),
    "untrusted_autorun": ("disabled", "enabled", "unknown"),
    "updates": ("none", "signed_offline", "signed_online", "unsigned", "unknown"),
    "kernel_branch": KERNELS,
    "kernel_maintenance": ("maintained", "unmaintained", "unknown"),
    "wifi": ("off", "on", "unknown"),
    "network_default": ("off", "on", "unknown"),
}
# Off-line permits an explicitly documented, absent update mechanism.
OPTIONAL_OFFLINE_GATE = "SEC-09"
CRITICAL_OFFLINE = frozenset(("SEC-01", "SEC-02", "SEC-03", "SEC-04",
                              "SEC-05", "SEC-06", "SEC-07", "SEC-08"))
SERVICE_NAMES = ("sshd", "telnetd", "httpd", "other")
SERVICE_SCOPES = ("loopback", "lan", "internet")
SERVICE_AUTHS = ("keys", "password", "none")


class DeclarationError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise DeclarationError(code)


def exact_fields(value, names, code):
    require(type(value) is dict and set(value) == set(names), code)


def enum_string(value, choices, code):
    require(type(value) is str and value in choices, code)


def empty_report():
    return {
        "status": "refused",
        "scope": "synthetic_declarations_only",
        "hardware_verified": False,
        "security_certified": False,
        "connected_ready": False,
        "deployment_allowed": False,
        "errors": [],
        "gates": [],
        "blockers": [],
        "limitations": ["no_authenticated_evidence", "no_runtime_observation",
                        "no_kernel_or_firmware_verification"],
    }


def analyze(data):
    """Classify contradictions and unknowns. Even coherent inputs NEVER pass a gate."""
    report = empty_report()
    try:
        exact_fields(data, ("format", "device", "profile", "provenance",
                            "configuration", "services", "gate_claims",
                            "attestations"), "invalid_schema")
        require(data["format"] == FORMAT, "invalid_format")
        require(data["device"] == "E606C0", "invalid_device")
        enum_string(data["profile"], ("OFFLINE", "CONNECTED"), "invalid_profile")
        require(type(data["provenance"]) is str and
                data["provenance"] == "synthetic", "invalid_provenance")
        profile = data["profile"]

        c = data["configuration"]
        exact_fields(c, CONFIG_ENUMS, "invalid_configuration")
        for name, choices in CONFIG_ENUMS.items():
            enum_string(c[name], choices, "invalid_configuration")

        services = data["services"]
        require(type(services) is list and len(services) <= 12, "invalid_services")
        active_names = set()
        for service in services:
            exact_fields(service, ("name", "scope", "authentication",
                                   "root_login"), "invalid_service")
            enum_string(service["name"], SERVICE_NAMES, "invalid_service")
            enum_string(service["scope"], SERVICE_SCOPES, "invalid_service")
            enum_string(service["authentication"], SERVICE_AUTHS, "invalid_service")
            require(type(service["root_login"]) is bool, "invalid_service")
            require(service["name"] not in active_names, "duplicate_service")
            active_names.add(service["name"])

        gate_claims = data["gate_claims"]
        exact_fields(gate_claims, GATES, "invalid_gates")
        for gate in GATES:
            enum_string(gate_claims[gate], GATE_STATES, "invalid_gates")
            if gate_claims[gate] == "not_applicable":
                require(profile == "OFFLINE" and gate == OPTIONAL_OFFLINE_GATE
                        and c["updates"] == "none", "invalid_gate_skip")

        attest = data["attestations"]
        exact_fields(attest, ("hardware_verified", "security_certified",
                              "connected_ready"), "invalid_attestations")
        require(all(type(value) is bool and value is False
                    for value in attest.values()), "unverified_attestation")

        faults = {}
        missing = {}
        def fail(gate, code):
            faults.setdefault(gate, []).append(code)
        def unknown(gate, code):
            missing.setdefault(gate, []).append(code)
        def is_unknown(name, gate):
            if c[name] == "unknown":
                unknown(gate, "unknown_" + name)

        if c["first_boot"] == "modified":
            fail("SEC-01", "first_boot_modified")
        is_unknown("first_boot", "SEC-01")
        if c["recovery"] == "modified":
            fail("SEC-01", "recovery_modified")
            fail("SEC-02", "recovery_modified")
        is_unknown("recovery", "SEC-02")

        if profile == "OFFLINE":
            if c["wifi"] == "on":
                fail("SEC-03", "wifi_enabled_offline")
            if services:
                fail("SEC-03", "active_service_offline")
        is_unknown("wifi", "SEC-03")
        if c["network_default"] == "on":
            fail("SEC-03", "network_enabled_by_default")
        is_unknown("network_default", "SEC-03")

        for service in services:
            if service["name"] == "telnetd":
                fail("SEC-03", "telnet_forbidden")
            if service["scope"] == "internet":
                fail("SEC-03", "internet_listener_forbidden")
            if service["name"] != "sshd":
                fail("SEC-04", "unapproved_service")
            if service["name"] == "sshd" and (
                service["authentication"] != "keys" or service["root_login"]
            ):
                fail("SEC-03", "insecure_ssh")
        if c["reader_privilege"] == "root":
            fail("SEC-05", "privileged_reader")
        is_unknown("reader_privilege", "SEC-05")
        if c["rootfs"] == "read_write":
            fail("SEC-06", "writable_rootfs")
        is_unknown("rootfs", "SEC-06")
        if c["untrusted_autorun"] == "enabled":
            fail("SEC-07", "untrusted_autorun_enabled")
        is_unknown("untrusted_autorun", "SEC-07")

        if c["updates"] == "unsigned":
            fail("SEC-09", "unsigned_updates")
        if profile == "CONNECTED":
            if c["updates"] == "none":
                fail("SEC-09", "no_update_path")
            is_unknown("updates", "SEC-09")
            if c["kernel_branch"] == "historic-2.6.35.3":
                fail("SEC-10", "obsolete_kernel")
            is_unknown("kernel_branch", "SEC-10")
            if c["kernel_maintenance"] == "unmaintained":
                fail("SEC-10", "unmaintained_kernel")
            is_unknown("kernel_maintenance", "SEC-10")
        else:
            if c["kernel_branch"] != "historic-2.6.35.3":
                unknown("SEC-10", "not_historical_offline_baseline")
            if c["kernel_maintenance"] == "unmaintained":
                report["limitations"].append("historic_kernel_unmaintained")

        for gate in GATES:
            state = gate_claims[gate]
            if state == "claimed_unmet":
                fail(gate, "declared_requirement_unmet")
            elif state == "unknown":
                unknown(gate, "requirement_not_established")

        # Claims are *never* evidence. Every 'claimed_met' remains UNKNOWN.
        for gate in GATES:
            state = gate_claims[gate]
            status = ("FAIL" if gate in faults else
                      "SKIP" if state == "not_applicable" else "UNKNOWN")
            report["gates"].append({"id": gate, "status": status,
                                    "declared": state,
                                    "reason": list(faults.get(gate, ())) +
                                    list(missing.get(gate, ()))})
        for gate in GATES:
            if gate in faults:
                report["blockers"].append({"gate": gate,
                                           "reasons": list(faults[gate])})
            elif gate in missing and (
                profile == "CONNECTED" or gate in CRITICAL_OFFLINE
            ):
                report["blockers"].append({"gate": gate,
                                           "reasons": list(missing[gate])})
        report["status"] = ("blocked" if report["blockers"] else
                            "declarations_consistent_unverified")
        report["profile"] = profile
        return report
    except DeclarationError as error:
        report["errors"] = [{"code": error.code}]
        return report


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise DeclarationError("invalid_json")


def analyze_json(text):
    """Parse a supplied string; no file paths, network, device I/O or subprocess."""
    if type(text) is not str or len(text) > MAX_JSON_CHARS:
        return {**empty_report(), "errors": [{"code": "invalid_json_text"}]}
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
    except DeclarationError as error:
        return {**empty_report(), "errors": [{"code": error.code}]}
    except (ValueError, RecursionError):
        return {**empty_report(), "errors": [{"code": "invalid_json"}]}
    return analyze(data)
