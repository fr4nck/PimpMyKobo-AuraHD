"""Offline-only, fail-closed memory metadata validator for PMKB Boot Contract V1.

No physical memory access, disk access, subprocesses, network or boot execution.
All addresses are declarations, not values recovered from the Aura HD.
"""
import json
import re

FORMAT = "pmkb-boot-contract-v1"
MAX_JSON_CHARS = 131072
U32_SPACE = 1 << 32
RAM_SIZE = 512 * 1024 * 1024
REQUIRED = frozenset(("kernel", "boot_data", "hwconfig", "waveform"))


class ContractError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def check(predicate, code):
    if not predicate:
        raise ContractError(code)


def fields(value, expected, code):
    check(type(value) is dict and set(value) == set(expected), code)


def uint(value, *, positive=False, aligned=False):
    check(type(value) is int and (value > 0 if positive else value >= 0)
          and value < U32_SPACE and (not aligned or value % 4 == 0),
          "invalid_integer")
    return value


def span(start, size):
    uint(start, aligned=True)
    uint(size, positive=True, aligned=True)
    check(start + size <= U32_SPACE, "address_overflow")
    return start, start + size


def report():
    return {"status": "refused", "scope": "declared_metadata_only",
            "hardware_verified": False, "boot_compatible": False,
            "memory_map_verified": False, "errors": []}


def analyze(contract):
    """Check declared spans and ABI metadata; never authorize flashing or boot."""
    result = report()
    try:
        fields(contract, ("format", "device", "provenance", "ram", "regions",
                          "image", "handoff", "parameters"), "invalid_schema")
        check(contract["format"] == FORMAT, "invalid_format")
        check(contract["device"] == "E606C0", "wrong_board")
        check(type(contract["provenance"]) is str and
              contract["provenance"] in ("synthetic", "manual_transcription"),
              "invalid_provenance")
        ram = contract["ram"]
        fields(ram, ("start", "size"), "invalid_ram")
        ram_start, ram_end = span(ram["start"], ram["size"])
        check(ram["size"] == RAM_SIZE, "ram_size_mismatch")

        items = contract["regions"]
        check(type(items) is list and 4 <= len(items) <= 64, "invalid_regions")
        regions = {}
        for item in items:
            fields(item, ("name", "start", "size"), "invalid_region")
            name = item["name"]
            check(type(name) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,31}", name)
                  is not None and name not in regions, "invalid_region_name")
            start, end = span(item["start"], item["size"])
            check(ram_start <= start < end <= ram_end, "region_outside_ram")
            regions[name] = (start, end)
        check(REQUIRED.issubset(regions), "missing_required_region")
        ordered = sorted(regions.items(), key=lambda pair: pair[1][0])
        for a, b in zip(ordered, ordered[1:]):
            check(a[1][1] <= b[1][0], "regions_overlap")

        image = contract["image"]
        fields(image, ("format", "load", "entry", "size"), "invalid_image")
        check(image["format"] == "uImage", "unsupported_image_format")
        load = uint(image["load"], aligned=True)
        entry = uint(image["entry"], aligned=True)
        size = uint(image["size"], positive=True)
        check(load == regions["kernel"][0] and
              size <= regions["kernel"][1] - load and
              load <= entry < load + size, "image_region_mismatch")

        handoff = contract["handoff"]
        fields(handoff, ("kind", "r0", "r1", "r2"), "invalid_handoff")
        check(handoff["kind"] in ("ATAGS", "DTB") and
              type(handoff["kind"]) is str, "unsupported_handoff")
        check(type(handoff["r0"]) is int and handoff["r0"] == 0,
              "invalid_boot_registers")
        uint(handoff["r1"])
        ptr = uint(handoff["r2"], aligned=True)
        # ARM booting.rst v6.18: DTB must be 64-bit aligned; ATAG is 32-bit.
        # Enforce minimum structural room for the header/terminator only.
        minimum = 40 if handoff["kind"] == "DTB" else 16
        check(regions["boot_data"][0] <= ptr and
              ptr + minimum <= regions["boot_data"][1],
              "boot_data_pointer_outside_region")
        if handoff["kind"] == "DTB":
            check(ptr % 8 == 0, "invalid_dtb_alignment")

        params = contract["parameters"]
        fields(params, ("hwcfg_p", "hwcfg_sz", "waveform_p", "waveform_sz"),
               "invalid_parameters")
        for prefix, region in (("hwcfg", "hwconfig"), ("waveform", "waveform")):
            addr = uint(params[prefix + "_p"], aligned=True)
            length = uint(params[prefix + "_sz"], positive=True)
            start, end = regions[region]
            check(addr == start and length <= end - addr,
                  "parameter_region_mismatch")

        result.update(status="consistent_unverified", region_count=len(regions),
                      handoff_kind=handoff["kind"],
                      declared_machine_id=handoff["r1"])
    except ContractError as error:
        result["errors"] = [{"code": error.code}]
    return result


def _unique_pairs(pairs):
    mapping = {}
    for key, value in pairs:
        check(key not in mapping, "duplicate_json_key")
        mapping[key] = value
    return mapping


def _invalid_constant(_):
    raise ContractError("invalid_json")


def analyze_json(text):
    """Strict pure JSON entry point. No file path support by design."""
    if type(text) is not str or len(text) > MAX_JSON_CHARS:
        return {**report(), "errors": [{"code": "invalid_json_text"}]}
    try:
        payload = json.loads(text, object_pairs_hook=_unique_pairs,
                             parse_constant=_invalid_constant)
    except ContractError as error:
        return {**report(), "errors": [{"code": error.code}]}
    except (ValueError, RecursionError):
        return {**report(), "errors": [{"code": "invalid_json"}]}
    return analyze(payload)
