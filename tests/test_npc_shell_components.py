# SPDX-License-Identifier: GPL-3.0-only
"""Overflow-only disconnected cloth preservation; no larger alias/animation budget."""
import unittest
from unittest.mock import patch
import numpy as np
import npc_geometry as g


def panels():
    vertices=[];faces=[]
    for offset in (0.,10.):
        base=len(vertices)
        vertices.extend([[offset+x,y,0.] for y in range(4) for x in range(4)])
        for y in range(3):
            for x in range(3):
                a=base+y*4+x;faces.extend([[a,a+1,a+5],[a,a+5,a+4]])
    return np.array(vertices),np.array(faces)


class ShellComponentTests(unittest.TestCase):
    def test_both_original_panels_keep_area_and_extent(self):
        p,f=panels();pp,ff=g.simplify_shell_components(p,f,8)
        self.assertLess(len(ff),len(f))
        for lo in (0.,10.):
            selected=ff[np.all(pp[ff][:,:,0]>=lo-1e-8,axis=1) &
                        np.all(pp[ff][:,:,0]<=lo+3.+1e-8,axis=1)]
            self.assertGreater(len(selected),0)
            tri=pp[selected];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()
            self.assertGreaterEqual(area,.8*18.)
            self.assertTrue(np.all(np.ptp(tri.reshape(-1,3),axis=0)>=.7*np.array([3.,3.,0.])))

    def test_one_connected_surface_keeps_existing_path(self):
        p,f=panels();self.assertIsNone(g.simplify_shell_components(p[:16],f[:18],4))

    def test_lost_component_is_error_not_permissive_fallback(self):
        p,f=panels()
        with patch.object(g,'simplify_shape',return_value=(np.array([[0.,0.,0.]]),np.empty((0,3),int))):
            with self.assertRaisesRegex(ValueError,'component lost'):
                g.simplify_shell_components(p,f,8)

    def test_successful_bake_never_uses_retry(self):
        sentinel=object();plan={'mode':'budget','face_limit':666,'quotas':[4],'protected':frozenset(),
                             'head_faces':0,'hair_reduced':False,'lod_only':False,'cuts':{}}
        with patch.object(g,'head_plan',return_value=plan),patch.object(g,'_bake',return_value=sentinel) as bake:
            self.assertIs(g.bake([],[],{},b'',head_detail='budget'),sentinel)
            self.assertEqual(bake.call_count,1);self.assertNotIn('shell_components',bake.call_args.kwargs)

    def test_only_alias_overflow_uses_same_inputs_and_unchanged_limit(self):
        shapes=[{'part':3}];sentinel=object();plan={'mode':'budget','face_limit':666,'quotas':[4],
                'protected':frozenset(),'head_faces':0,'hair_reduced':False,'lod_only':False,'cuts':{}}
        with patch.object(g,'head_plan',return_value=plan),patch.object(g,'_bake',side_effect=[g.AliasOverflow('Alias vertex budget exceeded',1),sentinel]) as bake:
            self.assertIs(g.bake(shapes,[],{},b'',head_detail='budget'),sentinel)
            self.assertEqual(bake.call_count,2);first,second=bake.call_args_list
            self.assertIs(first.args[0],second.args[0]);self.assertEqual(first.args[4],second.args[4]);self.assertEqual(second.args[4],666)
            self.assertTrue(second.kwargs['shell_components'])

    def test_full_sample_cap_reaches_only_overflow_retry(self):
        plan={'mode':'budget','face_limit':666,'quotas':[4],'protected':frozenset(),'head_faces':0,
              'hair_reduced':False,'lod_only':False,'cuts':{}}
        with patch.object(g,'head_plan',return_value=plan),patch.object(g,'_bake',side_effect=[g.AliasOverflow('Alias vertex budget exceeded'),object()]) as bake:
            g.bake([],[],{},b'',head_detail='budget',full_frame_budget=524288)
            self.assertNotIn('full_frame_budget',bake.call_args_list[0].kwargs)
            self.assertEqual(bake.call_args_list[1].kwargs['full_frame_budget'],524288)

    def test_full_sample_cap_refuses_before_texture_work(self):
        shape={'positions':np.repeat(np.array([[[0.,0.,0.],[1.,0.,0.],[0.,1.,1.]]]),64,axis=0),
               'faces':np.array([[0,1,2]]),'part':3}
        with patch.object(g.Image.Image,'quantize',side_effect=AssertionError('must refuse before texture work')):
            with self.assertRaisesRegex(g.AliasOverflow,'byte budget exceeded with full samples'):
                g._bake([shape],[],{},b'',666,None,[1],None,frozenset(),False,
                        shell_components=True,full_frame_budget=32)
        self.assertEqual(len(shape['positions']),64)

    def test_leg_or_second_overflow_is_still_failure(self):
        plan={'mode':'budget','face_limit':666,'quotas':[4],'protected':frozenset(),'head_faces':0,
              'hair_reduced':False,'lod_only':False,'cuts':{}}
        for errors,count in [([g.AliasOverflow('Player leg section collapsed')],1),
                             # the shell retry, then (locked head reducer, the default) the previous-reducer retry
                             ([g.AliasOverflow('Alias vertex budget exceeded')]*3,3)]:
            with patch.object(g,'head_plan',return_value=plan),patch.object(g,'_bake',side_effect=errors) as bake:
                with self.assertRaises(g.AliasOverflow):g.bake([],[],{},b'',head_detail='budget')
                self.assertEqual(bake.call_count,count)


if __name__=='__main__':unittest.main()
