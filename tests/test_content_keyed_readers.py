# SPDX-License-Identifier: GPL-3.0-only
"""Content-keyed readers (tools/build_cache.py CONTENT_KEYED_READERS, BUILD-UNIT-KEYS-REACH-64): the merging reader and
the layered archive reader count in no key by their code. A reader edit with the same output re-keys no unit and no
stage; an edit of the unit's own code still does; keys made before (the readers as code) are found as an older form."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_cache  # noqa: E402
import code_key  # noqa: E402
import pass_cache  # noqa: E402

READER = 'src/mwad/masters.py'
UNIT = '''from mwad.masters import master_path


def bake(data):
    return master_path(data).read_bytes()[:4]


if __name__ == '__main__':
    bake('.')
'''
MASTERS = '''import os

FORMAT = 'f1'


def master_path(data, masters=None):
    name = os.environ.get('AMIWIND_MASTERS', '')
    return data
'''


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'tools').mkdir()
        (self.root / 'src/mwad').mkdir(parents=True)
        (self.root / 'src/mwad/__init__.py').write_text('')
        (self.root / 'src/mwad/archives.py').write_text('X = 1\n')
        self.write('tools/unit.py', UNIT)
        self.write(READER, MASTERS)

    def write(self, rel, text):
        (self.root / rel).write_text(text, encoding='utf-8')

    def digest(self, content_keyed=True):
        index = build_cache.SourceIndex(self.root, top_format=pass_cache.PASS_KEY_FORM, content_keyed=content_keyed)
        return index.entry_digest(self.root / 'tools/unit.py', 'bake')[0]

    def stage(self, content_keyed=True):
        index = build_cache.SourceIndex(self.root, top_format=build_cache.STAGE_TOP_FORMAT, content_keyed=content_keyed)
        return index.selection(self.root / 'tools/unit.py')


class ContentKeyedReaders(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.tmp.cleanup()

    def test_the_list(self):
        self.assertEqual(sorted(build_cache.CONTENT_KEYED_READERS), ['src/mwad/archives.py', 'src/mwad/masters.py'])
        for path in build_cache.CONTENT_KEYED_READERS:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_reader_edit_with_the_same_output_rekeys_nothing(self):
        before, before_code, (stage, _) = self.repo.digest(), self.repo.digest(False), self.repo.stage()
        self.repo.write(READER, MASTERS.replace("name = os.environ.get('AMIWIND_MASTERS', '')",
                                                "chosen = os.environ.get('AMIWIND_MASTERS', '')"))
        self.assertEqual(self.repo.digest(), before)               # unit key: unchanged
        self.assertEqual(self.repo.stage()[0], stage)              # stage key: unchanged
        self.assertNotEqual(self.repo.digest(False), before_code)  # the older form saw the code
        self.assertEqual(stage[READER], build_cache.CONTENT_KEYED_READERS[READER])

    def test_unit_code_edit_still_rekeys(self):
        before = self.repo.digest()
        self.repo.write('tools/unit.py', UNIT.replace('[:4]', '[:8]'))
        self.assertNotEqual(self.repo.digest(), before)

    def test_the_reader_stays_in_the_reach(self):
        # its settings still count (the stage reads the layers), only its code is left out
        index = build_cache.SourceIndex(self.repo.root, top_format=build_cache.STAGE_TOP_FORMAT)
        self.assertIn('AMIWIND_MASTERS', index.environment_names(self.repo.root / 'tools/unit.py'))

    def test_previous_digests_hold_the_reader_as_code(self):
        script = (str(self.repo.root / 'tools/unit.py'), 'bake')
        with mock.patch.multiple(pass_cache, ROOT=self.repo.root, _DIGESTS={}, _COVERED={}):
            current = pass_cache.source_digest(script)
            older = pass_cache.source_digest(script, content_keyed=False)
            self.assertNotEqual(current, older)
            self.assertIn(older, pass_cache.previous_digests(script))

    def test_stage_record_of_the_older_form_compares_equal(self):
        selection, _ = self.repo.stage()
        old_selection, _ = self.repo.stage(content_keyed=False)
        new = {'stage': 's', 'sources': {'digest': build_cache.digest_json(selection), 'by_file': selection}}
        old = {'stage': 's', 'sources': {'digest': build_cache.digest_json(old_selection), 'by_file': old_selection}}
        self.assertNotEqual(new, old)
        self.assertEqual(build_cache.content_keyed_as_recorded(old, new), old)
        # a reach that did not hold the reader before still differs
        lost = {'stage': 's', 'sources': {'by_file': {k: v for k, v in old_selection.items() if k != READER}}}
        self.assertIs(build_cache.content_keyed_as_recorded(lost, new), new)

    def test_code_key_form(self):
        with mock.patch.dict(code_key._KEYS, {}, clear=True), mock.patch.dict(code_key._INDEX, {}, clear=True):
            new = code_key.code_key([('tools/unit.py', 'bake')], root=self.repo.root)
            old = code_key.code_key([('tools/unit.py', 'bake')], root=self.repo.root, content_keyed=False)
        self.assertEqual(new['files'][READER], build_cache.CONTENT_KEYED_READERS[READER])
        self.assertNotEqual(old['files'][READER], new['files'][READER])
        self.assertNotEqual(new['digest'], old['digest'])


class ChimUnitKeyForm(unittest.TestCase):
    def test_reader_code_survives_pickling(self):
        import pickle
        sys.path.insert(0, str(ROOT / 'tools'))
        from chim import units as U
        key = U._unit_key('k', 'p', 'r')
        back = pickle.loads(pickle.dumps(key))
        self.assertEqual((str(back), back.previous, back.reader_code), ('k', 'p', 'r'))
        self.assertEqual(U._reader_code_parts([key, {'a': U._unit_key('x', None)}]), ['r', {'a': 'x'}])
        self.assertTrue(U._holds_reader_code({'a': [key]}))


if __name__ == '__main__':
    unittest.main()
