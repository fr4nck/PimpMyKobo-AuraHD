"""L08-C: inert bounded ELF32 ARM DT_NEEDED inventory, no execution.

Requires the existing EABI5 identity preflight. Does not resolve or trust
libraries, interpret rpaths, install code or prove kernel compatibility.
"""
import struct
from arm_elf_preflight import inspect_arm_elf, ArmPreflightError


def inspect_arm_dependencies(data):
    identity = inspect_arm_elf(data)
    phoff = struct.unpack_from("<I", data, 28)[0]
    phsize, phnum = struct.unpack_from("<HH", data, 42)
    segments = []
    dynamics = []
    for i in range(phnum):
        t, off, va, _, sz, memsz, _, _ = struct.unpack_from(
            "<IIIIIIII", data, phoff + i * phsize)
        if off > len(data) or sz > len(data) - off or memsz < sz:
            raise ArmPreflightError("invalid_segment_bounds")
        if t == 1:  # PT_LOAD
            segments.append((va, off, sz))
        elif t == 2:  # PT_DYNAMIC
            if sz > 4096 or sz % 8:
                raise ArmPreflightError("invalid_dynamic_table")
            dynamics.append((off, sz))
    if len(dynamics) > 1:
        raise ArmPreflightError("multiple_dynamic_tables")
    needed = []
    if dynamics:
        off, sz = dynamics[0]
        entries = [struct.unpack_from("<II", data, off + k)
                   for k in range(0, sz, 8)]
        if not any(t == 0 for t, _ in entries):
            raise ArmPreflightError("unterminated_dynamic_table")
        entries = entries[:next(i for i,(t,_) in enumerate(entries) if t == 0)]
        tables = [v for t,v in entries if t == 5]  # DT_STRTAB
        sizes = [v for t,v in entries if t == 10]  # DT_STRSZ
        offsets = [v for t,v in entries if t == 1]  # DT_NEEDED
        if len(tables) != 1 or len(sizes) != 1 or sizes[0] > 4096:
            raise ArmPreflightError("invalid_dynamic_strings")
        mapped = [(off + (tables[0] - va), size)
                  for va,off,size in segments
                  if va <= tables[0] and tables[0] - va <= size
                  and sizes[0] <= size - (tables[0] - va)]
        if len(mapped) != 1:
            raise ArmPreflightError("unmapped_dynamic_strings")
        start, _ = mapped[0]
        strings = data[start:start + sizes[0]]
        for offset in offsets:
            if offset >= len(strings):
                raise ArmPreflightError("invalid_needed_name")
            end = strings.find(b"\x00", offset)
            if end < 0 or end == offset or end - offset > 127:
                raise ArmPreflightError("invalid_needed_name")
            try:
                name = strings[offset:end].decode("ascii")
            except UnicodeDecodeError as exc:
                raise ArmPreflightError("invalid_needed_name") from exc
            if "/" in name or "\\" in name or any(not (33 <= ord(c) <= 126) for c in name):
                raise ArmPreflightError("invalid_needed_name")
            needed.append(name)
        if len(needed) > 32 or len(set(needed)) != len(needed):
            raise ArmPreflightError("invalid_needed_count")
    return {"identity": identity, "needed": tuple(needed),
            "scope": "unresolved_metadata_only", "launchable": False}
