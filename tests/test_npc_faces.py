"""Synthetic speech and sex-specific appearance/animation fixtures."""
import struct,sys,tempfile,unittest,wave
from pathlib import Path
import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'tools')]
from mwad.npc import outfit
from npc_faces import ActorSkeleton,actor_samples,envelope

class FacePipeline(unittest.TestCase):
    def test_speech_silence_tail_and_exact_sample_count(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'test.wav'
            with wave.open(str(p),'wb') as w:
                w.setnchannels(1);w.setsampwidth(1);w.setframerate(11025)
                w.writeframes(bytes([128])*441+bytes([230])*441+bytes([128])*442)
            b=envelope(p);magic,rate,count,samples=struct.unpack_from('<4sHHI',b)
            self.assertEqual((magic,rate,count,samples),(b'AWL1',25,4,1324))
            self.assertEqual(list(b[12:]),[0,3,0,0])
    def test_female_idle_falls_back_but_walk_uses_authored_override(self):
        class Skeleton:
            N=object()
            events={'walkforward: loop start':20.,'walkforward: loop stop':21.}
            def idle_times(self,n):return np.arange(n)/4,.25
            def pose(self,t):return ('base',t)
        class Female(Skeleton):
            events={'walkforward: loop start':9.,'walkforward: loop stop':10.}
            def pose(self,t):return ('female',t)
        s=ActorSkeleton(Skeleton(),Female());times,faces,idle,walk=actor_samples(s)
        self.assertEqual(len(times),21);self.assertEqual(s.pose(times[0]),('base',0))
        self.assertEqual(s.pose(times[13]),('female',9));self.assertEqual(walk,.125)
        self.assertEqual(faces[8:13],[(0.,False),(1/3,False),(2/3,False),(1.,False),(0,True)])
    def test_female_body_equipment_fallback_and_proportions(self):
        def body(female,kind=0):return [('BYDT',bytes([2,0,female,kind])),('FNAM',b'human'),('MODL',b'fixture.nif')]
        npc=[('FLAG',struct.pack('<I',1)),('RNAM',b'human'),('NPDT',struct.pack('<h',1)),('NPCO',struct.pack('<i32s',1,b'shirt'))]
        cloth=[('CTDT',struct.pack('<i',0)),('INDX',b'\x02'),('BNAM',b'male shirt'),('CNAM',b'female shirt')]
        k={'NPC_':{'actor':npc},'RACE':{'human':[('RADT',struct.pack('<4fI',1.1,.9,1.3,1.,0))]},
           'BODY':{'male neck':body(0),'female neck':body(1),'male shirt':body(0,1),'female shirt':body(1,1)},
           'LEVI':{},'ARMO':{},'CLOT':{'shirt':cloth}}
        a=outfit(k,'actor');self.assertTrue(a['female']);self.assertAlmostEqual(a['height'],.9);self.assertEqual(a['weight'],1.)
        self.assertEqual(a['parts'][0]['id'],'female shirt')
        cloth[-1]=('CNAM',b'');self.assertEqual(outfit(k,'actor')['parts'][0]['id'],'male shirt')
        npc.pop();self.assertEqual(outfit(k,'actor')['parts'][0]['id'],'female neck')
