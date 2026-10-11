"""Unit reuse audit (HASH EVERYTHING; build_profile.py reuse): per cache the units a run computed and reused,
the input whose hash changed, a loud failure for a unit computed again with an unchanged key, unkeyed stages;
and the benchmark: a rebuild with no change computes 0 units."""
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
sys.path.insert(0, str(ROOT / 'tools'))
import build_profile  # noqa: E402
import pass_cache  # noqa: E402

SCHEMA = build_profile.PROVENANCE_SCHEMA


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def entry(cache, key, run, unit, inputs, when, parameters=None):
    """A JSON cache entry carrying a provenance record (the cache-provenance format)."""
    path = cache / key[:2] / (key + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'inputs': [{'name': n, 'sha256': s, 'bytes': 1} for n, s in inputs.items()],
                'parameters': parameters or {}, 'unit': unit}
    path.write_text(json.dumps({'row': {}, 'provenance': {
        'schema': SCHEMA, 'cache': cache.name, 'key': key, 'input_manifest': manifest, 'run': run,
        'created_at': when, 'output_sha256': sha(key)}}), encoding='utf-8')


def reuse_line(cache, key, run, at):
    folder = cache / '.provenance'
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / 'reuse.jsonl', 'a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps({'key': key, 'cache': cache.name, 'run': run, 'at': at}) + '\n')


class AuditTests(unittest.TestCase):
    def fixture(self, temp):
        cache = Path(temp) / 'world-terrain-v1'
        old, new = 'run-old', 'run-new'
        # vf0001: unchanged, reused by the new run
        entry(cache, sha('k1'), old, 'vf0001', {'terrain.bin': sha('t1'), 'palette': sha('p')}, '2026-10-10T20:00:00')
        reuse_line(cache, sha('k1'), new, '2026-10-11T00:59:00')
        # vf0002: its terrain changed, computed again with a new key
        entry(cache, sha('k2'), old, 'vf0002', {'terrain.bin': sha('t2'), 'palette': sha('p')}, '2026-10-10T20:00:01')
        entry(cache, sha('k2b'), new, 'vf0002', {'terrain.bin': sha('t2b'), 'palette': sha('p')}, '2026-10-11T01:00:00')
        # vf0003: computed again with the SAME key (the old entry was overwritten; its reuse line remains)
        reuse_line(cache, sha('k3'), old, '2026-10-10T20:30:00')
        entry(cache, sha('k3'), new, 'vf0003', {'terrain.bin': sha('t3')}, '2026-10-11T01:00:01')
        # vf0004: a new unit; vf0005: no unit name
        entry(cache, sha('k4'), new, 'vf0004', {'terrain.bin': sha('t4')}, '2026-10-11T01:00:02')
        entry(cache, sha('k5'), new, None, {'terrain.bin': sha('t5')}, '2026-10-11T01:00:03')
        return cache, new

    def test_computed_reused_changed_inputs_and_the_loud_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            cache, run = self.fixture(temp)
            report = build_profile.unit_reuse(run, [cache], stages=['world-terrain', 'area', 'npcs'])
        row = report['caches']['world-terrain-v1']
        self.assertEqual((row['computed'], row['reused']), (4, 1))
        units = {u['unit']: u for u in row['units']}
        self.assertEqual(units['vf0002']['status'], 'changed')
        self.assertEqual(units['vf0002']['changed_inputs'], ['terrain.bin'])
        self.assertEqual(units['vf0004']['status'], 'new unit')
        self.assertEqual([u['unit'] for u in report['failures']], ['vf0003'])
        self.assertEqual(len(report['unexplained']), 1)
        self.assertEqual(report['unkeyed'], ['area', 'npcs'])       # world-terrain has its unit cache
        text = '\n'.join(build_profile.unit_reuse_lines(report))
        self.assertIn('RECOMPUTED WITH AN UNCHANGED KEY: world-terrain-v1 vf0003', text)
        self.assertIn('vf0002: terrain.bin', text)

    def test_the_command_fails_on_a_recompute(self):
        with tempfile.TemporaryDirectory() as temp:
            cache, run = self.fixture(temp)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = build_profile.main(['reuse', run, '--cache', str(cache), '--fail-on-recompute'])
            self.assertEqual(code, 3)
            self.assertIn('RECOMPUTED WITH AN UNCHANGED KEY', out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_profile.main(['reuse', 'run-old', '--cache', str(cache),
                                                     '--fail-on-recompute']), 0)

    def test_parameters_count_as_an_input(self):
        self.assertEqual(build_profile.changed_inputs({'inputs': [], 'parameters': {'grain': 2}},
                                                      {'inputs': [], 'parameters': {'grain': 1}}), ['parameters'])
        self.assertEqual(build_profile.changed_inputs({'inputs': [{'name': 'a', 'sha256': '1'}]},
                                                      {'inputs': [{'name': 'b', 'sha256': '1'}]}), ['a', 'b'])


class NoChangeRebuildBenchmark(unittest.TestCase):
    """A rebuild with no change computes 0 units; a changed input recomputes exactly its unit."""

    def stage(self, inputs):
        computed = []
        cache = pass_cache.PassCache.open('benchmark-pass', {'grain': 1}, str(ROOT / 'tools' / 'pass_cache.py'))
        for name, data in sorted(inputs.items()):
            key = hashlib.sha256(data).hexdigest()
            if cache.load(key) is None:
                computed.append(name)
                cache.store(key, {'unit': name}, data[::-1])
        return computed, cache.summary()

    def test_no_change_rebuild_computes_nothing(self):
        units = {f'vf{n:04d}': f'terrain {n}'.encode() for n in range(12)}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {pass_cache.ENV: temp}):
            first, summary = self.stage(units)
            self.assertEqual((len(first), summary['misses']), (12, 12))
            again, summary = self.stage(units)
            self.assertEqual(again, [])
            self.assertEqual((summary['hits'], summary['misses']), (12, 0))
            changed, _ = self.stage(dict(units, vf0005=b'changed terrain'))
            self.assertEqual(changed, ['vf0005'])


if __name__ == '__main__':
    unittest.main()
