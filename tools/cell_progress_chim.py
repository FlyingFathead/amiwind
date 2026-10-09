# SPDX-License-Identifier: GPL-3.0-only
"""Read a CHIM world build's reports into a per-cell digest for the CHIM Progress Tracker.

A run is the folder `chim_build --validate --stats` wrote (chim-receipt.json, chim-validate.json, chim-stairs.json,
chim-heap.json, chim-zone-walk.json, chim-stats.json), or a set of loose files named PREFIX-receipt.json,
PREFIX-validate.json and so on. Every report is optional: a missing one means that audit is "not measured".

The digest (format aw-cell-run-1) says, per exterior cell the world holds placements in, what the build put there
and what each audit found. It holds no game data beyond cell numbers and counts. tools/cell_progress.py keeps one
digest per run, so later ingests need no access to the build folders.
"""
import json
import math
from pathlib import Path

RUN_FORMAT = 'aw-cell-run-1'
CELL_UNITS = 8192            # Morrowind world units per exterior cell (CHIM frames use the same units)
REPORTS = {'receipt': 'receipt', 'validate': 'validate', 'stairs': 'stairs', 'heap': 'heap', 'zone': 'zone-walk',
           'stats': 'stats'}


def _read(path):
    path = Path(path)
    return json.loads(path.read_bytes().decode('utf-8')) if path.is_file() else None


def report_path(base, kind):
    """Path of one report in a run folder (chim-X.json) or beside a prefix (PREFIX-X.json)."""
    base = Path(base)
    stem = REPORTS[kind]
    return base / ('chim-%s.json' % stem) if base.is_dir() else Path(str(base) + '-%s.json' % stem)


def frame_path(cell):
    return 'frames/x%+03d/y%+03d/frame.ccf' % (cell[0], cell[1])


def cell_of(frame, local_x, local_y):
    """Exterior cell of a point given relative to a frame's centre."""
    cx, cy = frame['centre']
    return (int(math.floor((cx + local_x) / CELL_UNITS)), int(math.floor((cy + local_y) / CELL_UNITS)))


def key(cell):
    return '%d,%d' % (cell[0], cell[1])


def _frames(receipt):
    out = []
    for f in (receipt.get('frames') or ([{'frame': receipt['frame']}] if receipt.get('frame') else [])):
        fr = f.get('frame') if 'frame' in f else f
        if fr and fr.get('cell'):
            out.append(fr)
    return out


def _chunk_cells(frame, per_chunk):
    """{cell: {chunks, owned, terrain_faces, placed_faces}} from the stats' per-chunk rows of one frame."""
    out = {}
    path = frame_path(frame['cell'])
    grain, low = frame['grain'], frame['low']
    for ch in per_chunk:
        if ch.get('frame') != path:
            continue
        i, j = ch['cell']
        cell = cell_of(frame, low[0] + (i + .5) * grain, low[1] + (j + .5) * grain)
        e = out.setdefault(cell, {'chunks': 0, 'owned': 0, 'terrain_faces': 0, 'placed_faces': 0, 'bytes': 0})
        e['bytes'] += ch.get('bytes', 0)
        e['chunks'] += 1
        e['owned'] += ch.get('owned', 0)
        e['terrain_faces'] += ch.get('terrain_faces', 0)
        e['placed_faces'] += ch.get('placed_faces', 0)
    return out


def _footprint(frame):
    """Cells a frame's chunk grid touches (used when the run has no stats file)."""
    x0, y0 = frame['low']
    x1, y1 = x0 + frame['nx'] * frame['grain'] - 1, y0 + frame['ny'] * frame['grain'] - 1
    a, b = cell_of(frame, x0, y0), cell_of(frame, x1, y1)
    return [(x, y) for x in range(a[0], b[0] + 1) for y in range(a[1], b[1] + 1)]


def _status(ok):
    return 'passed' if ok else 'failed'


def digest(name, base, label=None, commit=None, built_at=None):
    """The per-cell digest of one run, or raises ValueError when it has no receipt."""
    rep = {k: _read(report_path(base, k)) for k in REPORTS}
    receipt = rep['receipt']
    if not receipt:
        raise ValueError('%s: no CHIM receipt at %s' % (name, report_path(base, 'receipt')))
    frames = _frames(receipt)
    stats = rep['stats']
    cells, anchors = {}, set()
    for fr in frames:
        anchors.add(tuple(fr['cell']))
        got = _chunk_cells(fr, stats['chunks']['per_chunk']) if stats else {}
        if not got:
            got = {c: {'chunks': None, 'owned': None, 'terrain_faces': None, 'placed_faces': None, 'bytes': None}
                   for c in _footprint(fr)}
        for c, e in got.items():
            cur = cells.get(c)
            if cur is None:
                cells[c] = dict(e)
                continue
            for k, v in e.items():
                if v is not None:
                    cur[k] = (cur[k] or 0) + v
    # A cell counts as converted when the frame owns placements in it (or, without stats, it is the frame's own cell).
    converted = {c for c, e in cells.items() if (e['owned'] or 0) > 0} if stats else {c for c in cells if c in anchors}
    audits = {}

    def put(mech, cell, status, detail):
        audits.setdefault(mech, {})[key(cell)] = {'status': status, 'detail': detail}

    by_path = {frame_path(f['cell']): f for f in frames}
    val = rep['validate']
    if val is not None:
        for c in converted:
            put('format_validation', c, _status(val.get('ok')), '%d validator failures' % val.get('failure_count', 0))
    st = rep['stairs']
    if st is not None:
        bad = {}
        for f in st.get('failures', []):
            fr = by_path.get(f.get('map'))
            pt = f.get('point')
            c = cell_of(fr, pt[0], pt[1]) if fr and pt else (sorted(anchors)[0] if anchors else None)
            if c is not None:
                bad[c] = bad.get(c, 0) + 1
        adv = len(st.get('advisory_failures', []))
        for c in converted:
            n = bad.get(c, 0)
            put('stair_walk', c, 'failed' if n else 'passed',
                '%d flights/steps the standing box cannot walk (%d advisory); %d tested in the run' % (n, adv, st.get('tested', 0)))
    heap, zone = rep['heap'], rep['zone']
    if heap is not None or zone is not None:
        ok = all(x is not False for x in ([heap.get('ok')] if heap else []) + ([zone.get('ok')] if zone else []))
        parts = []
        if heap:
            fr = heap.get('frames') or []
            parts.append('heap ring: %s, least headroom %s B' % (heap.get('status'),
                         min([f.get('headroom_bytes', 0) for f in fr] or [0])))
        if zone:
            w = zone.get('walks') or []
            parts.append('zone walk: %s, %d failed chunk loads' % (zone.get('status'), sum(x.get('zone_fail', 0) for x in w)))
        for c in converted:
            put('memory_fit', c, _status(ok), '; '.join(parts))
    models = receipt.get('models')
    # Figures that belong to the whole run (a frame's heap ring, the zone walk, the build); the tracker shows them on
    # every converted cell of the run, labelled as run-level.
    run_stats = {}
    if heap and (heap.get('frames') or []):
        run_stats['frame_heap_peak_bytes'] = max(f.get('peak_bytes', 0) for f in heap['frames'])
        run_stats['frame_heap_budget_bytes'] = max(f.get('budget_bytes', 0) for f in heap['frames'])
    if zone and (zone.get('walks') or []):
        run_stats['zone_locked_peak_bytes'] = max(w.get('locked_peak', 0) for w in zone['walks'])
        run_stats['zone_failed_chunk_loads'] = sum(w.get('zone_fail', 0) for w in zone['walks'])
    if stats:
        b = stats.get('build') or {}
        if b.get('cpu_seconds') is not None:
            run_stats['build_cpu_s'] = b['cpu_seconds']
        mem = stats.get('memory') or {}
        if mem.get('model_zone_peak_bytes') is not None:
            run_stats['model_zone_peak_bytes'] = mem['model_zone_peak_bytes']
        d = stats.get('disk') or {}
        if d.get('bytes') is not None:
            run_stats['world_bytes'] = d['bytes']
    return {
        'format': RUN_FORMAT, 'name': name, 'label': label or name, 'commit': commit,
        'chim_version': receipt.get('chim_version') or (stats or {}).get('chim_version'),
        'world_format': (stats or {}).get('world_format') or receipt.get('world_format'),
        'builder': receipt.get('builder'), 'areas': receipt.get('areas') or [], 'built_at': built_at,
        'frames': [{'cell': fr['cell'], 'path': frame_path(fr['cell'])} for fr in frames],
        'placements': receipt.get('placements'), 'models': models,
        'cells': {key(c): dict(cells[c], converted=(c in converted)) for c in sorted(cells)},
        'audits': audits, 'run_stats': run_stats,
        'reports': sorted(k for k, v in rep.items() if v is not None),
    }
