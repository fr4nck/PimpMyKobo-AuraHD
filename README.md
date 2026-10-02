# PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Résurrection et modernisation de la Kobo Aura HD.

## Matériel cible

- Kobo Aura HD / N204
- SoC Freescale i.MX507
- 512 Mio de RAM
- Plateforme matérielle Netronix
- Écran E-Ink 6,8 pouces
- Résolution 1440 × 1080

## Objectif

Construire un système de lecture léger, libre et indépendant pour la Kobo Aura HD, sans dépendance aux services Kobo.

L'objectif envisagé est notamment :

- démarrage Linux adapté au matériel de l'Aura HD ;
- système utilisateur minimal ;
- KOReader comme interface de lecture ;
- conservation du support de l'écran E-Ink, du tactile et de l'éclairage ;
- possibilité de reconstruire une carte microSD système ;
- documentation reproductible de l'ensemble de la procédure.

## Sources matérielles

Les sources officielles Kobo spécifiques à l'Aura HD ont été retrouvées dans :

`Kobo-Reader/hw/imx507-aurahd`

Elles contiennent notamment :

- U-Boot 2009.08 modifié pour la plateforme Netronix ;
- Linux 2.6.35.3 modifié pour l'i.MX507 et le matériel Kobo/Netronix.

Ces sources amont ne sont pas incluses directement dans ce dépôt.

## Carte microSD originale

La microSD système originale de la liseuse a été retrouvée et doit rester intacte.

Géométrie observée :

- partition 1 : offset 9 961 472 octets, taille 256 Mio ;
- partition 2 : offset 278 397 440 octets, taille 256 Mio ;
- partition 3 : offset 546 833 408 octets, partition utilisateur `KOBOeReader`.

La zone précédant la première partition a été sauvegardée séparément.

### Sauvegarde de la zone de démarrage

- taille : 9 961 472 octets ;
- SHA-256 : `4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6`

Cette sauvegarde binaire n'est volontairement pas publiée dans le dépôt.

Elle contient notamment les données de bas niveau nécessaires à l'étude du démarrage et de la configuration matérielle de la liseuse.

## État du projet

Travail en cours.

Prochaines étapes :

1. analyser le HWCONFIG original ;
2. identifier précisément le PCBA Netronix ;
3. extraire et préserver la waveform E-Ink ;
4. documenter la disposition de la zone de démarrage ;
5. construire et tester U-Boot et le kernel ;
6. préparer une microSD de remplacement ;
7. construire un environnement Linux minimal ;
8. intégrer KOReader.

## Précaution

La microSD originale sert de référence et ne doit pas être modifiée.

Les expérimentations doivent être réalisées sur une carte de remplacement.
