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
            self.assertEqual(json.dumps(doc, indent=indent) + '\n', text, path)   # written as the view writes it
            rows = {m.casefold() for m in doc[field]}
            layer = {m.casefold() for ms in (doc.get('layers') or {}).values() for m in ms}
            self.assertLessEqual(layer, rows, path)                               # every layer row is a row
            view = json.loads(build_cache.layer_table_view(text, {'bloodmoon', 'tribunal'}, indent, field))
            self.assertNotIn('layers', view)
            self.assertFalse(layer & {m.casefold() for m in view[field]}, path)
        # the base CHIM stage reads Morrowind only: it leaves both layers out
        self.assertEqual(build_cache.stage_layers_left_out('chim'), {'bloodmoon', 'tribunal'})
        self.assertEqual(build_cache.stage_layers_left_out('chim-sol'), {'tribunal'})

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


if __name__ == '__main__':
    unittest.main()
