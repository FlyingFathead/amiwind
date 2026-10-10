"""Prerendered store: hits are byte-identical, changes miss, failed builds store nothing, list/verify/prune/import."""
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import build_cache  # noqa: E402
import prerendered  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402
from test_build_cache import STAGE_D, make_repository, metadata, steps_for, tree  # noqa: E402
import env_guard  # noqa: E402

MANIFESTS = os.name == 'posix'
FAIL = '''
import sys
sys.exit('gate failed: the fixture refuses this result')
'''


def source_record(repository):
    return {path.relative_to(repository).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(repository.rglob('*.py'))}


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class EntryFolderTests(unittest.TestCase):
    def test_versions_area_and_kind_are_in_the_path(self):
        meta = {'runtime_version': '0.0.33-dev1', 'chim_version': '0.1.0', 'world_format': '0.5'}
        chim = prerendered.entry_folder('chim', 'f' * 64, meta, ['x', '--area', 'balmora', '--area', 'seyda'])
        self.assertEqual(chim, 'chim/0.1.0/0.5/balmora+seyda/' + 'f' * 64)
        other_format = prerendered.entry_folder('chim', 'f' * 64, dict(meta, world_format='0.6'), ['--area', 'balmora'])
        self.assertEqual(other_format, 'chim/0.1.0/0.6/balmora/' + 'f' * 64)
        self.assertEqual(prerendered.entry_folder('balmora-interiors', 'a' * 64, meta, []), 'interiors/' + 'a' * 64)
        self.assertEqual(prerendered.entry_folder('town-vivec_arena', 'b' * 64, meta, []),
                         'legacy/0.0.33-dev1/town-vivec_arena/' + 'b' * 64)
        self.assertEqual(prerendered.entry_folder('census', 'c' * 64, meta, []), 'stages/0.0.33-dev1/census/' + 'c' * 64)
        self.assertEqual(prerendered.entry_folder('chim', 'd' * 64, {}, []), 'chim/unknown/unknown/world/' + 'd' * 64)

    def test_stage_selection(self):
        self.assertTrue(prerendered.selected('chim', 'default'))
        self.assertTrue(prerendered.selected('town-vivec_arena', 'default'))
        self.assertFalse(prerendered.selected('census', 'default'))
        self.assertTrue(prerendered.selected('census', 'all'))
        self.assertEqual(prerendered.parse_stages('beta, delta'), ['beta', 'delta'])
        with self.assertRaises(ValueError):
            prerendered.parse_stages('../x')

    def test_release_versions_write_but_do_not_read(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(prerendered.configure(folder, '0.0.33-dev1', root=Path(folder))['read'])
            final = prerendered.configure(folder, '0.0.33', root=Path(folder))
            self.assertFalse(final['read'])
            self.assertTrue(final['write'])
            self.assertIn('from-scratch', final['read_refused'])
            self.assertTrue(prerendered.configure(folder, '0.0.33-rc1', allow_release=True, root=Path(folder))['read'])

    def test_hard_links_across_file_systems_fall_back_to_copies(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source.bin', Path(folder) / 'target.bin'
            source.write_bytes(b'stored')
            with patch('os.link', side_effect=OSError(errno.EXDEV, 'cross-device link')):
                temporary = build_cache._copy_verified(source, target, hashlib.sha256(b'stored').hexdigest(), 0o644, True)
            self.assertEqual(temporary.read_bytes(), b'stored')
            self.assertEqual(os.stat(temporary).st_ino != os.stat(source).st_ino, True)

    def test_the_chim_unit_cache_is_not_part_of_the_fingerprint(self):
        # BUILD-CACHE-CHIM-UNITS-33: the unit cache keys units by their own fingerprints; hashing the
        # folder changed the chim stage's fingerprint whenever a build added units.
        with tempfile.TemporaryDirectory() as folder:
            run, units = Path(folder) / 'workspace' / 'build' / 'run', Path(folder) / 'workspace' / 'cache' / 'chim-units'
            units.mkdir(parents=True)
            command = [sys.executable, str(ROOT / 'tools' / 'chim_build.py'), '--unit-cache', str(units), '--out',
                       str(run / 'chim-world')]
            first, _ = build_cache.external_inputs('chim', command, run, {})
            (units / 'mesh').mkdir()
            (units / 'mesh' / 'unit.pickle').write_bytes(b'unit')
            second, _ = build_cache.external_inputs('chim', command, run, {})
        self.assertEqual(first, second)
        self.assertEqual(list(first.values()), ['not hashed (content-addressed cache)'])

    def test_the_commit_is_read_without_git(self):
        with tempfile.TemporaryDirectory() as folder:
            git = Path(folder) / '.git'
            (git / 'refs' / 'heads').mkdir(parents=True)
            (git / 'HEAD').write_text('ref: refs/heads/topic\n')
            (git / 'refs' / 'heads' / 'topic').write_text('a' * 40 + '\n')
            self.assertEqual(prerendered._read_head(folder), 'a' * 40)
            (git / 'refs' / 'heads' / 'topic').unlink()
            (git / 'packed-refs').write_text('# pack-refs\n' + 'b' * 40 + ' refs/heads/topic\n')
            self.assertEqual(prerendered._read_head(folder), 'b' * 40)
            self.assertIsNone(prerendered._read_head(Path(folder) / 'missing'))

    def test_builder_flags_inspect_the_store(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(build.main(['--prerendered', 'list', folder]), 0)
            self.assertEqual(build.main(['--prerendered', 'verify', folder]), 0)
            self.assertEqual(build.main(['--prerendered', 'prune', folder]), 0)
            with self.assertRaises(SystemExit) as stopped, contextlib.redirect_stderr(io.StringIO()):
                build.main(['--prerendered', 'verify'])
            self.assertEqual(stopped.exception.code, 1)
        self.assertIn('0 entries', output.getvalue())
        self.assertIn('0 removal candidates', output.getvalue())


class StoreBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / 'repo'
        self.data = self.root / 'data'
        self.data.mkdir()
        make_repository(self.repository)
        (self.repository / '.git').mkdir()
        (self.repository / '.git' / 'HEAD').write_text('c' * 40)
        self.store = self.root / 'store'

    def tearDown(self):
        self.temp.cleanup()

    def build(self, name, store=True, stages='all', version='0.0.0-dev1', parallel=False, workspace='workspace',
              steps=None, expect_failure=False):
        run = self.root / workspace / 'build' / name
        index = build_cache.SourceIndex(self.repository)
        meta = metadata()
        meta.update(compiler_jobs=2 if parallel else 1, runtime_version=version, python=sys.version,
                    source_sha256=source_record(self.repository))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            config = prerendered.configure(self.store, version, stages=stages, root=self.repository) if store else None
            steps = build_cache.prepare(steps or steps_for(self.repository, run, self.data), run, meta,
                                        index=index, prerendered=config)
            try:
                if parallel:
                    execute_parallel(steps, run, meta, self.repository)
                else:
                    build.execute(steps, run, meta)
            except RuntimeError:
                if not expect_failure:
                    raise
        state = json.loads((run / 'build-state.json').read_text())
        return run, state, output.getvalue()

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_hits_are_byte_identical_to_a_fresh_build(self):
        first, state, printed = self.build('first')
        self.assertEqual(state['status'], 'passed')
        self.assertEqual(sorted(state['stage_cache']['prerendered']['misses']), ['alpha', 'beta', 'delta', 'gamma'])
        entries = prerendered.Store(self.store).entries()
        self.assertEqual(len(entries), 4)
        summary = json.loads((first / 'profile' / 'prerendered.json').read_text())
        self.assertEqual(sorted(summary['stored']), ['alpha', 'beta', 'delta', 'gamma'])
        self.assertTrue(all(path.startswith('stages/0.0.0-dev1/') for path in summary['stored'].values()))
        receipt = json.loads((self.store / summary['stored']['alpha'] / 'receipt.json').read_text())
        for key in ('source_commit', 'builder_commit', 'inputs_digest', 'size', 'created', 'fingerprint', 'versions'):
            self.assertIn(key, receipt)
        self.assertEqual(receipt['fingerprint'], state['stage_cache']['fingerprints']['alpha'])
        self.assertEqual(receipt['source_commit'], 'c' * 40)   # the checkout's HEAD, read without git
        # alpha's entry is alpha's own output: the scratch file gamma deletes later is in it.
        self.assertTrue((self.store / summary['stored']['alpha'] / 'files' / 'alpha' / 'scratch.tmp').is_file())
        index = json.loads((self.store / 'index.json').read_text())
        self.assertEqual(set(index['entries']), set(entries))
        # Another workspace: every stage from the store, the same bytes as a build without it.
        second, state, printed = self.build('second', workspace='elsewhere')
        self.assertEqual(sorted(state['stage_cache']['prerendered']['hits']), ['alpha', 'beta', 'delta', 'gamma'])
        for entry in state['steps']:
            self.assertIn('from prerendered ', entry['reused'])
        self.assertIn('from prerendered', (second / 'logs' / '01-alpha.log').read_text())
        fresh, _, _ = self.build('fresh', store=False, workspace='plain')
        self.assertEqual(tree(second), tree(fresh))
        self.assertFalse((second / 'alpha' / 'scratch.tmp').exists())
        third, state, _ = self.build('third', workspace='parallel', parallel=True)
        self.assertEqual(tree(third), tree(fresh))
        uses = [row for row in prerendered.Store(self.store).usage() if row['action'] == 'used']
        self.assertEqual(len(uses), 8)

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_a_changed_input_misses_and_is_stored_beside(self):
        self.build('first')
        (self.repository / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        second, state, _ = self.build('second', workspace='other')
        record = state['stage_cache']['prerendered']
        self.assertEqual(sorted(record['hits']), ['alpha', 'beta', 'gamma'])
        self.assertEqual(record['misses'], {'delta': 'not stored'})
        self.assertTrue((second / 'delta' / 'd.txt').read_text().startswith('D:'))
        self.assertEqual(len(prerendered.Store(self.store).entries()), 5)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            prerendered.action_prune(prerendered.Store(self.store))
        self.assertIn('1 removal candidates', output.getvalue())
        self.assertIn('superseded', output.getvalue())
        self.assertEqual(len(prerendered.Store(self.store).entries()), 5)   # prune never deletes
        self.assertIn('a newer delta entry', output.getvalue())
        # The superseded entry is the older one, whatever the fingerprints (entry folder names) are.
        store = prerendered.Store(self.store)
        deltas = sorted((row for row in prerendered.rows(store) if row['stage'] == 'delta'), key=lambda row: row['last_event'])
        old, new = deltas
        self.assertIn(old['path'], output.getvalue())
        self.assertNotIn(new['path'], output.getvalue())
        # An entry a build used recently is never a candidate (another line may still build that code);
        # the entry it was superseded by is then the older event and becomes the candidate.
        store.log([{'time': prerendered.now(), 'action': 'used', 'stage': 'delta', 'path': old['path'],
                    'run': 'other-line', 'status': 'passed'}])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            prerendered.action_prune(store)
        self.assertNotIn(old['path'], output.getvalue())
        self.assertIn('1 removal candidates', output.getvalue())
        self.assertIn(new['path'], output.getvalue())
        # Same second, any folder order: the decision follows the usage log (BUILD-CACHE-OVERBROAD-33 merge).
        for reverse in (False, True):
            table = sorted(prerendered.rows(store), key=lambda row: row['path'], reverse=reverse)
            with patch.object(prerendered, 'rows', lambda _store, table=table: [dict(row, created='2026-10-09T00:00:00Z', last_used=None) for row in table]),                     contextlib.redirect_stdout(io.StringIO()) as output:
                prerendered.action_prune(store)
            self.assertNotIn(old['path'], output.getvalue())
            self.assertIn(new['path'], output.getvalue())

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_a_build_that_fails_a_later_gate_stores_nothing(self):
        (self.repository / 'tools' / 'gate.py').write_text(FAIL)
        run = self.root / 'workspace' / 'build' / 'failed'
        steps = steps_for(self.repository, run, self.data) + [
            ('gate', [sys.executable, str(self.repository / 'tools' / 'gate.py'), '--scene', str(run / 'delta')])]
        _, state, printed = self.build('failed', steps=steps, expect_failure=True)
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(prerendered.Store(self.store).entries(), {})
        self.assertFalse(any((self.store / '.pending').glob('*')))
        self.assertIn('nothing stored, the build failed', printed)

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_only_chosen_stages_are_stored(self):
        _, state, _ = self.build('first', stages='default')
        self.assertEqual(prerendered.Store(self.store).entries(), {})   # fixture stages are not default stages
        _, state, _ = self.build('second', stages='beta,delta', workspace='other')
        stored = {prerendered.Store(self.store).receipt(folder)['stage']
                  for folder in prerendered.Store(self.store).entries().values()}
        self.assertEqual(stored, {'beta', 'delta'})

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_list_and_verify_and_a_damaged_entry_is_never_used(self):
        self.build('first')
        self.build('second', workspace='other')
        store = prerendered.Store(self.store)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(prerendered.main(['list', str(self.store)]), 0)
            self.assertEqual(prerendered.action_verify(store), 0)
        self.assertIn('4 entries', output.getvalue())
        self.assertIn('used 1x (second)', output.getvalue())
        self.assertIn('0 damaged', output.getvalue())
        alpha = next(folder for folder in store.entries().values() if store.receipt(folder)['stage'] == 'alpha')
        blob = alpha / 'files' / 'alpha' / 'deep' / 'blob.bin'
        os.chmod(blob, 0o644)
        blob.write_bytes(b'damaged' + blob.read_bytes()[7:])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(prerendered.action_verify(store), 1)
        self.assertIn('DAMAGED', output.getvalue())
        third, state, _ = self.build('third', workspace='third')
        self.assertIn('refused', (third / 'logs' / '01-alpha.log').read_text())
        fresh, _, _ = self.build('fresh', store=False, workspace='plain')
        self.assertEqual(tree(third), tree(fresh))

    @unittest.skipUnless(MANIFESTS, 'stage wrapper and manifests are exercised on POSIX')
    def test_import_of_an_earlier_run_needs_the_code_that_built_it(self):
        first, _, _ = self.build('first', store=False)
        store = prerendered.Store(self.store)
        moved = self.root / 'moved-checkout'
        shutil.copytree(self.repository, moved)
        (moved / 'tools' / 'stage_d.py').write_text(STAGE_D.replace("'d:'", "'D:'"))
        with self.assertRaisesRegex(ValueError, 'not the code that built'):
            prerendered.action_import(store, first, moved, 'all')
        with contextlib.redirect_stdout(io.StringIO()):
            summary = prerendered.action_import(store, first, self.repository, 'all', source_commit='fixture')
        # gamma replaced alpha's scratch file later in the run: alpha's own output is gone from it
        self.assertEqual(sorted(summary['stored']), ['beta', 'delta', 'gamma'])
        self.assertIn('replaced later in the run by gamma', summary['not_stored']['alpha'])
        receipt = store.receipt(store.root / summary['stored']['beta'])
        self.assertEqual(receipt['source_commit'], 'fixture')
        self.assertIn('imported from first', receipt['adopted'])
        self.assertFalse((first / 'profile' / 'prerendered.json').exists())   # the old run is only read
        second, state, _ = self.build('second', workspace='other')
        self.assertEqual(sorted(state['stage_cache']['prerendered']['hits']), ['beta', 'delta', 'gamma'])
        fresh, _, _ = self.build('fresh', store=False, workspace='plain')
        self.assertEqual(tree(second), tree(fresh))


if __name__ == '__main__':
    unittest.main()
