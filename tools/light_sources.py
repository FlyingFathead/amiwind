#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Morrowind light sources mapped onto Quake's own light machinery.

Every original LIGH placement (lamp, candle, torch, fire, glow, darkener) gets
one class from its original model/ID and flags, a Quake lightstyle from its
original animation flags, and a Quake light entity for the map source.
Original lights never switch with the time of day (no light record or script
does); only the Off-by-default flag marks unlit props, which give no light. Steady
light is baked and costs nothing per frame; animated light uses Quake
lightstyles (surfaces rebuild only when a style value changes), grouped by
class so a face never needs more than Quake's four styles.

Usage (reads your own Morrowind.esm):
  light_sources.py census Morrowind.esm [--json report.json]
  light_sources.py lamp-table Morrowind.esm OUT.awl
The lamp table (AWL1) lists every exterior lamp, torch, fire and candle in
original coordinates, sorted by cell, for the engine's night lamp lights:
'AWL1', u32 count, then per lamp: i16 cell x, i16 cell y, f32 x, y, z,
u16 original radius, u8 class code, u8 colour (0 neutral, 1 warm, 2 cool)
(20 bytes, little-endian).
"""
import argparse, collections, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import records, subrecords, string

# Original LHDT flag bits.
NEGATIVE, FLICKER, FIRE, OFF_DEFAULT, FLICKER_SLOW, PULSE, PULSE_SLOW = 0x4, 0x8, 0x10, 0x20, 0x40, 0x80, 0x100
ANIMATED = FLICKER | FLICKER_SLOW | PULSE | PULSE_SLOW
# Quake lightstyles (id's QuakeC worldspawn numbering) plus AmiWind's switchable
# night-lamp style in Quake's switchable range (32 and up).
STYLE_NORMAL, STYLE_FLICKER, STYLE_GENTLE_PULSE, STYLE_FLICKER_SOFT, STYLE_SLOW_PULSE = 0, 1, 5, 6, 11
STYLE_NIGHT_LAMPS = 32
CLASSES = ('lamp', 'candle', 'torch', 'fire', 'glow_plant', 'negative', 'pure_light', 'other', 'off')


def classify(identifier, model, flags):
    """Class from the original model/ID first. The Fire flag is also set on
    candles and lanterns, so it only decides lights that name nothing else."""
    text = (identifier + ' ' + model).casefold()
    if flags & OFF_DEFAULT: return 'off'  # unlit prop: never a light source
    if flags & NEGATIVE: return 'negative'
    if 'torch' in text: return 'torch'
    if 'candle' in text or 'chandelier' in text: return 'candle'
    if any(k in text for k in ('lantern', 'lamp', 'streetlight', 'sconce')): return 'lamp'
    if 'mushroom' in text or 'shroom' in text: return 'glow_plant'
    if any(k in text for k in ('fire', 'flame', 'brazier', 'firepit')): return 'fire'
    if not model: return 'pure_light'
    if flags & FIRE: return 'fire'
    return 'other'


def quake_style(kind, flags, exterior):
    """Lightstyle for a placement. Outdoor lamps switch with night; animation
    flags pick the nearest of id's standard styles; everything else is steady."""
    if exterior and kind == 'lamp': return STYLE_NIGHT_LAMPS
    if flags & FLICKER: return STYLE_FLICKER
    if flags & FLICKER_SLOW: return STYLE_FLICKER_SOFT
    if flags & PULSE: return STYLE_GENTLE_PULSE
    if flags & PULSE_SLOW: return STYLE_SLOW_PULSE
    return STYLE_NORMAL


def colour_class(colour):
    r, g, b = colour
    if b > r and b > g: return 'cool'
    if r > b + 32: return 'warm'
    return 'neutral'


def light_records(raw):
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'LIGH': continue
        s = dict(subrecords(payload))
        if len(s.get('LHDT', b'')) != 24: continue
        identifier = string(s['NAME']); model = string(s.get('MODL', b''))
        lflags = struct.unpack_from('<I', s['LHDT'], 20)[0]
        out[identifier.casefold()] = {
            'id': identifier, 'model': model, 'radius': struct.unpack_from('<I', s['LHDT'], 12)[0],
            'colour': list(s['LHDT'][16:19]), 'flags': lflags, 'class': classify(identifier, model, lflags)}
    return out


def placements(raw, lights):
    """(cell key, light id, position) for every placed light; cell key is
    ('interior', name) or ('exterior', x, y)."""
    for tag, flags, payload in records(raw):
        if tag != 'CELL': continue
        subs = list(subrecords(payload))
        data = next((v for k, v in subs if k == 'DATA'), b'')
        if len(data) < 12: continue
        cell_flags, x, y = struct.unpack_from('<Iii', data)
        name = string(next((v for k, v in subs if k == 'NAME'), b''))
        key = ('interior', name) if cell_flags & 1 else ('exterior', x, y)
        current = None
        for k, v in subs:
            if k == 'FRMR': current = {}
            elif current is not None and k == 'NAME': current['id'] = string(v).casefold()
            elif current is not None and k == 'DATA' and len(v) == 24 and current.get('id') in lights:
                yield key, current['id'], struct.unpack_from('<3f', v); current = None


def entity(light, position, centre=(0.0, 0.0), scale=0.25, exterior=False):
    """Quake light entity text for the map source (ericw-tools light keys):
    1/d falloff ("delay" 1) like the original attenuation, original colour.
    Off-by-default lights get none (empty text)."""
    kind = light['class']
    if kind == 'off': return ''
    origin = [(position[0] - centre[0]) * scale, (position[1] - centre[1]) * scale, position[2] * scale]
    value = max(1, round(light['radius'] * scale))
    if kind == 'negative': value = -value
    style = quake_style(kind, light['flags'], exterior)
    colour = ' '.join('%.3f' % (c / 255) for c in light['colour'])
    text = '{\n"classname" "light"\n"origin" "%.2f %.2f %.2f"\n"light" "%d"\n"delay" "1"\n"_color" "%s"\n' % (
        *origin, value, colour)
    if style: text += '"style" "%d"\n' % style
    return text + '}'


LAMP_CLASSES = {'lamp': 1, 'torch': 2, 'fire': 3, 'candle': 4}
COLOUR_CODES = {'neutral': 0, 'warm': 1, 'cool': 2}
LAMP_ROW = struct.Struct('<hh3fHBB')


def lamp_table(raw):
    """AWL1 bytes: exterior warm light sources sorted by cell, then position."""
    lights = light_records(raw); rows = []
    for key, identifier, position in placements(raw, lights):
        light = lights[identifier]
        if key[0] != 'exterior' or light['class'] not in LAMP_CLASSES: continue
        if not (-32768 <= key[1] <= 32767 and -32768 <= key[2] <= 32767): raise ValueError('Cell out of range')
        rows.append((key[1], key[2], *position, min(light['radius'], 65535), LAMP_CLASSES[light['class']],
                     COLOUR_CODES[colour_class(light['colour'])]))
    rows.sort(key=lambda r: r[:5])
    return b'AWL1' + struct.pack('<I', len(rows)) + b''.join(LAMP_ROW.pack(*r) for r in rows)


def census(raw):
    lights = light_records(raw)
    per_class = collections.Counter(); per_cell = collections.Counter(); animated = collections.Counter()
    sides = collections.Counter(); colours = collections.Counter(); styles = collections.Counter()
    for key, identifier, position in placements(raw, lights):
        light = lights[identifier]; side = key[0]
        per_class[light['class']] += 1; per_cell[key] += 1; sides[side, light['class']] += 1
        colours[colour_class(light['colour'])] += 1
        styles[quake_style(light['class'], light['flags'], side == 'exterior')] += 1
        if light['flags'] & ANIMATED: animated[key] += 1

    def spread(side):
        values = sorted(n for k, n in per_cell.items() if k[0] == side)
        moving = sorted(animated.get(k, 0) for k in per_cell if k[0] == side)
        q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))] if v else 0
        busiest = max((k for k in per_cell if k[0] == side), key=lambda k: per_cell[k], default=None)
        return {'cells': len(values), 'median': q(values, .5), 'p90': q(values, .9), 'p99': q(values, .99),
                'max': values[-1] if values else 0, 'animated_median': q(moving, .5),
                'animated_p90': q(moving, .9), 'busiest': [str(p) for p in busiest[1:]] if busiest else None}
    return {'format': 'AmiWind light sources 1', 'light_records': len(lights),
            'placements': sum(per_class.values()),
            'classes': {k: {'placements': per_class[k], 'interior': sides['interior', k], 'exterior': sides['exterior', k]}
                        for k in CLASSES},
            'colours': dict(colours), 'styles': {str(k): v for k, v in sorted(styles.items())},
            'per_cell': {'interior': spread('interior'), 'exterior': spread('exterior')}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('census'); c.add_argument('master', type=Path); c.add_argument('--json', type=Path)
    t = sub.add_parser('lamp-table'); t.add_argument('master', type=Path); t.add_argument('out', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'lamp-table':
        data = lamp_table(args.master.read_bytes())
        args.out.write_bytes(data)
        print('lamps', struct.unpack_from('<I', data, 4)[0], 'bytes', len(data))
        return 0
    report = census(args.master.read_bytes())
    text = json.dumps(report, indent=2) + '\n'
    if args.json: args.json.write_bytes(text.encode('utf-8'))
    else: sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
