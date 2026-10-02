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

V1 creates an ext filesystem compatible with the device recovery and extracts `upgrade/fs.tgz` while preventing archive members from escaping the reconstructed root. Absolute paths, `..`, links or equivalent traversal are rejected.

System-tool requirements (`mkfs.ext4`, loop mounting or a mount-free method) must be detected explicitly. Missing prerequisites cause a clean failure and can never trigger access to physical media.

## Output validation

A rebuild is `complete` only after exact image-size validation, non-destructive filesystem checking, applicable `fs.md5sum` content verification, final image SHA-256, and creation of a rebuild manifest.

The historical SHA-256 `ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C` is evidence from the manual rebuild, not an expected value.

## Rebuild manifest

Proposed name: `rebuild-manifest.json`.

V1 fields: `schema_version`, `tool`, `created_utc`, `status` (`ok`, `incomplete`, `failed`), `backup_manifest_sha256`, unchanged `source_fingerprint`, `device`, `rootfs_size`, `rootfs_sha256`, `recovery_sha256`, `checks.filesystem`, `checks.manifest`, `checks.size`, `warnings`, and `errors`.

A local path is not persistent identity.

## Contract with future restore

A future restore tool must not trust the rebuilt-image SHA alone. It must independently match the target medium against the backup `source_fingerprint`.

`rebuild-rootfs` defines no rule authorizing physical writes; that decision belongs exclusively to a future `restore-rootfs`.

## Minimum tests before usable implementation

Tests must cover rejection of `/dev/sdX` and `\\.\PhysicalDriveN`, bad/unsupported/incomplete manifests, wrong E606C0 identity, missing or mismatched P2, corrupt/traversing recovery archives, destination collisions, insufficient space, interrupted temporary output, exact image size, filesystem and manifest checks, stable JSON, Unicode/space paths, a mechanical no-write-to-input guard, and Linux/Windows CI. Tests requiring a real ext4 environment must remain separate from portable unit tests.
