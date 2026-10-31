# SPDX-License-Identifier: GPL-3.0-only
"""Start straight in the game: --direct-to-game-map and --quick-character (tools/direct_start.py).

Every form parses (an area, "interior:<cell id>" with commas and spaces,
cell:X,Y, pos:X,Y,Z[@HEADING]) and bad input is refused with the reason; the
start point is checked against what the build holds (the Vivec Arena Pit is
refused while the Arena interiors are not converted, IMPORT-TOWN-NO-INTERIORS-32);
the image resolves it on the final payload (a door arrival, the engine's
arrival search moving a spot out of a wall, refusing water); the quick-start
lines are written only with the option; release candidates and finals refuse
it. The engine side (the start and character lines, the quick start at the
spot, saving once walking) is checked in tests/aga_miniwind_test.c and
tests/aga_scene_test.c.
"""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import direct_start as ds  # noqa: E402
import miniwind  # noqa: E402

DEV = '0.0.33-dev1'
TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')
FULL = ds.build_scope(['seyda', 'balmora', 'vivec_arena'], True)
MINI = ds.build_scope(['balmora'], False, miniwind_scope='full')
MINI_EXTERIOR = ds.build_scope(['balmora'], False, miniwind_scope='exterior')
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402


class Forms(unittest.TestCase):
    def test_area_names_and_aliases(self):
        for text, town, title in (('balmora', 'balmora', 'Balmora'), ('seyda_neen', 'seyda', 'Seyda Neen'),
                                  ('Balmora', 'balmora', 'Balmora'), ('vivec_arena', 'vivec_arena', None)):
            with self.subTest(text=text):
                start = ds.parse(text)
                self.assertEqual((start.kind, start.town), ('area', town))
                if title:
                    self.assertEqual(start.describe(), title)

    def test_interior_cell_ids_with_commas_and_spaces(self):
        start = ds.parse('interior:Vivec, Arena Pit')
        self.assertEqual((start.kind, start.cell), ('interior', 'Vivec, Arena Pit'))
        self.assertEqual(start.describe(), 'Vivec, Arena Pit')
        self.assertEqual(ds.parse('interior:  Balmora, Council Club ').cell, 'Balmora, Council Club')

    def test_cell_and_position(self):
        start = ds.parse('cell:-3,-2')
        self.assertEqual((start.x, start.y, start.gx, start.gy), (-3, -2, -20480.0, -12288.0))
        start = ds.parse('pos:-20480.5,-12288,1200@90')
        self.assertEqual((start.gx, start.gy, start.z, start.heading), (-20480.5, -12288.0, 1200.0, 90.0))
        self.assertEqual(ds.parse('pos:1,2,3').heading, 0.0)
        self.assertEqual(start.describe(), 'position -20480.5 -12288 1200')

    def test_bad_input_is_refused_with_the_reason(self):
        for text, reason in (('', 'needs a start point'), ('atlantis', 'unknown area'), ('interior:', 'needs the cell ID'),
                             ('cell:3', 'two whole grid numbers'), ('cell:a,b', 'two whole grid numbers'),
                             ('pos:1,2', 'three numbers'), ('pos:1,2,3@400', 'HEADING'),
                             ('pos:9999999,0,0', 'outside the world'), ('room:Vivec', 'unknown form'),
                             ('interior:Balé', 'printable ASCII')):
            with self.subTest(text=text), self.assertRaises(ValueError) as error:
                ds.parse(text)
            self.assertIn(reason, str(error.exception))


class Scope(unittest.TestCase):
    def test_areas_and_interiors_the_build_holds(self):
        self.assertEqual(ds.check(ds.parse('balmora'), MINI).town, 'balmora')
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('seyda_neen'), MINI)
        self.assertIn('not in this build', str(error.exception))
        start = ds.check(ds.parse('interior:Balmora, Council Club'), MINI)
        self.assertEqual((start.map, start.town), ('bmcouncil', 'balmora'))
        self.assertEqual(ds.check(ds.parse('interior:Seyda Neen, Arrille\'s Tradehouse'), FULL).map, 'tradehouse')
        # MiniWind holds the prison ship as a direct start only (the opening-ship preset; the intro
        # stage builds it anyway), in both scopes; never the Census office; the exterior scope no room.
        self.assertEqual(ds.check(ds.parse('interior:Imperial Prison Ship'), MINI).map, 'prison')
        self.assertEqual(ds.check(ds.parse('interior:Imperial Prison Ship'), MINI_EXTERIOR).map, 'prison')
        with self.assertRaises(ValueError):
            ds.check(ds.parse('interior:Seyda Neen, Census and Excise Office'), MINI)
        with self.assertRaises(ValueError):
            ds.check(ds.parse('interior:Balmora, Council Club'), MINI_EXTERIOR)
        # A quick test build without interiors keeps only the opening rooms.
        no_rooms = ds.build_scope(['seyda', 'balmora'], True, interiors_excluded=True)
        self.assertEqual(ds.check(ds.parse('interior:Imperial Prison Ship'), no_rooms).map, 'prison')
        with self.assertRaises(ValueError):
            ds.check(ds.parse('interior:Balmora, Council Club'), no_rooms)

    def test_the_vivec_arena_pit_is_in_a_build_that_holds_the_arena(self):
        # BUILD-MINIWIND-ARENA-PIT-REFUSED-36: the Pit is converted by the Arena's town stage (vai000, eecb4eb); a
        # build without the Arena refuses it naming the town to build, never "not converted"
        self.assertEqual(ds.check(ds.parse('interior:Vivec, Arena Pit'), FULL).map, 'vai000')  # a build with the Arena
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('interior:Vivec, Arena Pit'), MINI)
        self.assertIn('converted with the town vivec_arena (map vai000)', str(error.exception))
        self.assertNotIn('IMPORT-TOWN-NO-INTERIORS-32', str(error.exception))
        arena = ds.build_scope(['vivec_arena'], False, False, 'full')
        start = ds.check(ds.parse('interior:Vivec, Arena Pit'), arena)
        self.assertEqual((start.map, start.town), ('vai000', 'vivec_arena'))
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('interior:Vivec, Arena Pit'), ds.build_scope(['vivec_arena'], False, False, 'exterior'))
        self.assertIn('vivec_arena', str(error.exception))
        # a room the town table excludes is refused with its own reason
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('interior:Vivec, Guild of Mages'), ds.build_scope(['vivec_foreign'], False, False, 'full'))
        self.assertIn('does not convert it yet: model slots', str(error.exception))

    def test_cells_and_positions_inside_the_held_area(self):
        self.assertEqual(ds.check(ds.parse('cell:-3,-2'), MINI).cell_xy, [-3, -2])
        self.assertEqual(ds.check(ds.parse('pos:-20480,-12288,1200'), MINI).cell_xy, [-3, -2])
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('cell:2,-9'), MINI)
        self.assertIn('outside the area this build holds', str(error.exception))
        self.assertEqual(ds.check(ds.parse('cell:2,-9'), FULL).cell_xy, [2, -9])  # the open world

    def test_a_start_outside_the_map_the_town_makes_is_refused_before_any_stage(self):
        # MINIWIND-EXTERIOR-DIRECT-START-CELL-57: cell:0,-7 is in Seyda Neen's source grid (cells -5..1, -12..-6) but
        # not in the map it makes (global y up to -57344); the image step stopped 11-14 minutes in on it
        scope = ds.build_scope(['seyda'], False, False, 'exterior')
        with self.assertRaises(ValueError) as error:
            ds.check(ds.parse('cell:0,-7'), scope)
        self.assertIn('outside the map seyda makes', str(error.exception))
        self.assertIn('cell:0,-8', str(error.exception))
        self.assertEqual(ds.check(ds.parse('cell:0,-8'), scope).cell_xy, [0, -8])


class Character(unittest.TestCase):
    def masters(self, root):
        def record(tag, *subs):
            body = b''.join(t.encode() + struct.pack('<I', len(d)) + d for t, d in subs)
            return tag.encode() + struct.pack('<III', len(body), 0, 0) + body
        races = b''.join(record('RACE', ('NAME', name.encode() + b'\0'), ('RADT', bytes(136) + struct.pack('<i', flag)))
                         for name, flag in (('Dark Elf', 1), ('Nord', 1), ('Dremora', 0)))
        classes = b''.join(record('CLAS', ('NAME', name.encode() + b'\0'),
                                  ('CLDT', bytes(52) + struct.pack('<ii', flag, 0)))
                           for name, flag in (('Battlemage', 1), ('Barbarian', 1), ('Guard', 0)))
        (Path(root) / 'Morrowind.esm').write_bytes(races + classes)
        return Path(root)

    def test_default_profile_and_override(self):
        self.assertEqual(ds.parse_character(None), ds.DEFAULT_CHARACTER)
        self.assertEqual(ds.character_line(ds.DEFAULT_CHARACTER), 'Nord|Barbarian|Charioteer|m|Hors')
        with tempfile.TemporaryDirectory() as tmp:
            data = self.masters(tmp)
            character = ds.parse_character('dark_elf,battlemage,Ilmeni', data)
            self.assertEqual((character['race'], character['class'], character['name']), ('Dark Elf', 'Battlemage', 'Ilmeni'))
            self.assertEqual(ds.parse_character('Nord,Barbarian', data)['name'], 'Hors')
            for text, reason in (('Dremora,Battlemage', 'not a playable race'), ('Nord,Guard', 'not a playable class'),
                                 ('Nord', 'RACE,CLASS'), ('Nord,Barbarian,A|B', 'without "|"')):
                with self.subTest(text=text), self.assertRaises(ValueError) as error:
                    ds.parse_character(text, data)
                self.assertIn(reason, str(error.exception))


class Resolve(unittest.TestCase):
    def payload(self, root):
        id1 = Path(root) / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'maps/bmcouncil.bsp').write_bytes(b'x')
        (id1 / 'doors-balmora.txt').write_text(
            'AWD3\nbalmora bmcouncil 42 -5 35 25 5 45 35 12.5 -34 77 180\tCouncil Club\n', encoding='cp1252')
        (id1 / 'balmora-regions.txt').write_text(
            'AWBR1 2 96 540 0 0 77 90 0 0 77 90\nbm000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\n')
        return id1

    class Floor:
        """A flat floor at z 40 with a wall west of x = -10 and water east of x = 500 (map units)."""
        def ground(self, top, depth):
            return 40.0 if top[2] >= 40 and top[2] - depth <= 40 else None

        def solid(self, p):
            return p[0] < -10

        def dry(self, p):
            return p[0] < 500

    def test_interior_door_arrival(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.payload(tmp)
            start = ds.check(ds.parse('interior:Balmora, Council Club'), MINI)
            line, record = ds.resolve(start, id1, [])
            self.assertEqual(line, 'map bmcouncil 12.5 -34 77 180')
            self.assertEqual(record['from'], 'door arrival')
            (id1 / 'doors-balmora.txt').write_text('AWD3\n', encoding='cp1252')
            with self.assertRaises(ValueError) as error:
                ds.resolve(start, id1, [])
            self.assertIn('no door leads into', str(error.exception))

    def test_interior_without_a_door_uses_the_map_player_start(self):
        # The prison ship: no door leads into it; its info_player_start is the arrival.
        import struct
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.payload(tmp)
            entities = b'{\n"classname" "worldspawn"\n}\n{\n"angle" "90"\n"classname" "info_player_start"\n' \
                       b'"origin" "0 -35 -4"\n}\n\0'
            header = struct.pack('<i', 29) + struct.pack('<ii', 124, len(entities)) + bytes(124 - 12)
            (id1 / 'maps').mkdir(parents=True, exist_ok=True)
            (id1 / 'maps/prison.bsp').write_bytes(header + entities)
            start = ds.check(ds.parse('interior:Imperial Prison Ship'), MINI)
            line, record = ds.resolve(start, id1, [])
            self.assertEqual(line, 'map prison 0 -35 -4 90')
            self.assertEqual(record['from'], "the map's info_player_start")

    def test_positions_move_to_a_standing_spot_or_are_refused(self):
        towns = [{'name': 'balmora', 'regions': 'balmora-regions.txt', 'origin': [-5120.0, -3072.0, 0.0]}]
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.payload(tmp)
            floor = self.Floor()
            # In the wall (map x -12): moved 16 units east onto the floor.
            start = ds.parse('pos:%s,%s,160@0' % ((-12 - 5120) * 4, (0 - 3072) * 4))
            line, record = ds.resolve(start, id1, towns, collision_for=lambda name: floor)
            self.assertTrue(line.startswith('map balmora 4 0 40.25 90'), line)
            self.assertTrue(record['moved_to_standing_spot'])
            self.assertEqual(record['region'], 'bm000')
            # Standing already: kept, heading 90 (east) is engine yaw 0.
            start = ds.parse('pos:%s,%s,160@90' % ((100 - 5120) * 4, (0 - 3072) * 4))
            line, record = ds.resolve(start, id1, towns, collision_for=lambda name: floor)
            self.assertEqual(line, 'map balmora 100 0 40.25 0')
            self.assertFalse(record['moved_to_standing_spot'])
            # In water: refused with the reason.
            start = ds.parse('pos:%s,%s,160' % ((800 - 5120) * 4, (0 - 3072) * 4))
            with self.assertRaises(ValueError) as error:
                ds.resolve(start, id1, towns, collision_for=lambda name: floor)
            self.assertIn('no standing spot', str(error.exception))
            # Outside every map.
            start = ds.parse('pos:900000,900000,0')
            with self.assertRaises(ValueError) as error:
                ds.resolve(start, id1, towns, collision_for=lambda name: floor)
            self.assertIn('no map of this build holds', str(error.exception))

    def test_cell_centre_dropped_to_the_ground(self):
        towns = [{'name': 'balmora', 'regions': 'balmora-regions.txt', 'origin': [-5120.0, -3072.0, 0.0]}]
        with tempfile.TemporaryDirectory() as tmp:
            id1 = self.payload(tmp)
            line, record = ds.resolve(ds.parse('cell:-3,-2'), id1, towns, collision_for=lambda name: self.Floor())
            self.assertEqual(line, 'map balmora 0 0 40.25 90')

    def test_town_origins(self):
        from town_config import runtime_towns
        rows = {row['name']: row for row in ds.town_rows(runtime_towns())}
        self.assertEqual(rows['balmora']['origin'][:2], [-5120.0, -3072.0])
        self.assertEqual(rows['seyda']['origin'][:2], [-2816.0, -17920.0])


class DataFile(unittest.TestCase):
    def test_start_and_character_lines(self):
        data = miniwind.data_file('FEATURES ONLY: Balmora exterior (CHIM)', start='map bmcouncil 12.5 -34 77 180',
                                  character='Nord|Barbarian|Charioteer|m|Hors').decode('ascii')
        self.assertTrue(data.endswith('start map bmcouncil 12.5 -34 77 180\ncharacter Nord|Barbarian|Charioteer|m|Hors\n'))
        plain = miniwind.data_file('FEATURES ONLY: Balmora exterior (CHIM)').decode('ascii')
        self.assertNotIn('start', plain)
        quick = miniwind.data_file(ds.notice_features(ds.parse('balmora'), ['video']), town='balmora',
                                   start='town balmora', title=ds.QUICK_TITLE, features_prefix=None).decode('ascii')
        self.assertIn('title ATTENTION: THIS IS A QUICK TEST BUILD\nfeatures DIRECT TO: Balmora; excluded: video\n', quick)
        with self.assertRaises(ValueError):
            miniwind.data_file('FEATURES ONLY: x', start='x' * 96)

    def test_startup_screen_of_a_direct_start(self):
        lines = ds.logo_lines('0.0.33-dev1', '0.1.0', 'Vivec, Arena Pit')
        self.assertEqual(lines, ['Quick Test Build', 'AmiWind v0.0.33-dev1 / CHIM v0.1.0', 'Scene: Vivec, Arena Pit'])
        self.assertEqual(ds.logo_lines('0.0.33-dev1', None, 'Balmora')[1], 'AmiWind v0.0.33-dev1')

    def test_labels(self):
        self.assertEqual(ds.summary(ds.parse('interior:Vivec, Arena Pit')), 'quick test build: direct to Vivec, Arena Pit')
        self.assertEqual(ds.area_label(ds.parse('interior:Vivec, Arena Pit')), 'direct-vivec-arena-pit')
        self.assertEqual(ds.closure_cells(ds.parse('interior:Balmora, Council Club')), ['interior:Balmora, Council Club'])
        self.assertEqual(ds.closure_cells(ds.parse('pos:-20480,-12288,0')), ['cell:-3,-2'])


class ImageStep(unittest.TestCase):
    def test_the_quick_start_file_is_written_only_with_the_option(self):
        import build_aga
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            boot, out = Path(tmp) / 'boot', Path(tmp) / 'out'
            id1 = boot / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            out.mkdir()
            (id1 / 'maps/bmcouncil.bsp').write_bytes(b'x')
            (id1 / 'doors-balmora.txt').write_text(
                'AWD3\nbalmora bmcouncil 42 -5 35 25 5 45 35 12.5 -34 77 180\tCouncil Club\n', encoding='cp1252')
            # Without the options: nothing is written, the normal intro stays.
            args = SimpleNamespace(direct_start=None, quick_character=None, data_files=None)
            build_aga.direct_start_option(args)
            self.assertIsNone(build_aga.stage_direct_start(args, boot, out, None, []))
            self.assertFalse((id1 / miniwind.DATA_FILE).exists())
            # With a direct start outside MiniWind: the quick-test notice file with the start line.
            args = SimpleNamespace(direct_start='interior:Balmora, Council Club', quick_character=None, data_files=None)
            build_aga.direct_start_option(args)
            with contextlib.redirect_stdout(io.StringIO()):
                record = build_aga.stage_direct_start(args, boot, out, None, ['video'])
            text = (id1 / miniwind.DATA_FILE).read_text(encoding='ascii')
            self.assertEqual(text, 'AWMW1\ntown balmora\ntitle ATTENTION: THIS IS A QUICK TEST BUILD\n'
                                   'features DIRECT TO: Balmora, Council Club; excluded: video\n'
                                   'start map bmcouncil 12.5 -34 77 180\n'
                                   'header QUICK TEST BUILD: Balmora, Council Club\n')
            self.assertEqual(record['engine_line'], 'map bmcouncil 12.5 -34 77 180')
            self.assertEqual(record['character']['name'], 'Hors')
            self.assertTrue((out / 'direct-start.json').is_file())
            # In a MiniWind build the line joins the MiniWind notice.
            mini = {'features': 'FEATURES ONLY: Balmora exterior (CHIM)', 'scope': 'full', 'description': None}
            with contextlib.redirect_stdout(io.StringIO()):
                build_aga.stage_direct_start(args, boot, out, mini, [])
            text = (id1 / miniwind.DATA_FILE).read_text(encoding='ascii')
            self.assertTrue(text.startswith('AWMW1\ntown balmora\ntitle ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD\n'))
            self.assertTrue(text.endswith('start map bmcouncil 12.5 -34 77 180\n'
                                          'header MINIWIND TEST UNIT: Balmora\n'))
            # The title screen header carries the description when there is one.
            mini['description'] = 'Balmora on CHIM, incremental streaming, photo mode'
            with contextlib.redirect_stdout(io.StringIO()):
                build_aga.stage_direct_start(args, boot, out, mini, [])
            text = (id1 / miniwind.DATA_FILE).read_text(encoding='ascii')
            self.assertTrue(text.endswith('header MINIWIND TEST UNIT: Balmora on CHIM, incremental streaming, '
                                          'photo mode\n'))
            build_aga.direct_start_option(SimpleNamespace(direct_start=None))


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class Builder(unittest.TestCase):
    def configure(self, argv, version=DEV):
        args = build.parser().parse_args(argv)
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        with patch.object(build, 'VERSION', version), contextlib.redirect_stdout(io.StringIO()):
            if args.miniwind:
                build.configure_miniwind(args)
            import build_exclusions
            build_exclusions.resolve(args, version, area_build=bool(args.miniwind))
            build.configure_direct_start(args)
        return args

    def test_the_image_gets_the_start_only_with_the_option(self):
        import build_font_options as options
        for argv, expected in ((['--direct-to-game-map', 'interior:Balmora, Council Club'],
                                'interior:Balmora, Council Club'), ([], None)):
            args = self.configure(argv)
            args.builder_options = options.resolve_builder(args)
            with patch('build_jobs.auto_jobs', return_value=4):
                image = dict(build.commands(args, TOOLS, RUN))['image']
            if expected:
                self.assertEqual(image[image.index('--direct-start') + 1], expected)
            else:
                self.assertNotIn('--direct-start', image)
                self.assertNotIn('--quick-character', image)

    def test_release_candidates_and_finals_refuse_it(self):
        for version in ('0.0.33-rc1', '0.0.33'):
            for argv in (['--direct-to-game-map', 'balmora'], ['--direct-to-game-map', 'balmora',
                                                              '--quick-character', 'Nord,Barbarian']):
                with self.subTest(version=version, argv=argv), self.assertRaises(ValueError) as error:
                    self.configure(argv, version)
                self.assertIn('release candidate or final', str(error.exception))
        import build_aga
        from types import SimpleNamespace
        self.assertIn('--direct-start', build_aga.image_waivers(SimpleNamespace(direct_start='balmora')))

    def test_bad_area_and_missing_interior_stop_before_any_work(self):
        for argv, reason in ((['--direct-to-game-map', 'atlantis'], 'unknown area'),
                             (['--miniwind', '--miniwind-town', 'balmora', '--direct-to-game-map',
                               'interior:Vivec, Arena Pit'], 'converted with the town vivec_arena'),
                             (['--quick-character', 'Nord,Barbarian'], 'needs --direct-to-game-map')):
            with self.subTest(argv=argv), patch.object(build, 'VERSION', DEV), \
                    patch.object(build, 'prerequisites') as setup, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err, \
                    self.assertRaises(SystemExit):
                build.main([*argv, '--check', '--tools-dir', '/nonexistent-tools'])
            setup.assert_not_called()
            self.assertIn(reason, err.getvalue())

    def test_miniwind_scene_line_defaults_to_the_start(self):
        args = self.configure(['--miniwind', '--direct-to-game-map', 'interior:Balmora, Council Club'])
        self.assertEqual(args.miniwind_description, 'Balmora, Council Club')
        args = self.configure(['--miniwind', '--direct-to-game-map', 'balmora', '--miniwind-description', 'My test'])
        self.assertEqual(args.miniwind_description, 'My test')
        # The area build's reference closure covers the start.
        args = self.configure(['--miniwind', '--direct-to-game-map', 'interior:Balmora, Council Club',
                               '--exclude-unreferenced', 'voice'])
        self.assertEqual(args.closure_cells, ['interior:Balmora, Council Club'])
        self.assertEqual(args.unreferenced_groups, ['voice'])

    def test_miniwind_start_in_its_own_town(self):
        # BUILD-MINIWIND-DIRECT-START-TOWN-36: a MiniWind of another town starts in that town, and only there
        args = self.configure(['--miniwind', '--miniwind-town', 'vivec_arena', '--direct-to-game-map', 'vivec_arena'])
        self.assertEqual(args.direct_start.town, 'vivec_arena')
        with self.assertRaises(ValueError) as error:
            self.configure(['--miniwind', '--miniwind-town', 'vivec_arena', '--direct-to-game-map', 'balmora'])
        self.assertIn('not in this build. This build holds areas: vivec_arena', str(error.exception))


class StartFollowsContent(unittest.TestCase):
    """Maintainer order 2026-10-11 ("if you're only going to build a certain area, make sure the player is then there";
    BUILD-MINIWIND-DIRECT-START-TOWN-36): a partial-area build starts inside what it holds, derived when no start is
    given, refused before any stage when the start lies outside, checked again on the final image."""

    configure = Builder.configure

    def preset(self, name, *more):
        import io as _io
        import build_recipe
        argv = ['--miniwind-preset', name, *more]
        args = build.parser().parse_args(argv)
        build_recipe.configure(build.parser, args, argv, DEV, out=_io.StringIO())
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        with patch.object(build, 'VERSION', DEV), contextlib.redirect_stdout(io.StringIO()):
            build.configure_miniwind(args)
            import build_exclusions
            build_exclusions.resolve(args, DEV, area_build=True)
            build.configure_direct_start(args)
        return args

    def test_every_preset_starts_inside_its_own_content(self):
        import miniwind_presets
        for row in miniwind_presets.presets():
            with self.subTest(preset=row['name']):
                args = self.preset(row['name'])
                town = args.miniwind_town
                record = args.start_record
                self.assertEqual(record['town'] if record['kind'] != 'interior' else town, town)
                if args.direct_start is not None:
                    scope = ds.build_scope([town], False, False, args.miniwind_scope)
                    ds.check(ds.parse(row['start']), scope)  # inside the built content
                    self.assertIn('explicit', record['source'])
                else:
                    self.assertEqual((record['kind'], record['start']), ('area', town))
                    self.assertIn('derived', record['source'])

    def test_the_arena_pit_preset_starts_inside_the_pit(self):
        # BUILD-MINIWIND-ARENA-PIT-REFUSED-36: the preset builds Vivec (its start picks the town: the whole city takes
        # the Arena's rooms, project decision 2026-10-11), the resolver finds the Pit (vai000, listed by
        # config/vivec_arena.json) and the plan makes it in chim-rooms-vivec_city
        args = self.preset('vivec-arena-pit')
        # the interior scope since v0.0.42 (MINIWIND-NO-INTERIOR-SCOPE-42): the Pit only of the city's rooms
        self.assertEqual((args.miniwind_town, args.miniwind_scope), ('vivec_city', 'interior'))
        self.assertEqual((args.direct_start.kind, args.direct_start.map, args.direct_start.town),
                         ('interior', 'vai000', 'vivec_city'))
        self.assertIn('explicit', args.start_record['source'])
        import build_font_options as options
        args.builder_options = options.resolve_builder(args)
        with patch('build_jobs.auto_jobs', return_value=4), contextlib.redirect_stdout(io.StringIO()):
            steps = build.miniwind_commands(args, build.commands(args, TOOLS, RUN))
        names = [name for name, _ in steps]
        self.assertIn('chim-rooms-vivec_city', names)
        self.assertLess(names.index('chim-town-vivec_city'), names.index('chim-rooms-vivec_city'))
        image = dict(steps)['image']
        self.assertEqual(image[image.index('--chim-rooms') + 1], str(RUN / 'chim-rooms-vivec_city'))
        rooms = [str(part) for part in dict(steps)['chim-rooms-vivec_city']]
        self.assertEqual(rooms[rooms.index('--only-cell') + 1], 'Vivec, Arena Pit')
        self.assertIn('Vivec interiors', args.miniwind_record['features'] if 'features' in args.miniwind_record
                      else image[image.index('--miniwind-features') + 1])

    def test_a_room_with_no_stage_is_refused_before_any_stage(self):
        scope = ds.build_scope(['vivec_arena'], False, False, 'full')
        start = ds.check(ds.parse('interior:Vivec, Arena Pit'), scope)
        self.assertIs(ds.require_built_interior(start, []), start)
        with self.assertRaisesRegex(ValueError, ds.TOWN_INTERIORS_STAGE_BUG):
            ds.require_built_interior(start, ['vivec_arena'])
        balmora = ds.check(ds.parse('interior:Balmora, Council Club'), ds.build_scope(['balmora'], False, False, 'full'))
        self.assertIs(ds.require_built_interior(balmora, ['balmora']), balmora)  # Balmora's rooms: own stage

    def test_the_exterior_scope_has_no_room_stage(self):
        args = self.configure(['--miniwind', '--miniwind-town', 'vivec_arena', '--miniwind-scope', 'exterior'])
        import build_font_options as options
        args.builder_options = options.resolve_builder(args)
        with patch('build_jobs.auto_jobs', return_value=4), contextlib.redirect_stdout(io.StringIO()):
            steps = build.miniwind_commands(args, build.commands(args, TOOLS, RUN))
        self.assertNotIn('chim-rooms-vivec_arena', [name for name, _ in steps])

    def test_vivec_arena_starts_in_the_whole_city(self):
        # the Arena preset starts at the Arena arrival of the whole-city frame (project decision 2026-10-11 09:55)
        args = self.preset('vivec-arena-chim')  # no --miniwind-town: the start picks the town
        self.assertEqual(args.miniwind_town, 'vivec_city')
        self.assertEqual(args.chim_areas, ['vivec_city'])
        self.assertEqual((args.direct_start.kind, args.direct_start.town), ('area', 'vivec_city'))
        self.assertIn('derived from the start vivec_city', args.miniwind_town_source)
        # the short names lead to the whole city; the Arena-only frame stays reachable by its own name (legacy)
        self.assertEqual(ds.parse('vivec').town, 'vivec_city')
        self.assertEqual(ds.parse('arena').town, 'vivec_city')
        self.assertEqual(ds.parse('vivec_arena').town, 'vivec_arena')

    def test_the_whole_city_starts_in_its_frame(self):
        args = self.preset('vivec-city-chim')  # all of Vivec in one CHIM frame (stage B)
        self.assertEqual(args.miniwind_town, 'vivec_city')
        self.assertEqual(args.chim_areas, ['vivec_city'])
        self.assertEqual((args.direct_start.kind, args.direct_start.town), ('area', 'vivec_city'))

    def test_a_start_outside_the_built_content_is_refused_before_any_stage(self):
        for argv, text in ((['--miniwind', '--miniwind-town', 'vivec_arena', '--direct-to-game-map', 'cell:-3,-2'],
                            'cell -3,-2 is outside the area this build holds'),
                           (['--miniwind', '--miniwind-scope', 'exterior', '--direct-to-game-map',
                             'interior:Balmora, Council Club'], 'is not in this build')):
            with self.subTest(argv=argv), self.assertRaises(ValueError) as error:
                self.configure(argv)
            self.assertIn(text, str(error.exception))
            self.assertIn('This build holds areas:', str(error.exception))

    def test_no_start_means_the_towns_arrival(self):
        args = self.configure(['--miniwind', '--miniwind-town', 'vivec_arena'])
        self.assertEqual((args.start_record['kind'], args.start_record['start']), ('area', 'vivec_arena'))
        args = self.configure([])
        self.assertEqual(args.start_record['kind'], 'new-game')

    def test_start_town_of_each_form(self):
        self.assertEqual(ds.start_town(ds.parse('vivec_arena')), 'vivec_arena')
        self.assertEqual(ds.start_town(ds.parse('interior:Balmora, Council Club')), 'balmora')
        self.assertEqual(ds.start_town(ds.parse('cell:4,-11')), 'vivec_arena')
        self.assertIsNone(ds.start_town(ds.parse('cell:20,20')))

    def test_image_start_check(self):
        import map_files
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'start map vivec_arena is not in the image'):
                ds.image_start_check(id1, {'map': 'vivec_arena', 'arrival': None, 'source': 'test'})
            (id1 / 'maps' / 'vivec_arena-chim.chim').write_bytes(b'frame')
            report = Path(tmp) / 'start-check.json'
            record = ds.image_start_check(id1, {'map': 'vivec_arena', 'arrival': None, 'source': 'test'}, report)
            self.assertEqual((record['ok'], record['map_file']), (True, 'maps/vivec_arena-chim.chim'))
            self.assertTrue(json.loads(report.read_text(encoding='utf-8'))['ok'])
            (id1 / 'maps' / 'room.bsp').write_bytes(b'room')
            with patch.object(map_files, 'is_chim_frame', return_value=False),                     patch('arrival_spot.Collision'), patch('arrival_spot.standing_spot', return_value=None):
                with self.assertRaisesRegex(ValueError, 'no standing spot'):
                    ds.image_start_check(id1, {'map': 'room', 'arrival': [0, 0, 24], 'source': 'test'})
            with patch.object(map_files, 'is_chim_frame', return_value=False), patch('arrival_spot.Collision'),                     patch('arrival_spot.standing_spot', side_effect=ValueError('Cyclic or excessive collision tree')):
                record = ds.image_start_check(id1, {'map': 'room', 'arrival': [0, 0, 24], 'source': 'test'})
            self.assertTrue(record['ok'])
            self.assertIn('COLLISION-TRACE-LIMIT-ROUTED-ROOM-36', record['collision'])


if __name__ == '__main__':
    unittest.main()
