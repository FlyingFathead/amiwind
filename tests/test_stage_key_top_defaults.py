# SPDX-License-Identifier: GPL-3.0-only
"""Stage key form 4 (BUILD-KEY-TOP-DEFAULTS-NAME-54): a function's defaults count in its module's import-time key only
when they run code, each by its parameter's name. In form 3 a function whose defaults named a module constant put all
its defaults there, so adding partial_area=False to tools/harvest_build.py's require_chim_coverage (v0.0.54 combat)
re-keyed the CHIM world of every MiniWind. A form 3 record is compared in form 3 (same reach), so the change of form
rebuilds nothing."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

MODULE = '''
COVERAGE = 'coverage.json'


def check(source, partial=(), report=COVERAGE):
    return source, partial, report


def other():
    return 1
'''
STAGE = '''
import mod
print(mod.other())
'''


class TopDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        self.write(MODULE)
        (self.root / 'tools' / 'stage.py').write_text(STAGE, encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, text):
        (self.root / 'tools' / 'mod.py').write_text(text, encoding='utf-8')

    def key(self, top_format=build_cache.STAGE_TOP_FORMAT):
        index = build_cache.SourceIndex(self.root, top_format=top_format)
        return index.selection(self.root / 'tools' / 'stage.py')[0]['tools/mod.py']

    def test_the_stage_keys_are_form_4(self):
        self.assertEqual(build_cache.STAGE_TOP_FORMAT, 4)
        self.assertTrue(self.key().startswith(build_cache.UNIT_PREFIX[4]))

    def test_a_literal_parameter_added_keeps_the_key(self):
        before, before3 = self.key(), self.key(3)
        self.write(MODULE.replace('report=COVERAGE)', 'report=COVERAGE, partial_area=False)'))
        self.assertEqual(self.key(), before)
        self.assertNotEqual(self.key(3), before3)          # form 3: the whole default list was import-time code

    def test_a_default_that_runs_code_or_the_constant_it_names_rekeys(self):
        before = self.key()
        self.write(MODULE.replace('report=COVERAGE)', 'report=OTHER)').replace("COVERAGE = 'coverage.json'",
                                                                             "COVERAGE = OTHER = 'coverage.json'"))
        self.assertNotEqual(self.key(), before)
        self.write(MODULE.replace("'coverage.json'", "'coverage-2.json'"))
        self.assertNotEqual(self.key(), before)

    def test_a_form_3_record_is_compared_in_form_3_with_the_same_reach(self):
        index = build_cache.SourceIndex(self.root, top_format=4)
        script = self.root / 'tools' / 'stage.py'
        old = build_cache.SourceIndex(self.root, top_format=3).selection(script)[0]
        self.assertEqual(index.previous_selections(script)[3], old)


class FormTranslationTests(unittest.TestCase):
    """A form 3 record against a checkout where only a literal parameter was added (the v0.0.54 harvest_build edit):
    compared in form 3 the module differs; read through the record's own source tree in form 4, it is the same."""

    def setUp(self):
        import json
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.old, self.new = base / 'old', base / 'new'
        for root, module in ((self.old, MODULE), (self.new, MODULE.replace('report=COVERAGE)',
                                                                           'report=COVERAGE, partial_area=False)'))):
            (root / 'tools').mkdir(parents=True)
            (root / 'tools' / 'mod.py').write_text(module, encoding='utf-8')
            (root / 'tools' / 'stage.py').write_text(STAGE, encoding='utf-8')
        self.run = base / 'run'
        self.run.mkdir()
        (self.run / 'build-state.json').write_text(json.dumps({
            'stage_cache': {'scope': 'units'},
            'steps': [{'name': 'chim', 'command': ['python3', str(self.old / 'tools' / 'stage.py')]}]}))

    def tearDown(self):
        self.temp.cleanup()

    def parts(self, root, top_format):
        selected = build_cache.SourceIndex(root, top_format=top_format).selection(root / 'tools' / 'stage.py')[0]
        return {'stage': 'chim', 'sources': {'digest': build_cache.digest_json(selected), 'files': len(selected),
                                             'by_file': selected}}

    def test_a_literal_parameter_is_no_change_against_a_form_3_record(self):
        import engine_facts
        record = self.parts(self.old, 3)
        compared, current = self.parts(self.new, 3), self.parts(self.new, 4)
        self.assertEqual(build_cache.explain(record, compared), ['sources (tools/mod.py)'])   # form 3 alone
        self.assertEqual(build_cache.explain(record, engine_facts.translate(record, compared, self.run, 'chim',
                                                                            current)), [])

    def test_a_real_edit_still_shows_against_a_form_3_record(self):
        import engine_facts
        (self.new / 'tools' / 'mod.py').write_text(MODULE.replace('return 1', 'return 2'), encoding='utf-8')
        record = self.parts(self.old, 3)
        translated = engine_facts.translate(record, self.parts(self.new, 3), self.run, 'chim', self.parts(self.new, 4))
        self.assertEqual(build_cache.explain(record, translated), ['sources (tools/mod.py)'])


if __name__ == '__main__':
    unittest.main()
