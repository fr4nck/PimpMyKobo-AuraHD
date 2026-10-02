# Observed partition layout — Kobo Aura HD

[Français](partition-layout-fr.md) | **English**

Observed layout on the internal microSD card of the studied Aura HD.

| Partition | Offset | Size | Filesystem | Role |
|---|---:|---:|---|---|
| P1 | 9,961,472 | 268,435,968 | ext4 | `rootfs` |
| P2 | 278,397,440 | 268,435,968 | ext4 | `recoveryfs` |
| P3 | 546,833,408 | 31,368,150,016 | FAT32 | `KOBOeReader` |

The area preceding P1 is 9,961,472 bytes long and contains low-level boot data required by the device.

## Safety rule

The values above document the studied unit. Automated tooling must read and validate the actual partition table before performing any write operation.

At minimum it should verify:

1. physical device size;
2. partition style;
3. offsets;
4. partition sizes;
5. HWCONFIG;
6. E606C0 identification when that target is required;
7. backup integrity;
8. reconstructed image integrity.

Read-only mode should remain the default.
