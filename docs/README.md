# Documentation PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Cette documentation est organisée autour de deux objectifs : **sauver** une Aura HD à partir de ses propres données, puis **la libérer** progressivement de l'environnement utilisateur Kobo.

## Commencer ici

Pour une Aura HD qui ne démarre plus ou dont le reset usine a échoué :

1. [Protéger la microSD sous Windows avant inspection](windows-preservation-fr.md)
2. [Retrouver les fichiers sur sa propre Aura HD](retrouver-fichiers-fr.md)
3. [Inspecter la microSD en lecture seule](inspect-aura-hd-fr.md)
4. [Vérifier `recoveryfs`](verify-recovery-fr.md)
5. [Sauvegarder la microSD (pré-P1, P1, P2, P3 en option)](backup-aura-hd-fr.md)
6. [Vérifier une sauvegarde existante, hors ligne](verify-backup-aura-hd-fr.md)
7. [Comprendre la procédure de sauvetage observée](rescue-fr.md)

## Référence matérielle

- [Matériel Aura HD / Dragon / E606C0](hardware-fr.md)
- [HWCONFIG Netronix v1.7](hwconfig-fr.md)
- [Partitionnement observé](partition-layout-fr.md)

## Outils

Les scripts sont dans [`../tools/`](../tools/).

- `inspect-aura-hd.py` : identification et cartographie d'une microSD complète ;
- `verify-recovery.py` : validation du recovery, des archives usine et des fichiers E606C0 ;
- `backup-aura-hd.py` : sauvegarde vérifiée par SHA-256 d'une Aura HD E606C0 confirmée, vers un dossier explicitement fourni ;
- `verify-backup-aura-hd.py` : vérification hors ligne, en lecture seule, d'une sauvegarde existante par rapport à son manifeste.

Ces outils n'ouvrent jamais la microSD source en écriture. `backup-aura-hd.py` n'écrit que dans le dossier de sauvegarde.

## Données non publiées

Le dépôt ne contient volontairement pas les dumps de microSD, `fs.tgz`, `db.tgz`, images P1/P2, U-Boot précompilés, kernels précompilés ni futures extractions de waveform provenant d'une liseuse.

La documentation explique comment retrouver ces éléments sur son propre appareil et les conserver dans une sauvegarde privée.

## État des connaissances

Les éléments E606C0/HWCONFIG/recovery documentés ici ont été établis à partir d'une Aura HD réelle et des sources Netronix/Kobo correspondantes.

La localisation exacte et la procédure d'extraction reproductible de la waveform E-Ink restent à documenter avant publication d'un outil dédié.