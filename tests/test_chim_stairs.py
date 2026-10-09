# SPDX-License-Identifier: GPL-3.0-only
"""The stair walkability gate on a CHIM frame (chim.collision.stair_gate, COLLISION-STAIR-SLOPE-32).

A placed model holds a four-step flight (rise 4, run 10, width 40) on a slab, built through the
real CHIM units. With the steps' own collision the gate passes; with a convex fill over the
flight (the dev1 Vivec Arena fault) it fails and names the placement. The gate reads the
frame's own collision: chunk terrain and the placements' standing hulls.
"""
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.collision import FrameScene, stair_gate, stair_tasks  # noqa: E402
from chim.validate import validate  # noqa: E402
from chim.terrain import quake_texture_axes  # noqa: E402
from test_chim_format import TEXSIZE, fixture  # noqa: E402

RISE = 4.0


def quad(points, normal):
    """A face counter-clockwise about its outward normal, as box_surfaces makes them."""
    from mesh_geometry import split_surface
    q = np.array(points, dtype=float)
    n = np.array(normal, dtype=float)
    ax = quake_texture_axes(n)
    return [(patch, 0, ax / TEXSIZE, np.zeros(2), n) for patch in split_surface(q, np.column_stack((ax.T, np.zeros(2))))]


def box(lo, hi):
    return np.array([[x, y, z] for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])], dtype=float)


def stairs_prepared(fill=False):
    """A slab with a four-step flight on it (model units = local quarter units)."""
    polys = []
    polys += quad([(-60, 0, 0), (0, 0, 0), (0, 40, 0), (-60, 40, 0)], (0, 0, 1))      # approach
    for k in range(4):
        x, z0, z1 = 10 * k, RISE * k, RISE * (k + 1)
        polys += quad([(x, 0, z0), (x, 40, z0), (x, 40, z1), (x, 0, z1)], (-1, 0, 0))  # riser
        x1 = 10 * k + 10 if k < 3 else 70
        polys += quad([(x, 0, z1), (x1, 0, z1), (x1, 40, z1), (x, 40, z1)], (0, 0, 1))  # tread
    pieces = [box((-80, -20, -20), (90, 60, 0))]
    pieces += [box((10 * k, 0, 0), (70, 40, RISE * (k + 1))) for k in range(4)]
    if fill:
        pieces.append(box((-5, 0, 0), (40, 40, 30)))
    corners = np.vstack(pieces)
    return (np.column_stack((corners * 4, np.zeros((len(corners), 2)))), np.array([[0, 1, 2, 0]]), polys,
            [(c, None, [], 0.) for c in pieces], {})


ROWS = [{'ref': 21, 'cell': (0, 0), 'origin': (-300.0, -300.0, 40.0), 'yaw': 0.0, 'variant': 'small'},
        {'ref': 22, 'cell': (0, 0), 'origin': (300.0, 200.0, 40.0), 'yaw': 0.0, 'variant': 'large'}]


def world_of(tmp, fill):
    receipt, source = fixture(Path(tmp), placements=ROWS, prepared_of={0: stairs_prepared(fill)})
    fails, world = validate(tmp, source)
    assert not fails, fails[:5]
    return world


class ChimStairGateTests(unittest.TestCase):
    def test_flight_with_its_own_collision_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = world_of(tmp, False)
            report = stair_gate(tmp, world['frames'], jobs=1)
            self.assertEqual(report['status'], 'passed', report['failures'][:2])
            flight = [b for frame in report['summary'].values() for k, b in frame.items() if k == 'flight step']
            self.assertTrue(flight and sum(b.get('passed', 0) for b in flight) >= 3, report['summary'])

    def test_convex_fill_over_the_flight_fails_and_names_the_placement(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = world_of(tmp, True)
            report = stair_gate(tmp, world['frames'], jobs=1)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual({r['ref'] for r in report['failures']}, {21})

    def test_the_build_gate_writes_its_report_and_stops_on_a_failed_flight(self):
        import json
        import os
        from unittest import mock
        from chim.collision import require_stairs
        with tempfile.TemporaryDirectory() as tmp:
            world_of(tmp, True)
            with mock.patch.dict(os.environ, {'AMIWIND_STAIR_MITIGATION': 'on'}):
                with self.assertRaisesRegex(ValueError, 'ref 21'):
                    require_stairs(tmp, 1)
            self.assertEqual(json.loads((Path(tmp) / 'chim-stairs.json').read_text())['status'], 'failed')
            # the stair rule off (debugging builds only) skips the gate, as the legacy image step does
            with mock.patch.dict(os.environ, {'AMIWIND_STAIR_MITIGATION': 'off'}):
                self.assertEqual(require_stairs(tmp, 1)['status'], 'skipped')

    def test_point_hull_contents_follow_the_chunk_terrain(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = world_of(tmp, False)
            points = FrameScene(world, hull=0)
            from chim.collision import stand_height
            standing = FrameScene(world)
            z = stand_height(standing, -100.0, -350.0)
            self.assertEqual(points.contents((-100.0, -350.0, z + 30)), -1)
            self.assertEqual(points.contents((-100.0, -350.0, z - 60)), -2)

    def test_cores_tile_every_frame_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = world_of(tmp, False)
            tasks = stair_tasks(tmp, world['frames'])
            for x in (-511.0, -1.0, 0.0, 511.0, -5000.0, 5000.0):
                hits = [t for t in tasks if t[2][0] <= x < t[2][2] and t[2][1] <= 0.0 < t[2][3]]
                self.assertEqual(len(hits), 1, x)


if __name__ == '__main__':
    unittest.main()
