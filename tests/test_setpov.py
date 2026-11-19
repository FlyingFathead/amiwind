# SPDX-License-Identifier: GPL-3.0-only
"""dbg setpov (DBG-SETPOV-67; the maintainer, 2026-11-18: 1 first person, 2 the vanity camera, 3 third person, off): the
view locked for the test stills with a message on the screen and in the console; while it is locked the idle vanity
camera never starts and no key, wheel or camera command switches the view (aw_view_rules.c AW_ViewLock, aw_view.c
setpov_command)."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='latin-1'), flags=re.S)


class Wiring(unittest.TestCase):
    def test_the_numbers_the_words_and_the_messages(self):
        view = code('aw_view.c')
        command = view[view.index('static void setpov_command(void)'):view.index('static void vanity_start(void)')]
        for number, word, mode in (('1', 'first', 'AW_VIEW_FIRST'), ('2', 'vanity', 'AW_VIEW_VANITY'),
                                   ('3', 'third', 'AW_VIEW_THIRD')):
            self.assertIn('!strcmp(a,"%s") || !Q_strcasecmp((char *)a,"%s"))mode=%s;' % (number, word, mode), command)
        self.assertIn('"POV locked: %s (setpov %d)"', command)
        self.assertIn('"POV unlocked: %s"', command)
        self.assertIn('AW_UISubtitle("",line,4);', command)                 # on the screen too
        self.assertIn('Cmd_AddCommand("aw_setpov",setpov_command);', view)
        # the camera commands and the vanity orbit refuse while it is locked
        self.assertIn('if((!Q_strcasecmp(a,"first") || !Q_strcasecmp(a,"third") || !Q_strcasecmp(a,"toggle")) && '
                      'pov_locked_say())return;', view)
        start = view[view.index('static void vanity_start(void)'):]
        self.assertIn('if(pov_locked_say())return;', start[:start.index('\n}')])
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('VIDEO|setpov|aw_setpov|', catalogue)
        self.assertIn('dbg setpov', (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8'))


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class Native(unittest.TestCase):
    def test_the_lock_survives_the_idle_orbit_timer(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(
            self, 'aga_view_lock_test.c', [SRC / 'aw_view_rules.c', SRC / 'aw_anim.c'],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])


if __name__ == '__main__':
    unittest.main()
