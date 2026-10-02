# Recovering factory files from your own Aura HD

[Français](retrouver-fichiers-fr.md) | **English**

This repository intentionally does not publish complete system images, `fs.tgz`, `db.tgz`, full microSD dumps, or prebuilt blobs extracted from a reader.

That does not necessarily prevent recovery: an Aura HD that still has its microSD may already contain much of what is required to rescue itself.

This page explains where those files are located and how to recover them from **your own device**.

## Where are the useful files?

On the E606C0 Aura HD studied here, the microSD contains three partitions plus a raw area before P1.

| Area | Main role |
|---|---|
| raw area before P1 | U-Boot, kernel, HWCONFIG and low-level E-Ink data |
| P1 `rootfs` | main Linux system |
| P2 `recoveryfs` | recovery system and factory archives |
| P3 `KOBOeReader` | user data and Kobo database |

The most useful recovery files were found in P2:

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
/fs.md5sum
```

`fs.tgz` can rebuild P1. `db.tgz` contains initial data intended for P3. The two `E606C0` files match the Aura HD / Dragon hardware studied here.

## 1. Identify the correct microSD first

Never assume a physical disk number remains the same after reconnecting hardware.

On Windows, these read-only commands list disks and partitions:

```powershell
Get-Disk | Format-Table Number,FriendlyName,BusType,Size,PartitionStyle -AutoSize
```

After visually identifying the microSD, list its partitions using the disk number actually reported:

```powershell
Get-Partition -DiskNumber N | Format-Table PartitionNumber,DriveLetter,Type,Size,Offset -AutoSize
```

Replace `N` with the number actually shown by `Get-Disk`.

The studied device had this layout:

```text
P1  offset 9,961,472     size 268,435,968
P2  offset 278,397,440   size 268,435,968
P3  offset 546,833,408   FAT32, rest of the card
```

These values document the studied card. A future tool must always read and validate the real partition table before acting.

## 2. Back up P2 `recoveryfs` before exploring it

The recommended method is to work on an **image of P2**, not directly on the original partition.

On Linux, when the microSD is exposed as a normal block device, identify it first:

```bash
lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS
```

Then copy only the recovery partition to a local file. The device name depends on the host (`/dev/sdX2`, `/dev/mmcblkXp2`, etc.) and must be verified before the copy.

On Windows with WSL, some USB card readers are not exposed as Linux block devices. In that case, the method tested for this project is to read the P2 region from `\\.\PhysicalDriveN` using the offset and size reported by `Get-Partition`, then save that read into a local `AuraHD-p2-recovery.img` file.

That operation must be a **read from the microSD into a file**, never the reverse.

For the studied card:

```text
P2 offset: 278,397,440
P2 size:   268,435,968 bytes
```

The resulting image was exactly 268,435,968 bytes and was identified as:

```text
Linux ext4, label "recoveryfs"
```

## 3. Check P2 without modifying it

Before mounting:

```bash
e2fsck -f -n AuraHD-p2-recovery.img
```

The `-n` option prevents repairs.

Mount the image without replaying the ext4 journal:

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

`ro,noload` matters: the mount stays read-only and the journal is not replayed.

## 4. Find `fs.tgz`, `db.tgz`, U-Boot and the kernel

Once P2 is mounted:

```bash
find /mnt/aurahd-recovery/upgrade -maxdepth 3 -type f -printf '%p  %s bytes\n' | sort
```

On the studied E606C0 unit, this found:

```text
/mnt/aurahd-recovery/upgrade/fs.tgz
/mnt/aurahd-recovery/upgrade/db.tgz
/mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0
```

To keep a private local copy outside the repository:

```bash
mkdir -p ~/AuraHD-private-backup
cp -a /mnt/aurahd-recovery/upgrade/fs.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/db.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0 ~/AuraHD-private-backup/
```

These copies should remain local and should not be added to the public repository.

## 5. Verify recovered archives

The gzip archives can be tested without extracting them:

```bash
gzip -t /mnt/aurahd-recovery/upgrade/fs.tgz
gzip -t /mnt/aurahd-recovery/upgrade/db.tgz
```

The recovery filesystem also contains its own `fs.md5sum` manifest:

```bash
sudo sh -c 'cd /mnt/aurahd-recovery && md5sum -c fs.md5sum'
```

On the studied unit, checking as an unprivileged user failed on `bin/antiword` because of file permissions; running the verification as root completed successfully.

It is also useful to store SHA-256 hashes for private backups:

```bash
sha256sum ~/AuraHD-private-backup/*
```

## 6. Recover HWCONFIG

HWCONFIG is not a normal partition file: it lives in the raw area before P1.

On the studied unit:

```text
HWCONFIG offset: 524,288 bytes = 0x80000
signature:       HW CONFIG v1.7
```

After saving the raw area before P1 into a local file, locate the signature with:

```bash
grep -aob 'HW CONFIG' AuraHD-original-boot.bin
```

Then inspect the block:

```bash
dd if=AuraHD-original-boot.bin bs=1 skip=524288 count=110 status=none | od -Ax -tx1z
```

The studied unit reported, among other values:

```text
PCB                    28 -> E606C0
codename                dragon
RAM                     512 MiB
DisplayResolution       1440x1080
FrontLight              TABLE3+
CPUFreq                 1 GHz
HallSensor              TLE4913
DisplayBusWidth         16Bits_mirror
FrontLight_LED_Driver   SY7201
```

## 7. Back up the raw boot area

The raw area extends from the beginning of the microSD to the beginning of P1.

On the studied unit, P1 started at offset 9,961,472, so the first 9,961,472 bytes were copied into a local backup file.

That backup contains HWCONFIG and other critical low-level data.

It should not be published verbatim in this repository.

## 8. What about the E-Ink waveform?

The Netronix sources show that U-Boot also loads an E-Ink waveform from the low-level data area.

The project has **not yet documented its exact offset on the E606C0 Aura HD with enough confidence**.

Therefore this page intentionally does not yet provide a waveform extraction command. The exact location and format should be verified before publishing a reproducible procedure.

## 9. Rebuild P1 without distributing a Kobo image

Once `fs.tgz` has been recovered from the user's own P2, a fresh ext4 `rootfs` image can be created locally, populated with `fs.tgz`, and fully verified before any write to the reader.

That is the approach documented in [rescue-en.md](rescue-en.md).

It allows the project to publish a reproducible rescue method without hosting a downloadable Kobo system image.

## Keep these private

Keep local copies and hashes of:

- the raw pre-P1 boot-area backup;
- the original P1 image;
- the P2 `recoveryfs` image;
- `fs.tgz`;
- `db.tgz`;
- extracted prebuilt U-Boot and kernel files;
- any future waveform extraction.

The public repository should provide documentation and tools that let owners **find and verify** these items, rather than necessarily distributing the items themselves.
