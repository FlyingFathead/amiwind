import sys, struct, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_walkability import Scene, scan
from player_hull import pack_lumps

def scene(boxes):
    data=[bytearray() for _ in range(15)];entities=['{"classname" "worldspawn" "aw_hull" "tes3-humanoid-v1"}']
    # An empty world hull; collision is in placed brush models.
    data[14]+=struct.pack('<9f7i',*([0.]*9),-1,-1,-1,-1,0,0,0)
    for i,(low,high,origin,angles) in enumerate(boxes,1):
        root=len(data[9])//8
        for axis in range(3):
            for sign,bound in ((1,high[axis]),(-1,-low[axis])):
                normal=[0.,0.,0.];normal[axis]=sign;pi=len(data[1])//20
                data[1]+=struct.pack('<4fi',*normal,bound,3)
                node=len(data[9])//8
                data[9]+=struct.pack('<ihh',pi,-1,node+1 if node-root<5 else -2)
        data[14]+=struct.pack('<9f7i',*([0.]*9),-1,root,-1,-1,0,0,0)
        entities.append('{"classname" "func_wall" "model" "*%d" "aw_ref" "%d" "origin" "%s" "angles" "%s"}'%(i,100+i,origin,angles))
    data[0]=bytearray(('\n'.join(entities)+'\0').encode())
    return Scene(pack_lumps(data))

class WalkabilityAuditTests(unittest.TestCase):
    def test_shared_collision_suffix_is_not_reported_as_a_cycle(self):
        s=Scene.__new__(Scene)
        s.planes=[(0.,0.,1.,i+.5) for i in range(40)]
        s.nodes=[(i,i+1 if i<39 else -1,i+1 if i<39 else -1) for i in range(40)]
        s.brushes=[(0,(0.,0.,0.),((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),'fixture')]
        self.assertIsNone(s.trace((0,0,50),(0,0,-10)))

    def test_floor_hole_step_and_reachable_fall(self):
        s=scene([((-50,-50,-20),(0,50,10),'0 0 0','0 0 0'),((12,-50,-20),(50,50,14),'0 0 0','0 0 0')])
        self.assertEqual(s.floor((-4,0,20),20)['status'],'supported')
        self.assertEqual(s.floor((4,0,20),20)['status'],'unsupported')
        self.assertEqual(s.floor((-4,0,8),20)['status'],'blocked')
        report=scan(s,(-8,-4,20,4),20,4,20,(-8,0))
        self.assertGreater(len(report['possible_fall_samples']),0)
        self.assertLess(report['reachable_count'],report['summary']['supported'])
        closed=scene([((-50,-50,-20),(50,50,10),'0 0 0','0 0 0')])
        report=scan(closed,(-8,-4,20,4),20,4,20,(-8,0))
        self.assertEqual(report['possible_fall_samples'],[])
        self.assertEqual(report['reachable_count'],24)
    def test_rotated_wall_and_bad_tree(self):
        s=scene([((-1,-20,-20),(1,20,20),'10 5 0','0 90 0')])
        hit=s.trace((10,0,0),(10,10,0))
        self.assertAlmostEqual(hit['fraction'],.4)
        self.assertAlmostEqual(hit['normal'][1],-1)
        self.assertEqual(hit['reference'],'101')
        s.nodes[0]=(s.nodes[0][0],0,0)
        with self.assertRaisesRegex(ValueError,'Cyclic'):s.trace((10,0,0),(10,10,0))
