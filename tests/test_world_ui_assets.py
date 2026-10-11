"""Bounded map and journal packets from synthetic owned-data substitutes."""
import json
import hashlib
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_world_ui import journal_assets, quest_labels, map_asset, region_names, prepare, validate
from prepare_world_ui import (LAVA_RGB, SKY_BANK_INDICES, WORLD_MAPS, WORLD_MAP_VARIABLE, check_lava_layer, export_world_map,
                              lava_colour, lava_layer, lava_section_colour, lava_section_offset)

def sub(tag,value):return tag.encode()+struct.pack('<I',len(value))+value
def record(tag,payload):return tag.encode()+struct.pack('<III',len(payload),0,0)+payload
def journal(stage,text):return record('INFO',sub('DATA',struct.pack('<iibbbb',4,stage,-1,-1,-1,0))+sub('NAME',text))
class WorldUIAssetsTests(unittest.TestCase):
    def master(self):return record('DIAL',sub('NAME',b'TEST_HelloWorld\0')+sub('DATA',b'\4'))
    def test_region_names_follow_original_cell_assignments_and_display_names(self):
        def region(identifier, name):
            return record('REGN', sub('NAME', identifier)+sub('FNAM', name))
        def cell(x, y, region, flags=0, name=b'\0'):
            return record('CELL', sub('NAME',name)+sub('DATA',struct.pack('<Iii',flags,x,y))+sub('RGNN',region))
        raw=(cell(3,0,b'Internal ID\0')+cell(-1,-2,b'OTHER\0',name=b'Test Town\0')+cell(0,0,b'')
             +cell(5,5,b'',name=b'Lone Ruin\0')
             +cell(3,0,b'not-an-exterior-region\0',1,b'Interior Name\0')
             +region(b'Internal ID\0',b'Original Display Name\0')
             +region(b'other\0',b'Second Display Name\0'))
        packet=region_names(raw)
        self.assertEqual(packet[:16],b'ARN2'+struct.pack('<III',2,2,3))
        self.assertEqual(packet[16:80].rstrip(b'\0'),b'Original Display Name')
        self.assertEqual(packet[144:208].rstrip(b'\0'),b'Lone Ruin')
        self.assertEqual(packet[208:272].rstrip(b'\0'),b'Test Town')
        none=0xFFFFFFFF
        self.assertEqual(list(struct.iter_unpack('<iiII',packet[272:])),[(-1,-2,1,1),(3,0,0,none),(5,5,none,0)])
        with self.assertRaisesRegex(ValueError,'missing REGN'):
            region_names(cell(0,0,b'unknown'))
        with self.assertRaisesRegex(ValueError,'Duplicate exterior'):
            region_names(cell(0,0,b'')+cell(0,0,b''))
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
            self.assertEqual(set(receipt['files']),{'map.awm','journal.awj','entries.dat','quests.awq','region-names.awn'})
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
        # A record string ends at its first NUL, as in the game (MWAD-STRING-DECODE-35): no embedded NUL reaches
        # the text, so this entry is read as 'bad'.
        journal_assets(self.master()+journal(1,b'bad\0embedded'))
    def test_save_fingerprint_includes_world_and_journal_assets(self):
        from build_aga import write_content_fingerprint
        from area_config import SCENES
        from prepare_seyda_regions import regions as seyda_regions
        from balmora_regions import config, regions
        paths=[*(f"maps/{s['map']}.bsp" for s in SCENES),'maps/intro_docks.bsp','maps/sncourt.bsp',
               'seyda-regions.txt','balmora-regions.txt',*(f"maps/{r['name']}.bsp" for r in seyda_regions()),
               *(f"maps/{r['name']}.bsp" for r in regions(config())),
               'progs.dat','character/catalog.awc','world/map.awm','world/journal.awj','world/entries.dat','world/quests.awq','world/region-names.awn']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in paths:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(name.encode())
            for filename,entries in [('seyda-regions.txt',seyda_regions()),('balmora-regions.txt',regions(config()))]:
                rows=['AWBR1 '+str(len(entries))+' 96 540 0 0 64 90 0 0 64 90']
                rows.extend(' '.join(map(str,[r['name'],*r['core'][0],*r['core'][1],*r['coverage'][0],*r['coverage'][1]])) for r in entries)
                (root/filename).write_text('\n'.join(rows)+'\n')
            write_content_fingerprint(root);before=(root/'save-content.bin').read_bytes()
            self.assertEqual(len(before),32)
            # Empty optional catalogues preserve the exact pre-harvest stream.
            legacy=hashlib.sha256()
            for name in paths:
                legacy.update(name.encode('ascii')+b'\0'+hashlib.sha256((root/name).read_bytes()).digest())
            self.assertEqual(before,legacy.digest())
            a=root/'harvest-intro_docks.txt';b=root/'harvest-sncourt.txt'
            a.write_bytes(b'AWH2 0 0 0\n')
            write_content_fingerprint(root);one=(root/'save-content.bin').read_bytes()
            self.assertNotEqual(before,one)
            a.write_bytes(b'AWH1 0 0 0\n')
            write_content_fingerprint(root);changed=(root/'save-content.bin').read_bytes()
            self.assertNotEqual(one,changed)
            b.write_bytes(b'AWH2 0 0 0\n')
            write_content_fingerprint(root);two=(root/'save-content.bin').read_bytes()
            self.assertNotEqual(changed,two)
            a.unlink();a.write_bytes(b'AWH1 0 0 0\n')
            write_content_fingerprint(root);self.assertEqual(two,(root/'save-content.bin').read_bytes())
            a.unlink();b.unlink()
            write_content_fingerprint(root);self.assertEqual(before,(root/'save-content.bin').read_bytes())
            (root/'world/entries.dat').write_bytes(b'changed earned text')
            write_content_fingerprint(root);self.assertNotEqual(before,(root/'save-content.bin').read_bytes())
            (root/'world/map.awm').unlink()
            with self.assertRaisesRegex(ValueError,'Required'):write_content_fingerprint(root)

    def test_harvest_fingerprint_rejects_invalid_catalogue_envelopes(self):
        from build_aga import harvest_fingerprint_entries
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'maps').mkdir();(root/'maps/test.bsp').write_bytes(b'map')
            path=root/'harvest-test.txt'
            for raw in (b'',b'AWH3 0 0 0\n',b'AWH2 65 0 0\n',b'AWH2 0 0 25\n',
                        b'AWH2 0 0 0\nextra\n',b'AWH2 0 0 0\0\n',b'\xff',b'x'*65537):
                path.write_bytes(raw)
                with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):harvest_fingerprint_entries(root)
            path.write_bytes(b'AWH2 0 0 0\n')
            self.assertEqual(harvest_fingerprint_entries(root),[(path.name,hashlib.sha256(path.read_bytes()).hexdigest())])
            (root/'maps/test.bsp').unlink()
            with self.assertRaisesRegex(ValueError,'matching map'):harvest_fingerprint_entries(root)
            path.unlink();(root/'harvest-bad name.txt').write_bytes(b'AWH2 0 0 0\n')
            with self.assertRaisesRegex(ValueError,'path'):harvest_fingerprint_entries(root)

    def test_map_source_bounds_aspect_area_transform_and_ocean_colour(self):
        report={'terrain_bounds':[-2,-3,2,5],'areas':[{'name':'Balmora','centre':[-20,-12],'scale':.25}]}
        palette=bytes(range(256))*3
        raw=map_asset(report,Image.new('RGBA',(128,256),(34,66,84,255)),palette)
        self.assertEqual(raw[:4],b'AWM1');self.assertEqual(struct.unpack_from('<HH',raw,4),(256,512))
        self.assertEqual(struct.unpack_from('<4i',raw,8),(-16384,-24576,16384,40960))
        self.assertEqual(struct.unpack_from('<3f',raw,80),(-20,-12,.25))
        self.assertEqual(set(raw[92:]),{struct.unpack_from('<I',raw,28)[0]})
    # ------------------------------------------------------------ world map v2: the lava layer
    def lava_pools(self):
        oval=[[1000+400*math.cos(a*math.pi/12),2000+250*math.sin(a*math.pi/12)] for a in range(24)]
        return [{'cell':[0,0],'hull':[[100,100],[900,100],[900,700],[100,700]]},
                {'cell':[0,0],'hull':oval},
                {'cell':[-1,-1],'position':[-50.4,-60.6,12]}]

    def test_lava_layer_covers_every_pool_inside_its_footprint(self):
        pools=self.lava_pools();rows=lava_layer(pools)
        self.assertEqual(rows[0],{'cell':[0,0],'points':[[100,100],[900,100],[900,700],[100,700]],'bounds':[100,100,900,700],'pool':0})
        self.assertEqual(len(rows[1]['points']),16)          # 24-point oval reduced to the engine limit, inside it
        self.assertEqual(rows[2]['points'],[[-50,-61]])      # a pool known by its position only: one point
        self.assertEqual(check_lava_layer(rows,pools),{'pools':3,'covered':3,'cells':2,'points':21})
        with self.assertRaisesRegex(ValueError,'census'):check_lava_layer(rows[:2],pools)
        moved=[dict(r) for r in rows];moved[0]=dict(rows[0],points=[[100,100],[905,100],[900,700],[100,700]])
        with self.assertRaisesRegex(ValueError,'leaves its pool'):check_lava_layer(moved,pools)
        wrong=[dict(r) for r in rows];wrong[1]=dict(rows[1],cell=[5,5])
        with self.assertRaisesRegex(ValueError,'wrong cell'):check_lava_layer(wrong,pools)

    @staticmethod
    def land(height):
        """A fake master's land: cell (0, 0) with heights height(x, y) at the 65x65 vertices, 128 units apart."""
        return {(0,0):[[float(height(x*128,y*128)) for x in range(65)] for y in range(65)]}

    def test_visible_lava_follows_the_land_not_the_whole_footprint(self):
        import lava_map
        pool={'cell':[0,0],'hull':[[256,256],[1280,256],[1280,1280],[256,1280]],'top':256.0}
        # Land rises eastwards through the pool surface at x = 768: the western half is lava, the eastern half ground.
        land=self.land(lambda x,y:256+(x-768))
        rects=lava_map.visible_rects(pool,land)
        self.assertEqual(rects,[[256,256,768,1280]])
        # Fully buried: no rectangle at all. Fully below the surface: the whole footprint.
        self.assertEqual(lava_map.visible_rects(pool,self.land(lambda x,y:400)),[])
        self.assertEqual(lava_map.visible_rects(pool,self.land(lambda x,y:0)),[[256,256,1280,1280]])
        rows=lava_map.rows_for([pool],land)[0]
        self.assertEqual([r['bounds'] for r in rows],[[256,256,768,1280]])
        self.assertEqual(lava_layer([pool],land)[0]['points'],[[256,256],[768,256],[768,1280],[256,1280]])
        self.assertEqual(lava_layer([pool],self.land(lambda x,y:400)),[])        # a buried pool has no row
        report=check_lava_layer(rows,[pool],land)
        self.assertEqual((report['pools'],report['covered'],report['buried'],report['rects']),(1,1,0,1))
        self.assertEqual(report['overpaint_area'],0)
        buried=check_lava_layer([],[pool],self.land(lambda x,y:400))
        self.assertEqual((report['pools'],buried['covered'],buried['buried']),(1,0,1))

    def test_land_heights_read_from_the_masters_land_records(self):
        import lava_map
        def sub(tag,data):return tag+struct.pack('<I',len(data))+data
        def rec(tag,subs):body=b''.join(subs);return tag+struct.pack('<III',len(body),0,0)+body
        vhgt=struct.pack('<f',32.0)+bytes(4225)+bytes(3)           # every vertex 32 * 8 = 256 units
        raw=rec(b'LAND',[sub(b'INTV',struct.pack('<ii',-1,2)),sub(b'VHGT',vhgt)])
        raw+=rec(b'LAND',[sub(b'INTV',struct.pack('<ii',5,5))])    # no heights: not in the table
        land=lava_map.land_heights(raw)
        self.assertEqual(list(land),[(-1,2)]);self.assertEqual(land[(-1,2)][64][64],256.0)
        self.assertEqual(lava_map.land_height(land,-8192+4000,2*8192+100),256.0)
        self.assertIsNone(lava_map.land_height(land,0,0))          # no land: unknown, never buried
        self.assertFalse(lava_map.buried(land,0,0,100.0));self.assertTrue(lava_map.buried(land,-8000,2*8192+10,256.0))

    def test_lava_layer_audit_fails_on_a_mismatch_with_the_land(self):
        import lava_map
        pool={'cell':[0,0],'hull':[[256,256],[1280,256],[1280,1280],[256,1280]],'top':256.0,'model':'in_lava_1024'}
        land=self.land(lambda x,y:256+(x-768))
        whole=[{'cell':[0,0],'points':[[256,256],[1280,256],[1280,1280],[256,1280]],'bounds':[256,256,1280,1280],'pool':0}]
        with self.assertRaisesRegex(ValueError,r'disagrees with the land in cell \(0, 0\)'):lava_map.audit(whole,[pool],land)
        with self.assertRaisesRegex(ValueError,'disagrees with the land'):check_lava_layer(whole,[pool],land)
        rows=lava_map.rows_for([pool],land)[0];ok=lava_map.audit(rows,[pool],land)
        self.assertEqual(ok['totals']['pools'],1);self.assertLessEqual(ok['totals']['overpaint'],lava_map.OVERPAINT_MAX*ok['totals']['footprint'])
        self.assertEqual(lava_map.audit([],[pool],land and self.land(lambda x,y:400))['totals']['buried'],1)
        # Visible lava left out is a mismatch too.
        with self.assertRaisesRegex(ValueError,'disagrees with the land'):lava_map.audit([],[pool],land)

    def test_lava_colour_avoids_terrain_ocean_and_sky_bank(self):
        from sky_palette_overlay import BANK
        bank=set(BANK)|{t for t,_ in BANK.values()}
        self.assertEqual(set(SKY_BANK_INDICES),bank)
        palette=bytearray(768)
        for i in (95,156,40,41):palette[i*3:i*3+3]=bytes(LAVA_RGB)
        self.assertEqual(lava_colour(bytes(palette),{40}),41)

    def test_map_v1_unchanged_and_v2_appends_the_lava_section(self):
        report={'terrain_bounds':[-2,-3,2,5],'areas':[{'name':'Balmora','centre':[-20,-12],'scale':.25}]}
        palette=bytes(range(256))*3;image=Image.new('RGBA',(128,256),(34,66,84,255))
        v1=map_asset(report,image,palette)
        self.assertEqual(map_asset(report,image,palette,'v1'),v1)
        rows=lava_layer(self.lava_pools());v2=map_asset(report,image,palette,'v2',rows)
        self.assertEqual(v2[:4],b'AWM2');self.assertEqual(v2[4:len(v1)],v1[4:])
        tag,pools,points,colour=struct.unpack_from('<4sIII',v2,len(v1))
        self.assertEqual((tag,pools,points),(b'LAVA',3,21));self.assertEqual(lava_section_colour(v2),colour)
        self.assertNotIn(colour,set(v1[92:])|set(SKY_BANK_INDICES))
        self.assertEqual(struct.unpack_from('<hhHH4i',v2,len(v1)+16),(0,0,4,0,100,100,900,700))
        self.assertEqual(len(v2),len(v1)+16+3*24+21*8)
        self.assertEqual(lava_section_offset(v2),len(v1))
        with self.assertRaises(ValueError):map_asset(report,image,palette,'v3')

    def test_prepare_writes_v2_by_default_and_v1_when_selected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{},clear=False):
            os.environ.pop(WORLD_MAP_VARIABLE,None)
            root=Path(temp);data=root/'data';survey=root/'survey';scene=root/'scene'
            data.mkdir();survey.mkdir();(scene/'id1/gfx').mkdir(parents=True)
            raw=self.master()+journal(1,b'First journal entry\0')
            (data/'Morrowind.esm').write_bytes(raw)
            (scene/'id1/gfx/palette.lmp').write_bytes(bytes(range(256))*3)
            (survey/'world-survey.json').write_text(json.dumps({'master_sha256':hashlib.sha256(raw).hexdigest(),
                'terrain_bounds':[-1,-1,1,1],'areas':[]}))
            Image.new('RGBA',(8,8),(34,66,84,255)).save(survey/'terrain.png')
            receipt=prepare(data,survey,scene,lava_pools=self.lava_pools())
            awm=(scene/'id1/world/map.awm').read_bytes()
            self.assertEqual(awm[:4],b'AWM2');self.assertEqual(receipt['map_format'],'AWM2')
            layer=receipt['lava_layer']          # a master without land: the whole footprints are visible
            self.assertEqual({k:layer[k] for k in ('pools','covered','buried','cells','overpaint_area','colour')},
                             {'pools':3,'covered':3,'buried':0,'cells':2,'overpaint_area':0,'colour':lava_section_colour(awm)})
            self.assertGreater(layer['rects'],3)
            self.assertEqual(validate(scene/'id1'),receipt)
            # The real census reader on a master without lava: an empty layer, still v2.
            self.assertEqual(prepare(data,survey,scene)['lava_layer']['pools'],0)
            os.environ[WORLD_MAP_VARIABLE]='v1'
            receipt=prepare(data,survey,scene,lava_pools=self.lava_pools())
            self.assertEqual((scene/'id1/world/map.awm').read_bytes()[:4],b'AWM1')
            self.assertNotIn('map_format',receipt);self.assertNotIn('lava_layer',receipt)
            self.assertEqual(prepare(data,survey,scene,'v2',self.lava_pools())['map_format'],'AWM2')
            os.environ[WORLD_MAP_VARIABLE]='v9'
            with self.assertRaisesRegex(ValueError,'v1 or v2'):prepare(data,survey,scene)

    def test_world_map_build_option_default_cli_and_config(self):
        import argparse
        from build_font_options import add_font_options, resolve_font_options
        parser=argparse.ArgumentParser();add_font_options(parser)
        r=resolve_font_options(parser.parse_args([]))
        self.assertEqual((r['world_map'],r['world_map_selected_by']),('v2','shipped default'))
        r=resolve_font_options(parser.parse_args(['--world-map','v1']))
        self.assertEqual((r['world_map'],r['world_map_selected_by']),('v1','CLI override'))
        with tempfile.TemporaryDirectory() as temp:
            cfg=Path(temp)/'b.json';cfg.write_text('{"world_map": "v1"}')
            r=resolve_font_options(parser.parse_args(['--build-config',str(cfg)]))
            self.assertEqual((r['world_map'],r['world_map_selected_by']),('v1','build config'))
            cfg.write_text('{"world_map": "v3"}')
            with self.assertRaisesRegex(ValueError,'world_map'):resolve_font_options(parser.parse_args(['--build-config',str(cfg)]))
        import build_font_options
        self.assertEqual(build_font_options.WORLD_MAP_VARIABLE,WORLD_MAP_VARIABLE)
        self.assertEqual(build_font_options.WORLD_MAPS,WORLD_MAPS)
        with patch.dict(os.environ,{}):
            build_font_options.export_world_map('v2');self.assertEqual(os.environ[WORLD_MAP_VARIABLE],'v2')
            with self.assertRaises(ValueError):build_font_options.export_world_map('v0')
            export_world_map('v1');self.assertEqual(os.environ[WORLD_MAP_VARIABLE],'v1')
            with self.assertRaises(ValueError):export_world_map('v0')
if __name__=='__main__':unittest.main()
