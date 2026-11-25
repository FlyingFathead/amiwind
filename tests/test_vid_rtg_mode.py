# SPDX-License-Identifier: GPL-3.0-only
"""The screen mode on a graphics card (VIDEO-P96-MODEID-LOOKUP-FAILS-69).

Some Picasso96 setups answer the usual mode request (BestCModeIDTags) with no mode or with one the game cannot use, and
the start stopped on "Can't FindDisplayInfo()". engine/aga/src/vid_amiga.c now checks the card's answer, searches the
card's modes when the answer is refused, and falls back to the native AGA screen when the card has no usable mode.
The rule (between the AW-RTGMODE-RULE markers) uses no library, so it is compiled here on its own and run over made-up
mode lists; the rest checks the wiring in VID_Init that the native run cannot reach."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VID = ROOT / 'engine/aga/src/vid_amiga.c'

HARNESS = r'''
#include <stdio.h>
#include <stddef.h>
%(rule)s
/* id, width, height, depth, available */
static const struct aw_rtgmode lists[][6] = {
  /* 0: the exact size among larger ones: the exact one */
  {{0x11, 640, 480, 8, 1}, {0x12, 320, 240, 8, 1}, {0x13, 800, 600, 8, 1}, {0}},
  /* 1: only larger ones: the closest larger (least area) */
  {{0x21, 800, 600, 8, 1}, {0x22, 640, 480, 8, 1}, {0x23, 1024, 768, 8, 1}, {0}},
  /* 2: the right size but 16 bits, or not available, or too small: none */
  {{0x31, 320, 240, 16, 1}, {0x32, 320, 240, 8, 0}, {0x33, 320, 200, 8, 1}, {0}},
  /* 3: a tie in area: the one met first stays */
  {{0x41, 640, 480, 8, 1}, {0x42, 480, 640, 8, 1}, {0}},
  /* 4: refused ones before a usable one */
  {{0x51, 320, 240, 32, 1}, {0x52, 320, 240, 8, 0}, {0x53, 640, 512, 8, 1}, {0}},
};

int main (void)
{
  int l, i;
  for (l = 0; l < (int)(sizeof lists / sizeof lists[0]); l++) {
    const struct aw_rtgmode *best = NULL;
    for (i = 0; lists[l][i].id != 0; i++)
      if (aw_rtgmode_better (&lists[l][i], best, 320, 240))
        best = &lists[l][i];
    printf ("list%%d %%lx\n", l, best ? best->id : 0UL);
  }
  {
    struct aw_rtgmode m = {0x99, 320, 240, 8, 1};
    const char *why;
    why = aw_rtgmode_refusal (&m, 320, 240); printf ("ok %%s\n", why ? why : "usable");
    m.depth = 16; why = aw_rtgmode_refusal (&m, 320, 240); printf ("deep %%s\n", why ? why : "usable");
    m.depth = 8; m.available = 0; why = aw_rtgmode_refusal (&m, 320, 240); printf ("gone %%s\n", why ? why : "usable");
    m.available = 1; m.height = 200; why = aw_rtgmode_refusal (&m, 320, 240); printf ("small %%s\n", why ? why : "usable");
  }
  return 0;
}
'''


def source():
    return VID.read_text(encoding='utf-8')


def rule():
    text = source()
    return text[text.index('/* AW-RTGMODE-RULE-BEGIN */'):text.index('/* AW-RTGMODE-RULE-END */')]


def body(start):
    text = source()
    text = text[text.index(start):]
    return text[:text.index('\n}\n')]


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class RtgModeRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-rtg-mode-'))
        (cls.tmp / 'rule.c').write_text(HARNESS % {'rule': rule()}, encoding='utf-8')
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wextra', '-Wno-missing-field-initializers',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all',
                                str(cls.tmp / 'rule.c'), '-o', str(cls.tmp / 'rule')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(cls.tmp / 'rule')], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        cls.line = dict(l.split(' ', 1) for l in run.stdout.splitlines())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_exact_size_wins(self):
        self.assertEqual(self.line['list0'], '12')

    def test_else_the_closest_larger_mode(self):
        self.assertEqual(self.line['list1'], '22')

    def test_a_deep_a_missing_or_a_small_mode_is_never_chosen(self):
        self.assertEqual(self.line['list2'], '0')

    def test_on_a_tie_the_first_mode_stays(self):
        self.assertEqual(self.line['list3'], '41')

    def test_refused_modes_are_skipped(self):
        self.assertEqual(self.line['list4'], '53')

    def test_each_refusal_names_its_reason(self):
        self.assertEqual(self.line['ok'], 'usable')
        self.assertEqual(self.line['deep'], 'not 8 bits deep')
        self.assertEqual(self.line['gone'], 'not available')
        self.assertEqual(self.line['small'], 'too small')


class RtgModeWiringTests(unittest.TestCase):
    def test_the_card_is_asked_first_and_its_answer_checked(self):
        chooser = body('static ULONG aw_rtg_mode (')
        ask, check, search = (chooser.index('BestCModeIDTags'), chooser.index('aw_rtgmode_refusal'),
                              chooser.index('NextDisplayInfo'))
        self.assertLess(ask, check)
        self.assertLess(check, search)
        self.assertIn('IsCyberModeID', chooser)
        self.assertIn('aw_rtgmode_better', chooser)
        # every step is logged: the mode used, the refusal, the search's result
        self.assertEqual(len(re.findall(r'Con_Printf \("Screen mode: ', chooser)), 4)

    def test_vid_init_uses_the_chooser_and_falls_back_to_aga(self):
        init = body('void\tVID_Init (unsigned char *palette)')
        self.assertNotIn('BestCModeIDTags', init)
        chosen, native = init.index('aw_rtg_mode (BASEWIDTH, BASEHEIGHT)'), init.index('BIDTAG_MonitorID')
        self.assertLess(chosen, native)
        self.assertIn('using the native AGA screen', init)
        # the drawing path follows the mode chosen, so a native fallback mode is drawn the native way
        self.assertIn('is_cyber_mode = IsCyberModeID (mode)', init)


if __name__ == '__main__':
    unittest.main()
