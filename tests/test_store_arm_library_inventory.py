"""L08-D: strict synthetic SONAME inventory; no Kobo device operations."""
import json
from pathlib import Path
import struct
import sys
import unittest

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from arm_library_inventory import (LibraryInventoryError, read_library_inventory,
                                   assess_needed_libraries, inspect_elf_with_inventory)


def library_json(libraries=(), coverage="partial"):
    return json.dumps({
        "schema": "pmkb-elf-libraries-v1",
        "scope": "synthetic_fixture",
        "coverage": coverage,
        "libraries": list(libraries)
    }, sort_keys=True).encode("utf-8")


def elf_needing_libc():
    """ELF32 EABI5 with one synthetic PT_DYNAMIC DT_NEEDED entry."""
    data = bytearray(256)
    data[:7] = bytes((127, 69, 76, 70, 1, 1, 1))
    struct.pack_into("<HHI", data, 16, 2, 40, 1)
    struct.pack_into("<I", data, 28, 52)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<HHH", data, 40, 52, 32, 2)
    struct.pack_into("<IIIIIIII", data, 52,
                     1, 128, 0x1000, 0, 128, 128, 4, 4)
    struct.pack_into("<IIIIIIII", data, 84,
                     2, 160, 0x1020, 0, 32, 32, 4, 4)
    for at, tag, value in ((160, 5, 0x1050), (168, 10, 16),
                           (176, 1, 1), (184, 0, 0)):
        struct.pack_into("<II", data, at, tag, value)
    data[208:224] = bytes((0,)) + b"libc.so.6" + bytes((0,)) + bytes(5)
    return bytes(data)


class ArmLibraryInventoryTests(unittest.TestCase):
    def test_partial_inventory_distinguishes_unobserved_from_matched(self):
        inventory = read_library_inventory(library_json(("libz.so.1",)))
        result = assess_needed_libraries(("libc.so.6", "libz.so.1"), inventory)
        self.assertEqual(result["matched_in_fixture"], ("libz.so.1",))
        self.assertEqual(result["not_observed"], ("libc.so.6",))
        self.assertEqual(result["not_in_fixture"], ())
        self.assertFalse(result["launchable"])

    def test_complete_fixture_absence_never_claims_real_abi(self):
        inventory = read_library_inventory(library_json((), "complete"))
        result = assess_needed_libraries(("libc.so.6",), inventory)
        self.assertEqual(result["not_in_fixture"], ("libc.so.6",))
        self.assertEqual(result["not_observed"], ())
        self.assertEqual(result["comparison"], "soname_only_no_abi_proof")
        self.assertFalse(result["launchable"])

    def test_empty_dependencies_are_not_proof_of_compatibility(self):
        result = assess_needed_libraries((), read_library_inventory(library_json()))
        self.assertEqual(result["needed"], ())
        self.assertFalse(result["launchable"])

    def test_real_parser_integration_with_synthetic_elf(self):
        output = inspect_elf_with_inventory(
            elf_needing_libc(), library_json(("libc.so.6",), "complete"))
        self.assertEqual(output["elf"]["needed"], ("libc.so.6",))
        self.assertEqual(output["libraries"]["matched_in_fixture"], ("libc.so.6",))
        self.assertFalse(output["elf"]["launchable"])
        self.assertFalse(output["libraries"]["launchable"])
        self.assertFalse(output["launchable"])
        self.assertEqual(output["scope"], "synthetic_comparison_only")

    def test_reject_undeclared_real_scope_and_invalid_schema(self):
        for field, value, error in (
            ("scope", "kobo_verified", "unsupported_inventory_scope"),
            ("schema", "unknown", "invalid_inventory_schema"),
            ("coverage", "observed", "invalid_inventory_coverage"),
            ("libraries", "libc.so.6", "invalid_inventory_libraries"),
            ("libraries", ["../libc.so.6"], "invalid_library_name"),
            ("libraries", ["libc.so.6", "LIBC.SO.6"], "duplicate_library_name"),
        ):
            with self.subTest(field=field, value=value):
                data = json.loads(library_json())
                data[field] = value
                with self.assertRaises(LibraryInventoryError) as exc:
                    read_library_inventory(json.dumps(data).encode("utf-8"))
                self.assertEqual(str(exc.exception), error)

    def test_reject_duplicate_json_keys_and_nonfinite(self):
        duplicate = (b'{"schema":"pmkb-elf-libraries-v1",'
                     b'"schema":"pmkb-elf-libraries-v1"}')
        for raw, reason in (
            (duplicate, "duplicate_inventory_key"),
            (b'{"libraries":NaN}', "invalid_inventory_json"),
            (b"\xff", "invalid_inventory_json"),
            (b"[" * 1200 + b"]" * 1199, "invalid_inventory_json"),
            (b"x" * 16385, "invalid_inventory_size"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaises(LibraryInventoryError) as exc:
                    read_library_inventory(raw)
                self.assertEqual(str(exc.exception), reason)

    def test_bounded_name_list_and_safe_needed_input(self):
        for names, reason in (
            ([f"lib{i}.so" for i in range(129)], "invalid_inventory_libraries"),
            (["lib/x.so"], "invalid_library_name"),
            ([7], "invalid_library_name"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(LibraryInventoryError, reason):
                    read_library_inventory(library_json(names))
        inventory = read_library_inventory(library_json(("libc.so.6",)))
        forged = dict(inventory, libraries=("libc.so.6", "LIBC.SO.6"))
        with self.assertRaisesRegex(LibraryInventoryError, "invalid_inventory_source"):
            assess_needed_libraries(("libc.so.6",), forged)
        for required in (["libc.so.6"], ("libc.so.6", "libc.so.6"),
                         ("../libc.so.6",), ()):
            if required == ():
                self.assertFalse(assess_needed_libraries(required, inventory)["launchable"])
            else:
                with self.assertRaisesRegex(
                        LibraryInventoryError, "invalid_needed_names"):
                    assess_needed_libraries(required, inventory)


if __name__ == "__main__":
    unittest.main()
