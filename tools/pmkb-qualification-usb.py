#!/usr/bin/env python3
"""PMKB FIRST BOOT physical qualification helper.

The default mode is read-only. Physical writes are restricted to the already
identified P1 block partition and require a fresh preflight plus a typed local
confirmation. The whole-disk device is never opened for writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_MANIFEST = Path("/opt/pmkb/candidate.json")
DEFAULT_IMAGE = Path("/opt/pmkb/PMKB-FIRST-BOOT-1-0b00d858.img")
CHUNK = 4 * 1024 * 1024


class QualificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Partition:
    number: int
    path: str
    offset: int
    size: int


@dataclass(frozen=True)
class Target:
    disk_path: str
    size: int
    model: str
    serial: str
    partitions: tuple[Partition, ...]

    def partition(self, number: int) -> Partition:
        for item in self.partitions:
            if item.number == number:
                return item
        raise QualificationError(f"partition P{number} absente")


def run_json(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise QualificationError(f"commande échouée ({proc.returncode}): {' '.join(argv)}\n{proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise QualificationError(f"JSON invalide depuis {' '.join(argv)}: {exc}") from exc


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"image_name", "image_size", "image_sha256", "disk", "pre_p1", "partitions"}
    missing = sorted(required - data.keys())
    if missing:
        raise QualificationError(f"manifest incomplet: {', '.join(missing)}")
    if data["disk"].get("partition_table") != "dos":
        raise QualificationError("manifest: partition_table doit être dos/MBR")
    return data


def sha256_file(path: Path, length: int | None = None) -> str:
    h = hashlib.sha256()
    remaining = length
    with path.open("rb", buffering=0) as handle:
        while True:
            if remaining is not None and remaining <= 0:
                break
            want = CHUNK if remaining is None else min(CHUNK, remaining)
            block = handle.read(want)
            if not block:
                break
            h.update(block)
            if remaining is not None:
                remaining -= len(block)
    if remaining not in (None, 0):
        raise QualificationError(f"lecture courte de {path}: {remaining} octets manquants")
    return h.hexdigest()


def sha256_region(path: Path, offset: int, length: int) -> str:
    h = hashlib.sha256()
    remaining = length
    with path.open("rb", buffering=0) as handle:
        handle.seek(offset)
        while remaining:
            block = handle.read(min(CHUNK, remaining))
            if not block:
                raise QualificationError(f"lecture courte de {path} à l'offset {offset}")
            h.update(block)
            remaining -= len(block)
    return h.hexdigest()


def _flatten_lsblk(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in nodes:
        out.append(node)
        out.extend(_flatten_lsblk(node.get("children") or []))
    return out


def lsblk_snapshot() -> list[dict[str, Any]]:
    data = run_json([
        "lsblk", "-J", "-b", "-o",
        "PATH,NAME,TYPE,SIZE,TRAN,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS,PKNAME",
    ])
    return _flatten_lsblk(data.get("blockdevices") or [])


def sfdisk_snapshot(disk_path: str) -> dict[str, Any]:
    return run_json(["sfdisk", "--json", disk_path])


def _partition_number(path: str, disk_path: str) -> int | None:
    if not path.startswith(disk_path):
        return None
    suffix = path[len(disk_path):]
    if suffix.startswith("p"):
        suffix = suffix[1:]
    return int(suffix) if suffix.isdigit() else None


def validate_layout(disk_path: str, sfdisk: dict[str, Any], manifest: dict[str, Any]) -> tuple[Partition, ...]:
    table = sfdisk.get("partitiontable") or {}
    if table.get("label") not in {"dos", "mbr"}:
        raise QualificationError(f"{disk_path}: table attendue MBR/dos, trouvée {table.get('label')!r}")
    sector_size = int(table.get("sectorsize") or manifest["disk"].get("sector_size") or 512)
    expected = {int(p["number"]): p for p in manifest["partitions"]}
    found: dict[int, Partition] = {}
    for item in table.get("partitions") or []:
        node = str(item.get("node") or "")
        number = _partition_number(node, disk_path)
        if number is None:
            continue
        found[number] = Partition(
            number=number,
            path=node,
            offset=int(item["start"]) * sector_size,
            size=int(item["size"]) * sector_size,
        )
    if set(found) != set(expected):
        raise QualificationError(f"{disk_path}: partitions {sorted(found)} != attendues {sorted(expected)}")
    for number, spec in expected.items():
        got = found[number]
        if got.offset != int(spec["offset"]) or got.size != int(spec["size"]):
            raise QualificationError(
                f"{disk_path} P{number}: offset/taille {got.offset}/{got.size} != "
                f"{spec['offset']}/{spec['size']}"
            )
    return tuple(found[n] for n in sorted(found))


def discover_target(manifest: dict[str, Any]) -> Target:
    wanted_size = int(manifest["disk"]["size"])
    candidates: list[Target] = []
    for node in lsblk_snapshot():
        if node.get("type") != "disk" or int(node.get("size") or 0) != wanted_size:
            continue
        path = str(node.get("path") or "")
        if not path.startswith("/dev/") or path.startswith("/dev/loop"):
            continue
        try:
            parts = validate_layout(path, sfdisk_snapshot(path), manifest)
        except QualificationError:
            continue
        candidates.append(Target(
            disk_path=path,
            size=wanted_size,
            model=str(node.get("model") or "").strip(),
            serial=str(node.get("serial") or "").strip(),
            partitions=parts,
        ))
    if not candidates:
        raise QualificationError("aucune microSD ne correspond exactement à la géométrie Aura HD attendue")
    if len(candidates) != 1:
        names = ", ".join(c.disk_path for c in candidates)
        raise QualificationError(f"cible ambiguë: {len(candidates)} disques correspondent ({names})")
    return candidates[0]


def ensure_block_device(path: str) -> None:
    mode = os.stat(path).st_mode
    if not stat.S_ISBLK(mode):
        raise QualificationError(f"{path}: la cible d'écriture n'est pas un périphérique bloc")


def mounted_partitions(target: Target) -> list[str]:
    rows = {str(x.get("path")): x for x in lsblk_snapshot()}
    mounted: list[str] = []
    for part in target.partitions:
        entry = rows.get(part.path, {})
        points = [p for p in (entry.get("mountpoints") or []) if p]
        if points:
            mounted.append(f"{part.path} -> {', '.join(points)}")
    return mounted


def verify_candidate(image: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if not image.is_file():
        raise QualificationError(f"image candidate absente: {image}")
    size = image.stat().st_size
    expected_size = int(manifest["image_size"])
    if size != expected_size:
        raise QualificationError(f"image: taille {size} != {expected_size}")
    digest = sha256_file(image)
    if digest != manifest["image_sha256"]:
        raise QualificationError(f"image: SHA-256 {digest} != {manifest['image_sha256']}")
    return {"size": size, "sha256": digest}


def preflight(target: Target, image: Path, manifest: dict[str, Any], *, require_unmounted: bool) -> dict[str, Any]:
    if target.size != int(manifest["disk"]["size"]):
        raise QualificationError("taille disque modifiée depuis l'identification")
    parts = validate_layout(target.disk_path, sfdisk_snapshot(target.disk_path), manifest)
    if parts != target.partitions:
        raise QualificationError("géométrie/chemins de partitions modifiés depuis l'identification")
    image_info = verify_candidate(image, manifest)
    pre = manifest["pre_p1"]
    pre_hash = sha256_region(Path(target.disk_path), int(pre["offset"]), int(pre["size"]))
    if pre_hash != pre["sha256"]:
        raise QualificationError(f"PRE-P1 SHA-256 inattendu: {pre_hash}")
    p2spec = next(p for p in manifest["partitions"] if int(p["number"]) == 2)
    p2_hash = sha256_region(Path(target.disk_path), int(p2spec["offset"]), int(p2spec["size"]))
    if p2_hash != p2spec["sha256"]:
        raise QualificationError(f"P2/recoveryfs SHA-256 inattendu: {p2_hash}")
    mounts = mounted_partitions(target)
    if require_unmounted and mounts:
        raise QualificationError("partitions montées: " + "; ".join(mounts))
    return {
        "disk": target.disk_path,
        "model": target.model,
        "serial": target.serial,
        "image": image_info,
        "pre_p1_sha256": pre_hash,
        "p2_sha256": p2_hash,
        "mounted": mounts,
    }


def confirmation_phrase(manifest: dict[str, Any]) -> str:
    return f"ECRIRE P1 {manifest['image_sha256'][:8]}"


def ensure_supported_write_host() -> None:
    release = platform.release().lower()
    if "microsoft" in release or "wsl" in release:
        raise QualificationError("écriture physique refusée sous WSL; démarrez sur le Live USB PMKB")
    if os.name != "posix" or not sys.platform.startswith("linux"):
        raise QualificationError("écriture physique autorisée uniquement sous Linux natif/Live")


def write_partition(image: Path, partition_path: str, expected_size: int) -> None:
    ensure_supported_write_host()
    ensure_block_device(partition_path)
    if image.stat().st_size != expected_size:
        raise QualificationError("la taille du candidat ne correspond plus à P1")
    written = 0
    flags = os.O_RDWR | getattr(os, "O_EXCL", 0) | getattr(os, "O_SYNC", 0)
    fd = os.open(partition_path, flags)
    with image.open("rb", buffering=0) as src, os.fdopen(fd, "r+b", buffering=0) as dst:
        while written < expected_size:
            block = src.read(min(CHUNK, expected_size - written))
            if not block:
                raise QualificationError("fin prématurée du candidat pendant l'écriture")
            count = dst.write(block)
            if count != len(block):
                raise QualificationError(f"écriture courte sur P1: {count}/{len(block)}")
            written += count
        if src.read(1):
            raise QualificationError("le candidat contient des données au-delà de la taille de P1")
        dst.flush()
        os.fsync(dst.fileno())
    os.sync()


def _same_target(a: Target, b: Target) -> bool:
    return a.disk_path == b.disk_path and a.size == b.size and a.partitions == b.partitions


def perform_write(image: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    target = discover_target(manifest)
    before = preflight(target, image, manifest, require_unmounted=True)
    phrase = confirmation_phrase(manifest)
    print("\nÉCRITURE — seule P1 sera modifiée.")
    print(f"Cible : {target.disk_path} / {target.partition(1).path}")
    print("PRE-P1 et P2 sont vérifiées. P2/recoveryfs restera en lecture seule.")
    typed = input(f"Tapez exactement « {phrase} » pour autoriser l'écriture : ").strip()
    if typed != phrase:
        raise QualificationError("confirmation refusée; aucune écriture effectuée")

    again = discover_target(manifest)
    if not _same_target(target, again):
        raise QualificationError("la cible a changé après confirmation; STOP")
    preflight(again, image, manifest, require_unmounted=True)
    p1 = again.partition(1)
    if p1.size != int(manifest["image_size"]):
        raise QualificationError("P1 n'a pas exactement la taille du candidat")

    write_partition(image, p1.path, p1.size)

    p1_hash = sha256_file(Path(p1.path), p1.size)
    if p1_hash != manifest["image_sha256"]:
        raise QualificationError(f"P1 relue: SHA-256 inattendu {p1_hash}")
    after = preflight(again, image, manifest, require_unmounted=True)
    return {"before": before, "after": after, "p1_sha256": p1_hash}


def print_header(manifest: dict[str, Any]) -> None:
    print("=" * 66)
    print(" PimpMyKobo — Aura HD E606C0 — FIRST BOOT #1 qualification")
    print("=" * 66)
    print(f" HEAD      {manifest.get('head', '?')}")
    print(f" CANDIDAT  {manifest['image_sha256']}")
    print(" P2/recoveryfs et les 9 961 472 premiers octets sont sacrés.")
    print()


def human_preflight(image: Path, manifest: dict[str, Any], require_unmounted: bool = False) -> Target:
    target = discover_target(manifest)
    report = preflight(target, image, manifest, require_unmounted=require_unmounted)
    print(f"[✓] Carte reconnue : {target.disk_path} ({target.size} octets)")
    print("[✓] MBR et géométrie P1/P2/P3 conformes")
    print(f"[✓] PRE-P1 : {report['pre_p1_sha256']}")
    print(f"[✓] P2      : {report['p2_sha256']}")
    print(f"[✓] Candidat: {report['image']['sha256']}")
    if report["mounted"]:
        print("[!] Partitions actuellement montées :")
        for item in report["mounted"]:
            print(f"    {item}")
    else:
        print("[✓] Aucune partition cible montée")
    return target


def menu(image: Path, manifest: dict[str, Any]) -> int:
    while True:
        os.system("clear")
        print_header(manifest)
        print(" 1. Identifier et vérifier la microSD         [LECTURE SEULE]")
        print(" 2. Écrire le candidat sur P1                 [ÉCRITURE]")
        print(" 3. Vérifier P1 / PRE-P1 / P2 après écriture [LECTURE SEULE]")
        print(" 4. Afficher les invariants")
        print(" 0. Quitter")
        choice = input("\nChoix : ").strip()
        try:
            if choice == "1":
                human_preflight(image, manifest)
            elif choice == "2":
                result = perform_write(image, manifest)
                print("\n[✓] P1 écrite et relue")
                print(f"[✓] P1 SHA-256 : {result['p1_sha256']}")
                print("[✓] PRE-P1 toujours intact")
                print("[✓] P2/recoveryfs toujours intacte")
                print("\nPMKB FIRST BOOT #1 — READY FOR POWER")
            elif choice == "3":
                target = human_preflight(image, manifest, require_unmounted=False)
                digest = sha256_file(Path(target.partition(1).path), int(manifest["image_size"]))
                marker = "✓" if digest == manifest["image_sha256"] else "✗"
                print(f"[{marker}] P1 SHA-256 : {digest}")
                if marker != "✓":
                    raise QualificationError("P1 ne correspond pas au candidat figé")
            elif choice == "4":
                print("PRE-P1 : 0..9 961 471 — jamais écrit")
                print("P1     : seule partition autorisée à l'écriture")
                print("P2     : recoveryfs — jamais écrit")
                print("P3     : KOBOeReader — jamais écrit par cet outil")
            elif choice == "0":
                return 0
            else:
                print("Choix invalide")
        except (QualificationError, OSError, subprocess.SubprocessError) as exc:
            print(f"\n[STOP] {exc}")
        input("\nEntrée pour continuer…")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--preflight", action="store_true", help="lecture seule, puis quitte")
    parser.add_argument("--write-p1", action="store_true", help="écriture P1 après garde-fous et confirmation")
    parser.add_argument("--menu", action="store_true", help="interface texte interactive")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        verify_candidate(args.image, manifest)
        if args.write_p1:
            print_header(manifest)
            result = perform_write(args.image, manifest)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.preflight:
            print_header(manifest)
            human_preflight(args.image, manifest)
            return 0
        return menu(args.image, manifest)
    except (QualificationError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
