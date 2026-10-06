# SPDX-License-Identifier: GPL-3.0-only
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prepare_harvest import prepare, identity_key, stage_pickup_sound, PICKUP_SOURCE, PICKUP_PATH
from world_flora import inventory
from world_flora_policy import source_key
from player_hull import lumps, pack_lumps
from test_replace_bsp_world import fixture
from test_world_flora_integration import record, sub


def source(script='', owner=False, count=2, contents='levelled', extra=b''):
    raw = record('CONT', sub('NAME', b'plant\0') + sub('FNAM', b'Luminous Russula\0') + sub('MODL', b'f/flora_bc_mushroom_01.nif\0') +
                 sub('FLAG', struct.pack('<I', 11)) + sub('CNDT', struct.pack('<f', 0)) +
                 sub('SCRI', script.encode() + b'\0') + sub('NPCO', struct.pack('<i32s', count, contents.encode())))
    raw += record('INGR', sub('NAME', b'ingredient\0') + sub('FNAM', b'Original ingredient name\0'))
    raw += record('LEVI', sub('NAME', b'levelled\0') + sub('DATA', struct.pack('<I', 1)) + sub('NNAM', bytes([10])) +
                  sub('INDX', struct.pack('<I', 1)) + sub('INAM', b'ingredient\0') + sub('INTV', struct.pack('<H', 1)))
    raw += record('CELL', sub('DATA', struct.pack('<Iii', 0, -2, -10)) + sub('FRMR', struct.pack('<I', 42)) +
                  sub('NAME', b'plant\0') + sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0)) +
                  (sub('ANAM', b'owner\0') if owner else b''))
    return raw + extra


def inputs(raw):
    census = inventory(raw, ('small_mushroom',));refs = census['references']
    refs = [{**r, 'source_key': source_key(r, census['master_sha256'])} for r in refs]
    data = lumps(fixture(inline=True))
    data[0] = bytearray(b'{\n"classname" "worldspawn"\n}\n{\n"classname" "func_wall"\n"aw_ref" "42"\n"model" "*1"\n"origin" "1 2 3"\n"angles" "0 0 0"\n}\n\0')
    bsp = pack_lumps(data)
    return {'name': 'vf0000', 'sha256': hashlib.sha256(bsp).hexdigest(), 'source_references': refs}, bsp


class HarvestPreparationTests(unittest.TestCase):
    def cue(self, folder):
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as wav:
            wav.setparams((1,1,11025,0,'NONE','not compressed'));wav.writeframes(b'\x80'*11)
        raw=buffer.getvalue();path=folder/PICKUP_PATH;path.parent.mkdir(parents=True);path.write_bytes(raw)
        row=dict(source=PICKUP_SOURCE,category='effects',status='included',path=PICKUP_PATH,
                 bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),source_sha256='a'*64,frames=11,rate=11025)
        (folder/'media').mkdir();(folder/'media/catalogue.json').write_text(json.dumps({'entries':[row]}))
        return row,raw

    def test_pickup_sound_verified_staging_and_missing_warning(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);media=root/'media';out=root/'out';row,raw=self.cue(media)
            result=stage_pickup_sound(media,out)
            self.assertEqual(result['status'],'staged_verified');self.assertEqual(result['packaged'],'not_verified')
            self.assertEqual((out/PICKUP_PATH).read_bytes(),raw)
            with self.assertRaises(FileExistsError):stage_pickup_sound(media,out)
            missing=stage_pickup_sound(None,root/'absent')
            self.assertEqual(missing['status'],'missing_output');self.assertIn('warning',missing)
            self.assertFalse((root/'absent').exists())

    def test_pickup_sound_rejects_stale_output_wrong_category_and_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);media=root/'media';row,raw=self.cue(media);catalogue=media/'media/catalogue.json'
            for rows in ([dict(row,category='voices')],[row,row],[dict(row,sha256='b'*64)],[dict(row,frames=12)]):
                catalogue.write_text(json.dumps({'entries':rows}))
                result=stage_pickup_sound(media,root/'out')
                self.assertEqual(result['status'],'missing_output');self.assertIn('warning',result)
                self.assertFalse((root/'out').exists())
            catalogue.write_text(json.dumps({'entries':[row]}));(media/PICKUP_PATH).write_bytes(raw[:-1])
            self.assertEqual(stage_pickup_sound(media,root/'out')['status'],'missing_output')

    def test_original_contents_full_identity_and_brush_binding(self):
        raw = source();region, bsp = inputs(raw);payload, receipt = prepare(raw, region, bsp)
        self.assertTrue(payload.startswith(b'AWH3 2 2 1 1 '))
        self.assertTrue(payload.rstrip().endswith(b'Luminous Russula'))
        self.assertIn(b'\tOriginal ingredient name\n',payload)
        self.assertEqual(receipt['nodes'][0]['chance'], 10)
        self.assertEqual(receipt['nodes'][0]['flags'], 1)
        self.assertEqual(receipt['edges'][-1], (0, 0, 2))
        p = receipt['placements'][0]
        self.assertEqual(len(p['key']), 57)
        self.assertEqual(p['source_key'], region['source_references'][0]['source_key'])
        self.assertEqual(p['container_state']['flags'], 11)
        self.assertEqual(receipt['respawn'], 'disabled_first_stage')

    def test_source_identity_separates_master_cell_and_frmr(self):
        values = [('a'*64, 'exterior', (-2, -10), 42), ('b'*64, 'exterior', (-2, -10), 42),
                  ('a'*64, 'exterior', (-3, -10), 42), ('a'*64, 'exterior', (-2, -10), 43)]
        self.assertEqual(len({identity_key(v) for v in values}), 4)

    def test_rejects_script_ownership_restock_and_changed_contents(self):
        for kwargs in ({'script':'script'}, {'owner':True}, {'count':-2}):
            with self.subTest(kwargs=kwargs):
                raw=source(**kwargs);region,bsp=inputs(raw)
                with self.assertRaises(ValueError):prepare(raw,region,bsp)
        raw=source();region,bsp=inputs(raw);region['source_references'][0]['container_state']['items'][0]['count']=9
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):prepare(raw,region,bsp)

    def test_rejects_stale_bsp_and_duplicate_placement(self):
        raw=source();region,bsp=inputs(raw)
        with self.assertRaisesRegex(ValueError,'does not match'):prepare(raw,region,bsp+b'bad')
        region['source_references'] *= 2
        with self.assertRaisesRegex(ValueError,'Duplicate'):prepare(raw,region,bsp)

    def test_existing_unsupported_items_are_not_treated_as_missing(self):
        raw=source(contents='weapon',extra=record('WEAP',sub('NAME',b'weapon\0')));region,bsp=inputs(raw)
        with self.assertRaisesRegex(ValueError,'Only original ingredients'):prepare(raw,region,bsp)
        raw=source(contents='missing');region,bsp=inputs(raw);_,receipt=prepare(raw,region,bsp)
        self.assertEqual(receipt['nodes'][0]['kind'],2)

    def test_nested_lists_keep_outer_each_and_reject_cycles(self):
        inner=record('LEVI',sub('NAME',b'outer\0')+sub('DATA',struct.pack('<I',3))+sub('NNAM',b'\0')+
                     sub('INDX',struct.pack('<I',1))+sub('INAM',b'levelled\0')+sub('INTV',struct.pack('<H',1)))
        raw=source(contents='outer',extra=inner);region,bsp=inputs(raw);_,receipt=prepare(raw,region,bsp)
        self.assertEqual(len(receipt['nodes']),3);self.assertEqual(receipt['nodes'][0]['flags'],3)
        raw=raw.replace(b'levelled\0',b'outerxxx\0')
        # Use a direct self-reference rather than malformed lengths.
        cycle=record('LEVI',sub('NAME',b'outer\0')+sub('DATA',struct.pack('<I',1))+sub('NNAM',b'\0')+
                     sub('INDX',struct.pack('<I',1))+sub('INAM',b'outer\0')+sub('INTV',struct.pack('<H',1)))
        raw=source(contents='outer',extra=cycle);region,bsp=inputs(raw)
        with self.assertRaisesRegex(ValueError,'Cyclic'):prepare(raw,region,bsp)


if __name__=='__main__':unittest.main()
