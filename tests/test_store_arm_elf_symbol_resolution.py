"""L08-N tests for dynamic symbols and symbol-version node pairing."""
import struct
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from arm_elf_symbol_resolution import (
    ArmSymbolResolutionError, compare_required_symbols,
)
from test_store_arm_elf_runtime_metadata import build_elf

DT_NULL = 0
DT_SYMTAB = 6
DT_SYMENT = 11
DT_HASH = 4
DT_GNU_HASH = 0x6FFFFEF5


def add_symbol_table(base, *, symbol_name="open", defined=False,
                     version_index=2, hash_kind="sysv"):
    data = bytearray(base)
    name_offset = 100
    data[512 + name_offset:512 + name_offset + len(symbol_name) + 1] = (
        symbol_name.encode("ascii") + b"\x00")
    phnum = struct.unpack_from("<H", data, 44)[0]
    dynamic_phdr = 116 if phnum == 3 else 84
    dynamic_size = struct.unpack_from("<I", data, dynamic_phdr + 16)[0]
    null_pos = None
    for offset in range(256, 256 + dynamic_size, 8):
        tag, _value = struct.unpack_from("<II", data, offset)
        if tag == DT_NULL:
            null_pos = offset
            break
    if null_pos is None:
        raise ValueError("fixture has no DT_NULL")
    tags = [(DT_SYMTAB, 0x1578), (DT_SYMENT, 16)]
    if hash_kind == "sysv":
        tags.append((DT_HASH, 0x15AA))
    elif hash_kind == "gnu":
        tags.append((DT_GNU_HASH, 0x15AA))
    elif hash_kind is not None:
        raise ValueError("unknown hash kind")
    for i, pair in enumerate(tags):
        struct.pack_into("<II", data, null_pos + i * 8, *pair)
    struct.pack_into("<II", data, null_pos + len(tags) * 8, DT_NULL, 0)
    new_size = dynamic_size + len(tags) * 8
    struct.pack_into("<I", data, dynamic_phdr + 16, new_size)
    struct.pack_into("<I", data, dynamic_phdr + 20, new_size)
    struct.pack_into("<IIIBBH", data, 1400, 0, 0, 0, 0, 0, 0)
    struct.pack_into("<IIIBBH", data, 1416, name_offset, 0, 0, 0x12, 0,
                     1 if defined else 0)
    if hash_kind == "sysv":
        struct.pack_into("<IIIII", data, 1450, 1, 2, 1, 0, 0)
    elif hash_kind == "gnu":
        struct.pack_into("<IIII", data, 1450, 1, 1, 1, 5)
        struct.pack_into("<I", data, 1466, 0)
        struct.pack_into("<II", data, 1470, 1, 1)
    struct.pack_into("<HH", data, 1536, 0, version_index)
    return bytes(data)


class ElfSymbolResolutionTests(unittest.TestCase):
    def test_versioned_symbol_and_node_match(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        libc = add_symbol_table(build_elf(
            kind=3, soname="libc.so.6", verdef="GLIBC_2.4"), defined=True)
        result = compare_required_symbols(candidate, {"libc.so.6": libc})
        self.assertEqual(result["verdict"], "symbol_pairs_observed")
        finding = result["symbol_findings"][0]
        self.assertEqual(finding["name"], "open")
        self.assertEqual(finding["required_library"], "libc.so.6")
        self.assertEqual(finding["required_version"], "GLIBC_2.4")
        self.assertEqual(finding["state"], "symbol_and_version_node_observed_in_library")
        self.assertTrue(result["all_versioned_symbol_pairs_observed"])
        self.assertFalse(result["symbol_versions_verified"])
        self.assertFalse(result["dynamic_symbol_resolution_verified"])
        self.assertFalse(result["launchable"])

    def test_sysv_and_gnu_hash_symbol_counts_are_supported(self):
        for hash_kind in ("sysv", "gnu"):
            with self.subTest(hash_kind=hash_kind):
                candidate = add_symbol_table(build_elf(
                    needed="libc.so.6", verneed="GLIBC_2.4"),
                    hash_kind=hash_kind)
                libc = add_symbol_table(build_elf(
                    kind=3, soname="libc.so.6", verdef="GLIBC_2.4"),
                    defined=True, hash_kind=hash_kind)
                result = compare_required_symbols(candidate, {"libc.so.6": libc})
                self.assertEqual(result["candidate_symbol_count"], 2)
                self.assertTrue(result["all_versioned_symbol_pairs_observed"])

    def test_missing_symbol_and_wrong_version_are_distinguished(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        wrong_name = add_symbol_table(build_elf(
            kind=3, soname="libc.so.6", verdef="GLIBC_2.4"),
            symbol_name="close", defined=True)
        result = compare_required_symbols(candidate, {"libc.so.6": wrong_name})
        self.assertEqual(result["symbol_findings"][0]["state"],
                         "required_symbol_not_exported")
        wrong_version = add_symbol_table(build_elf(
            kind=3, soname="libc.so.6", verdef="GLIBC_2.17"),
            defined=True)
        result = compare_required_symbols(candidate, {"libc.so.6": wrong_version})
        self.assertEqual(result["symbol_findings"][0]["state"],
                         "required_symbol_version_not_exported")
        self.assertFalse(result["all_versioned_symbol_pairs_observed"])

    def test_missing_library_and_soname_mismatch_are_explicit(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        missing = compare_required_symbols(candidate, {})
        self.assertEqual(missing["symbol_findings"][0]["state"],
                         "required_library_not_supplied")
        wrong = add_symbol_table(build_elf(
            kind=3, soname="libother.so", verdef="GLIBC_2.4"), defined=True)
        result = compare_required_symbols(candidate, {"libc.so.6": wrong})
        self.assertEqual(result["symbol_findings"][0]["state"],
                         "required_library_soname_mismatch")

    def test_unversioned_symbol_name_is_only_an_observation(self):
        candidate = add_symbol_table(build_elf(needed="libc.so.6"),
                                     version_index=1)
        libc = add_symbol_table(build_elf(kind=3, soname="libc.so.6"),
                                defined=True, version_index=1)
        result = compare_required_symbols(candidate, {"libc.so.6": libc})
        self.assertEqual(result["symbol_findings"][0]["state"],
                         "unversioned_symbol_name_observed")
        self.assertIsNone(result["all_versioned_symbol_pairs_observed"])
        self.assertFalse(result["dynamic_symbol_resolution_verified"])

    def test_missing_candidate_versym_blocks_version_claim(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4", include_versym=False))
        result = compare_required_symbols(candidate, {})
        self.assertEqual(result["verdict"], "candidate_symbol_version_table_missing")
        self.assertEqual(result["symbol_findings"], ())
        self.assertFalse(result["symbol_versions_verified"])

    def test_missing_hash_table_is_unavailable_not_a_pass(self):
        candidate = add_symbol_table(build_elf(needed="libc.so.6"),
                                     hash_kind=None)
        result = compare_required_symbols(candidate, {})
        self.assertEqual(result["verdict"], "candidate_symbol_table_unavailable")
        self.assertIsNone(result["all_undefined_symbol_names_observed"])

    def test_malformed_hash_count_is_rejected(self):
        candidate = bytearray(add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4")))
        struct.pack_into("<I", candidate, 1454, 0xFFFFFFFF)
        with self.assertRaisesRegex(
                ArmSymbolResolutionError, "invalid_candidate_symbol_table"):
            compare_required_symbols(bytes(candidate), {})

    def test_malformed_provider_and_bad_library_map_do_not_pass(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        result = compare_required_symbols(candidate, {"libc.so.6": b"not ELF"})
        self.assertEqual(result["symbol_findings"][0]["state"],
                         "required_library_metadata_rejected")
        with self.assertRaisesRegex(ArmSymbolResolutionError, "invalid_library_map"):
            compare_required_symbols(candidate, {"../libc.so.6": b"x"})

    def test_comparison_is_memory_only(self):
        candidate = add_symbol_table(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        libc = add_symbol_table(build_elf(
            kind=3, soname="libc.so.6", verdef="GLIBC_2.4"), defined=True)
        with patch("builtins.open", side_effect=AssertionError("host file read")):
            with patch("os.open", side_effect=AssertionError("host file read")):
                result = compare_required_symbols(candidate, {"libc.so.6": libc})
        self.assertTrue(result["all_versioned_symbol_pairs_observed"])
        self.assertFalse(result["hardware_verified"])
        self.assertFalse(result["launchable"])


if __name__ == "__main__":
    unittest.main()
