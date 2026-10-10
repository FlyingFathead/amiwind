# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-UNIT-FP-SOURCE-LAYOUT-33: CHIM unit keys come from content. The same mesh from two source stages
(another archive offset, another position in the stage's texture list) is the same mesh unit, variant and
texture; different content is a different unit; texture keys in unit results hold no stage index."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.build import canonical_materials, mesh_fingerprint  # noqa: E402
from chim.models import material_texture_key  # noqa: E402

TEX_A = {'source': 'a.tga', 'sha256': 'aa' * 32, 'offset': 0, 'bytes': 10, 'width': 64, 'height': 64}
TEX_B = {'source': 'b.tga', 'sha256': 'bb' * 32, 'offset': 10, 'bytes': 10, 'width': 64, 'height': 64}


def model(offset, tex_a, tex_b, sha='11' * 32):
    return {'source': 'meshes/x/thing.nif', 'source_sha256': 'ff' * 32, 'vertices': 8, 'triangles': 12,
            'bounds': [[0, 0, 0], [1, 1, 1]], 'textures': [tex_a, tex_b],
            'materials': [{'texture_source': 'a.tga', 'diffuse': [1, 1, 1], 'texture_index': tex_a},
                          {'texture_source': 'b.tga', 'diffuse': [1, 1, 1], 'texture_index': tex_b}],
            'collision': {'source': 'NIF RootCollisionNode', 'offset': offset + 99, 'bytes': 9, 'sha256': '22' * 32},
            'flames': [], 'offset': offset, 'bytes': 100, 'sha256': sha}


class UnitKeyTests(unittest.TestCase):
    def test_same_mesh_from_two_stages_is_one_unit(self):
        stage1 = [TEX_A, TEX_B]
        stage2 = [dict(TEX_B, offset=5), dict(TEX_A, offset=77)] + [TEX_A]      # other order and offsets
        a = mesh_fingerprint(model(1000, 0, 1), {}, stage1)
        b = mesh_fingerprint(model(64000, 1, 0), {}, stage2)
        self.assertEqual(a, b)
        self.assertEqual(canonical_materials(model(1000, 0, 1)['materials'], stage1),
                         canonical_materials(model(64000, 1, 0)['materials'], stage2))

    def test_different_content_is_another_unit(self):
        stage = [TEX_A, TEX_B]
        self.assertNotEqual(mesh_fingerprint(model(0, 0, 1), {}, stage),
                            mesh_fingerprint(model(0, 0, 1, sha='33' * 32), {}, stage))
        self.assertNotEqual(mesh_fingerprint(model(0, 0, 1), {}, stage),
                            mesh_fingerprint(model(0, 1, 0), {}, stage))           # textures swapped
        self.assertNotEqual(mesh_fingerprint(model(0, 0, 1), {}, stage),
                            mesh_fingerprint(model(0, 0, 1), {'ratio': 0.5}, stage))

    def test_texture_keys_hold_content_not_positions(self):
        m1, m2 = model(0, 0, 1), model(0, 1, 0)
        shas1 = [TEX_A['sha256'], TEX_B['sha256']]
        shas2 = [TEX_B['sha256'], TEX_A['sha256']]
        self.assertEqual(material_texture_key(m1, 0, 64, False, shas1), material_texture_key(m2, 0, 64, False, shas2))
        # the legacy identity (no hashes) stays the stage index
        self.assertEqual(material_texture_key(m1, 0, 64, False)[0], 0)
        self.assertEqual(copy.deepcopy(m1), model(0, 0, 1))                      # inputs untouched


if __name__ == '__main__':
    unittest.main()
