import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compact_bsp import entities
from player_hull import pack_lumps,lumps
from replace_bsp_world import replace_world,rows,texture_blobs,FORMATS

PALETTE=bytes(range(256))*3


def fixture(inline=False,world_x=0):
    data=[bytearray() for _ in range(15)]
    def put(index,values):data[index]=bytearray().join(struct.pack(FORMATS[index],*row) for row in values)
    data[0]=bytearray(b'{\n"classname" "worldspawn"\n"aw_hull" "tes3-humanoid-v1"\n}\n')
    if inline:data[0]+=b'{\n"classname" "func_wall"\n"model" "*1"\n"origin" "123 456 0"\n}\n{\n"classname" "aw_static"\n"model" "progs/tree.spr"\n}\n'
    data[0]+=b'\0'
    put(1,[[1,0,0,world_x,0]]+([[0,1,0,7,1]] if inline else []))
    data[2]=bytearray(struct.pack('<ii',1,8)+b'terrain\0'+bytes(8)+struct.pack('<II4I',16,16,40,296,360,376)+bytes([42])*340)
    vertices=[[world_x,0,0],[world_x,16,0],[world_x,0,16]]
    if inline:vertices.extend([[0,7,0],[16,7,0],[0,7,16]])
    put(3,vertices);data[4]=bytearray(b'\1')
    count=2 if inline else 1
    put(5,[[i,-2,-1,-16,-16,-16,32,32,32,i,1] for i in range(count)])
    put(6,[[0,1,0,2,0,0,1,3,0,0]])
    put(7,[[i,0,3*i,3,0,0,255,255,255,4*i] for i in range(count)])
    data[8]=bytearray(bytes(range(4*count)))
    put(9,[[i,65535,65534] for i in range(count)])
    put(10,[[-2,-1,-16,-16,-16,32,32,32,0,0,0,0,0,0],[-1,0,-16,-16,-16,32,32,32,0,1,0,0,0,0]])
    put(11,[[0]])
    edges=[[0,0],[0,1],[1,2],[2,0]]
    if inline:edges.extend([[3,4],[4,5],[5,3]])
    put(12,edges);put(13,[[i] for i in range(1,3*count+1)])
    put(14,[[-16,-16,-16,32,32,32,0,0,0,i,i,-1,-1,1,i,1] for i in range(count)])
    return pack_lumps(data)


def face_semantics(raw,model):
    data=lumps(raw);r=rows(data);textures=texture_blobs(data[2]);result=[]
    first,count=r[14][model][14:16]
    for f in r[7][first:first+count]:
        points=[]
        for (se,) in r[13][f[2]:f[2]+f[3]]:
            edge=r[12][abs(se)];points.append(r[3][edge[0 if se>=0 else 1]])
        ti=r[6][f[4]]
        result.append((points,r[1][f[0]],f[1],ti[:8],textures[ti[8]],bytes(data[8][f[9]:f[9]+4])))
    return result


class ReplaceBspWorldTests(unittest.TestCase):
    def test_replacement_owns_world_tree_and_inline_semantics_survive(self):
        source=fixture(inline=True);base=fixture(world_x=1024)
        result,report=replace_world(source,base,PALETTE,PALETTE)
        a,b,c=lumps(source),lumps(base),lumps(result);r=rows(c)
        self.assertEqual(c[4],b[4]);self.assertEqual(c[10],b[10]);self.assertEqual(c[11],b[11])
        self.assertEqual(r[14][0],rows(b)[14][0])
        self.assertEqual(r[5][0],rows(b)[5][0])
        self.assertTrue(all(child<0 for child in r[5][0][1:3]))
        self.assertEqual(face_semantics(result,1),face_semantics(source,1))
        self.assertEqual(face_semantics(result,0),face_semantics(base,0))
        self.assertEqual(entities(c[0]),entities(a[0]))
        self.assertEqual(report['inline_models'],1)
        self.assertEqual(len(texture_blobs(c[2])),1)
        self.assertEqual(len(r[5]),2) # new world plus independent inline point tree

    def test_palette_hull_and_base_root_contracts_are_required(self):
        source=fixture(True);base=fixture()
        with self.assertRaisesRegex(ValueError,'palette'):
            replace_world(source,base,PALETTE,bytes(768))
        d=lumps(base);d[0]=d[0].replace(b'tes3-humanoid-v1',b'other-profile')
        with self.assertRaisesRegex(ValueError,'standing-hull'):
            replace_world(source,pack_lumps(d),PALETTE,PALETTE)
        d=lumps(base);struct.pack_into('<i',d[14],36,-1)
        with self.assertRaisesRegex(ValueError,'rooted at node zero'):
            replace_world(source,pack_lumps(d),PALETTE,PALETTE)

    def test_shared_world_leaf_is_rejected_before_parent_links_are_corrupted(self):
        source=fixture(True);base=lumps(fixture())
        struct.pack_into('<h',base[5],6,-2)
        with self.assertRaisesRegex(ValueError,'shared non-solid'):
            replace_world(source,pack_lumps(base),PALETTE,PALETTE)

    def test_missing_terminal_contents_is_rejected(self):
        source=lumps(fixture(True));base=fixture()
        leaf=list(struct.unpack_from(FORMATS[10],source[10],28));leaf[0]=-3
        struct.pack_into(FORMATS[10],source[10],28,*leaf)
        with self.assertRaisesRegex(ValueError,'terminal contents'):
            replace_world(pack_lumps(source),base,PALETTE,PALETTE)

    def test_same_texture_name_with_different_pixels_is_rejected(self):
        source=fixture(True);base=lumps(fixture());base[2][-1]^=1
        with self.assertRaisesRegex(ValueError,'differing pixels'):
            replace_world(source,pack_lumps(base),PALETTE,PALETTE)


if __name__=='__main__':unittest.main()
