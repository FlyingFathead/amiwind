"""HELD-BLADE-EDGE-ON-61: a weapon's item model is at least npc_items.ITEM_MIN_THICKNESS thick along its thinnest axis
(seen edge-on from behind, a held blade of a few tenths of a unit drew no pixel); other items keep their shape."""
import os
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import npc_items  # noqa: E402


class HeldBladeThickness(unittest.TestCase):
    def test_thin_axis_spread_about_its_middle(self):
        blade = np.array([[[0, 0, -0.2], [2, 28, 0.27], [-2, 10, 0], [1, -3, 0.1]]], float)   # 28.7 long, 0.47 thick
        out = npc_items.thicken(blade, 1.0)
        extent = out[0].max(axis=0) - out[0].min(axis=0)
        self.assertAlmostEqual(extent[2], 1.0, places=6)
        np.testing.assert_allclose(out[..., :2], blade[..., :2])                     # length and width unchanged
        self.assertAlmostEqual((out[0, :, 2].max() + out[0, :, 2].min()) / 2, 0.035, places=6)   # same middle

    def test_thick_enough_flat_or_off_unchanged(self):
        thick = np.array([[[0, 0, 0], [3, 20, 2]]], float)
        np.testing.assert_array_equal(npc_items.thicken(thick, 1.0), thick)
        card = np.array([[[0, 0, 0], [3, 20, 0]]], float)
        np.testing.assert_array_equal(npc_items.thicken(card, 1.0), card)
        thin = np.array([[[0, 0, 0], [3, 20, 0.3]]], float)
        np.testing.assert_array_equal(npc_items.thicken(thin, 0), thin)

    def test_weapons_only_and_the_switch(self):
        self.assertTrue(npc_items.is_weapon_mesh('w\\W_claymore.nif'))
        self.assertTrue(npc_items.is_weapon_mesh('meshes/w/w_iron_dagger.nif'))
        self.assertFalse(npc_items.is_weapon_mesh('m\\misc_com_plate_01.nif'))
        self.assertFalse(npc_items.is_weapon_mesh('a\\a_steel_shield.nif'))
        old = os.environ.pop(npc_items.ITEM_MIN_THICKNESS_ENV, None)
        try:
            self.assertEqual(npc_items.item_min_thickness(), npc_items.ITEM_MIN_THICKNESS)
            os.environ[npc_items.ITEM_MIN_THICKNESS_ENV] = '0'
            self.assertEqual(npc_items.item_min_thickness(), 0)
            os.environ[npc_items.ITEM_MIN_THICKNESS_ENV] = '9'
            with self.assertRaises(ValueError):
                npc_items.item_min_thickness()
        finally:
            os.environ.pop(npc_items.ITEM_MIN_THICKNESS_ENV, None)
            if old is not None:
                os.environ[npc_items.ITEM_MIN_THICKNESS_ENV] = old


if __name__ == '__main__':
    unittest.main()
