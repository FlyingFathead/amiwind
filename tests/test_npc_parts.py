"""NPC parts library (tools/npc_parts.py): synthetic meshes, no game assets."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parents[1] / 'tools')]


def grid(name, part, width, height, z0, frames=2):
    """A flat panel of width x height quads (same fixture as test_modular_npc)."""
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


class PartsLibrary(unittest.TestCase):
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
        return [grid('tri head', 0, 8, 8, 30, 1), grid('tri chest', 3, 12, 10, 15, 1),
                grid('tri foot', 15, 6, 4, 0, 1), grid('tri hand', 6, 3, 3, 12, 1)]

    def test_composed_parts_equal_the_whole_bake_layout(self):
        """Frames, faces, texture coordinates and the cropped atlas match the whole bake."""
        import numpy as np
        from npc_geometry import bake, bake_quotas
        from npc_parts import black_index, compose_arrays
        shapes = self.shapes()
        quotas = bake_quotas(shapes, 192)
        height = max(s['positions'][0, :, 2].max() for s in shapes) - min(s['positions'][0, :, 2].min() for s in shapes)
        flags = [s['part'] == 3 and np.ptp(s['positions'][0, :, 2]) >= .2 * height for s in shapes]
        frames, faces, uv, skin = bake(shapes, self.materials, {}, self.palette, budget=192)
        parts = []
        for s, q, f in zip(shapes, quotas, flags):
            pf, pa, pu, ps = bake([s], self.materials, {}, self.palette, quotas=[q], preserve=[f])
            parts.append({'frames': pf, 'faces': pa.astype(np.int32), 'uv': pu, 'skin': np.array(ps)})
        cf, cfa, cuv, atlas = compose_arrays(parts, black_index(self.palette))
        np.testing.assert_array_equal(cf, frames)
        np.testing.assert_array_equal(cfa, faces)
        np.testing.assert_array_equal(cuv, uv)
        rows = ((len(faces) + 31) // 32) * 16
        np.testing.assert_array_equal(atlas, np.array(skin)[:rows])

    def test_explicit_shell_flags_match_the_computed_ones(self):
        import numpy as np
        from npc_geometry import bake
        shapes = self.shapes()
        default = bake(shapes, self.materials, {}, self.palette, budget=96)
        from npc_geometry import bake_quotas
        height = max(s['positions'][0, :, 2].max() for s in shapes) - min(s['positions'][0, :, 2].min() for s in shapes)
        flags = [s['part'] == 3 and np.ptp(s['positions'][0, :, 2]) >= .2 * height for s in shapes]
        explicit = bake(shapes, self.materials, {}, self.palette, quotas=bake_quotas(shapes, 96), preserve=flags)
        for x, y in zip(default[:3], explicit[:3]):
            np.testing.assert_array_equal(x, y)
        with self.assertRaises(ValueError):
            bake(shapes, self.materials, {}, self.palette, quotas=bake_quotas(shapes, 96), preserve=[True])

    def test_shared_pseudo_inverses_are_bitwise_the_per_triangle_ones(self):
        """bake computes one batched pinv per shape; it must equal the old per-call results."""
        import numpy as np
        rng = np.random.default_rng(7)
        tris = rng.normal(size=(400, 3, 3)) * rng.choice([1e-3, 1., 40.], size=(400, 1, 1))
        tris[:5, 2] = tris[:5, 1]  # degenerate triangles too
        edges = np.stack((tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=2)
        batched = np.linalg.pinv(edges)
        for i in range(len(tris)):
            np.testing.assert_array_equal(np.linalg.pinv(np.column_stack((edges[i, :, 0], edges[i, :, 1]))), batched[i])
        idx = rng.integers(0, len(tris), 256)
        np.testing.assert_array_equal(np.linalg.pinv(edges[idx]), batched[idx])

    def test_quota_stand_ins_give_the_real_quotas(self):
        import numpy as np
        from npc_geometry import bake_quotas
        from npc_parts import quota_shapes
        shapes = self.shapes()
        rows = [{'name': s['name'], 'part': s['part'], 'faces': len(s['faces'])} for s in shapes]
        for budget in (480, 192, 96):
            np.testing.assert_array_equal(bake_quotas(quota_shapes(rows), budget), bake_quotas(shapes, budget))

    def test_store_round_trip_and_identity(self):
        import numpy as np
        from npc_parts import Store
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp); ident = {'kind': 'bake', 'quotas': [3, 4]}
            self.assertIsNone(store.load(ident))
            store.publish(ident, {'status': 'ready'}, {'frames': np.arange(6.).reshape(1, 2, 3)})
            result, arrays = store.load(ident)
            self.assertEqual(result, {'status': 'ready'}); self.assertEqual(store.result(ident), result)
            np.testing.assert_array_equal(arrays['frames'], np.arange(6.).reshape(1, 2, 3))
            self.assertIsNone(store.load({'kind': 'bake', 'quotas': [3, 5]}))
            (store.directory(ident) / 'payload.npz').write_bytes(b'changed')
            self.assertIsNone(store.load(ident))

    def test_policy_names_and_level_choice(self):
        from npc_parts import Planner, parse_policy
        self.assertIsNone(parse_policy('exact')); self.assertEqual(parse_policy('levels4'), 4)
        for bad in ('levels0', 'levels17', 'levels', 'tiers3'):
            with self.assertRaises(ValueError):
                parse_policy(bad)
        planner = Planner({}, {}, b'\0' * 768, None, {}, {}, 'levels2')
        planner.level_table['p'] = [40, 100]
        rows = [{'faces': 150}, {'faces': 50}]
        self.assertEqual(planner.level_quota('p', rows, [60, 20]), [75, 25])   # wants 80 -> level 100
        self.assertEqual(planner.level_quota('p', rows, [30, 10]), [30, 10])   # wants 40 -> level 40
        self.assertEqual(planner.level_quota('q', rows, [60, 20]), [60, 20])   # no table: exact

    def test_part_keys_separate_sides_slots_and_skeletons(self):
        from npc_parts import part_key
        left = {'mesh': 'b/B_N_Dark Elf_M_Foot.nif', 'filter': 'Left Foot', 'attach': 'Left Foot', 'slot': 16}
        right = {**left, 'filter': 'Right Foot', 'attach': 'Right Foot', 'slot': 15}
        self.assertNotEqual(part_key('meshes/base_anim.nif', left), part_key('meshes/base_anim.nif', right))
        self.assertNotEqual(part_key('meshes/base_anim.nif', left), part_key('meshes/base_animkna.nif', left))
        self.assertEqual(part_key('meshes/base_anim.nif', left),
                         part_key('Meshes\\Base_Anim.nif', {**left, 'mesh': 'B\\b_n_dark elf_m_foot.nif'}))


class JointSeams(unittest.TestCase):
    """npc_seam_audit: joints found from the source, gaps measured on the reduced model."""
    def setUp(self):
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')

    def panels(self, lift=0.):
        lower = grid('tri forearm', 11, 4, 3, 0., 1); upper = grid('tri upper arm', 13, 4, 3, 6., 1)
        upper['positions'] = upper['positions'] + [0, 0, lift]
        return [{'name': s['name'], 'points': s['positions'][0], 'faces': s['faces']} for s in (lower, upper)]

    def test_closed_joint_measures_nothing_open(self):
        import numpy as np
        from npc_seam_audit import measure, silhouette_holes
        shapes = self.panels()
        tris = np.concatenate([s['points'][s['faces']] for s in shapes])
        result = measure(shapes, tris)
        self.assertGreater(result['joint_length'], 0)
        self.assertEqual(result['open_length'], 0); self.assertEqual(result['max_gap'], 0)
        self.assertEqual(silhouette_holes(tris, tris, views=4)['hole_pixels'], 0)

    def test_pulled_back_part_opens_the_joint(self):
        import numpy as np
        from npc_seam_audit import check, measure
        source = self.panels(); reduced = self.panels(lift=1.)
        tris = np.concatenate([s['points'][s['faces']] for s in reduced])
        result = measure(source, tris)
        self.assertGreater(result['open_share'], .4)
        self.assertAlmostEqual(result['max_gap'], .5, delta=.03)  # at the inset point: a lower bound of the 1-unit opening
        report = {'appearances': [{'key': 'm1', 'candidate': result}, {'key': 'm2', 'candidate': measure(source, np.concatenate(
            [s['points'][s['faces']] for s in source]))}]}
        self.assertEqual([k for k, _ in check(report)], ['m1'])


class BuilderOption(unittest.TestCase):
    def test_whole_stays_the_default_and_adds_no_arguments(self):
        from build import npc_model_arguments, parser
        args = parser().parse_args([])
        self.assertEqual(args.npc_models, 'whole')
        self.assertEqual(npc_model_arguments(args), [])

    def test_parts_arguments_and_checks(self):
        from build import npc_model_arguments
        args = SimpleNamespace(npc_models='parts', npc_parts_policy='levels4', npc_parts_face_cap=480,
                               parts_cache=None, workspace=Path('/w'))
        self.assertEqual(npc_model_arguments(args), ['--npc-models', 'parts', '--parts-cache', Path('/w/cache/npc-parts-v1'),
                                                     '--npc-parts-policy', 'levels4', '--npc-parts-face-cap', 480])
        for change in ({'npc_parts_policy': 'levels99'}, {'npc_parts_face_cap': 700}):
            with self.assertRaises(ValueError):
                npc_model_arguments(SimpleNamespace(**{**vars(args), **change}))


if __name__ == '__main__':
    unittest.main()
