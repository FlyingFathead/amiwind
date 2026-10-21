"""Stair collision method 1 never rekeys a default build (CHIM-STAIR-COLLISION-MESH-47).

The CHIM mesh units are keyed by the code their worker can reach (tools/code_key.py, chim.units.CODE_ENTRIES). Method
1 runs in its own worker and unit kind ('mesh-stair'); the default worker ('mesh': chim.build.mesh_unit and what
prepare_mesh_bsp and mesh_geometry reach) must hold none of its code, so a change to method 1, its switch or its
check leaves every default mesh unit's key as it was. Static reach only: nothing is built.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
METHOD_1 = ('tools/stair_mesh.py', 'tools/stair_collision_env.py')


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy required')
class DefaultMeshKeyTests(unittest.TestCase):
    def test_default_mesh_key_holds_no_method_1_code(self):
        from chim.units import unit_code_key
        key = unit_code_key('mesh')
        self.assertFalse(key['uncertain'])
        for path in METHOD_1:
            self.assertNotIn(path, key['files'], path)
            self.assertNotIn(path, key['units'], path)

    def test_method_1_has_its_own_key_holding_its_code(self):
        from chim.units import unit_code_key
        stair = unit_code_key('mesh-stair')
        self.assertFalse(stair['uncertain'])
        self.assertIn('tools/stair_mesh.py', stair['files'])
        self.assertIn('collision_pieces_mesh', stair['units']['tools/stair_mesh.py'])
        self.assertNotEqual(stair['digest'], unit_code_key('mesh')['digest'])

    def test_default_reach_unchanged_by_the_switch(self):
        import os
        from unittest.mock import patch
        import chim.units as units
        from chim.build import mesh_fingerprint
        model = {'source': 'meshes/x/a.nif', 'sha256': '0' * 64, 'materials': [], 'triangles': 2}
        profile = {'stair_plates': True}
        with patch.dict(os.environ, {'AMIWIND_STAIR_COLLISION_METHOD': '1'}):
            units._TOOL_HASH.clear()
            on = mesh_fingerprint(model, profile, [])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_STAIR_COLLISION_METHOD', None)
            units._TOOL_HASH.clear()
            off = mesh_fingerprint(model, profile, [])
        # the switch is not a unit switch: a default-kind key is the same with it set (the option acts through the
        # profile and the 'mesh-stair' kind only)
        self.assertEqual(on, off)
        self.assertNotEqual(mesh_fingerprint(model, profile, [], 'mesh-stair'), off)


if __name__ == '__main__':
    unittest.main()
