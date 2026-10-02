# Recovering factory files from your own Aura HD

[Français](retrouver-fichiers-fr.md) | **English**

This repository intentionally does not publish complete system images, `fs.tgz`, `db.tgz`, full microSD dumps, or prebuilt blobs extracted from a reader.

That does not necessarily prevent recovery: an Aura HD that still has its microSD may already contain much of what is required to rescue itself.

This page explains where those files are located and how to recover them from **your own device**.

## Before anything else: prevent unintended writes

Project tools are read-only, but the operating system can still write to an inserted card.

- **Windows**: always cancel format prompts for the ext4 partitions. Avoid opening the FAT32 `KOBOeReader` volume unnecessarily while preserving the card.
- **Desktop Linux**: disable automount. A read-write ext4 mount may replay the journal.
- For detailed analysis, create a local image first and work from that copy.

## Where are the useful files?

On the studied E606C0 Aura HD, the microSD contains three partitions plus a raw area before P1.

| Area | Main role |
|---|---|
| raw area before P1 | U-Boot, kernel, HWCONFIG and low-level E-Ink data |
| P1 `rootfs` | main Linux system |
| P2 `recoveryfs` | recovery system and factory archives |
| P3 `KOBOeReader` | user data and Kobo database |

Useful recovery files observed in P2 include:

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
/fs.md5sum
```

`fs.tgz` can rebuild P1. `db.tgz` contains initial data intended for P3. The `E606C0` files match the Aura HD / Dragon hardware studied here.

## 1. Identify the card without assuming its disk number

The recommended method is now the project's inspector:

```powershell
python .\tools\inspect-aura-hd.py --verbose --hash-boot
```

On Windows, run it from an Administrator PowerShell. It uses `Get-Disk`, hard-codes no disk number, and only confirms an Aura HD when HWCONFIG matches the expected `v1.7 / 39-byte / PCB 28` format.

To simply list Windows disks without raw access:

```powershell
Get-Disk | Format-Table Number,FriendlyName,BusType,Size,PartitionStyle -AutoSize
```

On Linux:

```bash
lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS
```

Never assume a physical disk number or device name remains stable after reconnecting hardware.

The studied card had this layout:

```text
P1  offset 9,961,472     size 268,435,968
P2  offset 278,397,440   size 268,435,968
P3  offset 546,833,408   FAT32, rest of the card
```

These values document only the studied card. Tooling must read the actual partition table of the current medium.

## 2. Back up P2 `recoveryfs` before exploring it

The recommended method is to work on an **image of P2**, not directly on the original partition.

On Linux, after positively identifying the real recovery partition, a raw read can be copied into a local file. This documentation intentionally does not publish a ready-to-paste generic command containing a fake device name: the device identifier must be established on the actual machine first.

On Windows, some USB card readers are not exposed as Linux block devices in WSL. During the real rescue, P2 was read from the positively identified `PhysicalDrive` using the **offset and size actually read from the card**, then saved into a local file.

That operation must always go **from the microSD to a file**, never the reverse.

For the studied unit:

```text
P2 offset: 278,397,440
P2 size:   268,435,968 bytes
```

The resulting image was ext4 with label `recoveryfs`.

## 3. Check the P2 image without modifying it

Before mounting:

```bash
e2fsck -f -n AuraHD-p2-recovery.img
```

The `-n` option prevents repairs.

Mount without replaying the ext4 journal:

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

## 4. Find `fs.tgz`, `db.tgz`, U-Boot and the kernel

Once the P2 image is mounted:

```bash
find /mnt/aurahd-recovery/upgrade -maxdepth 3 -type f -printf '%p  %s bytes\n' | sort
```

On the studied unit this found, among other files:

```text
/mnt/aurahd-recovery/upgrade/fs.tgz
/mnt/aurahd-recovery/upgrade/db.tgz
/mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0
```

To keep private local copies outside the repository:

```bash
mkdir -p ~/AuraHD-private-backup
cp -a /mnt/aurahd-recovery/upgrade/fs.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/db.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0 ~/AuraHD-private-backup/
```

These copies should remain local and should not be added to the public repository.

## 5. Verify the recovery properly

The project verifier checks the manifest, complete gzip streams, tar end markers, archive contents and E606C0 artifacts:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files --lang en
```

The original rescue also used these independent checks:

```bash
gzip -t /mnt/aurahd-recovery/upgrade/fs.tgz
gzip -t /mnt/aurahd-recovery/upgrade/db.tgz
sudo sh -c 'cd /mnt/aurahd-recovery && md5sum -c fs.md5sum'
```

On the studied unit, `bin/antiword` required root privileges for a complete manifest verification.

## 6. Recover HWCONFIG

HWCONFIG is not a normal partition file: it lives in the raw area before P1.

On the studied unit:

```text
HWCONFIG offset: 524,288 bytes = 0x80000
signature:       HW CONFIG v1.7
```

After saving the raw pre-P1 area into a local file:

```bash
grep -aob 'HW CONFIG' AuraHD-original-boot.bin
```

Then:

```bash
dd if=AuraHD-original-boot.bin bs=1 skip=524288 count=110 status=none | od -Ax -tx1z
```

The studied unit reported PCB 28 / E606C0, 512 MiB RAM, 1440×1080 resolution, `TABLE3+`, `TLE4913`, `16Bits_mirror` display bus and `SY7201` LED driver.

## 7. Back up the raw boot area

The raw area extends from the start of the microSD to the actual beginning of P1.

On the studied unit, P1 started at offset 9,961,472, so the first 9,961,472 bytes were preserved locally. This area includes HWCONFIG and other critical low-level data.

It should not be published verbatim in this repository.

## 8. What about the E-Ink waveform?

The Netronix sources show that U-Boot also loads an E-Ink waveform from the low-level data area. Its exact offset on the E606C0 Aura HD is **not yet documented with enough confidence** to publish an extraction command.

## 9. Rebuild P1 without distributing a Kobo image

Once `fs.tgz` has been recovered from the owner's own P2, a fresh ext4 `rootfs` image can be created locally, populated and fully verified before any write to the reader. This is the approach documented in [rescue-en.md](rescue-en.md).

## Keep these private

Keep local copies and hashes of:

- the raw pre-P1 boot-area backup;
- the original P1 image;
- the P2 `recoveryfs` image;
- `fs.tgz`;
- `db.tgz`;
- extracted prebuilt U-Boot and kernel files;
- any future waveform extraction.

The public repository should provide tools that let owners **find and verify** these items rather than necessarily distributing the items themselves.
