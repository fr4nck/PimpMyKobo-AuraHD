# Documentation PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Cette documentation est organisée autour de deux objectifs : **sauver** une Aura HD à partir de ses propres données, puis **la libérer** progressivement de l'environnement utilisateur Kobo.

## Commencer ici

Pour une Aura HD qui ne démarre plus ou dont le reset usine a échoué :

1. [Protéger la microSD sous Windows avant inspection](windows-preservation-fr.md)
2. [Retrouver les fichiers sur sa propre Aura HD](retrouver-fichiers-fr.md)
3. [Inspecter la microSD en lecture seule](inspect-aura-hd-fr.md)
4. [Vérifier `recoveryfs`](verify-recovery-fr.md)
5. [Comprendre la procédure de sauvetage observée](rescue-fr.md)

## Référence matérielle

- [Matériel Aura HD / Dragon / E606C0](hardware-fr.md)
- [HWCONFIG Netronix v1.7](hwconfig-fr.md)
- [Partitionnement observé](partition-layout-fr.md)

## Outils

Les scripts sont dans [`../tools/`](../tools/).

[Installer la commande pmkb sur Debian/Ubuntu et WSL](cli-install-fr.md).

[Roadmap et état de qualification](ROADMAP.fr.md).

- `inspect-aura-hd.py` : identification et cartographie d'une microSD complète ;
- `verify-recovery.py` : validation du recovery, des archives usine et des fichiers E606C0.

Ces deux outils n'écrivent jamais sur la microSD. La reconstruction et la simulation locale sont décrites dans le [catalogue des outils](../tools/README.md). La [première restauration P1 sous Linux Live](restore-p1-linux-fr.md) utilise un exécuteur séparé et nécessite une autorisation d'écriture explicite.

## Données non publiées

Le dépôt ne contient volontairement pas les dumps de microSD, `fs.tgz`, `db.tgz`, images P1/P2, U-Boot précompilés, kernels précompilés ni futures extractions de waveform provenant d'une liseuse.

La documentation explique comment retrouver ces éléments sur son propre appareil et les conserver dans une sauvegarde privée.

## État des connaissances

Les éléments E606C0/HWCONFIG/recovery documentés ici ont été établis à partir d'une Aura HD réelle et des sources Netronix/Kobo correspondantes.

La localisation exacte et la procédure d'extraction reproductible de la waveform E-Ink restent à documenter avant publication d'un outil dédié.
