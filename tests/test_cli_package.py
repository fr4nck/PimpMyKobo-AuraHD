import contextlib
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_import_legacy_backup import load
import test_restore_rootfs as simulation_fixtures

cli = load("cli", "pmkb.py")
package = load("package", "build-deb.py")
REPO = Path(__file__).resolve().parent.parent
MAINTAINER = "Test Packager <test@example.invalid>"


class CommandTests(unittest.TestCase):
    def test_default_help_never_dispatches_or_accesses_devices(self):
        with mock.patch.object(cli.runpy, "run_path", side_effect=AssertionError("dispatched")), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(0, cli.main([]))
        self.assertIn("restore-p1", out.getvalue())
        self.assertIn("Physical restoration is refused under WSL", out.getvalue())

    def test_every_command_forwards_arguments_exactly_and_preserves_exit_codes(self):
        original_argv = sys.argv
        for command, (script, _) in cli.COMMANDS.items():
            forwarded = ["path with spaces", "--device", "/dev/explicit", "--write-p1",
                         "--authorize-plan-sha256", "a" * 64]
            def backend(path, run_name):
                self.assertEqual(Path(path).name, script)
                self.assertEqual("__main__", run_name)
                self.assertEqual([path, *forwarded], sys.argv)
                raise SystemExit(7)
            with self.subTest(command=command), mock.patch.object(cli.runpy, "run_path", side_effect=backend):
                self.assertEqual(7, cli.main([command, *forwarded]))
            self.assertIs(original_argv, sys.argv)

    def test_unknown_command_refused_without_dispatch(self):
        with mock.patch.object(cli.runpy, "run_path", side_effect=AssertionError("dispatched")), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                cli.main(["format-card"])
        self.assertEqual(2, error.exception.code)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "staged"

    def test_package_allowlist_has_no_private_data_hooks_or_services(self):
        source = self.root / "source"
        for directory, names in (("tools", package.SCRIPTS), ("docs", package.DOCS)):
            (source / directory).mkdir(parents=True, exist_ok=True)
            for name in names:
                (source / directory / name).write_bytes((REPO / directory / name).read_bytes())
        (source / "tools/private.img").write_bytes(b"PRIVATE")
        (source / "docs/secret.bin").write_bytes(b"PRIVATE")
        metadata = package.stage_package(source, self.stage, MAINTAINER)
        expected = {"usr/bin/pmkb", "DEBIAN/control", "DEBIAN/md5sums",
                    f"usr/share/doc/{package.PACKAGE}/build-info.json"}
        expected.update(f"usr/lib/{package.PACKAGE}/{name}" for name in package.SCRIPTS)
        expected.update(f"usr/share/doc/{package.PACKAGE}/{name}" for name in package.DOCS)
        actual = {p.relative_to(self.stage).as_posix() for p in self.stage.rglob("*") if p.is_file()}
        self.assertEqual(expected, actual)
        for path, sha in metadata["files_sha256"].items():
            self.assertEqual(sha, hashlib.sha256((self.stage / path).read_bytes()).hexdigest())
        control = (self.stage / "DEBIAN/control").read_text()
        self.assertIn("Depends: python3 (>= 3.10), e2fsprogs, fakeroot, tar", control)
        self.assertIn("Architecture: all", control)

    def test_relocated_launcher_and_all_peer_imports_work(self):
        package.stage_package(REPO, self.stage, MAINTAINER)
        launcher = self.stage / "usr/bin/pmkb"
        for args in ([], ["--version"], *([command, "--help"] for command in cli.COMMANDS)):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(launcher), *args],
                                        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertTrue(result.stdout)
        # All positional paths are deliberately nonexistent. The authorization
        # refusal must happen before any evidence or physical-device access.
        result = subprocess.run([sys.executable, str(launcher), "restore-p1", *(["missing"] * 9),
                                 "--write-p1", "--device", "/dev/must-not-open", "--ack-linux-live"],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("refused", report["status"])
        self.assertFalse(report["device_write_attempted"])

    def test_packaged_cli_runs_a_real_synthetic_simulation(self):
        package.stage_package(REPO, self.stage, MAINTAINER)
        fixture = simulation_fixtures.RestoreSimulationTests("test_simulation_only_replaces_p1_in_a_new_copy")
        fixture.setUp()
        try:
            before = fixture.target.read_bytes()
            command = self.stage / "usr/bin/pmkb"
            result = subprocess.run([sys.executable, str(command), "simulate", *(str(p) for p in fixture.paths),
                                     "--accept-legacy-import", "--simulate"], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("ok", report["status"], report)
            self.assertTrue(report["checks"]["outside_p1_unchanged"])
            self.assertFalse(report["physical_restore_eligible"])
            self.assertEqual(before, fixture.target.read_bytes())
        finally:
            fixture.doCleanups()

    def test_cli_retains_wsl_refusal_even_with_authorization_token(self):
        path = self.root / "plan.json"; path.write_bytes(b"synthetic reviewed-plan fixture")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with (mock.patch.object(sys, "platform", "linux"),
              mock.patch.object(platform, "release", return_value="6.6-microsoft-standard-WSL2"),
              mock.patch.object(os, "open", side_effect=AssertionError("device opened")),
              contextlib.redirect_stdout(io.StringIO()) as out):
            code = cli.main(["restore-p1", str(path), *(["missing"] * 8),
                             "--write-p1", "--device", "/dev/must-not-open", "--ack-linux-live",
                             "--authorize-plan-sha256", sha])
        self.assertEqual(1, code)
        result = json.loads(out.getvalue())
        self.assertEqual("refused", result["status"])
        self.assertFalse(result["device_write_attempted"])
        self.assertIn("WSL unsupported", result["errors"][0])

    def test_crlf_inputs_become_linux_text_and_md5sums_are_complete(self):
        package.stage_package(REPO, self.stage, MAINTAINER)
        for path in self.stage.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"\r\n", path.read_bytes())
        for line in (self.stage / "DEBIAN/md5sums").read_text().splitlines():
            md5, relative = line.split("  ", 1)
            self.assertEqual(md5, hashlib.md5((self.stage / relative).read_bytes()).hexdigest())
        self.assertEqual(b"#!/usr/bin/python3\n", (self.stage / "usr/bin/pmkb").read_bytes().splitlines(keepends=True)[0])

    def test_existing_outputs_bad_contact_and_device_paths_are_refused(self):
        self.stage.mkdir(); (self.stage / "keep").write_text("keep")
        with self.assertRaises(ValueError): package.stage_package(REPO, self.stage, MAINTAINER)
        self.assertEqual("keep", (self.stage / "keep").read_text())
        for maintainer in ("missing email", "Name <email>\nDepends: unsafe"):
            with self.assertRaises(ValueError): package.stage_package(REPO, self.root / "new", maintainer)
        for device in ("/dev/sdb", r"\\.\PhysicalDrive2"):
            with mock.patch.object(Path, "resolve", side_effect=AssertionError("device path canonicalized")):
                with self.assertRaises(ValueError): package.build(Path(device), MAINTAINER)
        output = self.root / "existing.deb"; output.write_bytes(b"keep")
        with self.assertRaises(ValueError): package.build(output, MAINTAINER)
        self.assertEqual(b"keep", output.read_bytes())

    def test_backend_failure_reports_diagnostic_and_publishes_nothing(self):
        output = self.root / "failed.deb"
        with (mock.patch.object(package.shutil, "which", return_value="/fake/dpkg-deb"),
              mock.patch.object(package.subprocess, "run", return_value=mock.Mock(returncode=2, stderr="bad control permissions"))):
            with self.assertRaisesRegex(ValueError, "bad control permissions"):
                package.build(output, MAINTAINER)
        self.assertFalse(output.exists())

    def test_concurrent_output_is_preserved_and_temporary_copy_is_cleaned(self):
        output = self.root / "race.deb"
        def backend(argv, **kwargs):
            Path(argv[-1]).write_bytes(b"synthetic package stub")
            return mock.Mock(returncode=0, stderr="")
        def competing_output(source, destination):
            Path(destination).write_bytes(b"concurrent output")
            raise FileExistsError("already exists")
        with (mock.patch.object(package.shutil, "which", return_value="/fake/dpkg-deb"),
              mock.patch.object(package.subprocess, "run", side_effect=backend),
              mock.patch.object(package.os, "link", side_effect=competing_output)):
            with self.assertRaises(FileExistsError): package.build(output, MAINTAINER)
        self.assertEqual(b"concurrent output", output.read_bytes())
        self.assertEqual([], list(self.root.glob(".pmkb-*.deb")))

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("dpkg-deb"), "real dpkg-deb backend")
    def test_real_deb_reproducible_owned_by_root_and_launches_when_extracted(self):
        first = self.root / "first.deb"; second = self.root / "second.deb"
        package.build(first, MAINTAINER); package.build(second, MAINTAINER)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        field = subprocess.run(["dpkg-deb", "--field", str(first), "Package", "Depends"],
                               text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertIn(package.PACKAGE, field.stdout)
        contents = subprocess.run(["dpkg-deb", "--contents", str(first)], text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertIn("root/root", contents.stdout)
        self.assertIn("./usr/bin/pmkb", contents.stdout)
        extracted = self.root / "extracted"
        subprocess.run(["dpkg-deb", "--extract", str(first), str(extracted)], check=True)
        command = extracted / "usr/bin/pmkb"
        self.assertTrue(command.stat().st_mode & 0o111)
        version = subprocess.run([sys.executable, str(command), "--version"],
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual(f"pmkb {cli.VERSION}", version.stdout.strip())
