# `build-koreader-rootfs` — V1 contract

[Français](build-koreader-rootfs-spec-fr.md) | **English**

Status: implemented for local assembly and offline validation; the Linux-only `--build` ext4 construction path has unit tests gated on a native Linux/WSL2 e2fsprogs+fakeroot backend and has not yet been exercised against a real KOReader release or real Kobo-origin runtime components. No physical write exists anywhere in this tool.

## Goal

Assemble, and optionally build, a local experimental P1 image that boots directly into KOReader on Aura HD E606C0, without Nickel in the normal startup path:

`Netronix boot -> kernel -> this rootfs -> KOReader`

This is distinct from [`rebuild-rootfs`](rebuild-rootfs-spec-en.md), which reconstructs the *factory* Kobo rootfs from a verified backup. `build-koreader-rootfs` never reads `fs.tgz` or any backup manifest; it only merges local, explicitly provided inputs.

## Inputs (all local; never a device)

1. `koreader_dir` — a locally extracted KOReader Kobo release. Its contents land under `/opt/koreader` in the assembled tree (so pass the directory that directly contains `reader.lua`, `luajit`, `libs/`, etc.).
2. `runtime_dir` — a local directory of additional runtime components merged at the rootfs root (for example a BusyBox binary and shared libraries extracted from the user's own Kobo backup). **This directory is never committed to the repository.** Its provenance, license and redistributability are the operator's responsibility; see [the offline liberation notes](offline-liberation-en.md).
3. The repository's own `experimental/offline-rootfs` overlay (init, inittab, the device-probe marker, the offline/network guard, the KOReader launch wrapper) is merged in automatically; it is not a CLI argument.
4. For `--build` only: `--reference-recovery` (a local P2 `recoveryfs` image providing the authoritative ext4 layout, exactly as in `rebuild-rootfs`) and `--size` (the exact output P1 size in bytes).

## Safety boundary

`build-koreader-rootfs` rejects any input or output path that looks like a block device (`/dev/...`, `\\.\PhysicalDriveN`). It never mounts, formats or writes physical media. The output image is created under a temporary `.part` name and only renamed into place after every check below passes; an existing output file or build manifest is never overwritten implicitly.

## Assembly (`plan_rootfs`, cross-platform, read-only on its inputs)

The assembly step merges three sources into one manifest, keyed by rootfs-relative path, without requiring any Linux-only tool:

1. the overlay (forced to mode `0755`, since repository-tracked executable bits are not reliable on every checkout);
2. baseline mount-point directories (`proc`, `sys`, `dev`, `dev/input`, `dev/pts`, `run`, `tmp`, `mnt`, `mnt/onboard`, `opt`, `opt/koreader`) so the tree is complete even from a sparse KOReader/runtime input;
3. `koreader_dir`, placed under `opt/koreader`;
4. `runtime_dir`, placed at the root.

Directories may be contributed by more than one source (for example `etc/` from both the overlay and `runtime_dir`) and are merged. A file or symlink may never replace anything already placed by an earlier source; any such collision fails the whole assembly with no partial output. Symlinks are recorded with their raw target and never followed or rewritten, matching `rebuild-rootfs`'s philosophy for archive symlinks: absolute or `..` targets are normal inside a rootfs (BusyBox applets, versioned `.so` links) and are kept as-is.

Required entry points, checked after assembly: `etc/init.d/rcS`, `etc/inittab`, `usr/bin/pmkb-check-offline`, `usr/bin/pmkb-reader`, `bin/kobo_config.sh`, `opt/koreader/reader.lua`, `opt/koreader/luajit`.

### Nickel-reference scan

A best-effort, bounded heuristic flags anything that looks like an unintended dependency on the Nickel/Kobo userspace:

- any manifest path whose name matches `nickel`, `hindenburg` or `kobo ereader.conf` (case-insensitive);
- any regular file of 2 MiB or less, sourced from `koreader_dir` or `runtime_dir` only, whose content contains `Nickel`, `Hindenburg`, `nickel_conf`, `/usr/local/Kobo` or `KoboRoot.tgz`.

The repository's own overlay is excluded from the content scan (but not from the path-name scan): its source is already reviewed in this repository, and its comments may legitimately *describe* bypassing Nickel without depending on it. A hit means "look at this before trusting the image", not an automatic proof of a problem; it is also not a proof of absence when there is no hit. Every hit is reported in `nickel_scan`.

## Construction (`--build`, Linux-only)

Reuses `rebuild-rootfs`'s ext4 helpers rather than re-implementing them:

- ext4 feature list, block size and inode size come from `--reference-recovery`'s superblock (`dumpe2fs -h`), exactly as in `rebuild-rootfs`; `mke2fs` runs with an empty `MKE2FS_CONFIG` and `-O none,<list>` so host defaults such as `metadata_csum` or `64bit` can never be added;
- the image is created at the exact requested `--size`; the filesystem uses `size // block_size` blocks, the remainder stays zero;
- the assembled tree is materialized into a temporary directory, `chown -R 0:0`'d and passed to `mke2fs -d` inside one `fakeroot` session (own/mode fidelity for `koreader_dir`/`runtime_dir` content therefore depends on their *source* filesystem already carrying correct POSIX permissions — this only works reliably when the inputs were extracted on Linux/WSL2, not assembled from a Windows-side dry run);
- per-file ownership beyond uniform `root:root` is not yet supported; this is recorded in the report as `owner_policy` and must be revisited if a future component needs a non-root owner.

## Output validation

A build is `experimental` (never `complete`/qualified in the hardware sense) only after:

1. exact image size;
2. ext4 parameters identical to the recovery reference, label `rootfs`;
3. `e2fsck -f -n` with no issue at all (exit 0);
4. a read-only, mount-free re-read of the image with `debugfs` for every manifest entry: presence, type, mode (symlinks excluded) and, for symlinks, fast-link target;
5. the content of every regular file compared by SHA-256 against the value computed during assembly;
6. a `<output>.koreader-build.json` report, with `status=experimental`, `complete=true`, `physical_restore_eligible=false`, `hardware_qualified=false`, final image SHA-256, and the ext4 parameters actually used.

On any mismatch the image stays under its temporary `.part` name and the result is `failed`.

## Relationship to other in-flight work

- [`feat/rebuild-rootfs-spec`](rebuild-rootfs-spec-en.md) already produced `experimental/offline-rootfs` (the init/launch overlay this tool consumes) and the [offline hardware audit](offline-hardware-audit-fr.md) documenting what remains unqualified (framebuffer preparation, touch/light device nodes, battery, suspend, USB). This tool does not re-derive or contradict that audit; it only gives the prototype a reproducible, verifiable path to an actual image file.
- `feat/audit-arm-runtime` (a separate, parallel branch) performs a read-only static ELF/ARM/dynamic-linker audit of an extracted rootfs directory. `build-koreader-rootfs` deliberately does not duplicate ELF parsing: once that branch lands, its audit should run against the directory this tool assembles (before `--build`) as an additional offline gate, in place of (not instead of) the content-based Nickel scan above, which looks at non-ELF text rather than ELF dependency graphs.

## Minimum tests before a real hardware trial

Covered by `tests/test_build_koreader_rootfs.py`: device-path and non-directory rejection, required-entry-point detection, file/symlink collisions across sources, legitimate directory merges, the bounded Nickel scan (by path and by content, including the overlay-exclusion case), JSON stability, non-Linux backend short-circuiting, and existing-output refusal — all without any Linux-only tool. A Linux-gated test (`BuildRootfsLinuxBuildTests`) exercises the real `fakeroot`/`mke2fs`/`e2fsck`/`debugfs` path end-to-end with synthetic fixtures; it still needs to be run on a native Linux/WSL2 host (this development checkout is Windows-only) and, before any hardware trial, repeated against a real extracted KOReader release and real local runtime components.
