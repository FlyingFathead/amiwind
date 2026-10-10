# SPDX-License-Identifier: GPL-3.0-only
"""MiniWind test spots (config/miniwind-presets.json, tools/miniwind_presets.py).

Every preset parses with the options' own parsers, every preset has its
--miniwind-NAME alias in --help, --miniwind-preset list prints the table, an
unknown preset is refused, release candidates and finals refuse presets, and
the Vivec Arena Pit preset stops with the start point's message while the
Arena interiors are not converted (IMPORT-TOWN-NO-INTERIORS-32).
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import miniwind_presets as mp  # noqa: E402

DEV = '0.0.33-dev1'


def run_main(argv, version=DEV):
    # build.main exports AMIWIND_* switches: restore them (TEST-ENV-LEAK-HULL-33)
    with patch.dict(os.environ), patch.object(build, 'VERSION', version), \
            patch.object(build, 'prerequisites') as setup, \
            contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        try:
            code = build.main(argv)
        except SystemExit as stop:
            code = stop.code
    return code, out.getvalue(), err.getvalue(), setup


class Table(unittest.TestCase):
    def test_every_preset_parses(self):
        rows = mp.presets()
        self.assertEqual([row['name'] for row in rows],
                         ['balmora', 'balmora-exterior', 'vivec-arena-pit', 'opening-ship', 'animkit'])
        ship = mp.find('opening-ship')
        self.assertEqual(ship['start'], 'interior:Imperial Prison Ship')
        self.assertEqual(ship['description'], 'Opening ship: lantern and ship lighting check')
        self.assertIs(ship['skip_census'], False)  # straight in at Jiub's lantern, no screen
        self.assertTrue(all(mp.find(n)['skip_census'] is None for n in ('balmora', 'balmora-exterior')))
        pit = mp.find('vivec-arena-pit')
        self.assertEqual(pit['start'], 'interior:Vivec, Arena Pit')
        self.assertEqual(pit['description'], 'Vivec Arena Pit: combat test')
        self.assertIn('npc-gallery', pit['exclude'])
        self.assertEqual(pit['unreferenced'], 'voice,npcs')
        self.assertEqual(mp.find('balmora-exterior')['scope'], 'exterior')

    def test_bad_rows_are_refused(self):
        good = dict(mp.find('balmora'))
        for change, reason in (({'name': 'Bad Name'}, 'lower case'), ({'scope': 'island'}, 'scope'),
                               ({'start': 'atlantis'}, 'unknown area'), ({'exclude': ['flora']}, 'refused'),
                               ({'unreferenced': 'music'}, 'always kept'), ({'character': 'Nord'}, 'RACE,CLASS'),
                               ({'description': ''}, 'empty'), ({'skip_census': 'yes'}, 'skip_census')):
            row = dict(good, **change)
            with self.subTest(change=change), self.assertRaises(ValueError) as error:
                mp.check_row(row)
            self.assertIn(reason, str(error.exception))
        with self.assertRaises(ValueError):
            mp.check_row({k: v for k, v in good.items() if k != 'character'})

    def test_aliases_appear_in_help(self):
        text = ' '.join(build.parser().format_help().split())
        self.assertIn('--miniwind-preset', text)
        for row in mp.presets():
            self.assertIn(mp.alias(row['name']), text)
        args = build.parser().parse_args(['--miniwind-vivec-arena-pit'])
        self.assertEqual(args.miniwind_preset, 'vivec-arena-pit')
        self.assertEqual(build.parser().parse_args(['--miniwind-preset', 'balmora']).miniwind_preset, 'balmora')

    def test_list_prints_the_table(self):
        code, out, err, setup = run_main(['--miniwind-preset', 'list'])
        self.assertEqual(code, 0)
        self.assertIn('--miniwind-vivec-arena-pit', out)
        self.assertIn('Vivec Arena Pit: combat test', out)
        setup.assert_not_called()

    def test_unknown_preset_is_refused(self):
        code, out, err, setup = run_main(['--miniwind-preset', 'atlantis', '--check'])
        self.assertEqual(code, 1)
        self.assertIn('unknown preset', err)
        setup.assert_not_called()

    def test_release_candidates_and_finals_refuse_presets(self):
        for version in ('0.0.33-rc1', '0.0.33'):
            with self.subTest(version=version):
                code, out, err, setup = run_main(['--miniwind-balmora', '--check'], version)
                self.assertEqual(code, 1)
                self.assertIn('release candidate or final', err)
                setup.assert_not_called()

    def test_the_arena_pit_waits_for_its_interiors(self):
        code, out, err, setup = run_main(['--miniwind-vivec-arena-pit', '--check', '--tools-dir', '/nonexistent'])
        self.assertEqual(code, 1)
        self.assertIn('Vivec, Arena Pit', err)
        self.assertIn('IMPORT-TOWN-NO-INTERIORS-32', err)
        setup.assert_not_called()

    def test_preset_fills_the_options_and_explicit_options_win(self):
        args = build.parser().parse_args(['--miniwind-vivec-arena-pit', '--miniwind-description', 'Mine'])
        mp.apply(args)
        self.assertTrue(args.miniwind)
        self.assertEqual(args.direct_to_game_map, 'interior:Vivec, Arena Pit')
        self.assertEqual(args.miniwind_description, 'Mine')
        self.assertEqual(args.exclude, ['npc-gallery'])
        self.assertEqual(args.exclude_unreferenced, 'voice,npcs')
        self.assertEqual(args.miniwind_preset_record['name'], 'vivec-arena-pit')
        args = build.parser().parse_args(['--miniwind-balmora'])
        mp.apply(args)
        self.assertEqual((args.miniwind_scope, args.direct_to_game_map), ('full', None))
        self.assertEqual(args.miniwind_description, 'Balmora: exterior and interiors')

    def test_the_table_is_a_public_file(self):
        names = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for path in (mp.TABLE, 'tools/miniwind_presets.py', 'tools/direct_start.py', 'tests/test_miniwind_presets.py',
                     'tests/test_direct_start.py'):
            self.assertIn(path, names)


if __name__ == '__main__':
    unittest.main()
