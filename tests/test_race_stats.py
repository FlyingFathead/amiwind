# SPDX-License-Identifier: GPL-3.0-only
"""RACE-STATS-57: the race page's View Stats button (engine/aga/src/aw_character.c), checked on the sources: reached
by the arrows between Hair and OK, by the mouse and by V; the box shows the race's base attributes for the chosen sex,
its skill bonuses and its specials from the catalogue already loaded (no new file, nothing more held); closing it
puts the focus back on the button. The public docs describe it."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'engine/aga/src/aw_character.c').read_text(encoding='utf-8')


class RaceStatsTests(unittest.TestCase):
    def test_the_arrows_reach_the_button_between_hair_and_ok(self):
        self.assertIn('static const unsigned char order[6]={0,1,2,3,STATS_ROW,4};', SOURCE)
        self.assertIn('row=order[(at+(key==K_UPARROW?5:1))%6];', SOURCE)
        self.assertNotIn('row=(row+(key==K_UPARROW?4:1))%5;', SOURCE)

    def test_enter_v_and_the_mouse_open_it_and_anything_closes_it(self):
        self.assertIn("(key==K_MOUSE1 && over_stats()) || (key==K_ENTER && row==STATS_ROW)", SOURCE)
        self.assertIn('stats_open=0;row=STATS_ROW;', SOURCE)
        self.assertIn('if(menu==1 && over_stats())row=STATS_ROW;', SOURCE)
        # a new page or a close never leaves the box up
        self.assertIn('confirming=stats_open=0;rotation=0;', SOURCE)
        self.assertIn('skip_confirm=stats_open=0;', SOURCE)

    def test_the_box_shows_the_race_record_for_the_chosen_sex(self):
        box = SOURCE[SOURCE.index('if(stats_open && menu==1){'):SOURCE.index('if(confirming){\n        AW_UIBox')]
        self.assertIn('r->attributes[i*2+choice.female]', box)     # RADT: male/female pairs
        self.assertIn('if(r->skills[i])', box)                      # the bonuses, as the original lists them
        self.assertIn('r->powers[i]', box)                          # the specials
        self.assertNotIn('COM_FOpenFile', box)                      # nothing read: the page's catalogue
        self.assertNotIn('malloc', box)

    def test_docs(self):
        doc = (ROOT / 'docs/CHARACTER_CREATION.md').read_text(encoding='utf-8')
        self.assertIn('### View Stats on the race page (v0.0.57)', doc)
        self.assertIn('apps/openmw/mwgui/race.cpp', doc)


if __name__ == '__main__':
    unittest.main()
