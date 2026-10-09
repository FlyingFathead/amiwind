# SPDX-License-Identifier: GPL-3.0-only
import copy
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),
               str(Path(__file__).resolve().parents[1]/'tools')]
from mwad.interior import select_geometry, original_doors, read_interior, read_interiors
from prepare_harvest_room import append_registry, world_directory, exterior_target


def sub(tag,data):return tag.encode()+struct.pack('<I',len(data))+data
def record(tag,data,flags=0):return tag.encode()+struct.pack('<III',len(data),0,flags)+data
def ref(number,name='door',target=None,deleted=False,extra=b''):
    raw=sub('FRMR',struct.pack('<I',number))+sub('NAME',name.encode()+b'\0')
    raw+=sub('DATA',struct.pack('<6f',number,2,3,0,0,.5))
    if target is not None:
        raw+=sub('DODT',struct.pack('<6f',10+number,20,30,0,0,1.25))
        if target:raw+=sub('DNAM',target.encode()+b'\0')
    return raw+extra+(sub('DELE',bytes(4)) if deleted else b'')
def cell(name,refs,interior=True):
    raw=sub('NAME',name.encode()+b'\0')+sub('DATA',struct.pack('<Iii',int(interior),0,0))
    if interior:raw+=sub('AMBI',bytes(16))
    return record('CELL',raw+refs)
def door_source():
    return record('DOOR',sub('NAME',b'door\0')+sub('MODL',b'd/door.nif\0'))


class HarvestRoomTests(unittest.TestCase):
    def fixture(self):
        plant=dict(number=7,id='flora_01',type='CONT',model='f/plant.nif',cell='Room',
                   position=[1.,2.,3.],rotation_radians=[0.,0.,.5],scale=1.)
        room=dict(name='Room',master_sha256='1'*64,refs=[dict(plant),
                  dict(plant,number=8,id='other_container',model='o/chest.nif'),
                  dict(plant,number=9,id='floor',type='STAT',model='i/floor.nif')])
        return room,plant

    def test_exact_exclusion_preserves_every_other_selected_reference(self):
        room,plant=self.fixture()
        old,old_omitted=select_geometry(room)
        selected,omitted=select_geometry(room,harvest_references=[plant],harvest_master_sha256='1'*64)
        self.assertEqual(old_omitted,[]);self.assertEqual(selected,old[1:])
        self.assertEqual(omitted,[dict(reference=7,id='flora_01',reason='external harvest reference')])
        self.assertEqual(len(room['refs']),3)

    def test_exclusion_rejects_wrong_master_cell_identity_pose_or_type(self):
        room,plant=self.fixture()
        for field,value in [('cell','Other room'),('number',99),('id','other'),
                            ('model','different.nif'),('position',[0.,0.,0.]),
                            ('rotation_radians',[0.,0.,0.]),('scale',2.),('type','STAT')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                select_geometry(room,harvest_references=[dict(plant,**{field:value})],harvest_master_sha256='1'*64)
        with self.assertRaises(ValueError):select_geometry(room,harvest_references=[plant],harvest_master_sha256='2'*64)
        with self.assertRaises(ValueError):select_geometry(room,harvest_references=[plant,plant],harvest_master_sha256='1'*64)

    def test_original_directed_doors_do_not_synthesize_reverse_links(self):
        raw=door_source()+cell('A',ref(1,target='b'))+cell('B',b'')+cell('',ref(2,target='A'),False)
        links=original_doors(raw)
        self.assertEqual([(r['number'],r['source_cell'],r['destination_cell']) for r in links],[(1,'A','B'),(2,'','A')])
        self.assertEqual(links[0]['destination']['position'],[11.,20.,30.])
        self.assertAlmostEqual(links[0]['destination']['rotation_radians'][2],1.25)

    def test_actual_interior_arrival_is_available_without_an_exterior_entrance(self):
        raw=door_source()+cell('A',ref(1,target='B'))+cell('B',b'')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.esm';path.write_bytes(raw)
            self.assertEqual(read_interior(path,'B')['entrances'],[])
            result=read_interior(path,'B',include_interior_entrances=True)
            self.assertEqual([r['number'] for r in result['entrances']],[1])
            self.assertEqual(result['master_sha256'],hashlib.sha256(raw).hexdigest())

    def test_one_pass_reader_equals_one_call_per_cell(self):
        # BUILD-DOOR-REFERENCE-SERIAL-33: the door step reads all destination
        # cells in one pass; every cell must equal its own read_interior call.
        light=record('LIGH',sub('NAME',b'lamp\0')+sub('MODL',b'l/lamp.nif\0')
                     +sub('LHDT',struct.pack('<fiiI',1,2,3,256)+bytes([9,8,7,0])+struct.pack('<I',1)))
        raw=door_source()+light+cell('A',ref(1,target='B')+ref(3,name='lamp')+ref(4,name='lamp'))
        raw+=cell('B',ref(5,name='lamp')+ref(6,target='A'))+cell('C',b'')
        raw+=cell('',ref(2,target='A')+ref(7,target='B'),False)+cell('',ref(8,target='C'),False)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.esm';path.write_bytes(raw)
            for entrances in (False,True):
                names=['C','A','B']
                many=read_interiors(path,names,include_interior_entrances=entrances)
                single=[read_interior(path,n,include_interior_entrances=entrances) for n in names]
                self.assertEqual(many,single)
            many=read_interiors(path,['A','B'])
            self.assertEqual([r['number'] for r in many[0]['entrances']],[2])
            many[0]['refs'][1]['light']['radius']=1   # cells do not share base records
            self.assertEqual(many[1]['refs'][0]['light']['radius'],256)
            self.assertIs(many[0]['refs'][1]['light'],many[0]['refs'][2]['light'])  # refs of one cell do
            with self.assertRaisesRegex(ValueError,'Interior must resolve uniquely: D'):
                read_interiors(path,['A','D'])

    def test_unknown_non_door_and_deleted_references_are_not_arrivals(self):
        raw=door_source()+record('STAT',sub('NAME',b'fake\0')+sub('MODL',b'floor.nif\0'))
        raw+=cell('A',ref(1,target='B',deleted=True)+ref(2,name='fake',target='B'))+cell('B',b'')
        self.assertEqual(original_doors(raw),[])

    def test_door_state_is_retained_without_claiming_lock_support(self):
        lock=sub('FLTV',struct.pack('<i',50))+sub('KNAM',b'key_id\0')
        raw=door_source()+cell('A',ref(1,target='B',extra=lock))+cell('B',b'')
        fields={r['tag']:r['hex'] for r in original_doors(raw)[0]['original_subrecords']}
        self.assertEqual(fields['FLTV'],struct.pack('<i',50).hex());self.assertEqual(fields['KNAM'],b'key_id\0'.hex())

    def test_temporary_reference_section_marker_is_not_door_state(self):
        raw=door_source()+cell('A',ref(1,target='B')+sub('NAM0',struct.pack('<I',1))+ref(2))+cell('B',b'')
        door=original_doors(raw)[0]
        self.assertNotIn('NAM0',[f['tag'] for f in door['original_subrecords']])
        self.assertEqual(door['cell_reference_section_markers'],[
            dict(tag='NAM0',hex='01000000',after_reference=1)])

    def test_registry_appends_without_shifting_existing_or_terrain_ids(self):
        first=append_registry(['Z room'],'1'*64)
        after=append_registry(['A room','Z room'],'1'*64,first)
        self.assertEqual(after['entries'][0],first['entries'][0]);self.assertEqual(after['entries'][1]['id'],8253)
        self.assertEqual(after['reserved_terrain_ids'],[60,8251])
        self.assertTrue(all(len(r['map'])<=15 and len('harvest-'+r['map']+'.txt')<=30 for r in after['entries']))
        with self.assertRaises(ValueError):append_registry([],'2'*64,after)
        broken=copy.deepcopy(after);broken['entries'].reverse()
        with self.assertRaises(ValueError):append_registry([],'1'*64,broken)

    def test_world_arrival_matches_town_priority_and_preserves_authored_z(self):
        raw=b'AWR2'+struct.pack('<I',1)
        raw+=struct.pack('<7f',0,0,0,-10,-10,10,10)
        raw+=struct.pack('<7f',100,100,0,-10,-10,10,10)
        raw+=struct.pack('<8s11f',b'vf0000',0,0,0,-100,-100,100,100,-110,-110,110,110)
        regions=world_directory(raw)
        self.assertEqual(exterior_target([8,4,120],regions),('seyda',[2.,1.,30.]))
        self.assertEqual(exterior_target([80,40,160],regions),('vf0000',[20.,10.,40.]))
        with self.assertRaises(ValueError):exterior_target([10000,0,0],regions)
        with self.assertRaises(ValueError):world_directory(raw+b'bad')


if __name__=='__main__':unittest.main()
