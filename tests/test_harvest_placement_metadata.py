# SPDX-License-Identifier: GPL-3.0-only
import struct,unittest
from prepare_harvest import source_context,placement_metadata,prepare_graph
from test_world_harvest import cells,refs,binding
from test_prepare_harvest import source
from test_world_flora_integration import record,sub
from mwad.audit import records

def fixture(extra):
 raw=cells(source(),[('Cave A',1,False)])
 return b''.join(record(tag,payload+extra if tag=='CELL' else payload) for tag,flags,payload in records(raw))

class MetadataTests(unittest.TestCase):
 def test_neutral_fields_retained_without_changing_original_quantity(self):
  extra=sub('ANAM',b'\0')+sub('INTV',struct.pack('<i',0))+sub('NAM9',struct.pack('<i',1))
  c=source_context(fixture(extra));r=refs(c)[0];m=placement_metadata(c,r)
  self.assertEqual((m['owner'],m['charge'],m['gold_value']),('',0,1))
  self.assertEqual([v['tag'] for v in m['original_subrecords']],['ANAM','INTV','NAM9'])
  graph=prepare_graph(c,[r],binding)
  self.assertEqual(graph[1][-1][2],2)
  self.assertEqual(graph[3][0]['placement_metadata'],m)
 def test_owner_is_preserved_and_cannot_become_unowned_loot(self):
  c=source_context(fixture(sub('ANAM',b'Original Owner\0')+sub('INTV',b'\0'*4)+sub('NAM9',b'\1\0\0\0')))
  r=refs(c)[0];m=placement_metadata(c,r)
  self.assertEqual(m['owner'],'Original Owner')
  self.assertEqual(m['admission'],'requires_ownership_and_theft')
  with self.assertRaisesRegex(ValueError,'ownership/theft'):prepare_graph(c,[r],binding)
 def test_nondefault_duplicate_and_malformed_fields_reject(self):
  for extra in (sub('INTV',struct.pack('<i',2)),sub('NAM9',struct.pack('<i',3)),
                sub('INTV',b'xx'),sub('ANAM',b'notterminated'),sub('INTV',b'\0'*4)*2):
   c=source_context(fixture(extra))
   with self.assertRaises(ValueError):prepare_graph(c,refs(c),binding)

if __name__=='__main__':unittest.main()
