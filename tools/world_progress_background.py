#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Local map layers for the world progress viewer, from your own Morrowind.esm.

- topo: each exterior cell's terrain heights (sea blue, land shaded from shore
  green to mountain grey) at N pixels per cell, north up, plus a sidecar JSON
  with the cell bounds.
- world: the game map menu's World level look, from each cell's low-resolution
  world-map terrain record (same frame as topo).
- cells: the Local level: a JSON with each cell's terrain and its original
  placements, shown when you click a cell (optionally marked placed or not).

Load the files into amiwind-toolkit/world-map.html with "Island (local)". They are
made from your game data: keep them on your machine, never commit or publish.

Usage:
  world_progress_background.py --esm Morrowind.esm --out island.png [--pixels 8]
  world_progress_background.py --esm Morrowind.esm --out island-world.png --style world
  world_progress_background.py --esm Morrowind.esm --out island-cells.json --style cells [--placed placed.json]
"""
import argparse, json, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import decode_heights, records, subrecords  # noqa: E402


def cell_heights(master):
    """{(x, y): 65x65 heights} for every LAND record with heights."""
    out = {}
    for tag, flags, payload in records(master):
        if tag != 'LAND' or flags & 0x20:
            continue
        s = dict(subrecords(payload))
        if 'VHGT' in s and 'DELE' not in s and len(s.get('INTV', b'')) == 8:
            out[struct.unpack('<ii', s['INTV'])] = decode_heights(s['VHGT'])
    return out


def world_heights(master):
    """{(x, y): 9x9 heights} from each LAND's low-resolution WNAM record: the data
    the game's own world map (map menu, World level) is drawn from."""
    out = {}
    for tag, flags, payload in records(master):
        if tag != 'LAND' or flags & 0x20:
            continue
        s = dict(subrecords(payload))
        if len(s.get('WNAM', b'')) == 81 and 'DELE' not in s and len(s.get('INTV', b'')) == 8:
            v = struct.unpack('<81b', s['WNAM'])
            out[struct.unpack('<ii', s['INTV'])] = [list(v[r * 9:r * 9 + 9]) for r in range(9)]
    return out


def cell_details(master, placed=None):
    """Local level (map menu, Local): per exterior cell 17x17 terrain heights and
    every original placement as [x, y, category, placed] with x, y in 0..255
    across the cell. PRIVATE: positions of the owner's game objects."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from entity_tracker import CATEGORIES, PLACEABLE, category
    from mwad.audit import cell_data
    bases, cells, names, regions = {}, {}, {}, {}
    for tag, flags, payload in records(master):
        if flags & 0x20:
            continue
        if tag == 'REGN':
            from mwad.audit import string
            f = dict(subrecords(payload))
            if 'NAME' in f and 'DELE' not in f:
                regions[string(f['NAME']).casefold()] = string(f.get('FNAM', f['NAME']))
            continue
        if tag in PLACEABLE:
            f = dict(subrecords(payload))
            if 'NAME' in f and 'DELE' not in f:
                from mwad.audit import string
                bases[string(f['NAME']).casefold()] = CATEGORIES.index(category(tag, string(f.get('MODL', b''))))
        elif tag == 'CELL':
            c = cell_data(list(subrecords(payload)))
            if not c['flags'] & 1:
                key = (c['x'], c['y'])
                names[key] = (c['name'], c['region'])
                rows = cells.setdefault(key, [])
                for r in c['refs']:
                    cat = bases.get(r['id'].casefold())
                    if r.get('deleted') or cat is None:
                        continue
                    gx = int((r['position'][0] / 8192 - c['x']) * 256)
                    gy = int((r['position'][1] / 8192 - c['y']) * 256)
                    rows.append([max(0, min(255, gx)), max(0, min(255, gy)), cat,
                                 None if placed is None else int(r['number'] in placed)])
    heights = cell_heights(master)
    out = {}
    for key in set(cells) | set(heights):
        grid = heights.get(key)
        name, region = names.get(key, ('', ''))
        out['%d,%d' % key] = {'name': name, 'region': regions.get(region.casefold(), region),
                              'h':[[round(grid[y][x]) for x in range(0, 65, 4)] for y in range(0, 65, 4)] if grid else None,
                              'refs': cells.get(key, [])}
    return {'format': 'AW-WORLD-CELLS1', 'categories': list(CATEGORIES), 'placed_known': placed is not None,
            'cells': out, 'pois': points_of_interest(master)}


def points_of_interest(master):
    """Named exterior places (label at the centre of their cells) and interior
    entrances (at the door), from the game data via tools/poi_checklist.py.
    Positions in cells: x, y as fractional cell coordinates."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from poi_checklist import build as poi_build, converted_cells
    out = []
    for p in poi_build(master, converted_cells(Path(__file__).resolve().parents[1])):
        if p['kind'] == 'exterior place':
            gx = sum(g[0] for g in p['grids']) / len(p['grids']) + .5
            gy = sum(g[1] for g in p['grids']) / len(p['grids']) + .5
            out.append({'name': p['name'], 'kind': 'place', 'x': round(gx, 3), 'y': round(gy, 3), 'converted': p['converted']})
            continue
        for e in p.get('entrances') or []:
            out.append({'name': p['name'], 'kind': p['kind'], 'x': round(e['position'][0] / 8192, 3),
                        'y': round(e['position'][1] / 8192, 3), 'converted': p['converted']})
    return out


def world_colour(v):
    """The game map menu's World level colouring of the WNAM value (-128..127):
    the original's dark map (deep sea 25,36,33, shallow sea 37,55,50, low land
    62,45,31 per UESP Tes3Mod:World_Map), via OpenMW 0.48's formula, which
    reproduces those values. No brightening: the original is dark."""
    y = v / 128.0
    if y < 0:
        r, g, b = 14 * y + 38, 20 * y + 56, 18 * y + 51
    elif y < 0.3:
        y = y * 8 if y < 0.1 else y - 0.1 + 0.8
        r, g, b = 66 - 32 * y, 48 - 23 * y, 33 - 16 * y
    else:
        y = (y - 0.3) * 1.428
        r, g, b = 34 - 29 * y, 25 - 20 * y, 17 - 12 * y
    return tuple(max(0, min(255, int(c))) for c in (r, g, b))


# Land ramp for Vvardenfell's measured heights (median 1400, Red Mountain 5500..17800):
# shore green, olive, brown, ash, then volcanic red at the summit. Same stops in the
# toolkit's Local view (amiwind-toolkit/world-map.html, topoColour).
# White is reserved for real snow (Solstheim, if added): never use it for height.
TERRAIN_STOPS = [(0, (92, 118, 74)), (1400, (122, 116, 78)), (3500, (120, 96, 70)), (6000, (104, 82, 70)), (10000, (100, 62, 50)), (15000, (118, 44, 32))]


def colour(h):
    if h <= 0:
        t = max(0.0, min(1.0, -h / 2048))
        return (int(70 - 40 * t), int(110 - 50 * t), int(150 - 40 * t))
    for (h0, c0), (h1, c1) in zip(TERRAIN_STOPS, TERRAIN_STOPS[1:]):
        if h <= h1:
            u = (h - h0) / (h1 - h0)
            return tuple(int(a + (b - a) * u) for a, b in zip(c0, c1))
    return TERRAIN_STOPS[-1][1]


def render(heights, pixels, paint=colour, sea=-1024, bounds=None):
    """Grid of N x N heights per cell (south row first) -> north-up image."""
    from PIL import Image
    if bounds is None:
        xs = [k[0] for k in heights]; ys = [k[1] for k in heights]
        bounds = [min(xs), min(ys), max(xs), max(ys)]
    w, h = (bounds[2] - bounds[0] + 1) * pixels, (bounds[3] - bounds[1] + 1) * pixels
    img = Image.new('RGB', (w, h), paint(sea))
    px = img.load()
    for (cx, cy), grid in heights.items():
        if not (bounds[0] <= cx <= bounds[2] and bounds[1] <= cy <= bounds[3]):
            continue
        n = len(grid) - 1
        ox, oy = (cx - bounds[0]) * pixels, (bounds[3] - cy) * pixels
        for j in range(pixels):
            row = grid[min(n, (pixels - 1 - j) * n // max(1, pixels - 1))]  # north up
            for i in range(pixels):
                px[ox + i, oy + j] = paint(row[min(n, i * n // max(1, pixels - 1))])
    return img, bounds


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--esm', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--pixels', type=int, default=8, choices=range(2, 33), metavar='2..32')
    p.add_argument('--style', choices=('topo', 'world', 'cells'), default='topo',
                   help='topo: full terrain heights; world: the game map menu\'s World level (low-resolution WNAM); '
                        'cells: the Local level, a JSON of per-cell terrain and placements (--out is the .json)')
    p.add_argument('--placed', type=Path, help='cells only: JSON list of placed reference numbers (fills the dots)')
    a = p.parse_args(argv)
    master = a.esm.read_bytes()
    if a.style == 'cells':
        placed = set(json.loads(a.placed.read_text(encoding='utf-8'))) if a.placed else None
        result = cell_details(master, placed)
        a.out.write_text(json.dumps(result, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
        print('cells %s: %d cells, %d placements' % (a.out, len(result['cells']),
                                                   sum(len(c['refs']) for c in result['cells'].values())))
        return 0
    topo = cell_heights(master)
    xs = [k[0] for k in topo]; ys = [k[1] for k in topo]
    bounds = [min(xs), min(ys), max(xs), max(ys)]  # same frame for both styles
    if a.style == 'world':
        img, bounds = render(world_heights(master), a.pixels, world_colour, -64, bounds)
    else:
        img, bounds = render(topo, a.pixels, colour, -1024, bounds)
    img.save(a.out)
    side = a.out.with_suffix('.json')
    side.write_text(json.dumps({'bounds': bounds, 'pixels_per_cell': a.pixels, 'style': a.style}) + '\n',
                    encoding='utf-8', newline='\n')
    print('island %s (%s) %dx%d, cells %s; bounds in %s' % (a.out, a.style, img.width, img.height, bounds, side))
    return 0


if __name__ == '__main__':
    sys.exit(main())
