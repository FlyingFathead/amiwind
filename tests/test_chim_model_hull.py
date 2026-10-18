# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-HULL-CHAIN-COST-33: a placed model with many convex pieces gets a routed standing hull. It
classifies every point like the one chain of all pieces (the legacy form, still selectable), and a
point test visits far fewer clipnodes."""
import struct
import sys
import unittest
from pathlib import Path
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.models import MODEL_ROUTE_PIECES, model_image_lumps  # noqa: E402


def boxes(n):
    """n box pieces in a row-and-column pattern, as a large canton body's convex parts."""
    out = []
    for k in range(n):
        x, y = (k % 8) * 40.0, (k // 8) * 40.0
        lo, hi = (x, y, 0.0), (x + 30.0, y + 30.0, 20.0 + (k % 3) * 10)
        pts = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
        out.append((pts, None, [], 0.))
    return out


def walk(lumps, root, p):
    """Contents and clipnodes visited, as SV_HullPointContents walks them."""
    planes, clips = lumps[1], lumps[9]
    num, visits = root, 0
    while num >= 0:
        visits += 1
        pi, front, back = struct.unpack_from('<iHH', clips, 8 * num)
        n0, n1, n2, dist = struct.unpack_from('<4f', planes, 20 * pi)
        child = front if n0 * p[0] + n1 * p[1] + n2 * p[2] - dist >= 0 else back
        num = child - 65536 if child >= 0xFFF0 else child
    return num, visits


class ModelHullTests(unittest.TestCase):
    def build(self, hull, n=40):
        parts = boxes(n)
        lo = np.min([p for p, *_ in parts], axis=0).min(axis=0)
        hi = np.max([p for p, *_ in parts], axis=0).max(axis=0)
        lumps = [bytes(x) for x in model_image_lumps([], parts, lo, hi, lambda m: 0, False, None, b'', hull)[0]]
        root = struct.unpack_from('<9f7i', lumps[14])[10]
        return lumps, root

    def test_a_model_without_collision_has_an_empty_point_hull_node(self):
        # CHIM-EMPTY-POINT-HULL-36: a render-only tile of a cut model had no point-hull node; its leaf root
        # (-2) reads as SOLID contents where the engine takes headnode[0] as hull 0's first clipnode, and an
        # empty node lump is refused on load (model.c Mod_LoadNodes)
        for hull in ('chain', 'routed', 'auto'):
            lumps = [bytes(x) for x in model_image_lumps([], [], (0., 0., 0.), (64., 64., 64.), lambda m: 0, False,
                                                         None, b'', hull)[0]]
            nodes = list(struct.iter_unpack('<i2h6h2H', lumps[5]))
            leaves = [r[0] for r in struct.iter_unpack('<ii6h2H4B', lumps[10])]
            root = struct.unpack_from('<9f7i', lumps[14])[9]
            self.assertGreaterEqual(len(nodes), 1, hull)
            self.assertGreaterEqual(root, 0, hull)
            for p in ((1., 2., 3.), (-50., 10., -9.), (30., 30., 100.)):
                num = root
                while num >= 0:
                    pi, front, back = nodes[num][:3]
                    n0, n1, n2, dist = struct.unpack_from('<4f', lumps[1], 20 * pi)
                    num = front if n0 * p[0] + n1 * p[1] + n2 * p[2] - dist >= 0 else back
                self.assertEqual(leaves[-num - 1], -1, (hull, p))   # CONTENTS_EMPTY

    def test_routed_hull_classifies_like_the_chain_with_fewer_visits(self):
        chain, croot = self.build('chain')
        routed, rroot = self.build('routed')
        rnd = np.random.default_rng(11)
        chain_visits = routed_visits = 0
        for p in rnd.uniform((-30, -30, -30), (350, 230, 70), (3000, 3)):
            a, va = walk(chain, croot, p)
            b, vb = walk(routed, rroot, p)
            self.assertEqual(a, b, p)
            chain_visits += va
            routed_visits += vb
        self.assertLess(routed_visits * 3, chain_visits)

    def test_auto_routes_chains_deeper_than_the_shared_limit(self):
        """One rule for the router and the audits (routed_hull.CHAIN_DEPTH_LIMIT, in clipnodes of chain depth):
        auto keeps a chain at or under the limit byte for byte and routes a deeper one; the audit's
        over_limit agrees model by model; the measurement override moves both."""
        import os
        from unittest.mock import patch
        from hull_chain_audit import hull_depth, over_limit
        from routed_hull import CHAIN_DEPTH_LIMIT, CHAIN_DEPTH_VARIABLE, chain_depth_limit, trace_cost_us
        self.assertEqual(CHAIN_DEPTH_LIMIT, 256)
        self.assertAlmostEqual(trace_cost_us(256), 348.16)
        seen = set()
        for n in (8, 20, 40, 60):
            chain, croot = self.build('chain', n)
            depth = hull_depth(chain[9], croot)[1]
            auto = self.build('auto', n)[0]
            deep = depth > chain_depth_limit()
            seen.add(deep)
            self.assertEqual(auto != chain, deep, (n, depth))
            self.assertEqual(over_limit(depth), deep)
            reach, rdepth = hull_depth(auto[9], self.build('auto', n)[1])
            self.assertFalse(over_limit(rdepth, reach) and deep)       # a routed hull is not a chain to report
        self.assertEqual(seen, {True, False})
        with patch.dict(os.environ, {CHAIN_DEPTH_VARIABLE: '100000'}):
            self.assertEqual(self.build('auto', 60)[0], self.build('chain', 60)[0])
            self.assertFalse(over_limit(5000))
        with patch.dict(os.environ, {CHAIN_DEPTH_VARIABLE: 'x'}), self.assertRaises(ValueError):
            chain_depth_limit()
        # district-size models are routed by the piece rule as before
        self.assertNotEqual(self.build('auto', MODEL_ROUTE_PIECES + 1)[0],
                            self.build('chain', MODEL_ROUTE_PIECES + 1)[0])

class HullFallbackTests(unittest.TestCase):
    """COLLISION-TRACE-COST-33: the shared builder (chim.build.build_areas, so every caller: chim_build,
    CHIMport) keeps the smallest routed mesh of a peak ring that does not fit as a chain and builds the world
    again, until it fits or nothing routed is left; the receipt records it."""

    def run_fallback(self, fits_after, candidates, mode='auto', sdk='/sdk'):
        import json
        import os
        import tempfile
        from unittest.mock import patch
        from chim import build as B
        calls = {'build': 0, 'heap': 0, 'env': []}

        def heap(*args, **kwargs):
            calls['heap'] += 1
            if calls['heap'] <= fits_after:
                raise ValueError('CHIM heap gate failed')
            return {'ok': True}

        def world(*args):
            calls['build'] += 1
            calls['env'].append(os.environ.get('AMIWIND_CHIM_KEEP_CHAIN', ''))
            return {'frames': 1}
        queue = list(candidates)
        with tempfile.TemporaryDirectory() as tmp,                 patch.dict(os.environ, {'AMIWIND_MODEL_HULL': mode, 'AMIWIND_CHIM_KEEP_CHAIN': ''}),                 patch.object(B, 'build_world', side_effect=world),                 patch('chim.heap.require_heap', side_effect=heap),                 patch('check_world_map_heap.compile_target_sizes', return_value=({}, None)),                 patch.object(B, 'routed_peak_mesh', side_effect=lambda out, kept: queue.pop(0) if queue else None):
            receipt = B.build_areas(['balmora'], '/data', Path(tmp), '/pal', hull_fallback_sdk=sdk)
            written = (Path(tmp) / 'chim-receipt.json')
            on_disk = json.loads(written.read_text()) if written.is_file() else None
            env_after = os.environ.get('AMIWIND_CHIM_KEEP_CHAIN')
        return receipt, calls, on_disk, env_after

    def test_build_areas_keeps_chains_until_the_ring_fits(self):
        receipt, calls, on_disk, env_after = self.run_fallback(2, ['x/ex_hlaalu_b_18', 'x/ex_hlaalu_b_23', 'x/other'])
        self.assertEqual(receipt['hull_fallback']['kept_as_chain'], ['x/ex_hlaalu_b_18', 'x/ex_hlaalu_b_23'])
        self.assertEqual(receipt['hull_fallback']['kept_as_chain_for_memory'], 2)
        self.assertEqual(on_disk['hull_fallback'], receipt['hull_fallback'])
        self.assertEqual((calls['build'], calls['heap']), (3, 3))
        self.assertEqual(calls['env'], ['', 'x/ex_hlaalu_b_18', 'x/ex_hlaalu_b_18,x/ex_hlaalu_b_23'])
        self.assertEqual(env_after, '')                 # the caller's setting is restored

    def test_no_fallback_without_sdk_without_auto_or_when_it_fits(self):
        for kwargs in ({'sdk': None}, {'mode': 'chain'}):
            receipt, calls, _, _ = self.run_fallback(99, ['x/a'], **kwargs)
            self.assertNotIn('hull_fallback', receipt)
            self.assertEqual((calls['build'], calls['heap']), (1, 0))
        receipt, calls, _, _ = self.run_fallback(0, ['x/a'])
        self.assertNotIn('hull_fallback', receipt)
        self.assertEqual((calls['build'], calls['heap']), (1, 1))
        receipt, calls, _, _ = self.run_fallback(99, ['x/a'])       # nothing more to fall back on
        self.assertEqual(receipt['hull_fallback']['kept_as_chain'], ['x/a'])


def contextlib_quiet():
    import contextlib
    import io
    return contextlib.redirect_stdout(io.StringIO())


if __name__ == '__main__':
    unittest.main()


class DeepFernUnionTests(unittest.TestCase):
    def test_scope_preserves_explicit_modes_and_heap_fallback(self):
        from chim.models import depth_compile_candidate
        self.assertTrue(depth_compile_candidate('meshes/o/Flora_Fire_Fern_02.NIF', 'auto'))
        for mode in ('chain', 'routed', 'balanced', 'compiled'):
            self.assertFalse(depth_compile_candidate('o/flora_fire_fern_02', mode))
        self.assertFalse(depth_compile_candidate('o/flora_fire_fern_02', 'auto', True))
        self.assertFalse(depth_compile_candidate('x/terrain_rock_ma_02', 'auto'))

    def test_compiled_hull_meshes_come_from_the_measured_table(self):
        # CHIM-HULL-ROUTE-NO-CUT-43: the deep chains the routing cannot divide are data, not code
        import json
        import tempfile
        from chim.models import compiled_hull_meshes, depth_compile_candidate
        table = compiled_hull_meshes()
        for stem in ('o/flora_fire_fern_01', 'o/flora_fire_fern_02', 'f/flora_tree_gl_08', 'f/flora_emp_parasol_02'):
            self.assertIn(stem, table)
            self.assertTrue(table[stem])
        self.assertTrue(depth_compile_candidate('meshes/f/Flora_Tree_GL_08.nif', 'auto'))
        self.assertFalse(depth_compile_candidate('meshes/f/flora_tree_gl_08.nif', 'chain'))
        self.assertFalse(depth_compile_candidate('f/flora_tree_gl_08', 'auto', meshes={}))
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d, 'x.json')
            bad.write_text(json.dumps({'format': 2, 'meshes': {}}))
            with self.assertRaisesRegex(ValueError, 'format 1'):
                compiled_hull_meshes(bad)

    def test_deep_fern_union_preserves_point_hull_and_rejects_failed_check(self):
        import os
        import tempfile
        from unittest.mock import patch
        from chim.models import variant_unit
        from hull_chain_audit import hull_depth
        qbsp = os.environ.get('AMIWIND_TEST_QBSP')
        if not qbsp:
            self.skipTest('requires external qbsp')
        # Many overlapping pieces defeat routing but have a simple exact union.
        parts = boxes(1) * 60
        ref = {'scale': 1., 'rotation_radians': [0., 0., 0.], 'position': [0., 0., 0.]}
        task = {'ref': ref, 'data': None, 'texsize': 64, 'centre': [0., 0.],
                'model': {'source': 'meshes/o/flora_fire_fern_02.nif'}, 'exact': False,
                'hollow': False, 'qbsp': qbsp, 'hull_patch': True}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'AMIWIND_MODEL_HULL': 'auto'}), \
                patch('prepare_mesh_bsp._prepare_placement', return_value=([], parts, (0., 0., 0.), (30., 30., 20.))), \
                patch('prepare_mesh_bsp.flame_entities', return_value=[]):
            task['collision_cache'] = tmp
            chain = variant_unit(dict(task, keep_chain=True))
            result = variant_unit(task)
            self.assertEqual(result['hull_form'], 'compiled')
            self.assertEqual(result['hull_check']['short'], 0)
            self.assertEqual(result['hull_check']['over'], 0)
            for lump in (3, 10):
                self.assertEqual(chain['lumps'][lump], result['lumps'][lump])
            def point_contents(lumps, point):
                node = struct.unpack_from('<i', lumps[14], 36)[0]
                while node >= 0:
                    plane, front, back = struct.unpack_from('<i2h', lumps[5], node * 24)
                    x, y, z, distance = struct.unpack_from('<4f', lumps[1], plane * 20)
                    node = front if x*point[0] + y*point[1] + z*point[2] >= distance else back
                return struct.unpack_from('<i', lumps[10], (-node-1)*28)[0]
            for point in np.random.default_rng(38).uniform((-20, -20, -20), (60, 60, 60), (500, 3)):
                self.assertEqual(point_contents(chain['lumps'], point), point_contents(result['lumps'], point))
            root = struct.unpack_from('<i', result['lumps'][14], 40)[0]
            self.assertLessEqual(hull_depth(result['lumps'][9], root)[1], 256)
            for point in ((0., 0., 0.), (15., 15., 10.), (100., 100., 100.)):
                oldroot = struct.unpack_from('<i', chain['lumps'][14], 40)[0]
                self.assertEqual(walk(chain['lumps'], oldroot, point)[0], walk(result['lumps'], root, point)[0])
            with patch('collision_bsp.compile_standing_checked', return_value=(([], -1), {'short': 1., 'over': 0.})):
                refused = variant_unit(task)
            self.assertNotEqual(refused['hull_form'], 'compiled')
            self.assertIn('inexact', refused['collision_fallback'])
