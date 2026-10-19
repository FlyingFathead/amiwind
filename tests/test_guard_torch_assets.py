import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
from prepare_guard_torches import guard_eligibility, registry, TorchLayer, _guard_models
from npc_geometry import bake


def field(value): return value.encode('cp1252')+b'\0'
def inventory(identifier, count=1): return struct.pack('<i32s', count, field(identifier))
def light(mesh='l/light_torch10.nif', flags=2):
    return [('MODL', field(mesh)), ('LHDT', bytes(20)+struct.pack('<I', flags))]


class GuardTorchAssetsTests(unittest.TestCase):
    def test_source_class_not_display_name_and_inventory(self):
        lights={'torch_infinite_time':light()}
        named_guard=[('CNAM',field('Commoner')),('FNAM',field('Guard')),('NPCO',inventory('torch_infinite_time'))]
        self.assertEqual(guard_eligibility(named_guard,lights,'l/light_torch10.nif'),(False,False,[]))
        for name in ('Guard','Ordinator Guard','gUaRd'):
            guard=[('CNAM',field(name)),('FNAM',field('Named NPC'))]
            self.assertEqual(guard_eligibility(guard,lights,'l/light_torch10.nif'),(True,False,[]))
            result=guard_eligibility(guard+[('NPCO',inventory('TORCH_INFINITE_TIME',-1))],lights,'l/light_torch10.nif')
            self.assertTrue(result[0]);self.assertTrue(result[1]);self.assertEqual(result[2][0]['count'],-1)
            self.assertFalse(guard_eligibility(guard+[('NPCO',inventory('torch_infinite_time',0))],lights,'l/light_torch10.nif')[1])

    def test_inventory_carry_flag_and_other_mesh_refused(self):
        actor=[('CNAM',field('Guard')),('NPCO',inventory('light'))]
        self.assertFalse(guard_eligibility(actor,{'light':light(flags=0)},'l/light_torch10.nif')[1])
        with self.assertRaisesRegex(ValueError,'different unsupported'):
            guard_eligibility(actor,{'light':light('l/other.nif')},'l/light_torch10.nif')
        with self.assertRaisesRegex(ValueError,'Malformed guard inventory'):
            guard_eligibility([('CNAM',field('Guard')),('NPCO',b'bad')],{},'l/light_torch10.nif')

    def row(self, count=8):
        return dict(source_id='guard source',base_model='progs/base.mdl',body_model='progs/gt_b_one.mdl',
                    torch_model='progs/gt_t_one.mdl',auto_inventory_eligible=True,frames=count,
                    emitters=[[1.25,-2.5,33.75]]*count)

    def test_binary_registry_8_and_21_frame_contract(self):
        for count in (8,21):
            raw=registry([self.row(count)])
            self.assertEqual(struct.unpack_from('>4sHH',raw),(b'AWG1',1,0))
            self.assertEqual(raw[8:72],b'guard source'.ljust(64,b'\0'))
            self.assertEqual(struct.unpack_from('>HH',raw,264),(count,1))
            self.assertEqual(struct.unpack_from('>iii',raw,268),(81920,-163840,2211840))
            self.assertEqual(len(raw),268+count*12)

    def test_registry_limits_fail_closed(self):
        for update in ({'frames':9},{'base_model':'../bad.mdl'},{'source_id':'x'*64},
                       {'emitters':[[float('nan'),0,0]]*8},{'emitters':[[129,0,0]]*8}):
            with self.assertRaises(ValueError):registry([{**self.row(),**update}])
        with self.assertRaises(ValueError):registry([self.row()]*2)
        with self.assertRaises(ValueError):registry([self.row()]*33)

    def test_layer_changes_only_left_clavicle_descendants_and_keeps_gait(self):
        class Base:
            N=None
            events={'torch: start':100.,'torch: stop':108.}
            parents={'root':None,'bip01 l clavicle':'root','hand':'bip01 l clavicle','right':'root'}
            nodes=parents
            def local(self,name,time):
                value=np.eye(4);value[3,0]=time;return value
        class Normal:
            def pose(self,time):
                def world(name):
                    value=np.eye(4);value[3,1]=time;return value
                return world
        times=np.arange(21)*.25;normal=Normal();layer=TorchLayer(Base(),normal,times)
        for index in (0,7,8,12,13,20):
            pose=layer.pose(index)
            np.testing.assert_array_equal(pose('right'),normal.pose(times[index])('right'))
            np.testing.assert_array_equal(pose('root'),normal.pose(times[index])('root'))
            phase=index if index<8 else index-13 if index>=13 else 0
            self.assertEqual(pose('hand')[3,0],2*(100+phase))
            self.assertEqual(pose('hand')[3,1],times[index])

    def test_female_override_file_root_is_not_used_for_unchanged_bones(self):
        class Base:
            N=None
            events={'torch: start':100.,'torch: stop':108.}
            parents={'male file root':None,'spine':'male file root',
                     'bip01 l clavicle':'spine','hand':'bip01 l clavicle','head':'spine'}
            nodes=parents
            def local(self,name,time): return np.eye(4)
        class FemalePose:
            def pose(self,time):
                def world(name):
                    if name=='male file root': raise KeyError(name)
                    value=np.eye(4);value[3,1]=time;return value
                return world
        layer=TorchLayer(Base(),FemalePose(),np.arange(21))
        self.assertEqual(layer.pose(20)('head')[3,1],20)
        self.assertEqual(layer.pose(20)('hand')[3,1],20)

    def test_registry_reads_exact_staged_source_identity_without_map_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1=Path(tmp);(id1/'maps').mkdir()
            entities='''{"classname" "aw_npc" "aw_source_id" "actual" "model" "progs/one.mdl"}
{"classname" "aw_npc" "aw_source_id" "notguard" "netname" "Guard" "model" "progs/two.mdl"}\0'''.encode()
            raw=struct.pack('<i2i',29,124,len(entities))+bytes(112)+entities
            p=id1/'maps/test.bsp';p.write_bytes(raw)
            kinds={'NPC_':{'actual':[('CNAM',field('Guard'))],'notguard':[('CNAM',field('Commoner'))]}}
            result=_guard_models(id1,kinds,{},'l/light_torch10.nif')
            self.assertEqual(len(result),1);self.assertEqual(result[0]['source_id'],'actual')
            self.assertFalse(result[0]['auto_inventory_eligible']);self.assertEqual(p.read_bytes(),raw)

    def test_guards_in_chim_frame_maps_are_found(self):
        # GUARD-TORCH-CHIM-FRAMES-44: exterior guards live in CHIM frame maps (balmora-chim.chim); a *.bsp-only
        # scan gave them no torch at night
        with tempfile.TemporaryDirectory() as tmp:
            id1=Path(tmp);(id1/'maps').mkdir()
            for name,source,model in (('balmora-chim.chim','outside','progs/out.mdl'),('inside.bsp','inside','progs/in.mdl')):
                entities=('{"classname" "aw_npc" "aw_source_id" "%s" "model" "%s"}\0'%(source,model)).encode()
                (id1/'maps'/name).write_bytes(struct.pack('<i2i',29,124,len(entities))+bytes(112)+entities)
            kinds={'NPC_':{'outside':[('CNAM',field('Guard'))],'inside':[('CNAM',field('Guard'))]}}
            found=sorted(r['source_id'] for r in _guard_models(id1,kinds,{},'l/light_torch10.nif'))
            self.assertEqual(found,['inside','outside'])

    def test_image_step_runs_guard_torches_after_the_chim_frame_maps(self):
        # GUARD-TORCH-CHIM-FRAMES-44: the scan must see the frame maps, so it runs after they are written and
        # before the world heap gate and the content fingerprint that read its companions
        source=(Path(__file__).resolve().parents[1]/'tools/build_aga.py').read_text(encoding='utf-8')
        torches=source.index('guard_torches = prepare_guard_torches(')
        self.assertLess(source.index('chim_frames = chim_frame_maps('),torches)
        self.assertLess(torches,source.index('world_heap=audit_world_map_heap_with_receipt('))
        self.assertLess(torches,source.index('omitted_maps = image_content_fingerprint('))

    def test_creature_residents_are_skipped_unknown_identities_still_refused(self):
        # dev1 2026-10-17: Vivec (a creature record) is placed as an aw_npc resident in his palace
        with tempfile.TemporaryDirectory() as tmp:
            id1=Path(tmp);(id1/'maps').mkdir()
            entities='''{"classname" "aw_npc" "aw_source_id" "vivec_god" "netname" "Vivec" "model" "progs/v.mdl"}\0'''.encode()
            raw=struct.pack('<i2i',29,124,len(entities))+bytes(112)+entities
            (id1/'maps/vpi015.bsp').write_bytes(raw)
            kinds={'NPC_':{}}
            self.assertEqual(_guard_models(id1,kinds,{},'l/light_torch10.nif',{'vivec_god'}),[])
            with self.assertRaisesRegex(ValueError,'lacks original source identity'):
                _guard_models(id1,kinds,{},'l/light_torch10.nif')

    def test_extra_pose_sampling_preserves_original_face_quota(self):
        points=np.array([[x,y,.02*x*x] for y in range(9) for x in range(9)],dtype=float)
        faces=[]
        for y in range(8):
            for x in range(8):
                a=y*9+x;faces.extend(((a,a+1,a+9),(a+1,a+10,a+9)))
        frames=np.repeat(points[None],16,axis=0)
        shape={'name':'head','part':0,'positions':frames,'faces':np.array(faces),
               'uv':points[:,:2]/8,'colours':np.ones((len(points),4)),'material':0}
        mats=[{'texture_index':None,'diffuse':[1,1,1],'alpha':1}];palette=bytes(range(256))*3
        original=bake([{**shape,'positions':frames[:8]}],mats,{},palette,budget=64)
        added=bake([shape],mats,{},palette,budget=64,reference_frames=8)
        np.testing.assert_array_equal(original[0],added[0][:8])
        np.testing.assert_array_equal(original[1],added[1]);np.testing.assert_array_equal(original[2],added[2])
        self.assertEqual(original[3].tobytes(),added[3].tobytes())
        with self.assertRaisesRegex(ValueError,'Invalid reference frame'):
            bake([shape],mats,{},palette,reference_frames=17)


class GuardBaseReproductionTests(unittest.TestCase):
    """NPC-HEAD-DECIMATION-33 (v0.0.44-dev1 image step): a guard whose base model was baked with the previous
    head reducer is reproduced by trying it after the configured one; a budget too small for the guard's shapes
    is skipped; the final error names the guard."""

    def arrays(self):
        faces = np.array([[0, 1, 2]]); uv = np.zeros((3, 2)); original = np.zeros((2, 3, 3))
        return faces, uv, original

    def test_previous_reducer_reproduces_and_small_budgets_are_skipped(self):
        import os
        from unittest import mock
        import prepare_guard_torches as guard
        faces, uv, original = self.arrays()
        calls = []
        def fake_bake(shapes, materials, textures, palette, budget, reference_frames):
            reducer = os.environ.get('AMIWIND_NPC_HEAD_REDUCER')
            calls.append((reducer, budget))
            if budget == 192:
                raise ValueError('Too many separate shapes for budget')
            if reducer == 'default' and budget == 384:
                return np.zeros((4, 3, 3)), faces, uv, None
            return np.zeros((4, 3, 3)), faces + 1, uv, None
        with mock.patch('npc_geometry.bake', side_effect=fake_bake), \
             mock.patch.dict('os.environ', {'AMIWIND_NPC_HEAD_REDUCER': 'locked'}):
            positions, proof = guard._reproduce_base([], [], {}, b'', 2, faces, uv, original, np.ones(3),
                                                     np.zeros(3), {'id': 'imperial guard'})
            self.assertEqual(os.environ['AMIWIND_NPC_HEAD_REDUCER'], 'locked')
        self.assertEqual(positions.shape, (4, 3, 3))
        self.assertEqual(proof, {'max_quant_steps_off': 0, 'coordinates_off': 0})
        self.assertEqual(calls[:5], [('locked', b) for b in (480, 384, 320, 256, 192)])
        self.assertEqual(calls[5:], [('default', 480), ('default', 384)])

    def test_no_reproduction_names_the_guard(self):
        from unittest import mock
        import prepare_guard_torches as guard
        faces, uv, original = self.arrays()
        with mock.patch('npc_geometry.bake', side_effect=ValueError('Too many separate shapes for budget')), \
             mock.patch.dict('os.environ', {'AMIWIND_NPC_HEAD_REDUCER': 'locked'}):
            # its own error type: prepare skips that guard and names it in the receipt (GUARD-TORCH-CHIM-FRAMES-44)
            with self.assertRaisesRegex(guard.BaseNotReproduced, 'Guard imperial guard: source bake does not reproduce'):
                guard._reproduce_base([], [], {}, b'', 2, faces, uv, original, np.ones(3), np.zeros(3),
                                      {'id': 'imperial guard'})

    def test_only_intro_actor_models_may_be_skipped(self):
        from prepare_guard_torches import check_skips
        check_skips([{'source_id': 'chargen boat guard 1', 'base_model': 'progs/np_deck.mdl', 'reason': 'x'}])
        with self.assertRaisesRegex(ValueError, 'Guard hlaalu guard_outside'):
            check_skips([{'source_id': 'hlaalu guard_outside', 'base_model': 'progs/a_bf6e2596469c.mdl',
                          'reason': 'Guard hlaalu guard_outside: source bake does not reproduce'}])

    def test_one_step_rounding_counts_as_reproduced_more_does_not(self):
        """v0.0.44-dev1: the boat guard's rebuild was 8 of 85,050 coordinates one quantisation step off."""
        import prepare_guard_torches as guard
        original = np.zeros((2, 100, 3)); scale = np.ones(3); origin = np.zeros(3)
        near = original.copy(); near[1, 0, 0] = 1.0
        self.assertEqual(guard._quantised_steps_off(near, original, scale, origin), (1, 1))
        far = original.copy(); far[1, 0, 0] = 3.0
        self.assertEqual(guard._quantised_steps_off(far, original, scale, origin), (3, 1))
        many = original.copy(); many[:, :, 0] = 1.0
        steps = guard._quantised_steps_off(many, original, scale, origin)
        self.assertGreater(steps[1], guard.MAX_SHARE_OFF * original.size)
        self.assertIsNone(guard._quantised_steps_off(original[:1], original, scale, origin))


if __name__=='__main__':unittest.main()
