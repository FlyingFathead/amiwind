# SPDX-License-Identifier: GPL-3.0-only
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from world_flora import flora_kind, inventory
from prepare_tree_sprites import collision_metadata, normalized_model, select_census
from prepare_world_flora import effective_representation, overlay_region
from world_flora_policy import load_policy, placement
from test_world_flora_integration import packet_fixture, record, sub
from test_replace_bsp_world import fixture, PALETTE
from player_hull import lumps


def source_fixture():
    source=record('CONT',sub('NAME',b'plant\0')+sub('MODL',b'f\\flora_bc_mushroom_01.nif\0')+
        sub('SCRI',b'fixture_script\0')+sub('FLAG',struct.pack('<I',11))+
        sub('CNDT',struct.pack('<f',7.5))+sub('NPCO',struct.pack('<i32s',2,b'fixture_loot')))
    source+=record('CELL',sub('DATA',struct.pack('<Iii',0,-2,-10))+
        sub('FRMR',struct.pack('<I',42))+sub('NAME',b'plant\0')+
        sub('XSCL',struct.pack('<f',1.5))+sub('DATA',struct.pack('<6f',1,2,3,.2,.3,.4)))
    return source


class SmallMushroomTests(unittest.TestCase):
    def test_category_is_opt_in_and_keeps_source_container_identity(self):
        source=source_fixture()
        self.assertEqual(inventory(source)['references'],[])
        census=inventory(source,('small_mushroom',));ref=census['references'][0]
        self.assertEqual(ref['number'],42)
        self.assertEqual(ref['cell'],[-2,-10])
        self.assertEqual(ref['position'],[1,2,3])
        self.assertEqual(ref['scale'],1.5)
        self.assertAlmostEqual(ref['rotation_radians'][0],.2)
        self.assertEqual(ref['script'],'fixture_script')
        self.assertEqual(ref['container_state'],{'items':[{'id':'fixture_loot','count':2}], 'flags':11,'weight':7.5})
        self.assertTrue(ref['requires_interaction'])
        self.assertIsNone(flora_kind('f/flora_emp_parasol_01.nif'))
        self.assertIsNone(flora_kind('f/flora_bc_mushroom_fake.nif'))

    def test_opt_in_reaches_selection_and_preserves_interaction_routing(self):
        census=inventory(source_fixture(),('small_mushroom',))
        with self.assertRaises(ValueError):select_census(census)
        _,refs=select_census(census,include_small_mushrooms=True)
        self.assertEqual(refs,census['references'])
        p=placement(refs[0],[[0,0,0],[2,2,3]],load_policy(),census['master_sha256'])
        self.assertEqual(effective_representation(p),'mesh_pending_interaction')
        self.assertEqual(p['source_key'],(census['master_sha256'],'exterior',(-2,-10),42))
        self.assertEqual(p['container_state'],refs[0]['container_state'])
        self.assertEqual(normalized_model('meshes/f/flora_bc_mushroom_01.nif',True),'f/flora_bc_mushroom_01.nif')
        with self.assertRaises(ValueError):normalized_model('f/flora_t_mushroom_01.nif',True)

    def test_ground_mushroom_has_no_invented_collision_hull(self):
        from prepare_scenery import nif_reader
        N=nif_reader();data=N.Data(version=0x04000002);node=N.NiNode();data.roots=[node]
        stream=io.BytesIO();data.write(stream)
        self.assertEqual(collision_metadata(stream.getvalue(),N,'small_mushroom')['mode'],'nonsolid')
        node.num_children=1;node.children.update_size();node.children[0]=N.RootCollisionNode()
        stream=io.BytesIO();data.write(stream)
        self.assertEqual(collision_metadata(stream.getvalue(),N,'small_mushroom')['mode'],'authored')

    def test_diagnostic_census_cannot_become_full_world_overlay(self):
        from prepare_world_flora import prepare
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ('terrain','base','flora'):(root/folder).mkdir()
            (root/'terrain/world-regions.json').write_text(json.dumps({'regions':[]}))
            (root/'base/world-scenery.json').write_text(json.dumps({'diagnostic_subset':False}))
            (root/'flora/tree-sprites.json').write_text(json.dumps({'diagnostic_subset':True}))
            with self.assertRaisesRegex(ValueError,'Full flora overlay requires full'):
                prepare(root/'terrain',root/'base',root/'flora',root/'palette.lmp',root/'output',jobs=1)

    def test_actual_overlay_adds_mesh_and_retains_container_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet_fixture(root)
            r=index['references'][0]
            r.update(type='CONT',kind='small_mushroom',script='fixture_script',requires_interaction=True,
                     container_state={'items':[{'id':'fixture_loot','count':2}],'flags':11,'weight':7.5},
                     source_collision={'mode':'nonsolid','reason':'small ground plant'})
            before=copy.deepcopy(r)
            receipt={'placements':[r],'assets':[]}
            base=root/'base.bsp';base.write_bytes(fixture(inline=True))
            palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            out=root/'overlay/scene.bsp'
            report=overlay_region(base,out,root,index,receipt,
                {'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]},palette)
            self.assertEqual(report['sprite_instances'],0)
            self.assertEqual(report['mesh_pending_interaction_instances'],1)
            self.assertEqual(report['unsupported_interactions'],[r['source_key']])
            self.assertGreater(report['bsp_models'],2)
            self.assertEqual(report['clipnodes'],len(lumps(base.read_bytes())[9])//8)
            preserved=report['source_references'][0]
            for field in ('number','cell','position','rotation_radians','scale','source_key','container_state','script'):
                self.assertEqual(preserved[field],before[field])
            self.assertEqual(preserved['effective_representation'],'mesh_pending_interaction')
            self.assertEqual(report['interaction_status'],'not_implemented')
            self.assertEqual(report['retained_content']['retained_content'],'verified')


if __name__=='__main__':unittest.main()
