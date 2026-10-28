# SPDX-License-Identifier: GPL-3.0-only
"""Magic effects as Quake sprites and particles (docs/MAGIC_EFFECTS.md): the image step's import
(tools/prepare_magic.py) on synthetic data, the engine's table rules (aw_magic_rules.c) on the same table, and the
engine wiring (aw_magic.c: default off, dbg cast, after the beams)."""
import math
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import prepare_magic as M  # noqa: E402

UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
RAMP = [[255 - 10 * i, 120, 40] for i in range(8)]


def emitter(**changes):
    e = {'count': 20, 'size': 4.5, 'life': 0.5, 'life_rand': 0.1, 'speed': 3.75, 'speed_rand': 1, 'axis': [0, 0, 1],
         'spread': 0.5, 'gravity': 0, 'start': 0, 'stop': 0.5, 'jitter': [1, 1, 2], 'ramp': RAMP}
    e.update(changes)
    return e


def sample_effects():
    phase = {'length': 1.0, 'sprite': 'progs/awmx_00.spr', 'size': 9.4, 'radius': 0, 'sound': 'aw/magic/destruction_cast.wav',
             'emitters': [emitter(), emitter(count=8, gravity=1)]}
    return [{'name': 'fire', 'mgef': 14, 'school': 'destruction', 'rgb': [253, 136, 66],
             'phases': {'hand': dict(phase, sprite=None, sound=None, emitters=[emitter()]), 'cast': phase,
                        'bolt': dict(phase, sprite='progs/awmx_01.spr', sound=None, emitters=[emitter(count=30)]),
                        'area': dict(phase, radius=10.5, emitters=[]),
                        'fail': {'length': 1.0, 'sprite': None, 'size': 0, 'radius': 0,
                                 'sound': 'aw/magic/spell_failure_destruc.wav', 'emitters': []}}},
            {'name': 'heal', 'mgef': 75, 'school': 'restoration', 'rgb': [213, 234, 249],
             'phases': {'cast': dict(phase, sprite=None, emitters=[])}}]


class TableTests(unittest.TestCase):
    def test_table_round_trip_and_refusals(self):
        text = M.table_text(250, sample_effects())
        self.assertTrue(text.startswith('AWMG1 250\n'))
        effects = M.read_table(text)
        self.assertEqual(effects['fire']['phases']['cast']['emitters'], 2)
        self.assertEqual(effects['fire']['phases']['hand']['sprite'], '-')
        self.assertIn('ph fire fail 1 - 0 0 aw/magic/spell_failure_destruc.wav', text)
        self.assertEqual(M.PHASE_ORDER[-2:], ('fail', 'bubble'))
        self.assertIn('fx fire 14 destruction 253 136 66 0\n', text)        # FLAGS (the record's ContinuousVfx etc.)
        self.assertEqual(len(M.read_table(text.replace('66 0\n', '66\n', 1))), 2)   # a 7-field fx line still reads
        self.assertIn('em fire bolt 30 4.5 0.5 0.1 3.75 1 0 0 1 0.5 0 0 0.5 1 1 2 255 120 40', text)
        bad = sample_effects()
        del bad[1]['phases']['cast']
        with self.assertRaises(ValueError):
            M.read_table(M.table_text(250, bad))
        with self.assertRaises(ValueError):
            M.read_table(text.replace('AWMG1', 'AWMG2'))
        with self.assertRaises(ValueError):
            M.emitter_line('fire', 'cast', emitter(ramp=RAMP[:3]))

    def test_numbers_are_plain_decimals(self):
        self.assertEqual([M.number(x) for x in (1.0, 0.5, -0.0, 12.34567, 1e-6)], ['1', '0.5', '0', '12.3457', '0'])


class MeshRuleTests(unittest.TestCase):
    def test_particle_texture_replaces_only_the_root_texture(self):
        # OpenMW's rule (nifloader.cpp, util.cpp): the effect's texture only where the root names it first
        self.assertEqual(M.effective_texture('vfx_firelight.tga', True, 'vfx_icestar.tga'), 'vfx_icestar.tga')
        self.assertEqual(M.effective_texture('vfx_firelight.tga', False, 'vfx_icestar.tga'), 'vfx_firelight.tga')
        self.assertEqual(M.effective_texture('vfx_firelight.tga', True, None), 'vfx_firelight.tga')

    def test_alpha_modes(self):
        self.assertTrue(M.additive(13))       # blend, source alpha, destination one
        self.assertFalse(M.additive(237))     # ordinary see-through
        self.assertFalse(M.additive(None))

    def test_axis_and_cone(self):
        axis, spread = M.axis_spread(0, 0.5, 0, 0)
        self.assertEqual([round(a, 4) for a in axis], [0, 0, 1])
        self.assertAlmostEqual(spread, math.tan(0.5), places=3)
        axis, spread = M.axis_spread(math.pi / 2, 0.1, 0, 0)
        self.assertAlmostEqual(axis[0], 1, places=4)
        self.assertEqual(M.axis_spread(math.pi / 2, 0.1, 0, math.pi)[1], 50.0)   # a full turn: every direction
        self.assertEqual(M.axis_spread(0, 1.6, 0, 0)[1], 50.0)

    def test_caps_share_the_phase_budget(self):
        self.assertEqual(M.caps([135, 135], 20), [10, 10])
        self.assertEqual(M.caps([100, 1], 40), [40, 1])
        self.assertEqual(M.caps([5, 3], 40), [5, 3])
        self.assertEqual(M.caps([0, 0], 40), [0, 0])

    def test_sprite_stands_for_the_particle_cloud(self):
        # one sprite for the many particles: the cloud's width (size + start box + travel), within the phase's range
        e = {'size': 10, 'jitter': [4, 4, 8], 'speed': 20, 'life': 1.0}
        self.assertEqual(M.cloud_size([e]), 10 + 16 + 20)
        self.assertEqual(M.sprite_size('cast', [e], []), round(46 * M.SCALE, 2))
        self.assertEqual(M.sprite_size('cast', [dict(e, size=1, jitter=[0, 0, 0], speed=0)], []), 8)   # the minimum
        self.assertEqual(M.sprite_size('hit', [dict(e, speed=2000)], []), 48)                           # the maximum

    def test_sounds_have_short_names(self):
        self.assertEqual(M.sound_file('destruction cast'), 'sound/aw/magic/destruction_cast.wav')
        self.assertLessEqual(len(Path(M.sound_file('a' * 80)).name), 30)
        self.assertEqual(M.sound_file('destruction bolt', loop=True), 'sound/aw/magic/loop_destruction_bolt.wav')
        for loop in (False, True):   # the engine's path field (sound/ dropped) holds under 40 characters
            self.assertLess(len(M.sound_file('a' * 80, loop)) - len('sound/'), 40)


class SoundRuleTests(unittest.TestCase):
    """The magic sounds per phase (rules from OpenMW mwworld/store.cpp, mwmechanics/spellcasting.cpp,
    mwworld/projectilemanager.cpp): the effect's own, else the school's; the failure always the school's."""

    def test_own_school_and_failure(self):
        row = {'school': 2, 'CSND': 'shock cast', 'BSND': '', 'HSND': 'shock hit'}
        self.assertEqual(M.phase_sound(row, 'cast', 'destruction'), ('shock cast', True))
        self.assertEqual(M.phase_sound(row, 'bolt', 'destruction'), ('destruction bolt', False))
        self.assertEqual(M.phase_sound(row, 'area', 'destruction'), ('destruction area', False))
        self.assertEqual(M.phase_sound(row, 'fail', 'destruction'), ('Spell Failure Destruction', False))
        self.assertEqual(M.phase_sound(row, 'hand', 'destruction'), (None, False))

    def test_sound_map_every_effect(self):
        mgef = {15: {'school': 2, 'CSND': 'shock cast'}, 75: {'school': 5}}
        table = M.sound_map(mgef, {'shock cast': 'Fx\\magic\\shokC.wav', 'restoration hit': 'Fx\\magic\\restH.wav'})
        self.assertEqual(table['15']['phases']['cast'], {'record': 'shock cast', 'own': True, 'file': 'Fx\\magic\\shokC.wav'})
        self.assertEqual(table['75']['phases']['hit']['file'], 'Fx\\magic\\restH.wav')
        self.assertEqual(table['75']['phases']['fail']['record'], 'Spell Failure Restoration')
        self.assertIsNone(table['15']['phases']['bolt']['file'])

    def test_bolt_loop_point_for_quakes_loader(self):
        import io
        import wave
        for frames in (b'\x80\x90\xa0', b'\x80\x90'):   # odd and even data lengths (RIFF padding)
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(1); w.setframerate(11025); w.writeframes(frames)
            raw = buffer.getvalue()
            self.assertEqual(M.loop_start(raw), -1)
            looped = M.with_loop_point(raw)
            self.assertEqual(M.loop_start(looped), 0)
            self.assertEqual(struct.unpack_from('<I', looped, 4)[0], len(looped) - 8)
            with wave.open(io.BytesIO(looped)) as w:
                self.assertEqual(w.readframes(10), frames)
        with self.assertRaises(ValueError):
            M.with_loop_point(b'not a wav file')


class TextureTests(unittest.TestCase):
    def glow(self):
        y, x = np.mgrid[0:64, 0:64]
        r = np.sqrt((x - 32) ** 2 + (y - 32) ** 2)
        strength = np.clip(1 - r / 30, 0, 1)
        rgba = np.zeros((64, 64, 4), np.uint8)
        rgba[..., 0] = 220 * strength
        rgba[..., 1] = 100 * strength
        rgba[..., 3] = 255 * strength
        return rgba

    def palette(self):
        return bytes(min(255, i) for i in range(256) for _ in range(3))  # a grey ramp

    def test_bubble_is_a_see_through_sphere_strongest_at_its_rim(self):
        raw = M.bubble_bytes(self.glow(), [128, 0, 128], self.palette())
        self.assertEqual(M.read_sprite(raw), (4, 32, 32))
        full = raw[36 + 20:36 + 20 + 1024]
        shown = lambda cells: sum(1 for i in cells if full[i] != 255)   # noqa: E731
        middle = [y * 32 + x for y in range(12, 20) for x in range(12, 20)]
        rim = [y * 32 + x for y in range(32) for x in range(32) if 13.5 < ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** .5 < 15.5]
        self.assertGreater(shown(rim) / len(rim), 2 * shown(middle) / len(middle))
        self.assertEqual(full[0], 255)                                 # outside the sphere: see-through

    def test_hit_model_baked_from_the_front(self):
        # a square shell 64 units wide standing on z 0..64, white texture: the bake covers the middle, centre z 32
        geo = [{'texture': 't', 'root_first': False, 'alpha': 13,
                'verts': np.array([[-32, 0, 0], [32, 0, 0], [32, 0, 64], [-32, 0, 64]], dtype=float),
                'uv': np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float), 'tris': np.array([[0, 1, 2], [0, 2, 3]])}]
        tex = np.full((8, 8, 4), 255, np.uint8)
        colour, strength, side, zc = M.shell_image(geo, {'t': tex})
        self.assertAlmostEqual(zc, 32)
        self.assertAlmostEqual(side, 64 * 1.08, places=3)
        self.assertGreater(strength[32, 32], 0.9)
        self.assertEqual(strength[0, 0], 0)
        self.assertIsNone(M.shell_image([], {}))
        raw = M.bubble_bytes(self.glow(), [128, 0, 128], self.palette(), shell=(colour, strength, side, zc))
        self.assertEqual(M.read_sprite(raw), (4, 32, 32))

    def test_ramp_brightest_first(self):
        colours = M.ramp(self.glow(), glow=True)
        self.assertEqual(len(colours), 8)
        self.assertGreaterEqual(colours[0][0], colours[-1][0])
        self.assertGreater(colours[0][0], colours[0][2])              # the texture's own hue, not grey

    def test_sprite_frames_fade_and_keep_255_see_through(self):
        raw = M.sprite_bytes(self.glow(), self.palette(), glow=True)
        self.assertEqual(M.read_sprite(raw), (4, 32, 32))
        frames = [raw[36 + 20 + i * (20 + 1024):36 + 20 + i * (20 + 1024) + 1024] for i in range(4)]
        shown = [sum(1 for b in f if b != 255) for f in frames]
        self.assertTrue(shown[0] > shown[1] > shown[2] > shown[3] > 0, shown)
        self.assertEqual(frames[0][0], 255)                           # the corner is see-through
        with self.assertRaises(ValueError):
            M.read_sprite(raw[:-1])


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EngineRuleTests(unittest.TestCase):
    def test_rules_and_the_builders_table(self):
        import test_aga_native_source as native
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'magic.awm'
            effects = sample_effects()
            effects[0]['phases']['cast']['emitters'] = [emitter(), emitter(count=8)]
            path.write_text(M.table_text(250, effects), encoding='ascii', newline='\n')
            native.NativeSourceTests().compile_run('aga_magic_rules_test.c', [SRC / 'aw_magic_rules.c'], cflags=UBSAN,
                                                   arguments=(str(path),))


class EngineWiringTests(unittest.TestCase):
    def code(self, name):
        return (SRC / name).read_text(encoding='utf-8')

    def test_default_off_dbg_cast_and_quake_machinery(self):
        magic = self.code('aw_magic.c')
        self.assertIn('{"aw_magic_fx","0",true}', magic)                   # default off (A/B: off is no work)
        self.assertIn('if(!aw_magic_fx.value){', magic)
        self.assertIn('Cmd_AddCommand("aw_magicfx",command);', magic)
        self.assertIn('CL_NewTempEntity()', magic)                          # sprites as temporary entities
        self.assertIn('free_particles', magic)                              # Quake's particle pool
        self.assertIn('if((int)aw_magic_fx.value<2)return;', magic)         # lights only with 2
        self.assertIn('S_MoveSound(SOUND_ENT,slot+1,c->bolt);', magic)      # the bolt's loop follows the bolt
        self.assertGreaterEqual(magic.count('bolt_sound_stop('), 4)         # ...and stops where it lands
        self.assertIn('sound_at(c->fx,AW_MAGIC_FAIL,c->eye);', magic)       # the failed cast: its sound only
        self.assertIn('void S_MoveSound(int entnum, int entchannel, vec3_t origin)', self.code('snd_dma.c'))
        # the caster's spellcast group: the spell leaves on its release key (aw_animkit.c AW_AnimKitCast)
        self.assertIn('float r=e?AW_AnimKitCast(e,variant[c->mode]):-1;', magic)
        self.assertIn('t1>=c->release', magic)
        kit = self.code('aw_animkit.c')
        self.assertIn('sprintf(key,"%s release",variant);rel=AW_SkelKeyFrame(t,g,key);', kit)
        self.assertEqual(kit.count('float AW_AnimKitCast(edict_t *e,const char *variant)'), 2)  # and its compiled-out stub
        # the orb types to compare (0 the first prototype kept), around the caster and the target; the shared fx API
        self.assertIn('static int orb_type=2;', magic)
        self.assertIn('orb_at(c,at,c->height,t1,orb,0);', magic)
        # the hit shell follows its target for the spell's duration (ContinuousVfx, dbg cast ... dur S)
        self.assertIn('orb_at(c,at3,c->hit_height,la1,len,c->duration>0);', magic)
        self.assertIn('(table->fx[fx].flags&AW_MAGIC_CONTINUOUS_VFX)?HOLD_DEFAULT:0', magic)
        self.assertIn('int AW_FxParticles(const float at[3],int count', magic)
        self.assertIn('int AW_FxSprite(struct model_s *model,const float at[3],float world_size,int frame) {', magic)
        self.assertIn('AW_MagicInit();', self.code('aw_debug.c'))
        main = self.code('cl_main.c')
        self.assertLess(main.index('CL_UpdateTEnts ();'), main.index('AW_MagicUpdate ();'))
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_magic_rules.c aw_magic.c', makefile)
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('PLAYTESTING|cast|aw_magicfx|', catalogue)
        self.assertIn('VIDEO|magicfx|aw_magic_fx|', catalogue)

    def test_image_step_writes_the_table(self):
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn('from prepare_magic import prepare as prepare_magic', build)
        self.assertIn("magic-effects.json", build)


if __name__ == '__main__':
    unittest.main()
