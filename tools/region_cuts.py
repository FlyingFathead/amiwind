#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Write sub-cell cut overlays (aw-cuts-1) for the 3D Map Inspector.

An overlay shows where region borders and section cuts go through a map, as
coloured vertical rectangles. It is planning data only: no map, region
directory or section plan is changed by writing or loading one.

Sources:
  town  a town region config: a Balmora-style settings file (bounds, core_size,
        overlap; regions come from balmora_regions.regions) or a bounded layout
        with an explicit "regions" list (the Seyda Neen layout).
  plan  a section plan in the prepare_interior_sections.py format: every
        section's coverage becomes a region and every portal a plane.

Coordinates are map-local, i.e. the compiled BSP XYZ of the built maps. Town
configs already store cores and coverage in that frame (local = (source -
centre) * scale); section plans use the room BSP's own XYZ.

Examples:
  region_cuts.py town --config config/balmora.json --map bm019 --out bm019-cuts.json
  region_cuts.py town --config config/seyda-bounded-regions.json --map sn012
  region_cuts.py plan --plan section-plan.json --out room-cuts.json
  region_cuts.py check --overlay bm019-cuts.json
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FORMAT = 'aw-cuts-1'
SPACE = 'map-local'
# Distinct colours, in the same order as the inspector's own cut palette.
COLOURS = ('#ff5d5d', '#4fc3ff', '#ffd24a', '#7dff8a', '#ff7df0', '#ff9f40',
           '#a98bff', '#3ff5d2', '#d7ff3f', '#ff4f9a', '#5f8bff', '#c8c8c8')
AXES = {0: 'x', 1: 'y', 2: 'z'}
LIMIT = 1e7


def colour(index):
    return COLOURS[index % len(COLOURS)]


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and abs(value) <= LIMIT


def _pair(value, what):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(map(_finite, value)) or value[0] >= value[1]:
        raise ValueError(what + ' must be [low, high] with low < high')
    return [value[0], value[1]]


def _rect(value, what):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(not isinstance(p, (list, tuple)) or len(p) != 2 or not all(map(_finite, p)) for p in value)
            or value[0][0] >= value[1][0] or value[0][1] >= value[1][1]):
        raise ValueError(what + ' must be [[x0, y0], [x1, y1]] with x0 < x1 and y0 < y1')
    return [list(value[0]), list(value[1])]


def _text(value, what, limit=60):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{what} must be 1-{limit} characters')
    return value.strip()


def _colour(value):
    if not isinstance(value, str) or not re.fullmatch('#[0-9a-fA-F]{6}', value):
        raise ValueError('Colour must be #rrggbb')
    return value.lower()


def validate_overlay(doc):
    """Check an overlay with the same rules as the inspector's loader."""
    if not isinstance(doc, dict) or doc.get('format') != FORMAT:
        raise ValueError('Expected format ' + FORMAT)
    if doc.get('space') != SPACE:
        raise ValueError('Overlay space must be "map-local" (compiled BSP XYZ)')
    if 'map' in doc:
        _text(doc['map'], 'Map name', 80)
    if 'z' in doc:
        _pair(doc['z'], 'Overlay z')
    regions, planes = doc.get('regions', []), doc.get('planes', [])
    if not isinstance(regions, list) or not isinstance(planes, list) or len(regions) > 256 or len(planes) > 256:
        raise ValueError('At most 256 regions and 256 planes')
    for region in regions:
        if not isinstance(region, dict) or ('core' not in region and 'coverage' not in region):
            raise ValueError('Region needs core or coverage')
        _text(region.get('name', 'region'), 'Region name')
        for key in ('core', 'coverage'):
            if key in region:
                _rect(region[key], 'Region ' + key)
        if 'z' in region:
            _pair(region['z'], 'Region z')
        if 'colour' in region:
            _colour(region['colour'])
    for plane in planes:
        if not isinstance(plane, dict) or plane.get('axis') not in ('x', 'y', 'z') or not _finite(plane.get('at')):
            raise ValueError('Plane needs axis x, y or z and a finite "at"')
        _text(plane.get('label', 'plane'), 'Plane label')
        if plane['axis'] == 'z':
            _pair(plane.get('x'), 'Horizontal plane x')
            _pair(plane.get('y'), 'Horizontal plane y')
        else:
            _pair([plane.get('from'), plane.get('to')], 'Plane from/to')
            if 'z' in plane:
                _pair(plane['z'], 'Plane z')
        if 'margin' in plane and (not _finite(plane['margin']) or plane['margin'] <= 0):
            raise ValueError('Plane margin must be positive')
        if 'colour' in plane:
            _colour(plane['colour'])
    return doc


def town_regions(settings):
    """Regions of a town config: an explicit layout list, or Balmora-style settings."""
    if isinstance(settings.get('regions'), list):
        entries = settings['regions']
        for entry in entries:
            _text(entry.get('name'), 'Region name', 15)
            _rect(entry.get('core'), 'Region core')
            _rect(entry.get('coverage'), 'Region coverage')
        return entries
    from balmora_regions import regions
    return regions(settings)


def _overlaps(a, b):
    return all(max(a[0][k], b[0][k]) < min(a[1][k], b[1][k]) for k in range(2))


def from_town(settings, map_name=None, *, z=None, all_regions=False, border_planes=False, label=None):
    """Overlay for one region map (its core, coverage and the neighbouring cores).

    Neighbours are the regions whose core overlaps the map's coverage: their
    borders are the sub-cell cuts that pass through that map. With
    all_regions, every core and coverage is written instead.
    """
    entries = town_regions(settings)
    names = [e['name'] for e in entries]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate region names')
    if all_regions:
        chosen, focus = list(entries), None
    else:
        if map_name not in names:
            raise ValueError(f'Unknown region map {map_name!r}; expected one of {names[0]}..{names[-1]}')
        focus = entries[names.index(map_name)]
        chosen = [focus] + [e for e in entries if e is not focus and _overlaps(e['core'], focus['coverage'])]
    regions = []
    for index, entry in enumerate(chosen):
        # The map itself keeps the first colour; neighbours cycle through the others.
        region = {'name': entry['name'], 'core': _rect(entry['core'], 'Region core'),
                  'colour': colour(index if index == 0 or all_regions else 1 + (index - 1) % (len(COLOURS) - 1))}
        if all_regions or entry is focus:
            region['coverage'] = _rect(entry['coverage'], 'Region coverage')
        regions.append(region)
    doc = {'format': FORMAT, 'map': map_name if map_name else 'all regions', 'space': SPACE,
           'source': label or 'town region config',
           'note': 'Region cores (solid walls) and coverage (dashed). Neighbouring cores show the sub-cell '
                   'cuts that pass through this map. Planning overlay only.',
           'regions': regions, 'planes': []}
    if z is not None:
        doc['z'] = _pair(z, 'Overlay z')
    if border_planes and focus is not None:
        doc['planes'] = core_border_planes(focus, chosen)
    return validate_overlay(doc)


def core_border_planes(focus, entries):
    """Each distinct core border line inside the focus coverage, as one plane."""
    cover = focus['coverage']
    lines = {}
    for entry in entries:
        (x0, y0), (x1, y1) = entry['core']
        for axis, at, low, high in (('x', x0, y0, y1), ('x', x1, y0, y1), ('y', y0, x0, x1), ('y', y1, x0, x1)):
            k = 0 if axis == 'x' else 1
            if not cover[0][k] < at < cover[1][k]:
                continue
            other = 1 - k
            low, high = max(low, cover[0][other]), min(high, cover[1][other])
            if low >= high:
                continue
            span = lines.setdefault((axis, at), [low, high])
            span[0], span[1] = min(span[0], low), max(span[1], high)
    planes = []
    for index, ((axis, at), (low, high)) in enumerate(sorted(lines.items())):
        planes.append({'label': f'border {axis}={at:g}', 'kind': 'region-border', 'axis': axis, 'at': at,
                       'from': low, 'to': high, 'colour': colour(index + 6)})
    return planes


def check_plan(plan):
    """Validate the plan's sections and portals with the section tool itself."""
    from prepare_interior_sections import section_text
    return section_text(plan)


def from_plan(plan, map_name=None, *, label=None, check=True):
    """Overlay of a section plan: section coverage boxes and portal planes."""
    if check:
        check_plan(plan)
    sections, portals = plan['sections'], plan['portals']
    regions = []
    for index, section in enumerate(sections):
        lo, hi = section['coverage']
        regions.append({'name': section['name'], 'coverage': [[lo[0], lo[1]], [hi[0], hi[1]]],
                        'z': [lo[2], hi[2]], 'colour': colour(index)})
    planes = []
    for index, portal in enumerate(portals):
        lo, hi = portal['bounds']
        axis = AXES[portal['axis']]
        plane = {'label': f"{portal['from']} | {portal['to']}", 'kind': 'portal', 'axis': axis,
                 'at': portal['split'], 'margin': portal['margin'], 'colour': colour(index + 6)}
        if axis == 'z':
            plane.update(x=[lo[0], hi[0]], y=[lo[1], hi[1]])
        else:
            other = 1 if axis == 'x' else 0
            plane.update({'from': lo[other], 'to': hi[other], 'z': [lo[2], hi[2]]})
        planes.append(plane)
    doc = {'format': FORMAT, 'map': map_name or plan.get('logical_map') or 'section plan', 'space': SPACE,
           'source': label or 'section plan',
           'note': 'Section coverage (dashed boxes) and portals (planes at the split, from the plan). '
                   'Planning overlay only; the plan is not installed.',
           'regions': regions, 'planes': planes}
    return validate_overlay(doc)


def write(doc, out):
    text = json.dumps(doc, indent=1) + '\n'
    if out is None:
        sys.stdout.write(text)
    else:
        with open(out, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    town = sub.add_parser('town', help='overlay from a town region config')
    town.add_argument('--config', type=Path, required=True)
    group = town.add_mutually_exclusive_group(required=True)
    group.add_argument('--map', help='region map name, e.g. bm019 or sn012')
    group.add_argument('--all', action='store_true', help='every region core and coverage')
    town.add_argument('--z', type=float, nargs=2, metavar=('ZMIN', 'ZMAX'))
    town.add_argument('--border-planes', action='store_true', help='also write each core border as a plane')
    town.add_argument('--out', type=Path)
    plan = sub.add_parser('plan', help='overlay from a section plan')
    plan.add_argument('--plan', type=Path, required=True)
    plan.add_argument('--map')
    plan.add_argument('--out', type=Path)
    check = sub.add_parser('check', help='validate an overlay, or a section plan with --plan')
    target = check.add_mutually_exclusive_group(required=True)
    target.add_argument('--overlay', type=Path)
    target.add_argument('--plan', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'town':
        settings = json.loads(args.config.read_text(encoding='utf-8'))
        write(from_town(settings, args.map, z=args.z, all_regions=args.all, border_planes=args.border_planes,
                        label=args.config.name), args.out)
    elif args.command == 'plan':
        write(from_plan(json.loads(args.plan.read_text(encoding='utf-8')), args.map, label=args.plan.name), args.out)
    elif args.overlay:
        doc = validate_overlay(json.loads(args.overlay.read_text(encoding='utf-8')))
        print(f"ok: {doc.get('map', '?')}: {len(doc.get('regions', []))} regions, {len(doc.get('planes', []))} planes")
    else:
        text = check_plan(json.loads(args.plan.read_text(encoding='utf-8')))
        print('ok: ' + text.decode('ascii').splitlines()[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
