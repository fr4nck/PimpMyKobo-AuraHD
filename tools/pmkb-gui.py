#!/usr/bin/env python3
"""Open the optional Qt/PySide6 local-file workshop. No physical restore UI."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("Qt/PySide6 est optionnel et n'est pas installé dans cet interpréteur.\n"
              "Voir docs/gui-fr.md pour l'installation ; la CLI reste disponible.", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("pmkb_qt", Path(__file__).with_name("pmkb-qt.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("PimpMyKobo")
    window = module.MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
