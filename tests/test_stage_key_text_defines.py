# SPDX-License-Identifier: GPL-3.0-only
"""How the stages key tools/text_defines.py (BUILD-STAGE-KEY-TEXT-DEFINES-59), read only, no build.

The text define table is read only by the steps that write game text (books, the journal, the dialogue and voice
tables, all in the image step). The CHIM world (chim_build.py) and interiors (chim_interiors.py) stages reached it only
through prepare_world_ui.py's import line, although they call only its validate(); a new define then re-converted
both. prepare_world_ui.py now imports it in journal_assets, its only reader, so the CHIM stages do not reach the file
and a define change keeps their keys, while every text writer still keys it and re-keys on a change.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402

DEFINES = 'tools/text_defines.py'
WORLD_STAGES = ('chim_build.py', 'chim_interiors.py')
TEXT_STAGES = ('build_aga.py', 'prepare_world_ui.py', 'prepare_books.py', 'dialogue_lut.py', 'greeting_lut.py')


class TextDefinesKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def test_world_stages_do_not_reach_the_defines(self):
        for script in WORLD_STAGES:
            with self.subTest(script=script):
                python, _, uncertain = self.index.closure(ROOT / 'tools' / script)
                self.assertFalse(uncertain, script)
                self.assertNotIn(DEFINES, python)
                selection, _ = self.index.selection(ROOT / 'tools' / script)
                self.assertNotIn(DEFINES, selection)
                # they still reach prepare_world_ui.py (validate), so the test proves the import moved, not the call
                self.assertIn('tools/prepare_world_ui.py', python)

    def test_text_stages_key_the_table(self):
        for script in TEXT_STAGES:
            with self.subTest(script=script):
                selection, uncertain = self.index.selection(ROOT / 'tools' / script)
                self.assertFalse(uncertain, script)
                self.assertIn(DEFINES, selection)
                self.assertIn('NAMES', (self.index.reached_units(ROOT / 'tools' / script) or {}).get(DEFINES, ()))

    def test_a_new_define_rekeys_the_text_stages(self):
        reached = {script: frozenset((self.index.reached_units(ROOT / 'tools' / script) or {})[DEFINES])
                   for script in TEXT_STAGES}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / DEFINES
            target.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / DEFINES, target)

            def digests():
                index = build_cache.SourceIndex(Path(tmp), top_format=build_cache.STAGE_TOP_FORMAT)
                return {script: index.unit_digest(DEFINES, set(units)) for script, units in reached.items()}

            before = digests()
            text = target.read_text(encoding='utf-8')
            target.write_text(text.replace("'actionrun', 'gamehour',", "'actionrun', 'awprobe', 'gamehour',", 1),
                              encoding='utf-8')
            self.assertNotEqual(target.read_text(encoding='utf-8'), text)
            after = digests()
            for script in TEXT_STAGES:
                self.assertNotEqual(after[script], before[script], script)


if __name__ == '__main__':
    unittest.main()
