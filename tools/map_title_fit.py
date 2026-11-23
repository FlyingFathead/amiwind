# SPDX-License-Identifier: GPL-3.0-only
"""Which place names fit the map's title in the game's font (MAP-VERSION-2-DEFAULT-68).

Map version 2 names the place the player is in in its title bar's plaque, the way the original's map window does: a
room's own name, an outdoor cell's own name, else its region's name (engine/aga/src/aw_worldui.c map_title_set). The
name is drawn in the game's own font (the inventory title's, gfx/book12.awf, else gfx/magic12.awf: aw_ui.c
small_font_begin) when it fits the plaque, else in the console glyphs (4 pixels a character), else cut with "...". The
rule is the shared layout helper's (aw_layout.c AW_LayoutTitle; its numbers in aw_layout_metrics), repeated here.

This tool measures every name an image can show there, from the image's own tables: the region and place names of
world/region-names.awn (the three masters' regions and named outdoor cells, Mournhold's districts included) and the
room names of the image's cell-numbers.json (every interior of the three masters), in the image's own title font, and
records which fall back to the console glyphs:

    python3 tools/map_title_fit.py --id1 RUN/image/boot/id1 --cells RUN/image/cell-numbers.json [--out REPORT.json]

or with the names read straight from the three masters (every region's display name, every named outdoor cell and
every interior cell of Morrowind.esm, Tribunal.esm and Bloodmoon.esm, built or not) and the image's font:

    python3 tools/map_title_fit.py --id1 RUN/image/boot/id1 --masters DATA_FILES

It prints the counts, the widest names of each kind and every name that falls back. Seconds; reads only.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_C = ROOT / 'engine' / 'aga' / 'src' / 'aw_layout.c'
FORMAT = 'aw-map-title-fit-1'
BAR_W = 308            # the map's title bar (aw_worldui.c mapv2_chrome: the window's, as the inventory's: 6,6 308 wide)
PLAQUE_MARGIN = 14     # aw_layout_metrics.plaque_margin (aw_icons.c title_bar: the text's width + 14)
PLAQUE_END = 3         # aw_layout_metrics.plaque_end
CONSOLE_CHAR = 4       # aw_layout_metrics.console_char (aw_console_glyphs.c AW_SmallStringColor)
NAME_MAX = 63          # aw_worldui.c map_name[64]
FONTS = ('gfx/book12.awf', 'gfx/magic12.awf')   # aw_ui.c small_font_begin: the first valid one
NO_NAME = 0xFFFFFFFF


def layout_numbers(text=None):
    """{field: value} of aw_layout.c's aw_layout_metrics table (the numbers this tool repeats)."""
    text = LAYOUT_C.read_text(encoding='utf-8') if text is None else text
    body = text[text.index('aw_layout_metrics={'):]
    body = body[:body.index('};')]
    return {name: int(value) for value, name in re.findall(r'(\d+),?\s*/\*\s*(\w+)', body)}


def font_advances(raw):
    """The 256 advances of an AWF1 font (aw_ui.c AW_UIValidateFont's checks; chars 2 and 3, the dialogue's link marks,
    have none: aw_ui.c advance); None when RAW is not a valid font."""
    n = len(raw)
    if n < 2056 or raw[:4] != b'AWF1' or raw[4] not in (12, 14, 16) or raw[5] != raw[4] + 2 or n > 26624:
        return None
    if n != 2056 + struct.unpack('<H', raw[6:8])[0]:
        return None
    advances = []
    for c in range(256):
        m = raw[8 + c * 8:16 + c * 8]
        offset = struct.unpack('<H', m[:2])[0]
        w, h, ox, oy, adv, pad = m[2], m[3], struct.unpack('b', m[4:5])[0], struct.unpack('b', m[5:6])[0], m[6], m[7]
        if w > 32 or h > 32 or adv > 32 or pad or offset + (w * h + 3) // 4 > n - 2056 or not -32 <= ox <= 32 \
                or not -32 <= oy <= 32:
            return None
        advances.append(0 if c in (2, 3) else adv)
    return advances


def text_width(name, advances):
    """NAME's width in pixels in the font (aw_ui.c AW_UIWidth: the advances summed, Windows-1252 bytes)."""
    return sum(advances[b] for b in name)


def fit(game_w, chars):
    """aw_layout.c AW_LayoutTitle: ('game' | 'console' | 'cut', the plaque's width, the glyphs shown)."""
    room = max(0, BAR_W - 2 * PLAQUE_END - PLAQUE_MARGIN)
    if 0 <= game_w <= room:
        return 'game', game_w + PLAQUE_MARGIN, chars
    if chars * CONSOLE_CHAR <= room:
        return 'console', chars * CONSOLE_CHAR + PLAQUE_MARGIN, chars
    chars = room // CONSOLE_CHAR
    return 'cut', chars * CONSOLE_CHAR + PLAQUE_MARGIN, chars


def region_names(raw):
    """(region names, place names) of an ARN2 file (tools/prepare_world_ui.py region_names), as bytes, the places a
    cell names (every place label is a cell's own name)."""
    if raw[:4] != b'ARN2':
        raise ValueError('region names: not ARN2')
    names, places, cells = struct.unpack('<III', raw[4:16])
    if len(raw) != 16 + (names + places) * 64 + cells * 16:
        raise ValueError('region names: wrong size')
    label = lambda i: raw[16 + i * 64:16 + i * 64 + 64].split(b'\0')[0]
    return [label(i) for i in range(names)], [label(names + i) for i in range(places)]


def room_names(cells):
    """The rooms' names of an image's cell-numbers.json (tools/cell_numbers.py), as the maps' worldspawn carries them."""
    return sorted({m['cell'].encode('cp1252') for m in cells.get('maps', []) if m.get('cell')})


MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')


def _records(raw):
    i = 0
    while i + 16 <= len(raw):
        tag, size, _, flags = struct.unpack('<4sIII', raw[i:i + 16])
        yield tag, flags, raw[i + 16:i + 16 + size]
        i += 16 + size


def _subrecords(payload):
    j = 0
    while j + 8 <= len(payload):
        tag, n = struct.unpack('<4sI', payload[j:j + 8])
        yield tag, payload[j + 8:j + 8 + n]
        j += 8 + n


def master_names(folder):
    """(regions, places, rooms) straight from the three masters in FOLDER: every region's display name (REGN FNAM),
    every named outdoor cell's name and every interior cell's name (CELL NAME), as bytes; a deleted record is left out."""
    regions, places, rooms = set(), set(), set()
    for master in MASTERS:
        path = Path(folder) / master
        if not path.is_file():
            continue
        for tag, flags, payload in _records(path.read_bytes()):
            if tag not in (b'REGN', b'CELL'):
                continue
            fields = {}
            for key, value in _subrecords(payload):
                if key == b'FRMR':
                    break
                fields.setdefault(key, value)
            if b'DELE' in fields:
                continue
            if tag == b'REGN':
                name = fields.get(b'FNAM', b'').split(b'\0')[0]
                if name:
                    regions.add(name)
                continue
            name = fields.get(b'NAME', b'').split(b'\0')[0]
            data = fields.get(b'DATA', b'')
            if name and len(data) >= 4:
                (rooms if struct.unpack('<I', data[:4])[0] & 1 else places).add(name)
    return sorted(regions), sorted(places), sorted(rooms)


def measure(id1, cells_path=None, masters=None):
    """The report: the font, the rule's numbers, every name's width and font choice, the counts and the fallbacks."""
    id1 = Path(id1)
    font_file, advances = None, None
    for name in FONTS:
        path = id1 / name
        if path.is_file():
            advances = font_advances(path.read_bytes())
            if advances:
                font_file = name
                break
    if not advances:
        raise ValueError('no valid title font in %s (%s)' % (id1, ', '.join(FONTS)))
    if masters:
        regions, places, rooms = master_names(masters)
    else:
        regions, places = region_names((id1 / 'world' / 'region-names.awn').read_bytes())
        rooms = room_names(json.loads(Path(cells_path).read_text(encoding='utf-8')))
    rows = []
    for kind, names in (('region', regions), ('place', places), ('room', rooms)):
        for name in names:
            shown = name[:NAME_MAX]
            game_w = text_width(shown, advances)
            font, plaque, chars = fit(game_w, len(shown))
            rows.append({'kind': kind, 'name': name.decode('cp1252'), 'game_px': game_w, 'console_px': len(shown) * 4 - 1,
                         'chars': len(shown), 'font': font, 'plaque': plaque, 'held_to': NAME_MAX if len(name) > NAME_MAX else None})
    counts = {}
    for row in rows:
        counts.setdefault(row['kind'], {'names': 0, 'game': 0, 'console': 0, 'cut': 0})
        counts[row['kind']]['names'] += 1
        counts[row['kind']][row['font']] += 1
    widest = {kind: sorted((r for r in rows if r['kind'] == kind), key=lambda r: -r['game_px'])[:5] for kind in counts}
    return {'format': FORMAT, 'font': font_file, 'names_from': 'masters' if masters else 'image tables',
            'room_px': BAR_W - 2 * PLAQUE_END - PLAQUE_MARGIN,
            'rule': {'bar': BAR_W, 'plaque_margin': PLAQUE_MARGIN, 'plaque_end': PLAQUE_END,
                     'console_char': CONSOLE_CHAR, 'name_max': NAME_MAX},
            'counts': counts, 'widest': widest, 'fallbacks': [r for r in rows if r['font'] != 'game'], 'names': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--id1', required=True, help="the image's id1 folder (RUN/image/boot/id1)")
    parser.add_argument('--cells', help="the image's cell-numbers.json (RUN/image/cell-numbers.json)")
    parser.add_argument('--masters', help='read the names straight from Morrowind.esm, Tribunal.esm and Bloodmoon.esm '
                                          'in this folder instead of the image tables')
    parser.add_argument('--out', help='write the whole report (every name) as JSON here')
    args = parser.parse_args(argv)
    if not args.masters and not args.cells:
        parser.error('--cells or --masters')
    print('=== PHASE 1/2: the title font and the names ===', flush=True)
    report = measure(args.id1, args.cells, args.masters)
    print('=== PHASE 2/2: the fit (the game font up to %d pixels, then the console glyphs) ===' % report['room_px'],
          flush=True)
    print('font %s, names from the %s' % (report['font'], report['names_from']))
    for kind, c in report['counts'].items():
        print('%-6s %4d names: %4d in the game font, %3d in the console glyphs, %d cut' % (
            kind, c['names'], c['game'], c['console'], c['cut']))
        for r in report['widest'][kind]:
            print('    %3d px (%2d chars) %-8s %s' % (r['game_px'], r['chars'], r['font'], r['name']))
    print('%d names fall back to the console glyphs:' % len(report['fallbacks']))
    for r in report['fallbacks']:
        print('    %3d px %-6s %-8s %s' % (r['game_px'], r['kind'], r['font'], r['name']))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        print('report: %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
