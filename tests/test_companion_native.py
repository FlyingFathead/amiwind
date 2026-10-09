# SPDX-License-Identifier: GPL-3.0-only
"""NPC companion test (dbg companion): the budgeted navigation core, the
engine glue with a synthetic server, and the source contracts that keep it
cheap, unsaved and wired in."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def text(name):
    return (SRC / name).read_text(encoding='utf-8')


def code(name):
    """Source without comments."""
    return re.sub(r'/\*.*?\*/', '', text(name), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class CompanionNativeTests(unittest.TestCase):
    def test_ping_flood_budget_speed_and_state_size(self):
        native.NativeSourceTests().compile_run('aga_npcpath_test.c', [SRC / 'aw_npcpath.c'], cflags=UBSAN)

    def test_commands_pick_mode_follow_release_and_saves(self):
        native.NativeSourceTests().compile_run(
            'aga_companion_test.c', [SRC / n for n in ('aw_companion.c', 'aw_npcpath.c', 'mathlib.c')],
            cflags=UBSAN)


class CompanionSourceContractTests(unittest.TestCase):
    def test_no_allocation_and_integer_navigation(self):
        for name in ('aw_npcpath.c', 'aw_companion.c'):
            with self.subTest(name=name):
                self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', code(name)))
        self.assertIsNone(re.search(r'\b(float|double)\b', code('aw_npcpath.c') + code('aw_npcpath.h')))
        self.assertIsNone(re.search(r'\b(sqrt|sin|cos|atan2|Q_atan2)\s*\(', code('aw_companion.c')))
        header = code('aw_npcpath.h')
        self.assertIn('#define AW_PATH_TRACES 2', header)

    def test_spawned_companion_is_not_a_resident_and_not_saved(self):
        companion = code('aw_companion.c')
        self.assertIn('companion_class[]="aw_companion"', companion)
        self.assertNotIn('"aw_npc";', companion)
        host = code('host_cmd.c')
        self.assertIn('AW_CompanionSkipSave (EDICT_NUM(i))', host)
        self.assertLess(host.index('AW_CompanionSaveSwap (1)'), host.index('AW_CompanionSkipSave (EDICT_NUM(i))'))
        self.assertIn('AW_CompanionSaveSwap (0)', host)
        self.assertIn('aw_companion_home(e,a->position,a->angles)', code('aw_save.c'))

    def test_think_runs_from_server_physics_and_hooks_are_wired(self):
        physics = code('sv_phys.c')
        loop = physics.index('SV_Physics: bad movetype')
        self.assertGreater(physics.index('AW_CompanionPhysics ()'), loop)
        self.assertIn('aw_companion_crosshair (x, y)', code('view.c'))
        self.assertIn('if (crosshair.value)', code('view.c'))
        self.assertIn('bits = aw_companion_buttons (bits)', code('cl_input.c'))
        self.assertIn('if(aw_companion_scene)aw_companion_scene(p);', code('aw_scene.c'))
        self.assertIn('AW_CompanionInit();', code('aw_debug.c'))
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_npcpath.c aw_companion.c', makefile)

    def test_actor_steps_leave_the_chim_ring_to_the_player(self):
        # CHIM-ACTOR-RING-33: an actor stepping first in a frame centred the ring on itself.
        walk = code('aw_walk.c')
        body = walk[walk.index('qboolean AW_ActorStep'):]
        self.assertLess(body.index('aw_chim_player=NULL;'), body.index('AW_WalkPlayer(p);'))
        self.assertLess(body.index('AW_WalkPlayer(p);'), body.index('aw_chim_player=ring;'))

    def test_catalogue_routes_and_docs(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        routes = {line.split('|')[1]: line.split('|')[2] for line in catalogue.splitlines()
                  if line.count('|') == 3 and not line.startswith('#')}
        self.assertEqual(routes['companion'], 'aw_companion')
        self.assertEqual(routes['companiontest'], 'aw_companiontest')
        self.assertEqual(routes['pickcompanion'], 'aw_pickcompanion')
        self.assertEqual(routes['choosecompanion'], 'aw_pickcompanion')
        companion = code('aw_companion.c')
        for handler in ('aw_companion', 'aw_companiontest', 'aw_pickcompanion'):
            self.assertIn('Cmd_AddCommand("%s",' % handler, companion)
        docs = (ROOT / 'docs' / 'DEBUG_OVERLAYS.md').read_text(encoding='utf-8')
        section = docs[docs.index('## NPC companion test'):]
        for words in ('dbg companion pick', 'dbg companion choose', 'dbg companion test', 'dbg companion off',
                      'dbg companion distance', 'dbg companion mimic speed', 'dbg companiontest on/off',
                      'dbg pickcompanion', 'dbg choosecompanion', '48..512', 'default 96'):
            self.assertIn(words, section)


if __name__ == '__main__':
    unittest.main()
