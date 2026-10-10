"""NPC heads keep their original geometry (NPC-HEAD-DECIMATION-33): synthetic meshes, no game assets."""
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]


def grid(name, part, width, height, z0, frames=2):
    import numpy as np
    xs, zs = np.meshgrid(np.linspace(0, 4, width + 1), np.linspace(z0, z0 + 6, height + 1))
    points = np.column_stack((xs.ravel(), .3 * np.sin(xs.ravel() * 2 + zs.ravel()), zs.ravel()))
    faces = []
    for j in range(height):
        for i in range(width):
            a = j * (width + 1) + i
            faces += [(a, a + 1, a + width + 1), (a + 1, a + width + 2, a + width + 1)]
    positions = np.stack([points + [0, 0, k * .5] for k in range(frames)])
    uv = np.column_stack((xs.ravel() / 4, (zs.ravel() - z0) / 6))
    return {'name': name, 'part': part, 'positions': positions, 'faces': np.array(faces),
            'uv': uv, 'colours': np.ones((len(points), 4)), 'material': 0}


def needs_numpy(test):
    def run(self):
        try:
            import numpy  # noqa: F401
            import fast_simplification  # noqa: F401
            import scipy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        return test(self)
    run.__name__ = test.__name__
    return run


class HeadRule(unittest.TestCase):
    palette = bytes(range(256)) * 3
    materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]

    def shapes(self, head=(8, 8), hair=(6, 4)):
        return [grid('tri head', 0, *head, 30), grid('tri hair', 1, *hair, 33),
                grid('tri chest', 3, 12, 10, 15), grid('tri foot', 15, 6, 4, 0)]

    @needs_numpy
    def test_default_mode_is_original(self):
        from mesh_geometry_env import npc_head_detail
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_NPC_HEAD_DETAIL', None)
            self.assertEqual(npc_head_detail(), 'original')
            os.environ['AMIWIND_NPC_HEAD_DETAIL'] = 'budget'
            self.assertEqual(npc_head_detail(), 'budget')
            self.assertEqual(npc_head_detail('original'), 'original')
            os.environ['AMIWIND_NPC_HEAD_DETAIL'] = 'tiny'
            with self.assertRaises(ValueError):
                npc_head_detail()

    @needs_numpy
    def test_head_and_hair_keep_every_original_triangle(self):
        import numpy as np
        from npc_geometry import bake, head_plan
        shapes = self.shapes()
        plan = head_plan(shapes, 192, head_detail='original')
        self.assertEqual(plan['protected'], frozenset({0, 1}))
        self.assertEqual([int(q) for q in plan['quotas'][:2]], [128, 48])
        frames, faces, uv, skin = bake(shapes, self.materials, {}, self.palette, budget=192, head_detail='original')
        # The first 128 + 48 output triangles are the authored head and hair, exactly, in every frame.
        start = 0
        for shape in shapes[:2]:
            n = len(shape['faces'])
            got = frames[:, start * 3:(start + n) * 3, :].reshape(len(frames), n, 3, 3)
            want = shape['positions'][:, shape['faces'], :]
            np.testing.assert_array_equal(got, want)
            start += n
        self.assertLess(len(faces) - 176, len(shapes[2]['faces']) + len(shapes[3]['faces']))
        import npc_geometry
        self.assertEqual({k: npc_geometry.LAST_PLAN[k] for k in ('mode', 'protected_shapes', 'hair_reduced',
                                                                  'lod_only')},
                         {'mode': 'original', 'protected_shapes': 2, 'hair_reduced': False, 'lod_only': False})

    @needs_numpy
    def test_budget_mode_is_the_previous_bake(self):
        import numpy as np
        from npc_geometry import _budget_quotas, bake, bake_quotas, head_plan
        shapes = self.shapes()
        # The previous split, unchanged (same numbers and bytes as the code before the head rule).
        expected = [int(q) for q in _budget_quotas(shapes, 192, 666, None, None)]
        self.assertEqual([int(q) for q in bake_quotas(shapes, 192, head_detail='budget')], expected)
        self.assertEqual(expected, [73, 19, 80, 19])
        plan = head_plan(shapes, 192, head_detail='budget')
        self.assertEqual((plan['protected'], plan['face_limit']), (frozenset(), 666))
        with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_DETAIL': 'budget'}):
            by_env = bake(shapes, self.materials, {}, self.palette, budget=192)
        explicit = bake(shapes, self.materials, {}, self.palette, budget=192, head_detail='budget')
        legacy_path = bake(shapes, self.materials, {}, self.palette, quotas=expected, head_detail='budget')
        for result in (explicit, legacy_path):
            for a, b in zip(by_env[:3], result[:3]):
                np.testing.assert_array_equal(a, b)
            self.assertEqual(by_env[3].tobytes(), result[3].tobytes())
        self.assertLess(expected[0], len(shapes[0]['faces']))  # the head is decimated in budget mode

    @needs_numpy
    def test_face_limit_raised_only_as_far_as_needed(self):
        from npc_geometry import bake, head_plan, animated_mdl
        shapes = self.shapes(head=(20, 15), hair=(10, 10))      # 600 + 200 head faces
        plan = head_plan(shapes, 480, head_detail='original')
        self.assertEqual((plan['face_limit'], plan['head_faces'], plan['hair_reduced']), (1024, 800, False))
        small = self.shapes(head=(14, 10), hair=(6, 4))          # 280 + 48: fits the caller's 666
        self.assertEqual(head_plan(small, 480, head_detail='original')['face_limit'], 666)
        frames, faces, uv, skin = bake(shapes, self.materials, {}, self.palette, head_detail='original')
        self.assertGreaterEqual(len(faces), 800)
        self.assertLessEqual(len(faces), 1024)
        self.assertLessEqual(skin.size[1], 480)
        raw = animated_mdl(frames, faces, uv, skin)
        self.assertEqual(struct.unpack_from('<ii', raw, 60), (frames.shape[1], len(faces)))

    @needs_numpy
    def test_cut_order_hair_details_torso_limbs_and_floors(self):
        from npc_geometry import head_plan
        shapes = self.shapes(head=(20, 20), hair=(20, 12))      # 800 + 480 > 1024
        classes = ['head', 'hair', 'torso', 'limb']
        floors = [800, 40, 30, 5]
        plan = head_plan(shapes, 480, head_detail='original', floors=floors, classes=classes)
        q = [int(x) for x in plan['quotas']]
        self.assertEqual(q[0], 800)                              # the head never gives way
        self.assertTrue(plan['hair_reduced'])
        self.assertEqual(plan['protected'], frozenset({0}))
        self.assertLessEqual(sum(q), 1024)
        self.assertEqual(set(plan['cuts']), {'hair'})            # hair alone absorbs the overshoot
        self.assertGreaterEqual(q[1], 40)
        # More to cut: hair down to its floor first, then the torso, the limb last; never below a floor.
        seen = set()
        for extra in range(0, 800, 7):
            plan = head_plan(shapes, 480, head_detail='original', floors=floors, classes=classes, extra_cut=extra)
            if plan['lod_only']:
                break
            q = [int(x) for x in plan['quotas']]
            self.assertEqual(q[0], 800)
            self.assertTrue(all(a >= b for a, b in zip(q, floors)))
            if 'torso' in plan['cuts']:
                self.assertEqual(q[1], 40)
            if 'limb' in plan['cuts']:
                self.assertEqual(q[1:3], [40, 30])
            seen |= set(plan['cuts'])
        self.assertEqual(seen, {'hair', 'torso', 'limb'})
        self.assertTrue(plan['lod_only'])                        # past every floor: no stick limbs

    @needs_numpy
    def test_lod_only_instead_of_stick_limbs(self):
        from npc_geometry import bake, head_plan
        import npc_geometry
        too_big = self.shapes(head=(30, 20), hair=(6, 4))       # a 1,200-face head alone
        plan = head_plan(too_big, 480, head_detail='original')
        self.assertEqual((plan['lod_only'], plan['mode']), (True, 'budget'))
        floors_too_big = head_plan(self.shapes(head=(20, 20)), 480, head_detail='original',
                                   floors=[800, 48, 240, 48], classes=['head', 'hair', 'torso', 'limb'])
        self.assertTrue(floors_too_big['lod_only'])
        bake(too_big, self.materials, {}, self.palette, head_detail='original')
        self.assertTrue(npc_geometry.LAST_PLAN['lod_only'])
        self.assertEqual(npc_geometry.LAST_PLAN['mode'], 'budget')
        with self.assertRaisesRegex(ValueError, 'Original head does not fit'):
            bake(too_big, self.materials, {}, self.palette, head_detail='original', lod_only='raise')

    @needs_numpy
    def test_limbs_keep_their_silhouette(self):
        import numpy as np
        from npc_geometry import body_classes, silhouette_floors, simplify_shape
        leg = grid('tri upper leg', 21, 4, 24, 0)
        tiny = grid('tri buckle', 3, 1, 1, 10)
        tiny['positions'] = tiny['positions'] * np.array([.1, .1, .02]) + np.array([0, 0, 10])
        shapes = [grid('tri head', 0, 8, 8, 30), leg, tiny]
        classes = body_classes(shapes, 36.)
        self.assertEqual(classes, ['head', 'limb', 'detail'])
        floors = silhouette_floors(shapes, classes)
        self.assertEqual(floors[0], 128)
        self.assertEqual(floors[2], 2)
        points = leg['positions'][0]
        _, kept = simplify_shape(points, leg['faces'].astype(np.int32), floors[1], True)
        self.assertLessEqual(len(kept), floors[1] + 2)
        self.assertGreater(floors[1], 4)                         # a limb is not reduced to a stick

    @needs_numpy
    def test_near_skin_keeps_16_texel_tiles_where_they_fit(self):
        import numpy as np
        from npc_geometry import mixed_tile_skin
        tile = lambda v: np.full((16, 16, 3), v, np.uint8)
        # 1,005 faces (Fargoth's near model): face 510, body 126, hair 369.
        tiles = [(tile(10), 0)] * 510 + [(tile(20), 3)] * 126 + [(tile(30), 1)] * 369
        skin, uv = mixed_tile_skin(tiles)
        self.assertLessEqual(skin.size[1], 480)
        self.assertEqual(skin.size[0], 512)
        spans = [int(uv[i * 3 + 1][0] - uv[i * 3][0]) for i in range(len(tiles))]
        self.assertTrue(all(x == 15 for x in spans[:636]))   # the face and the body keep 16 texels
        self.assertGreater(spans.count(7), 0)                 # the hair gives way first
        small = mixed_tile_skin([(tile(5), 3)] * 400)[0]
        self.assertEqual(small.size, (512, 208))              # all 16 texels when they fit

    @needs_numpy
    def test_creatures_and_headless_parts_unchanged(self):
        from npc_geometry import head_plan
        body = [grid('tri chest', 3, 12, 10, 15)]
        creature = [dict(grid('tri body', 0, 8, 8, 0), part=-1)]
        for shapes in (body, creature):
            self.assertEqual(head_plan(shapes, 192, head_detail='original')['protected'], frozenset())


class HeadDetailSwitch(unittest.TestCase):
    def test_shipped_default_config_and_cli(self):
        from build_font_options import resolve_font_options
        shipped = json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual(shipped['npc_head_detail'], 'auto')
        # v0.0.35: original heads are EXPERIMENTAL and off by default: auto is the previous (budget) bake,
        # with or without the near/far levels; --npc-head-detail original asks for them.
        r = resolve_font_options(SimpleNamespace(build_config=None))
        self.assertEqual((r['npc_head_detail'], r['npc_head_detail_setting']), ('budget', 'auto'))
        r = resolve_font_options(SimpleNamespace(build_config=None, npc_lod='on'))
        self.assertEqual((r['npc_head_detail'], r['npc_head_detail_setting']), ('budget', 'auto'))
        r = resolve_font_options(SimpleNamespace(build_config=None, npc_lod='off'))
        self.assertEqual(r['npc_head_detail'], 'budget')
        r = resolve_font_options(SimpleNamespace(build_config=None, npc_lod='on', npc_head_detail='original'))
        self.assertEqual((r['npc_head_detail'], r['npc_head_detail_selected_by']), ('original', 'CLI override'))
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'b.json'
            cfg.write_text('{"npc_head_detail": "budget"}')
            r = resolve_font_options(SimpleNamespace(build_config=cfg))
            self.assertEqual((r['npc_head_detail'], r['npc_head_detail_selected_by']), ('budget', 'build config'))
            r = resolve_font_options(SimpleNamespace(build_config=cfg, npc_head_detail='original'))
            self.assertEqual((r['npc_head_detail'], r['npc_head_detail_selected_by']), ('original', 'CLI override'))
            cfg.write_text('{"npc_head_detail": "half"}')
            with self.assertRaisesRegex(ValueError, 'npc_head_detail'):
                resolve_font_options(SimpleNamespace(build_config=cfg))

    def test_cli_flag_and_export(self):
        import build
        import mesh_geometry_env as E
        self.assertEqual(build.parser().parse_args(['--npc-head-detail', 'budget']).npc_head_detail, 'budget')
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(E.export_npc_head_detail('budget'), 'budget')
            self.assertEqual(os.environ['AMIWIND_NPC_HEAD_DETAIL'], 'budget')
            with self.assertRaises(ValueError):
                E.export_npc_head_detail('half')

    def test_gallery_cache_key_includes_the_mode(self):
        try:
            import numpy  # noqa: F401
            import gallery_cache
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        spec = {'kind': 'NPC_', 'appearance': {'parts': [], 'skeleton': 'meshes/base_anim.nif', 'height': 1, 'weight': 1}}
        creature = {'kind': 'CREA', 'mesh': 'r/rat.nif'}
        keys = {}
        for mode in ('original', 'budget'):
            with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_DETAIL': mode}):
                keys[mode] = gallery_cache.identity(spec, b'p', {}, {}, {})
                self.assertIsNone(gallery_cache.identity(creature, b'p', {}, {}, {})['npc_head_detail'])
        self.assertEqual((keys['original']['npc_head_detail'], keys['budget']['npc_head_detail']), ('original', 'budget'))
        self.assertNotEqual(gallery_cache.token(keys['original']), gallery_cache.token(keys['budget']))

    def test_dagoth_ur_profile_keeps_his_whole_model(self):
        # Owner decision 2026-10-09: Dagoth Ur (dagoth_ur_1 and dagoth_ur_2 share r/dagothr.nif) keeps all 2,254
        # original triangles through the shared-vertex encoding (NPC-DAGOTH-BODY-DECIMATION-33).
        config = json.loads((ROOT / 'config/gallery_model_quality.json').read_text())
        profile = config['profiles']['r/dagothr.nif']
        self.assertEqual((profile['id'], profile['encoding']), ('dagoth-whole-shared-vertex-v1', 'shared-vertex'))
        self.assertEqual(config['previous_profiles']['r/dagothr.nif']['id'], 'dagoth-mask-v1')  # kept on record

    @needs_numpy
    def test_shared_vertex_encoding_keeps_every_original_face(self):
        import numpy as np
        from npc_geometry import animated_mdl, shared_vertex_mdl
        palette = bytes(range(256)) * 3
        textures = {'body': np.full((256, 256, 4), 90, np.uint8), 'mask': np.full((128, 128, 4), 200, np.uint8)}
        materials = [{'texture_index': 'body', 'diffuse': [1., 1., 1.], 'alpha': 1.},
                     {'texture_index': 'mask', 'diffuse': [1., 1., 1.], 'alpha': 1.}]
        body = dict(grid('tri body', -1, 40, 30, 0, frames=1), material=0)      # 2,400 triangles, 1,271 vertices
        mask = dict(grid('tri mask', -1, 10, 8, 30, frames=1), material=1)      # 160 triangles, 99 vertices
        frames, faces, st, skin = shared_vertex_mdl([body, mask], materials, textures, palette)
        self.assertEqual(len(faces), 2560)
        self.assertEqual(frames.shape[1], 1271 + 99)
        np.testing.assert_array_equal(frames[0, :1271], body['positions'][0])   # original vertices, unmoved
        self.assertEqual(sorted(map(tuple, np.sort(faces[:2400], axis=1))),
                         sorted(map(tuple, np.sort(body['faces'], axis=1))))
        self.assertLessEqual(skin.size[0], 512)
        self.assertLessEqual(skin.size[1], 480)
        raw = animated_mdl(frames, faces, st, skin)
        self.assertEqual(struct.unpack_from('<ii', raw, 60), (1370, 2560))       # under the 2,000-vertex path
        tinted = dict(mask, colours=np.full((99, 4), .5))
        with self.assertRaisesRegex(ValueError, 'plain vertex colours'):
            shared_vertex_mdl([body, tinted], materials, textures, palette)


class WorldAllowances(unittest.TestCase):
    @staticmethod
    def mdl(vertices, triangles):
        header = struct.pack('<4si3f3ff3f8if', b'IDPO', 6, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0,
                             1, 8, 8, vertices, triangles, 1, 0, 0, 1.)
        return header + b'\0' * 32

    def test_extended_world_models_get_byte_matching_lines(self):
        try:
            from audit_gallery_budgets import world_allowances
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir(); (id1 / 'gallery').mkdir()
            big = self.mdl(2400, 800); (id1 / 'progs/fargoth.mdl').write_bytes(big)
            (id1 / 'progs/rat.mdl').write_bytes(self.mdl(900, 300))
            (id1 / 'gallery/m1.mdl').write_bytes(self.mdl(3000, 1000))
            (id1 / 'model-budgets.txt').write_text('AWPB1\ngallery/m1.mdl 3000 1000 116 0\n')
            report = world_allowances(id1)
            self.assertEqual([e['model'] for e in report['added']], ['progs/fargoth.mdl'])
            lines = (id1 / 'model-budgets.txt').read_bytes().decode().split('\n')
            self.assertEqual(lines[:2], ['AWPB1', 'gallery/m1.mdl 3000 1000 116 0'])
            self.assertEqual(lines[2], f'progs/fargoth.mdl 2400 800 {len(big)} {zlib.crc32(big):08x}')
            self.assertEqual(world_allowances(id1)['added'], [])     # idempotent
            (id1 / 'progs/huge.mdl').write_bytes(self.mdl(3100, 1100))
            with self.assertRaisesRegex(ValueError, 'ceiling'):
                world_allowances(id1)


if __name__ == '__main__':
    unittest.main()
