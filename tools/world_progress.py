#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""World progress table: one row per Vvardenfell exterior cell, for the map viewer.

The basis is the topomap: the open-world terrain, converted for the whole
island, read from the runtime region table (id1/world/regions.awr). Everything
else is a layer on top of it.

Inputs (generated or owner-maintained; none of them game data in the output):
  --regions   id1/world/regions.awr from the image (terrain coverage per cell)
  --entities  entity-tracker.json from the image build (tools/entity_tracker.py)
  --poi       the private POI checklist JSON (tools/poi_checklist.py); only
              counts per cell are copied, never place names
  --checked   docs/trackers/checked.json: cells the owner walked and accepted

Per cell: map ("full" town/area map, "terrain" topomap only, or "none"),
original vs placed entities, named places, interiors whose entrance is in the
cell (and how many are converted), and whether it is checked. Open
amiwind-toolkit/world-map.html (or the AmiWind Toolkit page) and load the output to see the layers.

Usage:
  world_progress.py --regions regions.awr --entities entity-tracker.json
                    [--poi poi.json] [--checked docs/trackers/checked.json]
                    --out world-progress.json
"""
import argparse, json, re, struct, sys
from pathlib import Path

FORMAT = 'AW-WORLD-PROGRESS2'
CELL_UNITS = 2048  # converted world units per exterior cell
WORLD_MAP_NAME = re.compile(r'vf[0-9]+$')


def terrain_regions(awr):
    """{(x, y): [open-world map names]} from an AWR2 region table: 'AWR2', entry
    count, town hand-off records (7 floats each), then per entry an 8-byte name
    and 11 floats (origin xyz, core, coverage) in world units."""
    if awr[:4] != b'AWR2':
        raise ValueError('not an AWR2 region table')
    count = struct.unpack_from('<I', awr, 4)[0]
    towns, rest = divmod(len(awr) - 8 - count * 52, 28)
    if rest or towns < 0:
        raise ValueError('AWR2 size does not match its entry count')
    cells, off = {}, 8 + towns * 28
    for i in range(count):
        name = awr[off + i * 52:off + i * 52 + 8].rstrip(b'\0').decode('ascii').lower()
        x, y = struct.unpack_from('<2f', awr, off + i * 52 + 8)
        cells.setdefault((int(x // CELL_UNITS), int(y // CELL_UNITS)), []).append(name)
    return cells


def terrain_cells(awr):
    """Exterior cells with open-world terrain (see terrain_regions)."""
    return set(terrain_regions(awr))


def exterior_xy(key):
    """'exterior:x,y' -> (x, y); None for interiors."""
    if not key.startswith('exterior:'):
        return None
    x, y = key[len('exterior:'):].split(',')
    return int(x), int(y)


def build(entities, places=None, checked=None, terrain=frozenset()):
    """terrain: cells with topomap terrain, or {cell: [open-world map names]}."""
    cells = {}

    def cell(xy):
        return cells.setdefault(xy, {'x': xy[0], 'y': xy[1], 'map': 'none', 'placed': 0, 'original': 0,
                                     'places': 0, 'interiors': 0, 'interiors_converted': 0, 'checked': False,
                                     'maps': []})
    for xy in terrain:
        c = cell(xy)
        c['map'] = 'terrain'
        if isinstance(terrain, dict):
            c['maps'] += terrain[xy]
    for name, keys in entities.get('map_cells', {}).items():
        for xy in {exterior_xy(k) for k in keys} - {None}:
            if name not in cell(xy)['maps']:
                cell(xy)['maps'].append(name)
    for key, cats in entities['cells'].items():
        xy = exterior_xy(key)
        if xy is None:
            continue
        c = cell(xy)
        c['original'] = sum(v[0] for v in cats.values())
        c['placed'] = sum(v[1] for v in cats.values())
    for xy in {exterior_xy(k) for k in entities.get('full_cells', [])} - {None}:
        cell(xy)['map'] = 'full'
    if places:
        by_name = {p['name']: p for p in places if p['kind'] != 'exterior place'}
        for p in places:
            if p['kind'] == 'exterior place':
                for xy in {tuple(g) for g in p['grids']}:
                    cell(xy)['places'] += 1
                continue
            root = by_name.get(p.get('reached_through') or p['name'], p)
            for xy in {tuple(e['grid']) for e in root.get('entrances') or []}:
                c = cell(xy)
                c['interiors'] += 1
                c['interiors_converted'] += bool(p.get('converted'))
    for xy in (checked or {}).get('cells', []):
        cell(tuple(xy))['checked'] = True
    rows = [cells[k] for k in sorted(cells)]
    for r in rows:  # town/area maps first, then open-world regions
        r['maps'].sort(key=lambda m: (bool(WORLD_MAP_NAME.match(m)), m))
    xs, ys = [r['x'] for r in rows], [r['y'] for r in rows]
    return {'format': FORMAT, 'master_sha256': entities.get('master_sha256'),
            'bounds': [min(xs), min(ys), max(xs), max(ys)] if rows else None,
            'summary': {'cells': len(rows), 'terrain': sum(r['map'] != 'none' for r in rows),
                        'full': sum(r['map'] == 'full' for r in rows),
                        'checked': sum(r['checked'] for r in rows),
                        'placed': sum(r['placed'] for r in rows), 'original': sum(r['original'] for r in rows)},
            'cells': rows}


def build_step(out, regions_path, entities_path, master_path, checked_path):
    """Image build step: write world-progress.json beside entity-tracker.json.
    POI counts come from the master file in memory (no place names written)."""
    import hashlib
    from poi_checklist import build as poi_build, converted_cells
    places = poi_build(Path(master_path).read_bytes(), converted_cells(Path(__file__).resolve().parents[1]))
    checked = json.loads(Path(checked_path).read_text(encoding='utf-8')) if Path(checked_path).is_file() else None
    result = build(json.loads(Path(entities_path).read_text(encoding='utf-8')), places, checked,
                   terrain_regions(Path(regions_path).read_bytes()))
    path = Path(out) / 'world-progress.json'
    path.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    return dict(report=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), summary=result['summary'])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--regions', type=Path, required=True)
    p.add_argument('--entities', type=Path, required=True)
    p.add_argument('--poi', type=Path)
    p.add_argument('--checked', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    load = lambda path: json.loads(path.read_text(encoding='utf-8')) if path else None
    result = build(load(a.entities), load(a.poi), load(a.checked), terrain_regions(a.regions.read_bytes()))
    a.out.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    s = result['summary']
    print('World progress: %d cells, %d with topomap terrain, %d full maps, %d checked; entities %d / %d placed'
          % (s['cells'], s['terrain'], s['full'], s['checked'], s['placed'], s['original']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
