"""SIGNPOST-NAMES-MISSING-65: a road signpost's boards say the place they point to when aimed at, as the original and
OpenMW 0.51 show a named activator's name (mwclass/activator.cpp getToolTipInfo). Each board is an activator record of
its own named after the place (active_sign_balmora_01 "Balmora"); the focus table (tools/prepare_focus.py) gives
every placed one an 'N' row at the board's centre with its box, and the engine tests the view ray against that box
and shows the name through the focus line (aw_inventory.c AW_PlacedFocus, aw_scene.c AW_SceneDraw).

Synthetic master only; no game data is read here.
"""
import math, struct, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_focus as focus


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def ref(number, ident, pos, rot=(0, 0, 0), *extra):
    return (sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident)) + b''.join(extra) +
            sub('DATA', struct.pack('<6f', *pos, *rot)))


def acti(ident, name, model):
    return rec('ACTI', sub('NAME', z(ident)), sub('MODL', z(model)), *([sub('FNAM', z(name))] if name else []))


MASTER = b''.join([
    acti('active_sign_balmora_01', 'Balmora', r'f\Active_signpost_01.NIF'),
    acti('active_sign_pelagiadB_01', 'Pelagiad (back road)', r'f\Active_signpost_01.NIF'),
    acti('active_signpost_01', '', r'f\Active_signpost_01.NIF'),          # the bare board: no name, no row
    acti('furn_shrine_test', 'Shrine', r'f\Furn_shrine_tribunal_01.NIF'),  # NAMED-ACTIVATOR-FOCUS-66: named, a row
    acti('sound_test00', 'Sound_Test00', 'EditorMarker.NIF'),                # a sound marker: never drawn, no row
    rec('CELL', sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, -3, -2)),
        ref(70, 'active_sign_balmora_01', (-20000, -12000, 1000)),
        ref(71, 'active_sign_pelagiadB_01', (-20000, -12000, 900), (0, 0, math.pi / 2), sub('XSCL', struct.pack('<f', 2.0))),
        ref(72, 'active_signpost_01', (-20000, -12000, 800)),
        ref(73, 'furn_shrine_test', (-20100, -12000, 800)),
        ref(74, 'sound_test00', (-20200, -12000, 800))),
])


def slab(axis, centre, eye, direction):
    """The engine's focus_board_ray (aw_inventory.c), line for line: where the ray enters the box, -1 a miss."""
    lo, hi = 0.0, 1e9
    d = [e - c for e, c in zip(eye, centre)]
    for a in axis:
        length = sum(v * v for v in a)
        e = sum(p * q for p, q in zip(d, a)) / length
        f = sum(p * q for p, q in zip(direction, a)) / length
        if abs(f) < 1e-9:
            if e < -1 or e > 1:
                return -1
            continue
        t0, t1 = sorted(((-1 - e) / f, (1 - e) / f))
        lo, hi = max(lo, t0), min(hi, t1)
        if lo > hi:
            return -1
    return lo


def axes(halves, quaternion):
    """The engine's focus_board_add: column k of the quaternion's rotation times half extent k."""
    r = focus.quaternion_matrix(quaternion)
    return [[r[i][k] * halves[k] for i in range(3)] for k in range(3)]


class SignBoardRows(unittest.TestCase):
    def rows(self):
        rooms = focus.placements(MASTER, focus.objects_of(MASTER), {})
        return {r[2]: r for r in rooms[focus.exterior_key(-3, -2)]}

    def test_each_named_board_gets_a_row_with_its_name(self):
        rows = self.rows()
        self.assertEqual(sorted(rows), [70, 71, 73])             # the bare board and the sound marker have none
        self.assertEqual((rows[73][0], rows[73][8]), ('N', 'Shrine'))   # NAMED-ACTIVATOR-FOCUS-66
        self.assertEqual((rows[70][0], rows[70][8], rows[70][10]), ('N', 'Balmora', focus.ACT_NONE))
        self.assertEqual(rows[71][8], 'Pelagiad (back road)')
        self.assertEqual(rows[70][1], 0)                          # never owned

    def test_the_row_sits_at_the_board_centre_turned_and_scaled(self):
        rows = self.rows()
        lo, hi = focus.FOCUS_BOXES[r'f\active_signpost_01.nif']
        centre = [(a + b) / 2 for a, b in zip(lo, hi)]
        self.assertAlmostEqual(rows[70][3], -20000 + centre[0], places=3)
        self.assertAlmostEqual(rows[70][4], -12000 + centre[1], places=3)
        # turned a quarter clockwise (Morrowind's angles) and twice the size: model +y (the arm) goes to world +x
        self.assertAlmostEqual(rows[71][3], -20000 + 2 * centre[1], places=3)
        self.assertAlmostEqual(rows[71][4], -12000 - 2 * centre[0], places=3)
        box = struct.unpack('<7f', rows[71][9][:28])
        self.assertAlmostEqual(box[1], (hi[1] - lo[1]), places=3)       # half extent y, scaled 2
        # the quarter turn as the builder's quaternion: about z, clockwise (w = sqrt(1/2), z = -sqrt(1/2))
        for got, want in zip(box[3:], (math.sqrt(.5), 0, 0, -math.sqrt(.5))):
            self.assertAlmostEqual(got, want, places=5)

    def test_the_quaternion_gives_back_the_rotation(self):
        # every board's turn, tilted ones too (97 boards of the original lean): the engine's matrix from the
        # quaternion equals the reference's rotation
        for angles in ((0, 0, 0), (0, 0, math.pi / 2), (0.1, -0.2, 2.5), (0.3, 0.05, -3.0), (math.pi, 0, 0.4)):
            r = focus.reference_rotation(angles)
            back = focus.quaternion_matrix(focus.rotation_quaternion(r))
            for i in range(3):
                for k in range(3):
                    self.assertAlmostEqual(back[i][k], r[i][k], places=5)

    def test_the_packed_row_keeps_name_and_box(self):
        rows = self.rows()
        packed = focus.pack_name_and_id('N', rows[71][8], rows[71][9])
        self.assertEqual(len(packed), focus.NAME + focus.IDENT)
        self.assertEqual(packed[:focus.NAME].rstrip(b'\0'), b'Pelagiad (back road)')
        self.assertEqual(packed[focus.NAME:focus.NAME + 28], rows[71][9][:28])

    def test_the_view_ray_meets_the_board_and_not_beside_it(self):
        rows = self.rows()
        box = struct.unpack('<7f', rows[70][9][:28])
        a = axes(box[:3], box[3:])
        centre = rows[70][3:6]
        eye = (centre[0] - 100, centre[1], centre[2])               # looking along +x at the board's face
        self.assertAlmostEqual(slab(a, centre, eye, (1, 0, 0)), 100 - box[0], places=3)
        self.assertEqual(slab(a, centre, (eye[0], eye[1], eye[2] + 40), (1, 0, 0)), -1)   # above the board
        self.assertEqual(slab(a, centre, eye, (-1, 0, 0)), -1)                             # looking away

    def test_a_placed_board_without_a_measured_box_stops_the_stage(self):
        odd = MASTER + b''.join([
            acti('active_sign_new_01', 'Newplace', r'f\Active_signpost_09.NIF'),
            rec('CELL', sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, 5, 5)), ref(80, 'active_sign_new_01', (0, 0, 0)))])
        with self.assertRaises(SystemExit) as stop:
            focus.placements(odd, focus.objects_of(odd), {})
        self.assertIn('active_sign_new_01', str(stop.exception))

    def test_every_outdoor_window_fits_the_engine_table(self):
        # FOCUS-ROWS-WINDOW-OVERFLOW-66: the engine reads the player's cell and its eight neighbours into FOCUS_ROWS
        # rows; the builder sums every 3 x 3 window (rooms alone) and stops the stage over that
        k = focus.exterior_key
        counts = {k(0, 0): 600, k(1, 0): 500, k(2, 0): 400, k(5, 5): 900, 7: 1000}
        self.assertEqual(focus.window_rows(counts), (1500, k(1, 0)))     # 600 + 500 + 400 around (1, 0)
        self.assertEqual(focus.window_rows({7: 1000}), (0, 0))           # a room is read alone
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        placed = (ROOT / 'engine/aga/src/aw_placed.c').read_text(encoding='utf-8')
        self.assertIn('#define FOCUS_ROWS %d' % focus.WINDOW_ROWS, inventory)
        self.assertIn('#define PLACED_MAX %d' % focus.PLACED_ITEMS, placed)  # the drawn items' list, checked apart
        tool = (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8')
        self.assertIn('if window > WINDOW_ROWS:', tool)
        self.assertIn('if most_items > PLACED_ITEMS:', tool)

    def test_the_engine_reads_and_aims_at_the_boards(self):
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn("row[0]!='C' && row[0]!='N')return;", inventory)
        self.assertIn("r->kind=='N' && (r->value=focus_board_add(row+FOCUS_ROW))<0", inventory)
        self.assertIn("focus_board_ray(focus_board_axis[row->value],at,eye,f)", inventory)
        board = inventory[inventory.index('static int focus_board_add('):inventory.index('static float focus_board_ray(')]
        self.assertNotIn('cos(', board)       # no trigonometry in play (68040-unimplemented instructions)
        self.assertNotIn('sin(', board)
        self.assertIn("else if(focus_rows[j].kind!='N')focus_rows[j].edict=1;", inventory)
        # the name goes through the focus line the items and doors use (no hand-placed text)
        scene = (ROOT / 'engine/aga/src/aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('AW_PlacedFocus(&focus_name', scene)
        self.assertIn('if(!name && focus_title)name=focus_title;', scene)


if __name__ == '__main__':
    unittest.main()
