# Kobo Aura HD — matériel observé

**Français** | [English](hardware-en.md)

## Identification

| Élément | Valeur |
|---|---|
| Modèle | Kobo Aura HD / N204 |
| Nom de code | `dragon` |
| PCB / PCBA | `E606C0` |
| ID HWCONFIG | 28 |
| ID interne U-Boot/kernel | 11 |
| SoC | Freescale i.MX50 / i.MX507 |
| CPU | ARM Cortex-A8 |
| Fréquence | 1 GHz |
| RAM | 512 Mio |
| Type RAM | `K4X2G323PC` |
| Écran | E-Ink 6,8 pouces |
| Résolution | 1440 × 1080 |
| Bus d'affichage | `16Bits_mirror` |
| Frontlight | `TABLE3+` |
| Driver LED | `SY7201` |
| Capteur Hall | `TLE4913` |

## Remappage PCBA

Dans le HWCONFIG, `bPCB = 28` correspond à `E606C0`.

Les branches U-Boot et kernel étudiées remappent ensuite cette valeur vers un identifiant interne `11`. Il faut donc distinguer l'identifiant matériel HWCONFIG de l'identifiant utilisé par certaines routines de la plateforme.

## Stockage

La machine étudiée stocke son système sur une microSD interne.

P1 contient `rootfs`, P2 contient `recoveryfs`, P3 est la partition utilisateur `KOBOeReader`.

## Remarque

Ces valeurs proviennent de l'exemplaire réellement analysé et de ses sources Netronix/Kobo associées. Elles servent de référence pour le développement d'outils de détection, mais un outil public doit toujours vérifier le HWCONFIG de la machine présente plutôt que supposer le modèle à partir d'un nom commercial.
