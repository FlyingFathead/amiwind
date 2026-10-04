# SPDX-License-Identifier: GPL-3.0-only
import unittest,struct
import numpy as np
from player_hull import lumps,pack_lumps
from replace_bsp_world import rows
from compact_bsp import entities
from cull_bsp_hidden import cull_bsp


def fixture(second_without_shell=False,moving=False):
    d=[bytearray() for _ in range(15)]
    d[0]=bytearray(('{"classname" "worldspawn" "aw_render_pool" "*3"}\n'
       '{"classname" "func_wall" "model" "*1" "aw_ref" "one" "aw_render_ranges" "0:1"}\n'
       '{"classname" "'+('func_door' if moving else 'func_wall')+'" "model" "*2" "aw_ref" "two" "aw_render_ranges" "0:1"}\0').encode())
    blob=struct.pack('<16s6I',b'opaque',16,16,40,296,360,376)+bytes(340)
    d[2]=bytearray(struct.pack('<ii',1,8)+blob)
    d[4]=bytearray(b'unchanged PVS');d[6]=bytearray(struct.pack('<8f2i',1,0,0,0,0,1,0,0,0,0))
    polygons=[[[5,0,0],[5,2,0],[5,0,2]],
      [[0,0,0],[0,0,2],[0,2,2],[0,2,0]],
      [[2,0,0],[2,2,0],[2,2,2],[2,0,2]],
      [[0,0,0],[2,0,0],[2,0,2],[0,0,2]],
      [[0,2,0],[0,2,2],[2,2,2],[2,2,0]],
      [[0,0,0],[0,2,0],[2,2,0],[2,0,0]],
      [[0,0,2],[2,0,2],[2,2,2],[0,2,2]],
      [[.5,.5,1],[1.5,.5,1],[.5,1.5,1]]]
    verts={};vids=[];d[12]=bytearray(struct.pack('<HH',0,0));edge=1;se=0
    for fid,polygon in enumerate(polygons):
        ids=[]
        for p in polygon:
            key=tuple(p)
            if key not in verts:verts[key]=len(verts);d[3]+=struct.pack('<3f',*p)
            ids.append(verts[key])
        q=np.array(polygon,dtype=float);normal=np.cross(q[1]-q[0],q[2]-q[0]);normal/=np.linalg.norm(normal)
        d[1]+=struct.pack('<4fi',*normal,float(normal@q[0]),3)
        d[7]+=struct.pack('<Hhihh4Bi',fid,0,se,len(ids),0,255,255,255,255,-1)
        for a,b in zip(ids,ids[1:]+ids[:1]):d[12]+=struct.pack('<HH',a,b);d[13]+=struct.pack('<i',edge);edge+=1;se+=1
    d[10]=bytearray(struct.pack('<ii6h2H4B',-1,-1,0,0,0,5,5,5,0,1,0,0,0,0));d[11]=bytearray(struct.pack('<H',0))
    for first,count in ((0,1),(1,6),(0,0) if second_without_shell else (1,6),(7,1)):
        d[14]+=struct.pack('<9f7i',0,0,0,5,5,5,0,0,0,-1,-1,-1,-1,1,first,count)
    return pack_lumps(d)

class HiddenBspTests(unittest.TestCase):
    def test_serialized_pool_face_removed_with_bindings_and_collision_intact(self):
        raw=fixture();out,receipt=cull_bsp(raw)
        self.assertEqual(receipt['removed_face_ids'],[7]);self.assertEqual(receipt['stored_faces_after'],7)
        self.assertEqual(receipt['collision_checks'],16);self.assertEqual(lumps(raw)[4],lumps(out)[4])
        es=entities(lumps(out)[0]);self.assertTrue(all('aw_render_ranges' not in e for e in es))
        r=rows(lumps(out));pool=int(es[0]['aw_render_pool'][1:]);self.assertEqual(r[14][pool][15],0)
    def test_partial_pool_range_remaps_visible_survivor(self):
        d=lumps(fixture());d[7]+=d[7][:20]
        struct.pack_into('<i',d[14],3*64+60,2)
        d[0]=bytearray(bytes(d[0]).replace(b'0:1',b'0:2'))
        out,receipt=cull_bsp(pack_lumps(d));self.assertEqual(receipt['removed_face_ids'],[7])
        es=entities(lumps(out)[0]);self.assertEqual(es[1]['aw_render_ranges'],'0:1')
        r=rows(lumps(out));pool=int(es[0]['aw_render_pool'][1:]);self.assertEqual(r[14][pool][15],1)
        f=r[7][r[14][pool][14]];points=[r[3][r[12][abs(r[13][i][0])][0 if r[13][i][0]>=0 else 1]] for i in range(f[2],f[2]+f[3])]
        self.assertEqual(points,[[5.,0.,0.],[5.,2.,0.],[5.,0.,2.]])
    def test_shared_face_retained_if_any_user_has_open_geometry(self):
        raw=fixture(second_without_shell=True);out,receipt=cull_bsp(raw)
        self.assertEqual(out,raw);self.assertEqual(receipt['removed_face_ids'],[])
    def test_moving_brush_and_its_pool_binding_are_protected(self):
        raw=fixture(moving=True);out,receipt=cull_bsp(raw)
        self.assertEqual(out,raw);self.assertEqual(receipt['removed_face_ids'],[])
    def test_disabled_and_interior_are_byte_exact(self):
        raw=fixture()
        for kwargs in ({'enabled':False},{'scene_kind':'interior'}):
            out,receipt=cull_bsp(raw,**kwargs);self.assertIs(out,raw);self.assertTrue(receipt['byte_identical'])
    def test_invalid_flag_rejected(self):
        with self.assertRaises(ValueError):cull_bsp(fixture(),enabled='true')
if __name__=='__main__':unittest.main()
