"""Synthetic Wi-Fi / SDIO suspend contract: no peripheral operations."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "experimental/power-lab/network_sleep_contract.py"
SPEC = importlib.util.spec_from_file_location("pmkb_network_sleep", SRC)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class NetworkSleepContractTests(unittest.TestCase):
    def test_default_and_clean_sleep_wake_stay_off(self):
        self.assertEqual("consistent_unverified", MOD.replay([])["status"])
        result = MOD.replay(["suspend", "resume", "suspend", "resume"])
        self.assertEqual("consistent_unverified", result["status"])
        self.assertFalse(result["network_requested"])
        self.assertFalse(result["wifi_symbolically_on"])
        self.assertEqual((2, 2), (result["suspend_count"], result["resume_count"]))
        for field in ("hardware_verified", "sdio_resume_verified",
                      "wifi_power_cut_verified", "rtc_verified"):
            self.assertFalse(result[field])

    def test_explicit_wifi_session_and_release_before_suspend(self):
        result = MOD.replay([
            "network_request", "sdio_ready", "wifi_on", "wifi_off",
            "network_release", "suspend", "resume",
            "network_request", "sdio_ready", "wifi_on",
        ])
        self.assertEqual("consistent_unverified", result["status"])
        self.assertTrue(result["wifi_symbolically_on"])
        self.assertEqual((1, 1), (result["suspend_count"], result["resume_count"]))

    def test_resume_never_grants_automatic_reconnection(self):
        for events, expected in (
            (["sdio_ready", "wifi_on"], "no_explicit_request"),
            (["network_request", "wifi_on"], "sdio_not_ready"),
            (["network_request", "sdio_ready", "wifi_on", "suspend"], "wifi_still_enabled"),
            (["network_request", "sdio_ready", "wifi_on", "network_release"], "wifi_still_enabled"),
            (["network_request", "sdio_ready", "wifi_off", "suspend", "resume", "wifi_on"], "no_explicit_request"),
            (["network_request", "sdio_ready", "wifi_off", "suspend", "resume", "network_request", "wifi_on"], "sdio_not_ready"),
        ):
            with self.subTest(events=events):
                self.assertEqual(expected, MOD.replay(events)["error"])

    def test_invalid_transitions_fail_closed(self):
        for events, expected in (
            (["resume"], "not_suspended"),
            (["suspend", "suspend"], "already_suspended"),
            (["suspend", "sdio_ready"], "asleep"),
            (["suspend", "network_request"], "asleep"),
            (["suspend", "wifi_off"], "asleep"),
        ):
            with self.subTest(events=events):
                self.assertEqual(expected, MOD.replay(events)["error"])

    def test_bounded_exact_event_input_without_mutation(self):
        for events in (None, {}, "suspend", [1], [True], ["reconnect"],
                       ["wifi_on", None], ["wifi_off"] * 129):
            with self.subTest(events=repr(events)[:60]):
                self.assertEqual("invalid_events", MOD.replay(events)["error"])
        source = ["network_request", "sdio_ready", "wifi_on"]
        self.assertEqual("consistent_unverified", MOD.replay(source)["status"])
        self.assertEqual(["network_request", "sdio_ready", "wifi_on"], source)

    def test_replay_is_pure_and_reports_no_hardware_verification(self):
        with patch("builtins.open", side_effect=AssertionError("I/O")), \
             patch("subprocess.run", side_effect=AssertionError("process")):
            report = MOD.replay(["sdio_ready", "suspend", "resume"])
        self.assertEqual("consistent_unverified", report["status"])
        self.assertFalse(report["hardware_verified"])
        self.assertFalse(report["rtc_verified"])


if __name__ == "__main__":
    unittest.main()
