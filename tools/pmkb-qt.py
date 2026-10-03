"""Qt workshop: local-file workflows through the existing CLI, never a shell."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                              QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
                              QPushButton, QScrollArea, QSplitter, QTabWidget, QVBoxLayout, QWidget)

spec = importlib.util.spec_from_file_location("gui_workflows", Path(__file__).with_name("gui-workflows.py"))
model = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(model)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PimpMyKobo — Atelier local")
        self.resize(1100, 850)
        self.setMinimumSize(920, 720)
        self.report = None
        self.output = bytearray()
        self.errors = bytearray()
        self.overflow = False
        self.keys = list(model.WORKFLOWS)
        self.fields = {}
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(lambda: self.capture(False))
        self.process.readyReadStandardError.connect(lambda: self.capture(True))
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(14)
        title = QLabel("PimpMyKobo"); title.setObjectName("brand")
        layout.addWidget(title)
        layout.addWidget(QLabel("Atelier local · sauvegardes, reconstruction et simulation"))
        boundary = QLabel("Travail sur fichiers uniquement. La restauration physique se fait séparément sous Linux Live.")
        boundary.setObjectName("boundary"); boundary.setWordWrap(True); layout.addWidget(boundary)
        split = QSplitter(); layout.addWidget(split, 1)
        self.navigation = QListWidget(); self.navigation.setMinimumWidth(250)
        self.navigation.setWordWrap(True)
        self.navigation.addItems([model.WORKFLOWS[key].title for key in self.keys])
        split.addWidget(self.navigation)
        content = QWidget(); split.addWidget(content); split.setStretchFactor(1, 1)
        column = QVBoxLayout(content); column.setContentsMargins(20, 0, 0, 0); column.setSpacing(12)
        self.heading = QLabel(); self.heading.setObjectName("heading"); column.addWidget(self.heading)
        self.description = QLabel(); self.description.setWordWrap(True); column.addWidget(self.description)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        self.form_container = QWidget(); self.form = QFormLayout(self.form_container)
        self.form.setContentsMargins(0, 5, 5, 5); self.form.setSpacing(9)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        scroll.setWidget(self.form_container); column.addWidget(scroll, 2)
        self.consent_row = QWidget(); consent_layout = QHBoxLayout(self.consent_row)
        consent_layout.setContentsMargins(0, 0, 0, 0)
        self.consent = QCheckBox(); self.consent_label = QLabel(); self.consent_label.setWordWrap(True)
        consent_layout.addWidget(self.consent); consent_layout.addWidget(self.consent_label, 1)
        column.addWidget(self.consent_row)
        self.action = QPushButton(); self.action.setObjectName("primary"); self.action.clicked.connect(self.run)
        column.addWidget(self.action)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setRange(0, 1)
        self.progress.setValue(0); column.addWidget(self.progress)
        self.status = QLabel("Choisissez une opération et ses fichiers."); self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText); column.addWidget(self.status)
        self.tabs = QTabWidget(); column.addWidget(self.tabs, 2)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True)
        self.details = QPlainTextEdit(); self.details.setReadOnly(True)
        self.tabs.addTab(self.summary, "Résumé"); self.tabs.addTab(self.details, "Rapport et diagnostics")
        self.save = QPushButton("Enregistrer le rapport…"); self.save.setEnabled(False)
        self.save.clicked.connect(self.save_result); column.addWidget(self.save)
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; color: #263b35; }
            QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget { background: #f4f3ed; }
            QLabel#brand { font-size: 29px; font-weight: 650; color: #183e32; }
            QLabel#heading { font-size: 20px; font-weight: 600; }
            QLabel#boundary { background: #e5ece5; padding: 12px; border-radius: 6px; }
            QListWidget { background: #eaece4; border: none; border-radius: 8px; padding: 5px; }
            QListWidget::item { padding: 12px 8px; }
            QListWidget::item:selected { background: #d4e3d6; color: #183e32; border-radius: 5px; }
            QLineEdit, QPlainTextEdit { background: #fffefa; border: 1px solid #cbd4cb; border-radius: 5px; padding: 7px; }
            QPushButton { background: #e4e9e1; border: 1px solid #cbd4cb; padding: 9px; border-radius: 5px; }
            QPushButton#primary { background: #23533e; color: white; font-weight: 600; }
            QPushButton:disabled { background: #dadfd7; color: #747e73; }
            QProgressBar { border: none; background: #e0e5dc; height: 5px; }
            QProgressBar::chunk { background: #527d55; }
        """)
        self.navigation.currentRowChanged.connect(self.select_workflow)
        self.navigation.setCurrentRow(0)

    def select_workflow(self, row: int):
        if row < 0 or row >= len(self.keys):
            return
        self.key = self.keys[row]
        workflow = model.WORKFLOWS[self.key]
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields = {}
        self.heading.setText(workflow.title); self.description.setText(workflow.description)
        for field in workflow.fields:
            entry = QLineEdit(); entry.setPlaceholderText("64 caractères hexadécimaux" if field.kind == "sha" else "Choisir un fichier…")
            entry.setAccessibleName(field.label); self.fields[field.key] = entry
            row_widget = QWidget(); line = QHBoxLayout(row_widget); line.setContentsMargins(0, 0, 0, 0)
            line.addWidget(entry, 1)
            if field.kind != "sha":
                browse = QPushButton("Choisir…")
                browse.clicked.connect(lambda checked=False, f=field, e=entry: self.browse(f, e))
                line.addWidget(browse)
            self.form.addRow(field.label, row_widget)
        self.consent.setAccessibleName(workflow.consent); self.consent.setChecked(False)
        self.consent_label.setText(workflow.consent)
        self.consent_row.setVisible(bool(workflow.consent))
        self.action.setText(workflow.button)
        self.action.setEnabled(not (self.key == "rebuild" and sys.platform != "linux"))
        self.report = None; self.save.setEnabled(False); self.summary.clear(); self.details.clear()
        self.status.setText("Reconstruction disponible sous Linux ou WSL." if not self.action.isEnabled()
                            else "Sélectionnez vos fichiers, puis lancez l'opération.")

    def browse(self, field, entry):
        picker = QFileDialog.getSaveFileName if field.kind == "output" else QFileDialog.getOpenFileName
        path, _ = picker(self, field.label, "", "Tous les fichiers (*)")
        if path:
            entry.setText(path)

    def set_busy(self, busy: bool):
        self.navigation.setEnabled(not busy); self.form_container.setEnabled(not busy)
        self.consent.setEnabled(not busy); self.action.setEnabled(not busy and not (self.key == "rebuild" and sys.platform != "linux"))
        self.progress.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress.setValue(1)
        self.save.setEnabled(not busy and self.report is not None)

    def run(self):
        if self.process.state() != QProcess.NotRunning:
            return
        self.report = None; self.save.setEnabled(False); self.summary.clear(); self.details.clear()
        try:
            values = {key: entry.text() for key, entry in self.fields.items()}
            if self.key == "report":
                self.report = model.read_report(values["report"])
                self.display_report(loaded=True)
                return
            args = model.build_request(self.key, values, self.consent.isChecked())
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc)); self.summary.setPlainText(str(exc))
            return
        self.output.clear(); self.errors.clear(); self.overflow = False
        self.set_busy(True); self.status.setText("Opération en cours… Les contrôles peuvent prendre plusieurs minutes.")
        self.process.start(sys.executable, [str(Path(__file__).with_name("pmkb.py")), *args])

    def capture(self, error: bool):
        data = bytes(self.process.readAllStandardError() if error else self.process.readAllStandardOutput())
        target = self.errors if error else self.output
        remaining = model.MAX_REPORT_BYTES - len(self.output) - len(self.errors)
        target.extend(data[:max(0, remaining)])
        if len(data) > remaining:
            self.overflow = True

    def finished(self, code: int, exit_status):
        self.capture(False); self.capture(True)
        self.details.setPlainText(self.output.decode("utf-8", errors="replace") + "\n" + self.errors.decode("utf-8", errors="replace"))
        try:
            if self.overflow:
                raise ValueError("Sortie trop volumineuse : le résultat n'est pas interprété.")
            if exit_status != QProcess.NormalExit:
                raise ValueError("L'opération s'est interrompue. Examinez les fichiers temporaires avant de relancer.")
            report = json.loads(self.output.decode("utf-8"))
            if not isinstance(report, dict):
                raise ValueError("La commande n'a pas fourni un rapport JSON valide.")
            self.report = report
            self.display_report(failed=code != 0)
            if self.errors:
                self.details.appendPlainText("\nDiagnostics :\n" + self.errors.decode("utf-8", errors="replace"))
        except (ValueError, UnicodeError) as exc:
            self.report = None; self.status.setText(str(exc)); self.summary.setPlainText(str(exc))
        self.set_busy(False)

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.report = None
            self.status.setText("Impossible de démarrer l'outil : " + self.process.errorString())
            self.set_busy(False)

    def display_report(self, loaded: bool = False, failed: bool = False):
        status = self.report.get("status", "")
        failed = failed or status in ("failed", "refused", "interrupted")
        title = ("Rapport chargé — contrôles non rejoués." if loaded else
                 "Opération refusée ou échouée. Consultez les diagnostics." if failed else
                 "Contrôles terminés. Consultez le rapport avant la suite.")
        lines = [title]
        provenance = self.report.get("input_provenance", self.report.get("provenance", {}))
        if isinstance(provenance, dict) and provenance.get("kind") == "legacy/imported":
            lines.extend(("Provenance : sauvegarde historique importée.", "Association des fichiers : déclarée, non vérifiée."))
        if status:
            lines.append("État indiqué dans le rapport : " + str(status))
        for name, label in (("errors", "Erreurs"), ("warnings", "Limites et remarques"), ("limitations", "Limites")):
            values = self.report.get(name, [])
            if isinstance(values, list) and values:
                lines.extend(("", label + " :", *(str(value) for value in values)))
        self.status.setText(title); self.summary.setPlainText("\n".join(lines))
        self.details.setPlainText(json.dumps(self.report, ensure_ascii=False, indent=2))
        self.save.setEnabled(True)

    def save_result(self):
        if self.report is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer une copie du rapport", "rapport.json", "Rapports JSON (*.json)")
        if not path:
            return
        try:
            model.save_report(path, self.report)
            self.status.setText("Rapport enregistré : " + path)
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def closeEvent(self, event):
        if self.process.state() != QProcess.NotRunning:
            event.ignore()
            QMessageBox.information(self, "Opération en cours", "Attendez la fin de l'opération avant de fermer l'atelier.")
        else:
            event.accept()
