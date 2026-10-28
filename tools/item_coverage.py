#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Item coverage: is every item of the three masters in AmiWind's tables and image? (docs/NPC_DEFAULTS.md)

For every WEAP, ARMO, CLOT, MISC, BOOK, ALCH, INGR, LOCK, PROB, REPA and LIGH record of Morrowind, Tribunal and
Bloodmoon (the last master's record of an id wins, a deleted record removes it, as in the game) it answers:

  actor table   in the shared item table AITM of id1/mwscript.awm (carried by an actor or named by a script;
                docs/ACTOR_STATE.md); read from the image's file when it has the section, else computed from the
                masters with the builder's own code (tools/mwscript)
  carried       carried by at least one NPC or creature record (NPCO; levelled lists resolved at the actor's level)
  catalogue     a row of the inventory catalogue id1/inventory/items.awi (docs/INVENTORY.md)
  ground model  that row names a world model that exists in the image (progs/inv)
  icon          that row names an icon that exists, or the icon table gfx/icons.awl has the item
  held model    weapons and shields: the carried-item model items/<w|s><hash>.mdl a hand bone holds
                (tools/npc_items.py item_stem); lights: none (no carried-light model yet)
  placed        placed in a cell of the masters (one or more references)
  takeable      placed, and its catalogue row can be picked up (a ground model and no script that blocks it:
                prepare_inventory flag 2)

Counts per record type and in all; with --private the item ids of every gap (private output, never in the repo).
Read-only; nothing of the game is written into the repo. Usage:

  tools/item_coverage.py --data-files DIR [--id1 IMAGE/boot/id1] [--json OUT] [--private OUT]
"""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]   # src first: the mwad package, not tools/mwad.py

from mwad.esm import records, subrecords, string, is_deleted  # noqa: E402

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
TYPES = ('WEAP', 'ARMO', 'CLOT', 'MISC', 'BOOK', 'ALCH', 'INGR', 'LOCK', 'PROB', 'REPA', 'LIGH')
COLUMNS = ('records', 'actor_table', 'carried', 'catalogue', 'ground_model', 'icon', 'held_model', 'placed',
           'takeable')
SHIELD = 8            # ARMO type 8: a shield (held on the shield bone)
LIGHT_CARRY = 0x2     # LHDT flag: the light can be carried
CATALOGUE_ROW = 512   # tools/prepare_inventory.py ROW
FLAG_PICKUP = 2       # prepare_inventory: a staged world model and an inert script


def _text(data):
    return string(data, errors='replace')


def read_masters(data_files):
    """{tag: {folded id: {'id', 'model', 'icon', 'type', 'carry'}}}, {folded id: placed references},
    {folded id: [(sub, data)]} of the NPC_ and CREA records."""
    from mwad.paths import child_ci
    items = {t: {} for t in TYPES}
    placed = {}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is None:
            continue
        for tag, flags, payload in records(path.read_bytes()):
            if tag in items:
                parts = list(subrecords(payload))
                fields = dict(parts)
                ident = _text(fields.get('NAME', b''))
                key = ident.casefold()
                if is_deleted(flags, parts):
                    items[tag].pop(key, None)
                    continue
                if not key:
                    continue
                kind, carry = -1, True
                data = fields.get({'WEAP': 'WPDT', 'ARMO': 'AODT', 'CLOT': 'CTDT', 'LIGH': 'LHDT'}.get(tag, ''), b'')
                if tag == 'WEAP' and len(data) >= 10:
                    kind = struct.unpack_from('<h', data, 8)[0]
                elif tag in ('ARMO', 'CLOT') and len(data) >= 4:
                    kind = struct.unpack_from('<i', data)[0]
                elif tag == 'LIGH' and len(data) >= 24:
                    carry = bool(struct.unpack_from('<I', data, 20)[0] & LIGHT_CARRY)
                icon = fields.get('TEXT' if tag == 'ALCH' else 'ITEX', b'')
                items[tag][key] = {'id': ident, 'model': _text(fields.get('MODL', b'')), 'icon': _text(icon),
                                   'type': kind, 'carry': carry}
            elif tag == 'CELL':
                after_ref = False
                for sub, data in subrecords(payload):
                    if sub == 'FRMR':
                        after_ref = True
                    elif sub == 'NAME' and after_ref:
                        key = _text(data).casefold()
                        placed[key] = placed.get(key, 0) + 1
                        after_ref = False
    return items, placed


def actor_items(data_files, id1=None):
    """(folded ids in the shared item table, folded ids carried by an actor, where the table came from)."""
    from mwscript.gamedata import GameData
    from mwscript.actors import ActorTables
    data = GameData().load(Path(data_files))
    names = []
    tables = ActorTables(data, lambda s: names.append(s) or len(names) - 1)
    carried = set()
    for row in tables.rows:
        for item, _count, _flags in tables.inventory[row['inv_first']:row['inv_first'] + row['inv_count']]:
            carried.add(names[tables.items[item]['id']].casefold())
    awm = Path(id1) / 'mwscript.awm' if id1 else None
    if awm is not None and awm.is_file():
        from mwscript import awms
        f = awms.read(awm.read_bytes())
        if f.get('AITM') is not None and 'AITM_rows' in f:
            strs = awms.strings(f)
            table = {strs[struct.unpack_from('>H', f['AITM'], 28 * i)[0]].casefold() for i in range(f['AITM_rows'])}
            return table, carried, 'image'
    from mwscript.compiler import compile_program
    program, _compiled = compile_program(data, handwritten=())
    return set(program.actors.item_index), carried, 'computed'


def read_image(id1):
    """{folded id: (model path, icon path, flags)} of the catalogue, the icon table bytes, the held model files."""
    id1 = Path(id1)
    catalogue = {}
    path = id1 / 'inventory' / 'items.awi'
    if path.is_file():
        raw = path.read_bytes()
        if raw[:4] != b'AWI2':
            raise ValueError('not an AWI2 inventory catalogue: %s' % path)
        for i in range(struct.unpack_from('<I', raw, 4)[0]):
            row = raw[8 + CATALOGUE_ROW * i: 8 + CATALOGUE_ROW * (i + 1)]
            ident = row[:64].split(b'\0')[0].decode('cp1252').casefold()
            flags = struct.unpack_from('<I', row, 180)[0]
            model = row[184:248].split(b'\0')[0].decode('cp1252')
            icon = row[248:312].split(b'\0')[0].decode('cp1252')
            catalogue[ident] = (model, icon, flags)
    icons = (id1 / 'gfx' / 'icons.awl').read_bytes() if (id1 / 'gfx' / 'icons.awl').is_file() else b''
    held = {p.name for p in (id1 / 'items').glob('*.mdl')} if (id1 / 'items').is_dir() else set()
    return catalogue, icons, held


def item_stem(kind, mesh):
    from npc_items import item_stem as stem   # one naming rule (tools/npc_items.py)
    return stem(kind, mesh)


def coverage(items, placed, table, carried, image=None):
    """{'by_type': {tag: {column: n}}, 'all': {column: n}, 'gaps': {tag: {column: [ids]}}}."""
    id1 = None
    if image is not None:
        id1, (catalogue, icons, held) = image
    out, gaps = {}, {}
    fixed_lights = 0
    for tag in TYPES:
        counts = dict.fromkeys(COLUMNS, 0)
        missing = {c: [] for c in COLUMNS[1:]}
        for key, rec in sorted(items[tag].items()):
            if not rec['carry']:   # a light that cannot be carried is scenery, not an item (LHDT flag 2)
                fixed_lights += 1
                continue
            counts['records'] += 1
            row = None
            has = {'actor_table': key in table, 'carried': key in carried, 'placed': placed.get(key, 0) > 0}
            if image is not None:
                row = catalogue.get(key)
                has['catalogue'] = row is not None
                has['ground_model'] = bool(row and row[0] and (id1 / row[0]).is_file())
                has['icon'] = bool(row and row[1] and (id1 / row[1]).is_file()) or \
                    ('item:' + key).encode('cp1252', 'replace') in icons
                if tag == 'WEAP' or (tag == 'ARMO' and rec['type'] == SHIELD):
                    kind = 'weapon' if tag == 'WEAP' else 'shield'
                    has['held_model'] = bool(rec['model']) and item_stem(kind, rec['model']) + '.mdl' in held
                has['takeable'] = has['placed'] and bool(row and row[2] & FLAG_PICKUP)
            for column, value in has.items():
                if value:
                    counts[column] += 1
                else:
                    missing[column].append(rec['id'])
        out[tag] = counts
        gaps[tag] = missing
    total = {c: sum(out[t][c] for t in TYPES) for c in COLUMNS}
    return {'by_type': out, 'all': total, 'gaps': gaps, 'fixed_lights': fixed_lights,
            'held_applies': {t: (sum(1 for r in items[t].values() if r['type'] == SHIELD) if t == 'ARMO' else
                                 len(items[t]) if t == 'WEAP' else 0) for t in TYPES}}


def table_text(result, source):
    head = ['type'] + list(COLUMNS)
    lines = ['| ' + ' | '.join(head) + ' |', '| --- |' + ' ---: |' * len(COLUMNS)]
    for tag in TYPES + ('all',):
        row = result['all'] if tag == 'all' else result['by_type'][tag]
        lines.append('| ' + ' | '.join([tag] + ['{:,}'.format(row[c]) for c in COLUMNS]) + ' |')
    lines.append('')
    lines.append('actor table from: %s; held model applies to %d weapons and %d shields; %d lights that cannot be '
                 'carried are left out' % (source, result['held_applies']['WEAP'], result['held_applies']['ARMO'],
                                          result['fixed_lights']))
    return '\n'.join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', required=True, help='the game data folder (Morrowind.esm and the add-ons)')
    p.add_argument('--id1', help="an image's boot/id1 folder (catalogue, icons, held models, mwscript.awm)")
    p.add_argument('--json', help='counts as JSON (no item ids)')
    p.add_argument('--private', help='every gap with its item ids (private: game data names)')
    a = p.parse_args(argv)
    print('item coverage: reading the masters', flush=True)
    items, placed = read_masters(a.data_files)
    print('item coverage: %d item records; the actor tables' % sum(len(v) for v in items.values()), flush=True)
    table, carried, source = actor_items(a.data_files, a.id1)
    image = (Path(a.id1), read_image(a.id1)) if a.id1 else None
    result = coverage(items, placed, table, carried, image)
    print(table_text(result, source))
    if a.json:
        Path(a.json).write_text(json.dumps({'source': source, 'by_type': result['by_type'], 'all': result['all'],
                                            'held_applies': result['held_applies'],
                                            'fixed_lights': result['fixed_lights']}, indent=1) + '\n',
                                encoding='utf-8', newline='\n')
    if a.private:
        Path(a.private).write_text(json.dumps(result['gaps'], indent=1) + '\n', encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
