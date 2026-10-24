# SPDX-License-Identifier: GPL-3.0-only
"""Exact code keys of the per-unit caches (tools/code_key.py; BUILD-CACHE-CLOSURE-WIDE-33,
BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46): a unit is keyed on the code its worker can reach, without comments;
a code change that leaves a unit's result byte-identical keeps the keys of the units after it (early cutoff); keys
of the previous form are still found; a worker that runs code outside its key stores nothing."""
import contextlib
import importlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
import code_key  # noqa: E402
import chim.units as units  # noqa: E402


def fresh():
    code_key._KEYS.clear()
    code_key._INDEX.clear()
    units._TOOL_HASH.clear()


def copy_repository(target):
    for folder in ('tools', 'src', 'config'):
        shutil.copytree(ROOT / folder, target / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def insert_after_docstring(text, function, line):
    head = text.index(function)
    end = text.index('"""', text.index('"""', head) + 3) + 3
    return text[:end] + '\n' + line + text[end:]


class NormalizedTextTests(unittest.TestCase):
    def test_comments_and_spacing_do_not_count_tokens_do(self):
        base = code_key.normalized_text('x = 1  # one\n\ndef f(a):\n    return a+1\n')
        self.assertEqual(base, code_key.normalized_text('x = 1  # the first\ndef f(a):\n\n    return a + 1  # sum\n'))
        self.assertNotEqual(base, code_key.normalized_text('x = 2\ndef f(a):\n    return a+1\n'))
        self.assertNotEqual(base, code_key.normalized_text('x = 1\ndef f(a):\n    return a-1\n'))
        # a docstring is a token (it may be read at run time)
        self.assertNotEqual(code_key.normalized_text('def f():\n    "a"\n'), code_key.normalized_text('def f():\n    "b"\n'))
        # build_cache's default-value rows of import-time code are kept as they are
        self.assertIn('ROW \0defaults f: x', code_key.normalized_text('\0defaults f: x\nY = 1\n'))


class CodeKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        self.write('tools/entry_mod.py', 'from side import helper\ndef work(thing):\n    return helper() + thing.run()\n'
                                         'def other():\n    return 0\n')
        self.write('tools/side.py', 'LIMIT = 4  # a limit\ndef helper():\n    return LIMIT\n'
                                    'def unused():\n    return 2\n')
        self.write('tools/things.py', 'class Thing:\n    def run(self):\n        return 1\n')
        fresh()

    def tearDown(self):
        fresh()
        for name in ('entry_mod', 'side', 'things'):
            sys.modules.pop(name, None)
        if str(self.root / 'tools') in sys.path:
            sys.path.remove(str(self.root / 'tools'))
        self.temp.cleanup()

    def write(self, rel, text):
        (self.root / rel).write_text(text)

    def key(self, entries=(('tools/entry_mod.py', 'work'),)):
        fresh()
        return code_key.code_key(entries, (), self.root)['digest']

    def test_the_key_is_the_reached_code(self):
        original = self.key()
        side = (self.root / 'tools/side.py').read_text()
        for name, edited in (('unreached function', side.replace('return 2', 'return 3')),
                             ('comment', side.replace('# a limit', '# the most'))):
            self.write('tools/side.py', edited)
            self.assertEqual(self.key(), original, name)
        self.write('tools/side.py', side.replace('return LIMIT', 'return LIMIT + 1'))
        self.assertNotEqual(self.key(), original)
        self.write('tools/side.py', side.replace('LIMIT = 4', 'LIMIT = 5'))
        self.assertNotEqual(self.key(), original)

    def test_the_trace_names_code_the_key_does_not_hold(self):
        sys.path.insert(0, str(self.root / 'tools'))
        entry = importlib.import_module('entry_mod')
        things = importlib.import_module('things')
        tracer = code_key.Tracer(self.root)
        try:
            tracer.begin()
            self.assertEqual(entry.work(things.Thing()), 5)
            tracer.end()
            ran = tracer.take()
        finally:
            tracer.close()
        if ran is None:
            self.skipTest('no sys.monitoring')
        self.assertIn(('tools/entry_mod.py', 'work'), ran)
        self.assertIn(('tools/things.py', 'Thing'), ran)
        key = code_key.code_key((('tools/entry_mod.py', 'work'),), (), self.root)
        # Thing.run runs on an object the worker is handed, from a module the worker does not import: the reach
        # cannot see it (a class of a reached module is part of that module's import-time code: covered)
        self.assertEqual(code_key.uncovered(ran, key, self.root), [('tools/things.py', 'Thing')])
        fresh()
        key = code_key.code_key((('tools/entry_mod.py', 'work'), ('tools/things.py', '<top>')), (), self.root)
        self.assertEqual(code_key.uncovered(ran, key, self.root), [])

    def test_a_key_neutral_module_is_never_read(self):
        # BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47: listing a key-neutral module's units to stop them read the file, and
        # the NPC gallery stage (which makes its model keys here) then read a file its fingerprint leaves out: the
        # stage was never reused. The stop is by path now; the key is the same as with the listed units.
        from build_cache import SourceIndex
        (self.root / 'tools/chim').mkdir()
        self.write('tools/chim/__init__.py', '')
        self.write('tools/chim/units.py', 'def run_units(items):\n    return list(items)\n')
        self.write('tools/entry_mod.py', 'from side import helper\nfrom chim import units\n'
                                         'def work(thing):\n    return units.run_units([helper() + thing.run()])\n')
        read = []
        symbols = SourceIndex._module_symbols

        def recording(index, relative):
            read.append(relative)
            return symbols(index, relative)
        with patch.object(SourceIndex, '_module_symbols', recording):
            key = code_key.code_key((('tools/entry_mod.py', 'work'),), (), self.root)
        self.assertNotIn('tools/chim/units.py', read)
        self.assertNotIn('tools/chim/units.py', key['files'])
        self.assertIn('tools/side.py', key['files'])
        fresh()
        index = code_key.source_index(self.root)
        listed = frozenset(('tools/chim/units.py', unit) for unit in
                           {'<top>', '<main>', *index._module_symbols('tools/chim/units.py')['units']})
        python, _, _, _ = index.entry_units(self.root / 'tools/entry_mod.py', 'work', stop=listed)
        self.assertEqual(set(key['files']), set(python))

    def test_the_gallery_model_key_reads_no_key_neutral_module(self):
        # the real NPC gallery model key (tools/gallery_cache.py CODE_ENTRIES), as the stage makes it
        from build_cache import SourceIndex
        import gallery_cache
        read = []
        symbols = SourceIndex._module_symbols

        def recording(index, relative):
            read.append(relative)
            return symbols(index, relative)
        fresh()
        with patch.object(SourceIndex, '_module_symbols', recording):
            key = code_key.code_key(gallery_cache.CODE_ENTRIES, gallery_cache.CODE_DATA, ROOT)
        self.assertFalse(key['uncertain'])
        self.assertEqual(sorted(code_key.KEY_NEUTRAL & set(read)), [])


class ChimUnitKeyTests(unittest.TestCase):
    def tearDown(self):
        fresh()

    def test_collision_change_keeps_terrain_variant_and_pvs_keys(self):
        """The v0.0.46-dev1 case: a walkable-surface hull change in tools/mesh_geometry.py (new statements in
        collision_parts and surface_loss_depth, a comment on a constant) rekeys the mesh units and the collision
        surface gate, which run it, and no other kind; an edit to the terrain's own code rekeys the terrain."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            copy_repository(root)

            def keys():
                fresh()
                return {kind: code_key.code_key(entries, [r for r in units.TOOLS.get(kind, ()) if not r.endswith('.py')],
                                                root)['digest'] for kind, entries in units.CODE_ENTRIES.items()}
            before = keys()
            mesh = (root / 'tools/mesh_geometry.py').read_text(encoding='utf-8')
            edited = mesh.replace('SURFACE_LOSS=.5  # a', 'SURFACE_LOSS=.5  # another comment, a', 1)
            for function in ('def collision_parts(', 'def surface_loss_depth('):
                edited = insert_after_docstring(edited, function, ' unused_probe=1')
            (root / 'tools/mesh_geometry.py').write_text(edited, encoding='utf-8')
            after = keys()
            changed = sorted(kind for kind in before if before[kind] != after[kind])
            # (mesh-stair: stair collision method 1's mesh worker runs the same converter, CHIM-STAIR-COLLISION-MESH-47)
            self.assertEqual(changed, ['hull-surface', 'mesh', 'mesh-stair'])
            terrain = (root / 'tools/chim/terrain.py').read_text(encoding='utf-8')
            (root / 'tools/chim/terrain.py').write_text(
                insert_after_docstring(terrain, 'def terrain_unit(', '    unused_probe = 1'), encoding='utf-8')
            self.assertNotEqual(keys()['terrain'], after['terrain'])

    def test_every_kind_has_a_certain_reach(self):
        for kind in units.CODE_ENTRIES:
            with self.subTest(kind=kind):
                key = units.unit_code_key(kind)
                self.assertFalse(key['uncertain'])
                self.assertNotIn('tools/chim/units.py', key['files'])
                for data in (r for r in units.TOOLS.get(kind, ()) if not r.endswith('.py')):
                    self.assertIn(data, key['files'])

    def test_previous_key_form_is_the_files_form(self):
        task = {'box': (0, 0, 256, 256), 'step': 128}
        key = units.fingerprint('terrain', task, 'routed', None)
        with patch.dict(os.environ, {units.CODE_KEYS_VARIABLE: 'off'}):
            fresh()
            old = units.fingerprint('terrain', task, 'routed', None)
        self.assertIsNone(old.previous)
        self.assertEqual(key.previous, old)
        self.assertNotEqual(str(key), str(old))
        # a key among the parts is replaced by its previous form too
        chained = units.fingerprint('pvs', key, [1, 2])
        with patch.dict(os.environ, {units.CODE_KEYS_VARIABLE: 'off'}):
            fresh()
            self.assertEqual(chained.previous, units.fingerprint('pvs', old, [1, 2]))

    def test_a_unit_stored_under_the_previous_form_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = units.UnitCache(directory)
            key = units.fingerprint('terrain', {'probe': 1})
            cache.put('terrain', key.previous, {'rows': [7]})
            result = units.run_units('terrain', [(key, 'task')], lambda task: self.fail('rebuilt'), 1, cache)
            self.assertEqual(result, [{'rows': [7]}])
            self.assertEqual(cache.stats['terrain']['reused'], 1)
            self.assertEqual(cache.stats['terrain']['reused_previous_key'], 1)

    def test_identical_results_keep_the_keys_downstream(self):
        """Early cutoff in the unit layer: a mesh unit rebuilt under a new key with a byte-identical result gives its
        variants the same key; another result, or other content, another key."""
        result = (np.arange(6.0).reshape(2, 3), [np.ones(3)], {'collision': 'routed'})
        same = (np.arange(6.0).reshape(2, 3), [np.ones(3)], {'collision': 'routed'})
        old_fp, new_fp = units.fingerprint('mesh', 'a'), units.fingerprint('mesh', 'a', 'rebuilt')
        content = units.content_key('model record', {'ratio': 1})
        a = units.result_key('mesh', content, result, old_fp)
        b = units.result_key('mesh', content, same, new_fp)
        self.assertEqual(str(a), str(b))
        self.assertEqual(b.previous, new_fp.previous)
        self.assertEqual(str(units.fingerprint('variant', a, 1)), str(units.fingerprint('variant', b, 1)))
        other = (np.arange(6.0).reshape(2, 3) + 1e-9, [np.ones(3)], {'collision': 'routed'})
        self.assertNotEqual(str(units.result_key('mesh', content, other, units.fingerprint('mesh', 'c'))), str(a))
        self.assertNotEqual(str(units.result_key('mesh', units.content_key('other'), same,
                                                 units.fingerprint('mesh', 'd'))), str(a))
        # a tuple is not a list; a value without a stable form keeps the unit's own key (no cutoff)
        self.assertNotEqual(units.output_digest((1, 2)), units.output_digest([1, 2]))
        fallback = units.fingerprint('mesh', 'e')
        self.assertIs(units.result_key('mesh', content, object(), fallback), fallback)

    def test_mesh_result_keys(self):
        from chim.build import mesh_result_keys
        model = {'source': 'meshes/x/a.nif', 'mesh_sha256': 'm', 'collision_sha256': 'c', 'materials': []}
        task = (0, model, {'ratio': 1}, 'archive', [])
        prepared = {0: (np.zeros(3), [], {'collision': 'routed'})}
        first = mesh_result_keys([(units.fingerprint('mesh', 'old code'), task)], prepared, [0])
        second = mesh_result_keys([(units.fingerprint('mesh', 'new code'), task)], prepared, [0])
        self.assertEqual(str(first[0]), str(second[0]))
        changed = mesh_result_keys([(units.fingerprint('mesh', 'other unit'), task)],
                                   {0: (np.ones(3), [], {'collision': 'routed'})}, [0])
        self.assertNotEqual(str(changed[0]), str(first[0]))

    def test_a_worker_outside_its_key_stores_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = units.UnitCache(directory)
            items = [(units.fingerprint('terrain', {'gap probe': i}), i) for i in range(3)]
            gap = [('tools/unreached.py', 'helper')]
            with patch.dict(units.KEY_GAPS, clear=True), patch.object(code_key, 'uncovered', return_value=gap), \
                    contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(units.run_units('terrain', items, abs, 1, cache), [0, 1, 2])
                self.assertIn('outside the unit key', printed.getvalue())
                self.assertEqual(cache.stats['terrain']['key_gap'], 3)
                for fp, _ in items:
                    self.assertIsNone(cache.get('terrain', fp))
                # the kind stays gapped in this process
                code_key.uncovered.return_value = []
                more = [(units.fingerprint('terrain', {'gap probe': 9}), -9)]
                self.assertEqual(units.run_units('terrain', more, abs, 1, cache), [9])
                self.assertIsNone(cache.get('terrain', more[0][0]))
            with patch.dict(units.KEY_GAPS, clear=True), patch.object(code_key, 'uncovered', return_value=[]):
                units.run_units('terrain', items, abs, 1, cache)
            self.assertEqual(cache.get('terrain', items[2][0]), 2)


if __name__ == '__main__':
    unittest.main()
