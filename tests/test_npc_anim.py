# SPDX-License-Identifier: GPL-3.0-only
"""Character animation kit (docs/ANIMATION.md): profiles, the sample plan on a
synthetic skeleton (groups, in-place root, female override, events, speeds),
the layout string, footstep classes, named alias frames, and the engine side
(aw_anim.c host fixture and source contracts)."""
import os
import re
import shutil
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import npc_anim  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


class FakeSkeleton:
    """Root bone moving +Y at `speed` NIF units/s at all times."""

    def __init__(self, keys, speed=100.0):
        self.N = None
        self.keys = sorted((t, k) for k, t in keys.items())
        self.events = dict(keys)
        self.nodes = {'bip01': 0, 'spine': 1}
        self.parents = {'bip01': None, 'spine': 'bip01'}
        self.speed = speed

    def local(self, name, time):
        m = np.eye(4)
        if name == 'bip01':
            m[3, :3] = (1.0, 2.0 + self.speed * time, 70.0)
        return m


KEYS = {'idle: start': 0.0, 'idle: stop': 2.0, 'walkforward: loop start': 10.0, 'walkforward: loop stop': 11.0,
        'death1: start': 20.0, 'death1: stop': 21.0, 'handtohand: chop start': 30.0,
        'handtohand: chop hit': 30.6, 'handtohand: chop large follow stop': 31.0}


def skeleton():
    s = FakeSkeleton(KEYS)
    s.keys += [(10.25, 'soundgen: left'), (10.75, 'soundgen: right'), (20.5, 'soundgen: moan')]
    s.keys.sort()
    return s


class PlanTests(unittest.TestCase):
    def test_profiles_start_with_the_previous_idle_frames(self):
        table = npc_anim.profiles()
        self.assertEqual(table['idle'], [['idle', 8]])
        for name, groups in table.items():
            self.assertEqual(groups[0], ['idle', 8], name)
        self.assertIn('full', table)

    def test_default_profile_is_idle_and_unknown_is_refused(self):
        old = os.environ.pop(npc_anim.ENV, None)
        try:
            self.assertEqual(npc_anim.selected_profile()[0], 'idle')
            with self.assertRaises(ValueError):
                npc_anim.selected_profile('nope')
        finally:
            if old is not None:
                os.environ[npc_anim.ENV] = old

    def test_idle_times_match_the_previous_sampler(self):
        kit, groups = npc_anim.plan(skeleton(), [['idle', 8]])
        times = [kit.samples[i][1] for i in range(8)]
        self.assertEqual(times, [float(t) for t in np.linspace(0, 2, 8, endpoint=False)])
        self.assertTrue(all(kit.samples[i][2] is None for i in range(8)))
        self.assertEqual(npc_anim.layout(groups), 'idle:0:8:0.2500')

    def test_walk_in_place_speed_events_and_layout(self):
        kit, groups = npc_anim.plan(skeleton(), [['idle', 8], ['walk', 8], ['death', 5], ['attack', 4], ['run', 2]])
        walk = groups[1]
        self.assertEqual((walk['base'], walk['count']), (8, 8))
        self.assertAlmostEqual(walk['speed'], 25.0)       # 100 NIF units/s x 0.25
        self.assertEqual(walk['events'], [(2, 'left'), (6, 'right')])
        # in place: the root keeps its idle x, y in every walk sample
        self.assertEqual(tuple(kit.pose(9)('bip01')[3, :2]), (1.0, 2.0))
        self.assertAlmostEqual(kit.pose(21)('bip01')[3, 1], 2.0 + 100 * 30.0)   # attack keeps the source root
        death = groups[2]
        self.assertEqual([kit.samples[death['base'] + i][1] for i in range(5)], [20.0, 20.25, 20.5, 20.75, 21.0])
        self.assertEqual(death['events'], [(2, 'moan')])
        self.assertAlmostEqual(groups[3]['hit'], .6)
        self.assertEqual(groups[4]['source'], 'idle')     # no run keys: the idle start stands in
        text = npc_anim.layout(groups, 'medium')
        self.assertIn('walk:8:8:0.1250:25.00', text)
        self.assertIn('@walk:2:left', text)
        self.assertNotIn('moan', text)                    # NPCs ignore moan/roar/scream (creatures use SNDG)
        self.assertIn('~left:aw/fx/footmedleft.wav:aw/fx/footwaterleft.wav:aw/fx/swimleft.wav', text)
        self.assertTrue(text.split()[-1].startswith('~right:'))
        self.assertEqual(npc_anim.needed_sounds(groups, 'medium'),
                         sorted(['FootMedLeft', 'FootWaterLeft', 'Swim Left', 'FootMedRight', 'FootWaterRight', 'Swim Right']))

    def test_female_override_takes_only_the_groups_it_has(self):
        female = FakeSkeleton({'walkforward: loop start': 5.0, 'walkforward: loop stop': 6.0}, speed=80.0)
        kit, groups = npc_anim.plan(skeleton(), [['idle', 8], ['walk', 4], ['death', 2]], female=female)
        self.assertEqual([g['source'] for g in groups], ['base', 'female', 'base'])
        self.assertIs(kit.samples[8][0], female)
        self.assertAlmostEqual(groups[1]['speed'], 20.0)

    def test_in_place_helper_for_other_group_tables(self):
        kit = npc_anim.in_place(skeleton(), [(10.5, True), (30.0, False)])
        self.assertEqual(tuple(kit.pose(0)('bip01')[3, :2]), (1.0, 2.0))
        self.assertAlmostEqual(kit.pose(1)('bip01')[3, 1], 2.0 + 100 * 30.0)
        combat = (ROOT / 'tools/prepare_combat.py').read_text(encoding='utf-8')
        self.assertIn('npc_anim.in_place(skeleton, entries)', combat)

    def test_sound_names_fit_classic_ffs(self):
        for foot in npc_anim.FOOT:
            for ids in npc_anim.event_sounds(foot).values():
                for soun in ids:
                    self.assertLessEqual(len(npc_anim.sound_file(soun).rsplit('/', 1)[1]), 30)

    def test_foot_class_from_boots_weight(self):
        kinds = {'ARMO': {'b': [('AODT', struct.pack('<if', 5, 10.0))], 'h': [('AODT', struct.pack('<if', 5, 25.0))],
                          'm': [('AODT', struct.pack('<if', 5, 15.0))], 'c': [('AODT', struct.pack('<if', 1, 1.0))]},
                 'GMST': {}}

        def app(item, skel='meshes/base_anim.nif'):
            return {'skeleton': skel, 'equipment': [{'item': item, 'kind': 'ARMO'}] if item else []}
        self.assertEqual(npc_anim.foot_class(kinds, app(None)), 'bare')
        self.assertEqual(npc_anim.foot_class(kinds, app('c')), 'bare')      # a cuirass is not boots
        self.assertEqual(npc_anim.foot_class(kinds, app('b')), 'light')     # <= 20 x 0.6
        self.assertEqual(npc_anim.foot_class(kinds, app('m')), 'medium')    # <= 20 x 0.9
        self.assertEqual(npc_anim.foot_class(kinds, app('h')), 'heavy')
        self.assertEqual(npc_anim.foot_class(kinds, app('h', 'meshes/base_animkna.nif')), 'bare')

    def test_publish_writes_the_layout_beside_the_model(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            record = {'model': 'progs/a_x.mdl', 'anim': {'layout': 'idle:0:8:0.3333', '_sounds': {'aw/fx/a.wav': b'RIFF'}}}
            npc_anim.publish(id1, record)
            self.assertEqual((id1 / 'progs/a_x.anm').read_bytes(), b'idle:0:8:0.3333\n')
            self.assertEqual((id1 / 'sound/aw/fx/a.wav').read_bytes(), b'RIFF')
            self.assertNotIn('_sounds', record['anim'])
            npc_anim.publish(id1, {'model': 'progs/b.mdl'})
            self.assertFalse((id1 / 'progs/b.anm').exists())


class VoiceTests(unittest.TestCase):
    def info(self, sound, *, race='', sex=-1, disp=0, conds=(), cls=''):
        import struct as st
        fields = [('DATA', st.pack('<iibbbb', 1, disp, -1, sex, -1, 0)), ('RNAM', race.encode() + b'\0'),
                  ('SNAM', sound.encode() + b'\0')]
        if cls:
            fields.append(('CNAM', cls.encode() + b'\0'))
        for scvr, value in conds:
            fields += [('SCVR', scvr.encode('latin-1')), ('INTV', st.pack('<i', value))]
        return fields

    def test_first_match_list_with_runtime_conditions(self):
        from mwad.npc import voice_lines
        topics = {'attack': [
            self.info('vo/d/m/a1.mp3', race='Dark Elf', conds=[('02sX3Random100', 75)]),
            self.info('vo/d/m/b1.mp3', race='Breton'),
            self.info('vo/d/m/a2.mp3', race='Dark Elf', cls='Guard'),
            self.info('vo/d/m/a3.mp3', race='Dark Elf', conds=[('0104l', 0)]),      # Health_Percent? op l: kept
            self.info('vo/d/m/a4.mp3', race='Dark Elf', conds=[('0190', 0)]),       # FriendHit... unknown op 0
            self.info('vo/d/m/a5.mp3', race='Dark Elf'),
            self.info('vo/d/m/a6.mp3', race='Dark Elf')]}
        actor = {'id': 'x', 'race': 'dark elf', 'female': False, 'class': 'Commoner', 'faction': ''}
        lines = voice_lines(topics, actor, 'attack')
        self.assertEqual(lines[0], ('vo/d/m/a1.mp3', (('r', 'g', 75),)))
        self.assertEqual(lines[-1], ('vo/d/m/a5.mp3', None))                         # the first unconditional ends it
        self.assertNotIn('vo/d/m/b1.mp3', [s for s, _ in lines])                     # other race
        self.assertNotIn('vo/d/m/a2.mp3', [s for s, _ in lines])                     # other class
        self.assertNotIn('vo/d/m/a6.mp3', [s for s, _ in lines])                     # never reached

    def test_pool_names_and_words(self):
        name = npc_anim.voice_pool_name('Vo\\d\\m\\Atk_DM001.mp3')
        import hashlib
        self.assertEqual(name, 'pool/a' + hashlib.sha256(b'sound/vo/d/m/atk_dm001.mp3').hexdigest()[:16] + '.wav')
        import prepare_media_assets
        self.assertEqual('sound/' + name, prepare_media_assets.sound_output('sound/vo/d/m/atk_dm001.mp3'))
        words = npc_anim.voice_words({'hit': [('vo/x.mp3', (('h', 'l', 30),)), ('vo/y.mp3', None)]})
        self.assertRegex(words, r'^!hit:[0-9a-f]{16}:hl30 !hit:[0-9a-f]{16}$')

    def test_engine_voice_rules_and_hooks(self):
        anim = (SRC / 'aw_anim.c').read_text(encoding='utf-8')
        for rule in ('case AW_VOICE_START:AW_VoiceSay(e,AW_VOICE_ATTACK_LINE,10000)',
                     'case AW_VOICE_SWING:AW_VoiceSay(e,AW_VOICE_ATTACK_LINE,1000)',
                     'case AW_VOICE_HIT:AW_VoiceSay(e,AW_VOICE_HIT_LINE,3000)',
                     'case AW_VOICE_FLEE:AW_VoiceSay(e,AW_VOICE_FLEE_LINE,10000)',
                     'aw_combat_voice=combat_voice;'):
            self.assertIn(rule, anim)
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        self.assertIn('if (distance < 750) aw_bark(self,3,0.15);', qc)
        self.assertIn('DotProduct(d,d)>750.0f*750.0f', anim)
        table = (SRC / 'pr_cmds.c').read_text(encoding='latin-1').split('builtin_t pr_builtin[] =', 1)[1].split('};', 1)[0]
        table = re.sub(r'#ifdef QUAKE2.*?#else(.*?)#endif', r'\1', table, flags=re.S)
        table = re.sub(r'/\*.*?\*/|//[^\n]*', '', table, flags=re.S)
        names = re.findall(r'\b(?:PF_\w+|SV_MoveToGoal)\b', table)
        self.assertEqual(names.index('PF_aw_bark'), int(re.search(r'aw_bark\s*=\s*#(\d+);', qc).group(1)))


class ActorCacheTests(unittest.TestCase):
    def test_standing_models_and_movers_are_counted(self):
        import tempfile
        sys.path.insert(0, str(ROOT / 'tools'))
        from chim.heap import actor_cache
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            (id1 / 'progs/a_1.mdl').write_bytes(b'x' * 1000)
            (id1 / 'progs/a_1_m.mdl').write_bytes(b'x' * 5000)
            (id1 / 'progs/a_2.mdl').write_bytes(b'x' * 2000)
            rows = [{'classname': 'aw_npc', 'model': 'progs/a_1.mdl'}, {'classname': 'aw_npc', 'model': 'progs/a_1.mdl'},
                    {'classname': 'aw_corpse', 'model': 'progs/a_2.mdl'}, {'classname': 'aw_static', 'model': 'progs/a_2.mdl'}]
            r = actor_cache(id1, rows, {'hunk': 16}, gap_bytes=8000)
        self.assertEqual(r['actor_models'], 2)
        self.assertEqual(r['standing_bytes'], 1024 + 2016)
        self.assertEqual(r['mover_bytes_at_once'], 5024)
        self.assertEqual(r['peak_bytes'], 1024 + 2016 + 5024)
        self.assertFalse(r['fits_gap'])


class BlockDodgeTests(unittest.TestCase):
    def test_block_from_the_shield_group_and_dodges_in_place(self):
        keys = dict(KEYS, **{'shield: block start': 40.0, 'shield: block hit': 40.4, 'shield: block stop': 41.0,
                             'walkleft: loop start': 50.0, 'walkleft: loop stop': 50.9,
                             'walkright: loop start': 60.0, 'walkright: loop stop': 60.9})
        kit, groups = npc_anim.plan(FakeSkeleton(keys), [['idle', 8], ['block', 5], ['dodgel', 3], ['dodger', 3]])
        block, left, right = groups[1], groups[2], groups[3]
        self.assertAlmostEqual(block['hit'], .4)
        self.assertEqual((left['base'], left['count'], right['base']), (13, 3, 16))
        self.assertEqual(left['kind'], 'once')
        self.assertEqual(tuple(kit.pose(13)('bip01')[3, :2]), (1.0, 2.0))      # in place
        text = npc_anim.layout(groups)
        self.assertIn('block:8:5:0.2000:0.400', text)
        self.assertIn('dodgel:13:3:', text)

    def test_full_profile_carries_block_and_dodge(self):
        names = [g for g, _ in npc_anim.profiles()['full']]
        self.assertEqual(names[-3:], ['block', 'dodgel', 'dodger'])


class MoverTests(unittest.TestCase):
    """Owner decision 2026-10-09: residents stand in 'react' and wear 'full' only while they move."""

    def test_split_profiles(self):
        self.assertEqual(npc_anim.split_profile('react+full'), ('react', 'full'))
        self.assertEqual(npc_anim.split_profile('full'), ('full', None))
        self.assertEqual(npc_anim.plan_profile('react+full'), npc_anim.profiles()['full'])
        with self.assertRaises(ValueError):
            npc_anim.split_profile('full+react')        # the mover must hold every standing group
        with self.assertRaises(ValueError):
            npc_anim.split_profile('react+nope')

    def groups(self):
        _, groups = npc_anim.plan(skeleton(), [['idle', 8], ['walk', 8], ['death', 5], ['attack', 4]])
        return groups

    def test_select_keeps_the_standing_groups_whole(self):
        groups = self.groups()
        out, index = npc_anim.select(groups, {'idle': 8, 'death': 5})
        self.assertEqual([g['name'] for g in out], ['idle', 'death'])
        self.assertEqual(index, list(range(8)) + [16, 17, 18, 19, 20])
        self.assertEqual(out[1]['base'], 8)

    def test_select_thins_loops_evenly_and_keeps_the_final_death_pose(self):
        groups = self.groups()
        out, index = npc_anim.select(groups, {'idle': 8, 'walk': 4, 'death': 2})
        walk, death = out[1], out[2]
        self.assertEqual(index[8:12], [8, 10, 12, 14])
        self.assertAlmostEqual(walk['step'], groups[1]['step'] * 2)    # same cycle duration
        self.assertEqual(walk['events'], [(1, 'left'), (3, 'right')])
        self.assertEqual(index[12:], [16, 20])                          # first and final pose
        self.assertEqual(death['count'], 2)

    def test_fit_meets_the_byte_budget(self):
        groups = self.groups()
        full = npc_anim.alias_bytes(25, 1440, 480, 512, 240)
        out, index = npc_anim.fit(groups, 1440, 480, 512, 240, budget=full - 1)
        self.assertLess(len(index), 25)
        self.assertLessEqual(npc_anim.alias_bytes(len(index), 1440, 480, 512, 240), full - 1)
        self.assertEqual(out[0]['count'], 8)                            # idle stays whole
        out, index = npc_anim.fit(groups, 1440, 480, 512, 240)
        self.assertEqual(len(index), 25)                                # fits: unchanged
        with self.assertRaises(ValueError):
            npc_anim.fit(groups, 1440, 480, 512, 240, budget=1000)

    def test_publish_writes_the_mover_and_names_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            record = {'model': 'progs/a_x.mdl', 'anim': {'layout': 'idle:0:8:0.3333 hit:8:3:0.3333', '_sounds': {},
                      '_mover': b'IDPO', 'mover': {'layout': 'idle:0:8:0.3333 walk:8:8:0.1250:38.50'}}}
            npc_anim.publish(id1, record)
            self.assertEqual((id1 / 'progs/a_x.anm').read_text(), 'idle:0:8:0.3333 hit:8:3:0.3333 >progs/a_x_m.mdl\n')
            self.assertEqual((id1 / 'progs/a_x_m.mdl').read_bytes(), b'IDPO')
            self.assertTrue((id1 / 'progs/a_x_m.anm').read_text().startswith('idle:0:8'))
            self.assertEqual(record['anim']['mover']['model'], 'progs/a_x_m.mdl')
            self.assertNotIn('_mover', record['anim'])

    def test_mover_names_fit_classic_ffs(self):
        self.assertLessEqual(len(npc_anim.mover_path('progs/a_0123456789ab.mdl').rsplit('/', 1)[1]), 30)

    def test_engine_wears_movers_only_while_moving(self):
        anim = (SRC / 'aw_anim.c').read_text(encoding='utf-8')
        self.assertIn('Mod_FindName(sv.model_precache[i]);', anim)       # registered by name, not loaded
        self.assertIn('Cache_Free(&m->cache)', anim)                       # memory back when it stops
        self.assertIn('AW_AnimLazy (model_precache[i]) ? Mod_FindName', (SRC / 'cl_parse.c').read_text(encoding='latin-1'))
        self.assertIn('AW_AnimSaveSwap (1);', (SRC / 'host_cmd.c').read_text(encoding='latin-1'))
        self.assertIn('AW_AnimMover(e,1);', (SRC / 'aw_companion.c').read_text(encoding='utf-8'))
        combat = (SRC / 'aw_combat.c').read_text(encoding='utf-8')
        self.assertIn('if(!layout)AW_AnimMover(e,1);', combat)
        self.assertIn('AW_AnimMover(s->e,0)', combat)


class AliasWriterTests(unittest.TestCase):
    def test_named_frames_and_limits(self):
        # Another suite module may have imported tools/mwad.py (the CLI) as 'mwad'; npc_geometry needs the
        # src/mwad package.
        loaded = sys.modules.get('mwad')
        if loaded is not None and not hasattr(loaded, '__path__'):
            for name in [n for n in sys.modules if n == 'mwad' or n.startswith('mwad.')]:
                del sys.modules[name]
        if sys.path[0] != str(ROOT / 'src'):
            sys.path.insert(0, str(ROOT / 'src'))      # before tools/ (tools/mwad.py is the CLI)
        try:
            from PIL import Image
            from npc_geometry import animated_mdl
        except ImportError as error:
            self.skipTest(str(error))
        frames = np.random.default_rng(1).random((40, 3, 3)) * 10
        skin = Image.new('P', (16, 16))
        uv = np.array([[0, 0], [15, 0], [0, 15]])
        faces = np.array([[0, 1, 2]])
        # A byte budget, not a frame count (TOOL-ALIAS-FRAMES-33): 40 light frames fit, unnamed too;
        # a budget smaller than the frames refuses.
        from npc_geometry import alias_frame_bytes, ALIAS_FRAME_BYTES, ALIAS_MAX_FRAMES
        self.assertIn(b'idle39\0', animated_mdl(frames, faces, uv, skin))
        self.assertEqual(alias_frame_bytes(40, 3), 40 * (28 + 12))
        with self.assertRaises(ValueError):
            animated_mdl(frames, faces, uv, skin, frame_bytes=alias_frame_bytes(39, 3))
        self.assertEqual(len(animated_mdl(frames, faces, uv, skin, frame_bytes=alias_frame_bytes(40, 3))),
                         len(animated_mdl(frames, faces, uv, skin)))
        self.assertEqual(ALIAS_FRAME_BYTES, alias_frame_bytes(64, 1999))     # the previous worst case
        with self.assertRaises(ValueError):
            animated_mdl(np.zeros((ALIAS_MAX_FRAMES + 1, 3, 3)), faces, uv, skin)
        heavy = np.random.default_rng(2).random((65, 1999, 3))
        with self.assertRaises(ValueError):                                  # 65 frames of a heavy model
            animated_mdl(heavy, faces, np.zeros((1999, 2)), skin)
        names = ['walk%02d' % i for i in range(40)]
        raw = animated_mdl(frames, faces, uv, skin, names=names)
        self.assertIn(b'walk39\0', raw)
        with self.assertRaises(ValueError):
            animated_mdl(frames, faces, uv, skin, names=names[:-1])
        with self.assertRaises(ValueError):
            animated_mdl(frames, faces, uv, skin, names=['x' * 16] * 40)
        self.assertEqual(animated_mdl(frames[:8], faces, uv, skin),
                         animated_mdl(frames[:8], faces, uv, skin, names=['idle%02d' % i for i in range(8)]))


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class AnimNativeTests(unittest.TestCase):
    def test_layout_groups_rate_and_events(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_anim_test.c', [SRC / 'aw_anim.c'], defines=['AW_ANIM_HOST_TEST'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class AnimSourceContractTests(unittest.TestCase):
    def test_builtin_81_is_aw_animprep_and_resident_spawn_calls_it(self):
        table = (SRC / 'pr_cmds.c').read_text(encoding='latin-1').split('builtin_t pr_builtin[] =', 1)[1].split('};', 1)[0]
        # the non-QUAKE2 build: keep the #else branch of the QUAKE2 block
        table = re.sub(r'#ifdef QUAKE2.*?#else(.*?)#endif', r'\1', table, flags=re.S)
        table = re.sub(r'/\*.*?\*/|//[^\n]*', '', table, flags=re.S)
        names = re.findall(r'\b(?:PF_\w+|SV_MoveToGoal)\b', table)
        self.assertEqual(names.index('PF_aw_npcfloor'), 80)
        qc = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        number = int(re.search(r'aw_animprep\s*=\s*#(\d+);', qc).group(1))
        self.assertEqual(names.index('PF_aw_animprep'), number)
        body = qc.split('void() aw_npc = {', 1)[1].split('};', 1)[0]
        self.assertLess(body.index('setmodel(self,self.model);'), body.index('aw_animprep(self);'))

    def test_engine_wiring(self):
        self.assertIn('aw_anim.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        self.assertIn('AW_AnimInit();', (SRC / 'aw_debug.c').read_text(encoding='utf-8'))
        companion = (SRC / 'aw_companion.c').read_text(encoding='utf-8')
        self.assertIn('AW_AnimMoveGroup(', companion)
        self.assertIn('AW_AnimSounds(', companion)
        # the previous frames stay for models without a layout (DON'T DELETE ANY METHOD)
        self.assertIn('e->v.frame=13+', companion)
        source = (SRC / 'aw_anim.c').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Z_Malloc|Cache_Alloc)\s*\(', source))
        self.assertIn('Hunk_FreeToLowMark(mark)', source)

    def test_resident_builders_use_the_kit(self):
        for name in ('prepare_area.py', 'import_town.py'):
            text = (ROOT / 'tools' / name).read_text(encoding='utf-8')
            self.assertIn('publish_anim(', text, name)
            self.assertIn('foot_class(', text, name)
        area = (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8')
        self.assertIn("elif profile_name=='idle':times,step=skeleton.idle_times(8)", area)

    def test_parser_never_stores_a_float_straight_into_a_short(self):
        # ENGINE-FLOAT-SHORT-STORE-33: the 68040 build put such stores into group 0
        source = (SRC / 'aw_anim.c').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'=\(short\)v\[', source))
        self.assertIn('int ib=(int)v[0]', source)

    def test_release_files_list_the_kit(self):
        listed = (ROOT / 'tools/release-files.json').read_text(encoding='utf-8')
        for name in ('tools/npc_anim.py', 'config/npc-anim-kit.json', 'engine/aga/src/aw_anim.c',
                     'engine/aga/src/aw_anim.h', 'tests/aga_anim_test.c', 'tests/test_npc_anim.py', 'docs/ANIMATION.md'):
            self.assertIn('"' + name + '"', listed)


if __name__ == '__main__':
    unittest.main()
