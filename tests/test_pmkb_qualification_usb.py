import importlib.util
import json
import re
import shutil
import subprocess
import sys
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
    def test_iso_staged_backend_imports_and_validates_sealed_fixture(self):
        # Stage exactly the backend install lines from the builder, without
        # access to sibling scripts left behind in the repository.
        source = (ROOT / "tools" / "build-qualification-live.sh").read_text(encoding="utf-8")
        variables = dict(re.findall(r'^(\w+)="\$REPO_DIR/(tools/[^"\n]+)"$', source, re.MULTILINE))
        installs = re.findall(
            r'^install -m 0644 "\$(\w+)" config/includes.chroot/(opt/pmkb/tools/[^\s]+)$',
            source, re.MULTILINE,
        )
        self.assertTrue(installs, "no backend payload found in builder")
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td)
            for variable, destination in installs:
                target = payload / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / variables[variable], target)
            ui = payload / "usr/local/sbin/pmkb-qualification"
            ui.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / variables["UI"], ui)
            fixture = payload / "fixture"
            generated = subprocess.run(
                [sys.executable, "-I", "-B", str(ROOT / "tests/make_qualification_live_fixture.py"), str(fixture)],
                capture_output=True, text=True,
            )
            self.assertEqual(0, generated.returncode, generated.stderr)
            checked = subprocess.run(
                [sys.executable, "-I", "-B", "-c", """
import hashlib, importlib.machinery, importlib.util, sys
from pathlib import Path
ui, backend_path, fixture = map(Path, sys.argv[1:])
loader = importlib.machinery.SourceFileLoader("payload_ui", str(ui))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
backend = module.load_backend(backend_path)
inspector = backend.legacy.load_inspector()
assert Path(inspector.__file__).parent == backend_path.parent
assert Path(backend.simulation.rebuild.__file__).parent == backend_path.parent
plan_path = fixture / "plan.json"
sha = hashlib.sha256(plan_path.read_bytes()).hexdigest()
plan, actual = backend.validate_sealed_plan(plan_path, fixture / "fixture.img", sha)
assert actual == sha
assert plan["write_authorized"] is False
assert plan["physical_restore_eligible"] is False
""", str(ui), str(payload / "opt/pmkb/tools/restore-p1-linux.py"), str(fixture)],
                cwd=payload, capture_output=True, text=True,
            )
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)

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

    def test_language_defaults_to_french_and_can_select_english(self):
        self.assertEqual("fr", mod.choose_language(input_func=lambda _prompt: ""))
        self.assertEqual("en", mod.choose_language(input_func=lambda _prompt: "2"))

    def test_console_keymaps_are_discovered_and_default_french_is_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fr = root / "i386" / "azerty" / "fr.kmap.gz"
            us = root / "i386" / "qwerty" / "us.kmap.gz"
            fr.parent.mkdir(parents=True)
            us.parent.mkdir(parents=True)
            fr.write_bytes(b"fixture")
            us.write_bytes(b"fixture")
            calls = []

            def fake_run(args, **_kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0, "", "")

            keymaps = mod.available_keymaps(root)
            self.assertEqual(fr, keymaps["i386/azerty/fr"])
            self.assertEqual(us, keymaps["i386/qwerty/us"])
            selected = mod.choose_keymap(
                "fr", input_func=lambda _prompt: "", root=root, run=fake_run,
            )
            self.assertEqual("i386/azerty/fr", selected)
            self.assertEqual(["loadkeys", str(fr)], calls[0])

    def test_power_controls_delegate_to_systemd(self):
        calls = []

        def fake_run(args, **_kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        mod.systemctl_action("reboot", run=fake_run)
        mod.systemctl_action("poweroff", run=fake_run)
        self.assertEqual([["systemctl", "reboot"], ["systemctl", "poweroff"]], calls)
        with self.assertRaises(mod.QualificationError):
            mod.systemctl_action("halt", run=fake_run)

    def test_live_builder_ships_keymaps_and_pmkb_grub_splash(self):
        source = (ROOT / "tools" / "build-qualification-live.sh").read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^kbd$")
        self.assertRegex(source, r"(?m)^console-data$")
        self.assertIn("config/bootloaders/grub-pc/splash.png", source)
        self.assertIn('LOGO="$REPO_DIR/assets/branding/pmkb-logo-original.png"', source)

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

    def test_menu_has_power_controls_instead_of_dead_quit(self):
        source = (ROOT / "tools" / "pmkb-qualification-usb.py").read_text(encoding="utf-8")
        self.assertIn('"menu_6": "Redémarrer le PC"', source)
        self.assertIn('"menu_7": "Éteindre le PC"', source)
        self.assertIn('systemctl_action("reboot")', source)
        self.assertIn('systemctl_action("poweroff")', source)
        self.assertNotIn('print(" 0. Quitter")', source)
        service = (
            ROOT / "live" / "pmkb-qualification" / "pmkb-qualification.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Restart=no", service)
        self.assertNotIn("Restart=always", service)


if __name__ == "__main__":
    unittest.main()
