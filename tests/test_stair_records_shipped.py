# SPDX-License-Identifier: GPL-3.0-only
"""Known-good stair records shipped with the source (B14, v0.0.42 plan 1.0b; docs/BUILD_PROFILE.md "Known-good
stair records"): one entry per CHIM frame under the frame walk's full key, with the frame's flight steps (place
and behaviour) and the SHA-256 of all its rows; hashes, references and coordinates only. --stair-walk-cache records
(the default without --developer-mode) reuses a frame whose key is there without walking it; a frame whose key is
not there is reported by name and not walked; cached walks it; full ignores every stored and shipped walk."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import collision  # noqa: E402
import stair_records  # noqa: E402


class ShippedRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        for name in ('AMIWIND_STAIR_WALK_REUSE', 'AMIWIND_STAIR_WALK_AREA', 'AMIWIND_PASS_CACHE',
                     stair_records.SHIPPED_ENV):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_STAIR_WALK_CACHE='cached', AMIWIND_STAIR_WALK_SAMPLE='0', AMIWIND_STAIR_WALK_KEY='frame', AMIWIND_STAIR_WALK='all', AMIWIND_STAIR_WATCH='off',
                          AMIWIND_RUN_VERSION='0.0.42-dev1', AMIWIND_RUN_NAME='2026_10_16_v0.0.42-dev1_full_abc1234')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def world(self, name, fill=False):
        from test_chim_stairs import world_of
        out = Path(self.tmp.name) / name
        out.mkdir()
        world_of(out, fill)
        return out

    def gate(self, out, cache=None, mode='cached'):
        from chim.validate import Failures, load_world
        os.environ['AMIWIND_STAIR_WALK_CACHE'] = mode
        if cache is not None:
            os.environ['AMIWIND_PASS_CACHE'] = str(cache)
        else:
            os.environ.pop('AMIWIND_PASS_CACHE', None)
        world = load_world(out, Failures())
        collision._STAIR_CACHE.clear()
        return collision.stair_gate(out, world[5], 1, models=world[4])

    def export(self, fill=False):
        """A full walk into a fresh pass cache, then the shipped records of that world (stair_records.export)."""
        out = self.world('walked-%s' % fill, fill)
        cache = Path(self.tmp.name) / ('cache-%s' % fill)
        walked = self.gate(out, cache)
        records = Path(self.tmp.name) / 'records'
        result = stair_records.export(out, cache, records / 'test-world.json', '0.0.42-dev1', 'abc1234',
                                      '2026_10_16_v0.0.42-dev1_full_abc1234')
        os.environ[stair_records.SHIPPED_ENV] = str(records)
        return walked, result, records

    def test_an_unchanged_world_is_not_walked(self):
        walked, result, records = self.export()
        self.assertEqual((result['entries'], result['missing_count']), (1, 0))
        self.assertGreaterEqual(result['flight_steps'], 3)
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked')):
            again = self.gate(self.world('same'), Path(self.tmp.name) / 'empty-cache', mode='records')
        self.assertEqual((again['pass_cache']['walked'], again['records']['matched'], again['records']['unmatched']),
                         (0, 1, []))
        self.assertEqual(again['status'], walked['status'])
        self.assertTrue(list(again['pass_cache']['frames'].values())[0].startswith('reused from the shipped records'))
        # the flight steps are the walked ones; the advisory rows are counted, not listed
        flights = lambda report: sorted(json.dumps(stair_records.flight_row(r)) for r in  # noqa: E731
                                        report['failures'] + report['advisory_failures'])
        self.assertEqual(flights(again), sorted(json.dumps(stair_records.flight_row(r)) for r in walked['failures']
                                                + walked['advisory_failures'] if r.get('flight')))

    def test_a_failed_flight_in_the_records_still_fails_the_gate(self):
        walked, _, _ = self.export(fill=True)
        self.assertEqual(walked['status'], 'failed')
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked')):
            again = self.gate(self.world('same', fill=True), mode='records')
        self.assertEqual(again['status'], 'failed')
        self.assertEqual({r['ref'] for r in again['failures']}, {r['ref'] for r in walked['failures']})

    def test_a_changed_frame_is_reported_and_not_walked(self):
        self.export(fill=False)
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked')):
            changed = self.gate(self.world('changed', fill=True), mode='records')
        self.assertEqual(changed['records']['matched'], 0)
        self.assertEqual(len(changed['records']['unmatched']), 1)
        self.assertEqual(changed['pass_cache']['walked'], 0)
        self.assertIn('not walked', list(changed['pass_cache']['frames'].values())[0])
        # on request (cached) it is walked, and its fill is found
        walked = self.gate(self.world('walked-on-request', fill=True), Path(self.tmp.name) / 'dev-cache')
        self.assertEqual((walked['pass_cache']['walked'], walked['status']), (1, 'failed'))

    def test_full_ignores_the_shipped_records(self):
        self.export()
        full = self.gate(self.world('full'), mode='full')
        self.assertIsNone(full.get('records'))
        self.assertEqual(full['pass_cache']['walked'], 1)

    def test_a_sampled_shipped_frame_is_walked_and_must_match(self):
        self.export()
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '1'
        sampled = self.gate(self.world('sampled'), mode='records')
        self.assertEqual(sampled['pass_cache']['sampled'], [list(sampled['pass_cache']['frames'])[0]])
        # a shipped record that does not match what the walk gives stops the gate
        records = Path(os.environ[stair_records.SHIPPED_ENV]) / 'test-world.json'
        data = json.loads(records.read_text(encoding='utf-8'))
        entry = data['entries'][0]
        entry['flights'][0][8] = 'failed' if entry['flights'][0][8] != 'failed' else 'passed'
        entry['flights_sha256'] = stair_records.sha256_of(entry['flights'])
        entry['entry_sha256'] = stair_records.sha256_of({k: v for k, v in entry.items() if k != 'entry_sha256'})
        stair_records.write_shipped(records, {k: v for k, v in data['head'].items() if k not in ('format', 'frames')},
                                    data['entries'])
        with self.assertRaisesRegex(ValueError, 'differs from its shipped record'):
            self.gate(self.world('tampered'), mode='records')

    def test_a_damaged_entry_is_never_reused(self):
        _, _, records = self.export()
        path = records / 'test-world.json'
        text = path.read_text(encoding='utf-8')
        data = json.loads(text)
        data['entries'][0]['flights'][0][2] += 1.0          # moved, without a new SHA-256
        path.write_text(json.dumps(data), encoding='utf-8', newline='\n')
        found, notes = stair_records.load_shipped(records)
        self.assertEqual((found, len(notes['damaged'])), ({}, 1))
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked')):
            report = self.gate(self.world('damaged'), mode='records')
        self.assertEqual((report['records']['matched'], len(report['records']['damaged'])), (0, 1))

    def test_the_file_holds_hashes_references_and_coordinates_only(self):
        _, result, records = self.export()
        data = json.loads((records / 'test-world.json').read_text(encoding='utf-8'))
        self.assertEqual(data['head']['format'], stair_records.SHIPPED_FORMAT)
        entry = data['entries'][0]
        self.assertEqual(sorted(entry), sorted(['path', 'cell', 'key', 'walker', 'rule', 'area', 'outcome', 'counts',
                                                'rows_sha256', 'flights', 'flights_sha256', 'entry_sha256']))
        for flight in entry['flights']:
            self.assertEqual(len(flight), 10)
            self.assertTrue(all(isinstance(v, (str, int, float, type(None))) for v in flight))
        self.assertEqual(result['sha256'], __import__('hashlib').sha256((records / 'test-world.json')
                                                                         .read_bytes()).hexdigest())
        self.assertNotIn(b'\r', (records / 'test-world.json').read_bytes())

    def test_export_refuses_a_world_that_was_not_walked(self):
        out = self.world('unwalked')
        result = stair_records.export(out, Path(self.tmp.name) / 'nothing', Path(self.tmp.name) / 'r' / 'x.json',
                                      '0.0.42-dev1', 'abc1234', 'run')
        self.assertEqual(result['missing_count'], 1)
        self.assertFalse((Path(self.tmp.name) / 'r' / 'x.json').exists())


class ShippedFile(unittest.TestCase):
    def test_the_shipped_records_read_back_and_are_listed(self):
        found, notes = stair_records.load_shipped(stair_records.SHIPPED_FOLDER)
        self.assertEqual(notes['damaged'], [])
        files = sorted(p.name for p in stair_records.SHIPPED_FOLDER.glob('*.json'))
        self.assertEqual(sorted(f['file'] for f in notes['files']), files)
        if files:
            self.assertGreater(len(found), 0)
            listed = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
            text = json.dumps(listed)
            for name in files:
                self.assertIn('config/stair-records/' + name, text)
            for name in files:
                self.assertLess((stair_records.SHIPPED_FOLDER / name).stat().st_size, 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
