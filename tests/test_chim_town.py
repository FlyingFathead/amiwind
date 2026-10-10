# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-LEGACY-CHAIN-33: a town on CHIM is made from the game data, not from legacy region maps.

Owner decision 2026-10-09 04:29 +0300: CHIM Balmora is the only Balmora of default builds;
the legacy Balmora chain stays behind --legacy-area balmora (or --builder legacy).
Synthetic data only (no game files).
"""
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import build  # noqa: E402
import build_font_options as options  # noqa: E402
import build_parallel  # noqa: E402
import chim_town  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


def plan(argv, native='on'):
    # CHIM-native towns are EXPERIMENTAL in v0.0.35 (--chim-native-towns, off by default): these plans opt in.
    args = build.parser().parse_args(list(argv) + ['--chim-native-towns', native])
    args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
    args.builder_options = options.resolve_builder(args)
    return build.commands(args, TOOLS, RUN)


def names(steps):
    return [name for name, _ in steps]


def value(command, flag):
    command = [str(p) for p in command]
    return command[command.index(flag) + 1]


class DefaultPlanTests(unittest.TestCase):
    def test_default_plan_has_no_legacy_balmora_stage(self):
        for argv in (['--jobs', '4'], ['--jobs', '4', '--miniwind'], ['--jobs', '4', '--builder', 'chim']):
            with self.subTest(argv=argv):
                steps = plan(argv)
                self.assertNotIn('balmora', names(steps))
                self.assertIn('chim-town-balmora', names(steps))
                self.assertLess(names(steps).index('chim'), names(steps).index('chim-town-balmora'))
                image = [str(p) for p in dict(steps)['image']]
                self.assertEqual(value(image, '--chim-town'), str(RUN / 'chim-town-balmora'))
                for flag in ('--balmora-cache', '--balmora-scenery'):
                    self.assertNotIn(flag, image)
                deps = build_parallel.stage_dependencies(steps)
                self.assertEqual(deps['chim-town-balmora'], ('chim', 'census'))
                self.assertIn('chim-town-balmora', deps['image'])

    def test_chim_town_command(self):
        command = [str(p) for p in dict(plan(['--jobs', '6']))['chim-town-balmora']]
        self.assertTrue(command[1].replace(chr(92), '/').endswith('tools/chim_town.py'))
        self.assertEqual(value(command, '--town'), 'balmora')
        self.assertEqual(value(command, '--scene'), str(RUN / 'intro-scene'))
        self.assertEqual(value(command, '--chim-world'), str(RUN / 'chim-world'))
        self.assertEqual(value(command, '--out'), str(RUN / 'chim-town-balmora'))
        self.assertEqual(value(command, '--jobs'), '6')

    def test_legacy_balmora_is_an_explicit_opt_in(self):
        for argv in (['--jobs', '4', '--legacy-area', 'balmora'], ['--jobs', '4', '--builder', 'legacy']):
            with self.subTest(argv=argv):
                steps = plan(argv)
                self.assertIn('balmora', names(steps))
                self.assertNotIn('chim-town-balmora', names(steps))
                image = [str(p) for p in dict(steps)['image']]
                self.assertEqual(value(image, '--balmora-cache'), str(RUN / 'balmora-work'))
                self.assertNotIn('--chim-town', image)
                self.assertEqual(build_parallel.stage_dependencies(steps)['balmora-interiors'], ('balmora',))
        help_text = next(a.help for a in build.parser()._actions if a.dest == 'legacy_areas')
        self.assertTrue(help_text.startswith('DEBUGGING ONLY'))

    def test_seyda_keeps_its_recorded_legacy_stage(self):
        args = build.parser().parse_args(['--builder', 'chim', '--chim-area', 'seyda', '--chim-area', 'balmora',
                                          '--chim-native-towns', 'on'])
        self.assertEqual(build.chim_native_towns(args), ['balmora'])
        args = build.parser().parse_args(['--builder', 'chim', '--chim-area', 'seyda', '--chim-area', 'balmora'])
        self.assertEqual(build.chim_native_towns(args), [])          # off by default: the legacy chains

    def test_default_build_keeps_the_legacy_balmora_chain(self):
        steps = plan(['--jobs', '4'], native='off')
        self.assertIn('balmora', names(steps))
        self.assertNotIn('chim-town-balmora', names(steps))
        args = build.parser().parse_args(['--builder', 'legacy'])
        self.assertEqual(build.chim_native_towns(args), [])


TIMINGS = '"aw_hand_idle" "2.5"\n"aw_hand_draw" "0.5"\n"aw_eye_height" "16.5"'  # seyda.bsp order


class EntityTests(unittest.TestCase):
    def test_worldspawn_and_start_as_the_compiled_region_maps_hold_them(self):
        from player_hull import PROFILE
        settings = {'town': {'message': 'Balmora'}}
        with patch('town_config.town_field', side_effect=lambda s, k: s['town'][k]):
            row = chim_town.worldspawn(settings, TIMINGS)
        self.assertEqual(list(row), ['aw_eye_height', 'aw_hand_draw', 'aw_hand_idle', 'classname', 'aw_hull', 'message'])
        self.assertEqual((row['aw_hull'], row['message'], row['aw_eye_height']), (PROFILE, 'Balmora', '16.5'))
        start = chim_town.player_start([-209.68310546875, -1486.1015625, 288.125])
        self.assertEqual(start, {'angle': '90', 'classname': 'info_player_start',
                                 'origin': '-209.68310546875 -1486.1015625 288.125'})

    def test_actor_identity_fields_come_last_as_the_annotation_leaves_them(self):
        text = ('{\n"aw_source_id" "x"\n"aw_ground_mode" "0"\n"classname" "aw_npc"\n"aw_ref" "5"\n'
                '"origin" "1.00000 2.00000 3.00000"\n}')
        row, = chim_town.actor_rows([text])
        self.assertEqual(list(row), ['classname', 'aw_ref', 'origin', 'aw_source_id', 'aw_ground_mode'])
        # the frame map's order: by class, then by the reference as text (as frame_entities sorts them)
        texts = ['{' + chr(10) + '"classname" "aw_npc"' + chr(10) + '"aw_ref" "%s"' % n + chr(10) + '}'
                 for n in ('41609', '261829', '67596')]
        self.assertEqual([r['aw_ref'] for r in chim_town.actor_rows(texts)], ['261829', '41609', '67596'])

    def test_grounding_writes_the_legacy_bake_fields_in_its_order(self):
        # The same fitted result through the legacy bake (a region map) and the CHIM frame path.
        import actor_grounding
        from player_hull import pack_lumps, lumps
        e = {'classname': 'aw_npc', 'aw_ref': '7', 'model': 'progs/a.mdl', 'origin': '10.00000 20.00000 30.00000',
             'angles': '0 90.00000 0', 'aw_source_id': 'someone', 'aw_ground_mode': '0'}
        result = {'status': 'supported', 'placed_origin': [10.0, 20.0, 17.25], 'mesh_contact': 'unchanged'}

        class Fitter:
            def fit(self, name, entity, authored, angles):
                self.seen = (authored, angles)
                return dict(result)
        fitter = Fitter()
        rows = [dict(e)]
        with patch.object(chim_town, 'frame_fitter', return_value=fitter):
            report = chim_town.ground_actors(rows, Path('/id1'), None)
        self.assertEqual(fitter.seen, ([10.0, 20.0, 30.0], (0.0, 90.0, 0.0)))
        self.assertEqual(report, [result])
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            text = '{\n' + ''.join('"%s" "%s"\n' % kv for kv in e.items()) + '}\n\0'
            (maps / 'bm000.bsp').write_bytes(pack_lumps([text.encode('cp1252')] + [b''] * 14))
            key = ('bm000', '7', (10.0, 20.0, 30.0), (0.0, 90.0, 0.0), 'progs/a.mdl')
            with patch.object(actor_grounding, '_ground_key',
                              side_effect=lambda m, stem, entity: ('bm000', key, [10.0, 20.0, 30.0], key[3])):
                actor_grounding._bake_map((str(maps / 'bm000.bsp'), {key: result}))
            legacy = chim_town.parse_entity(lumps((maps / 'bm000.bsp').read_bytes())[0].decode('cp1252'))
        self.assertEqual(list(rows[0].items()), list(legacy.items()))

    def test_native_towns_come_from_the_builder_environment(self):
        with patch.dict(os.environ, {chim_town.NATIVE_ENV: 'balmora'}):
            self.assertEqual(chim_town.native_towns(), ['balmora'])
        with patch.dict(os.environ, {chim_town.NATIVE_ENV: ''}):
            self.assertEqual(chim_town.native_towns(), [])


class ImageTests(unittest.TestCase):
    def town_dir(self, root):
        town = Path(root) / 'chim-town-balmora'
        (town / 'id1/progs').mkdir(parents=True)
        (town / 'id1/progs/a_1.mdl').write_bytes(b'MDL')
        (town / 'id1/balmora-regions.txt').write_text('AWBR1 1 96 540 0 0 64 90 0 0 0 0\n'
                                                      'bm000 -3072 -3072 -1536 -2304 -3072 -3072 -640 -1408\n')
        (town / 'door-bank.txt').write_text('AWD3\n')
        record = {'format': chim_town.FORMAT, 'town': 'balmora', 'map': 'balmora', 'door_file': 'doors-balmora.txt',
                  'rows': [{'classname': 'worldspawn', 'message': 'Balmora'},
                           {'classname': 'info_player_start', 'origin': '0 0 0'},
                           {'classname': 'aw_npc', 'aw_ref': '42', 'origin': '1 2 3'}]}
        (town / 'entities.json').write_text(json.dumps(record))
        return town

    def test_install_copies_files_and_keeps_an_interiors_door_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            town = self.town_dir(tmp)
            id1 = Path(tmp) / 'id1'
            id1.mkdir()
            record = chim_town.install(town, id1)
            self.assertEqual((id1 / 'progs/a_1.mdl').read_bytes(), b'MDL')
            self.assertEqual((id1 / 'doors-balmora.txt').read_text(), 'AWD3\n')
            self.assertEqual(record['door_bank'], 'chim-town (no converted interiors)')
            (id1 / 'doors-balmora.txt').write_text('AWD3\nfrom interiors\n')
            self.assertEqual(chim_town.install(town, id1)['door_bank'], 'converted interiors stage')
            self.assertEqual((id1 / 'doors-balmora.txt').read_text(), 'AWD3\nfrom interiors\n')

    def test_frame_rows_get_the_shared_sky_keys_and_legacy_maps_are_not_required(self):
        import build_aga
        from exterior_sky_build import SHARED_SKY_PATH
        with tempfile.TemporaryDirectory() as tmp:
            town = self.town_dir(tmp)
            from types import SimpleNamespace
            args = SimpleNamespace(chim_town=[town])
            self.assertEqual(build_aga.chim_native_towns(args), ['balmora'])
            rows = build_aga.chim_town_rows(args)['balmora']
            self.assertEqual((rows[0]['_aw_sky_mode'], rows[0]['_aw_sky_asset']), ('exterior', SHARED_SKY_PATH))
            id1 = Path(tmp) / 'id1'
            id1.mkdir()
            chim_town.install(town, id1)
            self.assertEqual(build_aga.never_built_maps(id1, ['balmora']), ['maps/balmora.bsp', 'maps/bm000.bsp'])
            self.assertEqual(build_aga.never_built_maps(id1, []), [])

    def test_harvest_plans_a_chim_towns_regions_without_maps(self):
        import harvest_build
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'balmora-regions.txt').write_text('AWBR1 1 96 540 0 0 64 90 0 0 64 90\n'
                                                     'bm000 -3072 -3072 -1536 -2304 -3072 -3072 -640 -1408\n')
            self.assertEqual(harvest_build.plan_rows(id1), [])
            rows = harvest_build.plan_rows(id1, native=['balmora'])
            self.assertEqual([(r['name'], r.get('chim')) for r in rows], [('bm000', True)])


if __name__ == '__main__':
    unittest.main()
