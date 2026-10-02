# Verifying `recoveryfs`

[Français](verify-recovery-fr.md) | **English**

`tools/verify-recovery.py` performs a read-only verification of an already mounted `recoveryfs` partition or a copied recovery tree.

The tool never mounts the microSD itself and never writes to the recovery source.

## What it checks

By default it verifies:

- the presence and consistency of `fs.md5sum`;
- complete reading of `upgrade/fs.tgz` and `upgrade/db.tgz`;
- complete gzip consumption through the footer so CRC32, ISIZE and truncation errors are observed;
- the two 512-byte zero blocks marking a correct tar end-of-archive;
- every tar entry and all regular-file payload data;
- rejection of empty archives or archives containing no regular files;
- at least one non-empty `u-boot_mddr_512-E606C0-*.bin` candidate;
- `uImage-E606C0` as a legacy U-Boot image: magic `0x27051956`, header CRC, declared data size and data CRC;
- optional zero padding after the declared `uImage` payload while rejecting non-zero trailing bytes;
- rejection of critical paths escaping the recovery tree through traversal or symlinks.

No file is extracted to disk during those checks.

With `--hash-files`, the tool computes SHA-256 for the two archives, every valid E606C0 U-Boot candidate, and the kernel.

## Why tar end markers are checked

A gzip stream can be perfectly valid while containing a truncated tar, for example when a `tar | gzip` pipeline is interrupted but gzip itself closes cleanly. A gzip-only check, or a tar reader that stops silently, can therefore produce a false positive.

The verifier explicitly requires the **1024 zero bytes at the tar end** before considering an archive coherent.

## Recommended preparation

Prefer working from a **copy of P2**, not directly from the original card.

Mounting a previously copied P2 image:

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

`ro,noload` prevents ext4 journal replay on the mounted image.

## Usage

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files --lang en
```

JSON output:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --json --lang en
```

## `--skip-md5` is not a green verdict

The manifest check can be skipped for diagnostics:

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --skip-md5 --lang en
```

In that mode the result contains `partial: true` and `ok: false`. If another check also fails, the human summary remains **INCOMPLETE OR INCONSISTENT** rather than hiding that failure behind the partial status.

## U-Boot variants

The verifier accepts files matching:

```text
u-boot_mddr_512-E606C0-*.bin
```

Empty files are rejected. If exactly one valid candidate exists, it can be reported as the unique candidate. If several variants are present, none is automatically selected: a future restoration tool should choose from HWCONFIG / RAM type rather than alphabetical ordering.

## `fs.md5sum` manifests

Absolute paths, `../` traversal and symlinks escaping the recovery tree are rejected.

GNU `md5sum` escaped filenames are decoded only for records actually prefixed with `\`. `\n`, `\r` and `\\` escapes are supported.

The verifier distinguishes missing files, unreadable files, mismatches and invalid manifest entries.

## Exit codes

- `0`: all mandatory checks passed;
- `1`: recovery is incomplete/inconsistent, or verification was deliberately partial with `--skip-md5`;
- `2`: the recovery path is invalid or inaccessible enough to prevent verification.

## Synthetic tests

The test suite covers, among other cases:

- truncated gzip and corrupt gzip CRC;
- valid gzip containing a truncated tar;
- directory-only archives;
- trailing garbage;
- traversal and escaping symlinks;
- empty U-Boot, alternate RAM variants and multiple variants;
- invalid `uImage` magic/CRC;
- zero-padded `uImage` files;
- GNU escaped manifest names;
- partial `--skip-md5` with and without another failure;
- absence of write-mode source opens during verification.

GitHub CI runs the tests on Linux and Windows across several Python versions. No Kobo firmware blob is included in the tests.

## Safety

The verifier repairs nothing and writes nothing. Its only purpose is to determine whether a copied `recoveryfs` is coherent enough to be used as the source of a later local reconstruction.
