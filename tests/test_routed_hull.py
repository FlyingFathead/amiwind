# SPDX-License-Identifier: GPL-3.0-only
"""tools/routed_hull.py, shared by the CHIM builder and the legacy converter (INTERIOR-HULL-CHAIN-33,
CHIM-HULL-CHAIN-COST-33): the routed standing hull classifies every point like the chain of all
pieces, coarser parts when the clipnode budget runs out (undone cleanly), the mode switch, and the
legacy converter routing a large model's hull."""
import os
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import routed_hull as R  # noqa: E402
from chim.models import BrushLumps, hull_pieces  # noqa: E402
from test_chim_model_hull import boxes, walk  # noqa: E402


class Lumps:
    """A bare lump set with a plane cache, as the legacy converter keeps them."""

    def __init__(self, clip_fill=0):
        self.lumps = [bytearray() for _ in range(15)]
        self.lumps[9] += bytes(8 * clip_fill)
        self.planes = {}

    def plane(self, n, d):
        key = tuple(np.round([*n, d], 5))
        if key not in self.planes:
            self.planes[key] = len(self.lumps[1]) // 20
            self.lumps[1] += struct.pack('<4fi', *n, d, 3)
        return self.planes[key]


def plates(n=60):
    """Thin plates spanning two axes, as a hull of authored surface plates (a ship's decks and walls, a
    bowl's tiers): every plate's box spans most of the model in x and y or in x and z."""
    out = []
    step = 960.0 / n
    for k in range(n):
        if k % 2:
            z = step * k
            lo, hi = (0.0, 0.0, z), (480.0, 480.0, z + 2.0)                 # a deck
        else:
            x = step * k
            lo, hi = (x, 0.0, 0.0), (x + 2.0, 480.0, 480.0)                 # a wall
        pts = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
        out.append((pts, None, [], 0.))
    return out


def chain_root(pieces):
    w = BrushLumps()
    _, croot = w.collider(pieces, False, None, point_hull=False)
    return [bytes(x) for x in w.lumps], croot


class RoutedHullTests(unittest.TestCase):
    def setUp(self):
        self.pieces = hull_pieces(boxes(48))

    def test_routed_standing_classifies_like_the_chain(self):
        chain, croot = chain_root(self.pieces)
        for mode in ('auto', 'balanced'):
            w = Lumps()
            root, step, chains = R.routed_standing(w.lumps, w.plane, w.planes, self.pieces, False, **R.routing(mode))
            routed = [bytes(x) for x in w.lumps]
            visits = [0, 0]
            for p in np.random.default_rng(5).uniform((-30, -30, -30), (350, 270, 70), (2000, 3)):
                a, va = walk(routed, root, p)
                b, vb = walk(chain, croot, p)
                self.assertEqual(a, b, (mode, p))
                visits[0] += va
                visits[1] += vb
            self.assertLess(visits[0], visits[1] / 3, mode)
        self.assertEqual(step, R.HULL_LEAF_PIECES)                          # balanced: the finest leaf fits
        self.assertLessEqual(max(chains), R.HULL_LEAF_PIECES)

    def test_nested_writes_every_piece_once(self):
        # plates spanning two axes: the balanced routing copies them into most parts, the nested one
        # chains each where its cut meets it: never more clipnodes than the chain plus one per cut
        pieces = hull_pieces(plates())
        chain, croot = chain_root(pieces)
        size = len(chain[9]) // 8
        nested, balanced = Lumps(), Lumps()
        root, _, chains = R.routed_standing(nested.lumps, nested.plane, nested.planes, pieces, False, steps=(0.0,))
        cuts = len(nested.lumps[9]) // 8 - size
        self.assertGreater(cuts, 0)
        self.assertLessEqual(cuts, len(pieces))
        self.assertEqual(sum(chains), len(pieces))
        R.routed_standing(balanced.lumps, balanced.plane, balanced.planes, pieces, False, **R.routing('balanced'))
        self.assertGreater(len(balanced.lumps[9]) // 8, 2 * size)
        routed = [bytes(x) for x in nested.lumps]
        for p in np.random.default_rng(9).uniform((-30, -30, -40), (510, 510, 520), (2000, 3)):
            self.assertEqual(walk(routed, root, p)[0], walk(chain, croot, p)[0], p)

    def test_every_node_of_a_routed_hull_is_at_or_after_its_root(self):
        # Quake's SV_RecursiveHullCheck stops with "bad node number" on a node below the model's head
        # (hull firstclipnode): the Arena Pit's routed hull crashed the engine (ROUTED-HULL-NODE-ORDER-33).
        # a ring around rows of boxes: its box straddles every cut, so without copies it is chained at the
        # first cut (the Pit's bowl tiers around its floor)
        ring = boxes(48) + [(np.array([[a, b, c] for a in (-20.0, 330.0) for b in (-20.0, 260.0) for c in (60.0, 64.0)]),
                             None, [], 0.)]
        cases = ((hull_pieces(ring), (0.0,)), (hull_pieces(plates()), (0.0,)), (hull_pieces(plates(200)), None),
                 (self.pieces, None))
        for pieces, steps in cases:
            w = Lumps(clip_fill=7)
            root, _, _ = R.routed_standing(w.lumps, w.plane, w.planes, pieces, False, steps=steps)
            nodes = list(struct.iter_unpack('<iHH', bytes(w.lumps[9])))
            seen, todo = set(), [root]
            while todo:
                n = todo.pop()
                if n < 0 or n >= R.CLIPNODE_LIMIT or n in seen:
                    continue
                self.assertGreaterEqual(n, root)
                seen.add(n)
                todo += list(nodes[n][1:])
            self.assertTrue(seen)

    def test_nested_fits_where_the_chain_fits(self):
        pieces = hull_pieces(plates(400))
        size = len(chain_root(pieces)[0][9]) // 8
        w = Lumps(clip_fill=R.CLIPNODE_LIMIT - size - len(pieces) - 2)
        _, step, _ = R.routed_standing(w.lumps, w.plane, w.planes, pieces, False)   # nested: no budget error
        self.assertEqual(step, 0.0)                                         # the copies did not fit: none
        b = Lumps(clip_fill=R.CLIPNODE_LIMIT - size - len(pieces) - 2)
        with self.assertRaisesRegex(ValueError, 'every routing step'):
            R.routed_standing(b.lumps, b.plane, b.planes, pieces, False, **R.routing('balanced'))

    def test_a_routing_out_of_clipnodes_is_undone_before_a_coarser_one(self):
        bal = R.routing('balanced')
        fine = Lumps()
        R.routed_standing(fine.lumps, fine.plane, fine.planes, self.pieces, False, steps=(R.HULL_LEAF_PIECES,), **bal)
        need = len(fine.lumps[9]) // 8
        coarse = Lumps()
        _, _, chains = R.routed_standing(coarse.lumps, coarse.plane, coarse.planes, self.pieces, False, steps=(48,),
                                         **bal)
        need_coarse = len(coarse.lumps[9]) // 8
        self.assertLess(need_coarse, need)
        # room for the coarse routing only: the fine try fails and leaves nothing behind
        w = Lumps(clip_fill=R.CLIPNODE_LIMIT - need_coarse - 1)
        start = len(w.lumps[9])
        root, leaf, _ = R.routed_standing(w.lumps, w.plane, w.planes, self.pieces, False,
                                          steps=(R.HULL_LEAF_PIECES, 48), **bal)
        self.assertEqual(leaf, 48)
        self.assertEqual(len(w.lumps[9]) - start, 8 * need_coarse)
        self.assertEqual(bytes(w.lumps[1]), bytes(coarse.lumps[1]))         # no planes left from the failed try
        self.assertEqual(len(w.planes), len(coarse.planes))

    def test_no_routing_fits_raises_for_the_chain_fallback(self):
        w = Lumps(clip_fill=R.CLIPNODE_LIMIT - 4)
        with self.assertRaisesRegex(ValueError, 'every routing step'):
            R.routed_standing(w.lumps, w.plane, w.planes, self.pieces, False)
        self.assertEqual((len(w.lumps[9]), len(w.lumps[1]), w.planes), (8 * (R.CLIPNODE_LIMIT - 4), 0, {}))

    def test_mode(self):
        self.assertFalse(R.wants_route(R.ROUTE_PIECES, 'auto'))
        self.assertTrue(R.wants_route(R.ROUTE_PIECES + 1, 'auto'))
        self.assertFalse(R.wants_route(1000, 'chain'))
        self.assertTrue(R.wants_route(2, 'routed'))
        self.assertTrue(R.wants_route(2, 'balanced'))
        self.assertEqual(R.routing('auto'), {'method': 'nested', 'axes': R.MODEL_AXES})
        self.assertEqual(R.routing('balanced'), {'method': 'balanced', 'axes': R.TERRAIN_AXES})
        self.assertFalse(R.wants_route(1000, 'routed', compiled=True))    # a qbsp union is never routed
        self.assertFalse(R.wants_route(0, 'routed'))
        with self.assertRaises(ValueError):
            R.wants_route(5, 'tree')

    def test_chim_brush_lumps_use_the_shared_routing(self):
        w = BrushLumps()
        region = R.region_of(self.pieces)
        root = w.routed_hull(self.pieces, region, exact=False)
        v = Lumps()
        v.lumps[10] += bytes(w.lumps[10])          # BrushLumps starts with its two leaves and edge 0
        v.lumps[12] += bytes(w.lumps[12])
        eqs, bx = R.expand(self.pieces, False)
        chains = []
        self.assertEqual(R.route(v.lumps[9], v.plane, eqs, bx, region, R.HULL_LEAF_PIECES, chains), root)
        self.assertEqual((bytes(v.lumps[9]), bytes(v.lumps[1]), chains), (bytes(w.lumps[9]), bytes(w.lumps[1]),
                                                                          w.hull_chains))


class LegacyConverterTests(unittest.TestCase):
    """prepare_mesh_bsp's collider (the legacy region assembly) routes a large model's standing hull by
    the shared module, record for record as the CHIM model writer, and keeps the chain when asked."""

    def legacy(self, mode, n):
        import tempfile
        from test_chim_format import box_surfaces, legacy_model
        import mesh_geometry_env as E
        surfaces, corners = box_surfaces(16, 32)
        parts = boxes(n)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {E.MODEL_HULL_VARIABLE: mode}):
            return legacy_model(Path(directory), surfaces, corners, parts=parts), surfaces, parts

    def chim(self, surfaces, parts, legacy, hull):
        from chim.models import model_image_lumps
        lumps, _ = model_image_lumps(surfaces, parts, legacy['lo'], legacy['hi'], lambda m: 7, False, None, b'', hull)
        return {'lumps': [bytes(x) for x in lumps], 'first': 0, 'num': 6,
                'clip0': struct.unpack_from('<9f7i', lumps[14])[10]}

    def test_auto_routes_a_large_model_without_copies(self):
        from test_chim_format import hull
        legacy, surfaces, parts = self.legacy('auto', 40)
        self.assertNotEqual(hull(self.chim(surfaces, parts, legacy, 'chain')), hull(legacy))
        # the same nested routing as the CHIM writer, without the copy allowance (shared map budget)
        lumps = Lumps()
        pieces = hull_pieces(parts)
        R.routed_standing(lumps.lumps, lumps.plane, lumps.planes, pieces, False, **R.routing('auto', shared_budget=True))
        self.assertEqual(len(legacy['lumps'][9]) // 8, len(lumps.lumps[9]) // 8)

    def test_a_map_shares_its_budget_so_the_legacy_routing_copies_nothing(self):
        from test_chim_format import hull
        legacy, surfaces, parts = self.legacy('auto', 40)
        chain_size = sum(len(e) for e in R.expand(hull_pieces(parts), False)[0])
        routed = len(legacy['lumps'][9]) // 8                           # the base map has no clipnodes
        self.assertLessEqual(routed, chain_size + len(parts))            # the chain plus one clipnode per cut
        self.assertEqual(R.routing('auto', shared_budget=True)['steps'], (0.0,))

    def test_balanced_mode_matches_the_chim_writer(self):
        from test_chim_format import hull
        legacy, surfaces, parts = self.legacy('balanced', 40)
        self.assertEqual(hull(self.chim(surfaces, parts, legacy, 'balanced')), hull(legacy))
        self.assertNotEqual(hull(self.chim(surfaces, parts, legacy, 'routed')), hull(legacy))

    def test_chain_mode_keeps_the_chain(self):
        from test_chim_format import hull
        legacy, surfaces, parts = self.legacy('chain', 40)
        self.assertEqual(hull(self.chim(surfaces, parts, legacy, 'chain')), hull(legacy))

    def test_a_small_model_keeps_the_chain_in_auto(self):
        from test_chim_format import hull
        legacy, surfaces, parts = self.legacy('auto', R.ROUTE_PIECES)
        self.assertEqual(hull(self.chim(surfaces, parts, legacy, 'chain')), hull(legacy))

    def test_mode_comes_from_the_environment(self):
        import mesh_geometry_env as E
        with patch.dict(os.environ, {E.MODEL_HULL_VARIABLE: 'chain'}):
            self.assertEqual(E.model_hull_mode(), 'chain')
        with patch.dict(os.environ, {E.MODEL_HULL_VARIABLE: ''}):
            self.assertEqual(E.model_hull_mode(), 'auto')
        with patch.dict(os.environ, {E.MODEL_HULL_VARIABLE: 'x'}):
            with self.assertRaises(ValueError):
                E.model_hull_mode()


class HullChainAuditTests(unittest.TestCase):
    """tools/hull_chain_audit.py: clipnodes and the longest path of every brush model's standing hull."""

    def test_chain_and_routed_depths(self):
        import tempfile
        import hull_chain_audit as A
        from test_chim_format import box_surfaces, legacy_model
        import mesh_geometry_env as E
        surfaces, corners = box_surfaces(16, 32)
        out = {}
        for mode in ('chain', 'auto'):
            with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {E.MODEL_HULL_VARIABLE: mode}):
                legacy_model(Path(d), surfaces, corners, parts=boxes(40))
                report = A.audit_map(Path(d) / 'out.bsp')
                out[mode] = report['models'][1]                                 # the placed model
        self.assertEqual(out['chain']['depth'], out['chain']['clipnodes'])   # a chain: depth = length
        self.assertLess(out['auto']['depth'], out['chain']['depth'] // 2)       # no copies in a shared map budget
        self.assertEqual(out['auto']['aw_ref'], '1')

    def test_tree_walk(self):
        import hull_chain_audit as A
        # 0 -> (1, 2), 1 -> (2, empty), 2 -> (solid, empty): a shared child, longest path 3
        clips = struct.pack('<iHH', 0, 1, 2) + struct.pack('<iHH', 0, 2, 0xFFFF) + struct.pack('<iHH', 0, 0xFFFE, 0xFFFF)
        self.assertEqual(A.hull_depth(clips, 0), (3, 3))
        self.assertEqual(A.hull_depth(clips, -1), (0, 0))
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            A.hull_depth(struct.pack('<iHH', 0, 0, 0xFFFF), 0)


class HeadNodeOrderTests(unittest.TestCase):
    """ROUTED-HULL-NODE-ORDER-33: every clipnode a model's hull reaches is at or above its head node, in every
    routing mode (the engine stops on load otherwise); the audit and the validator say so."""

    def test_every_mode_starts_at_its_lowest_clipnode(self):
        import hull_chain_audit as A
        pieces = hull_pieces(plates(120))
        for kwargs in (R.routing('auto'), R.routing('auto', shared_budget=True), R.routing('balanced')):
            w = Lumps(clip_fill=37)
            root, _, _ = R.routed_standing(w.lumps, w.plane, w.planes, pieces, False, **kwargs)
            clips = bytes(w.lumps[9])
            self.assertEqual(A.below_head(lambda n: struct.unpack_from('<iHH', clips, 8 * n)[1:], root), [], kwargs)

    def test_the_check_sees_a_node_below_the_head(self):
        import hull_chain_audit as A
        clips = struct.pack('<iHH', 0, 0xFFFF, 0xFFFE) + struct.pack('<iHH', 0, 0, 0xFFFF)   # node 1 -> node 0
        self.assertEqual(A.below_head(lambda n: struct.unpack_from('<iHH', clips, 8 * n)[1:], 1), [0])


if __name__ == '__main__':
    unittest.main()
