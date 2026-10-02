# Automatically inspect a Kobo Aura HD

[Français](inspect-aura-hd-fr.md) | **English**

`tools/inspect-aura-hd.py` inspects a complete microSD, a disk image, or local disks in order to identify a Kobo Aura HD / Dragon / E606C0.

The tool is **strictly read-only**: no source is opened for writing and no filesystem is mounted.

## What the tool checks

It:

1. reads the MBR;
2. looks for `HW CONFIG ` at Netronix offset `0x80000`;
3. reads the HWCONFIG version and payload size;
4. confirms an Aura HD only for `HW CONFIG v1.7`, a 39-byte payload and `bPCB = 28`;
5. reports PCB 28 in any other format as probable but unconfirmed;
6. validates MBR boot indicators, overlaps and, when source size is known, partitions extending beyond the medium;
7. detects ext and FAT signatures and labels without mounting partitions;
8. can compute SHA-256 of the raw pre-P1 area, only after positive identification and a valid MBR.

Low-level reads are aligned to 512 bytes, notably for Windows `\\.\PhysicalDriveN` handles.

## Important: a read-only tool does not make the medium physically read-only

Even though the tool writes nothing, the operating system may write to an inserted card:

- **Windows** may assign a drive letter to FAT32 P3 and offer to format the ext4 partitions: always cancel format prompts and avoid opening the user partition during diagnosis;
- **desktop Linux** may automount a partition and replay an ext4 journal: disable automount and, where practical, mark the block device read-only in the kernel after identifying it with certainty.

For deeper analysis, working from a local image remains preferable.

## Windows

Raw access to `\\.\PhysicalDriveN` normally requires an Administrator PowerShell.

From the repository root:

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

The tool uses `Get-Disk` to obtain current disk numbers and sizes. If PowerShell is missing, `Get-Disk` fails, or the command times out, disk-enumeration diagnostics are shown instead of blindly scanning physical-drive numbers.

To also display ordinary skipped devices:

```powershell
python .\tools\inspect-aura-hd.py --verbose --hash-boot
```

Actual read errors are reported even without `--verbose`.

## Linux

From the repository root:

```bash
sudo python3 ./tools/inspect-aura-hd.py --hash-boot
```

The scan uses `/sys/block`. `loop`, `nbd`, `rpmb` and boot pseudo-devices are skipped to reduce noise.

For an explicitly supplied block device, the tool also attempts a seek-to-end size query when `fstat` does not expose a usable size.

## WSL

WSL does not necessarily expose a Windows USB card reader as a Linux block device. In that case, running the inspector with Windows Python from PowerShell is recommended.

## Explicit source

The tool also accepts a complete disk image or an explicitly chosen raw device as a positional argument. Supplying a path disables automatic scanning for that run.

Open/read errors are always shown for an explicit source.

## Expected output on the studied E606C0 unit

```text
KOBO AURA HD IDENTIFIED
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
```

Partition data is then read directly from the medium. On the studied unit:

```text
P1: offset=9,961,472    size=268,435,968  type=0x83  ext label="rootfs"
P2: offset=278,397,440  size=268,435,968  type=0x83  ext label="recoveryfs"
P3: offset=546,833,408  ...              type=0x0C  FAT32 label="KOBOeReader"
```

These values are never used to arbitrarily choose a disk.

## JSON output

```powershell
python .\tools\inspect-aura-hd.py --json --lang en
```

The JSON document contains `schema_version`, `discovery_errors`, and `results`. Each result exposes fields including `source_size`, `errors[]`, `warnings[]`, MBR data and HWCONFIG data.

## Exit codes

- `0`: confirmed E606C0 Aura HD with no blocking inconsistency detected;
- `1`: no confirmed Aura HD and no access failure preventing diagnosis;
- `2`: access/read error, blocking enumeration failure, or a confirmed Aura HD with a blocking inconsistency.

A normal GPT disk or another simply unsupported medium is therefore not treated as an access error.

## Check `recoveryfs` next

The inspector intentionally does not walk the ext4 tree from the raw disk. To check `fs.tgz`, `db.tgz`, U-Boot and the kernel, use [`verify-recovery.py`](verify-recovery-en.md) on an image or an explicitly read-only mount.

## Tests

Synthetic tests include the complete inspection path through a fake reader that rejects every unaligned low-level read. GitHub CI runs the suite on Linux and Windows across several Python versions.
