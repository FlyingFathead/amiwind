"""Town seabed prism regression: keep original surfaces and valid half-spaces."""
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'tools', ROOT/'src'):
    sys.path.insert(0,str(p))
import prepare_quake as pq

class TownGroundTests(unittest.TestCase):
    def check_prism(self, heights):
        tri=[[0,0,heights[0]],[128,0,heights[1]],[128,128,heights[2]]]
        grids=[{'heights':[[z/pq.SCALE for z in heights]]}]
        with patch.object(pq,'town_ground_triangles',return_value=[(tri,94)]):
            raw=pq.town_ground_brushes(grids)[0]
        planes=[]
        for line in raw.splitlines()[1:-1]:
            points=np.array([[float(x) for x in point.split()] for point in re.findall(r'\( ([^()]*) \)',line)])
            self.assertEqual(points.shape,(3,3))
            a,b,c=points; normal=np.cross(a-b,c-b)
            self.assertGreater(np.linalg.norm(normal),0)
            planes.append((a,normal))
        top=np.array(tri)
        first=np.array([[float(x) for x in point.split()] for point in re.findall(r'\( ([^()]*) \)',raw.splitlines()[1])])
        self.assertEqual(sorted(map(tuple,first)),sorted(map(tuple,top)))
        bottom=pq.town_ground_base(grids)
        self.assertLess(bottom,min(heights))
        vertices=np.vstack([top,[[p[0],p[1],bottom] for p in tri]])
        for a,normal in planes:
            self.assertTrue(np.all((vertices-a)@normal<=1e-6))
        return bottom

    def test_flat_ocean_at_historical_floor(self):
        self.assertEqual(self.check_prism([-512,-512,-512]),-544)

    def test_deeper_ocean_preserves_all_surface_heights(self):
        self.assertEqual(self.check_prism([-750,-800,-768]),-832)

    def test_slope_crossing_historical_floor_is_closed(self):
        self.check_prism([-520,-480,-500])

    def test_shallow_ground_preserves_historical_floor(self):
        self.assertEqual(self.check_prism([-200,-100,0]),-512)

    def test_map_rounding_cannot_collapse_a_thin_prism(self):
        self.assertEqual(pq.town_ground_base([{'heights':[[-511.9999/pq.SCALE]]}]),-544)

    def test_invalid_heights_are_refused(self):
        for heights in ([],[float('nan')],[float('inf')]):
            with self.assertRaises(ValueError):
                pq.town_ground_base([{'heights':[heights]}])

if __name__=='__main__':
    unittest.main()
