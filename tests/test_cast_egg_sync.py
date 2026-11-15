# SPDX-License-Identifier: GPL-3.0-only
"""CAST-EGG-SYNC-62: the egg shell, the orb and their sprites, the hand glow and the cast sound start on the frame the
cast animation starts, and the look's bolt, touch or self hit on the frame the spell leaves (self, touch, target,
summon). The frame rule is host-built (aga_cast_sync_test.c); the engine wiring is checked in the source. The egg is
still the default shell, and the shipped game turns the look on."""
from pathlib import Path
import os
import shutil
import unittest
import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


class CastEggSync(unittest.TestCase):
    compile_run = native.NativeSourceTests.compile_run

    @unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
    @unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
    def test_frame_numbers_match(self):
        self.compile_run('aga_cast_sync_test.c', [SRC / 'aw_magic_rules.c'],
                         cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_the_look_starts_with_the_animation(self):
        cast, magic = code('aw_cast.c'), code('aw_magic.c')
        # at the press: the hands' cast and the held looks per range, on the same call
        self.assertIn('delay=AW_HandsCastStart()?AW_HandCastReleaseNow(0):0;', cast)
        self.assertIn('looks[r]=ranges&(1<<r)?AW_MagicCastLookStart(0,first_mgef(r),r,0):0;', cast)
        # at the release: the looks leave (1), fail (0, one failure sound) or are dropped (-1)
        self.assertIn('if(look_held)looks_release(1);', cast)
        self.assertIn('if(look_held)looks_release(0);else AW_MagicCastLook(', cast)
        self.assertIn('{pending=0;looks_release(-1);}', cast)
        self.assertIn('memset(looks,0,sizeof(looks));', cast)   # New Game
        # the look: its animation on the start call, its first-frame phases by the one rule, held until released
        self.assertIn('animate(&casts[slot]);casts[slot].f_anim=host_framecount;', magic)
        self.assertIn('if(held)casts[slot].release=AW_MAGIC_HELD_RELEASE;', magic)
        self.assertIn('c->release=AW_MagicCastRelease((float)(cl.time-c->start));', magic)
        self.assertIn('if(AW_MagicStartDue(c->begun,t1)){\n        c->begun=1;sound_at(c->fx,AW_MAGIC_CAST,c->eye);', magic)
        self.assertIn('if(AW_MagicStartDue(c->fail_done,t1)){', magic)
        self.assertIn('if(c->release>=AW_MAGIC_HELD_RELEASE && t1>AW_MAGIC_HELD_MAX){c->used=0;return;}', magic)
        self.assertNotIn('if(t0<=0)sound_at(c->fx,AW_MAGIC_CAST,c->eye);', magic)

    def test_egg_is_the_default_and_the_game_shows_the_look(self):
        magic = code('aw_magic.c')
        # aw_magic_orb: ones = orb type 2 (bubble + swirl), tens = shape 0 (the egg)
        self.assertIn('static cvar_t aw_magic_orb={"aw_magic_orb","2",true};', magic)
        self.assertIn('{"egg","sphere"}', magic)
        self.assertIn('enum {AW_MAGIC_SHAPE_EGG,AW_MAGIC_SHAPE_SPHERE,AW_MAGIC_SHAPES};',
                      (SRC / 'aw_magic.h').read_text(encoding='utf-8'))
        # the setting itself stays 0 (nothing loaded without it); the shipped game's defaults turn the look on
        self.assertIn('{"aw_magic_fx","0",true}', magic)
        cfg = (ROOT / 'config/game.cfg').read_text(encoding='utf-8').splitlines()
        self.assertIn('aw_magic_fx 1', cfg)


if __name__ == '__main__':
    unittest.main()
