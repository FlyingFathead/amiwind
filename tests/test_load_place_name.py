# SPDX-License-Identifier: GPL-3.0-only
"""The failed-load box names the place, not the map file (LF5-BOX-DESTINATION-MAP-NAME-68).

A load that names only its map (a saved game, a start, a typed map, the game code's changelevel) gave the box no
place name, so "Not enough memory to load" was followed by the map file's label (balmora, rifa4ef181ed) instead of the
place's name. engine/aga/src/aw_scene.c now reads the map's own place name from its worldspawn message, the part after
the last "/" as the HUD shows it. The rule between the AW-PLACE-TITLE-RULE markers reads only the entity text, so it is
compiled here on its own; the rest checks the wiring of the failure path."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / 'engine/aga/src/aw_scene.c'

HARNESS = r'''
#include <stdio.h>
#include <string.h>
%(rule)s
static void one(const char *name,const char *text){
    char out[64];int ok=worldspawn_place(text,out,sizeof(out));
    printf("%%s %%d [%%s]\n",name,ok,out);
}
int main(void){
    char small[5];
    one("region","{\n\"classname\" \"worldspawn\"\n\"message\" \"West Gash Region/Balmora\"\n}\n{\n\"message\" \"x\"\n}\n");
    one("spaced","{\n\"message\" \"Bitter Coast Region/ Seyda Neen\"\n\"wad\" \"a\"\n}\n");
    one("plain","{\n\"message\" \"Balmora, Guild of Mages\"\n}\n");
    one("none","{\n\"classname\" \"worldspawn\"\n}\n{\n\"message\" \"Elsewhere\"\n}\n");
    one("empty","{\n\"message\" \"Region/\"\n}\n");
    one("nobrace","\"message\" \"Balmora\"");
    printf("cut %%d [%%s]\n",worldspawn_place("{\n\"message\" \"Balmora\"\n}\n",small,sizeof(small)),small);
    return 0;
}
'''


def source():
    return SCENE.read_text(encoding='utf-8')


def rule():
    text = source()
    return text[text.index('/* AW-PLACE-TITLE-RULE-BEGIN */'):text.index('/* AW-PLACE-TITLE-RULE-END */')]


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class PlaceTitleRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-place-title-'))
        (cls.tmp / 'rule.c').write_text(HARNESS % {'rule': rule()}, encoding='utf-8')
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wextra', '-fsanitize=undefined,address',
                                '-fno-sanitize-recover=all', str(cls.tmp / 'rule.c'), '-o', str(cls.tmp / 'rule')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(cls.tmp / 'rule')], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        cls.line = dict(l.split(' ', 1) for l in run.stdout.splitlines())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_part_after_the_last_slash(self):
        self.assertEqual(self.line['region'], '1 [Balmora]')

    def test_one_space_after_the_slash_is_dropped_as_the_hud_does(self):
        self.assertEqual(self.line['spaced'], '1 [Seyda Neen]')

    def test_a_message_without_a_slash_is_the_name(self):
        self.assertEqual(self.line['plain'], '1 [Balmora, Guild of Mages]')

    def test_only_the_worldspawn_counts(self):
        self.assertEqual(self.line['none'], '0 []')

    def test_an_empty_name_or_no_entity_is_none(self):
        self.assertEqual(self.line['empty'], '0 []')
        self.assertEqual(self.line['nobrace'], '0 []')

    def test_the_name_is_cut_to_the_space_given(self):
        self.assertEqual(self.line['cut'], '1 [Balm]')


class PlaceTitleWiringTests(unittest.TestCase):
    def test_a_load_that_names_only_its_map_gives_the_box_the_place(self):
        text = source()
        self.assertNotIn('error_begin(&lerr,AW_LOADERR_ERROR,map_loading_name,"")', text)
        at = text.index('map_place(map_loading_name,place,sizeof(place));')
        self.assertLess(at, text.index('error_begin(&lerr,AW_LOADERR_ERROR,map_loading_name,place);'))

    def test_the_box_prefers_the_place_to_the_map(self):
        box = (ROOT / 'engine/aga/src/aw_loaderr.c').read_text(encoding='utf-8')
        self.assertIn('e->place[0]?e->place:e->map[0]?e->map:"?"', box)


if __name__ == '__main__':
    unittest.main()
