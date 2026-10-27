# SPDX-License-Identifier: GPL-3.0-only
"""An NPC's own animation file (DANCER-OWN-ANIM-IGNORED-53): the Suran dancers' records name anim_dancingGirl.nif as
their own animation (MODL), whose one group, idle9, is their dance, picked by their wander package (AI_W idle
chances). The builder appends that file's groups to the common humanoid table under 'd:', gives the four NPCs that
name it the view 'progs/humanoid.awsk|d' ('|d|f' for the three women), and loops the dance for the NPCs whose most
likely idle it is. Synthetic records and skeletons (the four records' own MODL and AI_W values); no game data."""
import re
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import npc_anim  # noqa: E402
import skeletal_actor as S  # noqa: E402
from mwad.npc import outfit  # noqa: E402
from test_skeletal_actor import Chain, ChainSkeleton, axis_quat  # noqa: E402

# The four NPC records of Morrowind.esm that name their own animation: (id, female, race, AI_W idle chances
# Idle2..Idle9), as the game data has them.
DANCERS = (('breton dancer girl', True, 'breton', (20, 20, 20, 10, 0, 0, 0, 80)),
           ('redguard dancer girl', True, 'redguard', (20, 20, 20, 20, 0, 0, 0, 80)),
           ('nord dancer girl', True, 'nord', (20, 20, 20, 20, 0, 0, 0, 80)),
           ('yakov', False, 'high elf', (40, 40, 40, 40, 40, 40, 40, 5)))
DANCE_FILE = 'meshes/anim_dancinggirl.nif'


def kinds():
    """Synthetic records: the four NPCs (MODL anim_dancingGirl.NIF, their AI_W) and one NPC without its own file."""
    def npc(female, race, idles, model=b'anim_dancingGirl.NIF'):
        fields = [('FLAG', struct.pack('<I', 1 if female else 8)),
                  ('RNAM', race.encode()), ('NPDT', struct.pack('<h', 1)),
                  ('AI_W', struct.pack('<HHB8BB', 0, 5, 0, *idles, 1))]
        return ([('MODL', model)] if model else []) + fields
    out = {'NPC_': {i: npc(f, r, c) for i, f, r, c in DANCERS},
           'RACE': {r: [('RADT', struct.pack('<4fI', 1., 1., 1., 1., 0))] for _, _, r, _ in DANCERS},
           'BODY': {}, 'LEVI': {}, 'ARMO': {}, 'CLOT': {}}
    out['NPC_']['plain'] = npc(True, 'breton', (60, 20, 10, 0, 0, 0, 0, 0), model=None)
    return out


class Dance(ChainSkeleton):
    """The dancing girl's file over the chain: one group, idle9 (another motion than the common table's)."""
    keys = [(0.0, 'idle9: start'), (14.33, 'idle9: stop')]

    def local(self, name, time):
        if name == 'upper':
            return S.local_matrix(axis_quat((0, 0, 1), 30 * time), (0.0, 0.0, 10.0))
        return Chain.local(self, name, time)


class Female(ChainSkeleton):
    keys = [(10.0, 'walkforward: start'), (10.25, 'walkforward: loop start'), (11.25, 'walkforward: loop stop'),
            (11.5, 'walkforward: stop')]


class Records(unittest.TestCase):
    def test_the_four_records_name_their_own_animation_and_idle_chances(self):
        k = kinds()
        for identifier, female, _, chances in DANCERS:
            a = outfit(k, identifier)
            self.assertEqual(a['animation'], DANCE_FILE)
            self.assertEqual(a['idle_chances'], list(chances))
            self.assertEqual(a['female'], female)
            self.assertEqual(S.own_animation(a), 'd')
        # every other appearance stays as it was: no new keys
        plain = outfit(k, 'plain')
        self.assertNotIn('animation', plain)
        self.assertNotIn('idle_chances', plain)
        self.assertIsNone(S.own_animation(plain))


class Table(unittest.TestCase):
    def table(self):
        bones = S.bone_order(Chain.parents, ['fore'])
        data, report = S.build_table(ChainSkeleton(), bones=bones, over=Female(), append='f:',
                                     more=((Dance(), 'd:'),))
        return data, report, S.read_table(data)

    def test_the_dance_is_appended_after_the_female_groups(self):
        _, report, table = self.table()
        self.assertEqual(list(table['groups']), ['idle', 'walkforward', 'f:walkforward', 'd:idle9'])
        first, last = table['groups']['d:idle9']
        self.assertEqual(last - first, 114)                     # 14.33 s at 8 frames a second
        names = list(table['groups'])
        self.assertIn(('start', names.index('d:idle9'), first), table['keys'])
        self.assertIn(('stop', names.index('d:idle9'), last), table['keys'])
        # the dance's frames are the dance file's motion, not the common idle's
        alone = S.read_table(S.build_table(Dance(), bones=S.bone_order(Chain.parents, ['fore']))[0])
        a_first, _ = alone['groups']['idle9']
        for k in (0, 40, 100):
            np.testing.assert_allclose(S.table_world(table, first + k), S.table_world(alone, a_first + k),
                                         atol=4 * max(table['scale'], alone['scale']))
        # the common and female groups keep their frames (the dance only adds frames at the end)
        plain = S.read_table(S.build_table(ChainSkeleton(), bones=S.bone_order(Chain.parents, ['fore']),
                                           over=Female(), append='f:')[0])
        for g in ('idle', 'walkforward', 'f:walkforward'):
            self.assertEqual(table['groups'][g], plain['groups'][g])

    def test_each_dancer_names_its_view_and_loops_its_dance(self):
        k = kinds()
        _, report, table = self.table()
        for identifier, female, _, chances in DANCERS:
            a = dict(outfit(k, identifier), skeleton='meshes/base_anim.nif')
            path = S.table_view(S.table_choice(a)[2], report['names'])
            self.assertEqual(path, 'progs/humanoid.awsk|d|f' if female else 'progs/humanoid.awsk|d')
            self.assertLess(len(path), S.BLOCK_TABLE_NAME)
            self.assertEqual(S.table_prefixes(path), ['d:', 'f:'] if female else ['d:'])
            own = npc_anim.own_idle(table, report['times'], a, 'd:')
            if identifier == 'yakov':
                self.assertIsNone(own)                      # idle9 is 5 against 40: he stands as before
                continue
            self.assertEqual(own['group'], 'd:idle9')
            first, last = table['groups']['d:idle9']
            self.assertEqual((own['base'], own['count']), (first, last - first))
            self.assertAlmostEqual(own['step'], 14.33 / 114)
            fields = npc_anim.own_idle_fields({'anim': {'skeletal': {'own_idle': own}}})
            self.assertEqual((fields['aw_idle_base'], fields['aw_idle_count']), (first, last - first))
        # the kit's groups of a dancer come from her view: her walk the female one, her idle the common one
        a = dict(outfit(k, 'breton dancer girl'), skeleton='meshes/base_anim.nif')
        kit = {g['name']: g for g in npc_anim.table_groups(
            table, [{'name': 'idle', 'base': 0, 'count': 3, 'kind': 'loop', 'step': .2, 'source': 'base',
                     'events': []},
                    {'name': 'walk', 'base': 0, 'count': 3, 'kind': 'loop', 'step': .2, 'source': 'base',
                     'events': []}],
            prefix=S.table_prefixes(S.table_choice(a)[2]))}
        first, last = table['groups']['f:walkforward']
        self.assertEqual(kit['walk']['table_frames'], (first + 2, last - 2))     # its loop keys, 0.25 s in and out
        self.assertEqual(kit['idle']['table_frames'], table['groups']['idle'])

    def test_without_the_file_the_view_drops_its_prefix(self):
        bones = S.bone_order(Chain.parents, ['fore'])
        _, report = S.build_table(ChainSkeleton(), bones=bones, over=Female(), append='f:')
        a = dict(outfit(kinds(), 'nord dancer girl'), skeleton='meshes/base_anim.nif')
        self.assertEqual(S.table_view(S.table_choice(a)[2], report['names']), 'progs/humanoid.awsk|f')

    def test_the_game_table_appends_the_files_the_data_has(self):
        made = {'meshes/base_anim.nif': ChainSkeleton(), S.FEMALE_SKELETON: Female(), DANCE_FILE: Dance()}

        def skeleton_of(path):
            return made[path]
        sources = S.own_sources(skeleton_of)
        self.assertEqual([p for _, p in sources], ['d:'])
        self.assertEqual(S.own_sources(lambda path: (_ for _ in ()).throw(KeyError(path))), [])
        self.assertEqual(S.OWN_ANIMATIONS[DANCE_FILE], 'd')

    def test_every_npc_of_the_three_masters_with_its_own_file_has_a_table(self):
        """The whole list (Morrowind.esm, Tribunal.esm, Bloodmoon.esm, audited 26 October 2026): four NPC records
        name an own animation file, all anim_dancingGirl.nif; each gets a view whose prefix the table appends."""
        k = kinds()
        for identifier, female, _, _ in DANCERS:
            a = dict(outfit(k, identifier), skeleton='meshes/base_anim.nif')
            prefix = S.own_animation(a)
            self.assertIn(prefix, S.OWN_ANIMATIONS.values())
            self.assertIn(S.TABLE_VIEW + prefix, S.table_choice(a)[2])
        self.assertEqual(len(DANCERS), 4)
        self.assertEqual(len(set(S.OWN_ANIMATIONS.values())), len(S.OWN_ANIMATIONS))     # one prefix per file


class EngineLoop(unittest.TestCase):
    def test_the_idle_think_loops_the_entitys_own_idle(self):
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        self.assertIn('.float aw_idle_base;', qc)
        self.assertIn('.float aw_idle_count;', qc)
        body = qc[qc.index('void() aw_npc_idle'):qc.index('void() aw_npc_idle') + 900]
        self.assertTrue(re.search(r'self\.frame >= self\.aw_idle_base \+ self\.aw_idle_count', body))
        self.assertIn('self.frame = self.aw_idle_base;', body)

    def test_the_resident_writers_pass_the_loop_on(self):
        for name in ('tools/prepare_area.py', 'tools/import_town.py'):
            self.assertIn('own_idle_fields(record)', (ROOT / name).read_text(encoding='utf-8'), name)


if __name__ == '__main__':
    unittest.main()
