import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_bounded_world import checked_bounds, prepare_inputs, terrain_brushes, audit_world_samples
from prepare_quake import brush, box
from player_hull import pack_lumps
from test_replace_bsp_world import fixture


def triangle(x, name):
    top = [[x, 0, 32], [x+128, 0, 48], [x, 128, 64]]
    return brush(top+[[p[0], p[1], -512] for p in top],
                 [(0, 1, 2), (3, 5, 4), (0, 3, 4), (1, 4, 5), (2, 5, 3)], name)


def texture_bsp():
    names = ['g0', 'g1', 'sky', 'stone', '*water']
    data = [bytearray() for _ in range(15)]
    tex = bytearray(struct.pack('<i', len(names))+bytes(4*len(names)))
    for i, name in enumerate(names):
        struct.pack_into('<i', tex, 4+4*i, len(tex))
        tex.extend(name.encode().ljust(16, b'\0')+struct.pack('<II4I', 16, 16, 40, 296, 360, 376)+bytes([i])*340)
    data[2] = tex
    return pack_lumps(data)


class BoundedWorldTests(unittest.TestCase):
    def test_keep_entire_intersecting_triangle_and_original_pixels(self):
        near, far = triangle(0, 'g0'), triangle(1024, 'g1')
        source = '{\n'+near+'\n'+far+'\n'+box([0, 0, 0], [8, 8, 8], 'clip')+'\n}'
        text, wad, report = prepare_inputs(source, texture_bsp(), [[16, 16], [80, 80]])
        self.assertIn(near, text)
        self.assertNotIn(far, text)
        self.assertNotIn('clip', text)
        self.assertEqual(report['selected_ground_brushes'], 1)
        self.assertEqual(report['excluded_brushes']['clip'], 1)
        self.assertEqual(report['enclosure'], [[-32, -32], [160, 160]])
        self.assertIn(bytes([4])*340, wad)
        self.assertNotIn('g1', report['texture_names'])

    def test_unknown_world_geometry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            terrain_brushes(triangle(0, 'g0')+box([0, 0, 0], [1, 1, 1], 'wall'))

    def test_source_extent_and_invalid_coverage_rejected(self):
        with self.assertRaisesRegex(ValueError, 'beyond source'):
            prepare_inputs(triangle(0, 'g0'), texture_bsp(), [[-1, 0], [64, 64]])
        for bounds in ([[0, 0], [0, 1]], [[0, 0], [float('nan'), 1]], [[0], [1]]):
            with self.assertRaises(ValueError):
                checked_bounds(bounds)

    def test_boundary_intersection_is_inclusive(self):
        source = triangle(0, 'g0')+triangle(128, 'g1')
        _, _, report = prepare_inputs(source, texture_bsp(), [[64, 16], [128, 80]])
        self.assertEqual(report['selected_ground_brushes'], 2)

    def test_terrain_collision_regression_detected(self):
        source = fixture()
        report = audit_world_samples(source, source, [[-16, -16], [16, 16]])
        self.assertEqual(report['samples'], 8092)
        with self.assertRaisesRegex(ValueError, 'collision sample mismatch'):
            audit_world_samples(source, fixture(world_x=8), [[-16, -16], [16, 16]])

    def test_certified_sea_strip_coverage_keeps_enclosure_outside(self):
        # First generated candidate provides a recognizable original shell.
        source, _, _ = prepare_inputs(triangle(0, 'g0')+triangle(1024, 'g1'),
                                       texture_bsp(), [[16, 16], [80, 80]])
        # Enlarge that generated shell so a strip outside the LAND is certified.
        source = source.replace('-32.000', '-96.000').replace('-64.000', '-128.000')
        _, _, report = prepare_inputs(source, texture_bsp(), [[-31, 16], [80, 80]])
        self.assertEqual(report['enclosure'][0][0], -63)
        self.assertIsNotNone(report['certified_source_sea_extent'])
        with self.assertRaisesRegex(ValueError, 'enclosure contract'):
            prepare_inputs(source.replace('*water 0 0 0 1 1', '*water 0 0 0 2 2'),
                           texture_bsp(), [[-31, 16], [80, 80]])


if __name__ == '__main__':
    unittest.main()
