# SPDX-License-Identifier: GPL-3.0-only
# Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
"""Method 2, the hand-made meshes (config/model-method-2.json, tools/model_method2.py, tools/lantern_rebuild.py;
MODEL-REPLACEMENT-OBJ-67): the lantern rebuild's construction, panels and units, its place in the builder (keyed by
model path + NIF SHA-256, its own unit kind, method 1 selectable), on synthetic models only (no game data).

The lantern pipeline's own thirteen tests (checkpoint-002), as they map to the builder:
  - read_obj: negative indices and a quad; a face without texture coordinates refused (2 tests, ported);
  - equal-depth glass composited once (ported, bake_side);
  - a product reference outside its folder refused (the archive traversal test, on the product's references);
  - an existing output folder kept untouched (ported, write_product);
  - the TES3 reader's transform, scale and texture convention, the hidden shape left out, another NIF version
    refused (ported onto the builder's own reader, prepare_scenery.model_geometry, which the build uses instead of a
    second import path; the root node's transform follows the game's root rule there, see the test);
  - texture lookup (DDS before the named file, case, paths) and the input archive (preconverted members, traversal):
    the build reads the model and its textures through the scenery export of the game's own archives
    (prepare_scenery.export_refs), never an archive the user hands in, so these have no counterpart here.
"""
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile  # noqa: F401  (the archive tests' module; see the docstring)
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import lantern_rebuild as L  # noqa: E402
import model_method2 as M  # noqa: E402

SOURCE = 'meshes/l/test_lantern_99.nif'
# Quake units, as the recipe's numbers: six rings (z, half width), the handle above the roof
RINGS = [[-8.0, 1.6], [-7.0, 1.7], [-6.5, 1.5], [-3.0, 1.5], [-2.5, 1.7], [-1.5, 0.5]]
GLASS, METAL, BASE, ROOF, CANDLE = range(5)
BANDS = [BASE, METAL, GLASS, METAL, ROOF]


def synthetic_source():
    """A synthetic lantern in builder units (Morrowind = Quake x 4, the NIF's texture v): the ring body with every
    quad split in four around its centre (more triangles than the rebuild), its panel band of half-transparent glass,
    a candle box behind it, and a thin handle strip over the roof. Returns (vertices N x 9, faces M x 4)."""
    v, f = [], []

    def quad(points, material, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
        centre = np.mean(points, axis=0)
        cu = np.mean(uv, axis=0)
        base = len(v)
        for p, t in zip(list(points) + [centre], list(uv) + [cu]):
            v.append([*(np.asarray(p) * 4), t[0], 1 - t[1], 255, 255, 255, 255])
        for i in range(4):
            f.append([base + i, base + (i + 1) % 4, base + 4, material])
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ring = [[(x * r, y * r, z) for x, y in corners] for z, r in RINGS]
    for j, material in enumerate(BANDS):
        for i in range(4):
            k = (i + 1) % 4
            quad([ring[j][i], ring[j][k], ring[j + 1][k], ring[j + 1][i]], material)
    quad(list(reversed(ring[0])), BASE)
    quad(ring[-1], METAL)
    # the candle, a box inside the panels
    lo, hi = (-0.5, -0.5, -6.0), (0.5, 0.5, -4.0)
    box = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    for i in range(4):
        a, b = box[i], box[(i + 1) % 4]
        quad([(a[0], a[1], lo[2]), (b[0], b[1], lo[2]), (b[0], b[1], hi[2]), (a[0], a[1], hi[2])], CANDLE)
    # the handle: a strip of two quads, |y| 0.05, from the roof's top up to z 0.5 (6 positions, 4 triangles)
    strip = [(-0.4, z) for z in (-1.4, -0.5, 0.5)]
    for (x0, z0), (x1, z1) in zip(strip, strip[1:]):
        base = len(v)
        for x, z, y, t in ((x0, z0, -0.05, (0, z0)), (x0, z0, 0.05, (1, z0)), (x1, z1, 0.05, (1, z1)),
                           (x1, z1, -0.05, (0, z1))):
            v.append([x * 4, y * 4, z * 4, t[0], 1 - t[1], 255, 255, 255, 255])
        f += [[base, base + 1, base + 2, METAL], [base, base + 2, base + 3, METAL]]
    return np.asarray(v, dtype=float), np.asarray(f, dtype=np.int64)


def synthetic_recipe(vertices, faces):
    points, _ = L.to_recipe_frame(vertices)
    return {'expected_source': {'unique_positions': int(len(np.unique(points, axis=0))), 'triangles': len(faces),
                                'min': points.min(0).tolist(), 'max': points.max(0).tolist(),
                                'bound_tolerance': 0.0001},
            'center_xy': [0, 0], 'rings': RINGS, 'panel_ring_pair': [2, 3],
            'ring_band_materials': ['base', 'metal', 'panels', 'metal', 'roof'],
            'handle': {'source_material': METAL, 'min_z': -1.5, 'max_abs_y': 0.14, 'expected_vertices': 6,
                       'expected_triangles': 4},
            'materials': {'base': BASE, 'roof': ROOF, 'metal': METAL},
            'uv': {'base': [0.1, 0.9], 'metal': [0.15, 0.85], 'roof_u': [0.4, 0.9], 'roof_v_start': 1.0,
                   'roof_v_step': 0.25},
            'bake': {'texture_size': 16, 'supersample': 2, 'ray_offset': 5, 'background_rgb': [0.02, 0.015, 0.01]},
            'expected_output': {'vertices': 30, 'triangles': 48, 'open_edges': 6}}


def synthetic_textures():
    colour = {GLASS: (200, 220, 255, 128), METAL: (90, 90, 100, 255), BASE: (120, 80, 40, 255),
              ROOF: (100, 60, 30, 255), CANDLE: (250, 230, 160, 255)}
    return {m: np.tile(np.array(c, np.uint8), (4, 4, 1)) for m, c in colour.items()}


class Units(unittest.TestCase):
    def test_the_recipe_frame_is_quake_units_and_the_obj_texture_convention(self):
        v = np.array([[4.0, -8.0, 12.0, 0.25, 0.1, 255, 255, 255, 255]])
        points, uvs = L.to_recipe_frame(v)
        np.testing.assert_allclose(points, [[1.0, -2.0, 3.0]])
        np.testing.assert_allclose(uvs, [[0.25, 0.9]])
        back, buv = L.from_recipe_frame(points, uvs)
        np.testing.assert_allclose(back, v[:, :3])
        np.testing.assert_allclose(buv, v[:, 3:5])

    def test_the_rebuilt_lantern_sits_where_the_original_did(self):
        # origin and bounds within 1e-4 (Quake units, the recipe's tolerance; 4e-4 Morrowind units)
        vertices, faces = synthetic_source()
        recipe = synthetic_recipe(vertices, faces)
        out_v, out_f, picture, report = L.rebuild(vertices, faces, 5, synthetic_textures(), recipe)
        np.testing.assert_allclose(out_v[:, :3].min(0) * 0.25, vertices[:, :3].min(0) * 0.25, atol=1e-4)
        np.testing.assert_allclose(out_v[:, :3].max(0) * 0.25, vertices[:, :3].max(0) * 0.25, atol=1e-4)
        # the model's origin is not moved: the body stays centred where the source's is
        np.testing.assert_allclose((out_v[:, :2].min(0) + out_v[:, :2].max(0)) / 2,
                                   (vertices[:, :2].min(0) + vertices[:, :2].max(0)) / 2, atol=4e-4)
        self.assertEqual((report['positions'], report['triangles'], report['open_edges']), (30, 48, 6))
        self.assertEqual(len(out_f), 48)


class Rebuild(unittest.TestCase):
    def setUp(self):
        self.vertices, self.faces = synthetic_source()
        self.recipe = synthetic_recipe(self.vertices, self.faces)

    def test_materials_are_the_sources_and_the_panels_one_picture(self):
        out_v, out_f, picture, report = L.rebuild(self.vertices, self.faces, 5, synthetic_textures(), self.recipe)
        used = {int(m) for m in out_f[:, 3]}
        self.assertEqual(used, {BASE, ROOF, METAL, 5})
        self.assertEqual(picture.shape, (16, 64, 3))           # four 16 x 16 sides side by side
        panel_u = out_v[out_f[out_f[:, 3] == 5][:, :3].ravel(), 3]
        self.assertEqual((panel_u.min(), panel_u.max()), (0.0, 4.0))
        # the middle of a side: the glass over the candle, lit by neither the background nor the metal
        middle = picture[8, 8].astype(int)
        self.assertGreater(middle[0], 150)
        self.assertGreater(middle[2], 120)

    def test_the_bake_is_the_same_bytes_every_time(self):
        first = L.rebuild(self.vertices, self.faces, 5, synthetic_textures(), self.recipe)
        second = L.rebuild(self.vertices, self.faces, 5, synthetic_textures(), self.recipe)
        self.assertEqual(first[2].tobytes(), second[2].tobytes())
        self.assertEqual(first[0].tobytes(), second[0].tobytes())

    def test_frosted_panels_need_no_texture_and_share_one_picture(self):
        out_v, out_f, picture, report = L.rebuild(self.vertices, self.faces, 5, {}, self.recipe, 'frosted')
        self.assertEqual(picture.shape, (16, 16, 3))
        panel_u = out_v[out_f[out_f[:, 3] == 5][:, :3].ravel(), 3]
        self.assertEqual((panel_u.min(), panel_u.max()), (0.0, 1.0))
        self.assertEqual(report['panels'], 'frosted')
        with self.assertRaises(ValueError):
            L.rebuild(self.vertices, self.faces, 5, {}, self.recipe, 'glass')

    def test_another_model_is_refused_by_its_counts_and_bounds(self):
        recipe = dict(self.recipe, expected_source=dict(self.recipe['expected_source'], triangles=229))
        with self.assertRaisesRegex(ValueError, 'does not match the recipe'):
            L.rebuild(self.vertices, self.faces, 5, synthetic_textures(), recipe)
        moved = self.vertices.copy()
        moved[:, 2] += 4.0          # one Quake unit up
        with self.assertRaisesRegex(ValueError, 'bounds'):
            L.rebuild(moved, self.faces, 5, synthetic_textures(), self.recipe)

    def test_the_handle_must_be_found(self):
        recipe = dict(self.recipe, handle=dict(self.recipe['handle'], max_abs_y=0.01))
        with self.assertRaisesRegex(ValueError, 'handle'):
            L.rebuild(self.vertices, self.faces, 5, synthetic_textures(), recipe)


class PipelineTests(unittest.TestCase):
    """The checkpoint's own tests (OBJ reading, the alpha composite, the private product)."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def make_obj(self, face):
        from PIL import Image
        Image.new('RGBA', (2, 2), (200, 100, 50, 128)).save(self.root / 'synthetic.png')
        (self.root / 'synthetic.mtl').write_text('newmtl panel\nmap_Kd synthetic.png\n')
        path = self.root / 'synthetic.obj'
        path.write_text('mtllib synthetic.mtl\nv -1 -1 0\nv 1 -1 0\nv 1 -1 1\nv -1 -1 1\nvt 0 0\nvt 1 0\nvt 1 1\n'
                        'vt 0 1\nusemtl panel\n' + face + '\n')
        return path

    def test_negative_obj_indices_and_quad(self):
        vertices, uvs, faces, textures = L.read_obj(self.make_obj('f -4/-4 -3/-3 -2/-2 -1/-1'))
        self.assertEqual((len(vertices), len(uvs), len(faces)), (4, 4, 2))
        self.assertEqual(faces[1][1], [0, 2, 3])
        self.assertTrue(textures['panel'].is_file())

    def test_missing_uvs_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UVs are required'):
            L.read_obj(self.make_obj('f 1 2 3'))

    def test_alpha_is_not_applied_twice_at_same_depth(self):
        from PIL import Image
        vertices, uvs, faces, _ = L.read_obj(self.make_obj('f 1/1 2/2 3/3 4/4'))
        faces += faces.copy()       # coincident triangles must not double the opacity
        image = np.array(Image.open(self.root / 'synthetic.png')) / 255
        recipe = {'panel_ring_pair': [0, 1], 'rings': [[0, 1], [1, 1]], 'center_xy': [0, 0],
                  'bake': {'ray_offset': 5, 'background_rgb': [0, 0, 0]}}
        actual = L.bake_side(0, vertices, uvs, faces, {'panel': image}, recipe, 16, 1)
        self.assertTrue(np.all(actual == np.array([100, 50, 25])), actual[0, 0].tolist())

    def test_a_reference_outside_the_folder_is_refused(self):
        path = self.root / 'unsafe.obj'
        path.write_text('mtllib ../outside.mtl\nv 0 0 0\n')
        with self.assertRaisesRegex(ValueError, 'inside the output folder'):
            L.read_obj(path)

    def test_existing_output_preserved_and_the_product_reads_back(self):
        vertices, faces = synthetic_source()
        out_v, out_f, picture, _ = L.rebuild(vertices, faces, 5, synthetic_textures(),
                                             synthetic_recipe(vertices, faces))
        existing = self.root / 'existing'
        existing.mkdir()
        (existing / 'keep.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            L.write_product(existing, out_v, out_f, picture, 5)
        self.assertEqual((existing / 'keep.txt').read_text(), 'keep')
        obj = L.write_product(self.root / 'new', out_v, out_f, picture, 5)
        positions, uvs, read_faces, textures = L.read_obj(obj)
        self.assertEqual(len(read_faces), 48)
        np.testing.assert_allclose(positions.max(0), out_v[:, :3].max(0) * 0.25, atol=1e-5)
        self.assertTrue(textures['panels'].is_file())


class TheBuildersReader(unittest.TestCase):
    """The checkpoint's TES3 input tests on the builder's own reader (prepare_scenery.model_geometry)."""

    def make_nif(self):
        from prepare_scenery import nif_reader
        N = nif_reader()
        data = N.Data(version=0x04000002)
        root = N.NiNode()
        root.name = b'Synthetic root'
        root.translation.x = 10
        root.scale = 2
        data.roots = [root]
        shape = N.NiTriShape()
        shape.name = b'Synthetic visible triangle'
        shape.translation.y = 4
        root.add_child(shape)
        g = N.NiTriShapeData()
        shape.data = g
        g.num_vertices = 3
        g.has_vertices = True
        g.vertices.update_size()
        for target, xyz in zip(g.vertices, [(1, 2, 3), (2, 2, 3), (1, 3, 3)]):
            target.x, target.y, target.z = xyz
        g.num_uv_sets = 1
        g.has_uv = True
        g.uv_sets.update_size()
        for target, coords in zip(g.uv_sets[0], [(.2, .3), (.8, .3), (.2, .9)]):
            target.u, target.v = coords
        g.num_triangles = 1
        g.num_triangle_points = 3
        g.triangles.update_size()
        g.triangles[0].v_1, g.triangles[0].v_2, g.triangles[0].v_3 = 0, 1, 2
        texture = N.NiSourceTexture()
        texture.use_external = 1
        texture.file_name = b'Textures\\Synthetic.TGA'
        prop = N.NiTexturingProperty()
        prop.has_base_texture = True
        prop.base_texture.source = texture
        shape.add_property(prop)
        hidden = N.NiTriShape()
        hidden.name = b'Synthetic hidden triangle'
        hidden.flags = 1
        hidden.data = g
        root.add_child(hidden)
        buffer = io.BytesIO()
        data.write(buffer)
        return buffer.getvalue(), N

    def test_tes3_read_transform_units_and_texture_convention(self):
        from mwad.scene import unpack_geometry
        from prepare_scenery import model_geometry
        raw, N = self.make_nif()
        packet, materials, bounds, skipped = model_geometry(raw, N)
        vertices, faces, _ = unpack_geometry(packet)
        vertices = np.asarray(vertices, dtype=float)
        # the builder's units: Morrowind units; the root node's own transform is dropped by the game's root rule
        # (nif_common.scenery_root_local, rule from OpenMW), the shape's kept: (1, 2, 3) + (0, 4, 0)
        np.testing.assert_allclose(vertices[0, :3], [1, 6, 3], atol=1e-6)
        # the recipe frame: Quake units and the OBJ convention, as the checkpoint's reader wrote them
        points, uvs = L.to_recipe_frame(vertices)
        np.testing.assert_allclose(points[0], [0.25, 1.5, 0.75])
        np.testing.assert_allclose(uvs[0], [.2, .7], atol=1e-6)
        self.assertEqual([tuple(f) for f in faces], [(0, 1, 2, 0)])
        self.assertEqual(materials[0]['texture_source'], 'Textures\\Synthetic.TGA')

    def test_the_hidden_shape_is_left_out(self):
        from prepare_scenery import model_geometry
        raw, N = self.make_nif()
        _, _, _, skipped = model_geometry(raw, N)
        self.assertEqual([s['reason'] for s in skipped], ['hidden_node'])

    def test_another_nif_version_is_refused(self):
        from prepare_scenery import model_geometry, nif_reader
        with self.assertRaisesRegex(ValueError, '4.0.0.2'):
            model_geometry(b'Gamebryo File Format, Version 20.2.0.7\n', nif_reader())


def table_with(row):
    return {'format': 1, 'models': {SOURCE: row}}


def row(**changes):
    vertices, faces = synthetic_source()
    base = {'source_sha256': 'a' * 64, 'method': 2, 'kind': 'lantern_rings', 'panels': 'baked',
            'source': {'batch': 'test', 'date': '2026-11-17'}, 'counts': {}, 'ab': 'test',
            'recipe': synthetic_recipe(vertices, faces)}
    return dict(base, **changes)


class Method2(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        for name in (M.METHOD_VARIABLE, M.PANELS_VARIABLE):
            os.environ.pop(name, None)
        self.addCleanup(self.env.stop)
        self.model = {'source': 'Meshes\\L\\Test_Lantern_99.NIF', 'source_sha256': 'a' * 64, 'sha256': 'p' * 64}
        self.profile = {'texture_size': 64, 'ratio': 0.5, 'visual_recipe': {'name': 'ev', 'sha256': 'p' * 64},
                        'faces': 'merge', 'stair_plates': True}

    def test_the_hand_made_mesh_wherever_the_model_is_placed_by_path_and_nif(self):
        out = M.apply_method2(self.profile, self.model, table_with(row()))
        self.assertEqual(out['visual_method2']['kind'], 'lantern_rings')
        self.assertEqual(out['visual_recipe'], {'name': 'method-2', 'sha256': 'a' * 64})
        # method 1's visual keys go, the stage's own settings stay
        self.assertNotIn('ratio', out)
        self.assertEqual((out['faces'], out['stair_plates'], out['texture_size']), ('merge', True, 64))
        self.assertEqual(M.unit_kind(out), M.UNIT_KIND)
        self.assertEqual(M.unit_kind(self.profile), 'mesh')

    def test_another_nif_or_path_keeps_method_1(self):
        other = dict(self.model, source_sha256='b' * 64)
        self.assertIs(M.apply_method2(self.profile, other, table_with(row())), self.profile)
        other = dict(self.model, source='meshes/l/test_lantern_98.nif')
        self.assertIs(M.apply_method2(self.profile, other, table_with(row())), self.profile)

    def test_method_1_stays_selectable_per_model_and_for_the_build(self):
        self.assertIs(M.apply_method2(self.profile, self.model, table_with(row(method=1))), self.profile)
        os.environ[M.METHOD_VARIABLE] = '1'
        self.assertIs(M.apply_method2(self.profile, self.model, table_with(row())), self.profile)
        os.environ[M.METHOD_VARIABLE] = '3'
        with self.assertRaises(ValueError):
            M.apply_method2(self.profile, self.model, table_with(row()))

    def test_the_panels_switch_for_an_ab(self):
        os.environ[M.PANELS_VARIABLE] = 'frosted'
        out = M.apply_method2(self.profile, self.model, table_with(row()))
        self.assertEqual(out['visual_method2']['panels'], 'frosted')

    def test_the_shipped_table(self):
        table = M.load_table()
        lantern = table['models']['meshes/l/light_com_lantern_02.nif']
        # frosted by the intake rule: 5,440 bytes of picture against about 15,134 of mesh saved (baked: 21,760)
        self.assertEqual((lantern['method'], lantern['kind'], lantern['panels']), (2, 'lantern_rings', 'frosted'))
        self.assertEqual(len(lantern['source_sha256']), 64)
        counts = lantern['counts']
        self.assertEqual((counts['triangles_before'], counts['triangles'], counts['triangles_change']), (229, 68, -161))
        self.assertEqual((counts['positions_before'], counts['positions'], counts['positions_change']), (166, 39, -127))
        self.assertEqual(lantern['source']['author'], 'FlyingFathead')
        L.load_recipe(lantern)
        # numbers only: no game data in the table
        text = M.TABLE.read_text(encoding='utf-8')
        self.assertNotIn('.dds', text.lower())
        self.assertNotIn('.tga', text.lower())

    def test_a_row_without_its_record_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 't.json'
            bad = row()
            del bad['ab']
            path.write_text(json.dumps(table_with(bad)), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'records its ab'):
                M.load_table(path)

    def test_the_gated_plain_pass_puts_method_2_on_its_own_unit_kind(self):
        # chim.build.gated_mesh_units' plain pass (its default run, mesh_units_with_method2): the method-2 meshes on
        # their own unit kind and worker, the others and the stair pass on run_units as before
        import chim.build as cb
        import chim.units as cu
        calls = []

        def fake_run(kind, items, worker, jobs, cache):
            calls.append((kind, [task[0] for _, task in items], getattr(worker, '__name__', '')))
            return ['%s:%d' % (kind, task[0]) for _, task in items]

        hand = M.apply_method2(self.profile, self.model, table_with(row()))
        items = [('f0', (0, {}, self.profile, 'a', [])), ('f1', (1, {'source': 's'}, hand, 'a', [])),
                 ('f2', (2, {}, self.profile, 'a', []))]
        with mock.patch.object(cu, 'run_units', fake_run), mock.patch.object(cb, 'run_units', fake_run):
            out = cb.mesh_units_with_method2('mesh', items, cb.mesh_unit, 1, None)
            stair = cb.mesh_units_with_method2('mesh-stair', items[:1], cb.mesh_unit, 1, None)
        self.assertEqual(out, ['mesh:0', '%s:1' % M.UNIT_KIND, 'mesh:2'])
        self.assertEqual(calls[:2], [('mesh', [0, 2], 'mesh_unit'), (M.UNIT_KIND, [1], 'mesh_unit_method2')])
        self.assertEqual(stair, ['mesh-stair:0'])

    def test_the_default_mesh_units_never_reach_method_2(self):
        from chim.units import unit_code_key
        plain = unit_code_key('mesh')['files']
        hand = unit_code_key(M.UNIT_KIND)['files']
        for rel in ('tools/model_method2.py', 'tools/lantern_rebuild.py'):
            self.assertNotIn(rel, plain)
            self.assertIn(rel, hand)


class TheMeshUnit(unittest.TestCase):
    """The method-2 unit on a synthetic scenery export: the drawn faces, the panel material and picture, the
    original collision."""

    def test_the_unit_draws_the_rebuild_with_its_panels_and_the_original_collision(self):
        from mwad.scene import pack_geometry
        from chim.build import mesh_unit
        from chim.units import _canonical
        vertices, faces = synthetic_source()
        raw = pack_geometry([[*map(float, r[:5]), *map(int, r[5:])] for r in vertices], faces.tolist(), 5)
        textures = synthetic_textures()
        with tempfile.TemporaryDirectory() as d:
            pak = Path(d) / 'scenery.mwpak'
            records, blob = [], bytearray(raw)
            for m in range(5):
                image = textures[m]
                data = struct.pack('>4sHH', b'MWT1', image.shape[1], image.shape[0]) + image.tobytes()
                blob += bytes(-len(blob) % 512)          # the archive's 512-byte alignment (mwad.scene)
                records.append({'offset': len(blob), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
                blob += data
            pak.write_bytes(bytes(blob))
            model = {'source': SOURCE, 'source_sha256': 'a' * 64, 'offset': 0, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'triangles': len(faces),
                     'materials': [{'texture_index': m, 'diffuse': [1, 1, 1]} for m in range(5)]}
            profile = M.apply_method2({'texture_size': 64}, model, table_with(row()))
            original = mesh_unit((0, model, {'texture_size': 64}, pak, records))
            v, f, polys, pieces, lod = M.mesh_unit_method2((0, model, profile, pak, records))
        self.assertEqual(lod['visual_primitive'], 'method2')
        self.assertEqual(lod['_flat_rgb'].shape, (16, 64, 3))
        panel = [p for p in polys if p[1] == 5]
        self.assertEqual(len(panel), 4)                         # one face a side
        self.assertTrue({p[1] for p in polys} <= {BASE, ROOF, METAL, 5})
        self.assertLess(len(polys), len(original[2]))
        self.assertEqual(_canonical(original[3]), _canonical(pieces))
        self.assertEqual(lod['visual_method2']['triangles'], 48)


if __name__ == '__main__':
    unittest.main()
