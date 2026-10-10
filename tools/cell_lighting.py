#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Per-cell lighting audit of the CHIM Progress Tracker: is a cell lit like the original?

Owner rule (2026-10-09): a cell is only complete when it is lit like Morrowind. This module is the one shared
implementation of that test. It is used by the tracker (tools/cell_progress.py), by the CHIM builder's lighting stats
and by the conversion runner, so all of them count lights and lit surfaces the same way.

Inputs per cell:
  placed  the original light placements of the cell, by class and by mesh / no mesh (light_census_cell(), from the
          light records and the cell references of your own master files; classes from tools/light_sources.py)
  build   what the CHIM build did for the cell: {"mode": none|lamps|baked, "terrain_faces", "terrain_lit",
          "model_faces", "model_lit", "baked": lights baked}. Missing = a build from before the lighting field: the
          mode every CHIM build used until then ("lamps": constant terrain light, models without lightmaps, the night
          lamp table) is assumed and marked so.

How a light reaches the frame:
  baked       a light entity baked into the lightmaps (Quake light entity + lightstyle), as the original lights the
              world around the source all the time;
  lamp_table  the engine's night lamp table (lamp, torch, fire and candle classes outdoors): dynamic light at night
              only, the nearest few lamps; it does not light the world as the original does, so it is partial;
  none        not represented at all.
A surface counts as lit when it carries real light data (a lightmap baked from the sun and the light sources, or a
light sample); one constant value for a whole chunk, or no lightmap at all, is not lit.

Status: lit = every active light baked and every terrain and model surface lit; unlit = no light reaches the frame
and no surface is lit; partial = anything in between; not_measured = the cell is not converted or its light census is
missing. Lights flagged Off by default give no light in the original either and are left out.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from light_sources import ANIMATED, CLASSES, LAMP_CLASSES, LIGHT_CLASS_CODES, classify, quake_style  # noqa: E402

FORMAT = 'aw-cell-lighting-1'
MODES = ('none', 'lamps', 'hybrid', 'baked')   # baked: a build that bakes every light (hybrid with all parts)
ASSUMED_MODE = 'lamps'            # every CHIM build before the lighting field: constant terrain, no model lightmaps, lamp table
STATUSES = ('lit', 'partial', 'unlit', 'not_measured')
STATUS_TEXT = collections.OrderedDict([
    ('lit', 'Lit: every light source of the cell baked (as the original lights it), every terrain and model surface lit.'),
    ('partial', 'Partial: some light reaches the frame (for example the night lamp table) or some surfaces are lit, '
                'but not all.'),
    ('unlit', 'Unlit: no light source reaches the frame and no surface carries real light data.'),
    ('not_measured', 'Not measured: the cell is not converted, or its light census is missing.'),
])
REACH = ('baked', 'lamp_table', 'none')
# Display names of the light classes (tools/light_sources.py CLASSES).
CLASS_LABELS = collections.OrderedDict([
    ('lamp', 'lamp / lantern'), ('candle', 'candle'), ('torch', 'torch'), ('fire', 'fire'), ('glow_plant', 'glowing plant'),
    ('negative', 'darkener (negative light)'), ('pure_light', 'plain light'), ('other', 'other'),
    ('off', 'off by default (no light)')])
assert tuple(CLASS_LABELS) == tuple(CLASSES)


def light_census_cell(lights):
    """Summary of one cell's light placements. lights: iterable of (class, has_mesh, flags, style)."""
    by_class = collections.OrderedDict()
    styles, animated, placed = collections.Counter(), 0, 0
    for kind, has_mesh, flags, style in lights:
        placed += 1
        row = by_class.setdefault(kind, {'mesh': 0, 'meshless': 0})
        row['mesh' if has_mesh else 'meshless'] += 1
        if kind != 'off':
            styles[str(style)] += 1
            animated += 1 if flags & ANIMATED else 0
    return {'placed': placed, 'by_class': {k: by_class[k] for k in CLASSES if k in by_class},
            'styles': dict(sorted(styles.items(), key=lambda kv: int(kv[0]))), 'animated': animated}


def census_light(identifier, obj, exterior=True):
    """(class, has_mesh, flags, style) of one placed light object (world_estimate_data object record)."""
    flags = obj.get('lflags') or 0
    kind = classify(identifier, obj.get('model') or '', flags)
    return kind, bool(obj.get('model')), flags, quake_style(kind, flags, exterior)


def totals(placed):
    """(active, off, meshless, mesh) light counts of a census summary."""
    active = off = meshless = mesh = 0
    for kind, row in (placed or {}).get('by_class', {}).items():
        n = row['mesh'] + row['meshless']
        if kind == 'off':
            off += n
            continue
        active += n
        meshless += row['meshless']
        mesh += row['mesh']
    return active, off, meshless, mesh


def reach(placed, mode, baked=None):
    """{baked, lamp_table, none}: how the active lights of a cell reach the frame in a lighting mode. baked = the
    number of lights the build reports baked (the build's own count wins in baked mode)."""
    if mode not in MODES:
        raise ValueError('unknown CHIM lighting mode: %r' % (mode,))
    out = dict.fromkeys(REACH, 0)
    active = totals(placed)[0]
    if mode == 'baked' or (mode == 'hybrid' and baked is not None):
        b = active if baked is None else min(active, int(baked))
        out['baked'], out['none'] = b, active - b
        return out
    table = {'lamps': LAMP_CLASSES, 'hybrid': LIGHT_CLASS_CODES}.get(mode, ())
    for kind, row in (placed or {}).get('by_class', {}).items():
        if kind == 'off':
            continue
        n = row['mesh'] + row['meshless']
        out['lamp_table' if kind in table else 'none'] += n
    return out


def surfaces(build, stats=None):
    """Surface figures {terrain_faces, terrain_lit, model_faces, model_lit, lit_share, assumed} of a converted cell.
    Without the build's lighting figures the assumed mode applies: faces from the cell stats, none of them lit."""
    b = build or {}
    faces = (stats or {}).get('faces') or {}
    tf = b.get('terrain_faces', faces.get('chim_terrain'))
    mf = b.get('model_faces', faces.get('chim_placed'))
    out = {'terrain_faces': tf, 'model_faces': mf, 'terrain_lit': b.get('terrain_lit', 0) if tf is not None else None,
           'model_lit': b.get('model_lit', 0) if mf is not None else None, 'assumed': 'terrain_lit' not in b}
    known = [(f, l) for f, l in ((tf, out['terrain_lit']), (mf, out['model_lit'])) if f is not None]
    total = sum(f for f, _ in known)
    out['lit_share'] = round(sum(l for _, l in known) / total, 4) if total else (1.0 if known else None)
    return out


def audit(placed, build=None, converted=True, stats=None):
    """The lighting audit of one cell: {format, status, reason, mode, assumed, placed, active, off, meshless, mesh,
    reach, surfaces}. See the module text for the rules."""
    b = build or {}
    mode = b.get('mode') or ASSUMED_MODE
    rec = {'format': FORMAT, 'mode': mode, 'assumed': 'mode' not in b, 'placed': placed}
    active, off, meshless, mesh = totals(placed)
    rec.update({'active': active, 'off': off, 'meshless': meshless, 'mesh': mesh})
    if not converted:
        rec.update(status='not_measured', reason='not converted', reach=None, surfaces=None)
        return rec
    if placed is None:
        rec.update(status='not_measured', reason='light census missing (ingest with --data-files)', reach=None, surfaces=None)
        return rec
    r = reach(placed, mode, b.get('baked'))
    s = surfaces(b, stats)
    rec.update(reach=r, surfaces=s)
    share = s['lit_share'] if s['lit_share'] is not None else 0.0
    lights_ok = r['none'] == 0 and r['lamp_table'] == 0
    if lights_ok and share >= 1.0:
        status, reason = 'lit', 'every light baked, every surface lit'
    elif r['baked'] == 0 and r['lamp_table'] == 0 and share == 0:
        status = 'unlit'
        reason = ('no light source reaches the frame' if active else 'no light sources') + \
            '; no surface carries real light data (%s)' % ('constant terrain light, models without lightmaps'
                                                           if mode != 'baked' else 'bake wrote nothing')
    else:
        status = 'partial'
        bits = []
        if r['lamp_table']:
            bits.append('%d light(s) only as night lamps' % r['lamp_table'])
        if r['none']:
            bits.append('%d light(s) not represented (%d without a mesh)' % (r['none'], min(r['none'], meshless)))
        if share < 1.0:
            bits.append('%.0f %% of the surfaces lit' % (100 * share))
        reason = '; '.join(bits)
    rec.update(status=status, reason=reason)
    if rec['assumed']:
        rec['reason'] += ' (mode %s assumed: the build predates the lighting figures)' % mode
    return rec


def headline(audits):
    """Island-wide lighting line over audits (an iterable of audit dicts): counts per status, lights per class and
    mesh / no mesh, and how the active lights reach the frame."""
    st = collections.Counter(a['status'] for a in audits)
    by_class = collections.OrderedDict((k, {'mesh': 0, 'meshless': 0}) for k in CLASSES)
    rch = dict.fromkeys(REACH, 0)
    cells_with_lights = 0
    for a in audits:
        p = a.get('placed') or {}
        if p.get('placed'):
            cells_with_lights += 1
        for k, row in p.get('by_class', {}).items():
            by_class[k]['mesh'] += row['mesh']
            by_class[k]['meshless'] += row['meshless']
        for k, n in (a.get('reach') or {}).items():
            rch[k] += n
    return {'cells': sum(st.values()), 'status': {k: st[k] for k in STATUSES}, 'cells_with_lights': cells_with_lights,
            'lights': {k: v for k, v in by_class.items() if v['mesh'] or v['meshless']}, 'reach': rch}
