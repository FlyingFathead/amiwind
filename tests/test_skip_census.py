# SPDX-License-Identifier: GPL-3.0-only
"""--skip-census and the quick character screen, builder side (tools/build.py, tools/build_aga.py).

The option's default (on for MiniWind and other direct-start builds unless
--quick-character gives the character, off for every other build), the explicit
--skip-census / --no-skip-census, the -devN-only refusal for normal builds, the
image command and its default-game.cfg line, the Census office files a MiniWind
image leaves out with it, the opening-ship preset (the prison ship as a
MiniWind direct start, kept by the prune), the title screen header and the
public docs. The engine side is checked natively (tests/aga_quickchar_test.c,
tests/aga_testbox_test.c, tests/aga_miniwind_test.c); that New Game and the
debug command reach the one entry point is checked here on the sources.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import build_aga  # noqa: E402
import miniwind  # noqa: E402
import miniwind_presets as mp  # noqa: E402

DEV = '0.0.33-dev1'
TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')
SRC = ROOT / 'engine/aga/src'


def configure(argv, version=DEV):
    args = build.parser().parse_args(argv)
    args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
    with patch.object(build, 'VERSION', version), contextlib.redirect_stdout(io.StringIO()):
        if getattr(args, 'miniwind_preset', None):
            mp.apply(args)
        if args.miniwind:
            build.configure_miniwind(args)
        import build_exclusions
        build_exclusions.resolve(args, version, area_build=bool(args.miniwind))
        build.configure_direct_start(args)
        build.configure_skip_census(args)
    return args


def image_command(args):
    import build_font_options as options
    args.builder_options = options.resolve_builder(args)
    with patch('build_jobs.auto_jobs', return_value=4), patch.object(build, 'VERSION', DEV), \
            contextlib.redirect_stdout(io.StringIO()):
        steps = build.commands(args, TOOLS, RUN)
        if args.miniwind:
            steps = build.miniwind_commands(args, steps) or steps
    return [str(p) for p in dict(steps)['image']]


class Defaults(unittest.TestCase):
    def test_default_is_on_for_quick_test_builds_and_off_for_normal_builds(self):
        for argv, on, source in (
                ([], False, 'default: normal build'),
                (['--miniwind'], True, 'default: quick test build'),
                (['--direct-to-game-map', 'balmora'], True, 'default: quick test build'),
                (['--miniwind', '--quick-character', 'Nord,Barbarian'], False,
                 'default: --quick-character gives the character'),
                (['--miniwind', '--quick-character', 'Nord,Barbarian', '--skip-census'], True, '--skip-census'),
                (['--miniwind', '--no-skip-census'], False, '--no-skip-census'),
                (['--skip-census'], True, '--skip-census')):
            with self.subTest(argv=argv):
                record = configure(argv).skip_census_record
                self.assertEqual(record, {'on': on, 'source': source})

    def test_the_default_command_is_unchanged(self):
        # A normal build: no --skip-census in the image step, so New Game keeps the ship and the census.
        self.assertNotIn('--skip-census', image_command(configure([])))
        self.assertIn('--skip-census', image_command(configure(['--skip-census'])))

    def test_flags_contradict(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build.parser().parse_args(['--skip-census', '--no-skip-census'])

    def test_normal_builds_refuse_it_for_release_candidates_and_finals(self):
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), self.assertRaises(ValueError) as error:
                configure(['--skip-census'], version)
            self.assertIn('release candidate or final', str(error.exception))
        # --no-skip-census changes nothing on a normal build: accepted everywhere.
        self.assertFalse(configure(['--no-skip-census'], '0.0.33').skip_census_record['on'])
        self.assertIn('--skip-census', build_aga.image_waivers(SimpleNamespace(skip_census=True)))
        self.assertNotIn('--skip-census', build_aga.image_waivers(SimpleNamespace(skip_census=False)))


class ImageStep(unittest.TestCase):
    def test_game_config_line_only_with_the_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'default-game.cfg').write_bytes(b'aw_autosaves 5')
            self.assertEqual(build_aga.stage_skip_census(SimpleNamespace(skip_census=False), id1), {'on': False})
            self.assertEqual((id1 / 'default-game.cfg').read_bytes(), b'aw_autosaves 5')
            with contextlib.redirect_stdout(io.StringIO()):
                record = build_aga.stage_skip_census(SimpleNamespace(skip_census=True), id1)
            text = (id1 / 'default-game.cfg').read_text(encoding='ascii')
            self.assertTrue(record['on'] and text.startswith('aw_autosaves 5\n') and text.endswith('aw_skip_census 1\n'))
            self.assertNotIn('\r', text)
        # The shipped defaults never set it themselves.
        self.assertNotIn('aw_skip_census', (ROOT / 'config/game.cfg').read_text(encoding='utf-8'))

    def test_census_files_leave_a_miniwind_image_with_the_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'maps').mkdir()
            (id1 / 'progs').mkdir()
            for name in ('balmora', 'census', 'prison'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'b')
            for name in miniwind.CENSUS_FILES + ('progs/np_jiub.mdl',):
                (id1 / name).write_bytes(b'x')
            kept = lambda: sorted(p.relative_to(id1).as_posix() for p in id1.rglob('*') if p.is_file())
            with patch.object(miniwind, 'kept_maps', return_value=({'balmora'}, 'bm')):
                record = miniwind.prune(id1)
                self.assertEqual(record['census_files_removed'], [])
                self.assertIn('doors-census.txt', kept())
                record = miniwind.prune(id1, census_files=True)
            self.assertEqual(sorted(record['census_files_removed']), sorted(miniwind.CENSUS_FILES))
            self.assertEqual(kept(), ['maps/balmora.bsp', 'progs/np_jiub.mdl'])
            self.assertTrue(all(r['reason'] == miniwind.SKIP_CENSUS for r in record['removed']
                                if r['file'] in miniwind.CENSUS_FILES))

    def test_the_prison_ship_stays_as_a_miniwind_direct_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'maps').mkdir()
            for name in ('balmora', 'census', 'prison', 'seyda'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'b')
            with patch.object(miniwind, 'kept_maps', side_effect=lambda root, scope, town='balmora', extra=(): ({town, *extra}, 'bm')):
                record = miniwind.prune(id1, extra=miniwind.start_maps('prison'))
            self.assertEqual(record['maps_kept'], ['balmora.bsp', 'prison.bsp'])
        self.assertEqual(miniwind.start_maps('census'), ())
        self.assertEqual(miniwind.start_maps(None), ())


class Presets(unittest.TestCase):
    def test_opening_ship_boots_at_jiub_without_the_screen(self):
        args = configure(['--miniwind-opening-ship'])
        self.assertTrue(args.miniwind)
        self.assertEqual(args.direct_to_game_map, 'interior:Imperial Prison Ship')
        self.assertEqual(args.miniwind_description, 'Opening ship: lantern and ship lighting check')
        self.assertEqual(args.skip_census_record, {'on': False, 'source': '--no-skip-census'})
        self.assertEqual(args.direct_start.map, 'prison')
        # An explicit option still wins over the row.
        self.assertTrue(configure(['--miniwind-opening-ship', '--skip-census']).skip_census_record['on'])

    def test_balmora_preset_keeps_the_default(self):
        self.assertEqual(configure(['--miniwind-balmora']).skip_census_record['source'], 'default: quick test build')


class Header(unittest.TestCase):
    def test_header_text_and_wrap(self):
        self.assertEqual(miniwind.header_line('Balmora: exterior and interiors'),
                         'MINIWIND TEST UNIT: Balmora: exterior and interiors')
        self.assertEqual(miniwind.header_line(None), 'MINIWIND TEST UNIT: Balmora')
        long_text = miniwind.header_line('x' * 200)
        self.assertEqual(len(long_text), miniwind.HEADER_CHARS)
        self.assertTrue(long_text.endswith('...'))
        measure = lambda s: 7 * len(s)
        self.assertEqual(miniwind.header_lines('MINIWIND TEST UNIT: Balmora', measure), (['MINIWIND TEST UNIT: Balmora'], False))
        lines, cut = miniwind.header_lines('MINIWIND TEST UNIT: Balmora on CHIM, incremental streaming, photo mode '
                                           'and a lot more words here', measure)
        self.assertEqual(lines, ['MINIWIND TEST UNIT: Balmora on CHIM,', 'incremental streaming, photo mode and a...'])
        self.assertTrue(cut and all(measure(line) <= miniwind.HEADER_WIDTH for line in lines))

    def test_header_reaches_the_notice_file_and_parses_in_the_engine_format(self):
        data = miniwind.data_file('FEATURES ONLY: Balmora exterior (CHIM)', header=miniwind.header_line('Scene'))
        self.assertTrue(data.endswith(b'header MINIWIND TEST UNIT: Scene\n'))
        with self.assertRaises(ValueError):
            miniwind.data_file('FEATURES ONLY: x', header='h' * (miniwind.HEADER_CHARS + 1))
        engine = (SRC / 'aw_miniwind.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_MINIWIND_HEADER %d' % (miniwind.HEADER_CHARS + 1), engine)


class EngineSources(unittest.TestCase):
    @unittest.expectedFailure  # EXPERIMENTAL, unfinished: the quick character screen work in progress
    # (docs/EXPERIMENTAL_FLAGS.md); this check passes once that part is written
    def test_new_game_and_the_debug_command_use_the_same_entry_point(self):
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        quick = (SRC / 'aw_quickchar.c').read_text(encoding='utf-8')
        self.assertIn('AW_QuickCharOpen(AW_QC_ALL|AW_QC_VOICE,quick_screen_done)', scene)
        self.assertRegex(quick, r'static void quickchar_command\(void\)\{[^}]*AW_QuickCharOpen\(')
        # The pages are the census office's own menus: only aw_quickchar.c opens them without the box,
        # and nothing else builds a character sheet.
        users = [p.name for p in SRC.glob('*.c') if 'AW_CharacterOpenQuick(' in p.read_text(encoding='utf-8', errors='replace')]
        self.assertEqual(sorted(users), ['aw_character.c', 'aw_quickchar.c'])
        self.assertNotIn('attributes[i]=', quick)

    def test_skip_census_new_game_and_the_normal_game(self):
        intro = (SRC / 'aw_intro.c').read_text(encoding='utf-8')
        self.assertRegex(intro, r'if\(AW_SkipCensus\(\)\)\{Cbuf_AddText\("aw_quick_start')
        self.assertIn('static cvar_t skip_census={"aw_skip_census","0"};', (SRC / 'aw_quickchar.c').read_text(encoding='utf-8'))

    @unittest.expectedFailure  # EXPERIMENTAL, unfinished: the quick character screen work in progress
    # (docs/EXPERIMENTAL_FLAGS.md); this check passes once that part is written
    def test_console_commands_are_documented(self):
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        for words, command in (('quickchar', 'aw_quickchar'), ('quickchar set', 'aw_quickchar_set'),
                               ('quickchar show', 'aw_quickchar_show'), ('seed', 'aw_seed'),
                               ('test status', 'aw_test_status')):
            self.assertRegex(catalogue, r'(?m)^[A-Z /]+\|%s\|%s\|' % (re.escape(words), command))


class Docs(unittest.TestCase):
    @unittest.expectedFailure  # EXPERIMENTAL, unfinished: the quick character screen work in progress
    # (docs/EXPERIMENTAL_FLAGS.md); this check passes once that part is written
    def test_docs_describe_every_item(self):
        guide = (ROOT / 'docs/chim/build_guide/DIRECT_START.md').read_text(encoding='utf-8')
        for item in ('--skip-census', '--no-skip-census', 'dbg quickchar', 'AW_QuickCharOpen', 'aw_quickchar_set',
                     'aw_seed', 'AWTEST:', 'test.cfg', 'cmd.cfg', 'aw_test_poll', 'AWCMDBOX', 'aw_boot_console',
                     'aw_test_start', 'aw_quickchar_voice', 'MINIWIND TEST UNIT'):
            self.assertIn(item, guide)
        mini = (ROOT / 'docs/chim/build_guide/MINIWIND.md').read_text(encoding='utf-8')
        self.assertIn('a quick beta-testing sandbox for individual areas, scenes and mechanisms', mini)
        self.assertIn('opening-ship', mini)
        self.assertIn('config/miniwind-presets.json', mini)


if __name__ == '__main__':
    unittest.main()
