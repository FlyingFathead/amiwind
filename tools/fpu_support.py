#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional FPU support library from the user's own Amiga installation.

ENGINE-FPSP-MISSING-31: a real 68040 or 68060 traps on FPU instructions it
does not implement and on denormalized/unnormalized operands; a support
library (68040.library / 68060.library, normally loaded by SetPatch) handles
those traps. AmiWind never ships one. With --amiga-libs DIR the builder copies
the user's own copy into LIBS: on the boot disk, and the startup sequence runs
AmiWindFPU (engine/aga/boot/fpulib.asm), which opens the one that matches the
CPU and keeps it open. Without it the build continues; the boot check then
reports "none" as a warning. See docs/FPU_SUPPORT_LIBRARY.md.

Each library found is identified by the shared known-inputs check
(tools/known_inputs.py, config/known-inputs.json): size, SHA-256 and the
version from its resident (RomTag) structure give one verdict per file,
"known: <source> (tested)", "unknown build of <name> v<version> (not tested;
used)" or "invalid: ... (not used)", applied with --amiga-libs-policy.
"""
from datetime import datetime, timezone
import hashlib
import json
import shutil
from pathlib import Path

import known_inputs

SUPPORT_LIBRARIES = ('68040.library', '68060.library')
# MMULib's 68040/68060 libraries open mmu.library; copied when it sits beside them.
COMPANION_LIBRARIES = ('mmu.library',)
LOADER = 'AmiWindFPU'
HUNK_HEADER = b'\x00\x00\x03\xf3'
MAXIMUM_BYTES = 4 * 1024 * 1024
NONE_TEXT = 'no FPU support library'


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _child(directory, name):
    """Case-insensitive lookup of one entry, as on an Amiga filesystem."""
    if not directory.is_dir():
        return None
    matches = [p for p in directory.iterdir() if p.name.casefold() == name.casefold()]
    if len(matches) > 1:
        raise ValueError(f'Several files named {name} (case-insensitive) in {directory}')
    return matches[0] if matches else None


def find(directory):
    """Return {canonical name: path} for the support and companion libraries.

    Looks in DIR itself and in DIR/LIBS (any case), the layout of a Workbench
    partition or a copied LIBS: drawer. DIR itself wins when both have one.
    """
    directory = Path(directory).expanduser()
    if not directory.is_dir():
        raise ValueError(f'--amiga-libs is not a directory: {directory}')
    places = [directory]
    libs = _child(directory, 'libs')
    if libs is not None and libs.is_dir():
        places.append(libs)
    found = {}
    for name in SUPPORT_LIBRARIES + COMPANION_LIBRARIES:
        for place in places:
            path = _child(place, name)
            if path is not None and path.is_file():
                found[name] = path
                break
    if not any(name in found for name in SUPPORT_LIBRARIES):
        return {}
    return found


def inspect(directory, policy='warn', lock=None, table=None):
    """Verdicts of the libraries find() returns; applies the policy.

    Returns (records, warnings); raises ValueError when the policy stops the
    build. lock: the build's input lock (hashes from one place); without it the
    hash comes from the lock the build exported, or the file itself."""
    found = find(directory)
    if table is None:
        table = lock.table if lock is not None else known_inputs.load_table()
    if lock is not None:
        lock.prepare(list(found.values()), core=True)
    records = []
    for name, path in found.items():
        size = path.stat().st_size
        info = None
        if size > MAXIMUM_BYTES:
            info = {'valid': False, 'version': None, 'reason': f'larger than {MAXIMUM_BYTES} bytes'}
        elif path.read_bytes()[:4] != HUNK_HEADER:
            info = {'valid': False, 'version': None, 'reason': 'no hunk header'}
        digest = lock.sha256(path) if lock is not None else known_inputs.input_sha256(path)
        row = known_inputs.classify('amiga-library', name, path, digest, table, size=size, info=info)
        row['file_date_hint'] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
        if lock is not None:
            lock.note_verdict(path, row, table)
        records.append(row)
    return records, known_inputs.enforce(records, policy, 'Amiga libraries')


def record(path, name, verdict=None):
    """Receipt row of an installed file: name, size, SHA-256, version, verdict."""
    row = {'name': name, 'bytes': Path(path).stat().st_size, 'sha256': _digest(path)}
    if verdict is not None:
        row.update(version=verdict.get('version'), verdict=verdict['verdict'], label=verdict.get('label'),
                   message=verdict['message'], file_date_hint=verdict.get('file_date_hint'))
    return row


def stage(directory, boot, loader=None, loader_target=LOADER, policy='warn', lock=None):
    """Copy the user's libraries into BOOT/LIBS and AmiWindFPU into BOOT.

    Returns the receipt for build.json. directory=None means the option was not
    given. Invalid files are never copied (listed under 'rejected'); the loader
    is copied only when a support library was installed.
    """
    if directory is None:
        return {'status': 'not_requested', 'summary': NONE_TEXT, 'libraries': [], 'companions': []}
    found = find(directory)
    source = str(Path(directory).expanduser())
    if not found:
        return {'status': 'not_found', 'source_dir': source,
                'summary': NONE_TEXT, 'libraries': [], 'companions': []}
    verdicts, warnings = inspect(directory, policy, lock)
    usable = {row['name']: row for row in verdicts if row['verdict'] != 'invalid'}
    rejected = [{key: row.get(key) for key in ('name', 'version', 'bytes', 'sha256', 'verdict', 'message')}
                for row in verdicts if row['verdict'] == 'invalid']
    if not any(name in usable for name in SUPPORT_LIBRARIES):
        return {'status': 'not_found', 'source_dir': source, 'policy': policy,
                'summary': NONE_TEXT + ' (none usable)', 'libraries': [], 'companions': [],
                'rejected': rejected, 'warnings': warnings}
    if loader is None or not Path(loader).is_file():
        raise ValueError('FPU support loader AmiWindFPU is missing beside the engine; rebuild the engine')
    boot = Path(boot)
    target = boot / 'LIBS'
    target.mkdir(exist_ok=True)
    installed, companions = [], []
    for name, path in found.items():
        if name not in usable:
            continue
        shutil.copyfile(path, target / name)
        if _digest(target / name) != _digest(path):
            raise ValueError('FPU support library copy differs from its source: ' + name)
        row = record(target / name, name, usable[name])
        if usable[name]['sha256'] is not None and row['sha256'] != usable[name]['sha256']:
            raise ValueError('FPU support library changed while the build read it: ' + name)
        (installed if name in SUPPORT_LIBRARIES else companions).append(row)
    shutil.copyfile(loader, boot / loader_target)
    names = ', '.join(row['name'] for row in installed)
    return {'status': 'installed', 'source_dir': source, 'policy': policy,
            'summary': names, 'libraries': installed, 'companions': companions, 'rejected': rejected,
            'warnings': warnings, 'install_dir': 'LIBS',
            'loader': {'path': loader_target, 'sha256': _digest(boot / loader_target)}}


def load_receipt(path):
    """fpu-support.json of a staged image; an older stage without it had none."""
    path = Path(path)
    if not path.is_file():
        return {'status': 'not_requested', 'summary': NONE_TEXT, 'libraries': [], 'companions': []}
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt.get('status') not in ('not_requested', 'not_found', 'installed'):
        raise ValueError('Unknown FPU support receipt status in ' + str(path))
    return receipt


def startup_sequence(receipt, check='SYS:AmiWindCheck', loader='SYS:AmiWindFPU', rest=('Stack 300000', 'SYS:AmiWind')):
    """The boot disk's S:startup-sequence; AmiWindFPU runs only when installed."""
    lines = ['FailAt 10']
    if receipt.get('status') == 'installed':
        lines.append(loader)
    lines.append(check)
    lines.extend(rest)
    return '\n'.join(lines) + '\n'


def _row_text(row):
    version = (' v' + row['version']) if row.get('version') else ''
    verdict = (': ' + row['message']) if row.get('message') else ''
    return f"{row['name']}{version} ({row['bytes']:,} bytes) SHA-256 {row['sha256']}{verdict}"


def summary_lines(receipt):
    """Build report lines: name, version, size, SHA-256 and verdict of each library."""
    rejected = ['  not used: ' + _row_text(row) for row in (receipt or {}).get('rejected', [])]
    if not receipt or receipt.get('status') != 'installed':
        return ['FPU support library: none (' + NONE_TEXT + ')'] + rejected
    lines = []
    for row in receipt['libraries']:
        lines.append('FPU support library: ' + _row_text(row))
    for row in receipt.get('companions', []):
        lines.append('  also copied: ' + _row_text(row))
    return lines + rejected
