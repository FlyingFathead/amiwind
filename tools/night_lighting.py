#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Night lighting world tables for the boot image.

The engine reads three tables from id1/world/ (aw_lamps.c, aw_fog_location.c):

  lamps.awl          night lamp lights: every exterior lamp, torch, fire and
                     candle of your own Morrowind.esm (tools/light_sources.py
                     lamp-table; AWL1).
  night-windows.txt  per map, the BSP textures of window and lamp glass that
                     glow at night (tools/night_windows.py), traced through
                     the scenery sources the town maps were converted from.
  fog-locations.txt  per place day and night fog distance, a validated copy
                     of config/fog-locations.txt.

The image builder writes them after the final map optimisation, so the
window table names the textures of the maps that ship. Scenery sources the
build was not given are skipped and listed in the receipt: a town whose own
scenery is missing gets no window line (its glass stays dark) rather than a
guessed one. A table that fails its own format check stops the build.
"""
import collections
import fnmatch
import hashlib
import json
import re
import struct
from pathlib import Path

TABLES = ('world/lamps.awl', 'world/night-windows.txt', 'world/fog-locations.txt')
FOG_SOURCE = Path(__file__).resolve().parents[1] / 'config/fog-locations.txt'
FOG_LINE = re.compile(r'([A-Za-z0-9_]{1,63}) ([0-9]{3,4}) ([0-9]{3,4})')
FOG_RANGE = (100, 1500)  # aw_fog_location.c accepts local units in this range
FOG_MAX_BYTES = 16384
FOG_MAX_LINE = 126  # the engine reads lines into a 128-byte buffer
LAMP_ROW_BYTES = 20
LAMP_MAX_ROWS = 65536  # aw_lamps.c rejects larger tables
LAMP_CACHE = 256  # aw_lamps.c keeps this many lamps for the 3 x 3 cells around the player
# Town map groups and the patterns their maps match (as in the dev runs).
TOWN_PATTERNS = {'balmora': ('bm0[0-9][0-9]', 'balmora'),
                 'seyda': ('sn0[0-9][0-9]', 'seyda', 'intro_docks', 'sncourt')}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fog_table(raw):
    """Validated fog-locations bytes and their place count."""
    if not raw or len(raw) > FOG_MAX_BYTES:
        raise ValueError('Invalid fog location table size')
    if b'\r' in raw or not raw.endswith(b'\n'):
        raise ValueError('Fog location table must use LF line ends and end with one')
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError('Fog location table is not ASCII') from None
    places = set()
    for number, line in enumerate(text.split('\n')[:-1], 1):
        if len(line) > FOG_MAX_LINE or any(ord(c) < 32 or ord(c) == 127 for c in line):
            raise ValueError(f'Invalid fog location line {number}')
        if not line or line.startswith('#'):
            continue
        match = FOG_LINE.fullmatch(line)
        if not match:
            raise ValueError(f'Fog location line {number} is not "name day night"')
        name, day, night = match[1].lower(), int(match[2]), int(match[3])
        if not all(FOG_RANGE[0] <= v <= FOG_RANGE[1] for v in (day, night)):
            raise ValueError(f'Fog location distance out of range on line {number}')
        if name in places:
            raise ValueError('Duplicate fog location: ' + name)
        places.add(name)
    return raw, len(places)


def check_lamp_table(raw):
    """Lamp count of a valid AWL1 table: the engine's header, size and cell order."""
    if len(raw) < 8 or raw[:4] != b'AWL1':
        raise ValueError('Invalid lamp table header')
    count = struct.unpack_from('<I', raw, 4)[0]
    if count > LAMP_MAX_ROWS or len(raw) != 8 + count * LAMP_ROW_BYTES:
        raise ValueError('Invalid lamp table size')
    cells = [struct.unpack_from('<hh', raw, 8 + k * LAMP_ROW_BYTES) for k in range(count)]
    if cells != sorted(cells):
        raise ValueError('Lamp table is not sorted by cell')
    per_cell = collections.Counter(cells)
    busiest = max((sum(per_cell.get((x + dx, y + dy), 0) for dx in (-1, 0, 1) for dy in (-1, 0, 1)), x, y)
                  for x, y in per_cell) if per_cell else (0, 0, 0)
    if busiest[0] > LAMP_CACHE:
        raise ValueError('Lamp table: %d lamps around cell %d, %d exceed the engine cache of %d (LAMPS-CACHE-31)'
                         % (busiest + (LAMP_CACHE,)))
    return count


def check_window_table(raw):
    """Map line count of a valid night window table (ASCII, LF, sorted maps)."""
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError('Night window table is not ASCII') from None
    if b'\r' in raw or (raw and not raw.endswith(b'\n')):
        raise ValueError('Night window table must use LF line ends')
    names = []
    for line in text.split('\n')[:-1]:
        words = line.split(' ')
        if len(words) < 2 or not all(words) or any(len(w) > 31 for w in words):
            raise ValueError('Invalid night window line: ' + line[:40])
        names.append(words[0])
    if names != sorted(set(names)):
        raise ValueError('Night window maps are not sorted and unique')
    return len(names)


def scenery_sources(balmora_scenery=None, town_scenery=None, scene=None, world_flora=None):
    """Every scenery source the town maps can come from, in lookup order.

    A reference resolves in the first source listing it: town scenery first,
    then the opening barrel, then the world flora overlay.
    """
    def under(base, *parts):
        return Path(base).joinpath(*parts) if base else None
    return [
        {'name': 'balmora', 'role': 'town', 'patterns': TOWN_PATTERNS['balmora'],
         'option': '--balmora-scenery', 'directory': under(balmora_scenery)},
        {'name': 'seyda', 'role': 'town', 'patterns': TOWN_PATTERNS['seyda'],
         'option': '--town-scenery', 'directory': under(town_scenery)},
        {'name': 'opening-barrel', 'role': 'overlay', 'patterns': TOWN_PATTERNS['seyda'],
         'option': '--scene', 'directory': under(scene, 'opening-barrel-source')},
        {'name': 'world-flora', 'role': 'overlay', 'patterns': ('*',),
         'option': '--world-flora', 'directory': under(world_flora, 'source')},
    ]


def image_sources(args):
    """Scenery sources from the image builder's options.

    --balmora-scenery defaults to the scenery of --balmora-cache, and
    --town-scenery to the directory of --town-flora-source-index.
    """
    balmora = getattr(args, 'balmora_scenery', None)
    if balmora is None and getattr(args, 'balmora_cache', None):
        balmora = Path(args.balmora_cache) / 'scenery'
    town = getattr(args, 'town_scenery', None)
    if town is None and getattr(args, 'town_flora_source_index', None):
        town = Path(args.town_flora_source_index).parent
    return scenery_sources(balmora, town, getattr(args, 'scene', None), getattr(args, 'world_flora', None))


def town_of(name):
    return next((town for town, patterns in TOWN_PATTERNS.items()
                 if any(fnmatch.fnmatch(name, p) for p in patterns)), None)


def night_windows(maps_dir, map_names, sources, palette=None, data_files=None):
    """(table bytes, report, summary) for the named maps.

    Only town exterior maps are classified; world terrain regions hold rocks,
    mushrooms and flora but no glass. A town whose own scenery source is
    absent is skipped, never classified against overlays alone.
    """
    import night_windows as N
    used, skipped_sources, loaded = [], [], []
    for source in sources:
        directory = source['directory']
        if directory is None:
            skipped_sources.append({'name': source['name'], 'option': source['option'], 'reason': 'not supplied'})
            continue
        if not (Path(directory) / 'scenery-index.json').is_file():
            skipped_sources.append({'name': source['name'], 'option': source['option'],
                                    'reason': 'no scenery-index.json in ' + str(directory)})
            continue
        scenery = N.ScenerySource(directory, data_files)
        used.append({'name': source['name'], 'role': source['role'], 'patterns': list(source['patterns']),
                     'index_sha256': sha((Path(directory) / 'scenery-index.json').read_bytes())})
        loaded.extend((pattern, scenery) for pattern in source['patterns'])
    towns_ready = {s['name'] for s in used if s['role'] == 'town'}
    palette_rgb = N.palette_rgb(Path(palette).read_bytes()) if palette else None
    rows, report, skipped_maps, other_maps = {}, {}, {}, 0
    for name in sorted(map_names):
        town = town_of(name)
        if town is None:
            other_maps += 1
            continue
        if town not in towns_ready:
            skipped_maps[name] = town + ' scenery not supplied'
            continue
        found, details = N.build([(name, (Path(maps_dir) / (name + '.bsp')).read_bytes())], loaded, palette_rgb)
        rows.update(found); report.update(details)
    table = N.table_text(rows).encode('ascii')
    summary = {'sources_used': used, 'sources_skipped': skipped_sources,
               'maps_classified': len(report), 'maps_with_glow': sum(1 for v in rows.values() if v),
               'glowing_textures': sum(len(v) for v in rows.values()),
               'town_maps_skipped': skipped_maps, 'other_maps_not_classified': other_maps,
               'unresolved_refs': sum(len(v.get('unresolved_refs', ())) for v in report.values()),
               'unsettled_textures': sum(len(v.get('unsettled', ())) for v in report.values())}
    return table, report, summary


def stage(id1, *, master, maps, sources, palette=None, data_files=None, work_dir=None,
          fog_source=FOG_SOURCE):
    """Write the three tables into id1/world and return their receipt."""
    from light_sources import lamp_table
    world = Path(id1) / 'world'
    world.mkdir(parents=True, exist_ok=True)
    lamps = lamp_table(Path(master).read_bytes())
    lamp_count = check_lamp_table(lamps)
    windows, report, summary = night_windows(Path(id1) / 'maps', maps, sources, palette, data_files)
    window_maps = check_window_table(windows)
    fog, places = fog_table(Path(fog_source).read_bytes())
    payloads = {'world/lamps.awl': lamps, 'world/night-windows.txt': windows, 'world/fog-locations.txt': fog}
    for name, raw in payloads.items():
        (Path(id1) / name).write_bytes(raw)
    tables = {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in payloads.items()}
    tables['world/lamps.awl']['lamps'] = lamp_count
    tables['world/night-windows.txt']['maps'] = window_maps
    tables['world/fog-locations.txt']['places'] = places
    tables['world/fog-locations.txt']['source'] = 'config/fog-locations.txt'
    receipt = {'format': 'AmiWind night lighting tables 1',
               'status': 'partial' if summary['sources_skipped'] else 'complete',
               'tables': tables, 'night_windows': summary}
    if work_dir is not None:
        work_dir = Path(work_dir); work_dir.mkdir(parents=True, exist_ok=True)
        path = work_dir / 'night-windows-report.json'
        path.write_bytes((json.dumps(report, indent=1, sort_keys=True) + '\n').encode('utf-8'))
        receipt['night_windows']['report'] = path.name
        receipt['night_windows']['report_sha256'] = sha(path.read_bytes())
        (work_dir / 'night-lighting.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
    for entry in summary['sources_skipped']:
        print(f"[warning] Night windows: {entry['name']} scenery skipped ({entry['reason']}).", flush=True)
    print(f'Night lighting: {lamp_count} lamps, {window_maps} maps with glowing glass, '
          f'{places} fog places ({receipt["status"]}).', flush=True)
    return receipt
