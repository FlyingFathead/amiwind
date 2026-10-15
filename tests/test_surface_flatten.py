"""Panel projection preserves source geometry and supports an off switch."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from surface_flatten import bake_panel, load_profiles, mounting_shift, mount_references, NeighboringFacadeSupport


class NeighboringFacadeTests(unittest.TestCase):
    @staticmethod
    def ref(number, model_index=0, position=(1, 0, 1), **extra):
        return dict(number=number, id='house', model_index=model_index,
                    position=list(position), rotation_radians=[0, 0, 0], scale=1, **extra)

    @staticmethod
    def wall(y=2):
        v=np.array([[0,y,0],[2,y,0],[2,y,2],[0,y,2]],float)
        f=np.array([[0,1,2,0],[0,2,3,0]])
        return v,f

    def test_cross_cell_support_repairs_window_without_adding_placements(self):
        from copy import deepcopy
        window=self.ref(10)
        selected=[window]
        index={'models':[{'source':'window.nif'}], 'references':deepcopy(selected)}
        model=(*self.wall(),None,None,{'flatten':{'axis':1,'facing':-1,'mounting_plane':0}})
        models={0:model}
        before=deepcopy(index)
        with self.assertRaisesRegex(ValueError,'No supporting'):
            mount_references(index,selected,models,(0,0),1)
        support=NeighboringFacadeSupport(Path('/unused'),{},[10])
        v,f=self.wall()
        support.walls=[(v[f[:,:3]],{'number':20,'cell':[-1,0]})]
        mount_references(index,selected,models,(0,0),1,support=support)
        self.assertAlmostEqual(window['_flatten_shift'],-1.5)
        self.assertEqual([r['number'] for r in selected],[10])
        self.assertEqual(index,before)
        np.testing.assert_array_equal(model[0],self.wall()[0])
        self.assertEqual(support.report['used'][0]['support']['number'],20)

    def test_supported_local_window_never_loads_neighbours(self):
        from unittest.mock import Mock
        refs=[self.ref(10),self.ref(20,1,position=(0,0,0))]
        v,f=self.wall()
        models={0:(v,f,None,None,{'flatten':{'axis':1,'facing':-1,'mounting_plane':0}}),
                1:(v,f,None,None,{})}
        support=Mock(side_effect=AssertionError('unnecessary owned input read'))
        mount_references({'models':[{'source':'window.nif'},{'source':'house.nif'}]},refs,models,(0,0),1,support=support)
        support.assert_not_called()
        self.assertAlmostEqual(refs[0]['_flatten_shift'],-1.5)

    def test_neighbour_loader_filters_cells_deleted_refs_types_and_selected_owners(self):
        from unittest.mock import patch
        from mwad.scene import pack_geometry
        settings={'source_cell':[0,0],'source_radius':0,'centre':[0,0],'scale':1}
        master={'sha256':'master-hash','objects':{'house':{'type':'STAT','model':'x/house.nif'},
                                               'container':{'type':'CONT','model':'x/house.nif'}},
                'cells':{(0,0):{'refs':[self.ref(10)]},
                         (-1,0):{'refs':[self.ref(20,position=(0,0,0)),
                                         self.ref(21,deleted=True),
                                         dict(self.ref(22),id='container')]},
                         (2,0):{'refs':[self.ref(30)]}}}
        v,f=self.wall();packet=pack_geometry([list(point)+[0.,0.,255,255,255,255] for point in v],f.tolist(),1)
        support=NeighboringFacadeSupport('/owned',settings,[10])
        with patch('mwad.paths.child_ci',side_effect=lambda root,name:root/name), \
             patch('mwad.audit.load_esm',return_value=master),patch('mwad.audit.BSA'), \
             patch('prepare_scenery.nif_reader'), \
             patch('prepare_scenery.bsa_read',return_value=b'owned-source') as read, \
             patch('prepare_scenery.model_geometry',return_value=(packet,[],[],[])) as geometry:
            self.assertAlmostEqual(support(self.ref(10),[1,0,1],[0,-1,0]),-1.5)
            self.assertAlmostEqual(support(self.ref(11),[1,0,1],[0,-1,0]),-1.5)
        read.assert_called_once();geometry.assert_called_once()
        self.assertEqual(len(support.walls),1)
        self.assertEqual(support.report['source_esm_sha256'],'master-hash')
        self.assertEqual(support.report['used'][0]['support']['cell'],[-1,0])
        self.assertEqual(support.report['used'][0]['support']['position'],[0,0,0])

    def test_nearest_source_hit_wins_and_missing_support_still_fails(self):
        support=NeighboringFacadeSupport('/unused',{},[])
        a,f=self.wall(2);b,_=self.wall(4)
        support.walls=[(b[f[:,:3]],{'number':20}), (a[f[:,:3]],{'number':21})]
        # Ray starts at y=-16 and moves inward: the y=2 wall is first.
        self.assertAlmostEqual(support(self.ref(10),[1,0,1],[0,-1,0]),-1.5)
        self.assertEqual(support.report['used'][0]['support']['number'],21)
        with self.assertRaisesRegex(ValueError,'including neighbouring'):
            support(self.ref(10),[100,0,1],[0,-1,0])

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0,
                         'real protected pool writes require a non-root POSIX user')
    def test_source_support_receipt_survives_real_cell_pool_without_work_directory(self):
        from chimport import CellPool
        support=NeighboringFacadeSupport('/unused',{},[])
        v,f=self.wall()
        support.walls=[(v[f[:,:3]],{'number':20,'cell':[-1,0],
                                  'model':'meshes/x/house.nif','source_sha256':'a'*64})]
        support.report['source_esm_sha256']='b'*64
        support(self.ref(10),[1,0,1],[0,-1,0])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'cell';out.mkdir();(out/'work').mkdir()
            source={'frames':[{'placements':[{'ref':10,'cell':[0,0]}],
                               'window_mount_support':support.report}]}
            (out/'chim-source.json').write_text(json.dumps(source))
            (out/'work/window-mount-support.json').write_text(json.dumps(support.report))
            pool=CellPool(root/'pool',link=False)
            pool.store(out,'c'*64,{'cell':[0,0],'converted':True,'errors':[]})
            restored=root/'restored';restored.mkdir()
            self.assertIsNotNone(pool.fetch('c'*64,restored))
            self.assertFalse((restored/'work').exists())
            got=json.loads((restored/'chim-source.json').read_text())
            self.assertEqual(got,source)
            self.assertEqual(got['frames'][0]['placements'],[{'ref':10,'cell':[0,0]}])
            self.assertEqual(got['frames'][0]['window_mount_support']['used'][0]['support']['number'],20)


class SurfaceFlattenTests(unittest.TestCase):
    def test_front_texture_winding_and_sources(self):
        v=np.array([[x,y,z,u,w,255,255,255,255] for y in (-2,2)
                    for x,z,u,w in [(0,0,0,0),(2,0,1,0),(2,2,1,1),(0,2,0,1)]],float)
        f=np.array([[0,1,2,0],[0,2,3,0],[4,5,6,1],[4,6,7,1]])
        before_v,before_f=v.copy(),f.copy()
        colors=[np.full((2,2,3),[120,30,10],dtype=np.uint8),np.full((2,2,3),[10,30,120],dtype=np.uint8)]
        out,faces,rgb,report=bake_panel(v,f,[{'diffuse':[1,1,1]}]*2,lambda i:colors[i],
            {'axis':1,'facing':-1,'plane':0,'texture_size':16,'type':'decorative_windows'})
        np.testing.assert_array_equal(v,before_v)
        np.testing.assert_array_equal(f,before_f)
        np.testing.assert_array_equal(out[:,1],0)
        np.testing.assert_array_equal(rgb,np.broadcast_to([120,30,10],rgb.shape))
        self.assertLess(np.cross(out[1,:3]-out[0,:3],out[2,:3]-out[0,:3])[1],0)
        self.assertEqual(len(faces),2)
        self.assertEqual(report['collision'],'unchanged source geometry')

    def test_type_off_removes_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            for enabled in (True,False):
                p.write_text(json.dumps({'types':{'windows':{'flatten':enabled,'models':{'window.nif':{'axis':1}}}}}))
                self.assertEqual(bool(load_profiles(p)),enabled)
            p.write_text('{"types":{"windows":{"flatten":"false","models":{}}}}')
            with self.assertRaises(ValueError):load_profiles(p)

    def test_shipped_profiles_are_exterior_only(self):
        self.assertIn('meshes/x/ex_nord_win_01.nif', load_profiles())
        self.assertEqual(load_profiles(scene_kind='interior'), {})
        with self.assertRaises(ValueError):
            load_profiles(scene_kind='unknown')

    def test_interior_bsp_keeps_window_without_house_support(self):
        """Run the BSP assembly path that aborted the Tradehouse/Warehouse.

        A deliberately small, asset-free window has two visible faces and no
        supporting house. Interior conversion must retain both authored faces
        and the same collision data as an explicitly unflattened conversion.
        """
        import hashlib
        import struct
        from unittest.mock import patch
        from mwad.scene import pack_geometry
        from player_hull import pack_lumps
        from prepare_mesh_bsp import append_meshes
        v = [[x,y,z,u,w,255,255,255,255] for y in (-2,2)
             for x,z,u,w in [(0,0,0,0),(8,0,1,0),(8,8,1,1),(0,8,0,1)]]
        f = [[0,1,2,0],[0,2,3,0],[4,5,6,0],[4,6,7,0]]
        raw = pack_geometry(v,f,1)
        model = {'source':'meshes/x/ex_nord_win_01.nif','offset':0,
                 'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                 'triangles':len(f),'materials':[{'texture_index':None,'diffuse':[1,1,1]}]}
        ref = {'number':1,'model_index':0,'scale':1,'position':[0,0,0],
               'rotation_radians':[0,0,0]}
        index = {'cell':'Synthetic Warehouse','models':[model],
                 'textures':[],'references':[ref]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'scenery-index.json').write_text(json.dumps(index))
            (root/'scenery.mwpak').write_bytes(raw)
            (root/'palette.lmp').write_bytes(bytes(range(256))*3)
            sections = [b'']*15
            sections[0] = b'{\n"classname" "worldspawn"\n}\n\0'
            sections[2] = struct.pack('<i',0)
            sections[10] = struct.pack('<i',-1)+bytes(24)
            sections[14] = bytes(64)
            (root/'base.bsp').write_bytes(pack_lumps(sections))
            def convert(name):
                return append_meshes(root/'base.bsp',root/name,root,
                                     root/'palette.lmp',centre=(0,0),jobs=1,
                                     references=[1])
            report = convert('interior.bsp')
            self.assertEqual(report['instances'],1)
            self.assertEqual(report['models'][0]['faces'],2)
            self.assertNotIn('flatten',report['models'][0]['visual_lod'])
            self.assertGreater(report['clipnodes'],0)
            with patch('surface_flatten.load_profiles', return_value={}):
                convert('authored.bsp')
            self.assertEqual((root/'interior.bsp').read_bytes(),
                             (root/'authored.bsp').read_bytes())
            # The exterior mounting guard still fails on unsupported geometry.
            del index['cell']
            (root/'scenery-index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError,'No supporting'):
                convert('unsupported-exterior.bsp')

    def test_mounting_follows_wall_and_rejects_missing_support(self):
        wall=np.array([[[0,2,0],[2,2,0],[2,2,2]],[[0,2,0],[2,2,2],[0,2,2]]],float)
        self.assertAlmostEqual(mounting_shift([1,0,1],[0,-1,0],wall),-1.5)
        with self.assertRaises(ValueError):mounting_shift([10,0,1],[0,-1,0],wall)
        with self.assertRaises(ValueError):mounting_shift([1,0,1],[0,1,0],wall)

    def test_flatten_only_profile_runs_through_converter(self):
        from mwad.scene import pack_geometry
        from prepare_mesh_bsp import _prepare_model
        import hashlib
        v=[[x,y,z,u,w,255,255,255,255] for y in (-2,2)
           for x,z,u,w in [(0,0,0,0),(8,0,1,0),(8,8,1,1),(0,8,0,1)]]
        f=[[0,1,2,0],[0,2,3,0],[4,5,6,0],[4,6,7,0]]
        raw=pack_geometry(v,f,1)
        record={'source':'window.nif','offset':0,'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest(),
                'materials':[{'texture_index':None,'diffuse':[1,1,1]}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'scene.mwpak';p.write_bytes(raw)
            _,data=_prepare_model((0,record,{'flatten':{'axis':1,'facing':-1,'plane':0,
                                  'type':'windows'}},p,[]))
            self.assertEqual(len(data[2]),1)
            self.assertTrue(data[3])
            self.assertEqual(p.read_bytes(),raw)
            np.testing.assert_array_equal(data[0],v)

    def test_two_sided_door_panel_keeps_original_collision(self):
        from mwad.scene import pack_geometry
        from prepare_mesh_bsp import _prepare_model
        from chim.units import _canonical
        import hashlib
        v=[[x,y,z,u,w,255,255,255,255] for y in (-2,2)
           for x,z,u,w in [(0,0,0,0),(8,0,1,0),(8,8,1,1),(0,8,0,1)]]
        f=[[0,1,2,0],[0,2,3,0],[4,5,6,0],[4,6,7,0]]
        raw=pack_geometry(v,f,1)
        record={'source':'door.nif','offset':0,'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest(),
                'materials':[{'texture_index':None,'diffuse':[1,1,1]}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'scene.mwpak';p.write_bytes(raw)
            _,base=_prepare_model((0,record,{},p,[]))
            _,panel=_prepare_model((0,record,{'visual_panel':{'axis':1,'facing':-1,
                                  'front_offset':-.1,'two_sided':True,'type':'door-panel'}},p,[]))
            self.assertEqual(len(panel[2]),2)
            self.assertEqual(_canonical(base[3]),_canonical(panel[3]))
            self.assertNotIn('flatten',panel[4])  # no facade mounting shift for a door
            self.assertEqual(panel[4]['visual_panel']['mounting_plane'],-2.1)
            np.testing.assert_array_equal(panel[0],v)
            self.assertEqual(p.read_bytes(),raw)
