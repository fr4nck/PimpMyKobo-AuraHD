# FIRST BOOT — incident template

[Protocol](../../first-boot-qualification-en.md) · reference commit:
`ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf`.
Copy privately; one incident per coherent symptom. No new test or write authorized.

## Context

- Incident ID / parent trial ID / relative trial-report path: —
- Exact candidate commit / image ID / P1 SHA-256 / reader version (or UNKNOWN): —
- Date/time/timezone / T+ / uncertainty / reset number: —
- Observer / current power and USB condition / hardware and initial card state: —
- Capture channel available? logs lost/partial/inaccessible? why? —
- Affected test IDs and result (NOT TESTED / PASS / FAIL / UNQUALIFIED): —

## Symptom (select; no diagnosis implied)

- [ ] White screen
- [ ] Frozen screen
- [ ] Bootloop
- [ ] KOReader absent
- [ ] Touch absent
- [ ] Touch reversed / axes exchanged
- [ ] Display reversed
- [ ] P3 absent
- [ ] Abnormal frontlight
- [ ] Other: —

Exact observed behavior, reproducibility **already observed**, timing/frequency,
last display content, LED transitions, requested vs actual light level: —
Do not repeat POWER or inject faults merely to complete this report.

## Last proven stage and evidence

| Stage | Observed / unknown / contradicted | Time / evidence / log / interpretation limits |
| --- | --- | --- |
| Supply / LED | — | — |
| Kernel / init | — | — |
| fb0 identity / actual refresh | — | — |
| Touch identity / raw events / UI mapping | — | — |
| P3 actual source/type/options / ready | — | — |
| Launcher / loader / live reader / usable UI | — | — |

Record actual mount/process/node identities where captured, not assumed eventN.
Link full dmesg, boot output and timestamps if available; a keyword or node alone
does not prove hardware readiness. Attach photos/video references.

## Actions and preservation

| Time / T+ | Action already taken (exact command/UI action/tool version) | Result/return / evidence | State or bytes possibly changed |
| --- | --- | --- | --- |
| — | — | — | — |

- STOP condition and time / new actions ceased / current safe state: —
- P2 unchanged: **UNCONFIRMED**; reference/after hashes, scope/method/evidence: —
- Pre-P1/P3 preservation / any unexpected RW/write / active operation: —
- Evidence index and exported volatile logs / missing evidence: —

## Diagnostic handoff

- Facts established / evidence: —
- Hypotheses (label unproven; supporting and contradicting facts): —
- Last proven stage / first unqualified dependency: —
- Next proposed observation, expected discriminating evidence and prerequisites: —
- Actions blocked / separate approval needed / person taking over: —

No factory reset, forced reboot, device write or P2 recovery execution is authorized
by this report. Refer conceptual rollback to the protocol; do not turn it into
an executable recovery procedure here.
