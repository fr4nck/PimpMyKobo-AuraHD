#!/usr/bin/env python3
"""Assemble, and optionally build, a local experimental KOReader-direct P1 rootfs.

This tool merges three local, non-redistributed-together sources into a single
rootfs tree for the Aura HD E606C0 "boot Netronix -> Linux -> PMKB -> KOReader"
path: the repository's own ``experimental/offline-rootfs`` overlay, a local
extracted KOReader Kobo release, and a local directory of additional runtime
components (for example a Kobo-origin BusyBox/libc extracted from the user's
own backup). Nothing here is fetched from the network, mounted, or written to
a physical/block device. See docs/build-koreader-rootfs-spec-en.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOL_ROOT = Path(__file__).resolve().parent.parent
OVERLAY_ROOT = TOOL_ROOT / "experimental" / "offline-rootfs"
# Reviewed, first-party KOReader defaults profile (docs/offline-hardware-
# qualification-fr.md): demonstrated necessary so startup never reads/writes
# Kobo's own "Kobo eReader.conf" against a read-only P3. Not user-supplied,
# so treated like the overlay for the Nickel content scan.
READER_PROFILE_FILE = TOOL_ROOT / "experimental" / "offline-audit" / "defaults.custom.lua"
READER_PROFILE_REL = "opt/koreader/defaults.custom.lua"

_REBUILD_SPEC = importlib.util.spec_from_file_location(
    "pmkb_rebuild_rootfs_internal", Path(__file__).with_name("rebuild-rootfs.py")
)
_rebuild = importlib.util.module_from_spec(_REBUILD_SPEC)
assert _REBUILD_SPEC.loader
_REBUILD_SPEC.loader.exec_module(_rebuild)

# Directories that must exist in the image even if a source tree is sparse.
# "opt"/"opt/koreader" guarantee the KOReader mount point exists on its own.
SKELETON_DIRS = ("proc", "sys", "dev", "dev/input", "dev/pts", "run", "tmp",
                  "mnt", "mnt/onboard", "opt", "opt/koreader")

REQUIRED_ENTRYPOINTS = (
    "etc/init.d/rcS", "etc/inittab", "usr/bin/pmkb-check-offline",
    "usr/bin/pmkb-check-onboard", "usr/bin/pmkb-reader", "bin/kobo_config.sh",
    "opt/koreader/reader.lua", "opt/koreader/luajit", READER_PROFILE_REL,
)

# Best-effort, bounded scan: a hit means "look at this", not a hard proof.
NICKEL_NAME_PATTERN = re.compile(r"nickel|hindenburg|kobo\s*ereader\.conf", re.I)
NICKEL_CONTENT_NEEDLES = (b"Nickel", b"Hindenburg", b"nickel_conf", b"/usr/local/Kobo", b"KoboRoot.tgz")
MAX_SCAN_BYTES = 2 * 1024 * 1024


class _AssemblyError(RuntimeError):
    pass


def _report(*, status: str, errors: list[str], warnings: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "tool": "build-koreader-rootfs",
        "status": status,
        "complete": False,
        "physical_restore_eligible": False,
        "hardware_qualified": False,
        "errors": errors,
        "warnings": warnings or [],
        **extra,
    }


def _join(base: str, rel_dir: Path, name: str) -> str:
    parts = [p for p in (base, rel_dir.as_posix() if str(rel_dir) != "." else "") if p]
    parts.append(name)
    return "/".join(parts)


def _place_symlink(source: Path, destination_root: Path | None, rel: str,
                    manifest: dict[str, dict], *, write: bool) -> None:
    if rel in manifest:
        raise _AssemblyError(f"path collision while assembling rootfs: /{rel}")
    target = os.readlink(source)
    manifest[rel] = {"kind": "symlink", "target": target}
    if write:
        assert destination_root is not None
        dest = destination_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, dest)


def _copy_tree(source: Path, destination_root: Path | None, manifest: dict[str, dict],
                sources: dict[str, Path], *, base: str = "", write: bool,
                force_mode: int | None = None) -> None:
    """Record (and, if write, materialize) every entry of ``source`` under ``base``.

    Directories may be shared across calls (overlay, KOReader release, runtime
    components all contribute to e.g. ``bin/`` or ``etc/``); files and symlinks
    may not silently replace anything already placed.
    """
    source = Path(source).resolve(strict=True)
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        dirnames.sort()
        filenames.sort()
        rel_dir = Path(dirpath).relative_to(source)
        kept = []
        for name in dirnames:
            full = Path(dirpath) / name
            rel = _join(base, rel_dir, name)
            if full.is_symlink():
                _place_symlink(full, destination_root, rel, manifest, write=write)
                continue
            kept.append(name)
            existing = manifest.get(rel)
            if existing is not None and existing["kind"] != "dir":
                raise _AssemblyError(f"path collision while assembling rootfs: /{rel}")
            manifest.setdefault(rel, {"kind": "dir", "mode": 0o755})
            if write:
                assert destination_root is not None
                (destination_root / rel).mkdir(parents=True, exist_ok=True)
        dirnames[:] = kept
        for name in filenames:
            full = Path(dirpath) / name
            rel = _join(base, rel_dir, name)
            if rel in manifest:
                raise _AssemblyError(f"path collision while assembling rootfs: /{rel}")
            if full.is_symlink():
                _place_symlink(full, destination_root, rel, manifest, write=write)
                continue
            if not full.is_file():
                raise _AssemblyError(f"unsupported source entry (not a file, dir or symlink): /{rel}")
            mode = force_mode if force_mode is not None else stat.S_IMODE(full.stat().st_mode)
            size = full.stat().st_size
            digest = _rebuild.sha256_file(full)
            manifest[rel] = {"kind": "file", "mode": mode, "size": size, "sha256": digest}
            if size <= MAX_SCAN_BYTES:
                sources[rel] = full
            if write:
                assert destination_root is not None
                dest = destination_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full, dest)
                os.chmod(dest, mode)


def _add_skeleton_dirs(manifest: dict[str, dict], destination_root: Path | None, *, write: bool) -> None:
    for rel in SKELETON_DIRS:
        existing = manifest.get(rel)
        if existing is not None and existing["kind"] != "dir":
            raise _AssemblyError(f"path collision while assembling rootfs: /{rel}")
        manifest.setdefault(rel, {"kind": "dir", "mode": 0o755})
        if write:
            assert destination_root is not None
            (destination_root / rel).mkdir(parents=True, exist_ok=True)


def _place_reader_profile(destination_root: Path | None, manifest: dict[str, dict], *, write: bool) -> None:
    """Install the reviewed, Nickel-config-avoiding KOReader defaults profile.

    Demonstrated necessary, not merely proposed (see
    docs/offline-hardware-qualification-fr.md): without
    KOBO_LIGHT_ON_START=-1 and KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=false,
    KOReader's startup frontlight sync reads, and on a missing setting can
    try to write, Kobo's own "Kobo eReader.conf" - a real failure risk
    against this prototype's read-only P3. Placed before koreader_dir is
    merged, so a koreader_dir that already ships its own
    defaults.custom.lua collides (and fails loudly) instead of silently
    overriding this safety setting.
    """
    if READER_PROFILE_REL in manifest:
        raise _AssemblyError(f"path collision while assembling rootfs: /{READER_PROFILE_REL}")
    if not READER_PROFILE_FILE.is_file():
        raise _AssemblyError("experimental/offline-audit/defaults.custom.lua is missing from this checkout")
    manifest[READER_PROFILE_REL] = {
        "kind": "file", "mode": 0o644,
        "size": READER_PROFILE_FILE.stat().st_size,
        "sha256": _rebuild.sha256_file(READER_PROFILE_FILE),
    }
    if write:
        assert destination_root is not None
        dest = destination_root / READER_PROFILE_REL
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(READER_PROFILE_FILE, dest)
        os.chmod(dest, 0o644)


def _scan_for_nickel(manifest: dict[str, dict], sources: dict[str, Path]) -> list[str]:
    hits = [f"/{rel}: path name matches a Nickel/Kobo-userspace pattern"
            for rel in manifest if NICKEL_NAME_PATTERN.search(rel)]
    for rel, path in sorted(sources.items()):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for needle in NICKEL_CONTENT_NEEDLES:
            if needle in data:
                hits.append(f"/{rel}: content references {needle.decode()!r}")
                break
    return hits


def _first_party_file_paths() -> set[str]:
    """Relative paths of this checkout's own reviewed content: the overlay
    plus the KOReader defaults profile. Neither is user-supplied, so neither
    is content-scanned for Nickel references once merged (see
    scan_tree_for_nickel)."""
    manifest: dict[str, dict] = {}
    _copy_tree(OVERLAY_ROOT, None, manifest, {}, write=False, force_mode=0o755)
    paths = {rel for rel, entry in manifest.items() if entry["kind"] == "file"}
    paths.add(READER_PROFILE_REL)
    return paths


def scan_tree_for_nickel(root: Path) -> list[str]:
    """Scan an already-assembled rootfs *directory* (not pre-merge sources) for
    unintended Nickel/Kobo-userspace references.

    This is the entry point other local tools (for example a separate static
    audit) should call against this builder's materialized output, instead of
    reimplementing the merge or calling the pre-merge ``_copy_tree``/
    ``_scan_for_nickel`` helpers directly on the final tree: once the overlay,
    KOReader release and runtime components are merged on disk, a file's
    origin is no longer recoverable from the tree alone, so a naive re-scan
    would always flag this repository's own ``usr/bin/pmkb-reader`` comment
    ("bypassing ... Nickel paths") as a false positive. This function instead
    recomputes this checkout's own first-party content (the overlay plus the
    KOReader defaults profile, see ``_first_party_file_paths``) and excludes
    exactly those relative paths from the content scan, while still
    name-scanning every path including theirs.
    Read-only: never mounts, executes or modifies anything under ``root``.
    """
    root = Path(root).resolve(strict=True)
    excluded = _first_party_file_paths()
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        rel_dir = Path(dirpath).relative_to(root)
        for name in (*dirnames, *filenames):
            rel = _join("", rel_dir, name)
            if NICKEL_NAME_PATTERN.search(rel):
                hits.append(f"/{rel}: path name matches a Nickel/Kobo-userspace pattern")
        for name in filenames:
            rel = _join("", rel_dir, name)
            if rel in excluded:
                continue
            full = Path(dirpath) / name
            if full.is_symlink() or not full.is_file():
                continue
            try:
                if full.stat().st_size > MAX_SCAN_BYTES:
                    continue
                data = full.read_bytes()
            except OSError:
                continue
            for needle in NICKEL_CONTENT_NEEDLES:
                if needle in data:
                    hits.append(f"/{rel}: content references {needle.decode()!r}")
                    break
    return hits


def plan_rootfs(koreader_dir: Path, runtime_dir: Path) -> tuple[dict[str, Any], dict[str, dict]]:
    """Cross-platform, read-only dry run: validate inputs and compute the full manifest."""
    errors = []
    for label, path in (("koreader", koreader_dir), ("runtime", runtime_dir)):
        if _rebuild.looks_like_device(str(path)):
            errors.append(f"{label} path is a physical/block device and is forbidden")
    if not errors:
        if not koreader_dir.is_dir():
            errors.append("koreader input is not a directory")
        if not runtime_dir.is_dir():
            errors.append("runtime input is not a directory")
        if not OVERLAY_ROOT.is_dir():
            errors.append("experimental/offline-rootfs overlay is missing from this checkout")
    if errors:
        return _report(status="failed", errors=errors), {}
    manifest: dict[str, dict] = {}
    sources: dict[str, Path] = {}
    try:
        # The overlay is first-party and already reviewed in this repository: it
        # contributes manifest entries but is not content-scanned for Nickel
        # references (its comments may legitimately describe bypassing Nickel).
        _copy_tree(OVERLAY_ROOT, None, manifest, {}, write=False, force_mode=0o755)
        _add_skeleton_dirs(manifest, None, write=False)
        _place_reader_profile(None, manifest, write=False)
        _copy_tree(koreader_dir, None, manifest, sources, base="opt/koreader", write=False)
        _copy_tree(runtime_dir, None, manifest, sources, write=False)
    except _AssemblyError as exc:
        return _report(status="failed", errors=[str(exc)]), {}
    missing = [p for p in REQUIRED_ENTRYPOINTS if p not in manifest]
    errors = [f"required entry point missing after assembly: /{p}" for p in missing]
    nickel_hits = _scan_for_nickel(manifest, sources)
    if nickel_hits:
        errors.append(f"unexpected Nickel/Kobo-userspace references found ({len(nickel_hits)})")
    total_size = sum(entry.get("size", 0) for entry in manifest.values())
    files = [{"path": rel, **entry} for rel, entry in sorted(manifest.items())]
    report = _report(
        status="failed" if errors else "assembled",
        errors=errors,
        entries=len(manifest),
        apparent_size=total_size,
        nickel_scan=nickel_hits,
        files=files,
    )
    return report, manifest


def _verify_built_image(image: Path, manifest: dict[str, dict], workdir: Path) -> list[str]:
    """Re-read the built image (debugfs, read-only) and compare it with the manifest."""
    errors: list[str] = []
    paths = sorted(manifest)
    stats = _rebuild._debugfs_batch(image, [f"stat {_rebuild._quote_debugfs(p)}" for p in paths], workdir)
    for rel, entry in manifest.items():
        block = stats.get(f"stat {_rebuild._quote_debugfs(rel)}", "")
        kind_match = re.search(r"Type: (.+?)\s+Mode:\s+([0-7]+)", block)
        if not kind_match:
            errors.append(f"missing in image: /{rel}")
            continue
        kind, mode = kind_match.group(1).strip(), kind_match.group(2)
        if _rebuild.DEBUGFS_TYPES.get(kind) != entry["kind"]:
            errors.append(f"/{rel}: type {kind} != {entry['kind']}")
            continue
        if entry["kind"] != "symlink" and int(mode, 8) & 0o7777 != entry["mode"] & 0o7777:
            errors.append(f"/{rel}: mode {mode} != {entry['mode'] & 0o7777:04o}")
        if entry["kind"] == "symlink":
            fast = re.search(r'Fast link dest: "(.*)"', block)
            if fast and fast.group(1) != entry["target"]:
                errors.append(f"/{rel}: link -> {fast.group(1)!r} != {entry['target']!r}")
    dump_dir = workdir / "verify-content"
    dump_dir.mkdir()
    files = [rel for rel, entry in manifest.items() if entry["kind"] == "file"]
    targets = {rel: dump_dir / str(i) for i, rel in enumerate(files)}
    _rebuild._debugfs_batch(image, [f'dump {_rebuild._quote_debugfs(rel)} "{out}"' for rel, out in targets.items()], workdir)
    for rel in files:
        out = targets[rel]
        if not out.is_file():
            errors.append(f"cannot read /{rel} from image")
            continue
        digest = _rebuild.sha256_file(out)
        out.unlink()
        if digest != manifest[rel]["sha256"]:
            errors.append(f"/{rel}: content differs from assembled manifest")
    return errors


def build_rootfs(koreader_dir: Path, runtime_dir: Path, reference_recovery: Path,
                  output_path: Path, size: int) -> dict[str, Any]:
    """Linux-only: materialize the planned tree into a local ext4 P1 image file."""
    plan, manifest = plan_rootfs(koreader_dir, runtime_dir)
    if plan["status"] != "assembled":
        return plan
    errors = []
    for label, path in (("reference recovery", reference_recovery), ("output", output_path)):
        if _rebuild.looks_like_device(str(path)):
            errors.append(f"{label} path is a physical/block device and is forbidden")
    if not errors and not reference_recovery.is_file():
        errors.append("reference recovery input is not a regular file")
    if not errors and output_path.exists():
        errors.append("output already exists; implicit overwrite is forbidden")
    if not isinstance(size, int) or size <= 0:
        errors.append("output size must be a positive integer")
    if errors:
        return _report(status="failed", errors=errors)
    backend_errors = _rebuild.require_linux_backend()
    if backend_errors:
        return _report(status="failed", errors=backend_errors)
    part = output_path.with_name(output_path.name + ".part")
    build_manifest_path = output_path.with_name(output_path.name + ".koreader-build.json")
    if part.exists() or build_manifest_path.exists():
        return _report(status="failed", errors=["temporary output or build manifest already exists; refusing collision"])
    try:
        # The recoveryfs superblock stays the authority: its features are known
        # to mount under the Kobo kernel, unlike host mke2fs defaults.
        reference = _rebuild.read_ext_parameters(reference_recovery)
        block_size = reference["block_size"]
        blocks = size // block_size
        if blocks <= 0:
            raise RuntimeError("requested size is smaller than one ext4 block")
        with tempfile.TemporaryDirectory(prefix="pmkb-koreader-rootfs-") as td:
            td_path = Path(td)
            root = td_path / "root"
            root.mkdir()
            # Re-walk the same three sources in the same order as the validated
            # plan, sharing one manifest so a real collision still aborts here
            # even if it could not (deterministically) have passed planning.
            build_manifest: dict[str, dict] = {}
            _copy_tree(OVERLAY_ROOT, root, build_manifest, {}, write=True, force_mode=0o755)
            _add_skeleton_dirs(build_manifest, root, write=True)
            _place_reader_profile(root, build_manifest, write=True)
            _copy_tree(koreader_dir, root, build_manifest, {}, base="opt/koreader", write=True)
            _copy_tree(runtime_dir, root, build_manifest, {}, write=True)
            conf = td_path / "mke2fs.conf"
            conf.write_text(_rebuild.MKE2FS_CONF, encoding="utf-8")
            with open(part, "xb") as handle:
                handle.truncate(size)
            features = ",".join(["none", *reference["features"]])
            script = (
                "set -eu\n"
                f"chown -R 0:0 {shlex.quote(str(root))}\n"
                f"MKE2FS_CONFIG={shlex.quote(str(conf))} mke2fs -q -F -T pmkb -L rootfs "
                f"-b {block_size} -I {reference['inode_size']} -E root_owner=0:0 "
                f"-O {shlex.quote(features)} -d {shlex.quote(str(root))} {shlex.quote(str(part))} {blocks}\n"
            )
            _rebuild.run_checked(["fakeroot", "--", "sh", "-c", script])
            if part.stat().st_size != size:
                raise RuntimeError("built image size does not match requested P1 geometry")
            built = _rebuild.read_ext_parameters(part)
            for key in ("features", "block_size", "inode_size"):
                if built[key] != reference[key]:
                    raise RuntimeError(f"built ext4 {key} {built[key]} != recovery reference {reference[key]}")
            if built.get("label") != "rootfs":
                raise RuntimeError("built filesystem label is not 'rootfs'")
            fsck = subprocess.run(["e2fsck", "-f", "-n", str(part)], text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if fsck.returncode != 0:
                raise RuntimeError(f"e2fsck -f -n reported problems (exit {fsck.returncode})")
            verify_errors = _verify_built_image(part, manifest, td_path)
        if verify_errors:
            shown = verify_errors[:20] + ([f"... {len(verify_errors) - 20} more"] if len(verify_errors) > 20 else [])
            return {**_report(status="failed", errors=["built image does not match assembled manifest", *shown]),
                    "temporary_output": str(part)}
        digest = _rebuild.sha256_file(part)
        os.replace(part, output_path)
        report_out = {
            "schema_version": 1,
            "tool": "build-koreader-rootfs",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "experimental",
            "complete": True,
            "physical_restore_eligible": False,
            "hardware_qualified": False,
            "device": "E606C0",
            "rootfs_size": size,
            "rootfs_sha256": digest,
            "ext4": {
                "reference": "superblock of the recovery image",
                "features": reference["features"],
                "block_size": block_size,
                "inode_size": reference["inode_size"],
                "blocks": blocks,
                "unused_tail_bytes": size - blocks * block_size,
                "label": "rootfs",
            },
            "owner_policy": "root:root (uniform); per-file ownership is not yet supported",
            "entries": len(manifest),
            "nickel_scan": [],
            "warnings": [],
            "errors": [],
        }
        build_manifest_path.write_text(json.dumps(report_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report_out
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        return {**_report(status="failed", errors=[str(exc)]),
                "temporary_output": str(part) if part.exists() else None}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble (and optionally build) a local experimental KOReader-direct "
                     "P1 rootfs for Aura HD E606C0. Local files only.")
    parser.add_argument("koreader_dir", help="extracted KOReader Kobo release; its contents land under /opt/koreader")
    parser.add_argument("runtime_dir", help="additional local runtime components merged at the rootfs root "
                                             "(e.g. BusyBox/libc extracted from the user's own backup); never committed to git")
    parser.add_argument("--build", metavar="OUTPUT_IMAGE",
                        help="construct the local P1 image (Linux-only; requires --reference-recovery and --size)")
    parser.add_argument("--reference-recovery", help="local P2 recoveryfs image providing the authoritative ext4 parameters")
    parser.add_argument("--size", type=int, help="exact output P1 size in bytes")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    koreader_dir, runtime_dir = Path(args.koreader_dir), Path(args.runtime_dir)
    if args.build:
        if not args.reference_recovery or not args.size:
            parser.error("--build requires --reference-recovery and --size")
        result = build_rootfs(koreader_dir, runtime_dir, Path(args.reference_recovery), Path(args.build), args.size)
    else:
        result, _manifest = plan_rootfs(koreader_dir, runtime_dir)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PimpMyKobo-AuraHD — build-koreader-rootfs")
        print("LOCAL FILES ONLY — physical/block devices are forbidden.")
        for warning in result.get("warnings", []):
            print(f"WARNING: {warning}")
        if result["status"] == "assembled":
            print(f"ASSEMBLED: {result['entries']} entries, {result['apparent_size']:,} apparent bytes")
            print("Use --build under Linux/WSL2 with --reference-recovery and --size to construct the local image.")
        elif result["status"] == "experimental":
            print(f"EXPERIMENTAL BUILD OK: {args.build} ({result['rootfs_size']:,} bytes)")
            print(f"SHA-256: {result['rootfs_sha256']}")
            print("Not hardware-qualified. physical_restore_eligible=false.")
        else:
            print("REFUSED/FAILED:")
            for error in result.get("errors", []):
                print(f"  - {error}")
    return 0 if result["status"] in ("assembled", "experimental") else 1


if __name__ == "__main__":
    raise SystemExit(main())
