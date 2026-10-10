"""Post-build audit (tools/build_audit.py): reuse classification, summary checks, time to fail, exclude effect."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import build_audit

SHA = 'a' * 64


def step(name, status='passed', start=0.0, elapsed=1.0, command=None, reused=None, returncode=0):
    item = {'name': name, 'status': status, 'started_seconds': start, 'elapsed_seconds': elapsed,
            'command': command or ['python3', 'tools/%s.py' % name], 'returncode': returncode}
    if reused:
        item['reused'] = reused
    return item


def write_run(root, name, steps, status='passed', cache=None, summary=True, warnings=0, videos=0, fingerprints=None):
    run = Path(root) / name
    run.mkdir(parents=True)
    state = {'schema': 'amiwind-build-receipt-v1', 'runtime_version': '0.0.34-dev1', 'status': status, 'steps': steps,
             'build_started_at': '2026-10-09T10:00:00+00:00', 'elapsed_seconds': sum(s['elapsed_seconds'] for s in steps)}
    if cache is not None:
        state['stage_cache'] = cache
    (run / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
    if summary:
        (run / 'build-summary.json').write_text(json.dumps({
            'status': status, 'output': {'sha256': SHA}, 'compiler_warnings': {'count': warnings},
            'media_coverage': {'status': 'complete', 'categories': {'videos': {'included': videos}}}}), encoding='utf-8')
    if fingerprints is not None:
        (run / 'profile').mkdir()
        (run / 'profile' / 'fingerprints.json').write_text(json.dumps(fingerprints), encoding='utf-8')
    return run


class ClassifyTests(unittest.TestCase):
    def test_expected_reasons(self):
        for reason, label in (
                ('compiles with the Amiga SDK, whose files are not fingerprinted (about 15 s)', 'never-reused'),
                ('final image: always assembled and verified from the stage outputs', 'never-reused'),
                ('not passed in rc1c (failed)', 'old-run-not-passed'),
                ('changed: dependency census, harvest, sources', 'inputs-changed'),
                ('changed: dependency scenery', 'dependency-rebuilt'),
                ('changed: sources (tools/prepare_quake.py)', 'inputs-changed'),
                ('changed: command, dependency census, harvest, world-flora-assets, external_inputs, sources', 'inputs-changed')):
            self.assertEqual(build_audit.classify(reason)[:2], ('expected', label), reason)

    def test_unexpected_reasons(self):
        for reason, label in (
                ('no output manifest in the old run', 'manifest-missing'),
                ('old output manifest incomplete or for another fingerprint', 'manifest-incomplete'),
                ('old outputs not reusable: wrote undeclared scratch', 'outputs-not-reusable'),
                ('old output world/a.bsp changed or missing since rc1c was built', 'old-output-changed'),
                ('its output x was replaced later in rc1c by image, so it cannot be reused alone', 'output-replaced'),
                ('something the audit has never seen', 'unknown-reason')):
            self.assertEqual(build_audit.classify(reason)[:2], ('unexpected', label), reason)

    def test_docs_only_source_change_is_key_overbroad(self):
        klass, label, detail = build_audit.classify('changed: sources (tools/release-files.json)')
        self.assertEqual((klass, label), ('unexpected', 'key-overbroad'))
        self.assertIn('tools/release-files.json', detail)
        self.assertEqual(build_audit.classify('changed: sources (docs/bugs/X.md, tools/release-files.json)')[1], 'key-overbroad')

    def test_hidden_files_or_dependency_change_is_only_a_note(self):
        self.assertEqual(build_audit.classify('changed: sources (tools/release-files.json, +2 more)')[0], 'info')
        self.assertEqual(build_audit.classify('changed: dependency census, sources (docs/A.md)')[0], 'info')

    def test_full_file_list_from_fingerprints_wins(self):
        reason = 'changed: sources (tools/release-files.json, +1 more)'
        self.assertEqual(build_audit.classify(reason, full_files=['tools/release-files.json', 'docs/B.md'])[1], 'key-overbroad')
        self.assertEqual(build_audit.classify(reason, full_files=['tools/release-files.json', 'tools/x.py'])[0], 'info')

    def test_schema_change_is_info(self):
        self.assertEqual(build_audit.classify('old has v1 fingerprints, this builder makes v2 (x): build once')[0], 'info')


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_reused_build_has_no_wake(self):
        cache = {'reuse_from': str(self.root / 'old'), 'reused': {'setup': {}, 'terrain': {}},
                 'not_reused': {'engine': 'compiles with the Amiga SDK, whose files are not fingerprinted (about 15 s)',
                                'image': 'final image: always assembled and verified from the stage outputs'}}
        run = write_run(self.root, 'new', [step('setup'), step('terrain'), step('engine'), step('image')], cache=cache)
        result = build_audit.audit(run)
        self.assertFalse(result['wake'], result['findings'])
        self.assertEqual((result['reuse']['reused'], result['reuse']['stages']), (2, 4))
        self.assertEqual(result['output_sha256'], SHA)

    def test_unexpected_rebuild_wakes(self):
        cache = {'reuse_from': str(self.root / 'old'), 'reused': {},
                 'not_reused': {'census': 'changed: sources (tools/release-files.json)',
                                'interior': 'no output manifest in the old run'}}
        run = write_run(self.root, 'new', [step('census'), step('interior')], cache=cache)
        result = build_audit.audit(run)
        kinds = {(f['kind'], f.get('stage')) for f in result['findings']}
        self.assertIn(('unexpected-rebuild', 'census'), kinds)
        self.assertIn(('unexpected-rebuild', 'interior'), kinds)
        self.assertTrue(result['wake'])

    def test_fingerprint_details_of_both_runs_are_compared(self):
        old = {'census': {'sources': {'by_file': {'tools/release-files.json': '1', 'tools/a.py': 'x'}}}}
        new = {'census': {'sources': {'by_file': {'tools/release-files.json': '2', 'tools/a.py': 'x'}}}}
        write_run(self.root, 'old', [step('census')], fingerprints=old)
        cache = {'reuse_from': '/vol/elsewhere/old', 'reused': {},
                 'not_reused': {'census': 'changed: sources (tools/release-files.json, +4 more)'}}
        run = write_run(self.root, 'new', [step('census')], cache=cache, fingerprints=new)
        result = build_audit.audit(run)
        entry = result['reuse']['not_reused']['census']
        self.assertEqual(entry['label'], 'key-overbroad')
        self.assertEqual(entry['changed_files'], ['tools/release-files.json'])

    def test_reuse_report_expectation_wins(self):
        cache = {'reuse_from': str(self.root / 'old'), 'reused': {}, 'not_reused': {'media': 'no output manifest in the old run'}}
        run = write_run(self.root, 'new', [step('media')], cache=cache)
        (run / 'reuse-report.json').write_text(json.dumps({'stages': {'media': {'reused': False, 'expected': True,
                                                                                'reason': 'first build with pool v1'}}}))
        result = build_audit.audit(run)
        self.assertEqual(result['reuse']['not_reused']['media']['class'], 'expected')
        self.assertFalse(result['wake'])

    def test_no_reuse_from_is_info_only(self):
        run = write_run(self.root, 'scratch', [step('setup')], cache={'reused': {}, 'not_reused': {}})
        result = build_audit.audit(run)
        self.assertFalse(result['wake'])
        self.assertEqual(result['findings'][0]['kind'], 'reuse')

    def test_late_failure_and_time_to_fail(self):
        steps = [step('setup', elapsed=10), step('chim', start=10, elapsed=2000), step('image', 'failed', 2010, 900, returncode=1)]
        run = write_run(self.root, 'late', steps, status='failed', summary=False, cache={'reused': {}, 'not_reused': {}})
        result = build_audit.audit(run)
        self.assertEqual(result['time_to_fail']['stage'], 'image')
        self.assertEqual(result['time_to_fail']['seconds'], 2910)
        kinds = [f['kind'] for f in result['findings']]
        self.assertIn('build-failed', kinds)
        self.assertIn('late-failure', kinds)

    def test_early_failure_is_not_late(self):
        run = write_run(self.root, 'early', [step('image', 'failed', 0, 20, returncode=1)], status='failed', summary=False,
                        cache={'reused': {}, 'not_reused': {}})
        kinds = [f['kind'] for f in build_audit.audit(run)['findings']]
        self.assertIn('build-failed', kinds)
        self.assertNotIn('late-failure', kinds)

    def test_summary_checks(self):
        run = write_run(self.root, 'warn', [step('setup'), step('engine', 'failed')], warnings=3,
                        cache={'reused': {}, 'not_reused': {}})
        kinds = [f['kind'] for f in build_audit.audit(run)['findings']]
        self.assertIn('summary-mismatch', kinds)
        self.assertIn('compiler-warnings', kinds)
        run = write_run(self.root, 'nosummary', [step('setup')], summary=False, cache={'reused': {}, 'not_reused': {}})
        self.assertIn('summary-missing', [f['kind'] for f in build_audit.audit(run)['findings']])

    def test_exclude_effect(self):
        media = step('media', elapsed=900, command=['python3', 'tools/import_media.py', '--exclude-video',
                                                     '--exclude-unreferenced', 'voice,npcs'])
        run = write_run(self.root, 'mw', [media], videos=17, cache={'reused': {}, 'not_reused': {}})
        result = build_audit.audit(run)
        kinds = [f['kind'] for f in result['findings']]
        self.assertIn('exclude-no-effect', kinds)
        self.assertIn('exclude-late', kinds)
        self.assertEqual(result['exclude']['exclude_unreferenced'], 'voice,npcs')
        quick = step('media', elapsed=30, command=['x', '--exclude-unreferenced', 'voice'])
        run = write_run(self.root, 'mw2', [quick], cache={'reused': {}, 'not_reused': {}})
        self.assertFalse(build_audit.audit(run)['wake'])

    def test_running_and_missing_runs(self):
        run = write_run(self.root, 'busy', [step('setup', 'running')], status='running', summary=False)
        result = build_audit.audit(run)
        self.assertEqual(result['findings'][0]['kind'], 'not-finished')
        self.assertIsNone(build_audit.audit(self.root / 'nothing'))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(build_audit.main([str(self.root / 'nothing')]), 2)

    def test_cli_exit_status(self):
        cache = {'reuse_from': str(self.root / 'old'), 'reused': {}, 'not_reused': {'x': 'no output manifest in the old run'}}
        run = write_run(self.root, 'cli', [step('x')], cache=cache)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(build_audit.main([str(run), '--json']), 1)
        self.assertEqual(json.loads(out.getvalue())['schema'], build_audit.SCHEMA)


class CompareTests(unittest.TestCase):
    def manifest(self, run, stage, files):
        folder = run / 'profile' / 'manifests'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (stage + '.json')).write_text(json.dumps({'files': {p: {'size': 1, 'sha256': h} for p, h in files.items()}}))

    def test_same_and_different_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = write_run(root, 'scratch', [step('chim')], cache={})
            b = write_run(root, 'release', [step('chim')], cache={})
            self.manifest(a, 'chim', {'chim/a.pak': '1', 'chim/stamp.txt': 'x'})
            self.manifest(b, 'chim', {'chim/a.pak': '1', 'chim/stamp.txt': 'y'})
            self.assertFalse(build_audit.compare_runs(a, b)['same'])
            same = build_audit.compare_runs(a, b, ignore=('*/stamp.txt',))
            self.assertTrue(same['same'])
            self.assertTrue(same['output']['same'])
            self.manifest(b, 'media', {'media/v.mp4': '2'})
            diff = build_audit.compare_runs(a, b, ignore=('*/stamp.txt',))
            self.assertEqual(diff['stages']['media']['counts'], [1, 0, 0])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_audit.main([str(a), '--compare', str(b)]), 1)

    def test_runs_without_manifests_are_never_same(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = write_run(root, 'a', [step('x')], cache={})
            b = write_run(root, 'b', [step('x')], cache={})
            result = build_audit.compare_runs(a, b)
            self.assertFalse(result['same'])
            self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
