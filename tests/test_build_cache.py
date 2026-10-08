"""Stage fingerprints and --reuse-from: exact invalidation, byte-identical reuse, refusals."""
import contextlib
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
import build  # noqa: E402
import build_cache  # noqa: E402
import build_profile  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

MANIFESTS = os.name == 'posix'

STAGE_A = '''
import sys
from pathlib import Path
def main():
    from helper import payload
    out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True)
    (out / 'a.txt').write_text(payload('a'))
    (out / 'deep').mkdir()
    (out / 'deep' / 'blob.bin').write_bytes(bytes(range(256)) * 512)
    (out / 'scratch.tmp').write_text('removed by stage c')
main()
'''
STAGE_B = '''
import sys
from pathlib import Path
from helper import payload
scene = Path(sys.argv[sys.argv.index('--scene') + 1]); out = Path(sys.argv[sys.argv.index('--out') + 1])
out.mkdir(parents=True)
(out / 'b.txt').write_text(payload('b') + (scene / 'a.txt').read_text())
'''
STAGE_C = '''
import sys
from pathlib import Path
scene = Path(sys.argv[sys.argv.index('--scene') + 1]); other = Path(sys.argv[sys.argv.index('--other') + 1])
(scene / 'c.txt').write_text('c:' + (other / 'b.txt').read_text())
(scene / 'scratch.tmp').unlink()
'''
STAGE_D = '''
import sys
from pathlib import Path
other = Path(sys.argv[sys.argv.index('--other') + 1]); out = Path(sys.argv[sys.argv.index('--out') + 1])
out.mkdir(parents=True)
(out / 'd.txt').write_text('d:' + (other / 'b.txt').read_text())
'''
HELPER = '''
import json
def payload(name):
    settings = json.loads(open(__file__.replace('tools/helper.py', 'config/settings.json')).read())
    return name + ':' + settings['value'] + '\\n'
CONFIG = 'config/settings.json'
'''


def make_repository(root):
    (root / 'tools').mkdir(parents=True)
    (root / 'config').mkdir()
    (root / 'engine').mkdir()
    (root / 'docs').mkdir()
    for name, text in (('stage_a.py', STAGE_A), ('stage_b.py', STAGE_B), ('stage_c.py', STAGE_C), ('stage_d.py', STAGE_D),
                       ('helper.py', HELPER), ('unrelated.py', 'VALUE = 1\n')):
        (root / 'tools' / name).write_text(text)
    (root / 'config' / 'settings.json').write_text('{"value": "one"}')
    (root / 'engine' / 'engine.c').write_text('int main(void) { return 0; }\n')
    (root / 'docs' / 'NOTES.md').write_text('# Notes\n')
    return build_cache.SourceIndex(root)


def steps_for(repository, run, data, jobs=2):
    tools = repository / 'tools'
    return [('alpha', [sys.executable, str(tools / 'stage_a.py'), '--data-files', str(data), '--out', str(run / 'alpha'),
                       '--jobs', str(jobs)]),
            ('beta', [sys.executable, str(tools / 'stage_b.py'), '--scene', str(run / 'alpha'), '--out', str(run / 'beta')]),
            ('gamma', [sys.executable, str(tools / 'stage_c.py'), '--scene', str(run / 'alpha'), '--other', str(run / 'beta')]),
            ('delta', [sys.executable, str(tools / 'stage_d.py'), '--other', str(run / 'beta'), '--out', str(run / 'delta')])]


def metadata(inputs=None):
    return {'compiler_jobs': 1, 'input_sha256': inputs or {'Morrowind.esm': 'aa'}, 'tools': {}, 'tool_sha256': {},
            'version_comparison': []}


def tree(run):
    return {p.relative_to(run).as_posix(): p.read_bytes() for p in sorted(Path(run).rglob('*'))
            if p.is_file() and p.relative_to(run).parts[0] in ('alpha', 'beta', 'delta')}


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / 'repo'
        self.data = self.root / 'data'
        self.data.mkdir()
        make_repository(self.repository)

    def tearDown(self):
        self.temp.cleanup()

    def fingerprints(self, run='run', jobs=2, inputs=None, env=None, steps=None):
        index = build_cache.SourceIndex(self.repository)
        steps = steps or steps_for(self.repository, self.root / run, self.data, jobs)
        with patch.dict(os.environ, env or {}):
            return build_cache.fingerprint_steps(steps, self.root / run, metadata(inputs), index)[0]

    def test_unchanged_inputs_give_the_same_fingerprint(self):
        first = self.fingerprints()
        self.assertEqual(first, self.fingerprints())
        self.assertEqual(first, self.fingerprints(run='another-run'))   # run folder normalized
        self.assertEqual(first, self.fingerprints(jobs=16))              # worker count normalized
        (self.repository / 'tools' / 'unrelated.py').write_text('VALUE = 2\n')
        (self.repository / 'engine' / 'engine.c').write_text('int main(void) { return 1; }\n')
        (self.repository / 'docs' / 'NOTES.md').write_text('# Changed notes\n')
        self.assertEqual(first, self.fingerprints(env={'UNRELATED': 'x', 'AMIWIND_BUILD_JOBS': '7'}))

    def test_any_input_tool_source_or_argument_changes_it(self):
        first = self.fingerprints()
        changed = self.fingerprints(inputs={'Morrowind.esm': 'bb'})
        self.assertNotEqual(first['alpha'], changed['alpha'])            # game input (alpha reads --data-files)
        self.assertNotEqual(first['gamma'], changed['gamma'])            # ... and everything after it
        (self.repository / 'tools' / 'helper.py').write_text(HELPER + '# edited\n')
        helper = self.fingerprints()
        self.assertNotEqual(first['alpha'], helper['alpha'])             # imported inside a function
        self.assertNotEqual(first['beta'], helper['beta'])
        (self.repository / 'tools' / 'helper.py').write_text(HELPER)
        self.assertEqual(first, self.fingerprints())
        (self.repository / 'config' / 'settings.json').write_text('{"value": "two"}')
        self.assertNotEqual(first['alpha'], self.fingerprints()['alpha'])  # data folder named in the code
        (self.repository / 'config' / 'settings.json').write_text('{"value": "one"}')
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C + '# edited\n')
        edited = self.fingerprints()
        self.assertEqual(first['alpha'], edited['alpha'])
        self.assertEqual(first['beta'], edited['beta'])
        self.assertNotEqual(first['gamma'], edited['gamma'])
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C)
        steps = steps_for(self.repository, self.root / 'run', self.data)
        steps[1][1].append('--extra')
        argument = self.fingerprints(steps=steps)
        self.assertEqual(first['alpha'], argument['alpha'])
        self.assertNotEqual(first['beta'], argument['beta'])
        self.assertNotEqual(first['gamma'], argument['gamma'])           # through its dependency
        self.assertNotEqual(first['alpha'], self.fingerprints(env={'AMIWIND_SCENERY_REDUCE': '0.5'})['alpha'])
        external = self.root / 'captions.json'
        external.write_text('[1]')
        steps = steps_for(self.repository, self.root / 'run', self.data)
        steps[0] = (steps[0][0], steps[0][1] + ['--intro-captions', str(external)])
        with_file = self.fingerprints(steps=steps)
        external.write_text('[2]')
        self.assertNotEqual(with_file['alpha'], self.fingerprints(steps=steps)['alpha'])

    def test_closure_and_explanations(self):
        index = build_cache.SourceIndex(self.repository)
        python, data, uncertain = index.closure(self.repository / 'tools' / 'stage_a.py')
        self.assertEqual(python, {'tools/stage_a.py', 'tools/helper.py'})
        self.assertEqual(data, {'config/settings.json'})
        self.assertFalse(uncertain)
        self.assertNotIn('docs/NOTES.md', index.files)
        old = {'command': ['x'], 'sources': {'digest': '1'}, 'dependencies': {'a': '1', 'b': '2'}}
        new = {'command': ['x'], 'sources': {'digest': '2'}, 'dependencies': {'a': '1', 'b': '3'}}
        self.assertEqual(build_cache.explain(old, new), ['dependency b', 'sources'])

    def test_real_stage_closures_leave_engine_sources_to_the_engine_and_image(self):
        """An engine C edit must not invalidate the conversion stages (measured on this repository)."""
        index = build_cache.SourceIndex()
        for script in ('prepare_world_scenery.py', 'prepare_world_regions.py', 'prepare_scenery.py', 'prepare_music.py'):
            python, data, uncertain = index.closure(ROOT / 'tools' / script)
            self.assertFalse(uncertain, script)
            self.assertIn('tools/' + script, python)
            self.assertFalse([path for path in data if path.startswith('engine/aga/src/')], script)
        python, data, _ = index.closure(ROOT / 'tools' / 'build_aga.py')
        self.assertTrue([path for path in data if path.startswith('engine/aga/src/')])
        self.assertIn('tools/optimize_world_maps.py', python)   # imported inside a function


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / 'repo'
        self.data = self.root / 'data'
        self.data.mkdir()
        make_repository(self.repository)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, name, reuse_from=None, parallel=False, mode='copy'):
        run = self.root / 'workspace' / name
        index = build_cache.SourceIndex(self.repository)
        meta = metadata()
        meta['compiler_jobs'] = 2 if parallel else 1
        meta['runtime_version'] = '0.0.0-dev1'
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            steps = build_cache.prepare(steps_for(self.repository, run, self.data), run, meta, reuse_from, mode, index)
            if parallel:
                execute_parallel(steps, run, meta, self.repository)
            else:
                build.execute(steps, run, meta)
        state = json.loads((run / 'build-state.json').read_text())
        return run, state, output.getvalue()

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_reused_outputs_are_byte_identical_to_a_fresh_build(self):
        first, state, _ = self.build('first')
        self.assertEqual(state['status'], 'passed')
        manifest = build_cache.load_manifest(first, 'alpha')
        self.assertEqual(set(manifest['files']), {'alpha/a.txt', 'alpha/deep/blob.bin', 'alpha/scratch.tmp'})
        self.assertEqual(build_cache.load_manifest(first, 'gamma')['deleted'], ['alpha/scratch.tmp'])
        second, state, printed = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
        for entry in state['steps']:
            self.assertTrue(entry['reused'].startswith('reused (fingerprint '), entry)
            self.assertIn('build_cache.py', ' '.join(entry['command']))
        self.assertIn('reused  alpha', printed)
        self.assertIn('Reused stage alpha from', (second / 'logs' / '01-alpha.log').read_text())
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        self.assertEqual(tree(second), tree(first))
        self.assertFalse((second / 'alpha' / 'scratch.tmp').exists())
        self.assertEqual((second / 'alpha' / 'c.txt').read_text(), (fresh / 'alpha' / 'c.txt').read_text())
        profile = json.loads((second / 'build-profile.json').read_text())
        self.assertEqual([row['reused']['from'] for row in profile['stages']], [str(first)] * 4)
        # A reused run is itself a reuse source, also for the parallel scheduler.
        third, state, _ = self.build('third', reuse_from=second, parallel=True)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'delta', 'gamma'])
        self.assertEqual(tree(third), tree(fresh))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_changed_stage_and_its_dependents_rebuild(self):
        first, _, _ = self.build('first')
        (self.repository / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        second, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'gamma'])
        self.assertIn('changed: sources', state['stage_cache']['not_reused']['delta'])
        self.assertEqual((second / 'delta' / 'd.txt').read_text(), 'D:b:one\na:one\n')
        # gamma deletes alpha's scratch file in place: when gamma rebuilds, alpha's version is
        # needed but no longer exists in the old run, so alpha (and all after it) rebuild too.
        (self.repository / 'tools' / 'stage_c.py').write_text(STAGE_C.replace("'c:'", "'C:'"))
        second, state, _ = self.build('second-c', reuse_from=first)
        self.assertEqual(state['stage_cache']['reused'], {})
        reasons = state['stage_cache']['not_reused']
        self.assertIn('changed: ', reasons['gamma'])
        self.assertIn('alpha/scratch.tmp was replaced later', reasons['alpha'])
        self.assertIn('depends on rebuilt stage alpha', reasons['beta'])
        self.assertTrue((second / 'alpha' / 'c.txt').read_text().startswith('C:'))
        (self.repository / 'tools' / 'helper.py').write_text(HELPER.replace("':'", "'='"))
        third, state, _ = self.build('third', reuse_from=first)
        self.assertEqual(state['stage_cache']['reused'], {})
        self.assertIn('changed: sources', state['stage_cache']['not_reused']['alpha'])
        self.assertEqual((third / 'beta' / 'b.txt').read_text(), 'b=one\na=one\n')

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_damaged_old_outputs_are_never_copied(self):
        first, _, _ = self.build('first')
        (first / 'delta' / 'd.txt').write_text('tampered')
        second, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(sorted(state['stage_cache']['reused']), ['alpha', 'beta', 'gamma'])
        self.assertIn('old output delta/d.txt changed or missing', state['stage_cache']['not_reused']['delta'])
        fresh, _, _ = self.build('fresh')
        self.assertEqual(tree(second), tree(fresh))
        self.assertFalse(list(second.rglob('*' + build_cache.TEMPORARY_SUFFIX)))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_damage_found_while_copying_rebuilds_or_stops(self):
        first, _, _ = self.build('first')
        run = self.root / 'workspace' / 'manual'
        (run / 'profile').mkdir(parents=True)
        index = build_cache.SourceIndex(self.repository)
        steps = steps_for(self.repository, run, self.data)
        fingerprints, components, problems, dependencies = build_cache.fingerprint_steps(steps, run, metadata(), index)
        plans, _ = build_cache.plan_reuse(steps, fingerprints, dependencies, components, problems, first)
        self.assertEqual(plans['gamma']['rebuild_hazard'], ['alpha/scratch.tmp'])
        self.assertEqual(plans['delta']['rebuild_hazard_count'], 0)
        (run / 'profile' / build_cache.PLAN_NAME).write_text(json.dumps(plans))
        # The old run is damaged after planning: delta can still rebuild itself ...
        (first / 'delta' / 'd.txt').write_text('tampered')
        (run / 'beta').mkdir()
        (run / 'beta' / 'b.txt').write_text('b:one\na:one\n')
        target = run / 'delta'
        rebuild = [sys.executable, '-c',
                   'import sys; from pathlib import Path; p = Path(sys.argv[1]); p.mkdir(); (p / "d.txt").write_text("rebuilt")',
                   str(target)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_cache.apply_stage(run, 'delta', rebuild), 0)
        self.assertEqual((run / 'delta' / 'd.txt').read_text(), 'rebuilt')
        self.assertIn('SHA-256', (run / 'profile' / 'reuse-fallback' / 'delta.txt').read_text())
        self.assertFalse(list(run.rglob('*' + build_cache.TEMPORARY_SUFFIX)))
        # ... but gamma, whose replaced file alpha left out, must stop the build instead.
        (run / 'alpha').mkdir()
        (first / 'alpha' / 'c.txt').write_text('tampered')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(build_cache.apply_stage(run, 'gamma', ['false']), 1)
        self.assertIn('cannot be rebuilt in this run either', output.getvalue())

    @unittest.skipUnless(MANIFESTS and hasattr(os, 'geteuid') and os.geteuid() != 0, 'hard links need a non-root POSIX user')
    def test_hard_links_are_verified_and_read_only(self):
        first, _, _ = self.build('first')
        second, state, _ = self.build('second', reuse_from=first, mode='hardlink')
        self.assertEqual(state['stage_cache']['reuse_mode'], 'hardlink')
        blob = second / 'alpha' / 'deep' / 'blob.bin'
        self.assertEqual(os.stat(blob).st_ino, os.stat(first / 'alpha' / 'deep' / 'blob.bin').st_ino)
        with self.assertRaises(PermissionError):
            blob.open('r+b')

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_concurrent_stages_touching_one_path_are_never_reused(self):
        run = self.root / 'workspace' / 'parallel'
        shared = 'import sys, time\nfrom pathlib import Path\np = Path(sys.argv[1]); p.mkdir(exist_ok=True)\n' \
                 'time.sleep(.3); (p / sys.argv[2]).write_text(sys.argv[2]); (p / "shared.txt").write_text(sys.argv[2])\ntime.sleep(.3)\n'
        steps = [('media', [sys.executable, '-c', shared, str(run / 'together'), 'media']),
                 ('music', [sys.executable, '-c', shared, str(run / 'together'), 'music']),
                 ('world-survey', [sys.executable, '-c', shared, str(run / 'alone'), 'survey'])]
        meta = metadata()
        meta['compiler_jobs'] = 3
        with contextlib.redirect_stdout(io.StringIO()):
            steps = build_cache.prepare(steps, run, meta, index=build_cache.SourceIndex(self.repository))
            execute_parallel(steps, run, meta, self.repository)
        index = json.loads((run / 'profile' / 'manifests' / 'index.json').read_text())
        self.assertFalse(index['media']['reusable'])
        self.assertFalse(index['music']['reusable'])
        self.assertIn('while', index['media']['reasons'][0])
        self.assertTrue(index['world-survey']['reusable'])

    def test_release_versions_refuse_reuse(self):
        for version in ('0.0.32', '0.0.32-rc1', '1.0.0'):
            with self.assertRaisesRegex(ValueError, 'from scratch'):
                build_cache.require_reuse_allowed(version)
            build_cache.require_reuse_allowed(version, allow_release=True)
        build_cache.require_reuse_allowed('0.0.32-dev1')
        with patch.object(build, 'VERSION', '0.0.32-rc1'), contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stop:
            build.main(['--stage', 'terrain', '--data-files', str(self.data), '--reuse-from', str(self.root),
                        '--workspace', str(self.root / 'workspace')])
        self.assertEqual(stop.exception.code, 1)
        with contextlib.redirect_stderr(io.StringIO()) as error, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit):
            build.main(['--dry-run', '--reuse-from', str(self.root)])
        self.assertIn('--reuse-from needs', error.getvalue())

    def test_unknown_or_unfinished_old_runs(self):
        with self.assertRaisesRegex(ValueError, 'no build-state.json'):
            self.build('first', reuse_from=self.root / 'missing')
        if not MANIFESTS:
            return
        first, _, _ = self.build('first-real')
        state = json.loads((first / 'build-state.json').read_text())
        state['steps'][1]['status'] = 'failed'
        (first / 'build-state.json').write_text(json.dumps(state))
        (first / 'profile' / 'manifests' / 'alpha.json').unlink()
        _, state, _ = self.build('second', reuse_from=first)
        self.assertEqual(state['stage_cache']['reused'], {})
        self.assertIn('no output manifest', state['stage_cache']['not_reused']['alpha'])
        self.assertIn('not passed', state['stage_cache']['not_reused']['beta'])

    def test_engine_and_image_always_run(self):
        self.assertEqual(set(build_cache.NON_REUSABLE), {'engine', 'image', 'dry-run-image'})
        roots = build_cache.output_roots(['python', '/w/run/a/x.bin', '/w/run/a', '/w/run/logs/1.log', '/w/run/b/c'], Path('/w/run'))
        self.assertEqual(roots, ['a', 'b/c'])
        self.assertEqual(build_cache.normalize_command(['p', '--out', '/w/run/x', '--jobs', '12'], Path('/w/run')),
                         ['p', '--out', '{RUN}/x', '--jobs', '{JOBS}'])


if __name__ == '__main__':
    unittest.main()
