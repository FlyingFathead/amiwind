# SPDX-License-Identifier: GPL-3.0-only
"""Unknown or modified assets must not inherit measured replacement policies."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from visual_recipes import apply_recipe


class RecipeIdentity(unittest.TestCase):
    def setUp(self):
        self.profile = {'ratio': 0.8, 'collision_none': False}
        self.model = {'source': 'Meshes\\X\\example.nif', 'sha256': 'a' * 64}
        self.data = {'recipes': {'trial': {'models': {'meshes/x/example.nif':
                    {'sha256': 'a' * 64, 'ratio': 0.1, 'error_share': 0.025}}}}}

    def test_exact_match_changes_visual_profile_only(self):
        result = apply_recipe(self.profile, self.model, 'trial', self.data)
        self.assertEqual(result['ratio'], 0.1)
        self.assertEqual(result['meshopt_error_share'], 0.025)
        self.assertFalse(result['collision_none'])
        self.assertEqual(self.profile, {'ratio': 0.8, 'collision_none': False})

    def test_modified_source_keeps_original_profile(self):
        self.model['sha256'] = 'b' * 64
        self.assertIs(apply_recipe(self.profile, self.model, 'trial', self.data), self.profile)

    def test_optimizer_revision_changes_profile_cache_identity(self):
        with patch('mesh_methods.meshopt_sha', return_value='a' * 64):
            first = apply_recipe(self.profile, self.model, 'trial', self.data)
        with patch('mesh_methods.meshopt_sha', return_value='b' * 64):
            second = apply_recipe(self.profile, self.model, 'trial', self.data)
        self.assertNotEqual(first['method_version'], second['method_version'])

    def test_primitive_requires_matching_identity_too(self):
        entry = self.data['recipes']['trial']['models']['meshes/x/example.nif']
        entry['primitive'] = {'kind': 'lantern_shell'}
        result = apply_recipe(self.profile, self.model, 'trial', self.data)
        self.assertEqual(result['visual_primitive'], entry['primitive'])
        self.assertFalse(result['collision_none'])
        self.model['sha256'] = 'b' * 64
        self.assertIs(apply_recipe(self.profile, self.model, 'trial', self.data), self.profile)

    def test_missing_hash_is_not_a_match(self):
        del self.model['sha256']
        self.assertIs(apply_recipe(self.profile, self.model, 'trial', self.data), self.profile)

    def test_same_hash_different_asset_is_not_a_match(self):
        self.model['source'] = 'meshes/x/other.nif'
        self.assertIs(apply_recipe(self.profile, self.model, 'trial', self.data), self.profile)

    def test_invalid_error_refused(self):
        self.data['recipes']['trial']['models']['meshes/x/example.nif']['error_share'] = float('nan')
        with self.assertRaises(ValueError):
            apply_recipe(self.profile, self.model, 'trial', self.data)

    def test_default_recipe_tolerance_is_explicit_and_scoped(self):
        self.data['recipes']['trial'].update(default_visual_ratio=0.2, default_error_share=0.01)
        self.model['source'] = 'meshes/x/other.nif'
        result = apply_recipe(self.profile, self.model, 'trial', self.data)
        self.assertEqual(result['ratio'], 0.2)
        self.assertEqual(result['meshopt_error_share'], 0.01)
        self.assertFalse(result['collision_none'])
        self.assertNotIn('meshopt_error_share', self.profile)
        self.model['source'] = 'meshes/x/terrain_rock_01.nif'
        self.assertIs(apply_recipe(self.profile, self.model, 'trial', self.data), self.profile)

    def test_default_recipe_rejects_invalid_tolerance(self):
        self.data['recipes']['trial'].update(default_visual_ratio=0.2, default_error_share=float('nan'))
        self.model['source'] = 'meshes/x/other.nif'
        with self.assertRaises(ValueError):
            apply_recipe(self.profile, self.model, 'trial', self.data)


class CollisionToleranceRecipes(unittest.TestCase):
    """A recipe entry may coarsen one mesh's collision pieces (collision_tolerance, 2-32 units)."""

    def doc(self, entry):
        return {'format': 1, 'recipes': {'t': {'models': {'meshes/x/root.nif': dict(entry, sha256='a' * 64)}}}}

    def test_tolerance_only_entry_keeps_the_drawn_mesh(self):
        from visual_recipes import apply_recipe
        out = apply_recipe({'ratio': 1}, {'source': 'meshes/x/root.nif', 'sha256': 'a' * 64}, 't',
                           self.doc({'collision_tolerance': 8}))
        self.assertEqual((out['collision_tolerance'], out['ratio']), (8.0, 1))

    def test_tolerance_bounds(self):
        from visual_recipes import apply_recipe
        with self.assertRaises(ValueError):
            apply_recipe({}, {'source': 'meshes/x/root.nif', 'sha256': 'a' * 64}, 't', self.doc({'collision_tolerance': 1}))

    def test_other_mesh_hash_keeps_default_collision(self):
        from visual_recipes import apply_recipe
        out = apply_recipe({'ratio': 1}, {'source': 'meshes/x/root.nif', 'sha256': 'b' * 64}, 't',
                           self.doc({'collision_tolerance': 8}))
        self.assertNotIn('collision_tolerance', out)


class OriginalCellRecipes(unittest.TestCase):
    def setUp(self):
        self.document = {'cell_settings': {'10,1': {'visual_recipe': 'trial', 'clip_to_terrain': True}}}
        self.index = {'models': [{'source': 'meshes/x/root.nif', 'sha256': 'a' * 64}],
                      'references': [{'number': 1, 'cell': [10, 1], 'model_index': 0, 'position': [10, 20, 30]},
                                     {'number': 2, 'cell': [10, 0], 'model_index': 0, 'position': [40, 50, 60]}]}

    def bind(self, home):
        from visual_recipes import scope_reference_recipes
        return scope_reference_recipes(self.index, {'source_cell': home}, self.document)

    def test_original_policy_matches_on_both_sides(self):
        home, apron = self.bind([10, 1]), self.bind([10, 0])
        self.assertEqual(home, apron)
        ref = apron['references'][0]
        model = apron['models'][ref['model_index']]
        self.assertEqual(model['_visual_recipe'], 'trial')
        self.assertTrue(model['_clip_to_terrain'])

    def test_shared_mesh_keeps_unrelated_placement_ordinary(self):
        out = self.bind([10, 1])
        a, b = out['references']
        self.assertNotEqual(a['model_index'], b['model_index'])
        self.assertIsNone(out['models'][b['model_index']]['_visual_recipe'])
        self.assertFalse(out['models'][b['model_index']]['_clip_to_terrain'])
        self.assertEqual([x['position'] for x in out['references']], [[10, 20, 30], [40, 50, 60]])
        self.assertEqual(self.index['references'][1]['model_index'], 0)
        self.assertNotIn('_visual_recipe', self.index['models'][0])

    def test_explicit_recipe_does_not_leak_to_foreign_cell(self):
        from visual_recipes import scope_reference_recipes
        out = scope_reference_recipes(self.index, {'source_cell': [10, 1], 'visual_recipe': 'trial'}, self.document)
        b = out['references'][1]
        self.assertIsNone(out['models'][b['model_index']]['_visual_recipe'])

    def test_empty_reference_set_preserves_mount_models(self):
        from visual_recipes import scope_reference_recipes
        index = dict(self.index, references=[])
        out = scope_reference_recipes(index, {'source_cell': [10, 0]}, self.document)
        self.assertEqual(out['models'][0]['sha256'], 'a' * 64)
        self.assertEqual(out['references'], [])
