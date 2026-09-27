"""Synthetic actor/alias fixtures; no original game assets required."""
import struct
import sys
import unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'tools')]
from mwad.npc import greeting_fixture,first,behavior_record,greeting_settings
from player_hull import MINS,MAXS,FACTORS,lumps,pack_lumps,graft_hull

class ActorRecords(unittest.TestCase):
    def test_wander_settings_and_package_order(self):
        fields=[('AIDT',struct.pack('<HBBB3xI',513,40,30,20,0x102)),
                ('AI_W',struct.pack('<hh10B',512,5,9,60,20,15,5,0,0,0,0,1)),
                ('AI_T',b'opaque travel fixture'),('CNDT',b'interior')]
        result=behavior_record(fields)
        self.assertEqual(result['hello'],513)  # Hello is not a byte.
        self.assertEqual(result['services'],0x102)
        self.assertEqual([p['tag'] for p in result['packages']],['AI_W','AI_T','CNDT'])
        wander=result['packages'][0]
        self.assertEqual((wander['distance'],wander['scaled_distance'],wander['duration_hours']), (512,128,5))
        self.assertEqual(wander['idle_weights'],[60,20,15,5,0,0,0,0])
        self.assertTrue(wander['repeat']);self.assertFalse(result['runtime_wandering'])
        self.assertEqual(bytes.fromhex(result['packages'][1]['raw_hex']),b'opaque travel fixture')
        with self.assertRaises(ValueError):behavior_record(fields+[('AI_W',b'bad')])
    def test_greeting_units_and_invalid_reset(self):
        gmst={'igreetdistancemultiplier':[('INTV',struct.pack('<i',6))],
              'fgreetdistancereset':[('FLTV',struct.pack('<f',512))],
              'igreetduration':[('INTV',struct.pack('<i',4))]}
        result=greeting_settings({'GMST':gmst},{'hello':30})
        self.assertEqual((result['distance'],result['reset_distance'],result['duration']),(45,128,4))
        with self.assertRaises(ValueError):greeting_settings({'GMST':gmst},{'hello':200})
    def test_greeting_rejects_context_and_preserves_order(self):
        def info(id,disp=50,gender=0):return [('INAM',id.encode()),('DATA',struct.pack('<iibbbb',1,disp,-1,gender,-1,0)),('RNAM',b'test race'),('SNAM',b'fixture.wav'),('NAME',id.encode())]
        ap={'id':'test actor','race':'test race','class':'test class','female':False}
        rows=[info('quest')+[('SCVR',b'condition')],info('high',90),info('female',50,1),info('first'),info('second')]
        got=greeting_fixture({'hello':rows},ap)
        self.assertEqual(got['info'],'first');self.assertIn('not full',got['mode'])
        with self.assertRaises(ValueError):greeting_fixture({'hello':[info('quest')+[('BNAM',b'script')]]},ap)
    def test_repeated_record_fields_not_flattened(self):
        self.assertEqual(first([('BNAM',b'first'),('BNAM',b'second')],'BNAM'),b'first')

class HullTransform(unittest.TestCase):
    def test_six_limits_and_visual_lumps_preserved(self):
        # Six half spaces of a synthetic expanded unit room; no original map.
        target=[bytearray() for _ in range(15)];target[0]=bytearray(b'{"classname" "worldspawn"}\0');target[14]=bytearray(64)
        target[3]=bytearray(b'visible geometry sentinel')
        source=[bytearray(x) for x in target]
        planes=[(1,0,0,16),(0,1,0,16),(0,0,1,24),(0,0,-1,32)]
        source[1]=bytearray(b''.join(struct.pack('<4fi',*p,3) for p in planes))
        source[9]=bytearray(b''.join(struct.pack('<ihh',i,i+1 if i<3 else -1,-2) for i in range(4)))
        output=lumps(graft_hull(pack_lumps(target),pack_lumps(source)))
        result=list(struct.iter_unpack('<4fi',output[1]))
        for p,d in zip(result,[7.32,7.12,16.625,16.625]):self.assertAlmostEqual(p[3],d,places=5)
        for i in range(15):
            if i not in (0,1,9,14):self.assertEqual(output[i],target[i])
        self.assertIn(b'tes3-humanoid-v1',output[0])
    def test_bad_bsp_rejected(self):
        with self.assertRaises(ValueError):lumps(bytes(124))

class AliasFrames(unittest.TestCase):
    def test_two_frames_share_quantization_and_topology(self):
        try:
            import numpy as np
            from PIL import Image
            from npc_geometry import animated_mdl,blend_keys
        except ImportError:self.skipTest('Install optional NPC conversion dependencies')
        frames=np.array([[[0,0,0],[1,0,0],[0,1,0]],[[0,0,2],[1,0,2],[0,1,2]]],float)
        skin=Image.new('P',(16,16));faces=np.array([[0,2,1]]);uv=np.array([[0,0],[15,0],[0,15]])
        raw=animated_mdl(frames,faces,uv,skin);head=struct.unpack_from('<4si3f3ff3f8if',raw)
        self.assertEqual(head[0:2],(b'IDPO',6));self.assertEqual(head[15:18],(3,1,2))
        self.assertEqual(len(raw),84+4+256+36+16+2*(28+12))
        q=blend_keys([0,1],np.array([[1.,0,0,0],[-1.,0,0,0]]),.5,True)
        self.assertAlmostEqual(abs(q[0]),1)
        with self.assertRaises(ValueError):animated_mdl(frames,np.array([[0,1,3]]),uv,skin)
