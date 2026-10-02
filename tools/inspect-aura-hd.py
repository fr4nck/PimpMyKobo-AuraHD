#!/usr/bin/env python3
"""
inspect-aura-hd.py - read-only inspector for Kobo Aura HD / Dragon microSD cards.

This tool NEVER opens a source for writing.
It can inspect a full-disk image or raw physical device and can auto-scan
locally attached disks on Windows and Linux.
"""

from __future__ import annotations

import argparse
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

HW_FIELDS = [
    "bPCB",
    "bKeyPad",
    "bAudioCodec",
    "bAudioAmp",
    "bWifi",
    "bBT",
    "bMobile",
    "bTouchCtrl",
    "bTouchType",
    "bDisplayCtrl",
    "bDisplayPanel",
    "bRSensor",
    "bMicroP",
    "bCustomer",
    "bBattery",
    "bLed",
    "bRamSize",
    "bIFlash",
    "bExternalMem",
    "bRootFsType",
    "bSysPartType",
    "bProgressXHiByte",
    "bProgressXLoByte",
    "bProgressYHiByte",
    "bProgressYLoByte",
    "bProgressCnts",
    "bContentType",
    "bCPU",
    "bUIStyle",
    "bRamType",
    "bUIConfig",
    "bDisplayResolution",
    "bFrontLight",
    "bCPUFreq",
    "bHallSensor",
    "bDisplayBusWidth",
    "bFrontLight_Flags",
    "bPCB_Flags",
    "bFrontLight_LED_Driver",
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
    "no_found": "Aucune Kobo Aura HD E606C0 n'a été identifiée.",
    "source": "Source",
    "model": "Matériel",
    "size": "Taille",
    "hw": "HWCONFIG",
    "pcb": "PCB",
    "identity": "Identification",
    "partitions": "Partitions MBR",
    "boot_hash": "SHA-256 zone avant P1",
    "access": "inaccessible en lecture",
    "not_kobo": "pas de HWCONFIG Aura HD reconnu",
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
    "no_found": "No Kobo Aura HD E606C0 was identified.",
    "source": "Source",
    "model": "Device",
    "size": "Size",
    "hw": "HWCONFIG",
    "pcb": "PCB",
    "identity": "Identification",
    "partitions": "MBR partitions",
    "boot_hash": "SHA-256 pre-P1 area",
    "access": "not readable",
    "not_kobo": "no recognized Aura HD HWCONFIG",
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
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{value} B"


def read_at(handle: BinaryIO, offset: int, size: int) -> bytes:
    handle.seek(offset)
    return handle.read(size)


def parse_mbr(handle: BinaryIO) -> dict[str, Any]:
    sector = read_at(handle, 0, SECTOR_SIZE)
    if len(sector) != SECTOR_SIZE or sector[510:512] != b"\x55\xaa":
        return {"valid": False, "partitions": []}

    partitions = []
    for index in range(4):
        entry = sector[446 + 16 * index : 446 + 16 * (index + 1)]
        ptype = entry[4]
        start_lba = int.from_bytes(entry[8:12], "little")
        sectors = int.from_bytes(entry[12:16], "little")
        if ptype == 0 or sectors == 0:
            continue
        partitions.append(
            {
                "number": index + 1,
                "type": ptype,
                "start_lba": start_lba,
                "sectors": sectors,
                "offset": start_lba * SECTOR_SIZE,
                "size": sectors * SECTOR_SIZE,
            }
        )
    return {"valid": True, "partitions": partitions}


def detect_filesystem(handle: BinaryIO, offset: int) -> dict[str, Any]:
    sb = read_at(handle, offset + 1024, 1024)
    if len(sb) >= 136 and sb[56:58] == b"\x53\xef":
        label = sb[120:136].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
        return {"filesystem": "ext", "label": label}

    boot = read_at(handle, offset, SECTOR_SIZE)
    if len(boot) >= 90:
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
    if len(header) != HWCONFIG_HEADER_SIZE or header[:10] != b"HW CONFIG ":
        return None

    version = header[10:15].split(b"\x00", 1)[0].decode("ascii", "replace")
    payload_size = header[15]
    payload = read_at(handle, HWCONFIG_OFFSET + HWCONFIG_HEADER_SIZE, payload_size)
    if len(payload) != payload_size:
        return {
            "offset": HWCONFIG_OFFSET,
            "version": version,
            "payload_size": payload_size,
            "truncated": True,
            "raw": payload.hex(),
        }

    fields = {}
    for index, value in enumerate(payload):
        name = HW_FIELDS[index] if index < len(HW_FIELDS) else f"unknown_{index}"
        fields[name] = value

    decoded = {}
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
    is_aura_hd = pcb == 28

    return {
        "offset": HWCONFIG_OFFSET,
        "version": version,
        "payload_size": payload_size,
        "truncated": False,
        "fields": fields,
        "decoded": decoded,
        "is_aura_hd_e606c0": is_aura_hd,
        "identity": "Kobo Aura HD / Dragon / E606C0" if is_aura_hd else None,
    }


def sha256_region(handle: BinaryIO, offset: int, size: int) -> str:
    import hashlib

    h = hashlib.sha256()
    handle.seek(offset)
    remaining = size
    while remaining:
        chunk = handle.read(min(4 * 1024 * 1024, remaining))
        if not chunk:
            raise OSError("unexpected end of source while hashing")
        h.update(chunk)
        remaining -= len(chunk)
    return h.hexdigest()


def inspect_source(source: str, metadata: dict[str, Any] | None, hash_boot: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": source,
        "metadata": metadata or {},
        "readable": False,
        "aura_hd": False,
    }
    try:
        with open(source, "rb", buffering=0) as handle:
            result["readable"] = True
            mbr = parse_mbr(handle)
            hw = parse_hwconfig(handle)
            result["mbr"] = mbr
            result["hwconfig"] = hw

            for partition in mbr["partitions"]:
                try:
                    partition.update(detect_filesystem(handle, partition["offset"]))
                except OSError as exc:
                    partition["filesystem_error"] = str(exc)

            if hw and hw.get("is_aura_hd_e606c0"):
                result["aura_hd"] = True

            if hash_boot and mbr["partitions"]:
                first_offset = min(p["offset"] for p in mbr["partitions"])
                if first_offset > 0:
                    result["pre_p1_sha256"] = sha256_region(handle, 0, first_offset)
                    result["pre_p1_size"] = first_offset
    except (OSError, PermissionError) as exc:
        result["error"] = str(exc)
    return result


def windows_candidates() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$ErrorActionPreference='Stop'; "
            "Get-Disk | Select-Object Number,FriendlyName,BusType,Size,PartitionStyle | "
            "ConvertTo-Json -Compress"
        ),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=15
        )
        data = json.loads(completed.stdout)
        if isinstance(data, dict):
            data = [data]
        candidates = []
        for item in data:
            number = int(item["Number"])
            candidates.append(
                {
                    "source": rf"\\.\PhysicalDrive{number}",
                    "metadata": {
                        "number": number,
                        "name": item.get("FriendlyName"),
                        "bus": item.get("BusType"),
                        "size": int(item["Size"]) if item.get("Size") is not None else None,
                        "partition_style": item.get("PartitionStyle"),
                    },
                }
            )
        return sorted(candidates, key=lambda x: x["metadata"]["number"])
    except Exception:
        return [
            {"source": rf"\\.\PhysicalDrive{i}", "metadata": {"number": i}}
            for i in range(16)
        ]


def linux_candidates() -> list[dict[str, Any]]:
    sys_block = Path("/sys/block")
    if not sys_block.exists():
        return []

    skip_prefixes = ("loop", "ram", "zram", "dm-", "md", "sr", "fd")
    candidates = []
    for entry in sorted(sys_block.iterdir()):
        name = entry.name
        if name.startswith(skip_prefixes):
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
        candidates.append(
            {
                "source": str(device),
                "metadata": {
                    "name": model or name,
                    "size": size,
                    "removable": removable == "1",
                },
            }
        )
    return candidates


def get_candidates() -> list[dict[str, Any]]:
    if os.name == "nt":
        return windows_candidates()
    return linux_candidates()


def print_human_result(result: dict[str, Any], lang: dict[str, str], verbose: bool) -> None:
    source = result["source"]
    meta = result.get("metadata", {})
    if not result.get("readable"):
        if verbose:
            print(f"- {source}: {lang['access']} ({result.get('error', '?')})")
        return

    hw = result.get("hwconfig")
    if not result.get("aura_hd"):
        if verbose:
            print(f"- {source}: {lang['not_kobo']}")
        return

    print()
    print("=" * 72)
    print(lang["found"])
    print("=" * 72)
    print(f"{lang['source']}: {source}")
    if meta.get("name"):
        print(f"{lang['model']}: {meta['name']}")
    if meta.get("size") is not None:
        print(f"{lang['size']}: {meta['size']:,} bytes ({human_size(meta['size'])})")

    if hw:
        print(
            f"{lang['hw']}: {hw.get('version', '?')} @ 0x{hw.get('offset', 0):X}, "
            f"{hw.get('payload_size', '?')} bytes"
        )
        fields = hw.get("fields", {})
        decoded = hw.get("decoded", {})
        pcb = fields.get("bPCB")
        pcb_name = decoded.get("bPCB", "?")
        print(f"{lang['pcb']}: {pcb} -> {pcb_name}")
        print(f"{lang['identity']}: {hw.get('identity')}")

        selected = [
            ("RAM", "bRamSize"),
            ("RAM type", "bRamType"),
            ("CPU", "bCPU"),
            ("CPU frequency", "bCPUFreq"),
            ("Display", "bDisplayResolution"),
            ("Frontlight", "bFrontLight"),
            ("Hall sensor", "bHallSensor"),
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
        print("  MBR: invalid / not found")
    else:
        for p in mbr.get("partitions", []):
            fs = p.get("filesystem", "?")
            label = p.get("label", "")
            label_text = f' label="{label}"' if label else ""
            print(
                f"  P{p['number']}: offset={p['offset']:,}  size={p['size']:,}  "
                f"type=0x{p['type']:02X}  {fs}{label_text}"
            )

    if result.get("pre_p1_sha256"):
        print(
            f"{lang['boot_hash']}: {result['pre_p1_sha256']} "
            f"({result.get('pre_p1_size', 0):,} bytes)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only inspector for Kobo Aura HD / Dragon raw microSD cards and full-disk images."
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        help=(
            "Full-disk image or raw device. If omitted, locally attached disks are scanned read-only."
        ),
    )
    parser.add_argument("--lang", choices=("fr", "en"), default="fr")
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Print machine-readable JSON."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also report skipped/inaccessible devices during auto-scan.",
    )
    parser.add_argument(
        "--hash-boot",
        action="store_true",
        help="Compute SHA-256 from byte 0 to the first MBR partition start.",
    )
    args = parser.parse_args()

    lang = FR if args.lang == "fr" else EN

    if not args.json_output:
        print(lang["title"])
        print(lang["readonly"])

    if args.source:
        candidates = [{"source": args.source, "metadata": {}}]
    else:
        candidates = get_candidates()
        if not args.json_output:
            print(lang["scanning"].format(count=len(candidates)))
            if os.name != "nt" and "microsoft" in platform.release().lower():
                print(lang["wsl"])

    results = [
        inspect_source(item["source"], item.get("metadata"), args.hash_boot)
        for item in candidates
    ]

    if args.json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print_human_result(result, lang, args.verbose)

    found = any(result.get("aura_hd") for result in results)
    if not found and not args.json_output:
        print()
        print(lang["no_found"])
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
