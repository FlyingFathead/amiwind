"""Bounded map and journal packets from synthetic owned-data substitutes."""
import json
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_world_ui import journal_assets, quest_labels, map_asset, prepare, validate

def sub(tag,value):return tag.encode()+struct.pack('<I',len(value))+value
def record(tag,payload):return tag.encode()+struct.pack('<III',len(payload),0,0)+payload
def journal(stage,text):return record('INFO',sub('DATA',struct.pack('<iibbbb',4,stage,-1,-1,-1,0))+sub('NAME',text))
class WorldUIAssetsTests(unittest.TestCase):
    def master(self):return record('DIAL',sub('NAME',b'TEST_HelloWorld\0')+sub('DATA',b'\4'))
    def test_prepare_and_validate_with_terrain_directory_present(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=root/'data';survey=root/'survey';scene=root/'scene'
            data.mkdir();survey.mkdir();(scene/'id1/gfx').mkdir(parents=True)
            world=scene/'id1/world';world.mkdir()
            raw=self.master()+journal(1,b'First journal entry\0')
            (data/'Morrowind.esm').write_bytes(raw)
            (scene/'id1/gfx/palette.lmp').write_bytes(bytes(range(256))*3)
            (survey/'world-survey.json').write_text(json.dumps({'master_sha256':hashlib.sha256(raw).hexdigest(),
                'terrain_bounds':[-1,-1,1,1],'areas':[]}))
            Image.new('RGBA',(8,8),(34,66,84,255)).save(survey/'terrain.png')
            region=b'AWR2'+struct.pack('<I',0)+bytes(56)
            (world/'regions.awr').write_bytes(region)
            (world/'other-tool-output').mkdir()
            receipt=prepare(data,survey,scene)
            self.assertEqual(set(receipt['files']),{'map.awm','journal.awj','entries.dat','quests.awq'})
            self.assertEqual(validate(scene/'id1'),receipt)
            self.assertEqual((world/'regions.awr').read_bytes(),region)
            # Re-running on the same private staging tree remains valid.
            self.assertEqual(prepare(data,survey,scene),receipt)
            (world/'entries.dat').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'World UI hash mismatch: entries.dat'):
                validate(scene/'id1')

    def test_sorted_journal_offsets_and_original_identity(self):
        raw=self.master()+journal(10,b'Second\0')+journal(1,b'Hello %PCName.\0')
        index,blob,count=journal_assets(raw)
        self.assertEqual(count,1);self.assertEqual(index[:8],b'AWJ1'+struct.pack('<I',2))
        stages=[]
        for at in (8,84):
            self.assertEqual(index[at:at+64].rstrip(b'\0'),b'test_helloworld')
            stage,offset,size=struct.unpack_from('<iII',index,at+64);stages.append(stage)
            self.assertTrue(blob[offset:offset+size].endswith(b'\0'))
        self.assertEqual(stages,[1,10])
        labels=quest_labels(raw,{})
        self.assertEqual(labels[72:].rstrip(b'\0'),b'Hello World')
    def test_ambiguous_stages_and_oversized_text_fail_closed(self):
        with self.assertRaises(ValueError):journal_assets(self.master()+journal(1,b'one')+journal(1,b'two'))
        with self.assertRaises(ValueError):journal_assets(self.master()+journal(1,b'x'*8192))
        with self.assertRaises(ValueError):journal_assets(self.master()+journal(1,b'bad\0embedded'))
    def test_save_fingerprint_includes_world_and_journal_assets(self):
        from build_aga import write_content_fingerprint
        from area_config import SCENES
        from prepare_seyda_regions import regions as seyda_regions
        from balmora_regions import config, regions
        paths=[*(f"maps/{s['map']}.bsp" for s in SCENES),'maps/intro_docks.bsp','maps/sncourt.bsp',
               'seyda-regions.txt',*(f"maps/{r['name']}.bsp" for r in seyda_regions()),
               'balmora-regions.txt',*(f"maps/{r['name']}.bsp" for r in regions(config())),
               'progs.dat','character/catalog.awc','world/map.awm','world/journal.awj','world/entries.dat','world/quests.awq']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in paths:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(name.encode())
            write_content_fingerprint(root);before=(root/'save-content.bin').read_bytes()
            self.assertEqual(len(before),32)
            (root/'world/entries.dat').write_bytes(b'changed earned text')
            write_content_fingerprint(root);self.assertNotEqual(before,(root/'save-content.bin').read_bytes())
            (root/'world/map.awm').unlink()
            with self.assertRaisesRegex(ValueError,'Required'):write_content_fingerprint(root)

    def test_map_source_bounds_aspect_area_transform_and_ocean_colour(self):
        report={'terrain_bounds':[-2,-3,2,5],'areas':[{'name':'Balmora','centre':[-20,-12],'scale':.25}]}
        palette=bytes(range(256))*3
        raw=map_asset(report,Image.new('RGBA',(128,256),(34,66,84,255)),palette)
        self.assertEqual(raw[:4],b'AWM1');self.assertEqual(struct.unpack_from('<HH',raw,4),(256,512))
        self.assertEqual(struct.unpack_from('<4i',raw,8),(-16384,-24576,16384,40960))
        self.assertEqual(struct.unpack_from('<3f',raw,80),(-20,-12,.25))
        self.assertEqual(set(raw[92:]),{struct.unpack_from('<I',raw,28)[0]})
if __name__=='__main__':unittest.main()
