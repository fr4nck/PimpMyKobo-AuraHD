# PMKB — Contre-expertise indépendante Claude / BOOT CONTRACT V1

Daté du 18 octobre 2026. **Audit critique souhaité**, lecture seule, sans adopter les conclusions de ChatGPT. Aucun Work/Codex requis pour cette passation ; ne pas supposer accès au PC 5700X, à la Kobo, aux sauvegardes privées ou au réseau local.

## Périmètre

Dépôt : https://github.com/fr4nck/PimpMyKobo-AuraHD . Branche unique concernée : feat/pmkb-powerlab-kernel-v0 ; PR #28 (DRAFT). Fichiers nouveaux : docs/boot-contract-v1-fr.md, docs/kernel-driver-matrix-v1-fr.md, experimental/power-lab/boot_contract.py, tests/test_boot_contract.py. État initial avant ce lot : d240fcc. Lire également les sept documents historiques cités dans le contrat.

## Hypothèses à contredire, pas à accepter

1. L'association HWCONFIG 28 → 11 n'est **pas** une preuve d'un machine ID ARM ; rechercher l'initialisation de r1 et les ATAG dans U-Boot.
2. Offsets pré-P1 (0x80000, 0x100000, 0x700000) ≠ adresses physiques RAM ; vérifier sans extrapolation IH_LOAD/IH_EP, paramètres hwcfg_p/waveform_p et réservations.
3. La présence de imx50.dtsi et du DTS Kobo **N514 E606F0B** sous Linux v6.18 n'établit pas un DTS Aura HD **N204 E606C0**.
4. Le pilote ntxec v6.18 rejette les versions MCU inconnues : trouver les versions supportées et vérifier si l'Aura HD correspond ; ne pas présumer du firmware.
5. zforce_ts v6.18 ≠ compatibilité automatique du ZForce v2 de la Kobo.
6. Un driver LCDIF/DRM n'est pas l'EPDC waveform de cette génération ; expliquer les pièces de portage nécessaires.
7. Le validateur ne sait rien de la décompression zImage, du contenu ATAG/DTB ni de la physique : tester si son statut consistent_unverified pourrait être mal interprété.
8. La voie ARM_APPENDED_DTB / ARM_ATAG_DTB_COMPAT doit être documentée à partir du tag précis et du bootloader réel ; pas une solution garantie.
9. La taille RAM 512 Mio est connue, mais la base réellement utilisée et les trous de réservation ne le sont pas ; identifier les preuves à obtenir.

## Méthode pour Claude

- Vérifier HEAD réel, diff, PR draft et concurrence avant toute proposition.
- Reprendre les sources officielles Linux avec tag v6.18, les sources Netronix épinglées et les docs du dépôt, puis classer preuve directe / source / calcul / hypothèse.
- Inspecter le validateur pour fausses acceptations, rejet incorrect d'un contrat légitime, entiers et débordements, JSON hostile, dépendances I/O, robustesse Windows/Linux ; ajouter des tests **synthétiques**.
- Reproduire les tests disponibles uniquement si l'environnement le permet et rapporter leur exécution exacte ; ne jamais appeler SKIP un PASS.
- Vérifier que seuls les fichiers de ce lot changent, sans toucher FIRST BOOT, P1, P2, P3, images, U-Boot réel, hardware drivers, rcS, Notes et launcher.
- Si défaut prouvé, proposer les corrections minimales avec preuves et tests ; **ne pas merger**, pas de nouveau dépôt/branche/PR.
- Ne pas télécharger, installer, compiler avec nouvelle toolchain, écrire sur disque physique ou flasher sans approbation explicite.
- Fournir résultats PASS/FAIL/SKIP par suite et gate, liens de sources exacts, risques résiduels et un verdict sur la faisabilité réelle **non encore démontrée** du boot moderne.

## Limites déjà connues

Pas de uImage / U-Boot privés relus dans ce lot ; pas de mesure physique ; aucune compilation du noyau 6.18 ; pas de DTB E606C0 prouvé ; aucun pilote moderne essayé sur Aura HD. Le contrôle de métadonnées n'est pas un certificat de boot.

## Autoprompt à coller à Claude Code

**Mission :** effectuer une contre-expertise strictement indépendante de PMKB BOOT CONTRACT V1 sur fr4nck/PimpMyKobo-AuraHD, branche feat/pmkb-powerlab-kernel-v0, PR #28 draft. Ne supposer ni PC 5700X, ni sauvegardes privées, ni périphérique Kobo à disposition. Vérifier HEAD et provenance avant tout. Relire docs/boot-contract-v1-fr.md, docs/kernel-driver-matrix-v1-fr.md, docs/imx50-boot-chain-audit-fr.md, docs/offline-hardware-qualification-fr.md, docs/offline-boot-gates-fr.md, puis experimental/power-lab/boot_contract.py et tests/test_boot_contract.py. Contrôler les sources épinglées du noyau Linux v6.18 et les références Kobo/Netronix. Attaquer prioritairement machine ID vs bPCB 11, adresses uImage/DRAM/ATAG, compat DTB avec U-Boot 2009.08, EPDC, ZForce v2, MSP430/ntxec et toute surévaluation de compatibilité. Si l'environnement le permet, rejouer tests existants sans téléchargement ; ajouter tests négatifs et prouver les erreurs détectées. Ne toucher à aucun boot réel, partition, image scellée, U-Boot ou code exécuté sur appareil. Ne pas créer branche/PR ni merger. Ne proposer de patch que pour défaut vérifié, en respectant les modifications concurrentes. Livrer un bilan PASS/FAIL/SKIP, références précises, risques/inconnues et suggestions de corrections. Ne pas déclarer de compatibilité matérielle sur seule présence d'un pilote.
