# SPDX-License-Identifier: GPL-3.0-only
"""Flora cards and the base depth push (BC-TREE-FLOATING-60, SEYDA-WALL-SHAPE-31).

The engine pushed the bottom quarter of every flora card's rows an eighth of the card's width back in the depth test,
so a trunk base no longer drew over a wall just behind it. On a slope the ground behind every trunk then covered the
pushed rows: trunks ended in a flat cut above the ground and the trees seemed to float. Now the push stays only on the
cards the builder marks ("aw_depth_push" "1": the card base meets a wall's or building's box), chosen by
chim.frame_map.flora_push_refs for every frame map (towns, specials, region frames), and the engine pushes only those
(r_sprite.c aw_flora_push_mode)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

from chim import frame_map as FM  # noqa: E402

SRC = ROOT / 'engine/aga/src'


def sprite(width, height, top):
    """A single-frame IDSP sprite of WIDTH x HEIGHT whose origin is TOP rows below its first row."""
    raw = struct.pack('<4siifiiifi', b'IDSP', 1, 2, float(max(width, height)), width, height, 1, 0.0, 0)
    raw += struct.pack('<5i', 0, -width // 2, top, width, height)
    return raw + bytes([255]) * (width * height)


def card(ref, x, y, z, scale=1.0, model='progs/aw_flora/f_0000000000000001.spr'):
    return {'classname': 'aw_flora', 'model': model, 'aw_ref': str(ref), 'aw_scale': '%g' % scale,
            'origin': '%g %g %g' % (x, y, z), 'angles': '0 0 0'}


class FloraPush(unittest.TestCase):
    def setUp(self):
        # a card 80 wide and 100 high, origin 60 rows down: its bottom 40 under the origin, the pushed rows (the
        # bottom quarter, 25 rows) from 40 to 15 under it, reaching 10 (80 / 8) around the trunk
        self.cards = {'progs/aw_flora/f_0000000000000001.spr': FM.sprite_card(sprite(80, 100, 60))}
        self.models = {0: {'name': 'x/ex_drystonewall_c_01@s1'}, 1: {'name': 'f/flora_bc_tree_02.nif#collision_only@s2'},
                       2: {'name': 'x/flora_ashtree_04@s2#2'}, 3: {'name': 'f/terrain_rocks_ai_02@s1'}}

    def chunks(self, *placed):
        return [{'owned': [{'model': m, 'box': box} for m, box in placed]}]

    def test_sprite_card_reads_the_frame(self):
        self.assertEqual(FM.sprite_card(sprite(80, 100, 60)), (80, 100, 60))
        with self.assertRaises(ValueError):
            FM.sprite_card(b'IDPO' + bytes(60))

    def test_only_walls_and_buildings_count(self):
        self.assertTrue(FM.flora_wall_model('x/ex_drystonewall_c_01@s1'))
        self.assertTrue(FM.flora_wall_model('x/terrain_ashland_rock_03@s2'))
        for name in ('f/flora_bc_tree_02.nif#collision_only@s2', 'x/flora_ashtree_04@s2#2', 'f/terrain_rocks_ai_02@s1',
                     'F/Flora_BC_Tree_01'):
            self.assertFalse(FM.flora_wall_model(name), name)

    def test_a_base_in_a_wall_box_is_marked(self):
        wall = ((5, -50, -100), (20, 50, 200))           # 5 units beside the trunk, through the pushed rows' heights
        rows = [card(1, 0, 0, 100)]
        refs, why = FM.flora_push_refs(rows, self.chunks((0, wall)), self.models, self.cards)
        self.assertEqual(refs, {'1'})
        self.assertEqual(why['1'], 'x/ex_drystonewall_c_01@s1')
        self.assertEqual(FM.mark_flora_push(rows, refs), 1)
        self.assertEqual(rows[0][FM.FLORA_PUSH_KEY], '1')

    def test_a_tree_on_open_ground_or_by_other_trees_is_not(self):
        rows = [card(1, 0, 0, 100)]
        far = ((30, -50, -100), (40, 50, 200))            # more than 10 (80 / 8) from the trunk
        high = ((5, -50, 90), (20, 50, 200))             # above the pushed rows (60..85)
        tree = ((-50, -50, -100), (50, 50, 300))         # another tree, an ash tree under x/, a rock under f/
        for placed in ((0, far), (0, high), (1, tree), (2, tree), (3, tree)):
            refs, _ = FM.flora_push_refs(rows, self.chunks(placed), self.models, self.cards)
            self.assertEqual(refs, set(), placed)
        self.assertEqual(FM.flora_push_refs(rows, [], self.models, self.cards), (set(), {}))
        self.assertEqual(FM.mark_flora_push(rows, set()), 0)
        self.assertNotIn(FM.FLORA_PUSH_KEY, rows[0])

    def test_the_card_scale_scales_the_base(self):
        # at scale 2 the pushed rows reach 20 around the trunk and lie 80..30 under the origin
        wall = ((15, -50, 30), (25, 50, 40))
        self.assertEqual(FM.flora_push_refs([card(1, 0, 0, 100)], self.chunks((0, wall)), self.models, self.cards)[0], set())
        self.assertEqual(FM.flora_push_refs([card(1, 0, 0, 100, 2)], self.chunks((0, wall)), self.models, self.cards)[0],
                         {'1'})

    def test_the_world_model_list_works_too(self):
        wall = ((5, -50, -100), (20, 50, 200))
        models = [{'name': 'x/ex_drystonewall_c_01@s1'}]
        self.assertEqual(FM.flora_push_refs([card(1, 0, 0, 100)], self.chunks((0, wall)), models, self.cards)[0], {'1'})

    def test_every_frame_map_writer_marks_its_cards(self):
        text = (ROOT / 'tools/chim/frame_map.py').read_text(encoding='utf-8')
        self.assertEqual(text.count("report['flora_push'] = flag_flora_push(id1, rows, world, index)"), 2)
        self.assertEqual(text.count("mark_flora_push(rows, set(task.get('flora_push', ())))"), 2)
        self.assertIn("task['flora_push'] = sorted(refs)", text)
        self.assertIn("**({'flora_push': task['flora_push']} if task.get('flora_push') else {})", text)
        # the engine's numbers are the builder's
        render = (SRC / 'render.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_FLORA_DEPTH_PUSH_FRAC %gf' % FM.FLORA_PUSH_FRAC, render)
        self.assertIn('#define AW_FLORA_BASE_SHARE %gf' % FM.FLORA_BASE_SHARE, render)

    def test_engine_reads_the_mark_and_pushes_only_marked_cards_by_default(self):
        statics = (SRC / 'chim/chim_statics.c').read_text(encoding='utf-8')
        self.assertIn('"%s"' % FM.FLORA_PUSH_KEY, statics)
        self.assertIn('(push ? 2 : 1)', statics)
        sprite_c = (SRC / 'r_sprite.c').read_text(encoding='utf-8')
        self.assertIn('int aw_flora_push_mode = AW_FLORA_PUSH_MARKED;', sprite_c)
        self.assertIn('ent->aw_flora != 2', sprite_c)


if __name__ == '__main__':
    unittest.main()
