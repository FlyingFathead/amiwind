# SPDX-License-Identifier: GPL-3.0-only
"""Entry check and developer mode (tools/entry_check.py; BUILD-IMAGE-STALE-PYTHONPATH-35)."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import entry_check  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402

VERSION = entry_check.source_version(ROOT)


def old_tree(base):
    """A fake old builder copy (like /opt/amiwind in an old container image) with one module."""
    tree = Path(base) / 'opt-amiwind'
    (tree / 'tools').mkdir(parents=True)
    (tree / 'src' / 'mwad').mkdir(parents=True)
    (tree / 'tools' / 'build_aga.py').write_text('VERSION = "0.0.26"\n')
    (tree / 'tools' / 'old_only.py').write_text('X = 1\n')
    (tree / 'src' / 'mwad' / '__init__.py').write_text('')
    (tree / 'VERSION').write_text('0.0.26\n')
    return tree


def fake_module(name, filename):
    module = types.ModuleType(name)
    module.__file__ = str(filename)
    return module


def record(folder, version=VERSION, head=None):
    path = Path(folder) / 'WORKING_VERSION.json'
    data = {'working_version': version}
    if head:
        data['integration_head'] = head
    path.write_text(json.dumps(data))
    return path


class ImportGuardTests(unittest.TestCase):
    def test_this_process_imports_nothing_from_another_tree(self):
        self.assertEqual(entry_check.foreign_imports(ROOT), [])

    def test_old_tree_module_is_named(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = old_tree(temp)
            modules = dict(sys.modules)
            modules['old_only'] = fake_module('old_only', tree / 'tools' / 'old_only.py')
            modules['build_aga'] = fake_module('build_aga', tree / 'tools' / 'build_aga.py')
            found = {name: why for name, _, why in entry_check.foreign_imports(ROOT, modules)}
            self.assertEqual(sorted(found), ['build_aga', 'old_only'])
            self.assertIn('another builder tree', found['old_only'])

    def test_builder_module_outside_the_source_is_named(self):
        with tempfile.TemporaryDirectory() as temp:
            modules = {'run_name': fake_module('run_name', Path(temp) / 'run_name.py')}
            (row,) = entry_check.foreign_imports(ROOT, modules)
            self.assertEqual(row[0], 'run_name')
            self.assertIn('outside the source tree', row[2])

    def test_guard_drops_other_trees_from_the_paths_and_refuses_loaded_modules(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = old_tree(temp)
            other = Path(temp) / 'plain'
            other.mkdir()
            environ = {'PYTHONPATH': os.pathsep.join([str(tree / 'src'), str(tree / 'tools'), str(other)])}
            path = [str(ROOT / 'tools'), str(tree / 'tools'), str(other)]
            logged = []
            self.assertIsNone(entry_check.guard_imports(ROOT, dict(sys.modules), environ, path, logged.append))
            self.assertEqual(environ['PYTHONPATH'], str(other))
            self.assertEqual(path, [str(ROOT / 'tools'), str(other)])
            self.assertIn('dropped another builder tree', logged[0])
            environ = {'PYTHONPATH': os.pathsep.join([str(tree / 'src'), str(tree / 'tools')])}
            modules = dict(sys.modules, old_only=fake_module('old_only', tree / 'tools' / 'old_only.py'))
            message = entry_check.guard_imports(ROOT, modules, environ, [], None)
            self.assertNotIn('PYTHONPATH', environ)
            self.assertIn('BUILD-IMAGE-STALE-PYTHONPATH-35', message)
            self.assertIn('old_only', message)

    @unittest.skipUnless(sys.platform != 'win32', 'POSIX subprocess check')
    def test_stale_pythonpath_cannot_shadow_a_removed_module(self):
        """The trap: an old tree on PYTHONPATH provides a module the source no longer has; the guard drops it."""
        with tempfile.TemporaryDirectory() as temp:
            tree = old_tree(temp)
            code = ('import sys; sys.path[:0] = [sys.argv[1] + "/src", sys.argv[1] + "/tools"]; import entry_check; '
                    'print(entry_check.guard_imports(log=None)); '
                    'import importlib.util; print(importlib.util.find_spec("old_only"))')
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tree / 'src'), str(tree / 'tools')]))
            out = subprocess.run([sys.executable, '-c', code, str(ROOT)], env=env, capture_output=True, text=True,
                                 check=True).stdout.split('\n')
            self.assertEqual(out[:2], ['None', 'None'])


class CheckTests(unittest.TestCase):
    def test_accepts_the_right_setup(self):
        with tempfile.TemporaryDirectory() as temp:
            pool = Path(temp) / 'pool'
            pool.mkdir()
            result = entry_check.check(ROOT, record(temp), pool=pool, probe_pool=True,
                                       run_name=f'2026_10_10_v{VERSION}_full_abc1234')
            self.assertTrue(result['ok'], result)
            self.assertTrue(result['working_version']['ok'])
            self.assertTrue(result['source_imports']['ok'])
            self.assertTrue(result['run_name']['ok'])
            self.assertTrue(result['pool']['ok'] or result['pool']['hardlinks'] is False)
            self.assertEqual(list(pool.iterdir()), [])  # the hard-link probe leaves nothing behind
            text = '\n'.join(entry_check.lines(result))
            self.assertIn('(a) working version', text)
            self.assertIn('Developer mode: OK', text)

    def test_refuses_a_version_mismatch_unless_accepted_with_a_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            path = record(temp, '0.0.26')
            result = entry_check.check(ROOT, path)
            self.assertFalse(result['ok'])
            self.assertIn('!= working version 0.0.26', result['refusals'][0])
            result = entry_check.check(ROOT, path, accept_mismatch='bisecting an old regression')
            self.assertTrue(result['ok'])
            self.assertIn('accepted: bisecting', result['warnings'][0])

    def test_refuses_an_old_tree_import(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = old_tree(temp)
            modules = dict(sys.modules, old_only=fake_module('old_only', tree / 'tools' / 'old_only.py'))
            result = entry_check.check(ROOT, record(temp), modules=modules)
            self.assertFalse(result['ok'])
            self.assertIn('module old_only', result['refusals'][0])

    def test_record_lookup_order(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / 'ws8'
            pool = workspace / 'cache' / 'asset-pool-v1'
            pool.mkdir(parents=True)
            cache_copy = record(workspace / 'cache')
            self.assertEqual(entry_check.find_record(None, workspace, pool, {}), (cache_copy, 'storage pool parent'))
            top = record(base)
            self.assertEqual(entry_check.find_record(None, workspace, pool, {})[0], top)
            self.assertEqual(entry_check.find_record(None, workspace, pool, {entry_check.ENV: 'env.json'})[0],
                             Path('env.json'))
            self.assertEqual(entry_check.find_record('given.json', workspace, pool, {entry_check.ENV: 'x'})[0],
                             Path('given.json'))
            self.assertIsNone(entry_check.find_record(None, base / 'nowhere' / 'ws', None, {})[0])

    def test_missing_record_only_warns(self):
        with tempfile.TemporaryDirectory() as temp:
            result = entry_check.check(ROOT, workspace=Path(temp) / 'a' / 'ws', environ={})
            self.assertTrue(result['ok'])
            self.assertIn('no working-version record', result['warnings'][0])

    def test_integration_head(self):
        def git(code):
            return lambda *a, **k: subprocess.CompletedProcess(a, code, '', 'fatal: bad object')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'src'
            source.mkdir()
            (source / '.git').mkdir()
            self.assertEqual(entry_check.contains_commit(source, 'abc1234', run=git(0))[0], True)
            self.assertEqual(entry_check.contains_commit(source, 'abc1234', run=git(1))[0], False)
            self.assertIsNone(entry_check.contains_commit(source, 'abc1234', run=git(128))[0])
            plain = Path(temp) / 'export'
            plain.mkdir()
            self.assertTrue(entry_check.contains_commit(plain, 'abc1234', 'abc1234def')[0])
            self.assertIsNone(entry_check.contains_commit(plain, 'abc1234')[0])
            result = entry_check.check(ROOT, record(temp, head='abc1234'), git=git(1))
            if (ROOT / '.git').exists():
                self.assertFalse(result['ok'])
                self.assertIn('integration head', result['refusals'][0])

    def test_run_name_rule(self):
        self.assertTrue(entry_check.run_name_check('2026_10_10_v0.0.35-dev1_full-try2_901f8e9', '0.0.35-dev1')[0])
        self.assertTrue(entry_check.run_name_check('2026_10_10_v0.0.35-dev1_miniwind-balmora_nogit', '0.0.35-dev1')[0])
        self.assertFalse(entry_check.run_name_check('final34b', '0.0.35-dev1')[0])

    def test_unwritable_or_missing_pool_warns(self):
        with tempfile.TemporaryDirectory() as temp:
            row = entry_check.pool_check(Path(temp) / 'missing')
            self.assertFalse(row['ok'])
            self.assertIn('missing', row['note'])
            with patch('os.access', return_value=False):
                self.assertIn('not writable', entry_check.pool_check(Path(temp))['note'])


@env_guard.isolated
class BuildEntryTests(unittest.TestCase):
    def run_build(self, argv):
        out = io.StringIO()
        with patch.object(build, 'dry_run_prerequisites', return_value={}), \
                patch('setup_build.use_environment'), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(out):
            try:
                code = build.main(argv)
            except SystemExit as stop:
                code = stop.code
        return code, out.getvalue()

    def test_developer_mode_block_accepts_and_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / 'ws'
            good = record(temp)
            code, out = self.run_build(['--dry-run', '--check', '--developer-mode', '--workspace', str(workspace),
                                        '--working-version', str(good)])
            self.assertEqual(code, 0, out)
            self.assertIn('Developer mode: OK', out)
            (Path(temp) / 'old').mkdir()
            bad = record(Path(temp) / 'old', '0.0.1')
            code, out = self.run_build(['--dry-run', '--check', '--devmode', '--workspace', str(workspace),
                                        '--working-version', str(bad)])
            self.assertEqual(code, 1)
            self.assertIn('developer mode refused the build', out)
            code, out = self.run_build(['--dry-run', '--check', '--devmode', '--workspace', str(workspace),
                                        '--working-version', str(bad), '--accept-version-mismatch', 'test'])
            self.assertEqual(code, 0, out)

    def test_default_build_has_no_block_but_the_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            code, out = self.run_build(['--dry-run', '--check', '--workspace', str(Path(temp) / 'ws')])
            self.assertEqual(code, 0, out)
            self.assertNotIn('Developer mode', out)
            code, out = self.run_build(['--dry-run', '--check', '--workspace', str(Path(temp) / 'ws'),
                                        '--working-version', str(record(temp))])
            self.assertEqual(code, 1)
            self.assertIn('need --developer-mode', out)
            tree = old_tree(temp)
            with patch.dict(sys.modules, old_only=fake_module('old_only', tree / 'tools' / 'old_only.py')):
                code, out = self.run_build(['--dry-run', '--check', '--workspace', str(Path(temp) / 'ws')])
            self.assertEqual(code, 1)
            self.assertIn('BUILD-IMAGE-STALE-PYTHONPATH-35', out)

    def test_check_entry_command(self):
        with tempfile.TemporaryDirectory() as temp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = build.main(['--check-entry', '--working-version', str(record(temp)),
                                   '--workspace', str(Path(temp) / 'ws')])
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn('Entry check: OK', out.getvalue())
            self.assertIn('(d) storage pool', out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = build.main(['--check-entry', '--json', '--working-version', str(record(temp, '0.0.1'))])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(out.getvalue())['ok'])


class ChimportEntryTests(unittest.TestCase):
    def test_cell_world_and_run_refuse_a_version_mismatch_before_any_work(self):
        import chimport
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ):
            os.environ.pop(entry_check.ENV, None)
            os.environ.pop('AMIWIND_ACCEPT_VERSION_MISMATCH', None)
            bad = record(temp, '0.0.1')
            common = ['--data-files', temp, '--palette', temp, '--out', str(Path(temp) / 'out'),
                      '--working-version', str(bad)]
            err = io.StringIO()
            with patch.object(chimport, 'convert_cell') as convert, patch.object(chimport, 'build_world') as world,                     patch.object(chimport, 'run') as run, contextlib.redirect_stderr(err),                     contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(chimport.main(['cell', '--cell=0,0', *common]), 2)
                self.assertEqual(chimport.main(['world', *common]), 2)
                self.assertEqual(chimport.main(['run', *common]), 2)
            convert.assert_not_called()
            world.assert_not_called()
            run.assert_not_called()
            self.assertIn('!= working version 0.0.1', err.getvalue())


if __name__ == '__main__':
    unittest.main()
