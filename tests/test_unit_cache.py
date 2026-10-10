# SPDX-License-Identifier: GPL-3.0-only
"""Resumable stage units (tools/pass_cache.py UnitCache; BUILD-IMAGE-NO-RESUME-33): a stage that failed
late, or runs again after a small change, takes its finished units from the cache and runs only the rest.
Outputs are byte-identical with the cache off, cold and warm; the key covers every input."""
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
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]
import pass_cache  # noqa: E402


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


class UnitCacheTests(unittest.TestCase):
    def unit(self, root, name='u', options=None, sources='s1', environment=None):
        return pass_cache.UnitCache(name, dict(options or {}, environment=environment or {}), sources, root)

    def test_round_trip_restores_every_file_and_the_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'out' / 'vf0001'
            (folder / 'sub').mkdir(parents=True)
            (folder / 'scene.bsp').write_bytes(b'bsp bytes')
            (folder / 'sub' / 'conversion.json').write_text('{"a": 1}\n')
            cache = self.unit(root / 'cache')
            cache.store_unit({'entry': 1}, {'name': 'vf0001', 'faces': 3}, folder)
            self.assertEqual(cache.restore_unit({'entry': 1}, root / 'again'), {'name': 'vf0001', 'faces': 3})
            self.assertEqual(tree(root / 'again'), tree(folder))
            self.assertIsNone(cache.restore_unit({'entry': 2}, root / 'other'))
            self.assertFalse((root / 'other').exists())          # a miss writes nothing
            with self.assertRaisesRegex(ValueError, 'not empty'):
                cache.restore_unit({'entry': 1}, folder)

    def test_key_covers_inputs_options_sources_and_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'f'
            folder.mkdir()
            (folder / 'x').write_bytes(b'x')
            setting = {'AMIWIND_STAIR_MITIGATION': 'a'}
            base = self.unit(root / 'c', options={'mode': 1}, environment=setting)
            base.store_unit({'in': 1}, {'ok': True}, folder)
            self.assertIsNotNone(base.load_unit({'in': 1}))
            for other in (self.unit(root / 'c', options={'mode': 2}, environment=setting),
                          self.unit(root / 'c', options={'mode': 1}, sources='s2', environment=setting),
                          self.unit(root / 'c', options={'mode': 1}, environment={'AMIWIND_STAIR_MITIGATION': 'b'}),
                          self.unit(root / 'c', name='v', options={'mode': 1}, environment=setting)):
                self.assertIsNone(other.load_unit({'in': 1}))
            self.assertIsNone(base.load_unit({'in': 2}))

    def test_damaged_or_missing_file_is_a_miss(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'f'
            folder.mkdir()
            (folder / 'a').write_bytes(b'aaa')
            cache = self.unit(root / 'c')
            cache.store_unit({'in': 1}, {}, folder)
            blob = next((root / 'c').rglob('*.bin'))
            blob.write_bytes(b'damaged')
            self.assertIsNone(cache.load_unit({'in': 1}))
            blob.unlink()
            self.assertIsNone(cache.load_unit({'in': 1}))

    def test_environment_ignores_the_scratch_folder_and_bookkeeping(self):
        script = ROOT / 'tools' / 'prepare_world_flora.py'
        with patch.dict(os.environ, {'AMIWIND_SCRATCH': '/run/a/scratch', 'AMIWIND_BUILD_JOBS': '7'}):
            first = pass_cache.environment(script)
        with patch.dict(os.environ, {'AMIWIND_SCRATCH': '/run/b/scratch', 'AMIWIND_BUILD_JOBS': '3'}):
            second = pass_cache.environment(script)
        self.assertEqual(first, second)
        self.assertNotIn('AMIWIND_SCRATCH', first)
        self.assertNotIn('AMIWIND_BUILD_JOBS', first)

    def test_off_means_no_cache(self):
        with patch.dict(os.environ, {pass_cache.ENV: 'off'}):
            self.assertIsNone(pass_cache.UnitCache.open('u', {}, __file__))


class FloraRegionResumeTests(unittest.TestCase):
    """World flora regions through the unit cache: identical stage outputs off, cold and warm; a warm run
    converts nothing; a changed owned input converts again."""

    def inputs(self, root):
        from test_world_flora_integration import packet_fixture, fixture, PALETTE, HASH
        flora = root / 'flora'
        flora.mkdir()
        _, index = packet_fixture(flora)
        index['master_sha256'] = HASH
        r = index['references'][0]
        asset = {'model': r['model'], 'sprite_asset_name': 'progs/aw_flora/f_' + 'a' * 16 + '.spr',
                 'source_xy_bake_center': [4, 4], 'pixel_bytes': 16}
        sprite = flora / asset['sprite_asset_name']
        sprite.parent.mkdir(parents=True)
        sprite.write_bytes(b'owned synthetic sprite')
        asset['sha256'] = hashlib.sha256(sprite.read_bytes()).hexdigest()
        palette = root / 'palette.lmp'
        palette.write_bytes(PALETTE)
        palhash = hashlib.sha256(PALETTE).hexdigest()
        receipt = {'placements': [r], 'assets': [asset], 'master_sha256': HASH, 'palette_sha256': palhash,
                   'selection': {'original_instances': 1}}
        (flora / 'tree-sprites.json').write_text(json.dumps(receipt))
        (flora / 'source/scenery-index.json').write_text(json.dumps(index))
        terrain, base = root / 'terrain', root / 'base'
        terrain.mkdir()
        base.mkdir()
        entry = {'name': 'vf0000', 'origin': [0, 0, 0], 'coverage': [[-100, -100], [100, 100]]}
        (terrain / 'world-regions.json').write_text(json.dumps({'master_sha256': HASH, 'regions': [entry]}))
        local = base / 'vf0000'
        local.mkdir()
        (local / 'scene.bsp').write_bytes(fixture(inline=True))
        (base / 'world-scenery.json').write_text(json.dumps(
            {'palette_sha256': palhash, 'regions': [{'name': 'vf0000', 'sha256': hashlib.sha256(
                (local / 'scene.bsp').read_bytes()).hexdigest()}]}))
        return terrain, base, flora, palette, sprite

    def test_off_cold_warm_identical_and_warm_converts_nothing(self):
        import prepare_world_flora
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            terrain, base, flora, palette, _ = self.inputs(root)
            outputs = {}
            for label, cache in (('off', 'off'), ('cold', str(root / 'cache')), ('warm', str(root / 'cache'))):
                guard = (patch.object(prepare_world_flora, 'convert_region', side_effect=AssertionError('converted'))
                         if label == 'warm' else contextlib.nullcontext())
                with patch.dict(os.environ, {pass_cache.ENV: cache}), guard:
                    prepare_world_flora.prepare(terrain, base, flora, palette, root / label, jobs=1,
                                                collision_packing='adaptive')
                outputs[label] = {k: v for k, v in tree(root / label).items() if k != 'world-flora.json'}
            self.assertEqual(outputs['off'], outputs['cold'])
            self.assertEqual(outputs['off'], outputs['warm'])
            self.assertTrue((root / 'cache' / 'world-flora-region').is_dir())

    def test_changed_owned_input_converts_again(self):
        import prepare_world_flora
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            terrain, base, flora, palette, sprite = self.inputs(root)
            with patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache')}):
                prepare_world_flora.prepare(terrain, base, flora, palette, root / 'one', jobs=1,
                                            collision_packing='adaptive')
                receipt = json.loads((flora / 'tree-sprites.json').read_text())
                sprite.write_bytes(b'another owned sprite')
                receipt['assets'][0]['sha256'] = hashlib.sha256(sprite.read_bytes()).hexdigest()
                (flora / 'tree-sprites.json').write_text(json.dumps(receipt))
                calls = []
                real = prepare_world_flora.convert_region
                with patch.object(prepare_world_flora, 'convert_region',
                                  side_effect=lambda task: calls.append(task) or real(task)):
                    prepare_world_flora.prepare(terrain, base, flora, palette, root / 'two', jobs=1,
                                                collision_packing='adaptive')
                self.assertEqual(len(calls), 1)


class SceneryRegionResumeTests(unittest.TestCase):
    def test_hit_restores_the_region_and_still_checks_the_terrain(self):
        import prepare_world_scenery
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            terrain, out = root / 'terrain', root / 'out'
            (terrain / 'vf0001').mkdir(parents=True)
            out.mkdir()
            source = terrain / 'vf0001' / 'scene.bsp'
            source.write_bytes(b'terrain')
            entry = {'name': 'vf0001', 'converted': {'sha256': hashlib.sha256(b'terrain').hexdigest()}}

            def convert(task):
                local = task[3] / task[4]['name']
                local.mkdir()
                (local / 'scene.bsp').write_bytes(b'overlaid')
                (local / 'conversion.json').write_text('{}\n')
                return {'name': 'vf0001', 'instances': 2, 'source_references': []}
            cache = pass_cache.UnitCache('world-scenery-region', {'environment': {}}, 's', root / 'cache')
            task = (terrain, root, root / 'palette', out, entry, cache, {'palette': 'p'})
            with patch.object(prepare_world_scenery, 'convert_region', side_effect=convert):
                first = prepare_world_scenery.convert_region_cached(task)
            (root / 'again').mkdir()
            moved = (terrain, root, root / 'palette', root / 'again', entry, cache, {'palette': 'p'})
            with patch.object(prepare_world_scenery, 'convert_region', side_effect=AssertionError('converted')):
                self.assertEqual(prepare_world_scenery.convert_region_cached(moved), first)
            self.assertEqual(tree(root / 'again'), tree(out))
            source.write_bytes(b'changed terrain')
            with self.assertRaisesRegex(ValueError, 'Retained terrain hash mismatch'):
                prepare_world_scenery.convert_region_cached(moved)


class ReleaseResumeSettingTests(unittest.TestCase):
    def test_release_builds_use_the_cache_only_with_release_reuse(self):
        for version in ('0.0.33', '0.0.33-rc1'):
            self.assertEqual(pass_cache.setting(version, '/w'), 'off')
            self.assertEqual(Path(pass_cache.setting(version, '/w', release_reuse=True)).parts[-2:],
                             ('cache', 'image-passes'))
        self.assertIn("pass_cache_setting(VERSION, args.workspace, getattr(args, 'allow_release_reuse', False))",
                      (ROOT / 'tools/build.py').read_text(encoding='utf-8'))


class StageOutputReproducibilityTests(unittest.TestCase):
    def test_world_survey_report_carries_no_wall_time(self):
        # BUILD-SURVEY-NOT-REPRODUCIBLE-33: summary.seconds made two runs of the same inputs differ, so the
        # stage never matched an earlier run and its dependents were refused reuse.
        import ast
        tree_ = ast.parse((ROOT / 'tools' / 'survey_vvardenfell.py').read_text(encoding='utf-8'))
        report = next(node.value for node in ast.walk(tree_) if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'report' for t in node.targets))
        names = {n.attr for n in ast.walk(report) if isinstance(n, ast.Attribute)}
        keywords = {k.arg for n in ast.walk(report) if isinstance(n, ast.Call) for k in n.keywords}
        self.assertNotIn('monotonic', names)
        self.assertNotIn('time', names)
        self.assertNotIn('seconds', keywords)


class ChimUnitCacheRefusalTests(unittest.TestCase):
    """BUILD-CACHE-OWNER-FAILS-STAGE-34: a cache entry that cannot be read or written never fails a stage."""

    def test_unwritable_cache_builds_locally_and_counts_the_refusal(self):
        from chim.units import UnitCache, run_units
        with tempfile.TemporaryDirectory() as tmp:
            cache = UnitCache(Path(tmp) / 'chim-units')
            output = io.StringIO()
            with patch('pathlib.Path.write_bytes', side_effect=PermissionError(13, 'Permission denied')),                     contextlib.redirect_stdout(output):
                results = run_units('frame', [('a' * 64, 2), ('b' * 64, 3)], lambda x: x * 10, 1, cache)
            self.assertEqual(results, [20, 30])
            self.assertEqual(cache.stats['frame']['write_refused'], 2)
            self.assertEqual(output.getvalue().count('cache write refused'), 1)
            self.assertEqual([p for p in Path(tmp).rglob('*') if p.is_file()], [])

    def test_unreadable_entry_is_a_miss(self):
        from chim.units import UnitCache
        with tempfile.TemporaryDirectory() as tmp:
            cache = UnitCache(Path(tmp))
            cache.put('frame', 'c' * 64, 7)
            with patch('pathlib.Path.read_bytes', side_effect=PermissionError(13, 'Permission denied')):
                self.assertIsNone(cache.get('frame', 'c' * 64))
            with patch('pathlib.Path.is_file', side_effect=PermissionError(13, 'Permission denied')):
                self.assertIsNone(cache.get('frame', 'c' * 64))
            self.assertEqual(cache.get('frame', 'c' * 64), 7)


if __name__ == '__main__':
    unittest.main()
