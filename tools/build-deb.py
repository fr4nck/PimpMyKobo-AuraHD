#!/usr/bin/env python3
"""Build a local .deb with dpkg-deb; never install it or access a device."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("pmkb", Path(__file__).with_name("pmkb.py"))
pmkb = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(pmkb)

PACKAGE = "pimpmykobo-aura-hd"
SCRIPTS = ("pmkb.py", *(script for script, _ in pmkb.COMMANDS.values()))
DOCS = ("cli-install-fr.md", "cli-install-en.md", "inspect-aura-hd-fr.md", "inspect-aura-hd-en.md",
        "verify-recovery-fr.md", "verify-recovery-en.md", "import-legacy-backup-fr.md",
        "import-legacy-backup-en.md", "rebuild-rootfs-spec-fr.md", "rebuild-rootfs-spec-en.md",
        "restore-rootfs-simulation-fr.md", "restore-rootfs-simulation-en.md",
        "prepare-p1-restore-fr.md", "restore-p1-linux-fr.md", "restore-p1-linux-en.md")
LAUNCHER = '''#!/usr/bin/python3
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "lib" / "pimpmykobo-aura-hd" / "pmkb.py"), run_name="__main__")
'''


def reject_device(path: Path) -> None:
    def check(value: str) -> None:
        raw = value.replace("\\", "/").lower()
        if raw.startswith("//") or raw == "/dev" or raw.startswith("/dev/"):
            raise ValueError("device/UNC output paths are forbidden")
    check(str(path))
    check(str(path.resolve()))


def normalized_copy(source: Path, destination: Path) -> None:
    # Windows checkouts may use CRLF; executable Linux shebangs require LF.
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    destination.chmod(0o644)


def stage_package(source: Path, destination: Path, maintainer: str) -> dict:
    if not re.fullmatch(r"[^<>\r\n]+ <[^<>\s@]+@[^<>\s@]+>", maintainer):
        raise ValueError("maintainer must be 'Name <email>' on a single line")
    reject_device(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("package staging destination must not exist")
    destination.mkdir()
    library = destination / "usr/lib" / PACKAGE
    docs = destination / "usr/share/doc" / PACKAGE
    for script in SCRIPTS:
        normalized_copy(source / "tools" / script, library / script)
    for document in DOCS:
        normalized_copy(source / "docs" / document, docs / document)
    launcher = destination / "usr/bin/pmkb"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(LAUNCHER.encode("utf-8")); launcher.chmod(0o755)
    files = sorted(path for path in destination.rglob("*") if path.is_file())
    hashes = {path.relative_to(destination).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (docs / "build-info.json").write_bytes((json.dumps({"package": PACKAGE, "version": pmkb.VERSION,
        "files_sha256": hashes}, indent=2) + "\n").encode("utf-8"))
    control = destination / "DEBIAN"; control.mkdir()
    size = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    (control / "control").write_bytes((
        f"Package: {PACKAGE}\nVersion: {pmkb.VERSION}\nArchitecture: all\n"
        f"Maintainer: {maintainer}\nSection: utils\nPriority: optional\n"
        "Depends: python3 (>= 3.10), e2fsprogs, fakeroot, tar\n"
        f"Installed-Size: {(size + 1023) // 1024}\n"
        "Homepage: https://github.com/fr4nck/PimpMyKobo-AuraHD\n"
        "Description: Local Aura HD rescue tools and guarded native Linux P1 restore\n"
        " Inspect and qualify recovery evidence, rebuild and simulate local images.\n"
        " Physical P1 restoration requires native Linux and separate explicit intent.\n"
        " No device is accessed by package installation; no Kobo images are included.\n").encode("utf-8"))
    payload = sorted(path for path in destination.rglob("*") if path.is_file() and control not in path.parents)
    (control / "md5sums").write_bytes("".join(
        f"{hashlib.md5(path.read_bytes()).hexdigest()}  {path.relative_to(destination).as_posix()}\n"
        for path in payload).encode("ascii"))
    for path in destination.rglob("*"):
        path.chmod(0o755 if path.is_dir() or path == launcher else 0o644)
        os.utime(path, (0, 0))
    destination.chmod(0o755); os.utime(destination, (0, 0))
    return {"package": PACKAGE, "version": pmkb.VERSION, "architecture": "all", "files_sha256": hashes}


def build(output: Path, maintainer: str) -> dict:
    reject_device(output)
    if output.exists() or output.is_symlink():
        raise ValueError("package output already exists; no overwrite")
    if output.suffix != ".deb" or not output.parent.is_dir():
        raise ValueError("output must be a new .deb file in an existing directory")
    executable = shutil.which("dpkg-deb")
    if not executable:
        raise ValueError("dpkg-deb required; build on Debian/Ubuntu or WSL")
    # Build on the Linux temporary filesystem: DrvFS may ignore chmod on a
    # Windows output directory, which dpkg-deb correctly rejects for DEBIAN/.
    with tempfile.TemporaryDirectory(prefix="pmkb-deb-") as temp:
        root = Path(temp)
        metadata = stage_package(Path(__file__).resolve().parent.parent, root / "package", maintainer)
        built = root / "package.deb"
        checked = subprocess.run([executable, "--root-owner-group", "--uniform-compression", "-Zgzip",
                                  "--build", str(root / "package"), str(built)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 env={**os.environ, "SOURCE_DATE_EPOCH": "0", "LC_ALL": "C"})
        if checked.returncode != 0:
            raise ValueError(f"dpkg-deb failed (exit {checked.returncode}): {checked.stderr.strip()}")
        with built.open("r+b") as handle:
            os.fsync(handle.fileno())
        metadata.update(sha256=hashlib.sha256(built.read_bytes()).hexdigest(), bytes=built.stat().st_size,
                        output=str(output))
        local_copy = None
        try:
            # Publish on the destination filesystem without overwriting, even
            # when the Linux staging filesystem and destination differ.
            with tempfile.NamedTemporaryFile(prefix=".pmkb-", suffix=".deb", dir=output.parent, delete=False) as out:
                local_copy = Path(out.name)
                with built.open("rb") as source:
                    shutil.copyfileobj(source, out)
                out.flush(); os.fsync(out.fileno())
            if hashlib.sha256(local_copy.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError("package destination readback mismatch")
            os.link(local_copy, output)
        finally:
            if local_copy is not None:
                local_copy.unlink()
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--maintainer", required=True, help="Package contact: Name <email>")
    args = parser.parse_args()
    try:
        result = build(args.output, args.maintainer)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"package build refused: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
