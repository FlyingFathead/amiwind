# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp with no argument (TP-PICKER-57): the settlements table (tools/tp_places_lut.py, AWTP1) on a synthetic
master (named exterior cells are places, a town over several cells is one, the arrival order CocMarkerHeading ->
a door's arrival above the sea -> a placed object on land -> the cells' middle, the last two without a height), the console-font list box's rules
(tests/aga_listbox_test.c over engine/aga/src/aw_listbox_rules.c) and the wiring (every older dbg tp form kept, the
scene picker when the table is missing, nothing resident, the image step, the Makefile)."""
import os
import shutil
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import tp_places_lut as T  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('latin-1') + b'\0'


def ref(number, ident, pos, destination=None, dest_cell=None, deleted=False):
    out = [sub('FRMR', struct.pack('<I', number)), sub('NAME', z(ident)),
           sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))]
    if destination:
        out.append(sub('DODT', struct.pack('<6f', *destination, 0, 0, 0)))
    if dest_cell:
        out.append(sub('DNAM', z(dest_cell)))
    if deleted:
        out.append(sub('DELE', b'\0\0\0\0'))
    return out


def cell(name, x, y, interior, refs=()):
    subs = [sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y))]
    for r in refs:
        subs += r
    return rec('CELL', subs)


def master():
    """Seyda Neen over two cells with two doors out (one nearer the middle) and a door to another room (no street);
    Ald-ruhn with a CocMarkerHeading and a door; Vivec, Foreign Quarter with a canal exit under the water nearer the
    middle than the street door; Fields of Kummu with no door (the middle, no height); an unnamed exterior cell; a
    deleted door; a name longer than the field; a deleted cell."""
    out = rec('TES3', [sub('HEDR', b'\0' * 300)])
    out += cell('Seyda Neen', -2, -9, False)
    out += cell('seyda neen', -3, -9, False)                                      # one place, case ignored
    out += cell('', 0, 0, False, [ref(1, 'flora_tree', (100, 100, 50))])          # the wilderness: no place
    out += cell('Ald-ruhn', -2, 6, False, [ref(2, 'CocMarkerHeading', (-15000, 53000, 2400))])
    out += cell('Vivec, Foreign Quarter', 4, -10, False)
    out += cell('Fields of Kummu', 1, -5, False, [ref(3, 'flora_kelp_01', (12300, -36870, -50)),     # in the water
                                                  ref(4, 'ex_dae_shrine', (13000, -37000, 200)),      # on land
                                                  ref(5, 'NorthMarker', (12290, -36860, 300))])        # a marker
    out += cell('The Very Long Name Of A Place On Vvardenfell', 9, 9, False)
    out += rec('CELL', [sub('NAME', z('Deleted Town')), sub('DATA', struct.pack('<Iii', 0, 30, 30))], flags=0x20)
    out += cell('Arrille\'s Tradehouse', 0, 0, True, [
        ref(10, 'in_door_01', (0, 0, 0), destination=(-17000, -73000, 300)),          # street, nearer the middle
        ref(11, 'in_door_02', (0, 0, 0), destination=(-24000, -66000, 200)),
        ref(12, 'in_door_03', (0, 0, 0), destination=(-16390, -73730, 300), dest_cell='Seyda Neen, Cellar'),
        ref(13, 'in_door_04', (0, 0, 0), destination=(-16390, -73730, 300), deleted=True),
        ref(14, 'in_door_05', (0, 0, 0), destination=(-15500, 52000, 2300)),          # Ald-ruhn: the marker wins
        ref(15, 'in_door_06', (0, 0, 0), destination=(36864, -77824, -200)),          # under the water, the middle
        ref(16, 'in_door_07', (0, 0, 0), destination=(34000, -79000, 900)),           # the street
        ref(17, 'in_door_08', (0, 0, 0), destination=(74000, 74000, 100)),            # long name's own door
    ])
    return out


def land(x, y, height):
    """A flat LAND record at HEIGHT original units (VHGT: offset in 8-unit steps, no deltas)."""
    return rec('LAND', [sub('INTV', struct.pack('<ii', x, y)),
                        sub('VHGT', struct.pack('<f', height / 8.0) + b'\0' * (65 * 65) + b'\0\0\0')])


def street_master():
    """Bal Test on land (terrain 1700): a tower door nearest the middle (arrival 2850) and a street door (1800);
    Canton Test over the water (terrain -800): a high door nearest the middle (2042), a lower walkway door 640
    units away (1728) and a far lower one (576, 2000 away)."""
    out = rec('TES3', [sub('HEDR', b'\0' * 300)])
    out += cell('Bal Test', -5, 9, False) + land(-5, 9, 1700)
    out += cell('Canton Test', 4, -14, False) + land(4, -14, -800)
    out += cell('Ruin Hall', 0, 0, True, [
        ref(20, 'door_a', (0, 0, 0), destination=(-36860, 77830, 2850)),       # the tower top, at the middle
        ref(21, 'door_b', (0, 0, 0), destination=(-35378, 78451, 1800)),       # the street
        ref(22, 'door_c', (0, 0, 0), destination=(36860, -110590, 2042)),      # high walkway, at the middle
        ref(23, 'door_d', (0, 0, 0), destination=(37400, -110400, 1728)),      # lower walkway nearby
        ref(24, 'door_e', (0, 0, 0), destination=(38700, -109100, 576)),       # far and low
    ])
    return out


class StreetDoorTests(unittest.TestCase):
    def test_ground_and_water_rules(self):
        rows = {r['name']: r for r in T.read_table(T.build_master(street_master())[0])}
        self.assertEqual((rows['Bal Test']['x'], rows['Bal Test']['z']), (-35378, 1800 + T.LIFT))
        self.assertEqual((rows['Canton Test']['x'], rows['Canton Test']['z']), (37400, 1728 + T.LIFT))

    def test_land_heights_follow_the_rows(self):
        deltas = bytearray(65 * 65)
        deltas[0] = 2          # row 0 starts 2 steps up
        deltas[65] = 1         # row 1 starts one more step up
        deltas[65 + 3] = 5     # and rises 5 steps at column 3
        x, y, grid = T.land_heights([('INTV', struct.pack('<ii', 1, 2)),
                                     ('VHGT', struct.pack('<f', 10.0) + bytes(deltas) + b'\0\0\0')])
        self.assertEqual((x, y), (1, 2))
        self.assertEqual(grid[0][0], 96)                     # (10 + 2) x 8
        self.assertEqual((grid[1][0], grid[1][3], grid[1][64]), (104, 144, 144))
        self.assertEqual(T.ground_at({(1, 2): grid}, 8192 + 3 * 128, 2 * 8192 + 128), 144)
        self.assertIsNone(T.ground_at({}, 0, 0))


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.report = T.build_master(master())
        cls.rows = {r['name']: r for r in T.read_table(cls.raw)}

    def test_places_are_the_named_exterior_cells_sorted(self):
        names = [r['name'] for r in T.read_table(self.raw)]
        self.assertEqual(names, ['Ald-ruhn', 'Fields of Kummu', 'Seyda Neen', 'The Very Long Name Of A Place O',
                                 'Vivec, Foreign Quarter'])
        self.assertEqual(self.rows['Seyda Neen']['cells'], 2)
        self.assertEqual(self.report['names_cut'], ['The Very Long Name Of A Place On Vvardenfell'])
        self.assertEqual(self.report['resident_bytes'], 0)

    def test_arrival_order(self):
        self.assertEqual(self.rows['Ald-ruhn'], {'name': 'Ald-ruhn', 'x': -15000, 'y': 53000, 'z': 2400 + T.LIFT,
                                                 'flags': T.F_HAS_Z | T.F_COC, 'cells': 1})
        seyda = self.rows['Seyda Neen']
        self.assertEqual((seyda['x'], seyda['y'], seyda['z'], seyda['flags']),
                         (-17000, -73000, 300 + T.LIFT, T.F_HAS_Z | T.F_DOOR))
        vivec = self.rows['Vivec, Foreign Quarter']
        self.assertEqual((vivec['x'], vivec['y'], vivec['z']), (34000, -79000, 900 + T.LIFT))
        kummu = self.rows['Fields of Kummu']
        # no door: where the object nearest the middle stands on land (not the kelp, not the marker; no height)
        self.assertEqual((kummu['x'], kummu['y'], kummu['z'], kummu['flags']), (13000, -37000, 0, 0))
        self.assertEqual(self.report['arrivals'], {'coc_marker': 1, 'door': 3, 'cell_middle': 1})

    def test_file_layout(self):
        self.assertEqual(self.raw[:8], b'AWTP\x00\x01\x00\x30')
        self.assertEqual(len(self.raw), T.HEADER + 5 * T.ROW)
        with self.assertRaises(ValueError):
            T.read_table(self.raw[:-1])

    def test_same_input_same_bytes(self):
        self.assertEqual(T.build_master(master())[0], self.raw)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class RuleTests(unittest.TestCase):
    def test_search_keys_clicks_and_the_table_reader(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_listbox_test.c', [SRC / 'aw_listbox_rules.c'], cflags=UBSAN)


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


class EngineWiringTests(unittest.TestCase):
    def test_dbg_tp_without_argument_opens_the_box_else_the_scene_picker(self):
        scene = code('aw_scene.c')
        self.assertIn('if(Cmd_Argc()==1 && sv.active){if(!AW_TpPlacesOpen())Cbuf_InsertText("aw_scene_menu\\n");return;}',
                      scene)
        # the named places and the coordinate forms come first, unchanged
        self.assertLess(scene.index('Usage: dbg tp X Y [Z] (original Morrowind global coordinates)'),
                        scene.index('if(!AW_TpPlacesOpen())'))

    def test_the_table_is_read_only_while_the_box_is_open(self):
        places = code('aw_tpplaces.c')
        self.assertIn('static void closed(void *ctx){\n    (void)ctx;free(table);table=NULL;rows=0;\n}', places)
        self.assertIn('AW_TryMalloc((unsigned long)size)', places)
        self.assertIn('AW_TpPlacesCommand(&p,command,sizeof(command))', places)
        box = code('aw_listbox.c')
        self.assertIn('free(shown);shown=NULL;active=0;', box)
        self.assertIn('AW_WorldUIOpenPanel(draw,key,closed)', box)
        # drawn in the console font
        self.assertIn('AW_ConsoleCharacter(x,y,(unsigned char)*s);', box)
        # on top of the game: the view keeps drawing behind the box (aw_modal_black blanks it for other windows)
        self.assertIn('aw_listbox_over_world=over_world;aw_listbox_restore=restore;', box)
        ui = code('aw_ui.c')
        hidden = ui[ui.index('int AW_ModalWorldHidden(void) {'):]
        self.assertLess(hidden.index('if(box==1)return 0;'), hidden.index('if(box==2)return 1;'))
        self.assertLess(hidden.index('if(box==2)return 1;'),
                        hidden.index('return (AW_InventoryActive() || AW_ModalBlackBackground())'))
        # the world waits behind a box: rendered once, then its kept copy (TP-PICKER-OPEN-FRAME-COST-57)
        self.assertLess(box.index('keep();'), box.index('AW_UIBox(BOX_X,BOX_Y,BOX_W,BOX_H);'))
        self.assertIn('free(backdrop);backdrop=NULL;', box)
        screen = code('screen.c')
        self.assertIn('if(!(aw_listbox_restore && aw_listbox_restore ()))\n'
                      '            AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));', screen)

    def test_built_into_the_engine_and_the_image(self):
        make = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_msgbox.c aw_listbox_rules.c aw_listbox.c aw_tpplaces.c', make)
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("tp_places_step(args.data_files, boot/'id1', out, jobs=jobs)", build)
        self.assertEqual(code('aw_tpplaces.c').count('"tp-places.lut"'), 1)
        self.assertEqual(T.NAME, 'tp-places.lut')


if __name__ == '__main__':
    unittest.main()
