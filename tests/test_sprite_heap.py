# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import struct,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from sprite_heap import estimate_sprite,inspect_sprites,allocation,sprite_loader_profile,efrag_pool_profile,inspect_efrags
SIZES={'hunk':16,'pointer':4,'float':4,'msprite':32,'mspriteframe':32,'mspritegroup':12,'mspriteframedesc':8,'entity':224}
def sprite(w=80,h=60):
    return struct.pack('<4siifiiifi',b'IDSP',1,2,100,w,h,1,0,0)+struct.pack('<5i',0,-w//2,h,w,h)+bytes([255])*(w*h)
class SpriteHeapTests(unittest.TestCase):
    def test_counts_decoded_header_frame_pixels_and_input_overlap(self):
        raw=sprite();r=estimate_sprite(raw,SIZES)
        self.assertEqual(r['resident_hunk_bytes'],allocation(32,16)+allocation(32+4800,16))
        self.assertEqual(r['temporary_input_bytes'],allocation(len(raw),16))
        self.assertEqual(estimate_sprite(sprite(8,8),SIZES)['temporary_input_bytes'],0)
    def test_streamed_policy_removes_staging_without_changing_residency(self):
        raw=sprite()
        before=estimate_sprite(raw,SIZES)
        after=estimate_sprite(raw,{**SIZES,'sprite_streaming':1})
        self.assertEqual(after['temporary_input_bytes'],0)
        for key in ('resident_hunk_bytes','pixel_bytes','frames','sha256'):
            self.assertEqual(before[key],after[key])
        self.assertEqual(after['input_loader_mode'],'streamed')

    def test_loader_policy_requires_enabled_guarded_dispatch(self):
        source='#define AW_STREAM_SPRITES 1\n#define AW_SPRITE_PIXEL_CHUNK 2048\n#if AW_STREAM_SPRITES\nif(Mod_TryStreamSprite(mod))return mod;\n#endif\n'
        profile=sprite_loader_profile(source)
        self.assertEqual(profile['mode'],'streamed')
        self.assertEqual(profile['conversion_stack_chunk_bytes'],2048)
        for disabled in (source.replace('SPRITES 1','SPRITES 0'),
                         source.replace('#if AW_STREAM_SPRITES',''),
                         '/*'+source+'*/', '// #define AW_STREAM_SPRITES 1\n'):
            self.assertEqual(sprite_loader_profile(disabled)['mode'],'staged')

    def test_repeated_placements_share_one_model_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'progs').mkdir();(root/'progs/tree.spr').write_bytes(sprite())
            entity=b'{"classname" "aw_flora" "model" "progs/tree.spr" "aw_scale" "0.5"}\n'
            r=inspect_sprites(entity+entity,root,SIZES)
            self.assertEqual(r['static_sprite_instances'],2);self.assertEqual(r['unique_sprite_models'],1)
            self.assertEqual(r['resident_hunk_bytes'],estimate_sprite(sprite(),SIZES)['resident_hunk_bytes'])
    def test_truncated_bad_group_or_extra_bytes_fail(self):
        raw=sprite()
        for bad in (raw[:-1],raw+b'x',raw[:36]+struct.pack('<i',2)+raw[40:]):
            with self.assertRaises(ValueError):estimate_sprite(bad,SIZES)
        group=raw[:36]+struct.pack('<ii',1,2)+struct.pack('<2f',.1,.2)+raw[40:]+raw[40:]
        r=estimate_sprite(group,SIZES);self.assertEqual(r['frames'],2);self.assertEqual(r['pixel_bytes'],9600)
    def test_missing_unsafe_assets_and_invalid_scales_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for path in ('../tree.spr','/tree.spr','missing.spr'):
                with self.assertRaises(ValueError):inspect_sprites(('{"model" "'+path+'"}').encode(),root,SIZES)
            for scale in ('0','-1','nan','inf','bad'):
                ent=('{"classname" "aw_flora" "model" "tree.spr" "aw_scale" "'+scale+'"}').encode()
                with self.assertRaises(ValueError):inspect_sprites(ent,root,SIZES)
    def test_pixel_hash_records_exact_asset_content(self):
        raw=sprite();changed=raw[:-1]+b'\0'
        a,b=estimate_sprite(raw,SIZES),estimate_sprite(changed,SIZES)
        self.assertEqual(a['resident_hunk_bytes'],b['resident_hunk_bytes']);self.assertNotEqual(a['sha256'],b['sha256'])
    def test_dense_flora_requires_larger_signon_and_keeps_capacity_margin(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'tree.spr').write_bytes(sprite(8,8))
            ent=b'{"classname" "aw_flora" "model" "tree.spr" "aw_scale" "1"}\n'
            raw=ent*266
            with self.assertRaisesRegex(ValueError,'signon capacity'):
                inspect_sprites(raw,root,{**SIZES,'signon_capacity':8192})
            report=inspect_sprites(raw,root,{**SIZES,'signon_capacity':16380})
            self.assertEqual(report['signon_upper_bound_bytes'],266*33+1024)
            self.assertGreater(report['signon_margin_bytes'],0)
            with self.assertRaisesRegex(ValueError,'signon capacity'):
                inspect_sprites(ent*480+b'{"classname" "func_wall"}\n'*100,root,SIZES)

    def test_efrag_bounds_scale_and_pages_include_header_and_alignment(self):
        raw=sprite(8,8)
        asset={'model':'tree.spr',**estimate_sprite(raw,SIZES)}
        sprites={'sprite_assets':[asset]}
        sizes={**SIZES,'efrag':16}
        policy={'base_links':1,'page_links':2,'max_links':7,'max_statics':512}
        table={'entities':b'{"classname" "aw_flora" "model" "tree.spr" "aw_scale" "1"}',
               'nodes':struct.pack('<i2h6h2H',0,-2,-3,*([-100]*3+[100]*3),0,0),
               'planes':struct.pack('<4fi',1,0,0,10,0),
               'leafs':b''.join(struct.pack('<ii6h2H4B',contents,0,*([0]*12)) for contents in (-2,-1,-1)),
               'models':b''}
        one=inspect_efrags(table,sprites,sizes,policy)
        self.assertEqual(one['required_links'],1)
        self.assertEqual(one['resident_hunk_bytes'],0)
        table['entities']=table['entities'].replace(b'"1"',b'"2"')
        scaled=inspect_efrags(table,sprites,sizes,policy)
        self.assertEqual(scaled['required_links'],2)
        self.assertEqual(scaled['overflow_pages'],1)
        self.assertEqual(scaled['page_payload_bytes'],36)
        self.assertEqual(scaled['page_alignment_bytes'],12)
        self.assertEqual(scaled['page_hunk_header_bytes'],16)
        self.assertEqual(scaled['resident_hunk_bytes'],64)
        self.assertEqual(inspect_efrags(table,sprites,{**sizes,'efrag_page':36},policy),scaled)
        with self.assertRaisesRegex(ValueError,'page layout'):
            inspect_efrags(table,sprites,{**sizes,'efrag_page':40},policy)
        table['entities']*=4
        with self.assertRaisesRegex(ValueError,'leaf-link limit'):
            inspect_efrags(table,sprites,sizes,policy)

    def test_efrag_policy_comes_from_matching_source_literals(self):
        source='#define MAX_EFRAGS 8192\n#define AW_EFRAG_PAGE_LINKS 1024\n#define AW_EFRAG_LIMIT 65536\n#define MAX_STATIC_ENTITIES 512\n'
        self.assertEqual(efrag_pool_profile(source),{'base_links':8192,'page_links':1024,'max_links':65536,'max_statics':512})
        for bad in ('/*'+source+'*/',source.replace('65536','65535'),source.replace('1024','0')):
            with self.assertRaises(ValueError):efrag_pool_profile(bad)

if __name__=='__main__':unittest.main()
