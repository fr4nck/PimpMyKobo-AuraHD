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
    "reader_privilege": ("unprivileged", "root", "root_transitional", "unknown"),
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

# Declarative opt-ins: NOT authenticated authorizations or runtime controls.
# Omission preserves the strict V1 defaults.
OPT_INS = frozenset((
    "offline_wifi", "offline_service", "telnet", "ssh_password", "ssh_root",
    "extra_service", "public_listener", "reader_root", "writable_rootfs",
    "untrusted_autorun", "unsigned_updates", "connected_no_updates",
    "legacy_connected", "unmaintained_kernel",
))
RISK_TEXT = {
    "offline_wifi_enabled": "La radio peut consommer de l'énergie et exposer l'ancien noyau.",
    "offline_service_enabled": "Un service réseau augmente la surface d'attaque de l'usage hors ligne.",
    "telnet_plaintext": "Telnet ne chiffre ni les commandes ni les identifiants.",
    "ssh_password_enabled": "Les mots de passe SSH peuvent être devinés ou réutilisés.",
    "ssh_root_login": "Une connexion SSH root expose directement les privilèges administrateur.",
    "nonstandard_service": "Ce service n'a pas été audité pour PMKB.",
    "internet_listener": "Une écoute publique expose l'appareil à des hôtes inconnus.",
    "reader_root": "Un document ou plugin malveillant peut agir avec les droits root.",
    "writable_rootfs": "Une racine modifiable augmente les risques de corruption et de persistance.",
    "untrusted_autorun": "Exécuter automatiquement un fichier importé peut lancer du code hostile.",
    "unsigned_updates": "Une mise à jour non authentifiée peut installer du code compromis.",
    "no_update_path": "Un système connecté sans mises à jour accumule les vulnérabilités.",
    "obsolete_kernel": "Le noyau historique ne reçoit plus de correctifs de sécurité amont.",
    "unmaintained_kernel": "Le noyau sans maintenance ne reçoit pas de correctifs garantis.",
}


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
        "declared_opt_ins": [],
        "risk_advisories": [],
        "gates": [],
        "blockers": [],
        "limitations": ["no_authenticated_evidence", "no_runtime_observation",
                        "no_kernel_or_firmware_verification"],
    }


def analyze(data):
    """Classify contradictions and unknowns. Even coherent inputs NEVER pass a gate."""
    report = empty_report()
    try:
        required = {"format", "device", "profile", "provenance",
                    "configuration", "services", "gate_claims", "attestations"}
        require(type(data) is dict and
                set(data) in (required, required | {"opt_ins"}), "invalid_schema")
        choices = data.get("opt_ins", [])
        require(type(choices) is list and len(choices) <= len(OPT_INS) and
                all(type(k) is str and k in OPT_INS for k in choices) and
                len(set(choices)) == len(choices), "invalid_opt_ins")
        opted = set(choices)
        report["declared_opt_ins"] = sorted(opted)
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
        accepted = {}
        def fail(gate, code):
            faults.setdefault(gate, []).append(code)
        def risk(gate, code, option):
            if option not in opted:
                fail(gate, code)
                return
            accepted.setdefault(gate, []).append(code)
            report["risk_advisories"].append({
                "gate": gate, "code": code, "opt_in": option,
                "level": "high" if code in (
                    "telnet_plaintext", "internet_listener", "unsigned_updates",
                    "untrusted_autorun", "obsolete_kernel") else "elevated",
                "message": RISK_TEXT[code],
                "user_authorization_verified": False,
            })
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
                risk("SEC-03", "offline_wifi_enabled", "offline_wifi")
            if services:
                risk("SEC-03", "offline_service_enabled", "offline_service")
        is_unknown("wifi", "SEC-03")
        if c["network_default"] == "on":
            fail("SEC-03", "network_enabled_by_default")
        is_unknown("network_default", "SEC-03")

        for service in services:
            if service["name"] == "telnetd":
                risk("SEC-03", "telnet_plaintext", "telnet")
            if service["scope"] == "internet":
                risk("SEC-03", "internet_listener", "public_listener")
            if service["name"] not in ("sshd", "telnetd"):
                risk("SEC-04", "nonstandard_service", "extra_service")
            if service["name"] == "sshd":
                if service["authentication"] != "keys":
                    risk("SEC-03", "ssh_password_enabled", "ssh_password")
                if service["root_login"]:
                    risk("SEC-03", "ssh_root_login", "ssh_root")
        if c["reader_privilege"] == "root":
            risk("SEC-05", "reader_root", "reader_root")
        elif c["reader_privilege"] == "root_transitional":
            if "reader_root" in opted:
                risk("SEC-05", "reader_root", "reader_root")
            elif profile == "CONNECTED":
                fail("SEC-05", "root_reader_connected")
            else:
                unknown("SEC-05", "temporary_root_hardware_necessity_unverified")
                report["limitations"].append("offline_root_exception_requires_review")
        is_unknown("reader_privilege", "SEC-05")
        if c["rootfs"] == "read_write":
            risk("SEC-06", "writable_rootfs", "writable_rootfs")
        is_unknown("rootfs", "SEC-06")
        if c["untrusted_autorun"] == "enabled":
            risk("SEC-07", "untrusted_autorun", "untrusted_autorun")
        is_unknown("untrusted_autorun", "SEC-07")

        if c["updates"] == "unsigned":
            risk("SEC-09", "unsigned_updates", "unsigned_updates")
        if profile == "CONNECTED":
            if c["updates"] == "none":
                risk("SEC-09", "no_update_path", "connected_no_updates")
            is_unknown("updates", "SEC-09")
            if c["kernel_branch"] == "historic-2.6.35.3":
                risk("SEC-10", "obsolete_kernel", "legacy_connected")
            is_unknown("kernel_branch", "SEC-10")
            if c["kernel_maintenance"] == "unmaintained":
                risk("SEC-10", "unmaintained_kernel", "unmaintained_kernel")
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
                                    list(missing.get(gate, ())) +
                                    list(accepted.get(gate, ()))})
        for gate in GATES:
            if gate in faults:
                report["blockers"].append({"gate": gate,
                                           "reasons": list(faults[gate])})
            elif gate in missing and (
                profile == "CONNECTED" or gate in CRITICAL_OFFLINE
            ):
                report["blockers"].append({"gate": gate,
                                           "reasons": list(missing[gate])})
        report["status"] = (
            "blocked" if report["blockers"] else
            "choices_consistent_unverified" if report["risk_advisories"] else
            "declarations_consistent_unverified"
        )
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
