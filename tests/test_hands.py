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
