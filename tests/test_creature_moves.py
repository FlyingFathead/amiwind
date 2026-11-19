# SPDX-License-Identifier: GPL-3.0-only
"""The creature moves table (tools/creature_moves.py, CREATURE-NIXHOUND-HUMAN-MOVES-67, docs/CREATURES.md "How each
creature moves and fights"): every creature record against the build's creature library and the original's rules,
on synthetic rows; and the engine's two rules it names (aw_combat.c: a four-legged creature never side-steps a miss,
the combat readout names a creature's own attacks)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):      # src first: tools/mwad.py must not shadow the src/mwad package
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))
import creature_moves as M  # noqa: E402

OWN = {g: 'table' for g in M.GROUPS}


def library():
    return {'models': {
        'r/nixhound.nif': {'method': 'skeletal', 'kit': dict(OWN), 'sources': ['meshes/r/xnixhound.kf'], 'triangles': 480},
        'r/beast.nif': {'method': 'skeletal', 'kit': dict(OWN, attack='base'), 'sources': ['meshes/r/xbeast.kf']},
        'r/netch.nif': {'method': 'skeletal', 'kit': dict(OWN, run='idle'), 'sources': ['meshes/r/xnetch.kf']},
        'r/queen.nif': {'method': 'skeletal', 'kit': dict(OWN, walk='idle', run='idle'), 'sources': []},
        'r/dremora.nif': {'method': 'skeletal', 'kit': dict(OWN, walk='base', run='walk'),
                          'sources': ['meshes/xbase_anim.kf', 'meshes/r/xdremora.kf']},
        'r/human_kf.nif': {'method': 'skeletal', 'kit': dict(OWN), 'sources': ['meshes/xbase_anim.kf']}}}


def records():
    return {'nix-hound': {'mesh': 'r\\NixHound.nif', 'name': 'Nix-Hound', 'flags': 0x40, 'dead': False},
            'beast': {'mesh': 'r/beast.nif', 'name': 'Beast', 'flags': 0x40, 'dead': False},
            'netch': {'mesh': 'r/netch.nif', 'name': 'Netch', 'flags': 0x20, 'dead': False},
            'netch_dead': {'mesh': 'r/netch.nif', 'name': 'Netch', 'flags': 0x20, 'dead': True},
            'queen': {'mesh': 'r/queen.nif', 'name': 'Queen', 'flags': 0, 'dead': False},
            'dremora': {'mesh': 'r/dremora.nif', 'name': 'Dremora', 'flags': 0x41, 'dead': False},
            'odd': {'mesh': 'r/human_kf.nif', 'name': 'Odd', 'flags': 0x40, 'dead': False},
            'gone': {'mesh': 'r/elsewhere.nif', 'name': 'Elsewhere', 'flags': 0x40, 'dead': False},
            'nomesh': {'mesh': '', 'name': 'No mesh', 'flags': 0, 'dead': False}}


class CreatureMovesTests(unittest.TestCase):
    def setUp(self):
        self.result = M.table(records(), library())
        self.rows = {r['id']: r for r in self.result['rows']}

    def test_attack_style_and_side_steps_by_the_two_legged_flag(self):
        nix, dremora = self.rows['nix-hound'], self.rows['dremora']
        self.assertEqual((nix['attack_style'], nix['side_steps']), ('own attacks 1-3', False))
        self.assertEqual((dremora['attack_style'], dremora['side_steps']), ('hand to hand', True))
        self.assertEqual(nix['flags'], ['walks'])
        self.assertEqual(nix['triangles'], 480)
        self.assertEqual(nix['mismatches'], [])                    # its own groups: no mismatch

    def test_mismatches(self):
        self.assertEqual(self.rows['beast']['mismatches'], ['human-groups: attack'])         # human group, four legs
        self.assertEqual(self.rows['odd']['mismatches'], ['human-groups: the shared xbase_anim.kf'])
        self.assertEqual(self.rows['netch']['mismatches'], ['run-on-idle'])                   # has a walk
        self.assertEqual(self.rows['netch_dead']['mismatches'], [])                           # a corpse does not run
        self.assertEqual(self.rows['dremora']['mismatches'], [])   # two-legged: the human groups are the original's
        self.assertEqual(self.rows['queen']['mismatches'], [])     # no walk in its files: idle, as in the original
        self.assertIn('walk, run', self.rows['queen']['notes'][0])
        self.assertEqual(self.rows['gone']['notes'], ['not in the creature library'])
        self.assertEqual(self.rows['nomesh']['notes'], ['no mesh'])
        self.assertEqual(self.result['counts']['mismatches'], 3)
        self.assertEqual(self.result['counts']['two-legged'], 1)

    def test_markdown_and_check_exit(self):
        text = M.markdown(self.result)
        self.assertIn('| nix-hound | r/nixhound.nif | walks | own attacks 1-3 | no |', text)
        self.assertIn('run-on-idle', text)
        self.assertEqual(text.count('\n| '), len(self.result['rows']) + 1)   # the header and one line a row

    def test_engine_rules_it_names(self):
        combat = (ROOT / 'engine/aga/src/aw_combat.c').read_text(encoding='utf-8')
        react = combat[combat.index('static void npc_react_miss'):combat.index('static void player_react_miss')]
        self.assertLess(react.index('start_block(s)'), react.index('if(s->f.creature==1)return;'))
        self.assertLess(react.index('if(s->f.creature==1)return;'), react.index('dodge_side(s,p)'))
        self.assertIn('*beast[]={"attack 1","attack 2","attack 3"}', combat)
        self.assertIn('print_swing(s->f.name,"you",s->attack,s->f.creature==1,&out);', combat)
        rules = (ROOT / 'engine/aga/src/aw_combat_rules.c').read_text(encoding='utf-8')
        self.assertIn('o->creature=(unsigned char)(b->flags&AWR_BIPEDAL?2:1);', rules)   # 1: four-legged


if __name__ == '__main__':
    unittest.main()
