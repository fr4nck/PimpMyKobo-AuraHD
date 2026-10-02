# PimpMyKobo-AuraHD — Roadmap

This roadmap keeps the project focused on one principle: **preserve first, modify only after the original device can be recovered**.

Status legend: **DONE** · **IN PROGRESS** · **NEXT** · **PLANNED** · **EXPERIMENTAL**

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

Goal: create a verifiable local copy before any destructive feature exists.

`backup-aura-hd` is developed separately from the rebuild work.

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

## 3. Offline rootfs rebuild — IN PROGRESS

Goal: produce a new P1 image without touching physical media.

Current work establishes a local-files-only boundary and validates the backup contract before construction.

Next implementation steps:

- consume a complete `backup-manifest.json`;
- verify the local P2 copy against its recorded size and SHA-256;
- validate the recovery content;
- create a new P1 image with exactly the geometry recorded in the backup;
- safely extract the factory root filesystem without archive traversal;
- validate the resulting filesystem and file manifest;
- hash the final image;
- produce `rebuild-manifest.json`.

`rebuild-rootfs` must reject physical/block-device paths. It has no authority to restore anything.

## 4. Rebuilt-image validation — NEXT

Goal: make a reconstructed image independently auditable before it can be written anywhere.

Required gates include:

- exact P1 size;
- filesystem structural check;
- expected content/manifests;
- critical permissions and links where applicable;
- SHA-256 of the final image;
- provenance back to the verified backup and source fingerprint;
- explicit incomplete/failed states.

A historical SHA-256 from one successful manual rebuild is evidence, not a universal expected hash: filesystem metadata can legitimately make independently rebuilt images differ bit-for-bit.

## 5. Guarded P1 restore — PLANNED

Goal: restore only after backup, rebuild and validation are proven.

This will be the first PMKB component allowed to write to physical media and therefore remains isolated from all earlier tools.

Mandatory design constraints before implementation:

- no automatic disk selection;
- positively identify an Aura HD E606C0;
- independently recompute the target fingerprint immediately before writing;
- require it to match the backup provenance;
- verify expected MBR geometry and P1 bounds;
- default to P1 only;
- preserve pre-P1, P2 and P3 unless a future separately designed operation explicitly says otherwise;
- require explicit human confirmation containing target identity, operation and affected range;
- re-check the target after confirmation and immediately before the first write;
- abort on ambiguity or device change;
- write only the bounded P1 byte range;
- flush, reread and verify the written data;
- produce a restore report.

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

## 8. User experience and retro extras — EXPERIMENTAL

Only after the core workflow is dependable:

- friendlier CLI progress and diagnostics;
- possible GUI using the same safety contracts rather than duplicating disk logic;
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
- `backup-aura-hd`: active independent backup lane.
- `rebuild-rootfs`: active local-only rebuild lane.
- `restore-rootfs`: intentionally not implemented yet.

Parallel development is welcome when branches do not weaken or bypass the interfaces and safety boundaries between these lanes.
