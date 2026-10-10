#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Hierarchical output hashes of a build stage: units -> segments -> stage (docs/BUILD_CACHE.md).

A stage's outputs (run-relative path -> SHA-256) are grouped into UNITS (one map, region, room, head preview
or catalogue file) and units into SEGMENTS (a town, a block of 100 open-world regions, the rooms, the character
heads). Each unit's hash covers its files, each segment's hash its unit hashes, and the stage hash its segment
hashes (a Merkle tree). Two runs compare by the stage hash in one step; only on a mismatch do they drill down to
the segments and units that differ. Diagnostics (logs, timing reports: build_cache.diagnostic) are left out.

The grouping is a pure function of the path, so the same outputs always give the same tree.
"""
import hashlib
import re
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:  # run as a script; never ahead of src/ when imported
    sys.path.append(str(Path(__file__).resolve().parent))

SCHEMA = 'AmiWind unit tree 1'
# Folders whose next path part is the unit (a map, a room, a head preview), wherever they sit in the path.
UNIT_FOLDERS = ('area-work', 'maps', 'character', 'progs')
NUMBERED = re.compile(r'^([a-z_]+?)(\d+)$')


def bucket(unit):
    """The segment part of a unit name: its letters, plus the hundreds of a numbered name (vf0123 -> vf01,
    bm007 -> bm0, sn029 -> sn0, h106 -> h1); other names share the bucket 'other'."""
    found = NUMBERED.match(unit)
    if not found:
        return 'other'
    letters, digits = found.groups()
    return letters + (digits[:-2] or '0')


def place(path):
    """(segment, unit) of one run-relative output path."""
    parts = path.split('/')
    for index, part in enumerate(parts[:-1]):
        if part in UNIT_FOLDERS:
            unit = parts[index + 1].split('.')[0]
            return '/'.join(parts[:index + 1]) + ':' + bucket(unit), unit
    if len(parts) >= 3:          # STAGE_ROOT/UNIT/... (world-terrain/vf0123/scene.bsp, balmora-work/bm007/...)
        return parts[0] + ':' + bucket(parts[1]), parts[1]
    if len(parts) == 2:          # STAGE_ROOT/file: one unit per file in the root's own segment
        return parts[0], parts[1]
    return '.', parts[0]


def _digest(rows):
    return hashlib.sha256(''.join(f'{a} {b}\n' for a, b in sorted(rows)).encode('utf-8')).hexdigest()


def tree(files):
    """The unit tree of {run-relative path: SHA-256} (diagnostics left out):
    {'schema', 'stage_hash', 'segments': {segment: {'hash', 'units': {unit: hash}}}}."""
    from build_cache import diagnostic
    grouped = {}
    for path, sha in files.items():
        if diagnostic(path):
            continue
        segment, unit = place(path)
        grouped.setdefault(segment, {}).setdefault(unit, []).append((path, sha))
    segments = {}
    for segment, units in grouped.items():
        hashes = {unit: _digest(rows) for unit, rows in units.items()}
        segments[segment] = {'hash': _digest(hashes.items()), 'units': hashes}
    return {'schema': SCHEMA, 'stage_hash': _digest((s, v['hash']) for s, v in segments.items()), 'segments': segments}


def of_manifest(manifest):
    """The unit tree of a stage output manifest: its files, and its links as 'link:TARGET'."""
    files = {path: row['sha256'] for path, row in (manifest.get('files') or {}).items()}
    files.update({path: 'link:' + str(target) for path, target in (manifest.get('links') or {}).items()})
    return tree(files)


def differences(new, old):
    """[(segment, unit or None, change)] between two trees: [] when the stage hashes match (one comparison);
    otherwise every changed, added or removed segment, and inside a changed segment every such unit."""
    if new['stage_hash'] == old['stage_hash']:
        return []
    found = []
    for segment in sorted(set(new['segments']) | set(old['segments'])):
        a, b = new['segments'].get(segment), old['segments'].get(segment)
        if a is None or b is None:
            found.append((segment, None, 'added' if b is None else 'removed'))
        elif a['hash'] != b['hash']:
            for unit in sorted(set(a['units']) | set(b['units'])):
                x, y = a['units'].get(unit), b['units'].get(unit)
                if x != y:
                    found.append((segment, unit, 'added' if y is None else 'removed' if x is None else 'changed'))
    return found


def describe(found, limit=5):
    """A short text of differences(): 'segment/unit changed, ...'."""
    text = ', '.join(f"{segment}{'/' + unit if unit else ''} {change}" for segment, unit, change in found[:limit])
    return text + (f' and {len(found) - limit} more' if len(found) > limit else '')
