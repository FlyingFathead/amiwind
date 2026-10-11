#!/usr/bin/env python3
"""Draw the CHIM progress map of the island as one PNG (for the README and release notes).

Reads the tracker data (format aw-cell-progress-1, written by tools/cell_progress.py ingest) and draws one square
per map cell, north up. No game textures and no names beyond a few place labels are used; the picture is made of
flat colours only.

  green     done: converted to CHIM and every measured check passed (or an empty sea cell)
  violet    converted, a check is still pending (hull policy)
  red       converted but failing a check, or not converted yet
  dark      not started (Solstheim)
  silver    open ocean (one shared ocean chunk)
  gold ring planned for the next release (the release plan layer)

Usage: cell_progress_map.py --data cell-progress.json --out map.png [--font FONT.ttf] [--scale 16] [--date YYYY-MM-DD]
Needs Pillow.
"""
import argparse
import json
import sys
from pathlib import Path

DONE = {'audits_passed', 'complete', 'complete_unlit', 'terrain_complete', 'terrain_complete_unlit',
        'empty_sea', 'playtested', 'approved'}
PENDING = {'hull_policy_pending'}
FAILING = {'converted_failing', 'not_converted'}
COLORS = {
    'done': (63, 157, 90), 'pending': (122, 111, 201), 'failing': (181, 73, 91),
    'not_started': (70, 74, 84), 'ocean': (143, 153, 168), 'none': (28, 32, 40),
}
GOLD = (240, 192, 48)
BG = (18, 22, 30)
LABELS = ['Seyda Neen', 'Balmora', 'Vivec', 'Ald-ruhn', 'Sadrith Mora', 'Gnisis', 'Pelagiad', 'Ebonheart',
          'Solstheim']


def category(cell):
    bucket = (cell.get('chim') or {}).get('bucket')
    if bucket == 'ocean':
        return 'ocean'
    if bucket in DONE:
        return 'done'
    if bucket in PENDING:
        return 'pending'
    if bucket in FAILING:
        return 'failing'
    if bucket == 'not_started':
        return 'not_started'
    return 'none'


def summarize(data):
    cells = data['cells']
    land = [c for c in cells.values() if c.get('land') and c.get('island') == 1]
    done = [c for c in land if category(c) == 'done']
    planned = [c for c in cells.values() if c.get('plan')]
    return {'land': len(land), 'done': len(done), 'planned': len(planned),
            'ocean': sum(1 for c in cells.values() if category(c) == 'ocean'),
            'solstheim': sum(1 for c in cells.values() if c.get('island') == 2 and c.get('land'))}


def label_positions(cells):
    pos = {}
    for name in LABELS:
        pts = [(c['x'], c['y']) for c in cells.values()
               if c.get('name') and (c['name'] == name or (name == 'Solstheim' and c['name'].startswith('Solstheim')))]
        if pts:
            pos[name] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return pos


def draw(data, out, font_path=None, scale=16, date=''):
    from PIL import Image, ImageDraw, ImageFont
    cells = data['cells']
    xs = [c['x'] for c in cells.values()]
    ys = [c['y'] for c in cells.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w = (x1 - x0 + 1) * scale
    h = (y1 - y0 + 1) * scale
    top, bottom = 64, 74
    img = Image.new('RGB', (w, h + top + bottom), BG)
    d = ImageDraw.Draw(img)

    def font(size):
        try:
            return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default(size)
        except Exception:
            return ImageFont.load_default()
    f_big, f_mid, f_small = font(int(scale * 1.5)), font(int(scale * 0.95)), font(int(scale * 0.8))

    def box(c):
        px = (c['x'] - x0) * scale
        py = top + (y1 - c['y']) * scale
        return px, py
    for c in cells.values():
        px, py = box(c)
        d.rectangle([px, py, px + scale - 1, py + scale - 1], fill=COLORS[category(c)])
    for c in cells.values():
        if c.get('plan'):
            px, py = box(c)
            d.rectangle([px, py, px + scale - 1, py + scale - 1], outline=GOLD, width=max(2, scale // 8))
    for name, (lx, ly) in label_positions(cells).items():
        px = (lx - x0 + 0.5) * scale
        py = top + (y1 - ly + 0.5) * scale
        tw = d.textlength(name, font=f_small)
        d.rectangle([px - tw / 2 - 3, py - scale * 0.5, px + tw / 2 + 3, py + scale * 0.5], fill=(0, 0, 0))
        d.text((px - tw / 2, py - scale * 0.45), name, fill=(255, 255, 255), font=f_small)
    s = summarize(data)
    title = 'AmiWind CHIM progress map'
    d.text((8, 6), title, fill=(255, 255, 255), font=f_big)
    sub = 'Done: %s of %s Vvardenfell land cells (%.1f %%)%s' % (
        format(s['done'], ','), format(s['land'], ','), 100.0 * s['done'] / max(1, s['land']),
        (' - ' + date) if date else '')
    d.text((8, 6 + int(scale * 1.8)), sub, fill=(210, 214, 222), font=f_mid)
    items = [('done', 'done'), ('pending', 'converted, hull policy pending'), ('failing', 'failing a check / not converted'),
             ('not_started', 'not started (Solstheim)'), ('ocean', 'open ocean')]
    lx, ly = 8, top + h + 10
    for key, text in items:
        d.rectangle([lx, ly, lx + scale, ly + scale], fill=COLORS[key])
        d.text((lx + scale + 6, ly), text, fill=(235, 238, 244), font=f_small)
        lx += scale + 14 + int(d.textlength(text, font=f_small)) + 6
        if lx > w - 200 and key != items[-1][0]:
            lx, ly = 8, ly + scale + 8
    ly2 = ly + scale + 10
    d.rectangle([8, ly2, 8 + scale, ly2 + scale], outline=GOLD, width=max(2, scale // 8))
    d.text((8 + scale + 6, ly2), 'gold ring: planned for the next release (%d cells)' % s['planned'],
           fill=(235, 238, 244), font=f_small)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', required=True, help='cell-progress.json from tools/cell_progress.py ingest')
    ap.add_argument('--out', required=True)
    ap.add_argument('--font')
    ap.add_argument('--scale', type=int, default=16)
    ap.add_argument('--date', default='')
    a = ap.parse_args(argv)
    data = json.loads(Path(a.data).read_text(encoding='utf-8'))
    if data.get('format') != 'aw-cell-progress-1':
        print('not a cell-progress file', file=sys.stderr)
        return 2
    print(json.dumps(draw(data, a.out, a.font, a.scale, a.date)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
