# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-KEY-MESH-TABLE-WHOLE-54: the per-mesh measured tables key each cached unit by the rows it read.

- the tables are left out of the pass and unit cache source digests (pass_cache.PASS_KEY_NEUTRAL), though the code
  those caches key names them (mesh_geometry_env.STANDING_ROOM_TABLE is in its selection);
- a unit records the decisions of the meshes it looked up; a new row for one mesh re-keys only the units of that
  mesh, every other unit is still taken from the cache; a reason text edited keeps them all;
- a unit that read a table whole (iteration) is re-keyed by any decision change;
- a hit inside a miss hands its rows to the outer unit (a room that took a model from the model cache).
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools')]
import pass_cache  # noqa: E402
import mesh_tables  # noqa: E402
import mesh_geometry_env  # noqa: E402


def write_table(path, meshes):
    path.write_text(json.dumps({'format': 'aw-collision-standing-room-1',
                                'meshes': {m: 'reason ' + m for m in meshes}}), encoding='utf-8')


class MeshTableKeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.table = self.dir / 'standing.json'
        write_table(self.table, ['meshes/x/a.nif'])
        self.env = patch.dict(os.environ, {pass_cache.ENV: str(self.dir / 'cache')})
        self.env.start()
        mesh_tables._VIEWS.clear()

    def tearDown(self):
        self.env.stop()
        pass_cache._RECORDING.clear()
        del mesh_tables._ACTIVE[:]
        self.tmp.cleanup()

    def cache(self):
        return pass_cache.PassCache('mesh-table-test', {}, 'sources', self.dir / 'cache')

    def unit(self, cache, mesh, whole=False):
        """A unit of MESH: its result, from the cache or built (it reads the table)."""
        found = cache.load(mesh)
        if found is not None:
            return 'hit'
        meshes = mesh_geometry_env.standing_room_meshes(self.table)
        result = sorted(meshes) if whole else (mesh in meshes)
        cache.store(mesh, {'result': result})
        return 'built'

    def test_tables_leave_the_source_digest(self):
        from build_cache import SourceIndex
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        selected, uncertain = index.selection(ROOT / 'tools/mesh_geometry_env.py')
        self.assertFalse(uncertain)
        self.assertIn('config/collision-standing-room.json', selected)
        for table in mesh_tables.TABLES:
            self.assertIn(table, pass_cache.PASS_KEY_NEUTRAL)

    def test_one_row_rekeys_only_its_mesh(self):
        cache = self.cache()
        meshes = ['meshes/x/a.nif', 'meshes/x/b.nif', 'meshes/x/c.nif']
        self.assertEqual([self.unit(cache, m) for m in meshes], ['built'] * 3)
        self.assertEqual([self.unit(cache, m) for m in meshes], ['hit'] * 3)
        write_table(self.table, ['meshes/x/a.nif', 'meshes/x/b.nif'])          # one new row: b
        self.assertEqual([self.unit(cache, m) for m in meshes], ['hit', 'built', 'hit'])
        # a reason text edited: the decisions stay, every unit is taken
        self.table.write_text(json.dumps({'format': 'aw-collision-standing-room-1', 'meshes': {
            'meshes/x/a.nif': 'new words', 'meshes/x/b.nif': 'more'}}), encoding='utf-8')
        self.assertEqual([self.unit(cache, m) for m in meshes], ['hit'] * 3)

    def test_whole_read_rekeys_on_any_row(self):
        cache = self.cache()
        self.assertEqual(self.unit(cache, 'all', whole=True), 'built')
        self.assertEqual(self.unit(cache, 'all', whole=True), 'hit')
        write_table(self.table, ['meshes/x/a.nif', 'meshes/x/z.nif'])
        self.assertEqual(self.unit(cache, 'all', whole=True), 'built')

    def test_inner_hit_rows_reach_the_outer_unit(self):
        inner, outer = self.cache(), pass_cache.PassCache('mesh-table-outer', {}, 'sources', self.dir / 'cache')
        self.assertEqual(self.unit(inner, 'meshes/x/a.nif'), 'built')
        self.assertIsNone(outer.load('room'))
        self.assertEqual(self.unit(inner, 'meshes/x/a.nif'), 'hit')       # the room took its model from the cache
        outer.store('room', {'room': 1})
        write_table(self.table, [])                                          # a's row gone
        self.assertIsNone(outer.load('room'))


if __name__ == '__main__':
    unittest.main()
