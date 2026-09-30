"""Terrain sampling, open armour and small-font regressions using synthetic data."""
import importlib.util
from pathlib import Path
import struct
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional conversion dependencies')
class TerrainMaterials(unittest.TestCase):
    def setUp(self):
        from balmora_regions import config
        self.settings = config()
        self.grid = {'heights': [[168]*65 for _ in range(65)],
                     'materials': [[34]*16 for _ in range(16)]}
        self.grid['materials'][3][12] = 0
        self.grids = {(-3, -2): self.grid}

    def test_reported_default_tile_repaired_without_touching_other_defaults(self):
        from prepare_balmora import terrain_at, terrain_material
        self.assertEqual(terrain_material(self.grids, self.settings, 550, -600), 34)
        self.assertEqual(terrain_at(self.grids, self.settings, 512, -640)[0], 42)
        self.grid['materials'][3][13] = 0
        self.assertEqual(terrain_material(self.grids, self.settings, 700, -600), 0)
        self.grid['materials'][3][12] = 8
        with self.assertRaisesRegex(ValueError, 'source tile'):
            terrain_material(self.grids, self.settings, 550, -600)

    def test_material_is_sampled_inside_quad_not_last_height_corner(self):
        from prepare_balmora import terrain_map
        self.settings['terrain_material_repairs'] = []
        self.grid['materials'][2][12] = 34
        text = terrain_map({'coverage': [[512, -768], [640, -640]]},
                           self.grids, self.settings, [0, 0, 80], '')
        self.assertIn(' g34 ', text)
        self.assertNotIn(' g0 ', text)

    def test_part6_default_patch_matches_surrounding_scrub(self):
        from prepare_balmora import terrain_material
        grid={'heights':[[504]*65 for _ in range(65)],
              'materials':[[14]*16 for _ in range(16)]}
        grid['materials'][0][15]=0
        grids={(-4,-2):grid}
        self.assertEqual(terrain_material(grids,self.settings,-1056,-921),14)
        grid['materials'][0][14]=0
        self.assertEqual(terrain_material(grids,self.settings,-1200,-921),0)
        grid['materials'][0][15]=24
        with self.assertRaisesRegex(ValueError,'source tile'):
            terrain_material(grids,self.settings,-1056,-921)


@unittest.skipUnless(all(importlib.util.find_spec(m) for m in
                       ('numpy', 'scipy', 'fast_simplification')), 'optional actor dependencies')
class ArmourCoverage(unittest.TestCase):
    def test_open_curved_panel_retains_area_and_extent(self):
        import numpy as np
        from npc_geometry import simplify_shape
        points = np.array([[4*np.sin(t), 3*np.cos(t), z]
                           for z in np.linspace(0, 10, 12)
                           for t in np.linspace(-1.4, 1.4, 17)])
        faces = []
        for row in range(11):
            for col in range(16):
                a = row*17+col
                faces.extend(((a, a+1, a+18), (a, a+18, a+17)))
        faces = np.array(faces, np.int32)
        reduced, triangles = simplify_shape(points, faces, 4, preserve_shell=True)
        def area(p, f):
            return np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],
                                           p[f[:,2]]-p[f[:,0]]), axis=1).sum()
        self.assertGreaterEqual(area(reduced, triangles), .8*area(points, faces))
        self.assertTrue(np.all(np.ptp(reduced, axis=0) >= .7*np.ptp(points, axis=0)))
        self.assertLess(len(triangles), len(faces))


class SmallOutlineFont(unittest.TestCase):
    def test_advance_contract_and_closed_counter_survive_native_packing(self):
        from PIL import ImageFont
        from prepare_ui import pack_truetype, rounded
        path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        if not path.is_file():
            self.skipTest('Optional system test font')
        for size in (12, 14, 16):
            native = ImageFont.truetype(str(path), size, encoding='unic',
                                       layout_engine=ImageFont.Layout.BASIC)
            raw = pack_truetype(path, size)
            for c in 'your choose soj':
                off,w,h,left,top,advance,_ = struct.unpack_from('<HBBbbBB',raw,8+ord(c)*8)
                self.assertEqual(advance, rounded(native.getlength(c)))
                self.assertLessEqual(2056+off+(w*h+3)//4, len(raw))
                if c == 'o':
                    ink = [[(raw[2056+off+(y*w+x)//4]>>(6-2*((y*w+x)%4)))&3
                            for x in range(w)] for y in range(h)]
                    top_row = next(row for row in ink if any(row))
                    self.assertTrue(any(top_row[1:-1]))
                    self.assertEqual(ink[h//2][w//2], 0)
