# SPDX-License-Identifier: GPL-3.0-only
"""The visible part of every lava pool, for the world map's LAVA layer (WORLDMAP-LAVA-MISMATCH-36).

A Morrowind lava pool is a flat tile (in_lava_1024 and kin) laid into the land at a fixed height. Where the land
rises above the tile the pool is buried and the player sees ground, not lava (the owner stood on grass inside a
mapped pool in Molag Amur: the land there is about 270 units, the pool surface 256). The footprint of a pool is
therefore the pool's plan outline *where the land lies below the pool surface*, not the outline itself.

This module reads the land heights of the master (LAND/VHGT, 65x65 vertices 128 units apart, bilinear between
them) and gives:

- visible_rects(pool, land, step): the visible part of one pool as axis-aligned rectangles on a step-unit grid
  (a square counts when its centre has land below the pool surface and all four corners lie in the pool's
  footprint; vertically equal runs are merged), none when the pool is completely buried;
- rows_for(pools, land): LAVA section rows (tools/prepare_world_ui format) for every pool, the grid coarsened
  (64, 128, 256 units) only when the rows would not fit the engine's pool limit;
- audit(rows, pools, land): the independent check of the layer against the real footprints (a finer 16-unit
  sampling): painted area where the land is above the pool, visible lava left unpainted, the largest land excess
  under a painted point, per pool and TOTALS; raises ValueError when a pool leaves its tolerance.

Nothing derived from your game files is part of this repository.
"""
import math
import struct

GRID = 64                  # Morrowind units: the rectangle grid of the layer (the land vertices are 128 apart)
GRIDS = (64, 128, 256)     # coarser grids tried when the rows exceed the engine's pool limit
AUDIT_STEP = 16            # Morrowind units: sampling of the audit
HULL_TOLERANCE = 1.0       # units: a rectangle corner may lie this far outside the pool's footprint
OVERPAINT_MAX = 0.12       # painted area on buried land, share of the pool's footprint area (audit tolerance)
MISSED_MAX = 0.20          # visible lava left unpainted, share of the pool's footprint area (audit tolerance)
EXCESS_MAX = 96.0          # units: land may rise this far above the pool surface under a painted audit sample
CELL = 8192
HEIGHT_FORMAT = 'aw-lava-map-1'


def land_heights(master):
    """{(cell x, cell y): 65x65 heights [y][x]} of every LAND record with heights in the master bytes."""
    from mwad.audit import decode_heights, records, subrecords
    out = {}
    for tag, flags, payload in records(master):
        if tag != 'LAND' or flags & 0x20:
            continue
        s = {}
        for k, v in subrecords(payload):
            s.setdefault(k, v)
        if 'VHGT' in s and 'DELE' not in s and len(s.get('INTV', b'')) == 8:
            out[struct.unpack('<ii', s['INTV'])] = decode_heights(s['VHGT'])
    return out


def land_height(land, x, y):
    """Bilinear land height at world (x, y); None where the master has no land for the cell."""
    cx, cy = math.floor(x / CELL), math.floor(y / CELL)
    grid = land.get((cx, cy))
    if grid is None:
        return None
    fx, fy = (x - cx * CELL) / 128.0, (y - cy * CELL) / 128.0
    ix, iy = min(int(fx), 63), min(int(fy), 63)
    ax, ay = fx - ix, fy - iy
    return (grid[iy][ix] * (1 - ax) * (1 - ay) + grid[iy][ix + 1] * ax * (1 - ay)
            + grid[iy + 1][ix] * (1 - ax) * ay + grid[iy + 1][ix + 1] * ax * ay)


def buried(land, x, y, top):
    """True when the land at (x, y) is at or above the pool surface; unknown land counts as not buried."""
    z = land_height(land, x, y)
    return z is not None and top is not None and z >= top


def _hull_contains(hull, x, y, tolerance):
    if len(hull) < 3:
        return bool(hull) and all(abs(p - q) <= tolerance for p, q in zip((x, y), hull[0]))
    for i, a in enumerate(hull):
        b = hull[(i + 1) % len(hull)]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length and ((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / length < -tolerance:
            return False
    return True


def _bounds(hull):
    xs, ys = [p[0] for p in hull], [p[1] for p in hull]
    return min(xs), min(ys), max(xs), max(ys)


def _mostly_visible(land, ax, ay, bx, by, top):
    """A grid square is lava when at least half of its 4x4 sample points lie on land below the pool surface."""
    seen = 0
    for u in range(4):
        for v in range(4):
            seen += not buried(land, ax + (u + .5) * (bx - ax) / 4, ay + (v + .5) * (by - ay) / 4, top)
    return seen >= 8


def _axis_rect(hull):
    x0, y0, x1, y1 = _bounds(hull)
    return abs(_area(hull) - (x1 - x0) * (y1 - y0)) <= 0.005 * max(_area(hull), 1.0)


def visible_rects(pool, land, step=GRID):
    """The visible lava of one pool: [[x0, y0, x1, y1]] integer rectangles in world units (see the module text).
    A pool whose outline is not an axis-aligned rectangle (ovals, turned tiles) uses a grid half as coarse."""
    hull = pool.get('hull') or []
    top = pool.get('top')       # no surface height: nothing is buried
    if len(hull) < 3:
        return []
    x0, y0, x1, y1 = _bounds(hull)
    step = min(step, max(16, 1 << int(math.log2(max(min(x1 - x0, y1 - y0) / 8, 16)))))     # small pools: 8 squares across
    if not _axis_rect(hull):
        step = max(step // 2, 16)
    nx, ny = max(1, math.ceil((x1 - x0) / step - 1e-9)), max(1, math.ceil((y1 - y0) / step - 1e-9))
    out, prev = [], {}
    for j in range(ny):
        cur = {}
        row = []
        for i in range(nx):
            ax, bx = x0 + i * step, min(x0 + (i + 1) * step, x1)
            ay, by = y0 + j * step, min(y0 + (j + 1) * step, y1)
            ok = (_mostly_visible(land, ax, ay, bx, by, top)
                  and all(_hull_contains(hull, x, y, HULL_TOLERANCE) for x in (ax, bx) for y in (ay, by)))
            row.append(ok)
        i = 0
        while i < nx:
            if row[i]:
                k = i
                while k + 1 < nx and row[k + 1]:
                    k += 1
                cur[(i, k)] = prev.pop((i, k), j)
                i = k + 1
            else:
                i += 1
        for (i0, i1), start in prev.items():
            out.append((i0, i1, start, j))
        prev = cur
    for (i0, i1), start in prev.items():
        out.append((i0, i1, start, ny))
    rects = []
    for i0, i1, j0, j1 in out:
        r = [int(round(x0 + i0 * step)), int(round(y0 + j0 * step)),
             int(round(min(x0 + (i1 + 1) * step, x1))), int(round(min(y0 + j1 * step, y1)))]
        if r[2] > r[0] and r[3] > r[1]:
            rects.append(r)
    return rects


def rows_for(pools, land, max_rows=2048):
    """(rows, step): one LAVA row per visible rectangle, {cell, points, bounds, pool}, in pool order. The grid is
    coarsened only when the rows would exceed max_rows. Fully buried pools have no row."""
    for step in GRIDS:
        rows = []
        for index, pool in enumerate(pools):
            if len(pool.get('hull') or []) < 3:      # known only by its position: one mark, unless land buries it
                pos = pool.get('position')
                if pos and not buried(land, pos[0], pos[1], pool.get('top', pos[2] if len(pos) > 2 else None)):
                    rows.append({'cell': [int(pool['cell'][0]), int(pool['cell'][1])],
                                 'points': [[int(round(pos[0])), int(round(pos[1]))]],
                                 'bounds': [int(round(pos[0])), int(round(pos[1]))] * 2, 'pool': index})
                continue
            for r in visible_rects(pool, land, step):
                rows.append({'cell': [int(pool['cell'][0]), int(pool['cell'][1])],
                             'points': [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]],
                             'bounds': list(r), 'pool': index})
        if len(rows) <= max_rows:
            return rows, step
    raise ValueError('Too many visible lava rectangles for the world map: %d' % len(rows))


def _area(hull):
    return abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1] - hull[(i + 1) % len(hull)][0] * hull[i][1]
                   for i in range(len(hull)))) / 2


def audit(rows, pools, land, step=AUDIT_STEP):
    """Check the layer against the real footprints with a step-unit sampling of every pool: returns
    {'pools': [per pool report], 'totals': {...}} and raises ValueError naming the first pool beyond tolerance.
    Per pool: footprint area, visible area (land below the surface), painted area, overpaint (painted on buried
    land), missed (visible, not painted), max_excess (largest land height above the surface under a painted
    sample, units); all areas in square units."""
    by_pool = {}
    for r in rows:
        by_pool.setdefault(r['pool'], []).append(r['bounds'])
    reports, bad = [], None
    for index, pool in enumerate(pools):
        hull = pool.get('hull') or []
        top, rects = pool.get('top'), by_pool.get(index, [])
        rep = {'pool': index, 'cell': list(pool['cell']), 'model': pool.get('model', ''), 'rects': len(rects),
               'footprint': round(_area(hull)) if len(hull) >= 3 else 0, 'visible': 0, 'painted': 0,
               'overpaint': 0, 'missed': 0, 'max_excess': 0.0}
        if len(hull) >= 3:
            x0, y0, x1, y1 = _bounds(hull)
            nx, ny = max(1, math.ceil((x1 - x0) / step)), max(1, math.ceil((y1 - y0) / step))
            cell = step * step
            for j in range(ny):
                for i in range(nx):
                    x, y = x0 + (i + .5) * step, y0 + (j + .5) * step
                    if not _hull_contains(hull, x, y, 0.0):
                        continue
                    z = land_height(land, x, y)
                    visible = z is None or top is None or z < top
                    painted = any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in rects)
                    rep['visible'] += cell * visible
                    rep['painted'] += cell * painted
                    if painted and not visible:
                        rep['overpaint'] += cell
                    if painted and z is not None and top is not None:
                        rep['max_excess'] = max(rep['max_excess'], z - top)
                    if visible and not painted:
                        rep['missed'] += cell
        rep['max_excess'] = round(max(rep['max_excess'], 0.0), 1)
        foot = max(rep['footprint'], 1)
        rep['overpaint_share'] = round(rep['overpaint'] / foot, 4)
        rep['missed_share'] = round(rep['missed'] / foot, 4)
        reports.append(rep)
        if bad is None and (rep['overpaint_share'] > OVERPAINT_MAX or rep['missed_share'] > MISSED_MAX
                            or rep['max_excess'] > EXCESS_MAX):
            bad = rep
    totals = {k: sum(r[k] for r in reports) for k in ('rects', 'footprint', 'visible', 'painted', 'overpaint', 'missed')}
    totals.update(pools=len(reports), buried=sum(1 for r in reports if not r['rects']),
                  max_excess=max([r['max_excess'] for r in reports] or [0.0]),
                  max_overpaint_share=max([r['overpaint_share'] for r in reports] or [0.0]),
                  max_missed_share=max([r['missed_share'] for r in reports] or [0.0]))
    if bad is not None:
        raise ValueError('Lava layer disagrees with the land in cell %r (pool %d: overpaint %.1f%%, missed %.1f%%, '
                         'land %.0f units above the surface)' % (tuple(bad['cell']), bad['pool'],
                                                                 100 * bad['overpaint_share'],
                                                                 100 * bad['missed_share'], bad['max_excess']))
    return {'format': HEIGHT_FORMAT, 'pools': reports, 'totals': totals}


def main(argv=None):
    """python3 tools/lava_map.py --data-files DIR [--json FILE]: the audit of the real layer, per cell and TOTALS."""
    import argparse
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))      # src first: tools/mwad.py is a script
    from lava import exterior_pools
    from mwad.paths import child_ci
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument('--data-files', required=True)
    ap.add_argument('--json', help='write the full per-pool report here')
    args = ap.parse_args(argv)
    land = land_heights(child_ci(Path(args.data_files), 'Morrowind.esm').read_bytes())
    pools = exterior_pools(args.data_files)
    rows, step = rows_for(pools, land)
    report = audit(rows, pools, land)
    cells = {}
    for rep in report['pools']:
        c = cells.setdefault(tuple(rep['cell']), {'pools': 0, 'buried': 0, 'rects': 0, 'footprint': 0, 'visible': 0,
                                                  'overpaint': 0, 'missed': 0, 'max_excess': 0.0})
        c['pools'] += 1
        c['buried'] += not rep['rects']
        for k in ('rects', 'footprint', 'visible', 'overpaint', 'missed'):
            c[k] += rep[k]
        c['max_excess'] = max(c['max_excess'], rep['max_excess'])
    print('cell      pools buried rects  footprint  visible  overpaint  missed  max land excess')
    for key in sorted(cells):
        c = cells[key]
        print('%-9s %5d %6d %5d %10d %8d %10d %7d %10.1f' % ('%d,%d' % key, c['pools'], c['buried'], c['rects'],
              c['footprint'], c['visible'], c['overpaint'], c['missed'], c['max_excess']))
    t = report['totals']
    print('TOTALS    %5d %6d %5d %10d %8d %10d %7d %10.1f   (grid %d units)' % (
        t['pools'], t['buried'], t['rects'], t['footprint'], t['visible'], t['overpaint'], t['missed'], t['max_excess'], step))
    if args.json:
        with open(args.json, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(report, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
