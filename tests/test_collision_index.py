"""A spatial index must preserve empty gaps and solid pieces in both hulls."""
from pathlib import Path
import random
import struct
import tempfile
import unittest
from collision_index import index_model_collision
from player_hull import MINS, MAXS, lumps, pack_lumps


class CollisionIndex(unittest.TestCase):
    def test_classification_and_rejection_cost_match_original_volumes(self):
        data = [bytearray() for _ in range(15)]
        data[0] = bytearray(b'{\n"aw_ref" "123"\n"model" "*1"\n}\n\0')
        data[14] = bytearray(struct.pack('<9f7i', *([0.]*9), -1,-1,-1,-1,0,0,0)
                             + struct.pack('<9f7i', *([0.]*9), 0,0,0,0,0,0,0))
        for part in range(64):
            low = [part*30, -4, -6];high = [part*30+8, 4, 6]
            for section, expanded in ((5,False),(9,True)):
                root = part*6;empty = -2 if section==5 else -1
                solid = -1 if section==5 else -2
                outside = root+6 if part<63 else empty
                for j in range(6):
                    axis = j//2;sign = 1 if j%2==0 else -1
                    d = high[axis]-(MINS[axis] if expanded else 0) if sign>0 else -low[axis]+(MAXS[axis] if expanded else 0)
                    normal = [0.,0.,0.];normal[axis] = sign
                    pi = len(data[1])//20;data[1] += struct.pack('<4fi',*normal,d,3)
                    inside = root+j+1 if j<5 else solid
                    node = struct.pack('<iHH',pi,outside & 65535,inside & 65535)
                    if section==5:node += struct.pack('<6h2H',*low,*high,0,0)
                    data[section] += node
        before = pack_lumps(data)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'test.bsp';path.write_bytes(before)
            report = index_model_collision(path,123)
            self.assertEqual(report['pieces'],64)
            after = path.read_bytes()
        def tree(raw,section):
            ls=lumps(raw);stride=24 if section==5 else 8;threshold=32768 if section==5 else 65520
            ns=[]
            for offset in range(0,len(ls[section]),stride):
                pi,a,b=struct.unpack_from('<iHH',ls[section],offset)
                ns.append((pi,a-65536 if a>=threshold else a,b-65536 if b>=threshold else b))
            return list(struct.iter_unpack('<4fi',ls[1])),ns,struct.unpack_from('<i',ls[14],64+(36 if section==5 else 40))[0]
        def contents(t,p):
            planes,nodes,n=t;tests=0
            while n>=0:
                self.assertGreaterEqual(n,t[2])
                pi,front,back=nodes[n];x,y,z,d,_=planes[pi]
                n=front if x*p[0]+y*p[1]+z*p[2]>=d else back;tests+=1
            return n,tests
        random.seed(901)
        points=[[random.uniform(-30,1950),random.uniform(-30,30),random.uniform(-35,35)] for _ in range(1000)]
        points += [[part*30+4,0,0] for part in range(64)]
        for section in (5,9):
            old,new=tree(before,section),tree(after,section);cost_old=cost_new=0
            for point in points:
                a,ac=contents(old,point);b,bc=contents(new,point)
                self.assertEqual(a,b);cost_old+=ac;cost_new+=bc
            self.assertLess(cost_new,cost_old*.5)
