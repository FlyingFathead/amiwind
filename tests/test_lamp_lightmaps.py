# SPDX-License-Identifier: GPL-3.0-only
"""Night-lamp lightmaps: lamp-only bake, engine grid, terrain entities, render pool."""
import re, struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from interior_lighting import bake_surface
import lamp_lightmaps as LL
from player_hull import lumps, pack_lumps

IDENTITY = np.eye(3)
SQUARE = np.array([[0, 0, 0], [32, 0, 0], [32, 32, 0], [0, 32, 0]], dtype=float)
AXES = np.array([[1, 0], [0, 1], [0, 0]], dtype=float)
LAMP = {'position': [16 * 4, 16 * 4, 10 * 4], 'radius': 20 * 4, 'color': [255, 255, 255]}


def lamp_only(**extra):
    return {'ambient': [0, 0, 0], 'falloff': 'original', 'facing': True, 'lights': [LAMP], **extra}


def sub(tag, data): return tag.encode() + struct.pack('<I', len(data)) + data
def record(tag, body): return tag.encode() + struct.pack('<III', len(body), 0, 0) + body


def master(lights, placements):
    out = b''
    for identifier, model, radius, colour, flags in lights:
        lhdt = struct.pack('<fiiI', 1.0, 0, 0, radius) + bytes(colour) + b'\0' + struct.pack('<I', flags)
        out += record('LIGH', sub('NAME', identifier + b'\0') + sub('MODL', model + b'\0') + sub('LHDT', lhdt))
    body = sub('NAME', b'\0') + sub('DATA', struct.pack('<Iii', 0, -3, -3))
    for n, (identifier, pos) in enumerate(placements, 1):
        body += sub('FRMR', struct.pack('<I', n)) + sub('NAME', identifier + b'\0') + sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))
    return out + record('CELL', body)


def tiny_bsp(placements):
    """World without faces; submodel 1 = an up-facing and a down-facing square."""
    verts = [(0, 0, 0), (32, 0, 0), (32, 32, 0), (0, 32, 0)]
    edges = [(0, 0), (0, 1), (1, 2), (2, 3), (3, 0)]
    up = [-4, -3, -2, -1]      # reversed loop: front side +z
    down = [1, 2, 3, 4]
    faces = [(0, 0, 0, 4, 0, 255, 255, 255, 255, -1), (0, 1, 4, 4, 0, 255, 255, 255, 255, -1)]
    world = (-64, -64, -64, 64, 64, 64, 0, 0, 0, 0, -1, -1, -1, 0, 0, 0)
    model = (0, 0, -1, 32, 32, 1, 0, 0, 0, 0, -1, -1, -1, 0, 0, 2)
    text = '{\n"classname" "worldspawn"\n"message" "test"\n}\n'
    for n, (origin, yaw) in enumerate(placements, 1):
        text += '{\n"classname" "func_wall"\n"aw_ref" "%d"\n"model" "*1"\n"origin" "%s"\n"angles" "0 %s 0"\n}\n' % (
            n, origin, yaw)
    data = [bytearray() for _ in range(15)]
    data[0] = bytearray((text + '\0').encode())
    data[1] = bytearray(struct.pack('<4fi', 0, 0, 1, 0, 2))
    data[3] = bytearray(b''.join(struct.pack('<3f', *v) for v in verts))
    data[6] = bytearray(struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0))
    data[7] = bytearray(b''.join(struct.pack('<Hhihh4Bi', *f) for f in faces))
    data[12] = bytearray(b''.join(struct.pack('<HH', *e) for e in edges))
    data[13] = bytearray(b''.join(struct.pack('<i', e) for e in up + down))
    data[14] = bytearray(struct.pack('<9f7i', *world) + struct.pack('<9f7i', *model))
    return pack_lumps(data)


def parsed(raw):
    data = lumps(raw)
    text = bytes(data[0]).rstrip(b'\0').decode()
    records = [dict(re.findall(r'"([^"\n]*)" "([^"\n]*)"', b)) for b in re.findall(r'\{[^{}]*\}', text)]
    faces = list(struct.iter_unpack('<Hhihh4Bi', data[7]))
    models = list(struct.iter_unpack('<9f7i', data[14]))
    return data, records, faces, models


class LampOnlyBakeTests(unittest.TestCase):
    def test_lamp_only_map_has_no_base_and_ends_at_twice_the_radius(self):
        near = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lamp_only(), front=[0, 0, 1])
        self.assertTrue(max(near) > 0)
        far = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.array([200., 0, 0]), lamp_only(),
                           front=[0, 0, 1])
        self.assertEqual(set(far), {0})

    def test_lambert_lights_only_the_front_side(self):
        front = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lamp_only(), front=[0, 0, 1])
        back = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lamp_only(), front=[0, 0, -1])
        self.assertEqual(set(back), {0})
        flat = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lamp_only(facing=False))
        self.assertTrue(all(f <= g for f, g in zip(front, flat)))
        self.assertLess(sum(front), sum(flat))

    def test_explicit_grid_sets_the_sample_count(self):
        samples = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lamp_only(),
                               sample_grid=((0, 0), (3, 4)), front=[0, 0, 1])
        self.assertEqual(len(samples), 12)

    def test_default_bake_is_unchanged_without_lambert(self):
        lighting = {'ambient': [40, 40, 40], 'lights': [LAMP]}
        a = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lighting)
        b = bake_surface(SQUARE, AXES, np.zeros(2), IDENTITY, np.zeros(3), lighting, front=[0, 0, -1])
        self.assertEqual(a, b)
        self.assertEqual(min(a), 40)


class GridAndGeometryTests(unittest.TestCase):
    def test_engine_grid_matches_calc_surface_extents(self):
        points = [(0, 0, 0), (32, 0, 0), (32, 16, 0), (0, 16, 0)]
        vecs = [(1, 0, 0, 0), (0, 1, 0, 0)]
        self.assertEqual(LL.engine_grid(points, vecs), ((0, 0), (3, 2)))
        # Constant UVs still get the engine's minimum 16-unit extent.
        self.assertEqual(LL.engine_grid(points, [(0, 0, 0, 5), (0, 0, 0, 5)]), ((0, 0), (2, 2)))
        self.assertEqual(LL.engine_grid([(-1, -17, 0), (15, 0, 0), (0, 3, 0)], vecs), ((-16, -32), (3, 4)))

    def test_polygon_distance(self):
        n = np.array([0, 0, 1.])
        self.assertAlmostEqual(LL.polygon_distance(np.array([16, 16, 5.]), SQUARE, n), 5)
        self.assertAlmostEqual(LL.polygon_distance(np.array([40, 16, 0.]), SQUARE, n), 8)


class RegionAndTerrainTests(unittest.TestCase):
    settings = {'centre': [-20480, -12288], 'scale': 0.25}

    def test_region_lamps_keep_lamps_reaching_the_coverage(self):
        raw = master([(b'light_de_streetlight_01_223', b'l\\light_de_streetlight_01.nif', 223, (245, 140, 40), 1),
                      (b'light_fire_100', b'l\\fire.nif', 100, (255, 100, 0), 0x10)],
                     [(b'light_de_streetlight_01_223', (-20480 + 400, -12288, 700)),
                      (b'light_de_streetlight_01_223', (-20480 + 4000, -12288, 700)),
                      (b'light_fire_100', (-20480, -12288, 700))])
        lamps = LL.region_lamps(raw, [[0, -50], [50, 50]], self.settings)
        self.assertEqual(len(lamps), 1)
        lamp = lamps[0]
        self.assertEqual((lamp['style'], lamp['radius'], lamp['placed_at']), (32, 55.75, 'placement'))
        self.assertEqual(lamp['position'], [100.0, 0.0, 175.0])

    def test_terrain_entities_fit_and_coverage(self):
        lamp = {'class': 'lamp', 'radius': 55.75, 'colour': [245, 140, 40], 'flags': 1, 'style': 32,
                'position': [100.0, 0.0, 175.0], 'source_position': [-20080.0, -12288.0, 700.0]}
        outside = dict(lamp, position=[500.0, 0.0, 175.0])
        texts = LL.terrain_entities([lamp, outside], self.settings, LL.ORIGINAL_FIT, [[0, -50], [200, 50]])
        self.assertEqual(len(texts), 1)
        keys = dict(re.findall(r'"([^"\n]*)" "([^"\n]*)"', texts[0]))
        self.assertEqual(keys['classname'], 'light')
        self.assertEqual((keys['style'], keys['delay'], keys['light'], keys['_anglescale']), ('32', '0', '300', '1'))
        self.assertEqual(keys['_falloff'], '98.0')
        self.assertEqual(keys['origin'], '100.00 0.00 175.00')
        self.assertEqual(texts[0].count('"delay"'), 1)

    def test_light_entities_are_removed_from_the_runtime_lump(self):
        lump = b'{\n"classname" "worldspawn"\n}\n{\n"classname" "light"\n"style" "32"\n}\n{\n"classname" "func_wall"\n}\n\0'
        out = LL.strip_light_entities(lump)
        self.assertNotIn(b'"light"', out)
        self.assertIn(b'func_wall', out)
        self.assertTrue(out.endswith(b'\0'))


class RenderPoolTests(unittest.TestCase):
    lamps = [{'position': [16.0, 16.0, 10.0], 'radius': 20.0, 'colour': [255, 255, 255], 'style': 32}]
    placements = [('0 0 0', '0'), ('1000 0 0', '0'), ('0 0 0', '90')]

    def test_lit_placements_get_their_own_maps_through_the_pool(self):
        raw = tiny_bsp(self.placements)
        out, report = LL.add_lamp_pool(raw, self.lamps)
        data, records, faces, models = parsed(out)
        self.assertEqual(report['placements_lit'], 2)
        self.assertEqual(report['faces_baked'], 2)
        self.assertEqual(report['faces_near_unlit'], 2)     # the down-facing squares
        self.assertEqual(report['model_variants_added'], 1)
        pool = models[int(records[0]['aw_render_pool'][1:])]
        first, count = pool[14], pool[15]
        self.assertEqual((first, count), (1, 3))           # tail face + two lit copies
        lit = [records[1], records[3]]
        for r, expected in zip(lit, ('1:1', '2:1')):
            self.assertEqual(r['aw_render_ranges'], expected)
            variant = models[int(r['model'][1:])]
            self.assertEqual(variant[14:16], (0, 1))      # only the never-lit face
        self.assertNotIn('aw_render_ranges', records[2])
        self.assertEqual(records[2]['model'], '*1')
        self.assertEqual(models[1][14:16], (0, 2))
        for copy in faces[2:4]:
            self.assertEqual(copy[5:9], (32, 255, 255, 255))
            self.assertGreaterEqual(copy[9], 0)
        # The shared faces keep no lightmap; the far placement is unchanged.
        self.assertEqual([f[9] for f in faces[:2]], [-1, -1])
        self.assertEqual(LL.check_lamp_grids(out), (2, []))
        self.assertEqual(len(data[8]), 2 * 3 * 3)          # two 3x3 blocks (yaw differs)

    def test_without_header_room_unlit_placements_draw_the_tail(self):
        out, report = LL.add_lamp_pool(tiny_bsp(self.placements), self.lamps, model_budget=2)
        data, records, faces, models = parsed(out)
        self.assertEqual(report['model_variants_added'], 0)
        self.assertEqual(models[1][14:16], (0, 1))
        self.assertEqual(records[2]['aw_render_ranges'], '0:1')
        self.assertEqual(report['submodels_total'], 2)       # submodel + pool
        with self.assertRaises(ValueError):
            LL.add_lamp_pool(tiny_bsp(self.placements), self.lamps, model_budget=1)

    def test_far_lamps_change_nothing_and_existing_pools_are_refused(self):
        raw = tiny_bsp(self.placements)
        far = [dict(self.lamps[0], position=[5000.0, 0.0, 0.0])]
        out, report = LL.add_lamp_pool(raw, far)
        self.assertEqual(lumps(out)[7], lumps(raw)[7])
        self.assertEqual(report['placements_lit'], 0)
        self.assertNotIn(b'aw_render_pool', bytes(lumps(out)[0]))
        pooled, _ = LL.add_lamp_pool(raw, self.lamps)
        with self.assertRaises(ValueError):
            LL.add_lamp_pool(pooled, self.lamps)

    def test_min_peak_drops_faint_faces(self):
        _, report = LL.add_lamp_pool(tiny_bsp(self.placements), self.lamps, min_peak=256)
        self.assertEqual(report['faces_baked'], 0)


if __name__ == '__main__':
    unittest.main()
