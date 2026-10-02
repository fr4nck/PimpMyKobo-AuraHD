# Automatically inspect a Kobo Aura HD

[Français](inspect-aura-hd-fr.md) | **English**

`tools/inspect-aura-hd.py` is the project's first tool intended to avoid manual handling of disk numbers, offsets and binary structures.

It works **strictly read-only**: sources are always opened using Python `rb` mode and the tool contains no write path to a physical disk.

## What the tool does

With no argument, it scans accessible disks and then:

1. reads the MBR;
2. looks for the `HW CONFIG ` signature at Netronix offset `0x80000`;
3. reads the HWCONFIG version and payload size;
4. decodes the known v1.7 fields;
5. recognizes the studied Aura HD when `bPCB = 28`, i.e. `E606C0 / Dragon`;
6. reads the four MBR partition entries;
7. detects ext and FAT signatures directly without mounting partitions;
8. reports `rootfs`, `recoveryfs` and `KOBOeReader` labels when present;
9. can optionally compute SHA-256 of the entire raw area before P1.

The tool does **not** assume that the Kobo is `PhysicalDrive2`, `/dev/sdb`, or any other fixed device name.

## Requirements

- Python 3.10 or newer recommended;
- no external Python modules;
- Windows or Linux.

On Windows, raw access to `\\.\PhysicalDriveN` may require an Administrator PowerShell.

On Linux, reading a raw block device may require `sudo`.

## Windows: automatic detection

From the repository root:

```powershell
python .\tools\inspect-aura-hd.py
```

The tool calls `Get-Disk` to obtain the current disk list and then attempts read-only opens only.

To also report skipped or inaccessible disks:

```powershell
python .\tools\inspect-aura-hd.py --verbose
```

To additionally hash the region from byte 0 to the actual beginning of P1:

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

## Linux

From the repository root:

```bash
sudo python3 ./tools/inspect-aura-hd.py
```

The scan uses `/sys/block` and does not rely on a predefined device name.

## WSL

WSL does not necessarily expose a Windows USB card reader as a Linux block device.

In that case, the simplest approach is to run the tool using Windows Python from PowerShell:

```powershell
python .\tools\inspect-aura-hd.py
```

The tool can also inspect a full-disk image stored in a file.

## Explicitly inspect an image or device

A complete microSD image:

```powershell
python .\tools\inspect-aura-hd.py C:\Users\Ordi\AuraHD-full.img
```

On Linux:

```bash
sudo python3 ./tools/inspect-aura-hd.py /dev/sdb
```

In the second example, `/dev/sdb` is documentation only. When using automatic scan with no argument, no device name needs to be entered.

## Expected output on an E606C0

The tool should recover at least:

```text
KOBO AURA HD IDENTIFIED
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
  RAM: 3 -> 512MB
  RAM type: 2 -> K4X2G323PC
  CPU: 2 -> mx50
  CPU frequency: 2 -> 1G
  Display: 3 -> 1440x1080
  Frontlight: 6 -> TABLE3+
  Hall sensor: 1 -> TLE4913
  Display bus: 3 -> 16Bits_mirror
  Frontlight LED driver: 0 -> SY7201
```

It then prints the partition layout actually read from the MBR. On the studied device, for example:

```text
P1: offset=9,961,472    size=268,435,968  ext label="rootfs"
P2: offset=278,397,440  size=268,435,968  ext label="recoveryfs"
P3: offset=546,833,408  ...              FAT32 label="KOBOeReader"
```

Those offsets are not used to arbitrarily identify the disk. They are displayed after reading that disk's own partition table.

## JSON output

To reuse the result in future scripts:

```powershell
python .\tools\inspect-aura-hd.py --json
```

The output includes:

- inspected source;
- disk metadata;
- MBR and partitions;
- decoded HWCONFIG fields;
- `E606C0` identification;
- detected filesystem labels.

## French output

French is the default. It can be selected explicitly with:

```powershell
python .\tools\inspect-aura-hd.py --lang fr
```

## Exit codes

- `0`: an E606C0 Aura HD was identified;
- `1`: no E606C0 Aura HD was identified.

## Current limitation: recoveryfs contents

The inspector detects P2 and its `recoveryfs` label directly from filesystem structures, but it does **not yet walk the ext4 directory tree** from Windows.

It therefore does not yet automatically confirm the presence of:

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
```

That check is intended for a separate `verify-recovery` tool working from an image or read-only mount.

## Safety

The design follows four rules:

- no `r+b`, `wb` or equivalent opens;
- no hard-coded disk number;
- identification from data actually read from the medium;
- no write operation even after a positive identification.

The goal is to make a diagnostic command safe enough that a mistaken device assumption cannot turn into data destruction.
