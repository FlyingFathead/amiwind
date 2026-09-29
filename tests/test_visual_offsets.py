"""Door clearance must preserve UVs, collision and unrelated placements."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from visual_offsets import apply_visual_offsets, visual_key
from prepare_mesh_bsp import _prepare_placement, _instance_key


class VisualOffsetTests(unittest.TestCase):
    def test_reference_selection_and_disable(self):
        index={'models':[{'source':'meshes/d/ex_nord_door_01.nif'}, {'source':'other'}]}
        refs=[{'model_index':mi,'number':n} for mi,n in [(0,113833),(0,113893),(0,113864),(1,113833)]]
        apply_visual_offsets(index,refs)
        self.assertEqual([visual_key(r) for r in refs],[(0,-2,0),(0,-2,0),(0,0,0),(0,0,0)])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'disabled.json';path.write_text(json.dumps({'enabled':False}))
            apply_visual_offsets(index,refs,path)
        self.assertTrue(all(visual_key(r)==(0,0,0) for r in refs))

    def test_visual_offset_preserves_uv_and_collision(self):
        ref={'model_index':0,'number':113833,'scale':1,'position':[0,0,0],
             'rotation_radians':[0,0,0]}
        p=np.array([[0.,0,0],[1,0,0],[0,0,1]])
        tetra=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        axes=np.array([[1.,0],[0,0],[0,1]])
        data=(np.column_stack((tetra*4,np.zeros((4,2)))),np.array([[0,1,2,0]]),
              [(p,0,axes,np.zeros(2),np.array([0.,-1,0]))],[(tetra,None,[],0)],{})
        before=_prepare_placement((ref,data,64,(0,0),None))
        moved={**ref,'_visual_offset':[0,-2,0]}
        after=_prepare_placement((moved,data,64,(0,0),None))
        a,b=before[0][0],after[0][0]
        np.testing.assert_allclose(b[0],a[0]+[0,-2,0])
        np.testing.assert_allclose(b[0]@b[2]+b[3],a[0]@a[2]+a[3])
        np.testing.assert_array_equal(before[1][0][0],after[1][0][0])
        self.assertEqual(_instance_key(ref,None),_instance_key(moved,None))
        self.assertNotEqual(visual_key(ref),visual_key(moved))
        self.assertTrue(np.all(b[0]>=after[2]) and np.all(b[0]<=after[3]))
