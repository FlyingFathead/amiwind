# SPDX-License-Identifier: GPL-3.0-only
"""Original inventory group selection and zero-time skeleton sampling."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import player_inventory_pose as pose


class Rig:
    def __init__(self, events, offset=0):
        self.N=object(); self.events=events; self.parents={'root':None,'hand':'root'}
        self.offset=offset
    def local(self, name, time):
        result=np.eye(4)
        result[3,0]=self.offset+time if name=='root' else 7
        return result


def keys(*names):
    result={}
    for i,n in enumerate(names):
        result['inventory'+n+': start']=10.0+i*5
        result['inventory'+n+': stop']=11.0+i*5
    return result


class InventoryPoseTests(unittest.TestCase):
    def test_dedicated_start_and_fallbacks_drive_real_skeleton_matrices(self):
        rig=Rig(keys('handtohand','weapononehand','weapontwohand'))
        kit, rows=pose.plan(rig)
        self.assertEqual(len(rows),10)
        self.assertEqual([r['show_left'] for r in rows],
                         [True,True,True,False,True,False,False,False,True,False])
        for row in rows:
            expected=10 if row['frame']==0 else 20 if not row['show_left'] else 15
            self.assertEqual(row['time'],expected)
            self.assertEqual(kit.pose(row['frame'])('hand')[3,0],expected+7)
        self.assertEqual(rows[1]['requested'],'inventoryshortbladeonehand')
        self.assertEqual(rows[1]['group'],'inventoryweapononehand')

    def test_available_specific_pose_precedes_generic_female_fallback(self):
        base=Rig(keys('handtohand','weapononehand','weapontwohand','shortbladeonehand'))
        female=Rig(keys('weapononehand'),100)
        kit,rows=pose.plan(base,female)
        self.assertEqual(rows[1]['source'],'base')
        self.assertEqual(rows[2]['source'],'female')
        self.assertEqual(kit.pose(2)('hand')[3,0],117)
        self.assertEqual(kit.pose(1)('hand')[3,0],32)

    def test_missing_authored_pose_never_substitutes_ordinary_idle(self):
        for ev in (keys('weapononehand','weapontwohand'),keys('handtohand','weapononehand')):
            ev.update({'idle: start':1,'idle: stop':2})
            with self.assertRaisesRegex(ValueError,'Missing original inventory pose'):
                pose.plan(Rig(ev))

    def test_malformed_section_refused_and_single_key_pose_supported(self):
        ev=keys('handtohand','weapononehand','weapontwohand')
        ev['inventoryhandtohand: stop']=ev['inventoryhandtohand: start']
        self.assertEqual(pose.plan(Rig(ev))[1][0]['time'],10)
        for value in (None,float('nan'),float('inf'),-1):
            broken=dict(ev);broken['inventoryhandtohand: stop']=value
            with self.assertRaises(ValueError):pose.plan(Rig(broken))

    def test_bake_writes_real_ten_frame_alias_and_aligned_tags(self):
        from unittest.mock import patch
        from PIL import Image
        import actor_frames
        import npc_items
        rig=Rig(keys('handtohand','weapononehand','weapontwohand'))
        rig.parents.update({'weapon bone':'hand','shield bone':'hand'})
        appearance=dict(skeleton='synthetic',weight=1.0,height=1.0)
        frames=np.array([[[0,0,0],[4,0,0],[0,4,8],[4,4,8]]] * 10,dtype=float)
        faces=np.array([[0,1,2],[1,3,2]])
        uv=np.array([[0,0],[3,0],[0,3],[3,3]])
        skin=Image.new('P',(4,4))
        def bake(*args,**kwargs):
            kwargs['face_parts'].extend([17,17])
            return frames,faces,uv,skin
        with patch('prepare_player_view._sources',return_value=({},object(),{'synthetic':rig})), \
             patch('prepare_player_view.body_appearance',return_value=appearance), \
             patch('npc_geometry.assemble',return_value=([],[],[])), \
             patch('npc_geometry.bake',side_effect=bake):
            name,raw,tags,report=pose.bake_body(('synthetic',b'', 'nord',False))
        self.assertEqual(name,'progs/body/nord_m_i.mdl')
        self.assertEqual(actor_frames.numframes(raw),10)
        self.assertEqual(actor_frames.tag_frames(tags),10)
        self.assertEqual(report['frames'],10)
        self.assertEqual(len(report['poses']),10)
        self.assertEqual(report['bytes'],len(raw))
        self.assertEqual(report['poses'][0]['group'],'inventoryhandtohand')

    def test_asset_identity_is_separate_and_bounded(self):
        self.assertEqual(pose.inventory_path('progs/body/argonian_f.mdl'),'progs/body/argonian_f_i.mdl')
        for bad in ('other.mdl','progs/body/../x.mdl','progs/body/x.txt'):
            with self.assertRaises(ValueError):pose.inventory_path(bad)


if __name__=='__main__':unittest.main()
