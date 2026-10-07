#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Performance charts for the public docs, as plain SVG (renders on GitHub, diffs
as text). The numbers are measurements recorded in the docs they illustrate:
docs/performance/TOWN-VISIBILITY.md and docs/SEYDA_NEEN_PERFORMANCE.md.

Usage: perf_charts.py write [--out docs/images]   (rewrite the SVGs)
       perf_charts.py check [--out docs/images]   (fail if they are stale)
"""
import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# Share of the map visible from an average leaf (Quake visibility data, dev5 maps).
VISIBILITY = [
    ('Mages Guild (interior)', 100), ('Temple (interior)', 100), ('Census (interior)', 100),
    ('Prison ship (interior)', 100), ('Balmora bm020', 89), ('Balmora bm028', 88),
    ('Balmora bm019', 87), ('Balmora bm029', 84), ('Open world vf0930', 85),
    ('Open world vf1383', 83), ('Seyda Neen docks', 76), ('Seyda Neen', 73),
    ('Open world vf1158', 70), ('Seyda Neen courtyard', 59), ('Open water vf1311', 39),
]
# Faces per map: in the world (structural, used by vis) and in func_wall models.
FACES = [
    ('Mages Guild', 42, 40488), ('Temple', 52, 35190), ('Census', 38, 20563),
    ('Balmora bm019', 2215, 36031), ('Balmora bm020', 2415, 35520),
    ('Seyda Neen', 3952, 21475), ('Open world vf0930', 4427, 10800),
]
# Seyda Neen sub-cell crossing load time in seconds: v0.0.30-dev4 range per
# sub-cell, and the v0.0.31 range on the same route.
SEYDA_LOAD = [
    ('sn017', (1.00, 1.02)), ('sn021', (1.14, 1.19)), ('sn019', (1.38, 1.47)),
    ('sn020', (1.28, 1.37)), ('sn014', (1.26, 1.37)), ('sn015', (1.32, 1.37)),
]
SEYDA_NOW = (0.39, 0.48)

INK, MUTED, GRID, BG = '#3d3d3a', '#77756f', '#d8d6cf', '#ffffff'
HOT, WARM, MID, COOL = '#c8423f', '#e0784f', '#e8a317', '#2f8f4e'
WORLD, MODELS = '#2a78d6', '#eb6834'
FONT = 'font-family="Helvetica, Arial, sans-serif"'


def _svg(width, height, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">\n'
            '<rect width="100%%" height="100%%" fill="%s"/>\n%s</svg>\n') % (width, height, width, height, BG, body)


def _text(x, y, s, size=12, colour=INK, anchor='start', weight='normal'):
    return '<text x="%g" y="%g" %s font-size="%d" fill="%s" text-anchor="%s" font-weight="%s">%s</text>\n' % (
        x, y, FONT, size, colour, anchor, weight, escape(s))


def visibility_chart():
    left, top, bar, gap, width = 190, 56, 18, 8, 380
    height = top + len(VISIBILITY) * (bar + gap) + 40
    out = [_text(16, 24, 'Share of the map Quake treats as visible from an average spot', 15, weight='bold'),
           _text(16, 42, 'Visibility data of the v0.0.31-dev5 maps; lower is better', 12, MUTED)]
    for pct in range(0, 101, 25):
        x = left + width * pct / 100
        out.append('<line x1="%g" y1="%d" x2="%g" y2="%d" stroke="%s" stroke-width="1"/>\n' % (x, top - 4, x, height - 36, GRID))
        out.append(_text(x, height - 20, '%d%%' % pct, 11, MUTED, 'middle'))
    for i, (name, pct) in enumerate(VISIBILITY):
        y = top + i * (bar + gap)
        colour = HOT if pct >= 95 else WARM if pct >= 80 else MID if pct >= 60 else COOL
        out.append(_text(left - 8, y + 13, name, 12, INK, 'end'))
        out.append('<rect x="%d" y="%d" width="%g" height="%d" rx="3" fill="%s"/>\n' % (left, y, width * pct / 100, bar, colour))
        out.append(_text(left + width * pct / 100 + 6, y + 13, '%d%%' % pct, 12, INK))
    return _svg(left + width + 60, height, ''.join(out))


def faces_chart():
    left, top, bar, gap, width = 150, 76, 20, 10, 420
    biggest = max(w + m for _, w, m in FACES)
    height = top + len(FACES) * (bar + gap) + 40
    out = [_text(16, 24, 'Faces per map: walls Quake can use for visibility vs func_wall models', 15, weight='bold'),
           _text(16, 42, 'Only world faces split the map into visibility cells; func_wall models are ignored', 12, MUTED),
           '<rect x="16" y="52" width="10" height="10" fill="%s"/>\n' % WORLD, _text(32, 61, 'World (structural)', 12, INK),
           '<rect x="170" y="52" width="10" height="10" fill="%s"/>\n' % MODELS, _text(186, 61, 'func_wall models', 12, INK)]
    for i, (name, world, models) in enumerate(FACES):
        y = top + i * (bar + gap)
        w1 = width * world / biggest; w2 = width * models / biggest
        out.append(_text(left - 8, y + 14, name, 12, INK, 'end'))
        out.append('<rect x="%d" y="%d" width="%g" height="%d" fill="%s"/>\n' % (left, y, max(w1, 1), bar, WORLD))
        out.append('<rect x="%g" y="%d" width="%g" height="%d" fill="%s"/>\n' % (left + max(w1, 1), y, w2, bar, MODELS))
        share = 100 * models / (world + models)
        out.append(_text(left + w1 + w2 + 6, y + 14, '{:,} / {:,} ({:.0f}% in func_walls)'.format(world, models, share), 11, MUTED))
    return _svg(left + width + 230, height, ''.join(out))


def seyda_chart():
    left, top, bar, gap, width, scale = 90, 76, 18, 10, 420, 1.6
    height = top + (len(SEYDA_LOAD) + 1) * (bar + gap) + 40
    out = [_text(16, 24, 'Seyda Neen sub-cell crossing: load time', 15, weight='bold'),
           _text(16, 42, 'Same scripted route; range over repeated runs (seconds, lower is better)', 12, MUTED),
           '<rect x="16" y="52" width="10" height="10" fill="%s"/>\n' % WARM, _text(32, 61, 'v0.0.30-dev4', 12, INK),
           '<rect x="130" y="52" width="10" height="10" fill="%s"/>\n' % COOL, _text(146, 61, 'v0.0.31 (all crossings)', 12, INK)]
    for t in (0, 0.4, 0.8, 1.2, 1.6):
        x = left + width * t / scale
        out.append('<line x1="%g" y1="%d" x2="%g" y2="%d" stroke="%s" stroke-width="1"/>\n' % (x, top - 4, x, height - 36, GRID))
        out.append(_text(x, height - 20, '%.1f s' % t, 11, MUTED, 'middle'))
    rows = [(n, r, WARM) for n, r in SEYDA_LOAD] + [('v0.0.31', SEYDA_NOW, COOL)]
    for i, (name, (low, high), colour) in enumerate(rows):
        y = top + i * (bar + gap)
        out.append(_text(left - 8, y + 13, name, 12, INK, 'end'))
        out.append('<rect x="%d" y="%d" width="%g" height="%d" rx="3" fill="%s"/>\n' % (left, y, width * high / scale, bar, colour))
        out.append(_text(left + width * high / scale + 6, y + 13, '%.2f-%.2f s' % (low, high), 11, MUTED))
    return _svg(left + width + 110, height, ''.join(out))


CHARTS = {
    'amiwind-perf-visibility-by-map.svg': visibility_chart,
    'amiwind-perf-faces-world-vs-funcwall.svg': faces_chart,
    'amiwind-perf-seyda-crossing-load.svg': seyda_chart,
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=('write', 'check'))
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'docs/images'))
    a = ap.parse_args(argv)
    out, stale = Path(a.out), []
    for name, make in sorted(CHARTS.items()):
        data = make().encode('utf-8')
        path = out / name
        if a.action == 'write':
            path.write_bytes(data)
        elif not path.is_file() or path.read_bytes() != data:
            stale.append(name)
    if stale:
        print('stale charts (run perf_charts.py write):', ', '.join(stale)); return 1
    print('%s %d charts' % ('wrote' if a.action == 'write' else 'checked', len(CHARTS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
