"""Host-only ARM ELF identity preflight for prospective PMKB packages.

This does not authenticate binaries, validate ABI compatibility, install,
link, or execute anything. Exact ARM machine identity is necessary, not
sufficient, for compatibility with Kobo Aura HD.
"""
import struct

MAX_PROBE_BYTES = 4096


class ArmPreflightError(ValueError):
    """Stable diagnostic code for rejected binary candidates."""


def inspect_arm_elf(candidate):
    if type(candidate) is not bytes or len(candidate) < 52:
        raise ArmPreflightError("elf_header_truncated")
    if candidate[:4] != b"\x7fELF":
        raise ArmPreflightError("not_elf")
    if candidate[4] != 1 or candidate[5] != 1 or candidate[6] != 1:
        raise ArmPreflightError("unsupported_elf_identity")
    # ELF32 little endian: type at 16, machine at 18, ELF version at 20.
    e_type, machine, version = struct.unpack_from("<HHI", candidate, 16)
    if version != 1 or e_type not in (2, 3):
        raise ArmPreflightError("unsupported_elf_type")
    if machine != 40:  # EM_ARM
        raise ArmPreflightError("not_arm")
    e_ehsize = struct.unpack_from("<H", candidate, 40)[0]
    if e_ehsize != 52:
        raise ArmPreflightError("invalid_elf_header")
    flags = struct.unpack_from("<I", candidate, 36)[0]
    eabi = (flags >> 24) & 0xff
    if eabi != 5:
        raise ArmPreflightError("unsupported_arm_eabi")
    phoff = struct.unpack_from("<I", candidate, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", candidate, 42)
    if phnum > 32 or (phnum and
            (phentsize != 32 or phoff < 52 or
             phoff + phnum * phentsize > len(candidate))):
        raise ArmPreflightError("invalid_program_headers")
    interpreters = []
    for index in range(phnum):
        offset = phoff + index * phentsize
        ptype, fileoff, _, _, filesize = struct.unpack_from("<IIIII", candidate, offset)
        if ptype != 3:
            continue
        if filesize == 0 or filesize > 256 or fileoff + filesize > len(candidate):
            raise ArmPreflightError("invalid_interpreter")
        raw = candidate[fileoff:fileoff + filesize]
        if not raw.endswith(b"\x00") or b"\x00" in raw[:-1]:
            raise ArmPreflightError("invalid_interpreter")
        try:
            path = raw[:-1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ArmPreflightError("invalid_interpreter") from exc
        if not path.startswith("/") or any(ord(ch) < 33 or ord(ch) > 126 for ch in path):
            raise ArmPreflightError("invalid_interpreter")
        interpreters.append(path)
    if len(interpreters) > 1:
        raise ArmPreflightError("multiple_interpreters")
    return {"arm_eabi": 5, "interpreter": interpreters[0] if interpreters else None,
            "format": "ELF32-LE", "machine": "EM_ARM",
            "type": "ET_EXEC" if e_type == 2 else "ET_DYN",
            "scope": "identity_only_unverified", "launchable": False}
