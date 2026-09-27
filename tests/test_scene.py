import hashlib
import io
import struct
import unittest
from mwad.scene import pack_geometry,unpack_geometry,distance_to_bounds,visible_refs,resident_set,read_asset
from mwad.audit import cell_data

class SceneTests(unittest.TestCase):
    def test_geometry_roundtrip_and_bad_extents(self):
        vertices=[(0,0,0,0,0,255,255,255,255),(1,0,0,1,0,64,64,64,255),(0,1,0,0,1,127,127,127,128)]
        data=pack_geometry(vertices,[(0,1,2,0)],1)
        v,f,n=unpack_geometry(data)
        self.assertEqual(v,vertices);self.assertEqual(f,[(0,1,2,0)]);self.assertEqual(n,1)
        for bad in (data[:-1],b'bad!'+data[4:],data+b'\0',data[:-2]+b'\0\1'):
            with self.assertRaises(ValueError):unpack_geometry(bad)
        with self.assertRaises(ValueError):pack_geometry(vertices,[(0,1,3,0)],1)
        with self.assertRaises(ValueError):pack_geometry([(float('nan'),*vertices[0][1:]),*vertices[1:]],[(0,1,2,0)],1)
        record={'offset':512,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        self.assertEqual(read_asset(io.BytesIO(bytes(512)+data),record),data)
        with self.assertRaises(ValueError):read_asset(io.BytesIO(bytes(512)+data[:-1]),record)

    def test_bounds_culling_keeps_crossing_geometry_and_shared_assets_once(self):
        ref={'model_index':0,'bounds':[[-100,-10,-10],[100,10,10]]}
        index={'references':[ref,dict(ref)],'models':[{'bytes':100,'textures':[0],'triangles':2}], 'textures':[{'bytes':64}]}
        self.assertEqual(len(visible_refs(index,[105,0,0],6)),2)
        self.assertEqual(len(visible_refs(index,[107,0,0],6)),0)
        r=resident_set(index,index['references']);self.assertEqual(r['geometry_bytes'],100);self.assertEqual(r['texture_bytes'],64);self.assertEqual(r['placed_triangles'],4)
        self.assertEqual(distance_to_bounds([0,0,0],ref['bounds']),0)

    def test_door_destination_is_separate_from_exterior_transform(self):
        subs=[('NAME',b'fictional\0'),('DATA',struct.pack('<Iii',0,0,0)),('FRMR',struct.pack('<I',9)),('NAME',b'door\0'),('DODT',struct.pack('<6f',1,2,3,0,0,0)),('DNAM',b'Example interior\0'),('DATA',struct.pack('<6f',4,5,6,0,0,0))]
        r=cell_data(subs)['refs'][0]
        self.assertEqual(r['position'],[4,5,6]);self.assertEqual(r['destination']['position'],[1,2,3]);self.assertEqual(r['destination_cell'],'Example interior')
