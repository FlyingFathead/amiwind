"""Synthetic canonical intro/carrier contracts; no game conversion or emulator."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_intro as intro
import prepare_seyda_carrier as carrier
import hand_metadata
from player_hull import lumps,pack_lumps

def bsp(text):
    parts=[b'' for _ in range(15)];parts[0]=(text+'\0').encode('cp1252')
    return pack_lumps(parts)

def ref(identifier,number,x=0,y=0,z=12,interior=False):
    return {'id':identifier,'number':number,
            'position':[x if interior else intro.CENTRE[0]+x,y if interior else intro.CENTRE[1]+y,z],
            'rotation_radians':[0,0,math.pi/2]}

def hand_report():
    return {'model':'progs/v_nord.mdl','frames':28,'eye_above_origin':16.5,
            'clips':{n:{'first':f,'count':c,'duration':d} for n,f,c,d in
                     [('idle',0,8,2.6),('draw',8,6,.46),('lower',14,4,.26),('punch',18,10,1.06)]}}

def scene(path):
    (path/'id1/maps').mkdir(parents=True);(path/'id1/progs').mkdir()
    for name in ('prison','seyda'):
        raw=bsp('{\n"classname" "worldspawn"\n}\n')
        (path/'id1/maps'/(name+'.bsp')).write_bytes(raw);(path/(name+'.bsp')).write_bytes(raw)
        # the bsp stage publishes Seyda Neen's scene entity list beside its map (BUILD-SEYDA-ENTITY-BUS-48)
        if name=='seyda':
            import seyda_entities;seyda_entities.publish(path,raw)

def record(identifier='guard'):
    return {'model':'progs/'+identifier.replace(' ','_')+'.mdl','appearance':{'name':identifier},
            'idle_step':.125,'walk_step':.25,'talk_displacement':1}

class IntroContracts(unittest.TestCase):
    def setUp(self):
        self.identifier='chargen boat guard 1';self.record=record(self.identifier)
        self.prison={'flags':1,'refs':[ref(self.identifier,1,8,12,16,True)]}
        self.cells=[{'flags':0,'refs':[ref(self.identifier,2,16,20,24),
                                     ref(self.identifier,3,4096,0,12),ref(self.identifier,4,4097,0,12)]}]

    def test_original_default_and_selected_rows_match_reference(self):
        default=intro.intro_actor_rows(self.identifier,4,self.record,self.prison,self.cells)
        selected=intro.intro_actor_rows(self.identifier,4,self.record,self.prison,self.cells,('seyda',))
        self.assertEqual(selected,{'seyda':default['seyda']})
        self.assertEqual(len(default['prison']),1);self.assertEqual(len(default['seyda']),2)
        from actor_grounding import fields as grounding_fields
        expected={}
        # The pre-extraction authored placement/serialization contract.
        for name,cell,r in [('prison',self.prison,self.prison['refs'][0]),
                            *[('seyda',self.cells[0],r) for r in self.cells[0]['refs'][:2]]]:
            interior=bool(cell['flags']&1)
            p=[(r['position'][i]-(intro.CENTRE[i] if not interior and i<2 else 0))*.25 for i in range(3)]
            fields={'classname':'aw_npc','model':self.record['model'],'origin':' '.join(f'{v:.5f}' for v in p),
                    'angles':f"0 {-math.degrees(r['rotation_radians'][2]):.5f} 0",'netname':self.identifier,
                    'aw_intro_role':4,'aw_idle_step':'.1250000','aw_walk_step':'.2500000'}
            fields['aw_idle_step']='0.1250000';fields['aw_walk_step']='0.2500000'
            fields.update(grounding_fields(self.identifier));fields['aw_ref']=r['number']
            text='{\n'+'\n'.join(intro.quote(k)+' '+intro.quote(v) for k,v in fields.items())+'\n}'
            expected.setdefault(name,[]).append(text)
        self.assertEqual(default,expected)
        self.assertIn('"origin" "4.00000 5.00000 6.00000"',selected['seyda'][0])
        self.assertIn('"angles" "0 -90.00000 0"',selected['seyda'][0])

    def test_malformed_duplicate_and_invalid_selection_refused(self):
        for bad in [('missing',),()]:
            with self.assertRaises(ValueError):intro.intro_references(self.identifier,self.prison,self.cells,bad)
        cells=copy.deepcopy(self.cells);cells[0]['refs'].append(cells[0]['refs'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):intro.intro_references(self.identifier,self.prison,cells)
        cells=copy.deepcopy(self.cells);cells[0]['refs'][0]['position'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Malformed'):intro.intro_references(self.identifier,self.prison,cells)

    def test_full_bundle_keeps_ten_default_bakes_selected_has_only_original_seyda_roles(self):
        prison={'flags':1,'refs':[]};cells=[{'flags':0,'refs':[]}];ids=[]
        for number,(identifier,stem,role) in enumerate(intro.INTRO_ACTORS,1):
            if role:
                interior=role<=3
                (prison if interior else cells[0])['refs'].append(ref(identifier,number,8,12,16,interior))
        def actor(task):
            data,palette,identifier,stem,role,appearance=task;ids.append(identifier)
            r=record(identifier);r['model']='progs/'+stem+'.mdl'
            return identifier,role,b'fixture-model',r
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);full=root/'full';selected=root/'selected';scene(full);scene(selected)
            with patch.object(intro,'outfit',return_value={}),patch.object(intro,'_actor',side_effect=actor), \
                 patch.object(intro,'ordered_map',side_effect=lambda fn,tasks,workers:map(fn,tasks)):
                result=intro.populate_intro_actors(root,full,{},cells,prison,bytes(768),1)
                self.assertEqual(len(result),10);self.assertEqual(len(ids),10)
                ids.clear()
                result=intro.populate_intro_actors(root,selected,{},cells,prison,bytes(768),1,
                                                   map_names=('seyda',),include_prototypes=False)
                expected=[a[0] for a in intro.INTRO_ACTORS if a[2]>=4]
                self.assertEqual(ids,expected)
                self.assertNotIn('fargoth',result)
                self.assertEqual((selected/'id1/maps/prison.bsp').read_bytes(),bsp('{\n"classname" "worldspawn"\n}\n'))

    def test_duplicate_rows_fail_before_any_target_bsp_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);scene(root)
            before={n:(root/'id1/maps'/(n+'.bsp')).read_bytes() for n in intro.INTRO_MAPS}
            row='{"classname" "aw_npc" "aw_ref" "17"}'
            with self.assertRaisesRegex(ValueError,'duplicate'):
                intro.append_intro_rows(root,{'prison':[],'seyda':[row,row]})
            for name,raw in before.items():self.assertEqual((root/'id1/maps'/(name+'.bsp')).read_bytes(),raw)

    def test_hand_stamp_matches_prior_valid_full_prepare_bytes(self):
        raw=bsp('{\n"classname" "worldspawn"\n}\n{"classname" "func_wall" "model" "*1"}\n')
        report=hand_report();parts=lumps(raw);text=parts[0].decode('cp1252');end=text.index('}')
        values=''.join('"aw_hand_'+name+'" "'+str(info['duration'])+'"\n' for name,info in report['clips'].items())
        values+='"aw_eye_height" "'+str(report['eye_above_origin'])+'"\n'
        parts[0]=(text[:end]+values+text[end:]).encode('cp1252')
        self.assertEqual(hand_metadata.stamp(raw,hand_metadata.hand_fields(report)),pack_lumps(parts))
        bad=bsp('{"classname" "worldspawn" "aw_hand_idle" "1" "aw_hand_idle" "2"}')
        with self.assertRaisesRegex(ValueError,'Duplicate'):hand_metadata.stamp(bad,hand_metadata.hand_fields(report))
        report['clips']['idle']['duration']=float('nan')
        with self.assertRaises(ValueError):hand_metadata.hand_fields(report)

    def test_carrier_rejects_wrong_timing_and_inherited_interior_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);scene(root);(root/'id1/gfx').mkdir();(root/'id1/gfx/palette.lmp').write_bytes(bytes(768))
            report=hand_report()
            with self.assertRaisesRegex(ValueError,'timing'):carrier.validate_inputs(root,report,{'clips':{}})
            with self.assertRaisesRegex(ValueError,'interior'):carrier.validate_inputs(root,report,{'clips':report['clips']})

    def test_carrier_calls_canonical_operations_in_palette_order_without_rooms(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';scene(source);(source/'id1/maps/prison.bsp').unlink();(source/'prison.bsp').unlink()
            (source/'id1/gfx').mkdir();base=bytes([1])*768;ui=bytes([2])*768;final=bytes([3])*768
            (source/'id1/gfx/palette.lmp').write_bytes(base);out=root/'new'
            report=hand_report();h=root/'hands.json';h.write_text(json.dumps(report))
            catalog={'clips':report['clips'],'scene_palette_sha256':carrier.digest(ui),'palette_sha256':carrier.digest(final)}
            c=root/'catalog.json';c.write_text(json.dumps(catalog));events=[]
            def actors(*args,**kwargs):
                self.assertEqual(args[5],base);self.assertEqual(kwargs['map_names'],('seyda',))
                self.assertFalse(kwargs['include_prototypes']);events.append('actors');return {}
            def reserve(data,id1):
                self.assertEqual((id1/'gfx/palette.lmp').read_bytes(),base)
                (id1/'gfx/palette.lmp').write_bytes(ui);events.append('reserve');return {}
            def populate(data,path,**kwargs):
                self.assertEqual((path/'id1/gfx/palette.lmp').read_bytes(),ui)
                self.assertEqual(kwargs['rooms'],{});self.assertEqual(kwargs['reports'],[])
                self.assertFalse(kwargs['doors']);self.assertTrue(kwargs['include_exterior'])
                events.append('populate');return {}
            with patch.object(carrier,'resolve_data_files',return_value=root), \
                 patch.object(carrier,'child_ci',return_value=root/'Morrowind.esm'), \
                 patch.object(carrier,'file_digest',return_value='synthetic-input-hash'), \
                 patch.object(carrier,'load_master',return_value=({},[],{})), \
                 patch.object(carrier,'read_interior',return_value={'flags':1,'refs':[]}), \
                 patch.object(carrier,'reserved_palette',return_value=(ui,{})), \
                 patch.object(carrier,'runtime_palette',return_value=final), \
                 patch.object(carrier,'populate_intro_actors',side_effect=actors), \
                 patch.object(carrier,'reserve',side_effect=reserve), \
                 patch.object(carrier,'populate',side_effect=populate), \
                 patch.object(carrier,'bind_opening',side_effect=lambda *args:(events.append('opening') or {})):
                result=carrier.prepare(root,source,out,h,c)
            self.assertEqual(events,['actors','reserve','populate','opening'])
            self.assertFalse(result['regional_bsp_compilation'])
            self.assertFalse(result['independent_interior_or_movie_conversion'])
            self.assertEqual((source/'id1/gfx/palette.lmp').read_bytes(),base)
            self.assertEqual((out/'id1/maps/seyda.bsp').read_bytes(),(out/'seyda.bsp').read_bytes())

if __name__=='__main__':
    unittest.main()
