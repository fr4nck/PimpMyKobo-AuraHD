# Verifying `recoveryfs`

[Français](verify-recovery-fr.md) | **English**

`tools/verify-recovery.py` performs a read-only verification of an already mounted `recoveryfs` partition, or of a copied recovery tree.

The tool does not mount the microSD itself and never writes to the recovery source.

## What it checks

By default it verifies:

- the presence of `fs.md5sum`;
- every file covered by that manifest;
- the complete gzip stream of `upgrade/fs.tgz`;
- the complete gzip stream of `upgrade/db.tgz`;
- the Aura HD E606C0 U-Boot file:
  `upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin`;
- the Aura HD E606C0 kernel:
  `upgrade/ntx508/uImage-E606C0`.

With `--hash-files`, it also computes SHA-256 hashes for the two archives and the two E606C0 files so users can document their own private backups.

## Recommended preparation

Work from an image of P2 whenever possible, and mount it explicitly read-only without replaying the ext4 journal:

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

The process for locating and copying P2 is documented in [Recovering files from your own Aura HD](recover-files-en.md).

## Usage

From the repository root:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery
```

To also record SHA-256 hashes:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

Machine-readable JSON output:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --json
```

The manifest check can be skipped temporarily with `--skip-md5`, but that substantially reduces the diagnostic value.

## Why root privileges may be needed

On the recovery studied for this project, `bin/antiword` was not readable by an ordinary user. The manifest therefore appeared to fail without `sudo` even though the files were correct.

The tool distinguishes between:

- missing files;
- unreadable files;
- MD5 mismatches;
- invalid manifest entries.

## Exit codes

- `0`: every requested check passed;
- `1`: at least one requested check is missing, unreadable or inconsistent.

## Safety

The source tree is opened only for reading. The tool contains no repair, extraction or raw-device write function.

Its purpose is to establish whether the recovery partition is trustworthy enough to use as the source for a later local reconstruction of P1.