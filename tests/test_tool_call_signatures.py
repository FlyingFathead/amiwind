# SPDX-License-Identifier: GPL-3.0-only
"""Every call between builder modules matches the callee's current signature.

BUILD-ACTOR-CONTACT-CALL-32: prepare_seyda_regions.convert gained required
keyword arguments in v0.0.27 and the actor-contact stage kept calling it the
old way; only a from-scratch build found it. This static check binds every
call to a top-level function of a tools/ or src/ module (imported by name, as
module.attribute, or defined in the same module) against that function's
parameters, without importing or running anything.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module_files():
    files = {path.stem: path for path in sorted((ROOT / 'tools').glob('*.py'))}
    for path in sorted((ROOT / 'src').rglob('*.py')):
        parts = path.relative_to(ROOT / 'src').with_suffix('').parts
        name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
        files.setdefault(name, path)
    return files


class Signature:
    def __init__(self, node):
        a = node.args
        positional = a.posonlyargs + a.args
        self.posonly = [p.arg for p in a.posonlyargs]
        self.positional = [p.arg for p in positional]
        self.positional_required = self.positional[:len(positional) - len(a.defaults)]
        self.vararg = a.vararg is not None
        self.kwonly = [p.arg for p in a.kwonlyargs]
        self.kwonly_required = [p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
        self.kwarg = a.kwarg is not None

    def bind(self, positional, keywords, method=False):
        """Return a problem description, or None when the call binds."""
        params = self.positional[1:] if method else self.positional
        required = [p for p in self.positional_required if p in params]
        if positional is not None and positional > len(params) and not self.vararg:
            return f'{positional} positional arguments for {len(params)} parameters'
        filled = set(params[:positional or 0])
        if keywords is None:
            return None
        for name in keywords:
            if name in filled:
                return f'argument {name!r} given twice'
            if name in self.posonly or (name not in params and name not in self.kwonly and not self.kwarg):
                return f'unexpected keyword argument {name!r}'
        filled |= set(keywords)
        if positional is not None:
            missing = [p for p in required if p not in filled]
            if missing:
                return 'missing required arguments ' + ', '.join(missing)
        missing = [p for p in self.kwonly_required if p not in filled]
        if missing:
            return 'missing required keyword arguments ' + ', '.join(missing)
        return None


def decorator_name(node):
    node = node.func if isinstance(node, ast.Call) else node
    return node.id if isinstance(node, ast.Name) else getattr(node, 'attr', None)


def top_level(tree):
    functions, classes = {}, {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Wrapping decorators may change the call shape; caches do not.
            if not all(decorator_name(d) in ('lru_cache', 'cache') for d in node.decorator_list):
                continue
            functions[node.name] = Signature(node)
        elif isinstance(node, ast.ClassDef):
            classes[node.name] = node
    # Names rebound at module level after their definition are not checked.
    rebound = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                rebound |= {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}
    return {k: v for k, v in functions.items() if k not in rebound}, classes


def local_names(function):
    """Names a function binds itself (parameters, assignments, loops, ...)."""
    names = {p.arg for p in function.args.posonlyargs + function.args.args + function.args.kwonlyargs}
    names |= {p.arg for p in (function.args.vararg, function.args.kwarg) if p}
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not function:
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def stale_calls():
    files = module_files()
    parsed, signatures = {}, {}
    for name, path in files.items():
        parsed[name] = ast.parse(path.read_text(encoding='utf-8'), str(path))
        signatures[name] = top_level(parsed[name])[0]
    problems = []
    checked = 0
    for name, tree in parsed.items():
        own = signatures[name]
        # Module-wide import bindings: alias -> (module, function) or alias -> module.
        imported, modules = {}, {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in signatures:
                for alias in node.names:
                    if alias.name in signatures[node.module]:
                        imported[alias.asname or alias.name] = (node.module, alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in signatures and (alias.asname or '.' not in alias.name):
                        modules[alias.asname or alias.name] = alias.name

        def visit(node, shadowed):
            nonlocal checked
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                inner = local_names(node) if not isinstance(node, ast.Lambda) else \
                    {p.arg for p in node.args.args + node.args.kwonlyargs}
                # Names bound by an import inside the function stay checkable.
                imports = {alias.asname or alias.name for n in ast.walk(node) if isinstance(n, ast.ImportFrom)
                           for alias in n.names}
                shadowed = shadowed | (inner - imports)
            if isinstance(node, ast.Call):
                target = None
                func = node.func
                if isinstance(func, ast.Name) and func.id not in shadowed:
                    if func.id in imported:
                        target = imported[func.id]
                    elif func.id in own and func.id not in imported:
                        target = (name, func.id)
                elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                      and func.value.id in modules and func.value.id not in shadowed
                      and func.attr in signatures[modules[func.value.id]]):
                    target = (modules[func.value.id], func.attr)
                if target:
                    positional = None if any(isinstance(a, ast.Starred) for a in node.args) else len(node.args)
                    keywords = None if any(k.arg is None for k in node.keywords) else [k.arg for k in node.keywords]
                    problem = signatures[target[0]][target[1]].bind(positional, keywords)
                    checked += 1
                    if problem:
                        problems.append(f'{files[name].relative_to(ROOT).as_posix()}:{node.lineno}: '
                                        f'{target[0]}.{target[1]}(): {problem}')
            for child in ast.iter_child_nodes(node):
                visit(child, shadowed)

        visit(tree, frozenset())
    return problems, checked


class ToolCallSignatures(unittest.TestCase):
    def test_no_stale_calls_between_builder_modules(self):
        problems, checked = stale_calls()
        self.assertGreater(checked, 500, 'the checker must actually bind calls')
        self.assertEqual(problems, [])

    def test_checker_finds_the_actor_contact_regression(self):
        tree = ast.parse('def convert(source, destination, *, source_map, palette, ericw_bin, threads=1):\n  pass\n')
        signature = top_level(tree)[0]['convert']
        self.assertIn('missing required keyword arguments', signature.bind(2, []))
        self.assertIsNone(signature.bind(2, ['source_map', 'palette', 'ericw_bin']))
        self.assertIn('unexpected keyword', signature.bind(2, ['source_map', 'palette', 'ericw_bin', 'jobs']))
        self.assertIn('positional', signature.bind(3, ['source_map', 'palette', 'ericw_bin']))


if __name__ == '__main__':
    unittest.main()
