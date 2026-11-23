"""The draw distance by region (REGIONAL-DRAW-DISTANCE-68): config/region-draw-distance.json, the repo default, becomes
world/region-draw.txt at the image step.

The engine (engine/aga/src/aw_fog.c) knows a cell's region by its index in the image's region catalogue
(world/region-names.awn and world/region-weather.aww, tools/prepare_world_ui.py: the sorted, case-folded REGN ids of the
build's merged masters, mwad.masters.master_path). This module writes one line per table row whose region is in that
catalogue, in the same order:

    # comment lines
    universal 300
    <catalogue index> <distance> <default|trial> <region id>

A row of a region the build's masters lack (the base game alone has no Solstheim) is left out and named in the report.
The engine reads at most ENGINE_ROWS rows, once; its universal value is its own constant, kept equal to the table's
and to tools/build_aga.py DEFAULT_FOG_DISTANCE by tests/test_region_draw.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'config' / 'region-draw-distance.json'
OUTPUT = 'world/region-draw.txt'
FORMAT = 'AmiWind region draw distance 1'
STATES = ('default', 'trial')
ENGINE_ROWS = 16          # engine/aga/src/aw_fog.c REGION_ROWS
DISTANCE_RANGE = (100, 4096)


def load(path=TABLE):
    """The validated table: {'universal': int, 'regions': [{'id', 'distance', 'state', ...}]}."""
    table = json.loads(Path(path).read_text(encoding='utf-8'))
    if table.get('format') != FORMAT:
        raise ValueError('%s: format must be %r' % (path, FORMAT))
    universal = table.get('universal')
    if not isinstance(universal, int) or not DISTANCE_RANGE[0] <= universal <= DISTANCE_RANGE[1]:
        raise ValueError('%s: universal must be a whole number of local units in %d..%d' % ((path,) + DISTANCE_RANGE))
    rows = table.get('regions')
    if not isinstance(rows, list) or len(rows) > ENGINE_ROWS:
        raise ValueError('%s: regions must be a list of at most %d rows (the engine reads that many)' % (path, ENGINE_ROWS))
    seen = set()
    for row in rows:
        ident = row.get('id')
        if not isinstance(ident, str) or not ident or ident != ident.casefold().strip() or len(ident.encode()) > 60:
            raise ValueError('%s: a row id must be the game\'s region id, case folded: %r' % (path, ident))
        if ident in seen:
            raise ValueError('%s: region %r listed twice' % (path, ident))
        seen.add(ident)
        distance = row.get('distance')
        if not isinstance(distance, int) or not DISTANCE_RANGE[0] <= distance <= DISTANCE_RANGE[1]:
            raise ValueError('%s: %s: distance must be a whole number in %d..%d' % ((path, ident) + DISTANCE_RANGE))
        if row.get('state') not in STATES:
            raise ValueError('%s: %s: state must be one of %s' % (path, ident, ', '.join(STATES)))
    return table


def region_order(raw):
    """The case-folded REGN ids of a master in the catalogue's order (sorted, deleted records left out), as
    tools/prepare_world_ui.py region_names orders world/region-names.awn."""
    from mwad.audit import records, subrecords, string
    ids = set()
    for tag, _flags, payload in records(raw):
        if tag != 'REGN':
            continue
        fields = dict(subrecords(payload))
        if 'DELE' in fields:
            continue
        ids.add(string(fields['NAME']).casefold())
    return sorted(ids)


def table_text(table, order):
    """(text of world/region-draw.txt, report) for the table and the catalogue ORDER of the image's masters."""
    index = {ident: i for i, ident in enumerate(order)}
    # every line under the engine's 96-byte line buffer (aw_fog.c region_table_read)
    lines = ['# config/region-draw-distance.json: catalogue index, distance, state, region id',
             'universal %d' % table['universal']]
    written, missing = [], []
    for row in table['regions']:
        if row['id'] not in index:
            missing.append(row['id'])
            continue
        lines.append('%d %d %s %s' % (index[row['id']], row['distance'], row['state'], row['id']))
        written.append({'id': row['id'], 'index': index[row['id']], 'distance': row['distance'], 'state': row['state']})
    return '\n'.join(lines) + '\n', {'universal': table['universal'], 'rows': written, 'not_in_masters': missing,
                                     'trial_rows': sum(1 for r in written if r['state'] == 'trial')}


def write(data_files, id1, table=None):
    """The image step: world/region-draw.txt in ID1 from the build's merged masters; returns the report."""
    from mwad.masters import master_path
    text, report = table_text(table or load(), region_order(master_path(data_files).read_bytes()))
    out = Path(id1) / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='ascii', newline='\n')
    report['bytes'] = len(text)
    return report
