"""L08-L synthetic ELF dynamic path and version-node parser tests."""
import struct
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

STORE = Path(__file__).resolve().parents[1] / "experimental" / "store-v0"
sys.path.insert(0, str(STORE))
from arm_elf_runtime_metadata import (
    ArmRuntimeMetadataError, inspect_arm_runtime_metadata,
    compare_required_version_nodes,
)

DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
DT_RPATH = 15
DT_TEXTREL = 22
DT_BIND_NOW = 24
DT_RUNPATH = 29
DT_FLAGS = 30
DT_VERSYM = 0x6FFFFFF0
DT_FLAGS_1 = 0x6FFFFFFB
DT_VERDEF = 0x6FFFFFFC
DT_VERDEFNUM = 0x6FFFFFFD
DT_VERNEED = 0x6FFFFFFE
DT_VERNEEDNUM = 0x6FFFFFFF


def build_elf(*, kind=2, needed=None, soname=None, rpath=None, runpath=None,
              verneed=None, verdef=None, include_versym=True, flags=0, flags1=0,
              interpreter=None, malformed=None):
    size = 2048
    data = bytearray(size)
    data[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", data, 16, kind, 40, 1)
    struct.pack_into("<I", data, 28, 52)
    struct.pack_into("<I", data, 36, 5 << 24)
    struct.pack_into("<HHH", data, 40, 52, 32, 3 if interpreter else 2)
    # One load segment maps file offset 0 to VA 0x1000.
    struct.pack_into("<IIIIIIII", data, 52, 1, 0, 0x1000, 0x1000,
                     size, size, 5, 4096)
    if interpreter:
        raw_interp = interpreter.encode("ascii") + b"\x00"
        interp_offset = size - len(raw_interp)
        data[interp_offset:] = raw_interp
        struct.pack_into("<IIIIIIII", data, 84, 3, interp_offset, 0, 0,
                         len(raw_interp), len(raw_interp), 4, 1)
        dynamic_phdr = 116
    else:
        dynamic_phdr = 84
    strings = bytearray(b"\x00")
    def add_string(value):
        offset = len(strings)
        strings.extend(value.encode("ascii") + b"\x00")
        return offset
    offsets = {
        "needed": add_string(needed) if needed is not None else None,
        "soname": add_string(soname) if soname is not None else None,
        "rpath": add_string(rpath) if rpath is not None else None,
        "runpath": add_string(runpath) if runpath is not None else None,
        "version_need_name": add_string(verneed) if verneed is not None else None,
        "version_def_name": add_string(verdef) if verdef is not None else None,
    }
    if len(strings) > 256:
        raise ValueError("fixture string table too large")
    data[512:512 + len(strings)] = strings
    tags = [(DT_STRTAB, 0x1200), (DT_STRSZ, 256)]
    if needed is not None:
        tags.append((DT_NEEDED, offsets["needed"]))
    if soname is not None:
        tags.append((DT_SONAME, offsets["soname"]))
    if rpath is not None:
        tags.append((DT_RPATH, offsets["rpath"]))
    if runpath is not None:
        tags.append((DT_RUNPATH, offsets["runpath"]))
    if verneed is not None:
        tags.extend(((DT_VERNEED, 0x1400), (DT_VERNEEDNUM, 1)))
    if verdef is not None:
        tags.extend(((DT_VERDEF, 0x1500), (DT_VERDEFNUM, 1)))
    if include_versym:
        tags.append((DT_VERSYM, 0x1600))
    if flags:
        tags.append((DT_FLAGS, flags))
    if flags1:
        tags.append((DT_FLAGS_1, flags1))
    if malformed == "duplicate_runpath":
        tags.extend(((DT_RUNPATH, offsets["runpath"]),))
    if malformed == "missing_strtab":
        tags = [(x, y) for x, y in tags if x != DT_STRTAB]
    if malformed == "unterminated_dynamic":
        tags = [(x, y) for x, y in tags if x != 0]
    tags.append((0 if malformed != "unterminated_dynamic" else 0x7FFFFFFF, 0))
    dynamic_size = len(tags) * 8
    struct.pack_into("<IIIIIIII", data, dynamic_phdr, 2, 256, 0x1100, 0x1100,
                     dynamic_size, dynamic_size, 6, 4)
    for i, pair in enumerate(tags):
        struct.pack_into("<II", data, 256 + i * 8, *pair)
    if verneed is not None:
        struct.pack_into("<HHIII", data, 1024, 1, 1, offsets["needed"], 16,
                         0 if malformed != "version_need_next" else 16)
        struct.pack_into("<IHHII", data, 1040, 0x12345678, 0, 2,
                         offsets["version_need_name"], 0)
    if verdef is not None:
        struct.pack_into("<HHHHIII", data, 1280, 1, 0, 2, 1, 0x87654321,
                         20, 0)
        struct.pack_into("<II", data, 1300, offsets["version_def_name"], 0)
    return bytes(data)


class ArmRuntimeMetadataTests(unittest.TestCase):
    def test_reports_interpreter_from_pt_interp(self):
        report = inspect_arm_runtime_metadata(build_elf(
            needed="libc.so.6", interpreter="/lib/ld-linux.so.3"))
        self.assertEqual(report["identity"]["interpreter"], "/lib/ld-linux.so.3")
        self.assertFalse(report["launchable"])

    def test_reports_rpath_runpath_and_dangerous_components(self):
        data = build_elf(needed="libc.so.6", soname="app",
                         rpath="/opt/old::relative",
                         runpath="$ORIGIN/../lib:/usr/lib")
        report = inspect_arm_runtime_metadata(data)
        self.assertEqual(report["needed"], ("libc.so.6",))
        self.assertEqual(report["soname"], "app")
        self.assertEqual(report["rpath"]["absolute_entries"], ("/opt/old",))
        self.assertEqual(report["rpath"]["empty_entry_indexes"], (1,))
        self.assertTrue(report["rpath"]["empty_component_may_use_current_directory"])
        self.assertEqual(report["runpath"]["origin_token_entries"], ("$ORIGIN/../lib",))
        self.assertIn("both_rpath_and_runpath_present", report["warnings"])
        self.assertIn("empty_rpath_component", report["warnings"])
        self.assertIn("absolute_runpath_component", report["warnings"])
        self.assertFalse(report["launchable"])

    def test_reports_textrel_and_bind_now_flags(self):
        report = inspect_arm_runtime_metadata(build_elf(
            needed="libc.so.6", flags=0x4 | 0x8, flags1=1))
        self.assertFalse(report["textrel_tag_present"])
        self.assertTrue(report["dynamic_flags"]["textrel_flag"])
        self.assertTrue(report["dynamic_flags"]["bind_now_flag"])
        self.assertTrue(report["dynamic_flags"]["bind_now_flag_1"])
        self.assertIn("text_relocations_declared", report["warnings"])

    def test_reads_version_need_and_definition_nodes(self):
        executable = inspect_arm_runtime_metadata(build_elf(
            needed="libc.so.6", verneed="GLIBC_2.4"))
        library = inspect_arm_runtime_metadata(build_elf(
            kind=3, soname="libc.so.6", verdef="GLIBC_2.4"))
        self.assertEqual(executable["version_requirements"][0]["library"], "libc.so.6")
        self.assertEqual(executable["version_requirements"][0]["versions"][0]["name"],
                         "GLIBC_2.4")
        self.assertEqual(library["version_definitions"][0]["name"], "GLIBC_2.4")
        self.assertTrue(executable["symbol_version_table_present"])
        self.assertFalse(executable["symbol_versions_verified"])

    def test_version_node_names_match_without_symbol_resolution_claim(self):
        exe = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        lib = build_elf(kind=3, soname="libc.so.6", verdef="GLIBC_2.4")
        result = compare_required_version_nodes(exe, {"libc.so.6": lib})
        self.assertTrue(result["all_required_version_nodes_observed"])
        self.assertEqual(result["libraries_not_supplied"], ())
        self.assertFalse(result["symbol_versions_verified"])
        self.assertFalse(result["transitive_dependencies_verified"])
        self.assertFalse(result["launchable"])

    def test_missing_library_and_missing_version_node_stay_unresolved(self):
        exe = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        missing = compare_required_version_nodes(exe, {})
        self.assertEqual(missing["binary_version_requirements"][0]["state"],
                         "library_metadata_not_supplied")
        self.assertEqual(missing["libraries_not_supplied"], ("libc.so.6",))
        lib = build_elf(kind=3, soname="libc.so.6", verdef="GLIBC_2.17")
        absent = compare_required_version_nodes(exe, {"libc.so.6": lib})
        self.assertEqual(absent["binary_version_requirements"][0]["state"],
                         "required_version_nodes_missing")
        self.assertFalse(absent["all_required_version_nodes_observed"])

    def test_soname_mismatch_and_nonshared_library_are_not_accepted(self):
        exe = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        wrong = build_elf(kind=3, soname="libother.so", verdef="GLIBC_2.4")
        result = compare_required_version_nodes(exe, {"libc.so.6": wrong})
        self.assertEqual(result["binary_version_requirements"][0]["state"],
                         "library_soname_mismatch")
        nonshared = build_elf(kind=2, soname="libc.so.6", verdef="GLIBC_2.4")
        result = compare_required_version_nodes(exe, {"libc.so.6": nonshared})
        self.assertEqual(result["binary_version_requirements"][0]["state"],
                         "library_not_et_dyn")

    def test_static_elf_has_no_dynamic_claims(self):
        data = bytearray(build_elf())
        struct.pack_into("<H", data, 44, 0)
        report = inspect_arm_runtime_metadata(bytes(data))
        self.assertEqual(report["scope"], "static_elf_identity_only")
        self.assertIsNone(report["rpath"])
        self.assertEqual(report["version_requirements"], ())
        self.assertFalse(report["launchable"])

    def test_malformed_dynamic_and_version_chains_fail_closed(self):
        for malformed, reason in (
            ("duplicate_runpath", "duplicate_dynamic_tag"),
            ("missing_strtab", "invalid_dynamic_strings"),
            ("unterminated_dynamic", "unterminated_dynamic_table"),
            ("version_need_next", "invalid_version_need_chain"),
        ):
            with self.subTest(malformed=malformed):
                data = build_elf(needed="libc.so.6", runpath="$ORIGIN/lib",
                                 verneed="GLIBC_2.4", malformed=malformed)
                with self.assertRaisesRegex(ArmRuntimeMetadataError, reason):
                    inspect_arm_runtime_metadata(data)

    def test_bad_version_addresses_and_library_map_limits_are_refused(self):
        data = bytearray(build_elf(needed="libc.so.6", verneed="GLIBC_2.4"))
        for pos in range(256, min(len(data), 256 + 4096), 8):
            tag, _value = struct.unpack_from("<II", data, pos)
            if tag == DT_VERNEED:
                struct.pack_into("<I", data, pos + 4, 0x90000000)
                break
            if tag == 0:
                break
        with self.assertRaisesRegex(ArmRuntimeMetadataError, "invalid_version_need_record"):
            inspect_arm_runtime_metadata(bytes(data))
        with self.assertRaisesRegex(ArmRuntimeMetadataError, "invalid_library_metadata_map"):
            compare_required_version_nodes(build_elf(), {"../libc.so.6": build_elf()})

    def test_comparison_is_memory_only(self):
        exe = build_elf(needed="libc.so.6", verneed="GLIBC_2.4")
        lib = build_elf(kind=3, soname="libc.so.6", verdef="GLIBC_2.4")
        with patch("builtins.open", side_effect=AssertionError("filesystem read")):
            with patch("os.open", side_effect=AssertionError("filesystem read")):
                result = compare_required_version_nodes(exe, {"libc.so.6": lib})
        self.assertTrue(result["all_required_version_nodes_observed"])
        self.assertFalse(result["hardware_verified"])


if __name__ == "__main__":
    unittest.main()
