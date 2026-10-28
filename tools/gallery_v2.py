#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""NPC Gallery v2.0: the gallery of the actors the game build has already made (NPC-GALLERY-V2).

The maintainer, 27 October 2026: "redo the NPC gallery ... so that it no longer uses the pre-baked stuff but our
latest models", "so that it basically does NOT bake or render any extra characters that we haven't built already",
"but uses the existing one's features so that you can look up npc's etc.", "the default type of npcgallery, NPC
Gallery v2.0".

The previous gallery (tools/build_gallery.py, the npc-gallery stage) baked its own copy of every NPC and creature
record: about 3,551 models, 7,107 files and 234 MB in the v0.0.53 image, 23 to 57 minutes of conversion when its cache
missed. Version 2.0 bakes nothing. The image step reads the actor rows the finished maps already carry (the town,
region frame and interior maps' aw_npc / aw_corpse entities) and the CHIM actor table's bases (the actor library's
creatures and NPCs), keeps one row per record, and writes one catalogue file, gallery/actors.txt. In the game the
gallery spawns the chosen actor from that row with the engine's own spawn path (ED_ParseEdict and the QuakeC spawn
function, as aw_actors.c does for a joining frame), so the gallery shows exactly the model, skeleton, animation table,
carried items and voice the game uses; a fix to an actor shows in the gallery at once.

The inspection room (maps/charplane.bsp: a lit floor, no game content) is compiled here as before (seconds); the
combat floor test (dbg combattest gallery) uses the same room.

Catalogue (gallery/actors.txt, cp1252, one row per line, tab separated):
  AWG2 <rows>
  <number> <kind NPC_|CREA> <record id> <name> <race> <class> <cell> <model> <entity text>
number: stable for one master (sorted by kind, then record id), the browse order is by name. The entity text is the
row's fields without the per-placement ones (quoted field and value pairs on one line, no tabs or line breaks).

The previous method stays selectable (--npc-gallery-method baked; DON'T DELETE ANY METHOD); the engine reads
gallery/catalog.txt (AWG1) when an image has no gallery/actors.txt.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# src/ ahead of tools/: run as a script, tools/mwad.py would hide the src/mwad package (actor_library.py's rule,
# BUILD-ACTOR-LIBRARY-MWAD-PATH-47)
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

FORMAT = 'AWG2'
RECEIPT_FORMAT = 'AmiWind NPC Gallery v2.0'
CATALOGUE = 'gallery/actors.txt'
ROOM = 'maps/charplane.bsp'
ACTOR_CLASSES = ('aw_npc', 'aw_corpse')
# per-placement fields: the gallery stands the actor on its own floor (chim/actors.py INSTANCE_FIELDS and the
# scene-only fields)
INSTANCE_FIELDS = ('origin', 'angles', 'angle', 'aw_ref', 'aw_ground_baked', 'aw_ground_valid', 'aw_authored_origin',
                   'aw_authored_z', 'targetname', 'target', 'aw_story_hidden', 'aw_intro_role')
# the engine's row buffer (aw_gallery.c GALLERY_ROW) and the text it parses (GALLERY_TEXT)
ROW_LIMIT = 2047
TEXT_LIMIT = 1400
# dropped in this order from a text over TEXT_LIMIT (the greeting lines; the voice table still has the record's)
LONG_FIELDS = ('aw_greeting_again', 'aw_greeting', 'aw_line')
ENTITY = re.compile(rb'\{([^{}]*)\}')
FIELD = re.compile(rb'"([^"]*)"\s+"([^"]*)"')
METHODS = ('v2', 'baked')


def method(args):
    """The build's gallery method: --npc-gallery-method, else v2 (the default since v0.0.54). An rc3 image recovery
    (--recover-image-from, tools/recover_image.py) rebuilds that run's baked gallery as before."""
    if not getattr(args, 'npc_gallery_method', None) and (getattr(args, 'recover_image_from', None) or
                                                          getattr(args, 'builder', None) == 'legacy'):
        # and the legacy builder's plan stays as it was (tests/test_chim_no_legacy)
        return 'baked'
    return getattr(args, 'npc_gallery_method', None) or 'v2'


def image_option(args, run):
    """The image step's gallery option: --no-npc-gallery, --gallery-v2 or the baked stage's --gallery RUN/npc-gallery.
    A MiniWind keeps leaving the gallery out unless the method is named (--npc-gallery-method v2)."""
    if getattr(args, 'no_npc_gallery', False):
        return ['--no-npc-gallery']
    if method(args) == 'baked':
        return ['--gallery', run / 'npc-gallery']
    if getattr(args, 'miniwind', False) and not getattr(args, 'npc_gallery_method', None):
        return ['--no-npc-gallery']
    return ['--gallery-v2']


def clean(value, limit=None):
    """A field value safe for the one-line entity text: no quotes, tabs or line breaks."""
    out = ''.join(' ' if c in '\t\r\n' else c for c in value if c not in '"\0')
    return out[:limit] if limit else out


def label(value, limit=95):
    """A catalogue label: printable ASCII, no tabs (prepare_gallery.safe_label's rule)."""
    return ''.join(c if 32 <= ord(c) <= 126 else '?' for c in value).replace('\t', ' ')[:limit]


def map_actor_rows(path):
    """Worker: the actor rows of one map file (lump 0 of a BSP29 or .chim frame map), file order."""
    import struct
    data = Path(path).read_bytes()
    if len(data) < 12:
        return []
    offset, length = struct.unpack_from('<ii', data, 4)
    out = []
    for body in ENTITY.findall(data[offset:offset + length]):
        row = {k.decode('latin1'): v.decode('latin1') for k, v in FIELD.findall(body)}
        if row.get('classname') in ACTOR_CLASSES and row.get('model') and \
                not float(row.get('aw_intro_role', 0) or 0):
            out.append(row)
    return out


def table_rows(id1):
    """The actor table's base rows (maps/chim-actors.cca: the actor library's creatures and NPCs), or []."""
    path = Path(id1) / 'maps/chim-actors.cca'
    if not path.is_file():
        return []
    from chim.actors import read_table
    _, _, _, bases, _ = read_table(path.read_bytes())
    rows = []
    for base in bases:
        if base['text']:
            row = {k.decode('latin1'): v.decode('latin1') for k, v in FIELD.findall(base['text'].encode('latin1'))}
            if row.get('classname') in ACTOR_CLASSES and row.get('model'):
                rows.append(row)
    return rows


def master_records(master):
    """{record id (casefolded): (kind, name, race, class, cell)} of every NPC_ and CREA record of the master; the cell
    is the first cell (interiors by name, exteriors by region or grid) that places it."""
    from mwad.audit import cell_data, records, string, subrecords
    actors, names = {}, {'RACE': {}, 'CLAS': {}}
    cells = {}
    for tag, flags, payload in records(Path(master).read_bytes()):
        if flags & 0x20:
            continue
        if tag in ('NPC_', 'CREA', 'RACE', 'CLAS'):
            fields = dict(subrecords(payload))
            if 'NAME' not in fields or 'DELE' in fields:
                continue
            ident = string(fields['NAME']).casefold()
            name = string(fields['FNAM']) if 'FNAM' in fields else ''
            if tag in names:
                names[tag][ident] = name
            else:
                actors[ident] = (tag, name, string(fields['RNAM']).casefold() if 'RNAM' in fields else '',
                                 string(fields['CNAM']).casefold() if 'CNAM' in fields else '')
        elif tag == 'CELL':
            try:
                cell = cell_data(list(subrecords(payload)))
            except ValueError:
                continue
            where = cell['name'] if cell['flags'] & 1 else '%s (%d, %d)' % (cell['region'] or cell['name'] or
                                                                                  'Exterior', cell['x'], cell['y'])
            for ref in cell['refs']:
                if not ref.get('deleted') and 'id' in ref:
                    cells.setdefault(ref['id'].casefold(), where)
    return {ident: (tag, name, names['RACE'].get(race, race), names['CLAS'].get(cls, cls), cells.get(ident, ''))
            for ident, (tag, name, race, cls) in actors.items()}


def entity_text(row):
    """(one-line entity text, dropped field names) of an actor row without its per-placement fields."""
    fields = [(k, clean(v)) for k, v in row.items() if k not in INSTANCE_FIELDS]
    dropped = []

    def joined():
        return ' '.join('"%s" "%s"' % kv for kv in fields)
    for name in LONG_FIELDS:
        if len(joined().encode('cp1252', 'replace')) <= TEXT_LIMIT:
            break
        if any(k == name for k, _ in fields):
            fields = [(k, v) for k, v in fields if k != name]
            dropped.append(name)
    text = joined()
    if len(text.encode('cp1252', 'replace')) > TEXT_LIMIT:
        raise ValueError('NPC gallery v2: actor %s: entity text %d bytes over %d' % (
            row.get('aw_source_id'), len(text), TEXT_LIMIT))
    return text, dropped


def collect(id1, jobs=1):
    """{record id (casefolded): row} of every actor the image places: the maps first (sorted by name; the first row
    of a record wins: towns, rooms and frames carry its greeting), then the actor table's bases. Rows whose model
    file is not in the image are returned apart: {record id: model}."""
    from build_parallel import ordered_map
    from map_files import map_files
    id1 = Path(id1)
    paths = map_files(id1 / 'maps')
    rows, missing = {}, {}
    # a model stored once under another name (tools/payload_share.py file aliases, id1/file-aliases.txt): the engine
    # opens the stored copy (aw_file_alias.c), so the row is shown
    aliases = {}
    if (id1 / 'file-aliases.txt').is_file():
        from payload_share import read_alias_table
        aliases = read_alias_table((id1 / 'file-aliases.txt').read_bytes())

    def present(name):
        return (id1 / name).is_file() or (name.casefold() in aliases and (id1 / aliases[name.casefold()]).is_file())
    found = ordered_map(map_actor_rows, [str(p) for p in paths], max(1, min(jobs, len(paths) or 1)),
                        cost=lambda path: Path(path).stat().st_size)   # the largest maps first
    for row in [r for batch in found for r in batch] + table_rows(id1):
        ident = (row.get('aw_source_id') or '').casefold()
        if not ident or ident in rows:
            continue
        if not present(row['model']):
            missing.setdefault(ident, row['model'])
            continue
        rows[ident] = row
        missing.pop(ident, None)
    return rows, missing


def catalogue_lines(rows, records):
    """The catalogue's lines (header first) and its report counts."""
    entries, dropped, unknown = [], {}, []
    for ident, row in rows.items():
        kind, name, race, cls, cell = records.get(ident, ('', '', '', '', ''))
        if not kind:
            unknown.append(ident)
            kind = 'CREA' if not row.get('aw_voice') and row.get('classname') != 'aw_corpse' else 'NPC_'
        text, cut = entity_text(row)
        if cut:
            dropped[ident] = cut
        entries.append(dict(kind=kind, id=ident, name=row.get('netname') or name or ident, race=race, cls=cls,
                            cell=cell, model=row['model'], text=text))
    entries.sort(key=lambda e: (e['kind'], e['id']))
    for number, e in enumerate(entries, 1):
        e['number'] = number
    entries.sort(key=lambda e: (label(e['name']).casefold(), e['id']))
    lines = ['%s %d' % (FORMAT, len(entries))]
    for e in entries:
        line = '\t'.join([str(e['number']), e['kind'], label(e['id']), label(e['name']), label(e['race'], 31),
                          label(e['cls'], 31), label(e['cell'], 63), label(e['model'], 63), e['text']])
        if len(line.encode('cp1252', 'replace')) > ROW_LIMIT:
            raise ValueError('NPC gallery v2: row of %s is %d bytes, over %d' % (e['id'], len(line), ROW_LIMIT))
        lines.append(line)
    counts = {'rows': len(entries), 'npcs': sum(e['kind'] == 'NPC_' for e in entries),
              'creatures': sum(e['kind'] == 'CREA' for e in entries),
              'corpses': sum('"classname" "aw_corpse"' in e['text'] for e in entries),
              'greeting_fields_dropped': dropped, 'not_in_master': sorted(unknown)}
    return lines, counts


def write_catalogue(id1, master, jobs=1):
    """Write gallery/actors.txt into ID1 from its finished maps; returns the report (counts, coverage, bytes)."""
    started = time.monotonic()
    id1 = Path(id1)
    rows, missing = collect(id1, jobs)
    records = master_records(master)
    lines, counts = catalogue_lines(rows, records)
    raw = ('\n'.join(lines) + '\n').encode('cp1252', 'replace')
    target = id1 / CATALOGUE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if target.read_bytes() != raw:
        raise ValueError('NPC gallery v2 catalogue readback differs')
    shown = set(rows)
    by_kind = {k: sorted(i for i, r in records.items() if r[0] == k and i not in shown) for k in ('NPC_', 'CREA')}
    report = dict(counts, format=RECEIPT_FORMAT, catalogue=CATALOGUE, bytes=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest(), baked_models=0,
                  master_records={'NPC_': sum(r[0] == 'NPC_' for r in records.values()),
                                  'CREA': sum(r[0] == 'CREA' for r in records.values())},
                  not_built_by_this_image={k: len(v) for k, v in by_kind.items()},
                  model_missing=dict(sorted(missing.items())),
                  seconds=round(time.monotonic() - started, 3))
    print('NPC Gallery v2.0: %d actors the image already holds (%d NPCs, %d creatures, %d corpses), %d bytes, '
          '%.1f s; nothing baked; %d NPC and %d creature records of the master are not placed by this image; %d '
          'rows name a model the image does not hold' % (
              report['rows'], report['npcs'], report['creatures'], report['corpses'], report['bytes'],
              report['seconds'], report['not_built_by_this_image']['NPC_'], report['not_built_by_this_image']['CREA'],
              len(missing)), flush=True)
    return report, by_kind


def build_room(palette, output, work, qbsp, vis, light):
    """Compile the inspection room (prepare_gallery.gallery_map: a floor and a sky box, no game content)."""
    from prepare_gallery import gallery_map
    from vis_options import light_args
    started = time.monotonic()
    work, output = Path(work), Path(output)
    work.mkdir(parents=True, exist_ok=False)
    gallery_map(work, Path(palette).read_bytes())
    with (work / 'compile.log').open('w', encoding='utf-8', newline='\n') as log:
        for command in ([str(Path(qbsp).resolve()), 'charplane.map'],
                        [str(Path(vis).resolve()), '-threads', '1', 'charplane.bsp'],
                        [str(Path(light).resolve()), *light_args('charplane.bsp')]):
            subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(work / 'charplane.bsp', output)
    raw = output.read_bytes()
    return {'room': ROOM, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'seconds': round(time.monotonic() - started, 3)}


def stage_room(id1, work, qbsp, vis, light):
    """The image step's first part: the room only (the catalogue waits for the finished maps: catalogue_step)."""
    id1 = Path(id1)
    if (id1 / 'gallery').exists():
        shutil.rmtree(id1 / 'gallery')
    (id1 / 'npc-gallery-disabled.txt').unlink(missing_ok=True)
    room = build_room(id1 / 'gfx/palette.lmp', id1 / ROOM, work, qbsp, vis, light)
    print('NPC Gallery v2.0: inspection room compiled in %.1f s (%d bytes); the catalogue is written from the '
          'finished maps' % (room['seconds'], room['bytes']), flush=True)
    return {'format': RECEIPT_FORMAT, 'status': 'room staged', 'room': room}


def catalogue_step(id1, master, out, report, jobs=1):
    """The image step's second part, on the finished maps: the catalogue; writes npc-gallery-staging.json and the
    private list of the master's records the image does not place (npc-gallery-v2-not-built.json)."""
    catalogue, not_built = write_catalogue(id1, master, jobs)
    if not catalogue['rows']:
        raise ValueError('NPC gallery v2: the image places no actor (no aw_npc row in any map or the actor table)')
    report = dict(report, status='passed', **catalogue)
    Path(out, 'npc-gallery-v2-not-built.json').write_text(json.dumps(not_built, indent=1) + '\n', encoding='utf-8',
                                                          newline='\n')
    Path(out, 'npc-gallery-staging.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8',
                                                     newline='\n')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--id1', type=Path, required=True, help="an image's id1 folder (its finished maps)")
    p.add_argument('--master', type=Path, required=True, help='Morrowind.esm')
    p.add_argument('--out', type=Path, required=True, help='a folder for the catalogue copy and the report')
    p.add_argument('--jobs', type=int, default=1)
    a = p.parse_args(argv)
    # measurement mode: the catalogue of an existing image, written beside it (OUT/gallery/actors.txt)
    a.out.mkdir(parents=True, exist_ok=True)
    rows, missing = collect(a.id1, a.jobs)
    lines, counts = catalogue_lines(rows, master_records(a.master))
    raw = ('\n'.join(lines) + '\n').encode('cp1252', 'replace')
    (a.out / 'actors.txt').write_bytes(raw)
    print(json.dumps(dict(counts, bytes=len(raw), model_missing=missing), indent=1))


if __name__ == '__main__':
    main()
