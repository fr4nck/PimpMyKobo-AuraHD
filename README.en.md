# PimpMyKobo-AuraHD

[Français](README.md) | **English**

Resurrection and modernization of the Kobo Aura HD.

## Target hardware

- Kobo Aura HD / N204
- Freescale i.MX507 SoC
- 512 MiB RAM
- Netronix hardware platform
- 6.8-inch E-Ink display
- 1440 × 1080 resolution

## Goal

Build a lightweight, free and independent reading system for the Kobo Aura HD without relying on Kobo services.

The project aims to provide:

- a Linux boot environment adapted to the Aura HD hardware;
- a minimal userspace;
- KOReader as the reading interface;
- support for the E-Ink display, touchscreen and frontlight;
- the ability to rebuild a complete system microSD card;
- reproducible documentation of the entire process.

## Hardware sources

Official Kobo sources specifically targeting the Aura HD were found under:

`Kobo-Reader/hw/imx507-aurahd`

They include:

- U-Boot 2009.08 modified for the Netronix platform;
- Linux 2.6.35.3 modified for the i.MX507 and Kobo/Netronix hardware.

These upstream sources are not included directly in this repository.

## Original microSD card

The reader's original system microSD card has been recovered and must remain unmodified.

Observed partition layout:

- partition 1: offset 9,961,472 bytes, size 256 MiB;
- partition 2: offset 278,397,440 bytes, size 256 MiB;
- partition 3: offset 546,833,408 bytes, `KOBOeReader` user partition.

The area preceding the first partition has been backed up separately.

### Boot-area backup

- size: 9,961,472 bytes;
- SHA-256: `4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6`

The binary backup is intentionally not published in this repository.

It contains low-level data required to investigate the reader's boot process and hardware configuration.

## Project status

Work in progress.

Next steps:

1. analyse the original HWCONFIG;
2. identify the exact Netronix PCBA;
3. extract and preserve the E-Ink waveform;
4. document the boot-area layout;
5. build and test U-Boot and the kernel;
6. prepare a replacement microSD card;
7. build a minimal Linux environment;
8. integrate KOReader.

## Precaution

The original microSD card is the reference copy and must not be modified.

All experiments should be performed on a replacement card.
