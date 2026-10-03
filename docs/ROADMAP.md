# PimpMyKobo-AuraHD — Roadmap

[Français](ROADMAP.fr.md) | **English**

Snapshot: 3 October 2026, `feat/rebuild-rootfs-spec`. Implemented code is distinguished from real-hardware qualification; none of the statuses below authorizes physical writes.

This roadmap keeps the project focused on one principle: **preserve first, modify only after the original device can be recovered**.

Status legend: **DONE** · **IMPLEMENTED** (hardware qualification pending where specified) · **IN PROGRESS** · **NEXT** · **PLANNED** · **EXPERIMENTAL**

## Current snapshot and next gates

| Milestone | Current evidence | Remaining gate |
|---|---|---|
| Legacy import | Implemented; actual pre-P1/P2 files qualified | Association remains declared; no native manifest fabricated |
| Full development-card backup | New read-only acquisition; full copy and second source read agree | Task-local acquisition is not the native backup tool |
| Offline P1 reconstruction | Actual image checked for filesystem, metadata, contents, links and hashes | Bootability untested |
| Full-image simulation | Actual backup copied; rebuilt P1 inserted; all regions outside P1 preserved | Local files only |
| Native Linux Live P1 executor | Implemented; synthetic failures and bounded writes tested | Hardware locking/ioctl, restore and boot qualification pending |
| Installable CLI | `pmkb` 0.1.0, local `.deb`, extracted launcher verified; 140 Linux tests and Linux/Windows CI | APT installation on the reference Live environment pending |
| Qt/PySide6 interface | Chosen direction after CLI; not implemented | First GUI should operate on local files and reuse existing contracts |

Next gates, in order:

1. Prepare a native Linux Live reference environment, validate CLI installation and access to evidence on persistent storage. Creating a Live USB also requires authorization before writing any physical support.
2. Identify the card explicitly and run the exclusive **read-only** full-target comparison. Refine/document the return-to-original-P1 procedure before the first write; automatic rollback is not implemented.
3. Review the exact target, P1 bounds and plan; obtain separate explicit human authorization. Only then perform the first bounded P1 restore, verify all preserved regions, and test boot on the Kobo. Failed or interrupted operations require review, not automatic retries.
4. Build the first Qt/PySide6 GUI for local evidence, reconstruction, simulation and reports. Reuse the CLI/backend checks; keep physical writing out of the first GUI. This local-only work can proceed while hardware qualification awaits the operator.
5. Integrate the native backup lane and qualify the end-to-end workflow on other Aura HD units; choose the project's own-code license before planning a public packaged release.
6. Start the liberation layer once the actual rescue and return-to-original workflow is proven.

See [CLI installation](cli-install-en.md), [local simulation](restore-rootfs-simulation-en.md) and [native Linux Live restore](restore-p1-linux-en.md).

## 1. Rescue and read-only inspection — DONE

Goal: understand an Aura HD E606C0 without modifying it.

- identify HWCONFIG v1.7 / PCB 28 / E606C0;
- parse and validate the MBR and P1/P2/P3 geometry;
- identify `rootfs`, `recoveryfs` and `KOBOeReader`;
- inspect physical media with read-only source access;
- validate factory recovery archives and E606C0 artifacts;
- expose read/access failures instead of silently treating them as a non-Kobo;
- support Windows sector-aligned reads;
- document host-OS write risks and preservation precautions;
- maintain synthetic tests and Linux/Windows CI.

The read-only foundation is qualified independently from future restore code.

## 2. Verified backup — IN PROGRESS

Goal: create a verifiable local copy before any physical write is authorized.

`backup-aura-hd` is developed separately from the rebuild work.

This branch already qualifies historical local files through an explicit `legacy/imported` contract. A complete backup of the development card was also acquired and reread using a task-local read-only acquisition script. Neither is a native `backup-aura-hd` manifest; native backup integration remains a separate gate.

V1 target:

- positively identify E606C0 before copying;
- save the pre-P1 boot/HWCONFIG area;
- save P1 `rootfs`;
- save P2 `recoveryfs`;
- make P3/user data opt-in because of its size;
- SHA-256 source ranges and destination files;
- produce `backup-manifest.json`;
- produce a stable target fingerprint independent of names such as `/dev/sdX` or `PhysicalDriveN`;
- never open the source for writing.

A backup is not considered usable merely because files were created: required components must be verified.

## 3. Offline rootfs rebuild — DONE for local construction

Goal: produce a new P1 image without touching physical media.

The local-files-only construction boundary is implemented and has been exercised on the actual recovery files. This proves local image construction, not successful boot.

Implemented checks and operations:

- validate the native backup contract or explicitly accept the separate qualified legacy contract;
- verify the local P2 copy against its recorded size and SHA-256;
- validate the recovery content;
- create a new P1 image with exactly the geometry recorded in the backup;
- safely extract the factory root filesystem without archive traversal;
- validate the resulting filesystem and file manifest;
- hash the final image;
- produce a `.rebuild.json` report with provenance and verification results.

`rebuild-rootfs` must reject physical/block-device paths. It has no authority to restore anything.

## 4. Rebuilt-image validation — DONE for offline checks

Goal: make a reconstructed image independently auditable before it can be written anywhere.

Implemented offline gates include:

- exact P1 size;
- filesystem structural check;
- expected content/manifests;
- critical permissions and links where applicable;
- SHA-256 of the final image;
- provenance back to the verified inputs; native fingerprint where applicable, explicit declared association for legacy inputs;
- explicit incomplete/failed states.

A historical SHA-256 from one successful manual rebuild is evidence, not a universal expected hash: filesystem metadata can legitimately make independently rebuilt images differ bit-for-bit.

The actual full-image simulation also preserves the boot prefix, P2, P3, gaps and trailing bytes. Legacy provenance and `physical_restore_eligible=false` remain unchanged. Bootability and P3 filesystem health are not qualified by these checks.

## 5. Guarded P1 restore — IMPLEMENTED; hardware qualification NEXT

Goal: restore only after backup, rebuild and validation are proven.

`restore-p1-linux.py` is isolated from earlier tools. Its default checks local files; its exclusive read-only device mode and physical write mode are separate. WSL/Windows physical access is refused. No physical restore has yet been performed in this development workflow.

Implemented constraints:

- no automatic disk selection;
- positively identify an Aura HD E606C0;
- recompute the entire target's SHA-256 before writing and require equality with the verified full backup;
- keep the legacy contract unchanged; record contemporary physical comparison and operator intent separately;
- verify expected MBR geometry and P1 bounds;
- default to P1 only;
- preserve pre-P1, P2 and P3 unless a future separately designed operation explicitly says otherwise;
- require explicit human confirmation containing target identity, operation and affected range;
- re-check the target after confirmation and immediately before the first write;
- abort on ambiguity or device change;
- write only the bounded P1 byte range;
- flush, reread and verify the written data;
- produce a restore report.

Additional Linux gates include whole removable USB media, unmounted partitions, no active swap/holders, native 64-bit Linux, kernel-exclusive access, persistent journal storage, a staged P1 checked read-only with e2fsck, durable original-P1 capture, durable write intent, cache invalidation and rereading the entire complement of P1. The confirmation token is bound to the reviewed plan SHA-256, with an explicit device and write operation.

Hardware behavior of exclusive locking/ioctl remains unqualified until an authorized Live operation. Original P1 and the full backup are retained for recovery, but automatic rollback is not implemented. A separate reviewed return procedure is required; no convenience bypass is planned.

No implementation should weaken these gates merely to make restoration easier.

## 6. Liberation layer — PLANNED

Goal: move from “recoverable Kobo” to a useful Aura HD whose software can be maintained without depending blindly on Kobo's historical recovery path.

Possible work includes:

- define what “liberated” means technically for E606C0;
- separate Kobo-proprietary material from redistributable PMKB tooling;
- make modifications reproducible from files legally obtained from the user's own device;
- preserve a documented route back to the verified original backup;
- evaluate alternative reader/user environments and boot-time customisation without sacrificing recovery.

This phase starts only after the restore safety model is proven on real hardware.

## 7. Reproducible rescue for other Aura HD units — PLANNED

Goal: make the project useful beyond the development device.

- FR/EN end-to-end documentation;
- device → inspect → backup → verify → rebuild → validate → guarded restore workflow;
- clear diagnostics for hardware variants and unsupported layouts;
- no publication of proprietary firmware, recovery images or dumps;
- tests remain synthetic and redistributable;
- recovery procedures remain useful even when the liberation layer is not wanted.

## 8. Installable CLI, Qt interface and retro extras

The `pmkb` CLI and local Debian/Ubuntu/WSL package are implemented. Installing the package does not access devices or run restoration. Qt/PySide6 is the next interface direction; no GUI has been implemented.

For the first GUI:

- select local evidence and display qualification status and provenance;
- invoke the existing local reconstruction and simulation operations;
- expose reports, errors and progress without rewriting safety logic;
- use the same command arguments and JSON contracts;
- exclude physical writes from the first version; their future UI needs separate design and hardware qualification.

Later refinements, once the core workflow is dependable:

- friendlier CLI progress and diagnostics;
- improve the GUI without duplicating device logic;
- PMKB visual identity and retro-themed presentation;
- optional Easter eggs such as Ikari Mode, kept completely outside safety-critical paths.

An Easter egg must never alter device detection, backup validation, fingerprints, restore confirmation or write boundaries.

## Architecture invariant

The intended pipeline is deliberately segmented:

```text
physical Aura HD
      |
      | read only
      v
inspect -> verified backup
                 |
                 | local files only
                 v
          offline rebuild
                 |
                 v
          image validation
                 |
                 | explicit guarded operation only
                 v
             P1 restore
```

**Backup → offline rebuild → validation → guarded write.**

There must never be a convenience path that silently collapses those stages into an unverified “fix my Kobo” write operation.

## Current development lanes

- Read-only inspection/recovery verification: qualified foundation.
- `backup-aura-hd`: separate native backup lane, not qualified on this branch.
- `rebuild-rootfs`: implemented local-only construction and offline validation.
- `restore-rootfs`: implemented local full-image simulator, no physical mode.
- `restore-p1-linux`: implemented separate native Live executor; hardware qualification and physical launch pending.
- `pmkb`: implemented installable CLI; Qt/PySide6 GUI planned.

Parallel development is welcome when branches do not weaken or bypass the interfaces and safety boundaries between these lanes.
