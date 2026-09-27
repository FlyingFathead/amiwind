"""Synthetic shape checks; no original meshes or textures are embedded."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
READY = all(importlib.util.find_spec(name) for name in ("numpy", "scipy"))
if READY:
    import numpy as np
    from mesh_geometry import surface_polygons, split_surface, collision_parts


@unittest.skipUnless(READY, "optional numpy/scipy geometry dependencies required")
class MeshGeometryTests(unittest.TestCase):
    def test_acute_piece_does_not_create_distant_solid_spike(self):
        from scipy.spatial import ConvexHull
        from prepare_mesh_bsp import bounded_planes
        from player_hull import MINS,MAXS
        points=np.array([[0,0,0],[100,0,0],[0,.1,0],[0,0,.1]],float)
        hull=ConvexHull(points)
        def contains(eq,p):
            n=eq[:,:3]
            d=-eq[:,3]+np.sum(np.where(n>=0,-n*np.array(MINS),-n*np.array(MAXS)),axis=1)
            return bool(np.all(n@p<=d+1e-5))
        # Original facet-only expansion extends far beyond the actual tip.
        self.assertTrue(contains(hull.equations,np.array([110,0,0])))
        bounded=bounded_planes(points,hull.equations)
        self.assertFalse(contains(bounded,np.array([110,0,0])))
        # Legitimate overlaps near every vertex must still collide.
        for vertex in points:
            for axis in range(3):
                for limit in (MINS[axis],MAXS[axis]):
                    p=vertex.copy();p[axis]-=limit*.99
                    self.assertTrue(contains(bounded,p))

    @staticmethod
    def area(poly):
        return abs(sum(np.cross(poly[i], poly[(i+1) % len(poly)])[2] for i in range(len(poly)))) / 2

    def test_merges_flat_quad_without_filling_missing_corner(self):
        # Six square tiles in an L; preserve its concave gap and surface area.
        vertices, faces = [], []
        for x, y in [(0,0), (1,0), (2,0), (0,1), (0,2)]:
            n = len(vertices)
            for u,v in [(x,y),(x+1,y),(x+1,y+1),(x,y+1)]:
                vertices.append([u*4,v*4,0,u,v,255,255,255,255])
            faces += [[n,n+1,n+2,0], [n,n+2,n+3,0]]
        result = surface_polygons(np.array(vertices,float), np.array(faces))
        self.assertAlmostEqual(sum(self.area(p[0]) for p in result), 5)
        self.assertLess(len(result), len(faces))
        for poly,mat,ax,off,normal in result:
            self.assertTrue(np.allclose(poly @ ax + off, poly[:,:2]))
            self.assertGreater(normal[2], 0)
            self.assertFalse(any(x>1.01 and y>1.01 for x,y,z in poly))

    def test_uv_splits_preserve_area_and_fit_surface_cache(self):
        p = np.array([[0.,0,0],[800.,0,0],[800.,500,0],[0.,500,0]])
        ax = np.array([[1.,0,0,13.],[0,1.,0,-5.]])
        result = split_surface(p, ax)
        self.assertGreater(len(result), 1)
        self.assertAlmostEqual(sum(self.area(q) for q in result), self.area(p))
        for q in result:
            uv = q @ ax[:,:3].T + ax[:,3]
            extent = (np.ceil(uv.max(0)/16)-np.floor(uv.min(0)/16))*16
            self.assertTrue(np.all(extent <= 256), extent)

    def test_disconnected_planks_keep_gap_in_collision(self):
        vertices, faces = [], []
        for x in (0., 40.):
            n=len(vertices)
            for u,v in [(x,0),(x+8,0),(x+8,8),(x,8)]:
                vertices.append([u,v,0,0,0,255,255,255,255])
            faces += [[n,n+1,n+2,0],[n,n+2,n+3,0]]
        parts=collision_parts(np.array(vertices),np.array(faces))
        self.assertEqual(len(parts),2)
        gap=np.array([6.,1.,0.])
        self.assertFalse(any(np.all(gap @ hull.equations[:,:3].T + hull.equations[:,3] <= 0) for points,hull,ids,error in parts))
