# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-OPTION-RECORD-KEYS-STAGES-47: a new builder option entry in config/option-changes.json rekeyed the chim,
town, flora, engine and image stages although none of them reads that file.

Causes (tools/build_cache.py, scope 'units'):
1. A function default that only builds a path counted with its module's import-time code: map_engine_limits.py
   check_config_budgets(config_dir=ROOT / 'config') put every file of config/ into the key of every stage that
   imports the module. Its files now count for the function's own unit (path_value).
2. A loop name bound by more than one loop had no known values: build_aga.py stage_debug_catalogues reads
   ROOT/'config'/name for three named files, but `name` is also bound by its second loop, so its key counted the
   whole folder. Reads inside a loop's body now have that loop's values (loop_choices), also when the sequence
   is a local name bound once to a written-out sequence.

The keys never under-declare: a stage that reaches the function or reads the named files is still keyed on them.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests')]
import build_cache  # noqa: E402

OPTION_CHANGES = 'config/option-changes.json'

LIMITS = '''
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def budget(value):
    return value
def check_budgets(config_dir=ROOT / 'config'):
    return [json.loads(path.read_text()) for path in sorted(Path(config_dir).glob('*.json'))]
'''
STAGE_IMPORTS = '''
from limits import budget
print(budget(1))
'''
STAGE_CHECKS = '''
from limits import check_budgets
print(check_budgets())
'''
CATALOGUES = '''
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def catalogues():
    files = [('debug.txt', b'D1'), ('marks.txt', b'M1')]
    payloads = []
    for name, magic in files:
        payloads.append((name, (ROOT / 'config' / name).read_bytes()))
    for name, raw in payloads:
        print(name, len(raw))
catalogues()
'''
# The same reads, but the list is changed before the loop: its values are not known.
CATALOGUES_GROWN = CATALOGUES.replace("    payloads = []\n", "    files.append(('other.txt', b'O1'))\n    payloads = []\n")
# The loop name is bound again inside the loop's body: no values for its reads there.
CATALOGUES_REBOUND = CATALOGUES.replace("        payloads.append(", "        name = name.upper()\n        payloads.append(")


def write(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write(self.root, {'tools/limits.py': LIMITS, 'tools/stage_imports.py': STAGE_IMPORTS,
                          'tools/stage_checks.py': STAGE_CHECKS, 'tools/stage_catalogues.py': CATALOGUES,
                          'config/budget.json': '{"entity_budget": 1}', 'config/history.json': '{"changes": []}',
                          'config/debug.txt': 'D1\n', 'config/marks.txt': 'M1\n', 'config/other.txt': 'O1\n'})

    def tearDown(self):
        self.temp.cleanup()

    def data(self, script, scope='units'):
        index = build_cache.SourceIndex(self.root, scope=scope)
        return {path for path in index.closure(self.root / 'tools' / script)[1] if path.startswith('config/')}

    def digest(self, script):
        return build_cache.SourceIndex(self.root).digest(self.root / 'tools' / script)[0]

    def test_a_path_default_keys_only_the_callers_of_its_function(self):
        self.assertEqual(self.data('stage_imports.py'), set())
        self.assertEqual(self.data('stage_checks.py'), {'config/budget.json', 'config/history.json', 'config/debug.txt',
                                                        'config/marks.txt', 'config/other.txt'})
        imports, checks = self.digest('stage_imports.py'), self.digest('stage_checks.py')
        (self.root / 'config' / 'history.json').write_text('{"changes": [{"option": "new"}]}', encoding='utf-8')
        self.assertEqual(imports, self.digest('stage_imports.py'))      # the history file is never read
        self.assertNotEqual(checks, self.digest('stage_checks.py'))     # the caller globs config/: still keyed

    def test_scope_symbols_keeps_the_previous_method(self):
        self.assertIn('config/history.json', self.data('stage_imports.py', scope='symbols'))

    def test_a_default_that_runs_code_still_counts_on_import(self):
        write(self.root, {'tools/limits.py': LIMITS.replace("config_dir=ROOT / 'config'",
                                                            "config_dir=sorted(ROOT.glob('config/*.json'))")})
        self.assertTrue({'config/budget.json', 'config/history.json'} <= self.data('stage_imports.py'))

    def test_loop_reads_name_only_the_listed_files(self):
        self.assertEqual(self.data('stage_catalogues.py'), {'config/debug.txt', 'config/marks.txt'})
        before = self.digest('stage_catalogues.py')
        (self.root / 'config' / 'other.txt').write_text('O2\n', encoding='utf-8')
        self.assertEqual(before, self.digest('stage_catalogues.py'))
        (self.root / 'config' / 'marks.txt').write_text('M2\n', encoding='utf-8')
        self.assertNotEqual(before, self.digest('stage_catalogues.py'))  # a listed file still counts

    def test_unknown_sequences_still_key_the_whole_folder(self):
        for name, text in (('grown', CATALOGUES_GROWN), ('rebound', CATALOGUES_REBOUND)):
            with self.subTest(name):
                write(self.root, {'tools/stage_catalogues.py': text})
                self.assertIn('config/other.txt', self.data('stage_catalogues.py'))
                self.assertIn('config/history.json', self.data('stage_catalogues.py'))


class DefaultPlanTests(unittest.TestCase):
    """The real tree: the default build's stage keys (tests/test_build_defaults.py plan)."""

    @classmethod
    def setUpClass(cls):
        from test_build_defaults import steps, TOOLS, RUN
        cls.plan, cls.tools, cls.run_folder = steps(), TOOLS, RUN
        cls.index = build_cache.SourceIndex(top_format=build_cache.STAGE_TOP_FORMAT)
        cls.keys = cls.fingerprints()

    @classmethod
    def fingerprints(cls):
        return build_cache.fingerprint_steps(cls.plan, cls.run_folder, {'tools': cls.tools}, cls.index)[0]

    def with_digest(self, relative, digest):
        original = self.index.files[relative]
        self.index.files[relative] = digest
        try:
            return self.fingerprints()
        finally:
            self.index.files[relative] = original

    def test_no_default_stage_is_keyed_on_the_option_history(self):
        keyed = []
        for name, command in self.plan:
            script = build_cache.stage_script([str(part) for part in command])
            if script is not None and script.is_file():
                python, data, uncertain = self.index.closure(script)
                self.assertFalse(uncertain, name)
                if OPTION_CHANGES in data:
                    keyed.append(name)
        self.assertEqual(keyed, [])

    def test_a_new_option_entry_keeps_every_stage_key(self):
        document = json.loads((ROOT / OPTION_CHANGES).read_text(encoding='utf-8'))
        document['changes'].append({'version': '9.9.9-dev1', 'option': 'example_option', 'flag': '--example-option',
                                    'change': 'added', 'to': False, 'source': 'test'})
        text = json.dumps(document, indent=2) + '\n'
        self.assertEqual(self.keys, self.with_digest(OPTION_CHANGES, hashlib.sha256(text.encode()).hexdigest()))

    def test_files_a_stage_reads_still_change_its_key(self):
        changed = self.with_digest('config/camera-marks.txt', '0' * 64)     # build_aga.py stage_debug_catalogues
        for stage in ('engine', 'image'):
            self.assertNotEqual(self.keys[stage], changed[stage], stage)
        changed = self.with_digest('config/world-flora.json', '0' * 64)     # tools/world_flora_policy.py
        self.assertNotEqual(self.keys['world-flora'], changed['world-flora'])


if __name__ == '__main__':
    unittest.main()
