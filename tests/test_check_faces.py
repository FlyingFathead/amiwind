"""Face validator (tools/check_faces.py) on synthetic, asset-free BSP29 maps.

Each fixture builds a small map whose faces are wrong in exactly one way
(CONVERT-FACE-PLANE-32, CONVERT-MERGE-NONPLANAR-32, CONVERT-TEXCOORD-RANGE-32,
MESH-EXTENT-GRID-31, EXTENTS-FPU-RULE-31, LIGHTMAP-TAIL-31, LIGHTMAP-GRID-31)
and checks that the validator names that fault and nothing else.
"""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from check_faces import (CHECKS, Config, MapError, check_bsp, main, merge)  # noqa: E402
from player_hull import pack_lumps  # noqa: E402
from surface_grid import engine_grid  # noqa: E402

AXES = ((1., 0., 0., 0.), (0., 1., 0., 0.))
# Clockwise seen from +z: a correct Quake face on the floor plane z=0, facing up.
SQUARE = [(0, 0, 0), (0, 64, 0), (64, 64, 0), (64, 0, 0)]


def newell(points):
    p = np.asarray(points, dtype=np.float64)
    return np.cross(p, np.roll(p, -1, axis=0)).sum(axis=0)


def plane_of(points):
    """Quake plane for a clockwise-from-front polygon: (normal, dist, side)."""
    facing = -newell(points)
    facing /= np.linalg.norm(facing)
    normal, side = facing, 0
    axis = int(np.argmax(np.abs(normal)))
    if abs(abs(normal[axis])-1) < 1e-9 and normal[axis] < 0:
        normal, side = -normal, 1
    return normal, float(normal @ np.asarray(points[0], dtype=np.float64)), side


def plane_type(normal):
    axis = int(np.argmax(np.abs(normal)))
    return axis if abs(normal[axis]-1) < 1e-9 else 3+axis


def build(polys, planes=None, sides=None, texinfos=(AXES,), face_texinfo=None, flags=None,
          lightofs=None, styles=None, lighting=b'', models=None, entities=None,
          textures=('wall',), edges=None, surfedges=None, faces=None, plane_types=None):
    """Pack a BSP29 map, one face per polygon, vertices not shared."""
    lumps = [b''] * 15
    vertices, edge_rows, surf, face_rows, plane_rows = [], [(0, 0)], [], [], []
    for index, poly in enumerate(polys):
        base = len(vertices)
        vertices.extend(poly)
        first = len(surf)
        for i in range(len(poly)):
            edge_rows.append((base+i, base+(i+1) % len(poly)))
            surf.append(len(edge_rows)-1)
        if planes and planes[index] is not None:
            normal, dist = planes[index]
            side = sides[index] if sides else 0
        else:
            normal, dist, side = plane_of(poly)
            if sides:
                side = sides[index]
        ptype = plane_types[index] if plane_types else plane_type(np.asarray(normal, dtype=float))
        plane_rows.append(struct.pack('<4fi', *normal, dist, ptype))
        face_rows.append([index, side, first, len(poly),
                          face_texinfo[index] if face_texinfo else 0,
                          *(styles[index] if styles else (255, 255, 255, 255)),
                          lightofs[index] if lightofs else -1])
    lumps[1] = b''.join(plane_rows)
    lumps[3] = b''.join(struct.pack('<3f', *v) for v in vertices)
    lumps[12] = b''.join(struct.pack('<2H', *e) for e in (edges or edge_rows))
    lumps[13] = b''.join(struct.pack('<i', s) for s in (surfedges or surf))
    rows = faces(face_rows) if faces else face_rows
    lumps[7] = b''.join(struct.pack('<HhihH4Bi', *row) for row in rows)
    lumps[6] = b''.join(struct.pack('<8f2i', *np.asarray(vecs).reshape(-1), 0,
                                    flags[i] if flags else 0) for i, vecs in enumerate(texinfos))
    table = struct.pack('<i', len(textures))
    headers = b''
    for i, name in enumerate(textures):
        table += struct.pack('<i', 4+4*len(textures)+40*i)
        headers += name.encode().ljust(16, b'\0') + struct.pack('<6I', 16, 16, 0, 0, 0, 0)
    lumps[2] = table + headers
    lumps[8] = lighting
    model_rows = models or [(0, len(polys))]
    lumps[14] = b''.join(struct.pack('<9f7i', *([0.]*9), 0, 0, 0, 0, 0, first, count)
                         for first, count in model_rows)
    lumps[0] = (entities or b'{\n"classname" "worldspawn"\n}\n') + b'\0'
    return pack_lumps([bytearray(x) for x in lumps])


def flagged(report):
    return {name: c['flagged'] for name, c in report['checks'].items() if c['flagged']}


class CleanMapTests(unittest.TestCase):
    def test_correct_face_has_no_findings(self):
        report = check_bsp(build([SQUARE]), 'clean')
        self.assertEqual(flagged(report), {})
        self.assertFalse(report['fatal'])
        self.assertEqual((report['faces'], report['faces_checked']), (1, 1))

    def test_back_side_face_with_side_flag(self):
        # Ceiling facing down: Quake stores +z and side 1.
        ceiling = [(0, 0, 64), (64, 0, 64), (64, 64, 64), (0, 64, 64)]
        normal, dist, side = plane_of(ceiling)
        self.assertEqual((tuple(normal), side), ((0., 0., 1.), 1))
        self.assertEqual(flagged(check_bsp(build([ceiling]), 'ceiling')), {})


class GeometryTests(unittest.TestCase):
    def test_plane_from_collinear_first_vertices(self):
        # CONVERT-FACE-PLANE-32: a merged wall starting with three collinear
        # vertices gets a plane through one of them and an arbitrary fourth;
        # here the stored plane is tilted 29 degrees about the x axis.
        wall = [(0, 0, 0), (32, 0, 0), (64, 0, 0), (64, 0, 64), (0, 0, 64)]
        angle = np.radians(29)
        normal = (0., np.cos(angle), np.sin(angle))
        report = check_bsp(build([wall], planes=[(normal, 0.)], plane_types=[4]), 'tilted')
        found = flagged(report)
        self.assertEqual(set(found), {'planarity', 'plane_tilt'})
        self.assertAlmostEqual(report['checks']['plane_tilt']['worst'][0]['value'], 29, places=3)
        self.assertAlmostEqual(report['checks']['planarity']['worst'][0]['value'], 64*np.sin(angle), places=3)
        self.assertTrue(report['fatal'])

    def test_rounded_grouping_bend_warns_only(self):
        # CONVERT-MERGE-NONPLANAR-32: one vertex 0.05 units off the plane.
        bent = [(0, 0, 0), (0, 64, 0), (64, 64, 0.05), (64, 0, 0)]
        report = check_bsp(build([bent], planes=[((0., 0., 1.), 0.)]), 'bent')
        self.assertEqual(set(flagged(report)), {'planarity'})
        self.assertEqual(report['checks']['planarity']['failing'], 0)
        self.assertFalse(report['fatal'])

    def test_reversed_winding(self):
        report = check_bsp(build([SQUARE[::-1]], planes=[((0., 0., 1.), 0.)]), 'reversed')
        self.assertEqual(set(flagged(report)), {'plane_side'})
        self.assertTrue(report['fatal'])

    def test_side_flag_without_reversed_plane(self):
        report = check_bsp(build([SQUARE], sides=[1]), 'side')
        self.assertEqual(set(flagged(report)), {'plane_side'})

    def test_degenerate_faces(self):
        two = [(0, 0, 0), (64, 0, 0)]
        collinear = [(0, 0, 0), (32, 0, 0), (64, 0, 0)]
        sliver = [(0, 0, 0), (0, 0.001, 0), (64, 0.001, 0), (64, 0, 0)]
        report = check_bsp(build([two, collinear, sliver], planes=[((0., 0., 1.), 0.)]*3), 'degenerate')
        self.assertEqual(flagged(report), {'degenerate_vertices': 1, 'degenerate_area': 1,
                                           'degenerate_sliver': 1})

    def test_repeated_vertex(self):
        repeated = [SQUARE[0], SQUARE[1], SQUARE[1], SQUARE[2], SQUARE[3]]
        self.assertEqual(flagged(check_bsp(build([repeated]), 'repeated')), {'zero_length_edge': 1})

    def test_nonconvex(self):
        # A notch 8 units deep in the top edge, still clockwise from +z.
        notch = [(0, 0, 0), (0, 64, 0), (32, 56, 0), (64, 64, 0), (64, 0, 0)]
        report = check_bsp(build([notch], planes=[((0., 0., 1.), 0.)]), 'notch')
        self.assertEqual(set(flagged(report)), {'nonconvex'})
        self.assertGreater(report['checks']['nonconvex']['worst'][0]['value'], 1)


class ExtentTests(unittest.TestCase):
    def test_grid_exact_span_grows_past_limit(self):
        # MESH-EXTENT-GRID-31 fixture of tests/test_surface_grid.py: 240
        # texels with grid-exact ends become 272 once stored.
        span = [(0.1, 0, 0), (0.1, 32, 0), (240.1, 32, 0), (240.1, 0, 0)]
        vecs = ((1., 0., 0., 15.9), (0., 1., 0., 0.))
        report = check_bsp(build([span], texinfos=(vecs,)), 'span')
        self.assertIn('extents_engine', flagged(report))
        self.assertEqual(report['checks']['extents_engine']['worst'][0]['extents'], [272, 32])

    def test_special_faces_are_exempt(self):
        wide = [(0, 0, 0), (0, 64, 0), (512, 64, 0), (512, 0, 0)]
        self.assertIn('extents_engine', flagged(check_bsp(build([wide]), 'wide')))
        self.assertNotIn('extents_engine', flagged(check_bsp(build([wide], flags=[1]), 'water')))

    def test_fpu_rule_disagreement(self):
        # EXTENTS-FPU-RULE-31: 720 * float(1/3) is 240.0000072 in double
        # (extent 256) but 240.0 in single precision (extent 240).
        third = float(np.float32(1/3))
        tri = [(0, 0, 0), (0, 16, 0), (720, 0, 0)]
        report = check_bsp(build([tri], texinfos=(((third, 0., 0., 0.), (0., 1., 0., 0.)),)), 'third')
        self.assertEqual(set(flagged(report)), {'extents_rule_disagreement'})
        worst = report['checks']['extents_rule_disagreement']['worst'][0]
        self.assertEqual((worst['engine_extents'], worst['binary32_extents']), ([256, 16], [240, 16]))

    def test_extent_rule_sizes_lightmaps(self):
        # A lightmap baked for the single-precision grid (16 x 2 samples) is
        # two bytes short under the engine rule (17 x 2).
        third = float(np.float32(1/3))
        tri = [(0, 0, 0), (0, 16, 0), (720, 0, 0)]
        raw = build([tri], texinfos=(((third, 0., 0., 0.), (0., 1., 0., 0.)),), lightofs=[0],
                    styles=[(0, 255, 255, 255)], lighting=bytes(32))
        report = check_bsp(raw, 'engine rule')
        self.assertEqual(report['checks']['lightmap_outside_lump']['flagged'], 1)
        self.assertEqual(report['extent_rule'], 'engine')
        old = check_bsp(raw, 'binary32 rule', Config(extent_rule='binary32'))
        self.assertEqual(set(flagged(old)), {'extents_rule_disagreement'})
        with self.assertRaises(ValueError):
            check_bsp(raw, 'bad', Config(extent_rule='decimal'))

    def test_engine_grid_matches_surface_grid(self):
        rng = np.random.default_rng(31)
        for _ in range(50):
            base = rng.uniform(-4000, 4000, 3)
            quad = [tuple(base+offset) for offset in ((0, 0, 0), (0, 40, 0), (37.3, 40, 0), (37.3, 0, 0))]
            vecs = (tuple(rng.uniform(-1, 1, 3))+(rng.uniform(-200, 200),),
                    tuple(rng.uniform(-1, 1, 3))+(rng.uniform(-200, 200),))
            raw = build([quad], texinfos=(vecs,), lightofs=[0], styles=[(0, 255, 255, 255)],
                        lighting=bytes(100000))
            report = check_bsp(raw, 'random')
            _, extents = engine_grid(quad, vecs)
            size = ((extents[0] >> 4)+1)*((extents[1] >> 4)+1)
            mismatch = report['checks']['lightmap_span_mismatch']['worst']
            if max(extents) <= 256:
                self.assertEqual(mismatch[0]['size'], size)


class TexcoordTests(unittest.TestCase):
    def test_outside_16_bits(self):
        report = check_bsp(build([SQUARE], texinfos=(((1., 0., 0., 40000.), (0., 1., 0., 0.)),)), 'far')
        self.assertEqual(set(flagged(report)), {'texcoord_range'})

    def test_near_edge_warns(self):
        report = check_bsp(build([SQUARE], texinfos=(((1., 0., 0., 31000.), (0., 1., 0., 0.)),)), 'near')
        self.assertEqual(set(flagged(report)), {'texcoord_margin'})
        self.assertFalse(report['fatal'])


class LightmapTests(unittest.TestCase):
    # SQUARE at axes (1, 0, 0, 0)/(0, 1, 0, 0): extents 64 x 64, 5 x 5 samples.
    def test_exact_blocks(self):
        raw = build([SQUARE, SQUARE], lightofs=[0, 25], styles=[(0, 255, 255, 255)]*2, lighting=bytes(50))
        report = check_bsp(raw, 'exact')
        self.assertEqual(flagged(report), {})
        self.assertEqual(report['faces_lit'], 2)

    def test_overlap_and_tail(self):
        # LIGHTMAP-TAIL-31 / LIGHTMAP-GRID-31: blocks baked on a smaller grid.
        raw = build([SQUARE, SQUARE], lightofs=[0, 20], styles=[(0, 255, 255, 255)]*2, lighting=bytes(40))
        report = check_bsp(raw, 'short')
        self.assertEqual(flagged(report), {'lightmap_overlap': 1, 'lightmap_outside_lump': 1})
        self.assertEqual(report['checks']['lightmap_overlap']['worst'][0]['value'], 5)
        self.assertEqual(report['checks']['lightmap_outside_lump']['worst'][0]['value'], 5)

    def test_styles_multiply_size(self):
        raw = build([SQUARE], lightofs=[0], styles=[(0, 1, 255, 255)], lighting=bytes(25))
        self.assertEqual(flagged(check_bsp(raw, 'styles')), {'lightmap_outside_lump': 1})

    def test_slack_and_shared(self):
        small = [(0, 0, 0), (0, 16, 0), (16, 16, 0), (16, 0, 0)]   # 2 x 2 samples
        raw = build([SQUARE, small, SQUARE], lightofs=[0, 0, 30], styles=[(0, 255, 255, 255)]*3,
                    lighting=bytes(55))
        found = flagged(check_bsp(raw, 'slack'))
        self.assertEqual(found, {'lightmap_span_mismatch': 2, 'lightmap_shared_size': 1})

    def test_negative_offset(self):
        raw = build([SQUARE], lightofs=[-5], styles=[(0, 255, 255, 255)], lighting=bytes(25))
        self.assertEqual(flagged(check_bsp(raw, 'negative')), {'lightmap_offset': 1})


class StructureTests(unittest.TestCase):
    def test_index_ranges(self):
        def corrupt(rows):
            rows[0][0] = 7          # plane
            rows[1][4] = 9          # texinfo
            rows[2][2] = 1000       # firstedge
            return rows
        raw = build([SQUARE]*4, faces=corrupt)
        found = flagged(check_bsp(raw, 'indices'))
        self.assertEqual(found, {'face_plane_index': 1, 'face_texinfo_index': 1, 'face_edge_range': 1})

    def test_surfedge_and_vertex_ranges(self):
        surf = [1, 2, 3, 99, 5, 6, 7, 8]
        edges = [(0, 0), (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 70), (70, 4)]
        raw = build([SQUARE, [(v[0]+100, v[1], v[2]) for v in SQUARE]], surfedges=surf, edges=edges)
        found = flagged(check_bsp(raw, 'edges'))
        self.assertEqual(found, {'surfedge_index': 1, 'edge_vertex_index': 1})

    def test_edge_zero_and_open_loop(self):
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (4, 7)]
        surf = [0, 1, 2, 3, 4, 5, 6, 7]
        raw = build([SQUARE, [(v[0]+100, v[1], v[2]) for v in SQUARE]], surfedges=surf, edges=edges)
        found = flagged(check_bsp(raw, 'loops'))
        self.assertEqual(found, {'edge_zero_used': 1, 'edge_loop_open': 1})

    def test_miptex_index(self):
        raw = build([SQUARE], textures=())
        self.assertEqual(flagged(check_bsp(raw, 'miptex')), {'texinfo_miptex_index': 1})

    def test_plane_type_and_normal(self):
        floor = build([SQUARE], planes=[((0., 0., -1.), 0.)], sides=[1], plane_types=[2])
        self.assertEqual(flagged(check_bsp(floor, 'negative axial')), {'plane_type': 1})
        short = build([SQUARE], planes=[((0., 0., 0.9), 0.)], plane_types=[5])
        self.assertEqual(set(flagged(check_bsp(short, 'short normal'))), {'plane_normal'})

    def test_models_and_breakdown(self):
        entities = b'{\n"classname" "worldspawn"\n}\n{\n"classname" "func_wall"\n"model" "*1"\n}\n'
        raw = build([SQUARE, SQUARE[::-1], SQUARE], planes=[None, ((0., 0., 1.), 0.), None],
                    models=[(0, 1), (1, 1)], entities=entities)
        report = check_bsp(raw, 'models')
        self.assertEqual(flagged(report), {'plane_side': 1, 'face_unowned': 1})
        self.assertEqual(report['per_model']['1'], {'classname': 'func_wall', 'faces': 1,
                                                    'flagged': {'plane_side': 1}})
        self.assertEqual(report['checks']['plane_side']['worst'][0]['classname'], 'func_wall')
        instanced = check_bsp(build([SQUARE, SQUARE], models=[(0, 1), (1, 1), (1, 1)]), 'instances')
        self.assertEqual((flagged(instanced), instanced['instanced_models']), ({}, 1))
        overlap = check_bsp(build([SQUARE, SQUARE], models=[(0, 2), (1, 1)]), 'overlap')
        self.assertEqual(flagged(overlap), {'face_multiple_models': 1})
        bad = build([SQUARE], models=[(0, 5)])
        self.assertIn('model_face_range', flagged(check_bsp(bad, 'bad model')))

    def test_unreadable(self):
        with self.assertRaises(MapError):
            check_bsp(b'\x1e\0\0\0' + bytes(120))
        with self.assertRaises(MapError):
            check_bsp(b'')


class ConfigAndCliTests(unittest.TestCase):
    def test_every_check_documented(self):
        doc = (Path(__file__).resolve().parents[1]/'docs/FACE_VALIDATION.md').read_text(encoding='utf-8')
        for name in CHECKS:
            self.assertIn(f'`{name}`', doc)

    def test_severity_and_threshold(self):
        bent = build([[(0, 0, 0), (0, 64, 0), (64, 64, 0.5), (64, 0, 0)]], planes=[((0., 0., 1.), 0.)])
        self.assertTrue(check_bsp(bent, 'bent')['fatal'])
        config = Config()
        config.set_threshold('planarity', 'fail', 1.0)
        self.assertFalse(check_bsp(bent, 'bent', config)['fatal'])
        config = Config()
        config.set_severity('planarity', 'warn')
        report = check_bsp(bent, 'bent', config)
        self.assertFalse(report['fatal'])
        self.assertEqual(report['checks']['planarity']['failing'], 1)
        config.set_severity('planarity', 'off')
        self.assertNotIn('planarity', check_bsp(bent, 'bent', config)['checks'])
        with self.assertRaises(ValueError):
            config.set_severity('nonexistent', 'warn')
        with self.assertRaises(ValueError):
            config.set_threshold('plane_side', 'warn', 1)

    def test_merge(self):
        reports = [check_bsp(build([SQUARE[::-1]], planes=[((0., 0., 1.), 0.)]), name) for name in 'ab']
        total = merge(reports + [check_bsp(build([SQUARE]), 'c')])
        self.assertEqual((total['maps'], total['faces']), (3, 3))
        self.assertEqual(total['checks']['plane_side']['flagged'], 2)
        self.assertEqual(total['checks']['plane_side']['maps'], 2)
        self.assertEqual(set(total['maps_with_findings']), {'a', 'b'})
        self.assertTrue(total['fatal'])

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return main(list(args))

    def test_cli_exit_codes_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'good.bsp').write_bytes(build([SQUARE]))
            self.assertEqual(self.run_cli(str(root)), 0)
            (root/'bad.bsp').write_bytes(build([SQUARE[::-1]], planes=[((0., 0., 1.), 0.)]))
            report = root/'report.json'
            self.assertEqual(self.run_cli(str(root), '--report', str(report), '--maps'), 1)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(data['maps'], 2)
            self.assertEqual(len(data['map_reports']), 2)
            self.assertNotIn(b'\r', report.read_bytes())
            self.assertEqual(self.run_cli(str(root), '--severity', 'plane_side=warn'), 0)
            (root/'broken.bsp').write_bytes(b'junk')
            self.assertEqual(self.run_cli(str(root), '--severity', 'plane_side=warn'), 2)
            self.assertEqual(self.run_cli('--list-checks', str(root)), 0)


if __name__ == '__main__':
    unittest.main()
