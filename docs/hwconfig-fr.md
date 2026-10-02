# HWCONFIG Netronix — Kobo Aura HD

**Français** | [English](hwconfig-en.md)

## Emplacement observé

Le bloc matériel se trouve à l'offset :

    524288 octets
    0x80000

Signature observée :

    HW CONFIG v1.7

## Structure

L'en-tête étudié est constitué de :

    char cMagicNameA[10];
    char cVersionNameA[5];
    unsigned char bHWConfigSize;

Dans l'exemplaire analysé :

- version : `v1.7`
- taille déclarée : 39 octets
- premier octet de payload : `bPCB = 0x1c = 28`

## Identification du PCB

La table Netronix associe :

    28 -> E606C0

Okreader associe également `E606C0` au nom de code `dragon` et au modèle Aura HD.

## Champs de fin confirmés

Les versions successives ajoutent notamment :

- v1.0 : `DisplayResolution`
- v1.1 : `FrontLight`
- v1.2 : `CPUFreq`
- v1.3 : `HallSensor`
- v1.4 : `DisplayBusWidth`
- v1.5 : `FrontLight_Flags`
- v1.6 : `PCB_Flags`
- v1.7 : `FrontLight_LED_Driver`

Valeurs observées :

| Champ | Brut | Interprétation |
|---|---:|---|
| DisplayResolution | 3 | 1440 × 1080 |
| FrontLight | 6 | `TABLE3+` |
| CPUFreq | 2 | 1 GHz |
| HallSensor | 1 | `TLE4913` |
| DisplayBusWidth | 3 | `16Bits_mirror` |
| FrontLight_Flags | 0 | aucun flag |
| PCB_Flags | 1 | `NO_KeyMatrix` |
| FrontLight_LED_Driver | 0 | `SY7201` |

## Prudence

Le format HWCONFIG évolue avec les générations Netronix/Kobo. Un décodeur doit toujours prendre en compte la version et la taille annoncées dans l'en-tête.

Le projet considère le HWCONFIG original comme une donnée matérielle critique à sauvegarder et à préserver.
