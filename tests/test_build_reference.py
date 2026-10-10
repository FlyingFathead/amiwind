# SPDX-License-Identifier: GPL-3.0-only
"""Stage output hashes, release reference checksums (warn only) and the end summary's reuse and reference
section (docs/BUILD_CACHE.md)."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build_cache  # noqa: E402
import build_reference  # noqa: E402


def make_run(run, stages, edition='GOG GOTY', old=None, reused=()):
    target = run / 'profile' / 'manifests'
    target.mkdir(parents=True)
    steps = []
    for name, files in stages.items():
        (target / f'{name}.json').write_text(json.dumps({
            'schema': build_cache.MANIFEST_SCHEMA, 'stage': name, 'status': 'complete', 'reusable': True,
            'reasons': [], 'files': {k: {'size': 1, 'sha256': v, 'mode': 420} for k, v in files.items()},
            'links': {}, 'deleted': [], 'directories': [], 'deleted_directories': []}))
        steps.append({'name': name, 'elapsed_seconds': 120.0})
    cache = {'reuse_from': str(old), 'reused': {name: {} for name in reused}, 'not_reused': {}} if old else {}
    (run / 'build-state.json').write_text(json.dumps({'steps': steps, 'stage_cache': cache,
                                                       'known_inputs': {'edition': {'edition': edition}}}))


class StageHashTests(unittest.TestCase):
    def test_a_stage_hash_ignores_diagnostics_and_follows_every_output(self):
        base = {'files': {'a/x.bsp': {'sha256': '1' * 64}, 'a/compile.log': {'sha256': '2' * 64}}, 'links': {}}
        same = {'files': {'a/x.bsp': {'sha256': '1' * 64}, 'a/compile.log': {'sha256': '3' * 64}}, 'links': {}}
        other = {'files': {'a/x.bsp': {'sha256': '4' * 64}}, 'links': {}}
        self.assertEqual(build_reference.stage_hash(base), build_reference.stage_hash(same))
        self.assertNotEqual(build_reference.stage_hash(base), build_reference.stage_hash(other))


class ReferenceTests(unittest.TestCase):
    def test_no_reference_match_and_first_differing_stage(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(build_reference, 'FOLDER', Path(temp) / 'checksums'):
            release = Path(temp) / 'release'
            make_run(release, {'terrain': {'t.bin': 'a' * 64}, 'scene': {'s.bin': 'b' * 64}})
            mine = Path(temp) / 'mine'
            make_run(mine, {'terrain': {'t.bin': 'a' * 64}, 'scene': {'s.bin': 'c' * 64}})
            result = build_reference.verify(mine, '9.9.9')
            self.assertEqual(result['status'], 'no-reference')
            self.assertIn('no reference checksums for v9.9.9', build_reference.verify_line(result))
            with patch('project_version.public_version', return_value='9.9.9'):
                path = build_reference.write(release)
            self.assertEqual(path.name, 'v9.9.9.json')
            self.assertEqual(build_reference.verify(release, '9.9.9')['stages_differing'], [])
            result = build_reference.verify(mine, '9.9.9')
            self.assertEqual(result['status'], 'differs')
            self.assertEqual(result['first_differing'], 'scene')
            self.assertEqual(result['stages_matching'], 1)
            self.assertIn('WARNING', build_reference.verify_line(result))
            text = path.read_text(encoding='utf-8')
            self.assertNotIn(temp, text)                       # hashes and output names only, no local paths


class EndSummaryTests(unittest.TestCase):
    def test_reuse_and_reference_section(self):
        import build_summary
        with tempfile.TemporaryDirectory() as temp, patch.object(build_reference, 'FOLDER', Path(temp) / 'checksums'):
            old, run = Path(temp) / 'old', Path(temp) / 'run'
            make_run(old, {'terrain': {'t.bin': 'a' * 64}, 'scene': {'s.bin': 'b' * 64}})
            make_run(run, {'terrain': {'t.bin': 'a' * 64}, 'scene': {'s.bin': 'b' * 64}}, old=old, reused=['terrain'])
            state = json.loads((run / 'build-state.json').read_text())
            state['stage_cache']['not_reused'] = {'scene': 'changed: sources (tools/prepare_quake.py)'}
            (run / 'build-state.json').write_text(json.dumps(state))
            record, lines = build_summary.reuse_and_reference(run, '9.9.9')
            text = '\n'.join(lines)
            self.assertIn('Reuse: 1 of 2 stages reused, 1 rebuilt (scene: input change)', text)
            self.assertIn('Time saved by reuse: about 2 min', text)
            self.assertIn('Stage hashes: 2 recorded', text)
            self.assertIn('no reference checksums for v9.9.9', text)
            self.assertEqual(sorted(record['stage_hashes']), ['scene', 'terrain'])
            self.assertEqual(record['reuse']['unexpected'], 0)


if __name__ == '__main__':
    unittest.main()
