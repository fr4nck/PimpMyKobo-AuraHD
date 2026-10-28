"""Plan tests operate on synthetic JSON and inert scenario labels only."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "experimental/offline-audit"
FIXTURES = ROOT / "tests/fixtures/sysfs-v1"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SNAPSHOT = load_module("plan_test_snapshot", DIRECTORY / "sysfs_snapshot.py")
# Dependencies are loaded before the no-I/O assertions, never during planning.
with patch.dict(sys.modules, {"sysfs_snapshot": SNAPSHOT}):
    MOD = load_module("plan_test_startup", DIRECTORY / "startup_plan.py")


def assumed_scenario():
    scenario = MOD.default_scenario()
    scenario["preconditions"] = {
        key: "assumed_satisfied" for key in MOD.PRECONDITIONS
    }
    scenario["decisions"] = {key: "assumed_resolved" for key in MOD.DECISIONS}
    return scenario


class InertStartupPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = (FIXTURES / "minimal.json").read_text(encoding="utf-8")

    def assert_inert(self, report):
        for key in ("plan_executable", "launch_performed", "hardware_verified",
                    "boot_qualified", "physical_restore_eligible"):
            self.assertIs(False, report[key], key)
        self.assertEqual("synthetic_planning_only", report["scope"])
        self.assertEqual(set(MOD.DECISIONS), set(report["real_decisions_unresolved"]))
        self.assertTrue(report["hardware_evidence_missing"])
        for entry in report["plan"] + report["trace"]:
            self.assertIs(False, entry["performed"])
        # No user callback, shell command or nested executable can enter a plan.
        def assert_json_data(value):
            if type(value) is dict:
                self.assertTrue(all(type(key) is str for key in value))
                for child in value.values():
                    assert_json_data(child)
            elif type(value) is list:
                for child in value:
                    assert_json_data(child)
            else:
                self.assertIn(type(value), (str, int, bool, type(None)))
        assert_json_data(report)

    def test_default_scenario_stops_before_node_preparation(self):
        report = MOD.plan_startup(self.snapshot)
        self.assertEqual("blocked", report["status"])
        self.assertTrue(report["snapshot_coherent"])
        self.assertEqual(["identify_devices"],
                         [entry["step"] for entry in report["plan"]])
        self.assertEqual(["identify_devices", "prepare_nodes"],
                         [entry["step"] for entry in report["trace"]])
        self.assertEqual("blocked", report["trace"][-1]["outcome"])
        self.assertNotIn("consider_reader_launch",
                         [entry["step"] for entry in report["plan"]])
        self.assert_inert(report)

    def test_all_assumptions_exercise_order_without_authorizing_execution(self):
        scenario = assumed_scenario()
        original = copy.deepcopy(scenario)
        report = MOD.plan_startup(self.snapshot, scenario)
        expected = ["identify_devices", "prepare_nodes", "prepare_framebuffer",
                    "prepare_profile", "consider_reader_launch"]
        self.assertEqual("simulation_complete", report["status"])
        self.assertEqual(expected, [entry["step"] for entry in report["plan"]])
        self.assertEqual(expected, [entry["step"] for entry in report["trace"]])
        self.assertEqual([], report["not_reached"])
        self.assertEqual([{"name": "snapshot_metadata", "state": "checked",
                           "scope": "synthetic_metadata_only"}],
                         report["checked_preconditions"])
        self.assertEqual(["identify_devices"], report["plan"][1]["depends_on"])
        self.assertEqual("class/input/event5",
                         report["plan"][1]["synthetic_identities"]["touch"]["sysfs_path"])
        self.assertEqual(original, scenario)
        self.assert_inert(report)

    def test_every_unresolved_decision_blocks_its_dependent_stage(self):
        for decision in MOD.DECISIONS:
            with self.subTest(decision=decision):
                scenario = assumed_scenario()
                scenario["decisions"][decision] = "unresolved"
                report = MOD.plan_startup(self.snapshot, scenario)
                blocked = next(step[0] for step in MOD.STEPS if decision in step[3])
                self.assertEqual("blocked", report["status"])
                self.assertEqual(blocked, report["trace"][-1]["step"])
                self.assertNotIn(blocked, [entry["step"] for entry in report["plan"]])
                self.assert_inert(report)

    def test_every_unknown_or_failed_precondition_blocks_progress(self):
        for prerequisite in MOD.PRECONDITIONS:
            for state in ("unknown", "assumed_failed"):
                with self.subTest(prerequisite=prerequisite, state=state):
                    scenario = assumed_scenario()
                    scenario["preconditions"][prerequisite] = state
                    report = MOD.plan_startup(self.snapshot, scenario)
                    self.assertEqual("blocked", report["status"])
                    self.assertEqual("blocked", report["trace"][-1]["outcome"])
                    self.assertTrue(any(b["name"] == prerequisite for b in report["blockers"]))
                    self.assert_inert(report)

    def test_injected_failure_stops_trace_and_all_dependent_stages(self):
        for index, step in enumerate(MOD.STEP_IDS):
            with self.subTest(step=step):
                scenario = assumed_scenario()
                scenario["failure_at"] = step
                report = MOD.plan_startup(self.snapshot, scenario)
                self.assertEqual("simulated_failure", report["status"])
                self.assertEqual(list(MOD.STEP_IDS[:index + 1]),
                                 [entry["step"] for entry in report["trace"]])
                self.assertEqual(list(MOD.STEP_IDS[index + 1:]), report["not_reached"])
                self.assertEqual("simulated_failure", report["trace"][-1]["outcome"])
                if step == "identify_devices":
                    self.assertNotIn("prepare_nodes",
                                     [entry["step"] for entry in report["plan"]])
                self.assert_inert(report)

    def test_all_snapshot_fixtures_keep_planning_and_hardware_separate(self):
        cases = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))["cases"]
        for case in cases:
            with self.subTest(file=case["file"]):
                text = (FIXTURES / case["file"]).read_text(encoding="utf-8")
                report = MOD.plan_startup(text, assumed_scenario())
                expected = "simulation_complete" if case["expected_status"] == "coherent" else "refused"
                self.assertEqual(expected, report["status"])
                if expected == "refused":
                    self.assertEqual([], report["plan"])
                    self.assertEqual(case["expected_error"], report["errors"][0]["code"])
                    self.assertEqual(list(MOD.STEP_IDS[1:]), report["not_reached"])
                self.assert_inert(report)

    def test_unrecognized_authorizations_commands_and_callbacks_are_refused(self):
        examples = [[], {"write_authorized": True}]
        for field, value in (("write_authorized", True), ("command", "reboot"),
                             ("callback", lambda: None), ("timeout", 5)):
            scenario = assumed_scenario()
            scenario[field] = value
            examples.append(scenario)
        for field, key, value in (
            ("decisions", "permissions_policy", "resolved"),
            ("preconditions", "panel_ready", True),
            ("preconditions", "panel_ready", lambda: None),
        ):
            scenario = assumed_scenario()
            scenario[field][key] = value
            examples.append(scenario)
        scenario = assumed_scenario()
        scenario["failure_at"] = "watchdog"
        examples.append(scenario)
        for scenario in examples:
            report = MOD.plan_startup(self.snapshot, scenario)
            self.assertEqual("refused", report["status"])
            self.assertEqual([{"code": "invalid_scenario"}], report["errors"])
            self.assertEqual([], report["plan"])
            self.assertEqual([], report["trace"])
            self.assert_inert(report)

    def test_no_fallback_operations_exist_in_success_or_failure_plans(self):
        scenarios = [assumed_scenario(), MOD.default_scenario()]
        for step in MOD.STEP_IDS:
            scenario = assumed_scenario()
            scenario["failure_at"] = step
            scenarios.append(scenario)
        allowed = {"identify_devices", "prepare_nodes", "prepare_framebuffer",
                   "prepare_profile", "consider_reader_launch"}
        for scenario in scenarios:
            report = MOD.plan_startup(self.snapshot, scenario)
            self.assertTrue({entry["step"] for entry in report["plan"]} <= allowed)
            self.assertTrue({entry["step"] for entry in report["trace"]} <= allowed)
            self.assert_inert(report)

    def test_planning_does_not_access_files_devices_or_helpers(self):
        scenario = assumed_scenario()
        with patch("builtins.open", side_effect=AssertionError("open")), \
             patch.object(io, "open", side_effect=AssertionError("io.open")), \
             patch.object(os, "open", side_effect=AssertionError("os.open")), \
             patch.object(subprocess, "run", side_effect=AssertionError("run")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("Popen")), \
             patch.object(os, "system", side_effect=AssertionError("system")), \
             patch.object(os, "stat", side_effect=AssertionError("stat")), \
             patch.object(os, "listdir", side_effect=AssertionError("listdir")):
            report = MOD.plan_startup(self.snapshot, scenario)
            self.assertEqual("simulation_complete", report["status"])
            self.assert_inert(report)
            self.assertEqual("blocked", MOD.plan_startup(self.snapshot)["status"])
            self.assertEqual("refused", MOD.plan_startup("{")["status"])

    def test_reports_do_not_share_mutable_state(self):
        first = MOD.plan_startup(self.snapshot, assumed_scenario())
        first["plan"][1]["synthetic_identities"]["touch"]["dev"].clear()
        first["real_decisions_unresolved"].clear()
        first["hardware_verified"] = True
        second = MOD.plan_startup(self.snapshot, assumed_scenario())
        self.assertEqual([13, 69],
                         second["plan"][1]["synthetic_identities"]["touch"]["dev"])
        self.assert_inert(second)
