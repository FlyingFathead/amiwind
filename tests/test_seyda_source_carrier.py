"""Direct original-source carrier parity; no original assets, compiler or emulator."""
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]
import prepare_seyda_source as source
import prepare_mesh_bsp as mesh
import prepare_opening_refs as opening
import chim_town
from compact_bsp import entities
from player_hull import pack_lumps, lumps
from chim.frame_map import empty_world, entity_text, model_bounds
from prepare_quake import CENTRE, SCALE

BARREL = 172851
MAP = '''{
"classname" "worldspawn"
"message" "AmiWind / Seyda Neen"
"wad" "town.wad"
{
( 0 0 0 ) ( 0 1 0 ) ( 1 0 0 ) g0 0 0 0 1 1
}
}
{
"classname" "aw_static"
"model" "progs/m000.mdl"
"origin" "0 0 0"
"angles" "0 0 0"
}
{
"classname" "aw_static"
"model" "progs/m001.spr"
"origin" "300 -200 0"
"angles" "0 0 0"
}
{
"classname" "info_player_start"
"origin" "16.0 44.0 74.0"
"angle" "90"
}
'''


def fixture(root):
    alias=root/'alias';scenery=root/'scenery';alias.mkdir();scenery.mkdir()
    (alias/'seyda.map').write_text(MAP)
    # Prepared canonical input includes an offset surface outside the raw box:
    # deriving bounds from original AABBs alone would miss it.
    polygon=np.array([[0.,0.,0.],[32.,0.,0.],[32.,32.,0.],[0.,32.,0.]])
    v=np.column_stack((polygon*4,np.zeros((4,2))))
    data=(v,np.array([[0,1,3,0]]),
          [(polygon+np.array([0.,0.,40.]),0,np.array([[1/64,0],[0,1/64],[0,0.]]),
            np.array([0.,0.]),np.array([0.,0.,1.]))],[],{})
    refs=[]
    for number,pos,rotation,scale in [(BARREL,[120,-45,46],[0.,0.,0.],1.),
                                     (4242,[-500,-500,0],[.2,-.3,1.1],1.7)]:
        world=[CENTRE[0]+pos[0]/SCALE,CENTRE[1]+pos[1]/SCALE,pos[2]/SCALE]
        refs.append(dict(number=number,id='chargen barrel fatigue' if number==BARREL else 'static',
                         type='CONT' if number==BARREL else 'STAT',model_index=0,scale=scale,
                         position=world,rotation_radians=rotation,
                         bounds=[[world[0]-256,world[1]-256,world[2]-256],
                                 [world[0]+256,world[1]+256,world[2]+256]]))
    index=dict(models=[dict(source='meshes/x/source.nif',triangles=2,
                           materials=[dict(texture_index=None,diffuse=[1,1,1])])],
               textures=[],references=refs,errors=[],groups={})
    (scenery/'scenery-index.json').write_text(json.dumps(index));(scenery/'scenery.mwpak').write_bytes(b'')
    return alias,scenery,index,data


class DirectSourceTests(unittest.TestCase):
    def seed(self,alias,scenery,index,data,**kwargs):
        with patch.object(mesh,'_prepare_model',side_effect=lambda task:(task[0],data)):
            return source.seed(alias,scenery,index['references'][0],**kwargs)

    def test_world_brushes_never_become_runtime_geometry_and_sprite_is_retained(self):
        rows=source.source_points(MAP)
        self.assertEqual([r['classname'] for r in rows],['worldspawn','aw_static','info_player_start'])
        self.assertEqual(rows[1]['model'],'progs/m001.spr')
        self.assertEqual(rows[0]['aw_source_carrier'],source.MARKER)
        self.assertNotIn('wad',rows[0])
        from player_hull import PROFILE
        self.assertEqual(rows[0]['aw_hull'],PROFILE)
        for bad in [MAP+'}',MAP.replace('"message"','"classname"',1),
                    MAP.replace('"classname" "worldspawn"','"classname" "func_wall"',1)]:
            with self.subTest(bad=bad[:30]),self.assertRaises(ValueError):source.source_points(bad)

    def test_real_normal_writer_and_direct_metadata_match_every_placed_transform_and_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alias,scenery,index,data=fixture(root)
            raw,report=self.seed(alias,scenery,index,data)
            parts=lumps(raw);self.assertFalse(any(parts[k] for k in (3,7,8)))
            self.assertFalse(report['runtime_payload']);self.assertFalse(report['terrain_compiled'])
            self.assertEqual({r['number'] for r in report['references']},{BARREL,4242})
            plain=empty_world((-1024,-1024,-100),(1024,1024,500))
            plain[0]=entity_text(source.source_points(MAP));(root/'base.bsp').write_bytes(pack_lumps(plain))
            (root/'palette.lmp').write_bytes(bytes(range(256))*3)
            with patch('subprocess.run',side_effect=AssertionError('compiler forbidden')):
                mesh.append_meshes(root/'base.bsp',root/'normal.bsp',scenery,root/'palette.lmp',
                                   centre=CENTRE,jobs=1,references=[BARREL,4242],prepared_models={0:data})
            normal=(root/'normal.bsp').read_bytes()
            def records(raw):
                return {r['aw_ref']:(r['origin'],r['angles'],model_bounds(raw,int(r['model'][1:])))
                        for r in entities(lumps(raw)[0]) if r.get('classname')=='func_wall'}
            self.assertEqual(records(raw),records(normal))
            # Both paths must keep the additional surface's extent, not just source vertices.
            self.assertGreater(records(raw)[str(BARREL)][2][1][2],32)
            # Reuse real region/special predicates and original activation extraction.
            actual,entries,models=chim_town.seyda_maps(raw)
            expected,_,_=chim_town.seyda_maps(normal)
            self.assertEqual(actual,expected)
            refs={r['number']:None for r in index['references']}
            names=[e['name'] for e in entries[:-2]]
            self.assertEqual(chim_town.seyda_static_check(actual,names,refs,{})[0],[])
            a,refused=chim_town.seyda_activated(actual,models,names)
            self.assertEqual(refused,[]);self.assertEqual([r['aw_ref'] for r in a],[str(BARREL)])
            self.assertEqual(a[0]['_box'],[list(v) for v in records(raw)[str(BARREL)][2]])

    def test_duplicate_nonfinite_and_wrong_model_reference_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alias,scenery,index,data=fixture(root)
            for edit in ['duplicate','nan','model','identity']:
                wrong=copy.deepcopy(index)
                if edit=='duplicate':wrong['references'].append(wrong['references'][0])
                elif edit=='nan':wrong['references'][0]['rotation_radians'][1]=float('nan')
                elif edit=='model':wrong['references'][0]['model_index']=99
                else:wrong['references'][0].pop('type')
                (scenery/'scenery-index.json').write_text(json.dumps(wrong))
                with self.subTest(edit=edit),self.assertRaises(ValueError):self.seed(alias,scenery,index,data)

    def test_missing_original_barrel_requires_exact_fresh_opening_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alias,scenery,index,data=fixture(root)
            barrel=index['references'][0];index['references']=index['references'][1:]
            (scenery/'scenery-index.json').write_text(json.dumps(index))
            with patch.object(mesh,'_prepare_model',return_value=(0,data)):
                with self.assertRaisesRegex(ValueError,'opening source'):source.seed(alias,scenery,barrel)
                extra=root/'opening';extra.mkdir();ei=copy.deepcopy(index);ei['references']=[copy.deepcopy(barrel)]
                (extra/'scenery-index.json').write_text(json.dumps(ei));(extra/'scenery.mwpak').write_bytes(b'')
                raw,record=source.seed(alias,scenery,barrel,extra)
                self.assertEqual({r['number'] for r in record['references']},{BARREL,4242})
                ei['references'][0]['position'][0]+=1
                (extra/'scenery-index.json').write_text(json.dumps(ei))
                with self.assertRaisesRegex(ValueError,'differs from original'):source.seed(alias,scenery,barrel,extra)

    def test_direct_route_calls_existing_canonical_stages_in_palette_order_without_append(self):
        import prepare_seyda_carrier as carrier
        from test_seyda_carrier import hand_report
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alias=root/'alias';(alias/'id1/gfx').mkdir(parents=True)
            (alias/'id1/progs').mkdir();base=bytes([1])*768;ui=bytes([2])*768;final=bytes([3])*768
            (alias/'id1/gfx/palette.lmp').write_bytes(base)
            hand=hand_report();h=root/'hand.json';h.write_text(json.dumps(hand))
            catalog=dict(clips=hand['clips'],scene_palette_sha256=carrier.digest(ui),palette_sha256=carrier.digest(final))
            c=root/'catalog.json';c.write_text(json.dumps(catalog));out=root/'output';events=[]
            parts=empty_world((-10,-10,-10),(10,10,10))
            parts[0]=entity_text([{'classname':'worldspawn','aw_source_carrier':source.MARKER}])
            seed=pack_lumps(parts);metadata=dict(format=source.FORMAT,runtime_payload=False)
            def reserve(data,id1):
                self.assertEqual((id1/'gfx/palette.lmp').read_bytes(),base)
                (id1/'gfx/palette.lmp').write_bytes(ui);events.append('reserve');return {}
            def actors(*args,**kwargs):
                self.assertEqual(args[5],base);events.append('actors');return {}
            def populate(data,path,**kwargs):
                self.assertEqual((path/'id1/gfx/palette.lmp').read_bytes(),ui)
                self.assertEqual(kwargs['rooms'],{});self.assertFalse(kwargs['doors'])
                events.append('populate');return {}
            def bind(data,path,**kwargs):
                self.assertEqual(kwargs,{'allow_append':False});events.append('opening');return {}
            with patch.object(carrier,'resolve_data_files',return_value=root), \
                 patch.object(carrier,'child_ci',return_value=root/'master'), \
                 patch.object(carrier,'file_digest',return_value='fixture-hash'), \
                 patch.object(carrier,'load_master',return_value=({},[],{})), \
                 patch.object(carrier,'read_interior',return_value={'flags':1,'refs':[]}), \
                 patch.object(carrier,'reserved_palette',return_value=(ui,{})), \
                 patch.object(carrier,'runtime_palette',return_value=final), \
                 patch.object(opening,'opening_references',return_value=([],[{'id':opening.BARREL}],set())), \
                 patch.object(source,'seed',return_value=(seed,metadata)), \
                 patch.object(carrier,'populate_intro_actors',side_effect=actors), \
                 patch.object(carrier,'reserve',side_effect=reserve), \
                 patch.object(carrier,'populate',side_effect=populate), \
                 patch.object(carrier,'bind_opening',side_effect=bind):
                record=carrier.prepare(root,alias,out,h,c,scenery=root/'scenery')
            self.assertEqual(events,['actors','reserve','populate','opening'])
            self.assertTrue(record['source_only']);self.assertFalse(record['regional_bsp_compilation'])
            self.assertFalse((alias/'id1/maps').exists())
            self.assertEqual((out/'seyda.bsp').read_bytes(),(out/'id1/maps/seyda.bsp').read_bytes())
            self.assertEqual((alias/'id1/gfx/palette.lmp').read_bytes(),base)

    def test_import_of_carrier_entries_never_starts_conversion_or_writes(self):
        import runpy
        with patch('subprocess.run',side_effect=AssertionError('unexpected subprocess')), \
             patch.object(Path,'write_bytes',side_effect=AssertionError('unexpected output')), \
             patch.object(Path,'write_text',side_effect=AssertionError('unexpected output')):
            runpy.run_path(str(ROOT/'tools/prepare_seyda_carrier.py'),run_name='carrier_import_check')
            runpy.run_path(str(ROOT/'tools/prepare_seyda_source.py'),run_name='source_import_check')

    def test_model_box_rejects_nonfinite_or_reversed_bounds(self):
        for low,high in [([0,0,0],[1,1,float('nan')]),([2,0,0],[1,1,1])]:
            with self.assertRaises(ValueError):source.model_row(low,high)

    def test_missing_barrel_no_append_fails_before_entity_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'id1/maps').mkdir(parents=True)
            parts=empty_world((-10,-10,-10),(10,10,10));parts[0]=entity_text([{'classname':'worldspawn'}])
            raw=pack_lumps(parts);path=root/'id1/maps/seyda.bsp';path.write_bytes(raw)
            barrel=dict(number=BARREL,id=opening.BARREL,type='CONT',position=[*CENTRE,0])
            with patch.object(opening,'resolve_data_files',return_value=root), \
                 patch.object(opening,'opening_references',return_value=([barrel],[barrel],{'ship'})), \
                 patch.object(opening,'append_meshes',side_effect=AssertionError('geometry append forbidden')):
                with self.assertRaisesRegex(ValueError,'append refused'):opening.prepare(root,root,allow_append=False)
            self.assertEqual(path.read_bytes(),raw)

    def test_marked_transport_requires_exact_receipts_but_legacy_path_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alias,scenery,index,data=fixture(root);raw,record=self.seed(alias,scenery,index,data)
            source_raw=(json.dumps(record)+'\n').encode();(root/'source-entities.json').write_bytes(source_raw)
            receipt=dict(source_only=True,carrier_bsp_sha256=hashlib.sha256(raw).hexdigest(),
                         source_entities_sha256=hashlib.sha256(source_raw).hexdigest())
            (root/'seyda-carrier.json').write_text(json.dumps(receipt))
            self.assertEqual(chim_town.source_carrier_record(root,raw),receipt)
            parts=lumps(raw);parts[7]=b'geometry';wrong=pack_lumps(parts)
            receipt['carrier_bsp_sha256']=hashlib.sha256(wrong).hexdigest()
            (root/'seyda-carrier.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'Invalid'):chim_town.source_carrier_record(root,wrong)
            (root/'source-entities.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Invalid'):chim_town.source_carrier_record(root,raw)
            parts[7]=b'';parts[0]=entity_text([{'classname':'worldspawn'}])
            self.assertIsNone(chim_town.source_carrier_record(root,pack_lumps(parts)))


if __name__=='__main__':
    unittest.main()
