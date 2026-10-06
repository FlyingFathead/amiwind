# SPDX-License-Identifier: GPL-3.0-only
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_hands import appearance_parts,nord_parts


class HandAppearances(unittest.TestCase):
    def body(self,part=5,race='nord',female=False,flags=0,kind=0,vampire=0,mesh='skin.nif'):
        return [('BYDT',bytes((part,vampire,flags|int(female),kind))),
                ('FNAM',race.encode()+b'\0'),('MODL',mesh.encode()+b'\0')]

    def test_race_sex_and_first_person_priority(self):
        bodies={'nord_m':self.body(),'nord_m.1st':self.body(mesh='male.nif'),
                'nord_f.1st':self.body(female=True,mesh='female.nif'),
                'khajiit_m.1st':self.body(race='khajiit',mesh='beast.nif')}
        kinds={'RACE':{'nord':[],'khajiit':[]},'BODY':bodies}
        for race,sex,mesh in [('nord',False,'male.nif'),('nord',True,'female.nif'),('khajiit',False,'beast.nif')]:
            parts=appearance_parts(kinds,race,sex)
            self.assertEqual([p['slot'] for p in parts],[6,7])
            self.assertEqual([p['mesh'] for p in parts],[mesh,mesh])
        self.assertEqual(nord_parts(kinds),appearance_parts(kinds,'nord',False))

    def test_same_race_fallback_order_and_unusable_records(self):
        bodies={'male.1st':self.body(mesh='male-first.nif'),
                'female':self.body(female=True,mesh='female-third.nif'),
                'zz-nonplayable.1st':self.body(female=True,flags=2),
                'zz-vampire.1st':self.body(female=True,vampire=1),
                'zz-clothing.1st':self.body(female=True,kind=1)}
        kinds={'RACE':{'nord':[]},'BODY':bodies}
        self.assertEqual(appearance_parts(kinds,'nord',True)[0]['mesh'],'female-third.nif')
        del bodies['female']
        self.assertEqual(appearance_parts(kinds,'nord',True)[0]['mesh'],'male-first.nif')
        del bodies['male.1st']
        with self.assertRaises(ValueError):appearance_parts(kinds,'nord',True)

    def test_missing_race_never_borrows_a_different_race(self):
        kinds={'RACE':{'nord':[],'argonian':[]},'BODY':{'nord.1st':self.body()}}
        with self.assertRaises(ValueError):appearance_parts(kinds,'argonian')
        with self.assertRaises(ValueError):appearance_parts(kinds,'unknown')
        with self.assertRaises(ValueError):appearance_parts(kinds,'nord',1)


    def test_catalogue_records_are_bounded_and_keep_race_sex_pairs(self):
        import struct
        from prepare_hand_catalog import model_paths,pack_catalog
        entries=[]
        for race in ('nord','dark elf','khajiit'):
            for female in (False,True):
                hand,torch=model_paths(race,female)
                entries.append(dict(race=race,female=female,hand_model=hand,torch_model=torch))
        raw=pack_catalog(entries)
        self.assertEqual(struct.unpack_from('>4sHH',raw),(b'AWH1',6,196))
        self.assertEqual(len(raw),8+6*196)
        self.assertEqual(raw[8+3*196+64],1)
        self.assertIn(b'progs/hands/dark_elf_f_t.mdl',raw)
        with self.assertRaises(ValueError):pack_catalog(entries+[entries[0]])
        with self.assertRaises(ValueError):model_paths('../nord',False)
        with self.assertRaises(ValueError):pack_catalog([dict(entries[0],hand_model='progs/v_nord.mdl')])
        with self.assertRaises(ValueError):pack_catalog([])


    def test_source_topology_keeps_shared_vertices_animation_and_repeated_uv(self):
        import numpy as np
        from hand_geometry import bake_source_hands
        positions=np.array([[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
                            [[0,0,0],[1,0,1],[1,1,2],[0,1,1]]],float)
        triangles=np.array([[0,1,2],[0,2,3]])
        uv=np.array([[-.25,0],[1.25,0],[1.25,1],[-.25,1]])
        shape=dict(positions=positions,faces=triangles,uv=uv,colours=np.ones((4,4)),material=0)
        texture=np.repeat((np.arange(16,dtype=np.uint8)*16).reshape(4,4,1),3,axis=2)
        palette=np.repeat(np.arange(256,dtype=np.uint8),3).tobytes()
        frames,faces,coords,skin=bake_source_hands([shape],[dict(texture_index='skin',diffuse=[1,1,1])],{'skin':texture},palette)
        np.testing.assert_array_equal(frames,positions)
        np.testing.assert_array_equal(faces,triangles[:,[0,2,1]])
        self.assertEqual(frames.shape[1],4) # no face-local expansion
        self.assertEqual(coords[1,0]-coords[0,0],6) # retain1.5texture repeats
        pixels=np.array(skin)
        for original,at in zip(uv,coords):
            x,y=at.astype(int);expected=texture[int(original[1]*4)%4,int(original[0]*4)%4,0]
            self.assertLessEqual(abs(int(pixels[y,x])-int(expected)),3) # palette quantizer cache precision
        self.assertLessEqual(skin.height,480)
        shape['colours'][1,3]=.5
        with self.assertRaises(ValueError):bake_source_hands([shape],[dict(texture_index='skin',diffuse=[1,1,1])],{'skin':texture},palette)


    def test_gradient_tint_keeps_shared_edge_trajectories_through_quantization(self):
        import numpy as np
        from hand_geometry import bake_source_hands
        from npc_geometry import animated_mdl
        from prepare_hand_sprites import decode_mdl
        positions=np.array([[[0,0,0],[2,0,0],[2,2,0],[0,2,0]],
                            [[0,0,1],[2,0,2],[2,2,3],[0,2,2]]],float)
        triangles=np.array([[0,1,2],[0,2,3]])
        colours=np.ones((4,4));colours[:,0]=[.1,.3,.7,1]
        shape=dict(positions=positions,faces=triangles,uv=np.array([[0,0],[1,0],[1,1],[0,1.]]),colours=colours,material=0)
        palette=np.repeat(np.arange(256,dtype=np.uint8),3).tobytes()
        frames,faces,coords,skin=bake_source_hands([shape],[dict(texture_index=None,diffuse=[1,1,1])],{},palette)
        self.assertEqual(len(faces),2)
        for actual,source in zip(faces,triangles):
            np.testing.assert_array_equal(frames[:,actual],positions[:,source[[0,2,1]]])
        decoded,_,_,_=decode_mdl(animated_mdl(frames,faces,coords,skin))
        np.testing.assert_array_equal(decoded[:,0],decoded[:,3])
        np.testing.assert_array_equal(decoded[:,2],decoded[:,4])

    def test_material_boundary_keeps_joint_seam_at_every_pose(self):
        import numpy as np
        from hand_geometry import bake_source_hands
        from npc_geometry import animated_mdl
        from prepare_hand_sprites import decode_mdl
        positions=np.array([[[0,0,0],[2,0,0],[0,2,0],[2,2,0]],
                            [[0,0,0],[2,0,2],[0,2,1],[2,2,3]]],float)
        shapes=[]
        for material,indices in enumerate(([0,1,2],[1,3,2])):
            shapes.append(dict(positions=positions[:,indices],faces=np.array([[0,1,2]]),
                               uv=np.array([[0,0],[1,0],[0,1.]]),colours=np.ones((3,4)),material=material))
        palette=np.repeat(np.arange(256,dtype=np.uint8),3).tobytes()
        materials=[dict(texture_index=None,diffuse=[1,1,1]),dict(texture_index=None,diffuse=[.5,.5,.5])]
        frames,faces,uv,skin=bake_source_hands(shapes,materials,{},palette)
        decoded,_,_,_=decode_mdl(animated_mdl(frames,faces,uv,skin))
        np.testing.assert_array_equal(decoded[:,1],decoded[:,3])
        np.testing.assert_array_equal(decoded[:,2],decoded[:,5])


    def test_source_oracle_rejects_new_holes_winding_and_animated_seam_tears(self):
        import numpy as np
        from hand_geometry import audit_source_topology
        points=np.array([[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
                         [[0,0,0],[1,0,1],[1,1,2],[0,1,1]]],float)
        faces=np.array([[0,1,2],[0,2,3]])
        source=[dict(positions=points,faces=faces)]
        emitted=points[:,[0,1,2,0,2,3]].copy();target=np.array([[0,2,1],[3,5,4]])
        result=audit_source_topology(source,emitted,target)
        self.assertEqual(result['authored_open_boundary_edges'],4)
        self.assertEqual(result['new_boundary_edges'],0)
        with self.assertRaises(ValueError):audit_source_topology(source,emitted,target[:1])
        with self.assertRaises(ValueError):audit_source_topology(source,emitted,target[:,[0,2,1]])
        emitted[1,3,2]+=.01 # identical rest pose cannot hide a later seam tear
        with self.assertRaises(ValueError):audit_source_topology(source,emitted,target)
