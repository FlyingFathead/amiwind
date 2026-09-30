import unittest
from unittest.mock import patch
from balmora_regions import config, regions, owner, audit_coverage, select_references, visual_profile


class BalmoraTests(unittest.TestCase):
    def test_shared_strider_settings_follow_the_seyda_profile(self):
        shared = {'ratio': .6, 'texture_size': 64, 'collision_source': 'root_node'}
        groups = {'silt_strider': {'visual_profiles': {'meshes/r/siltstrider.nif': shared}}}
        with patch('scenery_selection.load_groups', return_value=groups):
            a = visual_profile('R\\Siltstrider.NIF', 5600)
            self.assertEqual(a, shared)
            a['ratio'] = .1
            self.assertEqual(visual_profile('meshes/r/siltstrider.nif', 5600)['ratio'], .6)

    def test_open_architecture_is_not_collapsed_to_a_prop_triangle_budget(self):
        for source in ('meshes/x/ex_hlaalu_b_07.nif', 'meshes/x/ex_hlaalu_steps_06.nif',
                       'meshes/d/ex_h_trapdoor_01.nif', 'meshes/f/furn_de_sign_01.nif'):
            self.assertEqual(visual_profile(source, 738)['ratio'], 1.)
        self.assertLess(visual_profile('meshes/f/flora_tree_01.nif', 700)['ratio'], 1.)
        self.assertEqual(visual_profile('meshes/t/terrain_rock_01.nif', 640)['ratio'], .1)

    def test_reported_underpasses_preserve_authored_collision_openings(self):
        for source in ('meshes/x/ex_hlaalu_bridge_07.nif', 'X\\Ex_Velothi_Temple_02.NIF'):
            self.assertTrue(visual_profile(source, 735)['hollow_collision'])

    def test_every_core_crosses_both_directions_with_hysteresis(self):
        s = config(); entries = regions(s)
        for i, entry in enumerate(entries):
            centre = [(a+b)/2 for a,b in zip(*entry['core'])]
            self.assertEqual(owner(centre, entries), i)
            for axis in range(2):
                for sign in (-1, 1):
                    p = centre.copy(); edge = entry['core'][sign > 0][axis]
                    p[axis] = edge + sign*s['hysteresis']
                    self.assertEqual(owner(p, entries, i, s['hysteresis']), i)
                    p[axis] += sign
                    target = owner(p, entries, i, s['hysteresis'])
                    if target is None: continue
                    self.assertNotEqual(target, i)
                    self.assertEqual(owner(centre, entries, target, s['hysteresis']), i)

    def test_long_object_is_included_when_origin_is_outside_region(self):
        s = config(); entries = regions(s); s['centre']=[0,0]; s['scale']=1
        ref = {'number': 91, 'position': [2500,0,0], 'bounds':[[-2500,-10,0],[2600,10,100]]}
        index = {'references':[ref]}
        self.assertIn(91, select_references(index, entries[owner([-2800,0], entries)], s))
        self.assertEqual(audit_coverage(index, entries, s)['lost_references'], [])

    def test_invalid_positions_and_insufficient_diagonal_overlap(self):
        s=config(); entries=regions(s)
        with self.assertRaises(ValueError): owner([float('nan'),0],entries)
        s['overlap']=768
        with self.assertRaises(ValueError): regions(s)
