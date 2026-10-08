"""Surface extents and lightmap grids by the engine rule, from stored values.

Covers MESH-EXTENT-GRID-31 (grid-exact spans growing past 256 texels after
single-precision storage), LIGHTMAP-TAIL-31 / LIGHTMAP-GRID-31 (lightmaps
baked on the unstored grid) and VIVEC-TEXINFO-31 (unsigned texinfo indices).
All fixtures are synthetic and asset-free.
"""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from player_hull import pack_lumps
from surface_grid import (GRID_GUARD, binary32_uv, check_face, check_lumps, engine_grid,
                          grid, target_extents)

# A span of exactly 240 texels whose ends sit on 16-texel lines in double
# precision (s = 16 .. 256), but not once stored: float32(0.1) + float32(15.9)
# is just below 16 and float32(240.1) + float32(15.9) just above 256, so the
# engine rounds each end one block outward (272 texels), like the sewer
# corridor polygon of the Vivec Underworks.
SPAN = np.array([[0.1, 0., 0.], [240.1, 0., 0.], [240.1, 32., 0.], [0.1, 32., 0.]])
AXES = np.array([[1., 0., 0., 15.9], [0., 1., 0., 0.]])


def lumps_with_face(points, vecs, texinfo_count=1, texinfo_index=0, flags=0):
    sections = [b''] * 15
    sections[3] = b''.join(struct.pack('<3f', *p) for p in points)
    n = len(points)
    sections[12] = struct.pack('<HH', 0, 0) + b''.join(
        struct.pack('<HH', i, (i+1) % n) for i in range(n))
    sections[13] = b''.join(struct.pack('<i', i+1) for i in range(n))
    info = struct.pack('<8f2i', *np.asarray(vecs).reshape(-1), 0, flags)
    sections[6] = info * texinfo_count
    sections[7] = struct.pack('<HhihH4Bi', 0, 0, 0, n, texinfo_index, 255, 255, 255, 255, -1)
    return [bytearray(x) for x in sections]


class EngineRuleTests(unittest.TestCase):
    def test_engine_rule_is_double_after_every_operation(self):
        # Same fixture as tests/aga_face_texinfo_test.c: 720 * float(1/3) is
        # 240.0000072 in double but 240.0 in single precision.
        third = float(np.float32(1/3))
        points = [[0, 0, 0], [720, 0, 0], [0, 16, 0]]
        vecs = [[third, 0, 0, 0], [0, 1, 0, 0]]
        self.assertEqual(engine_grid(points, vecs), ((0, 0), (256, 16)))
        self.assertEqual(grid(binary32_uv(points, vecs))[1], (240, 16))
        self.assertEqual(target_extents(points, vecs), (256, 16))

    def test_constant_coordinates_keep_minimum_extent(self):
        self.assertEqual(engine_grid([[1, 2, 3]] * 3, [[0] * 4, [0] * 4]), ((0, 0), (16, 16)))


class GridExactSpanTests(unittest.TestCase):
    def test_double_precision_span_is_exactly_240(self):
        uv = SPAN @ AXES[:, :3].T + AXES[:, 3]
        self.assertEqual((uv[:, 0].min(), uv[:, 0].max()), (16.0, 256.0))
        lo, hi = np.floor(uv[:, 0].min()/16)*16, np.ceil(uv[:, 0].max()/16)*16
        self.assertEqual(hi - lo, 240)  # the old split_surface check passed it

    def test_stored_span_exceeds_the_limit_on_the_target(self):
        self.assertEqual(engine_grid(SPAN, AXES), ((0, 0), (272, 32)))
        self.assertEqual(target_extents(SPAN, AXES)[0], 272)
        with self.assertRaisesRegex(ValueError, 'Bad surface extents on the target'):
            check_face(SPAN, AXES)
        self.assertEqual(check_face(SPAN, AXES, special=True)[1], (272, 32))

    def test_split_surface_guard_splits_grid_exact_span(self):
        from mesh_geometry import split_surface
        self.assertEqual(GRID_GUARD, 1/16)
        pieces = split_surface(SPAN, AXES)
        self.assertGreater(len(pieces), 1)
        area = lambda q: abs(np.cross(q[1:-1]-q[0], q[2:]-q[0]).sum(axis=0)[2])/2
        self.assertAlmostEqual(sum(area(q) for q in pieces), area(SPAN))
        for piece in pieces:
            self.assertLessEqual(max(target_extents(piece, AXES)), 240)
            check_face(piece, AXES)

    def test_split_surface_keeps_spans_clear_of_the_grid(self):
        from mesh_geometry import split_surface
        inner = SPAN + [[8, 0, 0], [-8, 0, 0], [-8, 0, 0], [8, 0, 0]]
        self.assertEqual(len(split_surface(inner, AXES)), 1)

    def test_check_lumps_rejects_the_stored_span(self):
        data = lumps_with_face(SPAN, AXES)
        with self.assertRaisesRegex(ValueError, r'face 0 extents \(272, 32\)'):
            check_lumps(data)
        # Sky and water (TEX_SPECIAL) are exempt, as in the engine.
        self.assertEqual(check_lumps(lumps_with_face(SPAN, AXES, flags=1)), 1)
        self.assertEqual(check_lumps(lumps_with_face(SPAN[:, :] * [0.5, 1, 1], AXES)), 1)


def texinfo_fixture(index, count):
    """One lit face using texinfo `index` in a map with `count` texinfos."""
    points = [[0, 0, 0], [32, 0, 0], [32, 32, 0], [0, 32, 0]]
    data = lumps_with_face(points, [[1, 0, 0, 0], [0, 1, 0, 0]], count, index)
    struct.pack_into('<i', data[7], 16, 0)
    struct.pack_into('<4B', data[7], 12, 0, 255, 255, 255)
    data[8] = bytearray(9)
    data[2] = bytearray(struct.pack('<ii', 1, 8) + b'fixture'.ljust(16, b'\0')
                        + struct.pack('<6I', 16, 16, 40, 40+256, 40+320, 40+336) + bytes(340))
    data[0] = bytearray(b'{\n"classname" "worldspawn"\n}\n\0')
    data[1] = bytearray(struct.pack('<4fi', 0, 0, 1, 0, 2))
    data[10] = bytearray(struct.pack('<ii6h2H4B', -2, -1, *[0]*6, 0, 0, 0, 0, 0, 0))
    data[14] = bytearray(struct.pack('<9f7i', *[0]*9, -1, -1, -1, -1, 0, 0, 1))
    return data


class UnsignedTexinfoTests(unittest.TestCase):
    def test_tool_readers_accept_indices_up_to_65535(self):
        from check_geometry_render_inputs import BSP
        from deduplicate_bsp import light_ranges
        for index in (32767, 32768, 65535):
            with self.subTest(index=index):
                data = texinfo_fixture(index, index+1)
                self.assertEqual(check_lumps(data), 1)
                self.assertEqual(light_ranges(data), [(0, 0, 9)])
                parsed = BSP(pack_lumps(data))
                self.assertEqual(parsed.rows[7][0][4], index)
                self.assertEqual(parsed.face_inputs(0, True)[6], (32, 32))

    def test_tool_readers_reject_index_past_the_texinfo_lump(self):
        from check_geometry_render_inputs import BSP
        from deduplicate_bsp import light_ranges
        for index in (32767, 32768, 65535):
            with self.subTest(index=index):
                data = texinfo_fixture(index, index)
                with self.assertRaisesRegex(ValueError, 'texinfo'):
                    check_lumps(data)
                with self.assertRaisesRegex(ValueError, 'texinfo'):
                    light_ranges(data)
                with self.assertRaisesRegex(ValueError, 'texinfo'):
                    BSP(pack_lumps(data))


def assemble_lit(root, polygon, axes, offset):
    """One lit face through the mesh converter's assembly writer."""
    from prepare_mesh_bsp import append_meshes
    data = (np.column_stack((polygon * 4, np.zeros((len(polygon), 2)))),
            np.array([[0, 1, 3, 0]]),
            [(polygon, 0, axes, offset, np.array([0., 0, 1]))], [], {})
    ref = dict(number=1, model_index=0, scale=1, position=[0, 0, 0], rotation_radians=[0, 0, 0])
    model = dict(source='synthetic-grid.nif', triangles=2,
                 materials=[dict(texture_index=None, diffuse=[1, 1, 1])])
    (root/'scenery-index.json').write_text(json.dumps(dict(
        cell='Synthetic interior', models=[model], textures=[], references=[ref])))
    (root/'scenery.mwpak').write_bytes(b'')
    (root/'palette.lmp').write_bytes(bytes(range(256)) * 3)
    sections = [b''] * 15
    sections[0] = b'{\n"classname" "worldspawn"\n}\n\0'
    sections[2] = struct.pack('<i', 0)
    sections[10] = struct.pack('<i', -1) + bytes(24)
    sections[14] = bytes(64)
    (root/'base.bsp').write_bytes(pack_lumps(sections))
    lighting = dict(ambient=[40, 40, 40], lights=[dict(position=[400, 64, 64], radius=2000,
                                                       color=[200, 200, 200])])
    result = append_meshes(root/'base.bsp', root/'out.bsp', root, root/'palette.lmp',
                           centre=(0, 0), lighting=lighting, jobs=1, references=[1],
                           prepared_models={0: data})
    return (root/'out.bsp').read_bytes(), result


class ConverterLightmapGridTests(unittest.TestCase):
    def test_last_face_lightmap_matches_the_engine_grid(self):
        # s = 16 .. 176 in double precision (11 samples); stored, the ends
        # drift outward (0 .. 192, 13 samples). The bake must use 13.
        polygon = np.array([[0.1, 0., 0.], [160.1, 0., 0.], [160.1, 32., 0.], [0.1, 32., 0.]])
        axes = np.array([[1/64, 0], [0, 1/64], [0, 0.]])
        offset = np.array([15.9/64, 0.])
        with tempfile.TemporaryDirectory() as directory:
            raw, result = assemble_lit(Path(directory), polygon, axes, offset)
        lumps = [raw[o:o+n] for o, n in struct.iter_unpack('<ii', raw[4:124])]
        face, = struct.iter_unpack('<HhihH4Bi', lumps[7])
        vertices = np.array(list(struct.iter_unpack('<3f', lumps[3])))
        edges = list(struct.iter_unpack('<HH', lumps[12]))
        indices = [v[0] for v in struct.iter_unpack('<i', lumps[13])][face[2]:face[2]+face[3]]
        points = [vertices[edges[k][0] if k >= 0 else edges[-k][1]] for k in indices]
        vecs = np.array(struct.unpack_from('<8f', lumps[6], 40*face[4])).reshape(2, 4)
        mins, extents = engine_grid(points, vecs)
        self.assertEqual((mins, extents), ((0, 0), (192, 32)))
        self.assertEqual(face[9], 0)
        self.assertEqual(len(lumps[8]), 13*3)
        self.assertEqual(result['surface_check']['lightmap_regrids'], 1)
        self.assertEqual(result['surface_check']['faces'], 1)
        self.assertEqual(result['texinfo'], 1)


if __name__ == '__main__':
    unittest.main()
