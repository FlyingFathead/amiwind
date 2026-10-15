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

if __name__=='__main__':
    unittest.main()
