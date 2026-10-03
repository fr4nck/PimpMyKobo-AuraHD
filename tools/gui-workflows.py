"""Local-only GUI requests. No Qt dependency, device discovery or restore route."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
from pathlib import Path
from typing import NamedTuple

spec = importlib.util.spec_from_file_location("gui_legacy", Path(__file__).with_name("import-legacy-backup.py"))
legacy = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(legacy)

MAX_REPORT_BYTES = 16 * 1024 * 1024
ALLOWED_COMMANDS = frozenset(("inspect", "import-legacy", "rebuild-rootfs", "simulate", "prepare-p1"))


class Field(NamedTuple):
    key: str
    label: str
    kind: str = "file"


class Workflow(NamedTuple):
    title: str
    description: str
    button: str
    command: str | None
    fields: tuple[Field, ...]
    flags: tuple[str, ...] = ()
    consent: str = ""
    consent_required: bool = False


REBUILD = (Field("manifest", "Manifeste de sauvegarde"), Field("recovery", "Image P2 — recovery"),
           Field("output", "Nouvelle image P1", "output"))
SIMULATION = (Field("manifest", "Manifeste historique"), Field("rebuild", "Rapport de reconstruction"),
              Field("rootfs", "Image P1 reconstruite"), Field("backup", "Image complète de la carte"),
              Field("output", "Nouvelle image complète", "output"))
LEGACY_CONSENT = "Accepter la provenance historique déclarée pour cette opération sur fichiers."
WORKFLOWS = {
    "report": Workflow("Lire un rapport", "Consulter un rapport existant sans rejouer ses contrôles.",
                       "Ouvrir le rapport", None, (Field("report", "Rapport JSON"),)),
    "inspect": Workflow("Inspecter une image", "Lire le MBR et le HWCONFIG d'une image complète sélectionnée.",
                        "Inspecter l'image", "inspect", (Field("image", "Image complète de la carte"),),
                        ("--json", "--hash-boot")),
    "import": Workflow("Importer une sauvegarde historique", "Qualifier les fichiers disponibles sans inventer de sauvegarde native.",
                       "Créer le manifeste", "import-legacy",
                       (Field("prefix", "Fichier de la zone pré-P1"), Field("recovery", "Image P2 — recovery"),
                        Field("output", "Nouveau manifeste JSON", "output"),
                        Field("prefix_sha", "SHA-256 attendu de la zone pré-P1", "sha"),
                        Field("recovery_sha", "SHA-256 attendu de P2", "sha")), (),
                       "Je déclare que ces deux fichiers proviennent de la même carte. Cette association n'est pas vérifiée.", True),
    "rebuild-plan": Workflow("Préparer une reconstruction", "Vérifier les entrées et la taille prévue de P1 sans créer d'image.",
                             "Vérifier les entrées", "rebuild-rootfs", REBUILD, ("--json",), LEGACY_CONSENT),
    "rebuild": Workflow("Reconstruire P1", "Créer une nouvelle image locale à partir du recovery. Linux ou WSL requis.",
                        "Créer l'image P1", "rebuild-rootfs", REBUILD, ("--json", "--build"), LEGACY_CONSENT),
    "simulate-plan": Workflow("Préparer une simulation", "Vérifier les fichiers avant de copier une image complète.",
                              "Vérifier les entrées", "simulate", SIMULATION, (), LEGACY_CONSENT, True),
    "simulate": Workflow("Simuler le remplacement de P1", "Créer une nouvelle copie complète de l'image avec P1 remplacée. Prévoir l'espace pour cette copie.",
                         "Créer l'image simulée", "simulate", SIMULATION, ("--simulate",), LEGACY_CONSENT, True),
    "prepare-p1": Workflow("Préparer le plan P1", "Relier sauvegarde, reconstruction et simulation dans un plan local. Aucune restauration n'est lancée.",
                           "Créer le plan", "prepare-p1",
                           (Field("manifest", "Manifeste historique"), Field("rebuild", "Rapport de reconstruction"),
                            Field("rootfs", "Image P1 reconstruite"), Field("backup", "Sauvegarde complète"),
                            Field("acquisition", "Rapport d'acquisition"), Field("simulated", "Image complète simulée"),
                            Field("simulation_report", "Rapport de simulation"), Field("output", "Nouveau plan JSON", "output")),
                           (), LEGACY_CONSENT, True),
}


def local_path(value: str, output: bool = False) -> Path:
    if not value.strip():
        raise ValueError("Sélectionnez tous les fichiers nécessaires.")
    path = Path(value.strip()).expanduser()
    legacy.reject_device(path)
    if output:
        if path.exists() or path.is_symlink():
            raise ValueError("Le fichier de sortie existe déjà. Choisissez un nouveau nom.")
        if not path.parent.is_dir():
            raise ValueError("Le dossier de sortie doit exister.")
    else:
        legacy.regular(path)
    return path.resolve()


def build_request(key: str, values: dict[str, str], consent: bool = False) -> list[str]:
    if key not in WORKFLOWS or WORKFLOWS[key].command not in ALLOWED_COMMANDS:
        raise ValueError("Cette opération n'est pas disponible dans l'atelier local.")
    workflow = WORKFLOWS[key]
    if set(values) != {field.key for field in workflow.fields}:
        raise ValueError("Champs inattendus ou manquants.")
    if workflow.consent_required and not consent:
        raise ValueError("Confirmez la déclaration de provenance avant de continuer.")
    validated = {}
    for field in workflow.fields:
        if field.kind == "sha":
            value = values[field.key].strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"{field.label} : 64 caractères hexadécimaux sont requis.")
            validated[field.key] = value
        else:
            validated[field.key] = str(local_path(values[field.key], field.kind == "output"))
    args = [workflow.command]
    args.extend(validated[field.key] for field in workflow.fields if field.kind != "sha")
    args.extend(workflow.flags)
    if key == "import":
        args.extend(("--expected-pre-p1-sha256", validated["prefix_sha"],
                     "--expected-p2-sha256", validated["recovery_sha"], "--declare-same-source"))
    elif consent and workflow.command in ("rebuild-rootfs", "simulate"):
        args.append("--accept-legacy-import")
    return args


def read_report(value: str) -> dict:
    path = local_path(value)
    with path.open("rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("Le rapport ouvert n'est pas un fichier ordinaire.")
        data = handle.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("Rapport trop volumineux pour cette interface (16 Mio maximum).")
    result = json.loads(data.decode("utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("Le rapport JSON doit être un objet.")
    return result


def save_report(path: str, report: dict) -> Path:
    output = local_path(path, output=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return output
