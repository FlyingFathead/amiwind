# SPDX-License-Identifier: GPL-3.0-only
"""ENGINE-MUSIC-NO-OFF-SWITCH-36: dbg music on|off, default on, through the existing stream status handler.

The behaviour (off closes the stream, a pending read is abandoned and closes when its reply comes, nothing opens
until on again) is run by tests/test_music_player.py ("switch" case of tests/music_player_test.c).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


class MusicSwitchTests(unittest.TestCase):
    def test_catalogue_row_and_generated_page(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        row = re.search(r'\nAUDIO\|music\|aw_music_status\|(.*)', catalogue)
        self.assertIsNotNone(row)
        self.assertIn('on/off, true/false or 1/0', row.group(1))
        self.assertIn('default on', row.group(1))
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg music`', page)

    def test_default_on_and_no_new_command(self):
        text = (SRC / 'aw_music.c').read_text(encoding='utf-8')
        self.assertIn('static cvar_t music_switch={"aw_music","1"};', text)   # default on, not archived
        self.assertEqual(text.count('Cmd_AddCommand("aw_music_status",music_status)'), 1)
        self.assertNotIn('aw_music_set', text)
        init = text[text.index('int CDAudio_Init(void) {'):]
        # registered before the playlist is read, so dbg music answers on a disk without a soundtrack
        self.assertLess(init.index('Cvar_RegisterVariable(&music_switch)'), init.index('playlist.txt'))

    def test_off_stops_every_way_a_stream_starts(self):
        text = (SRC / 'aw_music.c').read_text(encoding='utf-8')
        for function in ('static int open_track(', 'static int advance('):
            body = text[text.index(function):]
            body = body[:body.index('\n}\n')]
            self.assertRegex(body, r'if\(muted\)return 0;', function)
        paint = text[text.index('void AW_MusicPaint('):]
        self.assertIn('if(!available || paused || muted)return;', paint[:400])
        apply = text[text.index('static void music_apply(void) {'):]
        apply = apply[:apply.index('\n}\n')]
        self.assertIn('close_music()', apply)   # pending read abandoned (aw_aread.c), never waited for
        self.assertNotIn('WaitPort', text)
        self.assertNotIn('WaitPkt', text)


if __name__ == '__main__':
    unittest.main()
