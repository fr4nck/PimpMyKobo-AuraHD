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

## Values observed on the studied unit

The studied device contains a `HW CONFIG v1.7` block at offset `0x80000` (`524288`).

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

The observed v1.7 payload contains 39 configuration bytes. The field added after `PCB_Flags` is `FrontLight_LED_Driver`.

## Kobo sources found

Aura HD-specific Kobo sources are available under:

    Kobo-Reader/hw/imx507-aurahd/

They include:

    linux-2.6.35.3.tar.gz
    u-boot-2009.08.tar.gz

U-Boot includes Netronix adaptations such as `NTX_HWCONFIG`, RAM parameters, E-Ink handling and low-level hardware data loading.

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

On the studied device, a factory reset had started and then failed.

Observed result:

- P1 `rootfs`: valid ext4 filesystem, but almost empty;
- P2 `recoveryfs`: intact and consistent;
- P3 `KOBOeReader`: recreated by the recovery procedure.

The Kobo recovery script in `recoveryfs` reads HWCONFIG, chooses hardware-specific artifacts when available, reformats P1/P3, then extracts `upgrade/fs.tgz` into P1 and `upgrade/db.tgz` into P3.

The studied recovery partition contains, among other files:

- `upgrade/fs.tgz`
- `upgrade/db.tgz`
- `upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin`
- `upgrade/ntx508/uImage-E606C0`

Both factory archives passed `gzip -t`, and the recovery tree was verified against `fs.md5sum`.

A fresh 256 MiB ext4 `rootfs` image was built locally, populated with `fs.tgz`, checked against `fs.md5sum`, then checked with `e2fsck`.

After writing only P1, the SHA-256 read back directly from the microSD matched the source image exactly:

    ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C

This demonstrates that an Aura HD whose `rootfs` was wiped may sometimes be rebuilt from its own recovery partition without downloading a third-party system image.

## Current tools

### `inspect-aura-hd.py`

A standalone Python inspector with no external dependencies and strictly read-only behavior. It discovers current disks, reads MBR/HWCONFIG, confirms `E606C0 / Dragon` only with the expected HWCONFIG format, and detects `rootfs`, `recoveryfs` and `KOBOeReader` labels without mounting partitions.

On Windows:

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

See [the inspector documentation](docs/inspect-aura-hd-en.md).

### `verify-recovery.py`

A read-only verifier for an already mounted or locally copied `recoveryfs`. It checks `fs.md5sum`, the complete gzip stream, tar end markers, archive members/payloads, E606C0 artifacts, and can compute SHA-256 hashes.

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files --lang en
```

See [the `verify-recovery` documentation](docs/verify-recovery-en.md).

Synthetic tests containing no Kobo firmware are present in `tests/`. CI runs them on Linux and Windows with Python 3.10 through 3.13.

## Publication philosophy

This repository should not redistribute:

- complete microSD images;
- personal dumps;
- `fs.tgz` or `db.tgz` extracted from a reader;
- prebuilt Kobo blobs when redistribution rights are unclear.

Instead, it should provide documentation, inspection, validation, backup and local reconstruction based on data already present on the user's own device.

## Safety rules

- read-only by default;
- never hard-code a physical disk number in public tools;
- validate sizes and offsets before writing;
- identify HWCONFIG and PCBA first;
- require a backup before modification;
- cryptographically verify writes;
- preserve `recoveryfs` and HWCONFIG whenever possible.

### Operating-system writes still matter

A read-only tool does not make the host operating system unable to write to the card.

- On Windows, always **cancel** format prompts for the ext4 partitions and avoid unnecessarily opening FAT32 P3 while making preservation copies.
- On desktop Linux, disable automount: a read-write ext4 mount may replay the journal. For sensitive work, prefer a local image or mark the positively identified block device read-only in the kernel before analysis.

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
- [x] Read-only `inspect-aura-hd` tool
- [x] Read-only `verify-recovery` tool
- [x] Synthetic tests without Kobo blobs
- [x] Linux/Windows CI on Python 3.10–3.13
- [ ] Validate `inspect-aura-hd` against the physical microSD through the Windows card reader
- [ ] Extract and document the E-Ink waveform precisely
- [ ] Write backup and local reconstruction tools
- [ ] Build the reference U-Boot and kernel
- [ ] Build a modern minimal userspace
- [ ] Integrate KOReader
- [ ] Test a fully liberated microSD image

## Documentation

- [Disassemble the Aura HD and access the internal microSD](docs/disassembly-en.md) — with original photos, iFixit/MobileRead sources and a Lynx-friendly text edition.
- [Text / Lynx disassembly guide](docs/disassembly-lynx-en.txt)
- [Documentation index](docs/README.en.md)
- [Aura HD rescue](docs/rescue-en.md)
- [Recover the recovery files](docs/recover-files-en.md)
- [Aura HD inspector](docs/inspect-aura-hd-en.md)
- [Verify recoveryfs](docs/verify-recovery-en.md)
- [Aura HD hardware](docs/hardware-en.md)
- [Netronix HWCONFIG](docs/hwconfig-en.md)
- [Partition layout](docs/partition-layout-en.md)

## License

The license for original project code has not been selected yet. Third-party components and sources retain their respective licenses.
