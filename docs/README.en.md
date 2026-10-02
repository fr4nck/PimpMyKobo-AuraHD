# PimpMyKobo-AuraHD documentation

[Français](README.md) | **English**

The documentation is organized around two goals: **rescue** an Aura HD using data already present on the device, then progressively **liberate** it from the Kobo userspace.

## Start here

For an Aura HD that no longer boots or whose factory reset failed:

1. [Protect the microSD on Windows before inspection](windows-preservation-en.md)
2. [Recover files from your own Aura HD](recover-files-en.md)
3. [Inspect the microSD read-only](inspect-aura-hd-en.md)
4. [Verify `recoveryfs`](verify-recovery-en.md)
5. [Back up the microSD (pre-P1, P1, P2, optional P3)](backup-aura-hd-en.md)
6. [Verify an existing backup, offline](verify-backup-aura-hd-en.md)
7. [Understand the observed rescue procedure](rescue-en.md)

## Hardware reference

- [Aura HD / Dragon / E606C0 hardware](hardware-en.md)
- [Netronix HWCONFIG v1.7](hwconfig-en.md)
- [Observed partition layout](partition-layout-en.md)

## Tools

Scripts live in [`../tools/`](../tools/).

- `inspect-aura-hd.py`: identify and map a complete Aura HD microSD or disk image;
- `verify-recovery.py`: validate the recovery tree, factory archives and E606C0 files;
- `backup-aura-hd.py`: SHA-256-verified backup of a confirmed E606C0 Aura HD into an explicitly given directory;
- `verify-backup-aura-hd.py`: offline, read-only verification of an existing backup against its manifest.

These tools never open the source microSD for writing. `backup-aura-hd.py` only writes into the backup directory.

## Data intentionally not published

The repository intentionally excludes complete microSD dumps, `fs.tgz`, `db.tgz`, P1/P2 images, prebuilt U-Boot images, prebuilt kernels and future waveform extractions originating from a reader.

The documentation instead explains how owners can locate those components on their own device and keep them in a private backup.

## Current knowledge status

The E606C0, HWCONFIG and recovery information documented here was established from a real Aura HD together with the corresponding Netronix/Kobo sources.

The exact E-Ink waveform location and a reproducible extraction procedure remain to be established before a dedicated tool is published.