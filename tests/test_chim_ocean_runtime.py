# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic ocean admission, routing, translated terrain seams and mixed format0.7 worlds."""
import copy
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools'), str(ROOT/'tests')]
from chim import regions as R
from chim import ocean_runtime as O
from chim import format as F
from chim.world import build_frames
from chim.validate import Failures, load_world
from chim.terrain import terrain_unit
from chim.build import local_terrain_task


def sub(tag, data):
    return tag.encode()+struct.pack('<I', len(data))+data


def rec(tag, data, flags=0):
    return tag.encode()+struct.pack('<III',len(data),0,flags)+data


def cell(x,y,refs=()):
    raw=sub('NAME',b'\0')+sub('DATA',struct.pack('<Iii',0,x,y))
    for n,ident,pos in refs:
        raw+=sub('FRMR',struct.pack('<I',n))+sub('NAME',ident.encode()+b'\0')
        raw+=sub('DATA',struct.pack('<6f',*pos,0,0,0))
    return rec('CELL',raw)


class Admission(unittest.TestCase):
    def test_original_leveled_reference_is_preserved_with_expansion_hash(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'Morrowind.esm').write_bytes(b'')
            (p/'Bloodmoon.esm').write_bytes(rec('LEVC',sub('NAME',b'horker\0'))+cell(-19,14,[(33410,'horker',[-153000,119000,-1300])]))
            a=O.admit_cell(p,[-19,14]);r=a['references'][0]
            self.assertEqual((r['number'],r['id'],r['type'],r['status'],r['master']),(33410,'horker','LEVC','deferred','Bloodmoon.esm'))
            self.assertEqual(a['records'],dict(placed=1,converted=0,deferred=1,failed=0,skipped=0))
            old=a['masters'][-1]['sha256'];(p/'Bloodmoon.esm').write_bytes((p/'Bloodmoon.esm').read_bytes()+rec('JUNK',b'x'))
            self.assertNotEqual(O.admit_cell(p,[-19,14])['masters'][-1]['sha256'],old)

    def test_land_visible_or_unknown_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'Morrowind.esm'
            for raw in [rec('LAND',sub('INTV',struct.pack('<ii',-19,14))),
                        rec('STAT',sub('NAME',b'rock\0'))+cell(-19,14,[(1,'rock',[-153000,119000,0])]),
                        cell(-19,14,[(1,'unknown',[-153000,119000,0])])]:
                p.write_bytes(raw)
                with self.assertRaises(ValueError):O.admit_cell(p.parent,[-19,14])

    def test_truncated_master_and_noninteger_cell_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'Morrowind.esm').write_bytes(b'broken')
            for xy in [[-19,14],[-19.0,14],[True,14]]:
                with self.assertRaises(ValueError):O.admit_cell(t,xy)

    def test_empty_no_land_cell_is_not_invented_as_a_placed_reference(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'Morrowind.esm').write_bytes(b'')
            a=O.admit_cell(t,[-6,26]);self.assertEqual(a['references'],[]);self.assertEqual(a['by_type'],{})
            self.assertFalse(a['native_verified']);self.assertFalse(a['packaged'])


class Ownership(unittest.TestCase):
    def test_explicit_ocean_only_and_exact_stage_kind_survives_roundtrip(self):
        status={(-19,14):dict(status='ocean',legacy_maps=[])}
        kept,problems,dropped=R.preflight([(-19,14)],{(-19,14)},status,{})
        self.assertEqual((kept,problems,dropped),([(-19,14)],[],[]))
        self.assertEqual(R.preflight([(-19,14)],set(),status,{})[0],[])
        kinds={(-19,14):'ocean'};self.assertEqual(R.decode_cells(R.encode_cells(kinds)),kinds)
        table=R.ownership(kinds);self.assertEqual(R.check_table(table),[])
        self.assertEqual(R.kind_summary(table['counts']),'0 seabed, 0 land, 1 ocean')
        self.assertEqual(R.kind_summary(dict(seabed=1,land=2)),'1 seabed, 2 land')
        s=R.frame_settings(table['frames'][0]);self.assertTrue(s['ocean_runtime']);self.assertEqual(s['missing_land'],'flat')
        self.assertEqual(s['centre'],[-151552,118784])

    def test_appended_rows_keep_names_negative_grid_and_adjacent_single_owners(self):
        old=[dict(name='vf0000',cell=[0,0],origin=[1024,1024,0],core=[[-1024,-1024],[1024,1024]],coverage=[[-1920,-1920],[1920,1920]])]
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'Morrowind.esm').write_bytes(b'')
            rows,added=O.append_routing_rows(old,[(-19,14),(-19,15)],t)
            self.assertEqual(rows[0],old[0]);self.assertEqual([r['name'] for r in added],['vf0001','vf0002'])
            self.assertEqual(added[0]['origin'],[-37888,29696,0])
            for x,y in [(-19,14),(-19,15)]:
                for dx,dy in [(0.001,0.001),(2047.999,2047.999)]:
                    p=(x*2048+dx,y*2048+dy)
                    owners=[r for r in rows if all(r['origin'][k]+r['core'][0][k]<=p[k]<r['origin'][k]+r['core'][1][k] for k in range(2))]
                    self.assertEqual(len(owners),1)
            with self.assertRaises(ValueError):O.append_routing_rows(old,[(0,0)],t)
            self.assertTrue(all(r['converted'] is None for r in added))


class Terrain(unittest.TestCase):
    def test_adjacent_shared_default_floor_water_materials_light_and_hull_are_identical(self):
        from test_chim_terrain_refs import grid_task
        # Compare independent direct terrain with the shared template translated as runtime grafting does.
        tasks=[grid_task(-256,0,lambda x,y:-512),grid_task(0,0,lambda x,y:-512)]
        tasks=[dict(t,materials=[[0,0],[0,0]]) for t in tasks]
        units=[terrain_unit(t) for t in tasks]
        local=terrain_unit(local_terrain_task(tasks[0],-256,0))
        local_image=F.brush_image(local['lumps'])[0]
        for t,u in zip(tasks,units):
            shifted=F.read_brush_image(F.translate_image(local_image,(t['box'][0],0,0)))
            for lump in (5,6,7,9,11,12,13,14):self.assertEqual(shifted[lump],bytes(u['lumps'][lump]))
            self.assertEqual(shifted[10][28:],bytes(u['lumps'][10])[28:])
            # Planes and vertices include both surface positions and normals; compare direct bytes.
            for lump,size in ((1,20),(3,12)):
                aa=list(struct.iter_unpack('<%df' % (size//4),shifted[lump]))
                bb=list(struct.iter_unpack('<%df' % (size//4),bytes(u['lumps'][lump])))
                self.assertEqual(len(aa),len(bb))
                for a,b in zip(aa,bb):
                    for x,y in zip(a,b):self.assertAlmostEqual(x,y,delta=1e-3)
        from chim.ocean import build_ocean,validate_ocean
        from test_chim_ocean import GROUND
        failures,figures=validate_ocean(build_ocean(GROUND)[0]);self.assertEqual(failures,[])
        self.assertEqual((figures['water'],figures['seabed']), (0,-512))

    def test_mixed_inline_and_shared_terrain_reads_without_reconverting_inline_payload(self):
        from test_chim_format import fixture
        specs=[]
        def capture(out,frames,*args,**kw):specs.extend(frames);return {}
        with tempfile.TemporaryDirectory() as t, patch('chim.build.build_frames',side_effect=capture):
            fixture(Path(t),placements=[],settings={'grain':256,'sector_chunks':2},same_ground=True,heights_of=lambda x,y:-512)
            fixture(Path(t),placements=[],settings={'grain':256,'sector_chunks':2,'terrain_refs':'on'},same_ground=True,heights_of=lambda x,y:-512)
        second=specs[1];second['frame']=dict(second['frame'],cell=(-19,14),centre=(-151552,118784))
        from test_chim_terrain_refs import grid_task
        task=grid_task(0,0,lambda x,y:-512)
        task['materials']=[[1,1],[1,1]]
        template=terrain_unit(task)
        second['terrain']={c:dict(template,offset=t['offset']) for c,t in second['terrain'].items()}
        with tempfile.TemporaryDirectory() as t:
            receipt=build_frames(t,specs,settings={'grain':256,'sector_chunks':2})
            fails=Failures();world=load_world(t,fails);self.assertEqual(list(fails),[])
            chunks=[c for _,_,cs in world[5] for c in cs]
            self.assertTrue(any('ref' in c for c in chunks));self.assertTrue(any('ref' not in c for c in chunks))
            self.assertEqual(receipt['world_format'],'0.7');self.assertEqual(receipt['terrain_refs']['records'],1)
            # Shared water/ground textures are content-deduplicated; no double terrain ownership.
            self.assertEqual(receipt['placements'],0)


class Installation(unittest.TestCase):
    def test_new_ocean_owner_installs_without_legacy_bsp_and_default_worlds_stay_unchanged(self):
        from chim import frame_map as FM
        from test_chim_format import fixture
        from test_chim_terrain_refs import grid_task
        from test_chim_regions import awr
        specs=[]
        def capture(out,frames,*args,**kw):specs.extend(frames);return {}
        with tempfile.TemporaryDirectory() as temp, patch('chim.build.build_frames',side_effect=capture):
            fixture(Path(temp),placements=[],same_ground=True,heights_of=lambda x,y:-512)
        spec=specs[0];xy=(-19,14);frame=R.ownership({xy:'ocean'})['frames'][0]
        spec['frame']=dict(cell=xy,centre=(-151552,118784),low=(-1920,-1920),span=(3840,3840),owned=((-1024,-1024),(1024,1024)))
        task=grid_task(0,0,lambda x,y:-512);task['materials']=[[1,1],[1,1]];template=terrain_unit(task)
        spec['terrain']={(x,y):dict(template,offset=(-1920+x*256,-1920+y*256,0)) for y in range(15) for x in range(15)}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=root/'owned';data.mkdir();(data/'Morrowind.esm').write_bytes(b'')
            rows,new=O.append_routing_rows([], [xy], data)
            id1=root/'id1';(id1/'maps').mkdir(parents=True);(id1/'world').mkdir()
            (id1/'world/regions.awr').write_bytes(awr([(e['origin'],sum(e['core'],[]),sum(e['coverage'],[])) for e in rows]))
            out=root/'world';receipt=build_frames(out,[spec],settings={'grain':256,'sector_chunks':3})
            world=FM.load(out)
            result=FM.build_region(id1,frame,out,world=world,rows='game-data',hand_fields={})
            self.assertEqual(result['replaced'],[]);self.assertEqual(result['source'],'game data (no legacy map)')
            self.assertTrue((id1/result['map']).is_file());self.assertFalse((id1/'maps/vf0000.bsp').exists())
            self.assertEqual(receipt['terrain_refs']['records'],1)
            self.assertEqual(len(world['frames'][0][2]),225)

    def test_world_terrain_stage_does_not_send_new_ocean_rows_to_bsp_compiler(self):
        import prepare_world_regions as P
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);survey=root/'survey';survey.mkdir();data=root/'owned';data.mkdir()
            for name in ['Morrowind.esm','Morrowind.bsa']:(data/name).write_bytes(b'')
            for name in ['world-survey.json','terrain-source.npz']:(survey/name).write_bytes(b'')
            scene=root/'scene';(scene/'id1/gfx').mkdir(parents=True);(scene/'id1/gfx/palette.lmp').write_bytes(bytes(768))
            report={'master_sha256':hashlib.sha256(b'').hexdigest(),'bsa_sha256':hashlib.sha256(b'').hexdigest(),'cells':[]}
            town=dict(origin=[0,0,0],core=[[-1,-1],[1,1]])
            with patch.object(P,'plan',return_value=(report,[])),patch.object(P,'terrain_wad',return_value=b''), \
                    patch.object(P,'town_handoffs',return_value=[town,town]),patch('lava.lava_mode',return_value='static'), \
                    patch.object(P,'compile_region',side_effect=AssertionError('Ocean must not compile a BSP')):
                result=P.prepare(survey,data,scene,root/'out',root/'bin',1,chim_cells={(-19,14)},ocean_cells={(-19,14)})
            self.assertEqual(len(result['ocean_routing_rows']),1)
            self.assertTrue(result['regions'][0]['chim_region'])
            self.assertIsNone(result['regions'][0]['converted'])
            raw=(scene/'id1/world/regions.awr').read_bytes();self.assertEqual(struct.unpack_from('<I',raw,4)[0],1)
            self.assertFalse(list((scene/'id1/maps').glob('*.bsp')))


class OriginalTerrain(unittest.TestCase):
    @staticmethod
    def land(x,y,height=-2048,material=1):
        vhgt=struct.pack('<f',height/8)+bytes(4228)
        return rec('LAND',sub('INTV',struct.pack('<ii',x,y))+sub('VHGT',vhgt)+sub('VTEX',struct.pack('<256H',*([material]*256))))

    @staticmethod
    def ltex(texture):
        return rec('LTEX',sub('INTV',struct.pack('<I',0))+sub('NAME',b'ground\0')+sub('DATA',texture.encode()+b'\0'))

    def test_master_local_materials_and_land_override_keep_original_border_samples(self):
        from chim.ocean_terrain import resolve_grids
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/'Morrowind.esm').write_bytes(self.ltex('base.tga')+self.land(0,0)+self.land(1,0,height=-1900))
            (p/'Bloodmoon.esm').write_bytes(self.ltex('snow.tga')+self.land(1,0))
            grids,materials,receipt=resolve_grids(p,{(0,0),(1,0)})
            self.assertEqual(grids[(0,0)]['heights'][0][-1],grids[(1,0)]['heights'][0][0])
            self.assertEqual(grids[(1,0)]['heights'][0][0],-2048)
            self.assertEqual(grids[(0,0)]['materials'][0][0],1)
            self.assertEqual(grids[(1,0)]['materials'][0][0],131073)
            self.assertEqual(materials[131073]['texture'],'snow.tga')
            self.assertEqual(receipt['masters'][-1]['name'],'Bloodmoon.esm')
            self.assertEqual([r['master'] for r in receipt['land_records'] if r['cell']==[1,0]],['Morrowind.esm','Bloodmoon.esm'])

    def test_base_world_map_only_land_keeps_existing_default_height_policy(self):
        from chim.ocean_terrain import resolve_grids
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'Morrowind.esm').write_bytes(rec('LAND',sub('INTV',struct.pack('<ii',11,23))+sub('WNAM',bytes(81))))
            grids,materials,receipt=resolve_grids(p,{(11,23)})
            self.assertEqual((grids,materials),({},{}))
            self.assertEqual(receipt['heightless_base_records'][0]['cell'],[11,23])
            (p/'Bloodmoon.esm').write_bytes(rec('LAND',sub('INTV',struct.pack('<ii',11,23))))
            with self.assertRaises(ValueError):resolve_grids(p,{(11,23)})

    def test_unresolved_or_deleted_expansion_land_is_refused(self):
        from chim.ocean_terrain import resolve_grids
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'Morrowind.esm').write_bytes(self.ltex('base.tga')+self.land(0,0))
            for raw in [self.land(1,0),rec('LAND',sub('INTV',struct.pack('<ii',1,0)),flags=32)]:
                (p/'Bloodmoon.esm').write_bytes(raw)
                with self.assertRaises(ValueError):resolve_grids(p,{(0,0),(1,0)})

    def test_expansion_material_uses_existing_archive_bytes_and_records_dependency(self):
        from chim.ocean_terrain import ground_textures
        from PIL import Image
        import io,hashlib
        raw=io.BytesIO();Image.new('RGB',(4,4),(225,60,30)).save(raw,format='PNG');data=raw.getvalue()
        class Source:
            def read(self,name):
                if name!='textures/snow.dds':raise FileNotFoundError(name)
                return data,'Bloodmoon.bsa'
        materials={131073:dict(texture='snow.tga',master='Bloodmoon.esm',source_index=1,record_sha256='abc')}
        palette=bytes(v for i in range(256) for v in (i,i,i))
        textures,dep=ground_textures('.',materials,palette,source=Source())
        self.assertEqual(list(textures),['g131073']);self.assertEqual(dep[0]['sha256'],hashlib.sha256(data).hexdigest())
        self.assertEqual(dep[0]['archive'],'Bloodmoon.bsa');self.assertEqual(dep[0]['asset'],'textures/snow.dds')

    def test_far_master_merge_is_ocean_only_and_bound_to_admission_hash(self):
        from chim import far
        from chim.ocean_terrain import resolve_grids
        import numpy as np
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'Morrowind.esm').write_bytes(self.ltex('base.tga')+self.land(0,0,height=-1900))
            (p/'Bloodmoon.esm').write_bytes(self.ltex('snow.tga')+self.land(0,0))
            _,_,sources=resolve_grids(p,{(0,0)})
            frames=[dict(cell=[1,1]),dict(cell=[2,2],ocean_runtime=True,ocean_masters=sources['masters'])]
            seen=[]
            def layer(lands,frame,*args):seen.append(float(lands[(0,0)][0][0]));return b'far',{'cell':frame['cell']}
            with patch.object(far,'cells_needed',return_value={(0,0)}),patch.object(far,'layer',side_effect=layer):
                rows=far.write_layers(p/'out',frames,p,boxes={})
            self.assertEqual(seen,[-1900,-2048]);self.assertNotIn('original_terrain_sources',rows[0])
            self.assertEqual(rows[1]['original_terrain_sources']['masters'],sources['masters'])
            frames[1]['ocean_masters']=[]
            with patch.object(far,'cells_needed',return_value={(0,0)}):
                with self.assertRaises(ValueError):far.write_layers(p/'out2',frames,p,boxes={})


if __name__=='__main__':unittest.main()
