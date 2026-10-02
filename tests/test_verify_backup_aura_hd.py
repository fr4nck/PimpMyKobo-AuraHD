from __future__ import annotations

import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from test_backup_aura_hd import P1, P1_SIZE, backup, build_source

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "verify-backup-aura-hd.py"
SPEC = importlib.util.spec_from_file_location("verify_backup_aura_hd", SCRIPT)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def run_main(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = verifier.main(argv)
    return code, out.getvalue()


def snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    state = {}
    for path in sorted(root.iterdir()):
        st = path.lstat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        state[path.name] = (st.st_size, st.st_mtime_ns, digest)
    return state


class VerifyBackupTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.image = self.tmp / "aura.img"
        self.data = build_source(self.image)
        self.dest = self.tmp / "backup"

    def tearDown(self) -> None:
        self._td.cleanup()

    def make_backup(self, **kwargs: Any) -> dict[str, Any]:
        return backup.run_backup(str(self.image), self.dest, **kwargs)

    def verify(self) -> dict[str, Any]:
        return verifier.verify_backup(self.dest)

    def edit_manifest(self, change: Callable[[dict[str, Any]], None]) -> None:
        path = self.dest / "backup-manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    @staticmethod
    def component(data: dict[str, Any], name: str) -> dict[str, Any]:
        return next(c for c in data["components"] if c["name"] == name)

    def assert_status(self, expected: str) -> dict[str, Any]:
        report = self.verify()
        self.assertEqual(report["status"], expected, report)
        self.assertEqual(report["ok"], expected == "valid")
        return report


class ValidBackupTests(VerifyBackupTestCase):
    def test_valid_backup_without_p3(self) -> None:
        self.make_backup()
        report = self.assert_status("valid")
        results = {c["name"]: c["result"] for c in report["components"]}
        self.assertEqual(results, {"pre_p1": "valid", "p1_rootfs": "valid",
                                   "p2_recoveryfs": "valid", "p3_userdata": "not_requested"})
        self.assertTrue(report["fingerprint"]["verifiable"])
        self.assertTrue(report["fingerprint"]["matches"])
        self.assertTrue(report["sha256sums"]["matches"])
        self.assertEqual(report["labels_reread"]["p1_rootfs"]["label"], "rootfs")
        code, _ = run_main([str(self.dest), "--json"])
        self.assertEqual(code, verifier.EXIT_VALID)

    def test_valid_backup_with_p3(self) -> None:
        self.make_backup(include_userdata=True)
        report = self.assert_status("valid")
        self.assertEqual(report["components"][3]["result"], "valid")
        self.assertEqual(report["labels_reread"]["p3_userdata"]["label"], "KOBOeReader")

    def test_valid_single_pass_backup(self) -> None:
        self.make_backup(reread=False)
        self.assert_status("valid")

    def test_unrequested_p3_file_is_only_a_warning(self) -> None:
        self.make_backup()
        (self.dest / "p3-userdata.img").write_bytes(b"stray")
        report = self.assert_status("valid")
        self.assertTrue(any("not requested" in w for w in report["warnings"]))


class FileProblemTests(VerifyBackupTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_backup()

    def test_missing_component_file_is_inconsistent(self) -> None:
        (self.dest / "p2-recoveryfs.img").unlink()
        self.assert_status("inconsistent")
        code, _ = run_main([str(self.dest)])
        self.assertEqual(code, verifier.EXIT_INCONSISTENT)

    def test_truncated_component_file_is_inconsistent(self) -> None:
        path = self.dest / "p1-rootfs.img"
        path.write_bytes(path.read_bytes()[:-512])
        report = self.assert_status("inconsistent")
        self.assertTrue(any("truncated" in i for i in report["inconsistencies"]))

    def test_corrupted_component_file_is_inconsistent(self) -> None:
        path = self.dest / "p1-rootfs.img"
        data = bytearray(path.read_bytes())
        data[4096] ^= 0x01
        path.write_bytes(bytes(data))
        report = self.assert_status("inconsistent")
        self.assertEqual(report["components"][1]["result"], "not_valid")

    def test_corrupted_pre_p1_breaks_fingerprint_check(self) -> None:
        path = self.dest / "pre-p1.bin"
        data = bytearray(path.read_bytes())
        data[0x90000] ^= 0xFF
        path.write_bytes(bytes(data))
        report = self.assert_status("inconsistent")
        self.assertFalse(report["fingerprint"]["verifiable"])

    def test_missing_sha256sums_is_inconsistent_for_finished_backup(self) -> None:
        (self.dest / "SHA256SUMS").unlink()
        self.assert_status("inconsistent")

    def test_divergent_sha256sums_is_inconsistent(self) -> None:
        sums = self.dest / "SHA256SUMS"
        lines = sums.read_text(encoding="utf-8").splitlines()
        lines[1] = "0" * 64 + lines[1][64:]
        sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assert_status("inconsistent")

    def test_sha256sums_listing_an_unknown_file_is_inconsistent(self) -> None:
        with open(self.dest / "SHA256SUMS", "a", encoding="utf-8") as sums:
            sums.write("0" * 64 + " *p3-userdata.img\n")
        self.assert_status("inconsistent")


class ManifestProblemTests(VerifyBackupTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_backup()

    def assert_invalid(self) -> None:
        report = self.assert_status("invalid")
        self.assertTrue(report["invalid_reasons"])
        code, _ = run_main([str(self.dest), "--json"])
        self.assertEqual(code, verifier.EXIT_INVALID)

    def test_missing_manifest_is_invalid(self) -> None:
        (self.dest / "backup-manifest.json").unlink()
        self.assert_invalid()

    def test_non_json_manifest_is_invalid(self) -> None:
        (self.dest / "backup-manifest.json").write_text("{not json", encoding="utf-8")
        self.assert_invalid()

    def test_unsupported_schema_is_invalid(self) -> None:
        self.edit_manifest(lambda d: d.update(schema_version=2))
        self.assert_invalid()

    def test_boolean_schema_is_invalid(self) -> None:
        self.edit_manifest(lambda d: d.update(schema_version=True))
        self.assert_invalid()

    def test_foreign_tool_is_invalid(self) -> None:
        self.edit_manifest(lambda d: d.update(tool="something-else"))
        self.assert_invalid()

    def test_missing_component_entry_is_invalid(self) -> None:
        self.edit_manifest(lambda d: d["components"].pop())
        self.assert_invalid()

    def test_missing_directory_is_invalid(self) -> None:
        self.dest = self.tmp / "nowhere"
        self.assert_invalid()

    def test_contradictory_recorded_hash_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: self.component(d, "p1_rootfs").update(sha256_stream="0" * 64))
        self.assert_status("inconsistent")

    def test_single_pass_with_reread_hash_is_inconsistent(self) -> None:
        def change(d: dict[str, Any]) -> None:
            d["options"]["source_reread"] = False
        self.edit_manifest(change)
        report = self.assert_status("inconsistent")
        self.assertTrue(any("--single-pass" in i for i in report["inconsistencies"]))

    def test_reread_enabled_without_reread_hash_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: self.component(d, "p2_recoveryfs").pop("sha256_source_reread"))
        self.assert_status("inconsistent")

    def test_declared_fingerprint_mismatch_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: d["target_fingerprint"].update(fingerprint_sha256="1" * 64))
        report = self.assert_status("inconsistent")
        self.assertFalse(report["fingerprint"]["matches"])

    def test_fingerprint_fields_consistent_with_each_other_but_not_with_file(self) -> None:
        def change(d: dict[str, Any]) -> None:
            fp = d["target_fingerprint"]
            fp["pre_p1_sha256"] = "2" * 64
            stable = {k: fp[k] for k in ("algorithm", "pre_p1_size", "pre_p1_sha256", "hwconfig_sha256", "partitions")}
            fp["fingerprint_sha256"] = hashlib.sha256(
                json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
        self.edit_manifest(change)
        report = self.assert_status("inconsistent")
        self.assertEqual(report["fingerprint"]["fields"]["pre_p1_sha256"], "differs")

    def test_declared_geometry_mismatch_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: d["mbr"]["partitions"][1].update(start_lba=9999))
        self.assert_status("inconsistent")

    def test_declared_label_mismatch_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: d["mbr"]["partitions"][0].update(label="other"))
        self.assert_status("inconsistent")

    def test_userdata_option_contradiction_is_inconsistent(self) -> None:
        self.edit_manifest(lambda d: d["options"].update(include_userdata=True))
        self.assert_status("inconsistent")

    def test_complete_flag_alone_is_not_trusted(self) -> None:
        self.edit_manifest(lambda d: self.component(d, "p2_recoveryfs").update(status="failed"))
        report = self.assert_status("inconsistent")
        self.assertTrue(any("complete: true" in i for i in report["inconsistencies"]))


class UnfinishedBackupTests(VerifyBackupTestCase):
    def interrupted_backup(self) -> None:
        original = backup.read_at

        def interrupt(handle: Any, offset: int, size: int, *args: Any) -> bytes:
            if offset == P1 and size == P1_SIZE:
                raise KeyboardInterrupt
            return original(handle, offset, size, *args)

        with mock.patch.object(backup, "read_at", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.make_backup()

    def test_interrupted_backup_is_incomplete(self) -> None:
        self.interrupted_backup()
        report = self.assert_status("incomplete")
        self.assertEqual(report["components"][0]["result"], "valid")
        self.assertEqual(report["components"][1]["result"], "not_verified")
        self.assertIn("p1-rootfs.img.part", report["leftovers"])
        code, _ = run_main([str(self.dest)])
        self.assertEqual(code, verifier.EXIT_INCOMPLETE)

    def test_part_file_renamed_to_final_name_is_not_trusted(self) -> None:
        self.interrupted_backup()
        (self.dest / "p1-rootfs.img.part").replace(self.dest / "p1-rootfs.img")
        report = self.assert_status("incomplete")
        self.assertEqual(report["components"][1]["result"], "not_verified")
        self.assertTrue(any("not trusted" in w for w in report["warnings"]))

    def test_interrupted_backup_claiming_complete_is_inconsistent(self) -> None:
        self.interrupted_backup()
        self.edit_manifest(lambda d: d.update(complete=True, status="complete"))
        self.assert_status("inconsistent")

    def test_failed_backup_is_incomplete_and_failed_file_never_valid(self) -> None:
        original = backup.readback_sha256

        def corrupt(path: Path) -> tuple[str, int]:
            if path.name.startswith("p2-recoveryfs"):
                with open(path, "r+b") as handle:
                    handle.write(b"\xff")
            return original(path)

        with mock.patch.object(backup, "readback_sha256", side_effect=corrupt):
            self.make_backup()
        report = self.assert_status("incomplete")
        self.assertIn("p2-recoveryfs.img.FAILED", report["leftovers"])
        self.assertNotEqual(report["components"][2]["result"], "valid")
        self.assertTrue(report["sha256sums"]["matches"], "SHA256SUMS lists only verified files")

    def test_failed_file_promoted_to_verified_is_inconsistent(self) -> None:
        self.test_failed_backup_is_incomplete_and_failed_file_never_valid()
        self.edit_manifest(lambda d: self.component(d, "p2_recoveryfs").update(status="verified"))
        self.assert_status("inconsistent")


class PathSafetyTests(VerifyBackupTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_backup()
        self.outside = self.tmp / "outside.img"
        self.outside.write_bytes((self.dest / "p1-rootfs.img").read_bytes())

    def assert_refused_name(self, name: str) -> None:
        self.edit_manifest(lambda d: self.component(d, "p1_rootfs").update(file=name))
        opened: list[str] = []
        real_open = builtins.open

        def tracking(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            opened.append(os.path.realpath(os.fspath(file)) if not isinstance(file, int) else "")
            return real_open(file, mode, *args, **kwargs)

        with mock.patch("builtins.open", new=tracking):
            self.assert_status("inconsistent")
        self.assertNotIn(os.path.realpath(self.outside), opened, "file outside the backup was read")

    def test_traversal_is_refused(self) -> None:
        self.assert_refused_name("../outside.img")

    def test_absolute_path_is_refused(self) -> None:
        self.assert_refused_name(str(self.outside))

    def test_windows_drive_path_is_refused(self) -> None:
        self.assert_refused_name("C:outside.img")

    def test_symlink_component_is_refused(self) -> None:
        target = self.dest / "p1-rootfs.img"
        target.unlink()
        try:
            target.symlink_to(self.outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.assert_refused_name("p1-rootfs.img")

    def test_safe_file_rejects_escaping_names(self) -> None:
        root = self.dest.resolve()
        for name in ("../outside.img", str(self.outside), "C:outside.img", "a\\b", "..", ".", "",
                     "sub/p1-rootfs.img", ".hidden"):
            path, problem = verifier.safe_file(root, name)
            self.assertIsNone(path, name)
            self.assertTrue(problem, name)
        path, problem = verifier.safe_file(root, "p1-rootfs.img")
        self.assertIsNone(problem)
        self.assertEqual(path, root / "p1-rootfs.img")

    def test_safe_file_rejects_symlinks(self) -> None:
        link = self.dest / "link.img"
        try:
            link.symlink_to(self.outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        path, problem = verifier.safe_file(self.dest.resolve(), "link.img")
        self.assertIsNone(path)
        self.assertIn("symbolic link", problem)

    def test_symlinked_manifest_is_invalid(self) -> None:
        manifest = self.dest / "backup-manifest.json"
        copy = self.tmp / "manifest-outside.json"
        copy.write_bytes(manifest.read_bytes())
        manifest.unlink()
        try:
            manifest.symlink_to(copy)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        report = self.assert_status("invalid")
        self.assertTrue(any("symbolic link" in r for r in report["invalid_reasons"]))

    def test_unsafe_name_in_sha256sums_is_refused(self) -> None:
        with open(self.dest / "SHA256SUMS", "a", encoding="utf-8") as sums:
            sums.write("0" * 64 + " *../outside.img\n")
        self.assert_status("inconsistent")


class NoWriteAndOutputTests(VerifyBackupTestCase):
    def test_verifier_never_writes_in_backup_directory(self) -> None:
        self.make_backup(include_userdata=True)
        (self.dest / "leftover.part").write_bytes(b"x")
        before = snapshot(self.dest)
        real_open, real_os_open = builtins.open, os.open
        modes: list[str] = []

        def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            modes.append(mode)
            self.assertEqual(mode, "rb", f"verifier opened {file} with mode {mode}")
            return real_open(file, mode, *args, **kwargs)

        def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), 0)
            return real_os_open(path, flags, *args, **kwargs)

        with mock.patch("builtins.open", new=guarded_open), mock.patch("os.open", new=guarded_os_open):
            report = verifier.verify_backup(self.dest)
            code, out = run_main([str(self.dest), "--json"])
        self.assertEqual(report["status"], "valid")
        self.assertEqual(code, 0)
        self.assertTrue(modes)
        self.assertEqual(snapshot(self.dest), before, "backup directory must be left untouched")

    def test_json_output_is_clean_ascii(self) -> None:
        self.dest = self.tmp / "sauvegarde été ✓"
        self.make_backup()
        code, out = run_main([str(self.dest), "--json"])
        self.assertEqual(code, 0)
        out.encode("ascii")  # safe on any Windows console code page
        data = json.loads(out)
        self.assertEqual(data["status"], "valid")
        self.assertEqual(data["schema_version"], 1)
        self.assertIn("declared_only", data)

    def test_human_output_fr_and_en(self) -> None:
        self.make_backup()
        _, fr = run_main([str(self.dest)])
        _, en = run_main([str(self.dest), "--lang", "en"])
        self.assertIn("SAUVEGARDE VALIDE", fr)
        self.assertIn("ni leur authenticité", fr)
        self.assertIn("BACKUP VALID", en)
        self.assertIn("neither their authenticity", en)


if __name__ == "__main__":
    unittest.main()
