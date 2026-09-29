"""The smaller exterior preserves original hulls and bounds the intro patch."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from player_hull import pack_lumps,lumps
from prepare_intro_docks import derive

class IntroDocksTests(unittest.TestCase):
    def test_boundary_roots_and_original_input(self):
        data=[bytearray() for _ in range(15)]
        data[0]=bytearray(b'{\n"classname" "worldspawn"\n}\n{\n"classname" "aw_npc"\n"origin" "9999 9999 0"\n}\n\0')
        data[1]=bytearray(struct.pack('<4fi',1,0,0,0,0))
        data[9]=bytearray(struct.pack('<iHH',0,65535,65535))
        data[10]=bytearray(struct.pack('<ii6h2H4B',-1,-1,0,0,0,0,0,0,0,0,0,0,0,0))
        model=struct.pack('<9f7i',-10,-10,-10,10,10,10,0,0,0,0,0,0,0,0,0,0)
        data[14]=bytearray(model+model)
        raw=pack_lumps(data);before=bytes(raw)
        result,report=derive(raw,(-100,-100,100,100));got=lumps(result)
        self.assertEqual(raw,before)
        self.assertEqual(report['actors_removed'],1)
        self.assertEqual(struct.unpack_from('<i',got[14],40)[0],0)
        self.assertEqual(struct.unpack_from('<i',got[14],104)[0],4)
        def content(point):
            node=0
            for _ in range(10):
                if node>=65520:return node
                plane,front,back=struct.unpack_from('<iHH',got[9],node*8)
                x,y,z,d,_=struct.unpack_from('<4fi',got[1],plane*20)
                node=front if x*point[0]+y*point[1]+z*point[2]>=d else back
            self.fail('Hull cycle')
        self.assertEqual(content((0,0,0)),65535)
        for p in [(200,0,0),(-200,0,0),(0,200,0),(0,-200,0)]:self.assertEqual(content(p),65534)
