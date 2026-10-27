"""L08-L: bounded ELF32 ARM dynamic path and symbol-version-node inventory.

This is static metadata only. It never opens files, resolves paths, loads
shared objects or runs target code. A version-node name match does not prove
that a referenced symbol exists or that the Kobo loader can resolve it.
"""
import struct

from arm_elf_dependencies import inspect_arm_dependencies, ArmPreflightError

MAX_ELF_BYTES = 16 * 1024 * 1024
MAX_DYNAMIC_BYTES = 4096
MAX_STRING_TABLE_BYTES = 4096
MAX_NEEDED = 32
MAX_VERSION_RECORDS = 128
MAX_VERSION_AUX = 128
MAX_LIBRARY_BYTES_TOTAL = 64 * 1024 * 1024

DT_NULL = 0
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
DF_TEXTREL = 0x4
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
PT_LOAD = 1
PT_DYNAMIC = 2

_SINGLETON_TAGS = frozenset((
    DT_STRTAB, DT_STRSZ, DT_SONAME, DT_RPATH, DT_RUNPATH, DT_FLAGS,
    DT_FLAGS_1, DT_VERNEED, DT_VERNEEDNUM, DT_VERDEF, DT_VERDEFNUM,
    DT_VERSYM,
))


class ArmRuntimeMetadataError(ValueError):
    """Stable rejection code for malformed or unsupported ELF metadata."""


def _add32(a, b, reason):
    if type(a) is not int or type(b) is not int or a < 0 or b < 0 or a > 0xFFFFFFFF - b:
        raise ArmRuntimeMetadataError(reason)
    return a + b


def _read_u16(data, offset, reason):
    if offset < 0 or offset > len(data) - 2:
        raise ArmRuntimeMetadataError(reason)
    return struct.unpack_from("<H", data, offset)[0]


def _read_u32(data, offset, reason):
    if offset < 0 or offset > len(data) - 4:
        raise ArmRuntimeMetadataError(reason)
    return struct.unpack_from("<I", data, offset)[0]


class _ELF:
    def __init__(self, data):
        if type(data) is not bytes or not 52 <= len(data) <= MAX_ELF_BYTES:
            raise ArmRuntimeMetadataError("invalid_elf_size")
        try:
            self.base = inspect_arm_dependencies(data)
        except ArmPreflightError as exc:
            # Preserve the existing stable parser reason for malformed dynamic
            # tables and dependency names; callers can distinguish the failure.
            raise ArmRuntimeMetadataError(str(exc)) from exc
        except (ValueError, struct.error) as exc:
            raise ArmRuntimeMetadataError("invalid_arm_elf") from exc
        self.data = data
        self.identity = self.base["identity"]
        phoff = _read_u32(data, 28, "invalid_program_headers")
        phentsize = _read_u16(data, 42, "invalid_program_headers")
        phnum = _read_u16(data, 44, "invalid_program_headers")
        if phnum > 32 or (phnum and
                (phentsize != 32 or phoff < 52 or phoff + phnum * 32 > len(data))):
            raise ArmRuntimeMetadataError("invalid_program_headers")
        self.loads = []
        self.dynamics = []
        for i in range(phnum):
            pos = phoff + i * 32
            p_type, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, _flags, _align = (
                struct.unpack_from("<IIIIIIII", data, pos))
            if (p_offset > len(data) or p_filesz > len(data) - p_offset or
                    p_memsz < p_filesz):
                raise ArmRuntimeMetadataError("invalid_segment_bounds")
            if p_type == PT_LOAD:
                if p_vaddr > 0xFFFFFFFF - p_filesz:
                    raise ArmRuntimeMetadataError("invalid_load_segment")
                self.loads.append((p_vaddr, p_offset, p_filesz))
            elif p_type == PT_DYNAMIC:
                if p_filesz > MAX_DYNAMIC_BYTES or p_filesz % 8:
                    raise ArmRuntimeMetadataError("invalid_dynamic_table")
                self.dynamics.append((p_offset, p_vaddr, p_filesz))
        if len(self.dynamics) > 1:
            raise ArmRuntimeMetadataError("multiple_dynamic_tables")
        self.entries = []
        if self.dynamics:
            off, _va, size = self.dynamics[0]
            if size < 8:
                raise ArmRuntimeMetadataError("invalid_dynamic_table")
            for cursor in range(off, off + size, 8):
                tag, value = struct.unpack_from("<II", data, cursor)
                if tag == DT_NULL:
                    break
                self.entries.append((tag, value))
            else:
                raise ArmRuntimeMetadataError("unterminated_dynamic_table")
            if len(self.entries) > 512:
                raise ArmRuntimeMetadataError("dynamic_entry_limit")
        self.by_tag = {}
        for tag, value in self.entries:
            self.by_tag.setdefault(tag, []).append(value)
        for tag in _SINGLETON_TAGS:
            if len(self.by_tag.get(tag, ())) > 1:
                raise ArmRuntimeMetadataError("duplicate_dynamic_tag")
        if not self.dynamics:
            self.strings = b""
            self.needed = tuple(self.base["needed"])
            self.soname = None
            return
        tables = self.by_tag.get(DT_STRTAB, [])
        sizes = self.by_tag.get(DT_STRSZ, [])
        if len(tables) != 1 or len(sizes) != 1 or not 0 < sizes[0] <= MAX_STRING_TABLE_BYTES:
            raise ArmRuntimeMetadataError("invalid_dynamic_strings")
        start = self.map_vaddr(tables[0], sizes[0], "unmapped_dynamic_strings")
        self.strings = data[start:start + sizes[0]]
        self.needed = tuple(self.base["needed"])
        sonames = self.by_tag.get(DT_SONAME, [])
        self.soname = self.string(sonames[0], "invalid_soname") if sonames else None

    def map_vaddr(self, address, size, reason):
        if type(address) is not int or type(size) is not int or address < 0 or size < 0:
            raise ArmRuntimeMetadataError(reason)
        if address > 0xFFFFFFFF - size:
            raise ArmRuntimeMetadataError(reason)
        found = []
        for va, offset, filesz in self.loads:
            if va <= address and address - va <= filesz:
                delta = address - va
                if size <= filesz - delta:
                    found.append(offset + delta)
        if len(found) != 1 or found[0] > len(self.data) - size:
            raise ArmRuntimeMetadataError(reason)
        return found[0]

    def string(self, offset, reason):
        if type(offset) is not int or offset < 0 or offset >= len(self.strings):
            raise ArmRuntimeMetadataError(reason)
        end = self.strings.find(b"\x00", offset)
        if end < 0 or end - offset > 255:
            raise ArmRuntimeMetadataError(reason)
        try:
            value = self.strings[offset:end].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ArmRuntimeMetadataError(reason) from exc
        if not value or any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
            raise ArmRuntimeMetadataError(reason)
        return value

    def optional_string(self, tag, reason):
        values = self.by_tag.get(tag, [])
        return self.string(values[0], reason) if values else None

    def parse_verneed(self):
        addr = self.by_tag.get(DT_VERNEED, [])
        count = self.by_tag.get(DT_VERNEEDNUM, [])
        if not addr and not count:
            return ()
        if len(addr) != 1 or len(count) != 1 or not 1 <= count[0] <= MAX_VERSION_RECORDS:
            raise ArmRuntimeMetadataError("invalid_version_need_table")
        records, seen = [], set()
        current = addr[0]
        for index in range(count[0]):
            if current in seen:
                raise ArmRuntimeMetadataError("version_need_cycle")
            seen.add(current)
            pos = self.map_vaddr(current, 16, "invalid_version_need_record")
            version, aux_count, file_offset, aux_delta, next_delta = struct.unpack_from(
                "<HHIII", self.data, pos)
            if (version != 1 or not 1 <= aux_count <= MAX_VERSION_AUX or
                    aux_delta < 16 or aux_delta % 4):
                raise ArmRuntimeMetadataError("invalid_version_need_record")
            filename = self.string(file_offset, "invalid_version_need_file")
            aux_addr = _add32(current, aux_delta, "invalid_version_need_aux")
            aux_seen, versions = set(), []
            for aux_index in range(aux_count):
                if aux_addr in aux_seen:
                    raise ArmRuntimeMetadataError("version_need_aux_cycle")
                aux_seen.add(aux_addr)
                aux_pos = self.map_vaddr(aux_addr, 16, "invalid_version_need_aux")
                hash_value, flags, other, name_offset, aux_next = struct.unpack_from(
                    "<IHHII", self.data, aux_pos)
                name = self.string(name_offset, "invalid_version_need_name")
                versions.append({
                    "name": name, "index": other & 0x7FFF,
                    "hidden": bool(other & 0x8000), "flags": flags,
                    "hash": hash_value,
                })
                if aux_index + 1 < aux_count:
                    if aux_next < 16 or aux_next % 4:
                        raise ArmRuntimeMetadataError("invalid_version_need_aux_chain")
                    aux_addr = _add32(aux_addr, aux_next, "invalid_version_need_aux")
                elif aux_next != 0:
                    raise ArmRuntimeMetadataError("invalid_version_need_aux_chain")
            records.append({"library": filename, "versions": tuple(versions),
                            "library_in_dt_needed": filename in self.needed})
            if index + 1 < count[0]:
                if next_delta < 16 or next_delta % 4:
                    raise ArmRuntimeMetadataError("invalid_version_need_chain")
                current = _add32(current, next_delta, "invalid_version_need_record")
            elif next_delta != 0:
                raise ArmRuntimeMetadataError("invalid_version_need_chain")
        return tuple(records)

    def parse_verdef(self):
        addr = self.by_tag.get(DT_VERDEF, [])
        count = self.by_tag.get(DT_VERDEFNUM, [])
        if not addr and not count:
            return ()
        if len(addr) != 1 or len(count) != 1 or not 1 <= count[0] <= MAX_VERSION_RECORDS:
            raise ArmRuntimeMetadataError("invalid_version_definition_table")
        records, seen = [], set()
        current = addr[0]
        for index in range(count[0]):
            if current in seen:
                raise ArmRuntimeMetadataError("version_definition_cycle")
            seen.add(current)
            pos = self.map_vaddr(current, 20, "invalid_version_definition_record")
            version, flags, other, aux_count, hash_value, aux_delta, next_delta = (
                struct.unpack_from("<HHHHIII", self.data, pos))
            if (version != 1 or not 1 <= aux_count <= MAX_VERSION_AUX or
                    aux_delta < 20 or aux_delta % 4):
                raise ArmRuntimeMetadataError("invalid_version_definition_record")
            aux_addr = _add32(current, aux_delta, "invalid_version_definition_aux")
            aux_seen, names = set(), []
            for aux_index in range(aux_count):
                if aux_addr in aux_seen:
                    raise ArmRuntimeMetadataError("version_definition_aux_cycle")
                aux_seen.add(aux_addr)
                aux_pos = self.map_vaddr(aux_addr, 8, "invalid_version_definition_aux")
                name_offset, aux_next = struct.unpack_from("<II", self.data, aux_pos)
                names.append(self.string(name_offset, "invalid_version_definition_name"))
                if aux_index + 1 < aux_count:
                    if aux_next < 8 or aux_next % 4:
                        raise ArmRuntimeMetadataError("invalid_version_definition_aux_chain")
                    aux_addr = _add32(aux_addr, aux_next, "invalid_version_definition_aux")
                elif aux_next != 0:
                    raise ArmRuntimeMetadataError("invalid_version_definition_aux_chain")
            records.append({"name": names[0], "parents": tuple(names[1:]),
                            "index": other & 0x7FFF, "flags": flags,
                            "hash": hash_value})
            if index + 1 < count[0]:
                if next_delta < 20 or next_delta % 4:
                    raise ArmRuntimeMetadataError("invalid_version_definition_chain")
                current = _add32(current, next_delta, "invalid_version_definition_record")
            elif next_delta != 0:
                raise ArmRuntimeMetadataError("invalid_version_definition_chain")
        return tuple(records)


def _search_path(raw):
    entries = tuple(raw.split(":"))
    absolute = tuple(x for x in entries if x.startswith("/"))
    origin_token = "$" + "{ORIGIN}"
    origin = tuple(x for x in entries if "$ORIGIN" in x or origin_token in x)
    empty = tuple(i for i, x in enumerate(entries) if not x)
    relative = tuple(x for x in entries if x and not x.startswith("/"))
    return {"raw": raw, "entries": entries, "absolute_entries": absolute,
            "origin_token_entries": origin, "relative_entries": relative,
            "empty_entry_indexes": empty,
            "empty_component_may_use_current_directory": bool(empty)}


def inspect_arm_runtime_metadata(data):
    """Read PT_INTERP, direct dependencies, RPATH/RUNPATH and version nodes."""
    elf = _ELF(data)
    if not elf.dynamics:
        return {
            "schema": "pmkb-arm-runtime-metadata-v1",
            "scope": "static_elf_identity_only",
            "identity": elf.identity, "needed": elf.needed, "soname": None,
            "rpath": None, "runpath": None, "version_requirements": (),
            "version_definitions": (), "symbol_version_table_present": False,
            "textrel_tag_present": False, "bind_now_tag_present": False,
            "dynamic_flags": {"dt_flags": None, "dt_flags_1": None,
                              "textrel_flag": False, "bind_now_flag": False,
                              "bind_now_flag_1": False},
            "warnings": (), "launchable": False, "symbol_versions_verified": False,
        }
    rpath_raw = elf.optional_string(DT_RPATH, "invalid_rpath")
    runpath_raw = elf.optional_string(DT_RUNPATH, "invalid_runpath")
    rpath = _search_path(rpath_raw) if rpath_raw is not None else None
    runpath = _search_path(runpath_raw) if runpath_raw is not None else None
    flags = elf.by_tag.get(DT_FLAGS, [])
    flags1 = elf.by_tag.get(DT_FLAGS_1, [])
    warnings = []
    for key, value in (("RPATH", rpath), ("RUNPATH", runpath)):
        if value and value["empty_component_may_use_current_directory"]:
            warnings.append("empty_" + key.lower() + "_component")
        if value and value["absolute_entries"]:
            warnings.append("absolute_" + key.lower() + "_component")
    if rpath is not None and runpath is not None:
        warnings.append("both_rpath_and_runpath_present")
    if DT_TEXTREL in elf.by_tag or (flags and flags[0] & DF_TEXTREL):
        warnings.append("text_relocations_declared")
    return {
        "schema": "pmkb-arm-runtime-metadata-v1",
        "scope": "static_dynamic_metadata_only",
        "identity": elf.identity,
        "needed": elf.needed,
        "soname": elf.soname,
        "rpath": rpath, "runpath": runpath,
        "version_requirements": elf.parse_verneed(),
        "version_definitions": elf.parse_verdef(),
        "symbol_version_table_present": DT_VERSYM in elf.by_tag,
        "textrel_tag_present": DT_TEXTREL in elf.by_tag,
        "bind_now_tag_present": DT_BIND_NOW in elf.by_tag,
        "dynamic_flags": {
            "dt_flags": flags[0] if flags else None,
            "dt_flags_1": flags1[0] if flags1 else None,
            "textrel_flag": bool(flags and flags[0] & DF_TEXTREL),
            "bind_now_flag": bool(flags and flags[0] & DF_BIND_NOW),
            "bind_now_flag_1": bool(flags1 and flags1[0] & DF_1_NOW),
        },
        "warnings": tuple(warnings),
        "launchable": False, "symbol_versions_verified": False,
    }


def compare_required_version_nodes(candidate, libraries_by_needed_name):
    """Compare required version NODE NAMES with supplied library definitions.

    This does not inspect dynamic symbol tables or prove a referenced symbol
    exists. Mapping keys must be the exact DT_NEEDED filename; bytes are
    caller-supplied and no filesystem access is performed.
    """
    if type(libraries_by_needed_name) is not dict or len(libraries_by_needed_name) > MAX_NEEDED:
        raise ArmRuntimeMetadataError("invalid_library_metadata_map")
    total = 0
    for name, data in libraries_by_needed_name.items():
        if (type(name) is not str or not name or len(name) > 128 or
                "/" in name or "\\" in name or type(data) is not bytes or
                len(data) > MAX_ELF_BYTES):
            raise ArmRuntimeMetadataError("invalid_library_metadata_map")
        total += len(data)
        if total > MAX_LIBRARY_BYTES_TOTAL:
            raise ArmRuntimeMetadataError("library_metadata_size_limit")
    binary = inspect_arm_runtime_metadata(candidate)
    parsed = {}
    for name, data in libraries_by_needed_name.items():
        try:
            parsed[name] = inspect_arm_runtime_metadata(data)
        except ArmRuntimeMetadataError as exc:
            parsed[name] = {"rejected": str(exc)}
    findings = []
    for req in binary["version_requirements"]:
        name = req["library"]
        expected = tuple(sorted({v["name"] for v in req["versions"]}))
        if not req["library_in_dt_needed"]:
            state, missing = "version_requirement_not_in_dt_needed", expected
        elif name not in parsed:
            state, missing = "library_metadata_not_supplied", expected
        elif "rejected" in parsed[name]:
            state, missing = "library_metadata_rejected", expected
        else:
            lib = parsed[name]
            if lib["identity"]["type"] != "ET_DYN":
                state, missing = "library_not_et_dyn", expected
            elif lib["soname"] is not None and lib["soname"] != name:
                state, missing = "library_soname_mismatch", expected
            else:
                provided = {v["name"] for v in lib["version_definitions"]}
                missing = tuple(x for x in expected if x not in provided)
                state = ("all_required_version_nodes_observed"
                         if not missing else "required_version_nodes_missing")
        findings.append({"library": name, "required_version_nodes": expected,
                         "missing_version_nodes": missing, "state": state})
    all_nodes = (None if not findings else
                 all(x["state"] == "all_required_version_nodes_observed"
                     for x in findings))
    needed_missing = tuple(x for x in binary["needed"] if x not in parsed)
    return {
        "schema": "pmkb-arm-version-node-comparison-v1",
        "scope": "version_node_names_only_not_symbol_resolution",
        "binary_needed": binary["needed"],
        "binary_version_requirements": tuple(findings),
        "all_required_version_nodes_observed": all_nodes,
        "libraries_not_supplied": needed_missing,
        "symbol_versions_verified": False,
        "transitive_dependencies_verified": False,
        "runtime_compatible": False, "hardware_verified": False,
        "launchable": False,
    }
