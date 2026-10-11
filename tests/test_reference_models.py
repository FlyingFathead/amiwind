# SPDX-License-Identifier: GPL-3.0-only
"""Reference models are recipes checked by SHA-256 (tools/reference_models.py, config/reference-models.json,
docs/chim/REFERENCE_MODELS.md): the config agrees with the converter profile it names, every step has a
recorded hash, the hashes are canonical, and a mismatch warns with the step's name instead of failing."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import reference_models as RM  # noqa: E402


class ReferenceModelConfigTests(unittest.TestCase):
    def test_config_names_a_profile_and_every_step(self):
        data = RM.load()
        self.assertEqual(data['format'], 'amiwind-reference-models-1')
        for row in data['models']:
            profile = RM.profile_of(row)
            for key in ('ratio', 'lock_boundaries', 'texture_size'):
                self.assertEqual(profile.get(key), row['method'][key], (row['name'], key))
            for step in RM.STEPS:
                sha = row['expected']['sha256'][step]
                self.assertEqual(len(sha), 64, (row['name'], step))
                int(sha, 16)

    def test_base_silt_strider(self):
        row = next(r for r in RM.load()['models'] if r['name'] == 'base silt strider')
        self.assertEqual(row['source'], 'meshes/r/siltstrider.nif')
        self.assertEqual(row['expected']['counts']['faces'], 3219)
        self.assertEqual(RM.profile_of(row)['ratio'], 0.45)

    def test_reference_models_doc_lists_every_model(self):
        text = (ROOT / 'docs/chim/REFERENCE_MODELS.md').read_text(encoding='utf-8')
        for row in RM.load()['models']:
            self.assertIn(row['source'], text)
            for step in RM.STEPS:
                self.assertIn(row['expected']['sha256'][step], text)


class ReferenceModelHashTests(unittest.TestCase):
    def test_mesh_hash_is_canonical(self):
        v = np.array([[0.0, 1.0000001, -0.0, 0.5, 0.25], [1, 2, 3, 0, 0], [3, 2, 1, 1, 1]])
        f = np.array([[0, 1, 2, 0]])
        same = v.copy()
        same[0, 2] = 0.0                  # no negative zero
        same[0, 1] = 1.0000004            # below the 1e-6 rounding
        self.assertEqual(RM.mesh_hash(v, f), RM.mesh_hash(same, f))
        moved = v.copy()
        moved[1, 0] += 1e-4
        self.assertNotEqual(RM.mesh_hash(v, f), RM.mesh_hash(moved, f))

    def test_faces_hash_follows_order_and_material(self):
        q = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0.0]])
        a = (q, 0, np.eye(3)[:, :2], np.zeros(2), np.array([0, 0, 1.0]))
        b = (q + 1, 1, np.eye(3)[:, :2], np.zeros(2), np.array([0, 0, 1.0]))
        self.assertNotEqual(RM.faces_hash([a, b]), RM.faces_hash([b, a]))
        self.assertEqual(RM.faces_hash([a, b]), RM.faces_hash([a, b]))

    def test_mismatch_warns_with_the_step(self):
        row = RM.load()['models'][0]
        expected = row['expected']['sha256']
        got = dict(expected, reduced='0' * 64, faces='1' * 64, counts={}, profile={})
        warnings = []
        with mock.patch.object(RM, 'compute', return_value=got), \
                mock.patch('world_estimate_data.MeshSource', return_value=object()):
            report = RM.check('/nowhere', warn=warnings.append)
        self.assertEqual(report['models'][0]['status'], 'differs at reduced')
        self.assertEqual(len(warnings), 1)
        self.assertIn('"reduced"', warnings[0])
        with mock.patch.object(RM, 'compute', return_value=dict(expected, counts={}, profile={})), \
                mock.patch('world_estimate_data.MeshSource', return_value=object()):
            self.assertEqual(RM.check('/nowhere', warn=warnings.append)['models'][0]['status'], 'ok')
        self.assertEqual(len(warnings), 1)

    def test_missing_source_is_a_warning(self):
        warnings = []
        with mock.patch.object(RM, 'compute', side_effect=FileNotFoundError('x')), \
                mock.patch('world_estimate_data.MeshSource', return_value=object()):
            report = RM.check('/nowhere', warn=warnings.append)
        self.assertEqual(report['models'][0]['status'], 'source not in the data files')
        self.assertTrue(warnings)
        json.dumps(report)


if __name__ == '__main__':
    unittest.main()
