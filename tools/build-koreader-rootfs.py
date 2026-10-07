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
# Kobo's own "Kobo eReader.conf" against a read-only P3. Its SHA-256 identifies
# reviewed first-party content in post-merge reports; references remain visible.
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

# Best-effort, bounded inventory. A signature is evidence to classify, not
# by itself proof that the normal PMKB -> KOReader boot path depends on Nickel.
NICKEL_NAME_PATTERN = re.compile(r"nickel|hindenburg|kobo\s*ereader\.conf", re.I)
NICKEL_CONTENT_NEEDLES = (
    b"Nickel", b"Hindenburg", b"nickel_conf", b"/usr/local/Kobo",
    b"KoboRoot.tgz", b"Kobo eReader.conf",
)
MAX_SCAN_BYTES = 2 * 1024 * 1024

# Text files executed/read directly on the normal bootstrap path. References in
# arbitrary KOReader upstream files remain findings; only active use from this
# small contract can be blocking here.
BOOTSTRAP_TEXT_PATHS = frozenset({
    "etc/inittab", "etc/init.d/rcS", "usr/bin/pmkb-check-offline",
    "usr/bin/pmkb-check-onboard", "usr/bin/pmkb-reader", "bin/kobo_config.sh",
    "opt/koreader/reader.lua", READER_PROFILE_REL,
})


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


def _finding(rel: str, kind: str, signature: str, reason: str, *,
             blocking: bool = False, origin: str = "unknown") -> dict[str, Any]:
    return {
        "path": "/" + rel,
        "kind": kind,
        "signature": signature,
        "classification": "blocking" if blocking else "informational",
        "blocking": blocking,
        "origin": origin,
        "reason": reason,
    }


def _format_finding(finding: dict[str, Any]) -> str:
    level = "FAIL" if finding["blocking"] else "INFO"
    return (f"{finding['path']}: {level} {finding['reason']} "
            f"({finding['signature']}; origin={finding['origin']})")


def _generic_content_finding(rel: str, data: bytes, origin: str) -> dict[str, Any] | None:
    lowered = data.lower()
    for needle in NICKEL_CONTENT_NEEDLES:
        if needle.lower() in lowered:
            return _finding(
                rel, "content_reference", needle.decode(),
                "Nickel/Kobo-userspace reference retained for review",
                origin=origin,
            )
    return None


def _shell_command_groups(text: str) -> list[list[str]]:
    groups: list[list[str]] = []
    for line in text.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        try:
            tokens = list(lexer)
        except ValueError:
            # Bootstrap validation rejects malformed scripts independently.
            continue
        group: list[str] = []
        for token in tokens:
            if token and all(ch in ";&|" for ch in token):
                if group:
                    groups.append(group)
                    group = []
            else:
                group.append(token)
        if group:
            groups.append(group)
    return groups


def _is_nickel_command(token: str) -> bool:
    name = token.rsplit("/", 1)[-1].lower()
    return name in {"nickel", "nickel.sh", "hindenburg", "hindenburg.sh"}


def _dangerous_runtime_reference(token: str) -> bool:
    lowered = token.lower()
    return ("/usr/local/kobo" in lowered or "kobo ereader.conf" in lowered
            or "nickel_conf" in lowered)


def _shell_group_blocker(group: list[str]) -> tuple[str, str] | None:
    if not group:
        return None
    i = 0
    while i < len(group) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", group[i]):
        i += 1
    while i < len(group) and group[i] in {"exec", "command", "nohup", "env", "if", "then", "elif", "do"}:
        i += 1
        while i < len(group) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", group[i]):
            i += 1
    if i >= len(group):
        return None
    command = group[i]
    args = group[i + 1:]
    if _is_nickel_command(command):
        return ("bootstrap_launch", command)
    if command in {".", "source"} and any(
            _is_nickel_command(arg) or _dangerous_runtime_reference(arg) for arg in args):
        return ("bootstrap_dependency", " ".join(args))
    if command.rsplit("/", 1)[-1].lower() not in {"echo", "printf", "logger"}:
        for token in (command, *args):
            if _dangerous_runtime_reference(token):
                return ("bootstrap_dependency", token)
    return None


def _lua_active_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return "\n".join(line.split("--", 1)[0] for line in text.splitlines())


def _blocking_findings_for_file(rel: str, data: bytes, origin: str) -> list[dict[str, Any]]:
    if rel not in BOOTSTRAP_TEXT_PATHS:
        return []
    findings: list[dict[str, Any]] = []
    if rel == READER_PROFILE_REL:
        text = _lua_active_text(data)
        light = re.search(r"\bKOBO_LIGHT_ON_START\s*=\s*(-?\d+)\b", text)
        if light is None or int(light.group(1)) == -2:
            signature = "missing -> upstream default -2" if light is None else "KOBO_LIGHT_ON_START=-2"
            findings.append(_finding(
                rel, "normal_path_dependency", signature,
                "normal KOReader startup would read Nickel frontlight state",
                blocking=True, origin=origin,
            ))
        sync = re.search(r"\bKOBO_SYNC_BRIGHTNESS_WITH_NICKEL\s*=\s*(true|false)\b", text, re.I)
        if sync is None or sync.group(1).lower() != "false":
            signature = ("missing -> upstream default true" if sync is None
                         else "KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=true")
            findings.append(_finding(
                rel, "normal_path_dependency", signature,
                "KOReader settings would read/write Kobo eReader.conf",
                blocking=True, origin=origin,
            ))
        return findings

    if rel == "opt/koreader/reader.lua":
        active = _lua_active_text(data)
        direct = re.search(
            r"(?:io\.open|os\.execute)\s*\([^\n)]*"
            r"(?:Kobo eReader\.conf|/usr/local/Kobo|(?:^|[/\"'])nickel(?:[\"'/\s]|$))",
            active, re.I,
        )
        if direct:
            findings.append(_finding(
                rel, "normal_path_dependency", direct.group(0)[:160],
                "reader.lua directly accesses or launches a Nickel/Kobo userspace component",
                blocking=True, origin=origin,
            ))
        return findings

    text = data.decode("utf-8", errors="replace")
    if rel == "etc/inittab":
        processes = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(":", 3)
            processes.append(parts[3] if len(parts) == 4 else stripped)
        groups = [group for process in processes for group in _shell_command_groups(process)]
    else:
        groups = _shell_command_groups(text)
    for group in groups:
        blocker = _shell_group_blocker(group)
        if blocker:
            kind, signature = blocker
            findings.append(_finding(
                rel, kind, signature,
                "required bootstrap path actively launches or depends on Nickel/Kobo userspace",
                blocking=True, origin=origin,
            ))
    return findings


def _first_party_file_hashes() -> dict[str, str]:
    """Reviewed first-party files keyed by path and SHA-256."""
    manifest: dict[str, dict] = {}
    _copy_tree(OVERLAY_ROOT, None, manifest, {}, write=False, force_mode=0o755)
    hashes = {
        rel: entry["sha256"] for rel, entry in manifest.items()
        if entry["kind"] == "file"
    }
    if READER_PROFILE_FILE.is_file():
        hashes[READER_PROFILE_REL] = _rebuild.sha256_file(READER_PROFILE_FILE)
    return hashes


def _origin_for_digest(rel: str, digest: str | None, trusted: dict[str, str]) -> str:
    if rel not in trusted:
        return "external"
    return "first_party_verified" if digest == trusted[rel] else "first_party_modified"


def _findings_from_sources(manifest: dict[str, dict], sources: dict[str, Path]) -> list[dict[str, Any]]:
    trusted = _first_party_file_hashes()
    findings: list[dict[str, Any]] = []
    for rel in sorted(manifest):
        if not NICKEL_NAME_PATTERN.search(rel):
            continue
        entry = manifest[rel]
        origin = _origin_for_digest(rel, entry.get("sha256"), trusted) if entry["kind"] == "file" else "unknown"
        findings.append(_finding(
            rel, "path_reference", "path-name",
            "path name matches a Nickel/Kobo-userspace pattern", origin=origin,
        ))
    for rel, path in sorted(sources.items()):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        origin = _origin_for_digest(rel, manifest.get(rel, {}).get("sha256"), trusted)
        generic = _generic_content_finding(rel, data, origin)
        if generic:
            findings.append(generic)
        findings.extend(_blocking_findings_for_file(rel, data, origin))
    return findings


def _scan_tree_findings(root: Path) -> list[dict[str, Any]]:
    root = Path(root).resolve(strict=True)
    trusted = _first_party_file_hashes()
    findings: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        rel_dir = Path(dirpath).relative_to(root)
        for name in dirnames:
            rel = _join("", rel_dir, name)
            if NICKEL_NAME_PATTERN.search(rel):
                findings.append(_finding(
                    rel, "path_reference", "path-name",
                    "path name matches a Nickel/Kobo-userspace pattern",
                ))
        for name in filenames:
            rel = _join("", rel_dir, name)
            full = Path(dirpath) / name
            if full.is_symlink() or not full.is_file():
                continue
            try:
                size = full.stat().st_size
                if size > MAX_SCAN_BYTES:
                    if NICKEL_NAME_PATTERN.search(rel):
                        findings.append(_finding(
                            rel, "path_reference", "path-name",
                            "path name matches a Nickel/Kobo-userspace pattern",
                        ))
                    continue
                digest = _rebuild.sha256_file(full)
                data = full.read_bytes()
            except OSError:
                continue
            origin = _origin_for_digest(rel, digest, trusted)
            if NICKEL_NAME_PATTERN.search(rel):
                findings.append(_finding(
                    rel, "path_reference", "path-name",
                    "path name matches a Nickel/Kobo-userspace pattern", origin=origin,
                ))
            generic = _generic_content_finding(rel, data, origin)
            if generic:
                findings.append(generic)
            findings.extend(_blocking_findings_for_file(rel, data, origin))
    return findings


def scan_tree_for_nickel(root: Path) -> list[str]:
    """Return all signatures; informational references are never hidden."""
    return [_format_finding(finding) for finding in _scan_tree_findings(root)]


def classify_tree_for_nickel(root: Path) -> dict[str, Any]:
    """Separate normal-path dependencies from informational compatibility refs."""
    findings = _scan_tree_findings(root)
    blocking = [finding for finding in findings if finding["blocking"]]
    return {
        "findings": findings,
        "blocking_findings": blocking,
        "scan": [_format_finding(finding) for finding in findings],
        "blocking": [_format_finding(finding) for finding in blocking],
    }

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
        # First-party content is scanned too: references stay visible, while
        # SHA-256 only identifies their reviewed origin for classification.
        _copy_tree(OVERLAY_ROOT, None, manifest, sources, write=False, force_mode=0o755)
        _add_skeleton_dirs(manifest, None, write=False)
        _place_reader_profile(None, manifest, write=False)
        if READER_PROFILE_FILE.stat().st_size <= MAX_SCAN_BYTES:
            sources[READER_PROFILE_REL] = READER_PROFILE_FILE
        _copy_tree(koreader_dir, None, manifest, sources, base="opt/koreader", write=False)
        _copy_tree(runtime_dir, None, manifest, sources, write=False)
    except _AssemblyError as exc:
        return _report(status="failed", errors=[str(exc)]), {}
    missing = [p for p in REQUIRED_ENTRYPOINTS if p not in manifest]
    errors = [f"required entry point missing after assembly: /{p}" for p in missing]
    nickel_findings = _findings_from_sources(manifest, sources)
    nickel_blocking = [finding for finding in nickel_findings if finding["blocking"]]
    if nickel_blocking:
        errors.append(f"blocking Nickel/Kobo-userspace dependencies found ({len(nickel_blocking)})")
    warnings = []
    informational = len(nickel_findings) - len(nickel_blocking)
    if informational:
        warnings.append(f"Nickel/Kobo-userspace informational findings retained ({informational})")
    total_size = sum(entry.get("size", 0) for entry in manifest.values())
    files = [{"path": rel, **entry} for rel, entry in sorted(manifest.items())]
    report = _report(
        status="failed" if errors else "assembled",
        errors=errors,
        warnings=warnings,
        entries=len(manifest),
        apparent_size=total_size,
        nickel_scan=[_format_finding(finding) for finding in nickel_findings],
        nickel_findings=nickel_findings,
        nickel_blocking=[_format_finding(finding) for finding in nickel_blocking],
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
        owner_match = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", block)
        if not kind_match or not owner_match:
            errors.append(f"missing or unreadable metadata in image: /{rel}")
            continue
        kind, mode = kind_match.group(1).strip(), kind_match.group(2)
        owner = (int(owner_match.group(1)), int(owner_match.group(2)))
        if _rebuild.DEBUGFS_TYPES.get(kind) != entry["kind"]:
            errors.append(f"/{rel}: type {kind} != {entry['kind']}")
            continue
        if entry["kind"] != "symlink" and int(mode, 8) & 0o7777 != entry["mode"] & 0o7777:
            errors.append(f"/{rel}: mode {mode} != {entry['mode'] & 0o7777:04o}")
        if owner != (0, 0):
            errors.append(f"/{rel}: owner {owner[0]}:{owner[1]} != 0:0")
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
                # In restricted user namespaces, uid/gid 0 may be unmapped and
                # the real chown(2) returns EINVAL. Keep chown -R so fakeroot
                # records uniform root:root metadata, but do not forward the
                # ownership syscall to the underlying filesystem.
                "export FAKEROOTDONTTRYCHOWN=1\n"
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
            "nickel_scan": plan.get("nickel_scan", []),
            "nickel_findings": plan.get("nickel_findings", []),
            "nickel_blocking": plan.get("nickel_blocking", []),
            "warnings": plan.get("warnings", []),
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
