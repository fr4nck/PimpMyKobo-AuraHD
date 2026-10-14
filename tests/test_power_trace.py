"""PMKB power-lab V0: arithmetic tests only, no device or sysfs access."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "experimental/power-lab/power_trace.py"
SPEC = importlib.util.spec_from_file_location("pmkb_power_trace", SRC)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def trace(*, power=100, source="synthetic", kernel="reference-2.6", duration=3600):
    return {
        "format": MOD.FORMAT, "provenance": source, "device": "E606C0",
        "scenario": "reading_idle",
        "conditions": {"workload": "same-book-same-pages", "kernel": kernel,
                       "instrument": "synthetic-test-meter", "wifi": "off",
                       "frontlight_percent": 0, "power_source": "battery"},
        "samples": [{"elapsed_s": 0, "voltage_mv": 4000, "current_ma": power},
                    {"elapsed_s": duration, "voltage_mv": 4000,
                     "current_ma": power}]
    }


class PowerTraceTests(unittest.TestCase):
    def test_exact_energy_integral_does_not_infer_battery_lifetime(self):
        src = trace()
        original = copy.deepcopy(src)
        result = MOD.analyze(src)
        self.assertEqual("calculated", result["status"])
        self.assertEqual(400, result["energy_mwh"])
        self.assertEqual(100, result["discharge_mah"])
        self.assertEqual(400, result["mean_power_mw"])
        self.assertEqual(src, original)
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["measurements_authenticated"])
        self.assertFalse(result["energy_saving_verified"])
        self.assertNotIn("battery_lifetime", result)

    def test_trapezoidal_integration(self):
        src = trace()
        src["samples"][0]["current_ma"] = 50
        src["samples"][1]["current_ma"] = 150
        result = MOD.analyze(src)
        self.assertEqual(400, result["energy_mwh"])
        self.assertEqual(100, result["discharge_mah"])

    def test_comparison_requires_matched_workload_without_proof_of_savings(self):
        a, b = trace(source="user_entered"), trace(power=75, source="user_entered", kernel="candidate")
        result = MOD.compare(a, b)
        self.assertEqual("calculated_unverified", result["status"])
        self.assertEqual(25.0, result["arithmetic_difference_percent"])
        self.assertFalse(result["energy_saving_verified"])
        self.assertFalse(result["hardware_verified"])
        b["conditions"]["frontlight_percent"] = 20
        self.assertEqual("conditions_mismatch", MOD.compare(a, b)["errors"][0]["code"])
        b["conditions"]["frontlight_percent"] = 0
        b["samples"][1]["elapsed_s"] = 100
        self.assertEqual("duration_mismatch", MOD.compare(a, b)["errors"][0]["code"])

    def test_schema_type_bounds_and_order_fail_closed(self):
        for mutate in (
            lambda t: t.update(device="another"),
            lambda t: t.update(provenance="device_verified"),
            lambda t: t["conditions"].update(wifi="automatic"),
            lambda t: t["conditions"].update(frontlight_percent=True),
            lambda t: t["conditions"].update(power_source="charger"),
            lambda t: t["samples"][0].update(elapsed_s=-1),
            lambda t: t["samples"][0].update(elapsed_s=True),
            lambda t: t["samples"][1].update(elapsed_s=0),
            lambda t: t["samples"][1].update(current_ma=float("nan")),
            lambda t: t["samples"][1].update(current_ma=-1),
            lambda t: t["samples"][1].update(current_ma=10**500),
            lambda t: t["samples"][1].update(voltage_mv=0),
            lambda t: t["samples"].append(dict(t["samples"][1])),
            lambda t: t["samples"][1].update(unapproved_key=True),
            lambda t: t.update(physically_qualified=True),
        ):
            data = trace()
            mutate(data)
            result = MOD.analyze(data)
            self.assertEqual("refused", result["status"], result)
            self.assertFalse(result["energy_saving_verified"])

    def test_strict_json_rejects_duplicate_keys_and_nonstandard_constants(self):
        data = json.dumps(trace())
        self.assertEqual("calculated", MOD.analyze_json(data)["status"])
        for source, code in (
            ('{"format":"bad","format":"pmkb-power-trace-v1"}', "duplicate_json_key"),
            ('{"samples":[{"elapsed_s":0,"elapsed_s":1}]}', "duplicate_json_key"),
            ('{"data":NaN}', "invalid_json"),
            ('{"data":Infinity}', "invalid_json"),
            ('{"data":', "invalid_json"),
        ):
            self.assertEqual(code, MOD.analyze_json(source)["errors"][0]["code"])
        self.assertEqual("invalid_json_text", MOD.analyze_json(" " * (MOD.MAX_JSON_CHARS + 1))["errors"][0]["code"])

    def test_pure_api_never_opens_files_or_invokes_commands(self):
        with patch("builtins.open", side_effect=AssertionError("I/O")), \
             patch("subprocess.run", side_effect=AssertionError("process")):
            self.assertEqual("calculated", MOD.analyze(trace())["status"])
            self.assertEqual("calculated", MOD.analyze_json(json.dumps(trace()))["status"])
            self.assertEqual("calculated_unverified",
                             MOD.compare(trace(), trace(power=80))["status"])


if __name__ == "__main__":
    unittest.main()
