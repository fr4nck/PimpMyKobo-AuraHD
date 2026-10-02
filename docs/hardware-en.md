# Kobo Aura HD — observed hardware

[Français](hardware-fr.md) | **English**

## Identification

| Item | Value |
|---|---|
| Model | Kobo Aura HD / N204 |
| Codename | `dragon` |
| PCB / PCBA | `E606C0` |
| HWCONFIG ID | 28 |
| Internal U-Boot/kernel ID | 11 |
| SoC | Freescale i.MX50 / i.MX507 |
| CPU | ARM Cortex-A8 |
| Frequency | 1 GHz |
| RAM | 512 MiB |
| RAM type | `K4X2G323PC` |
| Display | 6.8-inch E-Ink |
| Resolution | 1440 × 1080 |
| Display bus | `16Bits_mirror` |
| Frontlight | `TABLE3+` |
| LED driver | `SY7201` |
| Hall sensor | `TLE4913` |

## PCBA remapping

In HWCONFIG, `bPCB = 28` maps to `E606C0`.

The studied U-Boot and kernel branches then remap this value to internal ID `11`. The hardware HWCONFIG identifier must therefore be distinguished from the identifier used by some platform routines.

## Storage

The studied unit stores its system on an internal microSD card.

P1 contains `rootfs`, P2 contains `recoveryfs`, and P3 is the user-facing `KOBOeReader` partition.

## Note

These values come from the actually analyzed device and the matching Netronix/Kobo sources. They are a useful reference for detection tooling, but public tools should always validate the HWCONFIG of the connected device rather than infer hardware from a marketing name alone.
