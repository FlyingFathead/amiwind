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
import collections
import hashlib
import math
from pathlib import Path

RUN_FORMAT = 'aw-cell-run-1'
CELL_UNITS = 8192            # Morrowind world units per exterior cell
# A frame's centre is in Morrowind units, but its low corner, chunk grid and local points are in Quake units, 4 per Morrowind
# unit (tools/chim/areas.py: the ground box is centre + 4 * bounds). A frame of 24 x 24 chunks of 256 is 3 x 3 cells.
FRAME_LOCAL_SCALE = 4
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
    return (int(math.floor((cx + FRAME_LOCAL_SCALE * local_x) / CELL_UNITS)), int(math.floor((cy + FRAME_LOCAL_SCALE * local_y) / CELL_UNITS)))


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


def _declared_ownership(base,receipt):
    """Read declared town cores, never infer logical ownership from render copies.

    Original source receipts/catalogues are optional for historical builds. When
    a receipt declares owned_cells it must agree with the frame transform/grid.
    """
    frames={tuple(f['cell']):f for f in _frames(receipt)}
    declared={};counts={};notes=[];seen_cells=set();reference_union={}
    for area in receipt.get('areas',[]):
        if not isinstance(area,str) or '/' in area or '\\' in area or area in ('.','..'):
            raise ValueError('Invalid CHIM source area')
        folder=Path(base)/'work'/area
        source=_read(folder/'source-receipt.json')
        geometry=(source or {}).get('geometry',{})
        bounds=geometry.get('owned_cells')
        if bounds is None:continue
        if (not isinstance(bounds,list) or len(bounds)!=2 or
                any(not isinstance(p,list) or len(p)!=2 or any(type(v) is not int for v in p) for p in bounds)):
            raise ValueError('Malformed declared original-cell core')
        low,high=bounds
        if any(a>=b for a,b in zip(low,high)) or (high[0]-low[0])*(high[1]-low[1])>4096:
            raise ValueError('Invalid declared original-cell core extent')
        anchor=tuple(geometry.get('source_cell',()))
        if anchor not in frames:raise ValueError('Declared core has no matching CHIM frame')
        fr=frames[anchor];centre=geometry.get('centre');local=geometry.get('bounds');scale=geometry.get('scale')
        if centre!=fr['centre'] or scale!=1/FRAME_LOCAL_SCALE or not local or len(local)!=2:
            raise ValueError('Declared core frame transform differs')
        expected=[[centre[i]+local[j][i]/scale for i in range(2)] for j in range(2)]
        original=[[v*CELL_UNITS for v in p] for p in bounds]
        if expected!=original:raise ValueError('Declared core bounds are not original-cell aligned')
        grid=[[fr['centre'][i]+FRAME_LOCAL_SCALE*fr['low'][i] for i in range(2)],
              [fr['centre'][i]+FRAME_LOCAL_SCALE*(fr['low'][i]+fr[n]*fr['grain']) for i,n in enumerate(('nx','ny'))]]
        if any(grid[0][i]>original[0][i] or grid[1][i]<original[1][i] for i in range(2)):
            raise ValueError('CHIM terrain grid does not cover the declared core')
        core={(x,y) for x in range(low[0],high[0]) for y in range(low[1],high[1])}
        if core&seen_cells:raise ValueError('Duplicate logical original-cell owner')
        seen_cells|=core;declared[anchor]=core
        note={'area':area,'frame':frame_path(anchor),'owned_cells':bounds,'cells':len(core),
              'basis':'declared original-cell core; apron/render dependency copies do not own cells'}
        catalogue=_read(folder/'source-catalogue.json')
        if catalogue is not None:
            refs={(r.get('master','Morrowind.esm'),r['number']):r for r in catalogue['references']}
            if len(refs)!=len(catalogue['references']):raise ValueError('Duplicate original reference identity')
            ownership=catalogue.get('ownership') or {};seen=set();totals=collections.Counter()
            deferred={(r.get('master','Morrowind.esm'),r['number']):r for r in catalogue.get('deferred',[])}
            if len(deferred)!=len(catalogue.get('deferred',[])) or not set(deferred)<=set(refs):
                raise ValueError('Duplicate or unknown deferred original reference')
            local_counts={}
            for role in ('owned_references','dependency_references'):
                if role not in ownership:raise ValueError('Original reference ownership missing')
                for item in ownership[role]:
                    ident=(item['master'],item['reference']);cell=tuple(item['physical_cell'])
                    if ident in seen or ident not in refs:raise ValueError('Duplicate or missing original reference owner')
                    if (cell in core)!=(role=='owned_references'):raise ValueError('Original reference core ownership differs')
                    seen.add(ident);t=refs[ident].get('type','UNKNOWN');totals[t]+=1
                    union=reference_union.setdefault(ident,{'cell':cell,'type':t,'owner':None,
                                                           'dependency_frames':set(),'deferred':False})
                    if (union['cell'],union['type'])!=(cell,t):
                        raise ValueError('Original reference identity has inconsistent origin/type')
                    if role=='owned_references':
                        if union['owner'] is not None and union['owner']!=anchor:
                            raise ValueError('Duplicate logical original reference owner')
                        union['owner']=anchor
                    else:union['dependency_frames'].add(frame_path(anchor))
                    union['deferred'] |= ident in deferred
                    c=local_counts.setdefault(cell,{'owned_by_type':{},'dependency_by_type':{}})
                    group=c['owned_by_type' if role=='owned_references' else 'dependency_by_type']
                    group[t]=group.get(t,0)+1
                    if 'deferred' in catalogue:
                        c.setdefault('deferred_by_type',{})
                        if ident in deferred:
                            d=c['deferred_by_type'];d[t]=d.get(t,0)+1
            if seen!=set(refs):raise ValueError('Original reference ownership is incomplete')
            for cell in core:
                local_counts.setdefault(cell,{'owned_by_type':{},'dependency_by_type':{}})
                if 'deferred' in catalogue:local_counts[cell].setdefault('deferred_by_type',{})
            for cell,c in local_counts.items():
                c['basis']='original source catalogue identities by physical origin; not rendered model counts'
                counts.setdefault(anchor,{})[cell]=c
            note['source_references_by_type']=dict(sorted(totals.items()))
            note['owned_references']=len(ownership['owned_references'])
            note['dependency_references']=len(ownership['dependency_references'])
            note['deferred_by_type']=dict(sorted(collections.Counter(r.get('type','UNKNOWN') for r in deferred.values()).items())) if 'deferred' in catalogue else None
        notes.append(note)
    # Repeated footprint dependencies belong to their one logical owner, not
    # to each frame that needs to render them. Keep copies as separate provenance.
    merged={};dependency_ids={}
    unknown_deferred={cell for per in counts.values() for cell,c in per.items() if 'deferred_by_type' not in c}
    for ident,item in reference_union.items():
        cell=item['cell'];t=item['type']
        c=merged.setdefault(cell,{'owned_by_type':{},'dependency_by_type':{},'unique_by_type':{},
                                  'deferred_by_type':{},'dependency_by_frame':{}})
        group=c['owned_by_type' if item['owner'] is not None else 'dependency_by_type']
        group[t]=group.get(t,0)+1;c['unique_by_type'][t]=c['unique_by_type'].get(t,0)+1
        if item['deferred']:c['deferred_by_type'][t]=c['deferred_by_type'].get(t,0)+1
        for frame in item['dependency_frames']:
            per=c['dependency_by_frame'].setdefault(frame,{'by_type':{}})
            per['by_type'][t]=per['by_type'].get(t,0)+1
            dependency_ids.setdefault((cell,frame),set()).add(ident)
    for (cell,frame),ids in dependency_ids.items():
        per=merged[cell]['dependency_by_frame'][frame]
        per['unique_reference_count']=len(ids)
        per['identity_union_sha256']=hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest()
    for anchor,per_cell in counts.items():
        for cell,old in per_cell.items():
            if cell in merged:
                current=dict(merged[cell]);current['basis']=old['basis']
                if cell in unknown_deferred:current.pop('deferred_by_type',None)
                per_cell[cell]=current
    return declared,counts,notes


def digest(name, base, label=None, commit=None, built_at=None):
    """The per-cell digest of one run, or raises ValueError when it has no receipt."""
    rep = {k: _read(report_path(base, k)) for k in REPORTS}
    receipt = rep['receipt']
    if not receipt:
        raise ValueError('%s: no CHIM receipt at %s' % (name, report_path(base, 'receipt')))
    frames = _frames(receipt)
    stats = rep['stats']
    cells, anchors = {}, set()
    declared,source_counts,ownership_notes=_declared_ownership(base,receipt)
    converted=set()
    for fr in frames:
        anchors.add(tuple(fr['cell']))
        got = _chunk_cells(fr, stats['chunks']['per_chunk']) if stats else {}
        if not got:
            got = {c: {'chunks': None, 'owned': None, 'terrain_faces': None, 'placed_faces': None, 'bytes': None}
                   for c in _footprint(fr)}
        anchor=tuple(fr['cell'])
        if anchor in declared:
            converted.update(declared[anchor])
        else:
            converted.update(c for c,e in got.items() if ((e['owned'] or 0)>0 if stats else c==anchor))
        for c, e in got.items():
            if c in source_counts.get(anchor,{}):e['source_references']=source_counts[anchor][c]
            cur = cells.get(c)
            if cur is None:
                cells[c] = dict(e)
                continue
            for k, v in e.items():
                if k=='source_references':
                    # Explicit source ownership is unique; never add dicts/render copies.
                    if k in cur and cur[k]!=v:raise ValueError('Conflicting original source reference counts')
                    cur[k]=v;continue
                if v is not None:
                    cur[k] = (cur[k] or 0) + v
    # Declared complete cores include empty cells; apron placements are dependencies.
    if not converted<=set(cells):raise ValueError('Declared core lacks measured terrain cell coverage')
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
        'audits': audits, 'run_stats': run_stats, 'frame_ownership': ownership_notes,
        'lava': receipt.get('lava'),        # docs/LAVA.md: {mode, pools, cells: {cell: pools}}; None before the lava record
        'reports': sorted(k for k, v in rep.items() if v is not None),
    }
