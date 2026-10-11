#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The player's view data for the image (docs/THIRD_PERSON.md): the game settings the camera and the
death scene read, and the player's body for the third-person view, one per playable race and sex.

  id1/view/settings.txt   AWVS1, then 'NAME VALUE' lines from the owned master's game settings:
                          fVanityDelay (seconds idle before the vanity orbit), sLoadLastSaveMsg (the
                          death prompt, '%s' = the save; newlines written as \\n), sYes, sNo
  id1/view/bodies.txt     AWPB1, then RACE<TAB>0|1<TAB>MODEL lines (1 = female)
  id1/progs/body/*.mdl    the bodies; *.anm beside each: the animation kit's layout (tools/npc_anim.py)

The body (a stand-in for the full player appearance): the original's new-game player record ('player' in
Morrowind.esm: a common shirt, pants and shoes) worn by the race's own skin parts, with the race and sex's
first head and hair (by record ID), baked through the same resident pipeline as the town NPCs
(npc_geometry.assemble/bake, npc_anim.plan, the 'move' profile plus block: idle, walk, run, hit, death, block from the
skeleton's own text keys; female humans take base_anim_female.nif's overrides; beast races their own
skeleton). Not yet: the character's chosen head and hair, the inventory's worn equipment, the jump group.

Build switches (tools/build.py): --player-body on|off (default on; off bakes no body: third person is then
refused in game) and --death-retry on|off (default on; off writes aw_death_retry 0 into default-game.cfg).
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

SETTINGS_FORMAT = 'AWVS1'
BODIES_FORMAT = 'AWPB1'
NUMBERS = ('fVanityDelay',)
STRINGS = ('sLoadLastSaveMsg', 'sYes', 'sNo', 'sNotifyMessage2')   # sNotifyMessage2: no rest/wait, enemies nearby
PLAYER_RECORD = 'player'
BODY_PROFILE = 'move'
# Plus the shield block (COMBAT-BLOCKING-36): base_anim 'shield: block start..stop', played while the player
# guards (hold to block, an AmiWind extension) and after a blocked blow (OpenMW refreshHitRecoilAnims).
BODY_EXTRA = (('block', 5),)
BODY_DIR = 'progs/body/'
BUDGETS = (480, 384, 320, 256)
OPTIONS = {'player_body': '--player-body', 'death_retry': '--death-retry'}
DEATH_RETRY_OFF_LINES = (b'// --death-retry off: no quick retry after a lost fight (the original choices only)\n'
                         b'aw_death_retry 0\n')


# ---------------------------------------------------------------- build switches

def add_options(parser):
    parser.add_argument('--player-body', dest='player_body', choices=('on', 'off'), default=None,
                        help="Bake the player's body (one per playable race and sex) for the third-person view, "
                             'the vanity orbit and the death scene. Default: on. off: no body; the game then stays '
                             'in first person (docs/THIRD_PERSON.md)')
    parser.add_argument('--death-retry', dest='death_retry', choices=('on', 'off'), default=None,
                        help='After a lost fight the death prompt also offers "Retry fight" (an AmiWind extension; '
                             'the original offers the last save or the main menu). Default: on. off writes '
                             'aw_death_retry 0 into the game defaults')


def configure(args):
    """{'player_body', 'death_retry', 'source'}: the switches resolved before any work (the receipt keeps it)."""
    record = {}
    given = []
    for key, option in OPTIONS.items():
        value = getattr(args, key, None)
        record[key] = (value or 'on') == 'on'
        if value:
            given.append(option + ' ' + value)
    record['source'] = ', '.join(given) or 'default'
    return record


def image_arguments(record):
    """The image step's extra arguments: nothing when both are on (the default), so a default build's image
    command does not change; --no-player-body / --no-death-retry when off."""
    if not record:
        return []
    return (['--no-player-body'] if not record.get('player_body', True) else []) + \
           (['--no-death-retry'] if not record.get('death_retry', True) else [])


def stage_death_retry(no_retry, id1):
    """--death-retry off: aw_death_retry 0 at the end of default-game.cfg. Returns the record."""
    if not no_retry:
        return {'on': True}
    path = Path(id1) / 'default-game.cfg'
    raw = path.read_bytes() if path.exists() else b''
    if raw and not raw.endswith(b'\n'):
        raw += b'\n'
    path.write_bytes(raw + DEATH_RETRY_OFF_LINES)
    return {'on': False, 'config': 'id1/default-game.cfg', 'line': 'aw_death_retry 0'}


# ---------------------------------------------------------------- game settings

def _gmst(kinds, name):
    from mwad.npc import first
    fields = kinds['GMST'].get(name.casefold())
    if not fields:
        raise ValueError('Game setting missing from the master: ' + name)
    for tag in ('FLTV', 'INTV', 'STRV'):
        raw = first(fields, tag, None)
        if raw is None:
            continue
        if tag == 'FLTV':
            return struct.unpack('<f', raw)[0]
        if tag == 'INTV':
            return struct.unpack('<i', raw)[0]
        return raw.rstrip(b'\0').decode('cp1252')
    raise ValueError('Game setting without a value: ' + name)


def settings_text(kinds):
    """view/settings.txt from the master's game settings (never hard-coded values)."""
    lines = [SETTINGS_FORMAT]
    for name in NUMBERS:
        value = float(_gmst(kinds, name))
        if not 0 < value <= 3600:
            raise ValueError(f'{name} out of range: {value}')
        lines.append(f'{name} {value:.6g}')
    for name in STRINGS:
        value = _gmst(kinds, name)
        if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 and c != '\n' for c in value):
            raise ValueError('Unsupported text in game setting ' + name)
        if name == 'sLoadLastSaveMsg' and (value.count('%') != 1 or '%s' not in value):
            raise ValueError('sLoadLastSaveMsg must hold exactly one %s')
        value = value.replace('\n', '\\n')
        if len(value) > 150 or not value.isascii():
            raise ValueError('Game setting text too long or not ASCII: ' + name)
        lines.append(f'{name} {value}')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- bodies

def playable_races(kinds):
    from mwad.npc import first
    out = []
    for name, record in kinds['RACE'].items():
        radt = first(record, 'RADT')
        if len(radt) >= 20 and struct.unpack_from('<I', radt, len(radt) - 4)[0] & 1:
            out.append(name)
    return sorted(out)


def body_path(race, female):
    slug = race.casefold().replace(' ', '_')
    if not slug.replace('_', '').isalnum() or not slug.isascii() or len(slug) > 20:
        raise ValueError('Race ID cannot form a body model name: ' + race)
    return BODY_DIR + slug + ('_f' if female else '_m') + '.mdl'


def first_part(kinds, race, female, part):
    """The race and sex's first head (part 0) or hair (1) skin part by record ID (the original's chargen
    lists them in record order; a deterministic stand-in for the character's own choice)."""
    from mwad.npc import first, text
    found = []
    for identifier, body in kinds['BODY'].items():
        raw = first(body, 'BYDT')
        if len(raw) != 4:
            continue
        kind_part, vampire, flags, kind = raw
        if kind_part != part or vampire or kind or text(body, 'FNAM').casefold() != race:
            continue
        if bool(flags & 1) == female:
            found.append(identifier)
    return sorted(found)[0] if found else None


def body_appearance(kinds, race, female):
    """The new-game player record ('player') as the given race and sex: its clothes over the race's skin."""
    from mwad.npc import outfit
    source = kinds['NPC_'].get(PLAYER_RECORD)
    if source is None:
        raise ValueError('The master has no player record')
    head, hair = first_part(kinds, race, female, 0), first_part(kinds, race, female, 1)
    record = []
    for tag, data in source:
        if tag == 'RNAM':
            data = race.encode('cp1252') + b'\0'
        elif tag == 'FLAG':
            data = struct.pack('<I', (struct.unpack('<I', data)[0] & ~1) | (1 if female else 0))
        elif tag == 'BNAM':
            data = (head or '').encode('cp1252') + b'\0'
        elif tag == 'KNAM':
            data = (hair or '').encode('cp1252') + b'\0'
        record.append((tag, data))
    key = 'aw_player_body'
    view = dict(kinds)
    view['NPC_'] = dict(kinds['NPC_'])
    view['NPC_'][key] = record
    appearance = outfit(view, key)
    appearance.update(id='player body ' + race + (' female' if female else ' male'), head=head, hair=hair)
    return appearance


_cache = {}


def _sources(data):
    key = str(data)
    if key not in _cache:
        from mwad.audit import BSA
        from mwad.npc import load_master
        from mwad.paths import child_ci
        from npc_geometry import Assets
        kinds, _, _ = load_master(child_ci(Path(data), 'Morrowind.esm'))
        _cache[key] = (kinds, Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa'))), {})
    return _cache[key]


def bake_body(task):
    """Worker: one race/sex body. (path, model bytes, layout, report)."""
    data, palette, race, female = task
    import npc_anim
    from npc_geometry import Skeleton, assemble, bake, animated_mdl
    kinds, assets, rigs = _sources(data)
    appearance = body_appearance(kinds, race, female)
    if appearance['skeleton'] not in rigs:
        rigs[appearance['skeleton']] = Skeleton(assets, appearance['skeleton'])
    skeleton = rigs[appearance['skeleton']]
    female_rig = None
    if female and appearance['skeleton'] == 'meshes/base_anim.nif':
        if npc_anim.FEMALE_SKELETON not in rigs:
            rigs[npc_anim.FEMALE_SKELETON] = Skeleton(assets, npc_anim.FEMALE_SKELETON)
        female_rig = rigs[npc_anim.FEMALE_SKELETON]
    profile = list(npc_anim.profiles()[BODY_PROFILE]) + [list(g) for g in BODY_EXTRA]
    kit, groups = npc_anim.plan(skeleton, profile, female_rig, appearance.get('weight', 1.))
    times = npc_anim.idle_compatible_times(groups)
    shapes, materials, textures = assemble(assets, appearance, kit, times)
    # The largest vertex budget whose model keeps every group's frames within the alias byte budget
    # (npc_anim.fit), else the smallest tried with the frames fit() keeps: the body is seen up close and
    # moving, so smooth walk and run cycles outrank a few hundred vertices.
    best = None
    for budget in BUDGETS:
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget, reference_frames=8)
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == BUDGETS[-1]:
                raise ValueError(appearance['id'] + ': ' + str(error)) from error
            continue
        nv, nt, (sw, sh) = frames.shape[1], len(faces), skin.size
        fitted, index = npc_anim.fit(groups, nv, nt, sw, sh)
        best = (budget, frames, faces, uv, skin, fitted, index)
        if [g['count'] for g in fitted] == [g['count'] for g in groups]:
            break
    budget, frames, faces, uv, skin, fitted, index = best
    nv, nt = frames.shape[1], len(faces)
    names = [g['name'] + '%02d' % i for g in fitted for i in range(g['count'])]
    raw = animated_mdl(frames[index], faces, uv, skin, names=names)
    layout = npc_anim.layout(fitted)
    path = body_path(race, female)
    report = {'race': race, 'female': female, 'model': path, 'bytes': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(), 'frames': len(index), 'triangles': nt, 'vertices': nv,
              'budget': budget, 'skeleton': appearance['skeleton'], 'head': appearance.get('head'),
              'hair': appearance.get('hair'), 'parts': [p['id'] for p in appearance['parts']],
              'groups': {g['name']: g['count'] for g in fitted}, 'layout': layout}
    return path, raw, layout, report


def bodies_text(entries):
    lines = [BODIES_FORMAT]
    seen = set()
    for race, female, path in entries:
        if (race, female) in seen or '\t' in race or len(race) > 31 or len(path) > 47:
            raise ValueError('Bad body catalogue row')
        seen.add((race, female))
        lines.append(f'{race}\t{1 if female else 0}\t{path}')
    return '\n'.join(lines) + '\n'


def prepare(data_files, id1, jobs=None, bodies=True):
    from mwad.paths import resolve_data_files
    data = resolve_data_files(Path(data_files))
    id1 = Path(id1)
    kinds, _, _ = _sources(data)
    (id1 / 'view').mkdir(parents=True, exist_ok=True)
    text = settings_text(kinds)
    (id1 / 'view/settings.txt').write_text(text, encoding='ascii', newline='\n')
    report = {'settings': text.splitlines()[1:], 'settings_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'bodies': [], 'scope': 'stand-in body: the new-game player record (clothes) over the race skin, '
                                      'first head and hair of the race and sex; groups idle, walk, run, hit, death, block'}
    if not bodies:
        report['bodies_off'] = '--player-body off: no body; the game stays in first person'
        return report
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    races = playable_races(kinds)
    if not races or len(races) * 2 > 32:
        raise ValueError('Playable race count outside the body catalogue bounds')
    tasks = [(str(data), palette, race, female) for race in races for female in (False, True)]
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    (id1 / BODY_DIR).mkdir(parents=True, exist_ok=True)
    entries = []
    for path, raw, layout, row in ordered_map(bake_body, tasks, max(1, min(resolve_jobs(jobs), len(tasks)))):
        (id1 / path).write_bytes(raw)
        (id1 / (path[:-4] + '.anm')).write_text(layout + '\n', encoding='ascii', newline='\n')
        entries.append((row['race'], row['female'], path))
        report['bodies'].append(row)
    catalogue = bodies_text(entries)
    (id1 / 'view/bodies.txt').write_text(catalogue, encoding='ascii', newline='\n')
    report['catalogue_sha256'] = hashlib.sha256(catalogue.encode()).hexdigest()
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--id1', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=None)
    p.add_argument('--no-bodies', action='store_true')
    a = p.parse_args()
    print(json.dumps(prepare(a.data_files, a.id1, a.jobs, not a.no_bodies), indent=2))


if __name__ == '__main__':
    main()
