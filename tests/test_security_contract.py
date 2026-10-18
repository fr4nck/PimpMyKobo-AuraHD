"""Security V1: synthetic-only policy consistency; no hardware, network or writes."""
import copy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "experimental/security-contract/security_contract.py"
SPEC = importlib.util.spec_from_file_location("pmkb_security_contract", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def sample(profile="OFFLINE"):
    connected = profile == "CONNECTED"
    gate_claims = dict.fromkeys(MOD.GATES, "claimed_met")
    if not connected:
        gate_claims["SEC-09"] = "not_applicable"
        gate_claims["SEC-10"] = "unknown"
        gate_claims["SEC-11"] = "unknown"
        gate_claims["SEC-12"] = "unknown"
    return {
        "format": MOD.FORMAT,
        "device": "E606C0",
        "profile": profile,
        "provenance": "synthetic",
        "configuration": {
            "first_boot": "preserved",
            "recovery": "preserved",
            "rootfs": "read_only",
            "reader_privilege": "unprivileged",
            "untrusted_autorun": "disabled",
            "updates": "signed_offline" if connected else "none",
            "kernel_branch": "6.18" if connected else "historic-2.6.35.3",
            "kernel_maintenance": "maintained" if connected else "unmaintained",
            "wifi": "off",
            "network_default": "off",
        },
        "services": [],
        "gate_claims": gate_claims,
        "attestations": {
            "hardware_verified": False, "security_certified": False,
            "connected_ready": False,
        },
    }


def gate(result, name):
    return next(g for g in result["gates"] if g["id"] == name)


class SecurityContractTests(unittest.TestCase):
    def test_synthetic_offline_policy_never_certifies_any_gate(self):
        data = sample()
        original = copy.deepcopy(data)
        result = MOD.analyze(data)
        self.assertEqual("declarations_consistent_unverified", result["status"])
        self.assertEqual(data, original)
        self.assertEqual("SKIP", gate(result, "SEC-09")["status"])
        self.assertTrue(all(g["status"] != "PASS" for g in result["gates"]))
        self.assertFalse(result["deployment_allowed"])
        self.assertFalse(result["security_certified"])
        self.assertFalse(result["hardware_verified"])

    def test_connected_synthetic_secure_claims_remain_unverified(self):
        data = sample("CONNECTED")
        data["services"] = [{"name": "sshd", "scope": "lan",
                             "authentication": "keys", "root_login": False}]
        result = MOD.analyze_json(json.dumps(data))
        self.assertEqual("declarations_consistent_unverified", result["status"])
        self.assertEqual("UNKNOWN", gate(result, "SEC-10")["status"])
        self.assertFalse(result["connected_ready"])
        self.assertFalse(result["deployment_allowed"])

    def test_offline_radio_and_network_exposure_are_refused(self):
        for mutate in (
            lambda d: d["configuration"].update(wifi="on"),
            lambda d: d["configuration"].update(network_default="on"),
            lambda d: d["services"].append({"name": "sshd", "scope": "lan",
                    "authentication": "keys", "root_login": False}),
        ):
            data = sample()
            mutate(data)
            result = MOD.analyze(data)
            self.assertEqual("blocked", result["status"])
            self.assertEqual("FAIL", gate(result, "SEC-03")["status"])

    def test_insecure_connected_services_rejected(self):
        for service in (
            {"name": "telnetd", "scope": "lan", "authentication": "none",
             "root_login": False},
            {"name": "sshd", "scope": "lan", "authentication": "password",
             "root_login": False},
            {"name": "sshd", "scope": "lan", "authentication": "keys",
             "root_login": True},
            {"name": "sshd", "scope": "internet", "authentication": "keys",
             "root_login": False},
            {"name": "httpd", "scope": "lan", "authentication": "keys",
             "root_login": False},
        ):
            with self.subTest(service=service):
                data = sample("CONNECTED")
                data["services"] = [service]
                result = MOD.analyze(data)
                self.assertEqual("blocked", result["status"])
                self.assertTrue(any(g["status"] == "FAIL" for g in result["gates"]))

    def test_connected_requires_maintained_kernel_and_authenticated_updates(self):
        for field, value, expected_gate in (
            ("kernel_branch", "historic-2.6.35.3", "SEC-10"),
            ("kernel_maintenance", "unmaintained", "SEC-10"),
            ("updates", "none", "SEC-09"),
            ("updates", "unsigned", "SEC-09"),
        ):
            data = sample("CONNECTED")
            data["configuration"][field] = value
            result = MOD.analyze(data)
            self.assertEqual("blocked", result["status"])
            self.assertEqual("FAIL", gate(result, expected_gate)["status"])

    def test_privileges_recovery_autorun_and_rootfs(self):
        for field, bad, expected_gate in (
            ("first_boot", "modified", "SEC-01"),
            ("recovery", "modified", "SEC-02"),
            ("reader_privilege", "root", "SEC-05"),
            ("rootfs", "read_write", "SEC-06"),
            ("untrusted_autorun", "enabled", "SEC-07"),
        ):
            data = sample()
            data["configuration"][field] = bad
            result = MOD.analyze(data)
            self.assertEqual("blocked", result["status"])
            self.assertEqual("FAIL", gate(result, expected_gate)["status"])

    def test_root_transitional_exception_is_unverified_only_offline(self):
        data = sample()
        data["configuration"]["reader_privilege"] = "root_transitional"
        report = MOD.analyze(data)
        self.assertEqual("blocked", report["status"])
        self.assertEqual("UNKNOWN", gate(report, "SEC-05")["status"])
        self.assertIn("offline_root_exception_requires_review",
                      report["limitations"])
        self.assertFalse(report["deployment_allowed"])

    def test_root_transitional_is_not_accepted_for_connected(self):
        data = sample("CONNECTED")
        data["configuration"]["reader_privilege"] = "root_transitional"
        report = MOD.analyze(data)
        self.assertEqual("blocked", report["status"])
        self.assertEqual("FAIL", gate(report, "SEC-05")["status"])
        self.assertFalse(report["connected_ready"])

    def test_unknown_critical_requirements_fail_closed(self):
        for profile in ("OFFLINE", "CONNECTED"):
            data = sample(profile)
            data["configuration"]["wifi"] = "unknown"
            self.assertEqual("blocked", MOD.analyze(data)["status"])
            data = sample(profile)
            data["gate_claims"]["SEC-05"] = "unknown"
            self.assertEqual("blocked", MOD.analyze(data)["status"])

    def test_claimed_unmet_overrides_any_good_boolean(self):
        data = sample("CONNECTED")
        data["gate_claims"]["SEC-08"] = "claimed_unmet"
        result = MOD.analyze(data)
        self.assertEqual("blocked", result["status"])
        self.assertEqual("FAIL", gate(result, "SEC-08")["status"])

    def test_rejects_false_attestation_and_invalid_skip(self):
        for claim in ("hardware_verified", "security_certified", "connected_ready"):
            data = sample("CONNECTED")
            data["attestations"][claim] = True
            self.assertEqual("refused", MOD.analyze(data)["status"])
        data = sample("CONNECTED")
        data["gate_claims"]["SEC-09"] = "not_applicable"
        self.assertEqual("invalid_gate_skip", MOD.analyze(data)["errors"][0]["code"])
        data = sample()
        data["configuration"]["updates"] = "signed_offline"
        self.assertEqual("invalid_gate_skip", MOD.analyze(data)["errors"][0]["code"])

    def test_rejects_hostile_types_bounds_and_duplicates(self):
        changes = (
            lambda d: d.update(extra=True),
            lambda d: d.update(profile=["CONNECTED"]),
            lambda d: d.update(provenance="hardware"),
            lambda d: d["configuration"].update(wifi=True),
            lambda d: d["gate_claims"].update({"SEC-01": True}),
            lambda d: d["gate_claims"].pop("SEC-12"),
            lambda d: d["services"].append("sshd"),
            lambda d: d["services"].extend([{"name": "sshd", "scope": "lan",
                            "authentication": "keys", "root_login": False}] * 13),
            lambda d: d["services"].extend([{"name": "sshd", "scope": "lan",
                            "authentication": "keys", "root_login": False}] * 2),
            lambda d: d["services"].append({"name": "sshd", "scope": "lan",
                    "authentication": "keys", "root_login": 1}),
        )
        for change in changes:
            data = sample()
            change(data)
            self.assertEqual("refused", MOD.analyze(data)["status"])

    def test_strict_json_refusals(self):
        self.assertEqual("declarations_consistent_unverified",
                         MOD.analyze_json(json.dumps(sample()))["status"])
        for raw, error in (
            ('{"format":"x","format":"y"}', "duplicate_json_key"),
            ('{"nested":{"name":1,"name":2}}', "duplicate_json_key"),
            ('{"x":NaN}', "invalid_json"),
            ('{"x":Infinity}', "invalid_json"),
            ('{"x":', "invalid_json"),
            ('[]', "invalid_schema"),
        ):
            self.assertEqual(error, MOD.analyze_json(raw)["errors"][0]["code"])
        self.assertEqual("invalid_json_text", MOD.analyze_json(None)
                         ["errors"][0]["code"])
        self.assertEqual("invalid_json_text",
                         MOD.analyze_json(" " * (MOD.MAX_JSON_CHARS + 1))
                         ["errors"][0]["code"])

    def test_pure_api_never_opens_files_network_or_subprocesses(self):
        with patch("builtins.open", side_effect=AssertionError("FILE IO")), \
             patch.object(socket, "socket", side_effect=AssertionError("NETWORK")), \
             patch.object(subprocess, "run", side_effect=AssertionError("PROCESS")):
            self.assertEqual("declarations_consistent_unverified",
                             MOD.analyze(sample())["status"])
            self.assertEqual("declarations_consistent_unverified",
                             MOD.analyze_json(json.dumps(sample("CONNECTED")))
                             ["status"])


if __name__ == "__main__":
    unittest.main()
