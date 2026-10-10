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

class EnemyBarYellow(unittest.TestCase):
    """HUD-ENEMY-BAR-COLOUR-33: the reserved bank carries the enemy bar's yellow (format 2); the sky
    palette approval does not depend on the bank; a format 1 scene is upgraded in place."""
    def test_yellow_tint_matches_the_original_bar(self):
        from PIL import Image
        import ui_palette
        bar=ui_palette.yellow_bar(Image.new('RGBA',(2,2),(200,200,200,255)))
        self.assertEqual(bar.getpixel((0,0)),(200,146,0,255))
        self.assertEqual(ui_palette.PALETTE_FORMAT,'AmiWind reserved UI palette 2')
    def test_sky_approval_ignores_the_ui_bank(self):
        import hashlib,sky_palette_overlay as sky
        from unittest.mock import patch
        legacy=bytes(range(87));v1=bytes(225*3)+legacy+bytes(range(2*3))
        with patch.object(sky,'EXPECTED_PALETTE',hashlib.sha256(v1).hexdigest()):
            v2=v1[:225*3]+bytes([7])*87+v1[254*3:]
            self.assertTrue(sky.approved(v1))
            self.assertFalse(sky.approved(v2))
            self.assertTrue(sky.approved(v2,legacy))
            self.assertFalse(sky.approved(v2[:3]+b'\x09'+v2[4:],legacy))      # outside the bank: refused
    def test_format_1_scene_is_upgraded_in_place(self):
        import hashlib,json,ui_palette
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            game=Path(td);gfx=game/'gfx';gfx.mkdir()
            old=bytes([40,35,30])*225+bytes([9,9,9])*29+bytes([1,2,3])*2
            (gfx/'palette.lmp').write_bytes(old)
            for name,rows in (('colormap.lmp',64),('fog.lmp',16)):(gfx/name).write_bytes(bytes([224])*(256*rows))
            (gfx/'ui-palette.json').write_text(json.dumps({'format':'AmiWind reserved UI palette 1',
                'palette_sha256':hashlib.sha256(old).hexdigest()}),encoding='utf-8')
            new=old[:225*3]+bytes([200,146,0])*29+old[254*3:]
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
            sys.modules.pop('mwad',None)       # tools/mwad.py (the CLI) must not shadow the package
            with patch.object(ui_palette,'reserved_palette',return_value=(new,{})) as reserve:
                report=ui_palette.reserve(game,game)
            self.assertTrue(reserve.call_args.kwargs['upgrade'])
            self.assertEqual(report['format'],'AmiWind reserved UI palette 2')
            self.assertEqual((gfx/'palette.lmp').read_bytes(),new)
