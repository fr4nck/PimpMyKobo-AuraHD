"""Synthetic tests only: no U-Boot binary, Kobo dump, device or external fixture."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "experimental/power-lab/boot_contract.py"
SPEC = importlib.util.spec_from_file_location("pmkb_boot_contract", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def sample():
    base = 0x70000000  # SYNTHETIC base; NOT extracted from E606C0
    return {
        "format": MOD.FORMAT, "device": "E606C0",
        "provenance": "synthetic",
        "ram": {"start": base, "size": 512 * 1024 * 1024},
        "regions": [
            {"name": "boot_data", "start": base + 0x1000, "size": 0x1000},
            {"name": "kernel", "start": base + 0x800000, "size": 0x500000},
            {"name": "hwconfig", "start": base + 0x1F00000, "size": 0x1000},
            {"name": "waveform", "start": base + 0x2000000, "size": 0x120000},
        ],
        "image": {"format": "uImage", "load": base + 0x800000,
                  "entry": base + 0x800000, "size": 0x400000},
        "handoff": {"kind": "ATAGS", "r0": 0, "r1": 1234,
                    "r2": base + 0x1000},
        "parameters": {
            "hwcfg_p": base + 0x1F00000, "hwcfg_sz": 39,
            "waveform_p": base + 0x2000000, "waveform_sz": 1158319,
        },
    }


class BootContractTests(unittest.TestCase):
    def test_valid_synthetic_is_not_a_boot_certificate(self):
        value = sample()
        before = copy.deepcopy(value)
        outcome = MOD.analyze(value)
        self.assertEqual("consistent_unverified", outcome["status"])
        self.assertEqual(value, before)
        self.assertFalse(outcome["hardware_verified"])
        self.assertFalse(outcome["boot_compatible"])
        self.assertFalse(outcome["memory_map_verified"])
        self.assertEqual(4, outcome["region_count"])

    def test_dtb_handoff_declared_is_only_structural(self):
        value = sample()
        value["handoff"]["kind"] = "DTB"
        value["handoff"]["r1"] = 0xFFFFFFFF
        self.assertEqual("consistent_unverified", MOD.analyze(value)["status"])

    def test_dtb_alignment_and_minimum_boot_data_size(self):
        value = sample()
        value["handoff"]["kind"] = "DTB"
        value["handoff"]["r2"] += 4
        self.assertEqual("invalid_dtb_alignment",
                         MOD.analyze(value)["errors"][0]["code"])
        value["handoff"]["r2"] = value["regions"][0]["start"] + 0x1000 - 32
        self.assertEqual("boot_data_pointer_outside_region",
                         MOD.analyze(value)["errors"][0]["code"])
        value["handoff"]["kind"] = "ATAGS"
        self.assertEqual("consistent_unverified", MOD.analyze(value)["status"])
        value["handoff"]["r2"] += 20
        self.assertEqual("boot_data_pointer_outside_region",
                         MOD.analyze(value)["errors"][0]["code"])

    def test_fail_closed_negative_cases(self):
        actions = (
            lambda v: v["ram"].update(size=256 * 1024 * 1024),
            lambda v: v["ram"].update(start=-1),
            lambda v: v["ram"].update(start=True),
            lambda v: v["regions"][0].update(size=0),
            lambda v: v["regions"][0].update(size=3),
            lambda v: v["regions"][0].update(start=0xFFFFF000),
            lambda v: v["regions"][1].update(start=v["regions"][0]["start"]),
            lambda v: v["regions"].pop(),
            lambda v: v["regions"].append(dict(v["regions"][0])),
            lambda v: v["image"].update(load=0xDEADBEEF),
            lambda v: v["image"].update(entry=0xDEADBEEF),
            lambda v: v["image"].update(format="zImage"),
            lambda v: v["image"].update(size=True),
            lambda v: v["handoff"].update(kind="UNKNOWN"),
            lambda v: v["handoff"].update(r0=1),
            lambda v: v["handoff"].update(r1=None),
            lambda v: v["handoff"].update(r2=v["ram"]["start"]),
            lambda v: v["parameters"].update(hwcfg_p=0),
            lambda v: v["parameters"].update(waveform_sz=0x200000),
            lambda v: v["parameters"].update(hwcfg_sz=None),
            lambda v: v.update(verified=True),
            lambda v: v.update(provenance="binary_verified"),
            lambda v: v.update(device="E606F0B"),
        )
        for action in actions:
            with self.subTest(action=repr(action)):
                value = sample()
                action(value)
                result = MOD.analyze(value)
                self.assertEqual("refused", result["status"], result)
                self.assertFalse(result["boot_compatible"])

    def test_strict_json_rejects_duplicate_keys_constants_and_large_input(self):
        self.assertEqual("consistent_unverified",
                         MOD.analyze_json(json.dumps(sample()))["status"])
        for raw, error in (
            ('{"format":"x","format":"y"}', "duplicate_json_key"),
            ('{"data":NaN}', "invalid_json"),
            ('{"data":Infinity}', "invalid_json"),
            ('{"data":', "invalid_json"),
        ):
            self.assertEqual(error, MOD.analyze_json(raw)["errors"][0]["code"])
        self.assertEqual("invalid_json_text",
                         MOD.analyze_json(" " * (MOD.MAX_JSON_CHARS + 1))
                         ["errors"][0]["code"])

    def test_pure_api_does_not_open_files_or_run_processes(self):
        with patch("builtins.open", side_effect=AssertionError("file I/O")), \
             patch("subprocess.run", side_effect=AssertionError("subprocess")):
            self.assertEqual("consistent_unverified", MOD.analyze(sample())["status"])
            self.assertEqual("consistent_unverified",
                             MOD.analyze_json(json.dumps(sample()))["status"])


if __name__ == "__main__":
    unittest.main()
