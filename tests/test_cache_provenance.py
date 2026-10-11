# SPDX-License-Identifier: GPL-3.0-only
"""Cache provenance (CACHE-NO-PROVENANCE-36): every cache writer records who, when, which version and the output
SHA-256; payloads stay byte-identical; old entries without provenance still reuse; no key changes."""
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests')]
import build_cache  # noqa: E402
import cache_provenance as cp  # noqa: E402
import file_cache  # noqa: E402
import pass_cache  # noqa: E402

RUN = {'AMIWIND_RUN_NAME': '2026_10_11_v0.0.36-dev3_full_6891f7a', 'AMIWIND_RUN_COMMIT': '6891f7a',
       'AMIWIND_RUN_VERSION': '0.0.36-dev3', 'AMIWIND_AW_REQUEST': 'req-1', 'AMIWIND_RUN_JOB': 'cache-provenance',
       'AMIWIND_RUN_TOOLS_SHA256': 'ab' * 32, 'AMIWIND_RUN_CHIM_VERSION': '0.3.0', 'AMIWIND_RUN_WORLD_FORMAT': '0.7'}
REQUIRED = ('schema', 'cache', 'key', 'output_sha256', 'output_kind', 'input_manifest', 'created_at',
            'amiwind_version', 'commit', 'run', 'request', 'job', 'tools_sha256', 'chim_version', 'world_format',
            'retention', 'sources')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, RUN)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def assertComplete(self, record):
        self.assertIsNotNone(record)
        for field in REQUIRED:
            self.assertIn(field, record, field)
        self.assertEqual(record['schema'], cp.SCHEMA)
        self.assertTrue(record['output_sha256'])
        self.assertRegex(record['output_sha256'], '^[0-9a-f]{64}$')
        self.assertEqual(record['amiwind_version'], '0.0.36-dev3')
        self.assertEqual(record['commit'], '6891f7a')
        self.assertEqual(record['run'], RUN['AMIWIND_RUN_NAME'])
        self.assertEqual(record['job'], 'cache-provenance')
        self.assertEqual(record['retention']['class'], 'dev')
        self.assertRegex(record['created_at'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$')
        self.assertEqual(record['input_manifest']['sha256'],
                         cp.sha256_of({k: v for k, v in record['input_manifest'].items() if k != 'sha256'}))


class KeysUnchanged(unittest.TestCase):
    """Provenance statements never change a key (owner order 2026-10-11: nothing is redone)."""

    PLAIN = ('import json\n\n\ndef store(meta, path):\n    meta = dict(meta)\n'
             '    path.write_text(json.dumps(meta))\n    return meta\n\n\nclass Cache:\n'
             '    def put(self, meta):\n        meta["a"] = 1\n        return meta\n')
    WITH = ('import json\n\n\ndef store(meta, path):\n    meta = dict(meta)\n    import cache_provenance\n'
            '    cache_provenance.attach_pass(meta, None, "image-passes/x", "k", {}, "s")\n'
            '    path.write_text(json.dumps(meta))\n    return meta\n\n\nclass Cache:\n'
            '    def put(self, meta):\n        meta["a"] = 1\n        import cache_provenance\n'
            '        cache_provenance.reused(None, "x",\n                               "k")\n        return meta\n')

    def test_strip_removes_only_provenance_statements(self):
        self.assertEqual(build_cache.strip_provenance(self.PLAIN), self.PLAIN)
        self.assertEqual(build_cache.strip_provenance(self.WITH), self.PLAIN)

    def test_statement_sharing_a_line_or_a_whole_block_stays(self):
        shared = 'def f(x):\n    x = 1; cache_provenance.reused(None, "x", "k")\n    return x\n'
        self.assertEqual(build_cache.strip_provenance(shared), shared)
        alone = 'def f(x):\n    if x:\n        cache_provenance.reused(None, "x", "k")\n    return x\n'
        self.assertEqual(build_cache.strip_provenance(alone), alone)
        assigned = 'def f(x):\n    y = cache_provenance.make("c", "k", "0" * 64, "row")\n    return y\n'
        self.assertEqual(build_cache.strip_provenance(assigned), assigned)

    def test_same_inputs_same_key_before_and_after_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            digests = []
            for text in (self.PLAIN, self.WITH):
                root = Path(temp) / str(len(digests))
                (root / 'tools').mkdir(parents=True)
                (root / 'tools' / 'writer.py').write_text(text, newline='\n')
                (root / 'tools' / 'stage.py').write_text(
                    'import writer\nfrom pathlib import Path\n\nwriter.store({}, Path("x"))\n'
                    'writer.Cache().put({})\n', newline='\n')
                index = build_cache.SourceIndex(root)
                digests.append(index.digest((root / 'tools' / 'stage.py').resolve()))
            self.assertEqual(digests[0], digests[1])

    def test_the_cache_writers_carry_provenance_statements_only(self):
        """Every writer module is hooked, and with its provenance statements removed its key text equals the
        same module without any mention of the module (nothing else changed around them)."""
        for relative in ('tools/pass_cache.py', 'tools/file_cache.py', 'tools/chim/units.py',
                         'tools/prepare_world_regions.py', 'tools/storage_pool.py', 'tools/chimport.py'):
            text = (ROOT / relative).read_text(encoding='utf-8')
            self.assertIn('cache_provenance.', text, relative)
            self.assertNotIn(cp.PROVENANCE_MODULE if hasattr(cp, 'PROVENANCE_MODULE') else 'cache_provenance.',
                             build_cache.strip_provenance(text), relative)

    def test_provenance_module_is_output_neutral(self):
        self.assertIn('tools/cache_provenance.py', build_cache.INSTRUMENTATION_MODULES)
        for var in cp.RUN_ENV.values():
            self.assertIn(var, build_cache.IGNORED_ENV, var)
        source = (ROOT / 'tools' / 'cache_provenance.py').read_text(encoding='utf-8')
        # It reads no repository file and calls no repository module during builds (read/call traces).
        for module in ('project_version', 'file_cache', 'pass_cache', 'build_cache'):
            self.assertNotIn(f'import {module}', source)


class PassCacheProvenance(Base):
    def cache(self, name='optimize-world-maps'):
        with patch.dict(os.environ, {pass_cache.ENV: str(self.root / 'passes')}):
            return pass_cache.PassCache(name, {'opt': 1}, 'src' * 21 + 's', self.root / 'passes')

    def test_store_records_every_field_and_output_never_null(self):
        cache = self.cache()
        cache.store('11' * 32, {'map': 'a'}, b'new bytes')
        cache.store('22' * 32, {'map': 'b'}, None)
        for digest, expected in (('11' * 32, sha(b'new bytes')), ('22' * 32, cp.sha256_of({'map': 'b'}))):
            meta_path, _ = cache._paths(digest)
            record = json.loads(meta_path.read_text())['provenance']
            self.assertComplete(record)
            self.assertEqual(record['output_sha256'], expected)
            self.assertEqual(record['key'], cache.key(digest))
            self.assertEqual(record['input_manifest']['inputs'][0]['sha256'], digest)
            found, where = cp.lookup(meta_path)
            self.assertEqual((found, where), (record, 'inline'))

    def test_payload_bytes_identical_with_and_without_provenance(self):
        cache = self.cache()
        cache.store('11' * 32, {'map': 'a'}, b'new bytes')
        _, blob = cache._paths('11' * 32)
        with_provenance = sha(blob.read_bytes())
        meta_path, _ = cache._paths('11' * 32)
        meta = json.loads(meta_path.read_text())
        meta.pop('provenance')
        self.assertEqual(with_provenance, sha(b'new bytes'))
        self.assertEqual(cache.load('11' * 32), ({'map': 'a'}, b'new bytes'))
        meta_path.write_text(json.dumps(meta) + '\n')  # an entry written before provenance existed
        self.assertEqual(cache.load('11' * 32), ({'map': 'a'}, b'new bytes'))

    def test_failed_output_check_is_a_miss_never_a_failure(self):
        cache = self.cache('stair-walk')
        cache.store('33' * 32, {'rows': [1, 2]}, None)
        meta_path, _ = cache._paths('33' * 32)
        meta = json.loads(meta_path.read_text())
        meta['row'] = {'rows': [1, 3]}  # damaged row, provenance names the old one
        meta_path.write_text(json.dumps(meta) + '\n')
        self.assertIsNone(cache.load('33' * 32))

    def test_unit_cache_files_output(self):
        folder = self.root / 'unit'
        (folder / 'sub').mkdir(parents=True)
        (folder / 'sub' / 'a.txt').write_bytes(b'A')
        with patch.dict(os.environ, {pass_cache.ENV: str(self.root / 'passes')}):
            units = pass_cache.UnitCache('region', {'o': 1}, 'x' * 64, self.root / 'passes')
            units.store_unit({'entry': {'map': 'r1'}}, {'ok': True}, folder)
            meta_path, _ = units._paths(pass_cache.input_digest({'entry': {'map': 'r1'}}))
            record = json.loads(meta_path.read_text())['provenance']
            self.assertComplete(record)
            self.assertEqual(record['output_kind'], 'files')
            self.assertEqual(record['output_sha256'], cp.files_digest({'sub/a.txt': sha(b'A')}))
            self.assertEqual(record['input_manifest']['unit'], 'r1')
            target = self.root / 'restored'
            self.assertEqual(units.restore_unit({'entry': {'map': 'r1'}}, target), {'ok': True})

    def test_reuse_is_logged_and_counted(self):
        cache = self.cache()
        cache.store('11' * 32, {'map': 'a'}, None)
        cache.load('11' * 32)
        cache.load('11' * 32)
        cache.load('44' * 32)  # a miss is not a reuse
        counts, last = cp.reuse_counts(self.root / 'passes')
        self.assertEqual(counts, {cache.key('11' * 32): 2})
        shown = cp.show(str(cache._paths('11' * 32)[0]), self.root / 'passes')
        self.assertEqual(shown['reuse_count'], 2)
        self.assertEqual(shown['provenance']['run'], RUN['AMIWIND_RUN_NAME'])


class RealPassWrites(Base):
    """Every pass names its unit and its inputs one by one (the reuse audit names the changed input)."""

    def test_optimizer_pass_records_map_name_and_inputs(self):
        import contextlib
        import io
        from test_pass_cache import PassCacheTests
        from optimize_world_maps import optimize_maps
        helper = PassCacheTests()
        cache_dir = self.root / 'cache'
        maps = helper.maps(self.root / 'maps', helper.optimizer_inputs)
        with patch.dict(os.environ, {pass_cache.ENV: str(cache_dir)}), contextlib.redirect_stdout(io.StringIO()):
            optimize_maps(maps, self.root / 'report.json', jobs=1)
        records = [json.loads(path.read_text())['provenance']
                   for path in (cache_dir / 'optimize-world-maps').rglob('*.json')]
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertComplete(record)
            manifest = record['input_manifest']
            self.assertIn(manifest['unit'], ('a.bsp', 'b.bsp', 'c.bsp'))
            names = [row['name'] for row in manifest['inputs']]
            self.assertEqual(names, ['input', 'map bytes', 'pass sources', 'pass options'])
            self.assertTrue(all(row['sha256'] for row in manifest['inputs']))

    def test_changed_input_is_named(self):
        cache = pass_cache.PassCache('chim-zone-walk', {'unit': 'frame route'}, 's' * 64, self.root / 'p')
        records = []
        for positions in ([[0, 0]], [[0, 0], [64, 0]]):
            key = cp.sha256_of(positions)
            cp.name_unit(cache, key, 'route frames/x+00/y+00', [('frame', {'cell': [0, 0]}), ('positions', positions)])
            cache.store(key, {'holes': 0})
            records.append(json.loads(cache._paths(key)[0].read_text())['provenance'])
        self.assertEqual({r['input_manifest']['unit'] for r in records}, {'route frames/x+00/y+00'})
        before = {row['name']: row['sha256'] for row in records[0]['input_manifest']['inputs']}
        after = {row['name']: row['sha256'] for row in records[1]['input_manifest']['inputs']}
        self.assertEqual(sorted(name for name in before if before[name] != after[name]), ['input', 'positions'])

    def test_unit_cache_names_label_and_inputs(self):
        folder = self.root / 'unit'
        folder.mkdir()
        (folder / 'a').write_bytes(b'A')
        units = pass_cache.UnitCache('town-region', {}, 'x' * 64, self.root / 'p')
        inputs = {'entry': {'map': 'bm019'}, 'terrain': 'cd' * 32}
        units.store_unit(inputs, {'ok': 1}, folder)
        record = json.loads(units._paths(pass_cache.input_digest(inputs))[0].read_text())['provenance']
        self.assertEqual(record['input_manifest']['unit'], 'bm019')
        self.assertIn('terrain', [row['name'] for row in record['input_manifest']['inputs']])

    def test_a_failing_name_never_reaches_the_pass(self):
        cache = pass_cache.PassCache('x', {}, 's' * 64, self.root / 'p')
        cp.name_unit(cache, 'k', lambda: 'route %s' % [0, 0], lambda: 1 / 0)  # both raise inside: no record
        cache.store('k', {'a': 1})
        record = json.loads(cache._paths('k')[0].read_text())['provenance']
        self.assertComplete(record)
        self.assertIsNone(record['input_manifest']['unit'])

    def test_every_hook_hands_functions(self):
        import re
        for relative in ('tools/optimize_world_maps.py', 'tools/hidden_surface_build.py', 'tools/exterior_sky_build.py',
                         'tools/chim/frame_map.py', 'tools/chim/collision.py', 'tools/stair_walk.py',
                         'tools/chim/validate.py', 'tools/chim/zone_sim.py', 'tools/prepare_character.py',
                         'tools/pass_cache.py'):
            for line in (ROOT / relative).read_text(encoding='utf-8').splitlines():
                if 'cache_provenance.name_unit(' in line:
                    self.assertRegex(line, r'name_unit\(.*, lambda: .*, lambda: ', relative)

    def test_stair_frame_inputs_name_every_part(self):
        frame_row = ('frames/x+00/y+00/frame.ccf', {'cell': [0, 0]},
                     [{'cx': 0, 'cy': 0, 'image': b'T', 'owned': [{'model': 0}], 'reach': []}])
        names = [name for name, _ in cp.stair_frame_inputs(frame_row, [{'image': b'M'}])]
        self.assertEqual(names, ['frame', 'chunk 0,0 terrain', 'chunk 0,0 placements', 'model 0'])
        self.assertIsNone(cp.stair_frame_inputs(None, None))  # never raises in a pass

    def test_every_pass_writer_names_its_unit(self):
        for relative in ('tools/optimize_world_maps.py', 'tools/hidden_surface_build.py', 'tools/exterior_sky_build.py',
                         'tools/chim/frame_map.py', 'tools/chim/collision.py', 'tools/stair_walk.py',
                         'tools/chim/validate.py', 'tools/chim/zone_sim.py', 'tools/prepare_character.py',
                         'tools/pass_cache.py'):
            text = (ROOT / relative).read_text(encoding='utf-8')
            self.assertIn('cache_provenance.name_unit(', text, relative)
            self.assertNotIn('cache_provenance.', build_cache.strip_provenance(text), relative)


class AssetPoolProvenance(Base):
    def test_store_and_point_record_inputs(self):
        source = self.root / 'converted.bin'
        source.write_bytes(b'converted')
        cache = file_cache.FileCache(self.root / 'pool', 'textures', {'code': 'c'})
        key = cache.key('aa' * 32, {'mode': 1})
        self.assertTrue(cache.store(key, source, {'w': 1}))
        meta_path = cache._key_path(key)
        meta = json.loads(meta_path.read_text())
        record = meta['provenance']
        self.assertComplete(record)
        self.assertEqual(record['output_sha256'], sha(b'converted'))
        self.assertEqual(record['input_manifest']['inputs'][0]['sha256'], 'aa' * 32)
        self.assertEqual(record['cache'], 'pool/keys/textures')
        self.assertEqual(sha(cache.object_path(sha(b'converted')).read_bytes()), sha(b'converted'))
        # point(): sidecar beside the key, no 'sha256' field (the GC reads keys/*.json for 'sha256').
        key2 = cache.key('bb' * 32, {'mode': 1})
        self.assertTrue(cache.point(key2, sha(b'converted'), 9))
        sidecar = cp.read_sidecar(cache._key_path(key2))
        self.assertComplete(sidecar)
        self.assertNotIn('sha256', sidecar)
        self.assertEqual(json.loads(cache._key_path(key2).read_text())['sha256'], sha(b'converted'))
        # reuse
        self.assertEqual(cache.fetch(key, self.root / 'out.bin'), {'w': 1})
        self.assertEqual(cp.reuse_counts(self.root / 'pool')[0], {key: 1})

    def test_old_key_without_provenance_still_reused(self):
        source = self.root / 'converted.bin'
        source.write_bytes(b'converted')
        cache = file_cache.FileCache(self.root / 'pool', 'textures', {'code': 'c'})
        key = cache.key('aa' * 32, {'mode': 1})
        cache.store(key, source)
        meta = json.loads(cache._key_path(key).read_text())
        meta.pop('provenance')
        cache._key_path(key).write_text(json.dumps(meta) + '\n')
        self.assertEqual(cache.fetch(key, self.root / 'out.bin'), {})
        self.assertEqual((self.root / 'out.bin').read_bytes(), b'converted')


class ChimUnitProvenance(Base):
    def test_sidecar_payload_identical_verify_and_old_entries(self):
        from chim.units import UnitCache, fingerprint
        cache = UnitCache(self.root / 'chim-units')
        fp = fingerprint('pvs', {'cells': [1, 2]})
        cache.put('pvs', fp, {'rows': [7]})
        path = cache._path('pvs', fp)
        self.assertEqual(path.read_bytes(), pickle.dumps((fp, {'rows': [7]}), protocol=4))
        record = cp.read_sidecar(path)
        self.assertComplete(record)
        self.assertEqual(record['output_sha256'], sha(path.read_bytes()))
        self.assertEqual(record['input_manifest']['inputs'][0]['name'], 'tools')
        self.assertEqual(cp.lookup(path), (record, 'sidecar'))
        self.assertEqual(cache.get('pvs', fp), {'rows': [7]})
        # a sidecar naming other bytes: a miss (rebuilt), counted as damaged
        cp.write_sidecar(path, dict(record, output_sha256='0' * 64))
        self.assertIsNone(cache.get('pvs', fp))
        self.assertEqual(cache.stats['pvs']['damaged'], 1)
        # no sidecar (written before 2026-10-11): reused
        cp.sidecar_path(path).unlink()
        self.assertEqual(cache.get('pvs', fp), {'rows': [7]})


class WorldTerrainProvenance(Base):
    def test_store_records_tree_and_lookup_restores(self):
        import prepare_world_regions as pwr
        root = self.root / 'run' / 'r1'
        root.mkdir(parents=True)
        (root / 'scene.bsp').write_bytes(b'BSP')
        (root / 'compile.log').write_text('log')
        result = {'name': 'r1', 'converted': {'sha256': sha(b'BSP')}, 'input_sha256': 'cc' * 32, 'storage': {}}
        cache = self.root / 'world-terrain-v1'
        unit = 'dd' * 32
        pwr.unit_cache_store(cache, unit, root, result)
        record = json.loads((pwr.unit_cache_folder(cache, unit) / 'conversion.json').read_text())['provenance']
        self.assertComplete(record)
        self.assertEqual(record['output_kind'], 'files')
        self.assertEqual(record['input_manifest']['unit'], 'r1')
        self.assertEqual(sha((pwr.unit_cache_folder(cache, unit) / 'scene.bsp').read_bytes()), sha(b'BSP'))
        target = self.root / 'run2'
        target.mkdir()
        found = pwr.unit_cache_lookup(cache, unit, target, {'name': 'r1'}, 'cc' * 32)
        self.assertNotIn('provenance', found)  # the run's own conversion.json stays as before
        self.assertNotIn('provenance', json.loads((target / 'conversion.json').read_text()))
        self.assertEqual(cp.reuse_counts(cache)[0], {unit: 1})


class StageAndPoolProvenance(Base):
    def test_stage_record(self):
        manifest = {'stage': 'bsp', 'fingerprint': 'ff' * 32, 'inputs': {'a.txt': 'ee' * 32},
                    'files': {'x': {'sha256': '11' * 32, 'size': 3}}, 'counts': {'bytes': 3}}
        from unit_tree import of_manifest
        manifest['tree'] = of_manifest(manifest)
        cp.attach_stage(manifest, self.root / RUN['AMIWIND_RUN_NAME'])
        self.assertComplete(manifest['provenance'])
        self.assertEqual(manifest['provenance']['output_sha256'], manifest['tree']['stage_hash'])
        self.assertEqual(manifest['provenance']['input_manifest']['unit'], 'bsp')

    def test_pool_object_log(self):
        import storage_pool
        source = self.root / 'f.bin'
        source.write_bytes(b'x' * 10)
        storage_pool.ensure(self.root / 'pool', source, sha(b'x' * 10))
        rows = cp.read_jsonl(self.root / 'pool' / cp.FOLDER / 'objects.jsonl')
        self.assertEqual([row['sha256'] for row in rows], [sha(b'x' * 10)])
        self.assertEqual(rows[0]['run'], RUN['AMIWIND_RUN_NAME'])


class BackfillAndSummary(Base):
    def make_old_caches(self):
        passes = self.root / 'image-passes'
        cache = pass_cache.PassCache('cull', {}, 's' * 64, passes)
        cache.store('11' * 32, {'map': 'a'}, b'OUT')
        meta_path, _ = cache._paths('11' * 32)
        meta = json.loads(meta_path.read_text())
        meta.pop('provenance')
        meta_path.write_text(json.dumps(meta) + '\n')
        units = self.root / 'chim-units' / 'mesh' / 'ab'
        units.mkdir(parents=True)
        (units / ('ab' * 32 + '.pickle')).write_bytes(pickle.dumps(('ab' * 32, 1), protocol=4))
        builds = self.root / 'build'
        run = builds / '2026_10_10_v0.0.36-dev3_full_3b5e7a9'
        run.mkdir(parents=True)
        (run / 'build-state.json').write_text(json.dumps({'build_started_at': '2026-10-10T18:00:00+03:00',
                                                           'runtime_version': '0.0.36-dev3'}))
        return passes, self.root / 'chim-units', builds, cache

    def test_dry_run_then_backfill_additive_and_valid(self):
        passes, units, builds, cache = self.make_old_caches()
        before = {p: sha(p.read_bytes()) for p in sorted(self.root.rglob('*')) if p.is_file()}
        summary = cp.summary(passes)
        self.assertEqual((summary['with_provenance'], summary['without_provenance']), (0, 1))
        dry = cp.backfill([passes, units], builds, None, dry_run=True, log=lambda *a: None)
        self.assertEqual(dry[str(passes)]['backfilled'], 1)
        self.assertEqual(dry[str(units)]['backfilled'], 1)
        self.assertFalse((passes / cp.FOLDER).exists())
        real = cp.backfill([passes, units], builds, None, dry_run=False, log=lambda *a: None)
        self.assertEqual(real[str(units)]['payload_changed'], 0)
        after = {p: sha(p.read_bytes()) for p in before}
        self.assertEqual(before, after)  # payloads (and every file that existed) untouched
        record, where = cp.lookup(next(units.rglob('*.pickle')), units)
        self.assertEqual(where, 'backfill')
        self.assertEqual(record['output_sha256'], sha(next(units.rglob('*.pickle')).read_bytes()))
        self.assertEqual(record['sources']['output_sha256'], 'exact (source: stored bytes)')
        self.assertTrue(record['sources']['created_at'].startswith('estimated'))
        self.assertEqual(record['backfill_tool'], cp.BACKFILL_TOOL)
        self.assertIn(record['sources']['run'].split(' ')[0], ('inferred', 'N/A'))
        # still a valid reuse hit under its current key
        self.assertEqual(cache.load('11' * 32), ({'map': 'a'}, b'OUT'))
        # idempotent
        again = cp.backfill([passes, units], builds, None, dry_run=False, log=lambda *a: None)
        self.assertEqual(again[str(units)]['backfilled'], 0)
        self.assertEqual(cp.summary(units)['with_provenance'], 1)

    def test_run_name_facts(self):
        self.assertEqual(cp.run_name_facts('2026_10_10_v0.0.36-dev3_full_3b5e7a9'),
                         {'version': '0.0.36-dev3', 'commit': '3b5e7a9', 'date': '2026-10-10'})
        self.assertEqual(cp.run_name_facts('final4b'), {})


if __name__ == '__main__':
    unittest.main()
