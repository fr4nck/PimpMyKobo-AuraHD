# Rescuing a Kobo Aura HD

[Français](rescue-fr.md) | **English**

This document describes a diagnostic and reconstruction method for a Kobo Aura HD whose factory reset was interrupted.

## Studied hardware

- Kobo Aura HD / N204
- codename: `dragon`
- PCBA: `E606C0`
- platform: Netronix / Freescale i.MX50
- RAM: 512 MiB
- RAM type: `K4X2G323PC`
- HW CONFIG: v1.7

## Observed symptom

After an interrupted factory reset:

- P1 `rootfs` was a valid ext4 filesystem but almost empty;
- P2 `recoveryfs` remained intact;
- the recovery partition still contained the archives and hardware-specific files required to reconstruct the system.

`e2fsck -f -n` reported no structural error on P1 because the empty filesystem itself was consistent.

## What Kobo recovery does

The `recoveryfs:/etc/init.d/rcS` script:

1. reads HWCONFIG;
2. selects hardware-matching U-Boot and kernel images when available;
3. reformats P1 as ext4 with the `rootfs` label;
4. reformats P3 as FAT32 with the `KOBOeReader` label;
5. mounts P1;
6. extracts `/upgrade/fs.tgz` into P1;
7. mounts P3;
8. extracts `/upgrade/db.tgz` into P3.

A failure after formatting but before a successful `fs.tgz` extraction can therefore leave exactly the empty P1 observed here.

## Recovery files observed

The E606C0 recovery partition contained, among other files:

    upgrade/fs.tgz
    upgrade/db.tgz
    upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
    upgrade/ntx508/uImage-E606C0

## Integrity checks performed

### Recovery filesystem

`recoveryfs` completed all five `e2fsck -f -n` passes without structural inconsistencies.

Its `fs.md5sum` manifest was fully verified as root.

### Factory archives

    gzip -t upgrade/fs.tgz
    gzip -t upgrade/db.tgz

Both archives passed.

`fs.tgz` contained 2,529 entries and approximately 160.8 MB uncompressed.

## Offline reconstruction of P1

A fresh 256 MiB image was created on the PC and formatted as ext4 with the `rootfs` label.

`fs.tgz` was extracted into it.

The resulting rootfs included, among other paths:

    bin/
    dev/
    drivers/
    etc/
    lib/
    libexec/
    root/
    sbin/
    usr/
    linuxrc
    fs.md5sum

The reconstructed rootfs passed its own `fs.md5sum` manifest with no differences.

`e2fsck -f -n` also completed cleanly:

    rootfs: 2260/65536 files, 183174/262144 blocks

## Targeted P1 write

The rebuilt image was written only into the P1 region.

The bytes were then read back directly from the physical microSD and hashed. The read-back SHA-256 matched the source image exactly:

    ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C

This hash documents this specific reconstructed image. It is not intended as a universal Aura HD image hash.

## What should not be published

The project does not publish:

- the rebuilt P1 image;
- full microSD dumps;
- `fs.tgz` or `db.tgz` extracted from a reader;
- device blobs when redistribution rights are unclear.

The goal is to provide tooling that lets each owner use the data already present on their own Aura HD.

## Safety rules

- back up before any write operation;
- preserve `recoveryfs`;
- preserve HWCONFIG;
- identify the hardware before writing;
- read and validate the actual partition table;
- reconstruct and validate images offline;
- read back written bytes and compare cryptographic hashes;
- never hard-code a physical disk number in distributed tooling.
