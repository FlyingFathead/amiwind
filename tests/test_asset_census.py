# SPDX-License-Identifier: GPL-3.0-only
"""Asset census (tools/asset_census.py) on synthetic fixtures; no game data."""
import math
import random
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import asset_census as A  # noqa: E402
import world_chunk_estimate as wce  # noqa: E402


def cube(size=128.0):
    """Axis-aligned cube (Morrowind units) with planar UVs, one material, 24 vertices."""
    import numpy as np
    s = size
    quads = [((0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0), (0, 1)),      # bottom (u=x, v=y)
             ((0, 0, s), (0, s, s), (s, s, s), (s, 0, s), (0, 1)),      # top
             ((0, 0, 0), (0, 0, s), (s, 0, s), (s, 0, 0), (0, 2)),      # y=0
             ((0, s, 0), (s, s, 0), (s, s, s), (0, s, s), (0, 2)),      # y=s
             ((0, 0, 0), (0, s, 0), (0, s, s), (0, 0, s), (1, 2)),      # x=0
             ((s, 0, 0), (s, 0, s), (s, s, s), (s, s, 0), (1, 2))]      # x=s
    v, f = [], []
    for *corners, (a, b) in quads:
        base = len(v)
        for c in corners:
            v.append([*c, c[a] / s, c[b] / s])
        f.append([base, base + 1, base + 2, 0])
        f.append([base, base + 2, base + 3, 0])
    return np.array(v, float), np.array(f, int)


def bsp_with_shared_lightmap():
    """Two func_wall submodels whose single lit face points at the same 9 lightmap bytes."""
    verts, edges, surfedges, faces = [], [(0, 0)], [], []

    def square(lightofs):
        base = len(verts)
        verts.extend([(0.0, 0.0, 0.0), (32.0, 0.0, 0.0), (32.0, 32.0, 0.0), (0.0, 32.0, 0.0)])
        first = len(surfedges)
        for i in range(4):
            edges.append((base + i, base + (i + 1) % 4))
            surfedges.append(len(edges) - 1)
        faces.append(struct.pack('<HhiHH4Bi', 0, 0, first, 4, 0, 0, 255, 255, 255, lightofs))
    square(-1)            # world face, unlit
    square(0)
    square(0)
    models = [struct.pack('<9f7i', -64, -64, -1, 64, 64, 1, 0, 0, 0, -1, -1, -1, -1, 0, 0, 1),
              struct.pack('<9f7i', 0, 0, 0, 32, 32, 0, 0, 0, 0, -1, -1, -1, -1, 0, 1, 1),
              struct.pack('<9f7i', 0, 0, 0, 32, 32, 0, 0, 0, 0, -1, -1, -1, -1, 0, 2, 1)]
    ents = ('{\n"classname" "worldspawn"\n}\n{\n"classname" "func_wall"\n"model" "*1"\n"aw_ref" "11"\n}\n'
            '{\n"classname" "func_wall"\n"model" "*2"\n"aw_ref" "12"\n}\n')
    head = b't0'.ljust(16, b'\0') + struct.pack('<II4I', 16, 16, 40, 296, 360, 376)
    tex = struct.pack('<ii', 1, 8) + head + bytes(256 + 64 + 16 + 4)
    lumps = [ents.encode() + b'\0', struct.pack('<4fi', 0, 0, 1, 0, 2), tex,
             b''.join(struct.pack('<3f', *p) for p in verts), b'', b'',
             struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0), b''.join(faces), bytes(9), b'',
             struct.pack('<2i6h2H4B', -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), b'',
             b''.join(struct.pack('<2H', *e) for e in edges), b''.join(struct.pack('<i', s) for s in surfedges),
             b''.join(models)]
    header = bytearray(struct.pack('<i', 29))
    body = bytearray()
    for lump in lumps:
        header.extend(struct.pack('<ii', wce.HEADER + len(body), len(lump)))
        body.extend(lump)
        body.extend(b'\0' * (-len(body) % 4))
    return bytes(header + body)


def placement(model, s=1.0, r=(0.0, 0.0, 0.0), cls='clutter'):
    return {'model': model, 's': s, 'r': list(r), 'cls': cls}


class ClassesAndAngles(unittest.TestCase):
    def test_mesh_classes_follow_the_mesh_name(self):
        self.assertEqual(A.mesh_class('meshes/x/terrain_rock_ac_01.nif'), 'rocks')
        self.assertEqual(A.mesh_class('meshes/f/flora_tree_01.nif'), 'flora')
        self.assertEqual(A.mesh_class('meshes/x/ex_hlaalu_b_01.nif'), 'buildings')
        self.assertEqual(A.mesh_class('meshes/i/in_c_wall_01.nif'), 'buildings')
        self.assertEqual(A.mesh_class('meshes/f/furn_de_table_01.nif'), 'furniture')
        self.assertEqual(A.mesh_class('meshes/o/chest.nif', 'CONT'), 'furniture')
        self.assertEqual(A.mesh_class('meshes/m/misc_cup.nif', 'MISC'), 'clutter')
        self.assertEqual(A.mesh_class('meshes/bm/bm_rock_01.nif'), 'rocks')

    def test_tilt_is_the_angle_of_the_up_axis(self):
        self.assertAlmostEqual(A.tilt_degrees([0, 0, 2.0]), 0.0)
        self.assertAlmostEqual(A.tilt_degrees([math.radians(10), 0, 0]), 10.0, places=6)
        self.assertAlmostEqual(A.tilt_degrees([0, math.radians(30), 1.0]), 30.0, places=6)

    def test_octave_quantization_keeps_unit_scale(self):
        self.assertEqual(A.quantize_octave(1.0, 4), 1.0)
        self.assertAlmostEqual(A.quantize_octave(1.1, 4), 2 ** 0.25)
        self.assertAlmostEqual(A.quantize_octave(0.5, 8), 0.5)
        self.assertLessEqual(abs(A.quantize_octave(1.37, 16) / 1.37 - 1), 2 ** (1 / 32) - 1)

    def test_per_mesh_levels_span_the_range(self):
        lv = A.mesh_levels([0.8, 1.0, 1.6], 3)
        self.assertAlmostEqual(lv[0], 0.8)
        self.assertAlmostEqual(lv[-1], 1.6)
        self.assertAlmostEqual(A.nearest_level(1.5, lv), 1.6)
        self.assertEqual(A.mesh_levels([1.2, 1.2], 4), [1.2])

    def test_histograms(self):
        h = A.scale_histogram([1.0, 1.0, 0.55, 1.5, 2.5])
        self.assertEqual(h['exact_1'], 2)
        self.assertEqual(sum(h['bins']), 3)
        self.assertEqual(h['distinct_values'], 4)
        self.assertEqual(A.histogram([0.0, 1.5, 100], (0.0, 1.0, 2.0)), [0, 1, 1, 1])


class Variants(unittest.TestCase):
    def test_variant_counts_per_policy(self):
        rows = [placement('a', 1.0), placement('a', 1.0), placement('a', 1.05), placement('a', 1.5),
                placement('b', 1.0, (0.2, 0.0, 1.0)), placement('b', 1.0, (0.2, 0.0, 2.0)), placement('b', 1.0)]
        t = A.variant_table(rows)
        self.assertEqual(t['variants_today'], 6)      # a: 1.0, 1.05, 1.5; b: two tilted yaws + flat
        pol = {r['scale']: r for r in t['policies']}
        self.assertEqual(pol['runtime']['variants_tilt_runtime'], 2)
        self.assertEqual(pol['runtime']['variants_tilt_exact'], 4)
        self.assertEqual(pol['octave4']['variants_tilt_exact'], 5)   # 1.05 joins 1.0
        self.assertAlmostEqual(pol['runtime']['dedup_tilt_runtime'], 3.0)
        self.assertIn('scale_error_max', pol['octave8'])

    def test_quantized_tilt_shares_close_yaws(self):
        rows = [placement('b', 1.0, (0.2, 0.0, 1.0)), placement('b', 1.0, (0.2, 0.0, 1.05)),
                placement('b', 1.0, (0.2, 0.0, 2.0))]
        pol = {r['scale']: r for r in A.variant_table(rows)['policies']}
        self.assertEqual(pol['exact']['variants_tilt_exact'], 3)
        self.assertEqual(pol['exact']['variants_tilt_quant'], 2)
        self.assertEqual(pol['exact']['variants_tilt_runtime'], 1)

    def test_flat_yaw_does_not_make_a_variant(self):
        rows = [placement('a', 1.0, (0, 0, 0.3)), placement('a', 1.0, (0, 0, 2.3))]
        self.assertEqual(A.variant_table(rows)['variants_today'], 1)


class MeshCensus(unittest.TestCase):
    def test_cube_counts_follow_the_converter(self):
        v, f = cube()
        c = A.mesh_census(v, f, None, {'texture_size': 32}, [{'texture_source': 'tx_a.dds', 'diffuse': (1, 1, 1)}])
        self.assertEqual(c['faces'], 6)
        self.assertEqual(c['vertexes'], 8)
        self.assertEqual(c['edges'], 12)
        self.assertEqual(c['surfedges'], 24)
        self.assertEqual(c['planes'], 6)
        self.assertEqual(c['luxels'], 6 * 9)           # 32 texels each way: 3 x 3 samples per face
        self.assertEqual(c['textures'], ['textures/tx_a|32|1,1,1|0'])
        self.assertEqual(c['nodes'], 6)
        self.assertGreaterEqual(c['clipnodes'], 6)
        self.assertEqual(A.geometry_bytes(c), 6 * 20 + 24 * 4 + 12 * 4 + 8 * 12 + c['texinfo'] * 40 + 6 * 20 + 64)
        self.assertEqual(A.luxels_at(c, 1.0), 54)
        self.assertGreater(A.luxels_at(c, 2.0), 54)

    def test_collision_only_profile_has_no_faces(self):
        v, f = cube()
        c = A.mesh_census(v, f, None, {'collision_only': True}, [])
        self.assertEqual((c['faces'], c['textures']), (0, []))
        self.assertGreater(c['clipnodes'], 0)

    def test_texture_bytes(self):
        self.assertEqual(A.miptex_bytes(32), 40 + 32 * 32 + 16 * 16 + 8 * 8 + 4 * 4)
        self.assertEqual(A.miptex_bytes(64), 40 + 64 * 64 * 85 // 64)


class Chunks(unittest.TestCase):
    def brute(self, boxes, items, nitems, grain, radius, weights):
        g = A.ChunkGrid(boxes, items, nitems, grain, radius)
        out = {}
        for i in range(g.pad, g.nx - g.pad):
            for j in range(g.pad, g.ny - g.pad):
                cx, cy = (i + g.x0) * grain, (j + g.y0) * grain
                need = set()
                for (x0, y0, x1, y1), it in zip(boxes, items):
                    # chunk squares the box touches, within radius of the owned square
                    for a in range(int(math.floor(x0 / grain)), int(math.floor(x1 / grain)) + 1):
                        for b in range(int(math.floor(y0 / grain)), int(math.floor(y1 / grain)) + 1):
                            gx = max(abs(a * grain - cx) - grain, 0)
                            gy = max(abs(b * grain - cy) - grain, 0)
                            if math.hypot(gx, gy) <= radius:
                                need.add(it)
                out[(i, j)] = sum(weights[k] for k in need)
        return g, out

    def test_ring_totals_match_brute_force(self):
        rnd = random.Random(5)
        boxes, items = [], []
        for _ in range(40):
            x, y = rnd.uniform(-900, 900), rnd.uniform(-900, 900)
            w = rnd.uniform(1, 300)
            boxes.append([x, y, x + w, y + rnd.uniform(1, 300)])
            items.append(rnd.randrange(70))
        weights = [rnd.randrange(1, 1000) for _ in range(70)]
        for grain in (256, 512):
            g, ref = self.brute(boxes, items, 70, grain, 636, weights)
            sums, count = g.ring_totals({'w': weights}, max_cells=4096)
            for (i, j), v in ref.items():
                self.assertAlmostEqual(sums['w'][i, j], v, delta=0.5)
            i, j = next(iter(ref))
            self.assertEqual(sum(weights[k] for k in g.ring_items(i, j)), ref[(i, j)])

    def test_ring_offsets(self):
        offs = A.ring_offsets(256, 636)
        self.assertIn((0, 0), offs)
        self.assertIn((3, 0), offs)
        self.assertNotIn((4, 0), offs)
        self.assertNotIn((3, 3), offs)
        self.assertEqual(len(offs), len(set(offs)))

    def test_route_and_cache(self):
        route = A.door_route([(900, 0), (0, 0), (300, 0)])
        self.assertEqual(route, [(0.0, 0.0), (300.0, 0.0), (900.0, 0.0)])
        boxes = [[0, 0, 10, 10], [1200, 0, 1210, 10], [3000, 0, 3010, 10]]
        g = A.ChunkGrid(boxes, [0, 1, 2], 3, 256, 636)
        seq = A.walk_chunks([(0, 0), (3000, 0), (0, 0)], g)
        self.assertGreater(len(seq), 10)
        weights = [100, 200, 400]
        small = A.simulate_cache(seq, g.ring_items, weights, 0)
        big = A.simulate_cache(seq, g.ring_items, weights, 10 ** 6)
        self.assertEqual(small['cold_bytes'], 100)
        self.assertLess(big['bytes_read'], small['bytes_read'])   # walking back hits the kept models
        self.assertEqual(big['bytes_read'], 600)
        self.assertGreater(big['hit_rate'], small['hit_rate'])


class MapsAndDisk(unittest.TestCase):
    def test_shared_lightmap_is_split_between_placements(self):
        res = A.map_bakes(bsp_with_shared_lightmap())
        self.assertEqual(res['lighting_lump'], 9)
        rows = {r['ref']: r for r in res['placements']}
        self.assertEqual(sorted(rows), [11, 12])
        self.assertEqual(rows[11]['luxels'], 9)
        self.assertAlmostEqual(rows[11]['stored'], 4.5)
        self.assertAlmostEqual(rows[11]['stored'] + rows[12]['stored'], 9.0)
        self.assertEqual(res['world']['luxels'], 0)

    def test_terrain_cost_counts_the_world_model(self):
        t = A.terrain_cost(bsp_with_shared_lightmap())
        self.assertEqual(t['faces'], 1)
        self.assertEqual(t['lumps']['lighting_stored'], 0)
        self.assertGreater(t['terrain_bytes'], 0)

    def test_heightfield(self):
        h = A.heightfield_bytes(luxel_units=16)
        self.assertEqual(h['heights'], 65 * 65 * 2)
        self.assertEqual(h['lightmap'], 129 * 129)
        self.assertEqual(A.heightfield_bytes(luxel_units=32)['lightmap'], 65 * 65)
        self.assertEqual(A.heightfield_bytes(lightmap=False)['total'], 65 * 65 * 2 + 256)

    def test_disk_plan(self):
        plan = A.disk_plan({'a': int(2.5e9), 'b': int(1e9)}, int(1.66e9))
        self.assertEqual(plan['partitions'], 3)
        self.assertEqual(plan['images'], 2)
        self.assertFalse(plan['fits_one_image'])
        self.assertEqual(plan['packs_per_kind']['a'], 3)
        self.assertTrue(A.disk_plan({'a': 100}, int(1.66e9))['fits_one_image'])

    def test_streamer_kinds(self):
        vb = {'geometry_bytes': 1000, 'hull_bytes': 300, 'variants': 2}
        space = {'variant_bytes': {k: vb for k in ('runtime/runtime', 'octave8/quant')},
                 'variants': {'placements': 10},
                 'unique': {'per_class': {'buildings': {'geometry': 400, 'placed_geometry': 1600}}},
                 'luxels_per_placement_estimated': {'buildings': 1000, 'clutter': 500},
                 'angles': {k: {'placements': 2} for k in A.CLASSES}}
        rep = {'sets': {'x': {'exterior': dict(space), 'interior': dict(space),
                              'textures_both_spaces': {'texture_bytes': 50},
                              'terrain': {'island_32': 70}}}}
        bakes = {'per_class': {'buildings': {'luxels': 100, 'stored': 25}}}
        k = A.streamer_kinds(rep, bakes, extra={'sound': 5})
        self.assertEqual(k['interior lightmaps (tier 2)'], 250)
        self.assertEqual(k['interior light levels (tier 3)'], 4)       # flora + clutter
        self.assertEqual(k['placement records'], 20 * A.PLACEMENT_RECORD)
        self.assertEqual(k['sound'], 5)
        kit = A.streamer_kinds(rep, bakes, kit_in_maps=True)
        self.assertEqual(kit['interior geometry'], 1000 + 1200)

    def test_interior_map_cells_come_from_the_area_configs(self):
        cells = A.interior_map_cells()
        self.assertTrue(all(isinstance(k, str) and isinstance(v, str) for k, v in cells.items()))


if __name__ == '__main__':
    unittest.main()
