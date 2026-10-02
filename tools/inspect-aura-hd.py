#!/usr/bin/env python3
"""Read-only inspector for Kobo Aura HD / Dragon microSD cards."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, BinaryIO

SECTOR_SIZE = 512
HWCONFIG_OFFSET = 0x80000
HWCONFIG_HEADER_SIZE = 16
HWCONFIG_V17_PAYLOAD_SIZE = 39
MAX_BOOT_HASH_SIZE = 64 * 1024 * 1024
JSON_SCHEMA_VERSION = 1

HW_FIELDS = [
    "bPCB", "bKeyPad", "bAudioCodec", "bAudioAmp", "bWifi", "bBT", "bMobile",
    "bTouchCtrl", "bTouchType", "bDisplayCtrl", "bDisplayPanel", "bRSensor",
    "bMicroP", "bCustomer", "bBattery", "bLed", "bRamSize", "bIFlash",
    "bExternalMem", "bRootFsType", "bSysPartType", "bProgressXHiByte",
    "bProgressXLoByte", "bProgressYHiByte", "bProgressYLoByte", "bProgressCnts",
    "bContentType", "bCPU", "bUIStyle", "bRamType", "bUIConfig",
    "bDisplayResolution", "bFrontLight", "bCPUFreq", "bHallSensor",
    "bDisplayBusWidth", "bFrontLight_Flags", "bPCB_Flags", "bFrontLight_LED_Driver",
]

KNOWN_VALUES = {
    "bPCB": {28: "E606C0"},
    "bKeyPad": {11: "FL_Key"},
    "bWifi": {7: "WC121A2"},
    "bTouchCtrl": {8: "neonode_v2"},
    "bTouchType": {4: "IR-Type"},
    "bDisplayCtrl": {6: "MX508+TPS65185"},
    "bDisplayPanel": {10: '6.8" Bottom EPD'},
    "bRSensor": {2: "G Sensor"},
    "bMicroP": {0: "MSP430"},
    "bBattery": {1: "1500mA"},
    "bRamSize": {3: "512MB"},
    "bIFlash": {0: "Micro SD"},
    "bExternalMem": {2: "Micro SD"},
    "bRootFsType": {2: "Ext4"},
    "bSysPartType": {2: "TYPE3"},
    "bCPU": {2: "mx50"},
    "bUIStyle": {1: "Customer UI"},
    "bRamType": {2: "K4X2G323PC"},
    "bUIConfig": {0: "Normal"},
    "bDisplayResolution": {3: "1440x1080"},
    "bFrontLight": {6: "TABLE3+"},
    "bCPUFreq": {2: "1G"},
    "bHallSensor": {1: "TLE4913"},
    "bDisplayBusWidth": {3: "16Bits_mirror"},
    "bFrontLight_LED_Driver": {0: "SY7201"},
}

FR = {
    "title": "PimpMyKobo-AuraHD — inspection en lecture seule",
    "readonly": "AUCUNE ÉCRITURE : les sources sont ouvertes exclusivement en mode lecture.",
    "scanning": "Analyse de {count} disque(s) détecté(s)…",
    "found": "KOBO AURA HD IDENTIFIÉE",
    "probable": "PCB E606C0 DÉTECTÉ, MAIS FORMAT HWCONFIG NON CONFIRMÉ",
    "no_found": "Aucune Kobo Aura HD E606C0 confirmée n'a été identifiée.",
    "source": "Source", "model": "Matériel", "size": "Taille", "hw": "HWCONFIG",
    "pcb": "PCB", "identity": "Identification", "partitions": "Partitions MBR",
    "boot_hash": "SHA-256 zone avant P1", "access": "inaccessible en lecture",
    "not_kobo": "pas de HWCONFIG Aura HD confirmé", "error": "ERREUR",
    "warning": "AVERTISSEMENT",
    "unreadable_summary": "{count} disque(s) n'ont pas pu être ouverts ; relancer avec les droits administrateur/root si nécessaire.",
    "read_error_summary": "{count} disque(s) ont produit une erreur de lecture ou de diagnostic.",
    "discovery_error": "Impossible d'énumérer correctement les disques : {error}",
    "wsl": (
        "WSL détecté : un lecteur USB Windows peut ne pas apparaître comme périphérique bloc Linux. "
        "Si aucun disque n'est trouvé, lancez ce script avec Python Windows dans PowerShell, "
        "ou fournissez le chemin d'une image disque."
    ),
}

EN = {
    "title": "PimpMyKobo-AuraHD — read-only inspection",
    "readonly": "NO WRITES: sources are opened strictly read-only.",
    "scanning": "Scanning {count} detected disk(s)…",
    "found": "KOBO AURA HD IDENTIFIED",
    "probable": "E606C0 PCB DETECTED, BUT HWCONFIG FORMAT IS NOT CONFIRMED",
    "no_found": "No confirmed Kobo Aura HD E606C0 was identified.",
    "source": "Source", "model": "Device", "size": "Size", "hw": "HWCONFIG",
    "pcb": "PCB", "identity": "Identification", "partitions": "MBR partitions",
    "boot_hash": "SHA-256 pre-P1 area", "access": "not readable",
    "not_kobo": "no confirmed Aura HD HWCONFIG", "error": "ERROR",
    "warning": "WARNING",
    "unreadable_summary": "{count} disk(s) could not be opened; re-run with administrator/root privileges if needed.",
    "read_error_summary": "{count} disk(s) produced a read or diagnostic error.",
    "discovery_error": "Disk enumeration failed or was incomplete: {error}",
    "wsl": (
        "WSL detected: a Windows USB reader may not appear as a Linux block device. "
        "If no disk is found, run this script with Windows Python from PowerShell, "
        "or provide a disk-image path."
    ),
}


def human_size(value: int | None) -> str:
    if value is None:
        return "?"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    n = float(value)
    for unit in units:
        if n < 1024.0 or unit == units[-1]:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{value} B"


def read_at(handle: BinaryIO, offset: int, size: int, alignment: int = SECTOR_SIZE) -> bytes:
    """Read arbitrary bytes using aligned low-level reads, including Windows raw disks."""
    if offset < 0 or size < 0:
        raise ValueError("negative offset/size")
    if size == 0:
        return b""
    aligned_start = (offset // alignment) * alignment
    end = offset + size
    aligned_end = ((end + alignment - 1) // alignment) * alignment
    handle.seek(aligned_start)
    data = handle.read(aligned_end - aligned_start)
    start = offset - aligned_start
    return data[start : start + size]


def source_size_for(source: str, metadata: dict[str, Any], handle: BinaryIO) -> int | None:
    value = metadata.get("size")
    if isinstance(value, int) and value > 0:
        return value

    try:
        st = os.fstat(handle.fileno())
        if st.st_size > 0:
            return st.st_size
    except (OSError, AttributeError):
        pass

    try:
        current = handle.tell()
        end = handle.seek(0, os.SEEK_END)
        handle.seek(current, os.SEEK_SET)
        if isinstance(end, int) and end > 0:
            return end
    except (OSError, AttributeError):
        pass

    try:
        p = Path(source)
        if p.is_file():
            return p.stat().st_size
    except OSError:
        pass
    return None


def parse_mbr(handle: BinaryIO, source_size: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"valid": False, "partitions": [], "errors": [], "warnings": []}
    sector = read_at(handle, 0, SECTOR_SIZE)
    if len(sector) != SECTOR_SIZE:
        result["errors"].append("short MBR read")
        return result
    if sector[510:512] != b"\x55\xaa":
        result["errors"].append("missing MBR signature 0x55AA")
        return result

    partitions: list[dict[str, Any]] = []
    for index in range(4):
        entry = sector[446 + 16 * index : 446 + 16 * (index + 1)]
        boot_indicator = entry[0]
        ptype = entry[4]
        start_lba = int.from_bytes(entry[8:12], "little")
        sectors = int.from_bytes(entry[12:16], "little")
        if ptype == 0 or sectors == 0:
            continue
        if boot_indicator not in (0x00, 0x80):
            result["errors"].append(f"P{index+1}: invalid boot indicator 0x{boot_indicator:02X}")
        offset = start_lba * SECTOR_SIZE
        size = sectors * SECTOR_SIZE
        end = offset + size
        part = {
            "number": index + 1,
            "boot_indicator": boot_indicator,
            "type": ptype,
            "start_lba": start_lba,
            "sectors": sectors,
            "offset": offset,
            "size": size,
            "end": end,
            "beyond_end": False,
        }
        if start_lba < 1:
            result["errors"].append(f"P{index+1}: partition starts before sector 1")
        if source_size is not None and end > source_size:
            part["beyond_end"] = True
            result["errors"].append(
                f"P{index+1}: partition ends at {end}, beyond source size {source_size}"
            )
        partitions.append(part)

    by_start = sorted(partitions, key=lambda p: p["offset"])
    for left, right in zip(by_start, by_start[1:]):
        if left["end"] > right["offset"]:
            result["errors"].append(f"P{left['number']} overlaps P{right['number']}")

    if not partitions:
        result["errors"].append("no MBR partitions")
    result["partitions"] = partitions
    result["valid"] = not result["errors"]
    return result


def detect_filesystem(handle: BinaryIO, offset: int) -> dict[str, Any]:
    sb = read_at(handle, offset + 1024, 1024)
    if len(sb) >= 136 and sb[56:58] == b"\x53\xef":
        label = sb[120:136].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
        return {"filesystem": "ext", "label": label}

    boot = read_at(handle, offset, SECTOR_SIZE)
    if len(boot) >= 90 and boot[510:512] == b"\x55\xaa":
        fs_type = boot[82:90].decode("ascii", "replace").strip()
        if fs_type.startswith("FAT32"):
            label = boot[71:82].decode("ascii", "replace").strip()
            return {"filesystem": "FAT32", "label": label}
        fs_type16 = boot[54:62].decode("ascii", "replace").strip()
        if fs_type16.startswith("FAT"):
            label = boot[43:54].decode("ascii", "replace").strip()
            return {"filesystem": fs_type16 or "FAT", "label": label}
    return {"filesystem": "unknown", "label": ""}


def decode_bitflags(value: int, names: list[str]) -> list[str]:
    return [name for bit, name in enumerate(names) if value & (1 << bit)]


def parse_hwconfig(handle: BinaryIO) -> dict[str, Any] | None:
    header = read_at(handle, HWCONFIG_OFFSET, HWCONFIG_HEADER_SIZE)
    if len(header) != HWCONFIG_HEADER_SIZE:
        raise OSError("short read while reading HWCONFIG header")
    if header[:10] != b"HW CONFIG ":
        return None

    version = header[10:15].split(b"\x00", 1)[0].decode("ascii", "replace")
    payload_size = header[15]
    payload = read_at(handle, HWCONFIG_OFFSET + HWCONFIG_HEADER_SIZE, payload_size)
    if len(payload) != payload_size:
        raise OSError(
            f"short read while reading HWCONFIG payload: expected {payload_size}, got {len(payload)}"
        )

    fields: dict[str, int] = {}
    for index, value in enumerate(payload):
        name = HW_FIELDS[index] if index < len(HW_FIELDS) else f"unknown_{index}"
        fields[name] = value

    decoded: dict[str, Any] = {}
    for name, value in fields.items():
        text = KNOWN_VALUES.get(name, {}).get(value)
        if text is not None:
            decoded[name] = text
    if "bFrontLight_Flags" in fields:
        decoded["bFrontLight_Flags"] = decode_bitflags(
            fields["bFrontLight_Flags"], ["BootON", "TABLE1X", "EN_INV"]
        )
    if "bPCB_Flags" in fields:
        decoded["bPCB_Flags"] = decode_bitflags(
            fields["bPCB_Flags"], ["NO_KeyMatrix", "FPC_Touch", "LOGO_LED", "RD_MODE", "EPD_LV"]
        )

    pcb = fields.get("bPCB")
    pcb_match = pcb == 28
    format_confirmed = version == "v1.7" and payload_size == HWCONFIG_V17_PAYLOAD_SIZE
    confirmed = pcb_match and format_confirmed
    warnings: list[str] = []
    if pcb_match and not format_confirmed:
        warnings.append(
            f"PCB 28 / E606C0 detected but HWCONFIG format is {version!r}/{payload_size} bytes, "
            "not confirmed v1.7/39"
        )

    return {
        "offset": HWCONFIG_OFFSET,
        "version": version,
        "payload_size": payload_size,
        "fields": fields,
        "decoded": decoded,
        "pcb_e606c0": pcb_match,
        "format_confirmed": format_confirmed,
        "is_aura_hd_e606c0": confirmed,
        "identity": "Kobo Aura HD / Dragon / E606C0" if confirmed else None,
        "warnings": warnings,
    }


def sha256_region(handle: BinaryIO, offset: int, size: int) -> str:
    h = hashlib.sha256()
    remaining = size
    cursor = offset
    while remaining:
        length = min(4 * 1024 * 1024, remaining)
        chunk = read_at(handle, cursor, length)
        if len(chunk) != length:
            raise OSError("unexpected end of source while hashing")
        h.update(chunk)
        cursor += length
        remaining -= length
    return h.hexdigest()


def inspect_source(source: str, metadata: dict[str, Any] | None, hash_boot: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": JSON_SCHEMA_VERSION,
        "source": source,
        "metadata": metadata or {},
        "opened": False,
        "readable": False,
        "aura_hd": False,
        "errors": [],
        "warnings": [],
    }
    try:
        with open(source, "rb", buffering=0) as handle:
            result["opened"] = True
            source_size = source_size_for(source, result["metadata"], handle)
            result["source_size"] = source_size

            try:
                mbr = parse_mbr(handle, source_size)
            except (OSError, ValueError) as exc:
                mbr = {"valid": False, "partitions": [], "errors": [str(exc)], "warnings": []}
                result["errors"].append(f"MBR read: {exc}")
            result["mbr"] = mbr

            try:
                hw = parse_hwconfig(handle)
            except (OSError, ValueError) as exc:
                hw = None
                result["errors"].append(f"HWCONFIG: {exc}")
            result["hwconfig"] = hw

            if hw:
                result["warnings"].extend(hw.get("warnings", []))
                result["aura_hd"] = bool(hw.get("is_aura_hd_e606c0"))

            mbr_validation_errors = mbr.get("errors", [])
            if result["aura_hd"]:
                result["errors"].extend(f"MBR: {message}" for message in mbr_validation_errors)
            elif mbr_validation_errors:
                result["warnings"].extend(f"MBR: {message}" for message in mbr_validation_errors)

            result["readable"] = not any(
                message.startswith("MBR read:") or message.startswith("HWCONFIG:")
                for message in result["errors"]
            )

            for partition in mbr.get("partitions", []):
                if partition.get("beyond_end"):
                    partition.update({
                        "filesystem": "unknown",
                        "label": "",
                        "filesystem_error": "partition extends beyond source",
                    })
                    continue
                try:
                    partition.update(detect_filesystem(handle, partition["offset"]))
                except OSError as exc:
                    partition.update({"filesystem": "unknown", "label": "", "filesystem_error": str(exc)})
                    result["warnings"].append(
                        f"P{partition['number']} filesystem read failed: {exc}"
                    )

            if hash_boot and result.get("aura_hd"):
                if not mbr.get("valid"):
                    result["warnings"].append("boot hash skipped: MBR is not valid")
                elif not mbr.get("partitions"):
                    result["warnings"].append("boot hash skipped: no MBR partitions")
                else:
                    first_offset = min(p["offset"] for p in mbr["partitions"])
                    if first_offset <= 0:
                        result["warnings"].append("boot hash skipped: invalid first partition offset")
                    elif first_offset > MAX_BOOT_HASH_SIZE:
                        result["warnings"].append(
                            f"boot hash skipped: first partition starts beyond {MAX_BOOT_HASH_SIZE} bytes"
                        )
                    elif source_size is not None and first_offset > source_size:
                        result["warnings"].append("boot hash skipped: first partition starts beyond source")
                    else:
                        try:
                            result["pre_p1_sha256"] = sha256_region(handle, 0, first_offset)
                            result["pre_p1_size"] = first_offset
                        except OSError as exc:
                            result["errors"].append(f"boot hash: {exc}")
    except (OSError, PermissionError) as exc:
        result["errors"].append(str(exc))
        result["error"] = str(exc)
    return result


def windows_candidates(diagnostics: list[str] | None = None) -> list[dict[str, Any]]:
    command = [
        "powershell", "-NoProfile", "-Command",
        "$ErrorActionPreference='Stop'; "
        "Get-Disk | Select-Object Number,FriendlyName,BusType,Size,PartitionStyle | "
        "ConvertTo-Json -Compress",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except FileNotFoundError as exc:
        if diagnostics is not None:
            diagnostics.append(f"PowerShell not found: {exc}")
        return []
    except subprocess.TimeoutExpired as exc:
        if diagnostics is not None:
            diagnostics.append(f"Get-Disk timed out after {exc.timeout} seconds")
        return []
    except OSError as exc:
        if diagnostics is not None:
            diagnostics.append(f"cannot start PowerShell/Get-Disk: {exc}")
        return []

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown Get-Disk error").strip()
        if diagnostics is not None:
            diagnostics.append(f"Get-Disk failed: {detail}")
        return []
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        if diagnostics is not None:
            diagnostics.append(f"Get-Disk returned invalid JSON: {exc}")
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        if diagnostics is not None:
            diagnostics.append("Get-Disk returned an unexpected JSON shape")
        return []

    candidates: list[dict[str, Any]] = []
    for item in data:
        try:
            number = int(item["Number"])
        except (KeyError, TypeError, ValueError):
            if diagnostics is not None:
                diagnostics.append("Get-Disk returned an entry without a valid disk number")
            continue
        try:
            size = int(item["Size"]) if item.get("Size") is not None else None
        except (TypeError, ValueError):
            size = None
        candidates.append({
            "source": rf"\\.\PhysicalDrive{number}",
            "metadata": {
                "number": number,
                "name": item.get("FriendlyName"),
                "bus": item.get("BusType"),
                "size": size,
                "partition_style": item.get("PartitionStyle"),
            },
        })
    return sorted(candidates, key=lambda x: x["metadata"]["number"])


def linux_candidates(diagnostics: list[str] | None = None) -> list[dict[str, Any]]:
    del diagnostics
    sys_block = Path("/sys/block")
    if not sys_block.exists():
        return []
    skip_prefixes = ("loop", "ram", "zram", "dm-", "md", "sr", "fd", "nbd")
    candidates: list[dict[str, Any]] = []
    for entry in sorted(sys_block.iterdir()):
        name = entry.name
        if name.startswith(skip_prefixes) or "boot" in name or name.endswith("rpmb"):
            continue
        device = Path("/dev") / name
        if not device.exists():
            continue

        def read_text(path: Path) -> str | None:
            try:
                return path.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                return None

        sectors_text = read_text(entry / "size")
        size = int(sectors_text) * SECTOR_SIZE if sectors_text and sectors_text.isdigit() else None
        model = read_text(entry / "device/model")
        removable = read_text(entry / "removable")
        candidates.append({
            "source": str(device),
            "metadata": {"name": model or name, "size": size, "removable": removable == "1"},
        })
    return candidates


def get_candidates(diagnostics: list[str] | None = None) -> list[dict[str, Any]]:
    return windows_candidates(diagnostics) if os.name == "nt" else linux_candidates(diagnostics)


def print_human_result(
    result: dict[str, Any], lang: dict[str, str], verbose: bool, explicit: bool
) -> None:
    source = result["source"]
    meta = result.get("metadata", {})
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if not result.get("opened"):
        if explicit or verbose or errors:
            print(f"- {source}: {lang['access']}")
            for err in errors:
                print(f"  {lang['error']}: {err}")
        return

    hw = result.get("hwconfig")
    if not result.get("aura_hd"):
        if hw and hw.get("pcb_e606c0"):
            print()
            print(lang["probable"])
            print(f"{lang['source']}: {source}")
        elif errors:
            print(f"- {source}: {lang['not_kobo']}")
        elif verbose or explicit:
            print(f"- {source}: {lang['not_kobo']}")
        if errors:
            for err in errors:
                print(f"  {lang['error']}: {err}")
        if (verbose or explicit) and warnings:
            for warning in warnings:
                print(f"  {lang['warning']}: {warning}")
        return

    print()
    print("=" * 72)
    print(lang["found"])
    print("=" * 72)
    print(f"{lang['source']}: {source}")
    if meta.get("name"):
        print(f"{lang['model']}: {meta['name']}")
    if result.get("source_size") is not None:
        size = result["source_size"]
        print(f"{lang['size']}: {size:,} bytes ({human_size(size)})")
    if hw:
        print(
            f"{lang['hw']}: {hw.get('version', '?')} @ 0x{hw.get('offset', 0):X}, "
            f"{hw.get('payload_size', '?')} bytes"
        )
        fields = hw.get("fields", {})
        decoded = hw.get("decoded", {})
        pcb = fields.get("bPCB")
        print(f"{lang['pcb']}: {pcb} -> {decoded.get('bPCB', '?')}")
        print(f"{lang['identity']}: {hw.get('identity')}")
        selected = [
            ("RAM", "bRamSize"), ("RAM type", "bRamType"), ("CPU", "bCPU"),
            ("CPU frequency", "bCPUFreq"), ("Display", "bDisplayResolution"),
            ("Frontlight", "bFrontLight"), ("Hall sensor", "bHallSensor"),
            ("Display bus", "bDisplayBusWidth"),
            ("Frontlight LED driver", "bFrontLight_LED_Driver"),
        ]
        for label, field in selected:
            if field in fields:
                value = fields[field]
                decoded_value = decoded.get(field)
                if isinstance(decoded_value, list):
                    decoded_value = ", ".join(decoded_value) if decoded_value else "none"
                suffix = f" -> {decoded_value}" if decoded_value is not None else ""
                print(f"  {label}: {value}{suffix}")

    mbr = result.get("mbr", {})
    print(f"{lang['partitions']}:")
    if not mbr.get("valid"):
        print("  MBR: invalid / not fully validated")
    for part in mbr.get("partitions", []):
        fs = part.get("filesystem", "?")
        label = part.get("label", "")
        label_text = f' label="{label}"' if label else ""
        extra = " beyond_end" if part.get("beyond_end") else ""
        print(
            f"  P{part['number']}: offset={part['offset']:,}  size={part['size']:,}  "
            f"type=0x{part['type']:02X}  {fs}{label_text}{extra}"
        )

    if result.get("pre_p1_sha256"):
        print(
            f"{lang['boot_hash']}: {result['pre_p1_sha256']} "
            f"({result.get('pre_p1_size', 0):,} bytes)"
        )
    for err in errors:
        print(f"{lang['error']}: {err}")
    for warning in warnings:
        print(f"{lang['warning']}: {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only inspector for Kobo Aura HD / Dragon raw microSD cards and full-disk images."
    )
    parser.add_argument(
        "source", nargs="?",
        help="Full-disk image or raw device. If omitted, locally attached disks are scanned read-only.",
    )
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--hash-boot", action="store_true",
        help="Compute SHA-256 from byte 0 to the first MBR partition start, only after Aura HD identification.",
    )
    args = parser.parse_args()
    lang = FR if args.lang == "fr" else EN

    if not args.json_output:
        print(lang["title"])
        print(lang["readonly"])

    explicit = bool(args.source)
    discovery_errors: list[str] = []
    if explicit:
        candidates = [{"source": args.source, "metadata": {}}]
    else:
        candidates = get_candidates(discovery_errors)
        if not args.json_output:
            print(lang["scanning"].format(count=len(candidates)))
            if os.name != "nt" and "microsoft" in platform.release().lower():
                print(lang["wsl"])
            for error in discovery_errors:
                print(lang["discovery_error"].format(error=error))

    results = [
        inspect_source(item["source"], item.get("metadata"), args.hash_boot)
        for item in candidates
    ]

    if args.json_output:
        print(json.dumps(
            {
                "schema_version": JSON_SCHEMA_VERSION,
                "discovery_errors": discovery_errors,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ))
    else:
        for result in results:
            print_human_result(result, lang, args.verbose, explicit)
        unreadable = sum(1 for result in results if not result.get("opened"))
        read_errors = sum(1 for result in results if result.get("opened") and result.get("errors"))
        if not explicit and unreadable:
            print(lang["unreadable_summary"].format(count=unreadable))
        if not explicit and read_errors:
            print(lang["read_error_summary"].format(count=read_errors))

    good_matches = [r for r in results if r.get("aura_hd") and not r.get("errors")]
    any_matches = [r for r in results if r.get("aura_hd")]
    fatal_read_errors = any(r.get("errors") and not r.get("aura_hd") for r in results)

    if good_matches:
        return 0
    if any_matches:
        return 2
    if not args.json_output:
        print()
        print(lang["no_found"])
    if explicit and fatal_read_errors:
        return 2
    if not explicit and (discovery_errors or (candidates and all(not r.get("opened") for r in results))):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
