# SPDX-License-Identifier: GPL-3.0-only
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import sky_palette_overlay as overlay
from prepare_shared_sky_assets import prepare_staged_sky
from build_night_sky import PHASES,ATLAS_BYTES,validate

class PipelineTests(unittest.TestCase):
    def stage(self,root):
        id1=root/'stage/id1';(id1/'gfx').mkdir(parents=True)
        pal=bytearray(v for i in range(256) for v in (i,i,i))
        for i,(target,_) in overlay.BANK.items():pal[i*3:i*3+3]=pal[target*3:target*3+3]
        (id1/'gfx/palette.lmp').write_bytes(pal)
        for name,rows in [('colormap.lmp',64),('fog.lmp',16)]:
            (id1/'gfx'/name).write_bytes(bytes(range(256))*rows)
        (id1/'gfx/aw_shared_sky.lmp').write_bytes(bytes([224])*32768)
        return id1,overlay.sha(pal)
    def owned(self,root):
        data=root/'owned';(data/'tExTuReS').mkdir(parents=True)
        for name in ('Tx_Sky_Clear.tga','Tx_Sky_Cloudy.tga'):
            image=Image.new('RGBA',(4,4),(120,120,120,210));image.putpixel((0,0),(0,0,0,0));image.save(data/'tExTuReS'/name)
        return data
    def add_owned_night(self,data):
        names=['tx_stars','tx_stars_nebula','tx_stars_nebula2','tx_stars_nebula3']
        names += ['tx_'+moon+'_'+phase for moon in ('masser','secunda') for phase in PHASES]
        for i,name in enumerate(names):
            image=Image.new('RGBA',(4,4),(20+i*5,30+i*3,70+i*2,180))
            image.putpixel((0,0),(255,240,200,255));image.save(data/'tExTuReS'/(name+'.tga'))

    def test_verified_cloud_reuse_prepares_missing_night_then_verifies_without_owned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);id1,fingerprint=self.stage(root);data=self.owned(root)
            with patch.object(overlay,'EXPECTED_PALETTE',fingerprint):
                cloud=prepare_staged_sky(id1,data,root/'cloud-work')
            self.assertEqual(cloud['night_sky']['status'],'fallback_warning')
            shutil.copyfile(cloud['shared_sky_source'],id1/'gfx/aw_shared_sky.lmp')
            before={p.name:p.read_bytes() for p in (id1/'gfx').iterdir()}
            self.add_owned_night(data)
            report=prepare_staged_sky(id1,data,root/'night-work')
            self.assertEqual(report['status'],'verified_reuse')
            self.assertEqual(report['night_sky']['status'],'prepared_owned_night')
            self.assertTrue(report['night_sky']['night_sky'])
            atlas=(id1/'gfx/aw_night_sky.lmp').read_bytes();self.assertEqual(len(atlas),ATLAS_BYTES)
            validate(atlas,(id1/'gfx/palette.lmp').read_bytes())
            for name,raw in before.items():self.assertEqual((id1/'gfx'/name).read_bytes(),raw)
            again=prepare_staged_sky(id1,None,root/'verify-work')
            self.assertEqual(again['night_sky']['status'],'verified_reuse')
            self.assertFalse((root/'verify-work').exists())
            marker=id1/'gfx/night-sky.json';bad=json.loads(marker.read_text());bad['palette_sha256']='0'*64;marker.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):prepare_staged_sky(id1,None,root/'bad-marker')
            self.assertEqual((id1/'gfx/aw_night_sky.lmp').read_bytes(),atlas)

    def test_fresh_default_and_explicit_or_local_paths_also_prepare_night(self):
        for mode in ('default','explicit','local'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);id1,fingerprint=self.stage(root);data=self.owned(root);self.add_owned_night(data)
                options={'shared_sky_source':root/'custom.lmp'} if mode=='explicit' else {'local_skybox':'true'} if mode=='local' else {}
                with patch.object(overlay,'EXPECTED_PALETTE',fingerprint):
                    report=prepare_staged_sky(id1,data,root/'work',**options)
                self.assertEqual(report['night_sky']['status'],'prepared_owned_night')
                self.assertEqual((id1/'gfx/aw_night_sky.lmp').stat().st_size,ATLAS_BYTES)
                self.assertTrue((id1/'gfx/night-sky.json').is_file())

    def test_default_then_verified_reuse_and_backups(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);id1,fingerprint=self.stage(root);data=self.owned(root)
            before=(id1/'gfx/palette.lmp').read_bytes()
            with patch.object(overlay,'EXPECTED_PALETTE',fingerprint):
                report=prepare_staged_sky(id1,data,root/'work')
            self.assertTrue(report['vivid_sky']);self.assertEqual(report['status'],'prepared_owned_clouds')
            # BUILD-PATH-IN-PAYLOAD-32: the shipped marker does not name the build folder.
            marker=(id1/'gfx/sky-palette-bank.json').read_text(encoding='utf-8')
            self.assertNotIn(str(root),marker);self.assertNotIn(root.as_posix(),marker)
            self.assertEqual(json.loads(marker)['shared_sky_source'],'work/owned-cloud-sky.lmp')
            self.assertTrue(Path(report['shared_sky_source']).is_file())
            self.assertEqual((root/'work/before-originals/gfx/palette.lmp').read_bytes(),before)
            self.assertEqual((root/'work/before-originals/gfx/aw_shared_sky.lmp').read_bytes(),bytes([224])*32768)
            # Model the following configure_staged_maps installation, not a UI test.
            shutil.copyfile(report['shared_sky_source'],id1/'gfx/aw_shared_sky.lmp')
            again=prepare_staged_sky(id1,data,root/'second-work')
            self.assertEqual(again['status'],'verified_reuse');self.assertFalse((root/'second-work').exists())
            (id1/'gfx/aw_shared_sky.lmp').write_bytes(bytes(32768))
            with self.assertRaisesRegex(ValueError,'Stale'):prepare_staged_sky(id1,data,root/'third-work')
    def test_explicit_and_local_bypass_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);id1,_=self.stage(root);before=(id1/'gfx/palette.lmp').read_bytes()
            self.assertEqual(prepare_staged_sky(id1,None,root/'work',shared_sky_source=root/'explicit.lmp')['status'],'explicit_shared_source')
            self.assertEqual(prepare_staged_sky(id1,None,root/'work',local_skybox='true')['status'],'local_skybox_debug')
            self.assertEqual((id1/'gfx/palette.lmp').read_bytes(),before);self.assertFalse((root/'work').exists())
    def test_missing_owned_and_unsupported_palette_warn(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);id1,fingerprint=self.stage(root);before=(id1/'gfx/palette.lmp').read_bytes()
            with patch.object(overlay,'EXPECTED_PALETTE',fingerprint):
                report=prepare_staged_sky(id1,None,root/'no-owned')
            self.assertFalse(report['vivid_sky']);self.assertIn('No owned',report['warning']);self.assertEqual(report['night_sky']['status'],'fallback_warning')
            report=prepare_staged_sky(id1,None,root/'wrong-palette')
            self.assertFalse(report['vivid_sky']);self.assertIn('fingerprint',report['warning'])
            self.assertEqual((id1/'gfx/palette.lmp').read_bytes(),before)
    def test_unknown_payload_hard_error_preserves_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);id1,fingerprint=self.stage(root);data=self.owned(root);before=(id1/'gfx/palette.lmp').read_bytes()
            (id1/'unknown.bin').write_bytes(b'unsafe')
            with patch.object(overlay,'EXPECTED_PALETTE',fingerprint):
                with self.assertRaisesRegex(ValueError,'Unknown'):prepare_staged_sky(id1,data,root/'work')
            self.assertEqual((id1/'gfx/palette.lmp').read_bytes(),before)
            self.assertFalse((id1/'gfx/sky-palette-bank.json').exists())

if __name__=='__main__':unittest.main()
