"""Asset-free host regressions for auxiliary geometry range metadata."""
import unittest
from test_mesh_inspection import synthetic_bsp,exporter
from test_compact_bsp import fixture
from player_hull import lumps,pack_lumps
from compact_bsp import compact,entities

class PoolTests(unittest.TestCase):
    def scene(self,ranges='0:1',pool=True):
        d=lumps(synthetic_bsp(textured=True));d[14]+=d[14][:64]
        d[0]=bytearray(('{"classname" "worldspawn"'+(' "aw_render_pool" "*2"' if pool else '')+'}\n'
                       '{"classname" "func_wall" "model" "*1" "origin" "10 20 30" "angles" "0 90 0" "aw_ref" "synthetic" "aw_render_ranges" "'+ranges+'"}\0').encode())
        return exporter.extract(pack_lumps(d),'synthetic-pool.bsp')
    def test_complete_pool_display_and_transform(self):
        scene=self.scene();self.assertEqual(len(scene['objects']),3)
        world,base,delta=scene['objects'];self.assertEqual(sum(o['faceCount'] for o in scene['objects']),3)
        self.assertEqual(base['vertices'],delta['vertices']);self.assertEqual(base['polygons'][0]['uv'],delta['polygons'][0]['uv'])
    def test_roles_and_shared_placement_identity_survive_json_export(self):
        world, base, delta = self.scene()['objects']
        self.assertEqual(world['terrainRole'], 'world_legacy')
        self.assertEqual(base['entityIndex'], delta['entityIndex'])
        self.assertEqual(base['entityIndex'], 1)
        self.assertEqual(base['entityClassname'], 'func_wall')
        self.assertEqual(base['terrainRole'], 'none')
        self.assertIsNone(base['renderPool'])
        self.assertEqual(delta['renderPool'], {'model': 2, 'parent_model': 1, 'relative_range': [0, 1]})

    def test_canonical_role_uses_entity_metadata_at_any_model_index(self):
        for model_id in (1, 7):
            d = lumps(synthetic_bsp(textured=True))
            d[14] = d[14][:64] * (model_id + 1)
            d[0] = bytearray(('{"classname" "worldspawn"}\n'
                '{"classname" "aw_render_diagnostic" "model" "*' + str(model_id) +
                '" "aw_ref" "canonical_land_diagnostic"}\0').encode())
            terrain = exporter.extract(pack_lumps(d), 'synthetic-land.bsp')['objects'][1]
            self.assertEqual(terrain['terrainRole'], 'canonical_land')
            self.assertTrue(terrain['inspectorOnlyDiagnostic'])
            self.assertEqual(terrain['entityIndex'], 1)
            # A normal scenery object with a similar reference is not the receiver.
            d[0] = d[0].replace(b'aw_render_diagnostic', b'func_wall')
            ordinary = exporter.extract(pack_lumps(d), 'synthetic-ordinary.bsp')['objects'][1]
            self.assertEqual(ordinary['terrainRole'], 'none')

    def test_invalid_range_rejected(self):
        for ranges in ('-1:1','0:0','1:1','1.0:1','0:1,'):
            with self.assertRaises(ValueError):self.scene(ranges)
        with self.assertRaises(ValueError):self.scene(pool=False)
    def test_compaction_preserves_unplaced_pool(self):
        d=lumps(fixture());d[0]=bytearray(bytes(d[0]).replace(b'"worldspawn"',b'"worldspawn" "aw_render_pool" "*1"'))
        out,report=compact(pack_lumps(d));self.assertEqual(report['retained_models'],[0,1,2])
        self.assertEqual(entities(lumps(out)[0])[0]['aw_render_pool'],'*1')

if __name__=='__main__':unittest.main()
