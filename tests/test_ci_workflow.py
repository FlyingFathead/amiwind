"""The hosted CI layout (CI-SOURCE-JOB-TIMEOUT-52): cached tools, suite shards, the dry-run after the tests."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/source-check.yml'
sys.path.insert(0, str(ROOT / 'tools'))
import ci_tools  # noqa: E402


def jobs(text):
    """{job id: its block of lines} of a workflow (jobs two spaces under jobs:)."""
    body = text.split('\njobs:\n', 1)[1]
    out, name = {}, None
    for line in body.splitlines():
        match = re.match(r'^  ([A-Za-z0-9_-]+):\s*$', line)
        if match:
            name = match.group(1)
            out[name] = []
        elif name:
            out[name].append(line)
    return {name: '\n'.join(lines) for name, lines in out.items()}


class WorkflowLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding='utf-8')
        cls.jobs = jobs(cls.text)

    def shards(self):
        return int(re.search(r'^  TEST_SHARDS: "(\d+)"$', self.text, re.M).group(1))

    def test_the_jobs(self):
        self.assertEqual(sorted(self.jobs), sorted(['host-launcher-parity', 'tools', 'source-checks', 'tests',
                                                    'dry-run', 'tools-from-nothing', 'docker-builder']))

    def test_every_job_has_a_time_limit_with_headroom(self):
        for name, block in self.jobs.items():
            match = re.search(r'^    timeout-minutes: (\d+)\s*$', block, re.M)
            self.assertIsNotNone(match, name)
            self.assertGreaterEqual(int(match.group(1)), 10, name)

    def test_shard_matrix_is_one_to_n_and_the_run_names_n(self):
        count = self.shards()
        self.assertGreaterEqual(count, 2)
        tests = self.jobs['tests']
        matrix = re.search(r'^        shard: \[([0-9, ]+)\]\s*$', tests, re.M).group(1)
        self.assertEqual([int(x) for x in matrix.split(',')], list(range(1, count + 1)))
        self.assertIn('fail-fast: false', tests)
        self.assertIn('python tools/run_tests.py -v --module-timeout 900 --shard "${{ matrix.shard }}/$TEST_SHARDS"',
                      tests)
        self.assertEqual(self.text.count('tools/run_tests.py'), 1)

    def test_order_tools_then_tests_then_dry_run(self):
        self.assertRegex(self.jobs['tests'], r'(?m)^    needs: tools$')
        self.assertRegex(self.jobs['source-checks'], r'(?m)^    needs: tools$')
        self.assertRegex(self.jobs['dry-run'], r'(?m)^    needs: \[tools, source-checks, tests\]$')
        for step in ('tools/build.py --dry-run', 'tools/package_dry_run.py', 'actions/upload-artifact'):
            self.assertIn(step, self.jobs['dry-run'])
            self.assertNotIn(step, self.jobs['tests'])

    def test_cache_is_keyed_by_the_installer_and_users_check_it(self):
        tools = self.jobs['tools']
        self.assertIn('python tools/ci_tools.py key', tools)
        self.assertIn('test ! -e "$RUNNER_TEMP/amiwind-clean-tools"', tools)  # a key change: from nothing
        self.assertIn('python tools/ci_tools.py record', tools)
        self.assertIn('python tools/ci_tools.py verify', tools)
        for name in ('source-checks', 'tests', 'dry-run'):
            block = self.jobs[name]
            self.assertIn('key: ${{ needs.tools.outputs.key }}', block, name)
            self.assertIn('fail-on-cache-miss: true', block, name)
            self.assertIn('python tools/ci_tools.py verify', block, name)
            self.assertNotIn('actions/cache/save', block, name)
            # The same installer runs on the restored copy: it adds only missing host packages.
            self.assertIn('tools/build.py --autoinstall --install-dependencies --yes', block, name)

    def test_from_nothing_proof_stays(self):
        block = self.jobs['tools-from-nothing']
        self.assertNotIn('actions/cache', block)
        self.assertIn('test ! -e "$RUNNER_TEMP/amiwind-clean-tools"', block)
        self.assertIn('tools/build.py --autoinstall --install-dependencies --yes', block)
        self.assertIn('tools/build.py --dry-run', block)
        self.assertIn("startsWith(github.ref, 'refs/tags/')", block)
        self.assertIn("github.event_name == 'schedule'", block)
        self.assertRegex(self.text, r"(?m)^  schedule:\n    - cron: '[^']+'$")

    def test_actions_are_pinned_by_commit(self):
        for line in re.findall(r'uses: (\S+)', self.text):
            self.assertRegex(line, r'^[\w.-]+/[\w./-]+@[0-9a-f]{40}$', line)

    def test_repository_shards_run_every_module_exactly_once(self):
        """The real suite, split as the workflow splits it: discovery in a fresh interpreter."""
        script = textwrap.dedent('''
            import json, sys
            sys.path.insert(0, sys.argv[1])
            import run_tests
            modules = run_tests.discover(sys.argv[2])
            timings = run_tests.load_timings(sys.argv[3])
            shards = run_tests.shard_modules(modules, timings, int(sys.argv[4]))
            estimate = run_tests.estimates(modules, timings)
            print(json.dumps(dict(modules=list(modules), shards=shards,
                                  loads=[sum(estimate[m] for m in s) for s in shards],
                                  biggest=max(estimate.values()))))
        ''')
        result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tools'), str(ROOT / 'tests'),
                                 str(ROOT / 'tests/module-timings.json'), str(self.shards())],
                                cwd=tempfile.gettempdir(), capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        data = json.loads(result.stdout.strip().splitlines()[-1])
        flat = [m for shard in data['shards'] for m in shard]
        self.assertEqual(sorted(flat), sorted(data['modules']))
        self.assertEqual(len(flat), len(set(flat)))
        self.assertIn('test_ci_workflow', flat)
        self.assertTrue(all(data['shards']))
        # Balanced: no shard is more than the longest module above the lightest.
        self.assertLessEqual(max(data['loads']) - min(data['loads']), data['biggest'] + 1e-6)


class ToolsKeyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='amiwind-ci-tools-')
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def write(self, root, files):
        for name, text in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text), encoding='utf-8', newline='\n')

    def test_the_installer_closure_is_in_the_key(self):
        found = ci_tools.inputs()
        for name in ('tools/setup_build.py', 'tools/install_dependencies.py', 'tools/fetch_toolchain.py',
                     'tools/fetch_native.py', 'tools/build_versions.py', 'tools/build_host.py',
                     'src/mwad/__init__.py', 'src/mwad/paths.py', 'src/mwad/progress.py', 'tools/ci_tools.py'):
            self.assertIn(name, found)
        self.assertNotIn('tools/build.py', found)  # it only dispatches to the installer
        self.assertNotIn('tools/build_aga.py', found)  # a check of the built qcc only (CHECK_ONLY)
        self.assertLess(len(found), 20, found)
        # The one check-only import is still where CHECK_ONLY says it is.
        self.assertIn('build_aga', ci_tools._imported_names(ROOT / 'tools/fetch_native.py'))
        self.assertEqual(sorted(ci_tools.CHECK_ONLY), ['build_aga'])

    def test_a_new_import_joins_the_key_and_any_change_moves_it(self):
        root = self.tmp / 'repo'
        self.write(root, {
            'tools/setup_build.py': 'import helper\nfrom pkg.sub import thing\n',
            'tools/helper.py': 'def f():\n    import late\n',
            'tools/late.py': 'PIN = "1.0"\n',
            'tools/unrelated.py': '',
            'src/pkg/__init__.py': '',
            'src/pkg/sub.py': 'from . import other\n',
            'src/pkg/other.py': '__import__("dyn")\n',
            'tools/dyn.py': '',
        })
        names = ci_tools.inputs(root, ('setup_build',))
        self.assertEqual(names, ['src/pkg/__init__.py', 'src/pkg/other.py', 'src/pkg/sub.py', 'tools/dyn.py',
                                 'tools/helper.py', 'tools/late.py', 'tools/setup_build.py'])
        before = ci_tools.inputs_digest(root, ('setup_build',))
        (root / 'tools/unrelated.py').write_text('x = 1\n', encoding='utf-8')
        self.assertEqual(ci_tools.inputs_digest(root, ('setup_build',)), before)
        (root / 'tools/late.py').write_text('PIN = "1.1"\n', encoding='utf-8')
        self.assertNotEqual(ci_tools.inputs_digest(root, ('setup_build',)), before)

    def test_key_names_the_runner_and_the_inputs(self):
        key = ci_tools.key()
        self.assertTrue(key.startswith('amiwind-tools-'))
        self.assertIn(ci_tools.inputs_digest()[:24], key)

    def test_a_restored_copy_must_match_its_bootstrap_file_by_file(self):
        tools = self.tmp / 'tools'
        self.write(tools, {'sdk/bin/gcc': 'binary', 'venv/lib/x.py': 'x = 1\n'})
        os.chmod(tools / 'sdk/bin/gcc', 0o755)
        if hasattr(os, 'symlink'):
            try:
                os.symlink('gcc', tools / 'sdk/bin/cc')
            except OSError:
                pass
        self.assertEqual(ci_tools.record(tools), 0)
        self.assertEqual(ci_tools.verify(tools), 0)
        (tools / 'venv/lib/x.py').write_text('x = 2\n', encoding='utf-8')
        self.assertEqual(ci_tools.verify(tools), 1)
        (tools / 'venv/lib/x.py').write_text('x = 1\n', encoding='utf-8')
        self.assertEqual(ci_tools.verify(tools), 0)
        (tools / 'venv/lib/extra.py').write_text('', encoding='utf-8')
        self.assertEqual(ci_tools.verify(tools), 1)
        (tools / 'venv/lib/extra.py').unlink()
        (tools / 'sdk/bin/gcc').unlink()
        self.assertEqual(ci_tools.verify(tools), 1)

    def test_an_unrecorded_directory_is_refused(self):
        (self.tmp / 'empty').mkdir()
        self.assertEqual(ci_tools.verify(self.tmp / 'empty'), 1)


if __name__ == '__main__':
    unittest.main()
