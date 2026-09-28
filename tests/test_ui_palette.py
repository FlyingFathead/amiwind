"""Protect geometry/console colours while reserving redundant sky entries."""
import struct,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ui_palette import check_scene,check_pixels

class PaletteSafety(unittest.TestCase):
    def test_lighting_lookup_cannot_use_reserved_slots(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'gfx').mkdir();f=p/'gfx/colormap.lmp'
            f.write_bytes(bytes([0,224,254,255]));check_scene(p)
            f.write_bytes(bytes([0,225,254]));self.assertRaises(ValueError,check_scene,p)
    def test_alias_skin_audited_without_touching_vertex_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'progs').mkdir();(p/'gfx').mkdir()
            h=bytearray(88);struct.pack_into('<4si',h,0,b'IDPO',6);struct.pack_into('<3i',h,48,1,4,4)
            f=p/'progs/test.mdl';f.write_bytes(h+bytes([224])*16+bytes([225,226]))
            check_scene(p)
            f.write_bytes(h+bytes([225])*16);self.assertRaises(ValueError,check_scene,p)
    def test_indices_outside_bank_preserved(self):
        check_pixels(bytes([0,224,254,255]),'test')
        for i in range(225,254):self.assertRaises(ValueError,check_pixels,bytes([i]),'test')
