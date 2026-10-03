"""Audit-only proposal: never run boot scripts or initialize devices.

The upstream call-flow test requires explicitly supplied local KOReader sources
and a native LuaJIT. Ordinary CI performs static checks without private assets.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
PROPOSAL = ROOT / "experimental/offline-audit/defaults.custom.lua"
PINNED = {
    "defaults.lua": "be7c335d81dc6d7bebc608e15584b569ac2a541fbbabd019ad53719e3853f78f",
    "frontend/luadefaults.lua": "efaf82c77f6959689e6ea8c0be0eeb6f4e33a59a21afecd192a0993b7075f126",
    "frontend/device/kobo/powerd.lua": "c9404c9ef84d4378bde8757a8156a7dee2a3a0c99b669e42cdf2dcac60c67725",
    "frontend/device/kobo/nickel_conf.lua": "2b4f7f98090ae507204f49b8878f048589a57e81e14f9d6f7421af8231c576fa",
}


class OfflineAuditTests(unittest.TestCase):
    def test_proposed_profile_is_data_only_and_outside_boot_overlay(self):
        content = re.sub(r"--[^\n]*", "", PROPOSAL.read_text())
        self.assertRegex(content, r"\A\s*return\s*\{\s*KOBO_LIGHT_ON_START\s*=\s*-1\s*,\s*KOBO_SYNC_BRIGHTNESS_WITH_NICKEL\s*=\s*false\s*,\s*\}\s*\Z")
        self.assertFalse((ROOT / "experimental/offline-rootfs/defaults.custom.lua").exists())
        self.assertFalse((ROOT / "experimental/offline-rootfs/opt/koreader/defaults.custom.lua").exists())

    @unittest.skipUnless(os.environ.get("PMKB_AUDIT_KOREADER_ROOT") and os.environ.get("PMKB_AUDIT_LUAJIT"), "Explicit local upstream files and native LuaJIT required")
    def test_actual_upstream_call_flow_with_synthetic_read_only_config(self):
        upstream = Path(os.environ["PMKB_AUDIT_KOREADER_ROOT"])
        for name, expected in PINNED.items():
            source = upstream / name
            self.assertTrue(source.is_file())
            self.assertEqual(expected, hashlib.sha256(source.read_bytes()).hexdigest(), name)
        result = subprocess.run([
            os.environ["PMKB_AUDIT_LUAJIT"],
            str(ROOT / "tests/offline-audit/nickel-settings.lua"),
            str(upstream), str(PROPOSAL),
        ], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    @unittest.skipUnless(os.environ.get("PMKB_AUDIT_KOREADER_ROOT") and os.environ.get("PMKB_AUDIT_QEMU_ARM"), "Explicit local ARM runtime and QEMU user-mode required")
    def test_arm_framebuffer_abi_without_any_device_call(self):
        upstream = Path(os.environ["PMKB_AUDIT_KOREADER_ROOT"])
        header = upstream / "ffi/mxcfb_kobo_h.lua"
        self.assertEqual("9ecc98d2ced79f6af819f9c57d7f04b00eb2d8c8c4940d5acadac422f9055166", hashlib.sha256(header.read_bytes()).hexdigest())
        runtime = upstream.parent.parent
        result = subprocess.run([
            os.environ["PMKB_AUDIT_QEMU_ARM"], "-L", str(runtime),
            str(upstream / "luajit"),
            str(ROOT / "tests/offline-audit/framebuffer-abi.lua"), str(upstream),
        ], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)
