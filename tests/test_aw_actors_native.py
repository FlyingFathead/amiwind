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
               str(SRC / 'aw_ledger.c'),   # CELL-CHANGES-59 slice 6: the actors' rows are on the world change list
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

    def test_the_dead_stay_dead_across_a_room_and_a_save(self):
        # ACTOR-DEAD-RESPAWN-INTERIOR-65: killed outdoors (a fight, and a script on the actor record), a room entered and
        # left twice, then a save and a load: the town's map spawns them again inside the player's scene set-up, which
        # empties the combat slots; the change list is applied after it, so both bodies lie dead and the third lives
        self.assertIn('dead stay dead passed', self.run_check('deadstay'))

    def test_respawn_and_corpse_clearing_follow_the_original_over_time(self):
        # ACTOR-RESPAWN-CORPSE-RULES-66 (OpenMW 0.51 CellStore::respawn / clearCorpse; Morrowind.esm fCorpseRespawnDelay
        # 72, fCorpseClearDelay 72): with the game clock moved forward, an ordinary NPC's body is cleared after 72 h and
        # it stays dead for good, a Respawn-flagged one comes back, a Persistent one's body stays; through a save too
        self.assertIn('corpse rules passed', self.run_check('corpse'))

    def test_an_outdoor_body_lies_there_until_its_clear_delay(self):
        # OUTDOOR-DEAD-BODY-GONE-66: a joining outdoor cell's dead actor is spawned as its body (laid down, lootable)
        # until fCorpseClearDelay, then cleared for good; "chim actors corpses 0" keeps the older method (not spawned)
        self.assertIn('outdoor corpse passed', self.run_check('outdoorcorpse'))

    def test_summon_takes_an_optional_reference(self):
        # JOURNEY-STEP7-FIGHTER-NEAREST-66: "chim actors summon REF" copies the living resident of that reference, the
        # bare form still the nearest; an unknown or dead reference copies nobody and says so
        out = self.run_check('summonref')
        self.assertIn('summon by reference passed', out)
        self.assertIn('chim actors summon: no living actor of reference 999 here', out)

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

    def test_record_id_gives_its_world_model(self):
        # COMBAT-PLAYGROUND-CREATURE-HUMANOID-61: the combat playground draws a creature record with the model its
        # actor table base names (the mudcrab's), none for one without a model in this build
        out = self.run_check('basemodel')
        self.assertIn('base model progs/c_crab.mdl', out)
        self.assertIn('base model passed', out)

    def test_spawn_list_reads_every_living_base_with_its_name(self):
        # DBG-SPAWN-MENU-67: dbg spawn's list is every base of the table that spawns a living actor, with the record id
        # and the name its text holds (the creature and NPC libraries write aw_source_id and netname, as here); a base
        # without an id, a body (aw_corpse) and a creature without a model in this build are left out
        import test_chim_levelled as L
        library = {'crab': '"aw_source_id" "crab"\n"classname" "aw_npc"\n"model" "progs/c_crab.mdl"\n"netname" "Mudcrab"\n',
                   'rat': '"aw_source_id" "rat"\n"classname" "aw_npc"\n"model" "progs/c_rat.mdl"\n',
                   'rat_diseased': '"classname" "aw_npc"\n"model" "progs/c_rat.mdl"\n"netname" "Diseased Rat"\n',
                   'dead_rat': '"aw_source_id" "dead_rat"\n"classname" "aw_corpse"\n"model" "progs/c_rat.mdl"\n'}
        data, _ = self.A.build_table(self.A.exterior_actors(L.MASTER), {}, self.A.levelled_lists(L.MASTER),
                                     self.A.creature_ids(L.MASTER), library)
        tmp = Path(self.tmp.name)
        (tmp / 'spawn-actors.cca').write_bytes(data)
        result = subprocess.run([str(self.exe), 'baseeach', str(tmp / 'spawn-actors.cca'), str(tmp / 'frame.chim'), '0',
                                 str(tmp / 'frame2.chim')], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        given = sorted(set(l[5:] for l in result.stdout.splitlines() if l.startswith('each ')))
        self.assertEqual(given, ['crab|Mudcrab|1', 'rat||1'])
        count = int(next(l for l in result.stdout.splitlines() if l.startswith('base each ') and 'seen' not in l)[10:])
        seen = int(next(l for l in result.stdout.splitlines() if l.startswith('base each seen '))[15:])
        self.assertEqual(count, seen)
        self.assertGreaterEqual(count, 2)

    def test_a_named_list_is_rolled_by_its_id(self):
        # v0.0.67 (REST-CUT-NO-CREATURE-67, MWSCRIPT-PLACE-OTHER-KINDS-62): the builder's named lists (a region's sleep
        # list, a list a script places) are in the table with a levelled base of their own, last among the bases; the
        # engine rolls one by its id for a reference and keeps the pick (aw_actors.c AW_ActorsLevelledText). Before
        # v0.0.67 a list no exterior reference names had no base: the engine could not find it by id at all.
        import test_chim_levelled as L
        refs = self.A.exterior_actors(L.MASTER)
        data, report = self.A.build_table(refs, {}, self.A.levelled_lists(L.MASTER), self.A.creature_ids(L.MASTER),
                                          L.LIBRARY, named=('UNUSED', 'late', 'not_a_list'))
        self.assertEqual((report['levelled']['named_lists'], report['levelled']['named_lists_added']), (2, 1))
        _, _, _, bases, _ = self.A.read_table(data)
        lists = self.A.read_lists(data)
        tail = bases[-2:]
        self.assertEqual([b['hash'] for b in tail], [self.A.fnv('late'), self.A.fnv('unused')])
        self.assertTrue(all(b['kind'] == self.A.KINDS['LEVC'] and not b['text'] for b in tail))
        unused = lists[tail[1]['list']]
        self.assertEqual(len(unused[2]), 1)
        self.assertEqual(bases[unused[2][0][1]]['text'], L.LIBRARY['crab'])      # the crab, with its model
        tmp = Path(self.tmp.name)
        (tmp / 'named-actors.cca').write_bytes(data)
        result = subprocess.run([str(self.exe), 'named', str(tmp / 'named-actors.cca'), str(tmp / 'frame.chim'), '0',
                                 str(tmp / 'frame2.chim')], capture_output=True, text=True, cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('named unused progs/c_crab.mdl', result.stdout)
        self.assertIn('named lists passed', result.stdout)
        # without names the table is byte for byte the table of before
        plain, _ = self.A.build_table(refs, {}, self.A.levelled_lists(L.MASTER), self.A.creature_ids(L.MASTER),
                                      L.LIBRARY)
        self.assertEqual(plain, self.A.build_table(refs, {}, self.A.levelled_lists(L.MASTER),
                                                   self.A.creature_ids(L.MASTER), L.LIBRARY, named=())[0])

    def test_home_cell_joins_its_levelled_points(self):
        """OUTDOOR-CREATURES-HOME-CELL-67: the region frame map the session loads brings its cell's people and placed
        creatures but no levelled point (tools/chim/region_actors.py defers them), and the window's home frame never
        joins, so the arrival cell had none of its levelled creatures. A new map's first window tick joins the home
        cell's levelled points from the table: exactly the builder's roll for them at the player's level (the crab and
        the villager of the cell are not joined twice). A map change drops the queue of the map before (its places are
        that map's)."""
        import re
        for seed in (7, 8):
            out = self.run_check('homejoin', seed)
            self.assertIn('home join passed', out)
            self.assertIn('home cells joined 1', out)
            self.assertIn('home cells joined 2', out)
            self.assertIn('queued actors of the map before dropped', out)
            got = {int(l.split()[2]): l.split()[3] for l in out.splitlines() if l.startswith('homejoin ref ')}
            want = {}
            for r in self.records:
                b = self.bases[r['base']]
                if r['key'] not in (11, 12) or 'list' not in b:
                    continue
                pick, _ = self.A.levelled_pick(self.lists, b['list'], 1, self.A.rng_seed(r['key'], seed))
                m = re.search(r'"model" "([^"]+)"', self.bases[pick]['text']) if pick >= 0 else None
                if m:
                    want[r['key']] = m.group(1)
            self.assertEqual(got, want, seed)

    def test_same_map_reload_and_save_load_join_again(self):
        """ACTOR-TABLE-SAME-MAP-RELOAD-67: the map the player stands in spawned again under the same name (a save made
        there loaded, dbg aw hors 0) joined none of its cells, because the ticks told a new map by its name alone. Every
        server spawn now resets that (AW_ActorsServerReset, called by sv_main.c SV_SpawnServer): the reload and the
        save's load give the same creatures as the first spawn (the builder's roll, the picks kept), and a room spawned
        again takes its set-up again."""
        import re
        src = (SRC / 'sv_main.c').read_text(encoding='latin-1')
        spawn = src.split('void SV_SpawnServer', 1)[1]
        self.assertLess(spawn.index('memset (&sv, 0, sizeof(sv));'), spawn.index('AW_ActorsServerReset();'))
        for seed in (7, 8):
            out = self.run_check('samemap', seed)
            self.assertIn('same map passed', out)
            self.assertIn('home cells joined 3', out)
            passes = {}
            for line in out.splitlines():
                if line.startswith('samemap ') and ' ref ' in line:
                    w = line.split()
                    passes.setdefault(w[1], {})[int(w[3])] = w[4]
            self.assertEqual(set(passes), {'first', 'reload', 'load'})
            self.assertEqual(passes['first'], passes['reload'])
            self.assertEqual(passes['first'], passes['load'])
            want = {}
            for r in self.records:
                b = self.bases[r['base']]
                if r['key'] not in (11, 12) or 'list' not in b:
                    continue
                pick, _ = self.A.levelled_pick(self.lists, b['list'], 1, self.A.rng_seed(r['key'], seed))
                m = re.search(r'"model" "([^"]+)"', self.bases[pick]['text']) if pick >= 0 else None
                if m:
                    want[r['key']] = m.group(1)
            self.assertEqual(passes['first'], want, seed)

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
