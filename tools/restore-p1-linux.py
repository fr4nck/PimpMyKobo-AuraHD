#!/usr/bin/env python3
"""Restore only P1 on native Linux Live. Default: local checks, no device access."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("prepare", Path(__file__).with_name("prepare-p1-restore.py"))
prepare = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(prepare)
simulation = prepare.simulation
legacy = prepare.legacy
CHUNK = simulation.CHUNK


def require_native_linux(acknowledged: bool) -> None:
    if (not acknowledged or sys.platform != "linux" or "microsoft" in platform.release().lower()
            or platform.machine() not in ("x86_64", "aarch64")
            or os.geteuid() != 0):
        raise ValueError("device access requires root on native 64-bit Linux and --ack-linux-live; WSL unsupported")
    if (Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()
            or os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt")):
        raise ValueError("container or separate mount namespace unsupported")


def inspect_device(path: Path, sysroot: Path = Path("/sys"), procroot: Path = Path("/proc")) -> dict:
    """Metadata only: never open a block device here."""
    path = path.resolve(strict=True)
    if path.parent != Path("/dev"):
        raise ValueError("target must resolve to a block device directly under /dev")
    info = path.stat()
    if not stat.S_ISBLK(info.st_mode):
        raise ValueError("target is not a block device")
    number = f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}"
    node = (sysroot / "dev/block" / number).resolve(strict=True)
    if (node / "partition").exists() or (node / "removable").read_text().strip() != "1":
        raise ValueError("target must be a whole removable disk, never a partition/internal disk")
    if not any((parent / "subsystem").resolve().name == "usb" for parent in (node, *node.parents)):
        raise ValueError("only removable USB readers are supported")
    nodes = [node, *(child for child in node.iterdir() if (child / "partition").exists())]
    numbers = {entry.joinpath("dev").read_text().strip() for entry in nodes}
    if any(any((entry / "holders").iterdir()) for entry in nodes):
        raise ValueError("target or partition has active holders (LVM/RAID/device mapper)")
    for line in (procroot / "self/mountinfo").read_text().splitlines():
        fields = line.split()
        if len(fields) < 6:
            raise ValueError("invalid mountinfo; cannot establish unused target")
        if fields[2] in numbers:
            raise ValueError("target or partition is mounted; unmount it manually first")
    for line in (procroot / "swaps").read_text().splitlines()[1:]:
        fields = line.split()
        if not fields:
            raise ValueError("invalid swap metadata")
        swap = Path(fields[0]).stat()
        swap_device = swap.st_rdev if stat.S_ISBLK(swap.st_mode) else swap.st_dev
        if f"{os.major(swap_device)}:{os.minor(swap_device)}" in numbers:
            raise ValueError("target or partition is active swap")
    return {"path": str(path), "rdev": info.st_rdev, "major_minor": number,
            "sysfs": str(node), "partition_devices": sorted(numbers)}


class LinuxDisk:
    """One kernel-exclusive descriptor retained from identity checks to readback."""
    def __init__(self, path: Path, writable: bool):
        self.identity = inspect_device(path)
        flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
        fd = os.open(self.identity["path"], flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISBLK(opened.st_mode) or opened.st_rdev != self.identity["rdev"]:
                raise ValueError("device changed during exclusive open")
            self.handle = os.fdopen(fd, "r+b" if writable else "rb", buffering=0)
        except BaseException:
            os.close(fd)
            raise
        try:
            self.recheck()
            if self.sector_size() != 512 or (writable and self.ioctl_int(0x125E, "i") != 0):
                raise ValueError("requires 512-byte logical sectors and writable media for restore")
        except BaseException:
            self.handle.close()
            raise

    def ioctl_int(self, request: int, fmt: str) -> int:
        import fcntl
        buffer = bytearray(struct.calcsize(fmt))
        fcntl.ioctl(self.handle.fileno(), request, buffer, True)
        return struct.unpack(fmt, buffer)[0]

    def size(self) -> int:
        return self.ioctl_int(0x80081272, "Q")  # BLKGETSIZE64, 64-bit Linux ABI

    def sector_size(self) -> int:
        return self.ioctl_int(0x1268, "i")  # BLKSSZGET

    def recheck(self) -> None:
        if inspect_device(Path(self.identity["path"])) != self.identity:
            raise ValueError("device metadata changed while held exclusively")

    def flush_and_invalidate(self) -> None:
        import fcntl
        os.fsync(self.handle.fileno())
        fcntl.ioctl(self.handle.fileno(), 0x1261)  # BLKFLSBUF: flush then drop block cache

    def close(self) -> None:
        self.handle.close()


def durable_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def append_event(journal, **event) -> None:
    journal.write(json.dumps(event, ensure_ascii=False) + "\n")
    journal.flush()
    os.fsync(journal.fileno())


def persistent_storage(path: Path, device: dict) -> None:
    info = path.stat()
    number = f"{os.major(info.st_dev)}:{os.minor(info.st_dev)}"
    if number in device["partition_devices"]:
        raise ValueError("journal/rollback storage must be outside the target")
    types = set()
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        if len(fields) < 10 or "-" not in fields:
            raise ValueError("invalid mountinfo for persistent storage")
        if fields[2] == number:
            types.add(fields[fields.index("-") + 1])
    if not types or not types <= {"ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "exfat", "ntfs3"}:
        raise ValueError("journal requires a supported persistent filesystem, not Live RAM/overlay/FUSE/network storage")


def write_all(destination, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = destination.write(view)
        if count is None or count <= 0 or count > len(view):
            raise OSError("short/invalid write")
        view = view[count:]


def copy_range(source, destination, offset: int, size: int) -> str:
    source.seek(offset)
    remaining = size
    sha = hashlib.sha256()
    while remaining:
        data = source.read(min(CHUNK, remaining))
        if not data:
            raise ValueError("short input read")
        write_all(destination, data)
        sha.update(data)
        remaining -= len(data)
    return sha.hexdigest()


def check_staged_filesystem(path: Path) -> dict:
    legacy.regular(path)
    executable = shutil.which("e2fsck", path="/usr/sbin:/usr/bin:/sbin:/bin")
    if not executable:
        raise ValueError("e2fsck is required on Linux Live before any physical write")
    checked = subprocess.run([executable, "-f", "-n", str(path.resolve())],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, env={**os.environ, "LC_ALL": "C"})
    if checked.returncode != 0:
        raise ValueError(f"read-only e2fsck refused staged P1 (exit {checked.returncode}): {checked.stdout}")
    return {"command": "e2fsck -f -n (local staged file only)", "exit_code": 0,
            "output": checked.stdout}


def validate_local(plan_path: Path, manifest: Path, rebuild: Path, rootfs: Path,
                   backup: Path, acquisition: Path, simulated: Path,
                   simulation_report: Path, journal: Path) -> dict:
    for path in (plan_path, manifest, rebuild, rootfs, backup, acquisition, simulated, simulation_report):
        legacy.regular(path)
    legacy.reject_device(journal)
    if not journal.parent.is_dir():
        raise ValueError("journal parent must exist on separate persistent storage")
    for path in (journal, Path(str(journal) + ".replacement.img"), Path(str(journal) + ".original-p1.img")):
        if path.exists() or path.is_symlink():
            raise ValueError("journal/staging/rollback collision; never overwrite")
    plan = simulation.read_json(plan_path)
    with tempfile.TemporaryDirectory(prefix="p1-plan-check-", dir=journal.parent) as temp:
        verified = prepare.prepare(manifest, rebuild, rootfs, backup, acquisition,
                                   simulated, simulation_report, Path(temp) / "plan.json")
    if verified["status"] != "prepared" or plan != verified:
        raise ValueError("plan does not match freshly verified local evidence")
    return plan


def execute(plan_path: Path, manifest: Path, rebuild: Path, rootfs: Path, backup: Path,
            acquisition: Path, simulated: Path, simulation_report: Path, journal: Path,
            *, device: Path | None = None, check_device: bool = False, write_p1: bool = False,
            ack_linux_live: bool = False, authorize_plan_sha256: str | None = None) -> dict:
    result = {"tool": "restore-p1-linux", "schema_version": 1, "status": "refused",
              "complete": False, "device_write_attempted": False, "errors": []}
    disk = None
    log = None
    try:
        # Authorization and environment refusals precede even local staging/device opens.
        if write_p1 and (not authorize_plan_sha256 or authorize_plan_sha256 != legacy.digest(plan_path)):
            raise ValueError("--write-p1 requires --authorize-plan-sha256 matching the reviewed plan")
        if (check_device or write_p1):
            require_native_linux(ack_linux_live)
            if device is None:
                raise ValueError("explicit --device required; no discovery or default target")
        plan = validate_local(plan_path, manifest, rebuild, rootfs, backup, acquisition,
                              simulated, simulation_report, journal)
        result.update(plan_sha256=legacy.digest(plan_path), input_provenance=plan["input_provenance"],
                      bootability="not_tested", physical_restore_eligible=False)
        if write_p1 and authorize_plan_sha256 != result["plan_sha256"]:
            raise ValueError("reviewed plan changed during validation")
        if not (check_device or write_p1):
            result.update(status="local_ready", complete=True)
            return result
        if write_p1:
            persistent_storage(journal.parent, inspect_device(device))
            # No dependency on files on the target: mounted target partitions are refused.
            if shutil.disk_usage(journal.parent).free < 2 * plan["p1_size"] + CHUNK:
                raise ValueError("insufficient local space for staged replacement and original P1")
            replacement = Path(str(journal) + ".replacement.img")
            rollback = Path(str(journal) + ".original-p1.img")
            with rootfs.open("rb") as source, replacement.open("xb") as out:
                sha = copy_range(source, out, 0, plan["p1_size"])
                if source.read(1) or sha != plan["replacement_sha256"]:
                    raise ValueError("replacement changed during staging")
                out.flush(); os.fsync(out.fileno())
            if legacy.digest(replacement) != plan["replacement_sha256"]:
                raise ValueError("staged replacement failed readback")
            filesystem_check = check_staged_filesystem(replacement)
            if legacy.digest(replacement) != plan["replacement_sha256"]:
                raise ValueError("staged replacement changed during read-only filesystem check")
            log = journal.open("x", encoding="utf-8")
            append_event(log, phase="local_verified", plan=plan, plan_sha256=result["plan_sha256"],
                         staged_filesystem_check=filesystem_check)
            durable_directory(journal.parent)
        disk = LinuxDisk(device, write_p1)
        if write_p1:
            persistent_storage(journal.parent, disk.identity)
        result["device"] = disk.identity
        handle = disk.handle
        if disk.size() != plan["disk_size"]:
            raise ValueError("physical capacity differs from complete backup")
        if simulation.hash_region(handle, 0, plan["disk_size"]) != plan["required_target_full_sha256"]:
            raise ValueError("whole physical target differs from complete backup; no write")
        result["whole_target_matches_backup"] = True
        if not write_p1:
            result.update(status="device_ready_read_only", complete=True)
            return result
        with backup.open("rb") as source:
            old_sha = simulation.hash_region(source, plan["p1_offset"], plan["p1_size"])
        with rollback.open("xb") as out:
            if copy_range(handle, out, plan["p1_offset"], plan["p1_size"]) != old_sha:
                raise ValueError("physical P1 changed during rollback acquisition")
            out.flush(); os.fsync(out.fileno())
        if legacy.digest(rollback) != old_sha:
            raise ValueError("original P1 rollback failed readback")
        durable_directory(journal.parent)
        with replacement.open("rb") as source:
            # Retain this exact descriptor. Verify again before the durable write intent.
            if simulation.hash_region(source, 0, plan["p1_size"]) != plan["replacement_sha256"]:
                raise ValueError("staged replacement changed before write")
            disk.recheck()
            if disk.size() != plan["disk_size"] or simulation.hash_region(handle, 0, plan["disk_size"]) != plan["required_target_full_sha256"]:
                raise ValueError("target changed before write")
            append_event(log, phase="writing_p1", device=disk.identity, original_p1_sha256=old_sha,
                         rollback=str(rollback), offset=plan["p1_offset"], size=plan["p1_size"],
                         warning="Any interruption from this point may leave P1 partially restored; no automatic retry/rollback.")
            result["device_write_attempted"] = True
            handle.seek(plan["p1_offset"])
            if copy_range(source, handle, 0, plan["p1_size"]) != plan["replacement_sha256"]:
                raise ValueError("replacement changed during write")
        disk.flush_and_invalidate()
        disk.recheck()
        end = plan["p1_offset"] + plan["p1_size"]
        preserved = {"pre_p1": simulation.hash_region(handle, 0, plan["p1_offset"]),
                     "suffix_after_p1": simulation.hash_region(handle, end, plan["disk_size"] - end)}
        if (disk.size() != plan["disk_size"]
                or simulation.hash_region(handle, plan["p1_offset"], plan["p1_size"]) != plan["replacement_sha256"]
                or any(value != plan["preserved_sha256"][key] for key, value in preserved.items())):
            raise ValueError("post-write P1/preserved-region verification failed")
        result.update(status="ok", complete=True, p1_reread_sha256=plan["replacement_sha256"],
                      outside_p1_unchanged=True, rollback=str(rollback), original_p1_sha256=old_sha)
        append_event(log, phase="verified", result=result)
    except (OSError, ValueError, TypeError, KeyError, KeyboardInterrupt) as exc:
        result.update(status="failed" if result["device_write_attempted"] else "refused",
                      complete=False, errors=[str(exc) or "interrupted"],
                      p1_may_be_partial=result["device_write_attempted"])
        if log is not None:
            try:
                append_event(log, phase="failed", result=result)
            except OSError:
                result["errors"].append("journal update failed; retain all artifacts")
    finally:
        if disk is not None:
            try:
                disk.close()
            except OSError as exc:
                result.update(status="failed", complete=False)
                result["errors"].append(f"device close failed: {exc}")
        if log is not None:
            try:
                log.close()
            except OSError as exc:
                result.update(status="failed", complete=False)
                result["errors"].append(f"journal close failed: {exc}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan_path", "manifest", "rebuild", "rootfs", "backup", "acquisition",
                 "simulated", "simulation_report", "journal"):
        parser.add_argument(name, type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-device", action="store_true", help="exclusive read-only physical comparison")
    modes.add_argument("--write-p1", action="store_true", help="physical write, requires separate explicit authorization")
    parser.add_argument("--device", type=Path)
    parser.add_argument("--ack-linux-live", action="store_true")
    parser.add_argument("--authorize-plan-sha256")
    result = execute(**vars(parser.parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
