"""A manual talk tries the dialogue window before the voice table's greeting text can stop it (SELLUS-GRAVIUS-GREETING-ONLY-64).

With any bounty, Sellus Gravius' (and any guard's) conversation greeting in the voice table is a crime row stored without
text, because the table builder blanks lines whose defines are only filled at run time. pr_cmds.c PF_aw_converse returned
before the dialogue window when that text was empty, so only the hello voice line played and the papers could never be
handed over. The window picks its own greeting from the dialogue table, so it must be tried first.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src' / 'pr_cmds.c'


def converse_body():
    text = SRC.read_text(encoding='utf-8', errors='replace')
    start = text.index('static void PF_aw_converse(void)')
    end = text.index('\n}\n', start)
    return text[start:end]


class ConverseWindowFirst(unittest.TestCase):
    def test_empty_voice_text_does_not_return_before_the_window(self):
        body = converse_body()
        window = body.index('AW_DialWindowOpen(')
        # no early return between the voice-table lookup and the window: the lookup's failure only empties the text
        glut = body.index('AW_GlutConverse(')
        between = body[glut:window]
        self.assertNotRegex(between, r'AW_GlutConverse\([^;]*\)\)\s*return\s*;',
                            'an empty voice-table greeting must not return before the dialogue window is tried')
        self.assertIn('text[0]=0', between)

    def test_window_is_tried_before_the_subtitle_fallback(self):
        body = converse_body()
        self.assertLess(body.index('AW_DialWindowOpen('), body.index('AW_UISubtitle('))
        # the hello fallback (return 0 to QC) only after the window refused and there is no text
        after = body[body.index('AW_DialWindowOpen('):]
        self.assertTrue(re.search(r'if\(!text\[0\]\)\s*return\s*;', after),
                        'no text and no window: return 0 so QC says the hello line')

    def test_original_person_never_gets_a_line_in_place_of_the_window(self):
        """RC2-SELLUS-NO-TALK-65: in the original and OpenMW a person talks only in the dialogue window. A record's
        person whose window refused returns nonzero (no QC hello line) before any subtitle or hello fallback."""
        body = converse_body()
        after = body[body.index('AW_DialWindowOpen('):]
        record = after.index('"aw_source_id"')
        self.assertLess(record, after.index('AW_UISubtitle('), 'the record check comes after the subtitle')
        self.assertLess(record, after.index('if(!text[0])return;'), 'the record check comes after the hello fallback')
        guard = after[record:after.index('if(!text[0])return;')]
        self.assertRegex(guard, r'G_FLOAT\(OFS_RETURN\)=\.1f;return;', 'a refused window of a record person must not '
                         'return 0 (QC would say the hello line in its place)')


if __name__ == '__main__':
    unittest.main()
