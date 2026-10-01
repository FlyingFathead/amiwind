"""Synthetic world-space checks independent of owned game data."""
import math
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from world_survey import cell_of, local_to_world, world_to_local, triangle_bins, SpatialIndex, evaluate_cell, candidate_boxes

class WorldSurveyTests(unittest.TestCase):
    def test_negative_cells_and_reversible_area_coordinates(self):
        self.assertEqual(cell_of([-1,-8193]),[-1,-2])
        a={'centre':[-20480,-12288],'scale':.25}
        for p in ([0,0,0],[-63,-51,86],[8192,-5,-2]):
            self.assertEqual(world_to_local(local_to_world(p,a),a),p)
        with self.assertRaises(ValueError):cell_of([math.nan,0])
        with self.assertRaises(ValueError):local_to_world([0,0,0],dict(a,scale=0))
    def test_transformed_centroids_conserve_placed_triangles(self):
        ref={'position':[8191,-1,0],'rotation_radians':[0,0,0],'scale':2}
        bins=dict(triangle_bins(np.array([[0,0,0],[1,1,0],[-1,0,0]]),ref))
        self.assertEqual(sum(bins.values()),3)
        self.assertEqual(bins[(4,0)],1)
    def test_full_bounds_keep_distant_origin_and_overlap_objects_once(self):
        index=SpatialIndex([{'bounds':[[-20000,-4,0],[20000,4,10]],'triangles':100},
                            {'bounds':[[200,200,0],[300,300,20]],'triangles':7}])
        self.assertEqual(index.measure([[0,-1],[1,1]]),{'placed_source_triangles':100,'references':1})
        self.assertEqual(index.measure([[-30000,-30000],[30000,30000]])['placed_source_triangles'],107)
        self.assertEqual(index.measure([[201,201],[299,299]])['placed_source_triangles'],7)
        self.assertEqual(evaluate_cell([0,0],index,50,3584)['candidate'],None)
        self.assertEqual(evaluate_cell([0,0],index,110,3584)['candidate'],1)
    def test_bounded_subdivision_and_invalid_geometry(self):
        boxes=list(candidate_boxes([-1,1],2,100))
        self.assertEqual(len(boxes),4)
        self.assertEqual(boxes[0],[[-8292,8092],[-3996,12388]])
        with self.assertRaises(ValueError):list(candidate_boxes([0,0],3,0))
        with self.assertRaises(ValueError):SpatialIndex([{'bounds':[[1,0,0],[0,1,1]],'triangles':1}])
        self.assertEqual(SpatialIndex([]).measure([[0,0],[1,1]])['references'],0)
if __name__=='__main__':unittest.main()
