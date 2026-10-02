# Automatically inspect a Kobo Aura HD

[Français](inspect-aura-hd-fr.md) | **English**

`tools/inspect-aura-hd.py` avoids manual handling of disk numbers, offsets and binary structures.

The tool is **strictly read-only**: sources are opened with `rb`, and the script contains no physical-device write path.

## What the tool checks

With no argument it scans accessible disks and then:

1. reads the MBR;
2. validates its signature, boot indicators, partition bounds and overlaps;
3. looks for `HW CONFIG ` at Netronix offset `0x80000`;
4. reads HWCONFIG using 512-byte-aligned reads, which are required for Windows raw disks;
5. only confirms `E606C0 / Dragon / Aura HD` for the observed `v1.7` 39-byte format;
6. detects ext and FAT signatures directly without mounting partitions;
7. reports short reads and partitions extending beyond the actual source size;
8. can hash the pre-P1 area only after positive identification and MBR validation.

A HWCONFIG containing `PCB = 28` but a different version or payload size is reported as a **probable E606C0**, not as a confirmed identification.

## Windows

To read `\\.\PhysicalDriveN`, run PowerShell **as Administrator**.

From the repository root:

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

The script uses `Get-Disk` to discover the currently assigned disk numbers. No `PhysicalDriveN` value is hard-coded.

Access failures are not treated as “not a Kobo”: they are shown explicitly. When an explicitly supplied source cannot be read, the tool returns exit code `2`.

## Linux

From the repository root:

```bash
sudo python3 ./tools/inspect-aura-hd.py --hash-boot
```

The scan uses `/sys/block` and skips common virtual devices such as `loop`, `nbd` and `rpmb`.

## WSL

WSL does not necessarily expose a Windows USB card reader as a Linux block device. For a Windows USB reader, prefer **Windows Python from an Administrator PowerShell**.

## Important: the tools are read-only, the operating system may not be

Connecting the card may trigger writes outside the script.

- **Windows**: never accept a format prompt for the ext4 partitions. Avoid opening the FAT32 volume unnecessarily while taking preservation copies.
- **Desktop Linux**: disable automount before handling the card. A read-write ext4 mount may replay the journal.

For especially conservative work on Linux, the device can be marked read-only at the kernel level before inspection. First determine the real device with `lsblk`; names such as `/dev/sdX` in documentation are examples and must never be copied literally.

## Expected output on the studied E606C0 unit

```text
KOBO AURA HD IDENTIFIED
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
```

The tool then prints the partitions actually read from the disk, including MBR type, offset, size, detected filesystem and label when available.

## JSON output

```powershell
python .\tools\inspect-aura-hd.py --json --lang en
```

The JSON document contains `schema_version`, per-source results, `source_size`, `errors[]`, `warnings[]`, the parsed MBR, decoded HWCONFIG and detected filesystem labels.

## Exit codes

- `0`: confirmed E606C0 Aura HD;
- `1`: no confirmed Aura HD and no decisive access failure;
- `2`: access/read error prevented the requested diagnosis.

## Check `recoveryfs` next

`inspect-aura-hd.py` intentionally does not walk the recovery ext4 tree from the raw disk. Use [`verify-recovery.py`](verify-recovery-en.md) next on a copy or an explicitly read-only mount.

## Safety

Current safeguards include:

- source opened with `rb` only;
- 512-byte-aligned low-level reads;
- no hard-coded disk number;
- source-size and MBR-geometry validation;
- strict `v1.7 / 39-byte / PCB 28` identification;
- boot hashing capped at 64 MiB and only after positive identification;
- visible read errors rather than silent false negatives.
