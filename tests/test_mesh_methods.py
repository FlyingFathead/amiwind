# SPDX-License-Identifier: GPL-3.0-only
"""CHIM mesh methods (tools/mesh_methods.py, docs/chim/MESH_METHODS.md): planar merge (tools/planar_merge.py) and
meshoptimizer with locked borders (tools/meshopt.py, vendored in third_party/meshoptimizer) are deterministic,
never add faces, keep borders, and the method table selects them per mesh with the earlier method selectable."""
import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mesh_methods as MM  # noqa: E402
import meshopt  # noqa: E402
import planar_merge as PM  # noqa: E402


def grid(n=8, size=64.0, material=0, z=None, uv_shift=0.0):
    """An n x n grid of quads (two triangles each) on one plane, one texture mapping (Morrowind units, uv)."""
    v, f = [], []
    for j in range(n + 1):
        for i in range(n + 1):
            x, y = i * size / n, j * size / n
            v.append([x, y, 0.0 if z is None else z(x, y), x / 32.0 + uv_shift, y / 32.0])
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            b, c, d = a + 1, a + n + 2, a + n + 1
            f += [[a, b, c, material], [a, c, d, material]]
    return np.array(v, float), np.array(f, int)


def unshared(v, f):
    """Every triangle with its own three vertices."""
    nv = v[f[:, :3].reshape(-1)].copy()
    nf = np.column_stack((np.arange(len(nv)).reshape(-1, 3), f[:, 3]))
    return nv, nf


def digest(v, f):
    return hashlib.sha256(np.round(v, 6).tobytes() + np.asarray(f, np.int64).tobytes()).hexdigest()


def face_digest(polys):
    h = hashlib.sha256()
    for p, mat, ax, off, n in polys:
        h.update(np.round(np.asarray(p, float), 4).tobytes() + np.int32(mat).tobytes())
    return h.hexdigest()


def _reduce(args):
    v, f, ratio = args
    return digest(*meshopt.simplify_locked(v, f, ratio))


class PlanarMergeTests(unittest.TestCase):
    def test_flat_grid_becomes_one_face(self):
        v, f = grid()
        polys, _ = PM.polygons(v, f, 64)
        self.assertEqual(len(PM.merged_polygons(v, f, 64)), 1)
        self.assertEqual(len(polys), 1)
        self.assertEqual(len(np.asarray(polys[0][0])), 4)        # one face (the converter's, kept on a tie)

    def test_whole_texture_shift_still_merges(self):
        """Each triangle with its own corners (as a mesh exports them); the right half's texture coordinates one
        whole texture further on: the same texels, so one face. The converter's key keeps the halves apart."""
        v, f = unshared(*grid(n=2))
        right = [k for k, t in enumerate(f) if v[t[:3], 0].min() >= 32]
        for k in right:
            v[f[k, :3], 3] += 1.0
        self.assertEqual(len(PM.merged_polygons(v, f, 64)), 1)
        self.assertGreater(len(PM.converter_polygons(v, f, 64)), 1)

    def test_materials_and_bends_stay_apart(self):
        v, f = grid(n=2)
        f[:4, 3] = 1
        self.assertGreater(len(PM.merged_polygons(v, f, 64)), 1)
        v2, f2 = grid(n=4, z=lambda x, y: 0.0 if x <= 32 else (x - 32) * 0.5)
        self.assertGreaterEqual(len(PM.merged_polygons(v2, f2, 64)), 2)

    def test_never_more_faces_and_deterministic(self):
        rng = np.random.default_rng(3)
        v, f = grid(n=6, z=lambda x, y: float(rng.integers(0, 3)) * 2.0)
        a, _ = PM.polygons(v, f, 64)
        b, _ = PM.polygons(v, f, 64)
        self.assertLessEqual(len(a), len(PM.converter_polygons(v, f, 64)))
        self.assertEqual(face_digest(a), face_digest(b))

    def test_faces_start_at_a_corner(self):
        """The plane is taken from the first three points: they are never collinear."""
        v, f = grid(n=3)
        for p, *_ in PM.merged_polygons(v, f, 64):
            p = np.asarray(p)
            self.assertGreater(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])), 1e-6)

    def test_extent_split_still_applies(self):
        v, f = grid(n=4, size=4096.0)      # 1,024 Quake units across: past 240 texels at 64
        for p, mat, ax, off, n in PM.merged_polygons(v, f, 64):
            uv = np.asarray(p) @ (ax * 64) + off * 64
            self.assertLessEqual(float(np.ptp(uv[:, 0])), 256)
            self.assertLessEqual(float(np.ptp(uv[:, 1])), 256)


@unittest.skipUnless(meshopt.available(), 'no C++ compiler for the vendored meshoptimizer')
class MeshoptTests(unittest.TestCase):
    def test_reduces_and_keeps_border(self):
        v, f = grid(n=16, z=lambda x, y: 4.0 * np.sin(x / 9.0) * np.cos(y / 11.0))
        rv, rf = meshopt.simplify_locked(v, f, 0.25)
        self.assertLess(len(rf), len(f))                 # bounded by the error limit, not only the ratio
        border = {i for i, p in enumerate(v) if p[0] in (0, 64) or p[1] in (0, 64)}
        self.assertTrue(border <= set(rf[:, :3].reshape(-1).tolist()))       # every border vertex still used
        self.assertTrue(set(rf[:, 3]) == {0})

    def test_same_output_every_run_and_any_worker_count(self):
        from build_parallel import ordered_map
        tasks = [(*grid(n=12, z=lambda x, y, k=k: k * np.sin(x / 7.0)), 0.3) for k in range(1, 5)]
        one = list(ordered_map(_reduce, tasks, 1))
        two = list(ordered_map(_reduce, tasks, 2))
        self.assertEqual(one, two)
        self.assertEqual(one, [_reduce(t) for t in tasks])

    def test_closed_thin_part_is_kept(self):
        """A closed tube (a mast pole: no border to lock) is never collapsed to a line or removed."""
        v, f = [], []
        sides, rings = 6, 8
        for j in range(rings + 1):
            for i in range(sides):
                a = 2 * np.pi * i / sides
                v.append([60.0 * j, 4.0 * np.cos(a), 4.0 * np.sin(a), i / sides, j / rings])
        for j in range(rings):
            for i in range(sides):
                a, b = j * sides + i, j * sides + (i + 1) % sides
                f += [[a, b, b + sides, 0], [a, b + sides, a + sides, 0]]
        v, f = np.array(v, float), np.array(f, int)
        rv, rf = meshopt.simplify_locked(v, f, 0.1)
        span = np.ptp(rv[rf[:, :3].reshape(-1), :3], axis=0)
        self.assertTrue(np.all(span >= np.ptp(v[:, :3], axis=0) * 0.9))

    def test_library_named_by_source_hash(self):
        self.assertIn(hashlib.sha256((meshopt.source_sha256() + '|' + meshopt.compiler() + '|' +
                                      ' '.join(meshopt.FLAGS)).encode()).hexdigest()[:16], meshopt.library_path().name)

    def test_static_lod_dispatch(self):
        from static_lod import reduce_for_profile
        v, f = grid(n=10, z=lambda x, y: 3.0 * np.sin(x / 5.0))
        rv, rf, details = reduce_for_profile(v, f, {'ratio': 0.3, 'reducer': 'meshopt'})
        self.assertEqual(details['reducer'], 'meshopt')
        with self.assertRaises(ValueError):
            reduce_for_profile(v, f, {'ratio': 0.3, 'reducer': 'nonesuch'})


class MethodTableTests(unittest.TestCase):
    def test_table_is_valid(self):
        data = MM.load()
        self.assertIn(data['default'], MM.METHODS)
        for source, row in data['meshes'].items():
            self.assertTrue(source.startswith('meshes/'))
            self.assertIn('measured', row)

    def test_default_and_override(self):
        table = {'format': 'amiwind-mesh-methods-1', 'default': 'merge',
                 'meshes': {'meshes/x/ex_de_ship.nif': {'method': 'meshopt+merge'}}}
        self.assertEqual(MM.method_of('meshes/x/ex_de_ship.nif', None, table), 'meshopt+merge')
        self.assertEqual(MM.method_of('meshes/X/Ex_Hlaalu_B_01.nif', None, table), 'merge')
        self.assertEqual(MM.method_of('meshes/x/ex_de_ship.nif', {'mesh_method': 'converter'}, table), 'converter')
        with self.assertRaises(ValueError):
            MM.method_of('x', {'mesh_method': 'nonesuch'}, table)

    def test_converter_profile_is_unchanged(self):
        profile = {'ratio': 0.2, 'texture_size': 32}
        self.assertEqual(MM.apply(profile, 'meshes/x/a.nif', {'mesh_method': 'converter'}), profile)
        merged = MM.apply(profile, 'meshes/x/a.nif', {'mesh_method': 'merge'})
        self.assertEqual(merged['faces'], 'merge')
        self.assertNotIn('reducer', merged)
        full = MM.apply(profile, 'meshes/x/a.nif', {'mesh_method': 'meshopt+merge'})
        self.assertEqual(full['reducer'], 'meshopt')
        self.assertIn('meshopt-', full['method_version'])
        self.assertNotIn('reducer', MM.apply({'texture_size': 32}, 'meshes/x/a.nif', {'mesh_method': 'meshopt+merge'}))

    def test_rule(self):
        rule = MM.load()['rule']
        row = {'hard_surface': True, 'converter': {'faces': 4046, 'seam_torn': 0.02, 'rim_torn': 0.01, 'hausdorff': 50},
               'meshopt+merge': {'faces': 2611, 'seam_torn': 0.0, 'rim_torn': 0.0, 'hausdorff': 40}}
        self.assertTrue(MM.chooses_meshopt(row, rule))
        self.assertFalse(MM.chooses_meshopt(dict(row, hard_surface=False), rule))
        worse = dict(row, **{'meshopt+merge': dict(row['meshopt+merge'], hausdorff=80)})
        self.assertFalse(MM.chooses_meshopt(worse, rule))

    def test_vendored_sources_are_the_recorded_ones(self):
        text = (ROOT / 'third_party/meshoptimizer/README.md').read_text(encoding='utf-8')
        for name in meshopt.FILES + ('LICENSE.md',):
            self.assertIn(hashlib.sha256((meshopt.SOURCE / name).read_bytes()).hexdigest(), text)


if __name__ == '__main__':
    unittest.main()
