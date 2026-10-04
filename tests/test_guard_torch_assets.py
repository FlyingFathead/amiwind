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


if __name__=='__main__':unittest.main()
