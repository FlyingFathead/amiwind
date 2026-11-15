#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The combat style audit (NPC-CREATURE-COMBAT-STYLE-STATS-66, docs/ACTOR_RECORDS.md "Combat styles"): one world-wide
table, per NPC and creature record of the three masters, of the weapon it carries, the style of combat the original's
rules give it at the opening of a fight (melee, bow, crossbow, thrown, hand to hand, its own creature attacks; and
whether it has spells to cast), against the weapon the builder hands the engine's fight sheet (tools/prepare_combat.py
equipment, the same choice the actor table holds). A mismatch is a count, never an impression.

The reference rule is written here on its own, from OpenMW 0.51 for the rules only (nothing of its code is used):
mwmechanics/weaponpriority.cpp rateWeapon and rateAmmo, mwmechanics/combat.cpp getHitChance (the attacker's side; the
enemy's evasion is not known before the fight and is left out), mwclass/creature.cpp getSkill (a creature's skill is
its Combat, Magic or Stealth value by the skill's specialization) and the "weapon and shield" flag (a creature without
it fights only with its own attacks). Every fight starts with the enemy out of reach, so a ranged weapon is rated with
fAIRangeMeleeWeaponMult and a melee one with fAIMeleeWeaponMult. A levelled inventory entry is resolved as the builder
resolves it (prepare_combat.resolve: the highest entry at or below the level; the roll per actor is
ACTOR-LEVELLED-INVENTORY-ONE-PICK-66), so this table measures the choice of style alone.

Run in the shell container (nothing of the game is in the repo; outputs are private, the counts may go public):
  python3 tools/combat_style_audit.py --data-files DIR --out DIR [--public docs/combat-style-audit.json]
                                      [--ours-module PATH]  (another prepare_combat.py, e.g. an older commit's)
"""
import argparse
import importlib.util
import json
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
TAGS = ('NPC_', 'CREA', 'WEAP', 'LEVI', 'RACE', 'CLAS', 'GMST', 'SPEL', 'SKIL', 'ARMO')
# WPDT weapon type -> the skill it uses (the original's skill index) and its class
SKILL = {0: 22, 1: 5, 2: 5, 3: 4, 4: 4, 5: 4, 6: 7, 7: 6, 8: 6, 9: 23, 10: 23, 11: 23, 12: 23, 13: 23}
MELEE = set(range(9))
STYLE_OF = {9: 'bow', 10: 'crossbow', 11: 'thrown'}
AMMO_FOR = {9: 12, 10: 13}
STYLES = ('melee', 'bow', 'crossbow', 'thrown', 'hand to hand', 'creature attack', 'none')


def text(d):
    return d.split(b'\0', 1)[0].decode('cp1252', 'replace')


def first(fields, tag, default=b''):
    for t, d in fields:
        if t == tag:
            return d
    return default


def phase(n, total, what):
    print('=== PHASE %d/%d: %s ===' % (n, total, what), flush=True)


def read_masters(data_files):
    """({tag: {key: fields}}, Counter of placed references by folded id), the last record of an id winning; SKIL is
    keyed by its index, as the builder keys it."""
    from mwad.esm import records, subrecords
    from mwad.paths import child_ci, resolve_data_files
    try:
        data = resolve_data_files(Path(data_files))
    except ValueError:
        data = Path(data_files)
    out = {t: {} for t in TAGS}
    refs = Counter()
    for name in MASTERS:
        path = child_ci(data, name, required=False)
        if path is None:
            continue
        for tag, flags, payload in records(path.read_bytes()):
            if tag == 'CELL':
                in_ref = False
                for key, value in subrecords(payload):
                    if key == 'FRMR':
                        in_ref = True
                    elif key == 'NAME' and in_ref:
                        refs[text(value).casefold()] += 1
                        in_ref = False
                continue
            if tag not in out:
                continue
            parts = list(subrecords(payload))
            if tag == 'SKIL':
                out[tag][struct.unpack('<i', first(parts, 'INDX'))[0]] = parts
                continue
            ident = text(first(parts, 'NAME')).casefold()
            if not ident:
                continue
            if flags & 0x20 or any(t == 'DELE' for t, _ in parts):
                out[tag].pop(ident, None)
            else:
                out[tag][ident] = parts
    return out, refs


def setting(records, name, default):
    g = records['GMST'].get(name.casefold())
    if not g:
        return default
    v = first(g, 'FLTV')
    return struct.unpack('<f', v)[0] if len(v) == 4 else default


# ------------------------------------------------------------------ the reference rule

def stats_of(tag, fields, records, pc):
    """(skills, agility, luck, creature combat or None), or None."""
    npdt = first(fields, 'NPDT')
    if tag == 'CREA':
        if len(npdt) != 96:
            return None
        v = struct.unpack('<24i', npdt)
        by_spec = (v[14], v[15], v[16])
        skills = []
        for i in range(27):
            sk = first(records['SKIL'].get(i, []), 'SKDT')
            spec = struct.unpack_from('<i', sk, 4)[0] if len(sk) >= 8 else 0
            skills.append(by_spec[spec] if 0 <= spec <= 2 else v[14])
        return skills, v[5], v[9], v[14]
    if len(npdt) == 52:
        return list(npdt[10:37]), npdt[5], npdt[9], None
    if len(npdt) == 12:
        level = struct.unpack_from('<h', npdt)[0]
        try:
            attributes, skills, _ = pc.autocalc(records, fields, level)
        except (KeyError, IndexError, struct.error, ValueError):
            return None
        return skills, attributes[3], attributes[7], None
    return None


def rate(records, wpdt, stats, ammo=0.):
    """rateWeapon at the opening of a fight (the enemy out of reach), the enemy's side left out."""
    typ = struct.unpack_from('<h', wpdt, 8)[0]
    speed = struct.unpack_from('<f', wpdt, 12)[0]
    lo_hi = [(wpdt[22 + 2 * k], wpdt[23 + 2 * k]) for k in range(3)]       # chop, slash, thrust
    chop, slash, thrust = ((a + b) / 2. for a, b in lo_hi)
    melee = typ in MELEE
    mult = setting(records, 'fAIMeleeWeaponMult', 2.) if melee else setting(records, 'fAIRangeMeleeWeaponMult', 5.)
    if melee:
        total = slash + thrust + chop
        r = (slash ** 2 + thrust ** 2 + chop ** 2) / total if total else 0.
    elif typ == 11:
        r = 2 * chop
    else:
        r = chop
        if typ in AMMO_FOR:
            if ammo <= 0:
                return 0.
            r += ammo
    skills, agility, luck, combat = stats if stats else ([50] * 27, 0, 0, None)
    value = skills[SKILL[typ]]
    if value <= 0:
        return 0.
    hit = round(((value if combat is None else combat) + agility / 5. + luck / 10.) * setting(records, 'fFatigueBase', 1.25))
    r *= min(1., max(.01, hit / 100.))
    if typ not in (12, 13):
        r *= speed
    return r * mult


def reference(tag, fields, records, pc, items):
    """(style, weapon item or None) the original's rules give the fighter at the opening of a fight."""
    flag = struct.unpack('<I', first(fields, 'FLAG', b'\0\0\0\0')[:4].ljust(4, b'\0'))[0]
    if tag == 'CREA' and not flag & 4:
        return 'creature attack', None
    stats = stats_of(tag, fields, records, pc)
    weapons = []
    for item in items:
        w = first(records['WEAP'].get(item, []), 'WPDT')
        if len(w) >= 32:
            weapons.append((item, w, struct.unpack_from('<h', w, 8)[0]))
    ammo = {}
    for item, w, typ in weapons:
        if typ in (12, 13):
            ammo[typ] = max(ammo.get(typ, 0.), rate(records, w, stats))
    best, best_r = None, 0.
    for item, w, typ in weapons:
        if typ in (12, 13):
            continue
        r = rate(records, w, stats, ammo.get(AMMO_FOR.get(typ), 0.))
        if r > best_r:
            best, best_r = (item, typ), r
    if best is None:
        return ('creature attack' if tag == 'CREA' else 'hand to hand'), None
    return (STYLE_OF.get(best[1], 'melee')), best[0]


# ------------------------------------------------------------------ the table

def load_pc(path):
    if path is None:
        import prepare_combat
        return prepare_combat
    spec = importlib.util.spec_from_file_location('prepare_combat_ours', str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def carried(fields, records, pc, level):
    items = []
    for t, d in fields:
        if t == 'NPCO' and len(d) == 36 and struct.unpack_from('<i', d)[0] != 0:
            item = pc.resolve(records, text(d[4:]), level)
            if item:
                items.append(item)
    return items


def castable(fields, records):
    n = 0
    for t, d in fields:
        if t == 'NPCS':
            s = first(records['SPEL'].get(text(d).casefold(), []), 'SPDT')
            if len(s) >= 4 and struct.unpack_from('<i', s)[0] == 0:
                n += 1
    return n


def audit(records, refs, ref_pc, ours_pc):
    rows = []
    for tag in ('NPC_', 'CREA'):
        for ident, fields in sorted(records[tag].items()):
            npdt = first(fields, 'NPDT')
            if tag == 'CREA':
                level = struct.unpack_from('<i', npdt, 4)[0] if len(npdt) == 96 else 1
            else:
                level = struct.unpack_from('<h', npdt)[0] if len(npdt) >= 2 else 1
            items = carried(fields, records, ref_pc, level)
            want_style, want = reference(tag, fields, records, ref_pc, items)
            flag = struct.unpack('<I', first(fields, 'FLAG', b'\0\0\0\0')[:4].ljust(4, b'\0'))[0]
            if tag == 'CREA' and not flag & 4:
                got = None
            else:
                try:
                    picked, _ = ours_pc.equipment(records, fields, level, ranged=True)
                except (KeyError, IndexError, struct.error, ValueError) as exc:
                    picked = ('error', str(exc), None, b'')
                got = picked[1] if picked else None
            if got is None:
                got_style = 'creature attack' if tag == 'CREA' else 'hand to hand'
            else:
                w = first(records['WEAP'].get(got, []), 'WPDT')
                got_style = STYLE_OF.get(struct.unpack_from('<h', w, 8)[0], 'melee') if len(w) >= 10 else 'none'
            weapons = sorted({i for i in items if i in records['WEAP']})
            rows.append({'id': ident, 'kind': 'npc' if tag == 'NPC_' else 'creature', 'refs': refs.get(ident, 0),
                         'carried weapons': weapons, 'spells': castable(fields, records),
                         'reference style': want_style, 'reference weapon': want,
                         'our style': got_style, 'our weapon': got,
                         'match': 'same' if (want, want_style) == (got, got_style) else
                                  'same style' if want_style == got_style else 'different style'})
    return rows


def summary(rows):
    out = {'records': len(rows), 'placed references': sum(r['refs'] for r in rows),
           'reference styles': Counter(r['reference style'] for r in rows),
           'casting fighters': sum(1 for r in rows if r['spells']),
           'match': Counter(r['match'] for r in rows),
           'match (references)': Counter(), 'mismatches by styles': Counter()}
    for r in rows:
        out['match (references)'][r['match']] += r['refs']
        if r['match'] != 'same':
            out['mismatches by styles'][r['reference style'] + ' -> ' + r['our style']] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, Counter) else v) for k, v in out.items()}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--public', type=Path)
    p.add_argument('--ours-module', type=Path, help='the prepare_combat.py whose choice is audited (default: this tree)')
    p.add_argument('--label', default='this tree')
    a = p.parse_args(argv)
    phase(1, 3, 'reading the masters')
    records, refs = read_masters(a.data_files)
    print('  %d NPCs, %d creatures, %d weapons' % (len(records['NPC_']), len(records['CREA']), len(records['WEAP'])),
          flush=True)
    phase(2, 3, 'the reference choice against ' + a.label)
    import prepare_combat
    rows = audit(records, refs, prepare_combat, load_pc(a.ours_module))
    phase(3, 3, 'writing the table')
    a.out.mkdir(parents=True, exist_ok=True)
    s = summary(rows)
    s['label'] = a.label
    (a.out / 'combat-style-table.json').write_text(json.dumps(rows, indent=1) + '\n', encoding='utf-8', newline='\n')
    (a.out / 'combat-style-summary.json').write_text(json.dumps(s, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.public:
        a.public.write_text(json.dumps(s, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(s, indent=1), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
