# PimpMyKobo-AuraHD

![Retro PMKB logo — Pimp My Kobo](assets/branding/pmkb-logo-original.png)

[Français](README.md) | **English**

Rescue, liberation and modernization of the Kobo Aura HD.

The `pmkb` command groups the project tools. [Install on Debian/Ubuntu and WSL](docs/cli-install-en.md). Physical modes still require native Linux and explicit restore authorization.

## Goal

Build a lightweight, free and independent reading system for the Kobo Aura HD while documenting a reproducible rescue path for devices left unusable after a failed factory reset or software corruption.

The project has two complementary goals:

1. **Rescue an Aura HD** from its own microSD card without redistributing proprietary Kobo system images.
2. **Liberate the Aura HD** by keeping only the hardware-specific layers that are required, then progressively replacing the Kobo userspace with a minimal stack centered on KOReader and free software components.

The PMKB V1 target is **Linux → PMKB → KOReader directly**. Nickel and Kobo
activation are outside the normal path. Necessary Netronix/Kobo hardware
components remain identified and preserved; this does not mean the entire
stack has already been rebuilt from source.

## FIRST BOOT #1 — preparation status

As of 3 October 2026, the FIRST BOOT #1 candidate is undergoing reconstruction
and offline qualification. **No successful first PMKB hardware boot is established.**
The following tools are available on `integration/pmkb-first-boot-1` at
[`a8ce226`](https://github.com/fr4nck/PimpMyKobo-AuraHD/tree/a8ce226bcd46483feb8e35e49f826fa076098bfb),
and are not yet integrated into `main` in this snapshot.

| Item | Actual status / reference |
| --- | --- |
| KOReader/rootfs builder | Local assembly and Linux ext4 P1 construction available; [EN contract](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/a8ce226bcd46483feb8e35e49f826fa076098bfb/docs/build-koreader-rootfs-spec-en.md) |
| ARM/runtime/bootstrap/storage audit | Static audit available, separate from hardware trials; [scope (FR)](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/a8ce226bcd46483feb8e35e49f826fa076098bfb/docs/audit-arm-runtime-fr.md) |
| Preflight | Image/content aggregation available; no FAIL means neither successful boot nor write authorization; [contract (FR)](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/a8ce226bcd46483feb8e35e49f826fa076098bfb/docs/preflight-koreader-fr.md) |
| FIRST BOOT #1 candidate | Final reconstruction result, commit, P1 SHA-256 and image-linked reports still to be recorded; [integration state](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/a8ce226bcd46483feb8e35e49f826fa076098bfb/docs/pmkb-first-boot-1-en.md) |
| Actual PMKB hardware | **UNQUALIFIED**: boot, framebuffer/E-Ink, touch, frontlight, P3 mounting and USB; no hardware PASS claimed |
| Calibre | A **V1** requirement, book transfer/USB not hardware-qualified; the read-only P3 prototype does not demonstrate that workflow |

The [FIRST BOOT protocol](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf/docs/first-boot-qualification-en.md)
and [evidence templates](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/d64a6e82d10ab1bb8833f3dbd9f464a27de1777a/docs/templates/first-boot/README.en.md)
are prepared on documentation branches. Their tests remain NOT TESTED.
Links are pinned so they work before convergence.

**P2/recoveryfs is protected**: no modification, repurposing or log storage.
Preserve pre-P1/HWCONFIG/waveform and P3 as well. A validated local build still
requires a separate plan and authorization before physical writes; first boot
will qualify only tests actually performed with evidence.

The [documentation/Git convergence plan (FR)](docs/first-boot-convergence-fr.md)
lists the proposed order and historical text to update after validation.

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

The target chain preserves the i.MX50 Boot ROM, U-Boot/Netronix, HWCONFIG,
necessary hardware parameters and waveform, then Linux and a minimal PMKB P1
launching KOReader directly. This is the target architecture, not a hardware
boot already demonstrated.

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
- require preservation of P2/`recoveryfs`, HWCONFIG and all areas outside the target.

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
- [x] Local reconstruction, historical import and disk-image simulation
- [x] pmkb command and Debian/Ubuntu/WSL package
- [x] Native backup and offline verification tools available
- [ ] Qualify native backup on actual hardware
- [ ] Qualify P1 restoration and boot on native Linux Live
- [x] First Qt/PySide6 workshop for local operations available
- [ ] Build the reference U-Boot and kernel
- [x] Minimal PMKB prototype and KOReader builder available on the integration branch
- [x] ARM/runtime/bootstrap/storage audits and preflight available on the integration branch
- [ ] Validate and record the reconstructed FIRST BOOT #1 candidate
- [ ] Qualify the first PMKB boot and its hardware components
- [ ] Qualify the V1-required Calibre book/USB workflow
- [ ] Replace and rebuild preserved components when replacements are demonstrated

## Documentation

- [Disassemble the Aura HD and access the internal microSD](docs/disassembly-en.md) — with original photos, iFixit/MobileRead sources and a Lynx-friendly text edition.
- [Text / Lynx disassembly guide](docs/disassembly-lynx-en.txt)
- [Documentation index](docs/README.en.md)
- [Roadmap and next steps](docs/ROADMAP.md)
- [Aura HD rescue](docs/rescue-en.md)
- [Recover the recovery files](docs/recover-files-en.md)
- [Aura HD inspector](docs/inspect-aura-hd-en.md)
- [Verify recoveryfs](docs/verify-recovery-en.md)
- [Aura HD hardware](docs/hardware-en.md)
- [Netronix HWCONFIG](docs/hwconfig-en.md)
- [Partition layout](docs/partition-layout-en.md)

## License

The license for original project code has not been selected yet. Third-party components and sources retain their respective licenses.
