# SPDX-License-Identifier: GPL-3.0-only
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.scene import pack_geometry
from world_flora import inventory, flora_kind
from prepare_world_flora import effective_representation, overlay_region, remove_legacy_sprites, sprite_entity, verify_retained_content
from prepare_mesh_bsp import _prepare_model
from player_hull import lumps, pack_lumps
from test_replace_bsp_world import fixture, PALETTE

HASH = 'a' * 64

def sub(tag, value): return tag.encode() + struct.pack('<I', len(value)) + value

def record(tag, value): return tag.encode() + struct.pack('<III', len(value), 0, 0) + value

def ref(number=1):
    return {'number': number, 'cell': [0, 0], 'id': 'tree', 'model': 'f/flora_tree.nif',
            'type': 'STAT', 'position': [40, 50, 60], 'scale': 2.37,
            'rotation_radians': [.23, -.41, .8], 'model_index': 0,
            'bounds': [[0, 0, 0], [100, 100, 100]], 'source_key': [HASH, 'exterior', [0, 0], number],
            'renderer_policy': 'sprite', 'requires_interaction': False,
            'source_collision': {'mode': 'visual_fallback', 'reason': 'synthetic cube'}}


def packet_fixture(root):
    points = [(x,y,z) for z in (0, 8) for y in (0, 8) for x in (0, 8)]
    faces = [(0,2,3,0),(0,3,1,0),(4,5,7,0),(4,7,6,0),(0,1,5,0),(0,5,4,0),
             (2,6,7,0),(2,7,3,0),(0,4,6,0),(0,6,2,0),(1,3,7,0),(1,7,5,0)]
    geometry = pack_geometry([[x,y,z,x/8,y/8,255,255,255,255] for x,y,z in points], faces, 1)
    source = root / 'source';source.mkdir()
    (source / 'scenery.mwpak').write_bytes(geometry)
    model = {'source': 'meshes/f/flora_tree.nif', 'offset': 0, 'bytes': len(geometry),
             'sha256': hashlib.sha256(geometry).hexdigest(), 'triangles': 12,
             'materials': [{'texture_index': None, 'diffuse': [1,1,1]}], 'bounds': [[0,0,0],[8,8,8]]}
    r = ref();index = {'models': [model], 'textures': [], 'references': [r],
                      'chunk_size': 2048, 'chunks': {'0,0': [0]}, 'groups': {}, 'errors': []}
    return model, index

class WorldFloraIntegrationTests(unittest.TestCase):
    def test_inventory_preserves_container_contents_and_defers_ivy_orientation(self):
        source = record('STAT', sub('NAME', b'grass\0') + sub('MODL', b'f\\flora_grass_01.nif\0'))
        source += record('CONT', sub('NAME', b'stump\0') + sub('MODL', b'f\\flora_treestump_wg_01.nif\0') + sub('NPCO', struct.pack('<i32s', 3, b'owned_item')))
        source += record('STAT', sub('NAME', b'ivy\0') + sub('MODL', b'f\\flora_ivy_01.nif\0'))
        placements = b''
        for n, name in enumerate((b'grass\0', b'stump\0', b'ivy\0'), 1):
            placements += sub('FRMR', struct.pack('<I', n)) + sub('NAME', name) + sub('XSCL', struct.pack('<f', 2.37)) + sub('DATA', struct.pack('<6f', 1,2,3,.2,.3,.4))
        source += record('CELL', sub('DATA', struct.pack('<Iii', 0, 0, 0)) + placements)
        result = inventory(source, ('tree', 'grass'))
        self.assertEqual(len(result['references']), 2)
        self.assertEqual(result['references'][1]['container_state']['items'], [{'id': 'owned_item', 'count': 3}])
        self.assertTrue(result['references'][1]['requires_interaction'])
        self.assertEqual(result['deferred_references'][0]['kind'], 'ivy')
        self.assertEqual(flora_kind('l/light_de_streetlight.nif'), None)
        self.assertEqual(flora_kind('x/flora_ash_log_01.nif'), 'flora_log')
        self.assertEqual(flora_kind('i/in_strong_rubble01.nif'), None)

    def test_source_scaled_sprite_and_stateful_mesh_representation(self):
        r = ref();asset = {'sprite_asset_name': 'progs/aw_flora/f_' + 'a'*16 + '.spr', 'source_xy_bake_center': [4, 8]}
        text = sprite_entity(r, asset, [10, 20, -30])
        self.assertIn('"aw_scale" "2.37"', text)
        self.assertIn('"classname" "aw_flora"', text)
        self.assertLess(len(asset['sprite_asset_name']), 64)
        r['requires_interaction'] = True
        self.assertEqual(effective_representation(r), 'mesh_pending_interaction')

    def test_collision_only_retains_components_without_visible_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);model, index = packet_fixture(root)
            _, full = _prepare_model((0, model, {}, root/'source/scenery.mwpak', []))
            _, collision = _prepare_model((0, model, {'collision_only': True}, root/'source/scenery.mwpak', []))
            self.assertTrue(full[2])
            self.assertEqual(collision[2], [])
            self.assertEqual(len(full[3]), len(collision[3]))
            self.assertEqual(full[3][0][0].tolist(), collision[3][0][0].tolist())

    def test_actual_overlay_keeps_land_texture_and_existing_inline_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);model, index = packet_fixture(root)
            base = root/'base.bsp';base.write_bytes(fixture(inline=True));palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            r = index['references'][0];receipt = {'placements': [r], 'assets': [{'model': r['model'], 'sprite_asset_name': 'progs/aw_flora/f_'+'a'*16+'.spr', 'source_xy_bake_center': [4,4], 'pixel_bytes': 16}]}
            out=root/'overlay/scene.bsp';entry={'name': 'vf0000', 'origin': [0,0,0], 'coverage': [[-100,-100],[100,100]]}
            report=overlay_region(base,out,root,index,receipt,entry,palette)
            self.assertEqual(report['sprite_instances'], 1)
            self.assertEqual(report['retained_content']['retained_models'], 2)
            self.assertGreater(report['clipnodes'], 2)
            self.assertEqual(bytes(lumps(out.read_bytes())[4]), bytes(lumps(base.read_bytes())[4]))
            self.assertEqual(bytes(lumps(out.read_bytes())[8]), bytes(lumps(base.read_bytes())[8]))
            self.assertIn(b'"aw_scale" "2.37"', lumps(out.read_bytes())[0])
            broken=lumps(out.read_bytes());broken[8][0]^=1
            with self.assertRaises(ValueError):verify_retained_content(base.read_bytes(),pack_lumps(broken))

    def test_legacy_dedup_requires_source_mapping_model_pose_and_scale(self):
        r=ref();r['position']=[0,0,0]
        binding={'source_key': r['source_key'], 'source_model': r['model'], 'model':'progs/tree.spr', 'origin':[1,2,3], 'scale':1}
        data=lumps(fixture());data[0]=bytearray(b'{"classname" "worldspawn"}\n{"classname" "aw_static" "model" "progs/tree.spr" "origin" "1 2 3"}\n\0')
        result, removed=remove_legacy_sprites(pack_lumps(data),[binding],[r])
        self.assertEqual(removed,[r['source_key']]);self.assertNotIn(b'aw_static',lumps(result)[0])
        invalid={**binding,'source_model':'f/another_tree.nif'}
        with self.assertRaises(ValueError):remove_legacy_sprites(pack_lumps(data),[invalid],[r])

    def test_source_no_collision_markers_and_ground_policy(self):
        import io
        from prepare_scenery import nif_reader
        from prepare_tree_sprites import collision_metadata, unique_reference_numbers
        N = nif_reader()
        def raw(marker=None, authored=False):
            data=N.Data(version=0x04000002);node=N.NiNode();data.roots=[node]
            if marker:
                extra=N.NiStringExtraData();extra.string_data=marker;node.extra_data=extra
            if authored:
                node.num_children=1;node.children.update_size();node.children[0]=N.RootCollisionNode()
            stream=io.BytesIO();data.write(stream);return stream.getvalue()
        self.assertEqual(collision_metadata(raw(b'NCO'),N,'grass')['mode'],'nonsolid')
        self.assertEqual(collision_metadata(raw(authored=True),N,'bush')['mode'],'authored')
        self.assertEqual(collision_metadata(raw(),N,'fern')['mode'],'nonsolid')
        self.assertEqual(collision_metadata(raw(),N,'tree')['mode'],'visual_fallback')
        with self.assertRaises(ValueError):unique_reference_numbers([ref(),{**ref(),'cell':[1,1]}])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet_fixture(root)
            _, prepared=_prepare_model((0,model,{'collision_none':True},root/'source/scenery.mwpak',[]))
            self.assertTrue(prepared[2]);self.assertEqual(prepared[3],[])

    def test_nonsolid_sprite_overlay_avoids_collision_and_bad_float_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet_fixture(root)
            base=root/'base.bsp';base.write_bytes(fixture(inline=True));palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            r=index['references'][0];r['source_collision']={'mode':'nonsolid','reason':'NCO'}
            asset={'model':r['model'],'sprite_asset_name':'progs/aw_flora/f_'+'a'*16+'.spr','source_xy_bake_center':[4,4],'pixel_bytes':16}
            receipt={'placements':[r],'assets':[asset]}
            report=overlay_region(base,root/'overlay/scene.bsp',root,index,receipt,{'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]},palette)
            self.assertEqual(report['collision_stages'],[])
            self.assertEqual(report['bsp_models'],2)
            self.assertEqual(report['sprite_instances'],1)
            self.assertIn('"angles" "0 0 0"',sprite_entity(r,asset,[0,0,0]))
            for scale in (1e-50,1e39):
                with self.assertRaises(ValueError):sprite_entity({**r,'scale':scale},asset,[0,0,0])

    def test_opt_in_aggregate_preserves_world_convex_pieces_and_source_receipts(self):
        import numpy as np
        from prepare_mesh_bsp import _prepare_placement
        from prepare_world_flora import aggregate_collision
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet_fixture(root)
            r=index['references'][0];second={**copy.deepcopy(r),'number':2,'position':[60,70,80],'scale':1.73,'rotation_radians':[-.37,.29,-.61],'source_key':[HASH,'exterior',[0,0],2]}
            index['references'].append(second);index['chunks']['0,0']=[0,1]
            _,data=_prepare_model((0,model,{'collision_only':True},root/'source/scenery.mwpak',[]))
            entry={'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]}
            subset,prepared,numbers=aggregate_collision(index,[r,second],{0:data},entry)
            expected=[]
            for item in (r,second):
                _,parts,_,_=_prepare_placement((item,data,32,[0,0],None))
                yaw=-item['rotation_radians'][2];co,si=math.cos(yaw),math.sin(yaw)
                runtime=np.array([[co,-si,0],[si,co,0],[0,0,1]])
                expected.extend(p[0]@runtime.T+np.array(item['position'])*.25 for p in parts)
            for actual,wanted in zip(prepared[0][3],expected):
                np.testing.assert_allclose(actual[0],wanted,rtol=1e-12,atol=1e-12)
            self.assertEqual(len(prepared[0][3]),len(expected))
            base=root/'base.bsp';base.write_bytes(fixture(inline=True));pal=root/'palette.lmp';pal.write_bytes(PALETTE)
            asset={'model':r['model'],'sprite_asset_name':'progs/aw_flora/f_'+'a'*16+'.spr','source_xy_bake_center':[4,4],'pixel_bytes':16}
            receipt={'placements':[r,second],'assets':[asset]}
            report=overlay_region(base,root/'comparison/scene.bsp',root,index,receipt,entry,pal,aggregate_sprite_collision=True)
            self.assertEqual(report['bsp_models'],3)
            self.assertEqual(report['sprite_instances'],2)
            self.assertEqual(len(report['source_references']),2)
            self.assertEqual(report['retained_content']['retained_content'],'verified')

    def test_adaptive_actual_candidates_choose_default_or_aggregate_and_preserve_failures(self):
        from unittest.mock import patch
        from prepare_world_flora import RESERVES, FloraReserveError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet_fixture(root)
            r=index['references'][0];second={**copy.deepcopy(r),'number':2,'scale':1.73,'source_key':[HASH,'exterior',[0,0],2]}
            index['references'].append(second);index['chunks']['0,0']=[0,1]
            base=root/'base.bsp';base.write_bytes(fixture(inline=True));pal=root/'palette.lmp';pal.write_bytes(PALETTE)
            asset={'model':r['model'],'sprite_asset_name':'progs/aw_flora/f_'+'a'*16+'.spr','source_xy_bake_center':[4,4],'pixel_bytes':16}
            receipt={'placements':[r,second],'assets':[asset]};entry={'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]}
            def run(folder):
                return overlay_region(base,root/folder/'scene.bsp',root,index,receipt,entry,pal,collision_packing='adaptive')
            passing=run('passing-default')
            self.assertEqual(passing['collision_packing']['selected_strategy'],'per_instance')
            default_entities=passing['entities']
            with patch.dict(RESERVES,{'entities':default_entities-1}):
                adaptive=run('entity-failure')
            self.assertEqual(adaptive['collision_packing']['selected_strategy'],'aggregate')
            with patch.dict(RESERVES,{'models_plus_sprites':passing['reserve_metrics']['models_plus_sprites']-1}):
                model_repair=run('model-failure')
            self.assertEqual(model_repair['collision_packing']['selected_strategy'],'aggregate')
            self.assertEqual(len(adaptive['source_references']),2)
            self.assertEqual(adaptive['retained_content']['retained_content'],'verified')
            self.assertTrue((root/'entity-failure/collision-per_instance/candidate-scene.bsp').exists())
            self.assertEqual(len(adaptive['collision_packing']['attempts']),2)
            with patch.dict(RESERVES,{'entities':default_entities-1,'static_entities':1}):
                with self.assertRaises(FloraReserveError):run('both-fail')
            failure=json.loads((root/'both-fail/collision-packing.json').read_text())
            self.assertEqual(len(failure['attempts']),2);self.assertIsNone(failure['selected_strategy'])
            self.assertTrue((root/'both-fail/collision-aggregate/candidate-scene.bsp').exists())
            with patch.dict(RESERVES,{'clipnodes':0}):
                with self.assertRaises(FloraReserveError):run('clip-only')
            rejected=json.loads((root/'clip-only/collision-packing.json').read_text())
            self.assertEqual(len(rejected['attempts']),1)
            self.assertFalse((root/'clip-only/collision-aggregate').exists())

    def test_resume_checks_contract_bytes_refs_pose_and_retained_content(self):
        from prepare_world_flora import prepare, cached_region, input_contract
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flora=root/'flora';flora.mkdir();model,index=packet_fixture(flora);index['master_sha256']=HASH
            r=index['references'][0]
            asset={'model':r['model'],'sprite_asset_name':'progs/aw_flora/f_'+'a'*16+'.spr','source_xy_bake_center':[4,4],'pixel_bytes':16}
            sprite=flora/asset['sprite_asset_name'];sprite.parent.mkdir(parents=True);sprite.write_bytes(b'owned synthetic sprite')
            asset['sha256']=hashlib.sha256(sprite.read_bytes()).hexdigest()
            palette=root/'palette.lmp';palette.write_bytes(PALETTE);palhash=hashlib.sha256(PALETTE).hexdigest()
            receipt={'placements':[r],'assets':[asset],'master_sha256':HASH,'palette_sha256':palhash,'selection':{'original_instances':1}}
            (flora/'tree-sprites.json').write_text(json.dumps(receipt));(flora/'source/scenery-index.json').write_text(json.dumps(index))
            terrain=root/'terrain';terrain.mkdir();base=root/'base';base.mkdir();entry={'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]}
            (terrain/'world-regions.json').write_text(json.dumps({'master_sha256':HASH,'regions':[entry]}))
            local=base/'vf0000';local.mkdir();(local/'scene.bsp').write_bytes(fixture(inline=True))
            base_receipt={'palette_sha256':palhash,'regions':[{'name':'vf0000','sha256':hashlib.sha256((local/'scene.bsp').read_bytes()).hexdigest()}]}
            (base/'world-scenery.json').write_text(json.dumps(base_receipt))
            first=prepare(terrain,base,flora,palette,root/'first',jobs=1,collision_packing='adaptive')
            with patch('prepare_world_flora.convert_region',side_effect=AssertionError('Valid cache must skip conversion')):
                second=prepare(terrain,base,flora,palette,root/'second',jobs=1,collision_packing='adaptive',resume_from=root/'first')
            self.assertEqual(second['resume']['reused'],['vf0000'])
            self.assertEqual(first['regions'][0]['sha256'],second['regions'][0]['sha256'])
            # Unknown historical hashes require an explicit audited adoption.
            (root/'second/input-contract.json').unlink()
            adopted=prepare(terrain,base,flora,palette,root/'adopted',jobs=1,collision_packing='adaptive',resume_from=root/'second',adopt_legacy_resume_inputs=True)
            self.assertEqual(adopted['resume']['reused'],['vf0000'])
            self.assertIn('not recorded',adopted['resume']['historical_source_contract'])
            # A valid file hash cannot conceal altered source-instance metadata.
            report_path=root/'second/vf0000/conversion.json';changed=json.loads(report_path.read_text());changed['source_references'][0]['scale']=1;report_path.write_text(json.dumps(changed))
            regenerated=prepare(terrain,base,flora,palette,root/'regenerated',jobs=1,collision_packing='adaptive',resume_from=root/'second',adopt_legacy_resume_inputs=True)
            self.assertEqual(regenerated['resume']['reused'],[])
            self.assertIn('source identities',regenerated['resume']['regenerated'][0]['reason'])
            # Source image changes cannot reuse any previous input contract.
            sprite.write_bytes(b'changed sprite')
            with self.assertRaises(ValueError):input_contract(terrain,base,flora,palette,receipt)

    def test_policy_provenance_has_no_dependency_when_not_requested(self):
        import build
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            args=build.parser().parse_args(['--dry-run']);args.font_options={'synthetic':True}
            with patch.object(build,'ROOT',Path(tmp)):
                result=build.provenance(args,{})
                self.assertEqual(result['world_flora']['status'],'not_requested')
                self.assertIsNone(result['world_flora']['policy_sha256'])
                args.tree_sprites=True
                with self.assertRaises(FileNotFoundError):build.provenance(args,{})

    def test_opt_in_builder_auto_inventory_and_dependency_chain(self):
        import build
        from build_parallel import stage_dependencies
        args=build.parser().parse_args(['--tree-sprites']);args.data_files=Path('/owned');args.sdk=Path('/sdk')
        tools={name:'/tools/'+name for name in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
        steps=build.commands(args,tools,Path('/private/run'));commands=dict(steps);deps=stage_dependencies(steps)
        self.assertNotIn('--census',commands['world-flora-assets'])
        self.assertIn('--world-flora',commands['image'])
        self.assertIn('--town-flora-source-index',commands['image'])
        self.assertIn('--town-flora-scene-report',commands['image'])
        self.assertEqual(Path(commands['image'][commands['image'].index('--balmora-cache')+1]),Path('/private/run/balmora-work'))
        self.assertEqual(commands['world-flora'][commands['world-flora'].index('--collision-packing')+1],'adaptive')
        self.assertIn('world-scenery',deps['world-flora']);self.assertIn('world-flora',deps['image'])
        args.tree_sprites=False;commands=dict(build.commands(args,tools,Path('/private/run')))
        self.assertNotIn('world-flora',commands);self.assertNotIn('--world-flora',commands['image'])
        self.assertNotIn('--town-flora-source-index',commands['image'])
        self.assertNotIn('--town-flora-scene-report',commands['image'])
        self.assertNotIn('--balmora-cache',commands['image'])


class RefinedResumeContractTests(unittest.TestCase):
    def test_only_directory_receipt_changes_can_be_explicitly_reused(self):
        from prepare_world_flora import resume_contract_matches, canonical_hash
        before={'hashes':{'terrain_directory':'old','base_receipt':'old','palette':'p','full_reference_set':'r','sprite':'s'}}
        before['sha256']=canonical_hash(before['hashes'])
        after=copy.deepcopy(before);after['hashes']['terrain_directory']='new';after['hashes']['base_receipt']='new';after['sha256']=canonical_hash(after['hashes'])
        self.assertFalse(resume_contract_matches(before,after))
        self.assertTrue(resume_contract_matches(before,after,True))
        for key in ('palette','full_reference_set','sprite'):
            changed=copy.deepcopy(after);changed['hashes'][key]='changed';changed['sha256']=canonical_hash(changed['hashes'])
            self.assertFalse(resume_contract_matches(before,changed,True))
        before['sha256']='tampered'
        self.assertFalse(resume_contract_matches(before,after,True))

if __name__ == '__main__':unittest.main()
