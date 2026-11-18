"""The hull-surface table is the survey's output (CHIM-HULL-SURFACE-RESURVEY-48).

config/collision-hull-surface.json lists the meshes the collision surface rule applies to (CHIM-VIVEC-DOCK-WALKWAY-43).
It was measured on 18 October 2026 under the collision choice before v0.0.48-dev2; the default collision source
(authored: the RootCollisionNode, else the drawn triangles) and stair collision method 1 changed which meshes need it,
and the dev2 full build stopped at the collision surface gate in Balmora. tools/hull_surface_survey.py measures every
exterior mesh under the shipped defaults and writes the table. Checked here, without game data:
- the classification (table_rows): over a step without the rule and within a step with it -> table; still over with
  it -> known; ramps the visible-tread rule replaced and meshes within a step are left out (the gate's own rules);
- the placement-weighted clipnode counts (counts);
- write_table writes the schema the CHIM builder reads (chim.build.hull_surface_table, hull_surface_known);
- the shipped table is in that format, consistent (counts, sorted lower-case paths, no mesh both listed and known)
  and was measured under the shipped defaults it names.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
TABLE = ROOT / 'config' / 'collision-hull-surface.json'


def row(depth, replaced=False, clipnodes=10, error=None):
    r = {'depth': depth, 'replaced': replaced, 'clipnodes': clipnodes, 'note': ''}
    if error:
        r = {'error': error}
    return r


MESHES = [
    {'source': 'meshes/x/Deck.nif', 'placements': 3, 'base': row(19.4, clipnodes=10), 'rule': row(0.1, clipnodes=14)},
    {'source': 'meshes/x/still.nif', 'placements': 1, 'base': row(64.0), 'rule': row(30.0)},
    {'source': 'meshes/x/ramp.nif', 'placements': 2, 'base': row(64.0, replaced=True), 'rule': None},
    {'source': 'meshes/x/flat.nif', 'placements': 5, 'base': row(2.0, clipnodes=4), 'rule': row(0.0, clipnodes=6)},
    {'source': 'meshes/x/broken.nif', 'placements': 1, 'base': row(0, error='ValueError: x'), 'rule': None},
    # over a step only where a cell's visual recipe reduces it: listed for that recipe only
    {'source': 'meshes/x/ship.nif', 'placements': 2, 'base': row(64.0), 'rule': row(0.4),
     'counted': {'base': row(64.0, replaced=True, clipnodes=100), 'rule': row(54.0, replaced=True, clipnodes=140)},
     'variants': {'default': {'base': row(64.0, replaced=True), 'rule': row(54.0, replaced=True)},
                  'recipe:telvanni-v1': {'base': row(64.0), 'rule': row(0.4)}}},
]


class Survey(unittest.TestCase):
    def test_table_rows(self):
        from hull_surface_survey import table_rows
        table, known, recipes = table_rows(MESHES, 8.5)
        self.assertEqual(table, ['meshes/x/deck.nif'])
        self.assertEqual(recipes, {'telvanni-v1': ['meshes/x/ship.nif']})
        self.assertEqual(list(known), ['meshes/x/still.nif'])
        self.assertEqual(known['meshes/x/still.nif']['depth'], 30.0)
        self.assertTrue(known['meshes/x/still.nif']['reason'])

    def test_counts(self):
        from hull_surface_survey import counts
        # flat.nif on the rule: 6 x 5; deck without it: 10 x 3; still 10 x 1; ramp 10 x 2; broken left out
        # ship: its default variant (counted), without the rule unless listed for every cell: 100 x 2
        self.assertEqual(counts(MESHES, {'meshes/x/flat.nif'}), (5, 30 + 10 + 20 + 30 + 200))
        self.assertEqual(counts(MESHES, {'meshes/x/deck.nif'}), (3, 42 + 10 + 20 + 20 + 200))
        self.assertEqual(counts(MESHES, {'meshes/x/deck.nif'}, weighted=False), (3, 14 + 10 + 10 + 4 + 100))
        self.assertEqual(counts(MESHES, {'meshes/x/ship.nif'}), (2, 30 + 10 + 20 + 20 + 280))

    def test_write_table_is_read_by_the_builder(self):
        from hull_surface_survey import table_rows, write_table
        from chim.build import hull_surface_table, hull_surface_known, hull_surface_recipe_table
        table, known, recipes = table_rows(MESHES, 8.5)
        report = {'measured': '23 October 2026', 'exterior_models': 5, 'not_converted': 0, 'step_height': 8.5,
                  'defaults': {'collision_source': 'authored', 'stair_collision': '1', 'underside': 'names'},
                  'table': {'meshes': table, 'known_over_step': known, 'recipe_meshes': recipes, 'placements': 3,
                            'clipnodes_before_after': [1, 2], 'clipnodes_stored_once_before_after': [1, 2]}}
        previous = json.loads(TABLE.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'table.json'
            doc = write_table(path, report, previous)
            self.assertEqual(set(doc), set(previous))
            # the expansion layers' rows of the table it replaces stay (CHIM-SOLSTHEIM-HULL-SURFACE-64)
            layer = {m for ms in (previous.get('layers') or {}).values() for m in ms}
            self.assertEqual(doc.get('layers'), previous.get('layers'))
            self.assertEqual(hull_surface_table(path), {'meshes/x/deck.nif'} | layer)
            self.assertEqual(hull_surface_known(path), {'meshes/x/still.nif'})
            # and so do the recipe blocks a layer owns (layer_recipes: the rows of Mournhold's districts)
            owned = {r: set(previous['recipe_meshes'][r])
                     for rs in (previous.get('layer_recipes') or {}).values() for r in rs}
            self.assertEqual(doc.get('layer_recipes'), previous.get('layer_recipes'))
            self.assertEqual(hull_surface_recipe_table(path), {'telvanni-v1': {'meshes/x/ship.nif'}, **owned})
            self.assertEqual(doc['counts']['meshes'], 1)


class AppendLayerRows(unittest.TestCase):
    def test_rows_go_into_the_table_and_to_the_end_of_the_layers_list(self):
        from hull_surface_survey import append_layer_rows, main
        doc = {'schema': 'aw-collision-hull-surface-1', 'meshes': ['meshes/a.nif', 'meshes/m.nif', 'meshes/z.nif'],
               'layers': {'bloodmoon': ['meshes/z.nif', 'meshes/m.nif']}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'table.json'
            path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
            new = append_layer_rows(path, 'bloodmoon', ['Meshes\\B.nif', 'meshes/m.nif', 'meshes/y.nif'])
            self.assertEqual(new, ['meshes/b.nif', 'meshes/y.nif'])
            out = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(out['meshes'], ['meshes/a.nif', 'meshes/b.nif', 'meshes/m.nif', 'meshes/y.nif',
                                             'meshes/z.nif'])
            # the layer's earlier rows keep their places; the new ones follow in the order given
            self.assertEqual(out['layers']['bloodmoon'], ['meshes/z.nif', 'meshes/m.nif', 'meshes/b.nif',
                                                          'meshes/y.nif'])
            before = path.read_bytes()
            self.assertEqual(append_layer_rows(path, 'bloodmoon', ['meshes/b.nif']), [])
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError):
                append_layer_rows(path, 'bloodmoon', ['textures/x.dds'])
            rows = Path(d) / 'rows.json'
            rows.write_text(json.dumps({'tribunal': ['meshes/t.nif']}), encoding='utf-8')
            self.assertEqual(main(['append-layer', '--table', str(path), '--layer', 'tribunal', '--rows', str(rows),
                                   '--key', 'tribunal']), 0)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['layers']['tribunal'], ['meshes/t.nif'])


class ShippedTable(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(TABLE.read_text(encoding='utf-8'))

    def test_format(self):
        d = self.doc
        self.assertEqual(d['schema'], 'aw-collision-hull-surface-1')
        # counts are the base master's survey; an expansion layer's rows are named under layers
        layer = {m for ms in d.get('layers', {}).values() for m in ms}
        self.assertLessEqual(layer, set(d['meshes']))
        self.assertEqual(d['counts']['meshes'], len(set(d['meshes']) - layer))
        self.assertEqual(d['meshes'], sorted(d['meshes']))
        self.assertTrue(all(m == m.casefold() and m.startswith('meshes/') and '\\' not in m for m in d['meshes']))
        self.assertFalse(set(d['meshes']) & set(d['known_over_step']))
        from visual_recipes import load_recipes
        names = load_recipes()['recipes']
        for recipe, ms in d['recipe_meshes'].items():
            self.assertIn(recipe, names)
            self.assertEqual(ms, sorted(ms))
            self.assertFalse(set(ms) & set(d['meshes']))
        for m, k in d['known_over_step'].items():
            self.assertEqual(m, m.casefold())
            self.assertGreater(k['depth'], 8.5)
            self.assertTrue(k['reason'])
        self.assertEqual(len(d['counts']['clipnodes_before_after']), 2)

    def test_measured_under_the_shipped_defaults(self):
        from collision_source_env import DEFAULT_COLLISION_SOURCE
        from stair_collision_env import DEFAULT_STAIR_COLLISION_METHOD
        note = self.doc['measured']
        self.assertIn('tools/hull_surface_survey.py', note)
        self.assertIn('collision source %s' % DEFAULT_COLLISION_SOURCE, note)
        self.assertIn('stair collision method %s' % DEFAULT_STAIR_COLLISION_METHOD, note)


if __name__ == '__main__':
    unittest.main()
