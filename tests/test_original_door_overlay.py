# SPDX-License-Identifier: GPL-3.0-only
import copy
import math
from pathlib import Path
import tempfile
import unittest
from test_harvest_room import door_source,cell,ref,sub
from test_world_flora_integration import packet_fixture
from test_replace_bsp_world import fixture,PALETTE,face_semantics
from prepare_original_door_overlay import select_doors,append_geometry
from compact_bsp import entities
from player_hull import lumps


class OriginalDoorOverlayTests(unittest.TestCase):
    def test_selects_only_authored_exterior_loading_entrances(self):
        raw=door_source()+cell('',ref(42,target='Room'),False)+cell('Room',ref(43,target=''))
        selected=select_doors(raw,[42]);self.assertEqual(selected[0]['number'],42)
        self.assertEqual(selected[0]['destination']['position'],[52,20,30])
        for numbers in ([],[42,42],[999],[43]):
            with self.subTest(numbers=numbers),self.assertRaises(ValueError):select_doors(raw,numbers)

    def test_original_locked_owned_or_scripted_doors_are_not_silently_unlocked(self):
        for extra in (sub('FLTV',bytes([10,0,0,0])),sub('ANAM',b'owner\0')):
            raw=door_source()+cell('',ref(42,target='Room',extra=extra),False)+cell('Room',b'')
            with self.assertRaisesRegex(ValueError,'lock/script/ownership'):select_doors(raw,[42])

    def test_actual_original_transform_collision_and_retained_geometry_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);model,index=packet_fixture(root)
            profile=dict(ratio=1.,texture_size=64,preserve_shared_seams=True)
            index['groups']={'door':dict(visual_profiles={model['source']:profile})}
            ref=index['references'][0];ref['type']='DOOR';original=copy.deepcopy(index)
            source=root/'base.bsp';source.write_bytes(fixture(True));palette=root/'palette';palette.write_bytes(PALETTE)
            entry=dict(name='vf0000',origin=[3,4,-20],coverage=[[-100,-100],[100,100]])
            target=root/'new.bsp'
            report=append_geometry(source,target,root/'source/scenery.mwpak',index,entry,palette,root/'work')
            self.assertEqual(report['references'],[1]);self.assertEqual(index,original)
            old,new=lumps(source.read_bytes()),lumps(target.read_bytes())
            for model_id in (0,1):self.assertEqual(face_semantics(source.read_bytes(),model_id),face_semantics(target.read_bytes(),model_id))
            self.assertEqual(entities(new[0])[:-1],entities(old[0]));added=entities(new[0])[-1]
            self.assertEqual(added['aw_ref'],'1');self.assertEqual(list(map(float,added['origin'].split())),[7,8.5,35])
            self.assertAlmostEqual(float(added['angles'].split()[1]),-math.degrees(.8))
            self.assertGreater(len(new[9]),len(old[9]));self.assertGreater(len(new[7]),len(old[7]))
            with self.assertRaisesRegex(ValueError,'already present'):
                append_geometry(target,root/'duplicate.bsp',root/'source/scenery.mwpak',index,entry,palette,root/'duplicate-work')
            self.assertFalse((root/'duplicate.bsp').exists())


if __name__=='__main__':unittest.main()
