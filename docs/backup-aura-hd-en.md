# Backing up a Kobo Aura HD

[Français](backup-aura-hd-fr.md) | **English**

`tools/backup-aura-hd.py` copies the useful areas of a **positively identified E606C0** Aura HD microSD card into a backup directory, then verifies every copy with SHA-256.

> **PimpMyKobo never modifies the source.** The source is only ever opened read-only (`rb`). The tool does not mount, unmount, format or repartition anything, and never calls `dd` or `diskpart`. The only place it writes is the destination directory you specify.
>
> **The host operating system may still write to the card**: Linux automount, Windows drive letters and format prompts, indexing… See [Protecting the microSD on Windows](windows-preservation-en.md) and the "operating-system writes" section of [the inspector](inspect-aura-hd-en.md).

This tool **does not restore anything**. No restore command is provided.

## What is backed up

| File | Content | Mandatory |
|---|---|---|
| `pre-p1.bin` | byte 0 up to the start of P1: MBR, U-Boot, HWCONFIG, low-level data | yes |
| `p1-rootfs.img` | exact binary copy of P1 `rootfs` | yes |
| `p2-recoveryfs.img` | exact binary copy of P2 `recoveryfs` | yes |
| `p3-userdata.img` | exact binary copy of P3 `KOBOeReader` | **no**, only with `--include-userdata` |
| `backup-manifest.json` | machine-readable manifest | yes |
| `SHA256SUMS` | hashes of the verified files, `sha256sum` format | yes |

Sizes **always come from the MBR of the card being read**, never from an existing file. On the studied unit: pre-P1 area = 9,961,472 bytes, P1 = P2 = 268,435,968 bytes. A rebuilt 268,435,456-byte `rootfs` image is therefore not the same size as the real partition.

## What is not backed up

- P3 by default (about 30 GB on the studied card), because it mostly holds books and user data and takes a long time to copy;
- any areas between partitions or after P3: they are measured and reported in the manifest (`gaps_not_backed_up`, `unpartitioned_tail_bytes`);
- the card's hardware serial number (CID): it cannot be read reliably through a USB reader.

## Mandatory identification

Before creating anything, the tool reuses the qualified inspector and requires:

- `HW CONFIG` v1.7, 39 bytes, PCB 28 / E606C0;
- a valid MBR, with no overlaps and no partition beyond the end of the medium;
- exactly P1, P2, P3, in that order;
- P1 ext labelled `rootfs`, P2 ext labelled `recoveryfs`, P3 FAT. A P3 label other than `KOBOeReader` only produces a warning;
- a plausible pre-P1 area that contains HWCONFIG and is at most 64 MiB.

Otherwise: **BACKUP REFUSED**, exit code `2`, and no directory is created.

If the medium size cannot be determined, the tool checks that the last sector of P3 is readable before accepting the geometry.

## Destination

- It must be given explicitly and must either not exist or be an empty directory. Any collision is refused.
- Free space is checked before copying: requested components + 16 MiB margin.
- The tool refuses a destination located **on the source card** when that can be determined:
  - on Linux, via `/sys/dev/block` and `/proc/self/mountinfo`;
  - on Windows, via `Get-Partition -DriveLetter`, a read-only query.
- When it cannot be determined (network path, LVM/dm stacking, …), the tool refuses unless `--allow-unverified-destination` is given. Only use that option if you are certain the destination is not on the card.

## Usage

Always start with a dry run, which creates no file:

```powershell
python .\tools\backup-aura-hd.py \\.\PhysicalDriveN D:\Aura-backup --dry-run --lang en
```

Then the backup, from an Administrator PowerShell:

```powershell
python .\tools\backup-aura-hd.py \\.\PhysicalDriveN D:\Aura-backup --lang en
```

On Linux:

```bash
sudo python3 ./tools/backup-aura-hd.py /dev/sdX ~/Aura-backup --lang en
```

`N` and `sdX` are examples: use the disk actually identified by `inspect-aura-hd.py`.

Options:

- `--include-userdata`: also back up P3;
- `--single-pass`: do not re-read each source range a second time (faster, fewer checks);
- `--json`: only the JSON manifest is written to stdout, with progress going to stderr;
- `--quiet`: no progress output.

Exit codes:

- `0`: complete and verified backup (or successful dry run);
- `1`: backup failed;
- `2`: refused before any copy;
- `130`: interrupted.

## How copies are verified

For each component:

1. the bytes read from the source are hashed during the copy (`sha256_stream`);
2. the source range is read and hashed a second time (`sha256_source_reread`, unless `--single-pass`);
3. the file is written as `.part`, synced to disk, then **read back from the destination** (`sha256_destination`);
4. only if all three hashes and the size agree is the `.part` renamed to its final name.

On any mismatch, the file is renamed to `.FAILED`: it is kept as evidence but never treated as valid. The backup is then marked `failed`.

At the end, the pre-P1 area is read again to check that the card did not change in the meantime (`identity_recheck`).

To verify a backup later:

```bash
cd ~/Aura-backup && sha256sum -c SHA256SUMS
```

On Windows:

```powershell
Get-FileHash .\p1-rootfs.img -Algorithm SHA256
```

Compare the result with `SHA256SUMS` or with the component's `sha256` field in the manifest.

Limitation: on Linux, the second read of a block device may be served from the OS cache. It mainly detects an unstable reader, not physical degradation of the card.

## Reading `backup-manifest.json`

| Field | Meaning |
|---|---|
| `schema_version` | format version (1) |
| `status` | `in_progress`, `complete`, `failed` or `interrupted` |
| `complete` | `true` **only** if every requested component is `verified` and the identity recheck matches |
| `source.path_at_backup_time` | name used that day, **not an identity** (`path_is_identity: false`) |
| `source.size`, `source.size_from` | medium size and where that information came from |
| `identification` | decoded HWCONFIG: version, length, PCB, RAM, RAM type, CPU, display, raw fields |
| `mbr` | full geometry, types, labels, SHA-256 of sector 0, uncovered areas |
| `components[]` | for each file: offset, size, status (`verified`, `failed`, `interrupted`, `not_started`, `not_requested`), hashes, error if any |
| `target_fingerprint` | target fingerprint (see below) |
| `identity_recheck` | final re-read of the pre-P1 area |
| `warnings`, `errors` | warnings and errors |

The manifest is rewritten atomically after each component. An interrupted backup therefore still leaves a readable manifest with `complete: false`.

A `.part` file is **never** valid.

## Target fingerprint (`target_fingerprint`)

Algorithm `pmkb-target-v1`: SHA-256 of the canonical JSON (sorted keys, compact) containing:

- the size and SHA-256 of the pre-P1 area;
- the SHA-256 of the HWCONFIG block (header and payload);
- the MBR geometry: number, type, start LBA and sector count of each partition.

It is derived **only from bytes read on the source**. Names such as `PhysicalDrive2` or `/dev/sdb` are never part of it. The medium size is recorded alongside it but excluded from the digest, because it is not always determinable.

What it allows: checking that a card has **the same low-level content and geometry** as the one that was backed up.

Its limits:

- it identifies **content**, not a physical card: a bit-exact clone has the same fingerprint;
- any future write to the pre-P1 area changes it: Kobo update, new U-Boot or new kernel;
- its uniqueness between two Aura HD units is **not demonstrated**, because it is unknown whether the pre-P1 area contains per-device data;
- it says nothing about the state of P1, P2 and P3.

It **must not** become, on its own, the authorization rule of a future restore. Restore rules remain to be decided explicitly.

## Keep the backup private

The files produced contain proprietary and personal data: U-Boot, kernel, Kobo system, books. **Do not publish them.** The repository `.gitignore` already excludes `*.bin`, `*.img` and `backups/`.
