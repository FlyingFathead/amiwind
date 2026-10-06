import copy,struct,unittest
from compact_bsp import entities,entity_bytes
from player_hull import lumps,pack_lumps
from replace_bsp_world import FORMATS
from test_replace_bsp_world import fixture as source_fixture
from remove_harvest_geometry import remove_geometry,verify_survivors

def fixture(shared=False):
    data=lumps(source_fixture(True));records=entities(data[0]);records[1].update(aw_ref='42',origin='1 2 3',angles='0 0 0')
    if shared:
        data[14]+=data[14][64:128]
        records.append(dict(classname='func_wall',aw_ref='43',model='*2',origin='7 8 9',angles='0 12 0',custom='survive exactly'))
    data[0]=bytearray(entity_bytes(records))
    ref=dict(type='CONT',kind='small_mushroom',number=42,id='test_mushroom',model='test.nif',position=[4,8,12],rotation_radians=[0,0,0],scale=1,
             source_key=['a'*64,'exterior',[0,0],42])
    return pack_lumps(data),ref

class RemoverTests(unittest.TestCase):
    def test_exact_target_removed_and_shared_surviving_faces_preserved(self):
        raw,ref=fixture(True);out,report=remove_geometry(raw,[ref],[0,0,0])
        self.assertEqual(report['compaction']['retained_models'],[0,2])
        self.assertEqual(report['proof']['collision_tree_comparisons'],8)
        es=entities(lumps(out)[0]);self.assertNotIn('42',[e.get('aw_ref') for e in es])
        self.assertEqual(es[-1],dict(classname='func_wall',aw_ref='43',model='*1',origin='7 8 9',angles='0 12 0',custom='survive exactly'))

    def test_missing_duplicate_ambiguous_and_non_mushroom_targets_rejected(self):
        raw,ref=fixture()
        for field,value in [('number',43),('kind','tree'),('type','STAT'),('source_key',None)]:
            bad=copy.deepcopy(ref);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):remove_geometry(raw,[bad],[0,0,0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):remove_geometry(raw,[ref,ref],[0,0,0])
        d=lumps(raw);e=entities(d[0]);e.append(e[1]);d[0]=bytearray(entity_bytes(e))
        with self.assertRaisesRegex(ValueError,'Duplicate original reference entity'):remove_geometry(pack_lumps(d),[ref],[0,0,0])

    def test_unexpected_entity_metadata_pose_or_world_binding_rejected(self):
        raw,ref=fixture()
        for field,value in [('origin','1.01 2 3'),('angles','0 1 0'),('script','important'),('model','*0'),('classname','door')]:
            d=lumps(raw);e=entities(d[0]);e[1][field]=value;d[0]=bytearray(entity_bytes(e))
            with self.subTest(field=field),self.assertRaises(ValueError):remove_geometry(pack_lumps(d),[ref],[0,0,0])
        d=lumps(raw);d[0]=d[0].replace(b'"aw_ref" "42"',b'"aw_ref" "42"\n"aw_ref" "42"')
        with self.assertRaisesRegex(ValueError,'Duplicate entity attribute'):remove_geometry(pack_lumps(d),[ref],[0,0,0])

    def test_render_pool_or_world_merged_target_cannot_be_silently_removed(self):
        raw,ref=fixture();d=lumps(raw);e=entities(d[0]);e[0]['aw_render_pool']='*1';d[0]=bytearray(entity_bytes(e))
        with self.assertRaisesRegex(ValueError,'Render-pool'):remove_geometry(pack_lumps(d),[ref],[0,0,0])
        d=lumps(raw);struct.pack_into('<2i',d[14],64+56,0,1)
        with self.assertRaisesRegex(ValueError,'world renderer'):remove_geometry(pack_lumps(d),[ref],[0,0,0])

    def test_independent_comparator_detects_survivor_geometry_uv_material_collision_entity_and_pvs_damage(self):
        raw,ref=fixture(True);out,report=remove_geometry(raw,[ref],[0,0,0]);retained=report['compaction']['retained_models']
        for lump,offset in [(3,0),(6,0),(2,60),(1,0),(4,0),(8,0)]:
            d=lumps(out);d[lump][offset]^=1
            with self.subTest(lump=lump),self.assertRaises(ValueError):verify_survivors(raw,pack_lumps(d),retained,{1})
        d=lumps(out);d[0]=d[0].replace(b'survive exactly',b'damaged values')
        with self.assertRaisesRegex(ValueError,'entity attributes'):verify_survivors(raw,pack_lumps(d),retained,{1})

if __name__=='__main__':unittest.main()
