# SPDX-License-Identifier: GPL-3.0-only
"""The world flora and world scenery region units are keyed on the code that makes a region (read only, no build).

UNIT-KEY-WHOLE-FILE-63, seen again in the v0.0.64-dev3 build: the world-flora-region unit cache keyed every region on
the whole of tools/prepare_world_flora.py and everything the file reaches, so an edit anywhere in what the stage runs
(its main flow, or the cache code) left none of the 1931 stored regions usable. Both region caches are now keyed on
convert_region and its reach (unit_store.bake_keyed_cache, as the resident and room caches). This test edits a copy
of the checkout and reads the keys again:
- a comment and a new unused function in tools/mesh_tables.py keep every key (the measured-table code is the cache's
  own record code, pass_cache.PASS_KEY_NEUTRAL);
- an edit to the stage's main flow (check_chim_cells, which no region runs) keeps the region keys and still changes
  the old whole-file key (so the test can tell the two apart);
- an edit to a function a region runs (world_scenery.region_references) changes both region keys.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

PROBE = r'''
import json, sys
root = sys.argv[1]
sys.path[:0] = [root + '/tools', root + '/src']
import pass_cache
flora = root + '/tools/prepare_world_flora.py'
scenery = root + '/tools/prepare_world_scenery.py'
print(json.dumps({'flora': pass_cache.source_digest((flora, 'convert_region')),
                  'scenery': pass_cache.source_digest((scenery, 'convert_region')),
                  'flora_whole': pass_cache.source_digest(flora)}))
'''
SKIP = shutil.ignore_patterns('.git', '__pycache__', 'out', 'docs', 'tests', '*.pyc')


def keys(root):
    out = subprocess.run([sys.executable, '-B', '-c', PROBE, str(root)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def insert_after(path, line_start, text):
    source = path.read_text(encoding='utf-8')
    at = source.index(line_start)
    end = source.index('\n', at) + 1
    path.write_text(source[:end] + text + source[end:], encoding='utf-8', newline='\n')


class RegionUnitKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp(prefix='flora-key-'))
        cls.base = cls.temp / 'base'
        shutil.copytree(ROOT, cls.base, ignore=SKIP)
        cls.keys = keys(cls.base)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp, ignore_errors=True)

    def edited(self, name, edit):
        tree = self.temp / name
        shutil.copytree(self.base, tree)
        try:
            edit(tree)
            return keys(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)

    def test_the_caches_open_on_convert_region(self):
        import reuse_all
        openers = {o['name']: o['scripts'] for o in reuse_all.unit_cache_openers(ROOT)}
        for name, module in (('world-flora-region', 'prepare_world_flora.py'),
                             ('world-scenery-region', 'prepare_world_scenery.py')):
            with self.subTest(cache=name):
                self.assertEqual(openers[name], [[str(ROOT / 'tools' / module), 'convert_region']])

    def test_unrelated_mesh_table_edit_keeps_the_keys(self):
        def edit(tree):
            path = tree / 'tools/mesh_tables.py'
            text = path.read_text(encoding='utf-8')
            path.write_text(text + '\n# a comment\n\n\ndef _unused_probe(value):\n    return value + 1\n',
                            encoding='utf-8', newline='\n')
        after = self.edited('mesh', edit)
        self.assertEqual(after['flora'], self.keys['flora'])
        self.assertEqual(after['scenery'], self.keys['scenery'])

    def test_main_flow_edit_keeps_the_region_keys(self):
        def edit(tree):
            insert_after(tree / 'tools/prepare_world_flora.py', 'def check_chim_cells(', '    _probe = 1\n')
            insert_after(tree / 'tools/prepare_world_scenery.py', 'def check_chim_cells(', '    _probe = 1\n')
        after = self.edited('main', edit)
        self.assertEqual(after['flora'], self.keys['flora'])
        self.assertEqual(after['scenery'], self.keys['scenery'])
        self.assertNotEqual(after['flora_whole'], self.keys['flora_whole'])

    def test_edit_to_code_a_region_runs_changes_the_keys(self):
        def edit(tree):
            insert_after(tree / 'tools/world_scenery.py', 'def region_references(', '    _probe = 1\n')
        after = self.edited('used', edit)
        self.assertNotEqual(after['flora'], self.keys['flora'])
        self.assertNotEqual(after['scenery'], self.keys['scenery'])


if __name__ == '__main__':
    unittest.main()
