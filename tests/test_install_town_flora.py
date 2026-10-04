# SPDX-License-Identifier: GPL-3.0-only
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from install_town_flora import derive_bindings, install
from player_hull import lumps, pack_lumps
from test_world_flora_integration import packet_fixture, HASH
from test_replace_bsp_world import fixture, PALETTE


class TownFloraTests(unittest.TestCase):
    def setup_source(self,root):
        model,index=packet_fixture(root);model['source_sha256']='b'*64;index['master_sha256']=HASH
        r=index['references'][0];r['scale']=1.015
        asset={'model':r['model'],'sprite_asset_name':'progs/aw_flora/f_'+'a'*16+'.spr','source_xy_bake_center':[4,4],'pixel_bytes':16}
        source=root/asset['sprite_asset_name'];source.parent.mkdir(parents=True);source.write_bytes(b'private synthetic sprite')
        asset['sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        receipt={'master_sha256':HASH,'palette_sha256':hashlib.sha256(PALETTE).hexdigest(),'placements':[r],'assets':[asset]}
        (root/'tree-sprites.json').write_text(json.dumps(receipt));(root/'source/scenery-index.json').write_text(json.dumps(index))
        alias={'models':[{'model':model['source'],'kind':'sprite'}]}
        e={'name':'sn000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]}
        z=r['rotation_radians'][2];co,si=math.cos(z),math.sin(z)
        pos=[(r['position'][0]+4*co+4*si)*.25,(r['position'][1]-4*si+4*co)*.25,r['position'][2]*.25]
        d=lumps(fixture());d[0]=d[0].rstrip(b'\0')+('{"classname" "aw_static" "model" "progs/m000.spr" "origin" "'+' '.join(f'{v:.3f}' for v in pos)+'"}\n\0').encode()
        return index,receipt,alias,e,pack_lumps(d)

    def test_legacy_binding_uses_exact_source_identity_and_old_scale1_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);idx,receipt,alias,e,raw=self.setup_source(root)
            retained,bindings=derive_bindings(raw,idx,alias,receipt,idx,e)
            self.assertEqual(retained,[]);self.assertEqual(bindings[0]['source_key'],receipt['placements'][0]['source_key'])
            self.assertEqual(bindings[0]['scale'],1)
            bad=copy.deepcopy(idx);bad['references'][0]['scale']=1
            with self.assertRaises(ValueError):derive_bindings(raw,bad,alias,receipt,idx,e)
            ambiguous=copy.deepcopy(idx);second={**copy.deepcopy(ambiguous['references'][0]),'number':2,'source_key':[HASH,'exterior',[0,0],2]}
            ambiguous['references'].append(second);r2={**receipt,'placements':[*receipt['placements'],second]}
            with self.assertRaises(ValueError):derive_bindings(raw,ambiguous,alias,r2,idx,e)

    def test_existing_legacy_copy_outside_rotated_bounds_is_replaced_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flora=root/'flora';flora.mkdir();idx,receipt,alias,e,raw=self.setup_source(flora)
            # Old upright quad touches the apron; current tilted source bounds
            # lie beyond it. Binding preserves this exact existing copy only.
            idx['references'][0]['bounds']=[[1000,1000,0],[1100,1100,80]]
            (flora/'source/scenery-index.json').write_text(json.dumps(idx))
            scene=root/'scene';maps=scene/'id1/maps';maps.mkdir(parents=True)
            target=maps/'sn000.bsp';target.write_bytes(raw);palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            result=install(scene,flora,palette,entries=[e],town_source_index=idx,town_scene_report=alias,work_dir=root/'passed')
            row=result['maps'][0]
            self.assertEqual(row['existing_bound_original_refs_outside_source_bounds'],[receipt['placements'][0]['source_key']])
            self.assertEqual(row['removed_legacy_sprite_keys'],[receipt['placements'][0]['source_key']])
            self.assertEqual(len(row['source_references']),1)
            entities=bytes(lumps(target.read_bytes())[0])
            self.assertEqual(entities.count(b'"classname" "aw_flora"'),1)
            self.assertNotIn(b'progs/m000.spr',entities)
            self.assertEqual(e['coverage'],[[-100,-100],[100,100]])

    def test_unrelated_legacy_sprite_is_retained_and_bound_key_cannot_be_forged(self):
        from prepare_world_flora import overlay_region
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);idx,receipt,alias,e,raw=self.setup_source(root)
            d=lumps(raw);d[0]=d[0].rstrip(b'\0')+b'{"classname" "aw_static" "model" "progs/m999.spr" "origin" "1 2 3"}\n\0'
            raw=pack_lumps(d);base=root/'base.bsp';base.write_bytes(raw);palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            retained,bindings=derive_bindings(raw,idx,alias,receipt,idx,e)
            self.assertEqual(len(bindings),1)
            result=overlay_region(base,root/'valid/scene.bsp',root,idx,receipt,e,palette,legacy_sprite_bindings=bindings)
            text=bytes(lumps((root/'valid/scene.bsp').read_bytes())[0])
            self.assertIn(b'progs/m999.spr',text)
            self.assertEqual(result['existing_bound_original_refs_outside_source_bounds'],[])
            self.assertEqual(len(result['source_references']),1)
            forged=copy.deepcopy(bindings);forged[0]['source_key'][0]='wrong-master'
            with self.assertRaisesRegex(ValueError,'exact original source key'):
                overlay_region(base,root/'forged/scene.bsp',root,idx,receipt,e,palette,legacy_sprite_bindings=forged)

    def test_typed_town_admission_preserves_world_cap_and_final_abi_gate(self):
        from unittest.mock import patch
        from prepare_world_flora import overlay_region, RESERVES, FloraReserveError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);idx,receipt,alias,e,raw=self.setup_source(root)
            base=root/'base.bsp';base.write_bytes(fixture());palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            with patch.dict(RESERVES,{'bytes':1}):
                with self.assertRaises(FloraReserveError):
                    overlay_region(base,root/'world/scene.bsp',root,idx,receipt,{**e,'name':'vf0000'},palette)
                report=overlay_region(base,root/'town/scene.bsp',root,idx,receipt,e,palette,admission_profile='town')
            self.assertEqual(report['admission']['profile'],'town')
            self.assertIsNone(report['admission']['file_budget_bytes'])
            self.assertEqual(report['admission']['map_allowance_bytes'],6*1024*1024)
            self.assertEqual(report['admission']['baseline_reserve_bytes'],3*1024*1024)
            self.assertEqual(report['admission']['safety_headroom_bytes'],2*1024*1024)
            self.assertFalse(report['admission']['final_heap_verified'])
            self.assertIn('required',report['admission']['final_target_abi_gate'])
            self.assertIn('required',report['admission']['final_transport_gate'])
            with patch.dict(RESERVES,{'static_entities':0}):
                with self.assertRaises(FloraReserveError):
                    overlay_region(base,root/'capacity/scene.bsp',root,idx,receipt,e,palette,admission_profile='town')
            with self.assertRaisesRegex(ValueError,'explicit bounded town'):
                overlay_region(base,root/'fake/scene.bsp',root,idx,receipt,{**e,'name':'vf0000'},palette,admission_profile='town')

    def test_existing_mesh_is_retained_by_source_key_and_pose_not_number_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);idx,receipt,alias,e,raw=self.setup_source(root)
            d=lumps(fixture(inline=True));d[0]=bytearray(b'{"classname" "worldspawn"}\n{"classname" "func_wall" "model" "*1" "aw_ref" "1" "origin" "10 12.5 15"}\n\0')
            raw=pack_lumps(d);keys,bindings=derive_bindings(raw,idx,None,receipt,idx,e)
            self.assertEqual(keys,[receipt['placements'][0]['source_key']]);self.assertEqual(bindings,[])
            d[0]=d[0].replace(b'10 12.5 15',b'11 12.5 15')
            with self.assertRaises(ValueError):derive_bindings(pack_lumps(d),idx,None,receipt,idx,e)

    def test_explicit_seyda_routes_accept_same_original_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flora=root/'flora';flora.mkdir();idx,receipt,alias,e,raw=self.setup_source(flora)
            scene=root/'scene';maps=scene/'id1/maps';maps.mkdir(parents=True)
            palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            entries=[{**e,'name':name} for name in ('intro_docks','sncourt')]
            for row in entries:(maps/(row['name']+'.bsp')).write_bytes(raw)
            result=install(scene,flora,palette,entries=entries,town_source_index=idx,town_scene_report=alias)
            self.assertEqual(result['unique_original_refs'],1)
            self.assertEqual(result['removed_legacy_sprite_originals'],1)
            self.assertEqual(len(result['maps']),2)
            for row in entries:
                data=bytes(lumps((maps/(row['name']+'.bsp')).read_bytes())[0])
                self.assertEqual(data.count(b'"classname" "aw_flora"'),1)
            with self.assertRaises(ValueError):
                install(scene,flora,palette,entries=[{**e,'name':'../seyda'}],town_source_index=idx)

    def test_install_replaces_legacy_once_and_later_binding_failure_does_not_mutate_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);flora=root/'flora';flora.mkdir();idx,receipt,alias,e,raw=self.setup_source(flora)
            scene=root/'scene';maps=scene/'id1/maps';maps.mkdir(parents=True)
            target=maps/'sn000.bsp';target.write_bytes(raw);palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            second=maps/'sn001.bsp';second.write_bytes(raw.replace(b'progs/m000.spr',b'progs/m000.spr'))
            # Duplicate original legacy entities fail binding in the second map.
            d=lumps(second.read_bytes());d[0]=d[0].rstrip(b'\0')+bytes(d[0]).split(b'}')[1]+b'}\n\0';second.write_bytes(pack_lumps(d))
            with self.assertRaises(ValueError):install(scene,flora,palette,entries=[e,{**e,'name':'sn001'}],town_source_index=idx,town_scene_report=alias,work_dir=root/'failed')
            self.assertEqual(target.read_bytes(),raw)
            result=install(scene,flora,palette,entries=[e],town_source_index=idx,town_scene_report=alias,work_dir=root/'passed')
            entities=bytes(lumps(target.read_bytes())[0]);self.assertNotIn(b'progs/m000.spr',entities)
            self.assertEqual(entities.count(b'"classname" "aw_flora"'),1)
            self.assertIn(b'"aw_scale" "1.015"',entities)
            self.assertEqual(result['removed_legacy_sprite_originals'],1)
            self.assertEqual(result['unique_original_refs'],1)

if __name__=='__main__':unittest.main()
