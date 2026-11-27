#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The placed actor census: every actor row of every map of an image, judged on the model it stands in.

Why (ACTOR-CHECKS-MISS-PLACED-MODELS-69): the animation coverage table (tools/actor_library.py) reads the .bsp maps
only, 6 actors of about 3,100 in a full image, and counts a group as present when only the model worn in a fight
has it; the record audit took one model per record from the stage reports, placed or not. So actors built by an
older route passed unseen: the opening's people stand in their own 21-frame models with an idle and a walk group,
no item tag and, on the ship and the dock, their opening role kept.

What it reads, per actor row (classname aw_npc or aw_corpse) of maps/*.bsp and maps/*.chim (lump 0, the entity
text) and per base text of the actor table (maps/chim-actors.cca: the exterior cells' actors, which no map row
holds; listed with the table's name as their map): the record id, the reference, the standing model, and beside the model in progs/: its layout's own groups
(<model>.anm, without the groups of a '>' fight model), the fight model the layout links, and the item tags
(<model>.tag) of both.

Findings, one per row and kind:

  opening role kept        an aw_npc row with aw_intro_role 1 to 5 (the engine clears 6 to 8 at the spawn): the engine
                           gives such an actor no talk, name, greeting, idle line, behaviour package or engage check
  fight groups only on the fight model
                           the standing model's own layout has no attack group while it links a fight model: every
                           fight group (run, attack, hit, death) exists only on the model swapped in for a fight
  no item tag on the standing model
                           the linked fight model carries a weapon or shield tag, the standing model none: the actor
                           stands empty-handed until a fight
  no layout                an aw_npc row whose model is in the image without a layout: it plays its first frames only

config/actor-placed-census.json allows each kind up to a count, with the register entry that tracks it (or the
docs page that says it is by design); a count
over it, or a kind it does not name, stops the image step. The counts only go down: a fix lowers its row in the same
commit.

  python3 tools/actor_placed_census.py --id1 IMAGE/boot/id1 [--out DIR] [--allow FILE]

Writes DIR/actor-placed-census.json (every row) and prints the counts; exit 1 on a failure.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / 'config' / 'actor-placed-census.json'
REPORT = 'actor-placed-census.json'
ACTOR_CLASSES = ('aw_npc', 'aw_corpse')
TABLE = 'chim-actors.cca'
ROLE = 'opening role kept'
FIGHT_ONLY = 'fight groups only on the fight model'
NO_TAG = 'no item tag on the standing model'
NO_LAYOUT = 'no layout'
KINDS = (ROLE, FIGHT_ONLY, NO_TAG, NO_LAYOUT)
ROLES_KEPT = (1, 2, 3, 4, 5)          # engine/aga/src/aw_intro.c AW_IntroSpawn clears roles 6 to 8
_ENTITY = re.compile(r'\{[^{}]*\}')
_FIELD = re.compile(r'"([^"]+)"\s+"([^"]*)"')


def map_rows(path):
    """[{field: value}] of the entity text (lump 0) of a BSP29 or .chim map file; [] for a file too short."""
    raw = Path(path).read_bytes()
    if len(raw) < 12:
        return []
    off, size = struct.unpack_from('<ii', raw, 4)
    if off < 12 or size < 0 or off + size > len(raw):
        return []
    text = raw[off:off + size].decode('cp1252', 'replace')
    return [dict(_FIELD.findall(block)) for block in _ENTITY.findall(text)]


def table_bases(id1):
    """[{field: value}] of the actor table's base texts (maps/chim-actors.cca, tools/chim/actors.py): the actors of
    the exterior cells, which the engine spawns from the table and no map row holds; [] without a table."""
    path = Path(id1) / 'maps' / TABLE
    if not path.is_file():
        return []
    from chim.actors import read_table      # tools/ is on the path of every caller (the builder, the tests)
    out = []
    for base in read_table(path.read_bytes())[3]:
        fields = dict(_FIELD.findall(base.get('text') or ''))
        if fields:
            out.append(fields)
    return out


def layout(id1, model):
    """(own groups, fight model or None, has voice lines, has footsteps) of MODEL's layout; None without one."""
    path = Path(id1) / (model[:-4] + '.anm')
    if not path.is_file():
        return None
    words = path.read_text(encoding='cp1252').split()
    movers = [w[1:] for w in words if w.startswith('>')]
    return (sorted({w.split(':')[0] for w in words if w[:1] not in '@!~>'}), movers[0] if movers else None,
            any(w.startswith('!') for w in words), any(w[:1] in '@~' for w in words))


def tag(id1, model):
    """{'weapon', 'shield', 'light'} of MODEL's item tag (the paths it names, None for none); None without a tag."""
    path = Path(id1) / (model[:-4] + '.tag')
    if not path.is_file():
        return None
    out = {'weapon': None, 'shield': None, 'light': None}
    for line in path.read_text(encoding='cp1252').splitlines():
        words = line.split()
        if len(words) >= 2 and words[0] in out and words[1] != '-':
            out[words[0]] = words[1]
    return out


def rows(id1):
    """One dict per actor row of ID1's maps, sorted by map then reference."""
    id1 = Path(id1)
    out = []
    models = {}

    def facts(model):
        if model not in models:
            own = layout(id1, model)
            models[model] = {'in_image': (id1 / model).is_file(), 'layout': own, 'tag': tag(id1, model)}
        return models[model]

    from map_files import map_files            # every map file of the folder, whatever its extension
    maps = map_files(id1 / 'maps')
    sources = [(path.name, map_rows(path)) for path in maps]
    sources.append((TABLE, table_bases(id1)))
    for name, entities in sources:
        for f in entities:
            model = f.get('model', '')
            if f.get('classname') not in ACTOR_CLASSES or not model.endswith('.mdl'):
                continue
            m = facts(model)
            own = m['layout']
            mover = own[1] if own else None
            mm = facts(mover) if mover else None
            try:
                role = int(float(f.get('aw_intro_role', 0) or 0))
            except ValueError:
                role = 0
            row = {'map': name, 'classname': f['classname'], 'record': f.get('aw_source_id', '').casefold(),
                   'reference': f.get('aw_ref', ''), 'name': f.get('netname', ''), 'model': model, 'role': role,
                   'own_groups': own[0] if own else None, 'voice_lines': bool(own and own[2]),
                   'footsteps': bool(own and own[3]), 'fight_model': mover,
                   'fight_groups': mm['layout'][0] if mm and mm['layout'] else None,
                   'tag': m['tag'], 'fight_tag': mm['tag'] if mm else None}
            found = []
            if f['classname'] == 'aw_npc':
                if role in ROLES_KEPT:
                    found.append(ROLE)
                if own is None:
                    if m['in_image']:
                        found.append(NO_LAYOUT)
                elif mover and 'attack' not in own[0]:
                    found.append(FIGHT_ONLY)
                if mm and mm['tag'] and (mm['tag']['weapon'] or mm['tag']['shield']) and not m['tag']:
                    found.append(NO_TAG)
            row['findings'] = found
            out.append(row)
    return out


def placed_models(census):
    """{record id: sorted models its rows stand in} of a census document (or its rows)."""
    out = {}
    for row in census['rows'] if isinstance(census, dict) else census:
        if row.get('record'):
            out.setdefault(row['record'], set()).add(row['model'])
    return {k: sorted(v) for k, v in out.items()}


def document(all_rows):
    counts = {k: 0 for k in KINDS}
    actors = {k: set() for k in KINDS}
    for row in all_rows:
        for k in row['findings']:
            counts[k] += 1
            actors[k].add(row['record'] or row['model'])
    in_maps = [r for r in all_rows if r['map'] != TABLE]
    return {'format': 'AmiWind placed actor census 1', 'maps_with_actors': len({r['map'] for r in in_maps}),
            'actors': sum(1 for r in in_maps if r['classname'] == 'aw_npc'),
            'bodies': sum(1 for r in in_maps if r['classname'] == 'aw_corpse'),
            'table_bases': len(all_rows) - len(in_maps),
            'findings': counts, 'finding_records': {k: sorted(v) for k, v in actors.items()}, 'rows': all_rows}


def failures(doc, allow):
    """The lines that stop the image: a finding kind over its allowed count, or one the allow file does not name."""
    bad = []
    for kind, n in doc['findings'].items():
        row = allow.get(kind)
        if not n:
            continue
        if row is None:
            bad.append('%s: %d row(s), not named in config/actor-placed-census.json' % (kind, n))
        elif n > int(row.get('rows', 0)):
            bad.append('%s: %d row(s), %d allowed (%s): e.g. %s' % (
                kind, n, int(row.get('rows', 0)), row.get('register', 'no register entry'),
                ', '.join(doc['finding_records'][kind][:4])))
        elif not row.get('register') and not row.get('by_design'):
            bad.append('%s: allowed without a register entry or a by_design page' % kind)
    return bad


def read_allow(path=ALLOW):
    return json.loads(Path(path).read_text(encoding='utf-8'))['allow']


def stage(id1, out, allow=ALLOW):
    """The image step: write OUT/actor-placed-census.json and stop (ValueError) on a failure."""
    doc = document(rows(id1))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / REPORT).write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('Placed actor census: %d actors and %d bodies in %d maps, %d actor table bases; %s' % (
        doc['actors'], doc['bodies'], doc['maps_with_actors'], doc['table_bases'],
        ', '.join('%s %d' % kv for kv in doc['findings'].items())), flush=True)
    bad = failures(doc, read_allow(allow))
    if bad:
        raise ValueError('Placed actor census failed (ACTOR-CHECKS-MISS-PLACED-MODELS-69): ' + '; '.join(bad))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--id1', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--allow', type=Path, default=ALLOW)
    a = ap.parse_args(argv)
    doc = document(rows(a.id1))
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / REPORT).write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('placed actors %d, bodies %d, maps with actors %d, actor table bases %d' % (
        doc['actors'], doc['bodies'], doc['maps_with_actors'], doc['table_bases']))
    for kind, n in doc['findings'].items():
        print('  %-40s %5d rows  %s' % (kind, n, ', '.join(doc['finding_records'][kind][:6])))
    bad = failures(doc, read_allow(a.allow))
    for line in bad:
        print('FAIL ' + line)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
