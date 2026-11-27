#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The item sweep of a compiled room (CENSUS-SHELF-PLATE-BAKED-67; the same check is meant for every interior,
GAMEPLAY-PARITY-NEXT-69): every placed reference of the original cell, counted by category, against what the room's
map holds. Each live reference is one of:
  entity    an entity of the map carries its reference (aw_ref): a brush of its own (func_wall: furniture, an item, a
            container, a door), an actor (aw_npc), a flame (aw_flame). The engine aims at, takes, opens or talks to
            the thing through that edict.
  placed    drawn by the engine's placed item list (progs/items/placed.awp, the room's key: an item model by its
            reference, WORLD-OBJECT-PLACEMENT-59), aimed at and taken through its focus row.
  baked     in the room's bake (the conversion report's group) but carried by no entity: part of the room's geometry,
            drawn and solid, never aimed at or taken.
  left out  not in the map: the converter's rule (mwad.interior.omission_reason) when one applies, else "not in the
            map".
--check refuses (exit 1) when a takeable item of the cell (the original's carryable kinds, and a light that can be
carried) is neither an entity of its own nor on the placed list, or a container is not an entity, naming each: it
could not be aimed at, taken or opened.
Reads the master, the map and the placed list; writes only --out (JSON) and --md.

    room_item_census.py --data-files DIR --cell "Seyda Neen, Census and Excise Office" --map census.bsp
                        [--report census-conversion.json] [--placed placed.awp] [--out census.json] [--md census.md]
                        [--check]
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

# The original's record kinds by the names the tables use.
CATEGORY = {
    'MISC': 'misc', 'WEAP': 'weapon', 'ARMO': 'armour', 'CLOT': 'clothing', 'BOOK': 'book', 'INGR': 'ingredient',
    'ALCH': 'potion', 'APPA': 'apparatus', 'LOCK': 'lockpick', 'PROB': 'probe', 'REPA': 'repair item',
    'LIGH': 'light', 'CONT': 'container', 'DOOR': 'door', 'ACTI': 'activator', 'NPC_': 'NPC', 'CREA': 'creature',
    'STAT': 'static', 'LEVC': 'levelled creature', 'LEVI': 'levelled item',
}
ORDER = list(CATEGORY.values())
# The kinds a player can take (OpenMW 0.53 mwclass: each of these classes' activate gives the take action); a light
# only when its record says it can be carried (LHDT flag 0x2, mwclass/light.cpp Light::activate).
TAKEABLE = ('ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'INGR', 'LOCK', 'MISC', 'PROB', 'REPA', 'WEAP')
LIGHT_CARRY = 0x2


def takeable(ref):
    """1 when the player can take the placed reference in the original."""
    if ref.get('type') in TAKEABLE:
        return True
    return ref.get('type') == 'LIGH' and bool((ref.get('light') or {}).get('flags', 0) & LIGHT_CARRY)


def _entity_text(data):
    if len(data) < 4 + 15 * 8:
        raise ValueError('not a map: %d bytes' % len(data))
    offset, size = struct.unpack_from('<ii', data, 4)
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('the entity lump lies outside the map')
    return data[offset:offset + size].decode('latin-1').split('\0', 1)[0]


def map_room(data):
    """The room number of the map bytes DATA (its worldspawn's _aw_cell_int, tools/cell_numbers.py), 0 none."""
    block = re.search(r'\{[^{}]*\}', _entity_text(data))
    value = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block.group(0))).get('_aw_cell_int', '') if block else ''
    return int(value) if value.isdigit() else 0


def map_references(data):
    """{reference: [entity class, ...]} of the map bytes DATA (a Quake BSP): every entity of the entity lump that
    carries aw_ref, by its classname."""
    text = _entity_text(data)
    found = {}
    for block in re.findall(r'\{[^{}]*\}', text):
        fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        value = fields.get('aw_ref', '')
        if not value.isdigit() or int(value) <= 0:
            continue
        found.setdefault(int(value), []).append(fields.get('classname', '?'))
    return found


def placed_references(raw, room):
    """The references the placed item list RAW (an AWP1 file, tools/prepare_item_models.py read_placed) draws in
    room ROOM."""
    from prepare_item_models import read_placed
    return {row[0] for row in read_placed(raw).get(room, ())}


STATES = ('entity', 'placed list', 'baked', 'left out')


def census(refs, held, baked=(), omission=None, placed=()):
    """The sweep of one room. REFS: the cell's references (mwad.interior read_interior: number, id, type, model,
    deleted, light); HELD: map_references; BAKED: the references of the room's bake (the conversion report's group);
    OMISSION: a reference's converter rule or None (mwad.interior.omission_reason by default); PLACED: the references
    the placed item list draws in this room (placed_references).
    Returns {'rows': [...], 'categories': {category: counts}, 'problems': [...]}."""
    if omission is None:
        from mwad.interior import omission_reason
        omission = omission_reason
    baked, placed = set(baked), set(placed)
    rows, categories, problems = [], {}, []
    for ref in refs:
        category = CATEGORY.get(ref.get('type'), ref.get('type') or '?')
        counts = categories.setdefault(category, {'placed': 0, 'entity': 0, 'placed list': 0, 'baked': 0,
                                                  'left out': 0, 'deleted': 0, 'takeable': 0})
        row = {'reference': ref['number'], 'id': ref.get('id', ''), 'category': category}
        if ref.get('deleted'):
            counts['deleted'] += 1
            row['state'] = 'deleted'
            rows.append(row)
            continue
        counts['placed'] += 1
        can_take = takeable(ref)
        counts['takeable'] += can_take
        if ref['number'] in held:
            row['state'] = 'entity'
            row['entities'] = sorted(held[ref['number']])
        elif ref['number'] in placed:
            row['state'] = 'placed list'
        elif ref['number'] in baked:
            row['state'] = 'baked'
        else:
            row['state'] = 'left out'
            try:
                row['reason'] = omission(ref) or 'not in the map'
            except (KeyError, TypeError):
                row['reason'] = 'not in the map'
        counts[row['state']] += 1
        if can_take:
            row['takeable'] = True
        if (can_take and row['state'] not in ('entity', 'placed list')) or (
                ref.get('type') == 'CONT' and row['state'] != 'entity'):
            problems.append('%s %s (%s, reference %d) is %s: it cannot be aimed at, %s' % (
                'a takeable' if can_take else 'a', category, row['id'], ref['number'],
                row['state'] + (' (' + row['reason'] + ')' if row.get('reason') else ''),
                'taken' if can_take else 'opened'))
        rows.append(row)
    return {'rows': rows, 'categories': categories, 'problems': problems}


# The opening's two compiled rooms and their maps (tools/prepare_census.py, the interior stage's prison map): the image
# step sweeps them (build_aga.py) and stops the image when one has a problem.
OPENING_ROOMS = (('Imperial Prison Ship', 'prison'), ('Seyda Neen, Census and Excise Office', 'census'))


def opening_sweep(master, id1, rooms=OPENING_ROOMS, numbers=None):
    """The sweep of the opening rooms an image's id1 holds (its maps/<name>.bsp and progs/items/placed.awp), the
    master read once: {'rooms': {cell: result + 'md'}, 'absent': [cells whose map the image does not hold],
    'problems': ['cell: problem', ...]}.
    NUMBERS: {folded cell ID: room number} (tools/cell_numbers.py room_numbers), the table the image step stamps into
    each interior map's worldspawn (_aw_cell_int) late in the step (stamp_staged_cells): the sweep runs before that,
    when the map carries no number yet, so its room on the placed list is the table's (OPENING-SWEEP-BEFORE-STAMP-69:
    without it the prison ship's 79 items on the placed list read as left out and the dev6 build stopped). A map that
    carries a number other than the table's is a problem."""
    from mwad.interior import read_interiors
    id1 = Path(id1)
    present = [(cell, name) for cell, name in rooms if (id1 / 'maps' / (name + '.bsp')).is_file()]
    out = {'rooms': {}, 'absent': [cell for cell, name in rooms if (cell, name) not in present], 'problems': []}
    if not present:
        return out
    placed_raw = (id1 / 'progs/items/placed.awp').read_bytes() if (id1 / 'progs/items/placed.awp').is_file() else b''
    cells = read_interiors(master, [cell for cell, _ in present])
    for (cell, name), data in zip(present, cells):
        raw = (id1 / 'maps' / (name + '.bsp')).read_bytes()
        stamped = map_room(raw)
        listed = (numbers or {}).get(cell.casefold(), 0)
        room = stamped or listed
        result = census(data['refs'], map_references(raw), placed=placed_references(placed_raw, room)
                        if placed_raw and room else ())
        if stamped and listed and stamped != listed:
            result['problems'].append('the map says room %d, the cell number table %d: the placed list is read under '
                                      'the map\'s' % (stamped, listed))
        result.update(map=name + '.bsp', room=room, md=render_md(cell, result))
        out['rooms'][cell] = result
        out['problems'] += ['%s: %s' % (cell, p) for p in result['problems']]
    return out


def render_md(room, result):
    """The table of one room: a row per category (placed, entity, baked, left out, deleted, takeable), then the
    differences named."""
    columns = ('placed', 'entity', 'placed list', 'baked', 'left out', 'deleted', 'takeable')
    lines = ['# Item sweep: %s' % room, '', '| category | ' + ' | '.join(columns) + ' |',
             '|---|' + '---|' * len(columns)]
    cats = result['categories']
    for name in [c for c in ORDER if c in cats] + sorted(c for c in cats if c not in ORDER):
        lines.append('| %s | %s |' % (name, ' | '.join(str(cats[name][k]) for k in columns)))
    lines.append('| all | %s |' % ' | '.join(str(sum(c[k] for c in cats.values())) for k in columns))
    lines += ['', '"placed" counts the live references of the original cell; "placed list" the ones the engine draws '
              'from its placed item list.', '', '## Not drawn as an entity or from the placed list', '']
    other = [r for r in result['rows'] if r.get('state') in ('baked', 'left out')]
    lines += ['- %s `%s` (reference %d): %s%s' % (r['category'], r['id'], r['reference'], r['state'],
                                                 ' (' + r['reason'] + ')' if r.get('reason') else '')
              for r in other] or ['- none']
    lines += ['', '## Problems', ''] + (['- ' + p for p in result['problems']] or ['- none'])
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, help='the game data folder (its base master is read)')
    p.add_argument('--master', type=Path, help='the master file itself, in place of --data-files')
    p.add_argument('--cell', required=True)
    p.add_argument('--map', type=Path, required=True)
    p.add_argument('--report', type=Path, help="the room's conversion report: its groups' references are the bake")
    p.add_argument('--placed', type=Path, help='the placed item list (progs/items/placed.awp) the image carries')
    p.add_argument('--out', type=Path)
    p.add_argument('--md', type=Path)
    p.add_argument('--check', action='store_true')
    a = p.parse_args(argv)
    from mwad.interior import read_interior
    if a.master:
        master = a.master
    elif a.data_files:
        from mwad.masters import master_path
        from mwad.paths import resolve_data_files
        master = master_path(resolve_data_files(a.data_files))
    else:
        p.error('--data-files or --master')
    cell = read_interior(master, a.cell)
    baked = set()
    if a.report:
        report = json.loads(a.report.read_text(encoding='utf-8'))
        for group in (report.get('groups') or {}).values():
            baked.update(int(n) for n in group.get('references', ()))
    raw = a.map.read_bytes()
    room = map_room(raw)
    placed = placed_references(a.placed.read_bytes(), room) if a.placed and room else set()
    result = census(cell['refs'], map_references(raw), baked, placed=placed)
    result.update(cell=cell['name'], map=a.map.name, room=room, master_sha256=cell.get('master_sha256'))
    if a.out:
        a.out.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    md = render_md(cell['name'], result)
    if a.md:
        a.md.write_text(md, encoding='utf-8', newline='\n')
    print(md, end='')
    if a.check and result['problems']:
        print('ROOM ITEM CENSUS: %d problem(s) in %s' % (len(result['problems']), cell['name']))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
