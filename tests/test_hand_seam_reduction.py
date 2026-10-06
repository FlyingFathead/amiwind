# SPDX-License-Identifier: GPL-3.0-only
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from hand_seam_reduction import reduce_shape,boundary_edges


class HandSeamReduction(unittest.TestCase):
    def grid(self):
        points=np.array([(x*.1,y*.1,0) for y in range(5) for x in range(5)])
        triangles=[]
        for y in range(4):
            for x in range(4):
                a=y*5+x;triangles.extend(((a,a+1,a+6),(a,a+6,a+5)))
        return dict(positions=np.stack((points,points+[0,0,1])),faces=np.array(triangles),
                    uv=points[:,:2].copy(),colours=np.ones((len(points),4)))

    def test_interior_collapses_keep_authored_boundary_and_exact_sampled_vertices(self):
        shape=self.grid();reduced,report=reduce_shape(shape,12,max_uv_change=.25)
        self.assertLess(len(reduced['faces']),len(shape['faces']))
        source_indices=np.array(report['source_vertex_indices'])
        self.assertEqual(boundary_edges(source_indices[reduced['faces']]),boundary_edges(shape['faces']))
        np.testing.assert_array_equal(reduced['positions'],shape['positions'][:,source_indices])
        self.assertEqual(report['new_boundary_edges'],0)

    def test_later_pose_uv_and_tint_constraints_can_refuse_unsafe_budget(self):
        shape=self.grid()
        unchanged,report=reduce_shape(shape,1,max_displacement=0)
        self.assertEqual(len(unchanged['faces']),32);self.assertFalse(report['target_reached'])
        shape['uv']*=100
        unchanged,_=reduce_shape(shape,1,max_uv_change=.01)
        self.assertEqual(len(unchanged['faces']),32)
        shape=self.grid();shape['colours'][:,0]=np.arange(25)/25
        unchanged,_=reduce_shape(shape,1)
        self.assertEqual(len(unchanged['faces']),32)
        shape=self.grid();shape['positions'][1,:,0]*=100
        unchanged,_=reduce_shape(shape,1,max_displacement=.01)
        self.assertEqual(len(unchanged['faces']),32)

    def test_cannot_collapse_a_closed_tetrahedron_into_duplicate_faces(self):
        points=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]])
        shape=dict(positions=points[None],faces=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]]),
                   uv=points[:,:2],colours=np.ones((4,4)))
        reduced,report=reduce_shape(shape,2,max_displacement=2,max_uv_change=2)
        self.assertEqual(len(reduced['faces']),4);self.assertFalse(report['target_reached'])


    def test_projection_and_explicit_locks_are_never_removed(self):
        from hand_seam_reduction import projection_locks
        shape=self.grid();shape['positions'][:,:,0]+=5
        locks=projection_locks(shape,near=5.15)
        reduced,report=reduce_shape(shape,1,max_displacement=1,max_uv_change=1,extra_locked=locks)
        self.assertTrue(locks.issubset(set(report['source_vertex_indices'])))
        unchanged,_=reduce_shape(shape,1,max_displacement=1,max_uv_change=1,extra_locked=set(range(25)))
        self.assertEqual(len(unchanged['faces']),32)
        with self.assertRaises(ValueError):reduce_shape(shape,1,extra_locked={25})
