# FIRST BOOT #1 — Aura HD E606C0 qualification protocol

[Français](first-boot-qualification-fr.md) | **English**

Status: **protocol prepared; no hardware tests performed**. Every hardware
test below is **NOT TESTED**. This document authorizes neither microSD writes,
boot attempts nor restoration. **P2/recoveryfs is untouchable.**

Scope: first boot of a PMKB P1 directly into KOReader, without Nickel or Kobo
activation. Suspend, networking, USB/Calibre export and MCU updates are outside
this campaign. No builder, rootfs or reader changes accompany this document.

## 0. Evidence and verdicts

- **A**: [hardware audit at 235085e](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/235085ea27ff6680a03bf10e2798d7589f1c8f97/docs/offline-hardware-qualification-fr.md).
  Source/configuration/call-flow evidence, not physical qualification.
- **I**: [integration at a8ce226](https://github.com/fr4nck/PimpMyKobo-AuraHD/tree/a8ce226bcd46483feb8e35e49f826fa076098bfb),
  particularly rcS, inittab, pmkb-reader, pmkb-check-onboard,
  pmkb-check-offline, preflight-koreader.py and the FIRST BOOT document.
  This reference is not an authorized image. Pin the final consolidated
  commit and recheck differences before a future campaign.
- Kernel and KOReader archives are pinned and hashed in A. Source matches
  do not establish reproducibility of the entire preserved kernel binary.

| Verdict | Meaning | Consequence |
| --- | --- | --- |
| PASS | Test performed, expected result observed, evidence retained | Enables only its specified next steps |
| FAIL | Reliable observation demonstrates an error or unmet expectation | Block affected dependencies; STOP if dangerous |
| UNQUALIFIED | Evidence insufficient, ambiguous identity or measurement unavailable | Never substitute for PASS; block essential dependencies |
| NOT TESTED | Test not performed | No hardware conclusion |

Offline PASS is not hardware PASS. A preflight **without FAIL is not write
authorization**. Omitted tests remain NOT TESTED, not PASS.

## 1. Ordered gates before requesting physical-write authorization

Any unresolved gate blocks the request. Retain reports, plans and hashes privately.

- [ ] **G01 Candidate**: complete commit, image size/SHA-256, runtime/reader
  hashes, build manifest and ext4 parameters. Link the inspected tree to the
  actual image bytes; identical inputs alone do not prove that link.
- [ ] **G02 Preflight**: inspect both image integrity and extracted content
  from that image: ARM/dependencies/bootstrap/permissions/storage/no-Nickel
  settings. No FAIL; resolve applicable software UNQUALIFIED results before GO.
  Hardware UNQUALIFIED results are the purpose of the future campaign.
  Do not bypass physical_restore_eligible=false or hardware_qualified=false,
  or treat a recovery restoration contract as experimental-image permission.
- [ ] **G03 Target**: confirm dragon/E606C0, HWCONFIG v1.7/39 bytes/PCB 28,
  actual MBR geometry, P1 offset/size and ext4 compatibility with the preserved
  kernel. Device names are not identity; fingerprint identifies content, not CID.
- [ ] **G04 Preservation**: privately verify pre-P1, original P1, P2 and P3
  backups, manifests, sizes and hashes. Disclose unsaved gaps/tail; do not call
  a component backup a whole-card image.
- [ ] **G05 Recovery parachute**: verify P2 and its archives on a local copy,
  retain reference hash. Read scripts as data; never execute or mount P2 RW.
- [ ] **G06 Future P1-only plan**: exact ranges, filesystem fit, local simulation
  proving all bytes outside P1 preserved, planned reread. MBR/pre-P1/P2/P3 are
  outside the target. Prefer a separately authorized working card; retain original.
- [ ] **G07 Physical condition**: identified installed card, sound connectors,
  battery without anomalies, stable supply. Record cable/source/charge duration.
  A establishes no safe battery percentage. Anomalies mean STOP, not forced charge.
- [ ] **G08 Observability**: qualify an early-init capture channel and export
  volatile logs without writing P2/P3. Serial pinout/electrical levels/access
  are not qualified here; USB is not a proven console. Never open watchdog
  or enable USB storage to obtain logs. Without pre-UI capture, kernel/init
  diagnosis is UNQUALIFIED: resolve it or explicitly accept that limitation
  in the future GO; do not invent accessible logs after a white screen.
- [ ] **G09 Evidence kit**: operator/date/trial ID, camera/timer, panel landmarks,
  known DRM-free test book and evidence extraction before shutdown.
- [ ] **G10 Separate approval**: approve exact candidate/target/write ranges,
  unknowns, STOP conditions and rollback. Following a future authorized write,
  require reread hashes and unchanged P2/pre-P1/P3 before authorizing boot.

Current state: candidate gates to be completed; no physical write authorized.

## 2. Preservation and execution order

Never use P2 for logs, journal replay, repair, formatting, installation or tests.
Preserve its bytes/geometry/archives, MBR, U-Boot, kernel, HWCONFIG, waveform,
old P1 and P3. I mounts P3 FAT **ro**; settings live under volatile /tmp/pmkb.
Book access problems never justify remounting RW.

Light-button + POWER factory reset is not a neutral restart or our rollback:
audited P2 scripts may format P1/P3 and write U-Boot. Do not trigger it.

Actual I dependency order: kernel → rcS → proc/sysfs/tmpfs/coldplug → network
guard → required nodes → P3 ro → /run/pmkb-ready → pmkb-reader → temporary
profile → P3 recheck → exec luajit reader.lua. Establish mounting and launch
before interactive qualification. Reader evdev opening activates Neonode.
Tests use the reader or already validated tools; this lot installs no tools
or patterns. Their availability remains a candidate prerequisite.

## 3. POWER and white-screen diagnosis

Film before ordinary POWER, without the light button. Record USB condition.
Measure from T0; do not silently change cable/supply during a trial.

| ID | Expected result | Evidence | Blocking |
| --- | --- | --- | --- |
| B01 LED | Record color, steady/blinking, extinction and durations; no success pattern established | Timestamped video and USB condition | Not alone, absent electrical anomaly; LED alone never proves boot PASS |
| B02 kernel/init | Expected kernel/init, no panic/oops/reset loop/critical errors | Qualified console, dmesg, /proc/version, cmdline, uptime | Yes; inaccessible logs → UNQUALIFIED |
| B03 screen | Record first flash/content and usable UI; no Kobo logo/Nickel animation required | Continuous video and before/after photos | Yes for display; unchanged screen does not locate failure |
| B04 phases | Measure kernel/init/P3/exec/first-refresh/UI times and stability | Relative timestamps, resolution of measurement | Not as performance threshold; proven stalled dependency blocks next stages |

Suggested recording checkpoints: 5/15/30/60/120 seconds, **not manufacturer
timeouts or measured normal boot durations**. At 120 s without progress,
suspend further actions and collect evidence; do not infer a dead card or
force power off. Typical phase durations are **unknown**.

For a white screen, determine the last *proven* stage: supply/LED → kernel
and command line → init and nodes → P3/ready → launcher/loader/reader → fb0
and EPDC readiness → actual refresh. A framebuffer node is not panel-ready
proof, ready is not current mounting proof, an exec attempt is not a live UI.
Without a capture channel, record UNQUALIFIED; do not diagnose waveform or
touch failure from white appearance alone. No factory reset or repeated
uncontrolled POWER cycles.

## 4. Storage and reader

| ID | Expected result | Evidence | Blocking |
| --- | --- | --- | --- |
| S01 mount | Identified P3, vfat, exact /mnt/onboard mountpoint, ro; P2 not mounted; node agrees with sysfs | /proc/mounts, partitions, block sysfs, private geometry/hashes | Yes; wrong source/RW/P2 changes → STOP |
| S02 books | Witness book visible and readable after launch; not a P1 directory masquerading as mounted storage | Neutral witness listing/hash, UI photo | Yes for reading qualification |
| S03 absent at boot | In a separately approved scenario, rcS refuses before ready/reader, without repair/formatting | Missing-node/mount error, ready/process state | Yes if reader launches; scenario NOT TESTED now |
| S04 lost before exec | pmkb-check-onboard refuses loss between rcS and final check | Mount snapshot, guard error, no reader | Yes; future controlled test only, no forced unmount/hot removal |
| S05 lost after exec | Unknown: I has no continuous monitor; guard checks mountpoint only, not source/type/ro | Spontaneous-incident chronology/logs | UNQUALIFIED; no resilience claim and no induced loss on first boot |
| K01 direct launch | PRODUCT=dragon, PLATFORM=ntx508, expected LuaJIT/reader, dragon model, stable UI without activation/Nickel | Identified process /proc, launcher/reader output, UI/version | Yes; loader/crash/model errors FAIL |
| K02 independent profile | Temporary HOME/XDG; candidate KOBO_LIGHT_ON_START=-1 and Nickel brightness sync false | Static profile report, actual files/errors | Yes; compatibility module alone is not evidence of Nickel access |
| K03 reading | Open witness, turn 3 pages, return without crash | Photos, output/errors/times | Yes for reader; not long-term stability proof |

## 5. E-Ink

| ID | Expected result | Evidence | Blocking |
| --- | --- | --- | --- |
| E01 framebuffer | Character fb0 linked to sysfs; actual FBIO depth/stride/memory/dimensions coherent; physical panel 1080×1440 | fb0 dev/bits_per_pixel/rotate, FBIO tool/version, dmesg | Yes; actual 8/16 bpp and initial rotation unqualified; never assume 0/8 |
| E02 orientation | Asymmetric pattern/text and marked corners match physical/UI top | Four-corner photo, rotation readings | Yes for touch/reading; exchanged dimensions under rotation are not inherently failure |
| E03 full refresh | Known full action renews entire region to expected result, no SEND/WAIT error | Before/after/video, exact action, marker/return if exposed | Yes; black flash or ioctl success alone insufficient |
| E04 partial refresh | Controlled small region updates correctly without outside damage/error; genuinely partial | Region/coordinates/photos, mode/marker logs if exposed | Yes for partial PASS; full fallback means UNQUALIFIED partial; full-only diagnostic reading may continue |
| E05 ghosting | Record residue after 5 controlled changes; full refresh restores witness without observed objectionable residue | Fixed-light/exposure photos at 0/1/5 and after full | Persistent residue after full FAIL; partial traces documented; manufacturer quantitative threshold unknown |

## 6. Neonode

| ID | Expected result | Evidence | Blocking |
| --- | --- | --- | --- |
| N01 detection | Identify eventN named zForce-ir-touch; ABS_X/Y/PRESSURE, BTN_TOUCH; expected I²C client 0-0050 | Input devices, sysfs name/dev, I²C link, dmesg | Yes; event0/event1 alone not identity |
| N02 acquisition | Press/release produces expected events, no continuous phantom contacts | Timestamped validated evdev capture, physical position | Yes; UI click without raw trace leaves raw UNQUALIFIED |
| N03 axes | Physical right/down maps to UI right/down after dragon transformations | Raw/UI coordinates and landmark photos | Yes; advertised ABS bounds alone not calibration |
| N04 coverage | Centre, inset corners and four edge midpoints, 3 presses/release per zone reach target | 3×3 grid, raw/UI coordinates, hits/misses/photos | Yes for global PASS; failed zone remains FAIL, no silent partial qualification |

No measured pixel tolerance is established. Preserve offsets rather than
inventing precision. Never run Neonode programming/BSL/MASS_ERASE.

## 7. Frontlight

| ID | Expected result | Evidence | Blocking |
| --- | --- | --- | --- |
| F01 NTX chain | Character ntx_io matches sysfs, PMIC/MSP430 probe without critical errors | Node/sysfs, dmesg, candidate sources | Yes; documented minor 190 is not permission to fabricate a node |
| F02 off | Validated interface requests 0; actual panel illumination turns off | Requested level, observed stabilization, fixed-condition photo | Yes; failure prohibits increasing power |
| F03 levels | Proposed UI sequence 1→10→30→60→100→0, visible stable changes, effective final off | Requested values, fixed exposure photos, errors/times | Yes for light PASS; 100 is software limit, not proven thermal safety; stop earlier on anomalies |
| F04 light button | If mapped, button alone gives candidate's intended effect without reset | Input/button identity, event, level/photo before/after | Not for reader diagnostics if UI works; required to claim button qualified; unknown mapping → UNQUALIFIED |

Audited ioctl 241 takes integer 0–100, not a pointer; successful return alone
does not prove MSP430 probe or visible light. No ioctl is issued by this lot.

## 8. Exact observation interfaces and evidence collection

| Observation | Established interface | Limit |
| --- | --- | --- |
| Kernel | /proc/version, /proc/cmdline, /proc/uptime, dmesg | Preserved A kernel 2.6.35.3-850-gbc67621+; changed kernel requires new identity |
| Boot data | waveform_p, waveform_sz, hwcfg_p, hwcfg_sz command-line arguments | Presence not runtime integrity/panel readiness |
| E-Ink | /dev/fb0; /sys/class/graphics/fb0/{dev,rotate,bits_per_pixel} | hw_ready is internal, not a demonstrated sysfs file |
| Touch | /proc/bus/input/devices; /sys/class/input/eventN/device/name; eventN/dev; /dev/input/eventN | Input zForce-ir-touch differs in case from board zforce-ir-touch; expected I²C 0-0050 |
| Frontlight | /dev/ntx_io; /sys/class/misc/ntx_io/dev | Actual MSP430 visibility still unknown |
| LED | pmic_light.1/lit reference in recovery | Indicator, not frontlight; absolute sysfs path/pattern unqualified |
| Battery | /sys/class/power_supply/mc13892_bat/{capacity,status} candidate from audit | Presence/accuracy physically UNQUALIFIED |
| Bootstrap | /run/pmkb-ready, /proc/mounts | Volatile ready proves passage, not current mount/live reader |
| Profile/process | /tmp/pmkb HOME/XDG; identified /proc/PID/{cmdline,environ,status}; stdout/stderr | Not guaranteed log location; capture only necessary non-private fields |

Audited source locations/functions: drivers/video/mxc/mxc_epdc_fb.c
(epdc_firmware_func, mxc_epdc_fb_init_hw, initialization and SEND/WAIT),
mxc_epdc_fake_s1d13522.c (FW_IN_RAM),
drivers/input/touchscreen/zforce_i2c.c (probe/open/v2 replies),
mx50_ntx_io.c and PMIC/MSP430 transport (registration/light table),
drivers/watchdog/mxc_wdt.c (opening activates watchdog: do not open).
Some full source paths need confirmation in the archive. Exact successful
printk strings, including a guaranteed BootComplete spelling, are not established.
EPDC/waveform/HWCONFIG/zforce/input/I²C/MSP430/ntx_io/MMC/VFS/ext4/FAT/panic/oops
are search keywords, **not guaranteed literal messages**. Missing keywords
alone do not imply FAIL; retain the complete ring buffer first.

I provides no explicit syslogd/klogd, reader log redirection, or qualified
shell/USB/serial console. /var/log/messages, crash.log, pstore/ramoops and
/run/pmkb-boot.log are **not guaranteed**. Establish actual candidate paths
and capture channel; this documentation does not add them.

After **every test ID**, retain verdict/expected/actual result, relative time,
photo/video, dmesg delta and full capture, tool/version/return, relevant mount
and process state. Mark inaccessible evidence explicitly. Export volatile RAM
logs to the PC before shutdown through a separately qualified channel, never
to P2/P3. Hash captures privately. Do not publish serials, books, databases,
device.xml or .kobo.zip; those files are not PMKB boot evidence.

## 9. Immediate STOP

- Abnormal heat/odor/swelling/smoke or unstable electrical connection: stop
  and secure hardware; collecting logs never outranks electrical safety.
- P2 RW/write, unexpected pre-P1/MBR write, factory reset, repair/formatting,
  doubtful target/range: stop new commands, preserve evidence; no automatic
  restoration and no card removal during active operations.
- Wrong/RW P3, unexpected watchdog opening, unauthorized network/USB export
  or Neonode/MCU programming: stop the campaign.
- Panic/oops/reset loop, critical MMC error, unfinished refresh or light
  impossible to extinguish: STOP; collect safely without further stressing it.
- Missing essential observations or unlinked image/preflight: qualification
  STOP with UNQUALIFIED, not necessarily physical failure or immediate power cut.

STOP means no new test actions, **not** forced reboot/reset/restoration.
Absent immediate danger, preserve logs and determine active writes before shutdown.

## 10. Conceptual P2-based rollback — no execution or authorization

1. Suspend campaign, retain volatile evidence and timestamp state.
2. Verify offline P2 copy/reference hash and actual changes. Unknown/corrupt
   recovery means STOP; never modify P2.
3. Preserved original card is an option only in a separately authorized, safe
   intervention; it cannot promise boot if it was already broken.
4. If needed, use the **verified local P2 copy** as recovery-archive data to
   reconstruct a rescue Kobo P1 in a local file. Verify provenance/archives,
   geometry/filesystem/hashes offline; this temporarily abandons PMKB UI, not P2.
5. Prepare a separate P1-only plan, simulation, current target identity,
   failed-state backup and preservation checks. Obtain new specific approval.
6. Only after that future authorized operation, reread hashes and separately
   qualify rescue boot. Hashes alone never guarantee hardware success.

Never execute P2 init or factory reset: it can write P1/P3/U-Boot. P2 supplies
recovery data, not permission to activate destructive recovery. No physical
rollback commands are provided.

## 11. Future campaign record

Record trial/operator/date/USB condition, full candidate commit/image hash/size,
linked image/content reports, backup/plan/approvals, preserved-region hashes,
capture/export/tools, timed phases, each ID's verdict/evidence/next decision,
STOP and last proven stage. Every hardware ID remains **NOT TESTED** until run.
Unknown timing, log access, button mapping, calibration and post-exec mount-loss
behavior stay explicit. Successful first boot does not qualify suspend, USB,
Calibre, writable/persistent settings or long-term reliability.
