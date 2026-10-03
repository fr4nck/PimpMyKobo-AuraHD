# PimpMyKobo-AuraHD documentation

[Français](README.md) | **English**

The documentation is organized around two goals: **rescue** an Aura HD using data already present on the device, then progressively **liberate** it from the Kobo userspace.

## Start here

For an Aura HD that no longer boots or whose factory reset failed:

1. [Protect the microSD on Windows before inspection](windows-preservation-en.md)
2. [Recover files from your own Aura HD](recover-files-en.md)
3. [Inspect the microSD read-only](inspect-aura-hd-en.md)
4. [Verify `recoveryfs`](verify-recovery-en.md)
5. [Understand the observed rescue procedure](rescue-en.md)

## Hardware reference

- [Aura HD / Dragon / E606C0 hardware](hardware-en.md)
- [Netronix HWCONFIG v1.7](hwconfig-en.md)
- [Observed partition layout](partition-layout-en.md)

## Tools

Scripts live in [`../tools/`](../tools/).

[Install the pmkb command on Debian/Ubuntu and WSL](cli-install-en.md).

- `inspect-aura-hd.py`: identify and map a complete Aura HD microSD or disk image;
- `verify-recovery.py`: validate the recovery tree, factory archives and E606C0 files.

These two tools never write to the microSD source. See the [tool catalogue](../tools/README.md) for local reconstruction and simulation. The [first P1 restore on native Linux Live](restore-p1-linux-en.md) uses a separate executor and requires explicit write authorization.

## Data intentionally not published

The repository intentionally excludes complete microSD dumps, `fs.tgz`, `db.tgz`, P1/P2 images, prebuilt U-Boot images, prebuilt kernels and future waveform extractions originating from a reader.

The documentation instead explains how owners can locate those components on their own device and keep them in a private backup.

## Current knowledge status

The E606C0, HWCONFIG and recovery information documented here was established from a real Aura HD together with the corresponding Netronix/Kobo sources.

The exact E-Ink waveform location and a reproducible extraction procedure remain to be established before a dedicated tool is published.
