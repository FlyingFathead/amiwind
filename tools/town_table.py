#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate the engine's town table (engine/aga/src/aw_town_table.h).

The runtime knows towns only through this table: map name, region prefix and
directory, region cap, draw distance, world-directory slot or handoff frame,
behaviour flags and travel. It is generated from config/towns.json and the
town configs, checked in so native tests compile without a generator step,
and verified by build_aga.py engine and tests/test_town_import.py.

It also writes the expansions' room tables (engine/aga/src/aw_layer_table.h, from
config/room-batches-tribunal.json and config/room-batches-bloodmoon.json).

  python3 tools/town_table.py --write   # after changing a town config
  python3 tools/town_table.py --check   # exit 1 when the header is stale
"""
import argparse
from pathlib import Path
import sys

from town_config import FIXED_TOWNS, runtime_towns, town_interiors

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / 'engine/aga/src/aw_town_table.h'
FLAG_MACROS = {'seyda_scenes': 'AW_TOWN_SEYDA_SCENES', 'legacy_payload': 'AW_TOWN_LEGACY_PAYLOAD',
               'own_doors': 'AW_TOWN_OWN_DOORS', 'scenery_catalogue': 'AW_TOWN_SCENERY',
               'teleport_arrival': 'AW_TOWN_TELEPORT', 'ground_place': 'AW_TOWN_GROUND_PLACE'}


def c_string(value):
    if any(c in value for c in '"\\\r\n') or not value.isascii():
        raise ValueError('Town table strings must be plain ASCII')
    return '"' + value + '"'


def c_float(value):
    text = repr(float(value))
    return text[:-2] if text.endswith('.0') else text


def c_list(name, values, per_line):
    """#define NAME {v,...} on one line, or continued lines of per_line values."""
    if len(values) <= per_line:
        return ['#define ' + name + ' {' + ','.join(values) + '}']
    lines = ['#define ' + name + ' {\\']
    for i in range(0, len(values), per_line):
        last = i + per_line >= len(values)
        lines.append('    ' + ','.join(values[i:i + per_line]) + ('' if last else ',') + '\\')
    return lines + ['}']


# Handoff frames: the engine (aw_world.c valid_town and the arrival checks) accepts a core box only
# within +/-AW_COORD_BOUND local units of the frame origin (engine/aga/src/aw_coord.h). The bound is the
# coordinate range positions travel in (MSG_WriteCoord, CHIM-FRAME-COORD-RANGE-33): wide (the default since
# v0.0.36) 24 bits of 1/256 units, +/-32,768; narrow (--coord-range narrow, the method before) shorts of
# eighths, which wrap past COORD_RANGE. The table is the same for both engines, so it holds rows up to the
# wide bound; a narrow engine drops a row past 4,000 at run time, and the builder refuses to build such an
# area with --coord-range narrow (chim.areas.area_problems, coord_range.core_problem).
from coord_range import NARROW_BOUND, WIDE_BOUND
FRAME_BOUND = WIDE_BOUND
COORD_RANGE = 32767 / 8          # the narrow range (positions as 1/8-unit shorts)


def check_core(row):
    """Refuse a handoff row whose core box the engine would drop (outside +/-FRAME_BOUND)."""
    if not row.get('handoff'):
        return
    (x0, y0), (x1, y1) = row['core']
    if not (-FRAME_BOUND <= x0 < x1 <= FRAME_BOUND and -FRAME_BOUND <= y0 < y1 <= FRAME_BOUND):
        raise ValueError(f"Town {row['name']}: core box {row['core']} is outside +/-{FRAME_BOUND} local units, "
                         f"the wide coordinate range (CHIM-FRAME-COORD-RANGE-33): split the frame or move its origin")


def room_batch_lines(root=None):
    """The batch rooms (config/room-batches.json, tools/room_batches.py engine_rows): map names and titles by id, their
    save IDs from AW_ROOM_BATCH_BASE (aw_maps.h); a room a town or scene list holds keeps its own name there ("")."""
    from room_batches import engine_rows, load
    doc = load(root)
    table = engine_rows(doc, root) if doc else []
    if len(table) >= 4096:
        raise ValueError('The room list has ids past 4095: AW_ROOM_BATCH_BASE holds 4096 rooms')
    return ['/* Batch rooms (config/room-batches.json) by id: "" for an id held by a town or scene list. */',
            f'#define AW_ROOM_BATCH_COUNT {len(table)}',
            *c_list('AW_ROOM_BATCH_NAMES', [c_string(m) for m, _ in table] or ['""'], 8),
            *c_list('AW_ROOM_BATCH_TITLES', [c_string(t) for _, t in table] or ['""'], 1)]


# The expansions' rooms (BUILD-EXPANSIONS-31, the v0.0.64 layer plan): each expansion has its own room list and its own
# save-ID range of 4096 after the base batch rooms (aw_maps.h AW_TRIBUNAL_ROOM_BASE, AW_BLOODMOON_ROOM_BASE), so an
# expansion room never moves a base id and a base room never moves an expansion's. They go into their own generated
# header (engine/aga/src/aw_layer_table.h), never into aw_town_table.h: the CHIM world, town and flora stages key
# aw_town_table.h whole (tests/test_stage_key_engine_defines.py), and an expansion list must not re-key the base world.
# The engine is always compiled with all three lists, whatever expansions a build carries: one engine for every
# combination. A missing or empty list is a table of 0 rooms.
LAYER_HEADER = ROOT / 'engine/aga/src/aw_layer_table.h'
LAYER_ROOM_LIMIT = 4096
LAYERS = (('TRIBUNAL', 'Tribunal', 'room-batches-tribunal.json'),
          ('BLOODMOON', 'Bloodmoon', 'room-batches-bloodmoon.json'))


def layer_docs(root=None):
    """{macro: room list or None} of the repo's expansion room lists (None: the repo has no such file). The files are
    written out here, one loop over the names, so a stage key that reaches this reads these two files, not all of
    config/ (BUILD-SURVEY-KEY-CONFIG-35); tests/test_room_batches.py keeps the names equal to LAYERS."""
    import json
    out = {}
    for macro, config in [('TRIBUNAL', 'room-batches-tribunal.json'), ('BLOODMOON', 'room-batches-bloodmoon.json')]:
        path = Path(root or ROOT) / 'config' / config
        out[macro] = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    return out


def layer_room_rows(macro, title, config, root=None, doc=None):
    """[(map, title)] of one expansion's room list (DOC, the file config/CONFIG, format aw-room-batches-1) indexed by
    id, as room_batches.engine_rows gives the base list; [] for no list. Refuses a list that is not sound and one with
    an id past 4095 (its range holds 4096 rooms)."""
    from room_batches import check as check_rooms, engine_rows
    if doc is None:
        return []
    problems = check_rooms(doc)
    if problems:
        raise ValueError('config/%s (%s rooms): %s' % (config, title, '; '.join(problems[:6])))
    table = engine_rows(doc, root)
    if len(table) > LAYER_ROOM_LIMIT:
        raise ValueError('The %s room list has ids past 4095: AW_%s_ROOM_BASE holds 4096 rooms' % (title, macro))
    return table


def render_layer_header(root=None, docs=None):
    """The expansions' room tables (engine/aga/src/aw_layer_table.h). DOCS: {macro: room list} in place of the repo's
    files (tests)."""
    lines = [
        '/* SPDX-License-Identifier: GPL-2.0-or-later',
        ' * Generated by tools/town_table.py from config/room-batches-tribunal.json and',
        ' * config/room-batches-bloodmoon.json. Do not edit: change the lists and run',
        ' * tools/town_table.py --write. Each expansion\'s rooms take save IDs by their id',
        ' * from its own base (aw_maps.h AW_TRIBUNAL_ROOM_BASE, AW_BLOODMOON_ROOM_BASE). */',
        '#ifndef AW_LAYER_TABLE_H',
        '#define AW_LAYER_TABLE_H',
    ]
    found = dict(layer_docs(root), **(docs or {}))
    for macro, title, config in LAYERS:
        table = layer_room_rows(macro, title, config, root, found.get(macro))
        lines += ['/* %s rooms (config/%s) by id. */' % (title, config),
                  '#define AW_%s_ROOM_COUNT %d' % (macro, len(table)),
                  *c_list('AW_%s_ROOM_NAMES' % macro, [c_string(m) for m, _ in table] or ['""'], 8),
                  *c_list('AW_%s_ROOM_TITLES' % macro, [c_string(t) for _, t in table] or ['""'], 1)]
    lines += ['#endif', '']
    return '\n'.join(lines)


def render_header(root=None):
    rows = runtime_towns(root)
    for r in rows:
        check_core(r)
    extra = rows[len(FIXED_TOWNS):]
    rooms = town_interiors(root)
    ids = [r['id'] for r in rows]
    lines = [
        '/* SPDX-License-Identifier: GPL-2.0-or-later',
        ' * Generated by tools/town_table.py from config/towns.json and the town',
        ' * configs. Do not edit: change the configs and run tools/town_table.py --write.',
        ' * Row order is the stable save order; extra towns take save IDs from',
        ' * AW_TOWN_MAP_BASE, town interiors (towns in row order, then each',
        ' * list order of its town) from AW_TOWN_INTERIOR_BASE (aw_maps.h). */',
        '#ifndef AW_TOWN_TABLE_H',
        '#define AW_TOWN_TABLE_H',
        f'#define AW_TOWN_COUNT {len(rows)}',
        f'#define AW_TOWN_FIXED_COUNT {len(FIXED_TOWNS)}',
        f'#define AW_TOWN_EXTRA_COUNT {len(extra)}',
        '#define AW_TOWN_EXTRA_NAMES {' + ','.join(c_string(r['name']) for r in extra or [{'name': ''}]) + '}',
        '#define AW_TOWN_EXTRA_TITLES {' + ','.join(c_string(r['title']) for r in extra or [{'title': ''}]) + '}',
        f'#define AW_TOWN_INTERIOR_COUNT {len(rooms)}',
        *c_list('AW_TOWN_INTERIOR_NAMES', [c_string(r['map']) for r in rooms] or ['""'], 8),
        *c_list('AW_TOWN_INTERIOR_TITLES', [c_string(r['title']) for r in rooms] or ['""'], 1),
        '/* Town row (AW_Town index) whose door bank leads into each interior. */',
        *c_list('AW_TOWN_INTERIOR_TOWNS', [str(ids.index(r['town'])) for r in rooms] or ['0'], 32),
        *room_batch_lines(root),
        '/* name,title,prefix,regions,travel_npc,travel_target,region_cap,draw_distance,',
        '   world_slot,flags,travel_return,handoff,origin[3],core[4] */',
        '#define AW_TOWN_ROWS {\\',
    ]
    for i, r in enumerate(rows):
        flags = '|'.join(FLAG_MACROS[f] for f in r['flags']) or '0'
        values = [*map(c_string, (r['name'], r['title'], r['prefix'], r['regions'], r['travel_npc'], r['travel_target'])),
                  str(r['region_cap']), str(r['draw_distance']), str(r['world_slot']), flags,
                  str(int(r['travel_return'])), str(int(r['handoff'])),
                  '{' + ','.join(map(c_float, r['origin'])) + '}',
                  '{' + ','.join(map(c_float, [*r['core'][0], *r['core'][1]])) + '}']
        lines.append('    {' + ','.join(values) + '}' + (',' if i + 1 < len(rows) else '') + '\\')
    lines += ['}', '#endif', '']
    return '\n'.join(lines)


def check(root=None, header=None, layer_header=None):
    """True when the checked-in headers (the town table and the expansions' room tables) match the configs."""
    header = Path(header or HEADER)
    layer_header = Path(layer_header or LAYER_HEADER)
    return (header.is_file() and header.read_text(encoding='ascii') == render_header(root)
            and layer_header.is_file() and layer_header.read_text(encoding='ascii') == render_layer_header(root))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true', help='Rewrite engine/aga/src/aw_town_table.h')
    mode.add_argument('--check', action='store_true', help='Fail when the header differs from the configs')
    a = p.parse_args(argv)
    if a.write:
        HEADER.write_text(render_header(), encoding='ascii', newline='\n')
        LAYER_HEADER.write_text(render_layer_header(), encoding='ascii', newline='\n')
        print('Wrote', HEADER.relative_to(ROOT).as_posix(), 'and', LAYER_HEADER.relative_to(ROOT).as_posix())
        return 0
    if check():
        print('Town table is current.')
        return 0
    print('engine/aga/src/aw_town_table.h or aw_layer_table.h is stale; run tools/town_table.py --write',
          file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
