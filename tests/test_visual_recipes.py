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
