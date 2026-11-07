#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Every creature of the game's masters against what this build makes (FAUNA-COVERAGE-62).

Reads the masters the player owns (never written anywhere public; the census itself only counts) and works out, for
every creature record (CREA) of Morrowind, Tribunal and Bloodmoon, how the game data uses it:

- placed: its references in the exterior cells (per region) and in the interiors;
- levelled: the levelled creature lists (LEVC) that name it, and whether a list is used (placed, inside a used list,
  or placed by a script);
- summoned: named by a game setting sMagic...ID, the creature a summoning effect calls up (rule from OpenMW file
  apps/openmw/mwmechanics/summoning.cpp: the summoned creature's id is read from those settings);
- scripted: named by PlaceAtPC, PlaceAtMe, PlaceItem or PlaceItemCell in a script's text, directly or through a list.

With the build's facts (the record ids the image places: tools/gallery_v2.py, the maps and the actor table; the actor
library's models and their animation groups; the voice table's creature coverage) each record is built or not built,
and a record that is not built takes the first group of config/creature-census.json whose fact (and id patterns, when
it names some) matches it: an expansion master the image does not read, no model, a model the bake refused, summoned,
placed by a script, placed indoors only, not used by the game data. check() names every record that is not built and
that no group covers (an outdoor creature the build should have made, for one) and every master read that the config
does not name: the image step stops on any of them, so no creature is ever left out silently. `--data-files DIR
[--run RUN] [--json OUT]` prints it for an audit (RUN: a finished build run, for its image's facts).
"""
import argparse
from collections import Counter
import fnmatch
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
# run as a script, Python puts tools/ first and tools/mwad.py would hide the src/mwad package (as in actor_library.py)
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

CONFIG = ROOT / 'config/creature-census.json'
FORMAT = 'AmiWind creature census 1'
CENSUS = 'creature-census.json'        # beside the image step's receipts (private: it names record ids and cells)
STATUSES = ('missing', 'skipped')
FACTS = ('expansion', 'no_model', 'left_out', 'summon', 'script', 'interior', 'unused')
PLACE = re.compile(r'\bplace(?:atpc|atme|itemcell|item)\s*,?\s*(?:"([^"\r\n]+)"|([^\s,"]+))', re.I)
SUMMON_SETTING = re.compile(r'^smagic.*id$', re.I)
DEAD_OFFSET = 40                        # NPDT (96 bytes): health at byte 40 (creature_library.plan)


def load_config(path=None):
    config = json.loads(Path(path or CONFIG).read_text(encoding='utf-8'))
    if config.get('format') != 1:
        raise ValueError('Unsupported creature census config')
    names = set()
    for group in config['groups']:
        if group['name'] in names or group.get('status') not in STATUSES or group.get('when') not in FACTS:
            raise ValueError('Creature census group duplicate, with an unknown status or fact: ' + group['name'])
        names.add(group['name'])
        if group['status'] == 'missing' and not group.get('register'):
            raise ValueError('A missing group names its register entry: ' + group['name'])
        if group['status'] == 'skipped' and not group.get('reason'):
            raise ValueError('A skipped group names its reason: ' + group['name'])
    for group in config.get('levelled_points', ()):
        if not group.get('cells') or not group.get('register') or not group.get('reason') or group['name'] in names:
            raise ValueError('A levelled_points group names its cells, register entry and reason: ' + group['name'])
        names.add(group['name'])
    masters = config['masters']
    if not masters or masters[0]['name'] != 'Morrowind.esm' or masters[0].get('status') != 'read' or \
            any(m.get('status') != 'pending' or not m.get('register') for m in masters[1:]):
        raise ValueError('The base master is read; every other master is pending with its register entry')
    return config


def _string(data):
    return data.split(b'\0', 1)[0].decode('cp1252', 'replace')


def read_master(raw):
    """What one master holds for the census: {'creatures': {id: {mesh, name, flags, dead, aidt}}, 'deleted': {id},
    'lists': {id: [entry ids]}, 'cells': [(inside, region, cell, [(id, number)])], 'settings': {name: text},
    'scripts': {script id: [placed ids]}}; ids case-folded."""
    from mwad.audit import cell_data, normpath, records, subrecords
    out = dict(creatures={}, deleted=set(), lists={}, cells=[], settings={}, scripts={})
    topic = ''
    for tag, flags, payload in records(raw):
        if tag not in ('CREA', 'LEVC', 'CELL', 'GMST', 'SCPT', 'DIAL', 'INFO'):
            continue
        subs = list(subrecords(payload))
        fields = dict(subs)
        if tag == 'DIAL':
            topic = _string(fields.get('NAME', b'')).casefold()
            continue
        if tag == 'INFO':
            # a dialogue response's result script (BNAM) places creatures as a script does
            text = fields.get('BNAM', b'').decode('cp1252', 'replace')
            placed = sorted({(m.group(1) or m.group(2)).strip().casefold() for m in PLACE.finditer(text)})
            if placed:
                key = 'dialogue %s %s' % (topic, _string(fields.get('INAM', b'')))
                out['scripts'][key] = placed
            continue
        if tag == 'CELL':
            if flags & 0x20:
                continue
            cell = cell_data(subs)
            inside = bool(cell['flags'] & 1)
            refs = [(r['id'].casefold(), r['number']) for r in cell['refs'] if 'id' in r and not r.get('deleted')]
            out['cells'].append((inside, None if inside else (cell.get('region') or ''),
                                 cell['name'] if inside else (cell['x'], cell['y']), refs))
            continue
        if tag == 'GMST':
            if 'NAME' in fields and 'STRV' in fields and SUMMON_SETTING.match(_string(fields['NAME'])):
                out['settings'][_string(fields['NAME']).casefold()] = _string(fields['STRV']).casefold()
            continue
        if tag == 'SCPT':
            head = fields.get('SCHD', b'')
            name = _string(head[:32]).casefold() if head else ''
            text = fields.get('SCTX', b'').decode('cp1252', 'replace')
            placed = sorted({(m.group(1) or m.group(2)).strip().casefold() for m in PLACE.finditer(text)})
            if name and placed:
                out['scripts'][name] = placed
            continue
        if 'NAME' not in fields:
            continue
        ident = _string(fields['NAME']).casefold()
        if 'DELE' in fields or flags & 0x20:
            out['deleted'].add(ident)
            continue
        if tag == 'LEVC':
            out['lists'][ident] = [_string(d).casefold() for t, d in subs if t == 'CNAM']
            continue
        npdt = fields.get('NPDT', b'')
        out['creatures'][ident] = dict(
            mesh=normpath(_string(fields.get('MODL', b''))), name=_string(fields.get('FNAM', b'') or fields['NAME']),
            flags=struct.unpack('<I', fields['FLAG'])[0] if len(fields.get('FLAG', b'')) == 4 else 0,
            dead=len(npdt) == 96 and struct.unpack_from('<i', npdt, DEAD_OFFSET)[0] <= 0, aidt='AIDT' in fields)
    return out


def _reach(lists, roots):
    """Every list ROOTS reach (themselves and the lists inside them)."""
    seen, todo = set(), [r for r in roots if r in lists]
    while todo:
        lid = todo.pop()
        if lid in seen:
            continue
        seen.add(lid)
        todo.extend(e for e in lists[lid] if e in lists and e not in seen)
    return seen


def uses(masters):
    """{'records': {id: record + uses}, 'masters': [names], 'levelled_points': Counter per region} of MASTERS
    [(name, raw)] in load order (a later master's record of the same id replaces the earlier one; its cells add
    references). Each record: master (the first that defines it), mesh, name, dead, and per master read its uses:
    exterior {region: n}, interior {cell: n}, lists [ids], used_lists [ids], script [script ids], summon [settings]."""
    creatures, lists, settings, scripts = {}, {}, {}, {}
    cells = []
    for name, raw in masters:
        got = read_master(raw)
        for ident in got['deleted']:
            creatures.pop(ident, None)
            lists.pop(ident, None)
        for ident, row in got['creatures'].items():
            first = creatures.get(ident, {}).get('master', name)
            creatures[ident] = dict(row, master=first, final_master=name)
        lists.update(got['lists'])
        settings.update(got['settings'])
        scripts.update(got['scripts'])
        cells += [(name,) + c for c in got['cells']]
    placed_lists_ext, placed_lists_int = set(), set()
    placements, levelled = [], []
    rows = {i: dict(r, exterior=Counter(), interior=Counter(), placed_in=Counter(), lists=[], used_lists=[],
                    script=[], summon=[]) for i, r in creatures.items()}
    for master, inside, region, cell, refs in cells:
        where = 'interior' if inside else (region or 'no region')
        for ident, number in refs:
            if ident in rows:
                r = rows[ident]
                if inside:
                    r['interior'][cell] += 1
                else:
                    r['exterior'][where] += 1
                r['placed_in'][master] += 1
                placements.append((master, where, number, ident, cell))
            elif ident in lists:
                (placed_lists_int if inside else placed_lists_ext).add(ident)
                levelled.append((master, where, number, ident, cell))
    scripted_lists = {i for ids in scripts.values() for i in ids if i in lists}
    used = _reach(lists, placed_lists_ext | placed_lists_int | scripted_lists)
    for lid in sorted(lists):
        for entry in lists[lid]:
            if entry in rows and lid not in rows[entry]['lists']:
                rows[entry]['lists'].append(lid)
                if lid in used:
                    rows[entry]['used_lists'].append(lid)
    for sid, ids in sorted(scripts.items()):
        for ident in ids:
            for target in [ident] + ([e for lid in _reach(lists, {ident}) for e in lists[lid]] if ident in lists else []):
                if target in rows and sid not in rows[target]['script']:
                    rows[target]['script'].append(sid)
    for setting, ident in sorted(settings.items()):
        if ident in rows:
            rows[ident]['summon'].append(setting)
    return dict(records=rows, masters=[n for n, _ in masters], placements=placements, levelled=levelled,
                lists_used=len(used), lists=len(lists), scripts_placing=sum(
                    1 for ids in scripts.values() if any(i in rows or i in lists for i in ids)),
                summon_settings=len(settings))


def facts(row, base, image):
    """The facts of one record that is not built, in FACTS order (those that hold)."""
    out = []
    if row['master'] != base:
        out.append('expansion')
    if not row['mesh'] or (image.get('meshes') is not None and row['mesh'] not in image['meshes']):
        out.append('no_model')
    if row['mesh'] and row['mesh'] in image.get('left_out', {}):
        out.append('left_out')
    if row['summon']:
        out.append('summon')
    if row['script']:
        out.append('script')
    if row['interior'] and not row['exterior']:
        out.append('interior')
    if not (row['exterior'] or row['interior'] or row['used_lists'] or row['script'] or row['summon']):
        out.append('unused')
    return out


BLOCKING = ('no_model', 'left_out')     # a record without a model the build can make is never filed under another reason


def classify(config, ident, row_facts):
    if any(f in row_facts and not any(g['when'] == f for g in config['groups']) for f in BLOCKING):
        return None
    for group in config['groups']:
        if group['when'] in row_facts and (not group.get('ids') or
                                           any(fnmatch.fnmatchcase(ident, p.casefold()) for p in group['ids'])):
            return group
    return None


def held_points(config, points):
    """{'groups': [{name, register, reason, points, cells}], 'unclassified': [points]} of the base master's levelled
    creature points the image does not place: each in the first config 'levelled_points' group naming its cell."""
    groups = [dict(name=g['name'], register=g['register'], reason=g['reason'], points=0, cells=Counter())
              for g in config.get('levelled_points', ())]
    cells = [{c.casefold() for c in g['cells']} for g in config.get('levelled_points', ())]
    left = []
    for p in points:
        cell = p['cell'] if isinstance(p['cell'], str) else '%d,%d' % tuple(p['cell'])
        k = next((i for i, names in enumerate(cells) if cell.casefold() in names), None)
        if k is None:
            left.append(p)
            continue
        groups[k]['points'] += 1
        groups[k]['cells'][cell] += 1
    return dict(groups=[dict(g, cells=dict(g['cells'])) for g in groups], unclassified=left)


def expansion_group(config):
    return next((g for g in config['groups'] if g['when'] == 'expansion'), None)


def census(masters, config=None, image=None):
    """The census of MASTERS ([(name, raw)], the base master first). IMAGE: None (no build verdict: the data's uses
    only), or {'built': set of record ids the image places, 'meshes': set of meshes the data holds or None,
    'left_out': {mesh: reason}, 'kit_on_idle': {mesh: [groups]}, 'sounds_missing': [ids], 'partial': reason or None}."""
    config = config or load_config()
    statuses = {m['name']: m for m in config['masters']}
    unnamed = [n for n, _ in masters if n not in statuses]
    masters = [(n, raw) for n, raw in masters if n in statuses]
    base = masters[0][0] if masters else 'Morrowind.esm'
    data = uses(masters)
    image = image or {}
    built = image.get('built')
    groups = {g['name']: dict(name=g['name'], status=g['status'], when=g['when'], register=g.get('register'),
                              reason=g.get('reason'), records=[], placements=0, exterior=0, interior=0,
                              regions=Counter()) for g in config['groups']}
    refs = image.get('refs')            # reference numbers the image's maps place (None: not known)
    room_group = next((g for g in config['groups'] if g['when'] == 'interior'), None)
    built_rows, unmatched, unplaced, levelled_out, regions = [], [], [], [], {}
    record_group = {}
    for ident, row in sorted(data['records'].items()):
        if built is None or ident in built:
            if built is not None:
                built_rows.append(ident)
            continue
        found = facts(row, base, image)
        group = classify(config, ident, found)
        brief = dict(id=ident, name=row['name'], mesh=row['mesh'], master=row['master'], facts=found,
                     exterior=dict(row['exterior']), interior=len(row['interior']),
                     interior_placements=sum(row['interior'].values()), lists=row['used_lists'][:6],
                     scripts=row['script'][:6], summon=row['summon'])
        if group is None:
            unmatched.append(brief)
            continue
        record_group[ident] = group
        groups[group['name']]['records'].append(brief)
    # every placement: built, or not built for its record's reason, or (a record the image builds) a room placement
    # the room stage holds back; an outdoor placement of a built record is always spawned (the actor table)
    for master, where, number, ident, cell in data['placements']:
        region = regions.setdefault(where, Counter())
        region['placements'] += 1
        if built is None:
            continue
        inside = where == 'interior'
        if ident in built and master == base and (not inside or refs is None or number in refs):
            region['built'] += 1
            continue
        group = record_group.get(ident)
        if group is None and ident in built:
            group = expansion_group(config) if master != base else (room_group if inside else None)
        if group is None:
            if ident in built:
                unplaced.append(dict(id=ident, number=number, where=where, cell=cell, master=master))
            continue
        entry = groups[group['name']]
        entry['placements'] += 1
        entry['interior' if inside else 'exterior'] += 1
        entry['regions'][where] += 1
        region['missing'] += 1
        region['missing: ' + group['name']] += 1
    for master, where, number, _lid, cell in data['levelled']:
        region = regions.setdefault(where, Counter())
        region['levelled_points'] += 1
        if built is not None and master == base and (where != 'interior' or refs is None or number in refs):
            region['levelled_built'] += 1
        elif built is not None:
            levelled_out.append(dict(list=_lid, number=number, where=where, cell=cell, master=master))
    out_groups = [dict(g, regions=dict(sorted(g['regions'].items(), key=lambda kv: (-kv[1], kv[0]))))
                  for g in groups.values()]
    per_master = Counter(r['master'] for r in data['records'].values())
    on_idle = image.get('kit_on_idle') or {}
    partly = sorted({i for i in built_rows if data['records'][i]['mesh'] in on_idle})
    totals = dict(records=len(data['records']), per_master=dict(per_master),
                  placements=sum(c['placements'] for c in regions.values()),
                  levelled_points=sum(c['levelled_points'] for c in regions.values()),
                  lists=data['lists'], lists_used=data['lists_used'], scripts_placing=data['scripts_placing'],
                  summon_settings=data['summon_settings'])
    if built is not None:
        totals.update(built=len(built_rows), not_built=len(data['records']) - len(built_rows),
                      missing=sum(len(g['records']) for g in out_groups if g['status'] == 'missing'),
                      skipped=sum(len(g['records']) for g in out_groups if g['status'] == 'skipped'),
                      unclassified=len(unmatched), placements_unclassified=len(unplaced),
                      by_reason={g['name']: len(g['records']) for g in out_groups},
                      placements_built=sum(c['built'] for c in regions.values()),
                      levelled_built=sum(c['levelled_built'] for c in regions.values()),
                      built_with_groups_on_idle=len(partly),
                      built_without_sounds=len(set(image.get('sounds_missing') or ()) & set(built_rows)))
    return dict(format=FORMAT,
                masters=[dict(name=n, **{k: v for k, v in statuses[n].items() if k != 'name'}) for n, _ in masters],
                masters_not_in_config=unnamed, partial=image.get('partial'), totals=totals, groups=out_groups,
                unclassified=unmatched, placements_unclassified=unplaced[:200],
                levelled_not_built=held_points(config, [p for p in levelled_out if p['master'] == base]),
                levelled_not_built_expansions=sum(p['master'] != base for p in levelled_out),
                regions={k: dict(v) for k, v in sorted(regions.items(), key=lambda kv: (kv[0] == 'interior', kv[0]))},
                built_with_groups_on_idle={i: on_idle[data['records'][i]['mesh']] for i in partly},
                sounds_missing=sorted(set(image.get('sounds_missing') or ()) & set(built_rows)),
                rule='every creature record of the masters is built by the image or not built for the reason of a '
                     'group of config/creature-census.json')


def check(report):
    """Problems of a census (empty: passed). A partial build (a MiniWind) is reported, never stopped."""
    if report.get('partial'):
        return []
    problems = ['creature %s (%s, %s, %s; %s) is not built and no group of config/creature-census.json names why: '
                'register it and add it' % (u['id'], u['name'] or '-', u['mesh'] or 'no model', u['master'],
                                            ', '.join(u['facts']) or 'placed outdoors or in a used list')
                for u in report['unclassified']]
    problems += ['placement %s of %s (%s, %s) is not built although the image builds the creature'
                 % (p['number'], p['id'], p['where'], p['master']) for p in report['placements_unclassified']]
    problems += ['levelled creature point %s (%s in %s) is not placed and no levelled_points group of '
                 'config/creature-census.json names its cell' % (p['number'], p['list'], p['cell'])
                 for p in report['levelled_not_built']['unclassified']]
    problems += ['master %s is read but not named in config/creature-census.json' % n
                 for n in report['masters_not_in_config']]
    problems += ['built creature %s has no sounds in the voice table' % i for i in report['sounds_missing']]
    return problems


def read_masters(data_files, config=None):
    """[(name, raw)] of the config's masters that the data files hold, the base master first (required)."""
    from mwad.paths import child_ci, resolve_data_files
    config = config or load_config()
    data = resolve_data_files(data_files)
    out = []
    for index, row in enumerate(config['masters']):
        try:
            path = child_ci(data, row['name'])
        except (FileNotFoundError, OSError, ValueError):
            if index == 0:
                raise
            continue
        if path.is_file():
            out.append((row['name'], path.read_bytes()))
        elif index == 0:
            raise ValueError('The base master is missing: ' + row['name'])
    return out


class DataMeshes:
    """Whether the data holds a mesh (a path under meshes/, lower case): the archives' directories (read once, a
    fraction of a second), then the loose Meshes folder, walked only when a mesh is in no archive (a walk of the
    loose folder costs tens of seconds on a large install)."""

    def __init__(self, data_files):
        from mwad.audit import BSA
        from mwad.paths import resolve_data_files
        self.data = resolve_data_files(data_files)
        self.archived = set()
        for path in self.data.iterdir():
            if path.suffix.casefold() == '.bsa' and path.is_file():
                self.archived |= {n[len('meshes/'):] for n in BSA(path).entries if n.startswith('meshes/')}
        self.loose = None

    def __contains__(self, mesh):
        if mesh in self.archived:
            return True
        if self.loose is None:
            from mwad.audit import normpath
            folder = next((p for p in self.data.iterdir() if p.is_dir() and p.name.casefold() == 'meshes'), None)
            self.loose = set() if folder is None else {normpath(str(p.relative_to(folder)))
                                                       for p in folder.rglob('*') if p.is_file()}
        return mesh in self.loose


def image_facts(id1=None, out=None, library=None, data_files=None, master=None, partial=None, jobs=1):
    """The build's facts for census(): the record ids the image places (OUT/npc-gallery-v2-not-built.json when the
    gallery catalogue wrote it, else the maps and the actor table of ID1, tools/gallery_v2.collect), the actor
    library's left-out meshes and kit groups standing on the idle (LIBRARY/creature-library.json), the voice table's
    unmapped creatures (OUT/npc-voice-table.json) and the meshes of the data."""
    out = Path(out) if out else None
    built = None
    if out is not None and (out / 'npc-gallery-v2-not-built.json').is_file() and master is not None:
        from mwad.audit import records, subrecords
        ids = set()
        for tag, flags, payload in records(master):
            if tag == 'CREA' and not flags & 0x20:
                fields = dict(subrecords(payload))
                if 'NAME' in fields and 'DELE' not in fields:
                    ids.add(_string(fields['NAME']).casefold())
        not_built = json.loads((out / 'npc-gallery-v2-not-built.json').read_text(encoding='utf-8'))
        built = ids - set(not_built.get('CREA', ()))
    elif id1 is not None:
        from gallery_v2 import collect
        built = set(collect(id1, jobs)[0])
    left_out, on_idle = {}, {}
    manifest = Path(library) / 'creature-library.json' if library else None
    if manifest is not None and manifest.is_file():
        doc = json.loads(manifest.read_text(encoding='utf-8'))
        left_out = {k.split('@')[0].split('#')[0]: v for k, v in doc.get('left_out', {}).items()}
        on_idle = {k: m['groups_from_idle'] for k, m in doc.get('models', {}).items()
                   if '@' not in k and '#' not in k and m.get('groups_from_idle')}
    refs = None
    if id1 is not None and (Path(id1) / 'maps').is_dir():
        from build_parallel import ordered_map
        from map_files import map_files
        paths = [str(p) for p in map_files(Path(id1) / 'maps')]
        refs = set()
        for found in ordered_map(map_refs, paths, max(1, min(jobs, len(paths) or 1)),
                                 cost=lambda path: Path(path).stat().st_size):   # the largest maps first
            refs |= found
    sounds_missing = []
    if out is not None and (out / 'npc-voice-table.json').is_file():
        coverage = json.loads((out / 'npc-voice-table.json').read_text(encoding='utf-8')).get('coverage', {})
        sounds_missing = sorted(k.casefold() for k in coverage.get('creatures_unmapped') or {})
    return dict(built=built, refs=refs, meshes=DataMeshes(data_files) if data_files else None, left_out=left_out,
                kit_on_idle=on_idle, sounds_missing=sounds_missing, partial=partial)


ACTOR_ROWS = (b'aw_npc', b'aw_corpse', b'aw_levelled')
ENTITY = re.compile(rb'\{([^{}]*)\}')
FIELD = re.compile(rb'"([^"]*)"\s+"([^"]*)"')


def map_refs(path):
    """Worker: the reference numbers (aw_ref) of the actor rows of one map file (lump 0 of a BSP29 or .chim map):
    its placed creatures and NPCs, its corpses and its levelled creature points."""
    data = Path(path).read_bytes()
    if len(data) < 12:
        return set()
    offset, length = struct.unpack_from('<ii', data, 4)
    out = set()
    for body in ENTITY.findall(data[offset:offset + length]):
        row = dict(FIELD.findall(body))
        if row.get(b'classname') in ACTOR_ROWS and row.get(b'aw_ref', b'').isdigit():
            out.add(int(row[b'aw_ref']))
    return out


def summary(report):
    t = report['totals']
    if 'built' not in t:
        return ['Creature census: %d creature records (%s), %d placements, %d levelled spawn points (no build facts).'
                % (t['records'], ', '.join('%s %d' % kv for kv in t['per_master'].items()), t['placements'],
                   t['levelled_points'])]
    lines = ['Creature census: %d creature records (%s): %d built, %d not built (%d missing, %d skipped on purpose, '
             '%d unclassified); %d of %d placements built (%d unclassified), %d of %d levelled creature points%s.' % (
                 t['records'], ', '.join('%s %d' % kv for kv in t['per_master'].items()), t['built'], t['not_built'],
                 t['missing'], t['skipped'], t['unclassified'], t['placements_built'], t['placements'],
                 t['placements_unclassified'], t['levelled_built'], t['levelled_points'],
                 '; partial build: ' + report['partial'] if report.get('partial') else '')]
    for g in report['groups']:
        top = ', '.join('%s %d' % kv for kv in list(g['regions'].items())[:4])
        lines.append('  %-44s %-8s %4d records, %5d placements (%d outdoors, %d indoors)%s%s' % (
            g['name'], g['status'], len(g['records']), g['placements'], g['exterior'], g['interior'],
            ' [' + g['register'] + ']' if g['register'] else '', ': ' + top if top else ''))
    for g in report['levelled_not_built']['groups']:
        lines.append('  %-44s %4d levelled creature points not placed [%s]' % (g['name'], g['points'], g['register']))
    if t['built_with_groups_on_idle']:
        lines.append('  %d built records stand on their idle for a group their model lacks' % t['built_with_groups_on_idle'])
    return lines


def _region(name):
    if name == 'interior':
        return 'Rooms (all interiors)'
    if name == 'no region':
        return 'Outdoors, no region'
    return name[:-len(' Region')] if name.endswith(' Region') else name


def public_tables(report):
    """The census as the two Markdown tables of docs/CREATURES.md (counts only: no record ids or cells): per reason,
    and per region (placed creatures and levelled creature points, built and not built)."""
    t = report['totals']
    lines = ['| Creature records | Count | Placements | Status |', '| --- | ---: | ---: | --- |',
             '| Built by the image | %d | %d | built |' % (t['built'], t['placements_built'])]
    for g in report['groups']:
        status = 'skipped on purpose' if g['status'] == 'skipped' else \
            'missing ([%s](bugs/%s.md))' % (g['register'], g['register'])
        lines.append('| %s | %d | %d | %s |' % (g['name'], len(g['records']), g['placements'], status))
    lines.append('| All | %d | %d | |' % (t['records'], t['placements']))
    lines += ['', '| Region | Placed creatures | Built | Not built | Levelled creature points | Placed by the image |',
              '| --- | ---: | ---: | --- | ---: | ---: |']
    rows = sorted(report['regions'].items(), key=lambda kv: (kv[0] == 'interior', -kv[1].get('placements', 0)
                                                               - kv[1].get('levelled_points', 0), kv[0]))
    for name, c in rows:
        reasons = ', '.join('%s %d' % (k[len('missing: '):], v) for k, v in sorted(c.items())
                            if k.startswith('missing: '))
        lines.append('| %s | %d | %d | %s | %d | %d |' % (_region(name), c.get('placements', 0), c.get('built', 0),
                                                           reasons or 'none', c.get('levelled_points', 0),
                                                           c.get('levelled_built', 0)))
    lines.append('| All | %d | %d | %d | %d | %d |' % (t['placements'], t['placements_built'],
                                                       t['placements'] - t['placements_built'], t['levelled_points'],
                                                       t['levelled_built']))
    return lines


def partial_reason(args):
    """Why an image step's build is not the whole game for the census (reported, never stopped), or None: a
    MiniWind, excluded content, or no actor table (the outdoor creatures are spawned from it)."""
    reasons = []
    if getattr(args, 'miniwind', False):
        reasons.append('a MiniWind of part of the world')
    if getattr(args, 'exclude', None):
        reasons.append('content excluded (%s)' % args.exclude)
    if getattr(args, 'chim_actor_table', 'off') != 'on':
        reasons.append('no actor table (--chim-actor-table off)')
    return '; '.join(reasons) or None


def stage(id1, data_files, out, library=None, partial=None, jobs=1):
    """The image step's census: writes OUT/creature-census.json and stops (ValueError) on a problem of a full build."""
    from mwad.paths import child_ci
    config = load_config()
    masters = read_masters(data_files, config)
    master = child_ci(Path(data_files), 'Morrowind.esm').read_bytes()
    report = census(masters, config, image_facts(id1, out, library, data_files, master, partial, jobs))
    for line in summary(report):
        print(line, flush=True)
    (Path(out) / CENSUS).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    problems = check(report)
    if problems:
        raise ValueError('Creature census failed (FAUNA-COVERAGE-62): %d problem(s): %s'
                         % (len(problems), '; '.join(problems[:8])))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--run', type=Path, help='a finished build run: the facts of its image (image/, actor-library/)')
    parser.add_argument('--json', type=Path, help='write the census here (private: it names record ids and cells)')
    parser.add_argument('--tables', action='store_true', help='with --run: print the public tables (counts only)')
    args = parser.parse_args(argv)
    config = load_config()
    masters = read_masters(args.data_files, config)
    image = None
    if args.run:
        image = image_facts(args.run / 'image/boot/id1', args.run / 'image', args.run / 'actor-library',
                            args.data_files, masters[0][1])
    report = census(masters, config, image)
    for line in summary(report):
        print(line, flush=True)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if args.tables and image:
        for line in public_tables(report):
            print(line, flush=True)
    problems = check(report) if image else []
    for problem in problems:
        print('[census] ' + problem, flush=True)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
