# SPDX-License-Identifier: GPL-3.0-only
"""dbg tp names come from the town table (DEBUG-TP-TOWN-NAMES-32)."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / 'engine' / 'aga' / 'src' / 'aw_scene.c'


class DebugTeleportNameTests(unittest.TestCase):
    def test_help_line_is_built_from_the_town_table(self):
        text = SCENE.read_text(encoding='utf-8')
        helper = re.search(r'static void scene_help\(void\) \{(.*?)\n\}', text, re.S).group(1)
        # The list comes from the town table, filtered to what the disk has (DEBUG-TP-CHIM-33).
        self.assertIn('AW_TeleportDestinations(names,sizeof(names))', helper)
        region = (ROOT / 'engine/aga/src/aw_region.c').read_text(encoding='utf-8')
        lister = re.search(r'int AW_TeleportDestinations\(char \*out,int size\)\n\{(.*?)\n\}', region, re.S).group(1)
        self.assertIn('AW_TOWN_TELEPORT', lister)
        self.assertIn('t->name', lister)
        self.assertNotIn('dbg tp balmora/', text, 'fixed town list in the help text')

    def test_vivec_short_name_maps_to_the_arena(self):
        text = SCENE.read_text(encoding='utf-8')
        self.assertRegex(text, r'"vivec"\).*\n.*AW_TownFind\("vivec_arena"\)>=0\)s="vivec_arena"')
        towns = json.loads((ROOT / 'config' / 'towns.json').read_text(encoding='utf-8'))
        rows = towns['towns'] if isinstance(towns, dict) else towns
        arena = [t for t in rows if t['id'] == 'vivec_arena']
        self.assertTrue(arena and 'teleport_arrival' in arena[0]['flags'])

    def test_console_page_lists_vivec(self):
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('vivec (Vivec Arena)', page)


if __name__ == '__main__':
    unittest.main()
