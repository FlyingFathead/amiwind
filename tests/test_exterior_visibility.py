# SPDX-License-Identifier: GPL-3.0-only
"""Fictional meshes only: visibility provenance, fail-closed selection and collision."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),
               str(Path(__file__).resolve().parents[1]/'tools')]
import numpy as np
from exterior_visibility import (POLICY_FORMAT, VisibilityPolicyError,
    apply_exterior_selection, select_exterior_faces, source_visibility_issues)
from mwad.scene import pack_geometry, unpack_geometry
from prepare_scenery import model_geometry


def fixture():
    class Node:
        def __init__(self, children=(), hidden=False, properties=(), name=b'repeated'):
            self.children=children; self.flags=int(hidden); self.name=name; self.properties=properties
        def get_transform(self):return NS(as_list=lambda:np.eye(4).tolist())
    class Collision(Node):pass
    class Stencil:
        def __init__(self, mode, enabled=False):
            self.draw_mode=mode;self.stencil_enabled=int(enabled);self.flags=0
    class Material:pass
    class Texture:pass
    class Shape(Node):
        def __init__(self, **kwargs):
            super().__init__(**kwargs);self.skin_instance=None
            self.data=NS(num_vertices=3,num_triangles=1,num_uv_sets=0,uv_sets=[],
                has_vertex_colors=False,vertices=[NS(x=0,y=0,z=0),NS(x=4,y=0,z=0),NS(x=0,y=4,z=0)],
                get_triangles=lambda:[(0,1,2)])
    root=Node(properties=[Stencil(3)],children=[Shape(),None,
        Node(properties=[Stencil(1)],children=[Shape(),Shape(hidden=True)]),
        Collision(hidden=True,children=[Shape()])])
    class Data:
        roots=[root]
        def read(self, stream):pass
    return NS(Data=Data,NiAVObject=Node,NiNode=Node,RootCollisionNode=Collision,
              NiTriShape=Shape,NiStencilProperty=Stencil,NiMaterialProperty=Material,
              NiTexturingProperty=Texture),root


def model_fixture():
    v=np.array([[0,0,0,0,0,255,255,255,255],[4,0,0,1,0,255,255,255,255],
                [0,4,0,0,1,255,255,255,255],[0,0,4,1,1,255,255,255,255]],float)
    f=np.array([[0,2,1,0],[0,1,3,0],[0,3,2,0],[1,2,3,0]])
    m={'source':'meshes/fictional.nif','source_sha256':'a'*64,
       'materials':[{'source_shape':'same name','source_shape_path':'root[0]/children[2]',
           'source_face_range':{'start':0,'count':4},
           'source_visibility':{'draw_mode':1,'stencil_enabled':False}}]}
    policy={'format':POLICY_FORMAT,'models':[{'model':m['source'],'source_sha256':m['source_sha256'],
        'exclusions':[{'id':'fixture-enclosed-base','shape_path':'root[0]/children[2]',
            'triangles':[0],'classification':'verified_exterior_hidden',
            'evidence':'Synthetic tetrahedron base is the explicitly selected fixture surface.'}]}]}
    return v,f,m,policy


class VisibilityMetadataTests(unittest.TestCase):
    def test_inherited_override_hidden_collision_and_stable_paths(self):
        N,root=fixture();raw=b'NetImmerse File Format, Version 4.0.0.2\n'
        packet,materials,_,skipped=model_geometry(raw,N)
        self.assertEqual(len(unpack_geometry(packet)[1]),2)  # Both never duplicates triangles.
        self.assertEqual([m['source_visibility']['draw_mode'] for m in materials],[3,1])
        self.assertEqual([m['source_shape_path'] for m in materials],
            ['root[0]/children[0]','root[0]/children[2]/children[0]'])
        self.assertEqual(materials[1]['source_visibility']['origin_path'],'root[0]/children[2]')
        self.assertEqual([m['source_face_range'] for m in materials],[{'start':0,'count':1},{'start':1,'count':1}])
        self.assertEqual({s['reason'] for s in skipped},{'hidden_node','collision_node'})
        collision,_,_,_=model_geometry(raw,N,collision=True)
        self.assertEqual(len(unpack_geometry(collision)[1]),1)
        self.assertEqual(len(source_visibility_issues(materials)),1)

    def test_metadata_alone_does_not_flip_or_remove_geometry(self):
        N,root=fixture();raw=b'NetImmerse File Format, Version 4.0.0.2\n'
        before=model_geometry(raw,N)[0]
        root.properties[0].draw_mode=2
        after,materials,_,_=model_geometry(raw,N)
        self.assertEqual(before,after)
        self.assertEqual(source_visibility_issues(materials)[0]['draw_mode'],2)
        root.properties[0].draw_mode=0
        self.assertEqual(source_visibility_issues(model_geometry(raw,N)[1])[0]['draw_mode'],0)

    def test_real_tes3_nif_round_trip_retains_inherited_stencil(self):
        from prepare_scenery import nif_reader
        N=nif_reader();data=N.Data(version=0x04000002)
        root=N.NiNode();shape=N.NiTriShape();g=N.NiTriShapeData();shape.data=g
        root.name=b'fixture';shape.name=b'panel'
        root.num_children=1;root.children.update_size();root.children[0]=shape
        root.num_properties=1;root.properties.update_size();root.properties[0]=N.NiStencilProperty()
        root.properties[0].draw_mode=3
        g.num_vertices=3;g.has_vertices=True;g.vertices.update_size()
        for v,p in zip(g.vertices,[(0,0,0),(4,0,0),(0,4,0)]):v.x,v.y,v.z=p
        g.num_triangles=1;g.num_triangle_points=3;g.has_triangles=True;g.triangles.update_size()
        g.triangles[0].v_1=0;g.triangles[0].v_2=1;g.triangles[0].v_3=2
        data.roots=[root];stream=io.BytesIO();data.write(stream)
        packet,materials,_,_=model_geometry(stream.getvalue(),N)
        self.assertEqual(len(unpack_geometry(packet)[1]),1)
        self.assertEqual(materials[0]['source_visibility']['draw_mode'],3)
        self.assertEqual(materials[0]['source_visibility']['origin_path'],'root[0]')


class ExteriorPolicyTests(unittest.TestCase):
    def test_explicit_source_triangle_selection_preserves_input_and_reloads(self):
        v,f,m,policy=model_fixture();before=f.copy()
        selected=select_exterior_faces(policy,m['source'],m['source_sha256'],m['materials'],f,'exterior')
        m['exterior_visibility']=json.loads(json.dumps(selected))
        result=apply_exterior_selection(f,m)
        np.testing.assert_array_equal(result,f[1:])
        np.testing.assert_array_equal(f,before)
        self.assertEqual(selected['rules'][0]['resolved_packet_faces'],[0])
        self.assertIs(apply_exterior_selection(f,{**m,'exterior_visibility':None}),f)

    def test_wrong_context_hash_shape_face_and_unreviewed_rules_fail(self):
        _,f,m,policy=model_fixture()
        def resolve(p=policy, context='exterior', sha=m['source_sha256']):
            return select_exterior_faces(p,m['source'],sha,m['materials'],f,context)
        for context in ('interior',None):
            with self.assertRaises(VisibilityPolicyError):resolve(context=context)
        with self.assertRaises(VisibilityPolicyError):resolve(sha='b'*64)
        for field,value in [('shape_path','root[0]/children[99]'),('triangles',[4]),
                            ('triangles',[True]),('classification','candidate'),('evidence','')]:
            bad=copy.deepcopy(policy);bad['models'][0]['exclusions'][0][field]=value
            with self.assertRaises(VisibilityPolicyError):resolve(bad)
        bad=copy.deepcopy(policy);bad['models'][0]['exclusions'][0]['triangles']='all'
        with self.assertRaisesRegex(VisibilityPolicyError,'Whole-model'):resolve(bad)

    def test_retained_both_or_stencil_metadata_blocks_policy_acceptance(self):
        _,f,m,policy=model_fixture()
        for mode,enabled in [(3,False),(2,False),(0,False),(1,True)]:
            m['materials'][0]['source_visibility'].update(draw_mode=mode,stencil_enabled=enabled)
            with self.assertRaisesRegex(VisibilityPolicyError,'Unsupported retained'):
                select_exterior_faces(policy,m['source'],m['source_sha256'],m['materials'],f,'exterior')

    def test_edited_packet_ids_or_metadata_do_not_bypass_source_identity(self):
        _,f,m,policy=model_fixture()
        selection=select_exterior_faces(policy,m['source'],m['source_sha256'],m['materials'],f,'exterior')
        for key,value in [('excluded_packet_faces',[1]),('source_sha256','b'*64),('scene_kind','interior')]:
            m['exterior_visibility']={**selection,key:value}
            with self.assertRaises(VisibilityPolicyError):apply_exterior_selection(f,m)

    def test_mesh_stage_removes_only_visual_faces_preserving_collision(self):
        from prepare_mesh_bsp import _prepare_model
        v,f,m,policy=model_fixture()
        raw=pack_geometry([[*row[:5],*map(int,row[5:])] for row in v],f,1)
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'fixture.mwpak';archive.write_bytes(raw)
            m.update(offset=0,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),collision=None)
            _,baseline=_prepare_model((0,m,{},archive))
            m['exterior_visibility']=select_exterior_faces(policy,m['source'],m['source_sha256'],m['materials'],f,'exterior')
            _,candidate=_prepare_model((0,m,{},archive))
            self.assertEqual(len(baseline[2]),4);self.assertEqual(len(candidate[2]),3)
            np.testing.assert_array_equal(baseline[0],candidate[0])
            np.testing.assert_array_equal(baseline[1],candidate[1])
            self.assertEqual(len(baseline[3]),len(candidate[3]))
            for a,b in zip(baseline[3],candidate[3]):
                np.testing.assert_array_equal(a[0],b[0]);self.assertEqual(a[2:],b[2:])
            self.assertEqual(candidate[4]['exterior_visibility']['excluded_triangles'],1)
            with self.assertRaisesRegex(VisibilityPolicyError,'flattening'):
                _prepare_model((0,m,{'flatten':{'fixture':True}},archive))


class AutomaticHiddenSurfaceTests(unittest.TestCase):
    @staticmethod
    def cube_with_faces(extra, *, close=True):
        # Explicit outward cube surface, not a generated convex hull occluder.
        v=np.array([[-2,-2,-2],[2,-2,-2],[2,2,-2],[-2,2,-2],
                    [-2,-2,2],[2,-2,2],[2,2,2],[-2,2,2]],float)
        quads=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        f=[]
        for a,b,c,d in quads[:6 if close else 5]:f.extend([(a,b,c,0),(a,c,d,0)])
        for tri in extra:
            start=len(v);v=np.concatenate((v,np.asarray(tri,float)));f.append((start,start+1,start+2,1))
        return v,np.array(f),[{'alpha':1,'vertex_alpha_opaque':True} for _ in range(2)]

    def test_closed_opaque_shell_removes_only_strictly_enclosed_whole_triangles(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        inside=[[-.5,-.5,0],[.5,-.5,0],[0,.5,0]]
        crossing=[[-.5,-.5,0],[3,-.5,0],[0,.5,0]]
        touching=[[-.5,-.5,2],[.5,-.5,2],[0,.5,2]]
        outside=[[3,0,0],[4,0,0],[3,1,0]]
        v,f,m=self.cube_with_faces([inside,crossing,touching,outside]);original=f.copy()
        result,audit=auto_cull_hidden_surfaces(v,f,m)
        self.assertEqual(audit['removed_face_ids'],[12])
        self.assertEqual(audit['certified_occluders'],1)
        np.testing.assert_array_equal(result,f[[*range(12),13,14,15]])
        np.testing.assert_array_equal(f,original)
        self.assertGreater(audit['witnesses'][0]['minimum_support_plane_clearance'],1)

    def test_open_shell_is_not_closed_by_hull_or_near_vertex_welding(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        tri=[[0,0,0],[.5,0,0],[0,.5,0]]
        for close in (False,True):
            v,f,m=self.cube_with_faces([tri],close=close)
            if close:
                # One triangle corner is almost coincident, but creates a real opening.
                v=np.concatenate((v,[v[0]+[0,0,1e-10]]));f[0,0]=len(v)-1
            result,audit=auto_cull_hidden_surfaces(v,f,m)
            self.assertEqual(audit['removed_face_ids'],[])
            np.testing.assert_array_equal(result,f)

    def test_texture_vertex_alpha_and_draw_uncertainty_do_not_occlude(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        v,f,m=self.cube_with_faces([[[0,0,0],[.5,0,0],[0,.5,0]]])
        for change in ({'alpha':.5},{'texture_source':'fictional.dds'},
                       {'texture_source':'fictional.dds','texture_alpha_opaque':False},
                       {'source_visibility':{'draw_mode':2}}):
            mm=copy.deepcopy(m);mm[0].update(change)
            self.assertEqual(auto_cull_hidden_surfaces(v,f,mm)[1]['removed_face_ids'],[])
        mm=copy.deepcopy(m);mm[0].update(texture_source='fictional.dds',texture_alpha_opaque=True)
        self.assertEqual(auto_cull_hidden_surfaces(v,f,mm)[1]['removed_face_ids'],[12])
        vv=np.column_stack((v,np.zeros((len(v),2)),np.full((len(v),4),255)))
        vv[0,8]=254
        self.assertEqual(auto_cull_hidden_surfaces(vv,f,mm)[1]['removed_face_ids'],[])

    def test_inward_wound_occluder_nonmanifold_and_nonconvex_remain(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        v,f,m=self.cube_with_faces([[[0,0,0],[.5,0,0],[0,.5,0]]])
        reverse=f.copy();reverse[:12,:3]=reverse[:12,:3][:,::-1]
        self.assertEqual(auto_cull_hidden_surfaces(v,reverse,m)[1]['removed_face_ids'],[])
        duplicate=np.concatenate((f,f[:1]))
        self.assertEqual(auto_cull_hidden_surfaces(v,duplicate,m)[1]['removed_face_ids'],[])
        vv=v.copy();vv[6]=[0,0,0]
        self.assertEqual(auto_cull_hidden_surfaces(vv,f,m)[1]['removed_face_ids'],[])

    def test_disabled_and_interior_modes_preserve_every_face(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        v,f,m=self.cube_with_faces([[[0,0,0],[.5,0,0],[0,.5,0]]])
        for kwargs in ({'enabled':False},{'scene_kind':'interior'}):
            result,audit=auto_cull_hidden_surfaces(v,f,m,**kwargs)
            np.testing.assert_array_equal(result,f);self.assertEqual(audit['removed_face_ids'],[])

    def test_source_order_ids_and_precision_boundary_are_preserved(self):
        from exterior_visibility import auto_cull_hidden_surfaces
        v,f,m=self.cube_with_faces([[[0,0,2-1e-7],[.5,0,2-1e-7],[0,.5,2-1e-7]],
                                  [[0,0,-1],[0,.5,-1],[.5,0,-1]]])
        result,audit=auto_cull_hidden_surfaces(v,f,m)
        self.assertEqual(audit['removed_face_ids'],[13])
        np.testing.assert_array_equal(result,f[:13])

    def test_exact_orientation_rejects_an_outside_nearly_coplanar_point(self):
        from exterior_visibility import _hidden_orient_sign
        self.assertEqual(_hidden_orient_sign([0,0,0],[1,0,0],[0,1,0],[.5,.5,1e-100]),1)
        self.assertEqual(_hidden_orient_sign([0,0,0],[1,0,0],[0,1,0],[.5,.5,-1e-100]),-1)


if __name__=='__main__':unittest.main()
