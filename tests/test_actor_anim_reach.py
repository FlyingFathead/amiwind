# SPDX-License-Identifier: GPL-2.0-or-later
"""tools/actor_anim_reach.py and the engine limits it keeps (CREATURE-BIPED-ANIMS-62)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Appended, never put first: tools/ ahead of src/ makes tools/mwad.py shadow the src/mwad package for every test
# module discovered after this one (test_actor_ground failed to import in the per-module discovery, gate 9976).
if str(ROOT / 'tools') not in sys.path:
    sys.path.append(str(ROOT / 'tools'))
import actor_anim_reach as R  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def fixture(root, mover_layout='idle:0:8:0.3 walk:8:8:0.13:23 attack:22:8:0.1:0.46', write_mover=True):
    id1 = root / 'id1'
    (id1 / 'progs').mkdir(parents=True)
    (id1 / 'maps').mkdir()
    (id1 / 'progs' / 'c_slave.anm').write_text('idle:0:8:0.3 hit:8:3:0.3 >progs/c_slave_m.mdl\n')
    (id1 / 'progs' / 'c_slave.mdl').write_bytes(b'IDPO')
    if write_mover:
        (id1 / 'progs' / 'c_slave_m.anm').write_text(mover_layout + '\n')
        (id1 / 'progs' / 'c_slave_m.mdl').write_bytes(b'IDPO')
    (id1 / 'maps' / 'chim-actors.cca').write_bytes(
        b'\x00{ "aw_source_id" "ash_slave" "classname" "aw_npc" "model" "progs/c_slave.mdl" }\x00')
    lib = root / 'creature-library.json'
    lib.write_text(json.dumps({'models': {'r/ashslave.nif': {'model': 'progs/c_slave.mdl', 'groups': [
        {'name': 'idle', 'source': 'x.kf'}, {'name': 'walk', 'source': 'x.kf'}, {'name': 'attack', 'source': 'x.kf'}]}}}))
    return id1, lib


class ReachTests(unittest.TestCase):
    def test_walk_and_attack_through_the_mover_pass(self):
        with tempfile.TemporaryDirectory() as t:
            id1, lib = fixture(Path(t))
            failures, facts = R.check(id1, lib, lazies=64)
            self.assertEqual(failures, [])
            self.assertEqual(facts['movers'], 1)

    def test_a_missing_original_group_fails(self):
        with tempfile.TemporaryDirectory() as t:
            id1, lib = fixture(Path(t), mover_layout='idle:0:8:0.3 walk:8:8:0.13:23')
            failures, _ = R.check(id1, lib, lazies=64)
            self.assertTrue(any('attack not played' in f for f in failures), failures)

    def test_a_missing_mover_fails(self):
        with tempfile.TemporaryDirectory() as t:
            id1, lib = fixture(Path(t), write_mover=False)
            failures, _ = R.check(id1, lib, lazies=64)
            self.assertTrue(any('mover progs/c_slave_m.mdl' in f for f in failures), failures)

    def test_more_movers_than_the_engine_table_fails(self):
        with tempfile.TemporaryDirectory() as t:
            id1, lib = fixture(Path(t))
            failures, _ = R.check(id1, lib, lazies=0)
            self.assertTrue(any('over the engine mover name table' in f for f in failures), failures)


class EngineLimitTests(unittest.TestCase):
    def test_the_session_tables_are_not_filled_for_good(self):
        code = (SRC / 'aw_anim.c').read_text(encoding='latin-1')
        # the masters have 39 movers; a CHIM session is one level, so the name table holds every one of them
        self.assertGreaterEqual(R.engine_limit('LAZIES'), 39)
        # a full layout table gives an entry no live actor uses to the new model (never "idle only" for good)
        self.assertIn('else if((at=reclaim())<0)', code)
        self.assertNotIn('slot(m) || used>=TABLE', code)

    def test_the_arena_prepares_every_opponent_as_a_placed_actor(self):
        code = (SRC / 'aw_arena.c').read_text(encoding='latin-1')
        self.assertIn('{AW_AnimPrep(e);AW_ItemsPrep(e);}', code)


if __name__ == '__main__':
    unittest.main()
