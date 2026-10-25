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

## Tableau de pilotage

| Lot | Statut | Branche / SHA de départ | Travail livré / prévu | Qualification | Prochain sous-lot |
| --- | --- | --- | --- | --- | --- |
| L00 — État des lieux | **DONE** | `main@6ff6cabb` | Inventaire + journal, documentation seule | API/lecture statique PASS ; CI et physique NON EXÉCUTÉS | L01-A |
| L01 — FIRST BOOT | TODO | À vérifier sur PR #7 et #28 | Matrice des gates, dépendances et correctif/test minimal si possible | NON EXÉCUTÉ pour ce lot | L01-A |
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
