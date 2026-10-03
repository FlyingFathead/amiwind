"""Asset-free regression for canonical-geometry lightmap overrun repair."""
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from check_geometry_render_inputs import BSP
from player_hull import lumps, pack_lumps
from repair_bsp_light_bounds import repair_light_bounds
from test_replace_bsp_world import fixture


def truncated_inline():
    data = lumps(fixture(inline=True))
    for index, point in enumerate(((1.2, 0, 0), (0, 0, 0), (0, 16, 0)), 3):
        struct.pack_into('<3f', data[3], index*12, *point)
    struct.pack_into('<8f', data[6], 0, 21.7, 0, 0, 165.96, 0, 1, 0, 0)
    struct.pack_into('<i', data[7], 16, -1)
    struct.pack_into('<i', data[7], 36, 0)
    data[8] = bytearray([80]*6)
    return pack_lumps(data)


class LightBoundsRepairTests(unittest.TestCase):
    lighting = {'ambient': [80, 80, 80], 'lights': []}

    def test_rebakes_final_float_grid_and_preserves_all_other_inputs(self):
        raw = truncated_inline()
        before = BSP(raw)
        for wide in (False, True):
            with self.assertRaisesRegex(ValueError, 'Light sample range outside lump'):
                before.face_inputs(1, wide)
        result, report = repair_light_bounds(raw, self.lighting)
        after = BSP(result)
        self.assertEqual(report['faces_verified'], 2)
        self.assertEqual(report['repairs'][0]['sample_dimensions'], (4, 2))
        self.assertEqual(report['repairs'][0]['old_available_bytes'], 6)
        self.assertEqual(after.parts[8], bytes([80]*14))
        for index in set(range(15))-{7, 8}:
            self.assertEqual(before.parts[index], after.parts[index])
        self.assertEqual(before.rows[7][0], after.rows[7][0])
        self.assertEqual(before.rows[7][1][:-1], after.rows[7][1][:-1])
        for wide in (False, True):
            self.assertEqual(after.face_inputs(1, wide)[-1], bytes([80]*8))
        with self.assertRaisesRegex(ValueError, 'No out-of-lump'):
            repair_light_bounds(result, self.lighting)

    def test_refuses_ambiguous_arithmetic_grids(self):
        data = lumps(truncated_inline())
        scale, offset = 2.73, -469.4419860839844
        for index, point in enumerate(((195.4, 0, 0), (184, 0, 0), (184, 16, 0)), 3):
            struct.pack_into('<3f', data[3], index*12, *point)
        struct.pack_into('<8f', data[6], 0, scale, 0, 0, offset, 0, 1, 0, 0)
        data[8] = bytearray([80])
        with self.assertRaisesRegex(ValueError, 'different grids'):
            repair_light_bounds(pack_lumps(data), self.lighting)

    def test_refuses_missing_placement_and_multiple_styles(self):
        for kind in ('placement', 'styles'):
            data = lumps(truncated_inline())
            if kind == 'placement':
                data[0] = data[0].replace(b'"model" "*1"', b'"model" "*9"')
            else:
                data[7][20+13] = 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                repair_light_bounds(pack_lumps(data), self.lighting)


if __name__ == '__main__':
    unittest.main()
