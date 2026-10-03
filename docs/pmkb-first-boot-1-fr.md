# PMKB FIRST BOOT #1 — état de convergence

[English](pmkb-first-boot-1-en.md) | **Français**

Statut au 3 octobre 2026, branche `integration/pmkb-first-boot-1`. Ce document ne qualifie aucun démarrage matériel. Aucune écriture physique, aucun `/dev`, aucun `PhysicalDrive`, aucune modification de P2/recoveryfs n'a eu lieu dans ce lot.

## Origine

Trois chantiers parallèles convergent ici, chacun sur sa propre branche, aucune fusionnée dans `main` :

- `feat/build-koreader-rootfs` (`1b7c532`) : `build-koreader-rootfs`, l'assembleur/constructeur du rootfs KOReader direct.
- `feat/audit-arm-runtime` (`908b2a1`) : `audit-arm-runtime` (audit ELF/bootstrap/stockage) et `preflight-koreader` (agrégateur).
- `feat/rebuild-rootfs-spec` (`235085e`) : audit des interfaces matérielles (E-Ink, tactile Neonode v2, frontlight) sans Nickel, et une proposition de réglages KOReader indépendants de Nickel.

`integration/pmkb-first-boot-1` les fusionne tous les trois (cherry-pick de `235085e`, merge de `feat/audit-arm-runtime`) puis corrige les manques trouvés par la construction réelle de Codex sous Linux.

## 1. Corrections reprises du commit d'intégration local de Codex

| Correction | Où | Détail |
| --- | --- | --- |
| Résolution `$ORIGIN` dans RPATH/RUNPATH | `tools/audit-arm-runtime.py` | L'audit refusait auparavant *tout* RPATH/RUNPATH en bloc. `resolve_rpath()` étend désormais `$ORIGIN`/`${ORIGIN}` vers le répertoire contenant l'ELF (dans le rootfs invité), accepte les entrées absolues sans jeton, et refuse explicitement `$LIB`/`$PLATFORM` et tout chemin relatif qui reste ambigu après expansion. Les répertoires résolus s'ajoutent, par ELF, avant les trois répertoires par défaut (`/opt/koreader/libs`, `/lib`, `/usr/lib`). |
| `/usr/bin/pmkb-check-onboard` absent du contrat bootstrap | `tools/audit-arm-runtime.py` (`BOOT_SCRIPTS`) | Ce script (ajouté lors du lot précédent) n'était pas couvert par `--check-bootstrap`. Il l'est maintenant : bit d'exécution et shebang `#!/bin/sh` vérifiés comme les autres scripts. |
| `defaults.custom.lua` absent du contrat bootstrap | `tools/audit-arm-runtime.py` (`BOOT_DATA_FILES`) | Vérifié comme `reader.lua` : présence et non-vacuité, sans validation ELF ni shell. |
| Scanner Nickel permanent faux positif | `tools/preflight-koreader.py` (`nickel()`) | Appelait `_copy_tree`/`_scan_for_nickel` du constructeur directement sur l'arbre déjà fusionné, qui ne peut plus distinguer la surcouche de son propre contenu — chaque construction réelle échouait `nickel_signatures` à cause du commentaire « bypassing ... Nickel paths » de `pmkb-reader`. Corrigé en appelant `scan_tree_for_nickel(root)`, le point d'entrée public du constructeur conçu pour ce cas précis (déjà préparé lors du lot précédent, maintenant effectivement adopté). |

Ces quatre corrections sont désormais dans le code, testées, et non plus seulement dans une construction locale non versionnée.

## 2. Findings Nickel : classification

Reprenant et complétant la table d'audit de `235085e` (`docs/offline-hardware-qualification-fr.md`) :

| Chemin | Catégorie | Verdict |
| --- | --- | --- |
| `KOBO_LIGHT_ON_START=-2` par défaut → `_syncKoboLightOnStart()` → `NickelConf.frontLightLevel` | **Dépendance Nickel réelle** | Accès fichier réellement exécuté au démarrage normal si non désactivé ; le setter de secours peut échouer (`assert`) contre P3 en lecture seule. **Corrigé** : `KOBO_LIGHT_ON_START=-1` dans `defaults.custom.lua`, maintenant installé par le constructeur (section 3). |
| `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=true` par défaut → `saveSettings()` | **Dépendance Nickel réelle** | Idem : accès fichier réellement exécuté. **Corrigé** : `false` dans le même fichier. |
| `require(device/kobo/nickel_conf)` | **Compatibilité KOReader dormante** | Charge des définitions de fonctions ; aucun accès fichier tant que les deux réglages ci-dessus évitent les call-flows qui les invoquent. |
| Commentaire de `usr/bin/pmkb-reader` (« bypassing ... Nickel paths ») | **Finding informatif first-party** | Texte expliquant qu'on *évite* Nickel ; aucun accès fichier. Il reste visible dans le scanner mais ne bloque pas ; l'origine first-party n'est reconnue que si son SHA-256 correspond au dépôt. |
| `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL` dans `defaults.custom.lua` lui-même | **Finding informatif first-party** | Le nom de clé « NICKEL » reste visible. Le fichier n'est marqué `first_party_verified` que si son SHA-256 correspond au dépôt ; `true` ou l'absence de l'override sûr devient bloquant. |
| Marqueur `bin/kobo_config.sh`, `PRODUCT=dragon` | **Compatibilité KOReader dormante, pas une dépendance Nickel** | Détection matérielle réelle mais fichier propre à PMKB ; « Kobo » dans un nom de backend ne signifie pas Nickel. |
| `invertPageTurnButtons`, `external_keyboard_otg_mode_on_start`, `dbg.lua`, `ffi/rtc.lua` | **Commentaire/chaîne sans impact** | Documentation ou comparaison ; aucun des call-flows analysés par `235085e` ne les relie à un accès Nickel réel sur le chemin de démarrage normal. |
| Lanceur shell habituel de KOReader (retour Nickel, KFMon, restauration d'écran) | **Compatibilité KOReader dormante** | `pmkb-reader` appelle `reader.lua` directement, jamais ce lanceur ; son code de sortie n'est jamais atteint. |

**Conclusion : avec `defaults.custom.lua` installé (section 3), aucune dépendance Nickel n'est nécessaire au chemin normal de démarrage.** Ceci est démontré par le test `tests/offline-audit/nickel-settings.lua` (appel réel de `powerd.lua`/`nickel_conf.lua`/`luadefaults.lua`/`defaults.lua` du paquet KOReader vérifié, avec interception de toute ouverture du fichier Nickel — zéro accès observé avec les deux réglages) et par la classification du scanner : les signatures de compatibilité restent visibles, mais aucun finding bloquant n'est présent sur une construction synthétique propre.

## 3. Intégration du réglage KOReader démontré nécessaire

`experimental/offline-audit/defaults.custom.lua` (proposition de `235085e`, jusqu'ici non installée) est maintenant copié par le constructeur vers `opt/koreader/defaults.custom.lua` dans tout arbre assemblé — avant la fusion de `koreader_dir`, pour qu'un paquet KOReader fournissant déjà ce fichier entre en collision explicite plutôt que d'écraser silencieusement ce réglage de sécurité. C'est désormais un point d'entrée requis (`REQUIRED_ENTRYPOINTS`), vérifié par `audit-arm-runtime --check-bootstrap` (présence et non-vacuité) et identifié comme first-party uniquement par correspondance SHA-256 ; ses références Nickel restent visibles et informatives tant que les deux overrides sûrs sont présents.

Rien d'autre de `235085e` (audit E-Ink/tactile/frontlight, tests `offline-audit`) n'est intégré à la construction : non démontré nécessaire pour un premier boot logiciel, réservé à la qualification matérielle future.

## 4. Vérifications définitives (mission, point 4)

| Point | État | Preuve |
| --- | --- | --- |
| Scripts bootstrap exécutables | **Fait** (lot précédent, reconfirmé) | Bit exécutable posé directement dans l'index Git (`100755`) pour les 4 scripts + le nouveau `pmkb-check-onboard`, en renfort de `force_mode=0o755` du constructeur. `inittab` reste `100644` (donnée, pas un script). |
| `/mnt` et `/mnt/onboard` créés | **Fait** (lot précédent, reconfirmé) | `SKELETON_DIRS` du constructeur + `mkdir -p /mnt/onboard` dans `rcS` lui-même (défense en profondeur). |
| P3 revérifiée immédiatement avant lancement | **Fait, renforcé ce lot** | `pmkb-check-onboard` est maintenant la **dernière instruction avant `exec`** dans `pmkb-reader` (déplacé après `cd /opt/koreader`) : plus aucune opération ne s'intercale. Il lit `/proc/mounts`, une vue noyau **vivante**, pas un marqueur statique comme `/run/pmkb-ready` — c'est précisément ce qui ferme l'écart identifié : un démontage entre `rcS` et `pmkb-reader` est maintenant détecté, pas seulement un démontage avant `rcS`. Une vérification plus forte (comparaison d'identifiant de périphérique parent/enfant) a été envisagée mais écartée : elle ne serait pas testable avec des fixtures synthétiques (aucun vrai montage distinct possible sans matériel), pour un gain marginal au-delà d'une vue noyau déjà à jour. |
| `$ORIGIN` correctement géré | **Fait ce lot** | Section 1. Testé : résolution réussie, limitation au propre répertoire de l'ELF, refus de `$LIB`/`$PLATFORM`, refus d'un chemin relatif sans `$ORIGIN`. |
| Aucune dépendance Nickel nécessaire au chemin normal de boot | **Démontré** | Section 2. |

## 5. Convergence `build-koreader-rootfs` → `audit-arm-runtime` → `preflight-koreader`

Vérifié mécaniquement sur cette branche (les trois outils cohabitent désormais réellement, plus besoin d'un worktree jetable) :

1. `build-koreader-rootfs` assemble `experimental/offline-rootfs` + `experimental/offline-audit/defaults.custom.lua` + une version locale de KOReader + des composants runtime locaux en un répertoire.
2. `audit-arm-runtime --check-bootstrap --check-storage` audite ce répertoire sans le modifier : ELF ARM/dépendances (avec résolution `$ORIGIN`), permissions/scripts de lancement (y compris les deux nouveaux fichiers), structure `/mnt`/`/mnt/onboard`.
3. `preflight-koreader` agrège ces résultats plus le scanner Nickel désormais correct, avec verdicts `PASS`/`FAIL`/`UNQUALIFIED` par contrôle et globaux.

Le préflight distingue strictement les trois verdicts : un contrôle matériel (`framebuffer`, `touch`, `frontlight`, `p3_mount`, `usb_calibre`, `hardware_boot`) reste **toujours** `UNQUALIFIED` — ce dictionnaire n'a pas été touché dans ce lot et ne peut structurellement jamais devenir `PASS` sans un essai matériel distinct.

## 6. Reconstruction Linux — exacte

Sur Debian/WSL, avec `fakeroot`, `e2fsprogs` et une copie locale vérifiée de P2 (`recoveryfs`), une version extraite de KOReader (le répertoire contenant directement `reader.lua`/`luajit`/`libs/`) et un répertoire de composants runtime locaux non committés :

```bash
# 1. Image P1 expérimentale (Linux uniquement) ; 268 435 968 octets est la
#    taille P1 de référence du poste de développement — utiliser la taille
#    réellement enregistrée dans votre propre backup-manifest.json si différente.
python3 tools/build-koreader-rootfs.py \
    /chemin/koreader-vX.Y.Z/koreader \
    /chemin/runtime-aura-hd \
    --build PMKB-FIRST-BOOT-1.img \
    --reference-recovery /chemin/p2-recoveryfs.img \
    --size 268435968 \
    --json > PMKB-FIRST-BOOT-1.koreader-build.json

# 2. Même arbre, matérialisé séparément pour l'audit statique complet
#    (le répertoire temporaire de l'étape 1 est nettoyé après succès ;
#    ceci réutilise les mêmes fonctions publiques/internes, sans nouvel outil).
python3 - <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("builder", "tools/build-koreader-rootfs.py")
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
koreader = Path("/chemin/koreader-vX.Y.Z/koreader")
runtime = Path("/chemin/runtime-aura-hd")
dest = Path("PMKB-FIRST-BOOT-1-tree")
dest.mkdir()
manifest = {}
builder._copy_tree(builder.OVERLAY_ROOT, dest, manifest, {}, write=True, force_mode=0o755)
builder._add_skeleton_dirs(manifest, dest, write=True)
builder._place_reader_profile(dest, manifest, write=True)
builder._copy_tree(koreader, dest, manifest, {}, base="opt/koreader", write=True)
builder._copy_tree(runtime, dest, manifest, {}, write=True)
print("materialized:", dest)
PY

# 3. Audit statique complet (ELF/bootstrap/stockage) sur cet arbre
python3 tools/pmkb.py audit-arm-runtime PMKB-FIRST-BOOT-1-tree --check-bootstrap --check-storage

# 4. Préflight agrégé — doit afficher status != FAIL (UNQUALIFIED attendu
#    pour tous les éléments matériels, jamais PASS)
python3 tools/pmkb.py preflight-koreader PMKB-FIRST-BOOT-1-tree
```

Codé pour être reproductible : la sortie de l'étape 1 inclut le SHA-256 final de l'image et les paramètres ext4 utilisés dans `PMKB-FIRST-BOOT-1.img.koreader-build.json`.

## Interdits rappelés

Aucune étape ci-dessus n'écrit sur un périphérique physique, un `/dev`, un `PhysicalDrive`, ni ne modifie P2/recoveryfs. Aucun essai matériel n'est proposé par ce document. Le prochain GO matériel reste subordonné à une analyse commune du résultat réel Linux et à une autorisation explicite distincte.
