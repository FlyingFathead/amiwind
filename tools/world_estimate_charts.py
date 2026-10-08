# SPDX-License-Identifier: GPL-3.0-only
"""SVG charts of a world estimate, in the tools/perf_charts.py style (plain
SVG, same ink, grid and status colours). Every mark carries a <title>
tooltip. Town labels come from the user's own data at run time."""
import math
from pathlib import Path
from xml.sax.saxutils import escape

from perf_charts import INK, MUTED, GRID, BG, HOT, MID, COOL, WORLD, MODELS, FONT, _svg as svg

SEQ = ['#e8f1fb', '#c6dcf4', '#9cc2eb', '#6ea4df', '#4387d2', '#2a6bb8', '#1d4f8c']   # one hue, light -> dark
SET_COLOURS = {'vvardenfell': WORLD, 'tribunal': MID, 'bloodmoon': COOL}


def text(x, y, s, size=12, colour=INK, anchor='start', weight='normal'):
    return '<text x="%g" y="%g" %s font-size="%d" fill="%s" text-anchor="%s" font-weight="%s">%s</text>\n' % (
        x, y, FONT, size, colour, anchor, weight, escape(str(s)))


def line(x1, y1, x2, y2, colour=GRID, width=1, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%g"%s/>\n' % (
        x1, y1, x2, y2, colour, width, d)


def fmt(v):
    return '{:,}'.format(int(round(v)))


def sorted_panel(x0, y0, w, h, values, limit, title, colour=WORLD):
    """Descending sorted curve of one metric over all maps, with the limit line."""
    vals = sorted((float(v) for v in values), reverse=True) or [0.0]
    top = max(vals[0], limit) * 1.08 or 1.0
    out = [text(x0, y0 - 10, title, 13, weight='bold')]
    for k in range(5):
        yv = top * k / 4
        yy = y0 + h - h * yv / top
        out.append(line(x0, yy, x0 + w, yy))
        out.append(text(x0 - 6, yy + 4, fmt(yv), 10, MUTED, 'end'))
    n = len(vals)
    step = max(1, n // w)
    pts = ['%.1f,%.1f' % (x0 + w * i / max(1, n - 1), y0 + h - h * min(vals[i], top) / top) for i in range(0, n, step)]
    pts.append('%.1f,%.1f' % (x0 + w, y0 + h - h * min(vals[-1], top) / top))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"><title>%s: sorted, %d maps</title>'
               '</polyline>\n' % (' '.join(pts), colour, escape(title), n))
    ly = y0 + h - h * limit / top
    over = sum(1 for v in vals if v > limit)
    out.append(line(x0, ly, x0 + w, ly, HOT, 1.5, '5,3'))
    out.append(text(x0 + w, ly - 5, 'limit %s: %s maps over' % (fmt(limit), fmt(over)), 11, HOT, 'end', 'bold'))
    out.append(line(x0, y0 + h, x0 + w, y0 + h, MUTED))
    out.append(text(x0, y0 + h + 14, 'maps, sorted by value (left = largest)', 10, MUTED))
    return ''.join(out)


def heap_chart(rows, limits):
    w, h = 900, 420
    x0, y0, pw, ph = 90, 70, 780, 280
    budget = limits['heap_budget']
    vals = sorted(((r['evr_heap'], r['space'], r['name']) for r in rows), reverse=True)
    top = max(22.0, math.ceil((vals[0][0] if vals else 0) / 1e6 / 2) * 2)
    out = [text(16, 24, 'Estimated map heap vs the %s-byte budget, every proposed map ("everything")' % fmt(budget),
                15, weight='bold'),
           text(16, 42, 'One bar per map, sorted; orange = interior cell, blue = exterior region. Calibrated '
                        'estimate, not converted.', 12, MUTED)]
    for k in range(0, int(top) + 1, 2):
        yy = y0 + ph - ph * k / top
        out.append(line(x0, yy, x0 + pw, yy))
        out.append(text(x0 - 6, yy + 4, '%d MB' % k if k % 4 == 0 else '', 10, MUTED, 'end'))
    n = len(vals)
    for b in range(pw if n else 0):
        seg = vals[n * b // pw: max(n * b // pw + 1, n * (b + 1) // pw)]
        if not seg:
            continue
        v = seg[0][0] / 1e6
        inter = sum(1 for s in seg if s[1] == 'interior') * 2 >= len(seg)
        x = x0 + b
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"><title>%s: %.2f MB'
                   '</title></line>\n' % (x, y0 + ph, x, y0 + ph - ph * min(v, top) / top, MODELS if inter else WORLD,
                                          escape(seg[0][2]), v))
    by = y0 + ph - ph * (budget / 1e6) / top
    over = sum(1 for v in vals if v[0] > budget)
    risk = sum(1 for v in vals if 0.9 * budget < v[0] <= budget)
    out.append(line(x0, by, x0 + pw, by, HOT, 1.5, '5,3'))
    out.append(text(x0 + pw, by - 6, 'budget %.2f MB: %s maps over, %s within 10%%' % (budget / 1e6, fmt(over), fmt(risk)),
                    12, HOT, 'end', 'bold'))
    out.append(line(x0, y0 + ph, x0 + pw, y0 + ph, MUTED))
    out.append(text(x0, y0 + ph + 16, '%s maps, sorted by estimated heap (left = largest)' % fmt(n), 11, MUTED))
    out.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (x0, h - 30, MODELS) +
               text(x0 + 18, h - 20, 'interior cell', 11))
    out.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (x0 + 120, h - 30, WORLD) +
               text(x0 + 138, h - 20, 'exterior region (town-converter sub-cell)', 11))
    return svg(w, h, ''.join(out))


def faces_chart(rows, limits):
    w, h = 960, 640
    out = [text(16, 24, 'BSP sizes vs Quake limits, every proposed map ("everything")', 15, weight='bold'),
           text(16, 42, 'Each panel: one metric, all maps sorted by value, with the limit line. Calibrated estimates.',
                12, MUTED)]
    panels = [('faces', limits['faces'], 'Faces (limit %s)' % fmt(limits['faces'])),
              ('texinfo', limits['texinfo'], 'Texinfo (limit %s; %s planned)' % (fmt(limits['texinfo']),
                                                                                 fmt(limits['texinfo_planned']))),
              ('nodes', limits['nodes'], 'Hull-0 nodes (limit %s)' % fmt(limits['nodes'])),
              ('clipnodes', limits['clipnodes'], 'Clipnodes (limit %s)' % fmt(limits['clipnodes']))]
    for i, (k, lim, title) in enumerate(panels):
        x0 = 90 + (i % 2) * 460
        y0 = 90 + (i // 2) * 280
        vals = [r['evr_' + k] for r in rows]
        out.append(sorted_panel(x0, y0, 380, 200, vals, lim, title))
        if k == 'texinfo' and limits['texinfo_planned'] != lim:
            planned = limits['texinfo_planned']
            yy = y0 + 200 - 200 * (planned / (max(max(vals, default=0), lim) * 1.08))
            if yy > y0:
                n = sum(1 for v in vals if v > planned)
                out.append(line(x0, yy, x0 + 380, yy, MID, 1.5, '2,3'))
                out.append(text(x0 + 380, yy - 4, 'planned %s: %s over' % (fmt(planned), fmt(n)), 10, MID, 'end'))
    return svg(w, h, ''.join(out))


def entity_chart(rows, limits):
    w, h = 960, 380
    out = [text(16, 24, 'Entities per map vs engine tables ("everything": every placed object is a func_wall, '
                        'actors are edicts)', 15, weight='bold'),
           text(16, 42, 'Edicts vs MAX_EDICTS %d; inline brush models vs the %d budget; static flames vs %d.' % (
               limits['max_edicts'], limits['inline_models'], limits['static_flames']), 12, MUTED)]
    panels = [('evr_edicts', limits['max_edicts'], 'Edicts (MAX_EDICTS %d)' % limits['max_edicts']),
              ('evr_inline_models', limits['inline_models'], 'Inline models (budget %d)' % limits['inline_models']),
              ('evr_flames', limits['static_flames'], 'Static flames (%d)' % limits['static_flames'])]
    for i, (k, lim, title) in enumerate(panels):
        out.append(sorted_panel(70 + i * 310, 90, 240, 220, [r[k] for r in rows], lim, title, colour=MODELS))
    return svg(w, h, ''.join(out))


def gates_chart(summary, limits):
    names = [('heap', 'Heap budget'), ('inline_models', 'Inline models > %d' % limits['inline_models']),
             ('clipnodes', 'Clipnodes > %s' % fmt(limits['clipnodes'])),
             ('texinfo', 'Texinfo > %s' % fmt(limits['texinfo'])), ('nodes', 'Nodes > %s' % fmt(limits['nodes'])),
             ('night_lamp_cache_3x3', 'Night lamps > %d per 3x3 cells' % limits['lamp_cache_3x3']),
             ('surface_extent_256', 'Known surface extent > %d' % limits['surface_extent']),
             ('static_flames', 'Static flames > %d' % limits['static_flames']),
             ('faces', 'Faces > %s' % fmt(limits['faces'])), ('coord_4096', 'Coordinates beyond %d' % limits['coord']),
             ('edicts', 'Edicts > %d' % limits['max_edicts']), ('vertexes', 'Vertexes > %s' % fmt(limits['vertexes'])),
             ('texinfo_planned_65535', 'Texinfo > %s (planned)' % fmt(limits['texinfo_planned'])),
             ('marksurfaces', 'Marksurfaces > %s' % fmt(limits['marksurfaces'])),
             ('lightstyles', 'Lightstyles > %d' % limits['max_lightstyles']),
             ('terrain_ceiling', 'Ground above the %d frame ceiling' % limits['terrain_ceiling'])]
    left, top, bar, gap, width = 230, 70, 16, 7, 520
    sets = [s for s in ('vvardenfell', 'tribunal', 'bloodmoon') if s in summary]
    mx = max([sum(summary[s]['evr']['gates'][g]['fail'] for s in sets) for g, _ in names] + [1])
    out = [text(16, 24, 'Maps over each limit ("everything"), stacked by data set', 15, weight='bold'),
           text(16, 42, 'Vvardenfell (Morrowind.esm) / Tribunal / Bloodmoon; a map can fail several limits.', 12, MUTED)]
    for i, (g, label) in enumerate(names):
        y = top + i * (bar + gap)
        x = left
        out.append(text(left - 8, y + 12, label, 11, INK, 'end'))
        tot = 0
        for s in sets:
            n = summary[s]['evr']['gates'][g]['fail']
            if n:
                wd = width * n / mx
                out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="2" fill="%s"><title>%s %s: %d maps'
                           '</title></rect>\n' % (x, y, max(wd - 2, 1), bar, SET_COLOURS[s], s, escape(label), n))
                x += wd
            tot += n
        out.append(text(x + 6, y + 12, fmt(tot), 11, INK))
    y = top + len(names) * (bar + gap) + 14
    for j, s in enumerate(sets):
        out.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (left + j * 140, y, SET_COLOURS[s]) +
                   text(left + j * 140 + 18, y + 10, s.capitalize(), 11))
    return svg(800, y + 30, ''.join(out))


def heat_map(rows, limits, towns):
    """Exterior cells coloured by the worst 'everything' heap ratio of the regions whose core lies in the cell."""
    cells, sets = {}, {}
    for r in rows:
        if r['space'] != 'exterior' or not r['refs_total']:
            continue
        for c in r['core_cells'].split():
            x, y = map(int, c.split(','))
            cells[(x, y)] = max(cells.get((x, y), 0), r['evr_heap'] / limits['heap_budget'])
            sets[(x, y)] = r['set']
    if not cells:
        return svg(400, 80, text(16, 40, 'No exterior regions with objects.', 13))
    xs = [k[0] for k in cells]
    ys = [k[1] for k in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s, left, top = 13, 40, 70
    W = left + (x1 - x0 + 1) * s + 230
    H = max(top + (y1 - y0 + 1) * s + 60, 330)
    out = [text(16, 24, 'Worst estimated heap per exterior cell, every object placed ("everything")', 15, weight='bold'),
           text(16, 42, 'Cell colour = highest heap / budget of the sub-cell regions in that cell. North is up. '
                        'Bloodmoon cells outlined.', 12, MUTED)]
    edges = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    def colour(v):
        if v > 1.0:
            return HOT
        for i, e in enumerate(edges):
            if v <= e:
                return SEQ[i]
        return SEQ[-1]
    for (x, y), v in sorted(cells.items()):
        px = left + (x - x0) * s
        py = top + (y1 - y) * s
        stroke = (' stroke="%s" stroke-width="1"' % INK if sets[(x, y)] == 'bloodmoon'
                  else ' stroke="%s" stroke-width="0.5"' % BG)
        out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"%s><title>cell %d,%d: worst heap %.0f%% of '
                   'budget (%s)</title></rect>\n' % (px, py, s, s, colour(v), stroke, x, y, v * 100, sets[(x, y)]))
    for name, cs in sorted(towns.items()):
        cs = [c for c in cs if tuple(c) in cells]
        if len(cs) < 2:
            continue
        cx = sum(c[0] for c in cs) / len(cs)
        cy = sum(c[1] for c in cs) / len(cs)
        px = left + (cx - x0 + .5) * s
        py = top + (y1 - cy + .5) * s
        out.append('<text x="%.1f" y="%.1f" %s font-size="10" fill="%s" stroke="%s" stroke-width="2.5" '
                   'paint-order="stroke" text-anchor="middle" font-weight="bold">%s</text>\n' % (
                       px, py + 3, FONT, INK, BG, escape(name)))
    lx = left + (x1 - x0 + 1) * s + 30
    ly = top + 10
    out.append(text(lx, ly, 'heap / budget', 12, weight='bold'))
    labels = ['<= 50%', '50-60%', '60-70%', '70-80%', '80-90%', '90-100%', '> 100% (over)']
    for i, lab in enumerate(labels):
        c = SEQ[i] if i < 6 else HOT
        out.append('<rect x="%d" y="%d" width="14" height="14" fill="%s" stroke="%s" stroke-width="0.5"/>' % (
            lx, ly + 12 + i * 20, c, GRID) + text(lx + 22, ly + 24 + i * 20, lab, 11))
    over = sum(1 for v in cells.values() if v > 1)
    out.append(text(lx, ly + 170, '%d cells hold at least one' % over, 11, INK))
    out.append(text(lx, ly + 184, 'region over budget', 11, INK))
    out.append(text(lx, ly + 204, '%d cells with objects' % len(cells), 11, MUTED))
    return svg(W, H, ''.join(out))


def accuracy_chart(cmp, limits):
    """Predicted vs measured heap of the sample conversion (and calibration CV rows if present)."""
    w, h = 560, 520
    x0, y0, sz = 80, 70, 400
    pts = [(c['heap_true'] / 1e6, c['heap_pred'] / 1e6) for c in cmp.get('validation', []) + cmp.get('cv', [])
           if c.get('heap_true') and c.get('heap_pred')]
    lo = math.floor(min([p for q in pts for p in q] + [5.0]))
    hi = math.ceil(max([p for q in pts for p in q] + [limits['heap_budget'] / 1e6 + 1]))
    out = [text(16, 24, 'Estimator check: predicted vs measured map heap', 15, weight='bold'),
           text(16, 42, 'Colour = maps converted for this check (frozen predictions); grey = calibration CV.', 12, MUTED)]
    for k in range(lo, hi + 1):
        p = x0 + sz * (k - lo) / (hi - lo)
        q = y0 + sz - sz * (k - lo) / (hi - lo)
        out.append(line(p, y0, p, y0 + sz))
        out.append(line(x0, q, x0 + sz, q))
        if (k - lo) % 2 == 0:
            out.append(text(p, y0 + sz + 14, '%d' % k, 10, MUTED, 'middle'))
            out.append(text(x0 - 6, q + 4, '%d' % k, 10, MUTED, 'end'))
    out.append(line(x0, y0 + sz, x0 + sz, y0, MUTED, 1, '4,3'))
    b = limits['heap_budget'] / 1e6
    pb = x0 + sz * (b - lo) / (hi - lo)
    qb = y0 + sz - sz * (b - lo) / (hi - lo)
    out.append(line(pb, y0, pb, y0 + sz, HOT, 1, '5,3'))
    out.append(line(x0, qb, x0 + sz, qb, HOT, 1, '5,3'))
    out.append(text(pb + 4, y0 + 12, 'budget', 10, HOT))

    def dot(m, p, colour, r, title):
        px = x0 + sz * (min(max(m, lo), hi) - lo) / (hi - lo)
        py = y0 + sz - sz * (min(max(p, lo), hi) - lo) / (hi - lo)
        return '<circle cx="%.1f" cy="%.1f" r="%g" fill="%s" stroke="%s" stroke-width="1"><title>%s</title></circle>\n' % (
            px, py, r, colour, BG, escape(title))
    for c in cmp.get('cv', []):
        out.append(dot(c['heap_true'] / 1e6, c['heap_pred'] / 1e6, '#bdbab2', 2.5, '%s: measured %.2f MB, CV estimate '
                       '%.2f MB' % (c['map'], c['heap_true'] / 1e6, c['heap_pred'] / 1e6)))
    for c in cmp.get('validation', []):
        if not c.get('heap_true') or not c.get('heap_pred'):
            continue
        col = MODELS if c['space'] == 'interior' else WORLD
        out.append(dot(c['heap_true'] / 1e6, c['heap_pred'] / 1e6, col, 5, '%s %s: measured %.2f MB, frozen estimate '
                       '%.2f MB' % (c['map'], c['name'], c['heap_true'] / 1e6, c['heap_pred'] / 1e6)))
    out.append(text(x0 + sz / 2, y0 + sz + 32, 'measured heap (MB, check_world_map_heap on the converted BSP)', 11, INK,
                    'middle'))
    out.append('<text x="22" y="%d" %s font-size="11" fill="%s" transform="rotate(-90 22 %d)" text-anchor="middle">'
               'estimated heap (MB)</text>\n' % (y0 + sz / 2, FONT, INK, y0 + sz / 2))
    out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (x0 + 10, h - 20, MODELS) +
               text(x0 + 20, h - 16, 'converted interior', 11))
    out.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (x0 + 170, h - 20, WORLD) +
               text(x0 + 180, h - 16, 'converted exterior', 11))
    return svg(w, h, ''.join(out))


def write_charts(out, rows, summary, limits, towns, compare=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    built = [r for r in rows if r['refs_total'] > 0]
    files = {'heap-vs-budget.svg': heap_chart(built, limits), 'faces-vs-limits.svg': faces_chart(built, limits),
             'entities-vs-max-edicts.svg': entity_chart(built, limits),
             'limits-failing.svg': gates_chart(summary, limits), 'world-heat-map.svg': heat_map(built, limits, towns)}
    if compare:
        files['estimator-accuracy.svg'] = accuracy_chart(compare, limits)
    for k, v in files.items():
        (out / k).write_bytes(v.encode('utf-8'))
    return sorted(files)
