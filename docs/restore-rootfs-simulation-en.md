# Local P1 replacement simulation

`tools/restore-rootfs.py` V1 accepts **local regular files only**. It never
restores physical media, mounts anything or runs disk commands. Its default
mode validates inputs and prints a JSON plan without creating files.
`--simulate` creates a **new copy** of the local disk image and replaces P1
in that copy. All source files remain read-only.

```bash
python3 tools/restore-rootfs.py legacy-import.json rootfs.img.rebuild.json rootfs.img disk-source.img disk-simulation.img --accept-legacy-import
# Add --simulate after a ready plan to create the copy.
```

Inputs are the explicit legacy manifest and its referenced prefix/P2 files,
the P1 and its `rebuild-rootfs` or `build-koreader-rootfs` report, a complete
local disk image and a new output path.
Native backup manifests are not supported by this first contract. Devices,
Windows PhysicalDrive/UNC paths, resolved device aliases and non-regular
inputs are rejected. There is no physical mode or bypass option.

The simulator rereads legacy evidence and checks target MBR geometry, bounds
within the disk-image size, E606C0 HWCONFIG, and pre-P1/P2 hashes. It verifies
P1 length/hash, the report's reference to the legacy manifest, provenance
and complete reported checks. For `build-koreader-rootfs`, it requires the
typed E606C0 contract (P1 size/hash, `complete=true`, no errors,
`physical_restore_eligible=false`, `hardware_qualified=false`) and reruns
`e2fsck -f -n` read-only on the local image. Reports are unsigned: consistency
is checked, but report authenticity and bootability are not proven.

After copying and replacing P1, it rereads its bytes and compares hashes of
pre-P1, P2, P3 and **the entire suffix after P1**, including gaps and trailing
bytes. Output length and the original disk-image hash must remain correct.
The resulting plan records the producer tool and report hash in
`candidate_source`; the Live backend accepts only the two explicit producer
contracts and checks the candidate against the plan. The plan retains
`write_authorized=false` and `physical_restore_eligible=false`. Provenance and
`physical_restore_eligible=false` are retained. Preserving P3
bytes does not otherwise qualify their contents.

The full logical disk-image size must fit on the destination, even for a
sparse input. Existing output, `.part` or `.simulation.json` paths cause
refusal. Copy/verification failures retain at most an unqualified `.part`.
Publication without overwriting requires hard-link support on the output
filesystem. A report publication failure after image publication returns
`failed`; the published image passed byte checks, but the JSON result must
be retained before using it.

Success creates the image and `<output>.simulation.json`. It never
authorizes physical restore. Synthetic tests cover refusal, corruption,
source changes, insufficient space and read-only inputs; Linux integration
exercises an actual synthetic import → ext4 rebuild → disk-image simulation.

Separate prefix/P1/P2 backups are not a complete historical disk image:
P3 contents and actual card capacity are unverified. A synthetic demo must
be labeled accordingly, never treated as a real backup with invented P3.

For PMKB candidates, actual ext4 parameters are compared with the typed producer report and preserved recovery reference before read-only e2fsck. The prepared plan binds `simulation_sha256` to the whole simulated image, records the filesystem validation and retains `write_authorized=false`. Sealing checks the exact plan SHA-256; it does not grant physical write approval.
