"""Stage keys follow the SELECTED expansion layers (CHIM-SOL-FLORA-PATH-65): a stage that reads the layers (its code
names build_cache.MASTERS_ENV) adds the selected layers' masters and archives and the master list to its key; every
other stage keeps exactly the base key, with the layers selected (the default) or not. The builder's layer check stops
a build at once when a selected layer's file is missing or not the known version."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build  # noqa: E402
import build_cache  # noqa: E402
from mwad.paths import is_game_input  # noqa: E402

BASE = 'import sys\nprint(sys.argv)\n'
LAYERED = "import os, sys\nprint(os.environ.get('AMIWIND_MASTERS'), sys.argv)\n"


def game_inputs(data):
    return {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob('*')) if p.is_file() and is_game_input(p.relative_to(data))}


class LayerKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repository, self.data, self.run = root / 'repo', root / 'data', root / 'run'
        (self.repository / 'tools').mkdir(parents=True)
        (self.repository / 'tools' / 'stage_world.py').write_text(BASE)
        (self.repository / 'tools' / 'stage_layer.py').write_text(LAYERED)
        self.data.mkdir()
        for name in ('Morrowind.esm', 'Morrowind.bsa', 'Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'):
            (self.data / name).write_bytes(b'stub ' + name.encode())

    def tearDown(self):
        self.temp.cleanup()

    def keys(self, layers=None, with_record=True):
        tools = self.repository / 'tools'
        steps = [(n, [sys.executable, str(tools / s), '--data-files', str(self.data), '--out', str(self.run / n)])
                 for n, s in (('world', 'stage_world.py'), ('layer', 'stage_layer.py'))]
        metadata = {'compiler_jobs': 1, 'input_sha256': game_inputs(self.data), 'data_files': str(self.data),
                    'tools': {}, 'tool_sha256': {}, 'version_comparison': []}
        if with_record:
            metadata['expansion_layers'] = {'selected': list(layers or [])}
        return build_cache.fingerprint_steps(steps, self.run, metadata, build_cache.SourceIndex(self.repository))

    def test_no_dlc_keys_exactly_as_before(self):
        # --no-dlc gives every stage the key of a build without any selection record (today's keys)
        self.assertEqual(self.keys([])[0]['world'], self.keys(with_record=False)[0]['world'])
        self.assertEqual(self.keys([])[0]['layer'], self.keys(with_record=False)[0]['layer'])

    def test_default_selection_rekeys_no_base_stage(self):
        none, both = self.keys([]), self.keys(['Tribunal', 'Bloodmoon'])
        self.assertEqual(none[0]['world'], both[0]['world'])
        self.assertNotIn('load_order', both[1]['world']['game_inputs'])
        (self.data / 'Bloodmoon.esm').write_bytes(b'another Bloodmoon')
        self.assertEqual(both[0]['world'], self.keys(['Tribunal', 'Bloodmoon'])[0]['world'])

    def test_a_layer_reading_stage_follows_the_selection(self):
        none, blood, both = self.keys([]), self.keys(['Bloodmoon']), self.keys(['Tribunal', 'Bloodmoon'])
        self.assertNotEqual(none[0]['layer'], blood[0]['layer'])
        self.assertNotEqual(blood[0]['layer'], both[0]['layer'])
        self.assertEqual(blood[1]['layer']['game_inputs']['load_order'], ['Morrowind.esm', 'Bloodmoon.esm'])
        self.assertEqual(set(blood[1]['layer']['game_inputs']['masters']),
                         {'morrowind.esm', 'morrowind.bsa', 'bloodmoon.esm', 'bloodmoon.bsa'})
        # keyed by the selected layer's files, not by the others present
        (self.data / 'Tribunal.esm').write_bytes(b'another Tribunal')
        self.assertEqual(blood[0]['layer'], self.keys(['Bloodmoon'])[0]['layer'])
        (self.data / 'Bloodmoon.bsa').write_bytes(b'another archive')
        self.assertNotEqual(blood[0]['layer'], self.keys(['Bloodmoon'])[0]['layer'])

    def test_master_list(self):
        self.assertEqual(build_cache.master_list(['Bloodmoon', 'Tribunal']),
                         ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(build_cache.master_list([]), ['Morrowind.esm'])
        self.assertIn('AMIWIND_MASTERS', build_cache.IGNORED_ENV)


def report(**verdicts):
    return {'files': [{'name': name, 'verdict': verdict, 'sha256': 'ab' * 32} for name, verdict in verdicts.items()]}


KNOWN = {'Morrowind.esm': 'known', 'Morrowind.bsa': 'known', 'Tribunal.esm': 'known', 'Tribunal.bsa': 'known',
         'Bloodmoon.esm': 'known', 'Bloodmoon.bsa': 'known'}


class LayerCheckTests(unittest.TestCase):
    def test_present_and_known_pass(self):
        build.check_selected_layers(report(**KNOWN), ['Tribunal', 'Bloodmoon'])

    def test_missing_stops(self):
        files = dict(KNOWN)
        del files['Bloodmoon.bsa']
        with self.assertRaises(ValueError) as caught:
            build.check_selected_layers(report(**files), ['Tribunal', 'Bloodmoon'])
        self.assertIn('Bloodmoon.bsa is missing', str(caught.exception))
        self.assertIn('--no-dlc', str(caught.exception))
        build.check_selected_layers(report(**files), ['Tribunal'])   # not selected: not checked

    def test_different_checksum_stops(self):
        with self.assertRaises(ValueError) as caught:
            build.check_selected_layers(report(**dict(KNOWN, **{'Tribunal.esm': 'unknown'})), ['Tribunal'])
        self.assertIn('Tribunal.esm has SHA-256', str(caught.exception))

    def test_no_dlc_checks_nothing(self):
        build.check_selected_layers(report(**{'Morrowind.esm': 'known', 'Morrowind.bsa': 'known'}), [])
        self.assertEqual(build.expansion_selection(SimpleNamespace(dlc=None, dlc_off=True)), [])

    def test_the_known_values_are_in_the_table(self):
        import known_inputs
        names = {e['name'] for e in known_inputs.load_table()['entries'] if e.get('sha256')}
        for files in build.LAYER_FILES.values():
            self.assertLessEqual(set(files), names)


if __name__ == '__main__':
    unittest.main()
