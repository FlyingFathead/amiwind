# SPDX-License-Identifier: GPL-3.0-only
"""No undefined names in the builder modules (BUILD-FINALIZE-TORCHTEST-32).

A name used in a function but bound nowhere in it, in an enclosing function, in the module or in
builtins is a NameError waiting for the end of a long build. Python's own AST, no extra tools.
"""
import ast
import builtins
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['tools/build.py', 'tools/build_aga.py', 'tools/build_parallel.py', 'tools/build_summary.py',
           'tools/build_jobs.py', 'tools/build_profile.py', 'tools/build_cache.py', 'tools/world_volumes.py',
           'tools/build_windows_xdftool.py']
BUILTINS = set(dir(builtins)) | {'__file__', '__name__', '__doc__', '__spec__', '__builtins__'}


def bound_here(node):
    """Names bound directly in this function or module (not inside nested functions/classes)."""
    names = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for x in a.args + a.kwonlyargs + getattr(a, 'posonlyargs', []):
            names.add(x.arg)
        if a.vararg: names.add(a.vararg.arg)
        if a.kwarg: names.add(a.kwarg.arg)
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name); continue
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): names.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names: names.add((al.asname or al.name).split('.')[0])
        elif isinstance(n, ast.ExceptHandler) and n.name: names.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)): names.update(n.names)
        elif isinstance(n, ast.arg): names.add(n.arg)
        elif isinstance(n, ast.MatchAs) and n.name: names.add(n.name)
        stack.extend(ast.iter_child_nodes(n))
    return names


def undefined(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = []

    def visit(node, scope):
        scope = scope | bound_here(node)
        stack = list(ast.iter_child_nodes(node))
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                for d in getattr(n, 'decorator_list', []) + n.args.defaults + n.args.kw_defaults:
                    if d is not None: stack.append(d)
                visit(n, scope); continue
            if isinstance(n, ast.ClassDef):
                visit(n, scope); continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in scope:
                found.append('%s:%d %s' % (path.name, n.lineno, n.id))
            stack.extend(ast.iter_child_nodes(n))

    visit(tree, BUILTINS)
    return found


class BuilderUndefinedNameTests(unittest.TestCase):
    def test_no_undefined_names(self):
        for rel in MODULES:
            path = ROOT / rel
            if not path.exists():
                continue
            with self.subTest(module=rel):
                self.assertEqual(undefined(path), [])

    def test_check_catches_the_finalize_bug(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            sample = Path(temp) / 'sample.py'
            sample.write_text('def image():\n    report = 1\n    return finalize()\n\n'
                              'def finalize():\n    return {"torch_test": report}\n', encoding='utf-8')
            self.assertEqual(undefined(sample), ['sample.py:6 report'])


if __name__ == '__main__':
    unittest.main()
