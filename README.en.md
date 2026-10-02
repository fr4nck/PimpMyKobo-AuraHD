# PimpMyKobo-AuraHD

[Français](README.md) | **English**

Rescue, liberation and modernization of the Kobo Aura HD.

## Goal

Build a lightweight, free and independent reading system for the Kobo Aura HD while documenting a reproducible rescue path for devices left unusable after a failed factory reset or software corruption.

The project has two complementary goals:

1. **Rescue an Aura HD** from its own microSD card without redistributing proprietary Kobo system images.
2. **Liberate the Aura HD** by keeping only the hardware-specific layers that are required, then progressively replacing the Kobo userspace with a minimal stack centered on KOReader and free software components.

## Target hardware

- Kobo Aura HD / N204
- Codename: `dragon`
- Netronix PCBA: `E606C0`
- Freescale i.MX507 / i.MX50 family
- ARM Cortex-A8
- 512 MiB RAM
- RAM type: `K4X2G323PC`
- 6.8-inch E-Ink display
- 1440 × 1080 resolution
- Internal system storage on microSD

## Confirmed findings

The device studied here contains a `HW CONFIG v1.7` block at offset `0x80000` (`524288`).

Confirmed values:

| Field | Value |
|---|---|
| PCB | `28` → `E606C0` |
| Codename | `dragon` |
| Model | Kobo Aura HD |
| RAM | 512 MiB |
| CPU | i.MX50 |
| CPUFreq | 1 GHz |
| DisplayResolution | 1440 × 1080 |
| FrontLight | `TABLE3+` |
| HallSensor | `TLE4913` |
| DisplayBusWidth | `16Bits_mirror` |
| FrontLight LED driver | `SY7201` |

HWCONFIG v1.7 contains 39 configuration bytes. The field added after `PCB_Flags` is `FrontLight_LED_Driver`.

## Kobo sources found

Aura HD specific Kobo sources are available under:

    Kobo-Reader/hw/imx507-aurahd/

They include:

    linux-2.6.35.3.tar.gz
    u-boot-2009.08.tar.gz

U-Boot includes the Netronix adaptations, including `NTX_HWCONFIG`, RAM parameters, E-Ink handling and low-level hardware data loading.

## Boot architecture

    i.MX507 Boot ROM
            |
            v
    U-Boot 2009.08 / Netronix
            |
            +-- HWCONFIG
            +-- hardware parameters
            +-- E-Ink waveform
            |
            v
    Linux 2.6.35.3 / Kobo-Netronix
            |
            v
         rootfs
            |
            v
        userspace

The long-term target is to preserve only the hardware initialization layers that are actually required while replacing the Kobo userspace.

## Original microSD card

Observed physical size:

    31,914,983,424 bytes

Partition table: MBR.

| Area | Offset | Size | Role |
|---|---:|---:|---|
| Raw boot area | 0 | 9,961,472 bytes | U-Boot / kernel / HWCONFIG / E-Ink data |
| Partition 1 | 9,961,472 | 268,435,968 bytes | ext4 `rootfs` |
| Partition 2 | 278,397,440 | 268,435,968 bytes | ext4 `recoveryfs` |
| Partition 3 | 546,833,408 | rest of the card | FAT32 `KOBOeReader` |

Partition 1 therefore starts at 9.5 MiB, or 19,456 sectors of 512 bytes.

## Boot area backup

The first 9,961,472 bytes were copied read-only.

SHA-256:

    4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6

This binary backup is intentionally not published in the repository.

## Rescuing an Aura HD after an interrupted factory reset

On the device studied here, a factory reset had started and then failed.

Observed result:

- P1 `rootfs`: valid ext4 filesystem, but almost empty;
- P2 `recoveryfs`: intact and consistent;
- P3 `KOBOeReader`: recreated by the recovery procedure.

The Kobo recovery script present in `recoveryfs`:

1. selects the U-Boot and kernel images matching the hardware;
2. reformats P1 as ext4 `rootfs`;
3. reformats P3 as FAT32 `KOBOeReader`;
4. extracts `upgrade/fs.tgz` into P1;
5. extracts `upgrade/db.tgz` into P3.

The recovery partition on the studied unit contains, among other files:

- `upgrade/fs.tgz`
- `upgrade/db.tgz`
- `upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin`
- `upgrade/ntx508/uImage-E606C0`

Both `fs.tgz` and `db.tgz` passed `gzip -t`. The recovery filesystem was also checked against its `fs.md5sum` manifest.

A fresh 256 MiB ext4 `rootfs` image was built locally, populated with `fs.tgz`, verified against `fs.md5sum`, then checked with `e2fsck`.

After writing only P1, the SHA-256 read back directly from the microSD matched the source image exactly:

    ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C

This demonstrates that an Aura HD whose `rootfs` was wiped may sometimes be rebuilt from its own recovery partition without downloading a third-party system image.

## Publication philosophy

This repository should not redistribute:

- complete microSD images;
- personal dumps;
- `fs.tgz` or `db.tgz` extracted from a reader;
- prebuilt Kobo blobs when redistribution rights are unclear.

It should instead provide:

- documentation;
- inspection scripts;
- backup scripts;
- validation tools;
- local reconstruction from data already present on the user's own device;
- strong safeguards before any write operation.

## Planned repository layout

    docs/
    tools/
    scripts/
    configs/
    patches/
    liberated/

French documentation is the primary reference. English translations use the `.en.md` suffix.

## Safety rules

- read-only by default;
- never hard-code a physical disk number in public tools;
- validate sizes and offsets before writing;
- identify HWCONFIG and PCBA first;
- require a backup before modification;
- cryptographically verify writes;
- preserve `recoveryfs` and HWCONFIG whenever possible.

## Project status

- [x] Official Aura HD sources found
- [x] Original microSD recovered and mapped
- [x] Boot area backed up
- [x] HWCONFIG v1.7 decoded
- [x] PCBA identified: E606C0 / Dragon
- [x] Factory recovery analyzed
- [x] Real-world empty-`rootfs` failure diagnosed
- [x] `rootfs` rebuilt from `recoveryfs/upgrade/fs.tgz`
- [x] Reconstruction verified with MD5, e2fsck and SHA-256
- [ ] Extract and document the E-Ink waveform precisely
- [ ] Write a read-only `inspect-aura-hd` tool
- [ ] Write backup and local reconstruction tools
- [ ] Build the reference U-Boot and kernel
- [ ] Build a modern minimal userspace
- [ ] Integrate KOReader
- [ ] Test a fully liberated microSD image

## Documentation

- [Aura HD rescue](docs/rescue-en.md)
- [Aura HD hardware](docs/hardware-en.md)
- [Netronix HWCONFIG](docs/hwconfig-en.md)
- [Partition layout](docs/partition-layout-en.md)

## License

See [LICENSE](LICENSE).
