# SPDX-License-Identifier: GPL-3.0-only
"""NPC-LIBRARY-NO-UNIT-CACHE-63: an expansion layer's rows in a measured table keep the unit cache entries recorded
before them.

The NPC appearance and creature model entries record config/collision-hull-surface.json read whole ('*'). The
v0.0.64-dev2 commits added the Bloodmoon rows to that table under a "layers" block (build_cache.LAYER_ROW_TABLES); the
whole-table decision changed and all 418 appearances and the creature models were baked again, though their bakes
read none of those rows. A whole-table row now also matches the table without its layers' rows:
- an entry recorded on the table before the layer rows is still taken after them (the tables of both commits);
- a base row added still re-keys it, and so does a layer row added once the entry was recorded with the layers.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools')]
import mesh_tables  # noqa: E402

TABLE = 'config/collision-hull-surface.json'
BASE = ['meshes/x/a.nif', 'meshes/x/b.nif']
LAYER = ['meshes/f/terrain_rock_bm_04.nif', 'meshes/f/act_bm_garden_plot_01.nif']


def table_text(base, layer):
    doc = {'format': 'aw-collision-hull-surface-1', 'meshes': sorted(base + layer)}
    if layer:
        doc['layers'] = {'bloodmoon': list(layer)}
    return json.dumps(doc, indent=1) + '\n'


class LayerRowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'config').mkdir()
        self.path = self.root / TABLE
        self.patch = patch.object(mesh_tables, 'ROOT', self.root)
        self.patch.start()
        mesh_tables._VIEWS.clear()

    def tearDown(self):
        self.patch.stop()
        mesh_tables._VIEWS.clear()
        self.tmp.cleanup()

    def write(self, base, layer):
        self.path.write_text(table_text(base, layer), encoding='utf-8')
        mesh_tables._VIEWS.clear()

    def record(self):
        return mesh_tables.whole_rows((TABLE,))

    def test_layer_rows_keep_an_entry_recorded_before_them(self):
        self.write(BASE, [])                       # the table at 4bd67418: no layer rows
        before = self.record()
        self.write(BASE, LAYER)                    # at d031c7b5: the Bloodmoon rows added
        self.assertNotEqual(before, self.record())  # the whole table did change
        self.assertTrue(mesh_tables.matches(before))

    def test_a_base_row_still_rekeys(self):
        self.write(BASE, [])
        before = self.record()
        self.write(BASE + ['meshes/x/c.nif'], LAYER)
        self.assertFalse(mesh_tables.matches(before))

    def test_a_layer_row_rekeys_an_entry_recorded_with_the_layer(self):
        self.write(BASE, LAYER[:1])
        before = self.record()
        self.write(BASE, LAYER)
        self.assertFalse(mesh_tables.matches(before))

    def test_a_mesh_row_is_compared_as_it_is(self):
        self.write(BASE, [])
        used = {(TABLE, mesh_tables.norm(LAYER[0]))}
        before = mesh_tables.rows(used)
        self.write(BASE, LAYER)
        self.assertFalse(mesh_tables.matches(before))

    def test_the_shipped_table_matches_its_base_view(self):
        text = (ROOT / TABLE).read_text(encoding='utf-8')
        doc = json.loads(text)
        if not isinstance(doc.get('layers'), dict):
            self.skipTest('the shipped table names no layer rows')
        from build_cache import LAYER_ROW_TABLES, layer_table_view
        base = layer_table_view(text, set(doc['layers']), *LAYER_ROW_TABLES[TABLE])
        self.path.write_text(base, encoding='utf-8')
        mesh_tables._VIEWS.clear()
        before = self.record()
        self.path.write_text(text, encoding='utf-8')
        mesh_tables._VIEWS.clear()
        self.assertTrue(mesh_tables.matches(before))


if __name__ == '__main__':
    unittest.main()
