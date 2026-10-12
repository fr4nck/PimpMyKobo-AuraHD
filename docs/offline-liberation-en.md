# E606C0 offline liberation prototype

Approved direction, 3 October 2026: replace the Kobo application environment with direct KOReader startup. Physical restoration authorization remains withdrawn. Work is limited to new local files.

The first prototype retains the existing bootloader, kernel, HWCONFIG and E-Ink data. It combines explicitly selected GNU runtime components from private local evidence with official `koreader-kobo` v2026.07.1 and `experimental/offline-rootfs`. It is not yet a fully source-rebuilt or fully libre hardware stack. No private binaries are distributed in this repository.

The experimental init contains no Nickel/Hindenburg startup, stock update processing, automatic FAT repair, formatting or partition changes. It does not install Wi-Fi modules or module-autoload rules. The reader launch guard refuses missing/unknown network state and any interface other than loopback. This guard does not prove the absence of all kernel or hardware communications.

P3 is mounted read-only; KOReader uses temporary settings and caches. Direct LuaJIT startup bypasses the ordinary Kobo launcher and its exit paths. No automatic reader retry, return to Nickel or reboot is defined by this init. A pending `KoboRoot.tgz` in the actual backup would be applied by stock startup, but is never interpreted by the new init.

ARM BusyBox and LuaJIT run under QEMU user-mode with an isolated network namespace. All 36 bundled KOReader ELF libraries load with the selected runtime. This uses the PC kernel, not the Aura HD kernel. Synthetic tests exercise the network guard and shell parsing without running hardware commands.

The local experimental image is checked with read-only e2fsck. Its distinct report uses `status=experimental`, `complete=false`, `physical_restore_eligible=false`; it is not a recovery rebuild report. Existing reconstruction/simulation evidence must not qualify this different image.

Boot, device-node cold-plug, E-Ink initialization/rotation/refresh, touch, frontlight, battery, suspend, power, kernel watchdog and USB remain unqualified. Hot-plug is not implemented and settings are not persistent. No bootability or zero-traffic hardware guarantee is made. Any hardware trial requires a separately reviewed validation/rollback contract and renewed explicit authorization.

Sources: [official release](https://github.com/koreader/koreader/releases/tag/v2026.07.1), [dragon support](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua), [reference Kobo launcher](https://github.com/koreader/koreader/blob/v2026.07.1/platform/kobo/koreader.sh). [okreader](https://github.com/lgeek/okreader) is a historical reference, not a qualified ready-to-install Aura HD image.
