# SPDX-License-Identifier: GPL-3.0-only
"""CHIM regions: exterior cells on CHIM inside the legacy open world (builder option --chim-regions).

A selection of exterior cells (names such as "seabed" or "coast", a region name, or a cell file) becomes
CHIM frames that replace the legacy open-world maps of those cells. Each selected cell is its own frame,
the size of the cell, and its frame map takes the place of the cell's open-world map IN PLACE:
maps/vfNNNN.bsp of the cell becomes the CHIM frame map (the image step, chim.frame_map.build_region), so the
engine's open-world directory, its hand-over between maps, saves and every open-world tool keep the same map
names, and walking the island loads no more maps than before. A divided cell (2 x 2 or 4 x 4 legacy maps) is
one frame too: it takes the name of the cell's first map, whose directory row the world terrain stage widens to
the whole cell; the other maps' rows become its aliases (CHIM-REGION-DIVIDED-CELLS-36).
docs/chim/CHIM_REGIONS.md describes the route.

This module is the one writer of the ownership table (format aw-chim-ownership-1): which frame owns which
cell and why each selected cell was taken, dropped or refused. It reads no game data: the cell statuses
come from a CHIM progress tracker file (cell-progress.json, or docs/chim/cell-progress-reference.json),
the town boxes from the town configs.
"""
import csv
import hashlib
import io
import json
from pathlib import Path

FORMAT = 'aw-chim-ownership-1'
CELLS_FORMAT = 'aw-chim-cells-1'
# --chim-regions none: no CHIM region cells (tools/build.py; its default cell list is CHIM_CELLS_DEFAULT there)
NONE = 'none'
CELL_UNITS = 8192                 # Morrowind units per exterior cell
SCALE = 0.25                      # map units per Morrowind unit
CELL_MAP = int(CELL_UNITS * SCALE)   # 2048 map units per cell
HALF = CELL_MAP // 2
# Terrain-only ground past the owned cell: at least draw distance 540 + 32 (the stitcher's margin rule,
# town_config.handoff_core) and a whole number of 256-unit chunks with the cell (8 chunks) that the world's
# sector size 3 divides: 896 = 3.5 chunks a side -> 15 x 15 chunks, the legacy map's own coverage (+-1920).
TERRAIN_MARGIN = 896
LEAVE_MARGIN = 64                 # the engine leaves an open-world map 64 units past its core (aw_world.c)
HOLE_MAX = 8                      # an enclosed unselected pocket of up to this many cells is refused
# Cell kinds by tracker status (the tracker's ELIGIBLE set, tools/cell_progress.py). The open sea (no LAND)
# is taken only by an explicit cell selection: normal CHIM terrain references and appended routing rows.
# Named coast/region sets retain their existing footprint.
SEABED = ('empty_sea',)
LAND_DONE = ('complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'approved',
             'playtested', 'audits_passed')
OCEAN = ('ocean',)
NAMED = ('seabed', 'coast', 'sea-ring', 'coast2')
# The v0.0.36 coastline (project decision 2026-10-11: "the entire coastline, all 1's, all possible 2's ... as CHIM"):
# every cell of rings 1 and 2 from the sea; a cell that cannot go on CHIM is dropped with its reason, not refused.
COAST2_RINGS = (1, 2)
KIND_CODES = {'seabed': 's', 'land': 'l', 'ocean': 'o'}


def frame_id(cell):
    """The CHIM area id of a cell's frame (rcm7_p2 for cell -7,2): its folder in the CHIM world's work tree.
    The image installs its frame map under the name of the cell's open-world map (maps/vfNNNN.bsp)."""
    x, y = cell
    return 'rc%s%d_%s%d' % ('m' if x < 0 else 'p', abs(x), 'm' if y < 0 else 'p', abs(y))


def cell_key(cell):
    return '%d,%d' % tuple(cell)


def parse_cell(value):
    """(x, y) from "x,y", [x, y] or {"x": .., "y": ..} / {"cell": ..}."""
    if isinstance(value, dict):
        value = [value.get('x'), value.get('y')] if 'x' in value else value.get('cell')
    if isinstance(value, str):
        value = value.replace(';', ',').split(',')
    try:
        x, y = value
        fx, fy = float(x), float(y)
    except (TypeError, ValueError):
        raise ValueError('Not a cell: %r' % (value,))
    if fx != int(fx) or fy != int(fy):
        raise ValueError('Not a cell: %r' % (value,))
    return (int(fx), int(fy))


# ---------------------------------------------------------------- statuses

def load_status(path):
    """{(x, y): {'status', 'ring', 'region', 'set', 'legacy_maps'}} from a tracker file: the tracker store
    (aw-cell-progress-1, cell-progress.json) or the public reference (docs/chim/cell-progress-reference.json)."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    cells = data.get('cells') if isinstance(data, dict) else None
    if not isinstance(cells, dict):
        raise ValueError('%s: not a CHIM progress tracker file (no "cells" table)' % Path(path).name)
    out = {}
    file_generated = data.get('generated')      # when the tracker file itself was written (every record is at least this old)
    for key, rec in cells.items():
        chim = rec.get('chim') if isinstance(rec.get('chim'), dict) else None
        status = chim.get('status') if chim is not None else rec.get('status')
        island = rec.get('set') or {1: 'vvardenfell', 2: 'bloodmoon'}.get(rec.get('island'), '')
        legacy = rec.get('legacy') if isinstance(rec.get('legacy'), dict) else {}
        # the failing audits and the CHIMport run that measured them, for a refusal that says how old they are
        audits = (rec.get('audits') if isinstance(rec.get('audits'), dict) else {})
        failing = sorted(m for m, a in audits.items() if (a.get('status') if isinstance(a, dict) else a) == 'failed')
        audited = rec.get('audited') if isinstance(rec.get('audited'), dict) else (
            {'run': chim.get('build'), 'at': (chim.get('result_generated') or '')[:10] or None} if chim else {})
        out[parse_cell(key)] = {'status': status, 'ring': rec.get('ring'),
                                'region': rec.get('region') or rec.get('name') or '', 'set': island,
                                'legacy_maps': legacy.get('maps'), 'failing': failing, 'audited': audited or {},
                                'file_generated': file_generated,
                                'name': rec.get('name') or ''}
    return out


def kind_of(status):
    if status in SEABED:
        return 'seabed'
    if status in LAND_DONE:
        return 'land'
    if status in OCEAN:
        return 'ocean'
    return None


# ---------------------------------------------------------------- selection

def read_cell_file(path):
    """(cells, regions, record) of a cell file: aw-chim-cells-1 JSON, a Toolkit World Map state export
    (selected_cells[].cell) or a CSV with x and y columns (the tracker's Export CSV as is)."""
    path = Path(path)
    raw = path.read_bytes()
    record = {'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest()}
    text = raw.decode('utf-8-sig')
    if path.suffix.lower() == '.json' or text.lstrip().startswith('{'):
        data = json.loads(text)
        if isinstance(data, dict) and 'selected_cells' in data:
            record['format'] = 'toolkit world map state'
            return [parse_cell(c) for c in data['selected_cells']], [], record
        if not isinstance(data, dict) or data.get('format') != CELLS_FORMAT:
            raise ValueError('%s: a cell file is %s JSON, a Toolkit World Map state export or CSV'
                             % (path.name, CELLS_FORMAT))
        extra = set(data) - {'format', 'cells', 'regions', 'reason', 'notes'}
        if extra:
            raise ValueError('%s: unknown keys %s' % (path.name, ', '.join(sorted(extra))))
        regions = data.get('regions') or []
        if not isinstance(regions, list) or not all(isinstance(r, str) for r in regions):
            raise ValueError('%s: "regions" must be a list of names' % path.name)
        record.update(format=CELLS_FORMAT, reason=data.get('reason', ''), notes=data.get('notes', ''))
        return [parse_cell(c) for c in data.get('cells') or []], regions, record
    rows = [r for r in csv.reader(io.StringIO(text)) if any(v.strip() for v in r)]
    if not rows:
        raise ValueError('%s: empty cell file' % path.name)
    head = [v.strip().casefold() for v in rows[0]]
    if 'x' in head and 'y' in head:
        ix, iy = head.index('x'), head.index('y')
        rows = rows[1:]
    else:
        ix, iy = 0, 1
    record['format'] = 'csv'
    return [parse_cell([r[ix], r[iy]]) for r in rows], [], record


def match_region(name, statuses):
    known = sorted({v['region'] for v in statuses.values() if v['region']})
    key = name.strip().casefold()
    for region in known:
        if region.casefold() in (key, key + ' region'):
            return region
    raise ValueError('Unknown region %r. Regions in the tracker file: %s' % (name, '; '.join(known)))


def named_cells(name, statuses):
    """Cells of a named set, on Vvardenfell: seabed (empty sea), coast (finished land cells of ring 1, the
    cells touching the sea), sea-ring (both), coast2 (EVERY cell of rings 1 and 2, whatever its status: the
    preflight drops the ones that cannot go on CHIM, each with its reason)."""
    main = {c: v for c, v in statuses.items() if v['set'] == 'vvardenfell'}
    if name == 'seabed':
        return sorted(c for c, v in main.items() if v['status'] in SEABED)
    if name == 'coast':
        return sorted(c for c, v in main.items() if v['status'] in LAND_DONE and v['ring'] == 1)
    if name == 'sea-ring':
        return sorted(set(named_cells('seabed', statuses)) | set(named_cells('coast', statuses)))
    if name == 'coast2':
        return sorted(c for c, v in main.items() if v['ring'] in COAST2_RINGS)
    raise ValueError('Unknown named set: ' + name)


def region_cells(region, statuses):
    return [c for c, v in statuses.items() if v['region'] == region and kind_of(v['status']) in ('seabed', 'land')]


def select(specs, statuses, read_file=read_cell_file):
    """(cells, explicit, record): the union of every --chim-regions value. A value is a named set (seabed,
    coast, sea-ring), a region name (its finished cells), comma-separated names, or @FILE (explicit cells
    and/or regions). Explicit cells are taken as given: the preflight judges them."""
    cells, explicit, record = set(), set(), {'values': [], 'files': []}
    for spec in specs:
        parts = [spec] if spec.startswith('@') else [p.strip() for p in spec.split(',') if p.strip()]
        for part in parts:
            if part.startswith('@'):
                found, regions, rec = read_file(part[1:])
                explicit.update(found)
                cells.update(found)
                for region in regions:
                    cells.update(region_cells(match_region(region, statuses), statuses))
                record['files'].append(rec)
            elif part.casefold() in NAMED:
                cells.update(named_cells(part.casefold(), statuses))
            else:
                cells.update(region_cells(match_region(part, statuses), statuses))
            record['values'].append(part)
    record['explicit_cells'] = len(explicit)
    return sorted(cells), sorted(explicit), record


# ---------------------------------------------------------------- checks

def cell_box(cell):
    """A cell's box in Morrowind units (x0, y0, x1, y1)."""
    x, y = cell
    return (x * CELL_UNITS, y * CELL_UNITS, (x + 1) * CELL_UNITS, (y + 1) * CELL_UNITS)


def boxes_meet(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def box_covered(box, boxes):
    """True when the union of `boxes` covers all of `box` (axis-aligned, exact: every piece of the grid the boxes'
    edges cut `box` into has its centre inside one of them)."""
    inside = [b for b in boxes if boxes_meet(box, b)]
    if not inside:
        return False
    xs = sorted({box[0], box[2]} | {v for b in inside for v in (b[0], b[2]) if box[0] < v < box[2]})
    ys = sorted({box[1], box[3]} | {v for b in inside for v in (b[1], b[3]) if box[1] < v < box[3]})
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if not any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in inside):
                return False
    return True


def town_cells(cells, town_boxes):
    """Cells near `cells` (their bounding box and one more ring) that lie wholly inside the town frames: CHIM town
    cells with no legacy map left. The pocket test counts them as CHIM (CHIM-REGION-POCKET-TOWN-CELLS-42): a region
    frame next to a town frame crosses CHIM to CHIM, never into a second map."""
    cells = [tuple(c) for c in cells]
    boxes = list((town_boxes or {}).values())
    if not cells or not boxes:
        return []
    x0, x1 = min(c[0] for c in cells) - 1, max(c[0] for c in cells) + 1
    y0, y1 = min(c[1] for c in cells) - 1, max(c[1] for c in cells) + 1
    out = []
    for b in boxes:
        for x in range(max(x0, int(b[0] // CELL_UNITS)), min(x1, int(b[2] // CELL_UNITS)) + 1):
            for y in range(max(y0, int(b[1] // CELL_UNITS)), min(y1, int(b[3] // CELL_UNITS)) + 1):
                if (x, y) not in out and box_covered(cell_box((x, y)), boxes):
                    out.append((x, y))
    return sorted(out)


def holes(cells, limit=HOLE_MAX):
    """Unselected pockets enclosed by the selection (4-connected flood from outside its box: a pocket open
    only at a corner is enclosed, leaving it crosses a selected cell), of at most `limit` cells: sorted lists
    of cells. A larger enclosed area (the island inside a ring) is legacy territory, not a pocket."""
    chosen = set(map(tuple, cells))
    if not chosen:
        return []
    x0 = min(c[0] for c in chosen) - 1
    x1 = max(c[0] for c in chosen) + 1
    y0 = min(c[1] for c in chosen) - 1
    y1 = max(c[1] for c in chosen) + 1
    seen, pockets = set(), []

    def flood(start):
        part, stack = [], [start]
        seen.add(start)
        while stack:
            c = stack.pop()
            part.append(c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n in seen or n in chosen or not (x0 <= n[0] <= x1 and y0 <= n[1] <= y1):
                    continue
                seen.add(n)
                stack.append(n)
        return part
    for x in range(x0, x1 + 1):           # the outside: every unselected cell reachable from the box border
        for y in (y0, y1):
            if (x, y) not in seen:
                flood((x, y))
    for y in range(y0, y1 + 1):
        for x in (x0, x1):
            if (x, y) not in seen:
                flood((x, y))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if (x, y) not in seen and (x, y) not in chosen:
                part = flood((x, y))
                if len(part) <= limit:
                    pockets.append(sorted(part))
    return sorted(pockets)


def components(cells):
    """Number of 4-connected groups of the selection (reported, not refused)."""
    left, n = set(map(tuple, cells)), 0
    while left:
        stack = [left.pop()]
        n += 1
        while stack:
            x, y = stack.pop()
            for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if c in left:
                    left.remove(c)
                    stack.append(c)
    return n


def converter_note(recorded):
    """Whether recorded CHIMport audits ran on this converter (chimport.code_identity: tools/, src/, config/, VERSION,
    CHIM_VERSION). Results from another converter may predate the fix that makes a cell pass."""
    if not recorded:
        return 'converter not recorded: measured before converter hashes were kept, so likely an older builder'
    try:
        from chimport import code_identity
        current = code_identity()
    except Exception:                         # a missing tool never fails the preflight; it only says so
        return 'converter %s (current one not hashed here)' % recorded[:12]
    return ('the same converter as this build' if recorded == current
            else 'an older converter (%s, this build %s): measure again' % (recorded[:12], current[:12]))


def preflight(cells, explicit, statuses, town_boxes, one_map_only=False):
    """(kept cells, problems, dropped): problems refuse the build; dropped = cells of named sets and regions
    left out with their reason (inside a town's frame). town_boxes: {town: (x0, y0, x1, y1) Morrowind units}.

    A divided cell (its legacy open world split into 2 x 2 or 4 x 4 maps) is taken: its one CHIM frame owns the
    whole cell and the world terrain stage gives the frame one directory row for the cell
    (CHIM-REGION-DIVIDED-CELLS-36, docs/BUILD_MANIFEST.md step 2b). Only one_map_only (the earlier method,
    --chim-region-rows legacy, which copies the rows of ONE legacy map) refuses a cell whose tracker record lists
    more than one map; that list counts every map whose 896-unit apron holds an object of the cell, so it
    over-counts and is never used to judge the default method."""
    problems, dropped, kept = [], [], []
    stale = []          # refused on recorded audits: measured again with the current builder by one command
    for cell in cells:
        cell = tuple(cell)
        rec = statuses.get(cell)
        status = rec['status'] if rec else None
        kind = kind_of(status)
        if kind is None or (kind == 'ocean' and cell not in explicit):
            reason = ('CHIMport status %s, not finished (taken: %s)' % (status or 'unknown', ', '.join(SEABED + LAND_DONE))
                      if kind is None else 'open sea requires an explicit cell selection and original-source admission checks')
            if kind is None and rec and rec.get('failing'):
                when = rec.get('audited') or {}
                versions = ', '.join(v for v in (('AmiWind ' + when['amiwind_version']) if when.get('amiwind_version') else '',
                                                 ('CHIM ' + when['chim_version']) if when.get('chim_version') else '') if v)
                reason = ('CHIMport audits failing: %s (measured %s by run %s%s; %s)'
                          % (', '.join(rec['failing']), when.get('at') or (
                              'at an unrecorded time, before %s (when the status file was created)' % rec['file_generated']
                              if rec.get('file_generated') else 'at an unrecorded time'), when.get('run') or 'unknown',
                             ' with ' + versions if versions else '', converter_note(when.get('converter_sha256'))))
                if rec.get('name'):
                    reason = rec['name'] + ': ' + reason
            if cell in explicit:
                problems.append('cell %s: %s' % (cell_key(cell), reason))
                if kind is None and status in ('converted_failing', 'converted_unmeasured', 'hull_policy_pending'):
                    stale.append(cell_key(cell))
            else:                     # a named set (coast2) or region name: left out with its reason, listed
                dropped.append({'cell': list(cell), 'reason': reason})
            continue
        maps = rec.get('legacy_maps')
        if one_map_only and maps is not None and len(maps) != 1:
            problems.append('cell %s: the tracker lists %d legacy maps for it; the earlier region method '
                            '(--chim-region-rows legacy) copies exactly one open-world map' % (cell_key(cell), len(maps)))
            continue
        towns = sorted(t for t, box in town_boxes.items() if boxes_meet(cell_box(cell), box))
        if towns:
            # towns win, also over a cell listed by name (project decision 2026-10-11 09:55: all of Vivec is one CHIM
            # frame, so the coast lists' cells inside it leave the selection): dropped and recorded, never refused
            reason = 'inside the frame of %s (towns keep their own frame)' % ', '.join(towns)
            dropped.append({'cell': list(cell), 'reason': reason + ('; listed by name' if cell in explicit else '')})
            continue
        kept.append(cell)
    # cells wholly inside a town frame are CHIM too: they close a ring around a town, they never open a pocket
    for pocket in holes(kept + [c for c in town_cells(kept, town_boxes) if c not in kept]):
        problems.append('cells %s: a legacy pocket enclosed by CHIM region cells (select them too, or leave out a '
                        'neighbour): every crossing there would load two maps' % ' '.join(map(cell_key, pocket)))
    if stale:
        # CHIMPORT-STATUS-STALE-41: recorded audits can predate the fix that makes the cell pass; say how to measure
        # them again with the current builder instead of only refusing
        problems.append('measure the %d refused cell(s) again with this builder: python3 tools/chimport.py run --out RUN '
                        '--cells "%s", then feed the tracker and publish the reference (docs/chim/CHIMPORT.md, '
                        '"Running CHIMport yourself")' % (len(stale), ' '.join(stale)))
    return kept, problems, dropped


# ---------------------------------------------------------------- the table

def frame_row(cell, margin=TERRAIN_MARGIN):
    """One frame: id, cell, origin (map units: the cell centre x 0.25, z 0 as every CHIM frame), core = the
    owned cell box, ground = core + the terrain-only margin (frame-local map units)."""
    x, y = cell
    origin = [(x * CELL_UNITS + CELL_UNITS / 2) * SCALE, (y * CELL_UNITS + CELL_UNITS / 2) * SCALE, 0.0]
    return {'id': frame_id(cell), 'cell': [x, y], 'cells': [[x, y]], 'origin': origin,
            'core': [[-HALF, -HALF], [HALF, HALF]],
            'ground': [[-HALF - margin, -HALF - margin], [HALF + margin, HALF + margin]]}


def ownership(kinds, selection=None, dropped=(), margin=TERRAIN_MARGIN):
    """The ownership table (aw-chim-ownership-1) of preflighted cells. kinds: {(x, y): 'seabed' | 'land'}."""
    cells = sorted(kinds)
    frames = [dict(frame_row(c, margin), **({'kind': 'ocean'} if kinds[c] == 'ocean' else {})) for c in cells]
    table = {'format': FORMAT, 'cell_map_units': CELL_MAP, 'leave_margin': LEAVE_MARGIN, 'terrain_margin': margin,
             'cells': {cell_key(c): {'frame': frame_id(c), 'kind': kinds[c]} for c in cells},
             'frames': frames, 'dropped': list(dropped), 'selection': selection or {}}
    table['counts'] = {'cells': len(cells), 'frames': len(frames),
                       'seabed': sum(1 for k in kinds.values() if k == 'seabed'),
                       'land': sum(1 for k in kinds.values() if k == 'land'),
                       **({'ocean': sum(k == 'ocean' for k in kinds.values())} if 'ocean' in kinds.values() else {}),
                       'components': components(cells)}
    return table


def kind_summary(counts):
    text = '%d seabed, %d land' % (counts['seabed'], counts['land'])
    return text + (', %d ocean' % counts['ocean'] if counts.get('ocean') else '')


def check_table(table):
    """Problems of an ownership table read back (format, ids, one owner per cell, no pocket)."""
    if not isinstance(table, dict) or table.get('format') != FORMAT:
        return ['not an %s table' % FORMAT]
    problems, owners = [], {}
    for f in table['frames']:
        if f['id'] != frame_id(f['cell']):
            problems.append('frame %s does not name its cell %s' % (f['id'], f['cell']))
        for c in f['cells']:
            if cell_key(c) in owners:
                problems.append('cell %s owned by %s and %s' % (cell_key(c), owners[cell_key(c)], f['id']))
            owners[cell_key(c)] = f['id']
    if set(owners) != set(table['cells']):
        problems.append('the frames and the cell list disagree')
    return problems


def encode_cells(kinds):
    """The stage-command form of preflighted cells: "x,y:k ..." (k = s seabed, l land), sorted. The chim stage
    takes the cells on its command line, so its fingerprint covers exactly them (not the tracker file)."""
    return ' '.join('%d,%d:%s' % (c[0], c[1], KIND_CODES[kinds[c]]) for c in sorted(kinds))


def decode_cells(text):
    codes = {v: k for k, v in KIND_CODES.items()}
    out = {}
    for token in text.split():
        cell, _, code = token.partition(':')
        if code not in codes:
            raise ValueError('CHIM region cell %r: kind must be s (seabed), l (land) or o (ocean)' % token)
        out[parse_cell(cell)] = codes[code]
    return out


def frame_settings(frame, margin=TERRAIN_MARGIN):
    """One owned cell, with separate terrain/scenery apron and unchanged handoff core.

    Audit adjacent source cells too: a rock whose origin belongs to the next
    cell can cross this core and its handoff band. Whole-object footprint
    selection keeps needed apron copies; owned_cells keeps logical ownership
    and source-receipt identity separate (CHIM-FRAME-STATIC-SEAM-40).
    """
    x, y = frame['cell']
    name = frame['id']
    from visual_recipes import cell_settings
    return {
        **cell_settings((x, y)),
        'missing_land': 'flat', 'region_source_apron': True,
        **({'ocean_runtime': True} if frame.get('kind') == 'ocean' else {}),
        'format': 1, 'source_cell': [x, y], 'source_radius': 1,
        'owned_cells': [[x, y], [x + 1, y + 1]],
        'centre': [x * CELL_UNITS + CELL_UNITS // 2, y * CELL_UNITS + CELL_UNITS // 2], 'scale': SCALE,
        'bounds': [[-HALF, -HALF], [HALF, HALF]], 'reference_margin': margin,
        'terrain_margin': margin, 'handoff_core': [[-HALF, -HALF], [HALF, HALF]],
        'core_size': 1024, 'overlap': 896, 'hysteresis': 96, 'draw_distance': 540, 'terrain_step': 128,
        'terrain_material_repairs': [], 'entity_budget': 1000, 'model_budget': 220, 'collision_margin': 224,
        'region_core_overrides': {},
        'town': {'id': name, 'title': 'Cell %d,%d' % (x, y), 'map': name, 'map_prefix': 'zf', 'region_cap': 64,
                 'message': 'Cell %d,%d' % (x, y), 'region_file': name + '-regions.txt',
                 'door_file': 'scene-doors-' + name + '.txt', 'visual_group': name,
                 'arrival': {'source_position': [x * CELL_UNITS + 4096.0, y * CELL_UNITS + 4096.0, 0.0],
                             'reason': 'CHIM region frame (open world; no arrival of its own)'}, 'return': None},
    }



def check_source_land(settings, audit, land_records=None, source=None):
    """Allow heightless ocean in an apron, never a missing owned land cell.

    The wider reference survey must cross coastline cells with no LAND. Its
    fallback is recorded by mwad.audit; runtime terrain still follows the
    existing LAND/ocean terrain path. Explicit ocean cores retain admit_cell.

    An owned cell whose LAND record carries no heights (no VHGT: the 98 seabed
    cells, CHIM-REGION-SEABED-NO-HEIGHTS-42) is admitted as flat seabed at the
    original default height, as CHIMport converts it: rule from OpenMW
    components/esm3/loadland.hpp (Land::DEFAULT_HEIGHT -2048) and
    components/esmterrain/storage.cpp (a LAND without DATA_VHGT reads
    defaultHeight); mwad.audit.default_land is that height. land_records: a
    callable or set of the cells with a live LAND record in the masters
    (chim.ocean_runtime.land_cells), read only when the owned cell has no
    heights; a cell with no LAND record at all is still refused. source: the
    audit file (path, sha256) named in a refusal.
    """
    if not settings.get('region_source_apron'):
        return None
    area = audit['area']
    cell = tuple(settings['source_cell'])
    frame = (settings.get('town') or {}).get('id', '?')
    where = 'frame %s, owned cell (%d,%d)%s' % (frame, cell[0], cell[1], (
        ', source audit %s sha256 %s' % source) if source else '')
    if (list(area['center']) != list(cell) or area['radius_cells'] != settings['source_radius']
            or cell not in {(r['x'], r['y']) for r in area['cells']}):
        raise ValueError('Regional scenery source audit has a different owned cell or scope (%s; check: audit '
                         'centre %s radius %s against source_cell, source_radius %s)'
                         % (where, list(area['center']), area['radius_cells'], settings['source_radius']))
    if settings.get('ocean_runtime') or cell not in {tuple(c) for c in area['default_land_cells']}:
        return None
    records = land_records() if callable(land_records) else land_records
    if records is not None and cell in {tuple(c) for c in records}:
        return 'heightless-land'
    raise ValueError('Regional owned cell has no original LAND; explicit ocean admission required (%s; check: '
                     'check_source_land, the cell has %s and the frame is not open ocean)'
                     % (where, 'no LAND record in the masters' if records is not None
                        else 'no heights and no LAND record list was given'))


def town_boxes(towns, root=None):
    """{town: frame box in Morrowind units} of the towns a build holds (their frames win over CHIM regions)."""
    from actor_grounding_census import area_box
    return {t: tuple(area_box(t, root)) for t in towns}


def plan(specs, status_path, towns=(), root=None, read_file=read_cell_file, margin=TERRAIN_MARGIN, boxes=None,
         one_map_only=False):
    """(table, problems): the preflight and the ownership table of --chim-regions values against a tracker
    file; boxes: town boxes (default: those of `towns`, town_boxes); one_map_only: the earlier region method
    (preflight)."""
    statuses = load_status(status_path)
    cells, explicit, record = select(specs, statuses, read_file)
    record['status_file'] = {'file': Path(status_path).name,
                             'sha256': hashlib.sha256(Path(status_path).read_bytes()).hexdigest()}
    if boxes is None:
        boxes = town_boxes(towns, root) if towns else {}
    kept, problems, dropped = preflight(cells, set(explicit), statuses, boxes, one_map_only)
    if not kept and not problems:
        problems.append('the selection %s holds no cell' % ', '.join(specs))
    kinds = {c: kind_of(statuses[c]['status']) for c in kept}
    return ownership(kinds, record, dropped, margin), problems


def ocean_land_problems(kinds, data_files):
    """Cells taken as open ocean (the shared ocean chunk) that have a LAND record in the masters: refused in the
    preflight, in seconds, instead of by the ocean admission inside the CHIM stage (CHIMPORT-OCEAN-LAND-41)."""
    ocean = sorted(c for c, k in kinds.items() if k == 'ocean')
    if not ocean or not data_files:
        return []
    from chim.ocean_runtime import land_cells
    land = land_cells(data_files)
    bad = [c for c in ocean if tuple(c) in land]
    if not bad:
        return []
    return ['%d cell(s) the status file calls open ocean have LAND in the game data (seabed, not open sea): %s; '
            'measure them again with this builder: python3 tools/chimport.py run --out RUN --cells "%s", then feed the '
            'tracker and publish the reference' % (len(bad), ' '.join(cell_key(c) for c in bad),
                                                   ' '.join(cell_key(c) for c in bad))]


def owned_land_problems(kinds, data_files):
    """Land/seabed region cells with no LAND record at all in the masters: check_source_land refuses them inside
    the CHIM stage (no heights and no ocean admission), so the preflight names them in seconds first. A LAND
    record without heights is fine (flat seabed, CHIM-REGION-SEABED-NO-HEIGHTS-42)."""
    owned = sorted(c for c, k in kinds.items() if k != 'ocean')
    if not owned or not data_files:
        return []
    from chim.ocean_runtime import land_cells
    land = land_cells(data_files)
    bad = [c for c in owned if tuple(c) not in land]
    if not bad:
        return []
    return ['%d region cell(s) the status file calls land or seabed have no LAND record in the game data (the '
            'CHIM stage would refuse them: no original LAND, no open-ocean admission): %s'
            % (len(bad), ' '.join(cell_key(c) for c in bad))]


def ocean_map_split(kinds, data_files):
    """(replaced, routing, problems) of the selected cells by the world terrain planner's own rule
    (exterior_plan.ocean_routing), read from the base master in seconds before any stage: an open-sea cell with a
    CELL record has an open-world map, which its CHIM frame map replaces in place (replaced); one with no record
    gets a routing row (routing); a land or seabed cell without a map refuses the build here instead of 30 minutes
    in, in world terrain (CHIM-OCEAN-CELL-RECORD-ROUTING-43). Nothing is read without ocean cells or data files."""
    ocean = sorted(c for c, k in kinds.items() if k == 'ocean')
    if not ocean or not data_files:
        return [], [], []
    from mwad.paths import child_ci
    from exterior_plan import ocean_routing, source_cells
    mapped = set(source_cells(child_ci(Path(data_files), 'Morrowind.esm'))[0])
    routing, problems = ocean_routing(kinds, ocean, mapped)
    replaced = sorted(set(ocean) & mapped)
    return replaced, routing, ['world terrain would refuse the selection: %s' % p for p in problems]


def table_kinds(table):
    return {parse_cell(k): v['kind'] for k, v in table['cells'].items()}


def read_table(path):
    """The ownership table of a CHIM world (CHIM_WORLD/chim-regions.json), checked; None when absent."""
    path = Path(path)
    if not path.is_file():
        return None
    table = json.loads(path.read_text(encoding='utf-8'))
    problems = check_table(table)
    if problems:
        raise ValueError('%s: %s' % (path.name, '; '.join(problems[:4])))
    return table


TABLE_FILE = 'chim-regions.json'


def dumps(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='CHIM regions: preflight a --chim-regions selection and write its '
                                             'ownership table (docs/chim/CHIM_REGIONS.md)')
    ap.add_argument('select', nargs='+', help='seabed, coast, sea-ring, a region name, or @FILE (CSV, '
                                              'aw-chim-cells-1 JSON, Toolkit World Map state export)')
    ap.add_argument('--status', required=True, type=Path, help='CHIM progress tracker file (cell-progress.json)')
    ap.add_argument('--town', action='append', default=[], help='a town the build holds (its frame wins)')
    ap.add_argument('--out', type=Path, help='write the table here (JSON)')
    ap.add_argument('--cells', action='store_true', help='print the cells in the stage-command form')
    a = ap.parse_args(argv)
    table, problems = plan(a.select, a.status, a.town)
    for p in problems:
        print('CHIM regions preflight: ' + p)
    c = table['counts']
    print('CHIM regions: %d cells (%s) in %d frames, %d groups; %d dropped'
          % (c['cells'], kind_summary(c), c['frames'], c['components'], len(table['dropped'])))
    if a.cells:
        print(encode_cells(table_kinds(table)))
    if a.out:
        a.out.write_bytes(dumps(table).encode('utf-8'))
    return 1 if problems else 0


if __name__ == '__main__':
    import sys
    sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[2] / 'src')]
    raise SystemExit(main())
