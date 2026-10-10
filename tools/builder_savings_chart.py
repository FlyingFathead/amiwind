#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builder time savings chart (docs/performance/BUILDER_PROFILE.md) as a PNG, drawn with Pillow from
the numbers in docs/performance/builder-savings.json, so the image is reproducible and never edited
by hand.

Each item is a pair of bars on a log time axis: before (orange) and after (blue); a solid bar is a
measured value, a hatched bar an estimate. When a measurement replaces an estimate, change its value
and kind in the JSON and run `write` again.

Usage: builder_savings_chart.py write [--data JSON] [--out PNG]
       builder_savings_chart.py check [--data JSON] [--out PNG]   (fail if the PNG is stale)
"""
import argparse
import io
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/performance/builder-savings.json'
OUT = ROOT / 'docs/images/amiwind-builder-savings.png'
FONTS = ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/TTF/DejaVuSans.ttf')
BOLD = ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf')
SURFACE, INK, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e2dc'
BEFORE, AFTER = '#eb6834', '#2a78d6'   # categorical slots 2 and 1 of the docs' chart palette
WIDTH = 1800
LEFT, RIGHT = 600, 150                 # label column, room for the value labels
LOW, HIGH = 1.0, 10000.0               # axis: 1 s to about 2.8 h
TICKS = ((1, '1 s'), (10, '10 s'), (60, '1 min'), (600, '10 min'), (3600, '1 h'))


def font(size, bold=False):
    from PIL import ImageFont
    for path in (BOLD if bold else FONTS):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def duration(seconds):
    if seconds < 90:
        return '%d s' % round(seconds)
    if seconds < 5400:
        return '%d min' % round(seconds / 60)
    return '%.1f h' % (seconds / 3600)


def render(data):
    from PIL import Image, ImageDraw
    items = data['items']
    f_title, f_sub, f_text, f_small = font(38, True), font(24), font(24), font(20)
    bar, pair_gap, row_gap = 26, 6, 30
    legend_y = 140
    plot_top = 230
    row_h = 2 * bar + pair_gap + row_gap
    plot_bottom = plot_top + len(items) * row_h
    caption_top = plot_bottom + 70
    height = caption_top + 30 * len(data['caption']) + 30
    image = Image.new('RGB', (WIDTH, height), SURFACE)
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), data['title'], font=f_title, fill=INK)
    draw.text((40, 84), data['subtitle'], font=f_sub, fill=MUTED)

    # Legend outside the plot: colour = before/after, fill = measured/estimated.
    x = 40
    for colour, label, hatched in ((BEFORE, data['before_label'], False), (AFTER, data['after_label'], False),
                                   (MUTED, 'Measured', False), (MUTED, 'Estimated', True)):
        _bar(draw, x, legend_y, x + 44, legend_y + bar, colour, hatched)
        draw.text((x + 56, legend_y - 1), label, font=f_text, fill=INK)
        x += 56 + int(draw.textlength(label, font=f_text)) + 48

    span = WIDTH - LEFT - RIGHT

    def position(seconds):
        value = min(max(seconds, LOW), HIGH)
        return LEFT + span * (math.log10(value) - math.log10(LOW)) / (math.log10(HIGH) - math.log10(LOW))

    for seconds, label in TICKS:
        tx = position(seconds)
        draw.line([(tx, plot_top - 12), (tx, plot_bottom)], fill=GRID, width=2)
        width = draw.textlength(label, font=f_small)
        draw.text((tx - width / 2, plot_bottom + 12), label, font=f_small, fill=MUTED)
    draw.line([(LEFT, plot_top - 12), (LEFT, plot_bottom)], fill=MUTED, width=2)

    for index, item in enumerate(items):
        top = plot_top + index * row_h
        label_y = top + bar + pair_gap / 2 - 14
        draw.text((40, label_y), item['label'], font=f_text, fill=INK)
        for offset, key, colour in ((0, 'before', BEFORE), (bar + pair_gap, 'after', AFTER)):
            y = top + offset
            end = position(item[key])
            estimated = item[key + '_kind'] == 'estimated'
            _bar(draw, LEFT, y, end, y + bar, colour, estimated)
            text = ('~' if estimated else '') + duration(item[key])
            draw.text((end + 12, y - 1), text, font=f_small, fill=INK)

    for line, text in enumerate(data['caption']):
        draw.text((40, caption_top + 30 * line), text, font=f_small, fill=MUTED)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def _bar(draw, x0, y0, x1, y1, colour, hatched):
    """A bar with 4 px rounded ends; an estimate is hatched (diagonal lines) with an outline."""
    if x1 - x0 < 8:
        x1 = x0 + 8
    if not hatched:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=colour)
        return
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=SURFACE, outline=colour, width=3)
    step = 10
    start = int(x0) - int(y1 - y0)
    for x in range(start, int(x1), step):
        a = (max(x, x0 + 2), y1 - 2 - max(0, (x0 + 2) - x))
        b = (min(x + (y1 - y0), x1 - 2), y0 + 2 + max(0, x + (y1 - y0) - (x1 - 2)))
        if a[0] < b[0]:
            draw.line([a, b], fill=colour, width=3)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=('write', 'check'))
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args(argv)
    png = render(json.loads(args.data.read_text(encoding='utf-8')))
    if args.mode == 'write':
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(png)
        print('wrote %s (%d bytes)' % (args.out, len(png)))
        return 0
    if not args.out.is_file() or args.out.read_bytes() != png:
        print('stale: %s does not match %s; run builder_savings_chart.py write' % (args.out, args.data))
        return 1
    print('ok: %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
