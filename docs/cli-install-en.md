# Install pmkb on Debian/Ubuntu and WSL

The local `pimpmykobo-aura-hd` package installs the `pmkb` command, the existing Python tools and their documentation. It requires Python 3.10+ and depends on Python, e2fsprogs, fakeroot and tar. No third-party Python modules, Qt, services, udev rules or maintainer scripts are installed. Package installation does not run tools or access devices. No private Kobo data is included.

On Debian/Ubuntu or their WSL distributions, from the package directory:

```sh
sudo apt install ./pimpmykobo-aura-hd_0.1.0_all.deb
pmkb --version
pmkb --help
pmkb rebuild-rootfs --help
```

APT may install missing system dependencies. Remove the package with `sudo apt remove pimpmykobo-aura-hd`. User backups and reports are outside the package and are not removed.

Commands: `inspect`, `verify-recovery`, `import-legacy`, `rebuild-rootfs`, `simulate`, `prepare-p1` and `restore-p1`. Arguments, JSON output and exit codes are forwarded unchanged to the existing scripts. Use `pmkb COMMAND --help`. With no command, pmkb displays help only. It never automatically elevates privileges. `inspect` without a source retains the existing inspector's read-only disk discovery; use an explicit image path to avoid discovery.

WSL supports local-file qualification, reconstruction and simulation. Physical P1 access remains rejected under WSL; packaging does not change the native Linux guard. The first physical restore requires native Linux Live and separate explicit authorization; see the [Linux procedure](restore-p1-linux-en.md). Preparing or installing the package grants no restore authorization.

Build a local package from the repository on Debian/Ubuntu or WSL with dpkg-deb:

```sh
python3 tools/build-deb.py /existing/directory/pimpmykobo-aura-hd_0.1.0_all.deb \
  --maintainer 'Your name <your-address@example.org>'
```

Provide the actual package contact. The builder uses an explicit script/document allowlist, LF line endings and fixed owners/timestamps for reproducibility. It refuses existing output, needs no root and never installs anything. Installed `build-info.json` records the payload hashes and version. This is a local package, not a Debian/Ubuntu repository publication.

Paths: `/usr/bin/pmkb`, `/usr/lib/pimpmykobo-aura-hd`, `/usr/share/doc/pimpmykobo-aura-hd`. No backups, firmware, tests or package builder are shipped. The scripts can also be used directly from the checkout. A future Qt/PySide6 interface can reuse these commands and JSON reports; no GUI is implemented or required now.
