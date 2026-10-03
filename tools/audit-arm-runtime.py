#!/usr/bin/env python3
"""Read-only ELF dependency inventory for an extracted local PMKB rootfs."""
import argparse
import hashlib
import json
import os
import re
import stat
import struct
from pathlib import Path


def target(root, name):
    """Resolve links using guest /, never the host / (bounded against cycles)."""
    pending = name.split('/')
    parts = []
    links = 0
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                raise ValueError('path escapes rootfs')
            parts.pop()
            continue
        path = root.joinpath(*parts, part)
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            links += 1
            if links > 40:
                raise ValueError('symlink cycle or excessive depth')
            link = os.readlink(path)
            if link.startswith('/'):
                parts = []
            pending = link.split('/') + pending
        else:
            parts.append(part)
    path = root.joinpath(*parts)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('not a regular file')
    return path


def elf(data):
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('expected ELF32 little-endian version 1')
    header = struct.unpack_from('<HHIIIIIHHHHHH', data, 16)
    if header[0] not in (2, 3) or header[1] != 40 or header[2] != 1:
        raise ValueError('expected ARM executable or shared object')
    offset, size, count = header[4], header[8], header[9]
    if size != 32 or offset + size * count > len(data):
        raise ValueError('invalid program headers')
    segments = [struct.unpack_from('<IIIIIIII', data, offset + i * size) for i in range(count)]
    for seg in segments:
        if seg[1] + seg[4] > len(data):
            raise ValueError('truncated segment')
    interpreter = None
    dynamic = []
    def string_at(position, end):
        stop = data.find(b'\0', position, end)
        if stop < 0:
            raise ValueError('unterminated ELF string')
        return data[position:stop].decode('utf-8', errors='strict')
    for kind, start, _, _, length, *_ in segments:
        if kind == 3:
            interpreter = string_at(start, start + length)
            if not interpreter.startswith('/'):
                raise ValueError('interpreter must be absolute')
        if kind == 2:
            if length % 8:
                raise ValueError('invalid dynamic segment')
            terminated = False
            for pos in range(start, start + length, 8):
                tag, value = struct.unpack_from('<iI', data, pos)
                if tag == 0:
                    terminated = True
                    break
                dynamic.append((tag, value))
            if not terminated:
                raise ValueError('unterminated dynamic segment')
    tags = dict(dynamic)
    strings = []
    if any(tag in (1, 15, 29) for tag, _ in dynamic):
        if 5 not in tags or 10 not in tags:
            raise ValueError('missing dynamic string table')
        address, length = tags[5], tags[10]
        mapping = next((s for s in segments if s[0] == 1 and s[2] <= address
                        and address + length <= s[2] + s[4]), None)
        if mapping is None:
            raise ValueError('string table outside file-backed LOAD segment')
        start = mapping[1] + address - mapping[2]
        for tag, value in dynamic:
            if tag in (1, 15, 29):
                if value >= length:
                    raise ValueError('string offset outside table')
                strings.append((tag, string_at(start + value, start + length)))
    return {'interpreter': interpreter, 'needed': [s for t, s in strings if t == 1],
            'search_paths': [s for t, s in strings if t in (15, 29)], 'flags': header[6]}


# Contract of the offline prototype at bec7fd5 / 6522092 / fd76434, not a new init.
BOOT_ELFS = ('/sbin/init', '/bin/sh', '/bin/busybox', '/opt/koreader/luajit')
BOOT_SCRIPTS = ('/etc/init.d/rcS', '/usr/bin/pmkb-check-offline', '/usr/bin/pmkb-check-onboard',
                '/usr/bin/pmkb-reader', '/bin/kobo_config.sh')
BOOT_ACTIONS = ('::sysinit:/etc/init.d/rcS', '::once:/usr/bin/pmkb-reader',
                '::shutdown:/bin/umount -a -r')
# Non-script, non-ELF files whose presence/non-emptiness is still required.
BOOT_DATA_FILES = ('/opt/koreader/reader.lua', '/opt/koreader/defaults.custom.lua')


def bootstrap(root):
    """Check on-disk launch prerequisites, never execute init or scripts."""
    if os.name != 'posix':
        raise ValueError('bootstrap permissions require a POSIX extracted rootfs')
    records, errors = [], []
    for guest in (*BOOT_ELFS, *BOOT_SCRIPTS, '/etc/inittab', *BOOT_DATA_FILES):
        try:
            path = target(root, guest)
            mode = stat.S_IMODE(path.stat().st_mode)
            data = path.read_bytes()
            records.append({'path': guest, 'resolved_path': '/' + path.relative_to(root).as_posix(),
                            'mode': format(mode, '04o'), 'sha256': hashlib.sha256(data).hexdigest()})
            if not data:
                raise ValueError('empty bootstrap file')
            if guest in (*BOOT_ELFS, *BOOT_SCRIPTS) and not mode & 0o111:
                raise ValueError('bootstrap executable has no execute bit')
            if guest in BOOT_ELFS:
                elf(data)
            if guest in BOOT_SCRIPTS:
                if data.split(b'\n', 1)[0] != b'#!/bin/sh' or b'\r\n' in data:
                    raise ValueError('expected LF shell script with #!/bin/sh')
            if guest == '/etc/inittab':
                if b'\r' in data:
                    raise ValueError('inittab must use LF line endings')
                actions = [line.strip() for line in data.decode('utf-8').splitlines()
                           if line.strip() and not line.lstrip().startswith('#')]
                if sorted(actions) != sorted(BOOT_ACTIONS):
                    raise ValueError('inittab differs from the offline sysinit/once/shutdown contract')
        except (OSError, ValueError) as exc:
            errors.append(f'{guest}: {exc}')
    return records, errors


ORIGIN_TOKEN = re.compile(r'\$(?:ORIGIN|\{ORIGIN\})')
UNSUPPORTED_TOKEN = re.compile(r'\$(?:LIB|\{LIB\}|PLATFORM|\{PLATFORM\})')


def resolve_rpath(guest, search_paths):
    """Expand ``$ORIGIN``/``${ORIGIN}`` (the directory containing this ELF,
    within the guest rootfs) in RPATH/RUNPATH entries. Any other dynamic
    string token, or an entry that is still not rootfs-absolute after
    expansion, is rejected rather than guessed at."""
    origin = guest.rsplit('/', 1)[0] or '/'
    resolved = []
    for entry in search_paths:
        for part in entry.split(':'):
            if not part:
                continue
            if UNSUPPORTED_TOKEN.search(part):
                raise ValueError(f'unsupported dynamic string token in RPATH/RUNPATH: {part}')
            part = ORIGIN_TOKEN.sub(origin, part)
            if '$' in part or not part.startswith('/'):
                raise ValueError(f'unsupported or unresolved RPATH/RUNPATH entry: {part}')
            resolved.append(part.rstrip('/') or '/')
    return resolved


def storage(root):
    """Inspect the underlying rootfs mount directory, never mount or repair P3."""
    result = {'directories': [], 'onboard_empty': None, 'mount_verified': False}
    for guest in ('/mnt', '/mnt/onboard'):
        # Reject links at each level before descending, including guest-absolute
        # links. A mount target must not redirect to another rootfs location.
        path = root / guest.lstrip('/')
        try:
            info = path.lstat()
            mode = info.st_mode
            if not stat.S_ISDIR(mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('expected a real directory, not a file or symlink')
            result['directories'].append({'path': guest, 'mode': format(stat.S_IMODE(mode), '04o')})
        except (OSError, ValueError) as exc:
            return result, [f'{guest}: {exc}']
    try:
        # Record only presence, never names or contents of user books.
        result['onboard_empty'] = next((root / 'mnt/onboard').iterdir(), None) is None
    except OSError as exc:
        return result, [f'/mnt/onboard: {exc}']
    return result, []


def audit(root, check_bootstrap=False, check_storage=False):
    raw = str(root)
    if raw.startswith(('/dev', '/proc', '/sys', '\\\\.\\')):
        raise ValueError('local extracted rootfs required')
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or str(root).startswith(('/dev', '/proc', '/sys')):
        raise ValueError('local extracted rootfs directory required')
    records, errors = [], []
    # os.walk does not follow directory links. File links resolve within guest /.
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda exc: errors.append(f'rootfs traversal: {exc}')):
        dirs.sort()
        for name in sorted(files):
            guest = '/' + (Path(directory) / name).relative_to(root).as_posix()
            try:
                path = target(root, guest)
                with path.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF':
                        continue
                    stream.seek(0)
                    data = stream.read()
                info = elf(data)
                record = {'path': guest, 'sha256': hashlib.sha256(data).hexdigest(), **info}
                records.append(record)
                # RPATH/RUNPATH apply only to this ELF's own dependency lookups,
                # searched before the default library directories.
                rpath_dirs = resolve_rpath(guest, info['search_paths']) if info['search_paths'] else []
                for dep in ([info['interpreter']] if info['interpreter'] else []) + info['needed']:
                    candidates = [dep] if dep.startswith('/') else [base + '/' + dep for base in
                                  (*rpath_dirs, '/opt/koreader/libs', '/lib', '/usr/lib')]
                    if '/' in dep and not dep.startswith('/'):
                        raise ValueError('relative dependency path unsupported')
                    found = False
                    for candidate in candidates:
                        try:
                            dependency = target(root, candidate)
                            elf(dependency.read_bytes())
                            found = True
                            break
                        except FileNotFoundError:
                            continue
                        except (OSError, ValueError):
                            break
                    if not found:
                        errors.append(f'{guest}: missing or invalid ARM dependency {dep}')
            except (OSError, ValueError) as exc:
                errors.append(f'{guest}: {exc}')
    if not records:
        errors.append('no ARM ELF runtime found')
    boot_files = []
    if check_bootstrap:
        boot_files, boot_errors = bootstrap(root)
        errors.extend(boot_errors)
    storage_report = None
    if check_storage:
        storage_report, storage_errors = storage(root)
        errors.extend(storage_errors)
    return {'storage_checked': check_storage, 'storage': storage_report,
            'bootstrap_checked': check_bootstrap, 'bootstrap_files': boot_files,
            'tool': 'audit-arm-runtime', 'status': 'failed' if errors else 'ok',
            'physical_restore_eligible': False, 'hardware_qualified': False,
            'elf_files': records, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rootfs', help='local extracted directory; never a device or mounted card')
    parser.add_argument('--check-bootstrap', action='store_true',
                        help='also check the offline prototype launch files and POSIX execute bits')
    parser.add_argument('--check-storage', action='store_true',
                        help='also check the local /mnt/onboard directory required by the prototype')
    args = parser.parse_args()
    try:
        report = audit(args.rootfs, check_bootstrap=args.check_bootstrap,
                       check_storage=args.check_storage)
    except (OSError, ValueError) as exc:
        report = {'status': 'failed', 'errors': [str(exc)], 'physical_restore_eligible': False}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
