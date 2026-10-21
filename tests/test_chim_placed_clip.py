# SPDX-License-Identifier: GPL-3.0-only
"""Placed collision (engine chim/chim_placed_clip.c; used by world format 0.8 only, EXPERIMENTAL).

One collision shape per mesh, placed with the full rotation and a uniform scale at run time,
traced with the world-aligned standing box, against today's method: the same pieces rotated and
scaled by the builder (prepare_scenery.reference_rotation), expanded by the builder's exact
Minkowski sum (prepare_mesh_bsp.standing_planes, exact=True) into the piece chain and traced by
the engine's own SV_ClipMoveToEntity (world.c). Shapes are synthetic (no game data).

The run also measures today's yaw placements: a model built at yaw 0 and turned by the engine
(the trace is turned into the model's frame, so the player box turns with the model) against the
same model built at that yaw.
"""
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
SRC = ROOT / 'engine/aga/src'

try:
    import numpy as np
    from scipy.spatial import ConvexHull
except ImportError:  # pragma: no cover - the gate image has both
    np = None


def shapes():
    """Local convex pieces (point sets) of a few synthetic meshes, in world units."""
    from itertools import product
    box = lambda lo, hi: np.array(list(product(*zip(lo, hi))), dtype=float)
    ramp = np.array([[0, -10, 0], [30, -10, 0], [30, -10, 15], [0, 10, 0], [30, 10, 0], [30, 10, 15]], dtype=float)
    rng = np.random.default_rng(46)
    u = rng.normal(size=(18, 3))
    rock = u / np.linalg.norm(u, axis=1)[:, None] * np.array([18.0, 12.0, 9.0])
    return {
        'slab': [box((-20, -10, 0), (20, 10, 4))],
        'ramp': [ramp],
        'rock': [rock],
        'post': [box((-20, -10, 0), (20, 10, 4)), box((-3, -3, 0), (3, 3, 25))],
    }


# TES3 angles (radians, x y z as stored) and uniform scale
TRANSFORMS = [
    ('yaw0', (0, 0, 0.0), 1.0), ('yaw30', (0, 0, -0.5236), 1.0), ('yaw45', (0, 0, -0.7854), 1.0),
    ('yaw90', (0, 0, -1.5708), 1.0), ('yaw137s16', (0, 0, -2.39), 1.6),
    ('tiltx10', (0.17, 0, 0), 1.0), ('tilt_y20_yaw45', (0, 0.35, -0.7854), 1.0),
    ('tilt3_s08', (0.3, 0.2, 1.1), 0.8), ('tilt3_s23', (0.4, -0.3, 2.0), 2.3), ('tilt_small_s18', (0.05, 0.1, 0), 1.8),
    ('scale05', (0, 0, 0), 0.5), ('scale22', (0, 0, 0), 2.2),
]


def planes_of(points):
    """Unique outward planes (n, d: inside n.x < d), rounded as the builder stores them."""
    eq = np.unique(np.round(ConvexHull(points).equations, 5), axis=0)
    return eq


def piece_record(points):
    eq = planes_of(points)
    hull = ConvexHull(points)
    verts = points[hull.vertices]
    edges = []
    for a in range(len(eq)):
        for b in range(a + 1, len(eq)):
            on = [i for i, v in enumerate(verts)
                  if abs(eq[a, :3] @ v + eq[a, 3]) < 1e-3 and abs(eq[b, :3] @ v + eq[b, 3]) < 1e-3]
            if len(on) >= 2:
                edges.append((a, b, on[0]))
    lines = ['%d %d %d' % (len(eq), len(verts), len(edges))]
    lines += ['%.6f %.6f %.6f %.6f' % (*e[:3], -e[3]) for e in eq]
    lines += ['%.6f %.6f %.6f' % tuple(v) for v in verts]
    lines += ['%d %d %d' % e for e in edges]
    return lines


def chain(pieces, standing):
    from prepare_mesh_bsp import standing_planes
    lines = [str(len(pieces))]
    for points in pieces:
        eq = planes_of(points)
        if standing:
            eq = standing_planes(points, eq, exact=True)
        lines.append(str(len(eq)))
        lines += ['%.6f %.6f %.6f %.6f' % (*e[:3], -e[3]) for e in eq]
    return lines


def traces(points, origin, rng):
    lo = points.min(axis=0) + origin - 25
    hi = points.max(axis=0) + origin + 25
    out = []
    r = lambda: lo + rng.random(3) * (hi - lo)
    for _ in range(100):
        out.append((0, r(), r()))
    for _ in range(60):
        a = r()
        a[2], b = hi[2], a.copy()
        b[2] = lo[2]
        out.append((0, a, b))
    for _ in range(60):
        a = r()
        ang = rng.random() * 2 * math.pi
        out.append((0, a, a + 40 * np.array([math.cos(ang), math.sin(ang), 0])))
    for _ in range(40):
        a = r()
        out.append((0, a, a + rng.normal(size=3) * 3))
    for _ in range(40):
        out.append((1, r(), r()))
    return out


def write_cases(path):
    from prepare_scenery import reference_rotation
    rng = np.random.default_rng(4646)
    lines = []
    for sname, pieces in shapes().items():
        for tname, angles, scale in TRANSFORMS:
            ref = {'rotation_radians': list(angles), 'scale': scale}
            m = reference_rotation(ref)
            origin = np.array([137.5, -64.25, 20.0])
            baked = [p @ m.T * scale for p in pieces]
            yawonly = angles[0] == 0 and angles[1] == 0
            yaw = -angles[2] * 180 / math.pi
            lines.append('%s_%s %d %.6f %.6f %.6f %.6f %.7f %.7f %.7f %.6f' % (
                sname, tname, yawonly, scale, *origin, *angles, yaw))
            lines += ['%.8f %.8f %.8f' % tuple(row) for row in m]
            lines.append(str(len(pieces)))
            for p in pieces:
                lines += piece_record(p)
            lines += chain(baked, False)
            lines += chain(baked, True)
            if yawonly:
                lines += chain([p * scale for p in pieces], True)
            allpoints = np.concatenate(baked)
            t = traces(allpoints, origin, rng)
            lines.append(str(len(t)))
            lines += ['%d %.5f %.5f %.5f %.5f %.5f %.5f' % (k, *a, *b) for k, a, b in t]
    Path(path).write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')


def parse(text):
    rows = {}
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        words = line.split()
        row = {}
        for k in range(1, len(words) - 1, 2):
            row[words[k]] = float(words[k + 1])
        rows[words[0]] = row
    return rows


class PlacedClipContractTests(unittest.TestCase):
    def test_only_format_08_reaches_it(self):
        """In the engine since world format 0.8 (the experiment's AW_EXP_PLACED_CLIP gate is gone): the model loader
        converts a piece table only for a 0.8 world, and the collision takes it only for a chunk with a matrix per
        record, which only a 0.8 world's catalogue has; 0.4-0.7 collide through ClipModel as before."""
        text = (SRC / 'chim/chim_placed_clip.c').read_text(encoding='utf-8')
        self.assertNotIn('AW_EXP_PLACED_CLIP', text)
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('chim/chim_placed_clip.c', make)
        callers = sorted(p.name for p in SRC.rglob('*.c')
                         if p.name != 'chim_placed_clip.c' and 'ChimPlaced_' in p.read_text(encoding='utf-8', errors='replace'))
        self.assertEqual(callers, ['chim_chunks.c', 'chim_models.c'])
        models = (SRC / 'chim/chim_models.c').read_text(encoding='utf-8')
        self.assertIn('cm->piece_bytes = kind == CHIM_KIND_MODEL && chim_world.minor >= CHIM_PLACED_MINOR ?', models)
        self.assertEqual(models.count('ChimPlaced_'), 1)
        chunks = (SRC / 'chim/chim_chunks.c').read_text(encoding='utf-8')
        self.assertIn('int placed = chim_world.minor >= CHIM_PLACED_MINOR', chunks)
        self.assertIn('c->rot = placed ? (float *)(c->places + n) : NULL;', chunks)
        clip = chunks[chunks.index('static void ClipPlacement ('):]
        clip = clip[:clip.index('\n}\n')]
        self.assertLess(clip.index('if (c->rot)'), clip.index('ChimPlaced_TraceTable'))
        # without a matrix (0.4-0.7) the old path, unchanged
        self.assertTrue(clip.rstrip().endswith('ClipModel (p->ent.model, p->ent.origin, p->s, p->c, start, mins, maxs, end, best);'))
        self.assertEqual(chunks.count('ChimPlaced_'), 2)     # the matrix at load, the table trace


@unittest.skipIf(np is None, 'numpy and scipy are required')
@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class PlacedClipNativeTests(unittest.TestCase):
    def test_placed_matches_the_builders_baked_hull(self):
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        with tempfile.TemporaryDirectory(prefix='amiwind-placed-') as tmp:
            cases, out = Path(tmp) / 'cases.txt', Path(tmp) / 'out.txt'
            write_cases(cases)
            NativeSourceTests.compile_run(
                self, 'aga_placed_clip_test.c',
                [SRC / 'world.c', SRC / 'mathlib.c', SRC / 'chim/chim_placed_clip.c', SRC / 'chim/chim_format.c'],
                cflags=[*WARN, '-O1'],
                arguments=[str(cases), str(out)])
            text = out.read_text(encoding='ascii')
        if os.environ.get('AW_PLACED_CLIP_REPORT'):
            Path(os.environ['AW_PLACED_CLIP_REPORT']).write_text(text, encoding='ascii', newline='\n')
        rows = parse(text)
        self.assertEqual(len(rows), len(shapes()) * len(TRANSFORMS))
        for name, r in rows.items():
            with self.subTest(case=name):
                # same start/all-solid state and the same end point (5 hundredths) on every trace
                self.assertEqual(r['solid_diff'], 0, name)
                self.assertEqual(r['match'], r['traces'], name)
                self.assertLess(r['maxd'], 0.05, name)
        total_hits = sum(r['of'] for r in rows.values())
        normal_diff = sum(r['normal_diff'] for r in rows.values())
        self.assertGreater(total_hits, 1000)
        # a hit exactly on an edge may report either face; never more than a few in a hundred
        self.assertLess(normal_diff, 0.03 * total_hits)
        # today's yaw: the player box turns with the model (finding, measured, not asserted to be zero)
        yawed = [r for n, r in rows.items() if re.search(r'_yaw(30|45|137)', n)]
        self.assertTrue(any(r['today_bad'] > 0 for r in yawed))


if __name__ == '__main__':
    unittest.main()
