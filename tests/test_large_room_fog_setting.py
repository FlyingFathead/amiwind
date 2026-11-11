# SPDX-License-Identifier: GPL-3.0-only
"""The large-room fog's own settings (LARGE-ROOM-FOG-SETTING-64): aw_fog_large_rooms (on by default) and the indoor fog
distance aw_fog_distance_interior (300 by default, the outdoor aw_drawdistance unchanged), both saved, both with an
Options > Video row, dbg help and the console page. The native behaviour (an interior follows its own distance, the
face cut past the room's fog) is in tests/aga_culling_test.c and the menu rows in tests/aga_menu_test.c."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


class LargeRoomFogSetting(unittest.TestCase):
    def test_defaults_and_saved(self):
        fog = (SRC / 'aw_fog.c').read_text(encoding='utf-8')
        # the third field true = archived: written to config.cfg and read back at start
        self.assertIn('static cvar_t aw_fog_large_rooms={"aw_fog_large_rooms","1",true};', fog)
        self.assertIn('static cvar_t aw_fog_distance_interior={"aw_fog_distance_interior","300",true};', fog)
        self.assertIn('Cvar_RegisterVariable(&aw_fog_large_rooms);Cvar_RegisterVariable(&aw_fog_distance_interior);', fog)
        # the outdoor distance keeps its default
        self.assertIn('cvar_t aw_drawdistance = {"aw_drawdistance","300",true};', (SRC / 'r_main.c').read_text(encoding='utf-8'))
        self.assertIn('"aw_fog_large_rooms"', (SRC / 'aw_boolean.h').read_text(encoding='utf-8'))

    def test_an_interior_uses_its_own_distance(self):
        fog = (SRC / 'aw_fog.c').read_text(encoding='utf-8')
        body = fog[fog.index('int AW_LargeRoomDistance(void) {'):]
        body = body[:body.index('\n}\n')]
        self.assertIn('aw_fog_distance_interior.value', body)
        self.assertNotIn('aw_drawdistance', body)
        self.assertIn('!aw_fog_large_rooms.value', body)

    def test_menu_rows_and_help(self):
        menu = (SRC / 'aw_menu.c').read_text(encoding='utf-8')
        for text in ('"Fog distance outdoors: %ld"', '"Fog distance indoors: %ld"', '"Fog in large rooms: On"',
                     'ROW_FOG,ROW_RESET,ROW_FOG_INDOORS,ROW_ROOMFOG,ROW_FAR'):
            self.assertIn(text, menu)
        table = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(table, re.compile(r'^VIDEO\|fog indoors\|aw_fog_distance_interior\|', re.M))
        self.assertRegex(table, re.compile(r'^VIDEO\|fog large rooms\|aw_fog_large_rooms\|', re.M))
        page = (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg fog indoors`', page)
        self.assertIn('`dbg fog large rooms`', page)


if __name__ == '__main__':
    unittest.main()
