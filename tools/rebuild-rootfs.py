#!/usr/bin/env python3
"""Build a local Aura HD rootfs image from a verified PMKB backup.

The construction backend is deliberately Linux-only and operates on local files.
Physical/block-device paths are rejected. No restore operation exists here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHUNK = 4 * 1024 * 1024
SUPPORTED_BACKUP_SCHEMA = 1
PHYSICALDRIVE_RE = re.compile(r"^\\\\[.?]\\PhysicalDrive\d+$", re.I)
REQUIRED_TOOLS = ("mke2fs", "debugfs", "dumpe2fs", "e2fsck", "fakeroot", "tar")


def looks_like_device(value: str) -> bool:
    unix_raw = value.strip().replace("\\", "/")
    if unix_raw.startswith("//"):
        return True
    raw = value.strip().replace("/", "\\")
    if PHYSICALDRIVE_RE.match(raw):
        return True
    unix = value.strip().replace("\\", "/")
    if unix == "/dev" or unix.startswith("/dev/"):
        return True
    resolved = str(Path(value).resolve()).replace("\\", "/")
    return resolved == "/dev" or resolved.startswith("/dev/") or resolved.startswith("//")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("backup manifest root must be an object")
    return value


def _components(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("components")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _component(manifest: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((x for x in _components(manifest) if x.get("name") == name), None)


def _partitions(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    mbr = manifest.get("mbr")
    value = mbr.get("partitions") if isinstance(mbr, dict) else manifest.get("partitions")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _partition(manifest: dict[str, Any], number: int) -> dict[str, Any] | None:
    return next((x for x in _partitions(manifest) if x.get("number") == number), None)


def _is_e606c0(manifest: dict[str, Any]) -> bool:
    ident = manifest.get("identification")
    if isinstance(ident, dict):
        if ident.get("aura_hd_e606c0") is True:
            return True
        hw = ident.get("hwconfig")
        if isinstance(hw, dict):
            pcb = hw.get("pcb")
            if isinstance(pcb, dict) and pcb.get("raw") == 28 and pcb.get("decoded") == "E606C0":
                return True
    return manifest.get("device") == "E606C0"


def _component_hash(component: dict[str, Any]) -> str | None:
    for key in ("sha256_destination", "sha256", "sha256_stream"):
        value = component.get(key)
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
            return value.lower()
    return None


def preflight(manifest_path: Path, recovery_path: Path, output_path: Path, *, accept_legacy_import: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for label, path in (("manifest", manifest_path), ("recovery", recovery_path), ("output", output_path)):
        if looks_like_device(str(path)):
            errors.append(f"{label} path is a physical/block device and is forbidden")
    if errors:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "ok": False, "errors": errors, "warnings": warnings}
    try:
        if not manifest_path.is_file():
            raise ValueError("manifest input is not a regular file")
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "ok": False, "errors": [f"cannot read backup manifest: {exc}"], "warnings": warnings}
    if manifest.get("schema_version") != SUPPORTED_BACKUP_SCHEMA:
        errors.append(f"unsupported backup schema: {manifest.get('schema_version')!r}")
    imported = manifest.get("tool") == "import-legacy-backup" or "provenance" in manifest or "contract" in manifest
    if imported:
        if not accept_legacy_import:
            errors.append("legacy import requires explicit --accept-legacy-import")
        try:
            spec = importlib.util.spec_from_file_location("legacy_backup", Path(__file__).with_name("import-legacy-backup.py"))
            legacy = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(legacy)
            legacy.regular(manifest_path)
            legacy.reject_device(output_path)
            legacy.validate_import(manifest, manifest_path, recovery_path)
            warnings.extend(manifest["warnings"])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"legacy import refused: {exc}")
    elif manifest.get("complete") is not True or manifest.get("status") not in ("complete", "ok"):
        errors.append("backup manifest is not complete")
    if not _is_e606c0(manifest):
        errors.append("backup manifest does not identify E606C0")
    p1 = _partition(manifest, 1)
    p1_component = _component(manifest, "p1_rootfs")
    p1_size = p1.get("size") if p1 else None
    if not isinstance(p1_size, int) and p1_component:
        p1_size = p1_component.get("size")
    if not isinstance(p1_size, int) or p1_size <= 0:
        errors.append("backup manifest has no valid P1 size")
    recovery = _component(manifest, "p2_recoveryfs")
    if recovery is None:
        legacy = manifest.get("recovery")
        recovery = legacy if isinstance(legacy, dict) else None
    if recovery is None or recovery.get("status", "verified") != "verified":
        errors.append("backup manifest has no verified P2 recovery component")
    else:
        expected_size = recovery.get("size")
        expected_sha = _component_hash(recovery)
        if not isinstance(expected_size, int) or expected_size <= 0:
            errors.append("backup manifest has no valid recovery size")
        if expected_sha is None:
            errors.append("backup manifest has no valid recovery SHA-256")
        try:
            if not recovery_path.is_file():
                errors.append("recovery input is not a regular file")
            else:
                if isinstance(expected_size, int) and recovery_path.stat().st_size != expected_size:
                    errors.append("recovery size does not match backup manifest")
                if expected_sha is not None and sha256_file(recovery_path) != expected_sha:
                    errors.append("recovery SHA-256 does not match backup manifest")
        except OSError as exc:
            errors.append(f"cannot read recovery input: {exc}")
    if output_path.exists():
        errors.append("output already exists; implicit overwrite is forbidden")
    elif isinstance(p1_size, int):
        try:
            if shutil.disk_usage(output_path.parent).free < p1_size:
                errors.append("insufficient free space for rootfs image")
        except OSError as exc:
            errors.append(f"cannot determine destination free space: {exc}")
    result: dict[str, Any] = {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed" if errors else "ready", "ok": False, "errors": errors, "warnings": warnings}
    if not errors:
        result.update({"rootfs_size": p1_size, "backup_manifest_sha256": sha256_file(manifest_path), "target_fingerprint": manifest.get("target_fingerprint"), "recovery_sha256": _component_hash(recovery or {})})
        if imported:
            result.update(input_provenance=manifest["provenance"], physical_restore_eligible=False)
    return result


def require_linux_backend() -> list[str]:
    if sys.platform != "linux":
        return ["rootfs construction requires Linux (native, WSL2, VM, or live USB)"]
    return [f"required Linux tool not found: {tool}" for tool in REQUIRED_TOOLS if shutil.which(tool) is None]


def run_checked(argv: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)


# Superblock flags that describe a filesystem's state, not its layout: never copied.
RUNTIME_FEATURES = frozenset({"needs_recovery", "orphan_present"})
# Empty mke2fs configuration: the host's /etc/mke2fs.conf must not add features
# (metadata_csum, 64bit, orphan_file...) that the Kobo 2.6.35 kernel cannot mount.
MKE2FS_CONF = "[defaults]\n\n[fs_types]\n\tpmkb = {\n\t}\n"
DEBUGFS_TYPES = {
    "regular": "file", "directory": "dir", "symlink": "symlink",
    "character special": "chr", "block special": "blk", "FIFO": "fifo", "socket": "sock",
}


def read_ext_parameters(image: Path) -> dict[str, Any]:
    """Layout parameters of an ext2/3/4 image, read with ``dumpe2fs -h`` (read-only)."""
    out = subprocess.run(["dumpe2fs", "-h", str(image)], text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, check=True).stdout
    params: dict[str, Any] = {}
    for line in out.splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "Filesystem features":
            params["features"] = sorted(f for f in value.split() if f != "(none)" and f not in RUNTIME_FEATURES)
        elif key == "Block size":
            params["block_size"] = int(value)
        elif key == "Inode size":
            params["inode_size"] = int(value)
        elif key == "Filesystem volume name":
            params["label"] = "" if value == "<none>" else value
    missing = [k for k in ("features", "block_size", "inode_size") if k not in params]
    if missing:
        raise RuntimeError(f"cannot read ext4 parameters ({', '.join(missing)}) from {image.name}")
    return params


def _member_path(name: str) -> str:
    path = name.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.strip("/")


def _member_kind(member: tarfile.TarInfo) -> str:
    if member.isdir():
        return "dir"
    if member.issym():
        return "symlink"
    if member.ischr():
        return "chr"
    if member.isblk():
        return "blk"
    if member.isfifo():
        return "fifo"
    return "file"  # regular files and hard links


def _validate_archive(tf: tarfile.TarFile) -> tuple[dict[str, tarfile.TarInfo], dict[str, str], bytes | None]:
    """Reject unsafe members; return the final entry per path, file SHA-256s and fs.md5sum."""
    members = tf.getmembers()
    if not members:
        raise RuntimeError("fs.tgz is empty")
    entries: dict[str, tarfile.TarInfo] = {}
    for member in members:
        name = member.name.replace("\\", "/")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"unsafe archive path: {member.name}")
        if member.islnk():
            target = Path(member.linkname.replace("\\", "/"))
            if target.is_absolute() or ".." in target.parts:
                raise RuntimeError(f"unsafe archive hard link: {member.name}")
        # Symlink targets may be absolute or use "..": that is normal in a rootfs
        # (e.g. busybox applets) and tar stores them without following them.
        rel = _member_path(member.name)
        if rel:
            entries[rel] = member
    # What must never happen is extracting *through* a symlink of the archive,
    # which could write outside the temporary extraction directory.
    symlinks = {rel for rel, m in entries.items() if m.issym()}
    for rel in entries:
        parts = rel.split("/")
        for i in range(1, len(parts)):
            if "/".join(parts[:i]) in symlinks:
                raise RuntimeError(f"unsafe archive path through a symlink: {rel}")
    hashes: dict[str, str] = {}
    md5sum: bytes | None = None
    for rel, member in entries.items():
        if not member.isreg():
            continue
        handle = tf.extractfile(member)
        if handle is None:
            raise RuntimeError(f"cannot read archive member: {member.name}")
        h = hashlib.sha256()
        data = bytearray() if rel == "fs.md5sum" else None
        while chunk := handle.read(CHUNK):
            h.update(chunk)
            if data is not None:
                data.extend(chunk)
        hashes[rel] = h.hexdigest()
        if data is not None:
            md5sum = bytes(data)
    return entries, hashes, md5sum


def _fakeroot_build_script(fs_tgz: Path, root: Path, part: Path, conf: Path,
                           params: dict[str, Any], blocks: int) -> str:
    # One fakeroot process owns both extraction and mke2fs -d.  This is essential:
    # fakeroot's synthetic UID/GID and device-node metadata only exists inside that
    # process.  All paths are local temporary/output files, never block devices.
    q = shlex.quote
    features = ",".join(["none", *params["features"]])
    return "set -eu\n" + \
        f"mkdir -p {q(str(root))}\n" + \
        f"tar --numeric-owner --same-owner --same-permissions -xzf {q(str(fs_tgz))} -C {q(str(root))}\n" + \
        f"MKE2FS_CONFIG={q(str(conf))} mke2fs -q -F -T pmkb -L rootfs -b {params['block_size']} " \
        f"-I {params['inode_size']} -O {q(features)} -d {q(str(root))} {q(str(part))} {blocks}\n"


def _debugfs_batch(image: Path, commands: list[str], workdir: Path) -> dict[str, str]:
    """Run read-only debugfs commands (no -w) and return each command's output."""
    script = workdir / "debugfs.cmd"
    script.write_text("\n".join(commands) + "\n", encoding="utf-8")
    out = subprocess.run(["debugfs", "-f", str(script), str(image)], text=True, errors="replace",
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    blocks: dict[str, str] = {}
    current: str | None = None
    for line in out.splitlines():
        if line.startswith("debugfs: "):
            current = line[len("debugfs: "):]
            blocks[current] = ""
        elif current is not None:
            blocks[current] += line + "\n"
    return blocks


def _quote_debugfs(path: str) -> str:
    if '"' in path or "\n" in path:
        raise RuntimeError(f"path cannot be verified with debugfs: {path!r}")
    return f'"/{path}"'


def verify_image(image: Path, entries: dict[str, tarfile.TarInfo], hashes: dict[str, str],
                 md5sum: bytes | None, workdir: Path) -> tuple[dict[str, Any], list[str]]:
    """Re-read the built image (debugfs, read-only) and compare it with fs.tgz."""
    errors: list[str] = []
    stats = _debugfs_batch(image, [f"stat {_quote_debugfs(p)}" for p in entries], workdir)
    slow_links: list[str] = []
    failed: set[str] = set()
    metadata_ok = 0
    for rel, member in entries.items():
        block = stats.get(f"stat {_quote_debugfs(rel)}", "")
        kind = re.search(r"Type: (.+?)\s+Mode:\s+([0-7]+)", block)
        owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", block)
        if not kind or not owner:
            errors.append(f"missing in image: /{rel}")
            continue
        problems = []
        expected = _member_kind(member)
        if DEBUGFS_TYPES.get(kind.group(1).strip()) != expected:
            problems.append(f"type {kind.group(1).strip()} != {expected}")
        if expected != "symlink" and int(kind.group(2), 8) & 0o7777 != member.mode & 0o7777:
            problems.append(f"mode {kind.group(2)} != {member.mode & 0o7777:04o}")
        if (int(owner.group(1)), int(owner.group(2))) != (member.uid, member.gid):
            problems.append(f"owner {owner.group(1)}:{owner.group(2)} != {member.uid}:{member.gid}")
        if expected == "symlink":
            fast = re.search(r'Fast link dest: "(.*)"', block)
            if fast:
                if fast.group(1) != member.linkname:
                    problems.append(f"link -> {fast.group(1)!r} != {member.linkname!r}")
            else:
                slow_links.append(rel)
        if expected in ("chr", "blk"):
            dev = re.search(r"Device major/minor number: (\d+):(\d+)", block)
            if not dev or (int(dev.group(1)), int(dev.group(2))) != (member.devmajor, member.devminor):
                problems.append(f"device {dev.group(0) if dev else 'missing'} != {member.devmajor}:{member.devminor}")
        if problems:
            errors.append(f"/{rel}: " + "; ".join(problems))
            failed.add(rel)
        elif rel not in slow_links:
            metadata_ok += 1  # slow symlinks are counted once their target is checked

    # Content: dump every regular file and every slow symlink target, then compare.
    dump_dir = workdir / "content"
    dump_dir.mkdir()
    targets = {rel: dump_dir / str(i) for i, rel in enumerate([*hashes, *slow_links])}
    _debugfs_batch(image, [f'dump {_quote_debugfs(rel)} "{out}"' for rel, out in targets.items()], workdir)
    content_ok = 0
    md5_of: dict[str, str] = {}
    for rel, expected_sha in hashes.items():
        out = targets[rel]
        if not out.is_file():
            errors.append(f"cannot read /{rel} from image")
            continue
        data_sha, data_md5 = hashlib.sha256(), hashlib.md5()
        with out.open("rb") as handle:
            while chunk := handle.read(CHUNK):
                data_sha.update(chunk)
                data_md5.update(chunk)
        out.unlink()
        md5_of[rel] = data_md5.hexdigest()
        if data_sha.hexdigest() == expected_sha:
            content_ok += 1
        else:
            errors.append(f"/{rel}: content differs from fs.tgz")
    for rel in slow_links:
        out = targets[rel]
        target = out.read_bytes().decode("utf-8", "surrogateescape") if out.is_file() else None
        if target != entries[rel].linkname:
            errors.append(f"/{rel}: link -> {target!r} != {entries[rel].linkname!r}")
        elif rel not in failed:
            metadata_ok += 1

    md5_report: dict[str, Any] = {"present": md5sum is not None, "entries": 0, "matched": 0,
                                  "mismatched": [], "missing": []}
    if md5sum is not None:
        for line in md5sum.decode("utf-8", "surrogateescape").splitlines():
            match = re.match(r"^\\?([0-9a-fA-F]{32})\s+[ *]?(.+)$", line.strip())
            if not match:
                continue
            md5_report["entries"] += 1
            rel = _member_path(match.group(2))
            if rel not in md5_of:
                md5_report["missing"].append(rel)
            elif md5_of[rel] == match.group(1).lower():
                md5_report["matched"] += 1
            else:
                md5_report["mismatched"].append(rel)
        if md5_report["mismatched"] or md5_report["missing"]:
            errors.append(f"fs.md5sum: {len(md5_report['mismatched'])} mismatched, "
                          f"{len(md5_report['missing'])} missing")
    special = sum(1 for m in entries.values() if _member_kind(m) in ("chr", "blk", "fifo"))
    checks = {
        "metadata": {"entries": len(entries), "verified": metadata_ok},
        "content": {"files": len(hashes), "verified": content_ok},
        "symlinks": sum(1 for m in entries.values() if m.issym()),
        "special_files": special,
        "fs_md5sum": md5_report,
    }
    return checks, errors


def build_rootfs(manifest_path: Path, recovery_path: Path, output_path: Path, *, accept_legacy_import: bool = False) -> dict[str, Any]:
    result = preflight(manifest_path, recovery_path, output_path, accept_legacy_import=accept_legacy_import)
    if result["status"] != "ready":
        return result
    backend_errors = require_linux_backend()
    if backend_errors:
        result.update(status="failed", errors=backend_errors)
        return result
    p1_size = int(result["rootfs_size"])
    part = output_path.with_name(output_path.name + ".part")
    rebuild_manifest = output_path.with_name(output_path.name + ".rebuild.json")
    if part.exists() or rebuild_manifest.exists():
        result.update(status="failed", errors=["temporary output or rebuild manifest already exists; refusing collision"])
        return result
    try:
        # The Kobo-made recoveryfs is the reference for ext4 layout: its features are
        # known to be supported by the Kobo kernel, unlike the host mke2fs defaults.
        reference = read_ext_parameters(recovery_path)
        block_size = reference["block_size"]
        blocks = p1_size // block_size
        if blocks <= 0:
            raise RuntimeError("P1 size is smaller than one ext4 block")
        with tempfile.TemporaryDirectory(prefix="pmkb-rebuild-") as td:
            td_path = Path(td)
            fs_tgz = td_path / "fs.tgz"
            run_checked(["debugfs", "-R", f"dump /upgrade/fs.tgz {fs_tgz}", str(recovery_path)])
            if not fs_tgz.is_file() or fs_tgz.stat().st_size == 0:
                raise RuntimeError("required recovery artifact missing or empty: /upgrade/fs.tgz")
            with tarfile.open(fs_tgz, "r:gz") as tf:
                entries, hashes, md5sum = _validate_archive(tf)
            conf = td_path / "mke2fs.conf"
            conf.write_text(MKE2FS_CONF, encoding="utf-8")
            # Exact P1 geometry: the image is P1 bytes long; the filesystem uses whole
            # blocks and the remainder (if any) stays zero, as on the original card.
            with open(part, "xb") as handle:
                handle.truncate(p1_size)
            script = _fakeroot_build_script(fs_tgz, td_path / "root", part, conf, reference, blocks)
            run_checked(["fakeroot", "--", "sh", "-c", script])
            if part.stat().st_size != p1_size:
                raise RuntimeError("rebuilt image size does not match P1 geometry")
            built = read_ext_parameters(part)
            for key in ("features", "block_size", "inode_size"):
                if built[key] != reference[key]:
                    raise RuntimeError(f"rebuilt ext4 {key} {built[key]} != recovery reference {reference[key]}")
            if built.get("label") != "rootfs":
                raise RuntimeError("rebuilt filesystem label is not 'rootfs'")
            fsck = subprocess.run(["e2fsck", "-f", "-n", str(part)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if fsck.returncode != 0:
                raise RuntimeError(f"e2fsck -f -n reported problems (exit {fsck.returncode})")
            checks, verify_errors = verify_image(part, entries, hashes, md5sum, td_path)
        if verify_errors:
            shown = verify_errors[:20] + ([f"... {len(verify_errors) - 20} more"] if len(verify_errors) > 20 else [])
            return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "complete": False, "ok": False,
                    "errors": ["rebuilt image does not match fs.tgz", *shown], "warnings": [],
                    "checks": checks, "temporary_output": str(part)}
        digest = sha256_file(part)
        os.replace(part, output_path)
        warnings = list(result["warnings"])
        if md5sum is None:
            warnings.append("fs.tgz contains no fs.md5sum; content verified against fs.tgz only")
        report = {
            "schema_version": 1,
            "tool": "rebuild-rootfs",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "complete": True,
            "device": "E606C0",
            "backup_manifest_sha256": result["backup_manifest_sha256"],
            "target_fingerprint": result.get("target_fingerprint"),
            "recovery_sha256": result.get("recovery_sha256"),
            "rootfs_size": p1_size,
            "rootfs_sha256": digest,
            "ext4": {
                "reference": "superblock of the recovery image",
                "features": reference["features"],
                "block_size": block_size,
                "inode_size": reference["inode_size"],
                "blocks": blocks,
                "unused_tail_bytes": p1_size - blocks * block_size,
                "label": "rootfs",
            },
            "checks": {"size": True, "e2fsck": "clean", "ext4_parameters": True, **checks},
            "archive_entries": len(entries),
            "special_entries": checks["special_files"],
            "warnings": warnings,
            "errors": [],
        }
        if "input_provenance" in result:
            report.update(input_provenance=result["input_provenance"], physical_restore_eligible=False)
        rebuild_manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    except (OSError, subprocess.CalledProcessError, RuntimeError, tarfile.TarError) as exc:
        return {"schema_version": 1, "tool": "rebuild-rootfs", "status": "failed", "complete": False, "ok": False, "errors": [str(exc)], "warnings": [], "temporary_output": str(part) if part.exists() else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild a local Aura HD rootfs image from a verified PMKB backup")
    parser.add_argument("backup_manifest")
    parser.add_argument("recovery_image")
    parser.add_argument("output_image")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--build", action="store_true", help="perform Linux-only local image construction")
    parser.add_argument("--accept-legacy-import", action="store_true", help="accept declared historical association for local reconstruction only")
    args = parser.parse_args()
    paths = (Path(args.backup_manifest), Path(args.recovery_image), Path(args.output_image))
    result = (build_rootfs if args.build else preflight)(*paths, accept_legacy_import=args.accept_legacy_import)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PimpMyKobo-AuraHD — rebuild-rootfs")
        print("LOCAL FILES ONLY — physical/block devices are forbidden.")
        for warning in result.get("warnings", []):
            print(f"WARNING: {warning}")
        if result["status"] == "ready":
            print(f"READY: local inputs validated; planned P1 size = {result['rootfs_size']:,} bytes")
            print("Use --build under Linux/WSL2 to construct the local image.")
        elif result["status"] == "ok":
            print(f"OK: rebuilt image {args.output_image} ({result['rootfs_size']:,} bytes)")
            print(f"SHA-256: {result['rootfs_sha256']}")
        else:
            print("REFUSED/FAILED:")
            for error in result.get("errors", []):
                print(f"  - {error}")
    return 0 if result["status"] in ("ready", "ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
