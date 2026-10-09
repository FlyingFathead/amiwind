"""Modular NPC parts (docs/MODULAR_NPCS.md): synthetic meshes, no game assets."""
import sys
import unittest
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parents[1] / 'tools')]


def grid(name, part, width, height, z0, frames=2):
    import numpy as np
    xs, zs = np.meshgrid(np.linspace(0, 4, width + 1), np.linspace(z0, z0 + 6, height + 1))
    points = np.column_stack((xs.ravel(), np.zeros(xs.size), zs.ravel()))
    faces = []
    for j in range(height):
        for i in range(width):
            a = j * (width + 1) + i
            faces += [(a, a + 1, a + width + 1), (a + 1, a + width + 2, a + width + 1)]
    positions = np.stack([points + [0, 0, k * .5] for k in range(frames)])
    uv = np.column_stack((xs.ravel() / 4, (zs.ravel() - z0) / 6))
    return {'name': name, 'part': part, 'positions': positions, 'faces': np.array(faces),
            'uv': uv, 'colours': np.ones((len(points), 4)), 'material': 0}


class ModularParts(unittest.TestCase):
    def setUp(self):
        try:
            import numpy  # noqa: F401
            import fast_simplification  # noqa: F401
            import scipy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        self.palette = bytes(range(256)) * 3
        self.materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]

    def shapes(self):
        return [grid('tri head', 0, 8, 8, 30), grid('tri chest', 3, 12, 10, 15), grid('tri foot', 15, 6, 4, 0)]

    def test_default_bake_unchanged_by_explicit_quota_path(self):
        import numpy as np
        from npc_geometry import bake, bake_quotas
        shapes = self.shapes()
        default = bake(shapes, self.materials, {}, self.palette, budget=192)
        quotas = bake_quotas(shapes, 192)
        explicit = bake(shapes, self.materials, {}, self.palette, quotas=quotas)
        for a, b in zip(default[:3], explicit[:3]):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(default[3].tobytes(), explicit[3].tobytes())

    def test_parts_baked_once_concatenate_to_the_whole_model(self):
        """Unit scale and the outfit's own quotas: composition is byte-identical."""
        import numpy as np
        from npc_geometry import animated_mdl, bake, bake_quotas
        from modular_npc_study import compose
        shapes = self.shapes()
        whole = bake(shapes, self.materials, {}, self.palette, budget=192)
        quotas = bake_quotas(shapes, 192)
        height = max(s['positions'][0, :, 2].max() for s in shapes) - min(s['positions'][0, :, 2].min() for s in shapes)
        parts = [bake([s], self.materials, {}, self.palette, quotas=[q], shell_height=height)
                 for s, q in zip(shapes, quotas)]
        frames, faces, uv, skin = compose(parts, np.ones(3))
        np.testing.assert_array_equal(frames, whole[0])
        np.testing.assert_array_equal(faces, whole[1])
        self.assertEqual(animated_mdl(frames, faces, uv, skin), animated_mdl(*whole))

    def test_explicit_quotas_are_checked(self):
        from npc_geometry import bake
        shapes = self.shapes()
        for quotas in ([10, 10], [0, 10, 10], [400, 200, 100]):
            with self.assertRaises(ValueError):
                bake(shapes, self.materials, {}, self.palette, quotas=quotas)
        with self.assertRaises(ValueError):
            bake(shapes, self.materials, {}, self.palette, quotas=[20, 20, 20], shell_height=0)

    def test_part_key_separates_slots_and_mirrored_attachments(self):
        from modular_npc_study import part_key
        app = {'skeleton': 'meshes/base_anim.nif'}
        left = {'mesh': 'b/B_N_Dark Elf_M_Foot.nif', 'filter': 'Left Foot', 'attach': 'Left Foot', 'slot': 16}
        right = {**left, 'filter': 'Right Foot', 'attach': 'Right Foot', 'slot': 15}
        self.assertNotEqual(part_key(app, left), part_key(app, right))
        self.assertNotEqual(part_key(app, left), part_key({'skeleton': 'meshes/base_animkna.nif'}, left))
        self.assertEqual(part_key(app, left), part_key(app, {**left, 'mesh': 'B\\b_n_dark elf_m_foot.nif'}))


if __name__ == '__main__':
    unittest.main()
