"""Checks frugal synthetic permission candidates, never touching a Kobo."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "experimental/offline-audit"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SNAPSHOT = load("pmkb_access_test_snapshot", DIRECTORY / "sysfs_snapshot.py")
with patch.dict(sys.modules, {"sysfs_snapshot": SNAPSHOT}):
    PLAN = load("pmkb_access_test_plan", DIRECTORY / "device_access_plan.py")


def synthetic_snapshot(touch="event5"):
    files = {
        "class/graphics/fb0/dev": "29:0\n",
        "class/graphics/fb0/bits_per_pixel": "16\n",
        "class/graphics/fb0/rotate": "0\n",
        "class/input/event0/device/name": "gpio-keys\n",
        "class/input/event0/dev": "13:64\n",
        "class/input/" + touch + "/device/name": "zForce-ir-touch\n",
        "class/input/" + touch + "/dev": "13:69\n",
        "class/misc/ntx_io/dev": "10:190\n",
    }
    return {"schema_version": 1, "provenance": "synthetic",
            "files": [{"path": k, "text": v} for k, v in files.items()]}


class InertDeviceAccessTests(unittest.TestCase):
    def assert_inert(self, result):
        for field in ("hardware_verified", "permission_applied",
                      "reader_started", "boot_qualified", "security_certified",
                      "deployable", "runtime_ram_delta_measured"):
            self.assertIs(result[field], False, field)
        self.assertEqual(0, result["added_resident_processes_on_kobo"])
        self.assertEqual("synthetic_access_planning_only", result["scope"])

    def test_three_device_roles_only_and_never_boot_ready(self):
        src = synthetic_snapshot()
        original = copy.deepcopy(src)
        report = PLAN.plan_device_access(json.dumps(src))
        self.assertEqual(src, original)
        self.assert_inert(report)
        self.assertEqual("candidate_unverified", report["status"])
        self.assertTrue(report["snapshot_coherent"])
        self.assertEqual({"display", "touch", "frontlight"},
                         {x["role"] for x in report["candidates"]})
        self.assertEqual({"/dev/fb0", "/dev/input/event5", "/dev/ntx_io"},
                         {x["path"] for x in report["candidates"]})
        self.assertIn("button_event_identity_and_input_permissions",
                      report["evidence_missing"])

    def test_dynamic_event_numbers_without_guessing_button_event(self):
        for event in ("event1", "event5", "event17"):
            with self.subTest(event=event):
                report = PLAN.plan_device_access(json.dumps(synthetic_snapshot(event)))
                self.assertEqual("candidate_unverified", report["status"])
                self.assertEqual("/dev/input/" + event,
                                 report["candidates"][1]["path"])
                self.assertEqual(3, len(report["candidates"]))
                self.assertNotIn("/dev/input/event0",
                                 [x["path"] for x in report["candidates"]])

    def test_minimal_modes_do_not_write_touch_events(self):
        report = PLAN.plan_device_access(json.dumps(synthetic_snapshot()))
        paths = {x["path"]: x for x in report["candidates"]}
        self.assertEqual(("rw", "0660", "pmkb-hw"),
                         (paths["/dev/fb0"]["access_hypothesis"],
                          paths["/dev/fb0"]["mode_candidate"],
                          paths["/dev/fb0"]["group_candidate"]))
        self.assertEqual(("r", "0640", "pmkb-hw"),
                         (paths["/dev/input/event5"]["access_hypothesis"],
                          paths["/dev/input/event5"]["mode_candidate"],
                          paths["/dev/input/event5"]["group_candidate"]))
        self.assertEqual(("rw", "0660", "pmkb-hw"),
                         (paths["/dev/ntx_io"]["access_hypothesis"],
                          paths["/dev/ntx_io"]["mode_candidate"],
                          paths["/dev/ntx_io"]["group_candidate"]))
        self.assertTrue(all(x["node_type"] == "character" and
                            not x["applied"] for x in report["candidates"]))
        self.assertTrue(all(x["mode_candidate"] not in ("0666", "0777")
                            for x in report["candidates"]))

    def test_root_transitional_is_explicit_and_never_qualified(self):
        report = PLAN.plan_device_access(json.dumps(synthetic_snapshot()),
                                         strategy="root_transitional")
        self.assertEqual("candidate_unverified", report["status"])
        self.assertTrue(all(x["mode_candidate"] is None and
                            x["group_candidate"] is None
                            for x in report["candidates"]))
        self.assertIn("risk_acceptance_for_privileged_reader",
                      report["evidence_missing"])
        self.assert_inert(report)

    def test_missing_ntx_touch_or_fb_is_refused(self):
        for target in ("class/misc/", "class/input/event5/", "class/graphics/"):
            with self.subTest(target=target):
                src = synthetic_snapshot()
                src["files"] = [f for f in src["files"]
                                if not f["path"].startswith(target)]
                result = PLAN.plan_device_access(json.dumps(src))
                self.assertEqual("refused", result["status"])
                self.assertEqual([], result["candidates"])
                self.assert_inert(result)

    def test_corrupt_inputs_refuse_and_never_mint_devices(self):
        cases = (
            None, "{}", '{"schema_version":1,"schema_version":1}',
            '{"schema_version":NaN}', "{" * 2000, " " * 131073
        )
        for raw in cases:
            with self.subTest(length=len(raw) if type(raw) is str else 0):
                result = PLAN.plan_device_access(raw)
                self.assertEqual("refused", result["status"])
                self.assertEqual([], result["candidates"])
                self.assert_inert(result)
        src = synthetic_snapshot()
        src["provenance"] = "device_capture"
        self.assertEqual("refused", PLAN.plan_device_access(json.dumps(src))["status"])

    def test_bad_strategy_refused_even_for_coherent_snapshot(self):
        raw = json.dumps(synthetic_snapshot())
        for kind in (True, [], "unknown", "", None):
            self.assertEqual("invalid_strategy",
                             PLAN.plan_device_access(raw, kind)["errors"][0]["code"])

    def test_readonly_proposal_never_includes_block_watchdog_or_i2c_nodes(self):
        result = PLAN.plan_device_access(json.dumps(synthetic_snapshot()))
        for x in result["candidates"]:
            self.assertTrue(x["path"].startswith("/dev/"))
            self.assertFalse(any(name in x["path"] for name in
                             ("mmcblk", "watchdog", "i2c", "mem", "random")))
        self.assertEqual("candidate_unverified", result["status"])

    def test_result_is_fresh_and_input_unchanged(self):
        data = json.dumps(synthetic_snapshot())
        result = PLAN.plan_device_access(data)
        result["candidates"].clear()
        result["evidence_missing"].clear()
        later = PLAN.plan_device_access(data)
        self.assertEqual(3, len(later["candidates"]))
        self.assertTrue(later["evidence_missing"])

    def test_no_file_process_or_network_access(self):
        raw = json.dumps(synthetic_snapshot())
        with patch("builtins.open", side_effect=AssertionError("file I/O")), \
             patch.object(io, "open", side_effect=AssertionError("io I/O")), \
             patch.object(os, "open", side_effect=AssertionError("OS I/O")), \
             patch.object(subprocess, "run", side_effect=AssertionError("process")), \
             patch.object(socket, "socket", side_effect=AssertionError("network")):
            self.assertEqual("candidate_unverified",
                             PLAN.plan_device_access(raw)["status"])
            self.assertEqual("refused", PLAN.plan_device_access("{}")["status"])


if __name__ == "__main__":
    unittest.main()
