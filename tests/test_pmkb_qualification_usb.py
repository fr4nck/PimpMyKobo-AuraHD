import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pmkb_qualification_usb",
    ROOT / "tools" / "pmkb-qualification-usb.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

MANIFEST = json.loads(
    (ROOT / "live" / "pmkb-qualification" / "candidate.json").read_text(encoding="utf-8")
)
PLAN_SHA = "1" * 64


class FakeBackend:
    def __init__(self):
        self.calls = []
        self.verify_calls = []

    def execute_sealed_plan(self, plan_path, image, journal, **kwargs):
        self.calls.append((plan_path, image, journal, kwargs))
        if kwargs.get("write_p1"):
            return {
                "status": "ok",
                "complete": True,
                "rollback": "/persist/original-p1.img",
                "p1_reread_sha256": MANIFEST["image_sha256"],
                "outside_p1_unchanged": True,
            }
        return {
            "status": "device_ready_read_only",
            "complete": True,
            "plan_sha256": PLAN_SHA,
            "whole_target_matches_backup": True,
        }

    def verify_written_sealed_plan(self, plan_path, image, **kwargs):
        self.verify_calls.append((plan_path, image, kwargs))
        return {
            "status": "verified",
            "complete": True,
            "p1_reread_sha256": MANIFEST["image_sha256"],
            "outside_p1_unchanged": True,
        }


class QualificationUsbTests(unittest.TestCase):
    def test_manifest_is_still_pinned_to_frozen_candidate(self):
        self.assertEqual(268435968, MANIFEST["image_size"])
        self.assertEqual(
            "7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c",
            MANIFEST["image_sha256"],
        )
        self.assertEqual(
            "fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a",
            MANIFEST["partitions"][1]["sha256"],
        )

    def test_confirmation_is_candidate_and_plan_specific(self):
        self.assertEqual(
            "ECRIRE P1 7980fec1 PLAN 11111111",
            mod.confirmation_phrase(MANIFEST, PLAN_SHA),
        )

    def test_ui_contains_no_physical_writer(self):
        source = (ROOT / "tools" / "pmkb-qualification-usb.py").read_text(encoding="utf-8")
        self.assertNotIn("def write_partition", source)
        self.assertNotIn("os.open(", source)
        self.assertNotIn('open("r+b"', source)
        self.assertIn("execute_sealed_plan", source)

    def test_write_delegates_to_single_backend_after_readonly_preflight(self):
        backend = FakeBackend()
        device = Path("/dev/sdz")
        plan = Path("/opt/pmkb/restore-plan.json")
        image = Path("/opt/pmkb/candidate.img")
        phrase = mod.confirmation_phrase(MANIFEST, PLAN_SHA)
        with tempfile.TemporaryDirectory() as td:
            result = mod.perform_write(
                backend,
                plan,
                image,
                MANIFEST,
                PLAN_SHA,
                device,
                Path(td),
                input_func=lambda _prompt: phrase,
            )
        self.assertEqual("ok", result["status"])
        self.assertEqual(2, len(backend.calls))
        first = backend.calls[0][3]
        second = backend.calls[1][3]
        self.assertTrue(first["check_device"])
        self.assertFalse(first.get("write_p1", False))
        self.assertEqual(device, first["device"])
        self.assertTrue(second["write_p1"])
        self.assertEqual(device, second["device"])
        self.assertEqual(PLAN_SHA, second["authorize_plan_sha256"])

    def test_wrong_confirmation_never_calls_write_backend(self):
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(mod.QualificationError):
                mod.perform_write(
                    backend,
                    Path("/opt/pmkb/restore-plan.json"),
                    Path("/opt/pmkb/candidate.img"),
                    MANIFEST,
                    PLAN_SHA,
                    Path("/dev/sdz"),
                    Path(td),
                    input_func=lambda _prompt: "NON",
                )
        self.assertEqual(1, len(backend.calls))
        self.assertTrue(backend.calls[0][3]["check_device"])

    def test_postwrite_verification_is_delegated_to_backend(self):
        backend = FakeBackend()
        result = mod.verify_after_write(
            backend,
            Path("/opt/pmkb/restore-plan.json"),
            Path("/opt/pmkb/candidate.img"),
            PLAN_SHA,
            Path("/dev/sdz"),
        )
        self.assertEqual("verified", result["status"])
        self.assertEqual(1, len(backend.verify_calls))
        self.assertEqual(Path("/dev/sdz"), backend.verify_calls[0][2]["device"])

    def test_target_is_always_explicit(self):
        with self.assertRaises(mod.QualificationError):
            mod.ask_device(input_func=lambda _prompt: "sdb")
        self.assertEqual(
            Path("/dev/sdb"),
            mod.ask_device(input_func=lambda _prompt: "/dev/sdb"),
        )

    def test_systemd_quit_does_not_restart_menu(self):
        service = (
            ROOT / "live" / "pmkb-qualification" / "pmkb-qualification.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Restart=no", service)
        self.assertNotIn("Restart=always", service)


if __name__ == "__main__":
    unittest.main()
