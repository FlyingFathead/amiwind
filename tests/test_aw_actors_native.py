# SPDX-License-Identifier: GPL-3.0-only
"""The type 1 window's actors (engine aw_actors.c, EXPERIMENTAL, "chim crossing 1"), compiled natively with small
stubs (tests/aga_actors_test.c): the spawn queue and its per-tick budget, the warm step's order (warm 0 and 1),
the client lists keeping mover models lazy, actor-table queue entries (placement, id and instance scale from the
record) and the levelled roll (the same picks for the same seed, kept for a later join). The frame maps and the
actor table are real files: the table is built by the builder (tools/chim/actors.py) from the synthetic master of
tests/test_chim_levelled.py with one instance scale. Synthetic data only.
"""
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'

ACTORS = [  # (model, origin, ref, voice): the nearest to the player (at 0 0) first when spawned one per tick
    ('progs/a_far_mover.mdl', (900, 0, 0), 503, 'npc/far.wav'),
    ('progs/a_near.mdl', (100, 0, 0), 501, 'npc/near.wav'),
    ('progs/a_mid.mdl', (400, 0, 0), 502, 'npc/mid.wav'),
]
SCALED = {14: 1.5}  # the crab reference of test_chim_levelled's master


def frame_map(actors):
    text = '{\n"classname" "worldspawn"\n}\n{\n"classname" "light"\n"origin" "0 0 64"\n}\n'
    for model, origin, ref, voice in actors:
        text += ('{\n"classname" "aw_npc"\n"model" "%s"\n"origin" "%d %d %d"\n"aw_ref" "%d"\n"aw_voice" "%s"\n}\n'
                 % (model, *origin, ref, voice))
    body = text.encode('latin1')
    return b'CHIM' + struct.pack('<ii', 12, len(body)) + body


def actor_table():
    from chim import actors as A
    import test_chim_levelled as L
    data, _ = A.build_table(A.exterior_actors(L.MASTER), {}, A.levelled_lists(L.MASTER), A.creature_ids(L.MASTER),
                            L.LIBRARY, scales=SCALED)
    return A, data


@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class ActorsNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_aga_native_source import tree_project_version
        cls.A, data = actor_table()
        cls.lists = cls.A.read_lists(data)
        cls.head, cls.cells, cls.records, cls.bases, _ = cls.A.read_table(data)
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-actors-c-')
        tmp = Path(cls.tmp.name)
        (tmp / 'chim-actors.cca').write_bytes(data)
        (tmp / 'frame.chim').write_bytes(frame_map(ACTORS))
        (tmp / 'frame2.chim').write_bytes(frame_map([(m, o, r + 100, v) for m, o, r, v in ACTORS]))
        tree_project_version().generate_native(ROOT / 'VERSION', tmp)
        cls.exe = tmp / 'check'
        cmd = ['cc', '-std=gnu89', '-O1', '-Wall', '-Wno-unused', '-fsanitize=undefined', '-fno-sanitize-recover=all',
               '-include', str(ROOT / 'tests/aga_test_files.h'), '-I' + str(tmp), '-I' + str(SRC),
               str(ROOT / 'tests/aga_actors_test.c'), str(SRC / 'aw_actors.c'), str(SRC / 'chim/chim_actor_table.c'),
               str(SRC / 'chim/chim_format.c'), str(SRC / 'mathlib.c'), str(SRC / 'aw_format.c'),
               str(ROOT / 'tests/aga_hook_stubs.c'), '-lm', '-o', str(cls.exe)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, mode, seed=0):
        tmp = Path(self.tmp.name)
        result = subprocess.run([str(self.exe), mode, str(tmp / 'chim-actors.cca'), str(tmp / 'frame.chim'), str(seed),
                                 str(tmp / 'frame2.chim')], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_queue_and_budget(self):
        self.assertIn('queue and budget passed', self.run_check('queue'))

    def test_a_disabled_actor_is_not_spawned(self):
        # v0.0.51 object state: a script's Disable keeps the window from spawning it; Enable lets the next join do it
        self.assertIn('disabled actor passed', self.run_check('disabled'))

    def test_warm_order(self):
        out = self.run_check('warm')
        self.assertIn('warm 0 order passed', out)
        self.assertIn('warm 1 order passed', out)

    def test_client_lists_keep_movers_lazy(self):
        self.assertIn('lazy mover models passed', self.run_check('lazy'))

    def test_change_list_survives_a_save(self):
        # the save's export and a load's import (aw_save_changes_export/import): a killed actor stays dead, a moved
        # one stands where it was left
        self.assertIn('save round trip passed', self.run_check('save'))

    def test_home_frame_keeps_its_own_actors(self):
        # CHIM-ACTORS-TOWN-RETURN-EMPTY-47: a town frame's residents beside its own cell stay while the frame is held
        self.assertIn('home frame actors passed', self.run_check('home'))

    def test_table_entries_take_the_record(self):
        out = [l.split() for l in self.run_check('table').splitlines() if l.startswith('table ref ')]
        got = {int(l[2]): l for l in out}
        cell = next(c for c in self.cells if tuple(c[0]) == (0, 0))
        first, count = cell[1], cell[2]
        crab = next(r for r in self.records[first:first + count] if r['key'] == 14)
        line = got[14]
        self.assertAlmostEqual(float(line[4]), crab['origin'][0] + 2048, places=2)
        self.assertAlmostEqual(float(line[5]), crab['origin'][1], places=2)
        self.assertAlmostEqual(float(line[6]), crab['origin'][2], places=2)
        self.assertAlmostEqual(float(line[8]), crab['yaw'], places=2)
        self.assertEqual(line[10], 'progs/c_crab.mdl')
        self.assertAlmostEqual(float(line[12]), 1.5, places=3)          # the instance scale reaches the entity
        self.assertNotIn(13, got)                                          # the villager: no model in this build
        for key, l in got.items():
            if key != 14:
                self.assertAlmostEqual(float(l[12]), 1.0, places=3)     # unscaled references stay at 1

    def test_room_levelled_entity_rolls_spawns_there_and_keeps_its_pick(self):
        """CREATURE-ROOM-LEVELLED-54: a room map's aw_levelled entity is rolled from the table's list (its index in
        'sounds'), the creature spawned at the entity's place under its reference, the same one again when the room
        loads again (the C side asserts place and pick); at level 30 a list gives at least as much as at level 1."""
        out = self.run_check('room')
        self.assertIn('room levelled passed', out)
        rows = [l.split() for l in out.splitlines() if l.startswith('room ') and len(l.split()) == 5]
        self.assertTrue(rows)
        self.assertTrue(any(r[4] != 'none' for r in rows))

    def test_levelled_roll_is_deterministic_and_kept(self):
        def picks(seed):
            out = [l.split() for l in self.run_check('roll', seed).splitlines() if l.startswith('pick pass ')]
            return {(int(l[2]), int(l[4])): l[5] for l in out}
        first, again, other = picks(7), picks(7), picks(8)
        self.assertEqual(first, again)                                     # the same seed: the same picks
        self.assertTrue(first)
        for (p, ref), model in first.items():
            if p == 0 and (1, ref) in first:
                self.assertEqual(first[(1, ref)], model)                   # a later join keeps the pick
        self.assertEqual({k for k in first if k[0] == 0}, {(0, r) for p, r in first if p == 1})
        self.assertTrue(other)
        # the engine's picks are the builder's roll (tools/chim/actors.py levelled_pick) for that key and seed, at the
        # player's level (1 here); a pick of nothing spawns nothing
        import re
        for seed, got in ((7, first), (8, other)):
            want = {}
            for r in self.records:
                b = self.bases[r['base']]
                if 'list' not in b:
                    continue
                pick, _ = self.A.levelled_pick(self.lists, b['list'], 1, self.A.rng_seed(r['key'], seed))
                if pick >= 0:
                    m = re.search(r'"model" "([^"]+)"', self.bases[pick]['text'])
                    if m:
                        want[r['key']] = m.group(1)
            self.assertEqual({ref: model for (p, ref), model in got.items() if p == 0}, want, seed)


if __name__ == '__main__':
    unittest.main()
