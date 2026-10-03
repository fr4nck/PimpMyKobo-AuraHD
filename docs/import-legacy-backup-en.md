# Import a historical backup

`tools/import-legacy-backup.py` qualifies two **local regular files**: the
complete pre-P1 prefix and a P2 image. It never mounts anything, opens a
physical device or modifies an image. It exclusively creates a new JSON
manifest, refusing to overwrite an existing file.

```bash
python3 tools/import-legacy-backup.py historical-boot.bin historical-p2.img legacy-import.json --expected-pre-p1-sha256 YOUR_HISTORICAL_PREFIX_SHA256 --expected-p2-sha256 YOUR_HISTORICAL_P2_SHA256 --declare-same-source
python3 tools/rebuild-rootfs.py legacy-import.json historical-p2.img new-rootfs.img --accept-legacy-import --json
# Add --build under Linux/WSL to construct a new local file.
```

Expected SHA-256 values must be lowercase hexadecimal historical records.
The importer compares them to today's files. `--declare-same-source` declares
their historical association; separate files cannot prove common origin.

The `pmkb-legacy-rebuild-v1` contract has `tool=import-legacy-backup`,
`provenance.kind=legacy/imported`, `status=qualified`, `complete=false` and
`qualified_for_rebuild=true`. It is not a native `backup-aura-hd` manifest
or a complete backup.

Checks: full file SHA-256, valid non-overlapping three-partition MBR with
Aura HD-compatible partition types, prefix length equal to P1 offset,
E606C0 HWCONFIG v1.7/39, P2 length equal to MBR size, ext4 superblock and
filesystem dimensions fitting inside P2. The manifest records block/inode
sizes and raw feature masks, including `needs_recovery` without hiding it.

P1/P3 geometry comes from the MBR; their contents remain **not qualified**.
Physical card capacity, original-source reread, common origin, filesystem
health and recovery artifacts are **not checked**. A readable superblock
does not prove a healthy recovery filesystem or a usable `fs.tgz`.

Image paths are relative to the manifest. Preserve their locations or import
again after moving files. The manifest is unsigned: hashes compare current
bytes with historical records, but do not authenticate provenance.

Rebuild refuses this contract without `--accept-legacy-import`. With opt-in,
it rereads the recorded prefix and supplied P2, recomputes qualifications
and compares them with the manifest. Construction retains all existing
`fs.tgz` archive/content/metadata checks, internal MD5 checks when present,
ext4 parameter checks and `e2fsck -f -n`. The final report retains provenance
limitations and `physical_restore_eligible=false`. No native target
fingerprint is produced. This import must never authorize physical restore.

Device paths, resolved aliases, UNC paths and non-regular inputs are refused.
Synthetic tests cover refusal cases, read-only input access and, on Linux,
end-to-end reconstruction preserving provenance.
