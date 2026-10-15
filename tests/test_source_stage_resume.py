"""Source-stage retry regressions using synthetic files, no game assets."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    sys.path.insert(0, str(p))
import import_town
from chim.build import source_stage

class SourceStageResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / 'data'
        self.data.mkdir()
        for name in ('Morrowind.esm', 'Morrowind.bsa'):
            (self.data / name).write_bytes(b'synthetic')
        self.settings = dict(source_cell=[2, 8], source_radius=0, centre=[0, 0], scale=0.25)
        self.work = Path(self.tmp.name) / 'work'
        self.work.mkdir()
        (self.work / 'scenery').mkdir()
        (self.work / 'scenery/scenery-index.json').write_text('{"old": true}')
        (self.work / 'original-evidence.txt').write_text('preserve')

    def receipt(self):
        with patch.dict(os.environ, {'AMIWIND_LAVA': 'quake'}):
            return import_town.source_receipt(self.data, self.settings)

    def store(self, value):
        (self.work / 'source-receipt.json').write_text(json.dumps(value))

    def collect(self, data, work, jobs, settings):
        (work / 'scenery').mkdir()
        (work / 'scenery/scenery-index.json').write_text('{"fresh": true}')
        (work / 'lava-pools.json').write_text('{"mode":"quake","pools":[{"synthetic":true}]}')

    def test_pre_lava_receipt_rebuilds_and_preserves_original(self):
        old = self.receipt()
        old.pop('conversion', None)
        self.store(old)
        with patch('import_town.collect', side_effect=self.collect) as collect:
            result = source_stage(self.data, self.work, 1, self.settings)
        self.assertEqual(result, {'fresh': True})
        collect.assert_called_once()
        archived = list(self.work.parent.glob('work.stale-*'))
        self.assertEqual(len(archived), 1)
        self.assertEqual((archived[0] / 'original-evidence.txt').read_text(), 'preserve')
        self.assertEqual(json.loads((self.work / 'source-receipt.json').read_text()), self.receipt())
        with patch('import_town.collect') as collect:
            self.assertEqual(source_stage(self.data, self.work, 1, self.settings), {'fresh': True})
        collect.assert_not_called()

    def test_matching_source_is_reused(self):
        self.store(self.receipt())
        with patch('import_town.collect') as collect:
            self.assertEqual(source_stage(self.data, self.work, 1, self.settings), {'old': True})
        collect.assert_not_called()

    def test_changed_owned_input_is_still_refused(self):
        self.store(self.receipt())
        (self.data / 'Morrowind.esm').write_bytes(b'changed')
        with patch('import_town.collect') as collect, self.assertRaisesRegex(ValueError, 'other inputs'):
            source_stage(self.data, self.work, 1, self.settings)
        collect.assert_not_called()
        self.assertTrue((self.work / 'original-evidence.txt').is_file())

    def test_mode_and_conversion_code_are_in_receipt(self):
        quake = self.receipt()
        with patch.dict(os.environ, {'AMIWIND_LAVA': 'static'}):
            static = import_town.source_receipt(self.data, self.settings)
        self.assertNotEqual(quake, static)
        for name in ('import_town.py', 'lava.py'):
            self.assertEqual(quake['conversion']['code_sha256'][name],
                             hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest())


    def test_fixed_state_change_rebuilds_without_destroying_previous_stage(self):
        self.settings['fixed_visibility_state'] = {'stronghold': 1}
        self.store(self.receipt())
        self.settings['fixed_visibility_state'] = {'stronghold': 6}
        with patch('import_town.collect', side_effect=self.collect) as collect:
            self.assertEqual(source_stage(self.data, self.work, 1, self.settings), {'fresh': True})
        collect.assert_called_once()
        archived = list(self.work.parent.glob('work.stale-*'))
        self.assertEqual(len(archived), 1)
        self.assertTrue((archived[0] / 'original-evidence.txt').is_file())

    def test_fixed_state_receipt_required_and_bound_to_cell_and_state(self):
        refs = [{'number': 1}, {'number': 2}, {'number': 3}]
        self.assertIs(import_town.fixed_state_references(self.work, self.settings, refs), refs)
        self.settings['fixed_visibility_state'] = {'stronghold': 6}
        with self.assertRaises(FileNotFoundError):
            import_town.fixed_state_references(self.work, self.settings, refs)
        report = {'requested_state': {'stronghold': 6}, 'cell': [2, 8],
                  'references': [{'reference': 1, 'enabled_at_requested_state': False},
                                 {'reference': 2, 'enabled_at_requested_state': None}]}
        path = self.work / 'fixed-visibility.json'
        path.write_text(json.dumps(report))
        self.assertEqual(import_town.fixed_state_references(self.work, self.settings, refs), refs[1:])
        for key, value in [('cell', [10, 1]), ('requested_state', {'stronghold': 1})]:
            path.write_text(json.dumps(dict(report, **{key: value})))
            with self.assertRaisesRegex(ValueError, 'does not match'):
                import_town.fixed_state_references(self.work, self.settings, refs)

    def test_apron_snapshot_follows_original_cell_on_both_sides(self):
        recipe = lambda cell: {'fixed_visibility_state': {'stronghold': 6}} if tuple(cell) == (10, 1) else {}
        refs = [{'number': 100}, {'number': 101}, {'number': 200}]
        def audit(raw, cell, state):
            self.assertEqual(raw, b'synthetic')
            return dict(cell=list(cell), requested_state=state, references=[
                {'reference': 100, 'enabled_at_requested_state': False},
                {'reference': 101, 'enabled_at_requested_state': None}])
        with patch('visual_recipes.cell_settings', side_effect=recipe), patch('mwad.script_visibility.audit_cell', side_effect=audit) as reader:
            for centre in ((9, 1), (10, 1), (11, 2)):
                settings = dict(self.settings, source_cell=list(centre), source_radius=1)
                import_town.write_fixed_visibility(self.data, self.work, settings)
                self.assertEqual(import_town.fixed_state_references(self.work, settings, refs), refs[1:])
            self.assertEqual(reader.call_count, 3)
            self.assertTrue(all(call.args[1] == [10, 1] for call in reader.call_args_list))
        self.assertEqual(refs, [{'number': 100}, {'number': 101}, {'number': 200}])

    def test_neighbour_snapshot_is_in_source_receipt(self):
        recipe = lambda cell: {'fixed_visibility_state': {'stronghold': 6}} if tuple(cell) == (3, 8) else {}
        self.settings['source_radius'] = 1
        with patch('visual_recipes.cell_settings', return_value={}):
            old = self.receipt()
        with patch('visual_recipes.cell_settings', side_effect=recipe):
            new = self.receipt()
        self.assertNotEqual(old, new)
        self.assertEqual(new['fixed_visibility_cells'], [{'cell': [3, 8], 'requested_state': {'stronghold': 6}}])

    def test_apron_snapshot_rejects_wrong_or_missing_cell_receipt(self):
        recipe = lambda cell: {'fixed_visibility_state': {'stronghold': 6}} if tuple(cell) == (3, 8) else {}
        self.settings['source_radius'] = 1
        with patch('visual_recipes.cell_settings', side_effect=recipe):
            for reports in ([], [{'cell': [2, 8], 'requested_state': {'stronghold': 6}, 'references': []}],
                            [{'cell': [3, 8], 'requested_state': {'stronghold': 1}, 'references': []}]):
                (self.work / 'fixed-visibility.json').write_text(json.dumps({'schema':'source-cell-visibility-1','reports':reports}))
                with self.assertRaisesRegex(ValueError, 'does not match'):
                    import_town.fixed_state_references(self.work, self.settings, [{'number': 1}])

    def test_explicit_visibility_state_guards_stay_strict(self):
        for state in ({}, {'stage': True}, {'stage': float('inf')}, {'stage': float('nan')}, {'': 6}):
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, 'finite explicit globals'):
                import_town.fixed_visibility_cells(dict(self.settings, fixed_visibility_state=state))
