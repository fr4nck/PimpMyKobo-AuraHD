#!/usr/bin/env python3
"""Recover the private PMKB candidate bundle from an existing qualification Live.

The source is read-only. It may be either:
- an extracted/mounted Live root containing /opt/pmkb; or
- a SquashFS image such as live/filesystem.squashfs.

Only local files in DESTINATION are created. Physical/block-device paths are
explicitly refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class RecoveryError(RuntimeError):
    pass


METADATA_NAMES = (
    "candidate.json",
    "restore-plan.json",
    "BUILD-IDENTITY.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{path}: JSON illisible: {exc}") from exc
    if not isinstance(data, dict):
        raise RecoveryError(f"{path}: la racine JSON doit être un objet")
    return data


def ensure_regular_source(path: Path) -> None:
    if str(path).startswith("/dev/"):
        raise RecoveryError("les périphériques /dev/* sont refusés; fournissez un répertoire Live ou filesystem.squashfs")
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise RecoveryError(f"source inaccessible: {path}: {exc}") from exc
    if stat.S_ISBLK(mode) or stat.S_ISCHR(mode):
        raise RecoveryError("les périphériques physiques sont refusés")


def locate_bundle_dir(root: Path) -> Path:
    candidates = (root / "opt" / "pmkb", root)
    for candidate in candidates:
        if all((candidate / name).is_file() for name in METADATA_NAMES):
            return candidate
    raise RecoveryError(f"bundle PMKB introuvable sous {root}")


def extract_squashfs(source: Path, destination: Path, *, unsquashfs: str = "unsquashfs") -> Path:
    executable = shutil.which(unsquashfs)
    if executable is None:
        raise RecoveryError(
            "unsquashfs introuvable; installez squashfs-tools ou fournissez un Live déjà extrait"
        )
    result = subprocess.run(
        [
            executable,
            "-no-progress",
            "-d",
            str(destination),
            str(source),
            "opt/pmkb",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unsquashfs failed").strip()
        raise RecoveryError(f"extraction SquashFS échouée: {detail}")
    return locate_bundle_dir(destination)


def validate_bundle(bundle_dir: Path) -> dict[str, Any]:
    manifest_path = bundle_dir / "candidate.json"
    plan_path = bundle_dir / "restore-plan.json"
    identity_path = bundle_dir / "BUILD-IDENTITY.json"

    manifest = load_json(manifest_path)
    plan = load_json(plan_path)
    identity = load_json(identity_path)

    image_name = manifest.get("image_name")
    if not isinstance(image_name, str) or not image_name or Path(image_name).name != image_name:
        raise RecoveryError("candidate.json: image_name invalide")

    image_path = bundle_dir / image_name
    if not image_path.is_file():
        raise RecoveryError(f"candidat embarqué absent: {image_name}")

    try:
        image_size = int(manifest["image_size"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RecoveryError("candidate.json: image_size invalide") from exc

    expected_image_sha = manifest.get("image_sha256")
    if not isinstance(expected_image_sha, str) or len(expected_image_sha) != 64:
        raise RecoveryError("candidate.json: image_sha256 invalide")

    if image_path.stat().st_size != image_size:
        raise RecoveryError(
            f"taille candidat incohérente: {image_path.stat().st_size} != {image_size}"
        )

    image_sha = sha256_file(image_path)
    manifest_sha = sha256_file(manifest_path)
    plan_sha = sha256_file(plan_path)

    if image_sha != expected_image_sha:
        raise RecoveryError(f"SHA-256 candidat incohérent: {image_sha} != {expected_image_sha}")
    if identity.get("image_name") != image_name:
        raise RecoveryError("BUILD-IDENTITY.json: image_name divergent")
    if identity.get("image_sha256") != image_sha:
        raise RecoveryError("BUILD-IDENTITY.json: SHA candidat divergent")
    if identity.get("manifest_sha256") != manifest_sha:
        raise RecoveryError("BUILD-IDENTITY.json: SHA manifest divergent")
    if identity.get("plan_sha256") != plan_sha:
        raise RecoveryError("BUILD-IDENTITY.json: SHA plan divergent")
    if plan.get("replacement_sha256") != image_sha:
        raise RecoveryError("restore-plan.json: candidat divergent")
    if plan.get("write_authorized") is not False:
        raise RecoveryError("restore-plan.json: write_authorized doit rester false")
    if plan.get("physical_restore_eligible") is not False:
        raise RecoveryError("restore-plan.json: physical_restore_eligible doit rester false")

    return {
        "status": "valid",
        "image_name": image_name,
        "image_size": image_size,
        "image_sha256": image_sha,
        "manifest_sha256": manifest_sha,
        "plan_sha256": plan_sha,
        "identity_schema": identity.get("schema", 1),
        "candidate_head": identity.get("candidate_head", identity.get("head")),
        "live_head": identity.get("live_head"),
    }


def copy_bundle(bundle_dir: Path, destination: Path, report: dict[str, Any]) -> Path:
    if destination.exists():
        if not destination.is_dir():
            raise RecoveryError(f"destination non répertoire: {destination}")
        if any(destination.iterdir()):
            raise RecoveryError(f"destination non vide: {destination}")
    else:
        destination.mkdir(parents=True, exist_ok=False)

    names = list(METADATA_NAMES) + [str(report["image_name"])]
    for name in names:
        shutil.copyfile(bundle_dir / name, destination / name)

    copied = validate_bundle(destination)
    for key in ("image_sha256", "manifest_sha256", "plan_sha256"):
        if copied[key] != report[key]:
            raise RecoveryError(f"relecture destination incohérente: {key}")

    receipt = destination / "RECOVERED-BUNDLE.json"
    receipt.write_text(
        json.dumps(
            {
                **copied,
                "validation_status": copied["status"],
                "status": "recovered",
                "source_access": "read_only",
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt


def recover(source: Path, destination: Path, *, unsquashfs: str = "unsquashfs") -> dict[str, Any]:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    ensure_regular_source(source)

    if source.is_dir():
        bundle_dir = locate_bundle_dir(source)
        report = validate_bundle(bundle_dir)
        report["source_kind"] = "live_root"
        receipt = copy_bundle(bundle_dir, destination, report)
        report["receipt"] = str(receipt)
        return report

    if not source.is_file():
        raise RecoveryError(f"source ni fichier ni répertoire: {source}")

    with tempfile.TemporaryDirectory(prefix="pmkb-live-recover-") as td:
        bundle_dir = extract_squashfs(source, Path(td), unsquashfs=unsquashfs)
        report = validate_bundle(bundle_dir)
        report["source_kind"] = "squashfs"
        receipt = copy_bundle(bundle_dir, destination, report)
        report["receipt"] = str(receipt)
        return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="racine Live extraite/montée, ou fichier live/filesystem.squashfs",
    )
    parser.add_argument("destination", type=Path, help="répertoire local vide à créer/remplir")
    parser.add_argument(
        "--unsquashfs",
        default="unsquashfs",
        help="nom/chemin de unsquashfs pour une source SquashFS",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = recover(args.source, args.destination, unsquashfs=args.unsquashfs)
    except RecoveryError as exc:
        print(f"STOP: {exc}")
        return 2

    print("OK — bundle PMKB privé récupéré et revérifié")
    print(f"Candidat : {report['image_name']}")
    print(f"Taille   : {report['image_size']}")
    print(f"SHA-256  : {report['image_sha256']}")
    print(f"Plan     : {report['plan_sha256']}")
    print(f"Rapport  : {report['receipt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
