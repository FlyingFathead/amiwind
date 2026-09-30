"""Retained faces/hulls and signed edges survive model/data remapping."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compact_bsp import compact,entities
from player_hull import pack_lumps,lumps
from prepare_seyda_regions import regions
from balmora_regions import owner


def fixture():
    d=[bytearray() for _ in range(15)]
    d[0]=bytearray(b'{"classname" "worldspawn"}\n{"classname" "func_wall" "model" "*2" "aw_ref" "42"}\n\0')
    d[2]=bytearray(struct.pack('<4i',3,16,56,96)+b'A'*40+b'B'*40+b'C'*40)
    d[4]=bytearray(b'original visibility');d[8]=bytearray(b'original lighting')
    d[12]=bytearray(struct.pack('<HH',0,0))
    for i in range(3):
        d[1]+=struct.pack('<4fi',1,0,0,i,0)
        for v in ((i,0,0),(i,1,0),(i,0,1)):d[3]+=struct.pack('<3f',*v)
        for a,b in ((0,1),(1,2),(0,2)):d[12]+=struct.pack('<HH',i*3+a,i*3+b)
        d[13]+=struct.pack('<3i',i*3+1,i*3+2,-(i*3+3))
        d[6]+=struct.pack('<8f2i',1,0,0,0,0,1,0,0,i,0)
        d[7]+=struct.pack('<Hhihh4Bi',i,0,i*3,3,i,0,255,255,255,-1)
        d[5]+=struct.pack('<i2h6h2H',i,-1,-2,0,0,0,10,10,10,i,1)
        d[9]+=struct.pack('<iHH',i,65535,65534)
        d[14]+=struct.pack('<9f7i',0,0,0,10,10,10,0,0,0,i,i,i,i,1,i,1)
    d[10]=bytearray(struct.pack('<ii6h2H4B',-2,-1,0,0,0,10,10,10,0,0,0,0,0,0)+struct.pack('<ii6h2H4B',-1,0,0,0,0,10,10,10,0,1,0,0,0,0))
    d[11]=bytearray(struct.pack('<H',0))
    return pack_lumps(d)


class CompactBspTests(unittest.TestCase):
    def test_unmarked_world_faces_removed_without_removing_collision(self):
        source=lumps(fixture())
        source[11]=bytearray()
        struct.pack_into('<H',source[10],28+22,0)
        result,report=compact(pack_lumps(source),prune_world=True)
        result=lumps(result)
        models=list(struct.iter_unpack('<9f7i',result[14]))
        self.assertEqual(models[0][15],0)
        self.assertEqual(models[1][15],1)
        self.assertEqual(len(result[7]),20)
        self.assertEqual(result[4],source[4])
        planes=list(struct.iter_unpack('<4fi',result[1]))
        clips=list(struct.iter_unpack('<iHH',result[9]))
        self.assertEqual(planes[clips[models[0][10]][0]],(1.,0.,0.,0.,0))
        self.assertEqual(clips[models[0][10]][1:],(65535,65534))
        self.assertEqual(report['world_collision'],'unchanged')

    def test_retained_surface_vertices_and_collision_equations(self):
        raw=fixture();out,report=compact(raw);a,b=lumps(raw),lumps(out)
        self.assertEqual(report['retained_models'],[0,2]);self.assertLess(len(out),len(raw))
        self.assertEqual(entities(b[0])[1]['model'],'*1');self.assertEqual(entities(b[0])[1]['aw_ref'],'42')
        self.assertEqual(a[4],b[4]);self.assertEqual(a[8],b[8]);self.assertEqual(a[10],b[10])
        def resolved(d,model):
            models=list(struct.iter_unpack('<9f7i',d[14]));faces=list(struct.iter_unpack('<Hhihh4Bi',d[7]))
            planes=list(struct.iter_unpack('<4fi',d[1]));nodes=list(struct.iter_unpack('<iHH',d[9]))
            verts=list(struct.iter_unpack('<3f',d[3]));edges=list(struct.iter_unpack('<HH',d[12]));se=[v[0] for v in struct.iter_unpack('<i',d[13])]
            m=models[model];f=faces[m[14]];points=[verts[edges[abs(e)][e<0]] for e in se[f[2]:f[2]+f[3]]]
            node=nodes[m[10]]
            return points,planes[node[0]],node[1:]
        self.assertEqual(resolved(a,0),resolved(b,0));self.assertEqual(resolved(a,2),resolved(b,1))
        self.assertEqual(struct.unpack_from('<i',b[2])[0],2)
        self.assertNotIn(b'B'*40,b[2]);self.assertIn(b'C'*40,b[2])
        self.assertEqual(raw,fixture())

    def test_region_overlap_and_first_dock_route_share_core(self):
        rs=regions();self.assertLessEqual(len(rs),64)
        self.assertEqual(owner((695,-486),rs),owner((330,-200),rs))
        for r in rs:
            for axis in range(2):
                self.assertLessEqual(r['coverage'][0][axis],r['core'][0][axis])
                self.assertGreaterEqual(r['coverage'][1][axis],r['core'][1][axis])
        self.assertIsNotNone(owner((0,0),rs))
        town=owner((0,0),rs)
        for point in [(-300,200),(700,-486),(100,400),(-30,473)]:
            self.assertEqual(owner(point,rs),town)
        self.assertNotEqual(owner((-30,475),rs),town)
