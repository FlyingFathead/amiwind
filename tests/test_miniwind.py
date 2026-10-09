# SPDX-License-Identifier: GPL-3.0-only
"""AmiWind "MiniWind" Playtester Build (tools/miniwind.py, tools/build.py --miniwind).

Every item of the build type is checked here: the name in help and receipts,
the -devN-only refusal, the stage plan, the generated FEATURES list, the boot
notice data file, the startup screen lines (version line generated from VERSION
and CHIM_VERSION, its "CHIM v..." part in the console font, the optional
"Scene:" line, room for the engine's "Press ENTER to start" and a held last
frame), the image pruning, the PARTIAL-AREA
marking and the scopes (--miniwind-scope full, the default, and exterior, the
Balmora exterior only). The engine side (notice file, quick start, "Area
unavailable", the Enter screen) is checked natively in
tests/aga_miniwind_test.c, tests/aga_scene_test.c and tests/aga_movie_test.c.
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
import build
import build_aga
import build_font_options as options
import build_parallel
import miniwind

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')
DEV = '0.0.33-dev1'


def plan(argv):
    args = build.parser().parse_args(argv)
    args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
    if args.miniwind:
        with patch.object(build, 'VERSION', DEV), contextlib.redirect_stdout(io.StringIO()):
            build.configure_miniwind(args)
    args.builder_options = options.resolve_builder(args)
    return build.commands(args, TOOLS, RUN), args


def names(steps):
    return [name for name, _ in steps]


def value(command, flag):
    command = [str(p) for p in command]
    return command[command.index(flag) + 1]


EXPECTED_STAGES = ['setup', 'terrain', 'scenery', 'scene', 'bsp', 'npcs', 'hands', 'interior', 'dialogue-lookup',
                   'intro', 'census', 'balmora', 'balmora-interiors', 'door-audio', 'character', 'reading',
                   'opening-references', 'media', 'music', 'engine', 'harvest', 'hand-catalog', 'chim', 'image']


class BuildTypeTests(unittest.TestCase):
    def test_help_names_the_build_type(self):
        text = ' '.join(build.parser().format_help().split())
        self.assertIn('AmiWind "MiniWind" Playtester Build', text)
        self.assertIn('--miniwind-description', text)
        self.assertEqual(miniwind.NAME, 'AmiWind "MiniWind" Playtester Build')

    def test_refused_for_release_candidates_and_finals_before_any_work(self):
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), patch.object(build, 'VERSION', version), \
                    patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()) as err, \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.main(['--miniwind', '--check', '--tools-dir', '/nonexistent-tools'])
            setup.assert_not_called()
            self.assertIn('release candidate or final', err.getvalue())

    def test_accepted_for_a_private_dev_version(self):
        with patch.object(build, 'VERSION', DEV), patch.object(build, 'prerequisites',
                                                                side_effect=ValueError('stop here')) as setup, \
                contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()) as out, \
                self.assertRaises(SystemExit):
            build.main(['--miniwind', '--check', '--tools-dir', '/nonexistent-tools'])
        setup.assert_called_once()
        self.assertIn('stop here', err.getvalue())
        self.assertIn('Build type: AmiWind "MiniWind" Playtester Build | PARTIAL-AREA', out.getvalue())

    def test_contradictory_options_stop_before_any_work(self):
        for extra in (['--builder', 'legacy'], ['--chim-area', 'vivec_arena'], ['--extra-town', 'vivec_arena'],
                      ['--only-core-towns'], ['--seyda-recorded', '/recorded'], ['--dry-run'],
                      ['--stage', 'terrain'], ['--miniwind-description', '']):
            with self.subTest(extra=extra), patch.object(build, 'VERSION', DEV), \
                    patch.object(build, 'prerequisites') as setup, patch.object(build, 'dry_run_prerequisites') as dry, \
                    contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaises(SystemExit):
                build.main(['--miniwind', *extra, '--check', '--tools-dir', '/nonexistent-tools'])
            setup.assert_not_called()
            dry.assert_not_called()
        with patch.object(build, 'VERSION', DEV), patch.object(build, 'prerequisites') as setup, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build.main(['--miniwind-description', 'Balmora', '--check', '--tools-dir', '/nonexistent-tools'])
        setup.assert_not_called()


class PlanTests(unittest.TestCase):
    def test_stage_plan_holds_only_what_the_build_needs(self):
        steps, args = plan(['--jobs', '4', '--miniwind'])
        self.assertEqual(names(steps), EXPECTED_STAGES)
        for stage in ('npc-gallery', 'area', 'actor-contact', 'world-survey', 'world-ui', 'world-terrain',
                      'world-scenery-assets', 'world-scenery', 'world-flora-assets', 'world-flora'):
            self.assertNotIn(stage, names(steps))
        self.assertFalse(any(n.startswith('town-') for n in names(steps)))
        self.assertEqual(value(dict(steps)['chim'], '--area'), 'balmora')
        self.assertEqual(args.builder_options['builder'], 'chim')
        # every left-out stage of the normal CHIM plan is recorded with its reason
        normal, _ = plan(['--jobs', '4', '--builder', 'chim'])
        left = set(names(normal)) - set(names(steps))
        self.assertEqual(left, set(args.miniwind_record['left_out']))
        self.assertTrue(all(args.miniwind_record['left_out'].values()))

    def test_image_step_is_marked_and_ships_balmora_only(self):
        steps, args = plan(['--jobs', '4', '--miniwind'])
        image = [str(p) for p in dict(steps)['image']]
        self.assertIn('--miniwind', image)
        self.assertIn('--no-npc-gallery', image)
        self.assertEqual(value(image, '--chim-world'), str(RUN / 'chim-world'))
        for flag in ('--world-scenery', '--gallery', '--canonical-land-source', '--entity-baseline',
                     '--world-flora', '--seyda-recorded', '--miniwind-description'):
            self.assertNotIn(flag, image)
        self.assertEqual(value(image, '--miniwind-features'), miniwind.features_line(names(steps)))

    def test_description_reaches_the_image_and_the_receipt(self):
        text = 'Balmora on CHIM, incremental streaming, photo mode'
        steps, args = plan(['--jobs', '4', '--miniwind', '--miniwind-description', text])
        self.assertEqual(value(dict(steps)['image'], '--miniwind-description'), text)
        self.assertEqual(args.miniwind_record['description'], text)

    def test_features_list_is_generated_from_the_stage_plan(self):
        steps, _ = plan(['--jobs', '4', '--miniwind'])
        self.assertEqual(miniwind.features(names(steps)),
                         ['Balmora exterior (CHIM)', 'Balmora interiors', 'Balmora residents', 'harvestable plants',
                          'per-race hands', 'door sounds', 'books', 'music', 'sound effects and voices'])
        line = miniwind.features_line(names(steps))
        self.assertTrue(line.startswith('FEATURES ONLY: Balmora exterior (CHIM), Balmora interiors'))
        # a stage the plan does not run is not listed
        for extra, label in ((['--no-harvest'], 'harvestable plants'), (['--hands', 'sprites'], 'per-race hands')):
            with self.subTest(extra=extra):
                fewer, _ = plan(['--jobs', '4', '--miniwind', *extra])
                self.assertNotIn(label, miniwind.features(names(fewer)))
                self.assertNotIn(label, value(dict(fewer)['image'], '--miniwind-features'))
        # every label names a stage of the MiniWind plan
        self.assertTrue({stage for stage, _ in miniwind.FEATURES} <= set(names(steps)))

    def test_normal_plans_are_unchanged(self):
        for argv in (['--jobs', '4'], ['--jobs', '4', '--builder', 'chim']):
            with self.subTest(argv=argv):
                steps, args = plan(argv)
                image = [str(p) for p in dict(steps)['image']]
                self.assertFalse(any(part.startswith('--miniwind') for part in image))
                self.assertIn('--world-scenery', image)
                self.assertIn('npc-gallery', names(steps))
                self.assertFalse(hasattr(args, 'miniwind_record'))

    def test_dependencies_follow_the_plan(self):
        steps, _ = plan(['--jobs', '4', '--miniwind'])
        deps = build_parallel.stage_dependencies(steps)
        self.assertEqual(deps['balmora'], ('census',))
        self.assertIn('chim', deps['image'])
        self.assertFalse({'world-terrain', 'world-scenery', 'npc-gallery'} & set(deps['image']))
        # the image still waits for the whole scene chain (every stage before it, transitively)
        def before(stage, seen=None):
            seen = set() if seen is None else seen
            for dep in deps[stage]:
                if dep not in seen:
                    seen.add(dep)
                    before(dep, seen)
            return seen
        self.assertEqual(before('image'), set(names(steps)) - {'image'})
        # the same holds for the normal plan
        # the normal plan keeps its full dependency check
        normal, _ = plan(['--jobs', '4'])
        normal_deps = build_parallel.stage_dependencies(normal)
        self.assertEqual(normal_deps['balmora'], ('area',))
        self.assertIn('world-terrain', normal_deps['image'])

    def test_receipt_and_summary_say_partial_area(self):
        steps, args = plan(['--jobs', '4', '--miniwind'])
        args.font_options = {'synthetic': True}
        with tempfile.TemporaryDirectory() as tmp, patch.object(build, 'ROOT', Path(tmp)), \
                patch.object(build, 'input_hashes', return_value={}):
            receipt = build.provenance(args, {})
        self.assertEqual(receipt['recipe'], 'miniwind-balmora-chim-v1')
        record = receipt['build_type']
        self.assertEqual(record['name'], miniwind.NAME)
        self.assertIn('PARTIAL-AREA', record['partial_area'])
        self.assertEqual(record['stages'], names(steps))
        self.assertEqual(record['notice'], [miniwind.NOTICE_TITLE, miniwind.features_line(names(steps))])
        self.assertIn('PARTIAL-AREA', build.miniwind_mode())
        normal, normal_args = plan(['--jobs', '4'])
        normal_args.font_options = {'synthetic': True}
        with tempfile.TemporaryDirectory() as tmp, patch.object(build, 'ROOT', Path(tmp)), \
                patch.object(build, 'input_hashes', return_value={}), patch.object(build, 'sha256', return_value='0'):
            self.assertNotIn('build_type', build.provenance(normal_args, {}))
        from build_summary import BuildSummary
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            summary = BuildSummary(Path(tmp), DEV, build.miniwind_mode())
            summary.record_environment({'build_type': record})
            result = summary.finish('failed')
        self.assertEqual(result['build_type']['name'], miniwind.NAME)
        text = out.getvalue()
        self.assertIn('Build type: AmiWind "MiniWind" Playtester Build | PARTIAL-AREA', text)
        self.assertIn(miniwind.NOTICE_TITLE, text)
        self.assertIn('FEATURES ONLY: ', text)


class NoticeAndLogoTests(unittest.TestCase):
    def test_boot_notice_data_file(self):
        line = miniwind.features_line(EXPECTED_STAGES)
        raw = miniwind.data_file(line)
        self.assertEqual(raw.decode('ascii'), 'AWMW1\ntown balmora\n'
                         'title ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD\nfeatures ' + line + '\n')
        self.assertNotIn(b'\r', raw)
        for bad in ('', 'FEATURES ONLY: ', 'no prefix', 'FEATURES ONLY: ' + 'x' * 600, 'FEATURES ONLY: \tx'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                miniwind.data_file(bad)

    def test_version_line_is_generated_from_version_and_chim_version(self):
        from project_version import chim_version, public_version
        mini = {'features': miniwind.features_line(EXPECTED_STAGES), 'description': None}
        lines = build_aga.startup_lines(mini, None)
        chim = (ROOT / 'CHIM_VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(chim_version(ROOT / 'VERSION'), chim)
        # "CHIM v<CHIM_VERSION>" in the console font, the rest of the line in the game font
        self.assertEqual(lines, ('MiniWind Playtest',
                                 (('AmiWind v%s / ' % public_version(), 'game'), ('CHIM v%s' % chim, 'console'))))
        self.assertEqual(miniwind.line_text(lines[1]), 'AmiWind v%s / CHIM v%s' % (public_version(), chim))
        # not hand-typed: other files give other lines
        with patch.object(build_aga, 'VERSION', '9.8.7-dev6'), patch('project_version.chim_version',
                                                                      return_value='5.4.3'):
            self.assertEqual(build_aga.startup_lines(mini, None)[1],
                             (('AmiWind v9.8.7-dev6 / ', 'game'), ('CHIM v5.4.3', 'console')))
        self.assertEqual(miniwind.version_line('0.0.33-dev1', '0.1.0'), 'AmiWind v0.0.33-dev1 / CHIM v0.1.0')
        self.assertEqual(miniwind.version_segments('0.0.33-dev1', '0.1.0'),
                         (('AmiWind v0.0.33-dev1 / ', 'game'), ('CHIM v0.1.0', 'console')))
        # the font names are the renderer's
        import prepare_logo
        self.assertEqual((miniwind.GAME_FONT, miniwind.CONSOLE_FONT),
                         (prepare_logo.GAME_FONT, prepare_logo.CONSOLE_FONT))
        # normal builds keep their two lines
        self.assertEqual(build_aga.startup_lines(None, None),
                         ('An open-source RPG engine', 'for the Commodore Amiga'))

    def test_optional_scene_line(self):
        mini = {'features': 'FEATURES ONLY: x', 'description': 'Balmora on CHIM, incremental streaming, photo mode'}
        lines = build_aga.startup_lines(mini, None)
        self.assertEqual(lines[0], 'MiniWind Playtest')
        self.assertTrue(lines[2].startswith('Scene: Balmora on CHIM'))
        self.assertLessEqual(len(lines), 4)
        self.assertEqual(' '.join(lines[2:]), 'Scene: Balmora on CHIM, incremental streaming, photo mode')
        self.assertEqual(len(build_aga.startup_lines(dict(mini, description=None), None)), 2)

    def test_description_validation(self):
        self.assertIsNone(miniwind.check_description(None))
        self.assertEqual(miniwind.check_description('  Balmora   on CHIM '), 'Balmora on CHIM')
        for bad in ('', '   ', 'café', 'tab\there', 'x' * 70):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                miniwind.check_description(bad)
        # pixel wrap: two lines at most, or a clear refusal
        self.assertEqual(miniwind.wrap('aa bb cc', len, 5), ['aa bb', 'cc'])
        with self.assertRaisesRegex(ValueError, 'does not fit'):
            miniwind.wrap('aa bb cc dd ee', len, 5)

    def test_logo_screen_renders_four_lines_in_the_game_font(self):
        from PIL import Image
        from prepare_logo import prepare_logo, startup_layout, STARTUP_LINES
        self.assertEqual(startup_layout(STARTUP_LINES, 16), (53, 141))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new('RGBA', (100, 40), (255, 255, 255, 255)).save(p / 'logo.png')
            font = p / 'font.awf'
            # every glyph 1x1, 16-pixel lines, advance 2 (as test_prepare_video's font)
            font.write_bytes(struct.pack('<4sBBH', b'AWF1', 16, 18, 1)
                             + struct.pack('<HBBbbBB', 0, 1, 1, 0, 0, 2, 0) * 256 + b'\xc0')
            lines = miniwind.logo_lines(DEV, '0.1.0', 'Balmora on CHIM, incremental streaming, photo mode')
            self.assertEqual(lines, ['MiniWind Playtest',
                                     (('AmiWind v0.0.33-dev1 / ', 'game'), ('CHIM v0.1.0', 'console')),
                                     'Scene: Balmora on CHIM, incremental streaming, photo mode'])
            prepare_logo(p / 'logo.png', p / 'normal.awv', font)
            prepare_logo(p / 'logo.png', p / 'mini.awv', font, lines=lines, prompt_top=miniwind.PROMPT_Y)
            self.assertNotEqual((p / 'normal.awv').read_bytes(), (p / 'mini.awv').read_bytes())
            with self.assertRaises(ValueError):
                prepare_logo(p / 'logo.png', p / 'wide.awv', font, lines=['x' * 200])
            with self.assertRaises(ValueError):
                prepare_logo(p / 'logo.png', p / 'many.awv', font, lines=['x'] * 9)
            # a character the font has no glyph for is refused
            raw = bytearray(font.read_bytes())
            raw[8 + ord('Q') * 8 + 6] = 0
            font.write_bytes(bytes(raw))
            with self.assertRaisesRegex(ValueError, 'no glyph'):
                prepare_logo(p / 'logo.png', p / 'glyph.awv', font, lines=['MINIWIND', 'Q'])
            # a console segment is not checked against the game font, but it must fit
            prepare_logo(p / 'logo.png', p / 'console-q.awv', font, lines=['MINIWIND', [('Q', 'console')]])
            with self.assertRaisesRegex(ValueError, 'does not fit'):
                prepare_logo(p / 'logo.png', p / 'wide2.awv', font,
                             lines=['x', [('x' * 10, 'game'), ('C' * 40, 'console')]])
            with self.assertRaisesRegex(ValueError, 'segments'):
                prepare_logo(p / 'logo.png', p / 'kind.awv', font, lines=['x', [('CHIM', 'bold')]])

    def test_chim_segment_is_drawn_in_the_console_font(self):
        """Magic Cards' capital H is an uncial h ("ChIM"): the version line draws
        "CHIM v<CHIM_VERSION>" with the engine's console glyphs (the conchars atlas
        of the "Press ENTER to start" prompt), the rest in the game font, the whole
        line centred, the CHIM cells on the game font's baseline."""
        from PIL import Image
        from prepare_logo import (CONSOLE_BASELINE, CONSOLE_CELL, TEXT_WIDTH, console_atlas, console_missing,
                                  game_baseline, line_segments, prepare_logo, segment_layout, startup_layout)
        from prepare_video import HEADER
        from debug_font import readable_atlas
        self.assertEqual(console_atlas(), readable_atlas())
        # the engine's conchars lump is that atlas (tools/prepare_quake.py)
        quake = (ROOT / 'tools/prepare_quake.py').read_text(encoding='utf-8')
        self.assertIn("readable=readable_atlas()", quake)
        self.assertIn("lumps=[('conchars',64,readable)]", quake)
        self.assertEqual(console_missing('CHIM v0.1.0-dev2'), [])
        self.assertEqual(console_missing('CHIM', bytes(128 * 128)), ['C', 'H', 'I', 'M'])
        chim = (ROOT / 'CHIM_VERSION').read_text(encoding='utf-8').strip()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new('RGBA', (100, 40), (255, 255, 255, 255)).save(p / 'logo.png')
            font = p / 'font.awf'
            # every glyph 1x1 at row 11 of a 16-pixel line (baseline 12), advance 2
            font.write_bytes(struct.pack('<4sBBH', b'AWF1', 16, 18, 1)
                             + struct.pack('<HBBbbBB', 0, 1, 1, 0, 11, 2, 0) * 256 + b'\xc0')
            raw_font = font.read_bytes()
            self.assertEqual(game_baseline(raw_font), 12)
            lines = miniwind.logo_lines(DEV, chim)
            prepare_logo(p / 'logo.png', p / 'mini.awv', font, lines=lines, prompt_top=miniwind.PROMPT_Y)
            raw = (p / 'mini.awv').read_bytes()
            _, width, height, _, _, frames, _ = HEADER.unpack_from(raw)
            palette = raw[HEADER.size:HEADER.size + 768]
            last = raw[HEADER.size + 768 + (frames - 1) * width * height:HEADER.size + 768 + frames * width * height]
            lit = [sum(palette[i * 3:i * 3 + 3]) > 0 for i in last]
        game_text, chim_text = (text for text, _ in line_segments(lines[1]))
        self.assertEqual((game_text, chim_text), ('AmiWind v%s / ' % DEV, 'CHIM v' + chim))
        segments, line_width = segment_layout(lines[1], lambda text: 2 * len(text), 12)
        self.assertEqual(line_width, 2 * len(game_text) + CONSOLE_CELL * len(chim_text))
        self.assertLessEqual(line_width, TEXT_WIDTH)
        _, text_top = startup_layout(lines, 16, miniwind.PROMPT_Y)
        top, left = text_top + 16, (320 - line_width) // 2
        # the game-font part: one pixel per character on its glyph row, nothing else
        for i in range(2 * len(game_text)):
            for y in range(top, top + 12):
                self.assertEqual(lit[y * 320 + left + i], i % 2 == 0 and y == top + 11, (i, y))
        # the CHIM part: exactly the console glyph cells, their row 7 on the baseline
        atlas = readable_atlas()
        cell_top = top + 12 - CONSOLE_BASELINE
        x0 = left + 2 * len(game_text)
        for k, c in enumerate(chim_text.encode('ascii')):
            for yy in range(CONSOLE_CELL):
                for xx in range(CONSOLE_CELL):
                    inked = bool(atlas[((c // 16) * 8 + yy) * 128 + (c % 16) * 8 + xx])
                    self.assertEqual(lit[(cell_top + yy) * 320 + x0 + k * CONSOLE_CELL + xx], inked, (chr(c), xx, yy))
        # nothing of the line spills past its centred width
        for y in range(top, top + 16):
            self.assertFalse(any(lit[y * 320 + x] for x in range(0, left)), y)
            self.assertFalse(any(lit[y * 320 + x] for x in range(left + line_width, 320)), y)

    def test_normal_startup_screen_never_uses_the_console_font(self):
        """Normal builds keep their two game-font lines and stream byte for byte:
        the console glyphs are only drawn for segment lines."""
        from PIL import Image
        import prepare_logo as logo
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new('RGBA', (100, 40), (255, 255, 255, 255)).save(p / 'logo.png')
            font = p / 'font.awf'
            font.write_bytes(struct.pack('<4sBBH', b'AWF1', 16, 18, 1)
                             + struct.pack('<HBBbbBB', 0, 1, 1, 0, 0, 2, 0) * 256 + b'\xc0')
            with patch.object(logo, 'console_atlas', side_effect=AssertionError('console font used')):
                logo.prepare_logo(p / 'logo.png', p / 'normal.awv', font)
                logo.prepare_logo(p / 'logo.png', p / 'normal-fallback.awv', None)
                # plain-string MiniWind-style lines stay on the game-font path too
                logo.prepare_logo(p / 'logo.png', p / 'plain.awv', font, lines=['MiniWind Playtest', 'x'],
                                  prompt_top=miniwind.PROMPT_Y)
            logo.prepare_logo(p / 'logo.png', p / 'again.awv', font, lines=list(logo.STARTUP_LINES))
            self.assertEqual((p / 'normal.awv').read_bytes(), (p / 'again.awv').read_bytes())
        self.assertEqual(build_aga.startup_lines(None, None), logo.STARTUP_LINES)

    def test_chim_builds_show_powered_by_chim_and_legacy_builds_never(self):
        """v0.0.33, the first CHIM release: a CHIM build's startup screen says "RPG engine powered by
        CHIM" ("CHIM" in the console font); a legacy build keeps the v0.0.32 lines; MiniWind keeps its own."""
        from PIL import Image
        import prepare_logo as logo
        chim = build_aga.startup_lines(None, None, chim=True)
        self.assertEqual(chim, logo.CHIM_STARTUP_LINES)
        self.assertEqual([logo.line_text(line) for line in chim], ['RPG engine powered by CHIM'])
        legacy = build_aga.startup_lines(None, None)
        self.assertEqual(legacy, logo.STARTUP_LINES)
        self.assertFalse(any('CHIM' in logo.line_text(line) for line in legacy))
        mini = {'features': 'FEATURES ONLY: x', 'description': None}
        self.assertEqual(build_aga.startup_lines(mini, None, chim=True), build_aga.startup_lines(mini, None))
        # the image step selects the lines by the CHIM world it packs (--chim-world: --builder chim)
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("chim=bool(getattr(args,'chim_world',None))", source)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new('RGBA', (100, 40), (255, 255, 255, 255)).save(p / 'logo.png')
            font = p / 'font.awf'
            font.write_bytes(struct.pack('<4sBBH', b'AWF1', 16, 18, 1)
                             + struct.pack('<HBBbbBB', 0, 1, 1, 0, 0, 2, 0) * 256 + b'\xc0')
            for name, path in (('font', font), ('fallback', None)):
                with self.subTest(font=name):
                    logo.prepare_logo(p / 'logo.png', p / ('chim-%s.awv' % name), path, lines=list(chim))
                    logo.prepare_logo(p / 'logo.png', p / ('legacy-%s.awv' % name), path)
                    self.assertNotEqual((p / ('chim-%s.awv' % name)).read_bytes(),
                                        (p / ('legacy-%s.awv' % name)).read_bytes())

    def test_receipt_records_plain_lines_and_the_console_segment(self):
        from types import SimpleNamespace
        chim = (ROOT / 'CHIM_VERSION').read_text(encoding='utf-8').strip()
        mini = {'features': 'FEATURES ONLY: x', 'scope': 'full', 'description': 'Balmora'}
        with tempfile.TemporaryDirectory() as tmp:
            out, boot = Path(tmp) / 'out', Path(tmp) / 'boot'
            (boot / 'id1').mkdir(parents=True)
            out.mkdir()
            (boot / 'id1' / miniwind.DATA_FILE).write_bytes(b'AWMW1\n')
            (out / 'miniwind-prune.json').write_text(json.dumps(
                {'maps_removed': [], 'bytes_removed': 0, 'maps_kept': [], 'interiors_missing': []}))
            args = SimpleNamespace(miniwind=True, miniwind_features='FEATURES ONLY: x',
                                   miniwind_description='Balmora', miniwind_scope=None)
            with patch.object(build_aga, 'miniwind_options', return_value=mini), \
                    patch.object(build_aga, 'VERSION', DEV):
                receipt = build_aga.miniwind_receipt(args, out, boot)
        self.assertEqual(receipt['logo_lines'], ['MiniWind Playtest', 'AmiWind v%s / CHIM v%s' % (DEV, chim),
                                                 'Scene: Balmora'])
        self.assertEqual(receipt['logo_console_font'], ['CHIM v' + chim])
        json.dumps(receipt)


    def test_enter_screen_leaves_room_for_the_prompt_and_ends_fully_visible(self):
        from PIL import Image
        from prepare_logo import PROMPT_GAP, prepare_logo, startup_gains, startup_layout
        from prepare_video import HEADER
        # the engine draws the same prompt at the same row (aw_miniwind.h)
        header = (ROOT / 'engine/aga/src/aw_miniwind.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_MINIWIND_PROMPT "%s"' % miniwind.PROMPT, header)
        self.assertIn('#define AW_MINIWIND_PROMPT_Y %d' % miniwind.PROMPT_Y, header)
        self.assertEqual(miniwind.PROMPT, 'Press ENTER to start')
        self.assertLessEqual(miniwind.PROMPT_Y + 8, 200)
        self.assertLessEqual(len(miniwind.PROMPT) * 8, 320)
        # four game-font lines (title, version, a two-line Scene) end above the prompt
        logo_top, text_top = startup_layout(['x'] * 4, 16, miniwind.PROMPT_Y)
        self.assertGreaterEqual(logo_top, 0)
        self.assertLessEqual(text_top + 4 * 16, miniwind.PROMPT_Y - PROMPT_GAP)
        with self.assertRaises(ValueError):
            startup_layout(['x'] * 6, 16, miniwind.PROMPT_Y)
        # normal builds keep their fades exactly (2 s in, 5 s visible, 1 s out)
        self.assertEqual(startup_gains(), [i / 20 for i in range(20)] + [1] * 50 + [i / 10 for i in range(9, -1, -1)])
        held = startup_gains(True)
        self.assertEqual(held[-1], 1)
        self.assertEqual(held[:20], [i / 20 for i in range(20)])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            Image.new('RGBA', (100, 40), (255, 255, 255, 255)).save(p / 'logo.png')
            lines = miniwind.logo_lines(DEV, '0.1.0', 'Balmora')
            prepare_logo(p / 'logo.png', p / 'mini.awv', None, lines=lines, prompt_top=miniwind.PROMPT_Y)
            raw = (p / 'mini.awv').read_bytes()
            _, width, height, _, _, frames, _ = HEADER.unpack_from(raw)
            self.assertEqual(frames, len(held))
            palette = raw[HEADER.size:HEADER.size + 768]
            last = raw[HEADER.size + 768 + (frames - 1) * width * height:HEADER.size + 768 + frames * width * height]
            rgb = [tuple(palette[i * 3:i * 3 + 3]) for i in last]
            # the held last frame is fully lit (its logo is the brightest), and the
            # prompt's rows (and the gap above them) are black for the engine's text
            self.assertTrue(any(sum(c) > 600 for c in rgb))
            for y in range(miniwind.PROMPT_Y - PROMPT_GAP, height):
                self.assertTrue(all(c == (0, 0, 0) for c in rgb[y * width:(y + 1) * width]), y)
            # a normal stream still ends black
            prepare_logo(p / 'logo.png', p / 'normal.awv', None)
            raw = (p / 'normal.awv').read_bytes()
            _, width, height, _, _, frames, _ = HEADER.unpack_from(raw)
            self.assertEqual(frames, 80)
            last = raw[HEADER.size + 768 + (frames - 1) * width * height:HEADER.size + 768 + frames * width * height]
            palette = raw[HEADER.size:HEADER.size + 768]
            self.assertTrue(all(sum(palette[i * 3:i * 3 + 3]) == 0 for i in set(last)))

    def test_engine_waits_for_enter_on_the_startup_screen(self):
        source = (ROOT / 'engine/aga/src/aw_movie.c').read_text(encoding='utf-8')
        self.assertIn('if(position>=samples){if(held_screen())hold("complete");else finish("complete");return;}', source)
        self.assertIn('if(down && key==K_ENTER)finish("started");', source)
        self.assertIn('if(holding)draw_prompt();', source)
        # the held screen leads to the quick start (aw_miniwind.c AW_MiniwindAfterLogo)
        self.assertIn('Cbuf_AddText((char *)AW_MiniwindAfterLogo())', source)


class ImageTests(unittest.TestCase):
    def test_prune_keeps_balmora_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'intro').mkdir()
            for name in ('seyda', 'prison', 'census', 'sn001', 'intro_docks', 'sncourt', 'vivec_arena', 'va000',
                         'balmora', 'bm000', 'bm063', 'bmcaius', 'tharystomb', 'fargoth'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'x' * 4)
            (id1 / 'intro/mw_intro.awv').write_bytes(b'm' * 10)
            (id1 / 'intro/amiwind.awv').write_bytes(b'l')
            record = miniwind.prune(id1)
            self.assertEqual(record['maps_kept'], ['balmora.bsp', 'bm000.bsp', 'bm063.bsp', 'bmcaius.bsp',
                                                   'tharystomb.bsp'])
            self.assertEqual(len(record['maps_removed']), 9)
            self.assertTrue((id1 / 'intro/amiwind.awv').is_file())
            self.assertIn('bmtemple', record['interiors_missing'])
            (id1 / 'maps/balmora.bsp').unlink()
            with self.assertRaisesRegex(ValueError, 'no Balmora map'):
                miniwind.prune(id1)

    def test_save_fingerprint_binds_the_shipped_maps_only(self):
        # A partial-area image lacks the Seyda Neen maps the normal fingerprint requires.
        from area_config import SCENES
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            for name in ('maps', 'character', 'world'):
                (id1 / name).mkdir(parents=True)
            kept, _ = miniwind.kept_maps()
            for name in kept | {'bm000'}:
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'\x1d\0\0\0' + bytes(120))
            (id1 / 'balmora-regions.txt').write_text('AWBR1 1 96 540 0 0 77 90 0 0 77 90\n'
                                                      'bm000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\n')
            for name in ('progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj',
                         'world/entries.dat', 'world/quests.awq', 'world/region-names.awn'):
                (id1 / name).write_bytes(b'x')
            with self.assertRaises((ValueError, OSError)):   # the normal image requires Seyda Neen
                build_aga.write_content_fingerprint(id1)
            build_aga.write_content_fingerprint(id1, partial=True)
            first = (id1 / 'save-content.bin').read_bytes()
            (id1 / 'maps/bmcaius.bsp').write_bytes(b'\x1d\0\0\0' + bytes(121))
            build_aga.write_content_fingerprint(id1, partial=True)
            self.assertNotEqual((id1 / 'save-content.bin').read_bytes(), first)
            (id1 / 'maps/bmcaius.bsp').unlink()
            with self.assertRaisesRegex(ValueError, 'bmcaius'):
                build_aga.write_content_fingerprint(id1, partial=True)
        self.assertTrue(any(s['map'] == 'seyda' for s in SCENES))

    def test_marking_and_image_options(self):
        self.assertEqual(miniwind.hdf_name(DEV), 'AmiWind-v0.0.33-dev1-MiniWind-PARTIAL-AREA.hdf')
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("tag = miniwind_hdf_tag(args)", source)
        self.assertIn("-MiniWind-PARTIAL-AREA", miniwind.HDF_TAG)
        text = miniwind.marker_text(DEV, 'FEATURES ONLY: x', 'Balmora')
        self.assertIn('PARTIAL-AREA', text)
        self.assertIn(miniwind.NAME, text)
        self.assertIn('Scene: Balmora', text)

        class Args:
            miniwind, miniwind_features, miniwind_description = True, 'FEATURES ONLY: x', None
            world_scenery = world_terrain = world_flora = seyda_recorded = gallery = None
        with patch.object(build_aga, 'VERSION', DEV):
            self.assertEqual(build_aga.miniwind_options(Args())['features'], 'FEATURES ONLY: x')
            for field in ('world_scenery', 'gallery', 'seyda_recorded'):
                bad = Args()
                setattr(bad, field, Path('/x'))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    build_aga.miniwind_options(bad)
            bad = Args()
            bad.miniwind_features = None
            with self.assertRaises(ValueError):
                build_aga.miniwind_options(bad)
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), patch.object(build_aga, 'VERSION', version), \
                    self.assertRaisesRegex(ValueError, 'release candidate or final'):
                build_aga.miniwind_options(Args())

        class Normal:
            miniwind, miniwind_features, miniwind_description, world_scenery = False, None, None, Path('/w')
        self.assertIsNone(build_aga.miniwind_options(Normal()))
        Normal.world_scenery = None
        with self.assertRaises(ValueError):
            build_aga.miniwind_options(Normal())


EXTERIOR_STAGES = [name for name in EXPECTED_STAGES if name not in ('balmora-interiors', 'door-audio')]


class ScopeTests(unittest.TestCase):
    """--miniwind-scope exterior: the Balmora exterior on CHIM only (quick playtest, no NPC gallery)."""

    def test_default_scope_is_full_and_unchanged(self):
        default, default_args = plan(['--jobs', '4', '--miniwind'])
        full, full_args = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'full'])
        self.assertEqual(names(default), EXPECTED_STAGES)
        self.assertEqual(default, full)
        self.assertEqual(default_args.miniwind_record, full_args.miniwind_record)
        record = default_args.miniwind_record
        self.assertEqual((record['scope'], record['label']), ('full', None))
        self.assertEqual(record['partial_area'], 'PARTIAL-AREA test build: Balmora only; not a release')
        self.assertNotIn(miniwind.QUICK_LABEL, record['notice'][1])
        image = [str(p) for p in dict(default)['image']]
        self.assertNotIn('--miniwind-scope', image)
        self.assertEqual(miniwind.hdf_name(DEV), 'AmiWind-v0.0.33-dev1-MiniWind-PARTIAL-AREA.hdf')
        self.assertEqual(miniwind.run_name('build-x'), 'build-x')
        self.assertEqual(build.miniwind_mode(), miniwind.NAME + ' (' + miniwind.PARTIAL_AREA + ')')

    def test_exterior_plan_holds_only_the_exterior_stages(self):
        steps, args = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'exterior'])
        self.assertEqual(names(steps), EXTERIOR_STAGES)
        for stage in ('balmora-interiors', 'door-audio', 'npc-gallery', 'area', 'world-terrain', 'world-flora'):
            self.assertNotIn(stage, names(steps))
        self.assertTrue(args.no_npc_gallery)
        record = args.miniwind_record
        self.assertEqual((record['scope'], record['label']), ('exterior', 'quick playtest, no NPC gallery'))
        self.assertEqual(record['stages'], EXTERIOR_STAGES)
        for stage in ('balmora-interiors', 'door-audio', 'npc-gallery'):
            self.assertIn(stage, record['left_out'])
            self.assertTrue(record['left_out'][stage])
        # every stage of the normal CHIM plan it does not run is recorded with a reason
        normal, _ = plan(['--jobs', '4', '--builder', 'chim'])
        self.assertEqual(set(names(normal)) - set(names(steps)), set(record['left_out']))
        self.assertTrue(all(record['left_out'].values()))
        # the CHIM world, harvest, hands, music, media, residents and the engine stay
        for stage in ('chim', 'balmora', 'harvest', 'hand-catalog', 'hands', 'music', 'media', 'engine', 'census'):
            self.assertIn(stage, names(steps))

    def test_exterior_features_and_label_are_generated(self):
        steps, args = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'exterior'])
        self.assertEqual(miniwind.features(names(steps)),
                         ['Balmora exterior (CHIM)', 'Balmora residents', 'harvestable plants', 'per-race hands',
                          'books', 'music', 'sound effects and voices'])
        line = miniwind.features_line(names(steps), 'exterior')
        self.assertEqual(line, 'FEATURES ONLY: Balmora exterior (CHIM), Balmora residents, harvestable plants, '
                               'per-race hands, books, music, sound effects and voices; quick playtest, no NPC gallery')
        self.assertNotIn('Balmora interiors', line)
        self.assertNotIn('door sounds', line)
        image = [str(p) for p in dict(steps)['image']]
        self.assertEqual(value(image, '--miniwind-features'), line)
        self.assertEqual(value(image, '--miniwind-scope'), 'exterior')
        self.assertIn('--no-npc-gallery', image)
        self.assertNotIn('--gallery', image)
        self.assertEqual(args.miniwind_record['notice'], [miniwind.NOTICE_TITLE, line])
        miniwind.data_file(line)  # fits the engine's notice buffer
        # a stage the plan does not run is not listed in this scope either
        fewer, _ = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'exterior', '--no-harvest'])
        self.assertNotIn('harvestable plants', value(dict(fewer)['image'], '--miniwind-features'))

    def test_exterior_dependencies_skip_the_left_out_stages(self):
        steps, _ = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'exterior'])
        deps = build_parallel.stage_dependencies(steps)
        self.assertEqual(deps['balmora'], ('census',))
        self.assertEqual(deps['character'], ('balmora',))
        self.assertIn('chim', deps['image'])

        def before(stage, seen=None):
            seen = set() if seen is None else seen
            for dep in deps[stage]:
                if dep not in seen:
                    seen.add(dep)
                    before(dep, seen)
            return seen
        self.assertEqual(before('image'), set(names(steps)) - {'image'})
        # the full scope keeps its chain
        full = build_parallel.stage_dependencies(plan(['--jobs', '4', '--miniwind'])[0])
        self.assertEqual(full['door-audio'], ('balmora-interiors',))
        self.assertEqual(full['character'], ('door-audio',))

    def test_exterior_label_in_names_receipts_and_summary(self):
        steps, args = plan(['--jobs', '4', '--miniwind', '--miniwind-scope', 'exterior'])
        self.assertEqual(miniwind.hdf_name(DEV, scope='exterior'),
                         'AmiWind-v0.0.33-dev1-MiniWind-PARTIAL-AREA-quick-playtest-no-NPC-gallery.hdf')
        self.assertEqual(miniwind.run_name('build-20261009-000000', 'exterior'),
                         'build-20261009-000000-quick-playtest-no-NPC-gallery')

        class ImageArgs:
            miniwind, miniwind_scope = True, 'exterior'
        self.assertEqual(build_aga.miniwind_hdf_tag(ImageArgs()), '-MiniWind-PARTIAL-AREA-quick-playtest-no-NPC-gallery')
        ImageArgs.miniwind_scope = None
        self.assertEqual(build_aga.miniwind_hdf_tag(ImageArgs()), '-MiniWind-PARTIAL-AREA')
        ImageArgs.miniwind = False
        self.assertEqual(build_aga.miniwind_hdf_tag(ImageArgs()), '')
        text = miniwind.marker_text(DEV, 'FEATURES ONLY: x', None, scope='exterior')
        self.assertIn('Balmora exterior only', text)
        self.assertIn('quick playtest, no NPC gallery', text)
        args.font_options = {'synthetic': True}
        with tempfile.TemporaryDirectory() as tmp, patch.object(build, 'ROOT', Path(tmp)), \
                patch.object(build, 'input_hashes', return_value={}):
            receipt = build.provenance(args, {})
        self.assertEqual(receipt['recipe'], 'miniwind-balmora-exterior-chim-v1')
        self.assertIn('quick playtest, no NPC gallery', receipt['npc_gallery'])
        self.assertEqual(receipt['build_type']['label'], 'quick playtest, no NPC gallery')
        mode = build.miniwind_mode('exterior')
        self.assertIn('Balmora exterior only', mode)
        self.assertIn('quick playtest, no NPC gallery', mode)
        from build_summary import BuildSummary
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            summary = BuildSummary(Path(tmp), DEV, mode)
            summary.record_environment({'build_type': receipt['build_type']})
            result = summary.finish('failed')
        self.assertEqual(result['build_type']['scope'], 'exterior')
        self.assertIn('MiniWind scope: exterior (quick playtest, no NPC gallery)', out.getvalue())
        self.assertIn('; quick playtest, no NPC gallery', out.getvalue())

    def test_exterior_image_keeps_the_balmora_exterior_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            for name in ('seyda', 'prison', 'census', 'balmora', 'bm000', 'bm063', 'bmcaius', 'tharystomb'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'x' * 4)
            record = miniwind.prune(id1, scope='exterior')
            self.assertEqual(record['scope'], 'exterior')
            self.assertEqual(record['maps_kept'], ['balmora.bsp', 'bm000.bsp', 'bm063.bsp'])
            self.assertIn('bmcaius.bsp', record['maps_removed'])
            self.assertEqual(record['interiors_missing'], [])
        # the save fingerprint binds no interior in this scope
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            for name in ('maps', 'character', 'world'):
                (id1 / name).mkdir(parents=True)
            for name in ('balmora', 'bm000'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'\x1d\0\0\0' + bytes(120))
            (id1 / 'balmora-regions.txt').write_text('AWBR1 1 96 540 0 0 77 90 0 0 77 90\n'
                                                      'bm000 -1024 -1024 1024 1024 -2048 -2048 2048 2048\n')
            for name in ('progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj',
                         'world/entries.dat', 'world/quests.awq', 'world/region-names.awn'):
                (id1 / name).write_bytes(b'x')
            with self.assertRaises(ValueError):
                build_aga.write_content_fingerprint(id1, partial=True)   # the full scope needs the interiors
            build_aga.write_content_fingerprint(id1, partial='exterior')
            self.assertTrue((id1 / 'save-content.bin').is_file())
            # pure CHIM: the image step then removes Balmora's legacy maps (the region
            # table stays) and binds the frame map instead
            removed = ['maps/balmora.bsp', 'maps/bm000.bsp']
            for name in removed:
                (id1 / name).unlink()
            (id1 / 'maps/balmora-chim.bsp').write_bytes(b'\x1d\0\0\0' + bytes(130))
            build_aga.write_content_fingerprint(id1, partial='exterior', removed=removed)
            first = (id1 / 'save-content.bin').read_bytes()
            (id1 / 'maps/balmora-chim.bsp').write_bytes(b'\x1d\0\0\0' + bytes(131))
            build_aga.write_content_fingerprint(id1, partial='exterior', removed=removed)
            self.assertNotEqual((id1 / 'save-content.bin').read_bytes(), first)
            with self.assertRaises(ValueError):
                build_aga.write_content_fingerprint(id1, partial='exterior')   # removed maps must be declared

    def test_prune_records_rows_in_the_pure_chim_removal_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            for name in ('seyda', 'intro_docks', 'sncourt', 'prison', 'balmora', 'bm000', 'bmcaius'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(name.encode())
            from chim.frame_map import remove_legacy_areas
            record = miniwind.prune(id1, scope='exterior', remove_legacy=remove_legacy_areas)
            rows = {row['file']: row for row in record['removed']}
            self.assertEqual(sorted(rows), ['maps/bmcaius.bsp', 'maps/intro_docks.bsp', 'maps/prison.bsp',
                                            'maps/seyda.bsp', 'maps/sncourt.bsp'])
            for row in rows.values():
                self.assertEqual(set(row), {'file', 'bytes', 'sha256', 'town', 'reason'})
                self.assertEqual(row['reason'], miniwind.NOT_BUILT)
            self.assertEqual(rows['maps/seyda.bsp']['town'], 'seyda')
            self.assertEqual(rows['maps/intro_docks.bsp']['town'], 'seyda')
            self.assertIsNone(rows['maps/prison.bsp']['town'])
            self.assertEqual(rows['maps/seyda.bsp']['bytes'], 5)
            self.assertEqual(record['bytes_removed'], sum(r['bytes'] for r in rows.values()))
            self.assertEqual(record['maps_removed'], [f[5:] for f in sorted(rows)])

    def test_exterior_image_options(self):
        class Args:
            miniwind, miniwind_features, miniwind_description = True, 'FEATURES ONLY: x', None
            miniwind_scope, no_npc_gallery = 'exterior', True
            world_scenery = world_terrain = world_flora = seyda_recorded = gallery = None
        with patch.object(build_aga, 'VERSION', DEV):
            self.assertEqual(build_aga.miniwind_options(Args())['scope'], 'exterior')
            Args.no_npc_gallery = False
            with self.assertRaisesRegex(ValueError, 'implies --no-npc-gallery'):
                build_aga.miniwind_options(Args())
            Args.no_npc_gallery, Args.miniwind_scope = True, 'interiors'
            with self.assertRaisesRegex(ValueError, '--miniwind-scope'):
                build_aga.miniwind_options(Args())
        for version in ('0.0.33-rc1', '0.0.33'):
            Args.miniwind_scope = 'exterior'
            with self.subTest(version=version), patch.object(build_aga, 'VERSION', version), \
                    self.assertRaisesRegex(ValueError, 'release candidate or final'):
                build_aga.miniwind_options(Args())

        class Normal:
            miniwind, miniwind_features, miniwind_description, world_scenery = False, None, None, Path('/w')
            miniwind_scope = 'exterior'
        with self.assertRaisesRegex(ValueError, 'require --miniwind'):
            build_aga.miniwind_options(Normal())
        # the image command accepts the option with the same values
        self.assertIn("i.add_argument('--miniwind-scope',choices=('full','exterior')",
                      (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        self.assertEqual(miniwind.SCOPES, ('full', 'exterior'))

    def test_exterior_refused_for_release_candidates_and_finals(self):
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version), patch.object(build, 'VERSION', version), \
                    patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()) as err, \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.main(['--miniwind', '--miniwind-scope', 'exterior', '--check', '--tools-dir', '/nonexistent'])
            setup.assert_not_called()
            self.assertIn('release candidate or final', err.getvalue())

    def test_bad_scope_values_are_refused_before_any_work(self):
        for argv in (['--miniwind', '--miniwind-scope', 'interiors'], ['--miniwind', '--miniwind-scope', ''],
                     ['--miniwind-scope', 'exterior']):
            with self.subTest(argv=argv), patch.object(build, 'VERSION', DEV), \
                    patch.object(build, 'prerequisites') as setup, contextlib.redirect_stderr(io.StringIO()) as err, \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                build.main([*argv, '--check', '--tools-dir', '/nonexistent-tools'])
            setup.assert_not_called()
            self.assertIn('--miniwind', err.getvalue())
        with self.assertRaisesRegex(ValueError, 'full, exterior'):
            miniwind.check_scope('balmora')

    def test_exterior_accepted_for_a_private_dev_version(self):
        with patch.object(build, 'VERSION', DEV), patch.object(build, 'prerequisites',
                                                                side_effect=ValueError('stop here')) as setup, \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()) as out, \
                self.assertRaises(SystemExit):
            build.main(['--miniwind', '--miniwind-scope', 'exterior', '--check', '--tools-dir', '/nonexistent'])
        setup.assert_called_once()
        self.assertIn('MiniWind scope: exterior (quick playtest, no NPC gallery)', out.getvalue())
        self.assertIn('Balmora exterior only', out.getvalue())


class FingerprintTests(unittest.TestCase):
    def test_miniwind_module_leaves_engine_sources_out_of_stage_fingerprints(self):
        """Every stage imports tools/miniwind.py (build_parallel): an engine C edit must not
        invalidate the conversion stages through it (test_build_cache, the gate 585 failure)."""
        import build_cache
        index = build_cache.SourceIndex()
        for script in ('miniwind.py', 'build_parallel.py'):
            with self.subTest(script=script):
                python, data, uncertain = index.closure(ROOT / 'tools' / script)
                self.assertFalse(uncertain)
                self.assertFalse([path for path in python if path.startswith('tools/chim/')], script)
                self.assertFalse([path for path in data if path.startswith('engine/')], script)
        # the startup screen's console glyphs come from the converter's own atlas
        # module (no imports, no data files), never from engine sources
        python, data, uncertain = index.closure(ROOT / 'tools' / 'debug_font.py')
        self.assertEqual((sorted(python), sorted(data), uncertain), (['tools/debug_font.py'], [], False))
        self.assertIn('from debug_font import readable_atlas',
                      (ROOT / 'tools/prepare_logo.py').read_text(encoding='utf-8'))


class DocsTests(unittest.TestCase):
    def test_docs_describe_every_item(self):
        page = (ROOT / 'docs/MINIWIND_PLAYTESTER.md').read_text(encoding='utf-8')
        for text in (miniwind.NAME, '--miniwind', '--miniwind-description', miniwind.NOTICE_TITLE,
                     'FEATURES ONLY:', miniwind.LOGO_TITLE, 'AmiWind v0.0.33-dev1 / CHIM v0.1.0', 'Scene:',
                     miniwind.PROMPT, 'PARTIAL-AREA', 'Area unavailable', '-devN', 'not a release',
                     '--miniwind-scope exterior', miniwind.QUICK_LABEL, miniwind.QUICK_SLUG,
                     miniwind.SCOPE_PARTIAL_AREA['exterior']):
            self.assertIn(text, page)
        shipped = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for name in ('docs/MINIWIND_PLAYTESTER.md', 'tools/miniwind.py', 'tests/test_miniwind.py',
                     'tests/aga_miniwind_test.c', 'engine/aga/src/aw_miniwind.c', 'engine/aga/src/aw_miniwind.h'):
            self.assertIn(name, shipped)
        self.assertIn('MINIWIND_PLAYTESTER.md', (ROOT / 'docs/LINUX_BUILD.md').read_text(encoding='utf-8'))
        self.assertIn('MINIWIND_PLAYTESTER.md', (ROOT / 'README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
