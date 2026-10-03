# FIRST BOOT — trial report template

[Protocol](../../first-boot-qualification-en.md) · protocol commit: `ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf`

**Blank template; no hardware test or write authorization.** Copy into a private
trial folder outside Git. Replace — with facts or an explicit unknown.
Allowed results: NOT TESTED / PASS / FAIL / UNQUALIFIED. Missing evidence is
not PASS. One report per POWER attempt; retain earlier attempts separately.

## Identity and initial state

| Field | Value / supporting reference |
| --- | --- |
| Trial ID (UTC YYYYMMDDTHHMMSSZ-fbNN) | — |
| Image ID / local filename / size / image SHA-256 | — |
| Exact candidate Git commit (40 hexadecimal characters) / dirty build tree? | — |
| P1 image SHA-256 / size; post-write reread reference if previously authorized | — |
| Build manifest / runtime / preflight image and extracted-content references | — |
| KOReader version / package SHA-256 / actual observed version | — |
| Trial date/time ISO 8601 with timezone / operator pseudonym | — |
| POWER T0 / clock source and precision / wall-clock vs kernel uptime offset | — |
| Hardware: Aura HD E606C0/dragon claimed; actual identification evidence | — |
| HWCONFIG: expected v1.7, 39 bytes, PCB 28; actual values / evidence | — |
| Private target/card ID / size / MBR geometry / fingerprint reference | — |
| Initial card state: original/working copy, previous P1, last known boot, prior authorized operations | — |
| Initial display / LED / power supply / USB / charge history / anomalies | — |
| Backup verification / original card preservation / permitted ranges and approvals | — |
| Capture channel / export method / limitations and available tools | — |
| P2 reference SHA-256 / size / geometry / source and timestamp | — |
| P2 post-operation/read-only verification reference, SHA-256 / timestamp | — |
| Explicit P2 preservation confirmation | **UNCONFIRMED** — enter “P2 not modified” only with method/evidence and scope |
| P2 mounted? any unexpected write? pre-P1/P3 preservation evidence | — |

Record unknowns honestly. A matching hash covers the measured interval/content,
not every historical operation. This report does not authorize extra device
access to fill missing fields.

## Ten prerequisites

Use the protocol G01–G10; do not copy procedures here. All initially NOT TESTED.

| Gate | Result | Factual finding / evidence reference | Unresolved limitation / approval reference |
| --- | --- | --- | --- |
| G01 | NOT TESTED | — | — |
| G02 | NOT TESTED | — | — |
| G03 | NOT TESTED | — | — |
| G04 | NOT TESTED | — | — |
| G05 | NOT TESTED | — | — |
| G06 | NOT TESTED | — | — |
| G07 | NOT TESTED | — | — |
| G08 | NOT TESTED | — | — |
| G09 | NOT TESTED | — | — |
| G10 | NOT TESTED | — | — |

## Timeline

Rows are landmarks, **not guaranteed execution order or expected durations**.
Use actual order in notes, add rows for resets/errors. Time unavailable → UNKNOWN,
not zero. Separate observation time from inferred time; retain reset boundaries.

| Landmark | Wall time (timezone) | T+ seconds / uncertainty | Observation / evidence / log |
| --- | --- | --- | --- |
| POWER | — | 0 (definition; fill only when performed) | — |
| LED transitions | — | — | — |
| First E-Ink change | — | — | — |
| Usable framebuffer (how established?) | — | — | — |
| Touch detected (identity/evidence?) | — | — | — |
| P3 available (actual mount?) | — | — | — |
| KOReader launch (attempt vs confirmed process) | — | — | — |
| First usable KOReader screen | — | — | — |

## 25 test records

Blocking column is a short protocol pointer, **not a GO**. Consult that ID for
conditions; record the actual blocked dependency/continuation decision in notes.
Evidence/log references use relative private-folder paths or index IDs.
— means unfilled; explain unavailable/not captured evidence explicitly.

| ID / label | Result | Wall time or T+ / uncertainty | Factual observation | Evidence | Log | Blocking (protocol) | Notes / actual decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B01 LED | NOT TESTED | — | — | — | — | Conditional; see B01 | — |
| B02 Kernel/init | NOT TESTED | — | — | — | — | Yes; see B02 | — |
| B03 First screen change | NOT TESTED | — | — | — | — | Yes display; see B03 | — |
| B04 Phase durations | NOT TESTED | — | — | — | — | Conditional; see B04 | — |
| S01 P3 source/mount | NOT TESTED | — | — | — | — | Yes; see S01 | — |
| S02 Books | NOT TESTED | — | — | — | — | Yes reading; see S02 | — |
| S03 P3 absent at boot | NOT TESTED | — | — | — | — | Yes if launch; see S03 | — |
| S04 P3 lost before exec | NOT TESTED | — | — | — | — | Yes; see S04 | — |
| S05 P3 lost after exec | NOT TESTED | — | — | — | — | Resilience unqualified; see S05 | — |
| K01 Direct launch | NOT TESTED | — | — | — | — | Yes; see K01 | — |
| K02 Independent profile | NOT TESTED | — | — | — | — | Yes; see K02 | — |
| K03 First reading | NOT TESTED | — | — | — | — | Yes; see K03 | — |
| E01 Framebuffer | NOT TESTED | — | — | — | — | Yes; see E01 | — |
| E02 Orientation | NOT TESTED | — | — | — | — | Yes; see E02 | — |
| E03 Full refresh | NOT TESTED | — | — | — | — | Yes; see E03 | — |
| E04 Partial refresh | NOT TESTED | — | — | — | — | Yes partial; see E04 | — |
| E05 Ghosting | NOT TESTED | — | — | — | — | Conditional; see E05 | — |
| N01 Neonode detection | NOT TESTED | — | — | — | — | Yes; see N01 | — |
| N02 Acquisition | NOT TESTED | — | — | — | — | Yes; see N02 | — |
| N03 Touch axes/orientation | NOT TESTED | — | — | — | — | Yes; see N03 | — |
| N04 Screen zones | NOT TESTED | — | — | — | — | Yes; see N04 | — |
| F01 NTX chain | NOT TESTED | — | — | — | — | Yes; see F01 | — |
| F02 Frontlight off | NOT TESTED | — | — | — | — | Yes; see F02 | — |
| F03 Frontlight levels | NOT TESTED | — | — | — | — | Yes; see F03 | — |
| F04 Light button | NOT TESTED | — | — | — | — | Conditional; see F04 | — |

## Handoff

- Last proven stage / evidence: —
- STOP triggered? time, reason and current safe state: —
- Incidents (relative report paths): —
- Summary of PASS / FAIL / UNQUALIFIED / NOT TESTED, essential gaps: —
- P2 confirmation and preservation evidence reviewed by/date: —
- Volatile logs exported? unavailable evidence and cause: —
- Proposed next diagnostic step / blocked actions / required separate approval: —

No broad “hardware qualified” claim while an essential test lacks evidence.
