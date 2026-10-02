# Verifying `recoveryfs`

[Français](verify-recovery-fr.md) | **English**

`tools/verify-recovery.py` performs a read-only verification of an already mounted `recoveryfs` partition or a copied recovery tree.

The tool never mounts the microSD itself and never writes to the recovery source.

## What it checks

By default it verifies:

- the presence and consistency of `fs.md5sum`;
- complete reading of `upgrade/fs.tgz` and `upgrade/db.tgz`;
- tar structure validity;
- complete gzip consumption so CRC32, final size and truncation errors are observed;
- rejection of non-zero data after the logical tar end marker;
- at least one non-empty `u-boot_mddr_512-E606C0-*.bin` candidate;
- `uImage-E606C0` as a legacy U-Boot image: magic `0x27051956`, header CRC, declared size and data CRC;
- rejection of critical paths that escape the recovery tree through traversal or symlinks.

No file is extracted to disk during those checks.

With `--hash-files`, the tool also computes SHA-256 hashes for the two archives and the selected E606C0 artifacts.

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

In that mode the result contains `partial: true`, `ok: false`, and the program does not report a global success. Future reconstruction tooling must therefore never interpret this mode as a validated recovery.

## U-Boot variants

The RAM type is encoded in the U-Boot filename. The verifier no longer requires only `K4X2G323PC`; it accepts E606C0 candidates matching:

```text
u-boot_mddr_512-E606C0-*.bin
```

The actual selected filename is preserved in JSON output.

## `fs.md5sum` manifests

Absolute paths, `../` traversal and symlinks escaping the recovery tree are rejected.

GNU `md5sum` escaped filenames are decoded only when the manifest line is actually prefixed with `\`, preventing accidental transformation of literal backslash sequences.

The verifier distinguishes missing files, unreadable files, mismatches and invalid manifest entries.

## Exit codes

- `0`: all mandatory checks passed;
- `1`: recovery is incomplete/inconsistent, or verification was deliberately partial with `--skip-md5`;
- `2`: the recovery path is invalid or inaccessible enough to prevent verification.

## Synthetic tests

Repository tests now cover, among other cases:

- truncated archives;
- corrupt gzip CRC;
- trailing garbage;
- traversal and escaping symlinks;
- empty U-Boot files;
- alternate E606C0 U-Boot RAM variants;
- invalid `uImage` magic and CRC;
- escaped manifest names;
- partial `--skip-md5` mode.

The tests use synthetic files only and contain no Kobo firmware blobs.

## Safety

The verifier repairs nothing and writes nothing. Its only purpose is to establish whether a copied `recoveryfs` is coherent enough to be used as the source of a later local reconstruction.
