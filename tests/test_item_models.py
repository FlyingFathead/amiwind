"""The item model table stage (tools/prepare_item_models.py, ITEM-WORLD-MODELS-58) without game data."""
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_item_models as pim  # noqa: E402


def model(w=64, h=48, uv=((0, 0), (10, 5), (3, 20))):
    from PIL import Image
    from npc_geometry import animated_mdl
    skin = Image.new('P', (w, h))
    skin.putdata([i % 251 for i in range(w * h)])
    frames = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=float)
    return animated_mdl(frames, np.array([[0, 1, 2]]), np.array(uv, dtype=float), skin, names=['item00'])


class ItemModelTests(unittest.TestCase):
    def test_squeeze_cuts_the_skin_to_the_texture_coordinates(self):
        raw = model()
        out = pim.squeeze(raw)
        w, h = struct.unpack_from('<2i', out, 52)
        self.assertEqual((w, h), (12, 22))          # max u 10 + 2 rounded to 4, max v 20 + 2
        self.assertEqual(len(raw) - len(out), 64 * 48 - 12 * 22)
        for row in range(h):                         # every kept texel is the original's
            self.assertEqual(out[88 + row * w:88 + row * w + w], raw[88 + row * 64:88 + row * 64 + w])
        self.assertEqual(out[88 + w * h:], raw[88 + 64 * 48:])      # coordinates, faces and frame unchanged
        self.assertEqual(pim.squeeze(out), out)

    def test_squeeze_keeps_a_skin_that_is_all_used(self):
        raw = model(16, 8, ((0, 0), (15, 7), (3, 2)))
        self.assertEqual(pim.squeeze(raw), raw)

    def test_table_round_trip_and_paths(self):
        key = 'm/key_standard_01.nif'
        path = pim.model_path(key)
        self.assertTrue(path.startswith('progs/items/m') and path.endswith('.mdl') and len(path) < 64)
        self.assertEqual(pim.read_table(('AWT1 1\n%s\t%s\n' % (key, path)).encode()), {key: path})
        for bad in (b'AWT1 2\na\tb.mdl\n', b'AWT0 0\n', b'AWT1 1\na\tb.mdl'):
            with self.assertRaises(ValueError):
                pim.read_table(bad)


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def record(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def ref(number, ident, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0), scale=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident.encode() + b'\0')
    if scale is not None:
        out += sub('XSCL', struct.pack('<f', scale))
    return out + sub('DATA', struct.pack('<6f', *pos, *rot))


def cell(name, refs, interior=True, grid=(0, 0)):
    return record('CELL', sub('NAME', name.encode() + b'\0'),
                  sub('DATA', struct.pack('<Iii', 1 if interior else 0, *grid)), *refs)


class PlacedItemTests(unittest.TestCase):
    """WORLD-OBJECT-PLACEMENT-59: the per-map placement list built from the cells and the shared model table."""
    TABLE = {'m/misc_quill.nif': 'progs/items/m0123456789abcdef.mdl', 'm/dagger.nif': 'progs/items/mfedcba9876543210.mdl'}
    ITEMS = {'misc_quill': {'source_model': 'm\\Misc_Quill.nif'}, 'iron dagger': {'source_model': 'm\\dagger.nif'},
             'torch': {'source_model': 'm/torch.nif', 'light': {'radius': 64}}, 'odd': {'source_model': 'm/none.nif'}}

    def test_the_engine_room_is_the_engine_define(self):
        header = (ROOT / 'engine/aga/src/aw_inventory.h').read_text(encoding='utf-8')
        import re
        self.assertEqual(int(re.search(r'#define AW_PLACED_MODELS (\d+)', header).group(1)), pim.PLACED_MODELS)

    def test_the_engine_path_buffers_hold_a_model_path(self):
        # PLACED-ITEMS-ROOM-RESET-59: a 32-byte stack buffer took the 34-byte path and the machine reset
        import re
        source = (ROOT / 'engine/aga/src/aw_placed.c').read_text(encoding='utf-8')
        size = int(re.search(r'#define PLACED_PATH (\d+)', source).group(1))
        self.assertGreater(size, len(pim.model_path('m/any.nif')))
        self.assertNotRegex(source, r'char\s+\w+\[(\d|[12]\d|3[0-3])\]')
        self.assertNotIn('sprintf(path', source.replace('Q_snprintf(path', ''))

    def test_an_outdoor_map_read_too_early_is_read_again(self):
        # PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59: the focus table (and the placed list with it) read before the player
        # stands at the arrival saw no room number and was never read again outdoors
        import re
        source = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        body = re.search(r'static void focus_refresh\(const edict_t \*p\)\{(.*?)\n\}', source, re.S).group(1)
        self.assertIn('if(!focus_outdoor && focus_to_source(p->v.origin,game)){focus_load();return;}', body)
        # and a CHIM frame map counts as outdoors (the open-world region table has no entry for it)
        self.assertIn('aw_focus_chim_source && aw_focus_chim_source(local,game)', source)
        world = (ROOT / 'engine/aga/src/chim/chim_world.c').read_text(encoding='utf-8')
        self.assertIn('aw_focus_chim_source = Source;', world)
        self.assertIn('aw_focus_chim_local = Local;', world)
        self.assertNotIn('AW_WorldToSource(sv.name', source.split('static int focus_to_source', 1)[1].split('\n}', 1)[1])
        self.assertIn('outdoor=AW_PlacedRefresh();', (ROOT / 'engine/aga/src/aw_placed.c').read_text(encoding='utf-8'))

    def test_alias_angles_turn_the_model_as_the_placement(self):
        from prepare_scenery import reference_rotation
        for rot in ((0.0, 0.0, 1.0), (0.3, 0.0, 0.0), (0.0, -0.7, 2.0), (1.2, 0.4, -2.5), (3.0, 1.0, 0.5),
                    (0.0, 1.5707963, 0.3)):
            angles = pim.alias_angles(rot)
            want = reference_rotation({'rotation_radians': list(rot)})
            got = np.array(pim.alias_matrix(angles))
            self.assertLess(float(np.abs(got - want).max()), 1e-4, rot)
        # a yaw-only placement: the actors' rule, yaw = -z in degrees
        self.assertEqual(pim.alias_angles((0.0, 0.0, 0.5))[1], -np.degrees(0.5))

    def test_list_from_cells_round_trip(self):
        master = (cell('Census Office', [ref(5, 'misc_quill', (400.0, -8.0, 116.0), (0.0, 0.0, 1.0), 1.5),
                                         ref(3, 'iron dagger', (10.0, 20.0, 30.0)), ref(4, 'torch'), ref(6, 'odd'),
                                         ref(7, 'chair')])
                  + cell('', [ref(9, 'misc_quill', (8192.0 * 2 + 5, 7.0, 1.0))], interior=False, grid=(2, 0))
                  + cell('Unnumbered', [ref(11, 'misc_quill')]))
        rows, missing = pim.placement_list(master, self.ITEMS, self.TABLE, {'census office': 763})
        self.assertEqual({r[0] for r in rows[763]}, {5, 3})       # no carried light, no item without a model
        self.assertEqual(missing, {'m/none.nif': 1})
        from prepare_focus import exterior_key
        self.assertEqual([r[0] for r in rows[exterior_key(2, 0)]], [9])
        raw = pim.pack_placed(rows)
        back = pim.read_placed(raw)
        quill = [r for r in back[763] if r[0] == 5][0]
        self.assertEqual(quill[1], 0)                              # row 0 of the table: m/misc_quill.nif
        self.assertEqual(quill[5], 'progs/items/m0123456789abcdef.mdl')
        self.assertAlmostEqual(quill[2], 1.5, places=3)
        self.assertEqual(quill[3], (400.0, -8.0, 116.0))
        self.assertEqual([r[0] for r in back[763]], [3, 5])        # ascending by reference, like focus.awf
        self.assertEqual(len(raw), 8 + 2 * 16 + 3 * pim.PLACED_ROW)
        for bad in (b'AWP0' + raw[4:], raw[:-1], raw[:8] + raw[24:40] + raw[8:24] + raw[40:]):
            with self.assertRaises(ValueError):
                pim.read_placed(bad)

    def test_the_limit_is_refused_at_the_stage(self):
        from prepare_focus import exterior_key
        row = lambda n, m: (n, m, 'progs/items/m0123456789abcdef.mdl', 0, 0, 0, 0, 0, 0, 1.0)
        ok = {763: [row(i, i) for i in range(pim.PLACED_MODELS)]}
        self.assertEqual(pim.check_placed(ok)[763]['models'], pim.PLACED_MODELS)
        with self.assertRaisesRegex(ValueError, 'room 0x2fb: 97 item models'):
            pim.check_placed({763: [row(i, i) for i in range(pim.PLACED_MODELS + 1)]})
        # outdoors the cell and its eight neighbours count together (the engine holds the 3 x 3 at once)
        split = {exterior_key(0, 0): [row(i, i) for i in range(60)],
                 exterior_key(1, 1): [row(100 + i, 60 + i) for i in range(40)]}
        with self.assertRaisesRegex(ValueError, 'exterior cell .*: 100 item models'):
            pim.check_placed(split)
        apart = {exterior_key(0, 0): split[exterior_key(0, 0)], exterior_key(5, 5): split[exterior_key(1, 1)]}
        self.assertEqual(pim.check_placed(apart)[exterior_key(0, 0)]['models'], 60)


if __name__ == '__main__':
    unittest.main()
