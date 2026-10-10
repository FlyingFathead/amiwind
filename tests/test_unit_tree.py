# SPDX-License-Identifier: GPL-3.0-only
"""Hierarchical stage output hashes (tools/unit_tree.py): units -> segments -> stage."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import unit_tree  # noqa: E402

FILES = {
    'world-terrain/vf0123/scene.bsp': '1' * 64, 'world-terrain/vf0123/conversion.json': '2' * 64,
    'world-terrain/vf0124/scene.bsp': '3' * 64, 'world-terrain/vf0245/scene.bsp': '4' * 64,
    'world-terrain/vf0124/compile.log': '5' * 64,
    'intro-scene/area-work/bmtemple/room.bsp': '6' * 64, 'intro-scene/id1/maps/bm007.bsp': '7' * 64,
    'intro-scene/id1/character/h106.awh': '8' * 64, 'world-terrain/world-regions.json': '9' * 64,
}


class PlaceTests(unittest.TestCase):
    def test_units_and_segments(self):
        self.assertEqual(unit_tree.place('world-terrain/vf0123/scene.bsp'), ('world-terrain:vf01', 'vf0123'))
        self.assertEqual(unit_tree.place('intro-scene/area-work/bmtemple/room.bsp'),
                         ('intro-scene/area-work:other', 'bmtemple'))
        self.assertEqual(unit_tree.place('intro-scene/id1/maps/bm007.bsp'), ('intro-scene/id1/maps:bm0', 'bm007'))
        self.assertEqual(unit_tree.place('intro-scene/id1/character/h106.awh'),
                         ('intro-scene/id1/character:h1', 'h106'))
        self.assertEqual(unit_tree.place('world-terrain/world-regions.json'), ('world-terrain', 'world-regions.json'))


class TreeTests(unittest.TestCase):
    def test_same_outputs_same_tree_and_diagnostics_do_not_count(self):
        a = unit_tree.tree(FILES)
        b = unit_tree.tree(dict(FILES, **{'world-terrain/vf0124/compile.log': 'f' * 64}))
        self.assertEqual(a, b)
        self.assertEqual(unit_tree.differences(a, b), [])
        self.assertEqual(sorted(a['segments']['world-terrain:vf01']['units']), ['vf0123', 'vf0124'])

    def test_a_change_names_its_segment_and_unit_only(self):
        a = unit_tree.tree(FILES)
        b = unit_tree.tree(dict(FILES, **{'world-terrain/vf0124/scene.bsp': 'e' * 64}))
        found = unit_tree.differences(b, a)
        self.assertEqual(found, [('world-terrain:vf01', 'vf0124', 'changed')])
        self.assertEqual(a['segments']['world-terrain:vf02'], b['segments']['world-terrain:vf02'])
        self.assertNotEqual(a['stage_hash'], b['stage_hash'])
        added = unit_tree.tree(dict(FILES, **{'world-terrain/vf0900/scene.bsp': 'd' * 64}))
        self.assertEqual(unit_tree.differences(added, a), [('world-terrain:vf09', None, 'added')])
        self.assertIn('world-terrain:vf01/vf0124 changed', unit_tree.describe(found))

    def test_order_does_not_matter(self):
        self.assertEqual(unit_tree.tree(FILES), unit_tree.tree(dict(reversed(list(FILES.items())))))


if __name__ == '__main__':
    unittest.main()
