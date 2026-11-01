"""The class questions stage (CHARGEN-CENSUS-57 (c)): tools/prepare_chargen.py on hand-made ini text (no game data),
its place in the build (a stage of its own, depending on nothing, read by the image only) and the engine side."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def ini(questions=10, drop=None):
    lines = ['[General]', 'Something=1']
    for n in range(1, questions + 1):
        lines.append('[Question %d]' % n)
        for key in ('Question', 'AnswerOne', 'AnswerTwo', 'AnswerThree'):
            if (n, key) != drop:
                lines.append('%s=%s %d text' % (key, key, n))
        lines.append('Sound=Vo\\Misc\\CharGen QA%d.wav' % n)
    return '\r\n'.join(lines) + '\r\n'


class QuestionStageTests(unittest.TestCase):
    def build(self, text):
        import prepare_chargen
        with tempfile.TemporaryDirectory() as tmp:
            path = None
            if text is not None:
                path = Path(tmp) / 'Morrowind.ini'
                path.write_bytes(text.encode('cp1252'))
            return prepare_chargen.build(path)

    def test_ten_questions_in_order(self):
        payload, report = self.build(ini())
        self.assertEqual(payload[:5], b'AWQ1\x0a')
        self.assertEqual(report['questions'], 10)
        first = payload[5:]
        length = int.from_bytes(first[:2], 'little')
        self.assertEqual(first[2:2 + length], b'Question 1 text')
        self.assertNotIn(b'Sound', payload)

    def test_missing_or_incomplete_ini_gives_no_questions(self):
        for text in (None, ini(9), ini(drop=(4, 'AnswerTwo'))):
            payload, report = self.build(text)
            self.assertEqual(payload, b'AWQ1\x00')
            self.assertEqual(report['questions'], 0)

    def test_a_stage_of_its_own_read_by_the_image_only(self):
        import build_parallel
        self.assertEqual(build_parallel.DEPENDENCIES['chargen'], ())
        for name, deps in build_parallel.DEPENDENCIES.items():
            if name != 'image':
                self.assertNotIn('chargen', deps, name)
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("('chargen', tool('prepare_chargen.py', *(['--ini', ini] if ini else []), '--out', run / 'chargen'))", source)
        self.assertIn("if name == 'image' and 'chargen' in names:", (ROOT / 'tools/build_parallel.py').read_text(encoding='utf-8'))

    def test_the_install_ini_is_found_beside_data_files(self):
        import build
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Morrowind' / 'Data Files'
            data.mkdir(parents=True)
            for name in ('Morrowind.esm', 'Morrowind.bsa'):
                (data / name).write_bytes(b'x')
            self.assertIsNone(build.install_ini(data))
            (data.parent / 'Morrowind.ini').write_text(ini(), encoding='cp1252')
            self.assertEqual(build.install_ini(data), data.parent / 'Morrowind.ini')

    def test_engine_offers_questions_only_when_built(self):
        source = (ROOT / 'engine/aga/src/aw_character.c').read_text(encoding='utf-8')
        self.assertIn('"character/questions.awq"', source)
        self.assertIn('quiz_available>0?gold:muted', source)
        # greyed out, not only a colour the font barely shows (CHARGEN-BIRTHSIGN-REVIEW-58)
        self.assertIn('if(quiz_available<=0)greyed(', source)
        self.assertIn('if(quiz_load()){class_way=1;', source)


if __name__ == '__main__':
    unittest.main()
