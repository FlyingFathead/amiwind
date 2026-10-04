import unittest,numpy as np
from test_canonical_land_reference import CanonicalTests
from canonical_land_reference import CanonicalLand
from canonical_face_clip import CanonicalClipper,coalesce_convex_union
from terrain_visual_cull import _area

class ClipTests(CanonicalTests):
    def clipper(self,h=None):return CanonicalClipper(CanonicalLand(self.packet(heights=h),[-2048,-2048,0]))
    def test_no_finite_bottom(self):
        c=self.clipper();q=np.array([[1,1,-10000],[20,1,-10000],[20,20,-10000],[1,20,-10000]])
        self.assertEqual(c.clip(q),[])
    def test_crossing_vertical_shared_tile_edge(self):
        c=self.clipper();q=np.array([[32,1,-100],[32,50,-100],[32,50,0],[32,1,0]])
        parts=c.clip(q)
        self.assertAlmostEqual(sum(_area(p) for p in parts),49*50.5)
        self.assertTrue(all(p[:,2].min()==-50.5 for p in parts))
    def test_sloped_crossing(self):
        h=np.array([[[float(x*4) for x in range(65)] for y in range(65)]])
        c=self.clipper(h);q=np.array([[0,8,-100],[32,8,-100],[32,8,10],[0,8,10]])
        parts=c.clip(q)
        self.assertAlmostEqual(sum(_area(p) for p in parts),320)
    def test_missing_blocks(self):
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):
            self.clipper().clip(np.array([[-40,1,0],[-1,1,0],[-1,20,0],[-40,20,0]]))
    def test_t_junction_union(self):
        parts=[np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]]),np.array([[0,1,0],[1,1,0],[1,2,0],[0,2,0]]),np.array([[1,0,0],[2,0,0],[2,2,0],[1,2,0]])]
        merged=coalesce_convex_union(parts);self.assertEqual(len(merged),1);self.assertEqual(_area(merged[0]),4)
    def test_concavity_retained(self):
        parts=[np.array([[0,0,0],[1,0,0],[1,2,0],[0,2,0]]),np.array([[1,0,0],[2,0,0],[2,1,0],[1,1,0]])]
        self.assertEqual(len(coalesce_convex_union(parts)),2)

    def test_boundary_tolerance_policy(self):
        land=CanonicalLand(self.packet(),[-2048,-2048,0])
        for tol in (-1,float('inf'),float('nan')):
            with self.assertRaises(ValueError):CanonicalClipper(land,boundary_tolerance=tol)
        c=CanonicalClipper(land,boundary_tolerance=2e-5)
        q=np.array([[1,1,-50.50001],[20,1,-50.50001],[20,20,-50.50001],[1,20,-50.50001]])
        self.assertTrue(np.array_equal(c.clip(q)[0],q))
        self.assertEqual(CanonicalClipper(land).clip(q),[],'Default remains exact, not an implicit global tolerance')
        q[:,2]=-50.50003
        self.assertEqual(c.clip(q),[],'Meaningful beyond-band burial still cut')
        self.assertFalse(hasattr(c,'already_clipped'))

    def test_repeat_raw_and_float32_transform_stability(self):
        # Source-owned synthetic sloped NPZ and yawed placement, not a game fixture.
        h=np.array([[[float(x*4+y*2) for x in range(65)] for y in range(65)]])
        land=CanonicalLand(self.packet(heights=h),[-2048,-2048,0]);c=CanonicalClipper(land,.5,boundary_tolerance=2e-5)
        q=np.array([[1,8,-100.],[65,8,-100.],[65,8,20.],[1,8,20.]])
        first=c.clip(q);self.assertLess(sum(_area(p) for p in first),_area(q));self.assertTrue(first)
        # Every generated first-cut boundary remains at actual terrain-minus-overlap.
        self.assertTrue(any(abs(p[2]-land.sample(*p[:2])['height']+.5)<1e-10 for part in first for p in part))
        key=lambda parts:sorted(tuple(sorted(tuple(v) for v in p)) for p in parts)
        raw=first
        for i in range(10):
            new=[p for part in raw for p in c.clip(part)];self.assertEqual(key(new),key(raw));raw=new
        theta=.73;rotation=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1]])
        origin=np.array([13.12345,-27.23456,41.34567])
        def reload(parts):return [((p-origin)@rotation).astype('<f4').astype(float)@rotation.T+origin for p in parts]
        serialized=reload(first)
        for i in range(10):
            new=reload([p for part in serialized for p in c.clip(part)]);self.assertEqual(key(new),key(serialized));serialized=new

    def test_union_winding_all_projection_axes_and_both_sides(self):
        vector=lambda p:sum((np.cross(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1)),np.zeros(3))
        base=[np.array([[0.,0,0],[1,0,0],[1,1,0],[0,1,0]]),np.array([[1.,0,0],[2,0,0],[2,1,0],[1,1,0]])]
        for axes in ((0,1,2),(2,0,1),(1,2,0)):
            for reverse in (False,True):
                parts=[p[:,axes][::-1] if reverse else p[:,axes] for p in base]
                merged=coalesce_convex_union(parts)
                self.assertEqual(len(merged),1)
                self.assertGreater(float(vector(merged[0])@vector(parts[0])),0)
                self.assertEqual(_area(merged[0]),2)
                reloaded=np.frombuffer(merged[0].astype('<f4').tobytes(),dtype='<f4').reshape(-1,3).astype(float)
                self.assertGreater(float(vector(reloaded)@vector(parts[0])),0)
                self.assertEqual({tuple(v) for v in merged[0]},{tuple(v) for v in reloaded})

    def test_rotated_placement_reclips_actual_serialized_vertices(self):
        from canonical_bsp_cull import _stable_local_parts
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':.2*x*x+.02*y}
        clip=CanonicalClipper(Ground(),.5,boundary_tolerance=2e-5)
        world=np.array([[1,8,-30.],[65,8,-30.],[65,8,1500.],[1,8,1500.]])
        theta=.051;rotation=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1.]])
        origin=np.array([103.941,-708.905,41.31])
        source=((world-origin)@rotation).astype('<f4').astype(float)
        first=clip.clip(source@rotation.T+origin)
        stable,recuts,depth,zeros=_stable_local_parts(first,source,origin,rotation,clip)
        self.assertGreater(recuts,0);self.assertGreater(depth,0);self.assertEqual(zeros,0)
        self.assertGreater(sum(_area(p) for p in stable),0)
        for p in stable:
            np.testing.assert_array_equal(p,p.astype('<f4').astype(float))
            q=p@rotation.T+origin;again=clip.clip(q)
            self.assertEqual(len(again),1);np.testing.assert_array_equal(q,again[0])
        self.assertEqual(clip.boundary_tolerance,2e-5)

    def test_serialized_placement_nonconvergence_blocks(self):
        from canonical_bsp_cull import _stable_local_parts
        class Shrink:
            def clip(self,q):return [q[0]+(q-q[0])*.9]
        source=np.array([[0.,0,0],[32,0,0],[0,32,0]])
        with self.assertRaisesRegex(ValueError,'not repeat-stable'):
            _stable_local_parts([source*.5],source,np.zeros(3),np.eye(3),Shrink())

    def test_unchanged_serialized_placement_is_exact(self):
        from canonical_bsp_cull import _stable_local_parts
        class Unexpected:
            def clip(self,q):raise AssertionError('Unchanged source does not need another clip')
        source=np.array([[1.,2,3],[4,5,6],[7,8,3]])
        stable,recuts,depth,zeros=_stable_local_parts([source.copy()],source,np.zeros(3),np.eye(3),Unexpected())
        self.assertIs(stable[0],source);self.assertEqual((recuts,depth,zeros),(0,0,0))

    def test_new_bsp_ground_loop_matches_native_clockwise_contract(self):
        from canonical_face_clip import bsp_front_winding,_area_vector
        # A sloping source-owned LAND quad. Its math loop points upward, but
        # storing that loop unchanged leaves native scanline spans reversed.
        q=np.array([[0.,0,2],[32,0,6],[32,32,4],[0,32,0]])
        up=_area_vector(q);up/=np.linalg.norm(up)
        self.assertGreater(float(_area_vector(q)@up),0)
        for side in (0,1):
            for source in (q,q[::-1]):
                fixed=bsp_front_winding(source,up,side)
                normal=up*(-1 if side else 1)
                self.assertLess(float(_area_vector(fixed)@normal),0)
                self.assertEqual({tuple(v) for v in fixed},{tuple(v) for v in q})
                self.assertAlmostEqual(_area(fixed),_area(q))
                np.testing.assert_array_equal(bsp_front_winding(fixed,up,side),fixed)

    def test_clipped_winding_both_sides_after_float32_reload(self):
        c=self.clipper()
        source=np.array([[1.,1,-100],[65,1,-100],[65,1,0],[1,1,0]])
        vector=lambda p:sum((np.cross(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1)),np.zeros(3))
        for q in (source,source[::-1]):
            parts=c.clip(q);self.assertTrue(parts)
            for part in parts:
                reloaded=np.frombuffer(part.astype('<f4').tobytes(),dtype='<f4').reshape(-1,3).astype(float)
                self.assertGreater(float(vector(reloaded)@vector(q)),0)
                self.assertAlmostEqual(sum(_area(p) for p in parts),64*50.5)

if __name__=='__main__':unittest.main()
