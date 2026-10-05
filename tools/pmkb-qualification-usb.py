#!/usr/bin/env python3
"""PMKB FIRST BOOT qualification UI.

This module is deliberately not a physical writer. Every physical device open,
full-card comparison, rollback capture, durable journal and bounded P1 write is
performed by tools/restore-p1-linux.py, the single PMKB physical backend.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_MANIFEST = Path("/opt/pmkb/candidate.json")
DEFAULT_PLAN = Path("/opt/pmkb/restore-plan.json")
DEFAULT_IDENTITY = Path("/opt/pmkb/BUILD-IDENTITY.json")
DEFAULT_BACKEND = Path("/opt/pmkb/tools/restore-p1-linux.py")
LOCAL_BACKEND = Path(__file__).with_name("restore-p1-linux.py")
DEFAULT_IMAGE_DIR = Path("/opt/pmkb")
KEYMAP_ROOT = Path("/usr/share/keymaps")

COMMON_KEYMAPS = ("fr", "fr-latin9", "be", "ch-fr", "us", "uk", "de", "es", "it")

TEXT = {
    "fr": {
        "language_title": "Langue de l’interface / Interface language",
        "language_fr": "Français (défaut)",
        "language_en": "English",
        "language_prompt": "Choix [1] : ",
        "keyboard_title": "Clavier console",
        "keyboard_all": "99. Afficher tous les claviers disponibles",
        "keyboard_prompt": "Choix [défaut : {default}] : ",
        "keyboard_invalid": "Clavier inconnu. Choisissez un numéro, un nom exact ou 99.",
        "keyboard_loaded": "Clavier actif : {keymap}",
        "device_prompt": "Disque complet exact de la microSD (ex. /dev/sdb) : ",
        "journal_prompt": "Répertoire PERSISTANT pour journal + sauvegarde P1 : ",
        "menu_1": "Qualifier la microSD",
        "menu_2": "Écrire FIRST BOOT sur P1",
        "menu_3": "Vérifier P1 et tout l’extérieur de P1",
        "menu_4": "Afficher les invariants",
        "menu_5": "Changer langue / clavier",
        "menu_6": "Redémarrer le PC",
        "menu_7": "Éteindre le PC",
        "choice": "Choix : ",
        "confirm_reboot": "Confirmer le redémarrage ? [o/N] : ",
        "confirm_poweroff": "Confirmer l’arrêt du PC ? [o/N] : ",
        "invalid": "Choix invalide",
        "continue": "Entrée pour continuer…",
        "readonly_ok": "Cible qualifiée",
        "readonly_usb": "USB/amovible, non montée, sans swap/holders",
        "readonly_match": "Carte complète identique à la sauvegarde vérifiée",
        "write_ok": "P1 écrite puis relue",
        "write_outside": "Toute la zone hors P1 est inchangée",
        "verify_outside": "PRE-P1, P2, P3, gaps et octets hors P1 inchangés",
        "power_failed": "Commande systemd refusée",
    },
    "en": {
        "language_title": "Interface language / Langue de l’interface",
        "language_fr": "Français (default)",
        "language_en": "English",
        "language_prompt": "Choice [1]: ",
        "keyboard_title": "Console keyboard",
        "keyboard_all": "99. Show every available keyboard layout",
        "keyboard_prompt": "Choice [default: {default}]: ",
        "keyboard_invalid": "Unknown keyboard. Choose a number, an exact name, or 99.",
        "keyboard_loaded": "Active keyboard: {keymap}",
        "device_prompt": "Exact whole disk for the microSD (e.g. /dev/sdb): ",
        "journal_prompt": "PERSISTENT directory for journal + P1 backup: ",
        "menu_1": "Qualify the microSD",
        "menu_2": "Write FIRST BOOT to P1",
        "menu_3": "Verify P1 and everything outside P1",
        "menu_4": "Show invariants",
        "menu_5": "Change language / keyboard",
        "menu_6": "Reboot the PC",
        "menu_7": "Power off the PC",
        "choice": "Choice: ",
        "confirm_reboot": "Confirm reboot? [y/N]: ",
        "confirm_poweroff": "Confirm power off? [y/N]: ",
        "invalid": "Invalid choice",
        "continue": "Press Enter to continue…",
        "readonly_ok": "Target qualified",
        "readonly_usb": "USB/removable, unmounted, without swap/holders",
        "readonly_match": "Whole card is identical to the verified backup",
        "write_ok": "P1 written and read back",
        "write_outside": "Everything outside P1 is unchanged",
        "verify_outside": "PRE-P1, P2, P3, gaps and all bytes outside P1 are unchanged",
        "power_failed": "systemd command refused",
    },
}


class QualificationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise QualificationError(f"{path}: la racine JSON doit être un objet")
    return data


def load_manifest(path: Path) -> dict[str, Any]:
    data = load_json(path)
    required = {"image_name", "image_size", "image_sha256", "disk", "pre_p1", "partitions"}
    missing = sorted(required - data.keys())
    if missing:
        raise QualificationError("manifest incomplet: " + ", ".join(missing))
    name = data["image_name"]
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise QualificationError("manifest: image_name doit être un nom de fichier simple")
    if not _is_sha256(data["image_sha256"]):
        raise QualificationError("manifest: image_sha256 invalide")
    if data["disk"].get("partition_table") != "dos" or int(data["disk"].get("sector_size") or 0) != 512:
        raise QualificationError("manifest: géométrie disque PMKB invalide")
    return data


def load_identity(path: Path) -> dict[str, Any]:
    data = load_json(path)
    for key in ("head", "image_name", "image_sha256", "plan_sha256", "manifest_sha256"):
        if key not in data:
            raise QualificationError(f"identité Live incomplète: {key}")
    if not _is_sha256(data["image_sha256"]) or not _is_sha256(data["plan_sha256"]) or not _is_sha256(data["manifest_sha256"]):
        raise QualificationError("identité Live: empreinte SHA-256 invalide")
    return data


def load_backend(path: Path):
    selected = path
    if not selected.exists() and LOCAL_BACKEND.exists():
        selected = LOCAL_BACKEND
    if not selected.is_file():
        raise QualificationError(f"backend PMKB absent: {selected}")
    spec = importlib.util.spec_from_file_location("pmkb_restore_backend", selected)
    if spec is None or spec.loader is None:
        raise QualificationError(f"backend PMKB non chargeable: {selected}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for name in ("validate_sealed_plan", "execute_sealed_plan", "verify_written_sealed_plan"):
        if not hasattr(module, name):
            raise QualificationError(f"backend PMKB incomplet: {name}")
    return module


def image_path(manifest: dict[str, Any], override: Path | None = None) -> Path:
    return override if override is not None else DEFAULT_IMAGE_DIR / manifest["image_name"]


def validate_bundle(manifest_path: Path, plan_path: Path, identity_path: Path,
                    image: Path, backend) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load_manifest(manifest_path)
    identity = load_identity(identity_path)
    if not image.is_file():
        raise QualificationError(f"candidat absent: {image}")
    if image.stat().st_size != int(manifest["image_size"]):
        raise QualificationError("candidat: taille différente du manifest")
    image_sha = _sha256(image)
    if image_sha != manifest["image_sha256"]:
        raise QualificationError(f"candidat: SHA-256 inattendu {image_sha}")
    if identity["image_name"] != manifest["image_name"] or identity["image_sha256"] != image_sha:
        raise QualificationError("identité Live et candidat divergent")
    manifest_sha = _sha256(manifest_path)
    if identity["manifest_sha256"] != manifest_sha:
        raise QualificationError("manifest différent de celui scellé dans le Live")

    try:
        plan, plan_sha = backend.validate_sealed_plan(plan_path, image, identity["plan_sha256"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise QualificationError(str(exc)) from exc
    if plan_sha != identity["plan_sha256"]:
        raise QualificationError("plan scellé incohérent")

    p1spec = next((p for p in manifest["partitions"] if int(p["number"]) == 1), None)
    p2spec = next((p for p in manifest["partitions"] if int(p["number"]) == 2), None)
    if p1spec is None or p2spec is None:
        raise QualificationError("manifest: P1/P2 absentes")
    if (plan["disk_size"] != int(manifest["disk"]["size"])
            or plan["p1_offset"] != int(p1spec["offset"])
            or plan["p1_size"] != int(p1spec["size"])
            or plan["replacement_sha256"] != manifest["image_sha256"]
            or plan["preserved_sha256"]["pre_p1"] != manifest["pre_p1"]["sha256"]
            or plan["preserved_sha256"]["p2"] != p2spec.get("sha256")):
        raise QualificationError("plan scellé et manifest Aura HD divergent")
    return manifest, identity, plan


def _t(language: str, key: str) -> str:
    return TEXT.get(language, TEXT["fr"])[key]


def choose_language(input_func: Callable[[str], str] = input) -> str:
    while True:
        print("\n" + TEXT["fr"]["language_title"])
        print(f" 1. {TEXT['fr']['language_fr']}")
        print(f" 2. {TEXT['fr']['language_en']}")
        choice = input_func(TEXT["fr"]["language_prompt"]).strip()
        if choice in ("", "1"):
            return "fr"
        if choice == "2":
            return "en"
        print("Choix invalide / Invalid choice")


def available_keymaps(root: Path = KEYMAP_ROOT) -> dict[str, Path]:
    """Return every console keymap shipped in the Live image.

    Identifiers are paths relative to /usr/share/keymaps without the compressed
    keymap suffix, so duplicate basenames remain selectable without ambiguity.
    """
    found: dict[str, Path] = {}
    if not root.is_dir():
        return found
    suffixes = (".map.gz", ".kmap.gz", ".map", ".kmap")
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        suffix = next((item for item in suffixes if rel.endswith(item)), None)
        if suffix is None:
            continue
        found[rel[:-len(suffix)]] = path
    return found


def _find_keymap(keymaps: dict[str, Path], value: str) -> str | None:
    if value in keymaps:
        return value
    matches = [name for name in keymaps if Path(name).name == value]
    return matches[0] if len(matches) == 1 else None


def apply_keymap(identifier: str, keymaps: dict[str, Path], *,
                 run: Callable[..., Any] = subprocess.run) -> None:
    resolved = _find_keymap(keymaps, identifier)
    if resolved is None:
        raise QualificationError(f"clavier inconnu: {identifier}")
    result = run(
        ["loadkeys", str(keymaps[resolved])],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "loadkeys failed").strip()
        raise QualificationError(f"loadkeys {resolved}: {detail}")


def choose_keymap(language: str, input_func: Callable[[str], str] = input, *,
                  root: Path = KEYMAP_ROOT,
                  run: Callable[..., Any] = subprocess.run) -> str:
    keymaps = available_keymaps(root)
    if not keymaps:
        raise QualificationError("aucun clavier console disponible dans l'image Live")

    common: list[tuple[str, str]] = []
    seen: set[str] = set()
    for basename in COMMON_KEYMAPS:
        resolved = _find_keymap(keymaps, basename)
        if resolved is not None and resolved not in seen:
            common.append((basename, resolved))
            seen.add(resolved)

    default = (
        _find_keymap(keymaps, "fr")
        or _find_keymap(keymaps, "fr-latin9")
        or _find_keymap(keymaps, "us")
        or sorted(keymaps)[0]
    )
    while True:
        print("\n" + _t(language, "keyboard_title"))
        for index, (label, resolved) in enumerate(common, 1):
            suffix = "" if label == resolved else f" ({resolved})"
            print(f" {index}. {label}{suffix}")
        print(" " + _t(language, "keyboard_all"))
        choice = input_func(_t(language, "keyboard_prompt").format(default=Path(default).name)).strip()
        if choice == "":
            selected = default
        elif choice == "99":
            names = sorted(keymaps)
            for start in range(0, len(names), 3):
                print("  " + " | ".join(names[start:start + 3]))
            continue
        elif choice.isdigit() and 1 <= int(choice) <= len(common):
            selected = common[int(choice) - 1][1]
        else:
            selected = _find_keymap(keymaps, choice)
            if selected is None:
                print(_t(language, "keyboard_invalid"))
                continue
        apply_keymap(selected, keymaps, run=run)
        print(_t(language, "keyboard_loaded").format(keymap=selected))
        return selected


def configure_operator_environment(
    input_func: Callable[[str], str] = input,
    *,
    root: Path = KEYMAP_ROOT,
    run: Callable[..., Any] = subprocess.run,
) -> tuple[str, str]:
    language = choose_language(input_func=input_func)
    keymap = choose_keymap(language, input_func=input_func, root=root, run=run)
    return language, keymap


def systemctl_action(action: str, *, run: Callable[..., Any] = subprocess.run) -> None:
    if action not in ("reboot", "poweroff"):
        raise QualificationError(f"action systemd interdite: {action}")
    result = run(["systemctl", action], capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "systemctl failed").strip()
        raise QualificationError(f"{_t('fr', 'power_failed')}: {detail}")


def confirm_power(language: str, action: str,
                  input_func: Callable[[str], str] = input) -> bool:
    key = "confirm_reboot" if action == "reboot" else "confirm_poweroff"
    answer = input_func(_t(language, key)).strip().lower()
    return answer in {"o", "oui", "y", "yes"}


def confirmation_phrase(manifest: dict[str, Any], plan_sha256: str) -> str:
    return f"ECRIRE P1 {manifest['image_sha256'][:8]} PLAN {plan_sha256[:8]}"


def _backend_error(result: dict[str, Any], expected_status: str) -> QualificationError:
    errors = result.get("errors") or []
    detail = "; ".join(str(x) for x in errors) or f"statut {result.get('status')!r}"
    return QualificationError(f"backend PMKB: {detail}; attendu {expected_status}")


def preflight_device(backend, plan_path: Path, image: Path, expected_plan_sha256: str,
                     device: Path) -> dict[str, Any]:
    result = backend.execute_sealed_plan(
        plan_path, image, Path("/run/pmkb-readonly-unused.jsonl"),
        expected_plan_sha256=expected_plan_sha256,
        device=device, check_device=True, ack_linux_live=True,
    )
    if not result.get("complete") or result.get("status") != "device_ready_read_only":
        raise _backend_error(result, "device_ready_read_only")
    return result


def perform_write(backend, plan_path: Path, image: Path, manifest: dict[str, Any],
                  expected_plan_sha256: str, device: Path, journal_dir: Path,
                  *, language: str = "fr",
                  input_func: Callable[[str], str] = input) -> dict[str, Any]:
    before = preflight_device(backend, plan_path, image, expected_plan_sha256, device)
    phrase = confirmation_phrase(manifest, expected_plan_sha256)
    print("\nÉCRITURE — le backend PMKB unique écrira uniquement la plage P1.")
    print(f"Cible explicite : {device}")
    print("La carte complète correspond à la sauvegarde vérifiée.")
    print("Une copie durable de la P1 originale et un journal seront créés avant l'écriture.")
    typed = input_func(f"Tapez exactement « {phrase} » : ").strip()
    if typed != phrase:
        raise QualificationError("confirmation refusée; aucune écriture effectuée")

    if not journal_dir.is_dir():
        raise QualificationError(f"répertoire de journal absent: {journal_dir}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    journal = journal_dir / f"pmkb-first-boot-{stamp}.jsonl"
    result = backend.execute_sealed_plan(
        plan_path, image, journal,
        expected_plan_sha256=expected_plan_sha256,
        device=device, write_p1=True, ack_linux_live=True,
        authorize_plan_sha256=expected_plan_sha256,
    )
    if not result.get("complete") or result.get("status") != "ok":
        raise _backend_error(result, "ok")
    result["preflight"] = before
    result["journal"] = str(journal)
    return result


def verify_after_write(backend, plan_path: Path, image: Path, expected_plan_sha256: str,
                       device: Path) -> dict[str, Any]:
    result = backend.verify_written_sealed_plan(
        plan_path, image, expected_plan_sha256=expected_plan_sha256, device=device,
    )
    if not result.get("complete") or result.get("status") != "verified":
        raise _backend_error(result, "verified")
    return result


def ask_device(input_func: Callable[[str], str] = input, *, language: str = "fr") -> Path:
    value = input_func(_t(language, "device_prompt")).strip()
    if not value.startswith("/dev/"):
        raise QualificationError("cible explicite /dev/... obligatoire")
    return Path(value)


def ask_journal_dir(input_func: Callable[[str], str] = input, *, language: str = "fr") -> Path:
    value = input_func(_t(language, "journal_prompt")).strip()
    if not value:
        raise QualificationError("répertoire persistant obligatoire")
    return Path(value)


def print_header(manifest: dict[str, Any], identity: dict[str, Any], *, language: str = "fr", keymap: str | None = None) -> None:
    print("=" * 72)
    print(" PimpMyKobo — Aura HD E606C0 — FIRST BOOT #1 qualification")
    print("=" * 72)
    print(f" HEAD       {identity['head']}")
    print(f" CANDIDAT   {manifest['image_sha256']}")
    print(f" PLAN       {identity['plan_sha256']}")
    print(" Backend    restore-p1-linux.py (unique moteur d'accès physique)")
    if keymap is not None:
        print(f" Interface  {language.upper()}    Clavier {keymap}")
    print()


def menu(backend, manifest: dict[str, Any], identity: dict[str, Any],
         plan_path: Path, image: Path, *, language: str, keymap: str) -> int:
    while True:
        print_header(manifest, identity, language=language, keymap=keymap)
        print(f" 1. {_t(language, 'menu_1'):<44} [LECTURE SEULE / READ ONLY]")
        print(f" 2. {_t(language, 'menu_2'):<44} [ÉCRITURE / WRITE]")
        print(f" 3. {_t(language, 'menu_3'):<44} [LECTURE SEULE / READ ONLY]")
        print(f" 4. {_t(language, 'menu_4')}")
        print(f" 5. {_t(language, 'menu_5')}")
        print(f" 6. {_t(language, 'menu_6')}")
        print(f" 7. {_t(language, 'menu_7')}")
        choice = input("\n" + _t(language, "choice")).strip()
        try:
            if choice == "1":
                device = ask_device(language=language)
                result = preflight_device(backend, plan_path, image, identity["plan_sha256"], device)
                print(f"\n[✓] {_t(language, 'readonly_ok')} : {device}")
                print(f"[✓] {_t(language, 'readonly_usb')}")
                print(f"[✓] {_t(language, 'readonly_match')}")
                print(f"[✓] Plan : {result['plan_sha256']}")
            elif choice == "2":
                device = ask_device(language=language)
                journal_dir = ask_journal_dir(language=language)
                result = perform_write(
                    backend, plan_path, image, manifest, identity["plan_sha256"],
                    device, journal_dir, language=language,
                )
                print(f"\n[✓] {_t(language, 'write_ok')}")
                print(f"[✓] {_t(language, 'write_outside')}")
                print(f"[✓] P1 originale / original P1 : {result['rollback']}")
                print(f"[✓] Journal : {result['journal']}")
                print("\nPMKB FIRST BOOT #1 — READY FOR POWER")
            elif choice == "3":
                device = ask_device(language=language)
                result = verify_after_write(
                    backend, plan_path, image, identity["plan_sha256"], device,
                )
                print(f"\n[✓] P1 : {result['p1_reread_sha256']}")
                print(f"[✓] {_t(language, 'verify_outside')}")
            elif choice == "4":
                if language == "en":
                    print("\n- no automatic target discovery")
                    print("- native Linux/Live root only; WSL and containers refused")
                    print("- whole removable USB disk only")
                    print("- whole card compared with the backup before any write")
                    print("- durable P1 backup + journal before write intent")
                    print("- e2fsck -f -n on the staged candidate")
                    print("- no write outside P1")
                    print("- no automatic retry/rollback")
                else:
                    print("\n- aucune découverte automatique de cible")
                    print("- Linux natif/Live root uniquement; WSL et conteneurs refusés")
                    print("- disque complet amovible via USB uniquement")
                    print("- carte complète comparée à la sauvegarde avant écriture")
                    print("- sauvegarde P1 + journal durables avant write intent")
                    print("- e2fsck -f -n du candidat staged")
                    print("- aucune écriture hors plage P1")
                    print("- aucun retry/rollback automatique")
            elif choice == "5":
                language, keymap = configure_operator_environment()
            elif choice == "6":
                if confirm_power(language, "reboot"):
                    systemctl_action("reboot")
            elif choice == "7":
                if confirm_power(language, "poweroff"):
                    systemctl_action("poweroff")
            else:
                print(_t(language, "invalid"))
        except (QualificationError, OSError, ValueError) as exc:
            print(f"\n[STOP] {exc}")
        input("\n" + _t(language, "continue") + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--identity", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--backend", type=Path, default=DEFAULT_BACKEND)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--device", type=Path)
    parser.add_argument("--journal-dir", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--write-p1", action="store_true")
    modes.add_argument("--verify-after", action="store_true")
    modes.add_argument("--menu", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        backend = load_backend(args.backend)
        manifest = load_manifest(args.manifest)
        image = image_path(manifest, args.image)
        manifest, identity, _plan = validate_bundle(
            args.manifest, args.plan, args.identity, image, backend,
        )
        if args.preflight:
            if args.device is None:
                raise QualificationError("--preflight exige --device /dev/...")
            print_header(manifest, identity)
            print(json.dumps(preflight_device(
                backend, args.plan, image, identity["plan_sha256"], args.device,
            ), indent=2, ensure_ascii=False))
            return 0
        if args.write_p1:
            if args.device is None or args.journal_dir is None:
                raise QualificationError("--write-p1 exige --device et --journal-dir")
            print_header(manifest, identity)
            print(json.dumps(perform_write(
                backend, args.plan, image, manifest, identity["plan_sha256"],
                args.device, args.journal_dir,
            ), indent=2, ensure_ascii=False))
            return 0
        if args.verify_after:
            if args.device is None:
                raise QualificationError("--verify-after exige --device")
            print_header(manifest, identity)
            print(json.dumps(verify_after_write(
                backend, args.plan, image, identity["plan_sha256"], args.device,
            ), indent=2, ensure_ascii=False))
            return 0
        language, keymap = configure_operator_environment()
        return menu(
            backend, manifest, identity, args.plan, image,
            language=language, keymap=keymap,
        )
    except (QualificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
