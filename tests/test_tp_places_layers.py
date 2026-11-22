# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp's list box with the expansion layers (TP-LIST-EXPANSIONS-66): the settlements table and its room names are
read through the merging reader of exactly the selected layers (src/mwad/masters.py). With the base game alone the
table is byte-identical to the base master's own table and its unit key is unchanged; each of the four selections
(base, base + Tribunal, base + Bloodmoon, base + both) holds exactly its own places, never a place of an unselected
expansion; a layer's outdoor place is listed only where the image holds a frame of one of its cells."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import tp_places_lut as T  # noqa: E402
from test_tp_places import cell, master, rec, ref, sub, z  # noqa: E402
from mwad.masters import master_path  # noqa: E402

SELECTIONS = {
    'base': ('Morrowind.esm',),
    'tribunal': ('Morrowind.esm', 'Tribunal.esm'),
    'bloodmoon': ('Morrowind.esm', 'Bloodmoon.esm'),
    'both': ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'),
}


def layer(cells, masters=('Morrowind.esm',)):
    head = [sub('HEDR', b'\0' * 300)]
    for m in masters:
        head += [sub('MAST', z(m)), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', head) + b''.join(cells)


def tribunal():
    return layer([cell('Mournhold, Great Bazaar', 0, 0, True,
                       [ref(1, 'in_door_t', (0, 0, 0), destination=(100, 100, 50), dest_cell='Mournhold, Plaza')])])


def bloodmoon():
    return layer([cell('Raven Rock', -25, 19, False, [ref(1, 'ex_rock', (-25 * 8192 + 100, 19 * 8192 + 100, 300))]),
                  cell('Fort Frostmoth', -22, 17, False),            # no frame in the image: not listed
                  cell('Skaal Village, Greathall', 0, 0, True)])


FRAMES = {(-25, 19)}


class LayerSelections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name) / 'Data Files'
        cls.data.mkdir()
        (cls.data / 'Morrowind.esm').write_bytes(master())
        (cls.data / 'Tribunal.esm').write_bytes(tribunal())
        (cls.data / 'Bloodmoon.esm').write_bytes(bloodmoon())
        world = Path(cls.tmp.name) / 'chim-world' / 'chim' / 'frames' / 'x-25' / 'y+19'
        world.mkdir(parents=True)
        (world / 'frame.ccf').write_bytes(b'frame')
        cls.chim_world = Path(cls.tmp.name) / 'chim-world'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def table(self, masters):
        sel, base, frames = T.layer_inputs(self.data, self.chim_world, masters)
        path = master_path(self.data, sel, merged_dir=Path(self.tmp.name) / 'merged')
        data, report = T.build_master(path, base, frames)
        names = {r['name'] for r in T.read_table(data)}
        return data, report, names, set(T.interior_names(path).values())

    def test_frames_found(self):
        self.assertEqual(T.layer_inputs(self.data, self.chim_world, SELECTIONS['bloodmoon'])[2], FRAMES)

    def test_base_alone_unchanged(self):
        sel, base, frames = T.layer_inputs(self.data, self.chim_world, SELECTIONS['base'])
        self.assertIsNone(base)      # no layer inputs: the unit key stays the base master's SHA-256 alone
        data, report, _, _ = self.table(SELECTIONS['base'])
        self.assertEqual(data, T.build_master(master())[0])
        self.assertNotIn('places_not_built', report)

    def test_each_selection_holds_exactly_its_places(self):
        base_names = self.table(SELECTIONS['base'])[2]
        for what, masters in SELECTIONS.items():
            with self.subTest(what):
                _, report, names, rooms = self.table(masters)
                self.assertTrue(base_names <= names)
                has_t, has_b = 'Tribunal.esm' in masters, 'Bloodmoon.esm' in masters
                self.assertEqual('Mournhold, Great Bazaar' in rooms, has_t)
                self.assertEqual('Skaal Village, Greathall' in rooms, has_b)
                self.assertEqual('Raven Rock' in names, has_b)
                self.assertEqual(names - base_names, {'Raven Rock'} if has_b else set())
                self.assertNotIn('Fort Frostmoth', names)          # unbuilt: never listed
                if has_b:
                    self.assertEqual(report['places_not_built'], ['Fort Frostmoth'])

    def test_room_rows_searchable(self):
        _, _, _, rooms = self.table(SELECTIONS['both'])
        path = master_path(self.data, SELECTIONS['both'], merged_dir=Path(self.tmp.name) / 'merged')
        data, report = T.add_rooms(T.build_master(path)[0], {'mournhold, great bazaar': 'mh_bazaar'},
                                   T.interior_names(path))
        self.assertIn('Mournhold, Great Bazaar (interior)', {r['name'] for r in T.read_table(data)})

    def test_no_frames_no_layer_exteriors(self):
        sel, base, frames = T.layer_inputs(self.data, None, SELECTIONS['bloodmoon'])
        path = master_path(self.data, sel, merged_dir=Path(self.tmp.name) / 'merged')
        names = {r['name'] for r in T.read_table(T.build_master(path, base, frames)[0])}
        self.assertNotIn('Raven Rock', names)

    def test_image_step_passes_the_world(self):
        # the image step hands over its own options: the step reads the base CHIM world and the expansions' stores
        text = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("tp_places_step(args.data_files, boot/'id1', out, jobs=jobs, args=args)", text)
        step = (ROOT / 'tools' / 'tp_places_lut.py').read_text(encoding='utf-8')
        self.assertIn("chim_world = chim_world or getattr(args, 'chim_world', None)", step)
        self.assertIn("layer_worlds = layer_worlds or getattr(args, 'chim_layer_world', None)", step)

    def test_a_place_in_an_expansion_store_is_listed(self):
        # TP-LIST-MODULE-STORE-PLACES-68: Solstheim is built by its module into a store of its own (chimsol); the
        # base CHIM world holds none of its frames. A place whose cell has a frame in that store is in the game and
        # is listed; before, the 13 named places of Solstheim and its 202 outdoor people and creatures were left out
        # of the list of an image that held 135 of the island's cells
        from unittest import mock
        import chim.layer_stores as L
        holders = {(-22, 17): ('sl0061', [0, 0, 0])}
        with mock.patch.object(L, 'frame_holders', return_value=holders) as seen:
            sel, base, frames = T.layer_inputs(self.data, self.chim_world, SELECTIONS['bloodmoon'],
                                               layer_worlds=['chimsol=/nowhere'])
        seen.assert_called_once_with(['chimsol=/nowhere'])
        self.assertEqual(frames, FRAMES | {(-22, 17)})
        path = master_path(self.data, sel, merged_dir=Path(self.tmp.name) / 'merged')
        data, report = T.build_master(path, base, frames)
        names = {r['name'] for r in T.read_table(data)}
        self.assertIn('Fort Frostmoth', names)
        self.assertIn('Raven Rock', names)
        self.assertEqual(report['places_not_built'], [])
        # without the store's frames the place is named as not built, as before
        sel, base, frames = T.layer_inputs(self.data, self.chim_world, SELECTIONS['bloodmoon'])
        self.assertEqual(T.build_master(path, base, frames)[1]['places_not_built'], ['Fort Frostmoth'])
        # the base game alone asks no store
        with mock.patch.object(L, 'frame_holders', side_effect=AssertionError('asked')):
            self.assertEqual(T.layer_inputs(self.data, self.chim_world, SELECTIONS['base'],
                                            layer_worlds=['chimsol=/nowhere'])[1:], (None, None))


if __name__ == '__main__':
    unittest.main()
