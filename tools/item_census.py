#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Item census (DROP-ALL-TEST-58): can every kind of item be shown in the inventory and drawn on the ground?

For every carriable item record of the game's masters (weapons, armour, clothing, potions, ingredients, books, misc
items split into plain, gold and keys, carried lights, apparatus, lockpicks, probes, repair tools) it answers, per kind:

  records         carriable item records (a deleted record is gone, the spell-visual vfx_* weapons and spell bolts are not items,
                  a light that cannot be carried is scenery)
  catalogued      a row of the inventory catalogue (tools/prepare_inventory.py source_items); without a row an item
                  can be neither owned nor dropped
  icon field      the record names an inventory picture (ITEX; ALCH: TEXT)
  icon built      the picture is in the icon table of an image (--id1 only)
  model field     the record names a world model (MODL)
  model in table  that mesh has a model in the item model table (tools/prepare_item_models.py): the builder's own
                  mesh list, or the receipt of a real build (--receipt: the meshes it held back are counted as
                  missing)
  model drawn     the catalogue row of an image names an existing model file (--id1 only)

check() turns the numbers into failures: a kind with items missing from the catalogue, a kind whose records name
a model or picture the build does not carry, a kind with no drawable model or no picture at all. A record that
names no model or no picture is listed (private output) and counted, not failed: there is nothing to convert.
Read-only; nothing of the game is written into the repo. Usage:

  tools/item_census.py --data-files DIR [--receipt item-models-receipt.json] [--id1 IMAGE/boot/id1]
                       [--json OUT] [--private OUT]

Exit 0 when check() finds nothing, 1 when it lists failures."""
import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]   # src first: the mwad package, not tools/mwad.py

# Kind labels, in the order of the report. 'LIGH' means the carried lights only.
KIND_LABELS = ('WEAP', 'ARMO', 'CLOT', 'ALCH', 'INGR', 'BOOK', 'MISC', 'MISC:gold', 'MISC:key', 'LIGH', 'APPA',
               'LOCK', 'PROB', 'REPA')
COLUMNS = ('records', 'catalogued', 'icon_field', 'icon_built', 'model_field', 'model_in_table', 'model_drawn')
EFFECT_PREFIX = 'vfx_'      # spell-visual pseudo weapons, not items
# The spell projectiles the game also lists as weapons: no inventory picture, no geometry in their mesh (the item
# model stage reports them held back), never carried or placed.
EFFECT_IDS = frozenset(('magic_bolt', 'shield_bolt', 'shock_bolt'))


def kind_label(tag, rec):
    """The census kind of an item record read by item_coverage.read_masters (MISC: 'type' 1 = key flag set)."""
    if tag == 'MISC':
        if rec['id'].casefold().startswith('gold_'):
            return 'MISC:gold'
        return 'MISC:key' if rec['type'] == 1 else 'MISC'
    return tag


def census_records(items):
    """[{'id', 'kind', 'model', 'icon'}] of the carriable item records of read_masters' result."""
    out = []
    for tag in sorted(items):
        for key, rec in sorted(items[tag].items()):
            if not rec['carry'] or (tag == 'WEAP' and (key.startswith(EFFECT_PREFIX) or key in EFFECT_IDS)):
                continue
            out.append({'id': rec['id'], 'kind': kind_label(tag, rec), 'model': rec['model'], 'icon': rec['icon']})
    return out


def mesh_key(path):
    """The key of a world model in the item model table (tools/prepare_inventory.py mesh_key)."""
    return str(path).replace('\\', '/').strip().casefold()


def census(records, catalogued, table_keys, held=(), icon_ids=None, drawn_ids=None):
    """{'by_kind': {label: {column: n}}, 'all': {column: n}, 'gaps': {label: {column: [ids]}}, 'no_field': {...}}.

    CATALOGUED: folded ids of the catalogue; TABLE_KEYS: mesh keys that have a model in the table; HELD: mesh keys
    the model stage could not convert (never counted as in the table); ICON_IDS / DRAWN_IDS: folded ids with a
    built icon / a drawable catalogue model in an image, or None when no image is given (columns are then None)."""
    held = set(held)
    by_kind = {k: dict.fromkeys(COLUMNS, 0) for k in KIND_LABELS}
    gaps = {k: {c: [] for c in COLUMNS[1:]} for k in KIND_LABELS}
    no_field = {k: {'icon': [], 'model': []} for k in KIND_LABELS}
    for rec in records:
        kind, key = rec['kind'], rec['id'].casefold()
        row = by_kind[kind]
        row['records'] += 1
        has = {'catalogued': key in catalogued}
        has['icon_field'] = bool(rec['icon'])
        has['model_field'] = bool(rec['model'])
        if not rec['icon']:
            no_field[kind]['icon'].append(rec['id'])
        if not rec['model']:
            no_field[kind]['model'].append(rec['id'])
        mesh = mesh_key(rec['model']) if rec['model'] else ''
        has['model_in_table'] = bool(mesh) and mesh in table_keys and mesh not in held
        if icon_ids is not None:
            has['icon_built'] = key in icon_ids
        if drawn_ids is not None:
            has['model_drawn'] = key in drawn_ids
        for column, value in has.items():
            if value:
                row[column] += 1
            # a missing field is "nothing to convert" (no_field), not a gap of the build
            elif column in ('catalogued',) or (column == 'icon_built' and rec['icon']) or \
                    (column in ('model_in_table', 'model_drawn') and rec['model']):
                gaps[kind][column].append(rec['id'])
    for kind, row in by_kind.items():
        if icon_ids is None:
            row['icon_built'] = None
        if drawn_ids is None:
            row['model_drawn'] = None
    total = {c: (None if all(by_kind[k][c] is None for k in KIND_LABELS) else
                 sum(by_kind[k][c] or 0 for k in KIND_LABELS)) for c in COLUMNS}
    return {'by_kind': by_kind, 'all': total, 'gaps': gaps, 'no_field': no_field}


def check(result):
    """The failures of a census result, one plain sentence each (an empty list: every kind can be dropped)."""
    failures = []
    for kind in KIND_LABELS:
        row, gap = result['by_kind'][kind], result['gaps'][kind]
        if row['records'] == 0:
            failures.append('%s: no item records at all (the kind is missing from the census)' % kind)
            continue
        for column, text in (('catalogued', 'are not in the inventory catalogue'),
                             ('model_in_table', 'name a world model that is not in the item model table'),
                             ('icon_built', 'name an inventory picture that the image does not carry'),
                             ('model_drawn', 'have a catalogue row without a drawable world model')):
            if gap[column]:
                failures.append('%s: %d of %d items %s' % (kind, len(gap[column]), row['records'], text))
        if row['model_field'] == 0:
            failures.append('%s: no item of the kind names a world model' % kind)
        if row['icon_field'] == 0:
            failures.append('%s: no item of the kind names an inventory picture' % kind)
    return failures


def table_text(result):
    head = ['kind'] + list(COLUMNS) + ['no icon field', 'no model field']
    lines = ['| ' + ' | '.join(head) + ' |', '| --- |' + ' ---: |' * (len(head) - 1)]
    for label in KIND_LABELS + ('all',):
        row = result['all'] if label == 'all' else result['by_kind'][label]
        cells = ['-' if row[c] is None else '{:,}'.format(row[c]) for c in COLUMNS]
        if label == 'all':
            extra = [sum(len(result['no_field'][k][f]) for k in KIND_LABELS) for f in ('icon', 'model')]
        else:
            extra = [len(result['no_field'][label][f]) for f in ('icon', 'model')]
        lines.append('| ' + ' | '.join([label] + cells + ['{:,}'.format(n) for n in extra]) + ' |')
    return '\n'.join(lines)


def read_image(id1):
    """(folded ids with a built icon, folded ids whose catalogue row names an existing model) of an image's id1."""
    id1 = Path(id1)
    icons, drawn = set(), set()
    table = id1 / 'gfx' / 'icons.awl'
    if table.is_file():
        raw = table.read_bytes()
        if raw[:4] != b'AWL2':
            raise ValueError('not an AWL2 icon table: %s' % table)
        for i in range(struct.unpack_from('<I', raw, 4)[0]):
            name = raw[8 + 160 * i: 8 + 160 * i + 64].split(b'\0')[0].decode('cp1252').casefold()
            if name.startswith('inv:'):
                icons.add(name[4:])
    catalogue = id1 / 'inventory' / 'items.awi'
    if catalogue.is_file():
        raw = catalogue.read_bytes()
        if raw[:4] != b'AWI2':
            raise ValueError('not an AWI2 inventory catalogue: %s' % catalogue)
        for i in range(struct.unpack_from('<I', raw, 4)[0]):
            row = raw[8 + 512 * i: 8 + 512 * (i + 1)]
            model = row[184:248].split(b'\0')[0].decode('cp1252')
            if model and (id1 / model).is_file():
                drawn.add(row[:64].split(b'\0')[0].decode('cp1252').casefold())
    return icons, drawn


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', required=True, help='the game data folder (Morrowind.esm)')
    p.add_argument('--masters', default='Morrowind.esm', help='comma list of masters to read (default: the one the '
                   'builder catalogues)')
    p.add_argument('--receipt', help="a build's item-models-receipt.json (models it converted and held back)")
    p.add_argument('--id1', help="an image's boot/id1 folder (icon table and catalogue)")
    p.add_argument('--json', help='counts as JSON (no item ids)')
    p.add_argument('--private', help='every gap and missing field with its item ids (private output)')
    a = p.parse_args(argv)
    import item_coverage
    from mwad.paths import resolve_data_files
    item_coverage.MASTERS = tuple(m.strip() for m in a.masters.split(',') if m.strip())
    items, _placed = item_coverage.read_masters(a.data_files)
    records = census_records(items)
    data = resolve_data_files(Path(a.data_files))
    from prepare_inventory import source_items
    from prepare_item_models import meshes
    catalogued = set(source_items(data)[0])
    held = ()
    if a.receipt:
        receipt = json.loads(Path(a.receipt).read_text(encoding='utf-8'))
        table_keys, held = set(receipt['models']), set(receipt.get('held', {}))
        source = 'the receipt %s' % Path(a.receipt).name
    else:
        table_keys = set(meshes(data))
        source = "the builder's mesh list (conversion not verified: pass --receipt of a build)"
    icon_ids, drawn_ids = read_image(a.id1) if a.id1 else (None, None)
    result = census(records, catalogued, table_keys, held, icon_ids, drawn_ids)
    print(table_text(result))
    print('\nmodel table from %s; masters: %s' % (source, ', '.join(item_coverage.MASTERS)))
    failures = check(result)
    for line in failures:
        print('FAIL ' + line)
    print('item census: %s' % ('%d failure(s)' % len(failures) if failures else 'every kind can be shown and dropped'))
    if a.json:
        Path(a.json).write_text(json.dumps({'by_kind': result['by_kind'], 'all': result['all'],
                                            'failures': failures}, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.private:
        Path(a.private).write_text(json.dumps({'gaps': result['gaps'], 'no_field': result['no_field']}, indent=1) +
                                   '\n', encoding='utf-8', newline='\n')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
