#!/usr/bin/env python3
"""Read-only ELF dependency inventory for an extracted local PMKB rootfs."""
import argparse
import hashlib
import json
import os
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


def audit(root):
    raw = str(root)
    if raw.startswith(('/dev', '/proc', '/sys', '\\\\.\\')):
        raise ValueError('local extracted rootfs required')
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or str(root).startswith(('/dev', '/proc', '/sys')):
        raise ValueError('local extracted rootfs directory required')
    records, errors = [], []
    # os.walk does not follow directory links. File links resolve within guest /.
    for directory, dirs, files in os.walk(root, followlinks=False):
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
                if info['search_paths']:
                    errors.append(f'{guest}: RPATH/RUNPATH requires a separate loader audit')
                for dep in ([info['interpreter']] if info['interpreter'] else []) + info['needed']:
                    candidates = [dep] if dep.startswith('/') else [base + '/' + dep for base in
                                  ('/opt/koreader/libs', '/lib', '/usr/lib')]
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
    return {'tool': 'audit-arm-runtime', 'status': 'failed' if errors else 'ok',
            'physical_restore_eligible': False, 'hardware_qualified': False,
            'elf_files': records, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rootfs', help='local extracted directory; never a device or mounted card')
    args = parser.parse_args()
    try:
        report = audit(args.rootfs)
    except (OSError, ValueError) as exc:
        report = {'status': 'failed', 'errors': [str(exc)], 'physical_restore_eligible': False}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
