# SPDX-License-Identifier: GPL-3.0-only
"""Noclip switched off where the box touches the world lifts the player clear there (JOURNEY-DOCK-NOCLIP-UNSTUCK-RACE-68).

In the opening journey's first step on the v0.0.68-dev6 image, the player flies with noclip from the town start to the
prison ship's plank end and switches it off there; in most runs tonight the player was then found by the town start,
the end-of-opening boxes came up and the journey stopped. The engine's stuck check (sv_phys.c SV_CheckStuck) puts a
box the world test finds in solid back at ent->v.oldorigin, which only that check keeps, and only while walking: during
noclip it still held the spot before the flight. Noclip's own test (host_cmd.c Host_Noclip_f, the other bodies too)
let it go off with the box touching the rising plank, and the next frame threw the player back there. Now noclip going
off keeps the spot it goes off at, so the check lifts the box clear where it stands.

The behaviour runs natively with the two engine functions cut out of host_cmd.c and sv_phys.c (files too large to
link alone) into a slice that tests/aga_noclip_unstuck_test.c includes. On the source before the fix the check throws
the player back by the town start. AMIWIND_RUNTIME_SOURCE selects another engine tree for that comparison."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga')))
SRC = ENGINE / 'src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


def function(text, head):
    """The C definition starting at HEAD, to its closing brace at column 0."""
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


def line(text, head):
    at = text.index('\n' + head) + 1
    return text[at:text.index('\n', at) + 1]


def noclip_slice(host, phys):
    return ('/* cut from host_cmd.c and sv_phys.c by tests/test_noclip_unstuck.py */\n'
            + function(host, 'void Host_Noclip_f (void)\n{')
            + line(phys, 'unsigned long aw_stuck_searches,aw_stuck_tests,aw_stuck_failed;')
            + function(phys, 'void SV_CheckStuck (edict_t *ent)\n{'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class NoclipUnstuckNativeTests(unittest.TestCase):
    def test_noclip_off_touching_the_world_lifts_the_player_where_it_stands(self):
        """From the town start, noclip on, the flight to the plank end, noclip off there with the box touching the
        plank: the next frame's stuck check lifts the player clear at the plank end, never back by the town start; and
        over free floor nothing moves."""
        host = (SRC / 'host_cmd.c').read_text(encoding='utf-8', errors='replace')
        phys = (SRC / 'sv_phys.c').read_text(encoding='utf-8', errors='replace')
        with tempfile.TemporaryDirectory(prefix='amiwind-noclip-') as tmp:
            tmp = Path(tmp)
            native.tree_project_version().generate_native(ROOT / 'VERSION', tmp)
            (tmp / 'noclip_slice.c').write_text(noclip_slice(host, phys), encoding='utf-8')
            exe = tmp / 'check'
            cmd = [COMPILER, '-std=gnu89', '-O1', '-g', '-Wall', '-Wno-unused-function', '-Wno-unused-variable',
                   '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-include',
                   str(ROOT / 'tests/aga_test_files.h'), '-I' + str(tmp), '-I' + str(SRC),
                   str(ROOT / 'tests/aga_noclip_unstuck_test.c'), '-lm', '-o', str(exe)]
            built = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(exe)], cwd=tmp, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('ok: lifted clear where noclip went off', run.stdout)
        self.assertIn('PASS:', run.stdout)


class NoclipUnstuckWiringTests(unittest.TestCase):
    def test_noclip_off_keeps_its_spot_after_the_solid_test(self):
        noclip = function(code('host_cmd.c'), 'void Host_Noclip_f (void)\n{')
        off = noclip[noclip.index('if(SV_TestEntityPosition(sv_player))'):]
        self.assertLess(off.index('return;'), off.index('VectorCopy(sv_player->v.origin,sv_player->v.oldorigin);'))
        self.assertLess(off.index('VectorCopy(sv_player->v.origin,sv_player->v.oldorigin);'),
                        off.index('sv_player->v.movetype = MOVETYPE_WALK;'))

    def test_the_stuck_check_falls_back_to_oldorigin(self):
        check = function(code('sv_phys.c'), 'void SV_CheckStuck (edict_t *ent)\n{')
        self.assertIn('VectorCopy (ent->v.oldorigin, ent->v.origin);', check)


if __name__ == '__main__':
    unittest.main()
