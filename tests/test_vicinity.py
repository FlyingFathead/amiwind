import struct,unittest
from mwad.vicinity import region_audit,roster_markdown

def sub(tag,b):return tag.encode()+struct.pack('<I',len(b))+b
def rec(tag,fields):
 b=b''.join(sub(k,v) for k,v in fields);return tag.encode()+struct.pack('<III',len(b),0,0)+b
def cell(name,grid,refs,inside=False):
 fields=[('NAME',name.encode()),('DATA',struct.pack('<Iii',int(inside),*grid))]
 for number,identifier,extra in refs:
  fields += [('FRMR',struct.pack('<I',number)),('NAME',identifier.encode()),('DATA',struct.pack('<6f',0,0,0,0,0,0)),*extra]
 return rec('CELL',fields)
def npc(name):
 return rec('NPC_',[('NAME',name.encode()),('FNAM',name.encode()),('FLAG',struct.pack('<I',0)),
   ('RNAM',b'Test Race'),('AIDT',struct.pack('<HBBB3xI',30,10,20,0,0)),
   ('AI_W',struct.pack('<hh10B',100,0,0,*([0]*8),1))])
def fixture():
 dest=[('DODT',struct.pack('<6f',1,2,3,0,0,0)),('DNAM',b'Test House')]
 return (npc('outside')+npc('inside')+rec('DOOR',[('NAME',b'gate')])+rec('CONT',[('NAME',b'box'),('FLAG',struct.pack('<I',8))])+
  cell('Town',(-2,-9),[(1,'outside',[]),(2,'gate',dest),(3,'box',[('ANAM',b'owner')]),(4,'outside',[('DELE',b'')])])+
  cell('Test House',(0,0),[(5,'inside',[])],True)+cell('Unlinked House',(0,0),[(6,'inside',[])],True)+
  cell('Far',(7,8),[(7,'outside',[])]))
class VicinityTests(unittest.TestCase):
 def test_direct_interior_is_separate_and_no_runtime_load(self):
  report=region_audit(fixture(),radius=0)
  self.assertEqual(len(report['cells']),2)
  self.assertEqual(report['counts']['exterior']['NPC_'],1)
  self.assertEqual(report['counts']['interior']['NPC_'],1)
  self.assertIn('audit only',report['scope']['runtime_residency'])
  self.assertNotIn('Unlinked House',roster_markdown(report))
 def test_door_coordinates_and_container_metadata_survive(self):
  report=region_audit(fixture(),radius=0);p={r['number']:r for r in report['placements']}
  self.assertEqual(p[2]['target_cell_key'],'interior:test house')
  self.assertEqual(p[2]['destination']['position'],[1,2,3])
  self.assertEqual(p[2]['destination_status'],'source-coordinate-only')
  self.assertIn(['ANAM',b'owner'.hex()],p[3]['raw_subrecords'])
  self.assertNotIn(4,p)
 def test_behavior_order_and_unresolved_destination_are_reported(self):
  raw=fixture().replace(b'Test House',b'Lost House',1);r=region_audit(raw,radius=0)
  self.assertEqual(r['warnings'],['Missing direct interior: lost house'])
  actor=next(p for p in r['placements'] if p['type']=='NPC_')
  self.assertEqual(actor['behavior']['packages'][0]['scaled_distance'],25)
  self.assertFalse(actor['behavior']['runtime_wandering'])
 def test_duplicate_cells_and_unbounded_radius_rejected(self):
  with self.assertRaisesRegex(ValueError,'Duplicate CELL'):region_audit(fixture()+cell('Town',(-2,-9),[]))
  with self.assertRaises(ValueError):region_audit(fixture(),radius=5)
