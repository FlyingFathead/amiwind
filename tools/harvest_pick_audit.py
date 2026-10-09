#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Harvest pick audit: can every placed plant of every harvest catalogue be picked?

The engine picks a plant (aw_harvest_runtime.c target()) with a 72-unit point trace along the view
and a slab test against the plant's oriented box; a plant is the target only when its box is
entered before the trace hits world or a solid entity. Collision of converted scenery is an
approximation (convex pieces of the source collision), so a solid can enclose a plant that is
drawn in the open: a Bitter Coast tree's collision closes the space under its roots, and the
mushrooms growing there could not be picked (HARVEST-BITTERCOAST-29). The engine rule since the
fix: a solid that contains the plant's own centre does not hide that plant.

This tool replays target() offline for every plant of every harvest-<map>.txt next to its map: the
player stands at the plant's reach distance in eight directions (feet on the standing hull's floor,
eye 13.3 above the origin) and aims at the box centre. A plant is pickable when at least one
position picks it. Both rules are reported ('before' = the earlier engine rule, 'fixed' = the
current one); `check` fails on any plant that the current rule cannot pick from anywhere, unless
it is listed with its bug ID in config/harvest-pick-known.json.

Usage:
  harvest_pick_audit.py audit --id1 DIR --out REPORT.json [--jobs N] [--maps vf0850,...] [--bsp-dir DIR]
  harvest_pick_audit.py check --report REPORT.json [--known config/harvest-pick-known.json]
  harvest_pick_audit.py gate --id1 DIR --out REPORT.json [--jobs N]
"""
import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

KNOWN = Path(__file__).resolve().parents[1] / 'config/harvest-pick-known.json'
REACH = 72.0            # aw_harvest_runtime.c target(): VectorMA(eye, 72, forward, end)
VIEW_HEIGHT = 13.3      # engine/aga/qc/world.qc: self.view_ofs = '0 0 13.3'
STAND = (12.0, 24.0, 36.0)   # horizontal distances tried from the plant
DIRECTIONS = 8


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def angle_vectors(angles):
    """Quake AngleVectors (mathlib.c): forward, right, up."""
    p, y, r = (math.radians(v) for v in angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    forward = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return forward, right, up


def read_catalogue(text):
    """(model boxes, plants) of an AWH4 catalogue: plants are dicts with ref, model, origin, angles, scale."""
    lines = text.splitlines()
    head = lines[0].split()
    if not head or head[0] != 'AWH4':
        raise ValueError('not an AWH4 catalogue')
    count = int(head[-1])
    boxes = []
    for line in lines[1:1 + count]:
        p = line.split()
        boxes.append((tuple(map(float, p[2:5])), tuple(map(float, p[5:8]))))
    plants = []
    for line in lines[1 + count:]:
        p = line.split()
        if len(p) < 14 or not p[0].startswith('aw:h:') or not p[3].startswith('@'):
            continue
        plants.append({'ref': int(p[2]), 'model': int(p[3][1:]), 'origin': tuple(map(float, p[7:10])),
                       'angles': tuple(map(float, p[10:13])), 'scale': float(p[13]),
                       'label': ' '.join(p[14:])})
    return boxes, plants


class Box:
    """A plant's pick box as target() sees it (proxy angles with the pitch negated)."""

    def __init__(self, plant, box):
        self.origin, self.scale = plant['origin'], plant['scale']
        a = plant['angles']
        self.axis, self.right, self.up = angle_vectors((-a[0], a[1], a[2]))
        self.lo, self.hi = box
        c = [(self.lo[i] + self.hi[i]) / 2 for i in range(3)]
        self.centre = tuple(self.origin[k] + self.scale * (c[0] * self.axis[k] - c[1] * self.right[k] + c[2] * self.up[k])
                            for k in range(3))

    def entry(self, eye, forward, limit):
        """target()'s slab test: entry distance, or None."""
        delta = [eye[k] - self.origin[k] for k in range(3)]
        s = self.scale
        ray = (_dot(forward, self.axis) / s, -_dot(forward, self.right) / s, _dot(forward, self.up) / s)
        local = (_dot(delta, self.axis) / s, -_dot(delta, self.right) / s, _dot(delta, self.up) / s)
        lo, hi = 0.0, limit + .01
        for j in range(3):
            o, d = local[j], ray[j]
            if abs(d) < .00001:
                if o < self.lo[j] or o > self.hi[j]:
                    return None
                continue
            a, b = (self.lo[j] - o) / d, (self.hi[j] - o) / d
            if a > b:
                a, b = b, a
            lo, hi = max(lo, a), min(hi, b)
            if lo > hi:
                return None
        return lo if lo <= limit + .01 else None


def _scene(raw, hull):
    """audit_walkability.Scene with brush culling by box (the plain Scene traces every brush)."""
    from audit_walkability import Scene
    from player_hull import lumps

    class Culled(Scene):
        def __init__(self, raw, hull):
            super().__init__(raw, hull)
            models = list(struct.iter_unpack('<9f7i', lumps(raw)[14]))
            ents = [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', b))
                    for b in re.findall(r'\{[^{}]*\}', lumps(raw)[0].decode('cp1252'))]
            refs = {}
            for e in ents:
                if e.get('classname') == 'func_wall' and re.fullmatch(r'\*\d+', e.get('model', '')):
                    refs[e.get('aw_ref', e['model'])] = int(e['model'][1:])
            self.boxes = []
            for root, origin, basis, ref in self.brushes:
                m = models[0] if ref == 'world' else models[refs.get(ref, 0)]
                pad = 20.0 if hull == 1 else 1.0
                self.boxes.append(tuple(origin[i] + m[i] - pad for i in range(3)) +
                                  tuple(origin[i] + m[3 + i] + pad for i in range(3)))

        def _trace_brushes(self, start, end):
            out = []
            for brush, b in zip(self.brushes, self.boxes):
                if brush[3] == 'world' or all(min(start[i], end[i]) <= b[3 + i] and max(start[i], end[i]) >= b[i]
                                              for i in range(3)):
                    out.append(brush)
            return out

    return Culled(raw, hull)


def solid_at(scene, point):
    """Point contents through world and solid entities (a zero-length SV_Move's startsolid): the
    reference of the solid ('world' or the entity's aw_ref) or None."""
    hit = scene.trace(point, (point[0], point[1], point[2] + .01))
    return str(hit['reference']) if hit and hit['fraction'] == 0 else None


def audit_map(task):
    """One map: every plant, both rules."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    bsp, catalogue = Path(task[0]), Path(task[1])
    boxes, plants = read_catalogue(catalogue.read_text(encoding='ascii'))
    raw = bsp.read_bytes()
    point, stand = _scene(raw, 0), _scene(raw, 1)
    rows = []
    for plant in plants:
        box = Box(plant, boxes[plant['model']])
        inside = solid_at(point, box.centre)
        tried = before = fixed = 0
        for d in STAND:
            for k in range(DIRECTIONS):
                a = 2 * math.pi * k / DIRECTIONS
                x, y = box.centre[0] + d * math.cos(a), box.centre[1] + d * math.sin(a)
                top = box.centre[2] + 64
                floor = stand.floor((x, y, top), 160)
                if floor['status'] != 'supported' or floor['fraction'] == 0:
                    continue
                eye = (x, y, floor['height'] + VIEW_HEIGHT)
                if solid_at(point, eye):
                    continue
                v = [box.centre[i] - eye[i] for i in range(3)]
                n = math.sqrt(_dot(v, v))
                if n < 1e-3 or n > REACH:
                    continue
                forward = [c / n for c in v]
                end = tuple(eye[i] + REACH * forward[i] for i in range(3))
                hit = point.trace(eye, end)
                limit = REACH * (hit['fraction'] if hit else 1.0)
                tried += 1
                if box.entry(eye, forward, limit) is not None:
                    before += 1
                    fixed += 1
                elif inside and box.entry(eye, forward, REACH) is not None:
                    fixed += 1
        rows.append({'map': bsp.stem, 'ref': plant['ref'], 'label': plant['label'],
                     'origin': [round(v, 2) for v in plant['origin']], 'centre_in_solid': bool(inside),
                     'centre_solid': inside,
                     'positions': tried, 'pick_before': before, 'pick_fixed': fixed})
    return rows


def audit(id1, jobs=None, maps=None, progress=print, bsp_dir=None):
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    id1 = Path(id1)
    tasks, skipped = [], []
    for cat in sorted(id1.glob('harvest-*.txt')):
        name = cat.stem[len('harvest-'):]
        if maps and name not in maps:
            continue
        dirs = [Path(d) for d in bsp_dir.split(',')] if bsp_dir else [id1 / 'maps']
        bsp = next((d / (name + '.bsp') for d in dirs if (d / (name + '.bsp')).is_file()), None)
        if bsp is None:
            skipped.append(name)
        else:
            tasks.append((str(bsp), str(cat)))
    rows = []
    for i, part in enumerate(ordered_map(audit_map, tasks, resolve_jobs(jobs), cost=lambda t: Path(t[0]).stat().st_size)):
        rows.extend(part)
        if progress and (i % 50 == 0 or i == len(tasks) - 1):
            progress('harvest pick audit %d/%d maps' % (i + 1, len(tasks)))
    report = summarise(rows)
    # Catalogues without a BSP map of their own are followed on a CHIM frame map (AW_HarvestFollow);
    # CHIM collision is not replayed here.
    report['catalogues_without_map'] = skipped
    return report


def summarise(rows):
    """Per plant (a FRMR reference in several overlapping maps): pickable where any map picks it."""
    plants = {}
    for r in rows:
        p = plants.setdefault(r['ref'], {'ref': r['ref'], 'label': r['label'], 'maps': [], 'positions': 0,
                                         'pick_before': 0, 'pick_fixed': 0, 'centre_in_solid': False})
        p['maps'].append(r['map'])
        for k in ('positions', 'pick_before', 'pick_fixed'):
            p[k] += r[k]
        p['centre_in_solid'] = p['centre_in_solid'] or r['centre_in_solid']
        if r.get('centre_solid'):
            p['centre_solids'] = sorted(set(p.get('centre_solids', [])) | {r['centre_solid']})
    out = sorted(plants.values(), key=lambda p: p['ref'])
    return {'method': 'offline replay of aw_harvest_runtime.c target(): %d directions x %s units, eye %.1f above the '
                      'standing origin, aim at the box centre' % (DIRECTIONS, list(STAND), VIEW_HEIGHT),
            'maps': len({r['map'] for r in rows}), 'plants': len(out),
            'unpickable_before': [p['ref'] for p in out if p['positions'] and not p['pick_before']],
            'unpickable_fixed': [p['ref'] for p in out if p['positions'] and not p['pick_fixed']],
            'unreachable': [p['ref'] for p in out if not p['positions']],
            'rows': out}


def load_known(path=KNOWN):
    path = Path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    return {int(e['ref']): e for e in data.get('known', [])}


def check(report, known=None):
    """Failures: plants the current rule cannot pick that are not registered known findings. Plants
    with no standing position within reach (water, steep ground) are reported, not judged."""
    known = load_known() if known is None else known
    bad = sorted(set(report['unpickable_fixed']))
    return [r for r in bad if r not in known]


def main(argv=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('audit', 'gate'):
        p = sub.add_parser(name)
        p.add_argument('--id1', required=True)
        p.add_argument('--out', required=True)
        p.add_argument('--jobs', type=int)
        p.add_argument('--maps')
        p.add_argument('--bsp-dir', help='comma-separated folders searched for each map (default ID1/maps)')
        p.add_argument('--known', default=str(KNOWN))
    p = sub.add_parser('check')
    p.add_argument('--report', required=True)
    p.add_argument('--known', default=str(KNOWN))
    a = ap.parse_args(argv)
    if a.cmd in ('audit', 'gate'):
        report = audit(a.id1, a.jobs, set(a.maps.split(',')) if a.maps else None, bsp_dir=a.bsp_dir)
        Path(a.out).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
        print('harvest pick audit: %d plants in %d maps; unpickable before the fix %d, now %d, no standing '
              'position %d' % (report['plants'], report['maps'], len(report['unpickable_before']),
                               len(report['unpickable_fixed']), len(report['unreachable'])))
        if a.cmd == 'audit':
            return 0
    else:
        report = json.loads(Path(a.report).read_text(encoding='utf-8'))
    failures = check(report, load_known(a.known))
    if failures:
        print('harvest pick audit FAILED: %d plants cannot be picked and are not known findings: %s'
              % (len(failures), ', '.join(map(str, failures[:20]))))
        return 1
    print('harvest pick audit: passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
