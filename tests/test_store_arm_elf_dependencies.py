"""Synthetic ELF32 ARM dependency tests. No toolchains or device writes."""
import sys
import struct
from pathlib import Path
import unittest

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from arm_elf_dependencies import inspect_arm_dependencies, ArmPreflightError


def elf(*, needed=True, corrupt=False):
    data = bytearray(256)
    data[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", data, 16, 2, 40, 1)
    struct.pack_into("<I", data, 28, 52)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<HHH", data, 40, 52, 32, 2 if needed else 0)
    if needed:
        # PT_LOAD maps virtual 0x1000 to physical file offset 128
        struct.pack_into("<IIIIIIII", data, 52, 1, 128, 0x1000, 0, 128, 128, 4, 4)
        struct.pack_into("<IIIIIIII", data, 84, 2, 160, 0x1020, 0, 32, 32, 4, 4)
        # string table at virtual 0x1050/file offset 208
        struct.pack_into("<II", data, 160, 5, 0x1050)
        struct.pack_into("<II", data, 168, 10, 16)
        struct.pack_into("<II", data, 176, 1, 1 if not corrupt else 99)
        struct.pack_into("<II", data, 184, 0, 0)
        data[208:224] = b"\x00libc.so.6\x00" + bytes(5)
    return bytes(data)


class ArmDependencyTests(unittest.TestCase):
    def test_valid_identity_and_dynamic_name_not_launchable(self):
        result = inspect_arm_dependencies(elf())
        self.assertEqual(result["needed"], ("libc.so.6",))
        self.assertFalse(result["launchable"])
        self.assertFalse(result["identity"]["launchable"])

    def test_search_path_tags_are_observations_not_runtime_proof(self):
        for tag, key in ((15, "rpath_observed"), (29, "runpath_observed")):
            with self.subTest(tag=tag):
                data = bytearray(elf())
                # Use unused dynamic table space by replacing DT_NULL with
                # the tag, followed by DT_NULL at the next slot. The fixture
                # needs an extended table and string table.
                struct.pack_into("<I", data, 84 + 16, 40)
                struct.pack_into("<I", data, 84 + 20, 40)
                struct.pack_into("<I", data, 172, 28)
                struct.pack_into("<II", data, 184, tag, 11)
                struct.pack_into("<II", data, 192, 0, 0)
                data[219:227] = b"/opt/lib\x00"
                result = inspect_arm_dependencies(bytes(data))
                self.assertEqual(result[key], "/opt/lib")
                self.assertFalse(result["loader_search_paths_verified"])

    def test_search_path_outside_strings_is_rejected(self):
        data = bytearray(elf())
        struct.pack_into("<II", data, 184, 29, 100)
        struct.pack_into("<II", data, 192, 0, 0)
        struct.pack_into("<I", data, 84 + 16, 40)
        struct.pack_into("<I", data, 84 + 20, 40)
        with self.assertRaises(ArmPreflightError):
            inspect_arm_dependencies(bytes(data))

    def test_static_has_no_dynamic_dependencies(self):
        self.assertEqual(inspect_arm_dependencies(elf(needed=False))["needed"], ())

    def test_reject_missing_dynamic_strings_and_bad_segment(self):
        missing = bytearray(elf())
        struct.pack_into("<II", missing, 168, 10, 0)
        with self.assertRaisesRegex(ArmPreflightError, "invalid_dynamic_strings"):
            inspect_arm_dependencies(bytes(missing))
        bad = bytearray(elf())
        struct.pack_into("<I", bad, 56, 250)
        with self.assertRaisesRegex(ArmPreflightError, "invalid_segment_bounds"):
            inspect_arm_dependencies(bytes(bad))

    def test_invalid_name_offset_rejected(self):
        with self.assertRaisesRegex(ArmPreflightError, "invalid_needed_name"):
            inspect_arm_dependencies(elf(corrupt=True))


if __name__ == "__main__":
    unittest.main()
