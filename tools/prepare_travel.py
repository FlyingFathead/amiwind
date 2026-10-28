# SPDX-License-Identifier: GPL-3.0-only
"""The travel services table (TRAVEL-SERVICES-CHIM-51): every caravaner, shipmaster, gondolier and guild guide of the
user's own masters with its destinations, resolved to the maps of this image by the world door table's holder rule
(tools/world_doors.py: a town frame box, else the CHIM region frame of the cell, else the room), written to
id1/travel.txt for the engine (engine/aga/src/aw_travel_rules.c reads it; aw_scene.c opens the menu).

Nothing is invented: the destinations are the actors' own travel records (NPC_/CREA DODT position and rotation, DNAM
cell name for an interior), the prices and travel times the game settings fTravelMult, fTravelTimeMult and
fMagesGuildTravel. The rules are OpenMW's (rule from OpenMW file apps/openmw/mwgui/travelwindow.cpp; no code copied):
  - a provider standing in an interior (the guild guides) charges fMagesGuildTravel, and no time passes;
  - one standing outdoors charges the 3D distance from the player to the destination / fTravelMult (at least 1), and
    the ride takes the 2D distance / fTravelTimeMult whole hours;
  - a destination whose cell the game does not hold is not offered (OpenMW logs it); here a destination the image does
    not hold (a room not converted, Solstheim) is not offered either, and the receipt lists it with the reason.
Not yet applied (listed in the receipt): the barter adjustment of the price by disposition and Mercantile
(OpenMW mechanicsmanager getBarterOffer) and the price of travelling followers.

The engine computes the price and hours from the player's own position when its map can be turned back into the
original coordinates (aw_world.c AW_WorldToSource), else it uses the price and hours written here from the provider's
own placement.

File (cp1252 text, one record per line, '|' separated, no '|' inside a field):
  AWT1|<fTravelMult>|<fTravelTimeMult>|<fMagesGuildTravel>
  D|<provider id>|<interior 0/1>|<map>|<arrival x>|<y>|<z>|<yaw>|<source x>|<y>|<z>|<price>|<hours>|<label>
"""
import hashlib
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

FORMAT = 'AWT1'
FILE = 'travel.txt'
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
SETTINGS = {'ftravelmult': 4000.0, 'ftraveltimemult': 16000.0, 'fmagesguildtravel': 10.0}  # only if a master lacks one
ROWS_PER_PROVIDER = 4           # aw_travel.h AW_TRAVEL_ROWS (the most any provider offers; the menu box's rows)
LABEL_BYTES = 47                # aw_travel.h: the label buffer is 48 bytes


def destinations(fields):
    """[{position, rotation_radians, cell}] of one actor record's travel subrecords (DODT, then an optional DNAM)."""
    out, current = [], None
    for tag, data in fields:
        if tag == 'DODT':
            if len(data) != 24:
                raise ValueError('Invalid travel destination (DODT is %d bytes)' % len(data))
            values = struct.unpack('<6f', data)
            if not all(math.isfinite(v) for v in values):
                raise ValueError('Nonfinite travel destination')
            current = {'position': list(values[:3]), 'rotation_radians': list(values[3:]), 'cell': ''}
            out.append(current)
        elif tag == 'DNAM' and current is not None:
            current['cell'] = data.split(b'\0')[0].decode('cp1252')
    return out


def read_masters(data_files):
    """(providers, settings, cells) from the masters present, later masters replacing earlier records (the game's load
    order). providers: {id casefold: {kind, name, master, destinations}}; settings: the three game settings; cells: the
    Morrowind.esm cells (mwad.audit.cell_data) for placements and exterior names, and regions {id casefold: name}."""
    from mwad.audit import cell_data
    from mwad.esm import is_deleted, records, subrecords, text
    from mwad.paths import child_ci
    providers, settings, cells, regions = {}, dict(SETTINGS), [], {}
    found = []
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is None or not Path(path).is_file():
            continue
        found.append(name)
        for tag, flags, raw in records(Path(path).read_bytes()):
            if tag in ('NPC_', 'CREA'):
                fields = list(subrecords(raw))
                ident = text(fields, 'NAME').casefold()
                if is_deleted(flags, fields):
                    providers.pop(ident, None)
                    continue
                dests = destinations(fields)
                if dests:
                    providers[ident] = {'kind': tag, 'name': text(fields, 'FNAM'), 'master': name,
                                        'destinations': dests}
                else:
                    providers.pop(ident, None)
            elif tag == 'GMST':
                fields = dict(subrecords(raw))
                key = fields.get('NAME', b'').split(b'\0')[0].decode('cp1252').casefold()
                if key in SETTINGS:
                    if 'FLTV' in fields and len(fields['FLTV']) == 4:
                        settings[key] = struct.unpack('<f', fields['FLTV'])[0]
                    elif 'INTV' in fields and len(fields['INTV']) == 4:
                        settings[key] = float(struct.unpack('<i', fields['INTV'])[0])
            elif tag == 'REGN':
                fields = list(subrecords(raw))
                regions[text(fields, 'NAME').casefold()] = text(fields, 'FNAM')
            elif tag == 'CELL' and name == 'Morrowind.esm':
                cells.append(cell_data(list(subrecords(raw))))
    if 'Morrowind.esm' not in found:
        raise ValueError('Travel services: Morrowind.esm not found in ' + str(data_files))
    return providers, settings, cells, regions, found


def placements(providers, cells):
    """{provider id: (position, interior)} of each provider's first placement in Morrowind.esm."""
    out = {}
    for cell in cells:
        for ref in cell['refs']:
            ident = ref.get('id', '').casefold()
            if ident in providers and ident not in out and not ref.get('deleted') and 'position' in ref:
                out[ident] = (ref['position'], bool(cell['flags'] & 1))
    return out


def exterior_names(cells, regions):
    """{(x, y): the name an exterior cell shows: its own name, else its region's (OpenMW World::getCellName)}."""
    out = {}
    for cell in cells:
        if not cell['flags'] & 1:
            out[(cell['x'], cell['y'])] = cell['name'] or regions.get(cell['region'].casefold(), '') or 'Wilderness'
    return out


def price_hours(source, destination, interior, settings):
    """OpenMW travelwindow.cpp: the price and the hours of one ride from SOURCE (Morrowind units)."""
    if interior:
        return max(1, int(settings['fmagesguildtravel'])), 0
    d3 = math.dist(source, destination)
    d2 = math.dist(source[:2], destination[:2])
    mult, time_mult = settings['ftravelmult'], settings['ftraveltimemult']
    price = int(d3 / mult) if mult else int(d3)
    hours = int(d2 / time_mult) if time_mult else 0
    return max(1, price), hours


def clean_label(label):
    label = ''.join(c for c in label if c >= ' ' and c != '|')
    raw = label.encode('cp1252', 'replace')[:LABEL_BYTES]
    return raw.decode('cp1252')


def table(providers, settings, cells, regions, rooms, towns, frames, offsets=None):
    """(rows, left_out): one row per destination the image holds, and every one it does not, with the reason.
    rooms/towns/frames/offsets: as world_doors.table (frames = the region frames)."""
    from room_batches import exterior_cell
    from world_doors import exit_target, room_target
    offsets = offsets or {}
    where = placements(providers, cells)
    names = exterior_names(cells, regions)
    rows, left = [], []
    for ident in sorted(providers):
        p = providers[ident]
        place = where.get(ident)
        interior = bool(place and place[1])
        kept = 0
        for d in p['destinations']:
            label = d['cell'] or names.get(exterior_cell(d['position']), 'Wilderness')
            if d['cell']:
                target = room_target(d, d['cell'].casefold(), rooms, offsets)
                reason = 'room %s is not in this image' % d['cell']
            else:
                target = exit_target(d, towns, frames)
                reason = 'exterior cell %d,%d is in no frame of this image' % exterior_cell(d['position'])
            if target is None or kept >= ROWS_PER_PROVIDER:
                left.append({'provider': ident, 'destination': label,
                             'reason': reason if target is None else 'more than %d destinations' % ROWS_PER_PROVIDER})
                continue
            if place is None:
                price, hours = (price_hours([0, 0, 0], [0, 0, 0], True, settings) if interior else (1, 0))
                note = 'provider not placed in Morrowind.esm: price from the game setting only'
            else:
                price, hours = price_hours(place[0], d['position'], interior, settings)
                note = None
            row = {'provider': ident, 'name': p['name'], 'kind': p['kind'], 'master': p['master'],
                   'interior': interior, 'map': target[0], 'arrival': [round(v, 3) for v in target[1]],
                   'yaw': round(target[2], 3), 'source': [round(v, 1) for v in d['position']],
                   'price': price, 'hours': hours, 'label': clean_label(label)}
            if note:
                row['note'] = note
            rows.append(row)
            kept += 1
    return rows, left


def text(rows, settings):
    lines = ['%s|%.3f|%.3f|%d' % (FORMAT, settings['ftravelmult'], settings['ftraveltimemult'],
                                   int(settings['fmagesguildtravel']))]
    for r in rows:
        if '|' in r['provider'] or len(r['provider']) > 31 or len(r['map']) > 15:
            raise ValueError('Travel row does not fit the engine table: %s -> %s' % (r['provider'], r['map']))
        lines.append('D|%s|%d|%s|%.3f|%.3f|%.3f|%.3f|%.1f|%.1f|%.1f|%d|%d|%s' % (
            r['provider'], int(r['interior']), r['map'], *r['arrival'], r['yaw'], *r['source'], r['price'],
            r['hours'], r['label']))
    return '\n'.join(lines) + '\n'


def write(id1, data_files, rooms, towns, frames, offsets=None):
    """Write id1/travel.txt; returns the receipt (rows, left out, the rules not yet applied)."""
    providers, settings, cells, regions, found = read_masters(data_files)
    rows, left = table(providers, settings, cells, regions, rooms, towns, frames, offsets)
    body = text(rows, settings)
    path = Path(id1) / FILE
    path.write_bytes(body.encode('cp1252'))
    return {'format': FORMAT, 'masters': found, 'settings': settings, 'providers': len(providers),
            'providers_offered': len({r['provider'] for r in rows}), 'destinations': len(rows),
            'left_out': left, 'sha256': hashlib.sha256(body.encode('cp1252')).hexdigest(),
            'not_applied': ['barter adjustment by disposition and Mercantile (OpenMW getBarterOffer)',
                            'the price of travelling followers'],
            'rows': rows}
