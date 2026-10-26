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
    if candidate[:4] != b"\\x7fELF":
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
    return {"format": "ELF32-LE", "machine": "EM_ARM",
            "type": "ET_EXEC" if e_type == 2 else "ET_DYN",
            "scope": "identity_only_unverified", "launchable": False}
