# SPDX-License-Identifier: GPL-3.0-only
"""Explicit ocean admission and routing through existing CHIM terrain and AmiQuake hulls.

No OCEN renderer: CHK1/TERR terrain uses the normal world graft. Original leveled
creature references stay deferred. LAND or any other live reference is refused.
"""
import hashlib
import math
import struct
from pathlib import Path

from mwad.audit import cell_data
from mwad.esm import subrecords, string, is_deleted
from mwad.paths import child_ci

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
OBJECT_TYPES = set('STAT DOOR MISC WEAP CONT CREA LIGH NPC_ ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK ALCH LEVI LEVC'.split())


def admit_cell(data_files, cell):
    """Read/hash original masters; reject non-ocean/unsupported content, retain LEVC identity.

    This is a bounded-memory read, not a terrain or asset conversion. A master is
    identified on every call, so a changed expansion cannot reuse a zero-ref result.
    """
    if len(cell) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in cell):
        raise ValueError('Ocean cell needs two integer original coordinates')
    cell = tuple(cell)
    if any(abs(v) > 100 for v in cell):
        raise ValueError('Ocean cell is outside the supported original-world range')
    definitions, refs, masters, land = {}, [], [], []
    for name in MASTERS:
        try:
            path = child_ci(Path(data_files), name)
        except (FileNotFoundError, ValueError):
            if name == MASTERS[0]:
                raise
            continue
        if not path.is_file():
            if name == MASTERS[0]:
                raise ValueError('Ocean admission needs Morrowind.esm')
            continue
        sha = hashlib.sha256()
        with path.open('rb') as stream:
            while True:
                header = stream.read(16)
                if not header:
                    break
                if len(header) != 16:
                    raise ValueError('Truncated original record header')
                raw_tag, size, _, flags = struct.unpack('<4sIII', header)
                payload = stream.read(size)
                if len(payload) != size:
                    raise ValueError('Truncated original record')
                sha.update(header)
                sha.update(payload)
                tag = raw_tag.decode('ascii')
                if tag not in OBJECT_TYPES and tag not in ('CELL', 'LAND'):
                    continue
                subs = list(subrecords(payload))
                if tag in OBJECT_TYPES:
                    fields = dict(subs)
                    ident = string(fields.get('NAME', b''), 'object NAME').casefold()
                    if ident:
                        if is_deleted(flags, subs):
                            definitions.pop(ident, None)
                        else:
                            definitions[ident] = tag
                elif tag == 'LAND':
                    if is_deleted(flags, subs):
                        continue
                    xy = dict(subs).get('INTV', b'')
                    if len(xy) == 8 and struct.unpack('<ii', xy) == cell:
                        land.append(name)
                elif not is_deleted(flags, subs, header_only=True):
                    parsed = cell_data(subs)
                    if parsed['flags'] & 1 or (parsed['x'], parsed['y']) != cell:
                        continue
                    for ref in parsed['refs']:
                        if ref.get('deleted'):
                            continue
                        pos = ref.get('position')
                        if pos is None or len(pos) != 3 or not all(math.isfinite(v) for v in pos):
                            raise ValueError('Ocean reference lacks a finite source position')
                        refs.append(dict(ref, master=name, source_cell=list(cell)))
        masters.append({'name': name, 'sha256': sha.hexdigest(), 'bytes': path.stat().st_size})
    if land:
        raise ValueError('Ocean cell %s has LAND in %s' % (cell, ', '.join(land)))
    for ref in refs:
        kind = definitions.get(ref.get('id', '').casefold(), 'unknown')
        if kind != 'LEVC':
            raise ValueError('Ocean cell %s has unsupported %s reference %s; convert/account for it first'
                             % (cell, kind, ref['number']))
        ref.update(type=kind, status='deferred', reason='Original leveled creature spawning is not implemented')
    # Duplicate source identities are unsafe to flatten without a full content-loader override resolution.
    keys = [(r['master'], r['number']) for r in refs]
    if len(keys) != len(set(keys)) or any(r['number'] >> 24 for r in refs):
        raise ValueError('Ocean references need content-loader override resolution')
    return {'format': 'aw-chim-ocean-runtime-source-1', 'cell': list(cell), 'masters': masters,
            'references': refs, 'records': {'placed': len(refs), 'converted': 0, 'deferred': len(refs),
                                          'failed': 0, 'skipped': 0},
            'by_type': {'LEVC': len(refs)} if refs else {}, 'lighting': 'not_measured',
            'native_verified': False, 'packaged': False}


def append_routing_rows(entries, cells, data_files):
    """Append stable sequential AWR2 rows for explicit ocean cells lacking a legacy core.

    Existing vf names and rows stay unchanged; new rows are metadata only. They use
    normal frame maps generated from game data, not fabricated legacy BSP payloads.
    """
    entries = list(entries)
    cells = sorted(set(map(tuple, cells)))
    if not cells:
        return entries, []
    if any(e['name'] != 'vf%04d' % i for i, e in enumerate(entries)):
        raise ValueError('Ocean rows require a complete sequential world directory')
    if len(entries) + len(cells) > 8192:
        raise ValueError('Ocean rows exceed the existing AWR2 runtime directory limit')
    added = []
    for x, y in cells:
        source = admit_cell(data_files, (x, y))
        origin = [x * 2048 + 1024, y * 2048 + 1024, 0.0]
        world_box = (x * 2048, y * 2048, (x+1) * 2048, (y+1) * 2048)
        for entry in entries:
            lo, hi = entry['core']; ox, oy = entry['origin'][:2]
            if (lo[0]+ox < world_box[2] and world_box[0] < hi[0]+ox
                    and lo[1]+oy < world_box[3] and world_box[1] < hi[1]+oy):
                raise ValueError('Ocean cell %d,%d already has a core owner %s' % (x, y, entry['name']))
        row = {'name': 'vf%04d' % (len(entries)+len(added)), 'cell': [x, y], 'origin': origin,
               'core': [[-1024, -1024], [1024, 1024]],
               'coverage': [[-1920, -1920], [1920, 1920]], 'divisions': 1,
               'converted': None, 'chim_region': True, 'ocean_runtime': source}
        added.append(row)
    return entries + added, added
