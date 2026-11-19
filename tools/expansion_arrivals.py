#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp's arrivals in the expansions (DBG-TP-EXPANSION-ARRIVALS-66; docs/AMIWIND_CONSOLE_COMMANDS.md): the places of
config/expansion-arrivals.json (`dbg tp mournhold`, `dbg tp solstheim`, `dbg tp skaal`, ...) as rows of the image's
teleport-names.txt, the named places the engine reads (engine/aga/src/aw_scene.c named_place). The image step writes
them where it knows what it holds (tools/build_aga.py write_world_doors).

Each place is where the original itself puts the player: a script's PositionCell, a travel service's destination,
where a door puts the player. A place is present when the build selected its master (mwad.masters, AMIWIND_MASTERS)
and the image holds it:
  a room place      the image holds its cell's room map; the row is that map and the arrival in the map's own units,
                    the same arrival a script's PositionCell into the room compiles to (mwscript.rooms.arrival)
  an outdoor place  a town or CHIM region frame of the image holds the point (world_doors.holder); the row's map is
                    "global" and its point the original's global units, the height LIFT above the arrival (the
                    floor at or below it, as the settlement list's arrivals, tools/tp_places_lut.py)
Otherwise the row's map is "-" (NOT_HERE) and its label says why: the expansion is not in the build, or the image
does not hold the place yet. The engine prints that label and leaves the player where he is.

The smoke hops follow the image: hops() gives the hop lines for every place marked "hop" whose row the image's
teleport-names.txt holds as a working destination, nothing for the others (no hop and no failure without the
expansion).

  python3 tools/expansion_arrivals.py hops --id1 IMAGE/boot/id1 --base HOPS.txt [--out FILE]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

NOT_HERE = '-'              # world_doors.NOT_HERE: a place this image does not hold (aw_scene.c named_place)
GLOBAL = 'global'           # world_doors.GLOBAL_PLACE
LINE_BYTES = 190            # the engine reads lines of 192 bytes (named_place)
HOP_WAIT = 45               # seconds after each tp, as the delivery's hop script waits (DEV2-MAP-CHANGES-66)


def load():
    """The places of config/expansion-arrivals.json, checked (check)."""
    # the literal file name: the image stage's key reads this file, not the whole config/ folder (BUILD-SURVEY-KEY-CONFIG-35)
    return check(json.loads((ROOT / 'config' / 'expansion-arrivals.json').read_text(encoding='utf-8'))['places'])


def check(places):
    """PLACES, each checked: names (lower-case letters and digits, at most 23 characters, each once), master, place,
    label, at [x, y, z], and either a cell (a room place) or outdoors. Raises ValueError."""
    seen = set()
    for place in places:
        names = place.get('names') or []
        if (not names or not place.get('master') or not place.get('place') or not place.get('label')
                or len(place.get('at') or ()) != 3 or bool(place.get('cell')) == bool(place.get('outdoors'))):
            raise ValueError('expansion-arrivals.json: a place without names, master, place, label, at, or one of '
                             'cell and outdoors: %r' % place)
        for name in names:
            if not name or len(name) > 23 or not all('a' <= c <= 'z' or c.isdigit() for c in name) or name in seen:
                raise ValueError('expansion-arrivals.json: a bad or repeated name %r' % name)
            seen.add(name)
    return places


def number(value):
    """A coordinate as the config's rows write it: at most 4 decimals, no trailing zeros."""
    text = ('%.4f' % value).rstrip('0').rstrip('.')
    return '0' if text in ('', '-0') else text


def refusal(place, selected):
    """The label of a place this image does not hold: the expansion is not in the build, or the place not yet."""
    if not selected:
        master = place['master']
        return '%s is not in this build: it needs %s (%s).' % (place['place'], master.rsplit('.', 1)[0], master)
    return '%s is not in this build yet: this image does not hold it.' % place['place']


def rows(places, masters, rooms, holds=None, offsets=None):
    """One row per name of every place: {'name', 'map', 'at', 'yaw', 'label', 'state', 'place'}. MASTERS: the build's
    selected masters; ROOMS: {cell casefold: map} of the room maps the image holds; HOLDS(point): true when a frame of
    the image holds an outdoor point (world_doors.holder); OFFSETS: {cell casefold: offset} of the recentred rooms
    (town_interiors.room_offsets). state: 'present', 'needs the expansion' or 'not held'."""
    from mwscript.rooms import arrival
    from tp_places_lut import LIFT
    selected = {m.casefold() for m in masters}
    offsets = offsets or {}
    out = []
    for place in places:
        wanted = place['master'].casefold() in selected
        target, at, yaw, state = NOT_HERE, [0.0, 0.0, 0.0], 0.0, 'needs the expansion'
        if wanted:
            state = 'not held'
            if place.get('cell'):
                key = place['cell'].casefold()
                if rooms.get(key):
                    ax, ay, az, yaw = arrival(place['at'], float(place.get('facing', 0)), offsets.get(key))
                    target, at, state = rooms[key], [ax, ay, az], 'present'
            elif holds is not None and holds(place['at']):
                x, y, z = place['at']
                target, at, state = GLOBAL, [x, y, z + LIFT], 'present'
        label = place['label'] if state == 'present' else refusal(place, wanted)
        for name in place['names']:
            out.append({'name': name, 'map': target, 'at': at, 'yaw': yaw, 'label': label, 'state': state,
                        'place': place['place']})
    return out


def line(row):
    """The teleport-names.txt line of a row (name|map|x y z|yaw|label)."""
    return '%s|%s|%s|%s|%s' % (row['name'], row['map'], ' '.join(number(v) for v in row['at']), number(row['yaw']),
                               row['label'])


def text(base, table):
    """The image's teleport-names.txt: BASE (config/teleport-names.txt, bytes) and one line per row of TABLE, checked
    as the engine reads it (world_doors.teleport_names: no name twice, the field lengths; every line within LINE_BYTES)."""
    import world_doors
    body = base.decode('cp1252')
    if not body.endswith('\n'):
        body += '\n'
    lines = [line(row) for row in table]
    out = (body + '# The expansions\' arrivals (config/expansion-arrivals.json, tools/expansion_arrivals.py): a map of "-" is a\n'
           '# place this image does not hold; its label says why, and the player stays where he is.\n'
           + ''.join(l + '\n' for l in lines)).encode('cp1252')
    world_doors.teleport_names(out)
    long = [l for l in lines if len(l.encode('cp1252')) > LINE_BYTES]
    if long:
        raise ValueError('teleport-names.txt: lines longer than the engine reads: %s' % long)
    return out


def summary(table):
    """The receipt's view: {name: {'state', 'map'}} and the counts by state."""
    states = {}
    for row in table:
        states[row['state']] = states.get(row['state'], 0) + 1
    return {'rows': {row['name']: {'state': row['state'], 'map': row['map']} for row in table}, 'states': states}


def hops(names, places):
    """The smoke hop lines (the delivery hop script's form) for every place marked hop whose first name NAMES
    (an image's teleport-names.txt, bytes) holds as a working destination; [] when the image holds none of them."""
    import world_doors
    held = world_doors.teleport_names(names)
    out = []
    for place in places:
        name = place['names'][0]
        if place.get('hop') and name in held and held[name][0] != NOT_HERE:
            out += ['cmd dbg tp %s' % name, 'wait %d' % HOP_WAIT, 'state map', 'shot hop-%s' % name, 'state frame_ms']
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='command', required=True)
    h = sub.add_parser('hops', help='a hop script: BASE and a hop for every hop place the image holds')
    h.add_argument('--id1', type=Path, required=True, help="the image's id1 folder (its teleport-names.txt)")
    h.add_argument('--base', type=Path, required=True, help='the base hop script')
    h.add_argument('--out', type=Path, help='write the script here (else print it)')
    a = p.parse_args(argv)
    extra = hops((a.id1 / 'teleport-names.txt').read_bytes(), load())
    script = a.base.read_text(encoding='utf-8')
    if not script.endswith('\n'):
        script += '\n'
    script += ''.join(l + '\n' for l in extra)
    if a.out:
        a.out.write_text(script, encoding='utf-8', newline='\n')
        print('hops: %d expansion hops added (%s)' % (len(extra) // 5, ', '.join(l.split()[-1] for l in extra
                                                                             if l.startswith('cmd ')) or 'none'))
    else:
        sys.stdout.write(script)
    return 0


if __name__ == '__main__':
    sys.exit(main())
