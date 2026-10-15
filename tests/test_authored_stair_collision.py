# SPDX-License-Identifier: GPL-3.0-only
"""Two measured source stair families use strict authored collision, never guessed proxies."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools'), str(ROOT/'tests')]

import numpy as np
import prepare_scenery as scenery
from mwad.scene import unpack_geometry
from test_scenery_root_transform import fixture,matrix,RAW

MODELS=('meshes/x/ex_imp_wall_stairs_01.nif','meshes/x/ex_imp_wall_stairs_02.nif')


def nif(with_root=True,malformed=False):
    N=fixture(matrix());root=N.Data.roots[0]
    if with_root:
        shape=N.NiTriShape()
        for v in shape.data.vertices:v.z=24.
        if malformed:shape.data.vertices[0].z=float('nan')
        collision=N.RootCollisionNode(matrix(),[shape]);collision.name=b'RootCollisionNode'
        root.children=list(root.children)+[collision]
    return N


def read_model(name,N,collision=None):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'synthetic.nif';path.write_bytes(RAW)
        with patch.object(scenery,'nif_reader',return_value=N),patch.object(scenery,'model_flames',return_value=[]):
            return scenery._read_model((name,path,{'offset':0,'bytes':len(RAW)},collision))


class AuthoredStairCollisionTests(unittest.TestCase):
    def test_only_exact_proven_names_opt_in(self):
        for name in MODELS:
            self.assertTrue(scenery.authored_collision_required(name))
            self.assertTrue(scenery.authored_collision_required(name.upper().replace('/','\\')))
        for name in ['meshes/x/ex_imp_wall_stairs_03.nif','meshes/x/ex_imp_wall_stairs_01_copy.nif',
                     'meshes/other/ex_imp_wall_stairs_01.nif','meshes/x/ex_imp_wall_01.nif']:
            self.assertFalse(scenery.authored_collision_required(name),name)

    def test_original_visual_packet_unchanged_and_exact_root_packet_selected(self):
        for name in MODELS:
            N=nif();expected_visual=scenery.model_geometry(RAW,N)[0]
            expected_collision=scenery.model_geometry(RAW,N,collision=True)[0]
            _,raw,result,collision,error=read_model(name,N)
            self.assertIsNone(error);self.assertEqual(raw,RAW)
            self.assertEqual(result[0][0],expected_visual)
            self.assertEqual(collision[0],expected_collision)
            self.assertNotEqual(hashlib.sha256(collision[0]).digest(),hashlib.sha256(result[0][0]).digest())
            self.assertEqual({v[2] for v in unpack_geometry(collision[0])[0]},{24.})
            self.assertEqual({v[2] for v in unpack_geometry(result[0][0])[0]},{0.})

    def test_required_collision_never_takes_permissive_missing_root_fallback(self):
        for name in MODELS:
            for requested in (None,'root_node_or_visual'):
                result=read_model(name,nif(with_root=False),requested)
                self.assertIsNone(result[2]);self.assertIsNone(result[3])
                self.assertIn('No supported visible static triangles',result[4])

    def test_malformed_root_is_error_even_while_visible_mesh_is_valid(self):
        for name in MODELS:
            N=nif(malformed=True)
            self.assertTrue(scenery.model_geometry(RAW,N)[0])
            result=read_model(name,N)
            self.assertIsNone(result[2]);self.assertIsNone(result[3]);self.assertIsNotNone(result[4])

    def test_unproven_models_keep_original_selection_and_explicit_fallback(self):
        name='meshes/x/ex_imp_wall_stairs_03.nif'
        plain=read_model(name,nif())
        self.assertIsNone(plain[3]);self.assertIsNone(plain[4])
        missing=read_model(name,nif(with_root=False),'root_node_or_visual')
        self.assertIsNotNone(missing[2]);self.assertIsNone(missing[3]);self.assertIsNone(missing[4])
        strict=read_model(name,nif(with_root=False),'root_node')
        self.assertIsNotNone(strict[4])

    def test_stale_selected_source_rejected_before_archive_read(self):
        from prepare_mesh_bsp import _prepare_model
        for name in MODELS:
            for collision in (None,{'source':'visual convex fallback'}):
                model={'source':name,'collision':collision}
                with self.assertRaisesRegex(ValueError,'regenerate its source export'):
                    _prepare_model((0,model,{},Path('/nonexistent-unused-archive')))


if __name__=='__main__':unittest.main()
