# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp's categories and Beings (v0.0.66, TP-MENU-CATEGORY-FILTER-66, DBG-TP-TO-NPC-66) on synthetic masters: the
names list's four categories; a unique person (Fargoth) outdoors; a unique creature (Vivec) in a room, at its point in
the room's units; one name in two places (Dagoth Ur, listed once per place); a common kind (slaughterfish) listed
once with its placements file; a being whose room the image does not hold (left out, named); the expansion tags (a
tagged place, a tagged being, a tagged room; a base cell an expansion edits keeps its plain name); the search finds a
tagged label by its plain name."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import tp_places_lut as T  # noqa: E402
from test_tp_places import cell, rec, ref, sub, z  # noqa: E402


def actor(tag, ident, name):
    return rec(tag, [sub('NAME', z(ident)), sub('FNAM', z(name))])


def head(masters=()):
    subs = [sub('HEDR', b'\0' * 300)]
    for m in masters:
        subs += [sub('MAST', z(m)), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', subs)


def base():
    out = head()
    out += actor('NPC_', 'fargoth', 'Fargoth') + actor('CREA', 'vivec_god', 'Vivec')
    out += actor('CREA', 'dagoth_ur_1', 'Dagoth Ur') + actor('CREA', 'dagoth_ur_2', 'Dagoth Ur')
    out += actor('CREA', 'slaughterfish', 'Slaughterfish') + actor('NPC_', 'hidden_one', 'Hidden One')
    out += cell('Seyda Neen', -2, -9, False, [ref(1, 'fargoth', (-11000, -71000, 120))] +
                [ref(10 + i, 'slaughterfish', (-12000 - 500 * i, -72000, -300)) for i in range(4)])
    out += cell('Bitter Coast Region', -3, -9, False, [ref(20, 'slaughterfish', (-20000, -72000, -300))])
    out += cell('Vivec, Palace of Vivec', 0, 0, True, [ref(30, 'vivec_god', (400, 800, 80))])
    out += cell('Dagoth Ur, Facility Cavern', 0, 0, True, [ref(31, 'dagoth_ur_1', (40, 80, 0))])
    out += cell("Akulakhan's Chamber", 0, 0, True, [ref(32, 'dagoth_ur_2', (-40, 0, 16))])
    out += cell('Unbuilt Cave', 0, 0, True, [ref(33, 'hidden_one', (0, 0, 0))])
    return out


def tribunal():
    out = head(['Morrowind.esm'])
    out += actor('NPC_', 'almalexia', 'Almalexia')
    out += cell('Mournhold, Great Bazaar', 0, 0, True, [ref(40, 'almalexia', (0, 0, 0))])
    out += cell('Seyda Neen', -2, -9, False)                    # an edit of a base cell: stays untagged
    return out


def bloodmoon():
    return head(['Morrowind.esm']) + cell('Raven Rock', -25, 19, False)


ROOMS = {'vivec, palace of vivec': 'rvivec', 'dagoth ur, facility cavern': 'rdagoth1',
         "akulakhan's chamber": 'rakula', 'mournhold, great bazaar': 'mhbazaar'}


class Beings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data = Path(cls.tmp.name) / 'Data Files'
        data.mkdir()
        (data / 'Morrowind.esm').write_bytes(base())
        (data / 'Tribunal.esm').write_bytes(tribunal())
        (data / 'Bloodmoon.esm').write_bytes(bloodmoon())
        from mwad.masters import master_path
        masters = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
        cls.master = master_path(data, masters, merged_dir=Path(cls.tmp.name) / 'merged').read_bytes()
        tags = T.layer_tags([(m, (data / m).read_bytes()) for m in masters])
        base_cells = T.exterior_cells(data / 'Morrowind.esm')
        cls.table, cls.report = T.build_master(cls.master, base_cells, {(-25, 19)}, tags)
        cls.table_places = cls.table
        cls.table, _ = T.add_rooms(cls.table, ROOMS, T.interior_names(cls.master), cls.report['room_tags'])
        cls.table, cls.beings = T.add_beings(cls.table, cls.master, ROOMS, cls.report['beings_exterior'],
                                             cls.report['record_tags'], offsets={})
        cls.rows = {r['name']: r for r in T.read_table(cls.table)}
        cls.id1 = Path(cls.tmp.name) / 'id1'
        cls.id1.mkdir()
        cls.held = T.write_list(cls.id1, cls.table, cls.beings['kind_files_data'])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_four_categories_in_the_names_list(self):
        names = T.read_names((self.id1 / T.NAMES).read_bytes())
        self.assertEqual([n for _, n in names], [r['name'] for r in T.read_table(self.table)])
        by = dict((n, c) for c, n in names)
        self.assertEqual(by['Seyda Neen'], T.CAT_EXTERIOR)
        self.assertEqual(by['Vivec, Palace of Vivec (interior)'], T.CAT_INTERIOR)
        self.assertEqual(by['Fargoth'], T.CAT_BEING)
        self.assertEqual(self.held, len((self.id1 / T.NAMES).read_bytes()) - T.HEADER + 4 * len(names))

    def test_unique_person_outdoors(self):
        r = self.rows['Fargoth']
        self.assertEqual((r['id'], r['map'], r['x'], r['y'], r['z']), ('fargoth', '', -11000, -71000, 120))
        self.assertTrue(r['flags'] & T.F_BEING and not r['flags'] & T.F_NEAREST)

    def test_unique_creature_in_a_room(self):
        r = self.rows['Vivec']
        self.assertEqual((r['id'], r['map']), ('vivec_god', 'rvivec'))
        self.assertEqual((r['x'], r['y'], r['z']), (100, 200, 20))          # the room's units (x 0.25)
        self.assertTrue(r['flags'] & T.F_ROOM)

    def test_one_name_in_two_places(self):
        self.assertEqual(self.rows['Dagoth Ur, Facility Cavern']['id'], 'dagoth_ur_1')
        self.assertEqual(self.rows["Dagoth Ur, Akulakhan's Chamber"]['map'], 'rakula')
        self.assertNotIn('Dagoth Ur', self.rows)

    def test_common_kind_to_the_nearest(self):
        r = self.rows['Slaughterfish']
        self.assertTrue(r['flags'] & T.F_NEAREST)
        self.assertEqual(r['map'], T.kind_file_name('Slaughterfish'))
        kind = (self.id1 / T.KIND_DIR / (r['map'] + '.tpk')).read_bytes()
        self.assertEqual(kind[:8], b'AWTK\x00\x01\x00\x40')
        self.assertEqual(struct.unpack_from('>I', kind, 8)[0], 5)
        self.assertEqual(len(kind), 16 + 5 * 64)
        self.assertEqual(sum(1 for n in self.rows if n.startswith('Slaughterfish')), 1)

    def test_being_outside_the_image_left_out_and_named(self):
        self.assertFalse(any(n.startswith('Hidden One') for n in self.rows))
        self.assertIn('Hidden One (Unbuilt Cave)', self.beings['beings_not_built'])

    def test_expansion_tags(self):
        self.assertIn('Raven Rock (Bloodmoon)', self.rows)                         # a tagged place
        self.assertIn('Almalexia (Tribunal)', self.rows)                           # a tagged being
        self.assertIn('Mournhold, Great Bazaar (Tribunal) (interior)', self.rows)  # a tagged room
        self.assertIn('Seyda Neen', self.rows)                                     # edited base cell: plain
        self.assertNotIn('Seyda Neen (Tribunal)', self.rows)
        self.assertEqual(T.untagged('Raven Rock (Bloodmoon)'), 'Raven Rock')

    def test_image_rooms_with_out_writes_its_report(self):
        """The image step's own route (build_aga write_world_doors: image_rooms with OUT set) on data with a common
        kind: the JSON report is written (no kind file bytes in it) and the kind file lands in id1/tpk."""
        import json
        work = Path(self.tmp.name) / 'image'
        id1, out = work / 'id1', work / 'out'
        id1.mkdir(parents=True)
        out.mkdir()
        (id1 / T.NAME).write_bytes(self.table_places)
        (out / 'tp-places-table.json').write_text(json.dumps(self.report), encoding='utf-8')
        report = T.image_rooms(id1, ROOMS, self.master, out)
        self.assertNotIn('kind_files_data', report)
        written = json.loads((out / 'tp-places-rooms.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(written['kinds'], 1)
        self.assertEqual(written['names_bytes_open'], report['names_bytes_open'])
        self.assertTrue((id1 / T.KIND_DIR / (T.kind_file_name('Slaughterfish') + '.tpk')).is_file())
        self.assertTrue((id1 / T.NAMES).is_file())

    def test_same_input_same_bytes(self):
        again, _ = T.add_beings(self.table, self.master, ROOMS, self.report['beings_exterior'],
                                self.report['record_tags'], offsets={})
        self.assertEqual(again, self.table)


if __name__ == '__main__':
    unittest.main()
