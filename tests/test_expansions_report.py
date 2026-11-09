"""The expansions report (tools/expansions_report.py): Tribunal and Bloodmoon found or not, in plain lines.

Synthetic verdict records, tracker and census only; no game data is read."""
import json
from pathlib import Path
import tempfile
import unittest

import expansions_report as er

SHA = {'Morrowind.esm': 'a' * 64, 'Tribunal.esm': 'b' * 64, 'Bloodmoon.esm': 'c' * 64}
LABEL = 'Game of the Year edition (GOG and Steam, identical)'


def master(name, records):
    return {'name': name, 'kind': 'tes3-master', 'version': '1.30', 'sha256': SHA[name], 'verdict': 'known',
            'label': LABEL, 'bytes': 1, 'identity': {'valid': True, 'records': records}}


def archive(name, files):
    return {'name': name, 'kind': 'tes3-archive', 'version': None, 'sha256': 'd' * 64, 'verdict': 'known',
            'label': LABEL, 'bytes': 1, 'identity': {'valid': True, 'files': files}}


def game_data(*names):
    files = [master('Morrowind.esm', 50000), archive('Morrowind.bsa', 9000)]
    table = {'Tribunal.esm': master('Tribunal.esm', 9999), 'Tribunal.bsa': archive('Tribunal.bsa', 1174),
             'Bloodmoon.esm': master('Bloodmoon.esm', 10775), 'Bloodmoon.bsa': archive('Bloodmoon.bsa', 1545)}
    files += [table[n] for n in names]
    absent = [n for n in table if n not in names]
    return {'policy': 'warn', 'files': files, 'absent': absent, 'warnings': []}


def tracker(folder, shas=SHA):
    rows = [{'master': 'Tribunal.esm', 'state': 'runs'}, {'master': 'Tribunal.esm', 'state': 'not-in-image'},
            {'master': 'Tribunal.esm', 'state': 'inert'}, {'master': 'Bloodmoon.esm', 'state': 'carried'},
            {'master': 'Bloodmoon.esm', 'state': 'not-in-image'}, {'master': 'Morrowind.esm', 'state': 'runs'}]
    path = Path(folder) / 'mwscript-features.json'
    path.write_text(json.dumps({'version': '0.0.63-test', 'measured': {'masters': shas}, 'scripts': rows}),
                    encoding='utf-8')
    return path


CENSUS = {'masters': [{'name': 'Morrowind.esm', 'status': 'read'},
                      {'name': 'Tribunal.esm', 'status': 'pending', 'register': 'CREATURE-EXPANSION-62'},
                      {'name': 'Bloodmoon.esm', 'status': 'pending', 'register': 'CREATURE-EXPANSION-62'}],
          'totals': {'per_master': {'Morrowind.esm': 3, 'Tribunal.esm': 2, 'Bloodmoon.esm': 2}, 'built': 3},
          'groups': [{'records': [{'master': 'Tribunal.esm'}, {'master': 'Tribunal.esm'},
                                  {'master': 'Bloodmoon.esm'}]}],
          'unclassified': []}


class ExpansionsReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.tracker = tracker(self.folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_found(self):
        record = er.report(game_data('Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'),
                           tracker=self.tracker)
        text = er.lines(record)
        self.assertEqual(text[0], 'Expansions:')
        self.assertEqual(text[1], '  Tribunal: FOUND (Tribunal.esm v1.30 + Tribunal.bsa, ' + LABEL + '). Used now: '
                         '9,999 records in its master, 1,174 files in its archive, 1 of its 3 scripts run in '
                         'Vvardenfell, creatures counted in the summary. Waits for its world: Mournhold (1 scripts, '
                         'DLC-BUILD-LATER).')
        self.assertIn('Bloodmoon: FOUND (Bloodmoon.esm v1.30 + Bloodmoon.bsa', text[2])
        self.assertIn('Solstheim (1 scripts', text[2])
        self.assertFalse(any('[warning]' in t for t in text))
        self.assertEqual([r['status'] for r in record['expansions']], ['found', 'found'])
        json.dumps(record)    # the record goes into build-state.json and build-summary.json

    def test_one_missing(self):
        record = er.report(game_data('Tribunal.esm', 'Tribunal.bsa'), tracker=self.tracker)
        text = er.lines(record)
        self.assertIn('  Tribunal: FOUND', text[1])
        self.assertEqual(text[2], '  [warning] Bloodmoon: NOT FOUND (no Bloodmoon.esm in Data Files): left out; '
                                  'nothing of it is built, its world Solstheim neither.')

    def test_archive_missing(self):
        text = er.lines(er.report(game_data('Tribunal.esm', 'Bloodmoon.esm', 'Bloodmoon.bsa'), tracker=self.tracker))
        self.assertTrue(text[1].startswith('  [warning] Tribunal: PARTLY FOUND (Tribunal.esm v1.30, no Tribunal.bsa'))

    def test_both_missing(self):
        record = er.report(game_data(), tracker=self.tracker)
        text = er.lines(record)
        self.assertEqual(len([t for t in text if 'NOT FOUND' in t and t.startswith('  [warning]')]), 2)
        self.assertEqual([r['status'] for r in record['expansions']], ['not found', 'not found'])

    def test_no_dlc_hook(self):
        record = er.report(game_data('Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'), no_dlc=True,
                           tracker=self.tracker)
        text = er.lines(record)
        self.assertTrue(all('LEFT OUT by --no-dlc' in t for t in text[1:]))

    def test_tracker_of_other_masters_is_not_counted(self):
        other = tracker(self.folder, dict(SHA, **{'Tribunal.esm': 'e' * 64}))
        record = er.report(game_data('Tribunal.esm', 'Tribunal.bsa'), tracker=other)
        self.assertIsNone(record['expansions'][0]['scripts'])
        self.assertIn('other masters', record['scripts_source'])

    def test_summary_adds_the_census(self):
        record = er.report(game_data('Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'),
                           tracker=self.tracker)
        self.assertIs(er.finish(record, self.folder), record)        # no census yet: unchanged
        (self.folder / 'image').mkdir()
        (self.folder / 'image/creature-census.json').write_text(json.dumps(CENSUS), encoding='utf-8')
        final = er.finish(record, self.folder)
        text = er.lines(final, at_end=True)
        self.assertIn('0 of 2 creatures built (CREATURE-EXPANSION-62)', text[1])
        self.assertIn('1 of 2 creatures built (CREATURE-EXPANSION-62)', text[2])
        self.assertIsNone(record['expansions'][0]['creatures'])     # the start record is not changed


if __name__ == '__main__':
    unittest.main()
