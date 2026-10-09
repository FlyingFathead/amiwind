#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Sweep orders for the CHIM Progress Tracker: rings, the spiral, the risk (scout) list, the mesh reuse curve.

Pure functions on plain data (cells are (x, y) tuples); no game data in here.

  rings(land)             onion peel: ring 1 = land cells that touch non-land (8 neighbours), ring 2 the next
                          layer in, and so on. Computed per island, so a second island has its own rings.
  spiral(land, content)   one visiting order: per island (largest first) the sea-only cells that hold something and lie
                          nearest to it (ring 0), then its land ring by ring, outermost first. Inside a ring the walk always steps to
                          the nearest unvisited cell of the ring (clockwise on ties), starting next to where the
                          previous ring ended, so the converted area stays contiguous.
  risk_order(...)         riskiest first (score, then size).
  reuse_curve(order, meshes)
                          cumulative unique meshes along an order (store-once reuse curve), per ring and overall.
  draw_curve(...)         the curve as a PNG (Pillow).
"""
import math

NEIGHBOURS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def components(land):
    """Connected groups of land cells (8 neighbours), largest first; ties by lowest cell."""
    land = set(land)
    seen, out = set(), []
    for start in sorted(land):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx, dy in NEIGHBOURS:
                n = (x + dx, y + dy)
                if n in land and n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(sorted(comp))
    out.sort(key=lambda c: (-len(c), c[0]))
    return out


def rings(land):
    """{cell: ring number} (1 = coast) by peeling the land layer by layer."""
    remaining = set(land)
    out, k = {}, 1
    while remaining:
        layer = [c for c in remaining if any((c[0] + dx, c[1] + dy) not in remaining for dx, dy in NEIGHBOURS)]
        if not layer:   # cannot happen (a finite set always has a boundary); guard against a loop
            layer = list(remaining)
        for c in layer:
            out[c] = k
        remaining.difference_update(layer)
        k += 1
    return out


def _clockwise(cell, centre):
    """Angle of the cell around the centre, 0 at north, growing clockwise."""
    return math.atan2(cell[0] - centre[0], cell[1] - centre[1]) % (2 * math.pi)


def _walk(cells, start_near, centre):
    """Visit every cell of one ring: nearest unvisited first, clockwise on ties, begin next to start_near."""
    todo = sorted(cells)
    if not todo:
        return []
    if start_near is None:
        cur = min(todo, key=lambda c: (_clockwise(c, centre), c))
    else:
        cur = min(todo, key=lambda c: ((c[0] - start_near[0]) ** 2 + (c[1] - start_near[1]) ** 2, _clockwise(c, centre), c))
    order = [cur]
    todo.remove(cur)
    while todo:
        ang = _clockwise(cur, centre)
        here = cur
        cur = min(todo, key=lambda c: ((c[0] - here[0]) ** 2 + (c[1] - here[1]) ** 2,
                                       (_clockwise(c, centre) - ang) % (2 * math.pi), c))
        order.append(cur)
        todo.remove(cur)
    return order


def spiral(land, sea_content=(), groups=None):
    """-> list of (cell, ring, island): for each island (numbered from 1, largest first) the sea-only cells that hold
    something and are nearest to it (ring 0, walked nearest-first), then its land rings outside in. `groups` {cell: label}
    keeps land of different labels apart even where their cells touch on the grid (Solstheim shares the cell grid with
    Vvardenfell but is its own island)."""
    land = set(land)
    labels = {}
    for c in land:
        labels.setdefault((groups or {}).get(c, ''), set()).add(c)
    ring_of, comps = {}, []
    for label in sorted(labels):
        ring_of.update(rings(labels[label]))
        comps.extend(components(labels[label]))
    comps.sort(key=lambda c: (-len(c), c[0]))
    sea = sorted(set(sea_content) - land)
    owner = {}
    for c in sea:
        owner[c] = min(range(len(comps)), key=lambda i: (min(max(abs(c[0] - q[0]), abs(c[1] - q[1])) for q in comps[i]), i))             if comps else None
    out = []
    for i, comp in enumerate(comps):
        island = i + 1
        centre = (sum(c[0] for c in comp) / len(comp), sum(c[1] for c in comp) / len(comp))
        mine = [c for c in sea if owner[c] == i]
        last = None
        if mine:
            walked = _walk(mine, None, centre)
            out.extend((c, 0, island) for c in walked)
            last = walked[-1]
        by_ring = {}
        for c in comp:
            by_ring.setdefault(ring_of[c], []).append(c)
        for k in sorted(by_ring):
            walked = _walk(by_ring[k], last, centre)
            out.extend((c, k, island) for c in walked)
            last = walked[-1]
    out.extend((c, 0, 0) for c in sea if owner[c] is None)
    return out


def risk_order(cells, score, size):
    """Cells riskiest first: score descending, then size descending, then position."""
    return sorted(cells, key=lambda c: (-(score(c) or 0), -(size(c) or 0), c))


def reuse_curve(order, meshes, ring_of=None):
    """Store-once reuse along an order.

    order   list of cells; meshes {cell: set of mesh ids}; ring_of {cell: (island, ring)} (optional, for per-ring rows).
    Returns {points: [[cells_done, cumulative_unique, cumulative_if_every_cell_converted_its_own]],
             rings: [...], cells_without_new_mesh, total}.
    """
    seen, own_sum, points, per_ring, no_new = set(), 0, [], {}, 0
    for i, cell in enumerate(order, 1):
        ms = meshes.get(cell, set())
        new = ms - seen
        seen |= ms
        own_sum += len(ms)
        if ms and not new:
            no_new += 1
        points.append([i, len(seen), own_sum])
        if ring_of is not None:
            k = ring_of.get(cell, (0, 0))
            r = per_ring.setdefault(k, {'island': k[0], 'ring': k[1], 'cells': 0, 'cells_with_meshes': 0, 'new_meshes': 0, 'meshes_used': 0})
            r['cells'] += 1
            r['cells_with_meshes'] += 1 if ms else 0
            r['new_meshes'] += len(new)
            r['meshes_used'] += len(ms)
            r['cumulative_unique'] = len(seen)
            r['cumulative_cells'] = i
    rows = [per_ring[k] for k in sorted(per_ring)]
    for r in rows:
        r['new_share'] = round(r['new_meshes'] / r['meshes_used'], 4) if r['meshes_used'] else None
    return {'points': points, 'rings': rows, 'cells_without_new_mesh': no_new, 'total': len(seen)}


def thin(points, limit=400):
    """At most about `limit` points of a long curve, always keeping the first and the last."""
    if len(points) <= limit:
        return points
    step = len(points) / float(limit)
    keep = {int(i * step) for i in range(limit)} | {len(points) - 1}
    return [points[i] for i in sorted(keep)]


def draw_curve(path, series, title, ring_marks=(), size=(1000, 560)):
    """Write the reuse curve as a PNG. series: [(label, [[x, y, ...]], colour, y_index, clip)]; ring_marks: [(x, text)].
    The axis fits the series that are not clipped; a clipped series runs off the top and is labelled with its end value."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    L, R, T, B = 78, 24, 46, 64
    img = Image.new('RGB', (W, H), '#101923')
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    xmax = max([p[0] for _, pts, _, _, _ in series for p in pts] or [1])
    ymax = max([p[yi] for _, pts, _, yi, clip in series if not clip for p in pts] or [1])
    ymax = max(ymax * 1.06, 1)

    def X(v):
        return L + (W - L - R) * v / xmax

    def Y(v):
        return H - B - (H - T - B) * v / ymax
    d.text((L, 14), title, fill='#edf3fa', font=font)
    for i in range(6):
        yv = ymax * i / 5
        d.line([(L, Y(yv)), (W - R, Y(yv))], fill='#2a3b4d')
        d.text((8, Y(yv) - 5), '{:,}'.format(int(yv)), fill='#9fb3c8', font=font)
    for i in range(6):
        xv = xmax * i / 5
        d.text((X(xv) - 8, H - B + 8), '{:,}'.format(int(xv)), fill='#9fb3c8', font=font)
    d.text((L + (W - L - R) / 2 - 80, H - 24), 'cells converted (in sweep order)', fill='#9fb3c8', font=font)
    d.text((8, 28), 'unique meshes', fill='#9fb3c8', font=font)
    d.line([(L, T), (L, H - B), (W - R, H - B)], fill='#9fb3c8')
    for x, text in ring_marks:
        d.line([(X(x), T), (X(x), H - B)], fill='#243649')
        d.text((X(x) + 2, T + 2), text, fill='#6f8aa6', font=font)
    ly = T + 6
    for label, pts, colour, yi, clip in series:
        if pts:
            d.line([(X(p[0]), Y(min(p[yi], ymax))) for p in pts], fill=colour, width=2)
        if clip and pts:
            label += ' (off the chart: ends at {:,})'.format(int(pts[-1][yi]))
        d.rectangle([W - R - 380, ly, W - R - 368, ly + 8], fill=colour)
        d.text((W - R - 362, ly - 1), label, fill='#edf3fa', font=font)
        ly += 16
    img.save(path, 'PNG', optimize=True)
