"""The focus table with the expansions selected (EXPANSION-BASE-ONLY-TABLES-66): every named activator and container
the selected masters place has its measured box, checked before any stage (tools/build.py focus_box_preflight), and
the tables keyed by room number take every selected master's rooms (tools/cell_numbers.py room_numbers).

Hand-made masters only; no game data is read here.
"""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_focus as focus
import cell_numbers


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def ref(number, ident):
    return (sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident)) +
            sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0)))


def master(model, tag='ACTI', placed=True, name='Stone', flag=8):
    extra = [sub('FLAG', struct.pack('<I', flag))] if tag == 'CONT' else []
    cell = rec('CELL', sub('NAME', z('Room')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
               *([ref(5, 'thing')] if placed else []))
    return rec(tag, sub('NAME', z('thing')), sub('FNAM', z(name)), sub('MODL', z(model)), *extra) + cell


class MissingBoxTests(unittest.TestCase):
    def test_an_unmeasured_placed_activator_is_named_before_any_stage(self):
        self.assertEqual(focus.missing_boxes(master('f\\not_measured.nif')), [('N', 'f\\not_measured.nif', 'thing')])

    def test_a_measured_expansion_activator_passes(self):
        self.assertIn('f\\act_bm_stone_beast_01.nif', focus.FOCUS_BOXES)   # the one the dev2 focus stage met
        self.assertEqual(focus.missing_boxes(master('f/Act_BM_Stone_Beast_01.nif')), [])

    def test_unplaced_unnamed_and_invisible_activators_need_no_box(self):
        self.assertEqual(focus.missing_boxes(master('f\\not_measured.nif', placed=False)), [])
        self.assertEqual(focus.missing_boxes(master('f\\not_measured.nif', name='')), [])
        self.assertEqual(focus.missing_boxes(master('EditorMarker.nif')), [])

    def test_containers_need_a_box_unless_picked_in_the_world(self):
        self.assertEqual(focus.missing_boxes(master('o\\odd.nif', tag='CONT')), [('C', 'o\\odd.nif', 'thing')])
        self.assertEqual(focus.missing_boxes(master('o\\contain_bm_stalhrim_01.nif', tag='CONT')), [])
        # PLANT-BOX-AIM-69: an organic container opens its window unless a harvest kind covers its model
        # (FARGOTH-STASH-STUMP-69), so it needs its box as any other that opens; one of a harvest kind (a mushroom) is
        # picked in the world and needs none (before, every organic container was left out)
        self.assertEqual(focus.missing_boxes(master('o\\odd.nif', tag='CONT', flag=9)), [('C', 'o\\odd.nif', 'thing')])
        self.assertEqual(focus.missing_boxes(master('f\\flora_bc_mushroom_01.nif', tag='CONT', flag=9)), [])
        self.assertEqual(focus.missing_boxes(master('o\\flora_wickwheat_01.nif', tag='CONT', flag=9)), [])

    def test_the_build_runs_the_preflight_before_any_stage(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertEqual(text.count('problem = focus_box_preflight(args)'), 2)   # the build and its --check


class RoomNumberTests(unittest.TestCase):
    def test_every_selected_masters_rooms_are_numbered(self):
        table = cell_numbers.number_cells([('Morrowind.esm', ['B', 'A']), ('Tribunal.esm', ['Mournhold, Plaza'])])
        self.assertEqual(cell_numbers.room_numbers(table), {'a': 1, 'b': 2, 'mournhold, plaza': 3})


if __name__ == '__main__':
    unittest.main()
