#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Release graphs: small palette PNG bar charts drawn from a measurements JSON.

The JSON holds aggregate numbers only (bytes per area, counts per camera,
milliseconds per frame, seconds per build stage), never game data. Each chart is
one PNG with one or more panels; a panel has one unit and one linear axis that
starts at zero, so every bar in it is drawn on the same scale.

Honesty rules, checked before anything is drawn:
- every row has a value (or null = "not measured yet", or the row's own
  "missing" text) for every series, so a series cannot be dropped where it
  looks worse;
- emulator timings are labelled "FS-UAE (relative)" on the image itself;
  exact counts read in the emulator (bytes, faces) say "FS-UAE counts";
- timing panels say which host load they were measured under (quiet, busy, or
  mixed with a label on every bar); busy and quiet numbers are never unlabelled;
- ratios are worded "x less" / "x more", never "better".

Usage: release_graphs.py check DATA            (validate only)
       release_graphs.py write DATA --out DIR  (draw every chart)
       release_graphs.py write DATA --out DIR --only ID [--only ID ...]
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = 'amiwind-release-graphs 1'
SOURCES = {
    'emulator': 'FS-UAE (relative)',
    'emulator-count': 'FS-UAE counts',
    'build': 'builder output',
    'host': 'host measurement',
    'estimate': 'estimate',
}
HOSTS = {'quiet': 'quiet host', 'busy': 'busy host', 'mixed': 'host load per bar', 'n/a': ''}
TIMING_UNITS = {'s', 'ms', 'min', 'fps', 'frames/s', 'ms/frame', 's/frame'}
FILE_RE = re.compile(r'^amiwind-v\d+\.\d+\.\d+-[a-z0-9-]+\.png$')

# Reference categorical order (slot 1 blue, slot 2 orange, slot 3 aqua, slot 4 yellow).
SERIES_COLOURS = ['#eb6834', '#2a78d6', '#1baf7a', '#eda100']
SURFACE, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3de'
WIDTH = 960
LEFT = 230          # row label column
PLOT = 470          # bar area
BAR, BAR_GAP, ROW_GAP = 16, 3, 12


class GraphError(ValueError):
    pass


def _need(cond, msg):
    if not cond:
        raise GraphError(msg)


def validate(data):
    """Raise GraphError on the first rule a measurements document breaks."""
    _need(isinstance(data, dict) and data.get('schema') == SCHEMA, 'schema must be %r' % SCHEMA)
    charts = data.get('charts')
    _need(isinstance(charts, list) and charts, 'charts must be a non-empty list')
    ids, files = set(), set()
    for chart in charts:
        cid = chart.get('id')
        _need(isinstance(cid, str) and re.match(r'^[a-z0-9-]+$', cid or ''), 'chart id must be lower-case words: %r' % cid)
        _need(cid not in ids, 'duplicate chart id %s' % cid)
        ids.add(cid)
        name = chart.get('file', '')
        _need(FILE_RE.match(name), '%s: file must look like amiwind-vX.Y.Z-name.png, got %r' % (cid, name))
        _need(name not in files, '%s: duplicate file %s' % (cid, name))
        files.add(name)
        _need(isinstance(chart.get('title'), str) and chart['title'].strip(), '%s: title missing' % cid)
        series = chart.get('series')
        _need(isinstance(series, list) and 1 <= len(series) <= len(SERIES_COLOURS)
              and all(isinstance(s, str) and s for s in series) and len(set(series)) == len(series),
              '%s: series must be 1-%d distinct names' % (cid, len(SERIES_COLOURS)))
        panels = chart.get('panels')
        _need(isinstance(panels, list) and panels, '%s: panels missing' % cid)
        for p_index, panel in enumerate(panels):
            where = '%s panel %d' % (cid, p_index + 1)
            _need(isinstance(panel.get('title'), str) and panel['title'].strip(), where + ': title missing')
            unit = panel.get('unit')
            _need(isinstance(unit, str) and unit.strip(), where + ': unit missing')
            source = panel.get('source')
            _need(source in SOURCES, where + ': source must be one of %s' % sorted(SOURCES))
            host = panel.get('host')
            _need(host in HOSTS, where + ': host must be one of %s' % sorted(HOSTS))
            if source == 'emulator' or unit in TIMING_UNITS:
                _need(host != 'n/a', where + ': timings and emulator numbers must name the host load')
            rows = panel.get('rows')
            _need(isinstance(rows, list) and rows, where + ': rows missing')
            for row in rows:
                label = row.get('label')
                _need(isinstance(label, str) and label.strip(), where + ': row label missing')
                values = row.get('values')
                _need(isinstance(values, list) and len(values) == len(series),
                      '%s, %s: one value per series (%d), null when not measured' % (where, label, len(series)))
                for v in values:
                    _need(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)
                                        and math.isfinite(v) and v >= 0),
                          '%s, %s: values must be numbers >= 0 or null' % (where, label))
                if host == 'mixed':
                    hosts = row.get('hosts')
                    _need(isinstance(hosts, list) and len(hosts) == len(series), '%s, %s: mixed host needs a host per value' % (where, label))
                    for v, h in zip(values, hosts):
                        _need(v is None or h in ('quiet', 'busy'), '%s, %s: each measured value needs quiet or busy' % (where, label))
                missing = row.get('missing', [])
                _need(isinstance(missing, list) and len(missing) in (0, len(series)), '%s, %s: missing needs one entry per series' % (where, label))
                notes = row.get('notes', [])
                _need(isinstance(notes, list) and len(notes) in (0, len(series)), '%s, %s: notes need one entry per series' % (where, label))
    return True


def _fmt(v):
    if v >= 1000:
        return '{:,.0f}'.format(v)
    if v >= 100:
        return '{:.0f}'.format(v)
    if v >= 10:
        return ('{:.1f}'.format(v)).rstrip('0').rstrip('.')
    return ('{:.2f}'.format(v)).rstrip('0').rstrip('.')


def _ratio(values, lower_is_better):
    a, b = values[0], values[1]
    if not a or not b:
        return ''
    r = b / a
    if abs(r - 1) < 0.005:
        return 'same'
    return ('%sx less' % _fmt(1 / r)) if r < 1 else ('%sx more' % _fmt(r))


def _axis(v):
    """Axis top and tick step: 3-6 ticks of 1, 2, 2.5 or 5 x 10^k, top at or above v."""
    if v <= 0:
        return 1.0, 0.25
    exp = math.floor(math.log10(v)) - 1
    for k in (exp, exp + 1, exp + 2):
        for m in (1, 2, 2.5, 5):
            step = m * 10 ** k
            ticks = math.ceil(v / step - 1e-9)
            if 3 <= ticks <= 6:
                return ticks * step, step
    return 10 ** (exp + 2), 10 ** (exp + 1)


def _nice_max(v):
    return _axis(v)[0]


def _fonts():
    from PIL import ImageFont
    fonts = {}
    for key, size in (('title', 20), ('panel', 15), ('text', 13), ('small', 11)):
        try:
            fonts[key] = ImageFont.load_default(size=size)
        except (TypeError, OSError):  # Pillow without FreeType: one bitmap size
            fonts[key] = ImageFont.load_default()
    return fonts


def _wrap(draw, text, font, width):
    words, lines, line = text.split(), [], ''
    for w in words:
        test = (line + ' ' + w).strip()
        if line and draw.textlength(test, font=font) > width:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def _panel_meta(panel):
    bits = [panel['unit'], SOURCES[panel['source']]]
    if HOSTS[panel['host']]:
        bits.append(HOSTS[panel['host']])
    bits.append('lower is better' if panel.get('lower_is_better', True) else 'higher is better')
    return ' | '.join(bits)


def render(chart, out_path):
    """Draw one chart to out_path as an optimised palette PNG."""
    from PIL import Image, ImageDraw
    fonts = _fonts()
    probe = ImageDraw.Draw(Image.new('RGB', (8, 8)))
    series = chart['series']
    n = len(series)
    sub_lines = _wrap(probe, chart.get('subtitle', ''), fonts['text'], WIDTH - 40) if chart.get('subtitle') else []
    foot_lines = []
    for note in chart.get('footer', []):
        foot_lines += _wrap(probe, note, fonts['small'], WIDTH - 40)
    row_h = n * BAR + (n - 1) * BAR_GAP + ROW_GAP
    height = 22 + 26 + 18 * len(sub_lines) + 30
    for panel in chart['panels']:
        height += 26 + 20 + len(panel['rows']) * row_h + 26
    height += 14 * len(foot_lines) + 16
    img = Image.new('RGB', (WIDTH, height), SURFACE)
    d = ImageDraw.Draw(img)
    y = 18
    d.text((20, y), chart['title'], font=fonts['title'], fill=INK)
    if any(p['source'] == 'emulator' for p in chart['panels']):
        badge = SOURCES['emulator']
        bw = d.textlength(badge, font=fonts['text'])
        d.rounded_rectangle((WIDTH - 32 - bw, 14, WIDTH - 16, 38), radius=4, outline=INK2, width=1)
        d.text((WIDTH - 24, 18), badge, font=fonts['text'], fill=INK2, anchor='ra')
    y += 28
    for line in sub_lines:
        d.text((20, y), line, font=fonts['text'], fill=INK2)
        y += 18
    y += 6
    x = 20
    for i, name in enumerate(series):
        d.rounded_rectangle((x, y + 2, x + 12, y + 14), radius=3, fill=SERIES_COLOURS[i])
        d.text((x + 18, y), name, font=fonts['text'], fill=INK)
        x += 18 + int(d.textlength(name, font=fonts['text'])) + 26
    y += 24
    for panel in chart['panels']:
        y += 8
        d.text((20, y), panel['title'], font=fonts['panel'], fill=INK)
        y += 20
        d.text((20, y), _panel_meta(panel), font=fonts['small'], fill=INK2)
        y += 20
        measured = [v for row in panel['rows'] for v in row['values'] if v is not None]
        top, step = _axis(max(measured) if measured else 1.0)
        plot_top, plot_bottom = y - 4, y + len(panel['rows']) * row_h - ROW_GAP + 4
        for k in range(int(round(top / step)) + 1):
            gx = LEFT + PLOT * k * step / top
            d.line((gx, plot_top, gx, plot_bottom), fill=GRID, width=1)
            d.text((gx, plot_bottom + 3), _fmt(k * step), font=fonts['small'], fill=MUTED, anchor='ma')
        for row in panel['rows']:
            label_lines = _wrap(d, row['label'], fonts['text'], LEFT - 30)
            block = n * BAR + (n - 1) * BAR_GAP
            ly = y + block / 2 - 9 * len(label_lines)
            for line in label_lines:
                d.text((LEFT - 12, ly), line, font=fonts['text'], fill=INK, anchor='ra')
                ly += 18
            notes = row.get('notes') or [''] * n
            hosts = row.get('hosts') or [None] * n
            missing = row.get('missing') or [''] * n
            for i, v in enumerate(row['values']):
                by = y + i * (BAR + BAR_GAP)
                if v is None:
                    d.rectangle((LEFT, by, LEFT + 40, by + BAR - 1), outline=MUTED, width=1)
                    d.text((LEFT + 48, by + 1), missing[i] or 'not measured yet (TODO)', font=fonts['small'], fill=MUTED)
                    continue
                w = max(2, PLOT * v / top)
                d.rounded_rectangle((LEFT, by, LEFT + w, by + BAR - 1), radius=3, fill=SERIES_COLOURS[i])
                text = '%s %s' % (_fmt(v), panel['unit'])
                if hosts[i]:
                    text += ' (%s)' % hosts[i]
                if i == 1 and panel.get('ratio'):
                    ratio = _ratio(row['values'], panel.get('lower_is_better', True))
                    if ratio:
                        text += ' = %s' % ratio
                if notes[i]:
                    text += '  ' + notes[i]
                d.text((LEFT + w + 6, by + 1), text, font=fonts['small'], fill=INK)
            y += row_h
        y += 26
    for line in foot_lines:
        d.text((20, y), line, font=fonts['small'], fill=INK2)
        y += 14
    pal = img.quantize(colors=32, dither=Image.Dither.NONE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pal.save(out_path, optimize=True)
    return out_path


def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    validate(data)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('command', choices=('check', 'write'))
    ap.add_argument('data')
    ap.add_argument('--out', default='docs/images')
    ap.add_argument('--only', action='append', default=[])
    args = ap.parse_args(argv)
    try:
        data = load(args.data)
    except (GraphError, json.JSONDecodeError, OSError) as exc:
        print('release_graphs: %s' % exc, file=sys.stderr)
        return 1
    if args.command == 'check':
        print('release_graphs: %d charts valid' % len(data['charts']))
        return 0
    known = {c['id'] for c in data['charts']}
    unknown = sorted(set(args.only) - known)
    if unknown:
        print('release_graphs: unknown chart id(s): %s' % ', '.join(unknown), file=sys.stderr)
        return 1
    for chart in data['charts']:
        if args.only and chart['id'] not in args.only:
            continue
        path = render(chart, Path(args.out) / chart['file'])
        print('wrote %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
