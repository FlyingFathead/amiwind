# SPDX-License-Identifier: GPL-3.0-only
"""The table readers' first-minute check (tools/table_reader_check.py). No game data: the check's own rules are held
on stand-in readers and a stand-in selection.

- it is one line of the build's early checks, in the phase that runs before the first stage;
- with the base game alone, or with no data folder, it reads nothing and says nothing;
- every reader runs even when an earlier one fails, and each failure names its reader, its function and the
  selected files; a reader that ends the process is a problem too, never the end of the checks;
- a reader that returns nothing for a count it must have is a problem;
- while the readers run the selection is in the environment (the readers that still take it from there read the
  selected files, not the base game alone), and the environment is put back afterwards, also after a failure;
- a pass is recorded under a key of the game files and the readers' sources and found again; a problem is never
  recorded;
- every reader in the list names its counts' rule (MUST) and every source file of the key exists."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build_preflight  # noqa: E402
import table_reader_check as trc  # noqa: E402
from mwad.masters import MASTERS_ENV  # noqa: E402

THREE = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')


def selection(masters=THREE):
    return SimpleNamespace(masters=tuple(masters), data=Path('/data'), raw=b'', path=Path('/data/merged'), layers=[])


def reader(counts=None, must=(), error=None):
    def function(sel):
        if error is not None:
            raise error
        return counts
    function.MUST = must
    return function


class Registration(unittest.TestCase):
    def test_the_check_is_one_line_of_the_first_minute(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'table-readers']
        self.assertEqual(entry, [('table-readers', 'inputs', 'table_reader_check:table_readers')])

    def test_every_reader_names_its_rule_and_every_key_source_exists(self):
        names = [name for name, _ in trc.READERS]
        self.assertEqual(len(names), len(set(names)))
        for name, function in trc.READERS:
            self.assertIsInstance(function.MUST, tuple, name)
            self.assertTrue(function.__doc__, name)
        for rel in trc.SOURCES:
            self.assertTrue((ROOT / rel).is_file(), rel)
        self.assertIn('tools/table_reader_check.py', trc.SOURCES)


class NothingToCheck(unittest.TestCase):
    def test_the_base_game_alone_and_no_data_folder(self):
        said = []
        for args, masters in ((SimpleNamespace(data_files='/data', workspace=None), ('Morrowind.esm',)),
                              (SimpleNamespace(data_files='/data', workspace=None), ()),
                              (SimpleNamespace(data_files=None, workspace=None), THREE),
                              (None, THREE)):
            context = build_preflight.EarlyContext('inputs', args, masters=masters, log=said.append)
            with mock.patch.object(trc, 'reader_problems', side_effect=AssertionError('read')):
                self.assertEqual(trc.table_readers(context), [])
        self.assertEqual(said, [])


class TheReaders(unittest.TestCase):
    def test_every_reader_runs_and_each_failure_is_named(self):
        ran = []

        def good(sel):
            ran.append('good')
            return {'rows': 3}
        good.MUST = ('rows',)

        def last(sel):
            ran.append('last')
            return {'rows': 1, 'others': 0}
        last.MUST = ('rows',)
        said = []
        problems = trc.reader_problems(selection(), [
            ('first', reader(error=ValueError('a second record of an id'))),
            ('good', good),
            ('exits', reader(error=SystemExit(3))),
            ('empty', reader(counts={'rows': 0, 'cells': 5}, must=('rows', 'cells'))),
            ('none', reader(counts=None, must=('rows',))),
            ('last', last)], log=said.append)
        self.assertEqual(ran, ['good', 'last'])
        self.assertEqual(len(problems), 4)
        self.assertIn('reader first', problems[0])
        self.assertIn('ValueError: a second record of an id', problems[0])
        self.assertIn('Morrowind.esm, Tribunal.esm, Bloodmoon.esm', problems[0])
        self.assertIn('reader exits', problems[1])
        self.assertIn('SystemExit', problems[1])
        self.assertIn('reader empty', problems[2])
        self.assertIn('reads nothing where the game holds rows: rows', problems[2])
        self.assertNotIn('cells', problems[2].split('rows: ')[1].split(' (selected')[0])
        self.assertIn('reader none', problems[3])
        self.assertTrue(any('table reader good: 3 rows' in line for line in said))
        self.assertTrue(any('table reader last: 1 rows, 0 others' in line for line in said))

    def test_a_selection_that_cannot_be_made_is_the_one_problem(self):
        def broken():
            raise ValueError('Unknown master X.esm')
        problems = trc.reader_problems(broken, [('never', reader(error=AssertionError('ran')))], log=lambda _: None)
        self.assertEqual(len(problems), 1)
        self.assertIn('cannot be merged and read', problems[0])
        self.assertIn('Unknown master X.esm', problems[0])

    def test_the_selection_is_in_the_environment_only_while_the_readers_run(self):
        seen = []

        def looks(sel):
            seen.append(os.environ.get(MASTERS_ENV))
            return {}
        looks.MUST = ()
        for before in (None, 'Morrowind.esm'):
            with mock.patch.dict(os.environ, {}, clear=False):
                if before is None:
                    os.environ.pop(MASTERS_ENV, None)
                else:
                    os.environ[MASTERS_ENV] = before
                trc.reader_problems(selection(), [('looks', looks), ('fails', reader(error=KeyError('x')))],
                                    log=lambda _: None)
                self.assertEqual(os.environ.get(MASTERS_ENV), before)
        self.assertEqual(seen, ['Morrowind.esm,Tribunal.esm,Bloodmoon.esm'] * 2)


class ThePassRecord(unittest.TestCase):
    def context(self, workspace, said):
        args = SimpleNamespace(data_files='/data', workspace=str(workspace))
        return build_preflight.EarlyContext('inputs', args, masters=THREE, log=said.append)

    def test_a_pass_is_recorded_and_found_and_a_problem_never_is(self):
        with tempfile.TemporaryDirectory(prefix='aw-table-readers-') as tmp:
            said, calls = [], []

            def problems_of(result):
                def run(make, readers=None, log=print):
                    calls.append(result)
                    return list(result)
                return run
            with mock.patch.object(trc, 'check_key', return_value='k1'):
                with mock.patch.object(trc, 'reader_problems', side_effect=problems_of(['reader x fails'])):
                    self.assertEqual(trc.table_readers(self.context(tmp, said)), ['reader x fails'])
                self.assertFalse((Path(tmp) / trc.CACHE_FOLDER).exists())
                with mock.patch.object(trc, 'reader_problems', side_effect=problems_of([])):
                    self.assertEqual(trc.table_readers(self.context(tmp, said)), [])
                self.assertTrue((Path(tmp) / trc.CACHE_FOLDER / 'k1.json').is_file())
                with mock.patch.object(trc, 'reader_problems', side_effect=AssertionError('read again')):
                    self.assertEqual(trc.table_readers(self.context(tmp, said)), [])
                self.assertTrue(any('passed before' in line for line in said))
            with mock.patch.object(trc, 'check_key', return_value='k2'):       # other files or readers: read again
                with mock.patch.object(trc, 'reader_problems', side_effect=problems_of([])):
                    self.assertEqual(trc.table_readers(self.context(tmp, said)), [])
            self.assertEqual(len(calls), 3)

    def test_the_key_moves_with_a_game_file_and_with_a_reader_source(self):
        with tempfile.TemporaryDirectory(prefix='aw-table-readers-') as tmp:
            data, root = Path(tmp) / 'data', Path(tmp) / 'root'
            data.mkdir()
            for name in THREE:
                (data / name).write_bytes(name.encode())
            for rel in trc.SOURCES:
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text('source of ' + rel, encoding='utf-8')
            first = trc.check_key(data, THREE, root)
            self.assertEqual(first, trc.check_key(data, THREE, root))
            self.assertNotEqual(first, trc.check_key(data, THREE[:2], root))
            (data / 'Bloodmoon.esm').write_bytes(b'another file')
            second = trc.check_key(data, THREE, root)
            self.assertNotEqual(first, second)
            (root / 'tools/prepare_magic.py').write_text('a changed reader', encoding='utf-8')
            self.assertNotEqual(second, trc.check_key(data, THREE, root))


if __name__ == '__main__':
    unittest.main()
