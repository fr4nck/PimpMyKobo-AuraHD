# PimpMyKobo-AuraHD — Roadmap

[Français](ROADMAP.fr.md) | **English**

Snapshot: **6 October 2026**, integration reference `integration/pmkb-first-boot-1@c2a8ae54fd4a5c80f84415c165e90e566a8549de`.

Code implemented and tested on files is not equivalent to qualification on the real Kobo. **No physical write to a Kobo microSD has yet been performed in this workstream.** This roadmap grants no implicit write authorization.

## Immediate objective

The priority milestone is no longer to restore P1 on the original microSD.

The normal target workflow is now:

**original microSD read-only → capture PRE-P1 + P2 → remove original → build a new PMKB microSD → reread and verify → hardware FIRST BOOT on the Aura HD.**

The original microSD must remain untouched and be kept as the hardware backup.

The immediate finish line is simple:

**build a new microSD, install it in the Aura HD, and finally qualify the real first boot.**

## Current state

| Stage | Actual state | Remaining gate |
|---|---|---|
| PMKB FIRST BOOT #1 P1 candidate | **FROZEN / software-qualified** — 268,435,968 bytes, SHA-256 `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c` | Hardware boot not attempted |
| Reference PRE-P1 / HWCONFIG | **Qualified** | Must be reread from the real donor during creation |
| Reference P2 / recoveryfs | **Qualified** — SHA-256 `fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a` | Must be reread from the real donor during creation |
| Replacement backend `replace-microsd-linux.py` | **Implemented and merged** via PR #16 | Real write to replacement media not qualified |
| Original donor | **Read-only** contract implemented | Real hardware read in the new workflow pending |
| Live staging | PRE-P1 + P2 only, about 278 MiB; one card reader is enough | Must be exercised on the real Live |
| New P3 | FAT32 `KOBOeReader`, sized from target capacity | Real Kobo mount not qualified |
| Live UX | French/English, AZERTY, replacement-first flow, textual progress | Operator report should become clearer in a single screen |
| Live identity | Separate `candidate_head` / `live_head` prepared in PR #17; CI #130 green at this snapshot | PR #17 not merged into the reference above |
| PC boot of an older PMKB Live | **Observed** up to the PMKB menu | New Live containing replacement flow must be rebuilt and requalified |
| Aura HD FIRST BOOT | **UNQUALIFIED** | Boot, display, touch, frontlight, P3, USB/Calibre |

See [replacement microSD](remplacement-microsd-fr.md), [qualification USB](qualification-usb-fr.md), and [FIRST BOOT](pmkb-first-boot-1-en.md).

## 1. Align and freeze the preparation Live

Before touching any real microSD:

1. finish qualification of the current Live code, including separate candidate-P1 and Live-code identities;
2. rebuild the ISO from a clean Git checkout and exact commit;
3. retain the produced ISO SHA-256;
4. verify the candidate, backends, manifest, plan and build identity inside the ISO;
5. keep the main operator interface on **one screen**: progress, essential results and readable errors in one place;
6. present analyses as `OK / ERROR / TO TEST`, with technical details available without requiring another console;
7. version useful graphical source material and its provenance in Git; displaying illustrations in the Live is a refinement, not a safety prerequisite.

No complex graphical effects or animations are required for FIRST BOOT #1.

## 2. Make the exact P1 candidate available

The replacement flow can recapture PRE-P1 and P2 from the original microSD, but **not the PMKB P1 candidate**.

The real Live therefore requires exactly:

- `PMKB-FIRST-BOOT-1-0b00d858.img`
- size: `268435968`
- SHA-256: `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`

This artifact may come from the existing private build or from a previous private Live containing it, provided its SHA-256 is verified.

## 3. Build and boot the new real Live

1. build the PMKB ISO with the exact candidate and sealed plan;
2. verify its SHA-256;
3. write the ISO to the qualification USB stick, never to a Kobo microSD;
4. boot the laptop into native Linux Live;
5. verify PMKB startup, French/AZERTY if selected, and displayed candidate/Live identities.

The earlier successful PC boot only proves that this Live family can boot on that laptop; it does not qualify the new ISO.

## 4. Read the original microSD — strictly read-only

Normal workflow:

1. choose **Create / repair a new PMKB microSD**;
2. insert the original microSD;
3. explicitly enter the whole disk, for example `/dev/sdb`;
4. verify removable USB media, 512-byte logical sectors, geometry and Aura HD E606C0 identity;
5. reread and verify PRE-P1 / HWCONFIG;
6. reread and verify P2 / recoveryfs;
7. stage only:
   - PRE-P1: about 9.5 MiB;
   - P2: 256 MiB;
   - capture manifest.

The original card is opened read-only. **No write to it is required in this workflow.**

The staging fits in RAM; one card reader is sufficient.

## 5. Remove and preserve the original

After successful capture:

1. physically remove the original microSD;
2. store it as the hardware backup;
3. do not depend on it during target writing.

The donor must not need to remain present while the replacement target is written.

## 6. Prepare the replacement microSD

1. insert another microSD;
2. explicitly enter its whole-disk path;
3. verify it is removable, USB, unused and large enough;
4. reject a target that looks like the donor;
5. calculate P3 from actual target capacity;
6. display target capacity, future P3 size and exact plan;
7. bind the plan to this target's identity and fingerprint;
8. require the exact destructive confirmation.

Fixed system geometry:

- PRE-P1: offset 0, size 9,961,472;
- P1: offset 9,961,472, size 268,435,968;
- P2: offset 278,397,440, size 268,435,968;
- P3 starts at 546,833,408.

The current contract reserves at least 1 GiB for P3, making the theoretical minimum total capacity about 1.51 GiB. 16 GB and 32 GB cards are therefore far above the software minimum; real compatibility of very large capacities remains a hardware qualification matter.

## 7. Build the new card

Only after confirmation:

1. write donor PRE-P1, changing only the MBR P3 length for target capacity;
2. write P1 with the frozen PMKB candidate;
3. write P2 bit-for-bit from staging;
4. create FAT32 P3 labeled `KOBOeReader`.

Long operations show textual progress, for example:

`Original P2 recovery read: 72% (184.3/256.0 MiB, 18.4 MiB/s)`

No automatic retry and no implicit automatic rollback.

## 8. Reread and qualify the new card before the Kobo

Creation succeeds only if post-write checks pass:

- PRE-P1 reread and matches;
- P1 reread with expected SHA-256;
- P2 reread with expected SHA-256;
- MBR and geometry valid;
- P3 FAT32 valid;
- `KOBOeReader` label valid.

Operator reporting must clearly distinguish:

- **OK**: demonstrated by read/check;
- **ERROR**: invalid or interrupted operation;
- **TO TEST**: depends on Kobo hardware and cannot be inferred from the card alone.

A partially written target remains disposable/rebuildable. After a failure, diagnose and rebuild the target; the original stays untouched.

## 9. Hardware FIRST BOOT on the Aura HD

Install the new card and explicitly qualify:

1. real boot;
2. framebuffer / E-Ink display;
3. KOReader launch;
4. touch;
5. frontlight;
6. P3 mount at `/mnt/onboard`;
7. book/file access;
8. USB / Calibre;
9. stability after reboot.

Until exercised on the real device, these remain **UNQUALIFIED**.

Hardware results must be tied to the P1 candidate SHA, Live commit, constructed-card identity and session report.

## 10. The 31.9 GB full-card backup is no longer a prerequisite

The existing full backup remains useful as a cold archive, especially as an exact snapshot of the old P3 and user data.

The replacement workflow does not depend on it:

- PRE-P1 can be recaptured from the original;
- P2 can be recaptured from the original;
- P3 is recreated;
- PMKB P1 comes from the frozen candidate.

Target policy:

- keep the original microSD intact;
- keep hashes, manifests, scripts, documentation and small source assets in Git;
- keep large dumps as optional cold archives, not as a 24/7 service dependency;
- do not synchronize 31.9 GB merely to make the normal workflow possible.

## 11. P1 restoration on the original remains a separate advanced contract

`restore-p1-linux.py` remains available.

Its historical contract stays strict:

- target = known original card;
- whole card equals the qualified backup;
- only P1 may be written;
- everything outside P1 must remain unchanged.

This is an advanced recovery path, **not the normal repair workflow**.

It must never be weakened to accept arbitrary replacement cards; full replacement belongs to `replace-microsd-linux.py`.

## 12. Only after FIRST BOOT — PMKB product phase

Product work must not delay the first hardware boot.

After FIRST BOOT is qualified:

- stabilize KOReader as V1;
- design the PMKB e-ink launcher;
- organize Books / Apps / Games / Store / Web / Notes / Recipes / Settings;
- continue lightweight applications, network/diagnostic tools, PDA functions, offline cards and other planned capabilities;
- keep optional services non-resident when unused;
- then study two-panel split mode and interface refinements;
- keep retro themes, Ikari Mode and other Easter eggs outside all safety paths.

## 13. Then make rescue reproducible on other Aura HD units

After success on the development device:

- qualify the same workflow on other E606C0 units;
- document unsupported hardware variants and geometries;
- retain synthetic tests and FR/EN documentation;
- publish no private dumps, recovery images or firmware;
- separately decide what can become a lightweight public distribution.

## Architecture invariant

The primary workflow must remain segmented:

```text
original microSD
      |
      | read only
      v
PRE-P1 + P2 + E606C0 identification
      |
      | Live staging (~278 MiB)
      v
remove original
      |
      v
explicitly selected replacement microSD
      |
      | plan + destructive confirmation
      v
PRE-P1 + PMKB P1 + P2 + FAT32 P3
      |
      | reread / verification
      v
FIRST BOOT on Aura HD
```

**Read the original → remove it → build another card → reread → test hardware.**

No button, shortcut or interface improvement may turn this chain into an implicit write to the original card.
