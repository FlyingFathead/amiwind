# SPDX-License-Identifier: GPL-3.0-only
"""The Seyda Neen town step's options, checked when the builder composes the plan (BUILD-MINIWIND-SEYDA-KELP-INDEX-54).

A MiniWind builds no world flora; the Seyda Neen chim-town stage still checks the frame's kelp additions against the
town scenery's source index, so the index must reach it with or without flora. The builder refuses a chim-town command
that lacks an option the stage needs before any stage runs (tools/chim_town.py missing_options), not minutes later.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
from chim_town import missing_options  # noqa: E402

RUN = Path('/vol/ws8/build/run')


class SeydaTownOptionsTests(unittest.TestCase):
    def test_miniwind_without_flora_gets_the_index(self):
        options = build.seyda_town_options(RUN, {'scenery', 'chim', 'census'})
        self.assertEqual(options, ['--town-source-index', RUN / 'scenery/scenery-index.json'])
        self.assertEqual(missing_options('seyda', ['chim_town.py', '--town', 'seyda', *options]), [])

    def test_full_build_options_unchanged(self):
        options = build.seyda_town_options(RUN, {'scenery', 'world-flora-assets'})
        self.assertEqual([str(o) for o in options if str(o).startswith('--')],
                         ['--flora', '--town-source-index', '--town-scene-report'])
        self.assertEqual(missing_options('seyda', options), [])

    def test_missing_index_is_named(self):
        self.assertEqual(missing_options('seyda', ['--town', 'seyda']), ['--town-source-index'])
        self.assertEqual(missing_options('seyda', ['--flora', 'F', '--town-source-index', 'I']), ['--town-scene-report'])

    def test_other_towns_need_nothing_extra(self):
        self.assertEqual(missing_options('balmora', ['--town', 'balmora']), [])

    def test_stage_refuses_before_work(self):
        with self.assertRaises(SystemExit) as raised:
            from chim_town import main
            main(['--town', 'seyda', '--data-files', 'D', '--scene', 'S', '--chim-world', 'C', '--out', 'O'])
        self.assertEqual(raised.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
