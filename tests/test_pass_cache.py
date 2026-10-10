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
                saved = json.loads((root / label / 'stair-walk.json').read_text())
                counts[label] = saved.pop('pass_cache', None)
                reports[label] = json.dumps(saved, indent=1)
                self.assertTrue(report['exempt_failures'])
            if label == 'warm':
                with patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache')}),                         patch.object(stair_walk, 'check_map', side_effect=AssertionError('checked again')):
                    stair_walk.check(root / 'warm', jobs=1, exempt=['room'])
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

if __name__ == '__main__':
    unittest.main()
