# SPDX-License-Identifier: GPL-3.0-only
"""Image-step per-map pass cache: byte-identical maps and receipts with and without it
(BUILD-IMAGE-NOT-INCREMENTAL-33); release builds never use it."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests')]
import pass_cache  # noqa: E402
from optimize_world_maps import optimize_maps  # noqa: E402
from hidden_surface_build import cull_staged_maps  # noqa: E402


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def without_cache_note(report):
    return {k: v for k, v in report.items() if k not in ('pass_cache', 'started_at', 'finished_at')}


class PassCacheTests(unittest.TestCase):
    def maps(self, root, maker):
        folder = Path(root)
        folder.mkdir(parents=True)
        for name, raw in maker().items():
            (folder / name).write_bytes(raw)
        return folder

    def optimizer_inputs(self):
        from test_share_bsp_geometry import repeated_geometry
        from share_bsp_geometry import share_geometry
        from deduplicate_bsp import deduplicate
        raw = repeated_geometry()
        done = deduplicate(share_geometry(raw)[0])[0]  # already optimized: left unchanged
        return {'a.bsp': raw, 'b.bsp': done, 'c.bsp': raw}

    def test_optimizer_maps_and_receipt_identical_cold_warm_and_off(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            results = {}
            for label, cache in (('off', 'off'), ('cold', str(root / 'cache')), ('warm', str(root / 'cache'))):
                maps = self.maps(root / label, self.optimizer_inputs)
                with patch.dict(os.environ, {pass_cache.ENV: cache}):
                    report = optimize_maps(maps, root / f'{label}.json', jobs=2)
                saved = json.loads((root / f'{label}.json').read_text())
                saved.pop('pass_cache', None)
                results[label] = (tree(maps), json.dumps(saved, indent=2), report)
            self.assertEqual(results['off'][0], results['cold'][0])
            self.assertEqual(results['off'][0], results['warm'][0])
            self.assertEqual(results['off'][1], results['cold'][1])
            self.assertEqual(results['off'][1], results['warm'][1])
            self.assertNotIn('pass_cache', results['off'][2])
            entries = list((root / 'cache' / 'optimize-world-maps').rglob('*.json'))
            self.assertEqual(len(entries), 2)  # two distinct inputs, a.bsp and c.bsp share one

    def test_warm_optimizer_does_not_prepare_again_and_a_damaged_entry_is_ignored(self):
        import optimize_world_maps
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                patch.dict(os.environ, {pass_cache.ENV: str(Path(temp) / 'cache')}):
            root = Path(temp)
            optimize_maps(self.maps(root / 'one', self.optimizer_inputs), root / 'one.json')
            with patch.object(optimize_world_maps, 'share_geometry', side_effect=AssertionError('prepared again')):
                optimize_maps(self.maps(root / 'two', self.optimizer_inputs), root / 'two.json')
            for blob in (root / 'cache').rglob('*.bin'):
                blob.write_bytes(b'damaged')
            three = optimize_maps(self.maps(root / 'three', self.optimizer_inputs), root / 'three.json')
            self.assertEqual(tree(root / 'one'), tree(root / 'three'))
            self.assertEqual(three['status'], 'verified')

    def test_source_change_misses(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {pass_cache.ENV: temp}):
            a = pass_cache.PassCache('p', {}, 'sources-1', temp)
            b = pass_cache.PassCache('p', {}, 'sources-2', temp)
            c = pass_cache.PassCache('p', {'enabled': False}, 'sources-1', temp)
            a.store('in', {'x': 1}, b'out')
            self.assertEqual(a.load('in'), ({'x': 1}, b'out'))
            self.assertIsNone(b.load('in'))
            self.assertIsNone(c.load('in'))
            self.assertIsNone(a.load('other'))

    def test_cull_maps_proofs_and_receipt_identical_cold_warm_and_off(self):
        from test_cull_bsp_hidden import fixture

        def inputs():
            return {'ext.bsp': fixture(), 'int.bsp': fixture(), 'ext2.bsp': fixture(second_without_shell=True)}
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            results = {}
            for label, cache in (('off', 'off'), ('cold', str(root / 'cache')), ('warm', str(root / 'cache'))):
                maps = self.maps(root / label / 'maps', inputs)
                with patch.dict(os.environ, {pass_cache.ENV: cache}):
                    cull_staged_maps(maps, root / label / 'work', {'ext', 'ext2'}, jobs=2)
                report = without_cache_note(json.loads((root / label / 'work' / 'hidden-surfaces.json').read_text()))
                proofs = tree(root / label / 'work' / 'proofs')
                results[label] = (tree(maps), json.dumps(report, indent=2), proofs)
            self.assertNotEqual(results['off'][0]['ext.bsp'], fixture())  # the cull did remove faces
            for label in ('cold', 'warm'):
                self.assertEqual(results['off'], results[label], label)

    def test_stair_walk_adopts_a_passed_runs_earlier_form_without_walking(self):
        """stair_records.adopt on legacy maps: the walks of a passed master build stored as rows only (the cache's
        earlier form, an older walker) become checked records; a stored walk today's walker does not give adopts
        nothing (BUILD-CHIM-STAIR-WALK-UNCACHED-36)."""
        import stair_records
        import stair_walk
        from test_stair_walk import build
        real = stair_records.walker_sources
        for tamper in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                old_root, cache = root / 'old-source', root / 'ws' / 'cache' / 'image-passes'
                run = root / 'ws' / 'build' / '2026_10_10_v0.0.36-dev3_full_3b5e7a9'
                id1 = run / 'image' / 'boot' / 'id1'
                (id1 / 'maps').mkdir(parents=True)
                (id1 / 'maps' / 'room.bsp').write_bytes(build(fill=True))
                (id1 / 'maps' / 'hall.bsp').write_bytes(build())
                (run / 'image' / 'stair-walk.json').write_text('{}', encoding='utf-8')
                (run / 'build-state.json').write_text(json.dumps({'status': 'passed'}), encoding='utf-8')
                result = root / 'aw-result.json'
                result.write_text(json.dumps({'run_name': run.name, 'request_id': 'req-9', 'kind': 'build',
                                              'status': 'passed', 'commit': '3b5e7a9', 'version': 'v0.0.36-dev3'}))
                options = {'stair_mode': __import__('mesh_geometry_env').stair_mode(),
                           'models': hashlib.sha256(json.dumps({}, sort_keys=True).encode()).hexdigest()}
                old = pass_cache.PassCache('stair-walk', options, 'e' * 64, cache)
                for path in sorted((id1 / 'maps').glob('*.bsp')):
                    rows = json.loads(json.dumps(stair_walk.check_map((str(path), None, {}, 'all'))[1]))
                    if tamper and path.stem == 'hall':
                        rows[0] = dict(rows[0], result='failed' if rows[0]['result'] != 'failed' else 'passed')
                    old.store(hashlib.sha256(path.read_bytes()).hexdigest() + ':null', {'rows': rows})
                with patch.object(stair_records, 'walker_sources', side_effect=lambda r, script: (
                        ('e' * 64, {}) if Path(r) == old_root else real(r, script))):
                    done = stair_records.adopt(run, 'req-9', result, old_root, cache, sample=2)
                self.assertEqual(done['parts']['legacy maps']['found'], 2)
                if tamper:
                    self.assertIn('differ', done['refused'])
                    self.assertEqual(done['adopted'], 0)
                    continue
                self.assertEqual((done['refused'], done['adopted']), (None, 2), done)
                with patch.dict(os.environ, {pass_cache.ENV: str(cache), stair_walk.WALK_SAMPLE_ENV: '0'}), \
                        patch.object(stair_walk, 'check_map', side_effect=AssertionError('walked again')):
                    report = stair_walk.check(id1, jobs=1, exempt=['room'])
                self.assertTrue(all(how.startswith('reused from %s (0.0.36-dev3, 3b5e7a9, ' % run.name)
                                    for how in report['pass_cache']['maps'].values()), report['pass_cache']['maps'])

    def test_stair_walk_report_identical_cold_warm_and_off(self):
        import stair_walk
        from test_stair_walk import build
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports, counts = {}, {}
            for label, cache in (('off', 'off'), ('cold', str(root / 'cache')), ('warm', str(root / 'cache'))):
                maps = root / label / 'maps'
                maps.mkdir(parents=True)
                (maps / 'room.bsp').write_bytes(build(fill=True))
                (maps / 'hall.bsp').write_bytes(build())
                with patch.dict(os.environ, {pass_cache.ENV: cache}):
                    report = stair_walk.require(root / label, root / label / 'stair-walk.json', jobs=2, exempt=['room'])
                if label == 'cold':
                    # the cold run passed: its stair-walk records become reusable (tools/stair_records.py)
                    import stair_records
                    self.assertEqual(stair_records.promote(root / label)['marked'], 2)
                saved = json.loads((root / label / 'stair-walk.json').read_text())
                counts[label] = saved.pop('pass_cache', None)
                if counts[label]:
                    counts[label].pop('walked_again', None)
                reports[label] = json.dumps(saved, indent=1)
                self.assertTrue(report['exempt_failures'])
            if label == 'warm':
                with patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache'), stair_walk.WALK_SAMPLE_ENV: '0'}),                         patch.object(stair_walk, 'check_map', side_effect=AssertionError('checked again')):
                    stair_walk.check(root / 'warm', jobs=1, exempt=['room'])
                # with the check sample, a reused map is walked again and must match (BUILD-CHIM-STAIR-WALK-UNCACHED-36)
                with patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache'), stair_walk.WALK_SAMPLE_ENV: '1'}):
                    sampled = stair_walk.check(root / 'warm', jobs=1, exempt=['room'])
                self.assertEqual(len(sampled['pass_cache']['walked_again']), 1)
            self.assertEqual(reports['off'], reports['cold'])
            self.assertEqual(reports['off'], reports['warm'])
            # The receipt counts the pass cache's hits (owner decision 9 October 2026).
            self.assertIsNone(counts['off'])
            self.assertEqual((counts['cold']['hits'], counts['cold']['misses']), (0, 2))
            self.assertEqual((counts['warm']['hits'], counts['warm']['misses']), (2, 0))
            self.assertFalse(list((root / 'cache' / '.tally').glob('*/*')))  # nothing left behind

    def test_exterior_sky_maps_and_receipt_identical_cold_warm_and_off(self):
        # BUILD-IMAGE-NO-RESUME-33: the sky pass is a per-map unit too.
        import exterior_sky_build
        from test_exterior_sky_build import sky_fixture
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            results = {}
            for label, cache in (('off', 'off'), ('cold', str(root / 'cache')), ('warm', str(root / 'cache'))):
                maps = root / label / 'id1' / 'maps'
                maps.mkdir(parents=True)
                for name in ('outside', 'inside', 'unknown'):
                    (maps / (name + '.bsp')).write_bytes(sky_fixture())
                guard = (patch.object(exterior_sky_build, 'transform', side_effect=AssertionError('transformed again'))
                         if label == 'warm' else contextlib.nullcontext())
                with patch.dict(os.environ, {pass_cache.ENV: cache}), guard:
                    exterior_sky_build.configure_staged_maps(root / label / 'id1', exterior_maps=['outside'],
                                                             interior_maps=['inside'], work_dir=root / label / 'work')
                results[label] = (tree(root / label / 'id1'), tree(root / label / 'work'))
            self.assertNotEqual(results['off'][0]['maps/outside.bsp'], sky_fixture())
            for label in ('cold', 'warm'):
                self.assertEqual(results['off'], results[label], label)

    def test_release_builds_turn_the_cache_off(self):
        for version in ('0.0.33', '0.0.33-rc1', '0.0.33-rc12'):
            self.assertEqual(pass_cache.setting(version, '/w'), 'off', version)
        self.assertEqual(Path(pass_cache.setting('0.0.33-dev1', '/w')).parts[-2:], ('cache', 'image-passes'))
        self.assertIn("pass_cache_setting(VERSION, args.workspace, getattr(args, 'allow_release_reuse', False))",
                      (ROOT / 'tools/build.py').read_text(encoding='utf-8'))
        with patch.dict(os.environ, {pass_cache.ENV: 'off'}):
            self.assertIsNone(pass_cache.folder())
            self.assertIsNone(pass_cache.PassCache.open('p', {}, __file__))


HELPER = """def shared(x):
    return x + 1


def unused():
    return 0
"""
PASS_A = """import helper
LIMIT = 3


def worker(x):
    return helper.shared(x) * LIMIT


def rebind(x):
    return x


def main():
    print(rebind(worker(1)))


if __name__ == "__main__":
    main()
"""


class PassKeyTests(unittest.TestCase):
    """A per-map pass's key covers only the code its worker reaches: an edit elsewhere in the image tools keeps
    every recorded map; an edit to the worker or to what it calls rekeys it."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        self.write('helper.py', HELPER)
        self.write('pass_a.py', PASS_A)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        (self.root / 'tools' / name).write_text(text, encoding='utf-8')

    def digest(self):
        import build_cache
        index = build_cache.SourceIndex(self.root)
        return index.entry_digest(self.root / 'tools' / 'pass_a.py', 'worker'), index.digest(self.root / 'tools' / 'pass_a.py')

    def test_unrelated_edit_keeps_the_key(self):
        (entry, whole) = self.digest()
        self.assertFalse(entry[2])
        self.write('pass_a.py', (self.root / 'tools/pass_a.py').read_text().replace('return x\n', 'return x + 0\n'))
        self.write('helper.py', (self.root / 'tools/helper.py').read_text().replace('return 0', 'return 7'))
        entry2, whole2 = self.digest()
        self.assertEqual(entry[0], entry2[0])            # the worker's key is unchanged
        self.assertNotEqual(whole[0], whole2[0])          # the whole tool's key (the old method) changed

    def test_worker_or_callee_edit_rekeys(self):
        entry = self.digest()[0]
        self.write('helper.py', (self.root / 'tools/helper.py').read_text().replace('x + 1', 'x + 2'))
        callee = self.digest()[0]
        self.assertNotEqual(entry[0], callee[0])
        self.write('pass_a.py', (self.root / 'tools/pass_a.py').read_text().replace('LIMIT = 3', 'LIMIT = 4'))
        self.assertNotEqual(callee[0], self.digest()[0][0])

    def test_unknown_worker_refused(self):
        import build_cache
        with self.assertRaises(ValueError):
            build_cache.SourceIndex(self.root).entry_digest(self.root / 'tools' / 'pass_a.py', 'nothing')

    def test_real_passes_name_their_workers(self):
        import build_cache
        index = build_cache.SourceIndex()
        for script, function in (('optimize_world_maps.py', 'prepare_candidate'), ('exterior_sky_build.py', '_sky_map'),
                                 ('chim/frame_map.py', '_region_map'),
                                 ('prepare_guard_torches.py', '_convert_guard')):
            value, files, uncertain = index.entry_digest(ROOT / 'tools' / script, function)
            self.assertFalse(uncertain, script)
        # the optimizer's worker does not reach the CHIM rebind (an edit there keeps every optimized map)
        index.entry_digest(ROOT / 'tools' / 'optimize_world_maps.py', 'prepare_candidate')
        key = '%s::prepare_candidate' % (ROOT / 'tools' / 'optimize_world_maps.py').resolve()
        self.assertNotIn('rebind_chim_maps', index._reached[key].get('tools/optimize_world_maps.py', set()))
        # Classes run on import and are hashed in <top>, not separate units.
        # Verify the reached unit here and actual rekeying below.
        key = '%s::_convert_guard' % (ROOT / 'tools' / 'prepare_guard_torches.py').resolve()
        self.assertIn('<top>', index._reached[key].get('tools/npc_anim.py', set()))

    def test_guard_worker_rekeys_when_shared_bone_layer_changes(self):
        import build_cache
        for name in ('prepare_guard_torches.py', 'npc_anim.py'):
            self.write(name, (ROOT / 'tools' / name).read_text(encoding='utf-8'))
        script = self.root / 'tools/prepare_guard_torches.py'
        before, _, uncertain = build_cache.SourceIndex(self.root).entry_digest(script, '_convert_guard')
        self.assertFalse(uncertain)
        animation = (self.root / 'tools/npc_anim.py').read_text(encoding='utf-8')
        line = 'self.mask[name] = name in roots or inherited'
        self.assertEqual(animation.count(line), 1)
        self.write('npc_anim.py', animation.replace(line, 'self.mask[name] = name in roots and inherited'))
        after, _, uncertain = build_cache.SourceIndex(self.root).entry_digest(script, '_convert_guard')
        self.assertFalse(uncertain)
        self.assertNotEqual(before, after)

CACHE_MODULE = """def source_digest(*scripts):
    return 'key'
"""
PASS_B = """import helper
import pass_cache


def worker(x):
    return helper.shared(x)


def main():
    print(pass_cache.source_digest(__file__), worker(1))


if __name__ == "__main__":
    main()
"""


class PassKeyFormTests(unittest.TestCase):
    """BUILD-PASS-KEY-OVERBROAD-36: a new function in a shared module and an edit to the cache's own key code keep
    every pass and unit key; a result recorded under the older key form is found, verified and recorded again."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        for name, text in (('helper.py', HELPER), ('pass_cache.py', CACHE_MODULE), ('pass_b.py', PASS_B)):
            (self.root / 'tools' / name).write_text(text, encoding='utf-8', newline='\n')
        self.patch = patch.multiple(pass_cache, ROOT=self.root, _DIGESTS={})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def keys(self):
        pass_cache._DIGESTS.clear()
        script = self.root / 'tools' / 'pass_b.py'
        return (pass_cache.source_digest(script), pass_cache.source_digest((script, 'worker')),
                pass_cache.source_digest(script, form=1))

    def edit(self, name, old, new):
        path = self.root / 'tools' / name
        path.write_text(path.read_text(encoding='utf-8').replace(old, new), encoding='utf-8', newline='\n')

    def test_new_function_in_a_shared_module_keeps_the_key(self):
        whole, worker, old_form = self.keys()
        self.edit('helper.py', 'def unused():', 'def added(path, mode=0o644):\n    return path\n\n\ndef unused():')
        whole2, worker2, old_form2 = self.keys()
        self.assertEqual((whole, worker), (whole2, worker2))
        self.assertNotEqual(old_form, old_form2)  # what rekeyed every character head preview (Vivec try3)

    def test_cache_key_code_edit_keeps_the_key(self):
        whole, worker, old_form = self.keys()
        self.edit('pass_cache.py', "return 'key'", "return 'key, now with provenance'")
        whole2, worker2, old_form2 = self.keys()
        self.assertEqual((whole, worker), (whole2, worker2))
        self.assertNotEqual(old_form, old_form2)

    def test_reached_code_edit_still_rekeys(self):
        whole, worker, _ = self.keys()
        self.edit('helper.py', 'x + 1', 'x + 2')
        whole2, worker2, _ = self.keys()
        self.assertNotEqual(whole, whole2)
        self.assertNotEqual(worker, worker2)

    def test_older_key_form_found_verified_and_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            pass_cache.PassCache('p', {}, 'form-1', temp).store('in', {'x': 1}, b'out')
            current = pass_cache.PassCache('p', {}, 'form-2', temp, previous=('form-1',))
            self.assertEqual(current.load('in'), ({'x': 1}, b'out'))
            self.assertEqual(pass_cache.PassCache('p', {}, 'form-2', temp).load('in'), ({'x': 1}, b'out'))
            # a damaged older entry is a miss, never a wrong result
            pass_cache.PassCache('p', {}, 'form-1', temp).store('bad', {'x': 2}, b'good')
            blob = pass_cache.PassCache('p', {}, 'form-1', temp)._paths('bad')[1]
            blob.write_bytes(b'damaged')
            self.assertIsNone(pass_cache.PassCache('p', {}, 'form-2', temp, previous=('form-1',)).load('bad'))

    def test_an_earlier_trees_walks_are_read_in_its_own_key_form(self):
        import stair_records
        script = self.root / 'tools' / 'pass_b.py'
        self.assertEqual(stair_records.walker_sources(self.root, 'tools/pass_b.py')[0],
                         pass_cache.source_digest(script, form=1))       # its pass_cache.py has no PASS_KEY_FORM
        self.edit('pass_cache.py', "return 'key'", "return 'key'" + chr(10) + chr(10) + chr(10) + 'PASS_KEY_FORM = 2')
        self.assertEqual(stair_records.walker_sources(self.root, 'tools/pass_b.py')[0], self.keys()[0])

    def test_previous_digests_name_the_older_form(self):
        script = self.root / 'tools' / 'pass_b.py'
        self.assertEqual(pass_cache.previous_digests(script), (pass_cache.source_digest(script, form=1),))

if __name__ == '__main__':
    unittest.main()
