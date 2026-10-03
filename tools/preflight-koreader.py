#!/usr/bin/env python3
"""Aggregate offline KOReader checks; never authorize restoration or hardware boot."""
import argparse
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def peer(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


arm = peer('audit-arm-runtime')
rebuild = peer('rebuild-rootfs')
HARDWARE = ('framebuffer', 'touch', 'frontlight', 'p3_mount', 'usb_calibre', 'hardware_boot')
CONTENT = ('runtime_and_dynamic_dependencies', 'bootstrap_and_execute_bits', 'onboard_structure',
           'koreader_presence', 'nickel_signatures')


def item(status, reason, **evidence):
    return {'status': status, 'reason': reason, **evidence}


def nickel(root):
    """Reuse the builder's read-only scanner if installed alongside this tool."""
    if not Path(__file__).with_name('build-koreader-rootfs.py').is_file():
        return item('UNQUALIFIED', 'Builder Nickel scanner not present in this checkout; no duplicate scanner')
    builder = peer('build-koreader-rootfs')
    manifest, sources = {}, {}
    builder._copy_tree(root, None, manifest, sources, write=False)
    hits = builder._scan_for_nickel(manifest, sources)
    return item('FAIL' if hits else 'PASS',
                'Existing builder signature scan; hits require review, absence is not exhaustive proof',
                findings=hits)


def preflight(source):
    checks = {}
    report = {'tool': 'preflight-koreader', 'schema_version': 1, 'checks': checks,
              'hardware': {key: item('UNQUALIFIED', 'Requires actual Aura HD qualification') for key in HARDWARE},
              'complete': False, 'hardware_qualified': False, 'physical_restore_eligible': False,
              'device_write_attempted': False}
    try:
        raw = str(source)
        # Reuse the existing physical/UNC rejection before accessing the input.
        if rebuild.looks_like_device(raw):
            raise ValueError('Only local files or extracted directories are accepted')
        root = Path(source).resolve(strict=True)
        if root == Path(root.anchor) or any(parent == Path('/proc') or parent == Path('/sys')
                                            for parent in (root, *root.parents)):
            raise ValueError('Special filesystem/root input forbidden')
        mode = root.stat().st_mode
        if stat.S_ISDIR(mode):
            report['input_kind'] = 'extracted_directory'
            runtime = arm.audit(root)
            checks['filesystem'] = item('PASS', 'Local extracted directory; image integrity not established')
            checks['image_integrity'] = item('UNQUALIFIED', 'No filesystem image supplied', applicable=False)
            checks[CONTENT[0]] = item('FAIL' if runtime['errors'] else 'PASS',
                                      'Existing ARM ELF/dependency audit', evidence=runtime)
            if os.name == 'posix':
                files, errors = arm.bootstrap(root)
                checks[CONTENT[1]] = item('FAIL' if errors else 'PASS', 'Existing offline bootstrap contract',
                                          files=files, errors=errors)
                reader_errors = [error for error in errors if error.startswith('/opt/koreader/')]
                checks['koreader_presence'] = item('FAIL' if reader_errors else 'PASS',
                                                    'LuaJIT and nonempty reader.lua checked by bootstrap', errors=reader_errors)
            else:
                checks[CONTENT[1]] = item('UNQUALIFIED', 'POSIX extraction needed for execute permissions')
                checks['koreader_presence'] = item('UNQUALIFIED', 'Bootstrap permission audit unavailable')
            storage, errors = arm.storage(root)
            checks[CONTENT[2]] = item('FAIL' if errors else 'PASS', 'Existing mountpoint structure audit',
                                      evidence=storage, errors=errors)
            try:
                checks['nickel_signatures'] = nickel(root)
            except (OSError, ValueError, RuntimeError, AttributeError, ImportError) as exc:
                checks['nickel_signatures'] = item('UNQUALIFIED', f'Signature sources unavailable: {exc}')
        elif stat.S_ISREG(mode):
            report['input_kind'] = 'filesystem_image'
            for name in CONTENT:
                checks[name] = item('UNQUALIFIED', 'Image content not extracted; supply a local extracted tree separately')
            if not all(shutil.which(tool) for tool in ('dumpe2fs', 'e2fsck')):
                checks['filesystem'] = item('UNQUALIFIED', 'dumpe2fs and e2fsck required for image integrity')
            else:
                try:
                    before = rebuild.sha256_file(root)
                    params = rebuild.read_ext_parameters(root)
                    fsck = subprocess.run(['e2fsck', '-f', '-n', str(root)], text=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    after = rebuild.sha256_file(root)
                    checks['filesystem'] = item('PASS' if fsck.returncode == 0 and before == after else 'FAIL',
                        'Read-only ext filesystem integrity; no P1 geometry or kernel compatibility qualification',
                        parameters=params, sha256=before, unchanged=before == after,
                        e2fsck_exit=fsck.returncode, diagnostic=fsck.stdout)
                except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                    checks['filesystem'] = item('FAIL', f'Filesystem image audit failed: {exc}')
        else:
            raise ValueError('Input must be a regular local file or extracted directory')
    except (OSError, ValueError) as exc:
        checks['input'] = item('FAIL', str(exc))
    applicable = [check['status'] for check in checks.values() if check.get('applicable', True)]
    failed = 'FAIL' in applicable
    complete = 'UNQUALIFIED' not in applicable
    report['status'] = 'FAIL' if failed else ('PASS' if complete else 'UNQUALIFIED')
    report['offline_checks_satisfied'] = False if failed else (True if complete else None)
    report['offline_coverage_complete'] = complete
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Local extracted rootfs directory or standalone ext image; no devices')
    args = parser.parse_args()
    report = preflight(args.source)
    print(json.dumps(report, indent=2, sort_keys=True))
    return {'PASS': 0, 'FAIL': 1, 'UNQUALIFIED': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
