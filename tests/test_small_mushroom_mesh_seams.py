# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic curved material rims through the real flora-to-BSP converter."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.scene import pack_geometry
import prepare_world_flora as flora
from prepare_mesh_bsp import _prepare_model
from player_hull import lumps
from test_replace_bsp_world import fixture, PALETTE


def packet(root):
    # Different materials share their y=0 rim, with independent UV vertices.
    # Curvature makes material-by-material simplification move that boundary.
    vertices, faces = [], []
    for material in (0, 1):
        base = len(vertices)
        for y in range(9):
            for x in range(9):
                z = (x-4)**2 * .23 + y*y*.11 + material*y*.7
                vertices.append([x*4, y*4, z, x/8, y/8, 255, 255, 255, 255])
        for y in range(8):
            for x in range(8):
                a=base+y*9+x
                faces.extend([[a,a+1,a+10,material],[a,a+10,a+9,material]])
    raw=pack_geometry(vertices,faces,2);source=root/'source';source.mkdir()
    (source/'scenery.mwpak').write_bytes(raw)
    model={'source':'meshes/f/flora_bc_mushroom_01.nif','offset':0,'bytes':len(raw),
           'sha256':hashlib.sha256(raw).hexdigest(),'triangles':len(faces),
           'materials':[{'texture_index':None,'diffuse':[1,1,1]} for _ in range(2)],
           'bounds':[[0,0,0],[32,32,20]]}
    ref={'number':1,'cell':[0,0],'id':'synthetic_mushroom','model':'f/flora_bc_mushroom_01.nif',
         'kind':'small_mushroom','type':'CONT','position':[0,0,0],'scale':1,
         'rotation_radians':[0,0,0],'model_index':0,'bounds':model['bounds'],
         'source_key':['a'*64,'exterior',[0,0],1],'renderer_policy':'mesh',
         'requires_interaction':True,'source_collision':{'mode':'nonsolid','reason':'synthetic'},
         'container_state':{'flags':11,'items':[]},'script':''}
    index={'models':[model],'textures':[],'references':[ref],
           'chunk_size':2048,'chunks':{'0,0':[0]},'groups':{},'errors':[]}
    return model,index


class SmallMushroomMeshSeamTests(unittest.TestCase):
    def test_actual_overlay_preserves_original_rim_and_cache_category_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model,index=packet(root)
            base=root/'base.bsp';base.write_bytes(fixture(inline=True))
            palette=root/'palette.lmp';palette.write_bytes(PALETTE)
            entry={'name':'vf0000','origin':[0,0,0],'coverage':[[-100,-100],[100,100]]}
            def overlay(name,source_index):
                receipt={'placements':source_index['references'],'assets':[]}
                target=root/name/'scene.bsp'
                report=flora.overlay_region(base,target,root,source_index,receipt,entry,palette)
                self.assertEqual(report['retained_content']['retained_content'],'verified')
                return target.read_bytes()
            flora._CACHE.clear()
            tree=copy.deepcopy(index);r=tree['references'][0]
            r['kind']='tree';r['type']='STAT';r['requires_interaction']=False
            ordinary=overlay('ordinary-before',tree)  # Populate old category's cache first.
            small=overlay('small',index)  # Real unmocked reducer and final BSP writer.
            self.assertEqual(ordinary,overlay('ordinary-after',tree))
            # An independent full-geometry preparation feeds the same writer;
            # compare final BSP vertices, surfaces, UVs/textures and entity bytes.
            full=_prepare_model((0,model,{'texture_size':32,'collision_none':True,'ratio':1.},root/'source/scenery.mwpak',[]))
            flora._CACHE.clear()
            with patch('prepare_mesh_bsp._prepare_model',return_value=full):
                expected=overlay('full-reference',index)
            self.assertNotEqual(ordinary,expected,'synthetic control must actually exercise reduction')
            self.assertEqual(small,expected,'small mushroom overlay changed the shared source rim/UV geometry')
            self.assertGreater(len(lumps(small)[7]),len(lumps(ordinary)[7]))
            # References from older receipts without a kind keep their old path.
            flora._CACHE.clear();legacy=copy.deepcopy(tree);del legacy['references'][0]['kind']
            self.assertEqual(overlay('legacy-no-kind',legacy),ordinary)
            flora._CACHE.clear()


if __name__=='__main__': unittest.main()
