"""Synthetic tests of the bounded owned night-atlas contract; no game assets."""
import unittest
import struct
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from PIL import Image
from build_night_sky import build_atlas, validate, PHASES, ATLAS_BYTES, ART_BYTES, STAR_MASK_BYTES, fnv1a
from build_night_sky import prepare_night_sky, CONVERSION_REVISION


class NightAtlasTests(unittest.TestCase):
    palette = bytes(v for i in range(256) for v in (i, i, i))

    def images(self):
        result = {name: Image.new('RGBA', (8, 8), (0, 0, 0, 0)) for name in
                  ('tx_stars', 'tx_stars_nebula', 'tx_stars_nebula2', 'tx_stars_nebula3')}
        for moon in ('masser', 'secunda'):
            for i, phase in enumerate(PHASES):
                result['tx_'+moon+'_'+phase] = Image.new('RGBA', (8, 8), (32+i*24,)*3+(255,))
        return result

    def test_size_phase_order_and_explicit_point_star_mask(self):
        images = self.images()
        images['tx_stars'] = Image.new('RGBA', (512, 512))
        images['tx_stars'].putpixel((9, 13), (240, 240, 240, 255))
        raw = build_atlas(images, self.palette)
        self.assertEqual(len(raw), ATLAS_BYTES)
        pixels = validate(raw, self.palette)
        self.assertEqual(pixels[63*128+3], 240)
        self.assertEqual(raw[:4], b'AWN2')
        self.assertEqual(sum(v.bit_count() for v in pixels[ART_BYTES:]), 1)
        index=63*128+3
        self.assertTrue(pixels[ART_BYTES+index//8] & (1 << (index & 7)))
        self.assertEqual(pixels[0],255)  # empty black space is transparent
        for moon in range(2):
            for phase in range(8):
                self.assertEqual(pixels[16384+(moon*8+phase)*576:16384+(moon*8+phase+1)*576], bytes([32+phase*24])*576)

    def test_alpha_and_payload_palette_binding(self):
        images = self.images()
        images['tx_masser_new'] = Image.new('RGBA', (8, 8), (255, 255, 255, 0))
        raw = build_atlas(images, self.palette)
        self.assertEqual(validate(raw, self.palette)[16384+4*576:16384+5*576], bytes([255])*576)
        for damaged in (raw[:-1], raw[:4]+b'\0'+raw[5:], raw[:-1]+bytes([raw[-1]^1])):
            with self.assertRaises(ValueError):
                validate(damaged, self.palette)
        with self.assertRaises(ValueError):
            validate(raw, bytes([1])+self.palette[1:])
        with self.assertRaises(ValueError):
            build_atlas(images, self.palette[:-1])

    def test_black_key_keeps_stars_behind_original_nebula_and_moon_black_opaque(self):
        images=self.images()
        images['tx_stars']=Image.new('RGBA',(128,128),(240,240,240,255))
        images['tx_stars_nebula']=Image.new('RGBA',(128,128),(160,80,48,128))
        images['tx_masser_full']=Image.new('RGBA',(24,24),(0,0,0,255))
        raw=build_atlas(images,self.palette);pixels=validate(raw,self.palette)
        self.assertEqual(sum(v.bit_count() for v in pixels[ART_BYTES:]),0)
        self.assertNotEqual(pixels[63*128+63],240)  # original-alpha nebula occludes stars
        self.assertNotEqual(pixels[63*128+63],255)
        self.assertEqual(pixels[16384:16384+576],bytes(576))  # black lit/moon art remains solid
        legacy=b'AWN1'+raw[4:12]+struct.pack('<I',fnv1a(pixels[:ART_BYTES]))+pixels[:ART_BYTES]
        self.assertEqual(validate(legacy,self.palette),pixels[:ART_BYTES])
        with self.assertRaises(ValueError):validate(b'AWN2'+legacy[4:],self.palette)

    def test_tracked_legacy_warns_without_owned_and_upgrades_with_original_inputs(self):
        raw=build_atlas(self.images(),self.palette)
        art=raw[16:16+ART_BYTES]
        legacy=b'AWN1'+raw[4:12]+struct.pack('<I',fnv1a(art))+art
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);id1=root/'id1';gfx=id1/'gfx';gfx.mkdir(parents=True)
            (gfx/'palette.lmp').write_bytes(self.palette)
            target=gfx/'aw_night_sky.lmp';marker=gfx/'night-sky.json';target.write_bytes(legacy)
            old={'sha256':hashlib.sha256(legacy).hexdigest(),'palette_sha256':hashlib.sha256(self.palette).hexdigest(),
                 'path':'gfx/aw_night_sky.lmp','bytes':len(legacy),'night_sky':True}
            marker.write_text(json.dumps(old));old_marker=marker.read_bytes()
            fallback=prepare_night_sky(id1,None,root/'no-owned')
            self.assertEqual(fallback['status'],'legacy_fallback_warning')
            self.assertEqual(target.read_bytes(),legacy)
            self.assertFalse((root/'no-owned').exists())
            with patch('build_night_sky.owned_images',return_value=(self.images(),[])) as read:
                report=prepare_night_sky(id1,root/'owned',root/'upgrade')
                read.assert_called_once()
            self.assertTrue(report['upgraded_legacy_atlas'])
            self.assertEqual(target.read_bytes()[:4],b'AWN2')
            self.assertEqual((root/'upgrade/before-legacy/aw_night_sky.lmp').read_bytes(),legacy)
            self.assertEqual((root/'upgrade/before-legacy/night-sky.json').read_bytes(),old_marker)
            self.assertEqual(prepare_night_sky(id1,None,root/'reuse')['status'],'verified_reuse')

    def test_all_source_corners_are_visible_dome_cells_and_strongest_original_wins(self):
        images=self.images()
        stars=images['tx_stars']=Image.new('RGBA',(512,512))
        for xy in ((0,0),(511,0),(0,511),(511,511)):
            stars.putpixel(xy,(240,240,240,255))
        stars.putpixel((1,0),(100,100,100,255))
        pixels=validate(build_atlas(images,self.palette),self.palette)
        marked=[i for i in range(16384) if pixels[ART_BYTES+i//8] & (1 << (i&7))]
        self.assertEqual(len(marked),4)
        for i in marked:
            self.assertLess(abs(i%128-63)+abs(i//128-63),63)
            self.assertEqual(pixels[i],240)
        self.assertTrue(all(pixels[y*128+x]==255 for y in range(128) for x in range(128)
                            if abs(x-63)+abs(y-63)>=63))

    def test_original_alpha_is_not_lifted_and_moon_pixels_stay_independent(self):
        images=self.images()
        images['tx_stars_nebula']=Image.new('RGBA',(128,128),(160,80,48,128))
        base=Image.alpha_composite(Image.new('RGBA',(1,1),(9,10,16,255)),
                                   Image.new('RGBA',(1,1),(160,80,48,128))).getpixel((0,0))
        expected=min(range(255),key=lambda i:sum((i-v)**2 for v in base[:3]))
        before=build_atlas(images,self.palette)
        self.assertEqual(validate(before,self.palette)[63*128+63],expected)
        images['tx_stars']=Image.new('RGBA',(512,512),(255,255,255,255))
        images['tx_stars_nebula']=Image.new('RGBA',(128,128),(0,0,0,0))
        after=build_atlas(images,self.palette)
        self.assertEqual(before[16+16384:16+ART_BYTES],after[16+16384:16+ART_BYTES])

    def test_stale_awn2_revision_warns_without_owned_and_upgrades_with_inputs(self):
        raw=build_atlas(self.images(),self.palette)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);gfx=root/'id1/gfx';gfx.mkdir(parents=True)
            (gfx/'palette.lmp').write_bytes(self.palette)
            target=gfx/'aw_night_sky.lmp';target.write_bytes(raw)
            marker=gfx/'night-sky.json'
            old={'sha256':hashlib.sha256(raw).hexdigest(),'palette_sha256':hashlib.sha256(self.palette).hexdigest(),
                 'path':'gfx/aw_night_sky.lmp','bytes':len(raw),'conversion_revision':'obsolete'}
            marker.write_text(json.dumps(old));saved_marker=marker.read_bytes()
            report=prepare_night_sky(root/'id1',None,root/'no-owned')
            self.assertEqual(report['status'],'legacy_fallback_warning')
            self.assertTrue(report['stale_conversion'])
            self.assertEqual(marker.read_bytes(),saved_marker)
            self.assertEqual(target.read_bytes(),raw)
            self.assertFalse((root/'no-owned').exists())
            with patch('build_night_sky.owned_images',return_value=(self.images(),[])):
                report=prepare_night_sky(root/'id1',root/'owned',root/'upgrade')
            self.assertEqual(report['conversion_revision'],CONVERSION_REVISION)
            self.assertEqual(report['upgraded_from_atlas_version'],'AWN2')
            self.assertEqual((root/'upgrade/before-legacy/night-sky.json').read_bytes(),saved_marker)
            self.assertEqual(prepare_night_sky(root/'id1',None,root/'reuse')['status'],'verified_reuse')
