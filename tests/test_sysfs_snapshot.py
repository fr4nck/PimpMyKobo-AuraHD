"""Synthetic metadata tests only: no boot scripts, device nodes or real sysfs."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "experimental/offline-audit/sysfs_snapshot.py"
SPEC = importlib.util.spec_from_file_location("pmkb_synthetic_sysfs", MODULE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def fixture(event="event5"):
    contents = {
        "class/graphics/fb0/dev": "29:0\n",
        "class/graphics/fb0/bits_per_pixel": "16\n",
        "class/graphics/fb0/rotate": "0\n",
        "class/misc/ntx_io/dev": "10:190\n",
        "class/input/event0/device/name": "gpio-keys\n",
        "class/input/event0/dev": "13:64\n",
        f"class/input/{event}/device/name": "zForce-ir-touch\n",
        f"class/input/{event}/dev": "13:69\n",
    }
    return {"schema_version": 1, "provenance": "synthetic",
            "files": [{"path": p, "text": v} for p, v in contents.items()]}


def replace(snapshot, path, text):
    for item in snapshot["files"]:
        if item["path"] == path:
            item["text"] = text
            return
    raise AssertionError(path)


class SyntheticSysfsTests(unittest.TestCase):
    def assert_refused(self, snapshot, code):
        result = MOD.validate_snapshot(snapshot)
        self.assertEqual("refused", result["status"])
        self.assertFalse(result["snapshot_coherent"])
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["physical_restore_eligible"])
        self.assertEqual({}, result["identified"])
        self.assertEqual(code, result["errors"][0]["code"])

    def test_identifies_changed_event_indices_without_claiming_hardware_ready(self):
        for index in (1, 5, 17):
            with self.subTest(index=index):
                snapshot = fixture(f"event{index}")
                original = copy.deepcopy(snapshot)
                result = MOD.validate_snapshot(json.loads(json.dumps(snapshot)))
                self.assertEqual("coherent", result["status"])
                self.assertTrue(result["snapshot_coherent"])
                self.assertEqual(f"class/input/event{index}",
                                 result["identified"]["touch"]["sysfs_path"])
                self.assertFalse(result["hardware_verified"])
                self.assertFalse(result["boot_qualified"])
                self.assertFalse(result["physical_restore_eligible"])
                self.assertIn("framebuffer_driver_binding_and_panel_readiness",
                              result["unverified"])
                self.assertEqual(original, snapshot)

    def test_missing_components_and_partial_records_fail_closed(self):
        for prefix in ("class/graphics/", "class/input/", "class/misc/"):
            with self.subTest(prefix=prefix):
                data = fixture()
                data["files"] = [f for f in data["files"]
                                 if not f["path"].startswith(prefix)]
                self.assertEqual("refused", MOD.validate_snapshot(data)["status"])
        for path in ("class/graphics/fb0/rotate",
                     "class/input/event5/device/name",
                     "class/input/event5/dev"):
            data = fixture()
            data["files"] = [f for f in data["files"] if f["path"] != path]
            self.assert_refused(data, "missing_file")

    def test_duplicate_and_unknown_touch_identity(self):
        data = fixture()
        data["files"] += [
            {"path": "class/input/event7/device/name", "text": "zForce-ir-touch"},
            {"path": "class/input/event7/dev", "text": "13:71"},
        ]
        self.assert_refused(data, "touch_identity_ambiguous_or_missing")
        data = fixture()
        replace(data, "class/input/event5/device/name", "Some other touch")
        self.assert_refused(data, "touch_identity_ambiguous_or_missing")

    def test_second_framebuffer_is_ambiguous(self):
        data = fixture()
        data["files"].append({"path": "class/graphics/fb1/dev", "text": "29:1"})
        self.assert_refused(data, "framebuffer_identity_ambiguous_or_missing")

    def test_invalid_numbers_and_device_collisions(self):
        for value in ("-1:2", "13:x", "0:1", "4096:1", "13:1048576",
                      "13:1:2", "13:01", "13:1\nextra", "9" * 100 + ":1"):
            with self.subTest(value=value):
                data = fixture()
                replace(data, "class/input/event5/dev", value)
                code = "invalid_text" if "\nextra" in value else "invalid_dev"
                self.assert_refused(data, code)
        data = fixture()
        replace(data, "class/input/event5/dev", "13:64")
        self.assert_refused(data, "duplicate_dev")
        for path, value, code in (
            ("class/graphics/fb0/dev", "29:1", "unexpected_framebuffer_dev"),
            ("class/misc/ntx_io/dev", "10:191", "unexpected_ntx_dev"),
        ):
            data = fixture()
            replace(data, path, value)
            self.assert_refused(data, code)

    def test_invalid_modes_and_fabricated_readiness_refused(self):
        for path, value, code in (
            ("class/graphics/fb0/bits_per_pixel", "4", "unsupported_bpp"),
            ("class/graphics/fb0/rotate", "4", "invalid_rotation"),
        ):
            data = fixture()
            replace(data, path, value)
            self.assert_refused(data, code)
        data = fixture()
        data["files"].append({"path": "class/graphics/fb0/ready", "text": "1"})
        self.assert_refused(data, "unsupported_path")
        data = fixture()
        data["hardware_verified"] = True
        self.assert_refused(data, "invalid_schema")

    def test_bad_contract_paths_records_and_duplicate_paths(self):
        for path in ("/sys/class/input/event1/dev", "/dev/fb0",
                     "../class/misc/ntx_io/dev", r"class\misc\ntx_io\dev"):
            data = fixture()
            data["files"][0]["path"] = path
            self.assert_refused(data, "unsupported_path")
        data = fixture()
        data["files"].append(copy.deepcopy(data["files"][0]))
        self.assert_refused(data, "duplicate_path")
        for invalid in (None, [], {}, {"schema_version": True,
                        "provenance": "synthetic", "files": []}):
            self.assert_refused(invalid, "invalid_schema")
        data = fixture()
        data["provenance"] = "captured"
        self.assert_refused(data, "invalid_provenance")
        data = fixture()
        data["files"][0]["text"] = 29
        self.assert_refused(data, "invalid_text")
        data = fixture()
        data["files"][0]["target"] = "/dev/fb0"
        self.assert_refused(data, "invalid_record")
        data = fixture()
        data["files"] *= 40
        self.assert_refused(data, "invalid_files")

    def test_validation_does_not_open_files_or_launch_helpers(self):
        with patch("builtins.open", side_effect=AssertionError("open")), \
             patch.object(io, "open", side_effect=AssertionError("io.open")), \
             patch.object(os, "open", side_effect=AssertionError("os.open")), \
             patch.object(subprocess, "run", side_effect=AssertionError("run")):
            self.assertTrue(MOD.validate_snapshot(fixture())["snapshot_coherent"])
            self.assert_refused(None, "invalid_schema")


    def test_versioned_json_fixtures_have_expected_reports(self):
        directory = ROOT / "tests/fixtures/sysfs-v1"
        manifest = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
        expected_files = {
            "minimal.json", "touch-event1.json", "touch-event17.json",
            "framebuffer-present-unverified.json", "touch-missing.json",
            "touch-ambiguous.json", "ntx-missing.json", "invalid-dev.json",
            "dev-collision.json", "fabricated-ready.json",
            "duplicate-root-key.json", "duplicate-record-key.json",
        }
        self.assertEqual(1, manifest["schema_version"])
        self.assertEqual("synthetic_metadata_only", manifest["scope"])
        names = [case["file"] for case in manifest["cases"]]
        self.assertEqual(len(expected_files), len(names))
        self.assertEqual(expected_files, set(names))
        self.assertEqual(expected_files | {"cases.json"},
                         {p.name for p in directory.glob("*.json")})
        for case in manifest["cases"]:
            with self.subTest(file=case["file"]):
                text = (directory / case["file"]).read_text(encoding="utf-8")
                result = MOD.validate_snapshot_json(text)
                self.assertEqual(case["expected_status"], result["status"])
                self.assertFalse(result["hardware_verified"])
                self.assertFalse(result["boot_qualified"])
                self.assertFalse(result["physical_restore_eligible"])
                self.assertEqual("synthetic_metadata_only", result["scope"])
                self.assertIn("framebuffer_driver_binding_and_panel_readiness",
                              result["unverified"])
                if case["expected_status"] == "coherent":
                    self.assertTrue(result["snapshot_coherent"])
                    self.assertEqual([], result["errors"])
                    self.assertEqual(case["expected_touch"],
                                     result["identified"]["touch"]["sysfs_path"])
                else:
                    self.assertFalse(result["snapshot_coherent"])
                    self.assertEqual({}, result["identified"])
                    self.assertEqual(case["expected_error"],
                                     result["errors"][0]["code"])

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        directory = ROOT / "tests/fixtures/sysfs-v1"
        for name in ("duplicate-root-key.json", "duplicate-record-key.json"):
            with self.subTest(file=name):
                text = (directory / name).read_text(encoding="utf-8")
                # Demonstrate the information loss in an ordinary JSON reader.
                self.assertTrue(MOD.validate_snapshot(json.loads(text))["snapshot_coherent"])
                result = MOD.validate_snapshot_json(text)
                self.assertEqual("refused", result["status"])
                self.assertEqual("duplicate_json_key", result["errors"][0]["code"])
                self.assertEqual({}, result["identified"])

    def test_strict_json_syntax_and_input_limits(self):
        for text, code in (
            (None, "invalid_json_text"),
            (b"{}", "invalid_json_text"),
            (" " * (MOD.MAX_JSON_CHARACTERS + 1), "invalid_json_text"),
            ('{"schema_version": NaN}', "invalid_json"),
            ('{"schema_version": Infinity}', "invalid_json"),
            ('{"schema_version": -Infinity}', "invalid_json"),
            ('{"files":', "invalid_json"),
            ("{} {}", "invalid_json"),
            ("null", "invalid_schema"),
        ):
            with self.subTest(code=code, text_type=type(text).__name__):
                result = MOD.validate_snapshot_json(text)
                self.assertEqual("refused", result["status"])
                self.assertEqual(code, result["errors"][0]["code"])
                self.assertFalse(result["snapshot_coherent"])
                self.assertFalse(result["hardware_verified"])
                self.assertFalse(result["boot_qualified"])
                self.assertFalse(result["physical_restore_eligible"])
        for text in ("[" * 2048 + "0" + "]" * 2048,
                     '{"schema_version":' + "9" * 8192 + "}"):
            result = MOD.validate_snapshot_json(text)
            self.assertEqual("refused", result["status"])
            self.assertIn(result["errors"][0]["code"], {"invalid_json", "invalid_schema"})

    def test_json_validation_has_no_io_and_preserves_report_isolation(self):
        text = json.dumps(fixture())
        with patch("builtins.open", side_effect=AssertionError("open")), \
             patch.object(io, "open", side_effect=AssertionError("io.open")), \
             patch.object(os, "open", side_effect=AssertionError("os.open")), \
             patch.object(subprocess, "run", side_effect=AssertionError("run")):
            first = MOD.validate_snapshot_json(text)
            self.assertTrue(first["snapshot_coherent"])
            first["hardware_verified"] = True
            first["identified"].clear()
            second = MOD.validate_snapshot_json(text)
            self.assertFalse(second["hardware_verified"])
            self.assertEqual(3, len(second["identified"]))
            self.assertEqual("refused", MOD.validate_snapshot_json("{")["status"])
