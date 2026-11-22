"""Fixed conversion palette contracts; synthetic pixels only."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_quake
import build
import build_cache

class PaletteTests(unittest.TestCase):
    def test_default_matches_historical_sampled_bytes(self):
        samples=np.array([[i,(i*7)%256,(i*13)%256] for i in range(256)],dtype=np.uint8)
        strip=Image.fromarray(samples.reshape(1,-1,3),'RGB').quantize(colors=224)
        expected=strip.getpalette()[:672]+[102,119,136]*30+[238,221,170,0,0,0]
        self.assertEqual(prepare_quake.scene_palette(samples),expected)

    def test_image_step_refuses_a_sky_fallback_with_owned_data(self):
        # SKY-FLAT-PALETTE-DRIFT-41: the fallback shipped a flat sky behind one warning line.
        source=(ROOT/'tools/build_aga.py').read_text(encoding='utf-8')
        start=source.index('sky_asset_preparation = prepare_staged_sky(boot')
        check=source.index("sky_asset_preparation.get('status')=='fallback_warning'",start)
        self.assertLess(check,source.index('validate_world_ui(boot',start))
        self.assertIn("placeholder(args, 'shared-sky'",source[check:check+400])

    def test_explicit_palette_preserves_every_index(self):
        raw=bytes(range(256))*3
        samples=np.array([[1,2,3],[4,5,6]],dtype=np.uint8)
        self.assertEqual(bytes(prepare_quake.scene_palette(samples,raw)),raw)
        self.assertIsNone(prepare_quake.read_palette_input(None))

    def test_malformed_is_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for size in (0,767,769):
                palette=base/'bad.lmp';palette.write_bytes(bytes(size))
                out=base/('out-'+str(size))
                with self.assertRaisesRegex(ValueError,'exactly 768'):
                    prepare_quake.prepare(base/'missing-work',base/'missing-scene',out,palette_path=palette)
                self.assertFalse(out.exists())

    def test_actual_prepare_writes_fixed_palette_before_other_outputs(self):
        # Stop immediately after the real palette write: no scene/model conversion.
        class PaletteWritten(Exception): pass
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);work=base/'work';scene=base/'scene';out=base/'out'
            (work/'generated/seyda-neen').mkdir(parents=True);scene.mkdir()
            (work/'generated/seyda-neen/materials.json').write_text('{}')
            (scene/'scenery-index.json').write_text('{"textures":[]}')
            (scene/'scenery.mwpak').write_bytes(b'')
            palette=base/'fixed.lmp';raw=bytes(range(256))*3;palette.write_bytes(raw)
            image=io.BytesIO();Image.new('RGB',(32,32),(71,89,103)).save(image,format='PNG')
            written=[]
            real_write=Path.write_bytes
            def stop_after_palette(path,data):
                value=real_write(path,data)
                if path==out/'id1/gfx/palette.lmp':
                    written.append(bytes(data));raise PaletteWritten()
                return value
            with patch.object(prepare_quake,'read_workspace',return_value=(work,{'data_files':str(base)})), \
                 patch.object(prepare_quake,'resolve_data_files',return_value=base), \
                 patch.object(prepare_quake,'child_ci',side_effect=lambda p,n:Path(p)/n), \
                 patch.object(prepare_quake,'BSA'), \
                 patch.object(prepare_quake,'bsa_read',return_value=image.getvalue()), \
                 patch.object(Path,'write_bytes',stop_after_palette):
                with self.assertRaises(PaletteWritten):
                    prepare_quake.prepare(work,scene,out,palette_path=palette)
            self.assertEqual(written,[raw])
            self.assertEqual((out/'id1/gfx/palette.lmp').read_bytes(),raw)

    def test_builder_forwards_one_palette_argument_and_default_omits_it(self):
        tools={n:'/tools/'+n for n in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
        for args_in in ([],['--palette','/palettes with spaces/base.lmp']):
            args=build.parser().parse_args(['--data-files','/game','--sdk','/sdk',*args_in])
            command=dict(build.commands(args,tools,Path('/run')))['scene']
            if args_in:
                self.assertEqual(command.count('--palette'),1)
                self.assertEqual(command[command.index('--palette')+1],args_in[1])
            else:
                self.assertNotIn('--palette',command)

    def test_palette_content_changes_stage_external_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);palette=root/'palette.lmp';palette.write_bytes(bytes(768))
            command=[sys.executable,str(ROOT/'tools/prepare_quake.py'),'--palette',str(palette)]
            before,problems=build_cache.external_inputs('scene',command,root/'run',{})
            self.assertFalse(problems)
            self.assertIn(hashlib.sha256(bytes(768)).hexdigest(),before.values())
            palette.write_bytes(bytes([1])*768)
            after,problems=build_cache.external_inputs('scene',command,root/'run',{})
            self.assertFalse(problems);self.assertNotEqual(before,after)

ICEBERG_SOURCE=(192,213,224)      # tx_bm_iceberg's mean colour, as the converter stages it
RAMP_INDICES=[78,80,90,97,101,104,107,108,111,136,137,153,154,172,175,189]


def warm_sampled_palette():
    """A sampled palette like the scene's: 224 warm entries (red at least blue), no cool ones."""
    rng=np.random.default_rng(68)
    base=rng.uniform(20,240,(4096,1))
    samples=np.clip(np.hstack([base,base*rng.uniform(.86,.98,(4096,1)),base*rng.uniform(.62,.86,(4096,1))]),0,255)
    strip=Image.fromarray(samples.astype(np.uint8).reshape(1,-1,3),'RGB').quantize(colors=224)
    return strip.getpalette()[:672]+[102,119,136]*30+[238,221,170,0,0,0]


def lit(palette,colour,row):
    """The colour a texel of COLOUR shows at a colormap row, the way the scene converts it."""
    pal=Image.new('P',(1,1));pal.putpalette(palette)
    index=Image.new('RGB',(1,1),colour).quantize(palette=pal,dither=Image.Dither.NONE).getpixel((0,0))
    target=prepare_quake.colormap_bytes(palette)[row*256+index]
    return target,tuple(palette[target*3:target*3+3])


class IceRampTests(unittest.TestCase):
    """SOL-GLACIER-ICE-BROWN-SHEER-68: the ice drew brown-grey at the outdoor light rows."""

    def test_config_pins_the_sixteen_replaced_entries(self):
        ramp=prepare_quake.palette_ramp()
        self.assertEqual(sorted(row['index'] for row in ramp['entries']),RAMP_INDICES)
        self.assertEqual({row['index']:tuple(row['rgb']) for row in ramp['entries']},{
            104:(228,230,235),97:(205,208,209),101:(186,189,193),189:(166,172,179),80:(151,156,159),
            90:(141,142,145),137:(119,133,145),111:(128,129,130),153:(116,116,118),78:(104,117,128),
            136:(104,105,106),175:(89,101,110),172:(93,93,95),107:(79,85,92),108:(65,74,82),154:(52,60,67)})
        self.assertEqual(ramp['sampled_palette_sha256'],'618049d237fd474ee631b8f1aaf3b993abe14d3f46588b98c7c0643c098b8f50')
        self.assertTrue({'tx_bm_iceberg','tx_bm_ice_05','tx_bm_ice_06','tx_bm_icelayer_01','tx_bm_karstaag',
                         'tx_bm_karstaag_door','tx_bm_snow_02'}<=set(ramp['method']['source_textures']))
        for row in ramp['entries']:                  # every ramp colour is cool or neutral
            r,g,b=row['rgb'];self.assertGreaterEqual(b,r)

    def test_iceberg_at_row_32_is_warm_before_and_cool_with_the_ramp(self):
        old=warm_sampled_palette()
        ramp=dict(prepare_quake.palette_ramp())
        ramp['sampled_palette_sha256']=hashlib.sha256(bytes(old[:672])).hexdigest()
        new,applied=prepare_quake.apply_palette_ramp(old,ramp)
        self.assertTrue(applied)
        _,before=lit(old,ICEBERG_SOURCE,32)
        self.assertLess(before[2],before[0],before)          # the old palette: brown-grey (blue below red)
        index,after=lit(new,ICEBERG_SOURCE,32)
        self.assertIn(index,RAMP_INDICES)
        self.assertGreaterEqual(after[2],after[0],after)     # with the ramp: a cool grey
        for row in (0,16,24):
            self.assertGreaterEqual(lit(new,ICEBERG_SOURCE,row)[1][2],lit(new,ICEBERG_SOURCE,row)[1][0],row)
        # only the 16 entries change
        self.assertEqual([i for i in range(256) if old[i*3:i*3+3]!=new[i*3:i*3+3]],RAMP_INDICES)

    def test_another_sampled_palette_is_left_unchanged(self):
        old=warm_sampled_palette()
        new,applied=prepare_quake.apply_palette_ramp(old,prepare_quake.palette_ramp())
        self.assertFalse(applied);self.assertEqual(new,old)

    def test_malformed_ramp_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ramp.json'
            good=json.loads(prepare_quake.PALETTE_RAMP.read_text(encoding='utf-8'))
            for bad in ({**good,'schema':2},{**good,'entries':[]},
                        {**good,'entries':good['entries'][:1]*2},
                        {**good,'entries':[{'index':230,'rgb':[1,2,3]}]},
                        {**good,'entries':[{'index':5,'rgb':[1,2]}]}):
                path.write_text(json.dumps(bad),encoding='utf-8')
                with self.assertRaises(ValueError):prepare_quake.palette_ramp(path)

    def test_the_scene_stage_key_reads_the_ramp(self):
        index=build_cache.SourceIndex(ROOT,top_format=build_cache.STAGE_TOP_FORMAT)
        self.assertIn('config/scene-palette-ramp.json',index.closure(ROOT/'tools/prepare_quake.py')[1])


if __name__=='__main__':
    unittest.main()
