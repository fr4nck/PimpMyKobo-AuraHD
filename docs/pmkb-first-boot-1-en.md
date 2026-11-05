# PMKB FIRST BOOT #1 — convergence state

[Français](pmkb-first-boot-1-fr.md) | **English**

Status as of 3 October 2026, branch `integration/pmkb-first-boot-1`. This document qualifies no hardware boot. No physical write, no `/dev`, no `PhysicalDrive`, no P2/recoveryfs modification happened in this batch.

## Origin

Three parallel lanes converge here, each on its own branch, none merged into `main`:

- `feat/build-koreader-rootfs` (`1b7c532`): `build-koreader-rootfs`, the direct-KOReader rootfs assembler/builder.
- `feat/audit-arm-runtime` (`908b2a1`): `audit-arm-runtime` (ELF/bootstrap/storage audit) and `preflight-koreader` (aggregator).
- `feat/rebuild-rootfs-spec` (`235085e`): Nickel-free hardware-interface audit (E-Ink, Neonode v2 touch, frontlight) and a proposed Nickel-independent KOReader settings profile.

`integration/pmkb-first-boot-1` merges all three (cherry-pick of `235085e`, merge of `feat/audit-arm-runtime`) then fixes the gaps found by Codex's real Linux build.

## 1. Corrections carried over from Codex's local integration commit

| Fix | Where | Detail |
| --- | --- | --- |
| `$ORIGIN` resolution in RPATH/RUNPATH | `tools/audit-arm-runtime.py` | The audit used to refuse *any* RPATH/RUNPATH outright. `resolve_rpath()` now expands `$ORIGIN`/`${ORIGIN}` to the directory containing the ELF (within the guest rootfs), accepts token-free absolute entries, and explicitly refuses `$LIB`/`$PLATFORM` and any relative path still ambiguous after expansion. Resolved directories are added, per-ELF, ahead of the three default directories (`/opt/koreader/libs`, `/lib`, `/usr/lib`). |
| `/usr/bin/pmkb-check-onboard` missing from the bootstrap contract | `tools/audit-arm-runtime.py` (`BOOT_SCRIPTS`) | This script (added in the previous batch) wasn't covered by `--check-bootstrap`. It now is: execute bit and `#!/bin/sh` shebang checked like the other scripts. |
| `defaults.custom.lua` missing from the bootstrap contract | `tools/audit-arm-runtime.py` (`BOOT_DATA_FILES`) | Checked like `reader.lua`: presence and non-emptiness, no ELF/shell validation. |
| Permanent false-positive Nickel scanner | `tools/preflight-koreader.py` (`nickel()`) | Called the builder's `_copy_tree`/`_scan_for_nickel` directly on the already-merged tree, which can no longer distinguish the overlay from its own content — every real build failed `nickel_signatures` because of `pmkb-reader`'s "bypassing ... Nickel paths" comment. Fixed by calling `scan_tree_for_nickel(root)`, the builder's public entry point built for exactly this case (already prepared in the previous batch, now actually adopted). |

All four fixes are now in the code, tested, not only in an unversioned local build.

## 2. Nickel findings: classification

Extending `235085e`'s own audit table (`docs/offline-hardware-qualification-fr.md`):

| Path | Category | Verdict |
| --- | --- | --- |
| `KOBO_LIGHT_ON_START=-2` default → `_syncKoboLightOnStart()` → `NickelConf.frontLightLevel` | **Real Nickel dependency** | Actually executed file access on normal startup unless disabled; the fallback setter can fail (`assert`) against a read-only P3. **Fixed**: `KOBO_LIGHT_ON_START=-1` in `defaults.custom.lua`, now installed by the builder (section 3). |
| `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=true` default → `saveSettings()` | **Real Nickel dependency** | Same: actually executed file access. **Fixed**: `false` in the same file. |
| `require(device/kobo/nickel_conf)` | **Dormant KOReader compatibility** | Loads function definitions; no file access as long as the two settings above avoid the call-flows that invoke them. |
| `usr/bin/pmkb-reader`'s comment ("bypassing ... Nickel paths") | **Informational first-party finding** | Text explaining Nickel is *avoided*; no file access. It remains visible but non-blocking; first-party origin is recognized only when its SHA-256 matches the checkout. |
| `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL` inside `defaults.custom.lua` itself | **Informational first-party finding** | The "NICKEL" key stays visible. The file is marked `first_party_verified` only when its SHA-256 matches the checkout; `true` or a missing safe override is blocking. |
| `bin/kobo_config.sh` marker, `PRODUCT=dragon` | **Dormant KOReader compatibility, not a Nickel dependency** | Real hardware detection, but a PMKB-owned file; "Kobo" in a backend name does not mean Nickel. |
| `invertPageTurnButtons`, `external_keyboard_otg_mode_on_start`, `dbg.lua`, `ffi/rtc.lua` | **Comment/string without impact** | Documentation or comparison; none of the call-flows `235085e` analyzed connect them to a real Nickel access on the normal boot path. |
| KOReader's usual shell launcher (Nickel return, KFMon, screen restore) | **Dormant KOReader compatibility** | `pmkb-reader` calls `reader.lua` directly, never this launcher; its exit code path is never reached. |

**Conclusion: with `defaults.custom.lua` installed (section 3), no Nickel dependency is necessary on the normal boot path.** Demonstrated by `tests/offline-audit/nickel-settings.lua` (a real call-flow against the verified KOReader package's `powerd.lua`/`nickel_conf.lua`/`luadefaults.lua`/`defaults.lua`, intercepting every Nickel file open — zero access observed with the two settings) and by scanner classification: compatibility signatures remain visible, while a clean synthetic build has no blocking finding.

## 3. Integrating the demonstrated-necessary KOReader setting

`experimental/offline-audit/defaults.custom.lua` (`235085e`'s proposal, until now not installed anywhere) is now copied by the builder to `opt/koreader/defaults.custom.lua` in every assembled tree — before `koreader_dir` is merged, so a KOReader package that already ships this file collides explicitly instead of silently overriding this safety setting. It is now a required entry point (`REQUIRED_ENTRYPOINTS`), checked by `audit-arm-runtime --check-bootstrap` (presence and non-emptiness) and identified as first-party only by SHA-256 equality; its Nickel references remain visible and informational while the two safe overrides are present.

Nothing else from `235085e` (the E-Ink/touch/frontlight audit, the `offline-audit` tests) is integrated into the build: not demonstrated necessary for a first software boot, reserved for future hardware qualification.

## 4. Definitive verification (mission item 4)

| Item | State | Evidence |
| --- | --- | --- |
| Bootstrap scripts executable | **Done** (previous batch, reconfirmed) | Execute bit set directly in the git index (`100755`) for the 4 scripts plus the new `pmkb-check-onboard`, as defense-in-depth alongside the builder's `force_mode=0o755`. `inittab` stays `100644` (data, not a script). |
| `/mnt` and `/mnt/onboard` created | **Done** (previous batch, reconfirmed) | Builder's `SKELETON_DIRS` plus `mkdir -p /mnt/onboard` in `rcS` itself (defense in depth). |
| P3 re-verified immediately before launch | **Done, strengthened this batch** | `pmkb-check-onboard` is now the **last instruction before `exec`** in `pmkb-reader` (moved past `cd /opt/koreader`): nothing intervenes anymore. It reads `/proc/mounts`, a **live** kernel view, not a static marker like `/run/pmkb-ready` — exactly what closes the identified gap: an unmount between `rcS` and `pmkb-reader` is now detected, not only one before `rcS`. A stronger check (parent/child device-id comparison) was considered and dropped: it would not be testable with synthetic fixtures (no real distinct mount possible without hardware), for marginal gain over an already-live kernel view. |
| `$ORIGIN` correctly handled | **Done this batch** | Section 1. Tested: successful resolution, confinement to the ELF's own directory, refusal of `$LIB`/`$PLATFORM`, refusal of a relative path without `$ORIGIN`. |
| No Nickel dependency necessary on the normal boot path | **Demonstrated** | Section 2. |

## 5. Convergence: `build-koreader-rootfs` → `audit-arm-runtime` → `preflight-koreader`

Verified mechanically on this branch (the three tools genuinely coexist now, no scratch worktree needed):

1. `build-koreader-rootfs` assembles `experimental/offline-rootfs` + `experimental/offline-audit/defaults.custom.lua` + a local KOReader release + local runtime components into one directory.
2. `audit-arm-runtime --check-bootstrap --check-storage` audits that directory without modifying it: ARM ELF/dependencies (with `$ORIGIN` resolution), launch-file permissions/scripts (including the two new files), `/mnt`/`/mnt/onboard` structure.
3. `preflight-koreader` aggregates these results plus the now-correct Nickel scanner, with per-check and overall `PASS`/`FAIL`/`UNQUALIFIED` verdicts.

The preflight strictly keeps the three verdicts distinct: a hardware check (`framebuffer`, `touch`, `frontlight`, `p3_mount`, `usb_calibre`, `hardware_boot`) always stays `UNQUALIFIED` — that dictionary was not touched in this batch and structurally cannot become `PASS` without a separate hardware trial.

## 6. Exact Linux reconstruction

On Debian/WSL, with `fakeroot`, `e2fsprogs`, a verified local copy of P2 (`recoveryfs`), an extracted KOReader release (the directory directly containing `reader.lua`/`luajit`/`libs/`) and a directory of local, never-committed runtime components:

```bash
# 1. Experimental P1 image (Linux-only); 268,435,968 bytes is this
#    development unit's reference P1 size — use the size actually recorded
#    in your own backup-manifest.json if different.
python3 tools/build-koreader-rootfs.py \
    /path/to/koreader-vX.Y.Z/koreader \
    /path/to/aura-hd-runtime \
    --build PMKB-FIRST-BOOT-1.img \
    --reference-recovery /path/to/p2-recoveryfs.img \
    --size 268435968 \
    --json > PMKB-FIRST-BOOT-1.koreader-build.json

# 2. The same tree, materialized separately for full static audit
#    (step 1's temp directory is cleaned up on success; this reuses the
#    same public/internal functions, no new tool).
python3 - <<'PY'
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("builder", "tools/build-koreader-rootfs.py")
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
koreader = Path("/path/to/koreader-vX.Y.Z/koreader")
runtime = Path("/path/to/aura-hd-runtime")
dest = Path("PMKB-FIRST-BOOT-1-tree")
dest.mkdir()
manifest = {}
builder._copy_tree(builder.OVERLAY_ROOT, dest, manifest, {}, write=True, force_mode=0o755)
builder._add_skeleton_dirs(manifest, dest, write=True)
builder._place_reader_profile(dest, manifest, write=True)
builder._copy_tree(koreader, dest, manifest, {}, base="opt/koreader", write=True)
builder._copy_tree(runtime, dest, manifest, {}, write=True)
print("materialized:", dest)
PY

# 3. Full static audit (ELF/bootstrap/storage) on that tree
python3 tools/pmkb.py audit-arm-runtime PMKB-FIRST-BOOT-1-tree --check-bootstrap --check-storage

# 4. Aggregated preflight — status must not be FAIL (UNQUALIFIED expected
#    for every hardware item, never PASS)
python3 tools/pmkb.py preflight-koreader PMKB-FIRST-BOOT-1-tree
```

Built to be reproducible: step 1's output includes the final image SHA-256 and the ext4 parameters actually used, in `PMKB-FIRST-BOOT-1.img.koreader-build.json`.

## Reminder of what is forbidden

None of the steps above write to a physical device, a `/dev`, a `PhysicalDrive`, or modify P2/recoveryfs. No hardware trial is proposed by this document. The next hardware GO stays subordinate to a joint review of the real Linux result and a separate explicit authorization.
