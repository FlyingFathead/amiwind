# SPDX-License-Identifier: GPL-3.0-only
"""Actual whole-reference compaction and authenticated original-door fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from test_compact_bsp import fixture
from test_harvest_room import door_source, cell, ref
from compact_bsp import entities, entity_bytes
from player_hull import lumps, pack_lumps
from mwad.interior import original_doors
from prepare_interior_sections import prepare, pin, section_text
from interior_sections import decode, fingerprint_entries
import test_harvest_fingerprint as save_namespace


def inputs(root):
    base=root/'base';(base/'maps').mkdir(parents=True)
    raw=fixture();data=lumps(raw)
    data[0]=bytearray(entity_bytes([
        dict(classname='worldspawn'),dict(classname='info_player_start',origin='1 2 3',angle='90'),
        dict(classname='func_wall',model='*2',aw_ref='42'),
        dict(classname='func_wall',model='*1',aw_ref='43')]))
    raw=pack_lumps(data);(base/'maps/room.bsp').write_bytes(raw)
    (base/'harvest-room.txt').write_text('AWH3 0 0 0 1 '+'a'*64+'\n')
    index=json.dumps(dict(references=[dict(number=42),dict(number=43)])).encode()
    master=door_source()+cell('Room',ref(42,target=''))+cell('',ref(100,target='Room'),False)
    originals=original_doors(master)
    doors=dict(links=[dict(reference=d['number'],original=d,
        source='room' if d['source_cell']=='Room' else 'vf0000',
        target='vf0000' if d['source_cell']=='Room' else 'room',
        mins=[0,0,0],maxs=[1,1,1],arrival=[1,2,3],yaw=90,label='Original door') for d in originals])
    sections=[dict(name='sectiona',physical_id=8252,references=[42],coverage=[[-20]*3,[20]*3],spawn=[1,2,3],yaw=90),
              dict(name='sectionb',physical_id=8253,references=[43],coverage=[[-20]*3,[20]*3],spawn=[2,2,3],yaw=90)]
    plan=dict(master_sha256=pin(master)['sha256'],index_sha256=pin(index)['sha256'],
        doors_sha256=pin(json.dumps(doors,sort_keys=True,separators=(',',':')).encode())['sha256'],
        cell='Room',base_map='room.bsp',base=pin(raw),logical_map='room',logical_id=8252,
        entrance_section='sectiona',sections=sections,external_dependencies=[],
        portals=[dict(**{'from':'sectiona','to':'sectionb'},axis=0,split=0,margin=2,bounds=[[-10]*3,[10]*3])])
    return dict(plan=plan,base_id1=base,source_index=index,master=master,doors=doors),raw


class InteriorPreparationTests(unittest.TestCase):
    def test_actual_compactor_retains_union_models_and_original_directed_doors(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args,raw=inputs(root);report=prepare(**args,output=root/'out')
            self.assertEqual(report['union_references'],[42,43])
            self.assertEqual((args['base_id1']/'maps/room.bsp').read_bytes(),raw)
            for name,reference,spawn in [('sectiona',42,'1 2 3'),('sectionb',43,'2 2 3')]:
                candidate=(root/'out/id1/maps'/f'{name}.bsp').read_bytes()
                records=entities(lumps(candidate)[0]);self.assertLess(len(candidate),len(raw))
                self.assertEqual([int(e['aw_ref']) for e in records if 'aw_ref' in e],[reference])
                self.assertEqual(next(e['origin'] for e in records if e.get('classname')=='info_player_start'),spawn)
            self.assertEqual((root/'out/id1/doors-sectionb.txt').read_text(),'AWD3\n')
            self.assertEqual([(d['source'],d['target'],d['reference']) for d in report['original_door_links']],
                             [('sectiona','vf0000',42),('vf0000','sectiona',100)])
            self.assertEqual(report['native_acceptance'],'not_run')

    def test_source_base_door_and_union_mismatches_refuse_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args,_=inputs(root)
            mutations=[lambda a:a.update(master=a['master']+b'x'),
                       lambda a:a.update(source_index=a['source_index']+b' '),
                       lambda a:a['plan']['base'].update(sha256='f'*64),
                       lambda a:a['doors']['links'][0].update(yaw=91),
                       lambda a:a['plan']['sections'][1].update(references=[]),
                       lambda a:a['plan']['sections'][1].update(references=[43,999]),
                       lambda a:a['plan']['sections'][1].update(references=[43,43]),
                       lambda a:a['plan']['sections'][1].update(physical_id=8252),
                       lambda a:a['plan']['sections'][0].update(spawn=[8,2,3])]
            for mutate in mutations:
                a=copy.deepcopy(args);mutate(a)
                with self.subTest(mutation=mutate),self.assertRaises(ValueError):prepare(**a,output=root/'bad')
                self.assertFalse((root/'bad').exists())
            # Re-pinning altered transformed data still cannot change original record identity.
            a=copy.deepcopy(args);a['doors']['links'][0]['original']['number']=999
            a['plan']['doors_sha256']=pin(json.dumps(a['doors'],sort_keys=True,separators=(',',':')).encode())['sha256']
            with self.assertRaisesRegex(ValueError,'original directed'):prepare(**a,output=root/'bad')

    def test_portal_shared_coverage_and_hysteresis_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            args,_=inputs(Path(td));p=args['plan'];decode(section_text(p))
            for field,value in [('axis',3),('margin',0),('margin',40),('split',float('nan')),
                                ('bounds',[[-10]*3,[30]*3]),('bounds',[[0],[1]])]:
                bad=copy.deepcopy(p);bad['portals'][0][field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):section_text(bad)
            bad=copy.deepcopy(p);bad['portals']*=2
            with self.assertRaises(ValueError):section_text(bad)

    def test_fingerprint_binds_section_config_geometry_and_directed_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args,raw=inputs(root)
            self.assertEqual(fingerprint_entries(args['base_id1']),[])
            prepare(**args,output=root/'out');id1=root/'out/id1'
            with self.assertRaisesRegex(ValueError,'route map'):fingerprint_entries(id1)
            (id1/'maps/vf0000.bsp').write_bytes(raw)
            original=fingerprint_entries(id1)
            self.assertEqual(original,sorted(original))
            self.assertIn('maps/vf0000.bsp',dict(original))
            for name in ('maps/sectiona.bsp','maps/vf0000.bsp','doors-vf0000.txt','interior-sections.txt'):
                path=id1/name;before=path.read_bytes()
                after=before.replace(b' 90\t',b' 91\t') if name.endswith('vf0000.txt') else before+b'\n'
                if name=='interior-sections.txt':after=before.replace(b'0 2 -10',b'0 3 -10')
                path.write_bytes(after)
                self.assertNotEqual(fingerprint_entries(id1),original,name);path.write_bytes(before)
            (id1/'maps/vf0000.bsp').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'route BSP'):fingerprint_entries(id1)

    def test_real_save_fingerprint_changes_for_section_and_original_entry_banks(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);args,raw=inputs(root);prepare(**args,output=root/'out');id1=root/'out/id1'
            (id1/'maps/vf0000.bsp').write_bytes(raw)
            helper=save_namespace.HarvestFingerprintTests();helper.seed(id1)
            before=helper.fingerprint(id1)
            bank=id1/'doors-vf0000.txt';bank.write_bytes(bank.read_bytes().replace(b' 90\t',b' 91\t'))
            changed=helper.fingerprint(id1);self.assertNotEqual(before,changed)
            geometry=id1/'maps/sectionb.bsp';geometry.write_bytes(geometry.read_bytes()+b'\n')
            self.assertNotEqual(changed,helper.fingerprint(id1))


if __name__=='__main__':unittest.main()
