# `rebuild-rootfs` — V1 contract

Status: specification for the next tool. This stage never touches a microSD card or block device.

## Goal

Rebuild a local `rootfs` image from an already validated PMKB backup and `recoveryfs`. The tool only creates a new image file at an explicitly selected destination.

## Safety boundary

`rebuild-rootfs` rejects inputs resembling block devices (`/dev/...`, `\\.\PhysicalDriveN`). It never mounts, unmounts, formats or writes physical media and never invokes `dd`, `diskpart`, or a future restore tool.

The output is created under a temporary name and validated before rename. Existing files are never overwritten implicitly.

## V1 inputs

Required:

- a complete and consistent PMKB `backup-manifest.json`;
- a local P2 `recoveryfs` copy referenced by that manifest;
- an explicit local destination for the new P1 image.

Before construction the tool verifies the supported schema, E606C0 identity, P2 size and SHA-256, recorded P1 geometry, required recovery artifacts, and recovery validity using the same rules as `verify-recovery`.

No proprietary data is bundled with PMKB.

## New P1 size

The backed-up MBR geometry is authoritative. V1 output size must exactly match the P1 size recorded by the backup manifest. The 268,435,968-byte P1 observed on the development unit is reference evidence, never a validation constant.

## Construction

V1 creates an ext filesystem compatible with the device recovery and extracts `upgrade/fs.tgz` while preventing archive members from escaping the reconstructed root. Absolute or `..` member names, hard links leaving the archive, and any member that would be extracted *through* a symlink of the archive are rejected. Absolute or `..` symlink **targets** (for example `../../bin/busybox`) are normal in a rootfs: they are kept as-is and never followed during extraction.

### ext4 parameters (current Linux implementation)

- Filesystem parameters are **copied from the recovery image (P2) superblock**, written by the Kobo tools: exact ext4 feature list, block size and inode size. State flags (`needs_recovery`, `orphan_present`) are not copied.
- `mke2fs` runs with an empty configuration (`MKE2FS_CONFIG`) and `-O none,<list>`, so host defaults such as `metadata_csum` or `64bit`, which a 2.6.35 kernel cannot mount, cannot be added.
- The image is created at the exact P1 size. The filesystem uses `P1_size // block_size` blocks; the remainder (512 bytes on the studied unit) stays zero.
- After the build, the parameters are re-read with `dumpe2fs` and must equal the reference; the label must be `rootfs`.
- Extraction and `mke2fs -d` run in one `fakeroot` session, preserving numeric owners, modes (including setuid), links and device nodes without root privileges.
- The archive root directory owner is passed explicitly through `mke2fs -E root_owner=UID:GID`; otherwise mke2fs defaults to 0:0 even when the archive specifies another owner. Archives without a root entry retain the 0:0 default.

System-tool requirements (`mkfs.ext4`, loop mounting or a mount-free method) must be detected explicitly. Missing prerequisites cause a clean failure and can never trigger access to physical media.

## Output validation

A rebuild is `complete` only after:

1. exact image size;
2. ext4 parameters identical to the recovery reference, label `rootfs`;
3. `e2fsck -f -n` with no issue at all (exit 0);
4. a read-only, mount-free re-read of the image with `debugfs`. For **every** `fs.tgz` member: presence, type, mode, UID/GID, symlink target, device major/minor;
5. the content of **every** regular file and hard link compared by SHA-256 with `fs.tgz`; hard links must also share their target inode. Chained links are resolved within the archive, and dangling/cyclic/non-regular targets are refused;
6. verification against the `fs.md5sum` shipped inside `fs.tgz`, when present;
7. final image SHA-256;
8. writing the rebuild manifest `<output>.rebuild.json`, whose `checks` fields reflect the checks actually performed.

On any mismatch the image stays under its temporary `.part` name, is never renamed, and the result is `failed`.

The historical SHA-256 `ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C` is evidence from the manual rebuild, not an expected value.

## Rebuild manifest

Proposed name: `rebuild-manifest.json`.

V1 fields: `schema_version`, `tool`, `created_utc`, `status` (`ok`, `incomplete`, `failed`), `backup_manifest_sha256`, unchanged `source_fingerprint`, `device`, `rootfs_size`, `rootfs_sha256`, `recovery_sha256`, `checks.filesystem`, `checks.manifest`, `checks.size`, `warnings`, and `errors`.

A local path is not persistent identity.

## Contract with future restore

A future restore tool must not trust the rebuilt-image SHA alone. It must independently match the target medium against the backup `source_fingerprint`.

`rebuild-rootfs` defines no rule authorizing physical writes; that decision belongs exclusively to a future `restore-rootfs`.

[Legacy imports](import-legacy-backup-en.md) are accepted only with `--accept-legacy-import` for local reconstruction. Their declared association and `physical_restore_eligible=false` are retained in the result.

## Minimum tests before usable implementation

Tests must cover rejection of `/dev/sdX` and `\\.\PhysicalDriveN`, bad/unsupported/incomplete manifests, wrong E606C0 identity, missing or mismatched P2, corrupt/traversing recovery archives, destination collisions, insufficient space, interrupted temporary output, exact image size, filesystem and manifest checks, stable JSON, Unicode/space paths, a mechanical no-write-to-input guard, and Linux/Windows CI. Tests requiring a real ext4 environment must remain separate from portable unit tests.
