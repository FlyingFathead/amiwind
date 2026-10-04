import tempfile,unittest
from pathlib import Path
import numpy as np
from canonical_land_reference import CanonicalLand

class CanonicalTests(unittest.TestCase):
    def packet(self,heights=None,cells=None,materials=None,water=None):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'terrain.npz'
        np.savez(path,cells=np.array([[-1,-1]]) if cells is None else cells,
                 heights=np.full((1,65,65),-200.) if heights is None else heights,
                 materials=np.full((1,16,16),7) if materials is None else materials,
                 water=np.zeros(1) if water is None else water,spacing=np.array(128))
        return path
    def test_seabed_and_missing(self):
        t=CanonicalLand(self.packet(),[-2048,-2048,0])
        self.assertEqual(t.sample(16,16)['height'],-50)
        self.assertFalse(t.sample(16,16)['water_is_receiver'])
        self.assertEqual(t.sample(16,16)['material'],7)
        self.assertIsNone(t.sample(-1,16))
    def test_half_open_tile_bounds(self):
        t=CanonicalLand(self.packet(),[-2048,-2048,0])
        self.assertEqual(len(list(t.triangles([[0,0],[32,32]]))),2)
        self.assertEqual(len(list(t.triangles([[0,0],[2048,2048]]))),8192)
    def test_original_diagonal(self):
        h=np.zeros((1,65,65));h[0,0,1]=40;h[0,1,1]=80;h[0,1,0]=120
        t=CanonicalLand(self.packet(heights=h),[-2048,-2048,0])
        self.assertEqual(t.sample(24,8)['height'],10)
        self.assertEqual(t.sample(8,24)['height'],20)
    def test_invalid_inputs(self):
        for arguments in ({'cells':np.array([[.5,0]])},{'water':np.ones(1)},{'materials':np.zeros((1,2,2))}):
            with self.assertRaises(ValueError):CanonicalLand(self.packet(**arguments),[0,0,0])
    def test_cell_seam(self):
        h=np.zeros((2,65,65));h[1,:,0]=4
        with self.assertRaisesRegex(ValueError,'seam'):
            CanonicalLand(self.packet(heights=h,cells=np.array([[0,0],[1,0]]),materials=np.zeros((2,16,16))),[0,0,0])

if __name__=='__main__':unittest.main()
