"""Pure synthetic ELF header fixtures: no compiler, downloads or execution."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experimental" / "store-v0" / "arm_elf_preflight.py"
spec = importlib.util.spec_from_file_location("pmkb_arm_preflight", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def header(*, machine=40, elf_type=2, size=52):
    value = bytearray(52)
    value[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", value, 16, elf_type, machine, 1)
    struct.pack_into("<H", value, 40, size)
    return bytes(value)


class ArmELFPreflightTests(unittest.TestCase):
    def test_arm_identity_does_not_grant_execution(self):
        for kind in (2, 3):
            with self.subTest(kind=kind):
                result = module.inspect_arm_elf(header(elf_type=kind))
                self.assertEqual(result["machine"], "EM_ARM")
                self.assertFalse(result["launchable"])
                self.assertEqual(result["scope"], "identity_only_unverified")

    def test_reject_incompatible_and_truncated(self):
        cases = ((b"", "elf_header_truncated"),
                 (b"N" * 52, "not_elf"),
                 (header(machine=62), "not_arm"),
                 (header(elf_type=1), "unsupported_elf_type"),
                 (header(size=51), "invalid_elf_header"),
                 (header()[:30], "elf_header_truncated"))
        for sample, code in cases:
            with self.subTest(reason=code):
                with self.assertRaises(module.ArmPreflightError) as raised:
                    module.inspect_arm_elf(sample)
                self.assertEqual(str(raised.exception), code)

    def test_elf_identity_and_input_immutability(self):
        sample = bytearray(header())
        sample[5] = 2
        with self.assertRaisesRegex(module.ArmPreflightError,
                                    "unsupported_elf_identity"):
            module.inspect_arm_elf(bytes(sample))
        with self.assertRaisesRegex(module.ArmPreflightError,
                                    "elf_header_truncated"):
            module.inspect_arm_elf("not bytes")


if __name__ == "__main__":
    unittest.main()
