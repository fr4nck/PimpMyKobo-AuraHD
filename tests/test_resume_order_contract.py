"""Host-only synthetic dependency tests; never touch the Kobo or its RTC."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "experimental/power-lab/resume_order_contract.py"
SPEC = importlib.util.spec_from_file_location("pmkb_resume_order_contract", SRC)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ResumeOrderTests(unittest.TestCase):
    def test_offline_start_and_two_complete_resume_cycles(self):
        events = ["sdio_quiesced", "suspend", "resume", "mmc_ready", "sdio_ready",
                  "sdio_quiesced", "suspend", "resume", "mmc_ready", "sdio_ready"]
        result = MOD.replay(events)
        self.assertEqual("consistent_unverified", result["status"])
        self.assertEqual((2, 2), (result["suspend_count"], result["resume_count"]))
        self.assertTrue(result["sdio_symbolically_ready"])
        self.assertFalse(result["rtc_trusted_claim"])
        self.assertFalse(result["hardware_verified"])

    def test_sdio_cannot_precede_mmc_or_survive_resume(self):
        for events in (["sdio_ready"],
                       ["sdio_quiesced", "suspend", "resume", "sdio_ready"],
                       ["mmc_ready", "sdio_ready", "sdio_quiesced", "suspend",
                        "resume", "sdio_ready"],
                       ["mmc_ready", "sdio_ready", "mmc_ready", "sdio_ready",
                        "sdio_quiesced", "suspend", "resume", "sdio_ready"]):
            with self.subTest(events=events):
                self.assertEqual("mmc_not_ready", MOD.replay(events)["error"])
        result = MOD.replay(["mmc_ready", "sdio_ready", "mmc_ready"])
        self.assertFalse(result["sdio_symbolically_ready"])

    def test_suspend_requires_prior_quiescence_and_no_nonsense_transition(self):
        for events, expected in ((["suspend"], "sdio_not_quiesced"),
                                 (["resume"], "not_suspended"),
                                 (["sdio_quiesced", "suspend", "suspend"], "already_suspended"),
                                 (["sdio_quiesced", "suspend", "mmc_ready"], "asleep"),
                                 (["sdio_quiesced", "suspend", "sdio_quiesced"], "asleep"),
                                 (["sdio_quiesced", "mmc_ready", "suspend"], "sdio_not_quiesced")):
            with self.subTest(events=events):
                self.assertEqual(expected, MOD.replay(events)["error"])

    def test_untrusted_rtc_requires_new_source_after_battery_loss(self):
        for events in (["rtc_sync_confirmed"],
                       ["time_source_confirmed", "rtc_untrusted", "rtc_sync_confirmed"],
                       ["time_source_confirmed", "sdio_quiesced", "suspend", "resume",
                        "rtc_sync_confirmed"]):
            with self.subTest(events=events):
                self.assertEqual("time_source_missing", MOD.replay(events)["error"])
        result = MOD.replay(["rtc_untrusted", "time_source_confirmed",
                             "rtc_sync_confirmed"])
        self.assertTrue(result["rtc_trusted_claim"])
        self.assertFalse(result["rtc_verified"])
        self.assertFalse(MOD.replay(["rtc_untrusted"])["rtc_trusted_claim"])
        self.assertFalse(MOD.replay(["time_source_confirmed", "rtc_sync_confirmed",
                                     "rtc_untrusted"])["rtc_trusted_claim"])

    def test_explicit_time_source_is_not_physical_rtc_verification(self):
        result = MOD.replay(["rtc_untrusted", "sdio_quiesced", "suspend", "resume",
                             "mmc_ready", "sdio_ready", "time_source_confirmed",
                             "rtc_sync_confirmed"])
        self.assertEqual("consistent_unverified", result["status"])
        self.assertTrue(result["rtc_trusted_claim"])
        for key in ("hardware_verified", "mmc_resume_verified",
                    "sdio_resume_verified", "rtc_verified"):
            self.assertIs(result[key], False)
        self.assertEqual("asleep", MOD.replay(["sdio_quiesced", "suspend",
                                                 "time_source_confirmed"])["error"])

    def test_input_restrictions_are_bounded_and_non_mutating(self):
        for events in (None, "resume", {}, [True], [1], ["bad_command"],
                       ["rtc_sync_confirmed", None], ["mmc_ready"] * 129):
            with self.subTest(data=repr(events)[:50]):
                self.assertEqual("invalid_events", MOD.replay(events)["error"])
        events = ["mmc_ready", "sdio_ready"]
        self.assertEqual("consistent_unverified", MOD.replay(events)["status"])
        self.assertEqual(["mmc_ready", "sdio_ready"], events)

    def test_api_performs_no_io_or_commands(self):
        with patch("builtins.open", side_effect=AssertionError("file access")), \
             patch("subprocess.run", side_effect=AssertionError("process")):
            result = MOD.replay(["rtc_untrusted", "time_source_confirmed",
                                 "rtc_sync_confirmed", "sdio_quiesced", "suspend",
                                 "resume", "mmc_ready", "sdio_ready"])
        self.assertEqual("consistent_unverified", result["status"])


if __name__ == "__main__":
    unittest.main()
