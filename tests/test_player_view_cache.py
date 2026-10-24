# SPDX-License-Identifier: GPL-3.0-only
"""The player view's units (tools/prepare_player_view.py; BUILD-PLAYER-VIEW-UNDERUSED-48): the 80 bakes (body, torch
body, water body, inventory poses per race and sex) run in one worker pool for the step and are kept in the image
unit cache (tools/pass_cache.py UnitCache) by their inputs. A build with the same inputs makes none of them again,
and the image's files and the receipt are byte-identical with the cache off, cold and warm."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import pass_cache  # noqa: E402
import prepare_player_view as view  # noqa: E402

RACES = ['argonian', 'dark elf']
CALLS = []


def _seed(task):
    return hashlib.sha256(repr((task[1], task[2], task[3])).encode()).digest()


def fake_body(task):
    CALLS.append(('body', task[2], task[3]))
    path = view.body_path(task[2], task[3])
    raw = b'MDL' + _seed(task)
    row = {'race': task[2], 'female': task[3], 'model': path, 'sha256': hashlib.sha256(raw).hexdigest(),
           'groups': {'idle': 8, 'walk': 3 if task[3] else 4}, 'layout': 'idle 0 8', '_item_tags': 'TAGS 1\n'}
    return path, raw, 'idle 0 8', row


def fake_torch(task):
    CALLS.append(('torch', task[2], task[3]))
    body, held, meta = view.torch_paths(task[4]['model'])
    seed = _seed(task) + json.dumps(task[4]['groups'], sort_keys=True).encode()
    return body, b'T' + seed, 'idle 0 8', held, b'H' + seed, meta, b'AWBT' + seed, \
        {'race': task[2], 'female': task[3], 'base_model': task[4]['model'], 'groups': task[4]['groups']}


def fake_swim(task):
    CALLS.append(('swim', task[2], task[3]))
    path = view.swim_path(task[4]['model'])
    return path, b'W' + _seed(task), 'swim 0 8', {'race': task[2], 'female': task[3], 'model': path}


def fake_inventory(task):
    CALLS.append(('inventory', task[2], task[3]))
    path = view.body_path(task[2], task[3])[:-4] + '_i.mdl'
    return path, b'I' + _seed(task), 'TAGS 10\n', {'race': task[2], 'female': task[3], 'model': path,
                                                   'poses': [{'group': 'inventoryhandtohand', 'time': 0.5}]}


FAKES = {'body': fake_body, 'torch': fake_torch, 'swim': fake_swim, 'inventory': fake_inventory}


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


class PlayerViewUnitCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        for name in ('Morrowind.esm', 'Morrowind.bsa'):
            (self.data / name).write_bytes(b'')
        CALLS.clear()

    def tearDown(self):
        self.temp.cleanup()

    def cache(self, sources='s1'):
        return pass_cache.UnitCache(view.UNIT_CACHE, {'game_data': 'g', 'environment': {}}, sources,
                                    self.root / 'cache')

    def prepare(self, name, cache, palette=b'\1' * 768):
        id1 = self.root / name / 'id1'
        (id1 / 'gfx').mkdir(parents=True)
        (id1 / 'gfx/palette.lmp').write_bytes(palette)
        with patch.object(view, '_sources', return_value=({}, None, {})), \
             patch.object(view, 'settings_text', return_value='AWVS1\nfVanityDelay 30\n'), \
             patch.object(view, 'playable_races', return_value=list(RACES)), \
             patch.object(view, '_unit_worker', side_effect=FAKES.__getitem__), \
             patch.object(view, '_unit_cache', return_value=cache), \
             patch.dict(os.environ, {'AMIWIND_COST_HISTORY': str(self.root / 'costs')}):
            report = view.prepare(self.data, id1, jobs=1)
        return id1, report

    def test_cold_then_warm_makes_nothing_again_and_writes_the_same_bytes(self):
        off, off_report = self.prepare('off', None)
        self.assertEqual(len(CALLS), 4 * 2 * len(RACES))
        self.assertEqual(off_report.pop('unit_cache'), {'units': 16, 'reused': 0, 'made': 16, 'cache': 'off'})
        CALLS.clear()
        cold, cold_report = self.prepare('cold', self.cache())
        self.assertEqual(len(CALLS), 16)
        self.assertEqual(cold_report.pop('unit_cache')['reused'], 0)
        CALLS.clear()
        warm, warm_report = self.prepare('warm', self.cache())
        self.assertEqual(CALLS, [])                                    # every unit from the cache
        self.assertEqual(warm_report.pop('unit_cache'), {'units': 16, 'reused': 16, 'made': 0,
                                                         'cache': 'player-view'})
        self.assertEqual(tree(cold), tree(off))
        self.assertEqual(tree(warm), tree(off))
        # the receipt: same values in the same key order (it is written with json.dumps)
        self.assertEqual(json.dumps(cold_report), json.dumps(off_report))
        self.assertEqual(json.dumps(warm_report), json.dumps(off_report))
        self.assertIn('progs/body/argonian_f_t.mdl', tree(warm))
        self.assertEqual(tree(warm)['progs/body/argonian_f.tag'], b'TAGS 1\n')
        # the unit seconds are recorded for the next build's longest-first order
        recorded = json.loads((self.root / 'costs' / 'player-view.json').read_text())['seconds']
        self.assertEqual(len(recorded), 16)
        self.assertIn('body argonian female', recorded)

    def test_a_changed_input_makes_only_what_reads_it(self):
        self.prepare('cold', self.cache())
        CALLS.clear()
        self.prepare('palette', self.cache(), palette=b'\2' * 768)    # every unit reads the palette
        self.assertEqual(len(CALLS), 16)
        CALLS.clear()
        self.prepare('code', self.cache(sources='s2'))                 # the bake code changed
        self.assertEqual(len(CALLS), 16)
        CALLS.clear()
        with patch.dict(os.environ, {pass_cache.REBUILD_ENV: 'player-view:swim dark elf male'}):
            self.prepare('forced', self.cache())                       # --rebuild-unit names one unit
        self.assertEqual(CALLS, [('swim', 'dark elf', False)])

    def test_torch_inputs_hold_the_body_groups_and_water_inputs_the_model(self):
        task = ('data', b'\1' * 768, 'nord', True)
        row = {'model': 'progs/body/nord_f.mdl', 'groups': {'idle': 8}, 'sha256': 'x'}
        torch = view.unit_inputs(('torch', task + (row,)))
        self.assertEqual(torch['base'], {'model': 'progs/body/nord_f.mdl', 'groups': {'idle': 8}})
        other = view.unit_inputs(('torch', task + (dict(row, groups={'idle': 7}),)))
        self.assertNotEqual(pass_cache.input_digest(torch), pass_cache.input_digest(other))
        self.assertEqual(view.unit_inputs(('swim', task + (row,)))['base'], {'model': 'progs/body/nord_f.mdl'})
        body = view.unit_inputs(('body', task))
        self.assertEqual(body['entry'], {'name': 'body nord female'})
        self.assertEqual(body['palette_sha256'], hashlib.sha256(b'\1' * 768).hexdigest())
        self.assertNotIn('base', body)

    def test_results_round_trip_exactly_or_are_not_cached(self):
        result = ('progs/body/x.mdl', b'abc', 'layout', b'', {'a': [1, 2.5, None], 'b': 'c'})
        row, files = view.pack_result(result)
        self.assertEqual(files, {'0': b'abc', '1': b''})
        self.assertEqual(view.unpack_result(row, files), result)
        self.assertIsNone(view.pack_result(('p', b'x', {'tuple': (1, 2)})))   # would come back as a list
        cache = self.cache()
        cache.store_files({'entry': {'name': 'u'}}, row, files)
        self.assertEqual(view.unpack_result(*cache.load_unit({'entry': {'name': 'u'}})), result)
        self.assertEqual(pass_cache.list_units(self.root / 'cache')[0][:2], ('player-view', 'u'))

    def test_no_input_lock_no_cache(self):
        with patch.dict(os.environ, {pass_cache.ENV: str(self.root / 'cache')}), \
             patch('pass_cache.game_data_digest', return_value=None):
            self.assertIsNone(view._unit_cache())

    def test_one_pool_for_the_step(self):
        text = (ROOT / 'tools/prepare_player_view.py').read_text(encoding='utf-8')
        self.assertIn("with stage_pool(jobs, 'player view'):", text)
        self.assertEqual(text.count('ordered_map('), 0)                # every bake goes through run_units


if __name__ == '__main__':
    unittest.main()
