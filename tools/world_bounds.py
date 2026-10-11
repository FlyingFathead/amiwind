# SPDX-License-Identifier: GPL-3.0-only
"""World bounds: the edge of the built open world and the sea current that keeps the player inside it.

An AmiWind extension: the original game has no barrier (its open sea goes on). AmiWind's open world ends
896 units past the outermost cells (the overlap of the open-world maps), where an invisible wall used to
stop the player. With world bounds on (the builder default, --world-bounds on|off; the game's cvar
aw_world_bounds, `dbg worldbounds`), the water near that edge carries a current along the edge, like the
sea at the edge of some open-world games: swimming out, the player is turned aside and drifts along the
coast, and slowly back in; walking, jumping or flying out (no current out of the water), the outward motion
fades to nothing before the wall. Nobody is ever held: every push points back into the world.

The cell set is a lookup table, never a guess: the engine reads it from the image's own open-world
directory (world/regions.awr: a cell is in the world when an open-world map's core lies in it), and this
tool reads the same table (or a CHIM progress tracker file: cells with open-world maps, else the cells with
LAND) to report the box, the edge ring by cell kind and each edge's drift direction. The field below is the
reference of the engine's own (engine/aga/src/aw_bounds.c, the same numbers, test-checked).

Quake mechanism: Quake's water currents (CONTENTS_CURRENT_0..DOWN, a 150 units/s push scaled by depth,
sv_phys.c SV_CheckWater) are leaf contents baked by qbsp; the qbsp we ship does not write them, the push is
compiled only in Quake 2 builds (#ifdef QUAKE2) and every outer map would need its own copy. So the same
push is applied by position from the cell table, in the server's player physics (docs/WORLD_BOUNDS.md).

Commands:
  world_bounds.py report (--regions world/regions.awr | --progress cell-progress.json) [--json OUT]
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

FORMAT = 'aw-world-bounds-1'
CELL = 2048            # map units per exterior cell (8192 Morrowind units x 0.25)
OVERLAP = 896          # an open-world map reaches this far past its core (tools/prepare_world_regions.py)
PRE = 128              # the field starts this far inside the last cell
FULL = 640             # outward motion fully cancelled from here (past the cell edge)
HARD = 768             # past this the inward push is four times as strong (the wall is at OVERLAP - 16)
CURRENT = 150.0        # Quake's current: 150 units/s at full depth (waterlevel 3)
INWARD = 48.0          # back towards the world, units/s at full ramp
SIDES = ((1, 0, 'east'), (0, 1, 'north'), (-1, 0, 'west'), (0, -1, 'south'))
NEIGHBOURS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
FAR = HARD + 1.0       # a point with no world cell among its neighbours (teleports, debug flight)


def cell_of(x, y):
    return (math.floor(x / CELL), math.floor(y / CELL))


# ---------------------------------------------------------------- lookup tables

def cells_from_directory(raw):
    """{cell} of an image's open-world directory (world/regions.awr, AWR2): the cell each map's core lies
    in (the centre of its core, origin + core box, in map units). The engine builds the same table."""
    if len(raw) < 64 or raw[:4] != b'AWR2':
        raise ValueError('Not an open-world directory (AWR2)')
    count = struct.unpack_from('<I', raw, 4)[0]
    if len(raw) != 64 + 52 * count:
        raise ValueError('Open-world directory length does not match its row count')
    out = set()
    for i in range(count):
        ox, oy, _ = struct.unpack_from('<3f', raw, 64 + 52 * i + 8)
        x0, y0, x1, y1 = struct.unpack_from('<4f', raw, 64 + 52 * i + 20)
        out.add(cell_of(ox + (x0 + x1) / 2, oy + (y0 + y1) / 2))
    return out


def cells_from_progress(path, island='vvardenfell'):
    """({cell: kind}, source): the cells of the built open world from a CHIM progress tracker file. Cells
    with open-world maps (legacy maps) when the file records them, else the cells with LAND. Kind: 'land',
    'seabed' (LAND, nothing placed: empty sea) or 'open sea' (no LAND record), as tools/chim/regions.py
    names them."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from chim.regions import load_status
    status = {c: v for c, v in load_status(path).items() if v['set'] == island}
    mapped = {c: v for c, v in status.items() if v['legacy_maps']}
    chosen, source = (mapped, 'open-world maps') if mapped else \
        ({c: v for c, v in status.items() if v['status'] not in ('ocean', None)}, 'LAND cells')
    return {c: kind_of(v['status']) for c, v in chosen.items()}, source


def kind_of(status):
    if status == 'ocean':
        return 'open sea'
    if status == 'empty_sea':
        return 'seabed'
    return 'land'


# ---------------------------------------------------------------- the edge

def box(cells):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs), max(ys)


def ring(cells):
    """{cell: [side, ...]}: the world cells with an open side (no world cell beyond it), with the side
    names; plus the cells open only at a corner (diagonal), side list ['corner']."""
    out = {}
    for c in cells:
        sides = [name for dx, dy, name in SIDES if (c[0] + dx, c[1] + dy) not in cells]
        if not sides and any((c[0] + dx, c[1] + dy) not in cells for dx, dy in NEIGHBOURS):
            sides = ['corner']
        if sides:
            out[c] = sides
    return out


def drift_of(sides):
    """(outward normal, along-edge drift) of an edge cell's open sides: the normal is the sum of the open
    sides' normals, the drift that normal turned a quarter left (anticlockwise round the island)."""
    nx = sum(dx for dx, dy, name in SIDES if name in sides)
    ny = sum(dy for dx, dy, name in SIDES if name in sides)
    length = math.hypot(nx, ny)
    if not length:
        return None
    nx, ny = nx / length, ny / length
    return (nx, ny), (-ny, nx)


def enclosed_holes(cells):
    """Cells inside the box that are not world cells and cannot be reached from outside the box: pockets
    the open-world maps leave out (each one an invisible wall in the middle of the world)."""
    x0, y0, x1, y1 = box(cells)
    outside = set()
    pending = [(x, y) for x in range(x0 - 1, x1 + 2) for y in (y0 - 1, y1 + 1)] + \
              [(x, y) for y in range(y0 - 1, y1 + 2) for x in (x0 - 1, x1 + 1)]
    while pending:
        c = pending.pop()
        if c in outside or c in cells or not (x0 - 1 <= c[0] <= x1 + 1 and y0 - 1 <= c[1] <= y1 + 1):
            continue
        outside.add(c)
        pending.extend((c[0] + dx, c[1] + dy) for dx, dy, _ in SIDES)
    return sorted((x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
                  if (x, y) not in cells and (x, y) not in outside)


# ---------------------------------------------------------------- the field (engine reference)

def _nearest(px, py, cell):
    """Nearest point of a cell's square to (px, py) and its distance."""
    lo_x, lo_y = cell[0] * CELL, cell[1] * CELL
    qx = min(max(px, lo_x), lo_x + CELL)
    qy = min(max(py, lo_y), lo_y + CELL)
    return qx, qy, math.hypot(px - qx, py - qy)


def field(cells, x, y):
    """(depth, (nx, ny)) at a map-unit point, or None where the bounds do nothing. depth: signed distance
    past the edge of the world (negative inside the last cell, down to -PRE); (nx, ny): outward unit
    normal. Same rule as AW_BoundsField in aw_bounds.c."""
    c = cell_of(x, y)
    best = None
    if c in cells:
        for dx, dy in NEIGHBOURS:
            other = (c[0] + dx, c[1] + dy)
            if other in cells:
                continue
            qx, qy, d = _nearest(x, y, other)
            if best is None or d < best[0]:
                best = (d, qx - x, qy - y, dx, dy)
        if best is None or best[0] >= PRE:
            return None
        d, vx, vy, dx, dy = best
        if d > 1e-3:
            return -d, (vx / d, vy / d)
        length = math.hypot(dx, dy)
        return 0.0, (dx / length, dy / length)
    for dx, dy in NEIGHBOURS:
        other = (c[0] + dx, c[1] + dy)
        if other not in cells:
            continue
        qx, qy, d = _nearest(x, y, other)
        if best is None or d < best[0]:
            best = (d, x - qx, y - qy, -dx, -dy)
    if best is None:
        x0, y0, x1, y1 = box(cells)
        vx, vy = x - (x0 + x1 + 1) * CELL / 2, y - (y0 + y1 + 1) * CELL / 2
        length = math.hypot(vx, vy) or 1.0
        return FAR, (vx / length, vy / length)
    d, vx, vy, dx, dy = best
    if d > 1e-3:
        return d, (vx / d, vy / d)
    length = math.hypot(dx, dy)
    return 0.0, (dx / length, dy / length)


def ramp(depth):
    return min(1.0, max(0.0, (depth + PRE) / (FULL + PRE)))


def push(cells, x, y, vx, vy, waterlevel):
    """((vx, vy) after the outward motion is faded, (drift x, drift y)) at a point: the player physics'
    step, AW_BoundsApply in aw_bounds.c. The drift is added for the move only (Quake's basevelocity)."""
    f = field(cells, x, y)
    if f is None:
        return (vx, vy), (0.0, 0.0)
    depth, (nx, ny) = f
    r = ramp(depth)
    out = vx * nx + vy * ny
    if out > 0:
        vx, vy = vx - nx * out * r, vy - ny * out * r
    inward = INWARD * r * (4 if depth > HARD else 1)
    along = CURRENT * r * min(max(waterlevel, 0), 3) / 3.0
    return (vx, vy), (-nx * inward - ny * along, -ny * inward + nx * along)


# ---------------------------------------------------------------- builder option

DEFAULT = 'on'          # owner decision 2026-10-10: world bounds on by default
OPTION = '--world-bounds'


def add_option(parser):
    parser.add_argument(OPTION, choices=('on', 'off'), default=None,
                        help='The sea near the edge of the open world carries the player along it and back in '
                             '(an AmiWind extension: the original sea goes on; game cvar aw_world_bounds, '
                             '`dbg worldbounds`). Default: on. off: the game as before, no setting written. '
                             'docs/WORLD_BOUNDS.md')


def configure(args):
    """{'on', 'source'}: --world-bounds, resolved before any work (the builder's receipt keeps it)."""
    value = getattr(args, 'world_bounds', None)
    on = (value or DEFAULT) == 'on'
    return {'on': on, 'source': OPTION + ' ' + value if value else 'default'}


def image_arguments(record):
    """The image step's extra arguments: --world-bounds when on, nothing when off (an off build's image
    step and game settings are the same as before world bounds existed)."""
    return [OPTION] if record and record.get('on') else []


# ---------------------------------------------------------------- report

def report(cells, kinds=None, source=''):
    edge = ring(cells)
    kinds = kinds or {}
    by_kind, by_side = {}, {}
    for c, sides in edge.items():
        k = kinds.get(c, 'unknown')
        by_kind[k] = by_kind.get(k, 0) + 1
        for s in sides:
            by_side[s] = by_side.get(s, 0) + 1
    x0, y0, x1, y1 = box(cells)
    rows = []
    for c in sorted(edge):
        d = drift_of(edge[c])
        rows.append({'cell': list(c), 'kind': kinds.get(c, 'unknown'), 'open': edge[c],
                     'normal': [round(v, 4) for v in d[0]] if d else None,
                     'drift': [round(v, 4) for v in d[1]] if d else None})
    return {'format': FORMAT, 'source': source, 'cells': len(cells),
            'box': {'cells': [x0, y0, x1, y1], 'size': [x1 - x0 + 1, y1 - y0 + 1],
                    'map_units': [x0 * CELL - OVERLAP, y0 * CELL - OVERLAP,
                                  (x1 + 1) * CELL + OVERLAP, (y1 + 1) * CELL + OVERLAP]},
            'kinds': {k: sum(1 for c in cells if kinds.get(c, 'unknown') == k)
                      for k in sorted(set(kinds.get(c, 'unknown') for c in cells))},
            'ring': {'cells': len(edge), 'by_kind': dict(sorted(by_kind.items())),
                     'by_side': dict(sorted(by_side.items()))},
            'enclosed_holes': [list(c) for c in enclosed_holes(cells)],
            'field': {'pre': PRE, 'full': FULL, 'hard': HARD, 'overlap': OVERLAP, 'current': CURRENT,
                      'inward': INWARD},
            'edge': rows}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    r = sub.add_parser('report', help='the box, the edge ring by cell kind and the drift of each edge cell')
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument('--regions', type=Path, help="an image's world/regions.awr (what the engine reads)")
    src.add_argument('--progress', type=Path, help='a CHIM progress tracker file (cell-progress.json)')
    r.add_argument('--json', type=Path, help='write the full report (aw-world-bounds-1) here')
    args = ap.parse_args(argv)
    if args.regions:
        cells, kinds, source = cells_from_directory(args.regions.read_bytes()), None, 'open-world directory'
    else:
        kinds, source = cells_from_progress(args.progress)
        cells = set(kinds)
    out = report(cells, kinds, source)
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')
    b = out['box']
    print('World bounds (%s): %d cells, box %d,%d .. %d,%d (%d x %d cells)'
          % (source, out['cells'], *b['cells'], *b['size']))
    print('Edge ring: %d cells (%s); open sides %s; enclosed holes %d'
          % (out['ring']['cells'], ', '.join('%s %d' % kv for kv in out['ring']['by_kind'].items()),
             ', '.join('%s %d' % kv for kv in out['ring']['by_side'].items()), len(out['enclosed_holes'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
