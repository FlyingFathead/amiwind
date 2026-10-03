"""Initial-placement gate against small independent BSP/MDL fixtures."""
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from actor_grounding import fields, initial_state, bake_ground
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

    def test_baker_fits_actual_model_feet_and_retains_authored_coordinates(self):
        from check_actor_ground import entities
        self.put(actor());(self.id1/'progs/test.mdl').write_bytes(alias(4))
        report=bake_ground(self.maps)
        self.assertEqual(report[0]['mesh_contact'],'fitted')
        self.assertEqual(audit(self.maps)['status'],'passed')
        before=(self.maps/'room.bsp').read_bytes();e=entities(before)[1]
        self.assertEqual(e['aw_ground_valid'],'1')
        self.assertEqual(e['aw_authored_origin'],'0.00000 0.00000 0.25000')
        self.assertLess(float(e['origin'].split()[2]),0)
        bake_ground(self.maps);self.assertEqual((self.maps/'room.bsp').read_bytes(),before)

    def test_baker_cannot_certify_unsupported_actor(self):
        self.put(actor(80))
        report=bake_ground(self.maps)
        self.assertNotIn('placed_origin',report[0])
        self.assertEqual(audit(self.maps)['status'],'failed')
        self.assertNotIn(b'"aw_ground_valid" "1"',(self.maps/'room.bsp').read_bytes())

    def baseline(self):
        self.put(actor(2))
        path = self.id1/'approved.json'
        path.write_text(json.dumps(audit(self.maps), indent=2)+'\n')
        return path

    def test_private_acceptance_keeps_failed_audit_and_exact_baseline(self):
        approved = self.baseline(); before = approved.read_bytes()
        output = self.id1/'new-report.json'
        r = require(self.maps, output, approved)
        self.assertEqual(r['status'], 'failed')
        self.assertEqual(r['acceptance']['status'], 'owner-accepted-known-findings')
        self.assertFalse(r['acceptance']['production_gate_passed'])
        stored = json.loads(output.read_text())
        self.assertEqual(stored, json.loads(before))
        self.assertNotIn('acceptance', stored)
        self.assertEqual(approved.read_bytes(), before)

    def test_same_failure_count_with_changed_contact_is_rejected(self):
        approved = self.baseline()
        self.put(actor(2.1))
        self.assertEqual(len(audit(self.maps)['errors']), 1)
        with self.assertRaisesRegex(ValueError, 'differs from approved'):
            require(self.maps, self.id1/'new.json', approved)

    def test_changed_payload_even_with_same_contacts_is_rejected(self):
        approved = self.baseline()
        self.put(actor(2)+'{\n"classname" "info_null"\n}\n')
        with self.assertRaisesRegex(ValueError, 'differs from approved'):
            require(self.maps, self.id1/'new.json', approved)

    def test_added_contact_failure_is_rejected(self):
        approved = self.baseline()
        self.put(actor(2)+actor(2, ref='456'))
        with self.assertRaisesRegex(ValueError, 'differs from approved'):
            require(self.maps, self.id1/'new.json', approved)

    def test_invalid_baseline_is_not_waivable(self):
        self.put(actor(identifier='not-classified'))
        approved = self.id1/'approved.json'
        approved.write_text(json.dumps(audit(self.maps)))
        with self.assertRaisesRegex(ValueError, 'only unresolved mesh-contact'):
            require(self.maps, self.id1/'new.json', approved)

    def test_baseline_cannot_be_overwritten_by_audit(self):
        approved = self.baseline(); before = approved.read_bytes()
        with self.assertRaisesRegex(ValueError, 'separate'):
            require(self.maps, approved, approved)
        self.assertEqual(approved.read_bytes(), before)

    def test_zero_findings_pass_without_waiver(self):
        approved = self.baseline(); self.put(actor())
        r = require(self.maps, self.id1/'new.json', approved)
        self.assertEqual(r['acceptance']['status'], 'passed')
        self.assertTrue(r['acceptance']['production_gate_passed'])
        self.assertNotIn('approved_report_sha256', r['acceptance'])
        saved = (self.id1/'new.json').read_bytes()
        self.assertNotIn(b'\r', saved)
        self.assertEqual(hashlib.sha256(saved).hexdigest(), r['acceptance']['report_sha256'])

    def test_early_check_excludes_only_unbuilt_world_bsp_hashes(self):
        approved = self.baseline()
        r = json.loads(approved.read_text())
        r['payload_sha256']['maps/vf0000.bsp'] = '0'*64
        approved.write_text(json.dumps(r))
        require(self.maps, self.id1/'early.json', approved, before_world=True)
        with self.assertRaisesRegex(ValueError, 'differs from approved'):
            require(self.maps, self.id1/'final.json', approved)
        r['payload_sha256']['maps/room.bsp'] = '1'*64
        approved.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError, 'differs from approved'):
            require(self.maps, self.id1/'early.json', approved, before_world=True)
