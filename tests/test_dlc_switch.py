"""The expansion switch (DLC-BUILD-LATER): --dlc tribunal|bloodmoon|both|none, --no-dlc / --no-dlcs; the default is
every expansion found, and the chosen layer set is recorded in the expansions record."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
import build_parser  # noqa: E402
import expansions_report  # noqa: E402


def game_data(*names):
    return {'files': [{'name': n, 'kind': 'tes3-master' if n.endswith('.esm') else 'bsa', 'verdict': 'known',
                       'identity': {}} for n in names]}


GOTY = game_data('Morrowind.esm', 'Morrowind.bsa', 'Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa')


class SwitchTests(unittest.TestCase):
    def test_flags(self):
        import argparse
        p = argparse.ArgumentParser()
        build_parser.add_accept_entity_loss_group(p)
        self.assertEqual(vars(p.parse_args([]))['dlc'], None)
        self.assertTrue(p.parse_args(['--no-dlcs']).dlc_off)
        self.assertTrue(p.parse_args(['--no-dlc']).dlc_off)
        self.assertEqual(p.parse_args(['--dlc', 'bloodmoon']).dlc, 'bloodmoon')
        with self.assertRaises(SystemExit):
            p.parse_args(['--dlc', 'mournhold'])

    def test_selection(self):
        sel = build.expansion_selection
        self.assertIsNone(sel(SimpleNamespace(dlc=None, no_dlc=False)))
        self.assertEqual(sel(SimpleNamespace(dlc=None, no_dlc=True)), [])
        self.assertEqual(sel(SimpleNamespace(dlc='none', no_dlc=True)), [])
        self.assertEqual(sel(SimpleNamespace(dlc='tribunal', no_dlc=False)), ['Tribunal'])
        self.assertEqual(sel(SimpleNamespace(dlc='bloodmoon', no_dlc=False)), ['Bloodmoon'])
        self.assertEqual(sel(SimpleNamespace(dlc='both', no_dlc=False)), ['Tribunal', 'Bloodmoon'])
        with self.assertRaises(ValueError):
            sel(SimpleNamespace(dlc='both', no_dlc=True))

    def test_layers_in_the_record(self):
        self.assertEqual(expansions_report.report(GOTY, tracker='/missing')['layers'], ['Tribunal', 'Bloodmoon'])
        only = expansions_report.report(GOTY, tracker='/missing', selected=['Bloodmoon'])
        self.assertEqual(only['layers'], ['Bloodmoon'])
        self.assertEqual(only['expansions'][0]['status'], 'left out by --dlc')
        self.assertTrue(any('LEFT OUT by --dlc' in line for line in expansions_report.lines(only)))
        none = expansions_report.report(GOTY, tracker='/missing', selected=[])
        self.assertEqual((none['layers'], none['no_dlc']), ([], True))
        base = expansions_report.report(game_data('Morrowind.esm', 'Morrowind.bsa'), tracker='/missing')
        self.assertEqual(base['layers'], [])                  # default: every expansion FOUND


if __name__ == '__main__':
    unittest.main()
