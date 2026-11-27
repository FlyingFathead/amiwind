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

    def test_balmora_takes_its_street_arrival_and_keeps_the_map_route(self):
        # TPNAMES-HEIGHTS-56: a listed town map name takes its street arrival (the map start was a roof edge); on a
        # disk where no map holds the point (a MiniWind) the town's own map still loads.
        text = SCENE.read_text(encoding='utf-8')
        self.assertIn('strcmp(s,"town") && named_place(s,&r)){', text)
        self.assertIn('if(!map_valid(s)){Con_Printf("%s: no map on this disk holds that point', text)
        names = (ROOT / 'config' / 'teleport-names.txt').read_text(encoding='utf-8')
        self.assertIn('\nbalmora|global|-20536 -13960 346|0|Balmora\n', names)

    def test_console_page_lists_vivec(self):
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        # shortened in v0.0.66 and again in v0.0.69 for lordvivec (the 384-byte line)
        self.assertIn('vivec (city, else Arena) / lordvivec', page)

    def test_lordvivec_is_a_being_place_and_vivec_stays_the_city(self):
        # DBG-TP-LORDVIVEC-69: dbg tp lordvivec is a named place that points at Vivec's own record (vivec_god); the
        # engine takes the teleport list's Beings row of that id, so the arrival is beside him, facing him (the
        # builder's check of the row: tests/test_world_doors.py)
        names = (ROOT / 'config' / 'teleport-names.txt').read_text(encoding='utf-8')
        self.assertIn('\nlordvivec|being|0 0 0|0|vivec_god\n', names)
        self.assertNotRegex(names, r'(?m)^vivec\|')    # the short name stays the city (scene_command)
        text = SCENE.read_text(encoding='utf-8')
        command = text[text.index('static void scene_command(void) {'):]
        # the short name is resolved before any named place is read
        self.assertLess(command.index('s="vivec_city";'), command.index('named_place(s,&r)'))
        being = command[command.index('if(!strcmp(r.target,"being")){'):command.index('if(!strcmp(r.target,"-")){')]
        self.assertIn('if(AW_TpBeingByIdGo(r.label))return;', being)
        self.assertIn('tp_refused(AW_LOADERR_NOT_ON_DISK,s,r.label,NULL,', being)
        self.assertNotIn('load_scene(', being)
        places = (ROOT / 'engine' / 'aga' / 'src' / 'aw_tpplaces.c').read_text(encoding='utf-8')
        go = places[places.index('int AW_TpBeingByIdGo(const char *id){'):places.index('static void reset_being(')]
        self.assertIn('row=AW_TpPlacesBeingRow(f,ftell(f),size,id,&p);', go)
        self.assertLess(go.index('fclose(f);'), go.index('AW_TpBeingGo(&p);'))     # the file closed first
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        line = next(l for l in catalogue.splitlines() if l.startswith('WORLD / TRAVEL|tp|aw_teleport|'))
        self.assertIn(' / lordvivec / ', line)
        self.assertLessEqual(len(line.encode('utf-8')), 382)


if __name__ == '__main__':
    unittest.main()
