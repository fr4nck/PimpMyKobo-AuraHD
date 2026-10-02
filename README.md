# PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Résurrection, libération et modernisation de la Kobo Aura HD.

## Objectif

Construire un système de lecture léger et indépendant pour la Kobo Aura HD, sans dépendance aux services Kobo, en conservant le support complet du matériel d'origine et en utilisant KOReader comme environnement de lecture.

## Matériel cible

- Kobo Aura HD / N204
- Freescale i.MX507 / famille i.MX50
- ARM Cortex-A8
- 512 Mio de RAM
- écran E-Ink 6,8 pouces
- résolution 1440 × 1080
- plateforme matérielle Netronix
- stockage système sur microSD interne

## Sources Kobo retrouvées

Kobo publie les sources spécifiques à l'Aura HD dans :

    Kobo-Reader/hw/imx507-aurahd/

Elles contiennent notamment :

    linux-2.6.35.3.tar.gz
    u-boot-2009.08.tar.gz

U-Boot contient les adaptations Netronix, notamment `NTX_HWCONFIG`, les paramètres RAM, la gestion de l'écran E-Ink et le chargement des données matérielles.

## Architecture de démarrage

    Boot ROM i.MX507
            |
            v
    U-Boot 2009.08 / Netronix
            |
            +-- HWCONFIG
            +-- paramètres matériels
            +-- waveform E-Ink
            |
            v
    Linux 2.6.35.3 / Kobo-Netronix
            |
            v
         rootfs
            |
            v
         KOReader

L'objectif est de conserver les couches nécessaires au matériel tout en remplaçant le système utilisateur Kobo.

## MicroSD originale

La microSD système originale a été retrouvée et est désormais conservée comme référence en lecture seule.

Taille physique observée :

    31 914 983 424 octets

Table de partitions : MBR.

Disposition relevée :

| Zone | Offset | Taille |
|---|---:|---:|
| Zone brute de démarrage | 0 | 9 961 472 octets |
| Partition 1 | 9 961 472 | 268 435 968 octets |
| Partition 2 | 278 397 440 | 268 435 968 octets |
| Partition 3 / KOBOeReader | 546 833 408 | 31 368 150 016 octets |

La première partition commence donc à 9,5 Mio, soit 19 456 secteurs de 512 octets.

## Sauvegarde de la zone de démarrage

Les 9 961 472 premiers octets de la carte originale ont été copiés en lecture seule.

SHA-256 :

    4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6

Le dump binaire n'est volontairement pas publié dans ce dépôt.

## HWCONFIG Netronix

U-Boot et le kernel utilisent une structure `NTX_HWCONFIG` décrivant le matériel réel de la liseuse.

Les sources permettent notamment d'identifier :

- le PCBA ;
- la quantité et le type de RAM ;
- le processeur ;
- le contrôleur tactile ;
- le type de tactile ;
- le contrôleur d'affichage ;
- le panneau E-Ink ;
- la résolution ;
- le frontlight ;
- la fréquence CPU ;
- la largeur du bus d'affichage ;
- différents indicateurs matériels.

La table Netronix contient notamment :

    bPCB 15 = E60620
    bPCB 16 = E60630
    bPCB 17 = E60640
    bPCB 18 = E50600
    bPCB 19 = E60680

Le PCBA exact de cette Aura HD sera déterminé à partir du HWCONFIG extrait de sa propre microSD, et non supposé à partir du modèle commercial.

## Waveform E-Ink

La waveform fait partie des données matérielles chargées au démarrage par la plateforme Netronix.

Elle sera extraite et conservée depuis la carte originale avant toute expérimentation.

## Environnement de développement

    Windows
      └── WSL2
          └── Debian
              ├── arm-linux-gnueabihf-gcc
              ├── sources Kobo
              ├── okreader (référence)
              └── PimpMyKobo-AuraHD

Cross-compilateur actuellement installé :

    arm-linux-gnueabihf-gcc 14.2.0

Les sources Kobo datant de 2009–2013, une toolchain ARM historique pourra être utilisée si le GCC moderne s'avère incompatible.

## Organisation du travail

Les gros arbres amont et les dumps sont exclus de Git :

    aurahd-src/
    kobolabs/
    okreader/
    *.bin
    *.img
    *.raw

Le dépôt accueillera les éléments permettant de reproduire le projet :

    docs/
    scripts/
    configs/
    patches/

## Règle de sécurité

    SD originale
         |
         +--> lecture uniquement
                 |
                 v
            sauvegardes
                 |
                 v
             analyses
                 |
                 v
          reconstruction
                 |
                 v
       SD de remplacement
                 |
                 v
               tests

Aucune expérimentation nécessitant une écriture ne doit être réalisée sur la microSD originale.

## État du projet

- [x] Sources officielles Aura HD retrouvées
- [x] Sources U-Boot et kernel extraites
- [x] MicroSD originale retrouvée
- [x] Géométrie originale relevée
- [x] Zone pré-partition sauvegardée et vérifiée par SHA-256
- [ ] Décoder le HWCONFIG original
- [ ] Identifier le PCBA exact
- [ ] Extraire la waveform E-Ink
- [ ] Cartographier précisément la zone de boot
- [ ] Compiler U-Boot
- [ ] Compiler le kernel
- [ ] Construire le rootfs minimal
- [ ] Intégrer KOReader
- [ ] Générer la microSD de remplacement
- [ ] Premier boot

## Licence

Voir [LICENSE](LICENSE).
