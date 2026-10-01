"""Protect geometry/console colours while reserving redundant sky entries."""
import struct,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ui_palette import check_scene,check_pixels,sync_lookups

class PaletteSafety(unittest.TestCase):
    def test_new_skin_colours_are_lit_and_fogged_without_grey_sky_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            game=Path(td);gfx=game/'gfx';gfx.mkdir()
            palette=bytearray(bytes([40,35,30])*256)
            palette[224*3:225*3]=bytes([102,119,136])
            palette[228*3:229*3]=bytes([209,183,171])
            (gfx/'palette.lmp').write_bytes(palette)
            originals={}
            for name,rows in (('colormap.lmp',64),('fog.lmp',16)):
                originals[name]=bytes([224])*(256*rows);(gfx/name).write_bytes(originals[name])
            with self.assertRaisesRegex(ValueError,'Stale'):sync_lookups(game,check=True)
            sync_lookups(game);sync_lookups(game,check=True)
            for name,original in originals.items():
                result=(gfx/name).read_bytes()
                self.assertEqual(result[228],228) # Full light / zero fog stays flesh coloured.
                for i,(before,after) in enumerate(zip(original,result)):
                    if i%256 not in range(225,254):self.assertEqual(before,after)
            self.assertEqual((gfx/'fog.lmp').read_bytes()[15*256+228],224)
            (gfx/'fog.lmp').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'size'):sync_lookups(game)
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
