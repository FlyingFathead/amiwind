"""No build stage may throw away its finished units when one unit fails (incident INC-20261108-V062BUILD, cause C4:
the player view stored its units only after the whole map, so one failing body discarded every finished body and each
resume baked them all again). Every builder file that maps units through build_costs.costed_map and stores them in a
unit cache (store_files) must pass a worker that catches every exception and returns it, so the caller can store the
finished units before failing (collect-then-fail)."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _worker_catches(module, name):
    """True when the module-level function NAME has a try whose handlers catch Exception (or everything) and return."""
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Try):
                    for handler in sub.handlers:
                        caught = handler.type
                        broad = caught is None or (isinstance(caught, ast.Name) and caught.id in ('Exception', 'BaseException'))
                        if broad and any(isinstance(x, ast.Return) for x in ast.walk(handler)):
                            return True
            return False
    return None


POOL_MAPS = frozenset({'costed_map', 'ordered_map', 'completed_map', 'governed_map', 'in_order_map', 'spread_map'})


def _name(func):
    return getattr(func, 'id', getattr(func, 'attr', None))


def _stores_after_whole_map(module, label):
    """['label:line ...'] of functions that run a pool map to its end with list(...) and store units after it."""
    problems = []
    for function in ast.walk(module):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        whole = [node.lineno for node in ast.walk(function) if isinstance(node, ast.Call) and _name(node.func) == 'list'
                 and node.args and isinstance(node.args[0], ast.Call) and _name(node.args[0].func) in POOL_MAPS]
        stores = [node.lineno for node in ast.walk(function) if isinstance(node, ast.Call)
                  and _name(node.func) in ('store_files', 'store_unit')]
        if whole and any(line > min(whole) for line in stores):
            problems.append('%s:%d %s runs a pool map to its end and stores its units only after it (a stage stopped '
                            'midway keeps nothing)' % (label, min(whole), function.name))
    return problems


class UnitsKeptOnFailure(unittest.TestCase):
    def test_every_unit_cache_map_uses_a_catching_worker(self):
        problems = []
        files = sorted((ROOT / 'tools').rglob('*.py'))
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding='utf-8', errors='replace')
            if 'costed_map(' not in text or 'store_files(' not in text:
                continue
            module = ast.parse(text)
            for call in ast.walk(module):
                if not (isinstance(call, ast.Call) and getattr(call.func, 'id', getattr(call.func, 'attr', None)) == 'costed_map'):
                    continue
                if len(call.args) < 2 or not isinstance(call.args[1], ast.Name):
                    continue
                worker = call.args[1].id
                caught = _worker_catches(module, worker)
                if caught is False:
                    problems.append('%s: costed_map worker %s raises; a failing unit would discard the finished ones'
                                    % (path.relative_to(ROOT).as_posix(), worker))
        self.assertEqual(problems, [])

    def test_no_unit_is_stored_only_after_the_whole_map(self):
        """UNIT-STORED-AT-MAP-END-62: a function that runs a pool map to its end (list(costed_map(...)) and the
        like) and stores units after it keeps nothing when the map stops midway; every unit is stored the moment it
        comes back (tools/unit_store.py run_each, or a store inside the loop over the map or inside the worker)."""
        problems = []
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            text = path.read_text(encoding='utf-8', errors='replace')
            if 'store_files(' not in text and 'store_unit(' not in text:
                continue
            problems += _stores_after_whole_map(ast.parse(text), path.relative_to(ROOT).as_posix())
        self.assertEqual(problems, [])

    def test_the_check_sees_a_store_after_the_whole_map(self):
        old = ('def run_units(units, cache):\n    made = list(costed_map(UNIT_COSTS, bake, units, names, 4))\n'
               '    for unit, result in zip(units, made):\n        cache.store_files(unit, result, {})\n')
        self.assertTrue(_stores_after_whole_map(ast.parse(old), 'old.py'))
        new = ('def run_units(units, cache):\n    for unit, result in zip(units, costed_map(UNIT_COSTS, bake, units, '
               'names, 4)):\n        cache.store_files(unit, result, {})\n')
        self.assertEqual(_stores_after_whole_map(ast.parse(new), 'new.py'), [])

    def test_the_check_sees_a_raising_worker(self):
        module = ast.parse('def bake(u):\n    return u\n\ndef kept(u):\n    try:\n        return bake(u)\n'
                           '    except Exception as e:\n        return str(e)\n')
        self.assertFalse(_worker_catches(module, 'bake'))
        self.assertTrue(_worker_catches(module, 'kept'))


if __name__ == '__main__':
    unittest.main()
