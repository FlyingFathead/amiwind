# SPDX-License-Identifier: GPL-3.0-only
import unittest,struct,tempfile
from pathlib import Path
import numpy as np
from sky_palette_overlay import spans,lookup,convert,BANK

class Tests(unittest.TestCase):
    def test_mdl_group_header_unchanged(self):
        raw=bytearray(84);raw[:8]=struct.pack('<4si',b'IDPO',6);struct.pack_into('<3i',raw,48,1,2,2)
        raw+=struct.pack('<ii2f',1,2,.1,.2)+bytes([222,255,133,101])*2+bytes(64)
        self.assertEqual(spans(raw,'progs/test.mdl')[0],[(100,4),(104,4)])
    def test_sprite_group_and_origin(self):
        raw=bytearray(36);raw[:8]=struct.pack('<4si',b'IDSP',1);struct.pack_into('<i',raw,24,1)
        raw+=struct.pack('<ii2f',1,2,.1,.2)
        for _ in range(2):raw+=struct.pack('<4i',-4,5,2,2)+bytes([222,255,101,95])
        self.assertEqual(spans(raw,'progs/a.spr')[0],[(68,4),(88,4)])
    def test_bsp_mips(self):
        tex=struct.pack('<i i',1,8)+bytes(16)+struct.pack('<6I',8,8,40,104,120,124)+bytes([222])*85
        raw=bytearray(124);struct.pack_into('<i',raw,0,29);struct.pack_into('<2i',raw,20,124,len(tex));raw+=tex
        self.assertEqual(spans(raw,'maps/a.bsp')[0],[(172,64),(236,16),(252,4),(256,1)])
    def test_image_head_spans(self):
        self.assertEqual(spans(b'AWI1'+struct.pack('<2H',2,2)+bytes(4),'reading/a.awi')[0],[(8,4)])
        self.assertEqual(spans(b'AWH1'+struct.pack('<H',1)+bytes(82),'a.awh')[0],[(24,64)])
        raw=struct.pack('>4s4H2I',b'AWS1',4,1,1,0,20,30)+struct.pack('>3H',1,0,4)+bytes(4)
        self.assertEqual(spans(raw,'a.aws')[0],[(26,4)])
    def test_wad_qpic(self):
        raw=struct.pack('<4sii',b'WAD2',1,24)+struct.pack('<2i',2,2)+bytes(4)+struct.pack('<iiiBBH16s',12,12,12,66,0,0,b'pic')
        self.assertEqual(spans(raw,'gfx.wad')[0],[(20,4)])
    def test_own_palettes_unknown_and_truncation(self):
        self.assertFalse(spans(b'AWB2'+struct.pack('<2H',1,1)+bytes(769),'a.awb')[0])
        self.assertFalse(spans(b'AWB1'+struct.pack('<H',1)+bytes(60),'intro/barriers.awb')[0])
        for rel,raw in [('a.png',bytes(16)),('unknown.lmp',bytes(16)),('a.awi',b'AWI1')]:
            with self.assertRaises(ValueError):spans(raw,rel)
    def test_lookup_source_destination_relation(self):
        palette=bytes([v for i in range(256) for v in (i,i,i)])
        new=bytearray(palette)
        for i,(_,rgb) in BANK.items():new[i*3:i*3+3]=bytes(rgb)
        table=np.tile(np.arange(256,dtype=np.uint8),(64,1));table[5,50]=222
        out=np.frombuffer(lookup(table.tobytes(),palette,new,64,'colormap'),np.uint8).reshape(64,256)
        self.assertEqual(out[5,50],223);self.assertEqual(out[0].tolist(),list(range(256)))
        self.assertTrue(np.all(out[:,255]==255));self.assertFalse(np.any(out[:,:255]==255))
    def test_final_stage_audio_and_save_fingerprint(self):
        raw=struct.pack('>4sHHII',b'MWA1',11015,8192,1,1)+bytes(16384)
        self.assertFalse(spans(raw,'music/track01.mws')[0])
        self.assertFalse(spans(bytes(32),'save-content.bin')[0])
        for data,path in [(raw,'track01.mws'),(raw+b'!','music/track01.mws'),(bytes(31),'save-content.bin')]:
            with self.assertRaises(ValueError):spans(data,path)
        malformed=bytearray(raw);malformed[-1]=1
        with self.assertRaises(ValueError):spans(malformed,'music/track01.mws')
    def test_overlay_immutable_unknown_preflight_existing_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';(src/'gfx').mkdir(parents=True)
            pal=bytes([v for i in range(256) for v in (i,i,i)])
            pal=bytearray(pal)
            for i,(target,_) in BANK.items():pal[i*3:i*3+3]=pal[target*3:target*3+3]
            pal=bytes(pal)
            (src/'gfx/palette.lmp').write_bytes(pal)
            for name,rows in [('colormap.lmp',64),('fog.lmp',16)]:
                (src/'gfx'/name).write_bytes(bytes(range(256))*rows)
            (src/'gfx/loading.lmp').write_bytes(struct.pack('<2i',2,2)+bytes([222,255,101,95]))
            before={p.name:p.read_bytes() for p in (src/'gfx').iterdir()}
            report=convert(src,root/'output')
            self.assertEqual((root/'output/gfx/loading.lmp').read_bytes(),struct.pack('<2i',2,2)+bytes([223,255,101,94]))
            self.assertEqual(before,{p.name:p.read_bytes() for p in (src/'gfx').iterdir()})
            self.assertEqual(report['bank']['222']['pixels'],1)
            with self.assertRaises(ValueError):convert(src,root/'output')
            subset=convert(src,root/'changed-only',changed_only=True)
            self.assertFalse((root/'changed-only/gfx/loading.lmp').read_bytes()==(src/'gfx/loading.lmp').read_bytes())
            self.assertTrue(any(r['overlay_written'] for r in subset['files']))
            with self.assertRaisesRegex(ValueError,'fingerprint'):convert(src,root/'wrong-fingerprint','0'*64)
            broken=bytearray(pal);broken[222*3]=0
            (src/'gfx/palette.lmp').write_bytes(broken)
            with self.assertRaisesRegex(ValueError,'two units'):convert(src,root/'too-much-error')
            (src/'gfx/palette.lmp').write_bytes(pal)
            (src/'unknown.bin').write_bytes(bytes(8))
            with self.assertRaises(ValueError):convert(src,root/'rejected')
            self.assertFalse((root/'rejected').exists())

if __name__=='__main__':unittest.main()
