"""Stage keys cover only the game inputs a stage reads: an expansion's files being present never re-keys the base
world (BUILD-GAME-INPUT-KEY-BROAD-64, DLC-BUILD-LATER requirement 4), and a reuse source keyed with the older
blanket digest of every game input stays comparable, so the narrowing alone rebuilds nothing on the same data."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build_cache  # noqa: E402
from mwad.paths import is_game_input  # noqa: E402

STAGE = '''
import sys
print(sys.argv)
'''


def game_inputs(data):
    """As tools/build.py input_hashes: SHA-256 of every game input in the data folder."""
    return {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob('*')) if p.is_file() and is_game_input(p.relative_to(data))}


class GameInputKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repository, self.data, self.run = root / 'repo', root / 'data', root / 'run'
        (self.repository / 'tools').mkdir(parents=True)
        for name in ('stage_world.py', 'stage_media.py'):
            (self.repository / 'tools' / name).write_text(STAGE)
        (self.data / 'Meshes').mkdir(parents=True)
        (self.data / 'Morrowind.esm').write_bytes(b'TES3 stub master')
        (self.data / 'Morrowind.bsa').write_bytes(b'BSA stub archive')
        (self.data / 'Meshes' / 'rock.nif').write_bytes(b'NIF loose file')

    def tearDown(self):
        self.temp.cleanup()

    def steps(self):
        tools = self.repository / 'tools'
        return [('world', [sys.executable, str(tools / 'stage_world.py'), '--data-files', str(self.data),
                           '--out', str(self.run / 'world')]),
                ('media', [sys.executable, str(tools / 'stage_media.py'), '--scene', str(self.run / 'world')])]

    def fingerprint(self):
        metadata = {'compiler_jobs': 1, 'input_sha256': game_inputs(self.data), 'data_files': str(self.data),
                    'tools': {}, 'tool_sha256': {},
                    'version_comparison': []}
        index = build_cache.SourceIndex(self.repository)
        return build_cache.fingerprint_steps(self.steps(), self.run, metadata, index)

    def add_tribunal(self):
        (self.data / 'Tribunal.esm').write_bytes(b'TES3 stub plugin, master Morrowind.esm')
        (self.data / 'Tribunal.bsa').write_bytes(b'BSA stub expansion archive')

    def test_expansion_files_present_change_no_base_key(self):
        before = self.fingerprint()[0]
        self.add_tribunal()
        self.assertIn('Tribunal.esm', game_inputs(self.data))       # the full set still sees it
        after = self.fingerprint()[0]
        self.assertEqual(before, after)                              # every base stage key identical
        (self.data / 'Bloodmoon.esm').write_bytes(b'TES3 stub plugin two')
        self.assertEqual(before, self.fingerprint()[0])

    def test_base_inputs_still_key_every_reader(self):
        before = self.fingerprint()[0]
        (self.data / 'Morrowind.esm').write_bytes(b'TES3 another master')
        self.assertNotEqual(before['world'], self.fingerprint()[0]['world'])
        (self.data / 'Morrowind.esm').write_bytes(b'TES3 stub master')
        (self.data / 'Meshes' / 'rock.nif').write_bytes(b'NIF changed')
        self.assertNotEqual(before['world'], self.fingerprint()[0]['world'])

    def test_a_layer_stage_is_keyed_by_its_master(self):
        with patch.dict(build_cache.STAGE_GAME_INPUTS, {'world': ('morrowind.esm', 'morrowind.bsa', 'tribunal.esm')}):
            before = self.fingerprint()[0]
            self.add_tribunal()
            self.assertNotEqual(before['world'], self.fingerprint()[0]['world'])

    def test_the_bloodmoon_test_stages_are_keyed_by_bloodmoon_only(self):
        # tools/build.py --chim-sol-test: chim-sol-data and chim-sol read Bloodmoon's files, the base stages do not
        for name in ('chim-sol-data', 'chim-sol'):
            self.assertEqual(set(build_cache.STAGE_GAME_INPUTS[name]),
                             {'morrowind.esm', 'morrowind.bsa', 'bloodmoon.esm', 'bloodmoon.bsa'})
        tools = self.repository / 'tools'
        (tools / 'stage_sol.py').write_text(STAGE)
        sol = ('chim-sol', [sys.executable, str(tools / 'stage_sol.py'), '--data-files', str(self.run / 'chim-sol-data'),
                            '--out', str(self.run / 'chim-sol')])
        def keys():
            metadata = {'compiler_jobs': 1, 'input_sha256': game_inputs(self.data), 'data_files': str(self.data),
                        'tools': {}, 'tool_sha256': {}, 'version_comparison': []}
            return build_cache.fingerprint_steps(self.steps() + [sol], self.run, metadata,
                                                 build_cache.SourceIndex(self.repository))[0]
        before = keys()
        (self.data / 'Bloodmoon.esm').write_bytes(b'TES3 stub plugin, master Morrowind.esm')
        after = keys()
        self.assertNotEqual(before['chim-sol'], after['chim-sol'])
        self.assertEqual(before['world'], after['world'])
        self.add_tribunal()                                          # another layer's files: no key moves
        self.assertEqual(after, keys())

    def test_layer_rows_in_a_mesh_table_rekey_no_base_stage(self):
        # CHIM-SOLSTHEIM-HULL-SURFACE-64: Bloodmoon's rows in config/collision-hull-surface.json and
        # config/stair-check-known.json (build_cache.LAYER_ROW_TABLES) key only the stages that read Bloodmoon
        tools = self.repository / 'tools'
        reader = "from pathlib import Path\nTABLE = Path('config/collision-hull-surface.json')\nprint(TABLE.read_text())\n"
        for name in ('stage_world.py', 'stage_sol.py'):
            (tools / name).write_text(reader)
        (self.repository / 'config').mkdir()
        table = self.repository / 'config' / 'collision-hull-surface.json'
        base = {'schema': 'aw-collision-hull-surface-1', 'meshes': ['meshes/a/rock.nif', 'meshes/x/dock.nif'],
                'known_over_step': {}}
        table.write_text(json.dumps(base, indent=1) + '\n', encoding='utf-8')
        sol = ('chim-sol', [sys.executable, str(tools / 'stage_sol.py'), '--out', str(self.run / 'chim-sol')])

        def keys():
            metadata = {'compiler_jobs': 1, 'input_sha256': game_inputs(self.data), 'data_files': str(self.data),
                        'tools': {}, 'tool_sha256': {}, 'version_comparison': []}
            return build_cache.fingerprint_steps(self.steps() + [sol], self.run, metadata,
                                                 build_cache.SourceIndex(self.repository))[0]
        before = keys()
        layered = dict(base, meshes=['meshes/a/rock.nif', 'meshes/f/terrain_rock_bm_06.nif', 'meshes/x/dock.nif'],
                       layers={'bloodmoon': ['meshes/f/terrain_rock_bm_06.nif']})
        table.write_text(json.dumps(layered, indent=1) + '\n', encoding='utf-8')
        after = keys()
        self.assertEqual(before['world'], after['world'])            # the base stage: the table as it was
        self.assertNotEqual(before['chim-sol'], after['chim-sol'])   # the layer's stage: the whole table
        # a base row still re-keys the base stage
        layered['meshes'].append('meshes/x/new_base_mesh.nif')
        table.write_text(json.dumps(layered, indent=1) + '\n', encoding='utf-8')
        self.assertNotEqual(after['world'], keys()['world'])

    def test_the_repository_tables_base_view_drops_every_layer_row(self):
        for path, (indent, field) in build_cache.LAYER_ROW_TABLES.items():
            text = (ROOT / path).read_text(encoding='utf-8')
            doc = json.loads(text)
            if path not in build_cache.HAND_WRITTEN_LAYER_TABLES:
                self.assertEqual(json.dumps(doc, indent=indent) + '\n', text, path)   # written as the view writes it
            fields = field if isinstance(field, tuple) else (field,)       # one rows field, or several
            rows = {m.casefold() for one in fields for m in doc[one]}
            layer = {m.casefold() for ms in (doc.get('layers') or {}).values() for m in ms}
            self.assertLessEqual(layer, rows, path)                               # every layer row is a row
            view = json.loads(build_cache.layer_table_view(text, {'bloodmoon', 'tribunal'}, indent, field))
            self.assertNotIn('layers', view)
            self.assertFalse(layer & {m.casefold() for one in fields for m in view[one]}, path)
        # the base CHIM stage reads Morrowind only: it leaves both layers out
        self.assertEqual(build_cache.stage_layers_left_out('chim'), {'bloodmoon', 'tribunal'})
        self.assertEqual(build_cache.stage_layers_left_out('chim-sol'), {'tribunal'})

    def test_an_expansions_grounding_row_rekeys_only_the_stages_that_read_it(self):
        # BUILD-KEY-GROUNDING-LAYERS-WHOLE-FILE-68: config/actor_grounding_layers.json is a layer-row table; a Solstheim
        # person (a Bloodmoon row) left the base world stage and Mournhold's module keyed as before, and the reverse
        path = 'config/actor_grounding_layers.json'
        indent, field = build_cache.LAYER_ROW_TABLES[path]
        self.assertEqual(field, ('ground_npcs', 'exceptions'))
        dead = {'mode': 'authored_dead', 'reason': 'Authored initially dead NPC.'}
        base = {'format': 'AmiWind actor grounding layers 1', 'about': 'a', 'generator': 'g',
                'masters': ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'],
                'ground_npcs': ['aenar', 'plitinius mero'], 'exceptions': {'elberoth': dead}}
        text0 = json.dumps(base, indent=indent) + '\n'
        chim = build_cache.stage_layers_left_out('chim')
        mournhold = build_cache.stage_layers_left_out('tribunal-mournhold')
        sol = build_cache.stage_layers_left_out('chim-sol')

        def view(doc, left_out):
            return build_cache.layer_table_view(json.dumps(doc, indent=indent) + '\n', left_out, indent, field)
        # a Bloodmoon person classed ground and another authored dead: rows in both fields, named under the layer
        bloodmoon = dict(base, ground_npcs=['aenar', 'coventina celata', 'plitinius mero'],
                         exceptions={'elberoth': dead, 'solstheim dead': dead},
                         layers={'bloodmoon': ['coventina celata', 'solstheim dead']})
        self.assertEqual(view(bloodmoon, chim), text0)                 # the base world stage: as before
        self.assertEqual(view(bloodmoon, mournhold), text0)            # Mournhold's module: as before
        self.assertNotEqual(view(bloodmoon, sol), text0)               # the Solstheim stage reads them
        # the reverse: a Tribunal row moves Mournhold's module only
        tribunal = dict(base, ground_npcs=['aenar', 'mournhold person', 'plitinius mero'],
                        layers={'tribunal': ['mournhold person']})
        self.assertEqual(view(tribunal, chim), text0)
        self.assertEqual(view(tribunal, sol), text0)
        self.assertNotEqual(view(tribunal, mournhold), text0)
        # a row no layer names still re-keys every stage that reads the file
        plain = dict(base, ground_npcs=['aenar', 'plitinius mero', 'someone'])
        for left_out in (chim, mournhold, sol):
            self.assertNotEqual(view(plain, left_out), text0)
        # through the stage key's own step: the value the chim stage keys is the SHA-256 of the file before the row
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'config').mkdir()
            (Path(d) / path).write_text(json.dumps(bloodmoon, indent=indent) + '\n', encoding='utf-8')
            for stage, same in (('chim', True), ('tribunal-mournhold', True), ('chim-sol', False)):
                keyed = build_cache.layer_table_values({path: 'whole file'}, stage, d)[path]
                self.assertEqual(keyed == hashlib.sha256(text0.encode('utf-8')).hexdigest(), same, stage)
        # the shipped file: Coventina Celata of Solstheim's cell -21,24 is a Bloodmoon row (SOL-COVENTINA-NO-GROUND-
        # CLASS-68), so her class moved no base key
        text = (ROOT / path).read_text(encoding='utf-8')
        self.assertIn('coventina celata', json.loads(text)['layers']['bloodmoon'])
        self.assertNotIn('coventina celata',
                         json.loads(build_cache.layer_table_view(text, chim, indent, field))['ground_npcs'])

    def test_an_expansions_visual_recipe_and_cell_rows_rekey_no_base_stage(self):
        # BUILD-VISUAL-RECIPES-LAYER-ROWS-KEY-67: config/visual-recipes.json names Mournhold's and Solstheim's cells
        # under "layers" and their recipes under "layer_recipes"; a stage that reads neither expansion keys the
        # document without them, so a change to a district's recipe or cell row moves no base key
        path = 'config/visual-recipes.json'
        indent, field = build_cache.LAYER_ROW_TABLES[path]
        text = (ROOT / path).read_text(encoding='utf-8')
        doc = json.loads(text)
        self.assertEqual(doc['layer_recipes'], {'tribunal': ['mournhold-v1'], 'bloodmoon': ['solstheim-v1']})
        for layer, recipes in doc['layer_recipes'].items():
            cells = {k for k, v in doc['cell_settings'].items() if v.get('visual_recipe') in recipes}
            self.assertEqual(cells, set(doc['layers'][layer]), layer)      # every cell of a layer's recipe is named
        base = build_cache.layer_table_view(text, {'tribunal', 'bloodmoon'}, indent, field)
        view = json.loads(base)
        self.assertEqual(sorted(view['recipes']), sorted(set(doc['recipes']) - {'mournhold-v1', 'solstheim-v1'}))
        self.assertEqual(len(view['cell_settings']), len(doc['cell_settings']) - 15)
        self.assertNotIn('layers', view)
        self.assertNotIn('layer_recipes', view)
        # a district's recipe, a district cell's settings, a new district cell: the base view is the same text
        changed = json.loads(text)
        changed['recipes']['mournhold-v1']['status'] = 'changed'
        changed['cell_settings']['-12,-30']['no_land'] = False
        changed['cell_settings']['6,-30'] = {'visual_recipe': 'mournhold-v1'}
        changed['layers']['tribunal'].append('6,-30')
        self.assertEqual(build_cache.layer_table_view(json.dumps(changed), {'tribunal', 'bloodmoon'}, indent, field),
                         base)
        # the module's own stage reads Tribunal: its view keeps the districts and moves with them
        own = build_cache.stage_layers_left_out('tribunal-mournhold')
        self.assertEqual(own, {'bloodmoon'})
        self.assertNotEqual(build_cache.layer_table_view(json.dumps(changed), own, indent, field),
                            build_cache.layer_table_view(text, own, indent, field))
        self.assertIn('mournhold-v1', json.loads(build_cache.layer_table_view(text, own, indent, field))['recipes'])
        # a base cell's row or a base recipe still re-keys the base stages
        changed = json.loads(text)
        first = next(k for k in changed['cell_settings'] if k not in doc['layers']['tribunal'] + doc['layers']['bloodmoon'])
        changed['cell_settings'][first]['probe'] = 1
        self.assertNotEqual(build_cache.layer_table_view(json.dumps(changed), {'tribunal', 'bloodmoon'}, indent, field),
                            base)

    def test_older_blanket_key_stays_comparable(self):
        self.add_tribunal()
        _, components, _, _ = self.fingerprint()
        old = {name: dict(parts, game_inputs=build_cache.digest_json(game_inputs(self.data)))
               for name, parts in components.items() if 'game_inputs' in parts}
        self.assertTrue(old)
        for name, parts in old.items():
            compared = build_cache.comparable(parts, components[name], self.run, name)
            self.assertEqual(build_cache.explain(parts, compared), [])
        # other data under the old form still shows as a change
        (self.data / 'Tribunal.esm').write_bytes(b'TES3 a different plugin')
        _, components, _, _ = self.fingerprint()
        for name, parts in old.items():
            compared = build_cache.comparable(parts, components[name], self.run, name)
            self.assertEqual(build_cache.explain(parts, compared), ['game_inputs'])

    def test_code_handed_to_a_cache_key_does_not_make_a_stage_read_the_layers(self):
        # BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68: the CHIM source catalogue cache hands import_town.collect to a
        # unit key; that reach names the master list through the merging reader's module, and the base chim stage was
        # keyed by the expansions' masters, archives and master list. A stage reads the layers by its own code only.
        tools = self.repository / 'tools'
        (tools / 'masters.py').write_text("import os\nMASTERS_ENV = 'AMIWIND_MASTERS'\n\n\ndef selected():\n"
                                          "    return os.environ.get(MASTERS_ENV, '')\n")
        (tools / 'catalogue.py').write_text("def collect():\n    import masters\n    return masters.selected()\n")
        (tools / 'stage_world.py').write_text("import sys\nimport catalogue\nfrom pass_cache import source_digest\n\n\n"
                                              "def main():\n    print(sys.argv, source_digest((catalogue.__file__, 'collect')))\n"
                                              "\n\nmain()\n")
        (tools / 'stage_media.py').write_text("import masters\nprint(masters.selected())\n")
        index = build_cache.SourceIndex(self.repository, top_format=build_cache.STAGE_TOP_FORMAT)
        world, media = tools / 'stage_world.py', tools / 'stage_media.py'
        self.assertIn(build_cache.MASTERS_ENV, index.environment_names(world))      # the key still counts that code
        self.assertNotIn(build_cache.MASTERS_ENV, index.own_environment_names(world))
        self.assertFalse(build_cache.stage_reads_layers('world', world, index))
        self.assertTrue(build_cache.stage_reads_layers('media', media, index))      # its own code reads the list
        self.add_tribunal()
        metadata = {'compiler_jobs': 1, 'input_sha256': game_inputs(self.data), 'data_files': str(self.data),
                    'tools': {}, 'tool_sha256': {}, 'version_comparison': [],
                    'expansion_layers': {'selected': ['Tribunal']}}
        steps = [(name, [sys.executable, str(script), '--data-files', str(self.data), '--out', str(self.run / name)])
                 for name, script in (('world', world), ('media', media))]
        components = build_cache.fingerprint_steps(steps, self.run, metadata,
                                                   build_cache.SourceIndex(self.repository,
                                                                           top_format=build_cache.STAGE_TOP_FORMAT))[1]
        self.assertEqual(components['world']['game_inputs']['masters'], ['morrowind.bsa', 'morrowind.esm'])
        self.assertNotIn('load_order', components['world']['game_inputs'])
        self.assertEqual(components['media']['game_inputs']['load_order'], ['Morrowind.esm', 'Tribunal.esm'])

    def test_the_base_chim_stage_reads_no_layer(self):
        # the base world's CHIM stage is keyed by the base game's files whatever the build selects
        # (BUILD-KEY-CHIM-READS-LAYERS-VIA-UNIT-KEY-68); the modules of the expansions are keyed by their own layers
        index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        self.assertFalse(build_cache.stage_reads_layers('chim', ROOT / 'tools' / 'chim_build.py', index))
        self.assertEqual(build_cache.stage_game_masters('chim', ['tribunal', 'bloodmoon'], False),
                         build_cache.BASE_GAME_INPUTS)


if __name__ == '__main__':
    unittest.main()
