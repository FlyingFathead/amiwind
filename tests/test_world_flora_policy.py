# SPDX-License-Identifier: GPL-3.0-only
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from world_flora_policy import balmora_source_zone, load_policy, placement, selection_receipt, stable_sprite_name, transformed_bounds

HASH = 'a' * 64

def ref(number=1, position=None, scale=1, rotation=None):
    return {'number': number, 'cell': [0, 0], 'id': 'tree', 'model': 'f/tree.nif', 'type': 'STAT',
            'position': position or [0, 0, 100], 'scale': scale, 'rotation_radians': rotation or [0, 0, 0]}

def policy(enabled=True):
    return {'mesh_exclusion': {'enabled': enabled, 'source_bounds': [[-10, -10], [10, 10]]}}

class WorldFloraPolicyTests(unittest.TestCase):
    def test_current_balmora_zone_uses_core_without_adding_draw_apron(self):
        p = load_policy()
        self.assertEqual(p['mesh_exclusion']['source_bounds'], [[-32768, -24576], [-8192, 0]])
        s = {'centre': [20, 30], 'scale': .25, 'bounds': [[-8, -4], [8, 4]], 'overlap': 99999}
        self.assertEqual(balmora_source_zone(s), [[-12, 14], [52, 46]])

    def test_clockwise_rotation_and_exact_nonunit_scale_are_preserved(self):
        r = ref(position=[40, 50, 60], scale=2.37, rotation=[0, 0, math.pi / 2])
        saved = copy.deepcopy(r)
        b = transformed_bounds([[0, 0, 0], [10, 20, 30]], r)
        self.assertAlmostEqual(b[0][0], 40)
        self.assertAlmostEqual(b[0][1], 50 - 23.7)
        self.assertAlmostEqual(b[1][0], 40 + 47.4)
        self.assertAlmostEqual(b[1][2], 60 + 71.1)
        p = placement(r, [[0, 0, 0], [10, 20, 30]], policy(), HASH)
        self.assertEqual(p['scale'], r['scale'])
        self.assertEqual(p['rotation_radians'], r['rotation_radians'])
        self.assertEqual(r, saved)
        self.assertFalse(p['runtime_activation'])

    def test_whole_footprint_crossing_uses_one_mesh_policy_outside_origin(self):
        r = ref(position=[14, 0, -900], scale=2)
        p = placement(r, [[-3, -1, -2], [3, 1, 2]], policy(), HASH)
        self.assertEqual(p['renderer_policy'], 'mesh')
        self.assertTrue(p['exclusion_boundary_crossing'])
        self.assertEqual(placement(r, [[-3, -1, -2], [3, 1, 2]], policy(False), HASH)['renderer_policy'], 'sprite')

    def test_original_keys_preserve_coincident_instances_and_reject_duplicate_keys(self):
        items = [placement(ref(n), [[-1, -1, -1], [1, 1, 1]], policy(), HASH) for n in (1, 2)]
        self.assertEqual(selection_receipt(items)['original_instances'], 2)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            selection_receipt(items + [items[0]])

    def test_invalid_scales_and_nonfinite_transforms_fail_instead_of_skipping(self):
        for scale in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                placement(ref(scale=scale), [[0, 0, 0], [1, 1, 1]], policy(), HASH)
        with self.assertRaises(ValueError):
            placement(ref(rotation=[0, math.nan, 0]), [[0, 0, 0], [1, 1, 1]], policy(), HASH)

    def test_interactive_stump_semantics_and_scaled_tilt_are_retained(self):
        r = ref(position=[100, 100, 10], scale=.27, rotation=[.23, -.41, .8]);r['type'] = 'CONT'
        p = placement(r, [[-1, -3, -5], [2, 4, 6]], policy(), HASH)
        receipt = selection_receipt([p])
        self.assertTrue(p['requires_interaction'])
        self.assertEqual(receipt['nonunit_scale_instances'], 1)
        self.assertEqual(receipt['tilted_instances'], 1)
        self.assertEqual(receipt['sprite_instances'], 1)
        self.assertEqual(p['position'], r['position'])

    def test_asset_name_is_model_stable_and_independent_of_scene_index(self):
        self.assertEqual(stable_sprite_name('meshes/F/Flora_TREE_01.NIF'), stable_sprite_name('f\\flora_tree_01.nif'))
        self.assertNotEqual(stable_sprite_name('f/tree_01.nif'), stable_sprite_name('f/tree_02.nif'))

if __name__ == '__main__': unittest.main()
