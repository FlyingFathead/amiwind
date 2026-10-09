"""Stair walkability gate on synthetic BSP29 maps (COLLISION-STAIR-SLOPE-32).

A four-step flight (rise 4, run 10, width 40) with a landing: its visible faces
in one placement, its collision as standing-hull boxes. The gate passes; a
convex fill over the flight (the dev1 Vivec Arena fault) makes it fail; the
image step's require() refuses the map and names the step.
"""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
READY = importlib.util.find_spec('numpy') is not None

from player_hull import pack_lumps, PROFILE, MINS, MAXS  # noqa: E402


def build(fill=False, rise=4.):
    """BSP29 payload: world (empty), a visual-only placement (ref 100), collision boxes."""
    data = [bytearray() for _ in range(15)]
    verts, edges, surf, faces = [], [(0, 0)], [], []

    def face(points):
        # Quake winds a face clockwise seen from its front.
        first = len(surf)
        for i, p in enumerate(points):
            verts.append(p)
            a, b = len(verts) - 1, len(verts) - 1 + (1 if i + 1 < len(points) else 1 - len(points))
            edges.append((a, b)); surf.append(len(edges) - 1)
        faces.append(struct.pack('<hhihhBBBBi', 0, 0, first, len(points), 0, 0, 0, 0, 0, -1))

    def level(x0, x1, z, y0=0., y1=40.):   # upward face: clockwise from above
        face([(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)])

    def riser(x, z0, z1, y0=0., y1=40.):   # faces -x: clockwise seen from -x
        face([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)])

    models = [struct.pack('<9f7i', *([0.] * 9), -1, -1, -1, -1, 0, 0, 0)]
    first = len(faces)
    level(-60, 0, 0)                       # approach floor
    for k in range(4):
        riser(10 * k, rise * k, rise * (k + 1))
        level(10 * k, 10 * k + 10 if k < 3 else 70, rise * (k + 1))
    models.append(struct.pack('<9f7i', -60, 0, 0, 70, 40, rise * 4, 0, 0, 0, -1, -1, -1, -1, 0, first, len(faces) - first))
    entities = ['{\n"classname" "worldspawn"\n"aw_hull" "%s"\n}' % PROFILE,
                '{\n"classname" "func_wall"\n"model" "*1"\n"aw_ref" "100"\n"origin" "0 0 0"\n"angles" "0 0 0"\n}']
    boxes = [((-80, -20, -20), (90, 60, 0))]                       # floor slab
    boxes += [((10 * k, 0, 0), (70, 40, rise * (k + 1))) for k in range(4)]
    if fill:
        boxes.append(((-5, 0, 0), (40, 40, 30)))                   # convex fill over the flight
    for i, (low, high) in enumerate(boxes):
        lo = [low[0] + MINS[0], low[1] + MINS[1], low[2] + MINS[2]]
        hi = [high[0] + MAXS[0], high[1] + MAXS[1], high[2] + MAXS[2]]
        root = len(data[9]) // 8
        for axis in range(3):
            for sign, bound in ((1, hi[axis]), (-1, -lo[axis])):
                normal = [0., 0., 0.]; normal[axis] = sign
                index = len(data[1]) // 20
                data[1] += struct.pack('<4fi', *normal, bound, 3)
                node = len(data[9]) // 8
                data[9] += struct.pack('<ihh', index, -1, node + 1 if node - root < 5 else -2)
        models.append(struct.pack('<9f7i', *low, *high, 0, 0, 0, -1, root, -1, -1, 0, 0, 0))
        entities.append('{\n"classname" "func_wall"\n"model" "*%d"\n"aw_ref" "%d"\n"origin" "0 0 0"\n"angles" "0 0 0"\n}'
                        % (len(models) - 1, 200 + i))
    data[0] = bytearray(('\n'.join(entities) + '\n\0').encode())
    data[3] = bytearray(b''.join(struct.pack('<3f', *p) for p in verts))
    data[7] = bytearray(b''.join(faces))
    data[12] = bytearray(b''.join(struct.pack('<HH', *e) for e in edges))
    data[13] = bytearray(b''.join(struct.pack('<i', s) for s in surf))
    data[14] = bytearray(b''.join(models))
    return pack_lumps(data)


@unittest.skipUnless(READY, 'numpy required')
class StairWalkGateTests(unittest.TestCase):
    def rows(self, raw):
        import stair_walk
        return stair_walk.check_map((self.write(raw), None, {}))[1]

    def write(self, raw, name='room'):
        tmp = tempfile.mkdtemp(); self.addCleanup(lambda: __import__('shutil').rmtree(tmp))
        path = Path(tmp) / 'maps'; path.mkdir()
        (path / (name + '.bsp')).write_bytes(raw)
        return str(path / (name + '.bsp'))

    def test_open_flight_passes(self):
        import stair_walk
        rows = [r for r in self.rows(build()) if r['kind'] == 'step']
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(all(r['flight'] for r in rows))
        self.assertEqual({r['result'] for r in rows}, {'passed'})
        self.assertFalse([r for r in rows if stair_walk._gating(r)])

    def test_filled_flight_fails_with_its_position_and_rise(self):
        import stair_walk
        failed = [r for r in self.rows(build(fill=True)) if stair_walk._gating(r)]
        self.assertTrue(failed)
        self.assertEqual(failed[0]['ref'], '100')
        self.assertIn(failed[0]['detail']['status'], stair_walk.BLOCKING)
        self.assertEqual(failed[0]['rise'], 4.0)

    def test_require_stops_the_image_on_an_unclimbable_flight(self):
        import stair_walk
        path = Path(self.write(build(fill=True))).parent.parent
        with self.assertRaisesRegex(ValueError, 'Stair walkability gate failed'):
            stair_walk.require(path, path / 'stair-walk.json')
        self.assertEqual(__import__('json').loads((path / 'stair-walk.json').read_text())['status'], 'failed')
        # A recorded, owner-approved map is reported but does not stop it.
        report = stair_walk.require(path, path / 'stair-walk.json', exempt=['room'])
        self.assertTrue(report['exempt_failures'])
        self.assertEqual(report['status'], 'passed')

    def test_lone_step_is_advisory(self):
        import stair_walk
        rows = [dict(kind='step', flight=False, result='failed', detail=dict(status='blocked'))]
        self.assertFalse(stair_walk._gating(rows[0]))

    def test_check_polys_interface(self):
        """The CHIM builder calls check_polys with its own scene object."""
        import inspect
        import stair_walk
        self.assertEqual(list(inspect.signature(stair_walk.check_polys).parameters),
                         ['polys', 'scene', 'core', 'contents', 'proxy'])


if __name__ == '__main__':
    unittest.main()
