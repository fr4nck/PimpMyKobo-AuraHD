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

Required entry points, checked after assembly: `etc/init.d/rcS`, `etc/inittab`, `usr/bin/pmkb-check-offline`, `usr/bin/pmkb-check-onboard`, `usr/bin/pmkb-reader`, `bin/kobo_config.sh`, `opt/koreader/reader.lua`, `opt/koreader/luajit`.

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

## Real input contract (for whoever runs `--build` on Linux/WSL2)

This tool performs no ELF/ABI validation itself (that is `audit-arm-runtime`'s job, see below) and does not fetch or redistribute anything; it only merges whatever local files it is pointed at. Concretely:

- **`koreader_dir` structure.** Pass the directory whose immediate contents are what should land at `/opt/koreader` — typically the `koreader/` directory *inside* an extracted official `koreader-kobo-vX.Y.Z` release archive, not the archive's own top-level wrapper directory. At minimum it must contain `reader.lua` and an ARM `luajit` binary (the two required entry points under `opt/koreader/`); in practice a real release also brings `libs/` (bundled shared libraries) and Lua sources, all of which are copied through unchanged.
- **Expected architecture.** The target kernel is ARM (i.MX50, Aura HD/`dragon`), so `luajit` and every `.so` under `libs/` must be ARM ELF32 little-endian. This tool does not check that — it copies bytes as given. `audit-arm-runtime` is the static ELF/ARM check; run it against this tool's assembled output (or, once `--build` exists end to end, before `--build`) and treat a `build-koreader-rootfs` success alone as **not** proof of ARM compatibility.
- **`runtime_dir` structure.** Also a plain directory, merged at the rootfs root exactly like `koreader_dir` is merged under `opt/koreader/`: whatever relative path a file has under `runtime_dir` is the path it gets in the final tree (so `runtime_dir/bin/busybox` becomes `/bin/busybox`). There is no required layout beyond "do not collide with the overlay's own `bin/`, `etc/`, `usr/bin/` files" (see the collision rule above) and "provide what BusyBox/libc `luajit`/KOReader actually need to run", which this tool does not enumerate or verify.
- **Potentially necessary Kobo-origin components.** The project's current position (see [offline liberation](offline-liberation-en.md)) is that a BusyBox binary and a small, explicitly selected set of GNU/libc shared libraries extracted from the user's own backup may be necessary for V1, because no fully from-source replacement exists yet. Nothing wider than that is assumed necessary; do not add Kobo files to `runtime_dir` "just in case". Whatever is added must be locally extracted by the operator — **never committed to this repository and never fetched by this tool.**
- **Refusing unnecessary Nickel components.** `runtime_dir` and `koreader_dir` should contain only what KOReader/BusyBox actually need to run `reader.lua` against `/mnt/onboard` — not Nickel binaries, Nickel's Lua modules, `nickel_conf.lua`, or Nickel's own configuration file. The bounded scan above exists specifically to catch an accidental inclusion of this kind; a hit should be treated as "remove this from `runtime_dir`/`koreader_dir` and rebuild", not silently ignored.
- **Missing dynamic dependency.** This tool has no concept of a "missing dependency" — if a `.so` a binary needs is absent from `runtime_dir`/`koreader_dir`, assembly still succeeds (the missing file is simply not there) and, Linux-only, `--build` still produces an image. **Detecting that is exactly what `audit-arm-runtime`'s `DT_NEEDED` resolution against `/opt/koreader/libs`, `/lib`, `/usr/lib` is for** (see its own doc); it reports `missing or invalid ARM dependency <name>` for exactly this case. Never treat a `build-koreader-rootfs` success as proof that KOReader can actually load.

## Relationship to other in-flight work, and the confirmed chain

`build-koreader-rootfs` (this tool) → the directory it assembles → `audit-arm-runtime --check-bootstrap --check-storage` (ELF/dependency/bootstrap/storage audit) → `preflight-koreader` (aggregator) is meant to work as one chain, each stage reading the previous stage's local output, none of them executing anything or touching a device. This was verified end to end in a local-only scratch merge of this branch with `feat/audit-arm-runtime` at `908b2a1` (not pushed, not merged into either real branch — the worktree was discarded after verification):

- [`feat/rebuild-rootfs-spec`](rebuild-rootfs-spec-en.md) already produced `experimental/offline-rootfs` (the init/launch overlay this tool consumes) and the [offline hardware audit](offline-hardware-audit-fr.md) documenting what remains unqualified (framebuffer preparation, touch/light device nodes, battery, suspend, USB). This tool does not re-derive or contradict that audit; it only gives the prototype a reproducible, verifiable path to an actual image file.
- `feat/audit-arm-runtime`'s `tools/audit-arm-runtime.py` runs unmodified against a directory this tool materializes (via `--build`'s temporary tree, or by calling `plan_rootfs`'s underlying `_copy_tree(..., write=True)` directly) — confirmed mechanically: `--check-storage` correctly reports `/mnt` and `/mnt/onboard` as real directories (not symlinks) on a synthetic assembled tree, and `--check-bootstrap` (POSIX-only) reads the same required entry points this tool enforces.
- Its `preflight-koreader.py` aggregator already calls this tool's `_copy_tree`/`_scan_for_nickel` directly on the already-merged tree when `build-koreader-rootfs.py` is present alongside it (its own doc says so explicitly). **That reproduced a permanent false positive** in the scratch verification: the overlay's own `usr/bin/pmkb-reader` comment ("bypassing ... Nickel paths") is indistinguishable from external content once merged, so every real build would fail `nickel_signatures`. `scan_tree_for_nickel(root)` is the fix — a new, stable, public entry point in this tool meant specifically for a *post-merge* directory, which excludes the overlay's own files from content scanning by recomputing them from `experimental/offline-rootfs` rather than from pre-merge provenance. Re-running the patched call locally confirmed `nickel_signatures` goes from a permanent `FAIL` to `PASS` on a clean synthetic build, and still correctly `FAIL`s when an external file is made to reference Nickel. **`feat/audit-arm-runtime` has not adopted this yet** (not this tool's branch to change); its `nickel()` helper in `tools/preflight-koreader.py` should switch from `builder._copy_tree(...)`/`builder._scan_for_nickel(...)` to `builder.scan_tree_for_nickel(root)` on its own next sync.
- `build-koreader-rootfs` deliberately does not duplicate ELF parsing or dependency resolution — see the input contract above for exactly which gap `audit-arm-runtime` fills.

## Bootstrap defects found by `audit-arm-runtime --check-bootstrap`/`--check-storage`, and their fix here

That audit (documented in `docs/audit-arm-runtime-fr.md`) found three concrete gaps in the `experimental/offline-rootfs` prototype itself, reviewed and fixed in this tool's branch rather than left as a documented limitation:

1. the four launch scripts were tracked as `100644` in git. This tool already forced `0755` on every overlay file it copies (`force_mode=0o755`), so its own output was never affected — but a raw checkout of the overlay, bypassing this tool, would not be executable. Fixed directly in the git index (`git update-index --chmod=+x`) as a defense-in-depth complement, not a replacement, for the existing `force_mode`.
2. `rcS` mounted `/mnt/onboard` without creating it; only this tool's skeleton-directory guarantee (`SKELETON_DIRS` includes `mnt`/`mnt/onboard`) made that safe. `rcS` now also runs `mkdir -p /mnt/onboard` itself, so a differently assembled rootfs (not built by this tool) still mounts correctly.
3. `pmkb-reader` only checked `/run/pmkb-ready` (set once, during `rcS`), so a mount lost between the `sysinit` and `once` init stages would go undetected and KOReader would launch against a stale/empty `/mnt/onboard`. A new guard, `usr/bin/pmkb-check-onboard` (same shape as the existing `pmkb-check-offline`: read-only, refuses on a missing/unreadable mounts table, an injectable path argument for tests), re-verifies the mount via `/proc/mounts` immediately before `pmkb-reader` executes KOReader. This is now a required entry point.

## Minimum tests before a real hardware trial

Covered by `tests/test_build_koreader_rootfs.py`: device-path and non-directory rejection, required-entry-point detection, file/symlink collisions across sources, legitimate directory merges, the bounded Nickel scan both pre-merge (`plan_rootfs`, by path and by content, including the overlay-exclusion case) and post-merge (`scan_tree_for_nickel`, including the overlay-false-positive regression case above), JSON stability, non-Linux backend short-circuiting, and existing-output refusal — all without any Linux-only tool. `tests/test_offline_guard.py` adds a runtime test for the new `pmkb-check-onboard` guard and static ordering checks (`mkdir` before `mount`; guard before `exec`) on the overlay sources themselves, without executing `rcS`/`pmkb-reader` (still root/hardware-dependent). A Linux-gated test (`BuildRootfsLinuxBuildTests`) exercises the real `fakeroot`/`mke2fs`/`e2fsck`/`debugfs` path end-to-end with synthetic fixtures — confirmed passing on Ubuntu CI; it still needs to be repeated against a real extracted KOReader release and real local runtime components before any hardware trial.
