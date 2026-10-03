# First P1 restore on native Linux Live USB

`tools/restore-p1-linux.py` is separate from the legacy importer and disk-image simulator. Its default mode checks local files only; it never opens a device. The legacy provenance is retained. No physical restore has been authorized merely by preparing this tool.

Use native 64-bit x86_64/aarch64 Linux Live, Python 3.10+ and e2fsprogs. Device access requires root and `--ack-linux-live`; Windows, WSL, recognized containers and a different mount namespace from PID 1 are rejected. Live boot itself is acknowledged by the operator, not proved by software.

Supply nine positional paths: plan, legacy manifest, rebuild report, rebuilt P1, full backup, acquisition report, simulated full image, simulation report, and a new journal path. Keep the manifest's relative evidence hierarchy when moving files. Rewriting paths changes its hash and breaks bound reports. Full images require storage supporting files over 4 GB.

The default performs only local validation and temporary plan regeneration, even if a device argument is present. `--check-device --device /dev/disk/by-id/EXPLICIT_CARD_ID --ack-linux-live` additionally performs exclusive read-only access as root. Manually identify the whole card and unmount its partitions first; the tool never mounts, unmounts, changes protection or partitions anything. No journal is created during a read-only check.

Physical write requires the distinct `--write-p1` switch plus `--authorize-plan-sha256` matching the reviewed plan, a device, and the Live acknowledgement. These flags are not conversational approval. Obtain separate explicit human authorization before using them. There is no automatic discovery, default device, bypass, automatic retry or rollback.

The write backend revalidates all local evidence, stages and hashes P1, checks the staged file with read-only `e2fsck -f -n`, and durably records the plan. Journal and rollback storage must be separate from the target, persistent, and have at least twice P1's size plus 4 MiB free. ext2/3/4, XFS, Btrfs, FAT, exFAT and NTFS3 are supported if syncing succeeds; Live RAM, overlay, FUSE/ntfs-3g and network storage are refused. Existing sidecars are never overwritten.

The target must be a whole removable USB disk with 512-byte logical sectors, no mounted partitions, active swap or holders. A single `O_RDWR|O_EXCL|O_NOFOLLOW` descriptor is checked and retained throughout. Capacity is queried via ioctl; the entire card must hash exactly like the verified backup. Original P1 is copied into a new durable `.original-p1.img`, independently reread and checked against the backup. The full target is checked again before recording durable write intent.

Only the validated P1 range is written, with short-write handling. The backend syncs and invalidates the block cache, then reads P1 and the entire complement of P1. Success requires matching replacement and preservation hashes. Kernel-exclusive access does not isolate against every privileged raw writer; run no other disk tools. Whole-content equality does not prove a unique hardware serial. Unsigned reports provide consistency, not authenticity.

An interruption after `writing_p1` can leave P1 partial. Retain all artifacts, keep the card outside the Kobo, and review the journal before any further write. A new run refuses existing files or a target changed from the original backup. Manual rollback requires a separate procedure and authorization; automatic rollback is not implemented. Success does not prove bootability or P3 filesystem health. Legacy `physical_restore_eligible=false` remains unchanged; current operator intent and physical checks are recorded separately.

Tests use synthetic regular files, temporary sysfs/proc fixtures and mocked block descriptors. One Linux test runs real e2fsck on a synthetic ext4 image, verifying no input changes. No tests write real devices. Actual hardware locking/ioctl behavior awaits an authorized Live operation.

See the [detailed French procedure](restore-p1-linux-fr.md), [Linux open(2)](https://www.man7.org/linux/man-pages/man2/open.2.html), [Linux ioctl definitions](https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h) and [e2fsck(8)](https://man7.org/linux/man-pages/man8/e2fsck.8.html).
