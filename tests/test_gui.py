import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_import_legacy_backup import load
import test_restore_rootfs as fixtures

model = load("gui_model_test", "gui-workflows.py")
try:
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


class LocalRequestsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "--write-p1 $ special.img"
        self.file.write_bytes(b"synthetic local file")

    def test_explicit_image_required_no_device_discovery_or_restore_route(self):
        for key, values in (("inspect", {"image": ""}), ("inspect", {}),
                            ("inspect", {"image": str(self.file), "device": "/dev/sda"}),
                            ("restore-p1", {}), ("report", {})):
            with self.subTest(key=key, values=values), self.assertRaises(ValueError):
                model.build_request(key, values)
        args = model.build_request("inspect", {"image": str(self.file)})
        self.assertEqual(str(self.file.resolve()), args[1])
        self.assertEqual(["--json", "--hash-boot"], args[2:])

    def test_raw_devices_unc_directories_and_nonfiles_refused_before_open(self):
        for value in ("/dev/sda", "\\\\.\\PhysicalDrive1", "\\\\server\\share\\file", str(self.root)):
            with self.subTest(value=value), mock.patch.object(Path, "open", side_effect=AssertionError("opened")):
                with self.assertRaises((ValueError, OSError)):
                    model.build_request("inspect", {"image": value})

    @unittest.skipUnless(os.name == "posix", "POSIX special files")
    def test_device_alias_and_fifo_refused(self):
        alias = self.root / "alias"; alias.symlink_to("/dev/null")
        fifo = self.root / "fifo"; os.mkfifo(fifo)
        for path in (alias, fifo):
            with self.subTest(path=path), self.assertRaises(ValueError):
                model.local_path(str(path))

    def test_legacy_declaration_is_required_and_hashes_not_invented(self):
        values = {"prefix": str(self.file), "recovery": str(self.file),
                  "output": str(self.root / "new.json"), "prefix_sha": "A" * 64, "recovery_sha": "b" * 64}
        with self.assertRaises(ValueError):
            model.build_request("import", values)
        args = model.build_request("import", values, consent=True)
        self.assertIn("--declare-same-source", args)
        self.assertIn("a" * 64, args)
        values["recovery_sha"] = "unknown"
        with self.assertRaises(ValueError):
            model.build_request("import", values, consent=True)
        self.assertFalse((self.root / "new.json").exists())

    def test_reports_read_without_promoting_provenance_and_save_no_clobber(self):
        report = {"status": "ok", "provenance": {"kind": "legacy/imported", "association": "declared_not_verified"},
                  "physical_restore_eligible": False}
        source = self.root / "report.json"; source.write_text(json.dumps(report), encoding="utf-8")
        with mock.patch.object(model.legacy, "digest", side_effect=AssertionError("requalified")):
            self.assertEqual(report, model.read_report(str(source)))
        dest = self.root / "copy.json"; model.save_report(str(dest), report)
        with self.assertRaises(ValueError):
            model.save_report(str(dest), {"modified": True})
        self.assertEqual(report, json.loads(dest.read_text(encoding="utf-8")))
        source.write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            model.read_report(str(source))
        source.write_bytes(b" " * 65)
        with mock.patch.object(model, "MAX_REPORT_BYTES", 64), self.assertRaises(ValueError):
            model.read_report(str(source))


@unittest.skipUnless(QApplication is not None, "optional Qt dependency absent")
class QtWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.qt = load("qt_workshop_test", "pmkb-qt.py")

    def setUp(self):
        self.window = self.qt.MainWindow(); self.addCleanup(self.window.close)
        self.fixture = fixtures.RestoreSimulationTests("test_simulation_only_replaces_p1_in_a_new_copy")
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)

    def choose(self, key, values):
        self.window.navigation.setCurrentRow(self.window.keys.index(key))
        for name, value in values.items():
            self.window.fields[name].setText(str(value))

    def complete(self):
        self.assertTrue(self.window.process.waitForStarted(5000), self.window.process.errorString())
        self.assertTrue(self.window.process.waitForFinished(20000), "local subprocess timed out")
        self.app.processEvents()
        self.assertEqual(QProcess.NotRunning, self.window.process.state())

    def test_real_subprocess_simulates_only_in_new_copy_and_preserves_legacy(self):
        f = self.fixture
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in f.paths[:-1]}
        self.choose("simulate", dict(zip(("manifest", "rebuild", "rootfs", "backup", "output"), f.paths)))
        self.window.run()
        self.assertEqual(QProcess.NotRunning, self.window.process.state())
        self.assertFalse(f.output.exists())
        self.window.consent.setChecked(True); self.window.run(); self.complete()
        self.assertEqual("ok", self.window.report["status"], self.window.details.toPlainText())
        self.assertFalse(self.window.report["physical_restore_eligible"])
        self.assertIn("déclarée, non vérifiée", self.window.summary.toPlainText())
        self.assertTrue(f.output.exists())
        for path, digest in before.items():
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(sys.executable, self.window.process.program())
        self.assertNotIn("--write-p1", self.window.process.arguments())

    def test_inspection_requires_local_file_and_refuses_device_without_launch(self):
        self.choose("inspect", {"image": "\\\\.\\PhysicalDrive1"})
        with mock.patch.object(self.window.process, "start", side_effect=AssertionError("launched")):
            self.window.run()
        self.assertIsNone(self.window.report)
        self.choose("inspect", {"image": self.fixture.target})
        self.window.run(); self.complete()
        self.assertIsNotNone(self.window.report, self.window.details.toPlainText())
        self.assertIn(str(self.fixture.target.resolve()), self.window.process.arguments())

    def test_loaded_report_does_not_claim_checks_were_replayed(self):
        self.choose("report", {"report": self.fixture.report})
        with mock.patch.object(self.window.process, "start", side_effect=AssertionError("launched")):
            self.window.run()
        self.assertIn("contrôles non rejoués", self.window.summary.toPlainText())
        self.assertTrue(self.window.save.isEnabled())

    def test_failed_exit_preserves_stderr_and_does_not_claim_success(self):
        self.window.output.extend(b'{"status":"ok","errors":[]}')
        self.window.errors.extend(b"backend failed")
        self.window.finished(1, QProcess.NormalExit)
        self.assertIn("échouée", self.window.status.text())
        self.assertIn("backend failed", self.window.details.toPlainText())

    def test_crash_or_truncated_output_is_not_accepted(self):
        for overflow, status in ((True, QProcess.NormalExit), (False, QProcess.CrashExit)):
            self.window.output.clear(); self.window.output.extend(b'{"status":"ok"}')
            self.window.overflow = overflow
            self.window.finished(0, status)
            self.assertIsNone(self.window.report)
            self.assertFalse(self.window.save.isEnabled())
