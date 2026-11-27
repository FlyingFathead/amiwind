# SPDX-License-Identifier: GPL-3.0-only
"""A creature collides only up to its drawn body (SOL-SEA-INVISIBLE-BLOCKER-68, ACTOR-CLIP-ABOVE-DRAWN-BODY-69).

Every actor stood in the person box (world.qc aw_npc_floor: 0 .. 33.25), creatures included, so a horker swimming wholly
under the water surface in Solstheim's sea had 11 units of collision above the surface and stopped a player walking on
the water, with nothing drawn there. The engine's collision, walk and the rule run natively over a synthetic world with
the horker's measured rest frame (tests/aga_actor_clip_test.c): with aw_actor_clip 0 (the method before v0.0.69) the
walker is stopped, with 1 (the default) he passes over it, meets it on land where it is drawn, and never steps onto a
low creature. The source contracts: every new box asks the rule after it is set, world.c reads the top in all three
body tests, the step never lands on a body, the default is written into the game's settings, the console entry
exists."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class ActorClipNativeTests(unittest.TestCase):
    def test_the_walker_on_the_water_passes_over_the_swimming_horker(self):
        native.NativeSourceTests().compile_run(
            'aga_actor_clip_test.c', [SRC / 'world.c', SRC / 'sv_phys.c', SRC / 'aw_walk.c', SRC / 'mathlib.c',
                                      SRC / 'aw_actor_clip.c'], cflags=UBSAN)


class ActorClipSourceTests(unittest.TestCase):
    def test_every_new_box_asks_the_rule_after_it_is_set(self):
        # pr_cmds.c SetMinMaxSize (the setsize builtin, setmodel's box and the arena's): the rule reads the new box;
        # world.qc stays as it is (it is in the CHIM world's stage key)
        size = code('pr_cmds.c')
        size = size[size.index('void SetMinMaxSize (edict_t *e, float *min, float *max, qboolean rotate)'):]
        size = size[:size.index('\n}\n')]
        self.assertLess(size.index('VectorCopy (rmax, e->v.maxs);'), size.index('AW_ActorClipSet (e);'))
        self.assertLess(size.index('AW_ActorClipSet (e);'), size.index('SV_LinkEdict (e, false);'))
        self.assertNotIn('aw_actorclip', (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8'))
        self.assertIn('SetMinMaxSize(e,low,high,false);', code('aw_arena.c'))

    def test_every_body_test_reads_the_collision_top(self):
        world = code('world.c')
        self.assertIn('hullmaxs[2] = ClipTop (ent) - mins[2];', world)
        self.assertIn('touch->v.origin[i] + (i == 2 ? ClipTop (touch) : touch->v.maxs[i])', world)
        self.assertIn('e->v.origin[k] + (k == 2 ? ClipTop (e) : e->v.maxs[k])', world)
        self.assertIn('aw_actor_clip_top = AW_ActorClipTop;', code('aw_actor_clip.c'))
        self.assertIn('AW_BoundsInit();AW_ActorClipInit();', code('aw_debug.c'))
        self.assertIn('aw_walk.c aw_actor_clip.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_a_step_never_lands_on_a_body(self):
        walk = code('sv_phys.c')
        walk = walk[walk.index('void SV_WalkMove (edict_t *ent)'):]
        guard = walk.index('downtrace.ent->v.solid == SOLID_SLIDEBOX')
        self.assertLess(walk.index('downtrace = SV_PushEntity (ent, downmove);'), guard)
        self.assertLess(guard, walk.index('if (downtrace.plane.normal[2] >= AW_WALKABLE_Z)'))

    def test_the_default_is_in_the_game_settings_and_the_console(self):
        import build_aga
        self.assertIn(b'\naw_actor_clip 1\n', build_aga.ACTOR_LOGIC_LINES)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        # the console entry routes onto the setting itself: typed bare it turns it the other way (test_console_toggles)
        self.assertIn('DIAGNOSTICS|actorclip|aw_actor_clip|[on/off, true/false or 1/0; no argument toggles]', catalogue)
        self.assertIn('Cvar_RegisterVariable (&aw_actor_clip);', code('aw_actor_clip.c'))
        self.assertIn('`dbg actorclip`', (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
