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

    def test_a_row_appended_to_a_layer_keeps_an_entry_recorded_with_the_layer(self):
        """MESH-TABLE-LAYER-GROWS-67: a layer's list is append-only; an entry recorded when the layer was shorter
        read none of the rows appended since (Solstheim's 71 rows after the layer's first 25). Until v0.0.67 a row
        added to a recorded layer missed every such entry."""
        self.write(BASE, LAYER[:1])
        before = self.record()
        self.write(BASE, LAYER)
        self.assertNotEqual(before, self.record())
        self.assertTrue(mesh_tables.matches(before))

    def test_a_layer_row_changed_removed_or_put_first_still_rekeys(self):
        self.write(BASE, LAYER)
        before = self.record()
        self.write(BASE, LAYER[:1])                                    # a recorded row removed
        self.assertFalse(mesh_tables.matches(before))
        self.write(BASE, [LAYER[0], 'meshes/f/other.nif'])             # a recorded row replaced
        self.assertFalse(mesh_tables.matches(before))
        self.write(BASE, LAYER[1:])
        before = self.record()
        self.write(BASE, LAYER)                                        # the new row put before the recorded one
        self.assertFalse(mesh_tables.matches(before))
        self.write(BASE + ['meshes/x/c.nif'], LAYER[1:] + LAYER[:1])   # appended, but a base row changed too
        self.assertFalse(mesh_tables.matches(before))

    def test_a_mesh_row_is_compared_as_it_is(self):
        self.write(BASE, [])
        used = {(TABLE, mesh_tables.norm(LAYER[0]))}
        before = mesh_tables.rows(used)
        self.write(BASE, LAYER)
        self.assertFalse(mesh_tables.matches(before))

    def write_layers(self, base, layers):
        doc = {'format': 'aw-collision-hull-surface-1',
               'meshes': sorted(base + [m for rows in layers.values() for m in rows]), 'layers': layers}
        self.path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
        mesh_tables._VIEWS.clear()

    def test_a_second_layers_rows_keep_an_entry_recorded_with_the_first(self):
        """MESH-TABLE-SECOND-LAYER-REKEY-67: an entry recorded with the Bloodmoon rows read no Tribunal row."""
        self.write_layers(BASE, {'bloodmoon': LAYER})
        before = self.record()
        self.write_layers(BASE, {'bloodmoon': LAYER, 'tribunal': ['meshes/f/furn_banner_hanger_01.nif']})
        self.assertNotEqual(before, self.record())
        self.assertTrue(mesh_tables.matches(before))
        # and an entry older than both layers is still taken
        self.write_layers(BASE, {})
        older = self.record()
        self.write_layers(BASE, {'bloodmoon': LAYER, 'tribunal': ['meshes/f/furn_banner_hanger_01.nif']})
        self.assertTrue(mesh_tables.matches(older))

    def test_with_two_layers_rows_appended_to_both_keep_the_entry(self):
        self.write_layers(BASE, {'bloodmoon': LAYER[:1], 'tribunal': ['meshes/x/t.nif']})
        before = self.record()
        self.write_layers(BASE, {'bloodmoon': LAYER, 'tribunal': ['meshes/x/t.nif', 'meshes/x/u.nif']})
        self.assertTrue(mesh_tables.matches(before))
        self.write_layers(BASE, {'bloodmoon': LAYER, 'tribunal': ['meshes/x/u.nif', 'meshes/x/t.nif']})
        self.assertFalse(mesh_tables.matches(before))          # the second layer's new row put first

    def test_a_mesh_row_of_a_grown_layer_is_still_compared_as_it_is(self):
        self.write(BASE, LAYER[:1])
        before = mesh_tables.rows({(TABLE, mesh_tables.norm(LAYER[1]))})
        self.write(BASE, LAYER)
        self.assertFalse(mesh_tables.matches(before))          # the cell that places that mesh bakes again

    def test_with_two_layers_a_base_row_still_rekeys(self):
        self.write_layers(BASE, {'bloodmoon': LAYER})
        before = self.record()
        self.write_layers(BASE + ['meshes/x/c.nif'], {'bloodmoon': LAYER, 'tribunal': ['meshes/x/t.nif']})
        self.assertFalse(mesh_tables.matches(before))

    def write_doc(self, doc):
        self.path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
        mesh_tables._VIEWS.clear()

    def test_a_layers_recipe_rows_keep_an_entry_recorded_before_them(self):
        """Rows that apply only in the cells of a layer's own visual recipe (a base game mesh that needs the rule in
        Mournhold's districts and nowhere on Vvardenfell) go with their layer: an entry recorded before them, with or
        without another layer's rows, still matches; the same recipe block without a layer naming it does not."""
        base = {'format': 'aw-collision-hull-surface-1', 'meshes': sorted(BASE + LAYER),
                'recipe_meshes': {'old-recipe': ['meshes/x/a.nif']}, 'layers': {'bloodmoon': LAYER}}
        self.write_doc(base)
        before = self.record()
        block = {'old-recipe': ['meshes/x/a.nif'], 'town-recipe': ['meshes/x/b.nif']}
        self.write_doc(dict(base, meshes=sorted(BASE + LAYER + ['meshes/x/t.nif']), recipe_meshes=block,
                            layers={'bloodmoon': LAYER, 'tribunal': ['meshes/x/t.nif']},
                            layer_recipes={'tribunal': ['town-recipe']}))
        self.assertNotEqual(before, self.record())
        self.assertTrue(mesh_tables.matches(before))
        self.write_doc(dict(base, recipe_meshes=block))            # the recipe block as base rows: a real change
        self.assertFalse(mesh_tables.matches(before))

    def test_a_layers_recipe_row_keeps_the_mesh_rows_of_cells_elsewhere(self):
        """A base game mesh listed for a layer's own recipe: an entry that read that mesh's row before (a cell of
        another recipe, or of none) still matches; the mesh as a row of the layer itself, or under a recipe no layer
        names, is a change."""
        base = {'format': 'aw-collision-hull-surface-1', 'meshes': sorted(BASE + LAYER),
                'recipe_meshes': {'old-recipe': ['meshes/x/post.nif']}, 'layers': {'bloodmoon': LAYER}}
        self.write_doc(base)
        used = {(TABLE, 'meshes/x/post.nif'), (TABLE, 'meshes/x/rock.nif')}
        before = mesh_tables.rows(used)
        town = ['meshes/x/post.nif', 'meshes/x/rock.nif']
        block = {'old-recipe': ['meshes/x/post.nif'], 'town-recipe': town}
        layered = dict(base, recipe_meshes=block, layers={'bloodmoon': LAYER, 'tribunal': []},
                       layer_recipes={'tribunal': ['town-recipe']})
        self.write_doc(layered)
        self.assertNotEqual(before, mesh_tables.rows(used))
        self.assertTrue(mesh_tables.matches(before))
        self.write_doc(dict(base, recipe_meshes=block))                      # no layer names the recipe
        self.assertFalse(mesh_tables.matches(before))
        self.write_doc(dict(layered, meshes=sorted(BASE + LAYER + ['meshes/x/rock.nif']),
                            layers={'bloodmoon': LAYER, 'tribunal': ['meshes/x/rock.nif']}))
        self.assertFalse(mesh_tables.matches(before))                        # the rock is a row everywhere now

    def test_a_table_without_layer_recipes_is_viewed_as_before(self):
        from build_cache import layer_table_view
        text = table_text(BASE, LAYER)
        doc = json.loads(layer_table_view(text, {'bloodmoon'}, 1, 'meshes'))
        self.assertEqual(doc, {'format': 'aw-collision-hull-surface-1', 'meshes': sorted(BASE)})

    def test_the_shipped_table_matches_itself_with_shorter_layers(self):
        """The shipped table as it was when each layer held only the first part of its list (the Bloodmoon layer's
        first 25 rows, before Solstheim's were appended): an entry recorded on it is still taken."""
        doc = json.loads((ROOT / TABLE).read_text(encoding='utf-8'))
        layers = doc.get('layers')
        if not isinstance(layers, dict) or not any(len(rows) > 1 for rows in layers.values()):
            self.skipTest('the shipped table has no layer of two rows or more')
        for name, rows in layers.items():
            self.assertEqual(len(rows), len(set(rows)), name)          # no row twice
        cut = {name: list(rows)[:max(1, len(rows) // 4)] for name, rows in layers.items()}
        gone = {m for name, rows in layers.items() for m in list(rows)[len(cut[name]):]}
        earlier = dict(doc, meshes=[m for m in doc['meshes'] if m not in gone], layers=cut)
        self.write_doc(earlier)
        before = self.record()
        self.write_doc(doc)
        self.assertNotEqual(before, self.record())
        self.assertTrue(mesh_tables.matches(before))

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
