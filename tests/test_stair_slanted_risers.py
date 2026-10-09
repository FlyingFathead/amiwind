# SPDX-License-Identifier: GPL-3.0-only
"""Slanted risers in the shared stair rule (STAIRS-SEYDA-LIGHTHOUSE-32).

Stone blocks whose fronts lean back about 75 degrees (as the Seyda Neen lighthouse's outer stair):
on the lighthouse a standing box stepping up came down on such a slanted front, too steep to stand
on, so the walk refused five flight steps (the owner's mesh, reproduced in a private lab: 3 of 5
fail without the cut, 5 of 5 pass with it). The rule cuts such a face back to the vertical plane
through the tread's front edge. Synthetic meshes: the cut itself (a plate, a block, a face that
ends at no tread) and a flight walked by the stair gate's own walker on the model's standing hull.
"""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))
if READY:
    import numpy as np

STEPS, RISE, TREAD, WIDTH, LEAN, DEPTH, LENGTH = 6, 6.69, 6.24, 30.0, 2.4, 9.3, 8.0   # local (quarter) units


def blocks():
    """Closed blocks (source units, x4), the lighthouse's numbers: block k's tread at z = -k*RISE over
    x from k*TREAD to k*TREAD + LENGTH (each block's front reaches over the next one), its back face
    vertical, its front split into a vertical triangle and one leaning back LEAN over DEPTH; a
    floor slab past the lowest block and a landing above the highest. Faces counter-clockwise seen from outside."""
    v, f = [], []

    def box(pts, faces):
        start = len(v)
        v.extend(pts)
        for face in faces:
            for i in range(1, len(face) - 1):
                f.append([start + face[0], start + face[i], start + face[i + 1], 0])
    for k in range(STEPS):
        z, x0, x1 = -k * RISE, k * TREAD, k * TREAD + LENGTH     # the next block starts under this one's front
        # the front is split as the lighthouse's: a vertical triangle and a leaning one
        pts = [(x0, 0, z), (x1, 0, z), (x1, WIDTH, z), (x0, WIDTH, z),
               (x0, 0, z - DEPTH), (x1, 0, z - DEPTH), (x1 + LEAN, WIDTH, z - DEPTH), (x0, WIDTH, z - DEPTH)]
        box(pts, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)])
    for z, x0 in ((-STEPS * RISE, STEPS * TREAD), (0.0, -60.0)):     # the floor below, the landing above
        pts = [(x0, -4, z), (x0 + 60, -4, z), (x0 + 60, WIDTH + 4, z), (x0, WIDTH + 4, z),
               (x0, -4, z - 8), (x0 + 60, -4, z - 8), (x0 + 60, WIDTH + 4, z - 8), (x0, WIDTH + 4, z - 8)]
        box(pts, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (2, 6, 7, 3), (0, 3, 7, 4), (1, 5, 6, 2)])
    v = np.array(v, float) * 4
    return np.hstack((v, np.zeros((len(v), 2)))), np.array(f)


class _Hull:
    """One model's standing (1) or point (0) hull as an audit_walkability.Scene."""

    def __init__(self, lumps, hull):
        from audit_walkability import Scene, axes
        s = Scene.__new__(Scene)
        s.planes = list(struct.iter_unpack('<4fi', bytes(lumps[1])))
        if hull == 1:
            s.nodes = [(p, *(c - 65536 if c >= 0xFFF0 else c for c in (a, b)))
                       for p, a, b in struct.iter_unpack('<iHH', bytes(lumps[9]))]
        else:
            leaves = [r[0] for r in struct.iter_unpack('<ii6h2H4B', bytes(lumps[10]))]
            s.nodes = [(p, *(c if c >= 0 else leaves[-c - 1] for c in (a, b)))
                       for p, a, b, *_ in struct.iter_unpack('<i2h6h2H', bytes(lumps[5]))]
        root = struct.unpack_from('<9f7i', bytes(lumps[14]))[9 + hull]
        s.brushes = [(root, (0., 0., 0.), axes((0., 0., 0.)), 1)]
        s.sha256 = 'test'
        self.trace = s.trace


def gate(mode):
    from chim.models import BrushLumps, hull_pieces
    from mesh_geometry import collision_pieces, surface_polygons
    from stair_walk import check_polys, _gating
    v, f = blocks()
    pieces, exact, note = collision_pieces(v, f, {}, stairs=mode)
    w = BrushLumps()
    nroot, croot = w.collider(hull_pieces(pieces), exact)
    lo = np.min([p[0].min(axis=0) for p in pieces], axis=0)
    hi = np.max([p[0].max(axis=0) for p in pieces], axis=0)
    lumps = w.finish(lo, hi, nroot, croot, 0, 0)
    # visible faces in Quake winding (clockwise seen from the front), as the gate reads a map
    polys = [([tuple(float(c) for c in p) for p in poly[::-1]], 1)
             for poly, *_ in surface_polygons(v, f, geometry_only=True)]
    rows = check_polys(polys, _Hull(lumps, 1), None, None, _Hull(lumps, 0))
    flight = [r for r in rows if r['kind'] == 'step' and r.get('flight')]
    return flight, [r for r in rows if _gating(r)], note


@unittest.skipUnless(READY, 'numpy and scipy required')
class SlantedRiserTests(unittest.TestCase):
    def test_the_cut_never_adds_a_failure_to_a_flight(self):
        # a flight of leaning blocks with treads narrower than the standing box: the walk fails at the
        # same steps with and without the rule (a different cause: the box overhangs two treads), and
        # the cut adds no failure of its own
        off_flight, off_failures, _ = gate('off')
        on_flight, on_failures, note = gate('on')
        self.assertIn('vertical risers', note or '')
        self.assertEqual(len(on_flight), len(off_flight))
        self.assertLessEqual({tuple(r['point']) for r in on_failures}, {tuple(r['point']) for r in off_failures})

    def test_a_slanted_plate_becomes_vertical_at_the_tread_edge(self):
        from scipy.spatial import ConvexHull
        from mesh_geometry import vertical_risers
        from player_hull import WALKABLE_Z
        # a thin plate leaning back from the tread edge x = 8 (z 0) to x = 10.6 (z -9.3), 74 degrees
        top, bottom = np.array([[8., 0, 0], [8., 30, 0]]), np.array([[10.6, 0, -9.3], [10.6, 30, -9.3]])
        n = np.array([9.3, 0, 2.6]) / np.linalg.norm([9.3, 0, 2.6])
        pts = np.vstack([top + n * .2, top - n * .2, bottom + n * .2, bottom - n * .2])
        tread = np.array([[[0., 0, 0], [8, 0, 0], [8, 30, 0]], [[0., 0, 0], [8, 30, 0], [0, 30, 0]]])
        out, cut = vertical_risers([(pts, ConvexHull(pts), [], 0.)], tread, WALKABLE_Z)
        self.assertEqual(cut, 1)
        p = out[0][0]
        self.assertLess(np.ptp(p[:, 0]), 0.41)                  # vertical: no lean left
        self.assertLess(abs(float(p[:, 0].mean()) - 8.0), 0.25)     # at the edge (the plate's outer face)


if __name__ == '__main__':
    unittest.main()
