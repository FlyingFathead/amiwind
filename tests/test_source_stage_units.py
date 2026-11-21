# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-TESTER-32GB-OOM-67: each CHIM area's source catalogue (import_town.collect) is kept in the unit cache across
runs, so a CHIM stage that runs again in a new run folder takes it back instead of making it again.

Before, chim.build.source_stage reused a catalogue only from the run's own work folder (its source-receipt.json): a
build stopped for memory and started again in a new folder, or a CHIM stage rerun for a key change, made every area's
catalogue again (210 of 294 CPU minutes of a CHIM stage whose other units all came from the cache). Synthetic files, no
game data; collect is replaced by a writer of known bytes."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import import_town  # noqa: E402
from chim import source_units  # noqa: E402
from chim.build import source_stage  # noqa: E402


def tree(folder):
    """{relative path: SHA-256} of every file under FOLDER."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


class SourceCatalogueAcrossRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # one unit cache folder and input lock for the class (opening the cache hashes the repository's sources once):
        # each test has an area and a game data folder of its own, so their units never meet
        import known_inputs
        cls.shared = tempfile.TemporaryDirectory()
        lock = Path(cls.shared.name) / 'inputs.json'
        lock.write_text(json.dumps({'schema': known_inputs.LOCK_SCHEMA,
                                    'files': {'Morrowind.esm': {'sha256': '1' * 64}}}))
        cls.env = {'AMIWIND_PASS_CACHE': str(Path(cls.shared.name) / 'cache'), known_inputs.LOCK_ENV: str(lock),
                   'AMIWIND_LAVA': 'quake'}

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = self.root = Path(self.tmp.name)
        self.data = root / 'data'
        self.data.mkdir()
        for name in ('Morrowind.esm', 'Morrowind.bsa'):
            (self.data / name).write_bytes(b'synthetic ' + name.encode() + self.id().encode())
        self.area = 'synthetic'
        self.settings = {'source_cell': [2, 8], 'source_radius': 0, 'centre': [0, 0], 'scale': 0.25,
                         'town': {'id': self.area, 'title': 'Synthetic', 'visual_group': self.area,
                                  'test': self.id()}}
        self.calls = 0
        patcher = patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def collect(self, data, work, jobs, settings):
        """What collect writes, in miniature: the audit, the scenery export and the catalogue files."""
        self.calls += 1
        (work / 'audit').mkdir()
        (work / 'audit/placements.json').write_text('[{"number": 1}]\n')
        (work / 'audit/terrain.mwt').write_bytes(bytes(range(256)) * 4)
        (work / 'scenery').mkdir()
        (work / 'scenery/scenery-index.json').write_text('{"references": [], "made": %d}\n' % self.calls)
        (work / 'scenery/scenery.mwpak').write_bytes(b'MWPK' + bytes(1000))
        for name in ('source-catalogue.json', 'emitters.json', 'lava-pools.json', 'coverage.json'):
            (work / name).write_text('{"%s": true}\n' % name)
        # the footprint probe collect removes again (import_town.footprint_references)
        (work / 'frame-footprint').mkdir()
        (work / 'frame-footprint/probe.bin').write_bytes(b'probe')
        (work / 'frame-footprint/probe.bin').unlink()
        (work / 'frame-footprint').rmdir()

    def run_stage(self, run, collect=None):
        work = self.root / run / 'chim-world/work/synthetic'
        work.mkdir(parents=True, exist_ok=True)
        with patch('import_town.collect', side_effect=collect or self.collect):
            return work, source_stage(self.data, work, 1, self.settings)

    def test_a_new_run_folder_takes_the_catalogue_from_the_unit_cache(self):
        first, made = self.run_stage('run1')
        self.assertEqual(self.calls, 1)

        def refused(*_args, **_kwargs):
            raise AssertionError('collect ran again for an unchanged area in a new run folder')
        second, taken = self.run_stage('run2', refused)
        self.assertEqual(taken, made)
        self.assertEqual(tree(second), tree(first))          # the same files, byte for byte, the receipt included
        self.assertEqual(json.loads((second / 'source-receipt.json').read_text()),
                         import_town.source_receipt(self.data, self.settings))

    def test_the_receipt_is_not_stored_but_written_from_the_key(self):
        first, _ = self.run_stage('run1')
        cache, inputs = source_units.unit(self.settings, import_town.source_receipt(self.data, self.settings))
        row, files = cache.load_unit(inputs)
        self.assertEqual(row, {'format': source_units.FORMAT, 'area': 'synthetic'})
        self.assertNotIn(source_units.RECEIPT, files)
        self.assertEqual(sorted(files), sorted(set(tree(first)) - {source_units.RECEIPT}))

    def test_changed_game_files_make_the_catalogue_again(self):
        self.run_stage('run1')
        (self.data / 'Morrowind.esm').write_bytes(b'a changed master')
        self.run_stage('run2')
        self.assertEqual(self.calls, 2)

    def test_changed_settings_make_the_catalogue_again(self):
        self.run_stage('run1')
        self.settings['reference_margin'] = 64           # read by collect, not in the receipt's geometry
        self.run_stage('run2')
        self.assertEqual(self.calls, 2)

    def test_the_same_run_folder_still_reuses_its_own_receipt(self):
        self.run_stage('run1')
        with patch.object(source_units, 'restore', side_effect=AssertionError('the folder\'s own receipt first')):
            self.run_stage('run1', lambda *a, **k: self.fail('collect ran again in the same folder'))
        self.assertEqual(self.calls, 1)

    def test_files_there_before_collect_stay_out_of_the_unit(self):
        work = self.root / 'run1/chim-world/work/synthetic'
        work.mkdir(parents=True)
        (work / 'ocean-source.json').write_text('{"cell": [2, 8]}\n')     # written by prepare_area before the stage
        self.run_stage('run1')
        second, _ = self.run_stage('run2', lambda *a, **k: self.fail('collect ran again'))
        self.assertNotIn('ocean-source.json', tree(second))

    def test_cache_off_or_no_input_lock_runs_collect_as_before(self):
        import known_inputs
        for change in ({'AMIWIND_PASS_CACHE': 'off'}, {known_inputs.LOCK_ENV: ''}):
            with self.subTest(change=change), patch.dict(os.environ, change):
                self.assertEqual(source_units.unit(self.settings, {}), (None, None))
                before = self.calls
                self.run_stage('off-%d' % before)
                self.run_stage('off-%d-again' % before)
                self.assertEqual(self.calls, before + 2)

    def test_rebuild_unit_makes_it_again(self):
        self.run_stage('run1')
        with patch.dict(os.environ, {'AMIWIND_REBUILD_UNITS': '%s:synthetic' % source_units.UNIT}):
            self.run_stage('run2')
        self.assertEqual(self.calls, 2)

    def test_other_bytes_in_the_folder_are_never_overwritten(self):
        first, _ = self.run_stage('run1')
        receipt = import_town.source_receipt(self.data, self.settings)
        cache, inputs = source_units.unit(self.settings, receipt)
        work = self.root / 'run2/work'
        (work / 'scenery').mkdir(parents=True)
        (work / 'scenery/scenery.mwpak').write_bytes(b'other bytes')
        self.assertFalse(source_units.restore(cache, inputs, work, receipt))
        self.assertEqual(tree(work), {'scenery/scenery.mwpak': hashlib.sha256(b'other bytes').hexdigest()})
        # a restore that stopped midway left some of the stored files: the rest is written, the receipt last
        part = self.root / 'run3/work'
        (part / 'scenery').mkdir(parents=True)
        (part / 'scenery/scenery.mwpak').write_bytes((first / 'scenery/scenery.mwpak').read_bytes())
        self.assertTrue(source_units.restore(cache, inputs, part, receipt))
        self.assertEqual(tree(part), tree(first))

    def test_the_minute_one_report_counts_the_cache(self):
        """The reuse check counts a rebuilt stage's units in this cache (tools/reuse_all.py unit_cache_openers)."""
        import reuse_all
        openers = [o for o in reuse_all.unit_cache_openers(ROOT) if o['name'] == source_units.UNIT]
        self.assertEqual([(o['module'], o['scripts']) for o in openers],
                         [('tools/chim/source_units.py', [[str(ROOT / 'tools/import_town.py'), 'collect']])])


if __name__ == '__main__':
    unittest.main()
