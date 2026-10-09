#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Reference closure of an area build: the content the built cells reference.

--exclude-unreferenced [GROUP,...] (tools/build_exclusions.py) builds only what
the selected area references. This module computes that set from the owner's
masters (Morrowind.esm, Tribunal.esm, Bloodmoon.esm, in that order; a later
master's record replaces an earlier one):

  built cells -> their placements (by reference ID)
    -> base records (NPC, creature, static, light, door, container, item, ...)
    -> leveled lists, recursively
    -> NPCs: race, class, faction, head and hair, the race's body parts for
       their sex, inventory and the body parts of their clothing and armour
    -> scripts on any included record, and every object those scripts name
    -> models (MODL) and sounds (lights, doors, creature sound sets, region sounds)

plus a script scan: a script that names a built cell (PositionCell, PlaceItemCell,
AiTravel ...) may bring actors or items there, so every object it names is kept
("kept because a script may need it"). Anything unresolved is KEPT and listed in
the receipt, never silently dropped.

Voice (Harry, 2026-10-09: "everything in their dialogue pool is ok"): the voice
group keeps EVERY recorded line an included NPC could say: each dialogue line
(greetings, topics, voice idles/hellos/combat, persuasion) whose static speaker
conditions (speaker ID, race, class, faction, sex, cell) at least one included
NPC or creature satisfies. Function and variable conditions cannot be decided
before the game runs, so they never drop a line. Lines a script plays with Say
are kept. Only lines no included actor can ever say are left out.

Music is never part of a closure (owner rule): --exclude-unreferenced never
trims it; --exclude music is the separate, explicit opt-out.

Groups (one table, GROUPS): npcs (NPC/creature records, so the NPC gallery
holds exactly the included ones), voice, sounds (effects only the left-out
records name), models and textures. models and textures are recorded in the
receipt: the scene stages of an area build already convert only what the area
places, so no stage drops them yet.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad.audit import records, subrecords  # noqa: E402

FORMAT = 'AWCLOSURE1'
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
GROUPS = {
    'npcs': 'NPC and creature records the area does not place or script (the NPC gallery holds exactly the included ones)',
    'voice': 'recorded dialogue lines no included NPC or creature can ever say',
    'sounds': 'sound effects that only left-out records name',
    'models': 'models no included record uses (receipt only: the scene stages convert only what the area places)',
    'textures': 'textures of left-out models (receipt only, like models)',
}
NEVER = {'music': 'music is always kept (owner rule); --exclude music is the separate explicit opt-out'}
# Records with an ID and an optional model and script.
OBJECT_TAGS = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BODY', 'BOOK', 'CLOT', 'CONT', 'CREA', 'DOOR', 'INGR', 'LEVC',
               'LEVI', 'LIGH', 'LOCK', 'MISC', 'NPC_', 'PROB', 'REPA', 'STAT', 'WEAP')
SAY = re.compile(r'\bsay\s*,?\s*"([^"]+)"', re.I)
TOKEN = re.compile(r'"([^"\r\n]{1,64})"|([A-Za-z0-9_][A-Za-z0-9_\'.-]{0,63})')


def parse_groups(value):
    """'voice,npcs' -> ['npcs', 'voice'] (table order); None or 'all' -> every group."""
    if value in (None, '', 'all', True):
        return list(GROUPS)
    names = [part.strip().casefold() for part in str(value).split(',') if part.strip()]
    for name in names:
        if name in NEVER:
            raise ValueError(f'--exclude-unreferenced {name} is refused: {NEVER[name]}')
        if name not in GROUPS and name != 'all':
            raise ValueError(f'--exclude-unreferenced: unknown group "{name}"; groups: ' + ', '.join(GROUPS))
    if 'all' in names:
        return list(GROUPS)
    return [name for name in GROUPS if name in names]


def string(data):
    """A record string: up to the first NUL (fixed-width fields carry bytes after it)."""
    return data.split(b'\0', 1)[0].decode('cp1252', 'replace')


def norm_path(value):
    return value.replace('\\', '/').strip().casefold()


def fields_of(raw):
    return list(subrecords(raw))


def first(fields, tag):
    return next((data for name, data in fields if name == tag), None)


def text(fields, tag):
    data = first(fields, tag)
    return string(data).strip() if data is not None else ''


class Master:
    """The records of the masters that a closure needs."""

    def __init__(self):
        self.objects = {}      # id -> {'tag', 'model', 'script', ...}
        self.sounds = {}       # SOUN id -> file (relative to Sound/)
        self.sound_gens = []   # (creature id, sound id)
        self.regions = {}      # region id -> [sound ids]
        self.scripts = {}      # script id -> text
        self.cells = {}        # key -> {'name', 'interior', 'x', 'y', 'region', 'refs': [ids]}
        self.infos = []        # dialogue lines with a sound
        self.masters = []

    @classmethod
    def load(cls, data_files):
        master = cls()
        data_files = Path(data_files)
        for name in MASTERS:
            path = next((p for p in data_files.iterdir() if p.name.casefold() == name.casefold()), None)
            if path is None:
                continue
            master.masters.append(name)
            master.read(path.read_bytes())
        return master

    def read(self, raw_master):
        topic, topic_type = '', 0
        for tag, flags, raw in records(raw_master):
            if tag in OBJECT_TAGS:
                self.read_object(tag, flags, fields_of(raw))
            elif tag == 'SOUN':
                f = fields_of(raw)
                self.sounds[text(f, 'NAME').casefold()] = norm_path(text(f, 'FNAM'))
            elif tag == 'SNDG':
                f = fields_of(raw)
                self.sound_gens.append((text(f, 'CNAM').casefold(), text(f, 'SNAM').casefold()))
            elif tag == 'REGN':
                f = fields_of(raw)
                self.regions[text(f, 'NAME').casefold()] = [string(data[:32]).casefold() for name, data in f if name == 'SNAM']
            elif tag == 'SCPT':
                f = fields_of(raw)
                header = first(f, 'SCHD') or b''
                self.scripts[string(header[:32]).casefold()] = (first(f, 'SCTX') or b'').decode('cp1252', 'replace')
            elif tag == 'CELL':
                self.read_cell(fields_of(raw))
            elif tag == 'DIAL':
                f = fields_of(raw)
                topic = text(f, 'NAME')
                data = first(f, 'DATA') or b'\0'
                topic_type = data[0]
            elif tag == 'INFO':
                f = fields_of(raw)
                sound = text(f, 'SNAM')
                result = text(f, 'BNAM')
                if not sound and not result:
                    continue
                data = first(f, 'DATA') or b''
                sex = struct.unpack_from('<b', data, 9)[0] if len(data) >= 12 else -1
                self.infos.append({
                    'topic': topic, 'type': topic_type, 'id': text(f, 'INAM'), 'sound': norm_path(sound),
                    'speaker': text(f, 'ONAM').casefold(), 'race': text(f, 'RNAM').casefold(),
                    'class': text(f, 'CNAM').casefold(), 'faction': text(f, 'FNAM').casefold(),
                    'cell': text(f, 'ANAM').casefold(), 'sex': sex, 'result': result,
                    'deleted': bool(flags & 0x20)})

    def read_object(self, tag, flags, f):
        identifier = text(f, 'NAME').casefold()
        if not identifier:
            return
        if flags & 0x20 or first(f, 'DELE') is not None:
            self.objects.pop(identifier, None)
            return
        row = {'tag': tag, 'model': norm_path(text(f, 'MODL')), 'script': text(f, 'SCRI').casefold(), 'refs': []}
        if tag == 'NPC_':
            flag = first(f, 'FLAG')
            row.update(race=text(f, 'RNAM').casefold(), class_=text(f, 'CNAM').casefold(),
                       faction=text(f, 'ANAM').casefold(), female=bool(flag and struct.unpack('<i', flag[:4])[0] & 1),
                       refs=[text(f, 'BNAM').casefold(), text(f, 'KNAM').casefold()])
        if tag == 'CREA':
            row['refs'].append(text(f, 'CNAM').casefold())  # the creature whose sound set it uses
        if tag in ('NPC_', 'CREA', 'CONT'):
            row['refs'] += [string(data[4:36]).casefold() for name, data in f if name == 'NPCO' and len(data) >= 36]
        if tag in ('ARMO', 'CLOT'):
            row['refs'] += [string(data).casefold() for name, data in f if name in ('BNAM', 'CNAM')]
        if tag == 'LEVC':
            row['refs'] += [string(data).casefold() for name, data in f if name == 'CNAM']
        if tag == 'LEVI':
            row['refs'] += [string(data).casefold() for name, data in f if name == 'INAM']
        if tag == 'LIGH':
            row['sounds'] = [text(f, 'SNAM').casefold()]
        if tag == 'DOOR':
            row['sounds'] = [text(f, 'SNAM').casefold(), text(f, 'ANAM').casefold()]
        if tag == 'BODY':
            data = first(f, 'BYDT') or b'\0\0\0\0'
            row.update(race=text(f, 'FNAM').casefold(), part_type=data[3], female=bool(data[2] & 1))
        row['refs'] = [r for r in row['refs'] if r]
        row['sounds'] = [s for s in row.get('sounds', ()) if s]
        self.objects[identifier] = row

    def read_cell(self, f):
        header = first(f, 'DATA') or b''
        if len(header) < 12:
            return
        flags, x, y = struct.unpack_from('<Iii', header)
        interior = bool(flags & 1)
        name = text(f, 'NAME')
        key = ('interior', name.casefold()) if interior else ('exterior', x, y)
        cell = self.cells.setdefault(key, {'name': name, 'interior': interior, 'x': x, 'y': y,
                                           'region': text(f, 'RGNN').casefold(), 'refs': []})
        cell['name'] = name or cell['name']
        # Header subrecords come first; each placement starts at FRMR, and its NAME is
        # the base record's ID. A later master's cell adds its placements (moved and
        # deleted references are not resolved by ID: a deleted one is dropped).
        current, deleted, in_refs = None, False, False
        for tag, data in f:
            if tag == 'FRMR':
                if current and not deleted:
                    cell['refs'].append(current)
                current, deleted, in_refs = None, False, True
            elif in_refs and tag == 'NAME' and current is None:
                current = string(data).casefold()
            elif in_refs and tag == 'DELE':
                deleted = True
        if current and not deleted:
            cell['refs'].append(current)


def cell_key(spec):
    """'interior:Vivec, Arena Pit' / 'cell:-3,-2' / ('exterior', x, y) -> a Master.cells key."""
    if isinstance(spec, tuple):
        return spec
    kind, _, value = str(spec).partition(':')
    if kind == 'interior':
        return ('interior', value.strip().casefold())
    if kind == 'cell':
        x, y = (int(v) for v in value.split(','))
        return ('exterior', x, y)
    raise ValueError('Cell spec must be interior:<cell id> or cell:X,Y: ' + str(spec))


def area_cells(area, root=ROOT):
    """The cells a town area builds: its exterior grid (source_cell +- source_radius in
    the town config) and every interior the scene tables give that area."""
    towns = json.loads((Path(root) / 'config/towns.json').read_text(encoding='utf-8'))['towns']
    town = next((t for t in towns if t['id'] == area), None)
    if town is None:
        raise ValueError('Unknown area: ' + area)
    config = json.loads((Path(root) / 'config' / town['config']).read_text(encoding='utf-8'))
    cells = []
    if 'source_cell' in config:
        cx, cy = config['source_cell']
        radius = config.get('source_radius', 0)
        cells += [f'cell:{x},{y}' for x in range(cx - radius, cx + radius + 1) for y in range(cy - radius, cy + radius + 1)]
    scenes = list(config.get('scenes', ()))
    for name in ('balmora_interiors.json', 'seyda_area.json'):
        path = Path(root) / 'config' / name
        if path.is_file():
            scenes += json.loads(path.read_text(encoding='utf-8')).get('scenes', [])
    for scene in scenes:
        if scene.get('interior') is True and scene.get('area', 'seyda') == area and scene.get('cell'):
            cells.append('interior:' + scene['cell'])
        if scene.get('interior') is False and scene.get('area', 'seyda') == area and 'grid' in scene:
            cells.append('cell:%d,%d' % tuple(scene['grid']))
    return list(dict.fromkeys(cells))


def tokens(script_text):
    for quoted, bare in TOKEN.findall(script_text):
        yield (quoted or bare).casefold()


def closure(master, cells, groups=None):
    """The reference closure of `cells` (specs or keys) as a JSON-ready dict."""
    groups = parse_groups(groups) if not isinstance(groups, list) else groups
    keys = [cell_key(c) for c in cells]
    missing = [c for c, k in zip(cells, keys) if k not in master.cells]
    if missing:
        raise ValueError('Unknown cell(s) in the masters: ' + ', '.join(map(str, missing)))
    built = [master.cells[k] for k in keys]
    cell_names = sorted({c['name'].casefold() for c in built if c['name']})
    included, kept_by_script, unresolved = set(), {}, []
    scripts_done = set()
    pending = [ref for cell in built for ref in cell['refs']]

    def add(identifier, why=None):
        if identifier and identifier not in included:
            if identifier not in master.objects:
                if identifier not in {u['id'] for u in unresolved}:
                    unresolved.append({'id': identifier, 'why': why or 'placed or named but no record found; kept'})
                return
            pending.append(identifier)
            if why:
                kept_by_script.setdefault(identifier, why)

    def scan_script(name, why):
        name = (name or '').casefold()
        if not name or name in scripts_done:
            return
        scripts_done.add(name)
        source = master.scripts.get(name)
        if source is None:
            unresolved.append({'id': name, 'why': 'script named but not found; kept'})
            return
        for token in tokens(source):
            if token in master.objects:
                add(token, why)
            elif token in master.scripts and token != name:
                scan_script(token, why)  # StartScript / script chains

    # Scripts that name a built cell may place, move or spawn actors and items there.
    for name, source in master.scripts.items():
        words = set(tokens(source))
        if any(cell in words for cell in cell_names):
            scan_script(name, f'script {name} names a built cell')
    # The race's body parts per sex, for the NPCs that need them.
    bodies = {}
    for body, part in master.objects.items():
        if part['tag'] == 'BODY' and part.get('part_type') == 0:
            bodies.setdefault((part.get('race'), part.get('female')), []).append(body)

    def close():
        while pending:
            identifier = pending.pop()
            if identifier in included:
                continue
            if identifier not in master.objects:
                add(identifier)  # recorded as unresolved, kept
                continue
            included.add(identifier)
            row = master.objects[identifier]
            for ref in row['refs']:
                add(ref)
            if row['script']:
                scan_script(row['script'], f'script {row["script"]} of {identifier}')
            if row['tag'] == 'NPC_':
                for body in bodies.get((row.get('race'), row.get('female')), ()):
                    add(body)

    # Voice: every line an included actor could say (static conditions only; a
    # function or variable condition never drops a line).
    def can_say(info, actors):
        if info['speaker']:
            return info['speaker'] in included
        if info['cell'] and not any(name.startswith(info['cell']) for name in cell_names):
            return False
        for actor in actors:
            if info['race'] and info['race'] != actor.get('race'):
                continue
            if info['class'] and info['class'] != actor.get('class_'):
                continue
            if info['faction'] and info['faction'] != (actor.get('faction') or 'ffff'):
                continue
            if info['sex'] in (0, 1) and bool(info['sex']) != actor.get('female'):
                continue
            return True
        return False

    # Dialogue results of sayable lines can add objects (AddItem, PlaceAtPC ...),
    # which can add actors with lines of their own: repeat until nothing changes.
    while True:
        close()
        before = len(included)
        actors = [master.objects[i] for i in sorted(included) if master.objects[i]['tag'] == 'NPC_']
        voice_files, kept_lines, dropped_lines = set(), 0, 0
        for info in master.infos:
            if info['deleted']:
                continue
            sayable = can_say(info, actors)
            if sayable and info['result']:
                for token in tokens(info['result']):
                    if token in master.objects:
                        add(token, f'dialogue result of {info["id"]} ({info["topic"]})')
            if not info['sound']:
                continue
            if sayable:
                voice_files.add(info['sound'])
                kept_lines += 1
            else:
                dropped_lines += 1
        close()
        if len(included) == before:
            break
    # Lines a script plays with Say: kept (which script runs is decided in game).
    said_by_scripts = sorted({norm_path(m) for source in master.scripts.values() for m in SAY.findall(source)})
    voice_files |= set(said_by_scripts)
    npcs = sorted(i for i in included if master.objects[i]['tag'] == 'NPC_')
    creatures = sorted(i for i in included if master.objects[i]['tag'] == 'CREA')

    # Sounds: a sound only left-out records name is dropped; one nothing names stays.
    referrers = {}
    for identifier, row in master.objects.items():
        for sound in row.get('sounds', ()):
            referrers.setdefault(sound, set()).add(identifier)
    for creature, sound in master.sound_gens:
        referrers.setdefault(sound, set()).add(creature)
    regions = {c['region'] for c in built if c['region']}
    for region, sounds in master.regions.items():
        for sound in sounds:
            referrers.setdefault(sound, set()).add('region:' + region)
    # A sound any script names stays: which scripts run is decided in game.
    script_sounds = set()
    for source in master.scripts.values():
        script_sounds |= set(tokens(source))

    def used(user):
        return user[len('region:'):] in regions if user.startswith('region:') else user in included
    dropped_ids = {s for s, users in referrers.items()
                   if s in master.sounds and users and s not in script_sounds and not any(used(u) for u in users)}
    kept_files = {path for s, path in master.sounds.items() if s not in dropped_ids}
    dropped_sounds = sorted({master.sounds[s] for s in dropped_ids} - kept_files - {''})
    dropped_sounds = [path for path in dropped_sounds if not path.startswith('vo/')]

    models = sorted({master.objects[i]['model'] for i in included if master.objects[i]['model']})
    body_parts = sorted(i for i in included if master.objects[i]['tag'] == 'BODY')
    return {
        'format': FORMAT, 'groups': groups, 'masters': master.masters,
        'cells': [c['name'] or f"{c['x']},{c['y']}" for c in built], 'cell_keys': [list(k) for k in keys],
        'counts': {'records': len(included), 'npcs': len(npcs), 'creatures': len(creatures),
                   'body_parts': len(body_parts), 'models': len(models), 'voice_files': len(voice_files),
                   'voice_lines_kept': kept_lines, 'voice_lines_dropped': dropped_lines,
                   'sound_files_dropped': len(dropped_sounds), 'kept_by_script': len(kept_by_script),
                   'unresolved_kept': len(unresolved)},
        'npcs': npcs, 'creatures': creatures, 'body_parts': body_parts, 'models': models,
        'voice_files': sorted(voice_files), 'voice_files_said_by_scripts': said_by_scripts,
        'sound_files_dropped': dropped_sounds,
        'kept_by_script': dict(sorted(kept_by_script.items())), 'unresolved_kept': unresolved,
        'music': 'always kept (owner rule)',
        # Shared engine assets maps and the engine find by name or metadata (the shared sky,
        # palette, fonts, menus: build_exclusions.ALWAYS_INCLUDED) are never part of a closure:
        # nothing here filters them, and the image step checks them.
        'always_included': 'shared engine assets: never filtered; checked by the image step',
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='closure JSON')
    p.add_argument('--area', help='a town from config/towns.json (its exterior grid and interiors)')
    p.add_argument('--cell', action='append', default=[], help='interior:<cell id> or cell:X,Y (repeatable)')
    p.add_argument('--groups', default='all', help='comma list of ' + ', '.join(GROUPS) + ' (default all)')
    a = p.parse_args(argv)
    from mwad.paths import resolve_data_files
    cells = (area_cells(a.area) if a.area else []) + a.cell
    if not cells:
        p.error('give --area or --cell')
    record = closure(Master.load(resolve_data_files(a.data_files)), cells, parse_groups(a.groups))
    a.out.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(record['counts']), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
