# SPDX-License-Identifier: GPL-3.0-only
"""The actor table setting takes at startup (CHIM-EXTERIOR-ACTORS-MISSING-46, 2026-10-27).

The image's default-game.cfg (tools/build_aga.py) turns the actor table on with "chim actors table 1"; the game runs
that file before any map starts. The v0.0.53 final dropped the line without a word: aw_actors.c's command returned
while no map was running before it reached its settings, so every joining frame read its frame map and the 5,082
levelled creature references outdoors were never rolled (no wild guar, cliff racer, slaughterfish or mudcrab from a
levelled list). Checked here: every "chim actors" setting the builder writes into default-game.cfg is handled by the
command before its running-map check.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src/aw_actors.c'


def command_body():
    text = SRC.read_text(encoding='utf-8')
    start = text.index('static void Command (void)')
    end = text.index('\n}\n', start)
    return text[start:end]


class StartupSettingTests(unittest.TestCase):
    def test_settings_before_the_running_map_check(self):
        body = command_body()
        check = body.index('if (!sv.active)')
        for word in ('table', 'budget', 'warm', 'seed', 'trace', 'creatures'):
            at = body.index('!strcmp (a, "%s")' % word)
            self.assertLess(at, check, '"chim actors %s" must work before a map runs (default-game.cfg)' % word)

    def test_the_builder_writes_only_such_settings(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        words = set(re.findall(r'chim actors (\w+) [01]\\n', text))
        self.assertIn('table', words)
        body = command_body()
        check = body.index('if (!sv.active)')
        for word in words:
            self.assertLess(body.index('!strcmp (a, "%s")' % word), check, word)


if __name__ == '__main__':
    unittest.main()
