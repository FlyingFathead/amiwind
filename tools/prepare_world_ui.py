#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake private world-map pixels and indexed journal text from owned base data."""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PIL import Image
from mwad.audit import records, subrecords, string
from mwad.paths import ensure_external, child_ci
from build_scratch import scratch_dir

WORLD_UI_FILES = ('map.awm', 'journal.awj', 'entries.dat', 'quests.awq', 'region-names.awn', 'region-weather.aww')
NO_NAME = 0xFFFFFFFF  # region-names.awn row without a region or place
# Region weather (SKY-REDMOUNTAIN-BLUE-44, docs/DAY_NIGHT_AND_SKY.md "Region weather"): the ten weathers in the order of a REGN
# record's WEAT chances, named as their Morrowind.ini [Weather NAME] sections.
WEATHERS = ('Clear', 'Cloudy', 'Foggy', 'Overcast', 'Rain', 'Thunderstorm', 'Ashstorm', 'Blight', 'Snow', 'Blizzard')
# Colour stops in the engine's order (r_sky.c sky_rgb_stops / fog_rgb_stops: day, sunrise, sunset, night).
WEATHER_STOPS = ('Day', 'Sunrise', 'Sunset', 'Night')
WEATHER_REGIONS_MAX = 256     # region rows the engine holds (aw_weather.h AW_WEATHER_REGIONS)
WEATHER_HOURS = 20            # [Weather] Hours Between Weather Changes as Morrowind.ini ships it
# The values Morrowind.ini ships with, used when the data folder holds no Morrowind.ini (the staged inputs carry only
# the masters and archives): per weather the sky stops, the fog stops (both day, sunrise, sunset, night), the
# Transition Delta (per real second) and the Glare View. Clear equals the engine's own clear-weather stops.
WEATHER_FALLBACK = {
    'Clear': (((95, 135, 203), (117, 141, 164), (56, 89, 129), (9, 10, 11)),
              ((206, 227, 255), (255, 189, 157), (255, 189, 157), (9, 10, 11)), .015, 1.0),
    'Cloudy': (((117, 160, 215), (126, 158, 173), (111, 114, 159), (9, 10, 11)),
               ((245, 235, 224), (255, 207, 149), (255, 155, 106), (9, 10, 11)), .015, 1.0),
    'Foggy': (((184, 211, 228), (197, 190, 180), (142, 159, 176), (18, 23, 28)),
              ((150, 187, 209), (173, 164, 148), (113, 135, 157), (19, 24, 29)), .015, .25),
    'Overcast': (((143, 146, 149), (91, 99, 106), (108, 115, 121), (19, 22, 25)),
                 ((143, 146, 149), (91, 99, 106), (108, 115, 121), (19, 22, 25)), .015, 0.0),
    'Rain': (((116, 120, 122), (71, 74, 75), (73, 73, 73), (24, 25, 26)),
             ((116, 120, 122), (71, 74, 75), (73, 73, 73), (24, 25, 26)), .015, 0.0),
    'Thunderstorm': (((97, 104, 115), (35, 36, 39), (35, 36, 39), (19, 20, 22)),
                     ((97, 104, 115), (70, 74, 85), (70, 74, 85), (19, 20, 22)), .030, 0.0),
    'Ashstorm': (((124, 73, 58), (91, 56, 51), (106, 55, 40), (20, 21, 22)),
                 ((124, 73, 58), (91, 56, 51), (106, 55, 40), (20, 21, 22)), .035, 0.0),
    'Blight': (((90, 35, 35), (90, 35, 35), (92, 33, 33), (44, 14, 14)),
               ((128, 19, 19), (90, 35, 35), (92, 33, 33), (44, 14, 14)), .040, 0.0),
    'Snow': (((153, 158, 166), (106, 91, 91), (96, 115, 134), (31, 35, 39)),
             ((153, 158, 166), (106, 91, 91), (96, 115, 134), (31, 35, 39)), .015, 0.0),
    'Blizzard': (((121, 133, 145), (91, 99, 106), (108, 115, 121), (27, 29, 31)),
                 ((121, 133, 145), (91, 99, 106), (108, 115, 121), (21, 24, 28)), .030, 0.0),
}
# World map file format (docs/WORLD_MAP_AND_JOURNAL.md "Map file formats"): v1 = AWM1 (terrain pixels and
# settlements), v2 = AWM2 (AWM1 plus the LAVA section: the molten lava pools of the exterior cells). Builder option
# --world-map (config key world_map), exported to this stage as AMIWIND_WORLD_MAP; v1 stays selectable.
WORLD_MAPS = ('v1', 'v2')
DEFAULT_WORLD_MAP = 'v2'
WORLD_MAP_VARIABLE = 'AMIWIND_WORLD_MAP'
LAVA_TAG = b'LAVA'
LAVA_RGB = (255, 72, 24)      # the lava glow colour (tools/lava.py GLOW_COLOUR), matched to the palette
LAVA_POINTS = 16              # outline points per pool the engine accepts
LAVA_POOLS_MAX = 2048         # pools per map the engine accepts
LAVA_TOLERANCE = 1.0          # Morrowind units: integer outline points stay within this of the pool's footprint
# Palette entries the sky overlay remaps (tools/sky_palette_overlay.BANK keys) or remaps onto (its targets):
# the lava colour avoids both, so no terrain pixel can turn into the lava colour later.
SKY_BANK_INDICES = (222, 133, 95, 156, 140, 83, 221, 223, 113, 94, 158, 138, 82)


def world_map_version(value=None):
    """The world map format to write: the argument, else AMIWIND_WORLD_MAP, else the shipped default (v2)."""
    value = value or os.environ.get(WORLD_MAP_VARIABLE) or DEFAULT_WORLD_MAP
    if value not in WORLD_MAPS:
        raise ValueError('world_map must be v1 or v2')
    return value


def export_world_map(value):
    """Export the resolved world map format for the world-ui stage and the image step."""
    os.environ[WORLD_MAP_VARIABLE] = world_map_version(value)


def display_name(raw_name, what):
    encoded = raw_name.encode('cp1252')
    if not encoded or len(encoded) >= 64 or any(c < 32 for c in encoded):
        raise ValueError('Invalid original '+what+' display name')
    return encoded


def region_names(raw):
    """Original exterior CELL coordinates -> RGNN ID -> REGN display name,
    plus the cell's own original name (Balmora, Seyda Neen, a camp or ruin):
    the area of interest the player is in. Format ARN2.

    Keep the source names intact. A cell without RGNN has no known region;
    neither a nearby region nor a generated vf map number supplies one.
    """
    regions = {}; cells = {}
    for tag, flags, payload in records(raw):
        if tag not in ('REGN', 'CELL'): continue
        fields = {}
        for key, value in subrecords(payload):
            if tag == 'CELL' and key == 'FRMR': break
            fields[key] = value
        if 'DELE' in fields: continue
        if tag == 'REGN':
            identifier = string(fields['NAME']).casefold()
            encoded = display_name(string(fields.get('FNAM', b'')), 'region')
            if identifier in regions: raise ValueError('Duplicate original region ID')
            regions[identifier] = encoded
        else:
            if len(fields.get('DATA', b'')) != 12: raise ValueError('Invalid CELL header')
            cell_flags, x, y = struct.unpack('<Iii', fields['DATA'])
            if cell_flags & 1: continue
            if (x, y) in cells: raise ValueError('Duplicate exterior cell coordinate')
            place = string(fields.get('NAME', b''))
            cells[x, y] = (string(fields.get('RGNN', b'')).casefold(),
                           display_name(place, 'cell') if place else b'')
    names = sorted(regions); places = sorted({p for r, p in cells.values() if p})
    if len(names) > 1024 or len(places) > 1024 or len(cells) > 65536:
        raise ValueError('Region catalogue exceeds runtime bounds')
    indices = {name: i for i, name in enumerate(names)}
    place_indices = {name: i for i, name in enumerate(places)}
    rows = []
    for (x, y), (identifier, place) in sorted(cells.items()):
        if not identifier and not place: continue
        if identifier and identifier not in indices: raise ValueError('CELL references missing REGN: '+identifier)
        rows.append(struct.pack('<iiII', x, y, indices[identifier] if identifier else NO_NAME,
                                place_indices[place] if place else NO_NAME))
    return (b'ARN2' + struct.pack('<III', len(names), len(places), len(rows))
            + b''.join(regions[name].ljust(64, b'\0') for name in names)
            + b''.join(place.ljust(64, b'\0') for place in places) + b''.join(rows))


def _ini_file(data_files):
    if data_files is None:
        return None
    for parent in (Path(data_files), Path(data_files).parent):
        for p in parent.iterdir() if parent.is_dir() else ():
            if p.name.casefold() == 'morrowind.ini':
                return p
    return None


def weather_settings(data_files=None, ini_text=None):
    """The ten weathers' sky and fog stops, transition speed and glare, and the hours between weather changes:
    from Morrowind.ini ([Weather NAME] Sky/Fog Day/Sunrise/Sunset/Night Color, Transition Delta, Glare View;
    [Weather] Hours Between Weather Changes) where the data folder or its parent holds one, else the shipped values
    (WEATHER_FALLBACK). Returns (settings, hours, info); info names the source and every value taken from the
    fallback."""
    ini = None if ini_text is not None else _ini_file(data_files)
    if ini is not None:
        ini_text = ini.read_bytes().decode('cp1252', 'replace')
    sections = {}
    section = ''
    for line in (ini_text or '').splitlines():
        line = line.strip()
        if line.startswith('['):
            section = line.strip('[]').casefold(); continue
        if '=' in line:
            name, value = line.split('=', 1)
            sections.setdefault(section, {})[name.strip().casefold()] = value.strip()
    notes = []

    def colour(fields, key, fallback):
        try:
            parts = [int(v) for v in fields[key].split(',')]
        except (KeyError, ValueError):
            notes.append(key); return tuple(fallback)
        if len(parts) != 3 or not all(0 <= v <= 255 for v in parts):
            notes.append(key); return tuple(fallback)
        return tuple(parts)

    def number(fields, key, fallback, low, high):
        try:
            value = float(fields[key])
        except (KeyError, ValueError):
            notes.append(key); return fallback
        if not low <= value <= high:
            notes.append(key); return fallback
        return value

    settings = {}
    for weather in WEATHERS:
        sky, fog, delta, glare = WEATHER_FALLBACK[weather]
        fields = sections.get('weather ' + weather.casefold(), {})
        settings[weather] = {
            'sky': [colour(fields, 'sky %s color' % stop.casefold(), sky[i]) for i, stop in enumerate(WEATHER_STOPS)],
            'fog': [colour(fields, 'fog %s color' % stop.casefold(), fog[i]) for i, stop in enumerate(WEATHER_STOPS)],
            'delta': number(fields, 'transition delta', delta, 0.001, 1.0),
            'glare': number(fields, 'glare view', glare, 0.0, 1.0)}
    hours = number(sections.get('weather', {}), 'hours between weather changes', WEATHER_HOURS, 1, 240)
    info = {'ini': ini.name if ini is not None else ('text' if ini_text else None),
            'fallback_values': len(notes)}
    return settings, int(round(hours)), info


def region_weather(raw, settings=None, hours=WEATHER_HOURS):
    """region-weather.aww (AWW1): the weather chances of every region in region-names.awn's region order (sorted
    region IDs, the ARN2 index) and the ten weathers' looks. Header 'AWW1' <IIII> weathers, regions, hours between
    weather changes, 0; per weather 32 bytes: sky stops 4 x RGB, fog stops 4 x RGB (day, sunrise, sunset, night),
    <H> Transition Delta x 1000, <B> Glare View x 100, 5 zero bytes; per region 10 chance bytes (REGN WEAT:
    clear, cloudy, foggy, overcast, rain, thunderstorm, ash, blight, snow, blizzard; the base game's 8-byte WEAT
    leaves snow and blizzard 0)."""
    if settings is None:
        settings = weather_settings(ini_text='')[0]
    chances = {}
    for tag, flags, payload in records(raw):
        if tag != 'REGN': continue
        fields = dict(subrecords(payload))
        if 'DELE' in fields: continue
        identifier = string(fields['NAME']).casefold()
        weat = bytes(fields.get('WEAT', b''))
        if len(weat) not in (8, 10):
            raise ValueError('Region %s has a WEAT of %d bytes (8 or 10 expected)' % (identifier, len(weat)))
        chances[identifier] = weat.ljust(len(WEATHERS), b'\0')
    names = sorted(chances)
    if len(names) > WEATHER_REGIONS_MAX:
        raise ValueError('Region weather table exceeds runtime bounds: %d regions' % len(names))
    out = bytearray(b'AWW1' + struct.pack('<IIII', len(WEATHERS), len(names), hours, 0))
    for weather in WEATHERS:
        look = settings[weather]
        out += bytes(v for stop in look['sky'] for v in stop) + bytes(v for stop in look['fog'] for v in stop)
        out += struct.pack('<HB5x', int(round(look['delta'] * 1000)), int(round(look['glare'] * 100)))
    for name in names:
        out += chances[name]
    return bytes(out)


def read_region_weather(raw):
    """Parse an AWW1 file: (looks, regions, hours) with looks per weather {'sky','fog','delta','glare'} and regions
    a list of chance tuples in region index order."""
    if raw[:4] != b'AWW1':
        raise ValueError('Not a region weather file')
    weathers, count, hours, _ = struct.unpack_from('<IIII', raw, 4)
    if weathers != len(WEATHERS) or count > WEATHER_REGIONS_MAX or len(raw) != 20 + 32*weathers + 10*count:
        raise ValueError('Region weather file has the wrong shape')
    looks = []
    for w in range(weathers):
        row = raw[20+32*w:52+32*w]
        delta, glare = struct.unpack_from('<HB', row, 24)
        looks.append({'sky': [tuple(row[3*i:3*i+3]) for i in range(4)],
                      'fog': [tuple(row[12+3*i:15+3*i]) for i in range(4)], 'delta': delta/1000, 'glare': glare/100})
    base = 20 + 32*weathers
    return looks, [tuple(raw[base+10*i:base+10*i+10]) for i in range(count)], hours


def fixed(value,size):
    raw=value.encode('ascii')
    if not raw or len(raw)>=size or any(c<32 for c in raw):raise ValueError('Invalid journal identifier')
    return raw.ljust(size,b'\0')


def journal_assets(raw):
    kind=None;quest=None;entries={}
    for tag,flags,payload in records(raw):
        if tag not in ('DIAL','INFO'):continue
        f=dict(subrecords(payload))
        if tag=='DIAL':
            kind=f.get('DATA',b'\xff')[0];quest=string(f.get('NAME',b'')).lower()
        elif kind==4:
            if len(f.get('DATA',b''))!=12:raise ValueError('Malformed journal INFO data')
            stage=struct.unpack_from('<i',f['DATA'],4)[0]
            text=string(f['NAME']).replace('\r\n','\n').replace('\r','\n')
            body=text.encode('cp1252')+b'\0'
            if len(body)>8192 or b'\0' in body[:-1]:raise ValueError('Journal entry exceeds runtime text bounds')
            key=(quest,stage)
            if key in entries:raise ValueError('Ambiguous journal stage: '+str(key))
            entries[key]=body
    index=bytearray(b'AWJ1'+struct.pack('<I',len(entries)));blob=bytearray()
    for (quest,stage),body in sorted(entries.items()):
        index.extend(fixed(quest,64)+struct.pack('<iII',stage,len(blob),len(body)));blob.extend(body)
    return bytes(index),bytes(blob),len({key[0] for key in entries})


def quest_labels(raw, overrides):
    labels={}
    for tag,flags,payload in records(raw):
        if tag!='DIAL':continue
        f=dict(subrecords(payload))
        if f.get('DATA')!=b'\x04':continue
        source=string(f['NAME']);identifier=source.lower()
        # Base master has no QSTN quest titles. Derived labels are display-only;
        # source identifiers remain the lookup/save identity.
        words=re.sub(r'^[A-Za-z]+[0-9]*(?:_[0-9]+)?_', '', source)
        words=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',words).replace('_',' ')
        label=overrides.get(identifier,words or source)
        labels[identifier]=label
    result=bytearray(b'AWQ1'+struct.pack('<I',len(labels)))
    for identifier,label in sorted(labels.items()):
        value=label.encode('cp1252')
        if len(value)>=96 or b'\0' in value:raise ValueError('Quest label exceeds 95 bytes')
        result.extend(fixed(identifier,64)+value.ljust(96,b'\0'))
    return bytes(result)


def _area2(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _inside(point, hull, tolerance=0.0):
    """True when point lies in the counter-clockwise convex hull, allowing tolerance units outside each edge."""
    if len(hull) < 3:
        return bool(hull) and all(min(abs(point[i]-h[i]) for h in hull) <= tolerance for i in (0, 1))
    for i, a in enumerate(hull):
        b = hull[(i+1) % len(hull)]
        length = math.hypot(b[0]-a[0], b[1]-a[1])
        if length and _area2(a, b, point)/length < -tolerance:
            return False
    return True


def lava_outline(hull, limit=LAVA_POINTS):
    """At most limit integer points of a pool's convex footprint, never outside it: the vertex whose removal loses
    the least area is dropped until the limit holds (a convex outline minus a vertex stays inside it), then the
    points are rounded to whole Morrowind units (within LAVA_TOLERANCE of the footprint)."""
    points = [[float(p[0]), float(p[1])] for p in hull]
    while len(points) > limit:
        n = len(points)
        drop = min(range(n), key=lambda i: abs(_area2(points[i-1], points[i], points[(i+1) % n])))
        del points[drop]
    out = []
    for x, y in points:
        q = [int(round(x)), int(round(y))]
        if q not in out:
            out.append(q)
    if len(out) == 2:      # degenerate: keep the pool as one point at its centre
        out = [[int(round(sum(p[0] for p in points)/len(points))), int(round(sum(p[1] for p in points)/len(points)))]]
    return out


def lava_layer(pools, land=None):
    """LAVA section rows of the molten exterior pools (tools/lava.exterior_pools rows: cell, hull in world units),
    in the census order: {cell, points, bounds, pool}. With land (tools/lava_map.land_heights of the master, the
    default of the builder) the rows are the VISIBLE lava: rectangles where the land lies below the pool surface,
    none for a buried pool (WORLDMAP-LAVA-MISMATCH-36). Without land, the earlier method: one outline per pool
    from its whole footprint, at most 16 points (kept selectable). A pool known only by its position is one point."""
    if land is not None:
        import lava_map
        rows, _step = lava_map.rows_for(pools, land, LAVA_POOLS_MAX)
        return rows
    rows = []
    for index, pool in enumerate(pools):
        hull = pool.get('hull') or ([pool['position'][:2]] if pool.get('position') else [])
        if not hull:
            raise ValueError('Lava pool without footprint or position')
        points = lava_outline(hull)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        rows.append({'cell': [int(pool['cell'][0]), int(pool['cell'][1])], 'points': points,
                     'bounds': [min(xs), min(ys), max(xs), max(ys)], 'pool': index})
    if len(rows) > LAVA_POOLS_MAX:
        raise ValueError('Too many lava pools for the world map: %d' % len(rows))
    return rows


def check_lava_layer(rows, pools, land=None):
    """The layer check. With land (the visible-lava layer): every row belongs to a census pool in the same cell,
    lies inside that pool's footprint (within LAVA_TOLERANCE), and the layer agrees with the land
    (tools/lava_map.audit: painted on buried land, visible lava left out, land above the surface, per pool);
    the report carries the totals. Without land (the earlier whole-footprint layer): every census pool has its
    row in the same cell, the row's centre lies in the pool, and no row point lies outside its pool's footprint
    (beyond LAVA_TOLERANCE): the layer never paints non-lava."""
    if land is not None:
        import lava_map
        for row in rows:
            pool = pools[row['pool']] if 0 <= row.get('pool', -1) < len(pools) else None
            if pool is None:
                raise ValueError('Lava layer row without a census pool')
            if row['cell'] != [int(pool['cell'][0]), int(pool['cell'][1])]:
                raise ValueError('Lava layer row in the wrong cell: %r' % (row['cell'],))
            hull = pool.get('hull') or [pool['position'][:2]]
            if any(not _inside(p, hull, LAVA_TOLERANCE) for p in row['points']):
                raise ValueError('Lava layer outline leaves its pool in cell %r' % (row['cell'],))
        totals = lava_map.audit(rows, pools, land)['totals']
        return {'pools': len(pools), 'covered': len({r['pool'] for r in rows}), 'buried': totals['buried'],
                'cells': len({tuple(r['cell']) for r in rows}), 'points': sum(len(r['points']) for r in rows),
                'rects': len(rows), 'visible_area': totals['visible'], 'painted_area': totals['painted'],
                'overpaint_area': totals['overpaint'], 'missed_area': totals['missed'],
                'max_land_excess': totals['max_excess']}
    if len(rows) != len(pools):
        raise ValueError('Lava layer has %d pools, the census %d' % (len(rows), len(pools)))
    for row, pool in zip(rows, pools):
        hull = pool.get('hull') or [pool['position'][:2]]
        if row['cell'] != [int(pool['cell'][0]), int(pool['cell'][1])]:
            raise ValueError('Lava layer row in the wrong cell: %r' % (row['cell'],))
        if any(not _inside(p, hull, LAVA_TOLERANCE) for p in row['points']):
            raise ValueError('Lava layer outline leaves its pool in cell %r' % (row['cell'],))
        n = len(row['points'])
        centre = [sum(p[0] for p in row['points'])/n, sum(p[1] for p in row['points'])/n]
        if not _inside(centre, hull, LAVA_TOLERANCE):
            raise ValueError('Lava layer centre outside its pool in cell %r' % (row['cell'],))
    return {'pools': len(rows), 'covered': len(rows), 'cells': len({tuple(r['cell']) for r in rows}),
            'points': sum(len(r['points']) for r in rows)}


def lava_colour(palette, used):
    """The palette entry nearest the lava colour that no terrain pixel or the ocean fill uses and the sky overlay
    neither remaps nor remaps onto, so the colour on the map means lava and nothing else."""
    free = [i for i in range(256) if i not in used and i not in SKY_BANK_INDICES]
    if not free:
        raise ValueError('No free palette entry for the lava colour')
    return min(free, key=lambda i: (sum((palette[i*3+k]-LAVA_RGB[k])**2 for k in range(3)), i))


def lava_section(rows, colour):
    """LAVA section: tag and <III> pools, points, colour; per pool <hhHH4i> cell x, cell y, points, 0, bounds
    (x0, y0, x1, y1); then every point <ii> in pool order. Morrowind world units, little-endian."""
    raw = bytearray(LAVA_TAG + struct.pack('<III', len(rows), sum(len(r['points']) for r in rows), colour))
    for r in rows:
        raw.extend(struct.pack('<hhHH4i', r['cell'][0], r['cell'][1], len(r['points']), 0, *r['bounds']))
    for r in rows:
        for x, y in r['points']:
            raw.extend(struct.pack('<ii', x, y))
    return bytes(raw)


def lava_section_offset(raw):
    """Offset of the LAVA section of an AWM2 file (after the header, areas and pixels)."""
    width, height = struct.unpack_from('<HH', raw, 4)
    return 32 + 60 * struct.unpack_from('<I', raw, 24)[0] + width * height


def lava_section_colour(raw):
    return struct.unpack_from('<I', raw, lava_section_offset(raw) + 12)[0]


def map_asset(report, image, palette, version='v1', lava_rows=None):
    """map.awm: v1 = AWM1; v2 = the same bytes under AWM2 followed by the LAVA section of lava_rows."""
    if version not in WORLD_MAPS:raise ValueError('world_map must be v1 or v2')
    if len(palette)!=768:raise ValueError('Expected runtime palette')
    bounds=report['terrain_bounds'];dx=bounds[2]-bounds[0];dy=bounds[3]-bounds[1]
    height=512;width=round(height*dx/dy)
    if not 1<=width<=512: # Keep the longest dimension bounded.
        width=512;height=round(width*dy/dx)
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    background=Image.new('RGBA',image.size,(34,66,84,255));background.alpha_composite(image.convert('RGBA'))
    pixels=background.convert('RGB').resize((width,height),Image.Resampling.BOX).quantize(palette=pal,dither=Image.Dither.NONE).tobytes()
    areas=report['areas']
    raw=bytearray(b'AWM1'+struct.pack('<HH4iII',width,height,*[v*8192 for v in bounds],len(areas),Image.new('RGB',(1,1),(34,66,84)).quantize(palette=pal,dither=Image.Dither.NONE).getpixel((0,0))))
    for area in areas:
        stem={'Balmora':'balmora','Seyda Neen':'seyda'}[area['name']]
        raw.extend(fixed(stem,16)+fixed(area['name'],32)+struct.pack('<3f',*area['centre'],area['scale']))
    raw.extend(pixels)
    if version=='v2':
        raw[:4]=b'AWM2'
        raw.extend(lava_section(lava_rows or [],lava_colour(palette,set(pixels)|{raw[28]})))
    return bytes(raw)


def prepare(data_files,survey,scene,world_map=None,lava_pools=None):
    scene=ensure_external(scene,'private world UI');dest=scene/'id1/world';dest.mkdir(parents=True,exist_ok=True)
    master=child_ci(data_files,'Morrowind.esm').read_bytes()
    if survey is None:
        # Normal image builds need only the terrain overview, not the much
        # broader scenery-density survey. Use the same source terrain routine.
        from mwad.audit import load_esm, BSA
        from npc_geometry import Assets
        from survey_vvardenfell import terrain_arrays
        from world_survey import area_catalogue
        with scratch_dir('amiwind-world-map-') as directory:
            temp=Path(directory);source=load_esm(child_ci(data_files,'Morrowind.esm'))
            bounds,stats,terrain=terrain_arrays(source,temp,Assets(data_files,BSA(child_ci(data_files,'Morrowind.bsa'))))
            report={'master_sha256':source['sha256'],'terrain_bounds':bounds,
                    'areas':area_catalogue(Path(__file__).resolve().parents[1])}
            (temp/'world-survey.json').write_text(json.dumps(report))
            return prepare(data_files,temp,scene,world_map,lava_pools)
    report=json.loads((survey/'world-survey.json').read_text())
    if hashlib.sha256(master).hexdigest()!=report['master_sha256']:raise ValueError('Survey/master mismatch')
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    index,blob,quests=journal_assets(master)
    labels=quest_labels(master,json.loads((Path(__file__).resolve().parents[1]/'config/journal_titles.json').read_text()))
    version=world_map_version(world_map);lava_report=None;rows=None
    if version=='v2':
        if lava_pools is None:
            from lava import exterior_pools
            lava_pools=exterior_pools(data_files)
        import lava_map
        land=lava_map.land_heights(master)      # the visible lava only: land above a pool buries it (WORLDMAP-LAVA-MISMATCH-36)
        rows=lava_layer(lava_pools,land);lava_report=check_lava_layer(rows,lava_pools,land)
    worldmap=map_asset(report,Image.open(survey/'terrain.png'),palette,version,rows)
    looks,hours,weather_info=weather_settings(data_files)
    for name,raw in [('map.awm',worldmap),('journal.awj',index),('entries.dat',blob),('quests.awq',labels),
                     ('region-names.awn',region_names(master)),('region-weather.aww',region_weather(master,looks,hours))]:
        (dest/name).write_bytes(raw)
    receipt={'format':'AmiWind world UI 1','master_sha256':report['master_sha256'],
             'palette_sha256':hashlib.sha256(palette).hexdigest(),'journal_quests':quests,
             'journal_entries':(len(index)-8)//76,'journal_text_bytes':len(blob),'map_bytes':len(worldmap),
             'region_weather':dict(weather_info,hours=hours),
             'files':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in WORLD_UI_FILES}}
    if version=='v2':
        # v1 keeps its receipt byte for byte; v2 records the format and the lava coverage check.
        receipt['map_format']='AWM2';receipt['lava_layer']=dict(lava_report,colour=lava_section_colour(worldmap))
    (dest/'conversion.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def prepare_image(data_files, scene):
    """The image step's world UI (prepare with no survey: the terrain overview from the master) as its own timed
    phase. build_aga.build_image runs it in a spawned worker beside the combat data and the player view (about 10 s
    on one core, none of which reads or writes id1/world or the palette), then validates it where it ran before
    (BUILD-IMAGE-FINALIZE-UNDERUSED-48)."""
    import build_profile
    with build_profile.phase('Image: world UI', detail='beside the combat data and the player view'):
        return prepare(data_files, None, scene)


def validate(id1):
    dest=Path(id1)/'world';receipt=json.loads((dest/'conversion.json').read_text())
    expected=set(WORLD_UI_FILES)
    if receipt.get('format')!='AmiWind world UI 1' or set(receipt.get('files',{}))!=expected:
        raise ValueError('Incomplete world/journal conversion receipt')
    if receipt['palette_sha256']!=hashlib.sha256((Path(id1)/'gfx/palette.lmp').read_bytes()).hexdigest():
        raise ValueError('World map palette is stale; regenerate world UI assets')
    for name,digest in receipt['files'].items():
        if hashlib.sha256((dest/name).read_bytes()).hexdigest()!=digest:raise ValueError('World UI hash mismatch: '+name)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--survey',type=Path,help='Reuse a complete survey; absent builds only the overview');p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--world-map',choices=WORLD_MAPS,default=None,help='Map file format: v2 (default: with the lava pools) or v1 (terrain and settlements only)')
    a=p.parse_args();prepare(a.data_files,a.survey,a.scene,a.world_map)
    print(json.dumps(validate(a.scene/'id1'),indent=2))
