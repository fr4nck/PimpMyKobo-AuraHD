# FIRST BOOT evidence folder

[Français](README.md) | **English**

Blank text templates only. No hardware attempt, microSD access or P2 modification.
Use the [qualification protocol](../../first-boot-qualification-en.md) at
`ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf`; it defines expectations,
procedures and STOP conditions for all 25 IDs. Do not duplicate them here.

## Prepare a private trial folder

Copy [trial report](trial-report-en.md), [incident report](incident-report-en.md)
when needed, and [evidence index](evidence-index.tsv) into a folder **outside the
repository**, on the PC. Keep the protocol link/commit when copying; relative
links work in the repository, use the pinned
[online protocol](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf/docs/first-boot-qualification-en.md)
in private copies. Never use P2/P3 as evidence storage.

Trial ID: UTC `YYYYMMDDTHHMMSSZ-fbNN`, with NN the local attempt number.
Use separate folders/reports for separate POWER attempts; link related incidents.
Suggested private contents (create only what is needed):

- `trial-report.md`, `incident-01.md`, `evidence-index.tsv`
- `photos/`, `videos/`, `logs/`, `hashes/`, `preflight/`
- `serial/` only if a capture channel is eventually qualified.

File naming: `<trial-id>_<test-id-or-BOOT>_<sequence>_<neutral-description>.<ext>`.
Example **name only**: `20261004T090000Z-fb01_B03_001_screen.png`.
Use ASCII names, no spaces, personal names, serials or book titles.
Keep original captures unchanged; edited/redacted copies get distinct names
and a parent reference. Extension reflects actual format, not arbitrary conversion.

## Evidence convention

| Kind | Format / record |
| --- | --- |
| Photos | Original JPEG/PNG; timestamps, physical orientation, lighting/exposure; no fabricated before/after |
| Videos | Original available format (e.g. MP4); time reference/frame precision, POWER landmark, cuts disclosed |
| Logs | Raw bytes/text as captured; source/tool/version/encoding, wall clock vs kernel uptime, gaps/resets; retain complete log as well as extracts |
| Hashes | SHA-256 of local artifact/capture; path, byte size, calculation time/method and measured scope |
| Preflight | Original image/content reports, command/version, input image hash and extracted-tree relationship; do not equate no FAIL with hardware PASS |
| Serial | Only if available/qualified later; capture tool/settings/channel and timestamps, raw capture retained; no pinout/electrical assumptions |

The TSV index has one row per artifact: ID, relative path, kind, test IDs, captured
time, T+ (blank if unknown), size, SHA-256, source/tool and notes/parent reference.
Separate multiple test IDs with commas. Unknown hash/size/time stays blank with
reason in notes; never invent it. UTF-8, tab-separated, one physical line per row;
use spaces instead of embedded tabs/newlines. Relate every test to index IDs or
relative paths. Record unavailable evidence explicitly in the report.
An index hash establishes file integrity, not authenticity or successful boot.

## Defaults and manual work

Only IDs/labels, ten gates, timeline landmarks, blocking pointers and
**NOT TESTED** are prefilled. No script or collector: nothing discovers the
candidate, reads a device, computes hashes or assigns PASS automatically.
Existing reports may be copied and referenced after checking their provenance.
Record actual candidate/version/hashes, timestamps, observations, evidence paths,
results, blocking decisions and **P2 preservation confirmation manually**.
The initial P2 statement is UNCONFIRMED; never infer preservation from an empty form.

## Privacy and handoff

Git contains templates only. Real raw evidence remains private outside Git:
no card/rootfs/recovery dumps, proprietary binaries/waveforms, .kobo.zip,
device.xml, serials, personal libraries/databases or private paths.
Before publishing any selected report, review/redact private identifiers, images
and log contents; retain originals privately and label redacted derivatives.
Do not append real results to these templates. A future agent should receive the
trial report, incident report, index and permitted evidence together.
This evidence pack grants no boot/write/restoration approval.
