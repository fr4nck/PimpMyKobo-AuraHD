#!/usr/bin/env python3
"""Single command for the existing PimpMyKobo Aura HD tools."""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

VERSION = "0.2.0"
COMMANDS = {
    "preflight-koreader": ("preflight-koreader.py", "Aggregate offline KOReader checks; hardware remains unqualified."),
    "audit-arm-runtime": ("audit-arm-runtime.py", "Audit ARM ELF dependencies in a local rootfs read-only."),
    "gui": ("pmkb-gui.py", "Open the optional Qt workshop for local files only."),
    "inspect": ("inspect-aura-hd.py", "Inspect an image or device read-only."),
    "verify-recovery": ("verify-recovery.py", "Verify an extracted recovery tree read-only."),
    "import-legacy": ("import-legacy-backup.py", "Qualify historical local evidence."),
    "rebuild-rootfs": ("rebuild-rootfs.py", "Prepare or build P1 from local recovery evidence."),
    "simulate": ("restore-rootfs.py", "Plan or simulate P1 replacement in a new local disk image."),
    "prepare-p1": ("prepare-p1-restore.py", "Prepare a local, reviewable restoration plan."),
    "restore-p1": ("restore-p1-linux.py", "Check local evidence; physical modes require native Linux and explicit options."),
    "build-koreader-rootfs": ("build-koreader-rootfs.py", "Assemble/build an experimental KOReader-direct P1 rootfs."),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pmkb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Commands:\n" + "\n".join(f"  {name:17} {description}" for name, (_, description) in COMMANDS.items())
        + "\n\nUse pmkb COMMAND --help for arguments. No command: help only, no device access."
        + "\nPhysical restoration is refused under WSL and Windows; no automatic sudo.")
    parser.add_argument("--version", action="version", version=f"pmkb {VERSION}")
    parser.add_argument("command", choices=COMMANDS, nargs="?")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    script = Path(__file__).with_name(COMMANDS[args.command][0])
    previous = sys.argv
    try:
        # No shell, argument rewriting, device defaults or permission elevation.
        sys.argv = [str(script), *args.arguments]
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            if exc.code is not None and not isinstance(exc.code, int):
                print(exc.code, file=sys.stderr)
            return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        return 0
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
