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


# ---------------------------------------------------------------------------------------------------------------
# The store-once chart (owner, 2026-10-09: "what the hell is this chart trying to tell?"): the title is the takeaway,
# computed from the data; two panels with big text and every legend outside the plot; the no-reuse line is on a log scale
# so it fits; ring labels are staggered above the plot.

ORDER_SENTENCE = ('Spiral order grows one contiguous playable area from the coast inwards. Risk order meets the most distinct '
                  'meshes first, so a bug in a mesh shows up early.')


def reuse_takeaway(unique, without):
    """(title, ratio) in plain words: store-once conversions against every cell converting its own meshes."""
    if not unique or not without:
        return 'Store-once mesh reuse: no mesh counts yet', None
    ratio = without / float(unique)
    shown = ('%.0fx' % ratio) if ratio >= 10 else ('%.1fx' % ratio)
    return 'Store-once: {:,} mesh conversions instead of {:,} ({} fewer)'.format(unique, without, shown), ratio


def _font(size, bold=False):
    from PIL import ImageFont
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


def _wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def draw_reuse_chart(path, spiral, risk, unique, without, rings=(), cells_with_meshes=None, size=(1500, 1520)):
    """Write the store-once chart as a PNG. spiral / risk: reuse_curve points [cells_done, cumulative_unique, cumulative_own];
    rings: [(cells_done, label)] for the staggered labels above panel (a). Fonts: 20-24 px text, 34 px title."""
    from PIL import Image, ImageDraw
    W, H = size
    bg, ink, muted, grid = '#101923', '#edf3fa', '#b6c7d8', '#2a3b4d'
    c_store, c_risk, c_own = '#4fc3f7', '#ffcf55', '#ff7b72'
    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img)
    f_title, f_panel, f_text, f_tick, f_small = _font(34, True), _font(24, True), _font(22), _font(20), _font(18)
    L, R = 150, 230
    xmax = max([pt[0] for pt in list(spiral) + list(risk)] or [1])

    def X(v):
        return L + (W - L - R) * v / float(xmax)

    title, _ = reuse_takeaway(unique, without)
    d.text((L, 22), title, fill=ink, font=f_title)
    d.text((L, 70), '%s cells with placements; every mesh is converted once and placed by reference' % '{:,}'.format(cells_with_meshes or xmax),
           fill=muted, font=f_text)

    def side_label(top, bottom):
        width = int(d.textlength('meshes converted', font=f_text)) + 8
        tmp = Image.new('RGB', (width, 34), bg)
        ImageDraw.Draw(tmp).text((4, 4), 'meshes converted', fill=ink, font=f_text)
        tmp = tmp.rotate(90, expand=True)
        img.paste(tmp, (14, int((top + bottom) / 2.0 - width / 2.0)))

    def x_axis(bottom, label_y):
        for i in range(6):
            xv = xmax * i / 5.0
            d.text((X(xv), bottom + 8), '{:,}'.format(int(xv)), fill=muted, font=f_tick, anchor='ma')
        d.text((L + (W - L - R) / 2.0, label_y), 'cells converted (in sweep order)', fill=ink, font=f_text, anchor='ma')

    def legend(items, top):
        y = top
        for label, colour, dashed in items:
            if dashed:
                for k in range(0, 44, 14):
                    d.line([(L + k, y + 13), (L + k + 8, y + 13)], fill=colour, width=6)
            else:
                d.line([(L, y + 13), (L + 44, y + 13)], fill=colour, width=6)
            d.text((L + 62, y), label, fill=ink, font=f_text)
            y += 36
        return y

    # (a) log scale: with and without store-once
    ax_t, ax_b = 215, 565
    d.text((L, 124), '(a) Meshes converted so far: store-once against every cell converting its own meshes (log scale)', fill=ink, font=f_panel)
    top = max(without, unique, 10)
    import math
    decades = int(math.ceil(math.log10(top)))

    def Ya(v):
        return ax_b - (ax_b - ax_t) * math.log10(max(v, 1)) / float(decades)
    for k in range(decades + 1):
        v = 10 ** k
        d.line([(L, Ya(v)), (W - R, Ya(v))], fill=grid, width=1)
        d.text((L - 12, Ya(v)), '{:,}'.format(v), fill=muted, font=f_tick, anchor='rm')
    d.line([(L, ax_t), (L, ax_b), (W - R, ax_b)], fill=muted, width=2)
    side_label(ax_t, ax_b)
    for i, (x, label) in enumerate(rings):                      # staggered over two rows above the plot
        d.line([(X(x), ax_t - (8 if i % 2 else 30)), (X(x), ax_t)], fill='#6f8aa6', width=1)
        d.text((X(x) + 3, ax_t - (32 if i % 2 == 0 else 10)), label, fill=muted, font=f_small, anchor='ls' if False else 'lb')
    own = [(pt[0], pt[2]) for pt in spiral]
    store = [(pt[0], pt[1]) for pt in spiral]
    for pts, colour in ((own, c_own), (store, c_store)):
        if pts:
            d.line([(X(a), Ya(b)) for a, b in pts], fill=colour, width=5)
    for pts, colour in ((own, c_own), (store, c_store)):
        if pts:
            d.text((W - R + 14, Ya(pts[-1][1])), '{:,}'.format(int(pts[-1][1])), fill=colour, font=f_panel, anchor='lm')
    x_axis(ax_b, ax_b + 44)
    end = legend([('Every cell converts its own meshes (no reuse)', c_own, False),
                  ('Store-once: each mesh converted one time, placed by reference', c_store, False)], ax_b + 92)

    # (b) the two sweep orders, linear
    bx_t = end + 100
    bx_b = bx_t + 330
    d.text((L, end + 36), '(b) Two sweep orders: distinct meshes met so far', fill=ink, font=f_panel)
    ymax = max([pt[1] for pt in list(spiral) + list(risk)] or [1]) * 1.06

    def Yb(v):
        return bx_b - (bx_b - bx_t) * v / ymax
    for i in range(5):
        v = ymax * i / 4.0
        d.line([(L, Yb(v)), (W - R, Yb(v))], fill=grid, width=1)
        d.text((L - 12, Yb(v)), '{:,}'.format(int(v)), fill=muted, font=f_tick, anchor='rm')
    d.line([(L, bx_t), (L, bx_b), (W - R, bx_b)], fill=muted, width=2)
    side_label(bx_t, bx_b)
    for pts, colour in ((spiral, c_store), (risk, c_risk)):
        if pts:
            d.line([(X(pt[0]), Yb(pt[1])) for pt in pts], fill=colour, width=5)
    if spiral:
        d.text((W - R + 14, Yb(spiral[-1][1])), '{:,}'.format(int(spiral[-1][1])), fill=c_store, font=f_panel, anchor='lm')
    x_axis(bx_b, bx_b + 44)
    end = legend([('Spiral order: coast inwards, one contiguous area', c_store, False),
                  ('Risk order: riskiest cells first (cells with estimates)', c_risk, False)], bx_b + 92)
    y = end + 14
    for line in _wrap(d, ORDER_SENTENCE, f_text, W - 2 * L):
        d.text((L, y), line, fill=muted, font=f_text)
        y += 30
    img = img.crop((0, 0, W, min(H, y + 24)))
    img.save(path, 'PNG', optimize=True)
