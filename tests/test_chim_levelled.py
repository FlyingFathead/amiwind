# SPDX-License-Identifier: GPL-3.0-only
"""Levelled creature lists in the CHIM actor table (version 2, EXPERIMENTAL, --chim-actor-table on;
tools/chim/actors.py, engine chim/chim_actor_table.c ChimActors_LevelledPick, aw_actors.c) and the creature model
library (tools/creature_library.py).

A synthetic master holds levelled lists of every kind the game uses (calculate from all levels or only the highest
level at or below the player's, chance none, a list inside a list, an entry naming no record) and the exterior
references to them. Checked: the table's list section and bases; the exact probabilities of a roll at each level
against hand-worked values (the rule read from OpenMW 0.51 getLevelledItem); the roll's frequencies against those
probabilities; the engine's decoder and roll giving exactly the builder's picks for every list, level and seed
(native); a broken list section refused; a version 1 table byte for byte as before; the creature library's plan,
support states and base texts. Synthetic data only.
"""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'

from test_entity_tracker import base, cell, record, sub, z  # noqa: E402
from test_chim_actor_table import ref  # noqa: E402


def levc(ident, flags, chance, entries):
    body = [sub('NAME', z(ident)), sub('DATA', struct.pack('<I', flags)), sub('NNAM', bytes([chance])),
            sub('INDX', struct.pack('<I', len(entries)))]
    for entry, level in entries:
        body += [sub('CNAM', z(entry)), sub('INTV', struct.pack('<H', level))]
    return record('LEVC', *body)


def crea(ident, model, name, flags=0x48, health=10):
    npdt = bytearray(96)
    struct.pack_into('<i', npdt, 40, health)
    return record('CREA', sub('NAME', z(ident)), sub('MODL', z(model)), sub('FNAM', z(name)), sub('NPDT', bytes(npdt)),
                  sub('FLAG', struct.pack('<I', flags)))


MASTER = b''.join([
    crea('rat', 'r\\Rust Rat.NIF', 'Rat'), crea('rat_diseased', 'r\\rust rat.nif', 'Diseased Rat'),
    crea('crab', 'r\\mudcrab.nif', 'Mudcrab'), crea('racer', 'r\\cliffracer.nif', 'Cliff Racer', flags=0x20 | 0x08),
    crea('fish', 'r\\slaughterfish.nif', 'Slaughterfish', flags=0x10 | 0x08), crea('dead_rat', 'r\\rust rat.nif',
                                                                                  'Dead Rat', health=0),
    levc('all_lev', 1, 0, [('rat', 1), ('crab', 3), ('racer', 5)]),          # every entry at or below the level
    levc('top_lev', 0, 0, [('rat', 1), ('crab', 3), ('rat_diseased', 3), ('racer', 5)]),  # only the highest
    levc('maybe', 1, 25, [('rat', 1), ('crab', 1)]),                         # chance none 25
    levc('outer', 1, 0, [('maybe', 1), ('fish', 2)]),                        # a list inside a list
    levc('late', 1, 0, [('racer', 4), ('ghost_that_is_not', 4)]),            # nothing below 4; an unknown id
    levc('unused', 1, 0, [('crab', 1)]),                                     # no exterior reference
    base('NPC_', 'villager'),
    cell('', False, 0, 0, ref(11, 'all_lev', (100.0, 200.0, 8.0)) + ref(12, 'top_lev', (300.0, 50.0, 4.0))
         + ref(13, 'villager', (500.0, 500.0, 0.0)) + ref(14, 'crab', (900.0, 900.0, 0.0))),
    cell('', False, 1, 0, ref(21, 'outer', (8192.0 + 100.0, 50.0, 0.0)) + ref(22, 'late', (8192.0 + 400.0, 70.0, 0.0))),
    cell('Some Cave', True, refs=ref(31, 'unused')),
])

LIBRARY = {'crab': '"classname" "aw_npc"\n"model" "progs/c_crab.mdl"\n', 'rat': '"classname" "aw_npc"\n"model" "progs/c_rat.mdl"\n'}


def table():
    from chim import actors as A
    refs = A.exterior_actors(MASTER)
    return A.build_table(refs, {}, A.levelled_lists(MASTER), A.creature_ids(MASTER), LIBRARY)


class LevelledTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from chim import actors as A
        cls.A = A
        cls.data, cls.report = table()
        cls.head, cls.cells, cls.records, cls.bases, _ = A.read_table(cls.data)
        cls.lists = A.read_lists(cls.data)
        cls.names = {}
        for i, b in enumerate(cls.bases):
            cls.names[i] = next((k for k in ('rat', 'rat_diseased', 'crab', 'racer', 'fish', 'all_lev', 'top_lev',
                                             'outer', 'late') if A.fnv(k) == b['hash']), '?')

    def list_of(self, name):
        return next(b['list'] for b in self.bases if b['kind'] == self.A.KINDS['LEVC'] and b['hash'] == self.A.fnv(name))

    def dist(self, name, level):
        d = self.A.levelled_distribution(self.lists, self.list_of(name), level)
        return {self.names.get(k, 'none') if k != self.A.PICK_NONE else 'none': round(v, 9) for k, v in d.items() if v}

    def test_section(self):
        """Version 2; the lists the exterior uses (with the list inside a list, not the interior-only one); a base
        per creature a list can give, with its library text when the library has it."""
        self.assertEqual(self.head['version'], 2)
        self.assertEqual(len(self.lists), 5)                      # all_lev, late, maybe, outer, top_lev
        self.assertEqual(self.report['levelled']['lists'], 5)
        self.assertEqual(self.report['levelled']['entries_naming_nothing'], 1)
        crab = [b for b in self.bases if b['hash'] == self.A.fnv('crab')]
        self.assertEqual([b['text'] for b in crab], [LIBRARY['crab']])     # the direct reference and the lists share
        self.assertEqual(self.report['levelled']['creature_bases'], 5)     # rat, crab, racer, rat_diseased, fish
        self.assertEqual(self.report['levelled']['creature_bases_with_model'], 2)
        self.assertEqual(self.report['by_kind']['LEVC'], 4)

    def test_rule_by_hand(self):
        """The rule, worked by hand: all levels <= the player's, or only the highest; chance none; nested lists."""
        self.assertEqual(self.dist('all_lev', 1), {'rat': 1.0})
        self.assertEqual(self.dist('all_lev', 3), {'rat': 0.5, 'crab': 0.5})
        self.assertEqual(self.dist('all_lev', 30), {'rat': round(1 / 3, 9), 'crab': round(1 / 3, 9),
                                                     'racer': round(1 / 3, 9)})
        self.assertEqual(self.dist('top_lev', 2), {'rat': 1.0})
        self.assertEqual(self.dist('top_lev', 4), {'crab': 0.5, 'rat_diseased': 0.5})
        self.assertEqual(self.dist('top_lev', 9), {'racer': 1.0})
        self.assertEqual(self.dist('outer', 1), {'none': 0.25, 'rat': 0.375, 'crab': 0.375})
        self.assertEqual(self.dist('outer', 2), {'none': 0.125, 'rat': 0.1875, 'crab': 0.1875, 'fish': 0.5})
        self.assertEqual(self.dist('late', 3), {'none': 1.0})
        self.assertEqual(self.dist('late', 4), {'racer': 0.5, 'none': 0.5})   # the unknown id gives nothing

    def test_frequencies(self):
        """The roll (the engine's random numbers) follows the probabilities: 20,000 references each."""
        A = self.A
        for name, level in (('outer', 2), ('top_lev', 4), ('all_lev', 30)):
            index = self.list_of(name)
            want = A.levelled_distribution(self.lists, index, level)
            got = {}
            for key in range(1, 20001):
                pick, _ = A.levelled_pick(self.lists, index, level, A.rng_seed(key, 7))
                got[pick] = got.get(pick, 0) + 1
            for k, p in want.items():
                self.assertAlmostEqual(got.get(k, 0) / 20000, p, delta=0.015, msg=(name, level, k))

    def test_version_1_unchanged(self):
        """Without the lists the table is version 1, byte for byte as the dev line's 1db65508 wrote it (the
        synthetic case of test_chim_actor_table)."""
        import hashlib
        from test_chim_actor_table import MASTER as M1, ROWS, frame_map
        with tempfile.TemporaryDirectory(prefix='amiwind-levelled-v1-') as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            frame_map(maps / 'town-chim.chim', ROWS)
            data, _ = self.A.build_table(self.A.exterior_actors(M1), self.A.built_actors(maps, {}))
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         'd15c2cb7e2ce47a28bedde557295526c8c1d32551f68d02ecdd17f2cc2a0247a')
        self.assertIsNone(self.A.read_lists(data))

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_engine_picks_the_same(self):
        """The engine's decoders and roll (native) give exactly the builder's pick for every levelled base, player
        level 1-30 and 40 seeds; a broken list section is refused."""
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        A = self.A
        want = []
        for i, b in enumerate(self.bases):
            if b['kind'] != A.KINDS['LEVC']:
                continue
            for level in range(1, 31):
                for seed in range(40):
                    pick, _ = A.levelled_pick(self.lists, b['list'], level, A.rng_seed(1000 + i, seed))
                    want.append('pick %d %d %d %d' % (i, level, seed, pick))
        with tempfile.TemporaryDirectory(prefix='amiwind-levelled-c-') as tmp:
            path = Path(tmp) / 'chim-actors.cca'
            path.write_bytes(self.data)
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_chim_levelled_test.c',
                                          [SRC / 'chim/chim_format.c', SRC / 'chim/chim_actor_table.c'],
                                          cflags=[*WARN, '-O1'], arguments=[str(path), str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        self.assertEqual(lines[:4], ['refused chance', 'refused target', 'refused size', 'valid'])
        self.assertEqual(lines[4:], want)


class CreatureLibraryTests(unittest.TestCase):
    def test_plan_by_mesh(self):
        """One model per mesh (the two rats share one; the dead rat gets none); support state from the record's
        flags when the grounding policy does not name the creature (flies or swims without walking: off the ground)."""
        import creature_library as L
        planned = L.plan(MASTER)
        self.assertEqual(planned['meshes'], {'r/rust rat.nif': ['rat', 'rat_diseased'], 'r/mudcrab.nif': ['crab'],
                                             'r/cliffracer.nif': ['racer'], 'r/slaughterfish.nif': ['fish']})
        self.assertTrue(planned['bases']['dead_rat']['dead'])
        self.assertEqual({k: v['ground_mode'] for k, v in planned['bases'].items()},
                         {'rat': 0, 'rat_diseased': 0, 'crab': 0, 'racer': 1, 'fish': 1, 'dead_rat': 0})
        self.assertEqual(L.model_path('r/rust rat.nif'), L.model_path('R/Rust Rat.NIF'))

    def test_base_texts(self):
        """A base's text is a resident row's fields without the per-placement ones; the two rats name one model."""
        import creature_library as L
        planned = L.plan(MASTER)
        models = {m: {'model': L.model_path(m), 'step': 0.25} for m in planned['meshes']}
        texts = L.base_texts(L.manifest(planned, models))
        self.assertNotIn('dead_rat', texts)
        self.assertEqual(texts['rat'].split('\n')[3], '"model" "%s"' % L.model_path('r/rust rat.nif'))
        self.assertIn('"netname" "Diseased Rat"\n', texts['rat_diseased'])
        self.assertIn('"aw_ground_mode" "1"\n', texts['racer'])
        for text in texts.values():
            for field in ('origin', 'angles', 'aw_ref', 'aw_ground_baked', 'aw_ground_valid'):
                self.assertNotIn('"%s"' % field, text)
        from chim import actors as A
        data, report = A.build_table(A.exterior_actors(MASTER), {}, A.levelled_lists(MASTER), A.creature_ids(MASTER),
                                     texts)
        self.assertEqual(report['levelled']['creature_bases_with_model'], 5)
        self.assertEqual(report['spawnable_records'], 1)                   # the crab placed directly

    def test_no_unit_kind_or_stair_code_reaches_the_modules(self):
        from chim import units
        from chim import collision
        for kind in units.CODE_ENTRIES:
            for module in ('tools/creature_library.py', 'tools/chim/actors.py'):
                self.assertNotIn(module, units.TOOLS.get(kind, []), kind)
        self.assertFalse(any('creature_library' in f for f in collision.stair_code_selection()[0]))


if __name__ == '__main__':
    unittest.main()
