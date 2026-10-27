# Documentation PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Cette documentation est organisée autour de deux objectifs : **sauver** une Aura HD à partir de ses propres données, puis **la libérer** progressivement de l'environnement utilisateur Kobo.

## Commencer ici

Pour une Aura HD qui ne démarre plus ou dont le reset usine a échoué :

1. [Démonter l'Aura HD et accéder à la microSD interne](disassembly-fr.md) — avec schémas ASCII et sources ;
2. [Retrouver les fichiers sur sa propre Aura HD](retrouver-fichiers-fr.md) ;
3. [Inspecter la microSD en lecture seule](inspect-aura-hd-fr.md) ;
4. [Vérifier `recoveryfs`](verify-recovery-fr.md) ;
5. [Comprendre la procédure de sauvetage observée](rescue-fr.md).

Pour un navigateur texte, une console ou une session SSH : [version texte / Lynx du démontage](disassembly-lynx-fr.txt).

## Référence matérielle

- [Matériel Aura HD / Dragon / E606C0](hardware-fr.md)
- [HWCONFIG Netronix v1.7](hwconfig-fr.md)
- [Partitionnement observé](partition-layout-fr.md)

## Outils

Les scripts sont dans [`../tools/`](../tools/).

[Installer la commande pmkb sur Debian/Ubuntu et WSL](cli-install-fr.md).

[Roadmap et état de qualification](ROADMAP.fr.md).

[Registre permanent de recherche et des sources externes Kobo/PMKB](recherche-sources-fr.md) — projets vérifiés, informations, inspirations, candidats à intégrer, licences et priorités R0–R10.

- `inspect-aura-hd.py` : identification et cartographie d'une microSD complète ;
- `verify-recovery.py` : validation du recovery, des archives usine et des fichiers E606C0 ;
- [`backup-aura-hd.py`](backup-aura-hd-fr.md) : sauvegarde vérifiée par SHA-256 d'une Aura HD E606C0 confirmée, vers un dossier explicitement fourni ;
- [`verify-backup-aura-hd.py`](verify-backup-aura-hd-fr.md) : vérification hors ligne, en lecture seule, d'une sauvegarde existante par rapport à son manifeste.

Ces outils n'écrivent jamais sur la microSD. La reconstruction et la simulation locale sont décrites dans le [catalogue des outils](../tools/README.md). La [première restauration P1 sous Linux Live](restore-p1-linux-fr.md) utilise un exécuteur séparé et nécessite une autorisation d'écriture explicite.

Avant toute inspection sous Windows : [protéger la microSD](windows-preservation-fr.md).

## Launcher e-ink expérimental

- [Prototype Lua et README du launcher (V0.4/V0.5)](../experimental/launcher-v0/README.md) : navigation simulée sur PC ; aucun backend framebuffer/tactile qualifié.
- [**Lancer le simulateur illustré sur PC**](../experimental/launcher-v0/simulator.html) : huit panneaux cliquables, états clair/sombre et dock applicatif distinct de la barre système (V0.5 en prototype). Les actions sont inertes.
- [Graphismes V0.2 validés dans Git](../experimental/launcher-v0/assets/v02/) : original RGB, 16 gris, 4 gris, 1 bit, comparatif et manifeste.
- [Qualification des graphismes V0.2](launcher-v02-asset-qualification-2026-10-13-fr.md) : poids, SHA-256, limites matérielles.

## Notes PDA (prototype indépendant)

- [Notes V0.1 : guide français](../experimental/notes-v01/README.md) · [English](../experimental/notes-v01/README.en.md).
- [Ouvrir le simulateur Notes](../experimental/notes-v01/index.html) : texte, recherche, croquis monochrome facultatif, fichiers JSON/TXT/PNG, hors ligne et sans Kobo.
- La sauvegarde automatique dépend du navigateur ; un export JSON manuel reste nécessaire. La [PR V0.6 du launcher](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/25) n'est pas fusionnée : le bouton Notes de l'accueil n'est pas encore relié à cette application.

## Données non publiées

Le dépôt ne contient volontairement pas les dumps de microSD, `fs.tgz`, `db.tgz`, images P1/P2, U-Boot précompilés, kernels précompilés ni futures extractions de waveform provenant d'une liseuse.

La documentation explique comment retrouver ces éléments sur son propre appareil et les conserver dans une sauvegarde privée.

## État des connaissances

Les éléments E606C0/HWCONFIG/recovery documentés ici ont été établis à partir d'une Aura HD réelle et des sources Netronix/Kobo correspondantes.

La procédure d'ouverture et l'accès à la microSD interne sont désormais documentés à partir de notre propre démontage et recoupés avec iFixit et MobileRead.

La localisation exacte et la procédure d'extraction reproductible de la waveform E-Ink restent à documenter avant publication d'un outil dédié.
