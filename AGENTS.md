# PMKB — instructions for coding agents

## Mission

PimpMyKobo-AuraHD targets the Kobo Aura HD / N204 (`dragon`, PCBA `E606C0`). The project has two complementary goals:

1. preserve a reproducible and conservative rescue/recovery path for existing devices;
2. replace the normal Kobo/Nickel userspace with an independent PMKB environment.

The current functional target is **not** to restore Nickel as the normal UI. The first PMKB milestone is:

`Boot ROM i.MX50 -> Netronix/U-Boot layers required by the hardware -> Linux -> minimal PMKB rootfs -> KOReader directly`

No Kobo account or Kobo activation should be required for normal PMKB operation.

KOReader is the first useful graphical userspace. Later milestones may add an e-ink/touch launcher, package format and Store, native applications, games designed for e-ink/turn-based interaction, text/reader Web, Notes/Paperboard and Recipes. Do not implement those later milestones unless the current task explicitly asks for them.

Calibre compatibility is a V1 requirement: architecture and storage decisions must preserve a clean path from Calibre to user book storage to KOReader.

## Hardware and recovery invariants

- Target: Kobo Aura HD / N204, codename `dragon`, PCBA `E606C0`, i.MX50 family, 512 MiB RAM.
- The internal microSD uses an MBR layout with a raw boot area followed by P1 `rootfs`, P2 `recoveryfs`, and P3 `KOBOeReader`.
- **P2/recoveryfs is the recovery parachute. Preserve it.** Do not repurpose it for applications, packages or experiments.
- Existing Kobo/Netronix components may temporarily be required for hardware enablement. Identify them explicitly and do not redistribute proprietary blobs unless redistribution rights are established. Prefer extracting required local artifacts from the user's own device/recovery.
- Rescue/reconstruction tooling remains valuable even though Nickel is no longer the functional target.

## Absolute write-safety rules

Default to read-only operations.

Unless the user gives explicit authorization for the specific physical-write step:

- never write to a physical Kobo/microSD device;
- never issue `dd` or equivalent writes to `/dev/*`, `PhysicalDrive*`, or another raw physical target;
- never format, repartition, mount read-write, or otherwise mutate the physical card;
- never modify P2/recoveryfs;
- never weaken an existing physical-restore guard to make a test pass.

Image files, synthetic filesystems and temporary directories are allowed test targets. Clearly distinguish image-file writes from physical-device writes.

Before any future physical write, require the repository's identification/preflight/backup/plan checks and an explicit user approval for that exact operation.

## Working method

Start every task by checking the actual repository state and relevant existing documentation/code. Do not assume a previous chat description is current.

Work in small logical batches:

1. audit the current behavior and constraints;
2. make the smallest coherent change;
3. add/update tests where applicable;
4. run the relevant test suite;
5. audit the diff for accidental physical-write paths;
6. commit and push only when the batch is coherent.

Do not merge pull requests automatically. Do not close unrelated PRs/issues automatically.

Stop for a user decision only when it materially affects architecture, hardware safety, licensing/proprietary redistribution, or an irreversible action. For routine implementation details, choose the conservative solution, document it, and continue.

## PMKB/KOReader bootstrap priorities

When working on the current bootstrap milestone, prioritize concrete, testable progress toward a P1 image that can boot KOReader without Nickel:

- inspect KOReader upstream requirements and Kobo-specific launch/runtime assumptions;
- identify the minimum init/userspace, libraries, modules, firmware and device helpers required on Aura HD;
- reuse the already-established P1 geometry/ext4 compatibility constraints;
- build on local files/images first;
- validate ARM binaries and dynamic dependencies, permissions, symlinks, filesystem integrity, size and hashes;
- detect and document any remaining runtime dependency on Nickel/Kobo userspace;
- keep proprietary artifacts out of Git unless their redistribution license is clear;
- keep the build reproducible where practical.

Do not spend a bootstrap task implementing the future Store/launcher unless it is required to make the first KOReader boot possible.

## Documentation truthfulness

README and roadmap statements must distinguish:

- implemented and tested on synthetic/local images;
- verified against preserved real-device data;
- physically qualified on an actual Aura HD.

Never describe a physical restoration or successful hardware boot as completed until it has actually happened and evidence exists.

## Tests and CI

Keep tests free of redistributed Kobo firmware/blobs. Use synthetic fixtures where possible. Preserve Linux and Windows test coverage for host-side tools when relevant. Hardware-specific behavior that cannot be exercised in CI must be clearly marked as requiring hardware qualification, not silently treated as passing.

## Scope discipline

PMKB is intended to become an independent e-ink environment, not a general-purpose tablet OS. Prefer designs that exploit e-ink characteristics: static pages, partial refreshes, touch-first interaction and low background activity. Avoid introducing heavy frameworks or permanent services without a demonstrated need on this 512 MiB device.
