# Verifying an existing backup

[Français](verify-backup-aura-hd-fr.md) | **English**

`tools/verify-backup-aura-hd.py` checks, **offline**, a directory produced by [`backup-aura-hd.py`](backup-aura-hd-en.md). No Kobo needs to be connected.

The tool is **strictly read-only**: every file of the directory is opened with `rb`, and nothing is created, renamed or modified, not even the `.part` or `.FAILED` files left by an interrupted copy.

> **Scope.** A "valid" verdict proves that the files are **consistent with their manifest**. It proves neither their **authenticity** (a manifest and its files may have been replaced together) nor that they **can be restored** on a given card. The backup also covers only the selected components, not the whole card.

## Usage

```bash
python3 ./tools/verify-backup-aura-hd.py ~/Aura-backup --lang en
```

```powershell
python .\tools\verify-backup-aura-hd.py D:\Aura-backup --lang en
```

Options:

- `--json`: only the JSON report is written to stdout. Non-ASCII characters are escaped, so it is safe on any Windows console;
- `--lang en`: English human output (French is the default).

## The four verdicts

| Verdict | `status` | Exit code | Meaning |
|---|---|---|---|
| **BACKUP VALID** | `valid` | `0` | every requested component re-reads consistently with the manifest, `SHA256SUMS` and the target fingerprint |
| **BACKUP INCOMPLETE, INTERRUPTED OR RECORDED AS FAILED** | `incomplete` | `1` | no inconsistency found, but the backup did not finish: manifest `interrupted`, `in_progress` or `failed`, a component not verified, `complete: false` |
| **BACKUP INCONSISTENT OR CORRUPTED** | `inconsistent` | `2` | at least one demonstrated contradiction: missing, truncated or modified file, contradictory hashes, divergent `SHA256SUMS`, target fingerprint or geometry that does not match, dangerous path, `complete: true` contradicted |
| **INVALID MANIFEST** | `invalid` | `3` | inaccessible directory; manifest missing, unreadable, invalid JSON, unsupported schema or incomplete structure |

If any inconsistency is found, the verdict is `inconsistent`, even if the backup was otherwise also incomplete.

A backup **recorded as failed** by the backup tool (for example a divergent destination read-back, kept as `.FAILED`) is classified `incomplete`: the defect is already recorded in the manifest, and the verifier only confirms that the rest is consistent. The backup must be redone. If the verifier also detects a corruption (modified verified component, divergent `SHA256SUMS`…), the verdict becomes `inconsistent`: a recorded failure never hides a corruption.

## What is checked

**Manifest**

- supported `schema_version` (currently `1`, an integer) and `tool` equal to `backup-aura-hd`;
- presence and types of the fields;
- the exact set of four components.

**`complete: true` is never taken on trust.** It must be confirmed by:

- `status: complete`;
- every requested component re-read and valid;
- `identity_recheck.matches`;
- no recorded errors.

**Components**

- Pre-P1, P1 and P2 are always requested. P3 is requested only when `options.include_userdata` is `true`: its absence is otherwise normal.
- For a component recorded as `verified`:
  - the file has its canonical name and is a regular file, not a link;
  - its real size equals `size`, `bytes_written` and `destination_size`;
  - the recomputed SHA-256 equals `sha256`, `sha256_destination` and `sha256_stream`.
- `sha256_source_reread` must be present and equal when the backup re-read the source. It must be **absent** for a `--single-pass` backup.
- For `pre_p1`, the hash must also equal the one measured at identification (`expected_sha256`).
- A `.part` or `.FAILED` file is **never** a valid component. It is reported as a leftover of an unfinished or failed copy.
- A final file that exists while the manifest does not mark it `verified` is not trusted.

**`SHA256SUMS`**

- It must list exactly the verified components, with the recomputed hashes.
- Its absence is an inconsistency for a finished backup (`complete` or `failed`). It is normal for an interrupted one.

**Values re-read from the files versus values only declared**

Values **re-read** from the files:

- `pre-p1.bin` is parsed again with the qualified inspector parser. From it come:
  - the MBR: sector 0 SHA-256, type, LBA, size and offset of P1 to P3;
  - the HWCONFIG: v1.7, 39 bytes, PCB 28 and its fields;
  - the **target fingerprint**, recomputed with the backup tool's own algorithm.

  Each field is compared with its declared value. The internal consistency of `fingerprint_sha256` is checked as well.
- Component offsets and sizes are compared with the re-read geometry.
- Filesystem labels are re-read from valid images: P1 `rootfs`, P2 `recoveryfs`, and P3 when present.

Values **only declared**, reported as such in `declared_only`:

- source path and size, timestamps, `identity_recheck`;
- agreement with the real source. Since the card is not connected, `sha256_stream` and `sha256_source_reread` can only be compared with the files, not with the card.

**Paths**

The verifier refuses, without ever reading them:

- absolute paths, `..` traversal and directory separators;
- Windows drive names (`C:…`);
- symbolic links: component, `SHA256SUMS` or manifest;
- any name that resolves outside the backup directory.

## JSON report

Main fields:

- `schema_version` (report format: `1`), `status`, `ok`;
- `invalid_reasons[]`, `inconsistencies[]`, `incomplete_checks[]`, `warnings[]`;
- `components[]`: `result`, `declared_status`, `actual_size`, `sha256_recomputed`;
- `sha256sums`, `fingerprint` (`declared`, `recomputed`, `fields`, `matches`), `labels_reread`;
- `leftovers` (`.part`, `.FAILED`), `declared_only`, `scope`.

## Decisions adopted

1. The target fingerprint is a **matching hint**, never the sole criterion authorizing a restore.
2. The uniqueness of the pre-P1 area between two Aura HD units **remains unknown**.
3. Strict backup remains the default behaviour. A future rescue mode for a corrupted P1 will be a separate work item and is not implemented.
4. The backup covers the selected components, **not the whole card**.
