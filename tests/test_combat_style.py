# SPDX-License-Identifier: GPL-3.0-only
"""The combat style a fighter takes into a fight (NPC-CREATURE-COMBAT-STYLE-STATS-66, docs/ACTOR_RECORDS.md "Combat
styles"): tools/prepare_combat.py equipment weighs every weapon by its own skills as OpenMW 0.51 weaponpriority.cpp
rateWeapon does (a weapon whose skill is 0 is never taken, a low skill lowers its rating by the hit chance), on small
synthetic records (no game data in the repo); the world-wide table tools/combat_style_audit.py checks the same choice
with its own reference rule, and its public counts (docs/combat-style-audit.json) show no mismatch."""
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import combat_style_audit as csa  # noqa: E402
import prepare_combat  # noqa: E402

# the original's skill specializations (0 combat, 2 stealth): Long Blade 5 and Blunt 4 combat, Short Blade 22 and
# Marksman 23 stealth
SPEC = {i: 0 for i in range(27)}
SPEC.update({22: 2, 23: 2, 26: 2, 19: 2, 20: 2, 21: 2, 18: 2, 24: 2, 25: 2})


def wpdt(typ, chop, slash=(0, 0), thrust=(0, 0), speed=1.0):
    return struct.pack('<fihhffh6Bi', 10.0, 50, typ, 300, speed, 1.0, 0, *chop, *slash, *thrust, 0)


def npc(skills, agility=50, luck=40, items=()):
    d = bytearray(52)
    struct.pack_into('<h', d, 0, 5)
    for i in range(8):
        d[2 + i] = 50
    d[2 + 3], d[2 + 7] = agility, luck
    for i, v in skills.items():
        d[10 + i] = v
    return [('NPDT', bytes(d))] + [('NPCO', struct.pack('<i', n) + name.encode().ljust(32, b'\0')) for n, name in items]


def creature(combat, stealth, items=(), flag=0x45):
    v = [0, 5] + [50] * 8 + [40, 0, 80, 0, combat, 5, stealth, 1, 3, 2, 4, 0, 0, 0]
    return [('NPDT', struct.pack('<24i', *v)), ('FLAG', struct.pack('<I', flag))] + \
        [('NPCO', struct.pack('<i', n) + name.encode().ljust(32, b'\0')) for n, name in items]


def kinds():
    weap = {
        'mace': [('WPDT', wpdt(3, (1, 30), (1, 25), (1, 2)))],         # blunt: the highest maximum damage
        'longsword': [('WPDT', wpdt(1, (2, 18), (3, 20), (2, 16)))],   # long blade
        'dagger': [('WPDT', wpdt(0, (2, 8), (2, 8), (3, 10)))],        # short blade (stealth)
        'bow': [('WPDT', wpdt(9, (2, 20)))],
        'arrow': [('WPDT', wpdt(12, (2, 6)))],
    }
    return {'WEAP': weap, 'LEVI': {}, 'GMST': {}, 'RACE': {}, 'CLAS': {}, 'SPEL': {}, 'NPC_': {}, 'CREA': {},
            'ARMO': {}, 'SKIL': {i: [('SKDT', struct.pack('<ii', 0, s))] for i, s in SPEC.items()}}


def held(k, fields):
    w, _ = prepare_combat.equipment(k, fields, 5, ranged=True)
    return w[1] if w else None


class WeaponChoiceTests(unittest.TestCase):
    def test_the_skill_decides_not_the_biggest_damage(self):
        # a swordsman (Long Blade 70, Blunt 5) takes the sword although the mace hits harder: the mace's hit chance
        # is (5 + 10 + 4) x 1.25 = 24 %; the earlier choice took the highest maximum damage, the mace
        k = kinds()
        self.assertEqual(held(k, npc({5: 70, 4: 5}, items=((1, 'mace'), (1, 'longsword')))), 'longsword')
        self.assertEqual(held(k, npc({5: 5, 4: 70}, items=((1, 'mace'), (1, 'longsword')))), 'mace')

    def test_a_weapon_of_skill_zero_is_never_taken(self):
        k = kinds()
        self.assertIsNone(held(k, npc({5: 0}, items=((1, 'longsword'),))))          # fists, as the original
        self.assertEqual(held(k, npc({5: 1}, items=((1, 'longsword'),))), 'longsword')

    def test_a_marksman_shoots_and_a_bow_without_arrows_is_not_a_weapon(self):
        k = kinds()
        archer = npc({23: 80, 5: 10}, items=((1, 'longsword'), (1, 'bow'), (30, 'arrow')))
        self.assertEqual(held(k, archer), 'bow')
        self.assertEqual(held(k, npc({23: 80, 5: 10}, items=((1, 'longsword'), (1, 'bow')))), 'longsword')
        # without the ranged choice (the arena's held models) the melee weapon
        w, _ = prepare_combat.equipment(k, archer, 5)
        self.assertEqual(w[1], 'longsword')

    def test_a_creature_weighs_by_its_combat_magic_and_stealth(self):
        # a creature's Short Blade and Marksman are its Stealth value (OpenMW creature.cpp getSkill): with Stealth 0
        # it leaves the dagger and the bow and fights with its own attacks; its hit chance is its Combat value
        k = kinds()
        self.assertIsNone(held(k, creature(40, 0, items=((1, 'dagger'),))))
        self.assertEqual(held(k, creature(40, 30, items=((1, 'dagger'),))), 'dagger')
        self.assertEqual(held(k, creature(60, 30, items=((1, 'bow'), (20, 'arrow')))), 'bow')

    def test_the_audit_reference_agrees(self):
        k = kinds()
        k['NPC_'] = {'swordsman': npc({5: 70, 4: 5}, items=((1, 'mace'), (1, 'longsword'))),
                     'fists': npc({5: 0}, items=((1, 'longsword'),)),
                     'archer': npc({23: 80, 5: 10}, items=((1, 'longsword'), (1, 'bow'), (30, 'arrow')))}
        k['CREA'] = {'skel': creature(40, 0, items=((1, 'dagger'),)), 'scamp': creature(40, 30, ((1, 'dagger'),), 0x40)}
        rows = {r['id']: r for r in csa.audit(k, {}, prepare_combat, prepare_combat)}
        self.assertEqual({i: (r['reference style'], r['reference weapon']) for i, r in rows.items()},
                         {'swordsman': ('melee', 'longsword'), 'fists': ('hand to hand', None),
                          'archer': ('bow', 'bow'), 'skel': ('creature attack', None),
                          'scamp': ('creature attack', None)})
        self.assertEqual({r['match'] for r in rows.values()}, {'same'})


class WorldTableTests(unittest.TestCase):
    def test_no_style_mismatch_in_the_game(self):
        # the table over the three masters (tools/combat_style_audit.py, run in the shell container): every NPC and
        # creature takes the weapon the original's rule gives it
        s = json.loads((ROOT / 'docs/combat-style-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(s['match'], {'same': s['records']})
        self.assertGreater(s['records'], 3000)
        self.assertGreater(s['reference styles']['bow'], 100)


if __name__ == '__main__':
    unittest.main()
