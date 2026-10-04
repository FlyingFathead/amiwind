# SPDX-License-Identifier: GPL-3.0-only
import unittest,struct
from unittest.mock import patch
import numpy as np
from test_compact_bsp import fixture
from player_hull import lumps,pack_lumps
from replace_bsp_world import rows,FORMATS
from canonical_world_cull import cull_world_render
class Land:
    def metadata(self):return {'synthetic':True}
class Clip:
    def __init__(self,*args,**kwargs):pass
    def clip(self,q):return [np.array([[0,16,0],[0,32,0],[0,16,16.]])]
class WorldClipTests(unittest.TestCase):
    def source(self):
        d=lumps(fixture());r=rows(d)
        d[0]=bytearray(bytes(d[0]).replace(b'\0',b'{"classname" "func_wall" "model" "*1" "aw_ref" "43"}\0'))
        r[3][:3]=[[0,0,0],[0,32,0],[0,0,32]]
        r[6][0][:8]=[0,1,0,0,0,0,1,0]
        r[7][0][5:9]=[0,1,255,255];r[7][0][-1]=0
        d[8]=bytearray(range(18))
        blobs=[struct.pack('<16s6I',name,16,16,40,296,360,376)+bytes(340) for name in (b'wall',b'wall1',b'wall2')]
        d[2]=bytearray(struct.pack('<4i',3,16,396,776)+b''.join(blobs))
        for i in (3,6,7):d[i]=bytearray().join(struct.pack(FORMATS[i],*v) for v in r[i])
        return pack_lumps(d)
    def test_crossing_lightmapped_face_crops_every_style(self):
        source=self.source()
        with patch('canonical_world_cull.CanonicalClipper',Clip):out,receipt=cull_world_render(source,Land(),{'enabled':True,'overlap':.5})
        d=lumps(out);r=rows(d);f=r[7][0]
        self.assertEqual(bytes(d[8][f[-1]:f[-1]+8]),bytes([1,2,4,5,10,11,13,14]))
        self.assertEqual(receipt['counts']['lightmapped_fragments_cropped'],1)
        self.assertEqual(d[4],lumps(source)[4]);self.assertTrue(receipt['acceptance'].startswith('INCOMPLETE'))
    def test_off_is_exact(self):
        source=self.source();out,receipt=cull_world_render(source,Land(),{'enabled':False})
        self.assertIs(out,source)

    def points(self,raw,model):
        r=rows(lumps(raw));f=r[7][r[14][model][14]]
        return np.array([r[3][r[12][abs(r[13][i][0])][r[13][i][0]<0]] for i in range(f[2],f[2]+f[3])])
    def reverse_source(self,model):
        data=lumps(self.source());r=rows(data);f=r[7][r[14][model][14]]
        start,count=f[2:4]
        r[13][start:start+count]=[[-edge[0]] for edge in reversed(r[13][start:start+count])]
        data[13]=bytearray().join(struct.pack(FORMATS[13],*row) for row in r[13])
        return pack_lumps(data)
    def assert_source_winding(self,source,out,model):
        a,b=self.points(source,model),self.points(out,model)
        self.assertGreater(float(np.cross(a[1]-a[0],a[2]-a[0])@np.cross(b[1]-b[0],b[2]-b[0])),0)
    def test_world_writer_preserves_source_loop_opposing_plane(self):
        source=self.reverse_source(0)
        with patch('canonical_world_cull.CanonicalClipper',Clip):
            out,_=cull_world_render(source,Land(),{'enabled':True,'overlap':.5})
        self.assert_source_winding(source,out,0)
    def test_placement_writer_preserves_source_loop_opposing_plane(self):
        from canonical_bsp_cull import cull_bsp
        source=self.reverse_source(1)
        class Shrink:
            def __init__(self,*args,**kwargs):self.calls=0
            def clip(self,q):
                self.calls+=1
                return [q[0]+(q-q[0])*.5] if self.calls==1 else [q]
        with patch('canonical_bsp_cull.CanonicalClipper',Shrink),patch('canonical_bsp_cull.cull_world_render',side_effect=lambda raw,*args:(raw,{})):
            out,_=cull_bsp(source,Land(),{'enabled':True,'overlap':.5})
        self.assert_source_winding(source,out,1)
    def water_source(self):
        data=lumps(self.source());offset=struct.unpack_from('<i',data[2],4)[0]
        data[2][offset:offset+16]=b'*water'.ljust(16,b'\0')
        r=rows(data);r[1][0]=[0,0,1,0,2];r[3][:3]=[[0,0,0],[32,0,0],[0,32,0]]
        for i in (1,3):data[i]=bytearray().join(struct.pack(FORMATS[i],*row) for row in r[i])
        return pack_lumps(data)
    def test_visible_water_above_real_seabed_survives(self):
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':-10}
            def metadata(self):return {'synthetic':True}
        source=self.water_source()
        out,_=cull_world_render(source,Ground(),{'enabled':True,'overlap':.5})
        np.testing.assert_array_equal(self.points(source,0),self.points(out,0))
    def test_upward_water_buried_under_ground_is_removed(self):
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':10}
            def metadata(self):return {'synthetic':True}
        out,receipt=cull_world_render(self.water_source(),Ground(),{'enabled':True,'overlap':.5})
        self.assertEqual(rows(lumps(out))[14][0][15],0)
        self.assertEqual(receipt['counts']['removed'],1)
    def test_float32_water_boundary_stays_on_source_plane_and_repeats(self):
        from canonical_world_cull import _quantize_horizontal_water
        from canonical_face_clip import CanonicalClipper
        threshold=1100.00008
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':.5+64*(x-threshold)}
        clip=CanonicalClipper(Ground(),.5,boundary_tolerance=2e-5)
        source=np.array([[1000,0,0],[1200,0,0],[1200,32,0],[1000,32,0.]])
        p=np.array([[threshold,4,0],[threshold,16,0],[1000,4,0.]])
        fixed,steps=_quantize_horizontal_water(p,source,clip)
        self.assertGreater(steps,0);np.testing.assert_array_equal(fixed[:,2],p[:,2])
        self.assertTrue(all(point[2]+.5-clip.land.sample(*point[:2])['height']>=-2e-5 for point in fixed))
        again,steps=_quantize_horizontal_water(fixed,source,clip)
        self.assertEqual(steps,0);np.testing.assert_array_equal(fixed,again)

    def test_water_writer_actually_recuts_quantized_parts(self):
        from canonical_world_cull import _stable_horizontal_water_parts
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':-10}
        class Recut:
            land=Ground();overlap=.5;boundary_tolerance=2e-5
            def __init__(self):self.calls=0
            def clip(self,p):
                self.calls+=1
                return [p[0]+(p-p[0])*.5] if self.calls==1 else [p]
        p=np.array([[0,0,0],[2,0,0],[0,2,0.]])
        clip=Recut();parts,steps,recuts,depth=_stable_horizontal_water_parts([p],p,clip)
        self.assertEqual(clip.calls,2);self.assertEqual(recuts,1);self.assertEqual(depth,1)
        self.assertAlmostEqual(sum(np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))/2 for q in parts),.5)
    def test_water_writer_rejects_nonconverging_actual_recuts(self):
        from canonical_world_cull import _stable_horizontal_water_parts
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':-10}
        class Recut:
            land=Ground();overlap=.5;boundary_tolerance=2e-5
            def clip(self,p):return [p[0]+(p-p[0])*.9]
        p=np.array([[0,0,0],[2,0,0],[0,2,0.]])
        with self.assertRaisesRegex(ValueError,'not repeat-stable'):_stable_horizontal_water_parts([p],p,Recut())

    def test_unmerged_water_fallback_keeps_canonical_tile_partition(self):
        from canonical_face_clip import CanonicalClipper
        from terrain_visual_cull import _area
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':-10}
        q=np.array([[0,0,0],[64,0,0],[64,64,0],[0,64,0.]])
        clip=CanonicalClipper(Ground(),.5,boundary_tolerance=2e-5)
        parts=clip.clip(q,merge=False)
        self.assertEqual(len(parts),8);self.assertAlmostEqual(sum(_area(p) for p in parts),4096)
        for p in parts:self.assertTrue(np.ptp(p[:,0])<=32 and np.ptp(p[:,1])<=32)


    def test_float32_water_snap_preserves_grid_and_diagonal_seams(self):
        from canonical_world_cull import _quantize_horizontal_water
        from canonical_face_clip import CanonicalClipper
        threshold=1100.00008
        source=np.array([[1000,1000,0],[1200,1000,0],[1200,1200,0],[1000,1200,0.]])
        for axis,point in ((1,[1088,threshold,0]),(0,[threshold,threshold-32,0])):
            class Ground:
                origin=np.zeros(3)
                def sample(self,x,y):return {'height':.5+64*((x,y)[axis]-threshold)}
            clip=CanonicalClipper(Ground(),.5,boundary_tolerance=2e-5)
            triangle=np.array([point,[1040,1024,0],[1024,1040,0.]])
            fixed,steps=_quantize_horizontal_water(triangle,source,clip)
            self.assertGreater(steps,0)
            if axis==1:self.assertEqual(fixed[0,0],1088)
            else:self.assertEqual(fixed[0,0]-fixed[0,1],32)
            self.assertGreaterEqual(.5-clip.land.sample(*fixed[0,:2])['height'],-2e-5)
            again,_=_quantize_horizontal_water(fixed,source,clip)
            np.testing.assert_array_equal(again,fixed)

    def test_water_stability_loop_enters_atomic_fallback_branch(self):
        from canonical_world_cull import _stable_horizontal_water_parts
        from canonical_face_clip import CanonicalClipper
        class Ground:
            origin=np.zeros(3)
            def sample(self,x,y):return {'height':-10}
        class Recut(CanonicalClipper):
            def __init__(self):
                super().__init__(Ground(),.5,boundary_tolerance=2e-5)
                self.calls=0;self.atomic_calls=0
            def clip(self,p,*,merge=True):
                if not merge:
                    self.atomic_calls+=1
                    return super().clip(p,merge=False)
                self.calls+=1
                return [p[0]+(p-p[0])*.9] if self.calls<=9 else [p]
        q=np.array([[0,0,0],[64,0,0],[64,64,0],[0,64,0.]])
        clip=Recut();parts,_,recuts,depth=_stable_horizontal_water_parts([q],q,clip)
        self.assertEqual(clip.atomic_calls,1)
        self.assertEqual(recuts,9);self.assertEqual(depth,9)
        self.assertTrue(parts)
        self.assertTrue(all(np.ptp(p[:,0])<=32 and np.ptp(p[:,1])<=32 for p in parts))

if __name__=='__main__':unittest.main()
