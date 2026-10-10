# SPDX-License-Identifier: GPL-3.0-only
"""Lava as a Quake liquid (docs/LAVA.md, LAVA-NOT-IMPLEMENTED-33): the census rules, the shared converter
module (contract, footprint, brushes, entity, glow, warp texture), the builder option, the engine rules (host C)
and the source contracts that keep the engine side wired in."""
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

import lava as L  # noqa: E402
import lava_census as C  # noqa: E402


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def record(tag, subs, flags=0):
    payload = b''.join(k.encode() + struct.pack('<I', len(v)) + v for k, v in subs)
    return tag.encode() + struct.pack('<III', len(payload), 0, flags) + payload


def zstr(text, size=None):
    raw = text.encode('cp1252') + b'\0'
    return raw.ljust(size, b'\0') if size else raw


# A synthetic pool script in this test's own words: a loop sound and damage to a standing actor.
POOL_SCRIPT = 'begin hotpool\n; comment: HurtStandingActor 999\nPlayLoopSound3DVP "hot layer", 1.0, 1.0\n' \
              'HurtStandingActor, 20.0 ; per second\nend hotpool\n'


def master_bytes():
    return b''.join([
        record('SCPT', [('SCHD', zstr('hotpool', 52)), ('SCTX', POOL_SCRIPT.encode())]),
        record('SCPT', [('SCHD', zstr('quiet', 52)), ('SCTX', b'begin quiet\nend quiet\n')]),
        record('ACTI', [('NAME', zstr('pool_a')), ('MODL', zstr('i\\pool_a.nif')), ('SCRI', zstr('hotpool'))]),
        record('ACTI', [('NAME', zstr('vent')), ('MODL', zstr('x\\vent.nif')), ('SCRI', zstr('quiet'))]),
        record('STAT', [('NAME', zstr('rock')), ('MODL', zstr('x\\rock_lava.nif'))]),
        record('ACTI', [('NAME', zstr('gone')), ('MODL', zstr('i\\pool_a.nif')), ('SCRI', zstr('hotpool')),
                        ('DELE', b'\0\0\0\0')]),
    ])


def stacked_pool():
    """A 2 x 2 pool: molten plane at z -2 and a crust plane at z 0 (mesh units), one side face."""
    v, f = [], []
    for z, m in ((-2.0, 0), (0.0, 1)):
        base = len(v)
        v += [[-1, -1, z, 0, 0], [1, -1, z, 0, 0], [1, 1, z, 0, 0], [-1, 1, z, 0, 0]]
        f += [[base, base + 1, base + 2, m], [base, base + 2, base + 3, m]]
    base = len(v)
    v += [[-1, -1, -2, 0, 0], [1, -1, -2, 0, 0], [1, -1, 0, 0, 0]]
    f += [[base, base + 1, base + 2, 2]]          # a wall: not upward
    materials = [{'texture_source': 'tx_lava_molten.tga'}, {'texture_source': 'Tx_Lava_Crust.tga'},
                 {'texture_source': 'tx_rock.tga'}]
    return v, f, materials


class ContractTests(unittest.TestCase):
    def test_script_contract_reads_damage_and_sound_and_skips_comments(self):
        self.assertEqual(L.script_contract(POOL_SCRIPT), (20.0, 'hot layer'))
        self.assertEqual(L.script_contract('begin a\n; HurtStandingActor 5\nend a\n'), (0.0, ''))
        self.assertEqual(L.script_contract('HurtStandingActor 7.5'), (7.5, ''))

    def test_molten_objects_come_from_records_not_names(self):
        molten = L.molten_objects(master_bytes())
        self.assertEqual(sorted(molten), ['pool_a'])               # not the rock, not the quiet vent, not deleted
        self.assertEqual(molten['pool_a'], {'script': 'hotpool', 'dps': 20.0, 'sound': 'hot layer'})

    def test_lava_texture_names(self):
        self.assertTrue(L.is_lava_texture('textures\\Tx_Lava_Molten.dds'))
        self.assertFalse(L.is_lava_texture('tx_rock.tga'))
        self.assertFalse(L.is_lava_texture(None))


class GeometryTests(unittest.TestCase):
    def test_pool_points_take_upward_lava_faces_only(self):
        v, f, m = stacked_pool()
        pts = L.pool_points(v, f, m)
        self.assertEqual(len(pts), 8)
        self.assertEqual(sorted({float(z) for z in pts[:, 2]}), [-2.0, 0.0])
        self.assertEqual(L.pool_layers(v, f, m), ['tx_lava_molten.tga', 'Tx_Lava_Crust.tga'])   # bottom to top

    def test_footprint_is_placed_rotated_and_scaled(self):
        v, f, m = stacked_pool()
        pts = L.pool_points(v, f, m)
        ref = {'rotation_radians': [0, 0, -np.pi / 4], 'scale': 2.0, 'position': [100, 200, 50]}
        from prepare_scenery import reference_rotation
        hull, top = L.footprint(pts, reference_rotation(ref), ref['scale'], ref['position'])
        self.assertEqual(top, 50.0)
        self.assertEqual(len(hull), 4)
        r = [round(float(np.hypot(x - 100, y - 200)), 3) for x, y in hull]
        self.assertEqual(r, [round(2 * np.sqrt(2), 3)] * 4)           # corners at the scaled half-diagonal
        area = 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(hull, hull[1:] + hull[:1]))
        self.assertAlmostEqual(area, 16.0, places=3)                  # counter-clockwise, 4 x 4

    def test_convex_hull_drops_inner_and_collinear_points(self):
        hull = L.convex_hull_2d([[0, 0], [2, 0], [1, 0], [2, 2], [0, 2], [1, 1]])
        self.assertEqual(hull, [[0, 0], [2, 0], [2, 2], [0, 2]])

    def test_brushes_are_a_liquid_over_a_bed(self):
        hull = [[0, 0], [64, 0], [64, 64], [0, 64]]
        lava, bed = L.pool_brushes(hull, 100.0)
        self.assertEqual(lava.count('*lava'), 6)                      # every side: top, bottom, four walls
        self.assertEqual(bed.count(L.BED_TEXTURE), 6)
        zs = lambda text: sorted({float(z) for z in re.findall(r'\( \S+ \S+ (\S+) \)', text)})  # noqa: E731
        self.assertEqual(zs(lava), [100.0 - L.LIQUID_DEPTH, 100.0])
        self.assertEqual(zs(bed), [100.0 - L.LIQUID_DEPTH - L.BED_THICKNESS, 100.0 - L.LIQUID_DEPTH])
        # The player's feet (16.625 below the origin) stand in the liquid while the origin stays above it:
        # waterlevel 1, Morrowind's "standing on lava", never swimming.
        self.assertLess(L.LIQUID_DEPTH, 16.625)
        with self.assertRaises(ValueError):
            L.prism_brush([[0, 0], [1, 0]], 0, 1, '*lava')

    def test_entity_glow_and_bounds(self):
        hull = [[0, 0], [100, 0], [100, 100], [0, 100]]
        text = L.pool_entity(hull, 12.5)
        self.assertIn('"classname" "aw_lava"', text)
        self.assertIn('"origin" "50.00 50.00 12.50"', text)
        self.assertIn('"_aw_lava_radius" "70.71"', text)
        big = [[0, 0], [2048, 0], [2048, 1024], [0, 1024]]
        lights = L.glow_lights(big, 10)
        self.assertEqual(len(lights), 8)                             # 4 x 2 grid of 512
        self.assertTrue(all(set(l) == {'position', 'radius', 'color', 'flags'} for l in lights))
        self.assertTrue(all(l['position'][2] == 10 + L.GLOW_HEIGHT for l in lights))
        self.assertEqual(len(L.glow_lights([[0, 0], [10, 0], [10, 10], [0, 10]], 0)), 1)   # small pool: one light
        pools = [{'hull': [[400, 400], [800, 400], [800, 800], [400, 800]], 'top': 40}]
        low, high = L.quake_bounds(pools, [0, 0, 0], 0.25)
        self.assertEqual((low, high), ([100.0, 100.0, 10 - L.LIQUID_DEPTH - L.BED_THICKNESS], [200.0, 200.0, 10.0]))
        brushes, entities, records = L.map_parts([dict(pools[0], reference=7, id='pool_a', model='m', dps=20,
                                                       sound='s', layers=[])], [0, 0, 0], 0.25)
        self.assertEqual((len(brushes), len(entities), records[0]['reference'], records[0]['top']), (2, 1, 7, 10.0))
        self.assertIsNone(L.quake_bounds([], [0, 0, 0], 0.25))

    def test_warp_texture_lays_the_crust_over_the_molten_flow(self):
        molten = np.zeros((8, 8, 4), np.uint8)
        molten[...] = (200, 40, 10, 128)                 # its own alpha does not matter: the bottom layer is opaque
        crust = np.zeros((8, 8, 4), np.uint8)
        crust[...] = (40, 20, 10, 0)
        crust[:4, :, 3] = 255                            # crust on the top half, holes below
        im = np.asarray(L.lava_texture([molten, crust], size=8))
        self.assertEqual(im.shape, (8, 8, 3))
        self.assertEqual(tuple(im[0, 0]), (40, 20, 10))
        self.assertEqual(tuple(im[7, 0]), (200, 40, 10))
        with self.assertRaises(ValueError):
            L.lava_texture([])

    def test_mode_comes_from_the_environment_and_is_checked(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(L.VARIABLE, None)
            self.assertEqual(L.lava_mode(), 'quake')
            L.export_lava('static')
            self.assertEqual(L.lava_mode(), 'static')
            os.environ[L.VARIABLE] = 'molten'
            with self.assertRaises(ValueError):
                L.lava_mode()
        with self.assertRaises(ValueError):
            L.export_lava('hot')


class SoundTests(unittest.TestCase):
    """The pools' loop sound: the SOUN record, a few emitters spread over the pools, aw_loop entities."""

    def test_sound_record_stem_and_spread_emitters(self):
        raw = record('SOUN', [('NAME', zstr('Hot Layer')), ('FNAM', zstr('Fx/envrn/hot.wav')),
                              ('DATA', bytes([128, 0, 255]))])
        name, volume = L.sound_record(raw, 'hot layer')
        self.assertEqual(name, 'Fx/envrn/hot.wav')
        self.assertAlmostEqual(volume, 128 / 255)
        self.assertIsNone(L.sound_record(raw, 'other'))
        self.assertEqual(L.sound_stem('Hot Layer'), 'env/hot_layer.wav')
        sq = lambda x, y, s=100: [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]  # noqa: E731
        pools = [dict(hull=sq(0, 0, 400), top=10, sound='hot layer')] +                 [dict(hull=sq(1000 + 50 * i, 0), top=10, sound='hot layer') for i in range(6)] +                 [dict(hull=sq(0, 3000), top=10, sound='hot layer')]
        pts = L.loop_points(pools)
        self.assertEqual(len(pts), L.LOOP_LIMIT)
        self.assertEqual(pts[0]['origin'], [200.0, 200.0, 10])             # the largest pool first
        self.assertIn([50.0, 3050.0, 10], [p['origin'] for p in pts])      # then the farthest ones
        ents = L.loop_entities(pools, [0, 0, 0], 0.25, {'hot layer': 0.5})
        self.assertEqual(len(ents), L.LOOP_LIMIT)
        self.assertIn('"aw_voice" "env/hot_layer.wav"', ents[0])
        self.assertIn('"origin" "50.00 50.00 2.50"', ents[0])
        self.assertEqual(L.loop_entities(pools, [0, 0, 0], 0.25, {}), [])  # no converted sound: no emitter
        self.assertEqual(L.loop_points([]), [])

    def test_converters_place_the_loops(self):
        area = (ROOT / 'tools' / 'prepare_area.py').read_text(encoding='utf-8')
        self.assertIn('lava_rules.convert_sounds(', area)
        self.assertIn('lava_rules.loop_entities(', area)
        town = (ROOT / 'tools' / 'import_town.py').read_text(encoding='utf-8')
        self.assertIn('lava.loop_entities(mine,', town)
        self.assertIn("lava.convert_sounds(data, pools, scene / 'id1/sound', ffmpeg)", town)


class ChimGlowTests(unittest.TestCase):
    """CHIM frames have no lightmaps: the pools glow at night through the lamp table (class 8 rows)."""

    def test_glow_rows_share_a_grid_square_and_join_the_lamp_table(self):
        sq = lambda x, y, s=100: [[x, y], [x + s, y], [x + s, y + s], [x, y + s]]  # noqa: E731
        pools = [dict(hull=sq(10, 10), top=5), dict(hull=sq(200, 200), top=9),        # one square of 512
                 dict(hull=sq(9000, -300), top=1)]                                      # cell 1, -1
        rows = L.glow_rows(pools)
        self.assertEqual(len(rows), 2)
        first = [r for r in rows if r[0] == 0][0]
        self.assertEqual(first[:2], (0, 0))
        self.assertEqual((first[2], first[3], first[4]), (155.0, 155.0, 9 + L.GLOW_HEIGHT))
        self.assertEqual(first[6:], (L.LAMP_CLASS, 1))
        self.assertEqual([r for r in rows if r[0] == 1][0][:2], (1, -1))
        import light_sources as LS
        import night_lighting as NL
        self.assertNotIn(L.LAMP_CLASS, LS.LIGHT_CLASS_CODES.values())
        self.assertEqual(L.LAMP_CLASS, LS.LAVA_GLOW_CLASS)
        table = LS.lamp_table(b'', rows)
        self.assertEqual(NL.check_lamp_table(table), 2)                            # sorted by cell, valid
        self.assertEqual(LS.lamp_table(b''), LS.lamp_table(b'', ()))               # no lava: as before

    def test_image_step_adds_the_glow_only_with_quake_lava(self):
        text = (ROOT / 'tools' / 'night_lighting.py').read_text(encoding='utf-8')
        self.assertIn("lava.glow_rows(lava.exterior_pools(data_files))", text)
        self.assertIn("lava.lava_mode() == 'quake'", text)


class CensusTests(unittest.TestCase):
    def test_land_lava_counts_lava_ground_squares_per_cell(self):
        ltex = {0: {'id': 'grass', 'texture': 'tx_grass.tga'}, 4: {'id': 'MA_lava', 'texture': 'Tx_MA_lava.tga'}}
        grid = [0] * 256
        grid[:10] = [5] * 10                              # VTEX = LTEX index + 1
        grid[10] = 1
        self.assertEqual(C.land_lava(ltex, {(3, -2): tuple(grid), (0, 0): tuple([1] * 256)}), {(3, -2): 10})

    def test_lava_faces_footprint_counts_the_stacked_layers_once(self):
        v, f, m = stacked_pool()
        r = C.lava_faces(v, f, m)
        self.assertEqual((r['faces'], r['up_faces'], r['footprint'], r['area'], r['up_area']), (4, 4, 4.0, 8.0, 8.0))
        self.assertEqual(r['textures'], ['tx_lava_crust.tga', 'tx_lava_molten.tga'])
        self.assertEqual(C.lava_faces(v, f, [{'texture_source': 'a.tga'}] * 3), {})

    def test_master_extras_and_census_split_molten_from_rock(self):
        raw = master_bytes() + record('LTEX', [('NAME', zstr('MA_lava')), ('INTV', struct.pack('<i', 0)),
                                               ('DATA', zstr('Tx_MA_lava.tga'))])
        extras = C.master_extras(raw)
        self.assertEqual(extras['contracts'], {'hotpool': {'dps': 20.0, 'sound': 'hot layer'}})
        self.assertEqual(extras['scripts']['pool_a'], 'hotpool')
        extras['vtex'] = {(5, 5): tuple([1] * 3 + [0] * 253)}
        mesh = {'status': 'lava', 'area': 8.0, 'up_area': 8.0, 'footprint': 4.0, 'faces': 4, 'up_faces': 4,
                'textures': ['tx_lava_molten.tga'], 'bounds': [[-1, -1, -2], [1, 1, 0]], 'avoid_node': True}
        rock = dict(mesh, avoid_node=False, textures=['tx_ma_lava.tga'])
        masters = {'Morrowind.esm': {
            'sha256': '0' * 64,
            'objects': {'pool_a': {'type': 'ACTI', 'model': 'meshes/i/pool_a.nif', 'deleted': False},
                        'rock': {'type': 'STAT', 'model': 'meshes/x/rock_lava.nif', 'deleted': False}},
            'cells': [{'interior': True, 'x': 0, 'y': 0, 'name': 'Hot Cave', 'region': '', 'deleted': False,
                       'refs': [{'id': 'pool_a', 'p': [0, 0, 0], 'r': [0, 0, 0], 's': 2.0},
                                {'id': 'rock', 'p': [5, 5, 5], 'r': [0, 0, 0], 's': 1.0}]},
                      {'interior': False, 'x': 5, 'y': 5, 'name': '', 'region': 'Molag Mar Region', 'deleted': False,
                       'refs': [{'id': 'pool_a', 'p': [41000, 41000, 10], 'r': [0, 0, 0], 's': 1.0},
                                {'id': 'pool_a', 'p': [41000, 41100, 10], 'r': [0, 0, 0], 's': 1.0, 'del': 1}]}]}}
        census = C.build_census(masters, {'Morrowind.esm': extras},
                                {'meshes/i/pool_a.nif': mesh, 'meshes/x/rock_lava.nif': rock})
        s = census['summary']
        self.assertEqual((s['molten_placements'], s['molten_placements_exterior'], s['molten_placements_interior'],
                          s['rock_placements']), (2, 1, 1, 1))
        self.assertEqual((s['molten_cells_exterior'], s['molten_cells_interior']), (1, 1))
        self.assertEqual(s['molten_area'], 4.0 * 4 + 4.0)            # scale 2 -> footprint x 4
        self.assertEqual(s['molten_by_region'], {'(interior)': 1, 'Molag Mar Region': 1})
        self.assertEqual(s['exterior_cells_with_land_lava_rock'], 1)
        self.assertEqual(s['avoid_node_meshes'], ['meshes/i/pool_a.nif'])
        cells = C.cell_stats(census)
        self.assertEqual(cells['format'], C.CELLS_FORMAT)
        self.assertEqual(cells['cells']['Hot Cave']['status'], 'molten')
        self.assertEqual(cells['cells']['5,5'], {'interior': False, 'molten': 1, 'rock': 0, 'molten_area': 4.0,
                                                 'land_squares': 3, 'molten_meshes': ['meshes/i/pool_a.nif'],
                                                 'status': 'molten'})


class TrackerLavaTests(unittest.TestCase):
    """The per-cell lava audit (tools/cell_lava.py) and the World Map's Lava layer."""

    def test_audit_statuses(self):
        import cell_lava as V
        self.assertEqual(V.audit(None, None, False)['status'], 'not_measured')
        self.assertEqual(V.audit(0, None, True)['status'], 'none')
        self.assertEqual(V.audit(3, None, False)['status'], 'molten')
        self.assertEqual(V.audit(3, None, True)['status'], 'molten')            # a build from before the lava record
        self.assertEqual(V.audit(3, {'mode': 'static', 'pools': 0}, True)['status'], 'static')
        a = V.audit(3, {'mode': 'quake', 'pools': 3}, True)
        self.assertEqual((a['status'], a['converted_pools'], a['mode']), ('converted', 3, 'quake'))
        self.assertEqual(V.audit(3, {'mode': 'quake', 'pools': 1}, True)['status'], 'partial')
        h = V.headline([a, V.audit(2, None, False), V.audit(0, None, False)])
        self.assertEqual((h['cells_with_lava'], h['pools'], h['pools_converted']), (2, 5, 3))
        self.assertEqual(h['status']['none'], 1)
        self.assertEqual(tuple(V.STATUS_TEXT), V.STATUSES)

    def test_census_counts_molten_pools_per_cell(self):
        import collections
        from cell_progress import _count_refs
        e = {'counts': collections.Counter(), 'meshes': set(), 'placements': 0, 'flora': 0}
        objects = {'pool_a': {'type': 'ACTI', 'model': 'meshes/i/pool_a.nif', 'deleted': False},
                   'rock': {'type': 'STAT', 'model': 'meshes/x/rock.nif', 'deleted': False}}
        _count_refs(e, [{'id': 'pool_a'}, {'id': 'pool_a'}, {'id': 'rock'}, {'id': 'pool_a', 'del': 1}], objects,
                    molten=L.molten_objects(master_bytes()))
        self.assertEqual(e['lava'], 2)

    def test_world_map_layer_and_legend_preset(self):
        page = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
        for text in ("['lava', 'Lava (mapped / converted)']", 'const CHIM_LAVA = {', "'chim:lava:' + k", 'chimLavaBlock(c)'):
            self.assertIn(text, page)
        legend = (ROOT / 'amiwind-toolkit' / 'chim-legend.js').read_text(encoding='utf-8')
        self.assertIn("{id: 'lava',", legend)
        import cell_lava as V
        for status in V.STATUSES:
            if status != 'none':
                self.assertIn(status + ": ['#", page)                  # every status has a colour row


class BuilderOptionTests(unittest.TestCase):
    def test_quake_is_the_shipped_default_and_static_stays_selectable(self):
        from build_font_options import resolve_font_options
        r = resolve_font_options(SimpleNamespace(build_config=None))
        self.assertEqual((r['lava'], r['lava_selected_by']), ('quake', 'shipped default'))
        r = resolve_font_options(SimpleNamespace(build_config=None, lava='static'))
        self.assertEqual((r['lava'], r['lava_selected_by']), ('static', 'CLI override'))
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'b.json'
            cfg.write_text('{"lava": "static"}')
            r = resolve_font_options(SimpleNamespace(build_config=cfg))
            self.assertEqual((r['lava'], r['lava_selected_by']), ('static', 'build config'))
            cfg.write_text('{"lava": "molten"}')
            with self.assertRaisesRegex(ValueError, 'lava'):
                resolve_font_options(SimpleNamespace(build_config=cfg))

    def test_mode_is_a_unit_switch_and_reaches_the_room_converter(self):
        from chim.units import SWITCHES
        self.assertIn(L.VARIABLE, SWITCHES)
        area = (ROOT / 'tools' / 'prepare_area.py').read_text(encoding='utf-8')
        self.assertIn("lava_rules.pools_of(", area)
        self.assertIn("walls+=lava_brushes", area)
        self.assertIn("lava={'mode':lava_mode,'pools':lava_records}", area)
        self.assertIn('export_lava(args.font_options["lava"])', (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8'))


class ChimChunkTests(unittest.TestCase):
    """CHIM chunks carve the same lava prism into their world BSP (chim.terrain.chunk_terrain liquids)."""

    @staticmethod
    def contents(tree, point):
        n = 0
        while n >= 0:
            normal, dist, front, back = tree.nodes[n]
            n = front if float(np.dot(normal, point)) >= dist else back
        return tree.leaves[-1 - n]

    def test_lava_leaf_two_sided_warp_faces_and_a_bed_in_the_standing_hull(self):
        from chim.terrain import chunk_terrain, CONTENTS_LAVA
        hull = [[32, 32], [224, 32], [224, 224], [32, 224]]
        plain = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1)
        lumps, info = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024,
                                    lambda m: 0, 1, liquids=[{'hull': hull, 'top': 20.0}], lava_texture_id=2)
        self.assertEqual(CONTENTS_LAVA, -5)
        self.assertEqual(info['lava_faces'], 8)                    # 4 ground tiles x (up + down)
        self.assertEqual(info['lava_leaves'], 4)
        self.assertEqual(info['pieces'], plain[1]['pieces'] + 1)   # the bed
        tree = info['tree']
        self.assertEqual(self.contents(tree, (128, 128, 16)), -5)  # in lava
        self.assertEqual(self.contents(tree, (128, 128, 25)), -1)  # above it
        self.assertEqual(self.contents(tree, (128, 128, 11)), -1)  # between the ground and the lava bottom
        self.assertEqual(self.contents(tree, (10, 10, 16)), -1)    # beside it
        self.assertEqual(self.contents(tree, (128, 128, 5)), -2)   # the ground
        texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
        faces = list(struct.iter_unpack('<HhihH4Bi', lumps[7]))
        warp = [f for f in faces if texinfo[f[4]][9] & 1]
        self.assertEqual(len(warp), 8)
        self.assertTrue(all(f[9] == -1 for f in warp))           # no lightmap: drawn fully bright
        # no lava, no change: the chunk without liquids is byte for byte the earlier one
        again = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1,
                              liquids=[])
        self.assertEqual([bytes(x) for x in again[0]], [bytes(x) for x in plain[0]])
        with self.assertRaises(ValueError):
            chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1,
                          liquids=[{'hull': hull, 'top': 20.0}])     # no lava texture
        with self.assertRaises(ValueError):
            chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1,
                          liquids=[{'hull': hull[::-1], 'top': 20.0}], lava_texture_id=2)   # clockwise

    def test_overlapping_pools_merge_instead_of_multiplying_nodes(self):
        # Molag Amur places pools side by side and overlapping; carving each pool inside the other's outside used to
        # multiply nodes (17,820 extra nodes in one measured cell). Each side line now splits a region once.
        from chim.terrain import chunk_terrain
        pools = [{'hull': [[x, y], [x + 64, y], [x + 64, y + 64], [x, y + 64]], 'top': 20.0 + (x % 3)}
                 for x in range(16, 200, 40) for y in range(16, 200, 40)]          # 25 overlapping squares
        _, plain = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1)
        _, info = chunk_terrain((0, 0, 256, 256), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1,
                                liquids=pools, lava_texture_id=2)
        self.assertLess(info['nodes'] - plain['nodes'], 400)
        tree = info['tree']
        self.assertEqual(self.contents(tree, (60, 60, 15)), -5)    # where two squares overlap
        self.assertEqual(self.contents(tree, (250, 250, 15)), -1)  # outside every square
        self.assertEqual(self.contents(tree, (60, 60, 30)), -1)    # above the highest top

    def test_lava_under_the_ground_gets_no_face(self):
        from chim.terrain import chunk_terrain
        _, info = chunk_terrain((0, 0, 128, 128), 128, lambda x, y: 10.0, lambda x, y: 1, -1024, lambda m: 0, 1,
                                liquids=[{'hull': [[0, 0], [64, 0], [64, 64], [0, 64]], 'top': 5.0}],
                                lava_texture_id=2)
        self.assertEqual((info['lava_faces'], info['lava_leaves']), (0, 0))

    def test_frame_liquids_and_chunk_reach(self):
        from chim.build import frame_liquids, lava_box_reaches
        out = frame_liquids([{'hull': [[1000, 1000], [1400, 1000], [1400, 1400]], 'top': 40}], (1000, 1000))
        self.assertEqual(out, [{'hull': [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0]], 'top': 10.0}])
        self.assertTrue(lava_box_reaches(out[0], (50, 50, 300, 300)))
        self.assertFalse(lava_box_reaches(out[0], (100, 0, 300, 300)))


@unittest.skipUnless(os.environ.get('AMIWIND_TEST_QBSP'), 'requires external qbsp')
class CompiledPoolTests(unittest.TestCase):
    def test_qbsp_gives_the_pool_lava_contents_and_warp_faces(self):
        from prepare_quake import box, miptex, wad
        from PIL import Image
        hull = [[-64, -64], [64, -64], [64, 64], [-64, 64]]
        walls = [box([-128, -128, -64], [128, 128, -56], 'stone'), box([-128, -128, 120], [128, 128, 128], 'stone'),
                 box([-128, -128, -56], [-120, 128, 120], 'stone'), box([120, -128, -56], [128, 128, 120], 'stone'),
                 box([-120, -128, -56], [120, -120, 120], 'stone'), box([-120, 120, -56], [120, 128, 120], 'stone')]
        walls += L.pool_brushes(hull, 0.0)
        tile = Image.new('P', (16, 16), 0)
        textures = [(n, 68, miptex(n, tile.resize((64, 64)) if n == L.TEXTURE else tile))
                    for n in ('stone', L.TEXTURE, L.BED_TEXTURE)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pool.wad').write_bytes(wad(textures))
            (root / 'pool.map').write_text('{\n"classname" "worldspawn"\n"wad" "pool.wad"\n' + '\n'.join(walls) +
                                           '\n}\n{\n"classname" "info_player_start"\n"origin" "0 0 40"\n}\n' +
                                           L.pool_entity(hull, 0.0) + '\n')
            subprocess.run([os.environ['AMIWIND_TEST_QBSP'], '-nopercent', 'pool.map'], cwd=root, check=True,
                           stdout=subprocess.DEVNULL)
            raw = (root / 'pool.bsp').read_bytes()
        from player_hull import lumps
        lump = lumps(raw)
        contents = {struct.unpack_from('<i', lump[10], i)[0] for i in range(0, len(lump[10]), 28)}
        self.assertIn(-5, contents)                                   # CONTENTS_LAVA
        self.assertIn(b'*lava', lump[2])
        self.assertIn(b'"classname" "aw_lava"', lump[0])
        self.assertIn(b'"_aw_lava_radius"', lump[0])                  # the compiler keeps the underscore key


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EngineRuleTests(unittest.TestCase):
    def test_rules_damage_tint_ramp_and_colour(self):
        native.NativeSourceTests().compile_run('aga_lava_rules_test.c', [SRC / 'aw_lava_rules.c'], cflags=UBSAN)


class EngineWiringTests(unittest.TestCase):
    def test_damage_after_combat_tint_in_the_contents_shift_and_no_swimming(self):
        physics = code('sv_phys.c')
        self.assertLess(physics.index('AW_CombatPhysics ()'), physics.index('AW_LavaPhysics ()'))
        view = code('view.c')
        self.assertLess(view.index('AW_LavaContentsShift'), view.index('switch (contents)'))
        self.assertIn('AW_LavaInit();', code('aw_debug.c'))
        self.assertIn('AW_LavaEmbersDraw();', code('r_main.c'))
        self.assertIn('(sv_player->v.watertype != CONTENTS_LAVA)', code('sv_user.c'))
        self.assertIn('AW_CombatHurtPlayer(AW_LavaDamage(lava_dps.value,dt),"lava")', code('aw_lava.c'))
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_lava_rules.c aw_lava.c', makefile)
        qc = (ROOT / 'engine' / 'aga' / 'qc' / 'world.qc').read_text(encoding='utf-8')
        self.assertIn('self.watertype != -5', qc)
        self.assertIn('void() aw_lava = { remove(self); };', qc)
        self.assertNotIn('.float aw_lava_radius', qc)                # no edict field: the key starts with _
        walk = code('aw_walk.c')                                     # actors keep out (Morrowind's AvoidNode)
        self.assertIn('!(feet_in_lava(p,p->v.origin) && !feet_in_lava(p,origin))', walk)

    def test_blood_red_default_is_the_documented_one(self):
        header = (SRC / 'aw_lava.h').read_text(encoding='utf-8')
        tint = re.search(r'#define AW_LAVA_DEFAULT_TINT "(\d+) (\d+) (\d+)"', header).groups()
        doc = (ROOT / 'docs' / 'LAVA.md').read_text(encoding='utf-8')
        self.assertIn('| `aw_lava_tint` | `%s %s %s` |' % tint, doc)
        r, g, b = map(int, tint)
        self.assertTrue(r >= 100 and g < 16 and b < 16)             # blood red, not id's orange (255 80 0)
        self.assertIn('{"aw_lava_dps","20"}', code('aw_lava.c'))    # the pool script's damage

    def test_no_allocation_or_unseeded_rolls_in_the_rules(self):
        text = code('aw_lava_rules.c')
        self.assertIsNone(re.search(r'\b(malloc|calloc|realloc|Hunk_\w+|Z_Malloc|Cache_Alloc|rand)\s*\(', text))


if __name__ == '__main__':
    unittest.main()
