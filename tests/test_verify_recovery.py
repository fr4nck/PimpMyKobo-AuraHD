from __future__ import annotations

import builtins
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
import tarfile
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "verify-recovery.py"
SPEC = importlib.util.spec_from_file_location("verify_recovery", SCRIPT)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def make_tgz(path: Path, count: int = 5) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for index in range(count):
            data = (f"payload-{index}\n" * 100).encode()
            info = tarfile.TarInfo(f"file-{index}.txt")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def make_directory_only_tgz(path: Path) -> None:
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("empty-dir")
        info.type = tarfile.DIRTYPE
        archive.addfile(info)


def make_valid_gzip_with_truncated_tar(path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as archive:
        data = b"hello" * 100
        info = tarfile.TarInfo("one.txt")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    raw_tar = buf.getvalue().rstrip(b"\x00")
    path.write_bytes(gzip.compress(raw_tar))


def make_uimage(path: Path, payload: bytes = b"kernel synthetic", padding: bytes = b"") -> None:
    header = bytearray(64)
    header[0:4] = verify.UBOOT_MAGIC.to_bytes(4, "big")
    header[12:16] = len(payload).to_bytes(4, "big")
    header[24:28] = (zlib.crc32(payload) & 0xFFFFFFFF).to_bytes(4, "big")
    header[28] = 5
    header[29] = 2
    header[30] = 2
    header[31] = 0
    header[32:36] = b"test"
    header_crc = zlib.crc32(header) & 0xFFFFFFFF
    header[4:8] = header_crc.to_bytes(4, "big")
    path.write_bytes(bytes(header) + payload + padding)


def build_recovery(root: Path) -> None:
    ntx = root / "upgrade" / "ntx508"
    ntx.mkdir(parents=True)
    sample = b"recovery sample\n"
    (root / "sample.txt").write_bytes(sample)
    (root / "fs.md5sum").write_text(f"{md5(sample)}  sample.txt\n", encoding="utf-8")
    make_tgz(root / "upgrade" / "fs.tgz", 5)
    make_tgz(root / "upgrade" / "db.tgz", 2)
    (ntx / "u-boot_mddr_512-E606C0-K4X2G323PC.bin").write_bytes(b"u-boot synthetic")
    make_uimage(ntx / "uImage-E606C0")


@contextlib.contextmanager
def deny_reading(target: Path):
    """Raise PermissionError when *target* is opened, like an unreadable file.

    Both Path.open and builtins.open (used by gzip/tarfile) are intercepted, so
    the test is deterministic on Linux and Windows and needs no real permissions.
    """
    # realpath (not abspath): on Windows the temporary directory may be given as an
    # 8.3 short name while the verifier resolves paths to their long form.
    def canonical(file: Any) -> str:
        return os.path.normcase(os.path.realpath(os.fspath(file)))

    target_text = canonical(target)
    original_path_open = Path.open
    original_open = builtins.open

    def denied(file: Any) -> bool:
        try:
            return canonical(file) == target_text
        except TypeError:
            return False

    def path_open(path_obj, mode="r", *args, **kwargs):
        if denied(path_obj):
            raise PermissionError(13, "Permission denied", str(path_obj))
        return original_path_open(path_obj, mode, *args, **kwargs)

    def builtin_open(file, mode="r", *args, **kwargs):
        if denied(file):
            raise PermissionError(13, "Permission denied", str(file))
        return original_open(file, mode, *args, **kwargs)

    with mock.patch.object(Path, "open", new=path_open), mock.patch(
        "builtins.open", new=builtin_open
    ):
        yield


def run_main(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with mock.patch("sys.argv", ["verify-recovery.py", *argv]), contextlib.redirect_stdout(out):
        code = verify.main()
    return code, out.getvalue()


class VerifyRecoveryTests(unittest.TestCase):
    def test_complete_recovery_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            result = verify.inspect_recovery(root, True, True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["manifest"]["ok"])
            self.assertTrue(all(item["ok"] for item in result["archives"]))
            self.assertTrue(result["artifacts"]["ok"])

    def test_gzip_crc_corruption_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            data = bytearray(path.read_bytes())
            data[-8] ^= 0x01
            path.write_bytes(data)
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_truncated_gzip_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            data = path.read_bytes()
            path.write_bytes(data[: max(20, len(data) // 2)])
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_valid_gzip_containing_truncated_tar_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.tgz"
            make_valid_gzip_with_truncated_tar(path)
            result = verify.validate_tar_gzip(path)
            self.assertFalse(result["ok"], result)
            self.assertIn("tar end marker", result["error"])

    def test_directory_only_archive_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dirs.tgz"
            make_directory_only_tgz(path)
            result = verify.validate_tar_gzip(path)
            self.assertFalse(result["ok"], result)
            self.assertIn("no regular files", result["error"])

    def test_trailing_garbage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            path.write_bytes(path.read_bytes() + b"garbage")
            self.assertFalse(verify.validate_tar_gzip(path)["ok"])

    def test_manifest_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "sample.txt").write_text("modified\n", encoding="utf-8")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertEqual(len(result["manifest"]["mismatched"]), 1)

    def test_manifest_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            outside = root.parent / "outside.txt"
            outside.write_bytes(b"outside")
            try:
                (root / "fs.md5sum").write_text(f"{md5(b'outside')}  ../outside.txt\n", encoding="utf-8")
                result = verify.inspect_recovery(root, True, False)
                self.assertFalse(result["ok"])
                self.assertTrue(result["manifest"]["invalid_entries"])
            finally:
                outside.unlink(missing_ok=True)

    def test_gnu_escaped_manifest_name_is_decoded_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "fs.md5sum"
            digest = md5(b"x")
            manifest.write_text("\\" + f"{digest}  a\\\\b\n", encoding="utf-8")
            entries, errors = verify.parse_manifest(manifest)
            self.assertFalse(errors)
            self.assertEqual(entries, [(digest, "a\\b")])

    def test_gnu_carriage_return_escape_is_supported(self) -> None:
        self.assertEqual(verify._decode_gnu_escaped_name(r"a\rb"), "a\rb")

    def test_empty_uboot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "ntx508" / "u-boot_mddr_512-E606C0-K4X2G323PC.bin").write_bytes(b"")
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_different_e606c0_ram_variant_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            old = root / "upgrade" / "ntx508" / "u-boot_mddr_512-E606C0-K4X2G323PC.bin"
            new = old.with_name("u-boot_mddr_512-E606C0-OTHER-RAM.bin")
            old.rename(new)
            result = verify.inspect_recovery(root, True, False)
            self.assertTrue(result["artifacts"]["ok"])
            selected = Path(result["artifacts"]["selected_uboot"]["path"])
            self.assertEqual(selected.resolve(), new.resolve())

    def test_multiple_uboot_variants_are_not_auto_selected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "ntx508" / "u-boot_mddr_512-E606C0-OTHER.bin").write_bytes(b"other")
            result = verify.inspect_recovery(root, True, False)
            self.assertTrue(result["artifacts"]["ok"])
            self.assertIsNone(result["artifacts"]["selected_uboot"])
            self.assertTrue(result["warnings"])

    def test_bad_uimage_magic_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "ntx508" / "uImage-E606C0").write_bytes(b"x" * 100)
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_bad_uimage_crc_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "ntx508" / "uImage-E606C0"
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
            self.assertFalse(verify.inspect_recovery(root, True, False)["ok"])

    def test_zero_padded_uimage_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "uImage"
            make_uimage(path, padding=b"\x00" * 512)
            result = verify.validate_legacy_uimage(path)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["padding_bytes"], 512)

    def test_nonzero_uimage_padding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "uImage"
            make_uimage(path, padding=b"\x00\x01")
            self.assertFalse(verify.validate_legacy_uimage(path)["ok"])

    def test_skip_md5_is_partial_and_never_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "fs.md5sum").unlink()
            result = verify.inspect_recovery(root, False, False)
            self.assertFalse(result["ok"])
            self.assertTrue(result["partial"])
            self.assertTrue(result["checks_ok"])

    def test_skip_md5_does_not_mask_other_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "fs.tgz").write_bytes(b"broken")
            result = verify.inspect_recovery(root, False, False)
            self.assertTrue(result["partial"])
            self.assertFalse(result["checks_ok"])
            self.assertFalse(result["ok"])

    def test_symlink_escape_for_critical_archive_is_rejected(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as out:
            root = Path(td)
            build_recovery(root)
            path = root / "upgrade" / "fs.tgz"
            path.unlink()
            external = Path(out) / "fs.tgz"
            make_tgz(external)
            try:
                path.symlink_to(external)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertFalse(result["archives"][0]["ok"])

    def test_unreadable_manifest_file_is_incomplete_not_inconsistent(self) -> None:
        # Reproduces the real Aura HD case (bin/antiword: Permission denied)
        # without depending on chmod, root or Windows ACLs.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            with deny_reading(root / "sample.txt"):
                result = verify.inspect_recovery(root, True, False)
            manifest = result["manifest"]
            self.assertEqual(len(manifest["unreadable"]), 1)
            self.assertEqual(manifest["missing"], [])
            self.assertEqual(manifest["mismatched"], [])
            self.assertEqual(manifest["invalid_entries"], [])
            self.assertFalse(result["ok"])
            self.assertTrue(result["partial"])
            self.assertEqual(result["status"], "incomplete")
            self.assertNotEqual(result["status"], "inconsistent")
            self.assertEqual(result["inconsistencies"], [])
            self.assertEqual(result["unreadable_count"], 1)

    def test_unreadable_manifest_file_human_summary_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            for lang, expected, forbidden in (
                ("fr", "VÉRIFICATION INCOMPLÈTE", "INCOHÉRENT"),
                ("en", "VERIFICATION INCOMPLETE", "INCONSISTENT"),
            ):
                with deny_reading(root / "sample.txt"):
                    code, output = run_main([str(root), "--lang", lang])
                self.assertEqual(code, 1)
                self.assertIn(expected, output)
                self.assertNotIn(forbidden, output)
            with deny_reading(root / "sample.txt"):
                code, output = run_main([str(root), "--json"])
            data = json.loads(output)
            self.assertEqual(code, 1)
            self.assertEqual(
                (data["ok"], data["partial"], data["status"]), (False, True, "incomplete")
            )

    def test_unreadable_manifest_itself_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            with deny_reading(root / "fs.md5sum"):
                result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "incomplete")

    def test_unreadable_archive_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            with deny_reading(root / "upgrade" / "fs.tgz"):
                result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertTrue(result["archives"][0]["unreadable"])
            self.assertEqual(result["status"], "incomplete")

    def test_complete_recovery_status_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            result = verify.inspect_recovery(root, True, True)
            self.assertEqual(
                (result["ok"], result["partial"], result["status"]), (True, False, "ok")
            )
            code, output = run_main([str(root), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["status"], "ok")

    def test_manifest_mismatch_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "sample.txt").write_bytes(b"modified\n")
            result = verify.inspect_recovery(root, True, False)
            self.assertEqual(
                (result["ok"], result["partial"], result["status"]),
                (False, False, "inconsistent"),
            )

    def test_missing_manifest_file_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "sample.txt").unlink()
            result = verify.inspect_recovery(root, True, False)
            self.assertEqual(result["manifest"]["missing"], ["sample.txt"])
            self.assertEqual(
                (result["ok"], result["partial"], result["status"]),
                (False, False, "inconsistent"),
            )

    def test_missing_manifest_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "fs.md5sum").unlink()
            result = verify.inspect_recovery(root, True, False)
            self.assertEqual(result["status"], "inconsistent")

    def test_corrupt_archive_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "fs.tgz").write_bytes(b"broken")
            result = verify.inspect_recovery(root, True, False)
            self.assertEqual(
                (result["ok"], result["partial"], result["status"]),
                (False, False, "inconsistent"),
            )

    def test_invalid_uimage_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "ntx508" / "uImage-E606C0").write_bytes(b"x" * 100)
            self.assertEqual(verify.inspect_recovery(root, True, False)["status"], "inconsistent")

    def test_unreadable_file_does_not_mask_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "db.tgz").write_bytes(b"broken")
            with deny_reading(root / "sample.txt"):
                result = verify.inspect_recovery(root, True, False)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "inconsistent")
            self.assertEqual(result["unreadable_count"], 1)

    def test_skip_md5_status_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            result = verify.inspect_recovery(root, False, False)
            self.assertEqual(
                (result["ok"], result["partial"], result["status"]), (False, True, "incomplete")
            )
            code, output = run_main([str(root), "--skip-md5"])
            self.assertEqual(code, 1)
            self.assertIn("RECOVERY PARTIELLEMENT VÉRIFIÉ", output)

    def test_skip_md5_with_corruption_is_inconsistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            (root / "upgrade" / "fs.tgz").write_bytes(b"broken")
            result = verify.inspect_recovery(root, False, False)
            self.assertFalse(result["ok"])
            self.assertTrue(result["partial"])
            self.assertEqual(result["status"], "inconsistent")
            code, output = run_main([str(root), "--skip-md5"])
            self.assertEqual(code, 1)
            self.assertIn("RECOVERY INCOHÉRENT", output)

    def test_verifier_never_requests_write_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_recovery(root)
            original = Path.open
            modes: list[str] = []
            case = self

            def guarded(path_obj, mode="r", *args, **kwargs):
                modes.append(mode)
                case.assertNotIn("w", mode)
                case.assertNotIn("a", mode)
                case.assertNotIn("+", mode)
                return original(path_obj, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=guarded):
                result = verify.inspect_recovery(root, True, True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(modes)


if __name__ == "__main__":
    unittest.main()
