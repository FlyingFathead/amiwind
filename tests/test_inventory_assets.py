"""Synthetic original-record checks for inventory metadata and action admission."""
import struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_inventory as inv

def field(kind,data):
    return kind.encode()+struct.pack('<I',len(data))+data
def record(kind,fields):
    data=b''.join(field(k,v) for k,v in fields)
    return kind.encode()+struct.pack('<III',len(data),0,0)+data
def text(value):
    return value.encode()+b'\0'

class InventoryAssetsTests(unittest.TestCase):
    def test_binary_effects_are_not_enchantment_ids_and_original_initial_counts(self):
        raw=record('ALCH',[('NAME',text('potion')),('ALDT',struct.pack('<fii',.5,12,0)),('ENAM',b'\x00\x01\x02\x03'*6)])
        raw+=record('CLOT',[('NAME',text('shirt')),('FNAM',text('Shirt')),('CTDT',struct.pack('<ifHH',2,1.,3,0))])
        raw+=record('NPC_',[('NAME',text('player')),('NPCO',struct.pack('<i',1)+b'shirt'+b'\0'*27)])
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Morrowind.esm').write_bytes(raw)
            with patch.object(inv,'resolve_data_files',return_value=base):
                report=inv.prepare(base,base/'id1',palette=b'\0'*768,models=False)
            items=base.joinpath('id1/inventory/items.awi').read_bytes()
            self.assertEqual(items[:4],b'AWI2');self.assertEqual(len(items),8+2*512)
            self.assertEqual(items[8+312:8+376],b'\0'*64)
            initial=base.joinpath('id1/inventory/initial.awi').read_bytes()
            self.assertEqual(initial[:8],b'AWST'+struct.pack('<I',1))
            self.assertEqual(initial[8:72].split(b'\0')[0],b'shirt')
            self.assertEqual(struct.unpack_from('<ii',initial,72),(1,8))
            self.assertEqual(report['initial_items'],[{'id':'shirt','count':1}])

    def test_script_proof_requires_first_executable_registration_guard(self):
        source='Begin ring\nshort state\nshort OnPCAdd\nif ( CharGenState == -1 )\n return\nendif\nset state to 1\nEnd'
        self.assertTrue(inv.script_inert_after_registration(source))
        self.assertFalse(inv.script_inert_after_registration('Begin ring\nset state to 1\n'+source))
        self.assertFalse(inv.script_inert_after_registration('Begin ring\nif CharGenState == 1\nreturn\nendif'))
        with self.assertRaises(ValueError):inv.safe_text('binary\x01effect',64)
        with self.assertRaises(ValueError):inv.safe_text('a'*64,64)

if __name__=='__main__':unittest.main()
