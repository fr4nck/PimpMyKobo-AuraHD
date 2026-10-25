# PMKB — Journal permanent des lots (autoprompt classique)

Date d'initialisation : **2026-10-25**. Dépôt : `fr4nck/PimpMyKobo-AuraHD`. Branche canonique de pilotage : `main`.

## Règles de reprise et de preuve

- Exécuter **un seul lot (ou sous-lot) par réponse**. À la reprise, lire ce journal, puis recontrôler l'état GitHub avant toute action.
- Conserver ce fichier par **mises à jour ciblées**. `TODO` = non commencé, `IN_PROGRESS` = commencé sans sortie qualifiée, `DONE` = périmètre du lot livré, `BLOCKED` = empêchement décrit.
- État d'un lot documentaire `DONE` ne qualifie ni le matériel, ni les composants des lots suivants.
- Séparer contrôles statiques GitHub, CI réellement exécutées, tests ajoutés mais non exécutés et tests physiques. Aucune réussite ne peut être déduite de la seule présence d'un test.
- Préserver P1 FIRST BOOT scellée et SHA, PRE-P1, P2/recoveryfs, HWCONFIG et waveform ; **aucune écriture physique** sans autorisation spécifique. Aucun téléchargement, flash, fusion de PR ou dépendance lourde implicite.
- Consulter `AGENTS.md`, `docs/recherche-sources-fr.md`, les contrats de la branche de travail et les PR avant modification.

## LOT 00 — État des lieux et pilotage

**Statut : DONE (inventaire documentaire et journal créés ; aucun code modifié).**

- Base avant opération : `main@6ff6cabb88dfdd017118ec4e0a4ef012f21c3834` (API GitHub, 25/10/2026).
- Contrats lus : `AGENTS.md` de `main` ; registre `docs/recherche-sources-fr.md` de `main`. `docs/native-ui-v0-contract-fr.md` **repéré**, mais non relu, sur la branche PR #30 : le lire avant L02/L03/L05.
- Branches : **18** branches renvoyées par l'API (dont `main`, `integration/pmkb-first-boot-1`, `feat/pmkb-powerlab-kernel-v0`, `feat/pmkb-ui-native-v0`, `fix/pmkb-launcher-v06-text-band-selection`, `feat/pmkb-notes-v01-host`, `feat/pmkb-notes-v02-typography-drawer`, `fix/pmkb-notes-multitab-guard`). Les anciennes branches documentaires FIRST BOOT existent aussi.
- PR **ouvertes : 7**, état API au 25/10/2026 :
  - [#7](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/7) FIRST BOOT, `integration/pmkb-first-boot-1` → `main`, ouverte, **pas draft**, tête `6b0506a`.
  - [#28](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/28) PowerLab / noyau / émulation R2, `feat/pmkb-powerlab-kernel-v0` → `main`, draft, tête `f74fbc0`.
  - [#30](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/30) PMKB-UI native, HAL, Notes, calculatrice, `feat/pmkb-ui-native-v0` → `main`, draft, tête `9514eff`.
  - [#25](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/25) Launcher V0.6, `fix/pmkb-launcher-v06-text-band-selection` → `main`, draft, tête `1071842`.
  - [#26](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/26) Notes V0.1, `feat/pmkb-notes-v01-host` → `main`, draft, tête `599a63b`.
  - [#27](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/27) Notes V0.2, `feat/pmkb-notes-v02-typography-drawer` → **`feat/pmkb-notes-v01-host`**, draft, tête `80621aa`.
  - [#29](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/29) Notes / clavier / pont KOReader, `fix/pmkb-notes-multitab-guard` → **`feat/pmkb-notes-v02-typography-drawer`**, draft, tête `f8f4e77`.
- Déjà couvert : audit noyau/ZForce R1/R3 (`docs/kernel-community-audit-2026-10-24-fr.md`), audits forks OKReader, Marek, FBInk, Rain92, HA-IPaper, Kobo Whiteboard, KoboTolinoFindings, lgeek et kobo-service dans `docs/` sur `main`. Le registre source contient aussi des références et livrables R2 sur la branche #28. **Ne pas recommencer ces explorations en bloc.**
- **Manquants vérifiés dans `docs/` sur `main` :** aucun fichier d'audit autonome explicitement intitulé **OcherBook** ou **ZenOS**, aucun journal précédent `pmkb-autoprompt-lots-status-fr.md`. Une référence ou une synthèse peut exister dans d'autres fichiers/branches : rechercher de façon ciblée seulement au lot intéressé, puis consolider sans relancer l'inventaire des forks.
- Écarts et chevauchements à surveiller : les PR #26 → #27 → #29 forment une chaîne **de bases imbriquées**, non trois changements indépendants ; la PR #30 comporte elle aussi Notes/calculatrice/HAL ; la PR #25 protège le Launcher et les illustrations approuvées ; la PR #28 couvre déjà PowerLab et R2. Requalifier le diff avant tout portage, et ne fusionner aucune PR automatiquement.
- Distinction de preuve : le registre des sources **rapporte** des tests antérieurs sur R1/R2 et la HAL ; ils **n'ont pas été réexécutés dans le LOT 00**. FIRST BOOT sur Aura HD reste **NON QUALIFIÉ PHYSIQUEMENT**.
- Tests LOT 00 : **contrôles statiques / inventaire API PASS : 6 catégories** (métadonnées dépôt, HEAD main, PR, branches, arborescences, lecture AGENTS + registre) ; **FAIL : 0 constaté** ; **tests unitaires, CI et matériel : NON EXÉCUTÉS**.
- Fichiers changés : ce journal uniquement. Pas de changement logiciel, de carte, d'image ou de branche PR.
- Publication : commit documentaire sur `main` avec `[skip ci]` ; voir historique du fichier pour SHA exact. Aucune PR créée ni fusionnée.
- Suite précise : **LOT 01-A** — sur #7, relever les contrats FIRST BOOT, la matrice P1/P2/P3 et les vérifications boot encore ouvertes ; croiser uniquement les travaux R2 existants sur #28 ; terminer par conditions satisfaites / non satisfaites / qualification physique en attente. Pas d'écriture matérielle.

## LOT 01 — FIRST BOOT, sous-lot L01-A

**Statut du lot global : IN_PROGRESS. Sous-lot L01-A : DONE.** Ne pas commencer L02 avant clôture explicite de L01.

- Départ : `main@a53f9f9f9968bb65c9d8b18bd51fb96a835985e2` ; PR #7 `integration/pmkb-first-boot-1@6b0506a085c3f19d818f71fbeebcd7c8da8c3abf` ; PR #28 `feat/pmkb-powerlab-kernel-v0@f74fbc0335fc22c6188f752e9526eca66704a41e`.
- **Livraison [matrice FIRST BOOT L01-A](first-boot-gates-l01a-2026-10-25-fr.md)** : géométrie PRE-P1/P1/P2/P3, outils déjà existants, séparation copie scellée / profil QEMU virtuel, 15 gates avec preuves et limites, six verdicts matériels `UNQUALIFIED`.
- **Fait réellement** : lecture statique des PR #7/#28, du contrat de démarrage, du rapport d'émulation R2, du partitionnement, de la qualification des interfaces et des boot gates. Aucune modification de code, firmware, image, matériel ou PR.
- **Tests L01-A** : PASS = contrôles statiques de cohérence documentaire et du commit documentaire (un seul fichier ajouté) ; FAIL = 0 constaté ; **CI, suites Python/Lua et essais matériels : NON EXÉCUTÉS**. Les chiffres des rapports historiques #7/#28 sont des résultats antérieurs cités, pas réexécutés.
- **Publication** : `main@055f07ca306f1d1947625d81850ee38498725e09`, commit documentaire `[skip ci]` ; aucune PR créée/fusionnée.
- **Gates restantes** : correspondance effective de l'image FIRST BOOT scellée avec le code, champs binaires U-Boot/uImage et r1/r2, exécution KOReader, EPDC, ZForce, frontlight, montage P3 et transfert Calibre. **Aucun GO matériel**. Les tests QEMU et copies privées restent non exécutés.
- **Suite précise : L01-B**, sur la branche existante de la PR #7, inspecter le code et les tests de `preflight-koreader` et du contrôle `pmkb-check-onboard` : vérifier que les six gates physiques ne deviennent jamais PASS via fixtures ou JSON synthétiques et qu'une P3 absente refuse le lancement. Si défaut prouvé : fixture/test minimal sur #7, sinon documenter ce contrôle. Pas de fusion, pas d'essai matériel, pas de téléchargement.

## LOT 01 — FIRST BOOT, sous-lot L01-B

**Statut global L01 : IN_PROGRESS. Sous-lot L01-B : DONE (correctif sur PR #7, CI non exécutée/indisponible au relevé).**

- **Départ confirmé le 25/10/2026** : `main@c3a91c9df31897bc3f7a6eb330fce19777e66692` et `integration/pmkb-first-boot-1@6b0506a085c3f19d818f71fbeebcd7c8da8c3abf` (PR [#7](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/7) ouverte, non fusionnée) ; PR #28 inchangée (`f74fbc0`).
- **Contrôle statique PASS** : `tools/preflight-koreader.py` initialise et conserve les six gates matérielles (`framebuffer`, `touch`, `frontlight`, `p3_mount`, `usb_calibre`, `hardware_boot`) à `UNQUALIFIED`, avec `hardware_qualified=false`, `physical_restore_eligible=false`, même si ses vérifications *logicielles* retournent `PASS`. Le préflight n'accorde donc pas de GO matériel.
- **Défaut concret reproduit** : l'ancien `pmkb-check-onboard` se limitait à `grep ' /mnt/onboard '` et acceptait une table synthétique annonçant **P1** sur `/mnt/onboard`. `pmkb-reader` appelle heureusement ce garde juste avant `exec` ; le corriger ferme cette confusion de source sans toucher au montage initial de `rcS`.
- **Correctif publié sur la branche existante PR #7** : commit [`39a3ca76884776dace2665e6cf9183b9b3672b09`](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/39a3ca76884776dace2665e6cf9183b9b3672b09). Deux fichiers seulement : `experimental/offline-rootfs/usr/bin/pmkb-check-onboard` et `tests/test_offline_guard.py`. Le garde valide **une seule** entrée `/mnt/onboard`, source exacte `/dev/mmcblk0p3`, format `vfat`, option `ro` ; refus des montages superposés, source/format/options incorrects et table absente. Script shell lisible, pas de dépendance ni service permanent, pas d'ouverture de P3 et aucune modification de partition.
- **Tests exécutés sur l'hôte, en copie isolée** : **5 tests Python ciblés PASS, 0 FAIL**, y compris reproduction du défaut ancien, rejet des autres sources/types/options/doublons et `sh -n` ; scripts et données **synthétiques**, aucun montage physique. **Tests `tests/test_offline_guard.py` ajoutés/étendus sur GitHub mais pas exécutés comme suite intégrale du dépôt**, et **CI GitHub : aucune exécution trouvée** à ce commit lors du relevé (`total_count=0`), ni test KOReader/ARM/physique. Ne jamais compter les nouveaux scénarios Git comme PASS CI.
- **Diff réellement relu** : commit parent `6b0506a`, exactement **2 fichiers**, shell +14/-4 lignes, tests +15/-0 ; la PR #7 pointe bien sur `39a3ca7`, reste ouverte non fusionnée. Image scellée, P1/P2/PRE-P1, drivers, U-Boot et PR #28 **inchangés**. Le garde valide les informations de la table `/proc/mounts`, pas l'identité physique cryptographique de la microSD : aucune qualification matérielle ne s'en déduit.
- **Suite précise L01-C** : recontrôler Actions pour `39a3ca7`, qualifier les nouveaux tests de `test_offline_guard.py` dans une exécution concrète si possible **sans téléchargement ni CI coûteuse supplémentaire**, puis clôturer L01 si aucun autre défaut logiciel prouvé (gates matérielles encore en attente), sans fusion ni écriture réelle.

## LOT 01 — FIRST BOOT, sous-lot L01-C

**Sous-lot L01-C : DONE. LOT 01 global : IN_PROGRESS** (un défaut de garde tactile, déjà documenté, interdit la clôture sans examen).

- **Départ vérifié le 25/10/2026** : `main@c3a91c9df31897bc3f7a6eb330fce19777e66692`, PR [#7](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/7) toujours ouverte, non fusionnée, `integration/pmkb-first-boot-1@39a3ca76884776dace2665e6cf9183b9b3672b09`. Aucun commit de code supplémentaire en L01-C.
- **CI GitHub** : requête Actions filtrée sur `head_sha=39a3ca76884776dace2665e6cf9183b9b3672b09` : **0 run trouvé** (`total_count=0`). Le workflow `.github/workflows/tests.yml` est présent, mais **aucun PASS CI revendiqué ni nouvelle CI déclenchée**.
- **Qualification réellement exécutée** : six fichiers ciblés de la PR #7, lus via connecteur GitHub, recopiés dans une arborescence Linux isolée **sans clone ni téléchargement de dépôt/firmware/dépendance**. Leur empreinte **Git blob SHA-1** a été vérifiée contre les six SHA renvoyés par GitHub, toutes concordantes. Fichiers : `tests/test_offline_guard.py` (`cd240aeb`), `pmkb-check-onboard` (`0f99dd06`), `pmkb-check-offline` (`aa7a09bd`), `pmkb-reader` (`65051081`), `rcS` (`887fc3c9`), `kobo_config.sh` (`79197ebb`). Python **3.13.5**, shell POSIX. Commande exécutée : `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<tests-isolés> python3 -m unittest -v test_offline_guard.OfflineGuardTests test_offline_guard.RootfsSourceContractTests`.
- **Résultat : 5 tests PASS, 0 FAIL**, 0.030 seconde : présence unique P3 RO VFAT et rejets des fixtures négatives (dont sources P1, type faux, RW, doublons), réseau OFFLINE, syntaxe `sh -n` des cinq scripts, ordre création de `/mnt/onboard` et recontrôle juste avant `exec` KOReader. Les scénarios sont **des fichiers synthétiques** ; aucun montage réel, aucune ouverture de `/dev`, aucune image ou carte altérée.
- **NON EXÉCUTÉS** : `ExperimentalContractTests` du même module (requiert `test_restore_rootfs.py` et les outils de restauration non copiés), reste de la suite du dépôt, GitHub Actions, construction ARM/KOReader, QEMU et essais réels E-Ink/tactile/frontlight/USB. Ne pas afficher `5/5` comme une validation de tout FIRST BOOT.
- **Obstacle logiciel restant constaté directement dans `rcS`** : `[ -c /dev/input/event0 ] && [ -c /dev/input/event1 ]` exige deux numéros fixes **sans identifier le parent `zForce-ir-touch`**, alors que `eventN` dépend de l'ordre des périphériques ; `ntx_io` n'est pas vérifié. C'est déjà signalé par `docs/offline-boot-gates-fr.md`. Un démarrage valide peut être refusé ou un autre input confondu avec le tactile. Ne pas déclarer L01 globalement DONE tant que cette condition n'a pas été contre-qualifiée.
- **Publication** : uniquement mise à jour de ce journal sur `main` avec `[skip ci]` ; PR #7 et #28, image scellée, PRE-P1 et P2 **inchangées**. Aucun GO matériel.
- **Reprise exacte : L01-D** — audit ciblé du garde de présence `eventN` dans `rcS` : identification de `zForce-ir-touch` via sysfs plutôt que deux numéros arbitraires, contrôle de `ntx_io` si nécessaire et fixtures de périphériques synthétiques. Changement limité au bootstrap + tests sur la PR #7 si justifié ; ne pas commencer L02 ni réécrire le pilote tactile.

## Tableau de pilotage

| Lot | Statut | Branche / SHA de départ | Travail livré / prévu | Qualification | Prochain sous-lot |
| --- | --- | --- | --- | --- | --- |
| L00 — État des lieux | **DONE** | `main@6ff6cabb` | Inventaire + journal, documentation seule | API/lecture statique PASS ; CI et physique NON EXÉCUTÉS | L01-A |
| L01 — FIRST BOOT | **IN_PROGRESS** (L01-A/B/C DONE) | `main@c3a91c9`, PR #7 `39a3ca7`, PR #28 `f74fbc0` | [Matrice 15 gates L01-A](first-boot-gates-l01a-2026-10-25-fr.md), garde P3 et qualification ciblée L01-C | **5/5 tests ciblés PASS, 0 FAIL**, 6 blobs vérifiés ; CI/boot NON EXÉCUTÉS | **L01-D** |
| L02 — HWCONFIG / ZForce / rotation | TODO | À déterminer ; consulter PR #30 | Fixtures des orientations et événements, comparer la HAL existante | NON EXÉCUTÉ | L02-A |
| L03 — Moteur e-ink | TODO | À déterminer ; consulter PR #30 | Banc d'invalidation / gris / refresh, sans moteur concurrent | NON EXÉCUTÉ | L03-A |
| L04 — Énergie / Wi-Fi / reprise | TODO | À déterminer ; consulter PR #28 | Contrats de veille, SDIO et RTC ; réseau à la demande | NON EXÉCUTÉ | L04-A |
| L05 — Launcher / widgets / Notes | TODO | À déterminer ; PR #25, #26-27-29, #30 | Correctif UX ciblé ; respecter ADR-005, 8 illustrations | NON EXÉCUTÉ | L05-A |
| L06 — Store *.pmkb | TODO | À déterminer | Contrat de manifeste, répertoire de test et exemple | NON EXÉCUTÉ | L06-A |
| L07 — Tableau blanc | TODO | À déterminer | Démo hors ligne à traits persistants | NON EXÉCUTÉ | L07-A |
| L08 — Maison | TODO | À déterminer | Interface locale sur JSON synthétique, sans serveur | NON EXÉCUTÉ | L08-A |
| L09 — Lecture / partitions | TODO | À déterminer | Grille / Thème ; visionneuse testable | NON EXÉCUTÉ | L09-A |
| L10 — Utilitaires natifs | TODO | À déterminer ; consulter #30 | Démarrer par le composant le plus mûr (calculatrice à requalifier) | NON EXÉCUTÉ | L10-A |
| L11 — Intégration | TODO | À déterminer | Matrice de conformité et coûts, sans fusion automatique | NON EXÉCUTÉ | L11-A |

**Commande de reprise :** `CONTINUE PMKB` → lire ce journal et l'API GitHub courante, exécuter seulement le premier sous-lot incomplet, qualifier, documenter et arrêter.
