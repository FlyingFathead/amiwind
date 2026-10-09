#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Combat data from the user's own master file (docs/COMBAT.md).

Writes into the image's id1:
  combat/settings.txt  the game settings the melee rules read, and the combat sounds
  combat/actors.txt    one combat sheet per NPC record (fixed or autocalculated stats,
                       best melee weapon, armour rating, Fight/Flee)
  sound/combat/*.wav   the original hit, miss, swish and fall sounds (11025 Hz, 8-bit mono)
  arena/fighters.txt   the Vivec Arena minigame's baked fighters (config/arena_fighters.json)
  arena/f*.mdl         their models with combat frames

Independent readers of the original record layouts; the autocalculation follows the
original game's rules as the OpenMW engine documents them (apps/openmw/mwclass/npc.cpp
autoCalculateAttributes/autoCalculateSkills, mwclass/npc.cpp getArmorRating,
files/data-mw/scripts/omw/combat/local.lua). No values are embedded here: everything is
read from the master at build time.
"""
import argparse
import hashlib
import json
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from mwad.audit import BSA, records, subrecords, string
from mwad.paths import child_ci, resolve_data_files

SETTINGS = ('fFatigueBase', 'fFatigueMult', 'fCombatDistance', 'fHandToHandReach',
            'fMinHandToHandMult', 'fMaxHandToHandMult', 'fHandtoHandHealthPer',
            'fDamageStrengthBase', 'fDamageStrengthMult', 'fCombatArmorMinMult', 'fCombatKODamageMult',
            'fCombatCriticalStrikeMult', 'fKnockDownMult', 'iKnockDownOddsBase', 'iKnockDownOddsMult',
            'fFatigueAttackBase', 'fFatigueAttackMult', 'fWeaponFatigueMult',
            'fFatigueReturnBase', 'fFatigueReturnMult', 'fUnarmoredBase1', 'fUnarmoredBase2',
            'iBlockMinChance', 'iBlockMaxChance', 'fSwingBlockBase', 'fSwingBlockMult', 'fBlockStillBonus',
            'fFatigueBlockBase', 'fFatigueBlockMult', 'fWeaponFatigueBlockMult',
            'fCombatBlockLeftAngle', 'fCombatBlockRightAngle', 'fCombatDelayNPC',
            'fNPCHealthBarTime', 'fNPCHealthBarFade')
# Settings only the builder needs (armour classes, magicka).
BUILD_SETTINGS = ('iBaseArmorSkill', 'fLightMaxMod', 'fMedMaxMod', 'iHelmWeight', 'iCuirassWeight',
                  'iPauldronWeight', 'iGreavesWeight', 'iBootsWeight', 'iGauntletWeight', 'iShieldWeight',
                  'fNPCbaseMagickaMult')
SOUNDS = (('health', 'Health Damage'), ('miss', 'miss'), ('punch', 'Hand To Hand Hit'),
          ('light', 'Light Armor Hit'), ('medium', 'Medium Armor Hit'), ('heavy', 'Heavy Armor Hit'),
          ('swish', 'SwishM'), ('critical', 'critical damage'), ('fall', 'Body Fall Medium'))
# Original weapon types 0..8 are melee; skill each uses; two-handed (no shield).
WEAPON_SKILL = {0: 22, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 7, 7: 6, 8: 6}
TWO_HANDED = {2, 4, 5, 6, 8}
# Animation group suffix per weapon type for the fighters' frames.
STANCE = {None: 'handtohand', 0: 'weapononehand', 1: 'weapononehand', 3: 'weapononehand', 7: 'weapononehand',
          2: 'weapontwohand', 8: 'weapontwohand', 4: 'weapontwowide', 5: 'weapontwowide', 6: 'weapontwowide'}
MOVE_SUFFIX = {'handtohand': 'hh', 'weapononehand': '1h', 'weapontwohand': '2c', 'weapontwowide': '2w'}
# Armour type -> rating weight (Npc::getArmorRating slots; bracers sit in the gauntlet slots).
ARMOR_WEIGHT = {0: .1, 1: .3, 2: .1, 3: .1, 4: .1, 5: .1, 6: .05, 7: .05, 8: .1, 9: .05, 10: .05}
ARMOR_SLOT = {0: 'helmet', 1: 'cuirass', 2: 'lpauldron', 3: 'rpauldron', 4: 'greaves', 5: 'boots',
              6: 'lgauntlet', 7: 'rgauntlet', 8: 'shield', 9: 'lgauntlet', 10: 'rgauntlet'}
SLOT_WEIGHT = {'helmet': .1, 'cuirass': .3, 'lpauldron': .1, 'rpauldron': .1, 'greaves': .1, 'boots': .1,
               'lgauntlet': .05, 'rgauntlet': .05, 'shield': .1}
ARMOR_TYPE_GMST = {0: 'iHelmWeight', 1: 'iCuirassWeight', 2: 'iPauldronWeight', 3: 'iPauldronWeight',
                   4: 'iGreavesWeight', 5: 'iBootsWeight', 6: 'iGauntletWeight', 7: 'iGauntletWeight',
                   8: 'iShieldWeight', 9: 'iGauntletWeight', 10: 'iGauntletWeight'}
# 31 frames: the alias writer's limit is 32 (npc_geometry.animated_mdl).
FRAME_GROUPS = (('idle', 4), ('run', 6), ('attack', 8), ('hit', 3), ('knock', 4), ('death', 6))


def first(fields, tag, default=b''):
    return next((v for k, v in fields if k == tag), default)


def load(master):
    kinds = {k: {} for k in ('NPC_', 'RACE', 'CLAS', 'SKIL', 'WEAP', 'ARMO', 'LEVI', 'GMST', 'SOUN')}
    for tag, flags, raw in records(master.read_bytes()):
        if tag not in kinds:
            continue
        fields = list(subrecords(raw))
        if tag == 'SKIL':
            kinds[tag][struct.unpack('<i', first(fields, 'INDX'))[0]] = fields
            continue
        if flags & 0x20 or first(fields, 'DELE'):
            continue
        kinds[tag][string(first(fields, 'NAME')).casefold()] = fields
    return kinds


def gmst(kinds, name):
    fields = kinds['GMST'].get(name.casefold())
    if fields is None:
        raise ValueError('Missing game setting ' + name)
    if name[0] == 'f':
        return struct.unpack('<f', first(fields, 'FLTV'))[0]
    return float(struct.unpack('<i', first(fields, 'INTV'))[0])


def round_even(value):
    return float(round(value))          # Python rounds halves to even, as round_ieee_754


def autocalc(kinds, npc, level):
    """Attributes, skills and health of an NPC with autocalculated stats."""
    female = bool(struct.unpack('<I', first(npc, 'FLAG'))[0] & 1)
    race = first(kinds['RACE'][string(first(npc, 'RNAM')).casefold()], 'RADT')
    bonus = dict(struct.unpack_from('<14i', race, 0)[i:i + 2] for i in range(0, 14, 2))
    attributes = [struct.unpack_from('<2i', race, 56 + 8 * i)[female] for i in range(8)]
    cldt = first(kinds['CLAS'][string(first(npc, 'CNAM')).casefold()], 'CLDT')
    favoured = struct.unpack_from('<2i', cldt, 0)
    specialization = struct.unpack_from('<i', cldt, 8)[0]
    pairs = [struct.unpack_from('<2i', cldt, 12 + 8 * i) for i in range(5)]   # (minor, major)
    for a in favoured:
        if 0 <= a < 8:
            attributes[a] += 10
    skill_data = {i: struct.unpack_from('<2i', first(f, 'SKDT'), 0) for i, f in kinds['SKIL'].items()}
    for a in range(8):
        total = 0.
        for index, (governing, _) in skill_data.items():
            if governing != a:
                continue
            add = .2
            for minor, major in pairs:
                if minor == index:
                    add = .5
                if major == index:
                    add = 1.
            total += add
        attributes[a] = min(round_even(attributes[a] + (level - 1) * total), 100.)
    multiplier = 3 + (2 if specialization == 0 else 1 if specialization == 2 else 0) + (1 if 5 in favoured else 0)
    health = (attributes[0] + attributes[5]) // 2 + multiplier * (level - 1)
    skills = [0.] * 27
    for i, bonus_points in ((0, 10), (1, 25)):
        for pair in pairs:
            if 0 <= pair[i] < 27:
                skills[pair[i]] += bonus_points
    for index, (_, spec) in skill_data.items():
        if not 0 <= index < 27:
            continue
        major = 1. if any(index in pair for pair in pairs) else .1
        same = spec == specialization
        skills[index] = min(round_even(skills[index] + 5 + bonus.get(index, 0) + (5 if same else 0) +
                                       (level - 1) * (major + (.5 if same else 0.))), 100.)
    return [int(a) for a in attributes], [int(s) for s in skills], float(health)


def resolve(kinds, identifier, level, depth=0):
    """A leveled list as a fixed pick: the highest entry at or below the level
    (no chance roll, so every build picks the same item)."""
    key = identifier.casefold()
    if key not in kinds['LEVI'] or depth > 8:
        return key if key not in kinds['LEVI'] else None
    entries, pending = [], None
    for tag, data in kinds['LEVI'][key]:
        if tag == 'INAM':
            pending = string(data).casefold()
        elif tag == 'INTV' and pending is not None:
            lev = struct.unpack('<H', data)[0]
            if lev <= level:
                entries.append((lev, pending))
            pending = None
    if not entries:
        return None
    return resolve(kinds, max(entries)[1], level, depth + 1)


def equipment(kinds, npc, level):
    items = []
    for tag, data in npc:
        if tag == 'NPCO' and len(data) == 36 and struct.unpack_from('<i', data)[0] != 0:
            item = resolve(kinds, string(data[4:]), level)
            if item:
                items.append(item)
    weapon = None
    for item in items:
        if item in kinds['WEAP']:
            w = first(kinds['WEAP'][item], 'WPDT')
            typ = struct.unpack_from('<h', w, 8)[0]
            if typ not in WEAPON_SKILL:
                continue
            best = max(w[23], w[25], w[27])
            if weapon is None or best > weapon[0]:
                weapon = (best, item, typ, w)
    armor = {}
    for item in items:
        if item in kinds['ARMO']:
            typ = struct.unpack_from('<i', first(kinds['ARMO'][item], 'AODT'))[0]
            armor.setdefault(ARMOR_SLOT.get(typ), (item, typ))
    if weapon and weapon[2] in TWO_HANDED:
        armor.pop('shield', None)
    armor.pop(None, None)
    return weapon, armor


def armor_rating(kinds, armor, skills, settings):
    unarmored = skills[17]
    rating = 0.
    for slot, weight in SLOT_WEIGHT.items():
        if slot not in armor:
            rating += weight * (settings['fUnarmoredBase1'] * unarmored) * (settings['fUnarmoredBase2'] * unarmored)
            continue
        item, typ = armor[slot]
        _, wt, _, _, _, base = struct.unpack_from('<ifiiii', first(kinds['ARMO'][item], 'AODT'))
        limit = settings[ARMOR_TYPE_GMST[typ]]
        if wt == 0:
            value = base
        else:
            skill = skills[21] if wt <= limit * settings['fLightMaxMod'] + .0005 else \
                skills[2] if wt <= limit * settings['fMedMaxMod'] + .0005 else skills[3]
            value = base * skill / settings['iBaseArmorSkill']
        rating += weight * value
    return rating


def text(value):
    return ''.join(c if 32 <= ord(c) < 127 and c not in '\t|' else '?' for c in value)


def sheet(kinds, identifier, settings):
    npc = kinds['NPC_'][identifier]
    npdt = first(npc, 'NPDT')
    level = struct.unpack_from('<h', npdt)[0]
    if len(npdt) == 52:
        attributes = list(npdt[2:10])
        skills = list(npdt[10:37])
        health, magicka, fatigue = struct.unpack_from('<3h', npdt, 38)
        source = 'f'
    elif len(npdt) == 12:
        attributes, skills, health = autocalc(kinds, npc, level)
        fatigue = attributes[0] + attributes[2] + attributes[3] + attributes[5]
        magicka = int(attributes[1] * settings['fNPCbaseMagickaMult'])
        source = 'a'
    else:
        raise ValueError('Malformed NPC NPDT ' + identifier)
    aidt = first(npc, 'AIDT')
    fight, flee = (aidt[2], aidt[3]) if len(aidt) == 12 else (30, 30)
    weapon, armor = equipment(kinds, npc, level)
    if weapon:
        _, item, typ, w = weapon
        weight, speed, reach = struct.unpack_from('<f', w, 0)[0], struct.unpack_from('<f', w, 12)[0], \
            struct.unpack_from('<f', w, 16)[0]
        wfield = [1 + typ, WEAPON_SKILL[typ], *w[22:28], round(reach, 4), round(speed, 4), round(weight, 4)]
    else:
        item, typ = '', None
        wfield = [0, 26, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    rating = armor_rating(kinds, armor, skills, settings)
    name = text(string(first(npc, 'FNAM')))
    row = [identifier, name, level, ' '.join(map(str, attributes)), ' '.join(map(str, skills)),
           f'{health} {magicka} {fatigue}', f'{fight} {flee}', ' '.join(map(str, wfield)),
           f'{rating:.3f} {1 if "shield" in armor else 0}', source]
    return '\t'.join(map(str, row)), {'weapon': item, 'weapon_type': typ, 'armor': sorted(a for a, _ in armor.values()),
                                       'level': level, 'source': source, 'name': name}


def bucket(identifier):
    c = identifier[:1]
    return ord(c) - 97 if 'a' <= c <= 'z' else 26


def write_actors(kinds, settings, path):
    """AWCA1 count, then an index line of 27 fixed-width offsets (a..z, other)
    into the sorted rows that follow, so the engine reads only one bucket."""
    rows, skipped = [], []
    for identifier in sorted(kinds['NPC_']):
        # The console types ASCII: records with other IDs are left out (counted).
        if any(c in identifier for c in '\t\n|') or len(identifier) > 31 or not identifier.isascii():
            skipped.append(identifier)
            continue
        rows.append(sheet(kinds, identifier, settings)[0])
    text = actor_file(rows)
    path.write_text(text, encoding='ascii', newline='\n')
    return len(rows), len(text.encode('ascii')), len(skipped)


def actor_file(rows):
    """The file text for sorted rows: header, index line, rows. A letter with
    no rows points at the next letter's start (or the end), so a lookup reads
    nothing; IDs not starting with a letter are bucket 26."""
    offsets = [None] * 27
    at = 0
    for row in rows:
        b = bucket(row.split('\t', 1)[0])
        if offsets[b] is None:
            offsets[b] = at
        at += len(row.encode('ascii')) + 1
    following = at
    for b in range(25, -1, -1):
        if offsets[b] is None:
            offsets[b] = following
        following = offsets[b]
    if offsets[26] is None:
        offsets[26] = at
    body = '\n'.join(rows) + '\n' if rows else ''
    return f'AWCA1 {len(rows)}\n' + 'I' + ''.join(f' {o:08d}' for o in offsets) + '\n' + body


def convert_wav(raw, out):
    """Original PCM WAV -> 11025 Hz 8-bit mono, linear resampling (deterministic)."""
    import io
    with wave.open(io.BytesIO(raw)) as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        data = w.readframes(frames)
    if width == 1:
        samples = (np.frombuffer(data, np.uint8).astype(np.float64) - 128) / 128
    elif width == 2:
        samples = np.frombuffer(data, '<i2').astype(np.float64) / 32768
    else:
        raise ValueError('Unsupported WAV sample width')
    samples = samples.reshape(-1, channels).mean(axis=1)
    count = max(1, int(round(len(samples) * 11025 / rate)))
    resampled = np.interp(np.arange(count) * rate / 11025, np.arange(len(samples)), samples)
    pcm = np.clip(np.rint(resampled * 127 + 128), 0, 255).astype(np.uint8)
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(11025); w.writeframes(pcm.tobytes())
    return count / 11025


def frame_times(skeleton, stance):
    """Sample times per group; a missing group repeats the idle start."""
    ev = skeleton.events
    counts = dict(FRAME_GROUPS)
    idle_times, idle_step = skeleton.idle_times(counts['idle'])
    suffix = MOVE_SUFFIX[stance]

    def span(start, stop, count, fallback):
        if start in ev and stop in ev and ev[stop] > ev[start]:
            a, b = ev[start], ev[stop]
            return list(np.linspace(a, b, count, endpoint=False)), (b - a) / count, a, b
        return [fallback] * count, 0.1, None, None
    groups = {'idle': (list(idle_times), idle_step, None, None)}
    run = span(f'runforward{suffix}: loop start', f'runforward{suffix}: loop stop', counts['run'], idle_times[0])
    if run[2] is None:
        run = span('runforward: loop start', 'runforward: loop stop', counts['run'], idle_times[0])
    groups['run'] = run
    groups['attack'] = span(f'{stance}: chop start', f'{stance}: chop large follow stop', counts['attack'], idle_times[0])
    groups['hit'] = span('hit1: start', 'hit1: stop', counts['hit'], idle_times[0])
    groups['knock'] = span('knockdown: start', 'knockdown: stop', counts['knock'], idle_times[0])
    death = span('death1: start', 'death1: stop', counts['death'] - 1, idle_times[0])
    groups['death'] = (death[0] + [ev.get('death1: stop', idle_times[0])], death[1], death[2], death[3])
    hit_key = ev.get(f'{stance}: chop hit')
    a, b = groups['attack'][2], groups['attack'][3]
    hit_fraction = (hit_key - a) / (b - a) if hit_key is not None and a is not None else .5
    return groups, hit_fraction


def bake_fighter(task):
    data, palette, identifier, stance = task
    from mwad.npc import load_master, outfit
    from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl
    kinds, _, _ = _master(data)
    appearance = outfit(kinds, identifier)
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    skeleton = Skeleton(assets, appearance['skeleton'])
    groups, hit_fraction = frame_times(skeleton, stance)
    times = [t for name, _ in FRAME_GROUPS for t in groups[name][0]]
    shapes, materials, textures = assemble(assets, appearance, skeleton, np.array(times))
    for budget in (480, 384, 320, 256, 192):
        try:
            frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget=budget, reference_frames=8)
            break
        except ValueError as error:
            if str(error) != 'Alias vertex budget exceeded' or budget == 192:
                raise ValueError(identifier + ': ' + str(error)) from error
    raw = animated_mdl(frames, faces, uv, skin)
    layout, at = [], 0
    for name, count in FRAME_GROUPS:
        step = groups[name][1]
        layout.append(f'{name}:{at}:{count}:{step:.4f}' + (f':{hit_fraction:.3f}' if name == 'attack' else ''))
        at += count
    return identifier, raw, {'name': appearance['name'], 'layout': ' '.join(layout), 'frames': len(frames),
                             'vertices': int(frames.shape[1]), 'triangles': len(faces), 'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest()}


_masters = {}


def _master(data):
    key = str(Path(data).resolve())
    if key not in _masters:
        from mwad.npc import load_master
        _masters[key] = load_master(child_ci(data, 'Morrowind.esm'))
    return _masters[key]


def prepare(data_files, id1, jobs=None, fighters=None):
    data = resolve_data_files(Path(data_files))
    id1 = Path(id1)
    kinds = load(child_ci(data, 'Morrowind.esm'))
    settings = {name: gmst(kinds, name) for name in SETTINGS + BUILD_SETTINGS}
    (id1 / 'combat').mkdir(parents=True, exist_ok=True)
    (id1 / 'sound/combat').mkdir(parents=True, exist_ok=True)
    from npc_geometry import Assets
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    lines = ['AWCS1']
    lines += [f'{name} {settings[name]:.6g}' for name in SETTINGS]
    sounds = {}
    for key, record in SOUNDS:
        fields = kinds['SOUN'].get(record.casefold())
        if not fields:
            continue
        source = 'sound/' + string(first(fields, 'FNAM')).replace('\\', '/').casefold()
        raw = assets.read(source)
        seconds = convert_wav(raw, id1 / 'sound/combat' / f'{key}.wav')
        lines.append(f'sound {key} combat/{key}.wav')
        sounds[key] = {'record': record, 'source': source, 'seconds': round(seconds, 3)}
    (id1 / 'combat/settings.txt').write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')
    count, size, skipped = write_actors(kinds, settings, id1 / 'combat/actors.txt')
    report = {'settings': {k: settings[k] for k in SETTINGS}, 'sounds': sounds,
              'actors': {'count': count, 'bytes': size, 'skipped_non_ascii_or_long_ids': skipped}}
    config = json.loads((ROOT / 'config/arena_fighters.json').read_text(encoding='utf-8'))
    chosen = fighters if fighters is not None else [row['id'] for row in config['fighters']]
    if chosen:
        from build_jobs import resolve_jobs
        from build_parallel import ordered_map
        palette = (id1 / 'gfx/palette.lmp').read_bytes()
        tasks = []
        for identifier in chosen:
            key = identifier.casefold()
            if key not in kinds['NPC_']:
                raise ValueError('Arena fighter is not an NPC record: ' + identifier)
            weapon, _ = equipment(kinds, kinds['NPC_'][key], struct.unpack_from('<h', first(kinds['NPC_'][key], 'NPDT'))[0])
            tasks.append((data, palette, key, STANCE[weapon[2] if weapon else None]))
        (id1 / 'arena').mkdir(parents=True, exist_ok=True)
        rows, baked = [f'AWAF1 {len(tasks)}'], {}
        for identifier, raw, record in ordered_map(bake_fighter, tasks, min(resolve_jobs(jobs), len(tasks))):
            stem = 'f' + hashlib.sha256(identifier.encode()).hexdigest()[:12]
            (id1 / 'arena' / f'{stem}.mdl').write_bytes(raw)
            rows.append('\t'.join((identifier, f'arena/{stem}.mdl', text(record['name']), record['layout'])))
            baked[identifier] = {**record, 'model': f'arena/{stem}.mdl'}
            print('Arena fighter ready:', identifier, record['bytes'], 'bytes', file=sys.stderr, flush=True)
        (id1 / 'arena/fighters.txt').write_text('\n'.join(rows) + '\n', encoding='ascii', newline='\n')
        report['fighters'] = baked
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--id1', type=Path, required=True, help='image id1 folder (needs gfx/palette.lmp for fighters)')
    p.add_argument('--fighter', action='append', help='bake only these NPC records (default: config/arena_fighters.json)')
    p.add_argument('--no-fighters', action='store_true', help='combat sheets and sounds only')
    p.add_argument('--jobs', type=int)
    a = p.parse_args()
    print(json.dumps(prepare(a.data_files, a.id1, a.jobs, [] if a.no_fighters else a.fighter), indent=2))
