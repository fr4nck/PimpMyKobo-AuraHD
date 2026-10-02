from __future__ import annotations

import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from test_inspect_aura_hd import KNOWN_PAYLOAD, build_image, mbr_entry

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "backup-aura-hd.py"
SPEC = importlib.util.spec_from_file_location("backup_aura_hd", SCRIPT)
assert SPEC and SPEC.loader
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)

MiB = 1024 * 1024
P1, P2, P3 = 2048 * 512, 3072 * 512, 4096 * 512
P1_SIZE, P2_SIZE, P3_SIZE = 1024 * 512, 1024 * 512, 2048 * 512
HWCONFIG_END = 0x80000 + 16 + len(KNOWN_PAYLOAD)


def build_source(path: Path, **kwargs: Any) -> bytes:
    """Synthetic Aura HD image filled with pseudo-random data (no Kobo blob)."""
    build_image(path, **kwargs)
    rng = random.Random(1234)
    data = bytearray(path.read_bytes())

    def fill(start: int, end: int) -> None:
        data[start:end] = rng.randbytes(end - start)

    fill(512, 0x80000)                       # pre-P1, keeping MBR and HWCONFIG
    fill(HWCONFIG_END, P1)
    for offset, size in ((P1, P1_SIZE), (P2, P2_SIZE)):
        fill(offset, offset + 1024)          # keep the ext superblock at +1024
        fill(offset + 2048, offset + size)
    fill(P3 + 512, P3 + P3_SIZE)             # keep the FAT boot sector
    path.write_bytes(bytes(data))
    return bytes(data)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_main(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = backup.main(argv)
    return code, out.getvalue(), err.getvalue()


class SectorAlignedFile(io.FileIO):
    """Source handle that rejects unaligned I/O, like a Windows raw disk."""

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0 and offset % 512:
            raise OSError(22, f"unaligned seek {offset}")
        return super().seek(offset, whence)

    def read(self, size: int = -1) -> bytes:
        if self.tell() % 512 or (size != -1 and size % 512):
            raise OSError(22, f"unaligned read {size}@{self.tell()}")
        return super().read(size)


class BackupTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.image = self.tmp / "aura.img"
        self.data = build_source(self.image)
        self.dest = self.tmp / "backup"

    def tearDown(self) -> None:
        self._td.cleanup()

    def run_backup(self, **kwargs: Any) -> dict[str, Any]:
        return backup.run_backup(str(self.image), self.dest, **kwargs)

    def component(self, manifest: dict[str, Any], name: str) -> dict[str, Any]:
        return next(c for c in manifest["components"] if c["name"] == name)

    def assert_refused(self, **kwargs: Any) -> list[str]:
        with self.assertRaises(backup.Refusal) as ctx:
            self.run_backup(**kwargs)
        self.assertFalse(self.dest.exists(), "a refused backup must not create the destination")
        return ctx.exception.reasons


class IdentificationTests(BackupTestCase):
    def test_synthetic_aura_is_identified_and_backup_is_complete(self) -> None:
        manifest = self.run_backup()
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["status"], "complete")
        ident = manifest["identification"]
        self.assertTrue(ident["aura_hd_e606c0"])
        self.assertEqual(ident["hwconfig"]["version"], "v1.7")
        self.assertEqual(ident["hwconfig"]["payload_size"], 39)
        self.assertEqual(ident["hwconfig"]["pcb"], {"raw": 28, "decoded": "E606C0"})
        self.assertEqual(ident["hwconfig"]["ram_type"]["decoded"], "K4X2G323PC")

    def test_non_aura_source_is_refused_before_copy(self) -> None:
        self.image.write_bytes(bytes(4 * MiB))
        reasons = self.assert_refused()
        self.assertTrue(any("HW CONFIG" in r or "MBR" in r for r in reasons), reasons)

    def test_invalid_hwconfig_version_is_refused(self) -> None:
        build_source(self.image, version=b"v1.6\x00")
        reasons = self.assert_refused()
        self.assertTrue(any("v1.7" in r for r in reasons), reasons)

    def test_wrong_pcb_is_refused(self) -> None:
        build_source(self.image, payload=b"\x1b" + KNOWN_PAYLOAD[1:])
        self.assert_refused()

    def test_invalid_mbr_signature_is_refused(self) -> None:
        data = bytearray(self.data)
        data[510:512] = b"\x00\x00"
        self.image.write_bytes(bytes(data))
        reasons = self.assert_refused()
        self.assertTrue(any("MBR" in r for r in reasons), reasons)

    def test_partition_beyond_source_is_refused(self) -> None:
        data = bytearray(self.data)
        data[478:494] = mbr_entry(0x0C, 4096, 999999)
        self.image.write_bytes(bytes(data))
        self.assert_refused()

    def test_missing_p3_is_refused(self) -> None:
        data = bytearray(self.data)
        data[478:494] = bytes(16)
        self.image.write_bytes(bytes(data))
        reasons = self.assert_refused()
        self.assertTrue(any("P1, P2, P3" in r for r in reasons), reasons)

    def test_wrong_recoveryfs_label_is_refused(self) -> None:
        data = bytearray(self.data)
        data[P2 + 1024 + 120 : P2 + 1024 + 136] = b"other".ljust(16, b"\x00")
        self.image.write_bytes(bytes(data))
        reasons = self.assert_refused()
        self.assertTrue(any("recoveryfs" in r for r in reasons), reasons)


class CopyTests(BackupTestCase):
    def test_exact_copies_of_pre_p1_p1_p2(self) -> None:
        self.run_backup()
        self.assertEqual((self.dest / "pre-p1.bin").read_bytes(), self.data[0:P1])
        self.assertEqual((self.dest / "p1-rootfs.img").read_bytes(), self.data[P1 : P1 + P1_SIZE])
        self.assertEqual((self.dest / "p2-recoveryfs.img").read_bytes(), self.data[P2 : P2 + P2_SIZE])

    def test_partition_sizes_come_from_mbr(self) -> None:
        manifest = self.run_backup()
        self.assertEqual(self.component(manifest, "p1_rootfs")["size"], P1_SIZE)
        self.assertEqual((self.dest / "p1-rootfs.img").stat().st_size, P1_SIZE)

    def test_p3_is_not_copied_by_default(self) -> None:
        manifest = self.run_backup()
        self.assertFalse((self.dest / "p3-userdata.img").exists())
        self.assertEqual(self.component(manifest, "p3_userdata")["status"], "not_requested")
        self.assertTrue(manifest["complete"])

    def test_p3_is_copied_with_explicit_option(self) -> None:
        manifest = self.run_backup(include_userdata=True)
        self.assertTrue(manifest["complete"])
        self.assertEqual((self.dest / "p3-userdata.img").read_bytes(), self.data[P3 : P3 + P3_SIZE])

    def test_source_and_destination_hashes_match(self) -> None:
        manifest = self.run_backup(include_userdata=True)
        sums = (self.dest / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(sums), 4)
        for component in manifest["components"]:
            expected = sha(self.data[component["offset"] : component["offset"] + component["size"]])
            self.assertEqual(component["status"], "verified")
            self.assertEqual(component["sha256_stream"], expected)
            self.assertEqual(component["sha256_source_reread"], expected)
            self.assertEqual(component["sha256_destination"], expected)
            self.assertIn(f"{expected} *{component['file']}", sums)
            self.assertEqual(sha((self.dest / component["file"]).read_bytes()), expected)

    def test_single_pass_skips_source_reread(self) -> None:
        manifest = self.run_backup(reread=False)
        self.assertTrue(manifest["complete"])
        self.assertNotIn("sha256_source_reread", self.component(manifest, "p1_rootfs"))

    def test_existing_empty_destination_is_accepted(self) -> None:
        self.dest.mkdir()
        self.assertTrue(self.run_backup()["complete"])

    def test_dry_run_creates_nothing(self) -> None:
        manifest = self.run_backup(dry_run=True)
        self.assertEqual(manifest["status"], "dry_run")
        self.assertFalse(self.dest.exists())


class FailureTests(BackupTestCase):
    def test_corrupted_destination_marks_backup_failed(self) -> None:
        original = backup.readback_sha256

        def corrupt_then_read(path: Path) -> tuple[str, int]:
            if path.name.startswith("p1-rootfs"):
                with open(path, "r+b") as handle:  # destination file of the test, never the source
                    first = handle.read(1)
                    handle.seek(0)
                    handle.write(bytes([first[0] ^ 0xFF]))
            return original(path)

        with mock.patch.object(backup, "readback_sha256", side_effect=corrupt_then_read):
            manifest = self.run_backup()
        p1 = self.component(manifest, "p1_rootfs")
        self.assertEqual(p1["status"], "failed")
        self.assertFalse(manifest["complete"])
        self.assertEqual(manifest["status"], "failed")
        self.assertFalse((self.dest / "p1-rootfs.img").exists())
        self.assertTrue((self.dest / "p1-rootfs.img.FAILED").exists(), "evidence must be kept")
        self.assertEqual(self.component(manifest, "p2_recoveryfs")["status"], "not_started")
        sums = (self.dest / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertNotIn("p1-rootfs", sums)
        on_disk = json.loads((self.dest / "backup-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(on_disk["complete"])

    def test_unstable_source_reread_marks_backup_failed(self) -> None:
        original = backup.hash_source_range

        def flaky(handle: Any, offset: int, size: int) -> str:
            return "0" * 64 if offset == P2 else original(handle, offset, size)

        with mock.patch.object(backup, "hash_source_range", side_effect=flaky):
            manifest = self.run_backup()
        self.assertEqual(self.component(manifest, "p2_recoveryfs")["status"], "failed")
        self.assertFalse(manifest["complete"])

    def test_pre_p1_change_after_copy_marks_backup_failed(self) -> None:
        with mock.patch.object(backup, "hash_source_range", return_value="0" * 64):
            manifest = self.run_backup(reread=False)
        self.assertFalse(manifest["identity_recheck"]["matches"])
        self.assertFalse(manifest["complete"])

    def test_insufficient_space_is_refused(self) -> None:
        with mock.patch.object(backup, "disk_free", return_value=1024):
            reasons = self.assert_refused()
        self.assertTrue(any("free space" in r for r in reasons), reasons)

    def test_space_check_counts_userdata_only_when_requested(self) -> None:
        needed = P1 + P1_SIZE + P2_SIZE + backup.SPACE_MARGIN
        with mock.patch.object(backup, "disk_free", return_value=needed):
            self.assertTrue(self.run_backup()["complete"])
        self.dest = self.tmp / "backup2"
        with mock.patch.object(backup, "disk_free", return_value=needed):
            self.assert_refused(include_userdata=True)

    def test_non_empty_destination_is_refused(self) -> None:
        self.dest.mkdir()
        (self.dest / "previous.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(backup.Refusal) as ctx:
            self.run_backup()
        self.assertTrue(any("not empty" in r for r in ctx.exception.reasons))
        self.assertEqual(os.listdir(self.dest), ["previous.txt"])

    def test_destination_that_is_a_file_is_refused(self) -> None:
        self.dest.write_text("x", encoding="utf-8")
        with self.assertRaises(backup.Refusal):
            self.run_backup()

    def test_destination_on_source_is_refused(self) -> None:
        with mock.patch.object(backup, "destination_on_source", return_value="on_source"):
            reasons = self.assert_refused()
        self.assertTrue(any("on the source" in r for r in reasons))

    def test_undetermined_destination_requires_explicit_override(self) -> None:
        with mock.patch.object(backup, "destination_on_source", return_value="undetermined"):
            self.assert_refused()
            manifest = self.run_backup(allow_unverified_destination=True)
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["destination"]["on_source_check"], "undetermined")

    def test_interruption_leaves_no_valid_part_file(self) -> None:
        original = backup.read_at

        def interrupt(handle: Any, offset: int, size: int, *args: Any) -> bytes:
            if offset == P1 and size == P1_SIZE:
                raise KeyboardInterrupt
            return original(handle, offset, size, *args)

        with mock.patch.object(backup, "read_at", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_backup()
        manifest = json.loads((self.dest / "backup-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["complete"])
        self.assertEqual(manifest["status"], "interrupted")
        self.assertEqual(self.component(manifest, "pre_p1")["status"], "verified")
        self.assertEqual(self.component(manifest, "p1_rootfs")["status"], "interrupted")
        self.assertEqual(self.component(manifest, "p2_recoveryfs")["status"], "not_started")
        self.assertFalse((self.dest / "p1-rootfs.img").exists())
        self.assertFalse((self.dest / "SHA256SUMS").exists())
        for name in os.listdir(self.dest):
            if name.endswith(".part"):
                self.assertNotIn(name, [c["file"] for c in manifest["components"] if c["status"] == "verified"])

    def test_interruption_exit_code(self) -> None:
        with mock.patch.object(backup, "copy_component", side_effect=KeyboardInterrupt):
            code, _, _ = run_main([str(self.image), str(self.dest), "--quiet"])
        self.assertEqual(code, backup.EXIT_INTERRUPTED)


class ManifestTests(BackupTestCase):
    def test_json_output_is_clean_and_matches_manifest_file(self) -> None:
        code, out, err = run_main([str(self.image), str(self.dest), "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("P1 rootfs", err, "progress goes to stderr")
        on_disk = json.loads((self.dest / "backup-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(data, on_disk)
        for key in ("schema_version", "tool", "tool_version", "created_utc", "completed_utc",
                    "source", "identification", "mbr", "components", "target_fingerprint",
                    "complete", "status"):
            self.assertIn(key, data)
        self.assertEqual(data["schema_version"], 1)
        self.assertFalse(data["source"]["path_is_identity"])
        self.assertEqual(data["source"]["size"], len(self.data))
        self.assertEqual([p["number"] for p in data["mbr"]["partitions"]], [1, 2, 3])
        self.assertEqual([p["label"] for p in data["mbr"]["partitions"]],
                         ["rootfs", "recoveryfs", "KOBOeReader"])

    def test_refusal_json(self) -> None:
        self.image.write_bytes(bytes(4 * MiB))
        code, out, _ = run_main([str(self.image), str(self.dest), "--json"])
        self.assertEqual(code, backup.EXIT_REFUSED)
        data = json.loads(out)
        self.assertEqual(data["status"], "refused")
        self.assertTrue(data["reasons"])

    def test_failed_backup_exit_code(self) -> None:
        with mock.patch.object(backup, "readback_sha256", return_value=("0" * 64, 0)):
            code, _, _ = run_main([str(self.image), str(self.dest), "--quiet"])
        self.assertEqual(code, backup.EXIT_FAILED)

    def test_fingerprint_is_stable_and_independent_of_path(self) -> None:
        first = self.run_backup(dry_run=True)["target_fingerprint"]
        moved = self.tmp / "renamed copy.img"
        moved.write_bytes(self.data)
        second = backup.run_backup(str(moved), self.dest, dry_run=True)["target_fingerprint"]
        self.assertEqual(first["fingerprint_sha256"], second["fingerprint_sha256"])
        self.assertEqual(first["pre_p1_sha256"], sha(self.data[:P1]))
        self.assertFalse(first["source_size_in_digest"])

    def test_fingerprint_changes_with_pre_p1_content(self) -> None:
        first = self.run_backup(dry_run=True)["target_fingerprint"]["fingerprint_sha256"]
        data = bytearray(self.data)
        data[0x90000] ^= 0xFF
        self.image.write_bytes(bytes(data))
        second = self.run_backup(dry_run=True)["target_fingerprint"]["fingerprint_sha256"]
        self.assertNotEqual(first, second)


class SafetyTests(BackupTestCase):
    def test_source_is_never_opened_for_writing(self) -> None:
        source = os.path.normcase(os.path.realpath(self.image))
        real_open, real_os_open = builtins.open, os.open
        seen: list[str] = []

        def is_source(file: Any) -> bool:
            try:
                return os.path.normcase(os.path.realpath(os.fspath(file))) == source
            except TypeError:
                return False

        def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if is_source(file):
                seen.append(mode)
                self.assertEqual(mode, "rb", "source must only be opened read-only")
            return real_open(file, mode, *args, **kwargs)

        def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            if is_source(path):
                self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC), 0)
            return real_os_open(path, flags, *args, **kwargs)

        with mock.patch("builtins.open", new=guarded_open), mock.patch("os.open", new=guarded_os_open):
            manifest = self.run_backup(include_userdata=True)
        self.assertTrue(manifest["complete"])
        self.assertTrue(seen)
        self.assertEqual(self.image.read_bytes(), self.data, "source content must be unchanged")

    def test_sector_aligned_reader_like_windows_raw_disk(self) -> None:
        aligned = lambda path, *a, **k: SectorAlignedFile(path, "rb")  # noqa: E731
        with mock.patch.object(backup, "open_source", new=aligned), \
             mock.patch.object(backup.inspector, "open", new=aligned, create=True):
            manifest = self.run_backup(include_userdata=True)
        self.assertTrue(manifest["complete"], manifest["errors"])

    def test_paths_with_spaces_and_unicode(self) -> None:
        folder = self.tmp / "Kobo Aura été ✓"
        folder.mkdir()
        image = folder / "carte d'origine ü.img"
        image.write_bytes(self.data)
        dest = folder / "sauvegarde 2026 — Ω"
        code, out, _ = run_main([str(image), str(dest), "--json", "--quiet"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["complete"])
        self.assertEqual((dest / "p2-recoveryfs.img").read_bytes(), self.data[P2 : P2 + P2_SIZE])


if __name__ == "__main__":
    unittest.main()
