"""Initial-placement gate against small independent BSP/MDL fixtures."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from actor_grounding import fields, initial_state
from check_actor_ground import audit, require
from player_hull import pack_lumps, PROFILE


def alias(bottom=0):
    # Three independent feet vertices, eight declared idle poses, one skin.
    raw=bytearray(struct.pack('<4si3f3ff3f8if',b'IDPO',6,1,1,1,0,0,bottom,4,0,0,0,
                              1,4,4,3,1,8,0,0,1))
    raw+=struct.pack('<i',0)+bytes(16)+bytes(3*12)+struct.pack('<4i',1,0,1,2)
    for i in range(8):
        raw+=struct.pack('<i4B4B16s',0,0,0,0,0,2,2,0,0,b'idle')
        raw+=bytes((0,0,0,0,2,0,0,0,0,2,0,0))
    return raw


def bsp(actor, floor=0):
    chunks=[b'' for _ in range(15)]
    chunks[0]=('{\n"classname" "worldspawn"\n"aw_hull" "'+PROFILE+'"\n}\n'+actor).encode()
    chunks[1]=struct.pack('<4fi',0,0,1,floor,2)
    chunks[5]=struct.pack('<ihh6h2H',0,-1,-2,*([0]*8))
    chunks[9]=struct.pack('<ihh',0,-1,-2)
    chunks[10]=b''.join(struct.pack('<ii6h2H4B',c,-1,*([0]*12)) for c in (-1,-2))
    chunks[14]=struct.pack('<9f7i',*([0]*9),0,0,0,0,2,0,0)
    return pack_lumps(chunks)


def actor(z=.25,identifier='heddvild',mode=0,ref='123'):
    return ('{\n"classname" "aw_npc"\n"aw_ref" "'+ref+'"\n"aw_source_id" "'+identifier+
            '"\n"aw_ground_mode" "'+str(mode)+'"\n"origin" "0 0 '+str(z)+
            '"\n"angles" "0 0 0"\n"model" "progs/test.mdl"\n"netname" "Test"\n}\n')


class GroundGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.id1=Path(self.tmp.name);self.maps=self.id1/'maps';self.maps.mkdir()
        (self.id1/'progs').mkdir();(self.id1/'progs/test.mdl').write_bytes(alias())

    def put(self,text,name='room',floor=0):
        (self.maps/(name+'.bsp')).write_bytes(bsp(text,floor))

    def test_grounded_origin_does_not_hide_floating_rendered_mesh(self):
        self.put(actor());self.assertEqual(audit(self.maps)['status'],'passed')
        (self.id1/'progs/test.mdl').write_bytes(alias(4))
        r=audit(self.maps);self.assertEqual(r['status'],'failed')
        self.assertEqual(r['summary'],{'failed-contact':1})
        with self.assertRaisesRegex(ValueError,'gate failed'):require(self.maps,self.id1/'receipt.json')
        self.assertEqual(json.loads((self.id1/'receipt.json').read_text())['status'],'failed')

    def test_embedded_or_unsupported_placements_fail_without_moving_them(self):
        for z in (-3,40):
            self.put(actor(z));before=(self.maps/'room.bsp').read_bytes()
            self.assertEqual(audit(self.maps)['status'],'failed')
            self.assertEqual((self.maps/'room.bsp').read_bytes(),before)

    def test_explicit_airborne_exception_and_unclassified_actor(self):
        self.assertEqual(initial_state('VIVEC_GOD'),'levitating')
        self.assertEqual(fields('Cliff Racer')['aw_ground_mode'],1)
        self.put(actor(40,'agronian guy',1))
        r=audit(self.maps);self.assertEqual(r['status'],'passed');self.assertEqual(r['summary'],{'explicit-exception':1})
        self.put(actor(40,'agronian guy',0));self.assertEqual(audit(self.maps)['status'],'failed')
        self.put(actor(identifier='unknown-new-actor'));self.assertEqual(audit(self.maps)['status'],'failed')

    def test_overlap_uses_owner_support_and_requires_identical_copies(self):
        (self.id1/'balmora-regions.txt').write_text('AWBR1\nbm000 -10 -10 10 10 -20 -20 20 20\n')
        self.put(actor(10.25),'bm000',10)
        self.put(actor(10.25),'balmora',0) # visible overlap's lower floor is not authority
        r=audit(self.maps);self.assertEqual(r['status'],'passed');self.assertEqual(r['distinct_placements'],1)
        self.put(actor(.25),'balmora');self.assertEqual(audit(self.maps)['status'],'failed')
        self.put('','bm000',10);self.assertEqual(audit(self.maps)['status'],'failed')

    def test_missing_owner_duplicate_and_bad_model_fail(self):
        self.put(actor()+actor());self.assertEqual(audit(self.maps)['status'],'failed')
        self.put(actor());(self.id1/'progs/test.mdl').write_bytes(b'bad')
        self.assertEqual(audit(self.maps)['status'],'failed')
