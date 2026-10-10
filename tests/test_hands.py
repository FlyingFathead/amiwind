import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
class Hands(unittest.TestCase):
    def test_clip_boundaries_and_hand_only_bake(self):
        import numpy as np
        from prepare_hands import CLIPS,sample_clips
        from npc_geometry import bake
        events={}
        for i,(_,a,b,n,end) in enumerate(CLIPS):events[a]=i*2;events[b]=i*2+1
        times,clips=sample_clips(events)
        self.assertEqual(len(times),28)
        self.assertEqual(clips['punch']['first'],18)
        self.assertLess(times[7],events['idlehh: stop'])
        self.assertEqual(times[13],events['handtohand: equip stop'])
        events['idlehh: stop']=0
        with self.assertRaises(ValueError):sample_clips(events)
        # No head slot: quota weights must still support float normalization.
        shape={'part':6,'positions':np.array([[[0,0,0],[1,0,0],[0,1,0]]],float),
               'faces':np.array([[0,1,2]]),'uv':np.zeros((3,2)),
               'colours':np.ones((3,4)),'material':0}
        frames,faces,uv,skin=bake([shape],[{'texture_index':None,'diffuse':[1,1,1]}],{},bytes(range(256))*3,budget=64)
        self.assertEqual(frames.shape,(1,3,3));self.assertEqual(len(faces),1)

    def test_weapon_stances_fill_the_same_frame_contract(self):
        # First-person weapon views: each stance samples its own original groups into the
        # same 28 frames (idle 8, draw 6, lower 4, punch 10); the runtime state logic is shared.
        from prepare_hands import CLIPS,STANCES,stance_clips,sample_clips
        self.assertEqual(stance_clips('hh'),CLIPS)
        self.assertEqual(stance_clips('1h')[0][1:3],('idle1h: start','idle1h: stop'))
        self.assertEqual(stance_clips('2w')[3][1:3],('weapontwowide: chop start','weapontwowide: chop large follow stop'))
        for stance in STANCES:
            events={}
            for i,(_,a,b,n,end) in enumerate(stance_clips(stance)):events[a]=i*2;events[b]=i*2+1
            times,clips=sample_clips(events,stance)
            self.assertEqual(len(times),28);self.assertEqual([c['first'] for c in clips.values()],[0,8,14,18])
        with self.assertRaises(ValueError):sample_clips({},'1h')          # groups missing
        with self.assertRaises(ValueError):stance_clips('bow')

    def test_view_tags_place_items_like_the_hand_vertices(self):
        # An item vertex placed by the view tag (item model in its own axes, 0.25 scale) lands where
        # prepare_hands puts a vertex attached to the bone: ((v @ R + t) * 0.25 - camera) @ VIEW_AXES.
        import numpy as np
        import npc_items
        R=npc_items.angle_matrix(25,-70,40);t=np.array([12.,-30.,90.]);camera=np.array([1.,2.,24.])
        class Pose:
            def pose(self,time):
                def bone(name):
                    m=np.eye(4);m[:3,:3]=R;m[3,:3]=t;return m
                return bone
        row=npc_items.view_tags(Pose(),[0],camera,{'weapon':True})[0]
        v=np.array([[3.,-1.,40.],[0.,0.,0.],[-5.,2.,-7.]])
        expected=((v@R+t)*.25-camera)@npc_items.VIEW_AXES
        rebuilt=(v*.25)@npc_items.angle_matrix(*row[3:6])+np.array(row[:3])
        np.testing.assert_allclose(rebuilt,expected,atol=1e-6)
        self.assertEqual(row[6:],[0.0]*6)
