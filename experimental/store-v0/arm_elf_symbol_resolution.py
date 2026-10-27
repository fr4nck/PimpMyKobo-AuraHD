"""L08-N bounded ELF dynamic-symbol and symbol-version audit.

This compares supplied ELF symbol names and version-node names. It does not
perform runtime linking, relocation, interposition or target execution.
"""
import struct

from arm_elf_runtime_metadata import (
    ArmRuntimeMetadataError, MAX_ELF_BYTES, MAX_NEEDED,
    MAX_LIBRARY_BYTES_TOTAL, DT_VERSYM, _ELF, inspect_arm_runtime_metadata,
)

DT_HASH = 4
DT_SYMTAB = 6
DT_SYMENT = 11
DT_GNU_HASH = 0x6FFFFEF5
MAX_DYNAMIC_SYMBOLS = 65536
MAX_HASH_BUCKETS = 65536
MAX_GNU_CHAIN_READS = MAX_DYNAMIC_SYMBOLS * 4
_SYMBOL_BYTES = 16
_EXTERNAL_BINDINGS = frozenset((1, 2, 10))
_EXTERNAL_VISIBILITIES = frozenset((0, 3))


class ArmSymbolResolutionError(ValueError):
    """Stable refusal code for malformed ELF symbol metadata."""


def _symbol_count(elf):
    sysv = elf.by_tag.get(DT_HASH, [])
    gnu = elf.by_tag.get(DT_GNU_HASH, [])
    if len(sysv) > 1 or len(gnu) > 1:
        raise ArmSymbolResolutionError("duplicate_dynamic_hash_tag")
    if sysv:
        address = sysv[0]
        offset = elf.map_vaddr(address, 8, "invalid_sysv_hash_header")
        buckets, chains = struct.unpack_from("<II", elf.data, offset)
        if (not 1 <= buckets <= MAX_HASH_BUCKETS or
                not 1 <= chains <= MAX_DYNAMIC_SYMBOLS):
            raise ArmSymbolResolutionError("invalid_dynamic_symbol_count")
        elf.map_vaddr(address, 8 + 4 * (buckets + chains),
                      "invalid_sysv_hash_table")
        return chains
    if not gnu:
        return None
    address = gnu[0]
    offset = elf.map_vaddr(address, 16, "invalid_gnu_hash_header")
    buckets, symoffset, bloom_size, _shift = struct.unpack_from(
        "<IIII", elf.data, offset)
    if (not 1 <= buckets <= MAX_HASH_BUCKETS or
            not 1 <= symoffset <= MAX_DYNAMIC_SYMBOLS or
            not 1 <= bloom_size <= MAX_HASH_BUCKETS):
        raise ArmSymbolResolutionError("invalid_gnu_hash_header")
    bucket_address = address + 16 + bloom_size * 4
    if bucket_address > 0xFFFFFFFF:
        raise ArmSymbolResolutionError("invalid_gnu_hash_bucket_address")
    bucket_offset = elf.map_vaddr(
        bucket_address, buckets * 4, "invalid_gnu_hash_buckets")
    chain_address = bucket_address + buckets * 4
    if chain_address > 0xFFFFFFFF:
        raise ArmSymbolResolutionError("invalid_gnu_hash_chain_address")
    max_index = symoffset - 1
    reads = 0
    for i in range(buckets):
        first = struct.unpack_from("<I", elf.data, bucket_offset + i * 4)[0]
        if first == 0:
            continue
        if first < symoffset or first >= MAX_DYNAMIC_SYMBOLS:
            raise ArmSymbolResolutionError("invalid_gnu_hash_bucket")
        index = first
        while index < MAX_DYNAMIC_SYMBOLS:
            current = chain_address + (index - symoffset) * 4
            chain_offset = elf.map_vaddr(current, 4, "invalid_gnu_hash_chain")
            value = struct.unpack_from("<I", elf.data, chain_offset)[0]
            reads += 1
            if reads > MAX_GNU_CHAIN_READS:
                raise ArmSymbolResolutionError("gnu_hash_chain_limit")
            max_index = max(max_index, index)
            if value & 1:
                break
            index += 1
        else:
            raise ArmSymbolResolutionError("unterminated_gnu_hash_chain")
    return max_index + 1


def _version_maps(metadata):
    needs, definitions = {}, {}
    for requirement in metadata["version_requirements"]:
        for version in requirement["versions"]:
            index = version["index"]
            if index <= 1:
                continue
            value = {
                "library": requirement["library"],
                "version": version["name"],
                "library_in_dt_needed": requirement["library_in_dt_needed"],
            }
            if index in needs and needs[index] != value:
                raise ArmSymbolResolutionError("ambiguous_version_need_index")
            needs[index] = value
    for definition in metadata["version_definitions"]:
        index = definition["index"]
        if index <= 1:
            continue
        value = definition["name"]
        if index in definitions and definitions[index] != value:
            raise ArmSymbolResolutionError("ambiguous_version_definition_index")
        definitions[index] = value
    return needs, definitions


def _parse_dynamic_symbols(data):
    try:
        elf = _ELF(data)
        metadata = inspect_arm_runtime_metadata(data)
    except ArmRuntimeMetadataError as exc:
        raise ArmSymbolResolutionError("invalid_elf_metadata") from exc
    if not elf.dynamics:
        return {"state": "no_dynamic_table", "metadata": metadata,
                "symbol_count": 0, "undefined": (), "exports": {}}
    symtab = elf.by_tag.get(DT_SYMTAB, [])
    syment = elf.by_tag.get(DT_SYMENT, [])
    if not symtab and not syment:
        return {"state": "dynamic_symbol_table_unavailable", "metadata": metadata,
                "symbol_count": 0, "undefined": (), "exports": {}}
    if len(symtab) != 1 or len(syment) != 1 or syment[0] != _SYMBOL_BYTES:
        raise ArmSymbolResolutionError("invalid_dynamic_symbol_table")
    count = _symbol_count(elf)
    if count is None:
        return {"state": "dynamic_symbol_count_unavailable", "metadata": metadata,
                "symbol_count": 0, "undefined": (), "exports": {}}
    if not 1 <= count <= MAX_DYNAMIC_SYMBOLS:
        raise ArmSymbolResolutionError("invalid_dynamic_symbol_count")
    symbol_offset = elf.map_vaddr(
        symtab[0], count * _SYMBOL_BYTES, "invalid_dynamic_symbol_table")
    versym_tags = elf.by_tag.get(DT_VERSYM, [])
    if len(versym_tags) > 1:
        raise ArmSymbolResolutionError("duplicate_dynamic_versym")
    versym_present = bool(versym_tags)
    versym_offset = (elf.map_vaddr(
        versym_tags[0], count * 2, "invalid_dynamic_versym_table")
        if versym_present else None)
    needs, definitions = _version_maps(metadata)
    version_metadata_present = bool(
        metadata["version_requirements"] or metadata["version_definitions"])
    version_table_missing = version_metadata_present and not versym_present
    undefined, exports = [], {}
    for index in range(count):
        offset = symbol_offset + index * _SYMBOL_BYTES
        name_offset, _value, _size, info, other, section = struct.unpack_from(
            "<IIIBBH", elf.data, offset)
        binding, symbol_type = info >> 4, info & 0x0F
        if binding not in _EXTERNAL_BINDINGS:
            continue
        name = elf.string(name_offset, "invalid_dynamic_symbol_name",
                          allow_empty=True)
        if not name:
            continue
        word = (struct.unpack_from("<H", elf.data, versym_offset + index * 2)[0]
                if versym_present else 1)
        version_index, hidden = word & 0x7FFF, bool(word & 0x8000)
        if section == 0:
            requirement = needs.get(version_index) if version_index > 1 else None
            undefined.append({
                "name": name, "binding": binding, "type": symbol_type,
                "visibility": other & 0x03, "version_index": version_index,
                "version_hidden": hidden, "version_requirement": requirement,
                "version_index_mapped": version_index <= 1 or requirement is not None,
            })
        elif (other & 0x03) in _EXTERNAL_VISIBILITIES:
            if version_index > 1:
                version_name = definitions.get(version_index)
                mapped = version_name is not None
            else:
                version_name, mapped = None, not version_table_missing
            exports.setdefault(name, []).append({
                "name": name, "binding": binding, "type": symbol_type,
                "visibility": other & 0x03, "version_index": version_index,
                "version_hidden": hidden, "version_name": version_name,
                "version_index_mapped": mapped,
            })
    return {
        "state": "symbol_version_table_missing" if version_table_missing else "ok",
        "metadata": metadata, "symbol_count": count,
        "versym_present": versym_present,
        "undefined": tuple(undefined), "exports": exports,
    }


def _validate_library_map(libraries):
    if type(libraries) is not dict or len(libraries) > MAX_NEEDED:
        raise ArmSymbolResolutionError("invalid_library_map")
    total = 0
    for name, data in libraries.items():
        if (type(name) is not str or not name or len(name) > 128 or
                "/" in name or "\\" in name or type(data) is not bytes or
                len(data) > MAX_ELF_BYTES):
            raise ArmSymbolResolutionError("invalid_library_map")
        total += len(data)
        if total > MAX_LIBRARY_BYTES_TOTAL:
            raise ArmSymbolResolutionError("library_symbol_metadata_size_limit")


def compare_required_symbols(candidate, libraries_by_needed_name):
    """Compare undefined symbols with supplied exports and version nodes."""
    _validate_library_map(libraries_by_needed_name)
    try:
        executable = _parse_dynamic_symbols(candidate)
    except ArmSymbolResolutionError as exc:
        raise ArmSymbolResolutionError("invalid_candidate_symbol_table") from exc
    if executable["state"] != "ok":
        state = ("candidate_symbol_version_table_missing"
                 if executable["state"] == "symbol_version_table_missing"
                 else "candidate_symbol_table_unavailable")
        return {
            "schema": "pmkb-elf-symbol-version-audit-v1",
            "scope": "dynamic_symbol_metadata_only",
            "verdict": state, "candidate_symbol_table_state": executable["state"],
            "candidate_symbol_count": executable["symbol_count"],
            "undefined_symbol_count": len(executable["undefined"]),
            "symbol_findings": (),
            "all_versioned_symbol_pairs_observed": None,
            "all_undefined_symbol_names_observed": None,
            "symbol_versions_verified": False,
            "dynamic_symbol_resolution_verified": False,
            "runtime_compatible": False, "launchable": False,
        }
    parsed = {}
    for name, data in libraries_by_needed_name.items():
        try:
            parsed[name] = _parse_dynamic_symbols(data)
        except ArmSymbolResolutionError as exc:
            parsed[name] = {"state": "library_metadata_rejected", "reason": str(exc)}
    findings = []
    for symbol in executable["undefined"]:
        name = symbol["name"]
        index = symbol["version_index"]
        requirement = symbol["version_requirement"]
        required_library = requirement["library"] if requirement else None
        required_version = requirement["version"] if requirement else None
        if index == 0:
            state = "local_symbol_version_index"
        elif index > 1 and requirement is None:
            state = "version_index_unmapped"
        elif index > 1 and not requirement["library_in_dt_needed"]:
            state = "version_requirement_not_in_dt_needed"
        elif index > 1 and required_library not in parsed:
            state = "required_library_not_supplied"
        elif index > 1:
            provider = parsed[required_library]
            if provider["state"] == "library_metadata_rejected":
                state = "required_library_metadata_rejected"
            elif provider["state"] == "symbol_version_table_missing":
                state = "provider_symbol_version_table_missing"
            elif provider["state"] != "ok":
                state = "required_library_symbol_table_unavailable"
            elif provider["metadata"]["identity"]["type"] != "ET_DYN":
                state = "required_library_not_et_dyn"
            elif (provider["metadata"]["soname"] is not None and
                  provider["metadata"]["soname"] != required_library):
                state = "required_library_soname_mismatch"
            else:
                candidates = provider["exports"].get(name, [])
                if not candidates:
                    state = "required_symbol_not_exported"
                elif any(item["version_index_mapped"] and
                         item["version_name"] == required_version
                         for item in candidates):
                    state = "symbol_and_version_node_observed_in_library"
                elif any(not item["version_index_mapped"] for item in candidates):
                    state = "provider_symbol_version_index_unmapped"
                else:
                    state = "required_symbol_version_not_exported"
        else:
            found = False
            for library_name, provider in parsed.items():
                if provider["state"] != "ok":
                    continue
                if provider["metadata"]["identity"]["type"] != "ET_DYN":
                    continue
                soname = provider["metadata"]["soname"]
                if soname is not None and soname != library_name:
                    continue
                for item in provider["exports"].get(name, []):
                    if (item["version_index_mapped"] and
                            (item["version_name"] is None or
                             not item["version_hidden"])):
                        found = True
                        break
                if found:
                    break
            state = ("unversioned_symbol_name_observed" if found
                     else "symbol_name_not_observed_in_supplied_libraries")
        findings.append({
            "name": name, "binding": symbol["binding"], "type": symbol["type"],
            "version_index": index, "version_hidden": symbol["version_hidden"],
            "required_library": required_library, "required_version": required_version,
            "state": state, "optional_weak_symbol": symbol["binding"] == 2,
        })
    versioned = [x for x in findings if x["required_version"] is not None]
    success_states = frozenset((
        "symbol_and_version_node_observed_in_library",
        "unversioned_symbol_name_observed",
    ))
    all_versioned = (None if not versioned else all(
        x["state"] == "symbol_and_version_node_observed_in_library"
        for x in versioned))
    all_names = (None if not findings else all(
        x["state"] in success_states for x in findings))
    provider_states = tuple({
        "name": name, "state": item["state"],
        "soname": item["metadata"]["soname"] if "metadata" in item else None,
        "symbol_count": item.get("symbol_count", 0),
        "undefined_count": len(item.get("undefined", ())),
        "exported_name_count": len(item.get("exports", {})),
        "reason": item.get("reason"),
    } for name, item in sorted(parsed.items()))
    unresolved = sum(x["state"] not in success_states for x in findings)
    return {
        "schema": "pmkb-elf-symbol-version-audit-v1",
        "scope": "dynamic_symbol_name_and_version_node_metadata_only",
        "verdict": "symbol_pairs_observed" if unresolved == 0 else "symbol_pairs_incomplete",
        "candidate_symbol_table_state": executable["state"],
        "candidate_symbol_count": executable["symbol_count"],
        "candidate_undefined_symbol_count": len(executable["undefined"]),
        "library_symbol_tables": provider_states,
        "symbol_findings": tuple(findings),
        "all_versioned_symbol_pairs_observed": all_versioned,
        "all_undefined_symbol_names_observed": all_names,
        "unresolved_symbol_count": unresolved,
        "symbol_versions_verified": False,
        "dynamic_symbol_resolution_verified": False,
        "transitive_dependencies_verified": False,
        "runtime_compatible": False, "hardware_verified": False,
        "launchable": False,
    }
