# SPDX-License-Identifier: GPL-3.0-only
"""MWAD-NAME-CLASH-66: a module in tools/ never hides a package or module of src/.

tools/mwad.py had the name of the src/mwad package, so any process with tools/ before src/ on sys.path imported the
command instead of the package (TEST-WORKER-SYSPATH-32, BUILD-ACTOR-LIBRARY-MWAD-PATH-47, dev11 gate 10940). The file
now takes the package's place when imported (its package path is src/mwad) and is the command line only as a script.
THAT REPAIR IS HELD BACK in v0.0.66-dev12 (tools/mwad.py is as in v0.0.66-dev11): it changes the source analysis of
every build stage that imports mwad, so ten stages would be built again with the same outputs; it returns with
proven-equal key rows. The two tests that need it are marked as expected failures (see HELD_BACK); when the repair
returns, remove the marks. The command-line test and the package init test stay."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
TOOLS = ROOT / 'tools'


def src_names():
    return {p.stem if p.is_file() else p.name for p in SRC.iterdir()
            if (p.is_file() and p.suffix == '.py') or (p.is_dir() and (p / '__init__.py').exists())}


def tools_names():
    return {p.stem if p.is_file() else p.name for p in TOOLS.iterdir()
            if (p.is_file() and p.suffix == '.py') or (p.is_dir() and (p / '__init__.py').exists())}


HELD_BACK = ('MWAD-NAME-CLASH-66: the repair (tools/mwad.py taking the package\'s place when imported) is held back '
             'because it re-keys the build\'s stages that import mwad though no output changes; it returns with '
             'proven-equal key rows for those stages and their unit caches. Meanwhile every caller puts src before tools.')


class NameClashTests(unittest.TestCase):
    @unittest.expectedFailure  # HELD_BACK
    def test_a_tools_name_that_is_a_src_name_resolves_to_src_with_tools_first(self):
        clashes = sorted(src_names() & tools_names())
        self.assertIn('mwad', src_names())
        for name in clashes:
            # tools FIRST: the order that used to hide the package
            code = ('import sys; sys.path[:0] = [%r, %r]; import %s as m; import os; '
                    'paths = list(getattr(m, "__path__", [])) or [m.__file__]; '
                    'print(os.path.realpath(paths[0]))' % (str(TOOLS), str(SRC), name))
            done = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=str(ROOT))
            self.assertEqual(done.returncode, 0, done.stderr)
            where = Path(done.stdout.strip())
            self.assertTrue(SRC.resolve() in where.parents or where == SRC.resolve(),
                            '%s imported from %s with tools/ first, not from src/' % (name, where))

    @unittest.expectedFailure  # HELD_BACK
    def test_the_package_submodules_import_with_tools_first(self):
        code = ('import sys; sys.path[:0] = [%r, %r]; import mwad.cli, mwad.paths; '
                'print(callable(mwad.cli.main))' % (str(TOOLS), str(SRC)))
        done = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), 'True')

    def test_the_package_init_defines_no_name_that_tools_mwad_would_have_to_load(self):
        # tools/mwad.py, imported as mwad, takes the package's place through its package path but does not run
        # src/mwad/__init__.py; a name defined there would be missing for every importer with tools/ first.
        tree = ast.parse((SRC / 'mwad' / '__init__.py').read_text(encoding='utf-8'))
        body = list(tree.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]  # the docstring
        names = [type(node).__name__ for node in body]
        self.assertEqual(names, [], 'src/mwad/__init__.py now defines top-level names (%s): tools/mwad.py must then '
                                    'load those names too, or the package is incomplete when tools/ comes first'
                         % ', '.join(names))

    def test_the_command_still_runs_as_a_script(self):
        done = subprocess.run([sys.executable, '-I', str(TOOLS / 'mwad.py'), '--help'], capture_output=True, text=True,
                              cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stderr)
        for command in ('setup', 'convert', 'doctor', 'audit'):
            self.assertIn(command, done.stdout)


if __name__ == '__main__':
    unittest.main()
