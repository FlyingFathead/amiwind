# SPDX-License-Identifier: GPL-3.0-only
"""Static flames and placement light on CHIM frames (CHIM-EXTERIOR-FLAMES-MISSING-48, CHIM-MESHLESS-LIGHTS-33).

Flames: a CHIM model keeps its particle emitters in its entity lump (model frame); the frame maps of towns, region
frames and batch rooms now carry them as aw_flame rows (tools/chim/flames.py), at the places the town and room
converters put them (prepare_mesh_bsp.flame_entities), within the engine's per-map table (STATIC_FLAME_MAX).
Lights: every exterior light source that adds light, the lights without a mesh among them, gives the placements it
reaches a light level in their placed records (world format 0.12, tools/chim/placement_light.py)."""
import json
import math
import os
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import flames as FL  # noqa: E402
from chim import format as F  # noqa: E402
from chim import placement_light as PL  # noqa: E402

ENGINE = ROOT / 'engine/aga/src'
# A campfire's emitter (prepare_scenery.model_flames row, NIF units): x, y, z, size, particle, rise, spread
CAMPFIRE = [8.0, 0.0, 16.0, 8.0, 24.0, 40.0, 12.0]


def model_image(entities_text, name='l/light_fire'):
    lumps = [b''] * 15
    lumps[0] = (entities_text + '\0').encode('ascii')
    return {'name': name, 'image': F.brush_image(lumps)[0]}


def flame_text(*rows):
    return ''.join('{\n"classname" "aw_flame"\n"origin" "%.2f %.2f %.2f"\n"aw_flame_size" "%.2f"\n%s}\n'
                   % (x, y, z, size, '"aw_flame_shape" "%s"\n' % shape if shape else '')
                   for x, y, z, size, shape in rows)


def record(model, origin, yaw=0.0, flags=0, angles=None):
    r = {'model': model, 'origin': tuple(origin), 'yaw': yaw, 'flags': flags, 'ref': 1}
    if angles is not None:
        r['angles'] = tuple(angles)
    return r


class FlameRowsTests(unittest.TestCase):
    def test_emitters_are_read_from_the_model_entity_lump(self):
        m = model_image('{\n"classname" "worldspawn"\n}\n' + flame_text((2, 0, 4, 2, '6.00 10.00 3.00'),
                                                                         (0, 1, 2, 0.8, None)))
        found = FL.model_flames(m['image'])
        self.assertEqual([f['origin'] for f in found], [(2.0, 0.0, 4.0), (0.0, 1.0, 2.0)])
        self.assertEqual([(f['size'], f['shape']) for f in found], [('2.00', '6.00 10.00 3.00'), ('0.80', None)])
        self.assertEqual(FL.model_flames(model_image('')['image']), [])

    def test_the_placement_turns_its_emitters_as_the_engine_turns_the_model(self):
        flames = FL.model_flames(model_image(flame_text((2, 0, 4, 8, '6.00 10.00 3.00')))['image'])
        row = FL.placed_flames(record(0, (100, 200, 30), yaw=90.0), flames)[0]
        self.assertEqual(row['origin'], '100.00 202.00 34.00')
        self.assertEqual((row['aw_flame_size'], row['aw_flame_shape']), ('8.00', '6.00 10.00 3.00'))
        # a 0.8 record: the three angles through chim.placed.model_matrix
        import numpy as np
        from chim.placed import model_matrix
        angles = (10.0, 30.0, 5.0)
        row = FL.placed_flames(record(0, (1, 2, 3), angles=angles), flames)[0]
        want = np.array([1, 2, 3]) + model_matrix(angles) @ np.array([2.0, 0.0, 4.0])
        self.assertEqual(row['origin'], '%.2f %.2f %.2f' % tuple(want))

    def test_story_hidden_and_not_fire_meshes_get_none(self):
        models = {0: model_image(flame_text((0, 0, 0, 8, None))),
                  1: model_image(flame_text((0, 0, 0, 2, None)), name='f/active_blight_large'),
                  2: model_image(flame_text((0, 0, 0, 2, None)), name='x/terrain_lava_vent@t1')}
        chunks = [{'owned': [record(0, (0, 0, 0)), record(0, (50, 0, 0), flags=F.FLAG_STORY_HIDDEN),
                             record(1, (90, 0, 0)), record(2, (120, 0, 0))]}]
        rows, report = FL.frame_rows(chunks, models)
        self.assertEqual([r['origin'] for r in rows], ['0.00 0.00 0.00'])
        self.assertEqual(report['story_hidden_placements'], 1)
        self.assertEqual(report['not_fire_emitters'], {'f/active_blight_large': 1, 'x/terrain_lava_vent': 1})
        self.assertTrue(FL.fire_mesh('l/light_fire') and FL.fire_mesh('l/furn_de_firepit_f#2'))
        self.assertTrue(FL.fire_mesh('l/light_fire_nosmoke'))
        self.assertFalse(FL.fire_mesh('steam_lavariver') or FL.fire_mesh('f/furn_mist256'))

    def test_the_cap_keeps_the_largest_fires_and_counts_the_rest(self):
        models = {0: model_image(flame_text((0, 0, 0, 0.8, None))),               # a candle
                  1: model_image(flame_text((0, 0, 0, 8, '24.00 40.00 12.00')))}  # a hearth
        owned = [record(0, (k, 0, 0)) for k in range(FL.STATIC_FLAME_MAX)] + [record(1, (0, 500 + k, 0))
                                                                              for k in range(3)]
        rows, report = FL.frame_rows([{'owned': owned}], models)
        self.assertEqual(len(rows), FL.STATIC_FLAME_MAX)
        self.assertEqual((report['emitters'], report['written'], report['over_cap']),
                         (FL.STATIC_FLAME_MAX + 3, FL.STATIC_FLAME_MAX, 3))
        # the three hearths are kept (largest first): the engine reads the first STATIC_FLAME_MAX of a map
        self.assertEqual([r.get('aw_flame_shape') for r in rows[:3]], ['24.00 40.00 12.00'] * 3)
        self.assertEqual(report['hearth_size'], 3)
        self.assertEqual(report['entity_bytes'], FL.entity_bytes(rows))

    def test_one_emitter_reached_twice_is_written_once(self):
        models = {0: model_image(flame_text((0, 0, 0, 8, None)))}
        rows, report = FL.frame_rows([{'owned': [record(0, (5, 5, 5))]}, {'owned': [record(0, (5, 5, 5))]}], models)
        self.assertEqual((len(rows), report['placements']), (1, 2))

    def test_the_cap_is_the_engines(self):
        source = (ENGINE / 'aw_guard_torch.c').read_text()
        self.assertEqual(int(re.search(r'#define STATIC_FLAME_MAX (\d+)', source).group(1)), FL.STATIC_FLAME_MAX)
        self.assertIn('flame=!strcmp(com_token,"aw_flame")', source)
        self.assertIn('if(shape[0]>=4)', source)             # FL.HEARTH_SIZE: the hearth colour table and embers
        self.assertEqual(FL.HEARTH_SIZE, 4.0)


class WorldFlameTests(unittest.TestCase):
    """The real CHIM units (tests/test_chim_format.py fixture) with a campfire emitter on the 'small' mesh."""

    @classmethod
    def setUpClass(cls):
        from test_chim_format import fixture
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        fixture(cls.world, flames_of={0: [CAMPFIRE]})
        cls.plain = Path(cls.tmp.name) / 'plain'
        fixture(cls.plain)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_frame_with_a_campfire_gets_its_flames_where_the_town_converter_puts_them(self):
        import numpy as np
        from chim.frame_map import load
        from prepare_mesh_bsp import flame_entities
        from test_chim_format import CENTRE, MODEL_OF, ROWS
        rows, report = FL.frame_rows_of(load(self.world), (0, 0))
        small = [p for p in ROWS if MODEL_OF[p['variant']] == 0]
        self.assertEqual((report['placements'], report['emitters'], report['over_cap']), (len(small), len(small), 0))
        # the legacy converter's own rows for the same placements (tools/prepare_mesh_bsp.py), same frame
        model = {'flames': [CAMPFIRE]}
        want = []
        for p in small:
            ref = {'position': [CENTRE[0] + p['origin'][0] * 4, CENTRE[1] + p['origin'][1] * 4, p['origin'][2] * 4],
                   'rotation_radians': [0.0, 0.0, -math.radians(p['yaw'])], 'scale': 1.0}
            text = flame_entities(ref, model, CENTRE)[0]
            want.append(np.array([float(v) for v in re.search(r'"origin" "([^"]+)"', text).group(1).split()]))
        got = sorted((np.array([float(v) for v in r['origin'].split()]) for r in rows), key=lambda a: tuple(a))
        for g, w in zip(got, sorted(want, key=lambda a: tuple(a))):
            self.assertLess(float(np.abs(g - w).max()), 0.02, (g, w))
        self.assertTrue(all(r['aw_flame_shape'] == '6.00 10.00 3.00' and r['aw_flame_size'] == '8.00' for r in rows))

    def test_the_town_frame_map_carries_the_flames(self):
        from test_chim_frame_map import town
        from chim import frame_map as M
        from test_chim_format import ROWS
        with mock.patch('harvest_build.town_origin', return_value=[4096 * 0.25, 4096 * 0.25, 0.0]), \
                mock.patch('town_config.load_settings', return_value={'source_cell': [0, 0]}), \
                tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), {r['ref'] for r in ROWS})
            record = M.build(id1, 'balmora', self.world)
            rows = M.entities((id1 / 'maps/balmora-chim.chim').read_bytes())
        flames = [r for r in rows if r['classname'] == 'aw_flame']
        self.assertEqual(len(flames), 3)
        self.assertEqual(record['flames']['written'], 3)
        self.assertEqual(record['flames']['replaced_map_rows'], 0)
        # the flames' entity text is in the Hunk rest the map states
        self.assertEqual(int(rows[0][M.HUNK_KEY]) - M.hunk_rest(id1, [r for r in rows if r['classname'] != 'aw_flame']),
                         FL.entity_bytes(flames))

    def test_a_world_without_emitters_writes_no_flames(self):
        from chim.frame_map import load
        rows, report = FL.frame_rows_of(load(self.plain), (0, 0))
        self.assertEqual((rows, report['emitters'], report['entity_bytes']), ([], 0, 0))

    def test_a_region_frame_map_from_the_game_data_carries_them(self):
        from chim import frame_map as M
        flames, report = FL.frame_rows_of(M.load(self.world), (0, 0))
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            task = {'id1': str(id1), 'frame': {'id': 'rcp0_p0', 'cell': [0, 0]}, 'name': 'vf0000', 'placed': [],
                    'worldspawn': {'classname': 'worldspawn', 'message': 'Vvardenfell'}, 'start_z': 24.0,
                    'bounds': [[-512, -512, -64], [512, 512, 512]], 'stream': False, 'origin': [0, 0, 0],
                    'flame_rows': flames, 'flames': report}
            data, record = M._region_map_game_data(task)
            plain, _ = M._region_map_game_data(dict(task, flame_rows=[], flames={}))
        rows = M.entities(data)
        self.assertEqual([r['origin'] for r in rows if r['classname'] == 'aw_flame'], [r['origin'] for r in flames])
        self.assertEqual(record['flames']['written'], 3)
        self.assertNotIn('aw_flame', plain.decode('latin-1'))
        # the pass-cache key names the rows only when there are some: a frame without flames keeps its key
        key = M.region_inputs(dict(task, rows='game-data', grid=None), None)
        self.assertNotEqual(key, M.region_inputs(dict(task, rows='game-data', grid=None, flame_rows=[]), None))
        self.assertEqual(M.region_inputs(dict(task, rows='game-data', grid=None, flame_rows=[]), None),
                         M.region_inputs({k: v for k, v in dict(task, rows='game-data', grid=None).items()
                                          if k not in ('flame_rows', 'flames')}, None))


class RoomShellFlameTests(unittest.TestCase):
    def room(self, tmp, shell, extra=()):
        from chim import frame_map as M
        from chim import interior as I
        from chim import placed as P
        from chim_room_batches import SHELL_KEY
        world = {'classname': 'worldspawn', 'message': 'Census and Excise Office'}
        if shell:
            world[SHELL_KEY] = '1'
        rows = [world, {'classname': 'info_player_start', 'origin': '0 0 40', 'angle': '0'}] + list(extra)
        lumps = M.empty_world((-256, -256, -64), (256, 256, 256))
        lumps[0] = M.entity_text(rows)
        bsp = Path(tmp) / 'room.bsp'
        bsp.write_bytes(F.brush_image(lumps)[0])
        # the record's model field is the store id (7, from its model list)
        rec = P.placement(1, 4242, 7, (64.0, 0.0, 0.0), (0.0, 180.0, 0.0), 0, 0, 0,
                          ((48, -16, 0), (80, 16, 64)), 1)
        record = I.room_record(((-256, -256, -64), (256, 256, 256)), [7], [rec])
        return bsp, record

    def test_a_batch_rooms_shell_map_gets_the_hearth_from_its_record(self):
        from chim import interior as I
        hearth = model_image(flame_text((8, 0, 4, 8, '24.00 40.00 12.00')), name='l/light_de_firepit')
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(FL, 'store_models', lambda store: {7: hearth}):
            bsp, record = self.room(tmp, shell=True)
            data, report = I.room_map(bsp, 'census', record, ((-256, -256, -64), (256, 256, 256)), store=tmp)
        from chim import frame_map as M
        flames = [r for r in M.entities(data) if r['classname'] == 'aw_flame']
        self.assertEqual([r['origin'] for r in flames], ['56.00 0.00 4.00'])       # yaw 180 turns +8 x to -8
        self.assertEqual(report['flames']['written'], 1)

    def test_a_room_converted_whole_keeps_its_own_flames(self):
        from chim import interior as I
        from chim import frame_map as M
        own = {'classname': 'aw_flame', 'origin': '1 2 3', 'aw_flame_size': '8.00'}
        wall = {'classname': 'func_wall', 'model': '*1', 'aw_ref': '4242', 'origin': '64 0 0'}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(FL, 'store_models', lambda store: self.fail('a whole room reads no store')):
            bsp, record = self.room(tmp, shell=False, extra=[own, wall])
            data, report = I.room_map(bsp, 'census', record, ((-256, -256, -64), (256, 256, 256)), store=tmp)
        flames = [r for r in M.entities(data) if r['classname'] == 'aw_flame']
        self.assertEqual(flames, [own])
        self.assertNotIn('flames', report)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(__import__('shutil').which('cc'), 'a Linux C compiler is required')
class FireLightNativeTests(unittest.TestCase):
    """The engine's fire light (chim_chunks.c ChimChunks_FireLevel) gives the levels the builder's rule gives
    (placement_light.frame_levels with the fires as sources)."""

    def test_engine_levels_match_the_builders_rule(self):
        import subprocess
        from test_aga_native_source import tree_project_version
        with tempfile.TemporaryDirectory() as scratch:
            tree_project_version().generate_native(ROOT / 'VERSION', Path(scratch))   # chim_version.h
            exe = Path(scratch) / 'fire-light'
            command = ['cc', '-std=gnu89', '-O1', '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all',
                       '-include', str(ROOT / 'tests/aga_test_files.h'), '-I' + scratch,
                       '-I' + str(ENGINE), str(ROOT / 'tests/aga_chim_fire_light_test.c'),
                       str(ENGINE / 'chim/chim_chunks.c'), '-lm', '-o', str(exe)]
            built = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        got = [int(m.group(1)) for m in re.finditer(r'level \d+ (\d+)', run.stdout)]
        boxes = [(90, -30, 0, 110, -10, 16), (150, -20, 0, 170, 0, 16), (300, -20, 0, 320, 0, 16),
                 (400, -20, 0, 420, 0, 16), (-310, 30, -8, -290, 50, 8), (-100, 0, 0, -80, 20, 16)]
        fires = [{'position': (100.0 * 4, -20.5 * 4, 8.0 * 4), 'radius': 128.0 * 4, 'luma': 186.4},
                 {'position': (-300.25 * 4, 40.0 * 4, 0.0), 'radius': 64.0 * 4, 'luma': 120.0}]
        PL._ARRAYS.clear()
        want = PL.frame_levels({'centre': (0.0, 0.0)}, [{'_pid': k, '_box': (b[:3], b[3:])}
                                                         for k, b in enumerate(boxes)], fires)
        self.assertEqual(got, [want.get(k, 0) for k in range(len(boxes))])
        self.assertEqual(got[3], 0)                      # past twice the radius
        self.assertGreater(got[0], got[1])
        self.assertGreater(got[1], got[2])
        self.assertIn('fire light: rows read', run.stdout)


class FireLightRowTests(unittest.TestCase):
    def test_a_fire_placement_gets_its_light_record_on_its_first_row(self):
        models = {0: model_image(flame_text((0, 0, 4, 8, '6.00 10.00 3.00'), (2, 0, 4, 8, None)))}
        frame = {'centre': (1000.0, 2000.0)}
        light = {'position': (1000.0 + 400.0, 2000.0, 0.0), 'radius': 512.0, 'luma': 180.0, 'class': 'fire',
                 'mesh': True, 'model': 'l\\Light_Fire.NIF'}
        far = dict(light, position=(1000.0 + 4000.0, 2000.0, 0.0))
        chunks = [{'owned': [record(0, (100.0, 0.0, 0.0)), record(0, (300.0, 0.0, 0.0))]}]
        rows, report = FL.frame_rows(chunks, models, frame=frame, lights={'l/light_fire': [light, far]})
        lit = [r for r in rows if FL.FIRE_LIGHT_KEY in r]
        self.assertEqual([r[FL.FIRE_LIGHT_KEY] for r in lit], ['128.0 180.0'])     # radius in map units
        self.assertEqual((report['fire_lights'], report['fire_placements_without_light']), (1, 1))
        # without the setting: no light keys, the rows as before
        plain, report = FL.frame_rows(chunks, models)
        self.assertFalse(any(FL.FIRE_LIGHT_KEY in r for r in plain))
        self.assertNotIn('fire_lights', report)

    def test_the_setting_is_on_by_default_and_exports_the_master(self):
        import argparse
        import build
        self.assertEqual(build.parser().parse_args([]).chim_fire_light, 'on')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {}):
            (Path(tmp) / 'Morrowind.esm').write_bytes(b'TES3')
            self.assertEqual(FL.export_fire_light('on', tmp), 'on')
            self.assertEqual(os.environ[FL.FIRE_LIGHT_VARIABLE], 'on')
            self.assertEqual(Path(os.environ[PL.MASTER_VARIABLE]).name, 'Morrowind.esm')
            FL.export_fire_light('off')
            self.assertIsNone(FL.fire_light_sources())
        del argparse

    def test_dbg_campfires_is_a_catalogued_boolean_and_hides_light_and_flames(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text()
        self.assertIn('VIDEO|campfires|aw_campfires|', catalogue)
        self.assertIn('"aw_campfires"', (ENGINE / 'aw_boolean.h').read_text())
        lamps = (ENGINE / 'aw_lamps.c').read_text()
        self.assertIn('static cvar_t aw_campfires={"aw_campfires","1"};', lamps)
        self.assertIn('if(on!=r_campfires){r_campfires=on;D_FlushCaches();}', lamps)
        self.assertIn('if(lamps[i].fire && !r_campfires)continue;', lamps)
        self.assertIn('placement_add = r_lamps && r_campfires ? placement_light : 0;', (ENGINE / 'r_surf.c').read_text())
        self.assertIn('if(!r_campfires && R_SkyExterior())return;', (ENGINE / 'aw_guard_torch.c').read_text())
        world = (ENGINE / 'chim/chim_world.c').read_text()
        self.assertIn('ChimChunks_FireLights (is_room ? NULL : entities);', world)


class PlacementLightTests(unittest.TestCase):
    def test_the_weight_is_the_rooms_original_attenuation(self):
        from interior_lighting import original_weight
        frame = {'centre': (0.0, 0.0)}
        for d in (0.5, 5.0, 9.0, 12.0, 18.0, 25.0, 39.0, 41.0):
            source = {'position': (0.0, 0.0, 0.0), 'radius': 80.0, 'luma': 200.0, 'class': 'pure_light',
                      'mesh': False}
            # a placement whose drawn-box centre is d frame-local units from the source
            p = {'_pid': 1, '_box': ((d - 1, -1, -1), (d + 1, 1, 1))}
            PL._ARRAYS.clear()
            got = PL.frame_levels(frame, [p], [source]).get(1, 0)
            self.assertEqual(got, PL.level(200.0 * original_weight(d, 80.0 * PL.SCALE)), d)

    def test_levels_round_to_steps_and_small_sums_are_none(self):
        self.assertEqual([PL.level(v) for v in (0, 3.9, 4, 11.9, 12, 100, 300)], [0, 0, 8, 8, 16, 104, 255])

    def test_every_class_that_adds_light_counts_and_darkeners_do_not(self):
        from test_light_sources import cell, ligh, record as esm_record
        raw = b''.join([esm_record('TES3', b''),
                        ligh(b'light_x', b'', 128, (255, 255, 255), 0),               # no mesh
                        ligh(b'glow_shroom', b'', 64, (0, 128, 255), 0),             # glowing plant, no mesh
                        ligh(b'dark_64', b'', 64, (255, 255, 255), 4),               # darkener
                        ligh(b'light_fire_off', b'l\\fire.nif', 64, (255, 128, 0), 0x20),   # off by default
                        ligh(b'light_pitfire00', b'l\\pitfire.nif', 256, (255, 160, 64), 0x51),
                        cell(b'', 0, 0, 0, [(b'light_x', (100, 100, 50)), (b'glow_shroom', (10, 10, 0)),
                                            (b'dark_64', (0, 0, 0)), (b'light_fire_off', (5, 5, 5)),
                                            (b'light_pitfire00', (900, 900, 0))]),
                        cell(b'Some Room', 1, 0, 0, [(b'light_x', (0, 0, 0))])])
        found = PL.sources(raw)
        self.assertEqual(sorted((s['class'], s['mesh']) for s in found),
                         [('fire', True), ('glow_plant', False), ('pure_light', False)])

    def test_the_world_stores_levels_in_placed_records_as_format_0_12(self):
        from test_chim_format import CENTRE, ROWS, fixture
        from chim.frame_map import load
        # one light without a mesh right on placement 11 (frame-local -400 -400 10)
        source = {'position': (CENTRE[0] - 1600.0, CENTRE[1] - 1600.0, 60.0), 'radius': 256.0, 'luma': 180.0,
                  'class': 'pure_light', 'mesh': False}
        settings = {'grain': 256, 'sector_chunks': 2, 'placement_format': '0.8'}
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(PL, 'environment_sources', lambda: ('sources', [source])):
                receipt, _ = fixture(Path(tmp) / 'lit', settings=dict(settings))
            plain, _ = fixture(Path(tmp) / 'plain', settings=dict(settings))
            world = load(Path(tmp) / 'lit')
            levels = {r['ref']: r['flags'] >> 8 for _, _, chunks in world['frames'] for c in chunks
                      for r in c['owned']}
            index = F.read_index((Path(tmp) / 'lit/chim/world.cwi').read_bytes())
        self.assertEqual(receipt['world_format'], '0.12')
        self.assertEqual(plain['world_format'], '0.8')
        self.assertNotIn('placement_light', plain)
        self.assertGreater(levels[11], 0)
        self.assertEqual({k: v for k, v in levels.items() if k != 11}, {r['ref']: 0 for r in ROWS if r['ref'] != 11})
        self.assertEqual(receipt['placement_light']['placements_lit'], 1)
        self.assertEqual(receipt['placement_light']['sources_without_mesh'], 1)
        self.assertEqual(index[0]['placements'], len(ROWS))

    def test_a_world_without_placed_records_stores_none_and_says_so(self):
        from test_chim_format import CENTRE, fixture
        source = {'position': (CENTRE[0] - 1600.0, CENTRE[1] - 1600.0, 60.0), 'radius': 256.0, 'luma': 180.0,
                  'class': 'pure_light', 'mesh': False}
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(PL, 'environment_sources', lambda: ('sources', [source])):
                receipt, _ = fixture(Path(tmp) / 'lit')
        self.assertIn(receipt['world_format'], ('0.5', '0.7'))
        self.assertEqual(receipt['placement_light']['placements_lit'], 0)
        self.assertIn('placement format 0.8', receipt['placement_light']['note'])

    def test_off_is_the_default_without_the_stage(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PL.MODE_VARIABLE, None)
            self.assertEqual(PL.environment_sources(), ('off', None))
        with mock.patch.dict(os.environ, {PL.MODE_VARIABLE: 'sources', PL.MASTER_VARIABLE: '/nonexistent/x.esm'}):
            with self.assertRaises(ValueError):
                PL.environment_sources()
        self.assertEqual([PL.mode_for_lighting(t) for t in ('hybrid', 'lamps', 'none')], ['sources', 'off', 'off'])

    def test_records_keep_their_low_flags(self):
        from chim import placed as P
        rec = P.placement(1, 2, 3, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0, 0, 0, ((0, 0, 0), (1, 1, 1)), 20,
                          story_hidden=True)
        lit = PL.with_light(rec, 96)
        self.assertEqual(PL.record_light(lit), 96)
        self.assertEqual(P.read_placement(lit)['flags'] & 0xFF, P.read_placement(rec)['flags'] & 0xFF)
        self.assertEqual(PL.with_light(rec, 0), rec)
        with self.assertRaises(ValueError):
            PL.with_light(lit, 8)

    def test_the_setting_is_experimental_and_off_by_default(self):
        import argparse
        from chim.light_types import HYBRID_PARTS
        from build import chim_stage_options
        self.assertEqual(HYBRID_PARTS['placement_light_level'], 'experimental')
        # a default build's CHIM command line is unchanged; sources passes the option through
        self.assertNotIn('--placement-light', chim_stage_options(argparse.Namespace()))
        self.assertNotIn('--placement-light', chim_stage_options(argparse.Namespace(chim_placement_light='off')))
        options = chim_stage_options(argparse.Namespace(chim_placement_light='sources'))
        self.assertEqual(options[options.index('--placement-light') + 1], 'sources')
        stage = (ROOT / 'tools/chim_build.py').read_text()
        self.assertIn('os.environ[placement_light.MODE_VARIABLE] = a.placement_light', stage)
        self.assertIn("child_ci(a.data_files, 'Morrowind.esm', required=False)", stage)
        surf = (ENGINE / 'r_surf.c').read_text()
        self.assertIn('if (placement_light > 0 && R_SkyExterior ())', surf)


if __name__ == '__main__':
    unittest.main()
