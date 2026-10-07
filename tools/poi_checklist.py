#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Points-of-interest checklist from the user's own Morrowind.esm.

Lists every named exterior place (settlements and landmarks, grouped across
their grid cells) and every interior cell with its entrances from the
exterior, grouped by region, with a rough type and conversion status. Interiors
reached only through other interiors are attached to their parent through the
door graph. Writes a Markdown checklist (for the "building inspector" pass) and
a JSON file. The output names the game's places: keep it private unless the
owner decides otherwise.

Conversion status comes from config/seyda_area.json and
config/balmora_interiors.json. The type is a hint from the cell name and the
most common static kit, not an authoritative classification.

Example:
  poi_checklist.py --esm /path/Data Files/Morrowind.esm \\
      --markdown private/poi-checklist.md --json private/poi-checklist.json
"""
import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import records, subrecords, cell_data, string  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# (name fragment, type) checked in order on the lower-case cell name.
NAME_TYPES = (
    ('ancestral tomb', 'tomb'), ('tomb', 'tomb'), ('burial', 'tomb'),
    ('cave', 'cave'), ('grotto', 'cave'), ('cavern', 'cave'), ('mine', 'mine'),
    ('egg mine', 'mine'), ('shrine', 'shrine'), ('temple', 'temple'),
    ('stronghold', 'stronghold'), ('fort', 'fort'), ('tower', 'tower'),
    ('ship', 'ship'), ('guild', 'guild'), ('tradehouse', 'shop'), ('trader', 'shop'),
    ('smith', 'shop'), ('pawnbroker', 'shop'), ('club', 'tavern'), ('inn', 'tavern'),
    ('cornerclub', 'tavern'), ('house', 'house'), ('manor', 'house'), ('shack', 'house'),
    ('hut', 'house'), ('yurt', 'house'), ('canton', 'canton'), ('plaza', 'district'),
    ('arena', 'arena'), ('prison', 'prison'), ('sewer', 'sewer'), ('underworks', 'sewer'),
)
# (static id prefix, type) for cells whose name says nothing.
KIT_TYPES = (
    ('in_dwrv', 'Dwemer ruin'), ('in_dwe', 'Dwemer ruin'), ('in_dae', 'Daedric shrine'),
    ('in_strong', 'stronghold'), ('in_v_', 'Velothi interior'), ('in_t_', 'tomb'),
    ('in_cave', 'cave'), ('in_lava', 'cave'), ('in_moldcave', 'cave'), ('in_mudcave', 'cave'),
    ('in_bc_cave', 'cave'), ('in_hlaalu', 'Hlaalu interior'), ('in_redoran', 'Redoran interior'),
    ('in_telv', 'Telvanni interior'), ('in_impsmall', 'Imperial interior'), ('in_c_', 'common interior'),
)


def classify(name, statics):
    lowered = name.casefold()
    for fragment, kind in NAME_TYPES:
        if fragment in lowered:
            return kind
    kits = Counter(next((kind for prefix, kind in KIT_TYPES if s.casefold().startswith(prefix)), None)
                   for s in statics)
    kits.pop(None, None)
    return kits.most_common(1)[0][0] if kits else 'interior'


def converted_cells(root):
    cells = set()
    for name in ('config/seyda_area.json', 'config/balmora_interiors.json'):
        path = root / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        for entry in data.get('scenes', data if isinstance(data, list) else []):
            if isinstance(entry, dict) and entry.get('cell'):
                cells.add(entry['cell'].casefold())
    return cells


def build(raw, converted):
    statics, doors, cells = set(), set(), []
    for tag, flags, payload in records(raw):
        if flags & 0x20:
            continue
        subs = list(subrecords(payload))
        if tag in ('STAT', 'DOOR'):
            fields = dict(subs)
            if 'NAME' in fields and 'DELE' not in fields:
                (statics if tag == 'STAT' else doors).add(string(fields['NAME']).casefold())
        elif tag == 'CELL':
            cells.append(cell_data(subs))
    exterior_names = {}
    interiors = {}
    for cell in cells:
        if cell['flags'] & 1:
            interiors[cell['name']] = cell
        elif cell['name']:
            place = exterior_names.setdefault(cell['name'], {'name': cell['name'], 'grids': [], 'regions': Counter()})
            place['grids'].append([cell['x'], cell['y']])
            if cell['region']:
                place['regions'][cell['region']] += 1
    links = []  # (source cell, source interior?, grid, position, destination interior)
    for cell in cells:
        for ref in cell['refs']:
            target = ref.get('destination_cell')
            if ref.get('deleted') or not target or ref.get('id', '').casefold() not in doors:
                continue
            links.append((cell, bool(cell['flags'] & 1), [cell['x'], cell['y']], ref['position'], target))
    entrances, parents = {}, {}
    for cell, inside, grid, position, target in links:
        if target not in interiors:
            continue
        if not inside:
            entrances.setdefault(target, []).append({
                'grid': grid, 'position': [round(v, 1) for v in position],
                'exterior': cell['name'], 'region': cell['region']})
        else:
            parents.setdefault(target, set()).add(cell['name'])
    # Interiors reached only from other interiors inherit their nearest
    # exterior-connected ancestor (breadth first over the door graph).
    anchor = {name: name for name in entrances}
    queue = deque(entrances)
    children = {}
    for target, sources in parents.items():
        for source in sources:
            children.setdefault(source, set()).add(target)
    while queue:
        current = queue.popleft()
        for child in sorted(children.get(current, ())):
            if child not in anchor:
                anchor[child] = anchor[current]
                queue.append(child)
    places = []
    for name, place in sorted(exterior_names.items()):
        region = place['regions'].most_common(1)[0][0] if place['regions'] else ''
        places.append({'kind': 'exterior place', 'name': name, 'region': region,
                       'grids': sorted(place['grids']), 'converted': False})
    for name, cell in sorted(interiors.items()):
        statics_here = [r.get('id', '') for r in cell['refs']
                        if not r.get('deleted') and r.get('id', '').casefold() in statics]
        own = entrances.get(name, [])
        root = anchor.get(name)
        root_entrances = entrances.get(root, []) if root else []
        region = (own or root_entrances or [{'region': ''}])[0]['region']
        settlement = (own or root_entrances or [{'exterior': ''}])[0]['exterior']
        places.append({
            'kind': classify(name, statics_here), 'name': name, 'region': region,
            'settlement': settlement, 'entrances': own,
            'reached_through': root if root and root != name else None,
            'unreachable': root is None, 'converted': name.casefold() in converted})
    return places


def markdown(places):
    lines = ['# Points of interest', '',
             'Generated from the user\'s own Morrowind.esm by tools/poi_checklist.py.',
             'Columns: converted (map exists in the build configuration), auto-checked,',
             'inspected. Types are hints. Private: lists the game\'s place names.', '']
    by_region = {}
    for place in places:
        by_region.setdefault(place['region'] or '(no region)', []).append(place)
    for region in sorted(by_region):
        group = by_region[region]
        done = sum(p['converted'] for p in group)
        lines += ['## %s (%d places, %d converted)' % (region, len(group), done), '']
        for p in sorted(group, key=lambda p: (p['kind'] != 'exterior place', p.get('settlement') or '', p['name'])):
            if p['kind'] == 'exterior place':
                where = 'grid ' + ', '.join('%d,%d' % tuple(g) for g in p['grids'][:4]) + (' ...' if len(p['grids']) > 4 else '')
            elif p['entrances']:
                e = p['entrances'][0]
                where = '%s, door at grid %d,%d' % (e['exterior'] or 'wilderness', *e['grid'])
            elif p['reached_through']:
                where = 'inside ' + p['reached_through']
            else:
                where = 'no door from the exterior'
            lines.append('- [%s] converted  [ ] auto-checked  [ ] inspected - %s (%s) - %s' % (
                'x' if p['converted'] else ' ', p['name'], p['kind'], where))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--esm', type=Path, required=True, help="The user's own Morrowind.esm")
    p.add_argument('--markdown', type=Path, help='Checklist output (keep private)')
    p.add_argument('--json', type=Path, help='Machine-readable output (keep private)')
    a = p.parse_args(argv)
    places = build(a.esm.read_bytes(), converted_cells(ROOT))
    if a.markdown:
        a.markdown.write_text(markdown(places), encoding='utf-8', newline='\n')
    if a.json:
        a.json.write_text(json.dumps(places, indent=1) + '\n', encoding='utf-8', newline='\n')
    kinds = Counter(p['kind'] for p in places)
    print('%d places (%d converted): %s' % (len(places), sum(p['converted'] for p in places),
          ', '.join('%s %d' % kv for kv in kinds.most_common())))


if __name__ == '__main__':
    main()
