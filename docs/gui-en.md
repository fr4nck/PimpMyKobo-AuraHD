# Qt/PySide6 local workshop

The first GUI reads reports, inspects explicitly selected images, imports historical evidence, prepares/builds P1, simulates replacement and prepares a local plan. It has no physical restore button, device discovery or privilege elevation. Outputs must be new files. Historical association remains declared, not verified, with explicit provenance acceptance.

Python 3.10+ and Qt/PySide6 are required only for the GUI. From the checkout:

```sh
python -m venv .venv
.venv/bin/python -m pip install PySide6-Essentials==6.10.2
.venv/bin/python tools/pmkb.py gui
```

On Windows use `.venv/Scripts/python.exe` instead of `.venv/bin/python`. Actual reconstruction is disabled in the Windows interface and requires Linux or WSL with e2fsprogs, fakeroot and tar. WSL needs a working graphical environment. The application does not automatically switch from Windows to WSL.

The Debian launcher `pmkb gui` uses system Python and requires Qt available to that interpreter. For Qt in a virtual environment, invoke that Python explicitly:

```sh
.venv/bin/python /usr/lib/pimpmykobo-aura-hd/pmkb.py gui
```

The package does not bundle or install Qt. CLI commands and `pmkb gui --help` work without it. Progress indicates an active operation without an estimated percentage. Wait for completion before closing. Existing validators run in a subprocess without a shell. Interrupted operations may leave temporary files; examine diagnostics before retrying.

Loading a report does not replay checks or prove authenticity. Reports and diagnostics are capped at 16 MiB. Saving creates a new JSON copy without overwriting. Synthetic tests do not qualify hardware restoration or bootability.
