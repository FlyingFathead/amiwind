import unittest
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from canonical_terrain_brushes import canonical_prisms


class Land:
    def triangles(self, bounds):
        return iter([[[0,0,1],[32,0,3],[32,32,5]], [[0,0,1],[32,32,5],[0,32,7]]])
    def sample(self,x,y): return {'height': 1, 'material': 9}
    def metadata(self): return {'kind': 'synthetic authored LAND'}


class CanonicalPrismTests(unittest.TestCase):
    def test_direct_distinct_diagonal_planes_and_precision(self):
        brushes, receipt = canonical_prisms(Land(), [[0,0],[32,32]])
        self.assertEqual(len(brushes), 2)
        self.assertIn('( 32 32 5 )', brushes[0])
        self.assertIn('( 0 32 7 )', brushes[1])
        self.assertEqual(receipt['source_triangles'],2)
        self.assertNotEqual(brushes[0],brushes[1])
    def test_missing_coverage_fails(self):
        with self.assertRaisesRegex(ValueError,'coverage'):
            canonical_prisms(Land(), [[0,0],[64,32]])
    def test_bottom_cannot_cut_ground(self):
        with self.assertRaisesRegex(ValueError,'bottom'):
            canonical_prisms(Land(), [[0,0],[32,32]], bottom=2)


if __name__=='__main__': unittest.main()
