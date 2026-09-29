"""Synthetic source-door mapping: exterior destinations need no cell name."""
import struct,tempfile,unittest
from pathlib import Path
from prepare_doors import catalogue,runtime_position

def sub(tag,data):return tag.encode()+struct.pack('<I',len(data))+data
def record(tag,data):return tag.encode()+struct.pack('<III',len(data),0,0)+data
def cell(name,flags,ref,target=None):
    data=sub('NAME',name.encode()+b'\0')+sub('DATA',struct.pack('<Iii',flags,-1,-9))
    data+=sub('FRMR',struct.pack('<I',ref))+sub('NAME',b'hatch\0')
    point=(10,20,30) if flags&1 else (-11000,-71000,30)
    data+=sub('DATA',struct.pack('<6f',*point,0,0,0))
    data+=sub('DODT',struct.pack('<6f',-8482,-73627,320,0,0,.7854))
    if target is not None:data+=sub('DNAM',target.encode()+b'\0')
    return record('CELL',data)
class Doors(unittest.TestCase):
    def test_instance_destination_and_direction_are_not_inferred_from_base(self):
        raw=record('DOOR',sub('NAME',b'hatch\0')+sub('MODL',b'd\\hatch.nif\0')+sub('SNAM',b'open\0'))
        raw+=cell('Imperial Prison Ship',1,1)+cell('Seyda Neen',0,2,'Imperial Prison Ship')
        raw+=cell('Seyda Neen, Census and Excise Office',1,3,'Seyda Neen, Census and Excise Office')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.esm';p.write_bytes(raw);rows=catalogue(p)['doors']
        self.assertEqual(len(rows),3)
        self.assertFalse(rows[0]['destination_interior']);self.assertTrue(rows[1]['destination_interior'])
        self.assertEqual(rows[0]['open_sound'],'open')
        self.assertEqual(runtime_position([-8482,-73627,320],False),[695.5,-486.75,80])
        self.assertEqual(runtime_position([20,40,80],True),[5,10,20])
