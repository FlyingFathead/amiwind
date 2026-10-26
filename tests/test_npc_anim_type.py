# SPDX-License-Identifier: GPL-3.0-only
"""--npc-anim-type 1|2 (docs/MODULAR_NPCS.md "Runtime method C", docs/ANIMKIT.md): the build switch and its keys, the
kit's layout filled from a shared animation table, the female groups layered over the common ones, the table each
actor plays and the carried items' skeletal tag. Synthetic skeletons and tables; no game data."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import build  # noqa: E402
import npc_anim  # noqa: E402
import skeletal_actor as S  # noqa: E402
from test_skeletal_actor import Chain, ChainSkeleton, axis_quat  # noqa: E402


class Switch(unittest.TestCase):
    def test_skeletal_is_the_default_and_baked_is_chosen_on_purpose(self):
        self.assertEqual(build.parser().parse_args([]).npc_anim_type, 2)
        self.assertEqual(build.parser().parse_args(['--npc-anim-type', '1']).npc_anim_type, 1)
        with patch('sys.stderr'), self.assertRaises(SystemExit):
            build.parser().parse_args(['--npc-anim-type', '3'])

    def test_the_environment_carries_the_type_into_the_stage_keys(self):
        def args(*argv):
            a = build.parser().parse_args(list(argv))
            a.npc_anim = build.ANIM_KIT_PROFILES[a.anim_kit]        # as build.main resolves it
            return a
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(npc_anim.ANIM_TYPE_ENV, None)
            build.export_option_environment(args('--npc-anim-type', '1'), announce=False)
            self.assertEqual(os.environ.get(npc_anim.ANIM_TYPE_ENV), '1')
            self.assertEqual(npc_anim.anim_type(), 1)
            build.export_option_environment(args(), announce=False)
            self.assertNotIn(npc_anim.ANIM_TYPE_ENV, os.environ)
            self.assertEqual(npc_anim.anim_type(), 2)
        with self.assertRaises(ValueError):
            npc_anim.anim_type('3')
        # the stage fingerprints collect the AMIWIND_* names the reached code holds (build_cache.environment_names)
        import build_cache
        source = (ROOT / 'tools/npc_anim.py').read_text(encoding='utf-8')
        self.assertIn(npc_anim.ANIM_TYPE_ENV, build_cache.environment_names([(source, None)]))

    def test_the_resident_unit_cache_keys_the_two_types_apart(self):
        # prepare_area's resident unit cache (open_residents: UnitCache over the AMIWIND_* names its code reaches)
        import pass_cache
        with patch.dict(os.environ, {npc_anim.ANIM_TYPE_ENV: '1'}):
            baked = pass_cache.environment(ROOT / 'tools/prepare_area.py')
        self.assertEqual(baked.get(npc_anim.ANIM_TYPE_ENV), '1')
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(npc_anim.ANIM_TYPE_ENV, None)
            skeletal = pass_cache.environment(ROOT / 'tools/prepare_area.py')
        self.assertNotEqual(baked, skeletal)

    def test_the_actor_library_keys_the_two_types_apart(self):
        import npc_library
        app = {'parts': [], 'skeleton': 'meshes/base_anim.nif', 'height': 1.0, 'weight': 1.0, 'female': False}
        with patch.dict(os.environ, {npc_anim.ANIM_TYPE_ENV: '1'}):
            baked = npc_library.appearance_key(app, 'react+full')
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(npc_anim.ANIM_TYPE_ENV, None)
            skeletal = npc_library.appearance_key(app, 'react+full')
        self.assertNotEqual(baked, skeletal)


def kit_table():
    """A table as read_table gives it: idle, a walk with its loop and footsteps, a hand-to-hand attack, a shield
    block, the walk-left loop (the dodge) and a jump."""
    groups = {'idle': (0, 9), 'walkforward': (10, 20), 'handtohand': (21, 40), 'shield': (41, 49),
              'walkleft': (50, 60), 'jump': (61, 66)}
    keys = [('start', 0, 0), ('stop', 0, 9),
            ('start', 1, 10), ('loop start', 1, 11), ('soundgen: left', 1, 13), ('soundgen: right', 1, 17),
            ('loop stop', 1, 19), ('stop', 1, 20),
            ('chop start', 2, 22), ('chop hit', 2, 26), ('chop large follow stop', 2, 30),
            ('block start', 3, 41), ('block hit', 3, 44), ('block stop', 3, 49),
            ('loop start', 4, 51), ('loop stop', 4, 59),
            ('start', 5, 61), ('loop start', 5, 63), ('loop stop', 5, 63), ('stop', 5, 66)]
    return {'groups': groups, 'keys': keys, 'rate': 8.0, 'frames': 67}


def plan_groups(*names):
    """plan()-like groups (their baked frames do not matter: the table's replace them)."""
    out = []
    for name in names:
        g = {'name': name, 'base': 0, 'count': 3, 'kind': npc_anim.GROUPS[name][2], 'step': .2, 'source': 'base',
             'events': [(0, 'left')]}
        if name == 'walk':
            g['speed'] = 48.5
        if name in ('attack', 'block'):
            g['hit'] = .4
        out.append(g)
    return out


class LayoutFromTable(unittest.TestCase):
    def test_kit_groups_play_the_table_frames(self):
        groups = npc_anim.table_groups(kit_table(), plan_groups('idle', 'walk', 'attack', 'block', 'dodgel', 'swim',
                                                                'jump', 'land'))
        by = {g['name']: g for g in groups}
        # loops and 'once' groups leave the stop key's frame out (the start's pose again), 'hold' groups end on it
        self.assertEqual((by['idle']['base'], by['idle']['count']), (0, 9))
        self.assertEqual((by['walk']['base'], by['walk']['count']), (11, 8))
        self.assertEqual((by['attack']['base'], by['attack']['count']), (22, 8))
        self.assertEqual((by['block']['base'], by['block']['count']), (41, 8))
        self.assertEqual((by['dodgel']['base'], by['dodgel']['count']), (51, 8))     # the dodge: the walk-left loop
        self.assertEqual((by['jump']['base'], by['jump']['count']), (61, 3))
        self.assertEqual((by['land']['base'], by['land']['count']), (63, 4))
        # a group the table lacks stands on the idle (OpenMW falls back to idle)
        self.assertEqual((by['swim']['base'], by['swim']['count'], by['swim']['source']), (0, 1, 'idle'))
        # own speed and hit fraction are plan()'s; footsteps are the table's keys inside the frames
        self.assertEqual(by['walk']['speed'], 48.5)
        self.assertEqual(by['attack']['hit'], .4)
        self.assertEqual(by['walk']['events'], [(2, 'left'), (6, 'right')])
        self.assertEqual(by['idle']['events'], [])
        self.assertTrue(all(g['step'] == .125 for g in groups))

    def test_a_view_plays_its_own_groups_first(self):
        """SKEL-TABLE-SHARED-FEMALE-52: the female walk lives in the common table as 'f:walkforward'; a female
        human's layout ('f:' view) plays it and every group the view lacks from the common ones."""
        t = kit_table()
        t['groups']['f:walkforward'] = (67, 75)
        t['keys'] = t['keys'] + [('start', 6, 67), ('loop start', 6, 68), ('loop stop', 6, 74), ('stop', 6, 75)]
        t['frames'] = 76
        female = {g['name']: g for g in npc_anim.table_groups(t, plan_groups('idle', 'walk'), prefix='f:')}
        common = {g['name']: g for g in npc_anim.table_groups(t, plan_groups('idle', 'walk'))}
        self.assertEqual(female['walk']['table_frames'], (68, 74))
        self.assertEqual(common['walk']['table_frames'], (11, 19))
        self.assertEqual(female['idle']['table_frames'], common['idle']['table_frames'])

    def test_the_layout_parses_as_the_engine_reads_it(self):
        groups = npc_anim.table_groups(kit_table(), plan_groups('idle', 'walk', 'attack'))
        text = npc_anim.layout(groups, 'bare')
        words = text.split()
        self.assertIn('idle:0:9:0.1250', words)
        self.assertIn('walk:11:8:0.1250:48.50', words)
        self.assertIn('attack:22:8:0.1250:0.400', words)
        self.assertIn('@walk:2:left', words)
        self.assertFalse(any(w.startswith('>') for w in words))    # no mover
        # engine rules (aw_anim.c AW_AnimParse): base + count within the model's frames (a skeletal model's are its
        # table's, model_alias_stream.inc), count 1..64, step 0..5
        for g in groups:
            self.assertTrue(0 <= g['base'] and g['base'] + g['count'] <= 67 and 1 <= g['count'] <= 64)
            self.assertTrue(0 < g['step'] < 5)

    def test_each_group_keeps_its_own_frame_time(self):
        times = [i * .125 for i in range(67)]
        times[11:20] = list(np.linspace(times[11], times[11] + 1.0, 9))     # 8 frames over 1 s: 0.125
        times[22:31] = list(np.linspace(10.0, 10.9, 9))                     # 0.1125 s a frame
        groups = npc_anim.table_groups(kit_table(), plan_groups('walk', 'attack'), times=times)
        self.assertAlmostEqual(groups[0]['step'], .125)
        self.assertAlmostEqual(groups[1]['step'], .1125)

    def test_attack_stance_and_long_groups(self):
        t = kit_table()
        t['groups']['weapontwowide'] = (0, 66)
        t['keys'] = t['keys'] + [('chop start', 6, 1), ('chop large follow stop', 6, 7)]
        g = npc_anim.table_groups(t, plan_groups('idle', 'attack'), 'weapontwowide')
        self.assertEqual((g[1]['base'], g[1]['count']), (1, 6))
        t['keys'] = t['keys'] + [('chop large follow stop', 6, 7)]
        t['groups']['handtohand'] = (0, 66)
        t['keys'] = [k if k[:2] != ('chop large follow stop', 2) else (k[0], 2, 100) for k in t['keys']]
        with self.assertRaises(ValueError):
            npc_anim.table_groups(t, plan_groups('idle', 'attack'))


class FemaleOver(ChainSkeleton):
    """A female file over the chain: its own walk (another motion, another place in its file) and one group of its
    own; no idle."""
    keys = [(10.0, 'walkforward: start'), (11.5, 'walkforward: stop'), (20.0, 'idle4: start'), (21.0, 'idle4: stop')]

    def local(self, name, time):
        if name == 'upper':
            return S.local_matrix(axis_quat((0, 1, 0), 50 * time), (0.0, 0.0, 10.0))
        return Chain.local(self, name, time)


class LayeredTable(unittest.TestCase):
    def test_the_female_groups_replace_the_common_ones(self):
        base, over = ChainSkeleton(), FemaleOver()
        bones = S.bone_order(Chain.parents, ['fore'])
        data, report = S.build_table(base, bones=bones, over=over)
        table = S.read_table(data)
        self.assertEqual(list(table['groups']), ['idle', 'walkforward', 'idle4'])
        self.assertEqual(report['over'], ['walkforward', 'idle4'])
        alone, _ = S.build_table(over, bones=bones)
        alone = S.read_table(alone)
        first, last = table['groups']['walkforward']
        a_first, a_last = alone['groups']['walkforward']
        self.assertEqual(last - first, a_last - a_first)
        for k in range(last - first + 1):
            np.testing.assert_allclose(S.table_world(table, first + k), S.table_world(alone, a_first + k),
                                       atol=4 * max(table['scale'], alone['scale']))
        # the common idle stays the common file's
        common, _ = S.build_table(base, bones=bones)
        common = S.read_table(common)
        np.testing.assert_allclose(S.table_world(table, 3), S.table_world(common, 3),
                                   atol=4 * max(table['scale'], common['scale']))
        # the text keys follow their groups
        names = list(table['groups'])
        self.assertIn(('start', names.index('idle4'), table['groups']['idle4'][0]), table['keys'])

    def test_without_a_layer_the_table_is_the_skeleton_alone(self):
        bones = S.bone_order(Chain.parents, ['fore'])
        one, _ = S.build_table(ChainSkeleton(), bones=bones)
        two, _ = S.build_table(ChainSkeleton(), bones=bones, over=None)
        self.assertEqual(one, two)


class ReducedFromTheKitsPoses(unittest.TestCase):
    def test_a_skeletal_resident_is_reduced_from_the_baked_kits_samples(self):
        # SKEL-GROUND-SOLES-52: reduced from the 8 idle samples alone, a beast resident's soles (Wusha, an Argonian,
        # dev1-try8) came out unlike its baked idle's and no spot on its sloped floor fitted; reduced from the kit's
        # own samples (every group of the profile, as type 1 bakes them) it fits where the baked idle did
        seen = {}

        class Poser:
            samples = [(None, 3.25, None), (None, 3.5, None)]
        groups = [{'name': 'idle', 'base': 0, 'count': 2, 'kind': 'loop', 'step': .2, 'events': [],
                   'source': 'base'}]
        table = {'groups': {'idle': (0, 3)}, 'keys': [('start', 0, 0), ('stop', 0, 3)], 'rate': 8.0, 'frames': 4}
        report = {'times': [0, .125, .25, .375], 'bone_names': ['bip01']}

        def model(*args, **kwargs):
            seen.update(kwargs)
            return b'MDL', {'vertices': 3, 'faces': 1}

        class Nif:
            N = None
        app = {'skeleton': 'meshes/base_animkna.nif', 'weight': 1.0, 'height': 1.0}
        with patch.object(S, 'game_table', lambda *a: (b'T', report, table, 'progs/humanoid_kna.awsk', Nif(), None)), \
                patch.object(npc_anim, 'plan', lambda *a, **k: (Poser(), groups)), \
                patch.object(S, 'skeletal_model', model), \
                patch('npc_items.carried_models', lambda *a: ({}, {})):
            S.skeletal_resident('k', None, app, b'', [('idle', 8)], None)
        self.assertIsInstance(seen['poser'], Poser)
        self.assertEqual(list(seen['times']), [0.0, 1.0])            # the kit's sample indices
        self.assertEqual(seen['rest_time'], 3.25)                    # its first sample: the idle start
        self.assertEqual(seen['head_detail'], 'budget')


class Choice(unittest.TestCase):
    def test_each_actor_plays_its_skeletons_table(self):
        human = {'skeleton': 'meshes/base_anim.nif', 'female': False}
        self.assertEqual(S.table_choice(human), ('meshes/base_anim.nif', None, 'progs/humanoid.awsk'))
        self.assertEqual(S.table_choice(dict(human, female=True)),
                         ('meshes/base_anim.nif', 'meshes/base_anim_female.nif', 'progs/humanoid.awsk|f'))
        # SKEL-TABLE-SHARED-FEMALE-52: the female view reads the common table's file, its own groups first
        self.assertEqual(S.table_file('progs/humanoid.awsk|f'), 'progs/humanoid.awsk')
        self.assertEqual(S.table_prefix('progs/humanoid.awsk|f'), 'f:')
        self.assertEqual(S.table_prefix('progs/humanoid.awsk'), '')
        self.assertEqual(sorted({S.table_file(p) for p in S.GAME_TABLES.values()}),
                         ['progs/humanoid.awsk', 'progs/humanoid_kna.awsk'])
        beast = {'skeleton': 'meshes/base_animkna.nif', 'female': True}
        self.assertEqual(S.table_choice(beast), ('meshes/base_animkna.nif', None, 'progs/humanoid_kna.awsk'))
        with self.assertRaises(ValueError):
            S.table_choice({'skeleton': 'meshes/other.nif'})
        for path in S.GAME_TABLES.values():
            self.assertLess(len(path), S.BLOCK_TABLE_NAME)


class ItemTag(unittest.TestCase):
    def test_the_skeletal_tag_round_trips(self):
        bones = ['bip01', 'weapon bone', 'shield bone']
        text = S.skeletal_tag(2730, {'weapon': 'items/w_iron_dagger.mdl'}, bones, [.25, .25, .2625])
        self.assertTrue(text.startswith('AWTS1 2730\n'))
        self.assertFalse(text.startswith('AWTG1'))      # today's item reader refuses it (aw_items.c)
        back = S.read_skeletal_tag(text)
        self.assertEqual(back, {'frames': 2730, 'paths': {'weapon': 'items/w_iron_dagger.mdl', 'shield': None},
                                'bones': [1, 2], 'scale': [.25, .25, .2625]})
        self.assertEqual(S.read_skeletal_tag(S.skeletal_tag(5, {}, ['bip01'], [1, 1, 1]))['bones'], [-1, -1])
        with self.assertRaises(ValueError):
            S.read_skeletal_tag('AWTG1 3\n')

    def test_a_guards_torch_carries_its_flame_point(self):
        # the torch beside the guard's own shield on the shield bone, its 'fire emitter' point in that bone's space
        # (aw_guard_torch.c shows it by the day and night cycle)
        text = S.skeletal_tag(2730, {'shield': 'items/a_shield.mdl'}, ['shield bone'], [.25, .25, .25],
                              light=('items/gt_torch_0123456789ab.mdl', (1.5, -2.25, 30.0)))
        self.assertTrue(text.endswith('light items/gt_torch_0123456789ab.mdl\nemitter 1.500000 -2.250000 30.000000\n'))
        back = S.read_skeletal_tag(text)
        self.assertEqual(back['paths']['shield'], 'items/a_shield.mdl')
        self.assertEqual((back['light'], back['emitter']), ('items/gt_torch_0123456789ab.mdl', [1.5, -2.25, 30.0]))
        self.assertEqual(back['bones'], [-1, 0])
        self.assertNotIn('light', S.read_skeletal_tag(S.skeletal_tag(5, {}, ['bip01'], [1, 1, 1])))


if __name__ == '__main__':
    unittest.main()
