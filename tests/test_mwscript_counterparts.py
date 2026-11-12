# SPDX-License-Identifier: GPL-3.0-only
"""The counterparts tracker (config/mwscript-counterparts.json, v0.0.63): every game script AmiWind's own code
carries has an entry with its counterpart and a parity verdict, step by step; the tracker page shows it."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import mwscript_features as F  # noqa: E402
from mwscript.compiler import handwritten_patterns  # noqa: E402


class Counterparts(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(F.COUNTERPARTS.read_text(encoding='utf-8'))

    def test_every_entry_has_a_counterpart_and_a_verdict(self):
        self.assertEqual(F.counterpart_problems(self.doc), [])
        for e in self.doc['entries']:
            self.assertTrue((ROOT / e['counterpart']['file']).exists(), e['script'])

    def test_an_entry_without_a_pointer_or_a_verdict_is_refused(self):
        bad = copy.deepcopy(self.doc)
        bad['entries'][0]['counterpart'] = {'file': '', 'function': ''}
        bad['entries'][1]['verdict'] = 'fine'
        bad['entries'][2]['steps'][0]['verdict'] = ''
        problems = F.counterpart_problems(bad)
        self.assertEqual(len(problems), 3, problems)

    def test_every_carried_script_has_an_entry_and_no_entry_is_run(self):
        # the compiler's hand-written list and the tracker name the same scripts: a pattern with an entry for each
        # script it matches (chargenboat* = the deck guard and the woman), and no entry for a script that runs
        patterns = set(handwritten_patterns())
        names = {e['script'].casefold() for e in self.doc['entries']}
        for p in patterns:
            self.assertTrue(any(n == p or (p.endswith('*') and n.startswith(p[:-1])) for n in names), p)
        for n in names:
            self.assertTrue(any(n == p or (p.endswith('*') and n.startswith(p[:-1])) for p in patterns), n)

    def test_the_ship_repeat_lines_count_only_while_near(self):
        # v0.0.63 parity fix: CharGenNameNPC and CharGenWalkNPC count their repeat timer only within 150 (37.5 map
        # units), CharGenBoatWomen within 180 (45) with no line playing; the hand-written steps did it always
        intro = (ROOT / 'engine/aga/src/aw_intro.c').read_text(encoding='utf-8')
        self.assertIn('jiub_timer+=jiub_state!=50 || distance(roles[1],player())<37.5?dt:0;', intro)
        self.assertIn('guard_timer+=guard_state!=70 || distance(roles[2],player())<37.5?dt:0;', intro)
        self.assertIn('upper_timer+=roles[3] && distance(roles[3],player())<45 && AW_SpeechRemaining()<=0?dt:0;', intro)
        self.assertNotIn('jiub_timer+=dt;guard_timer+=dt;upper_timer+=dt;', intro)
        # OPENING-SHIP-GUARD-STEPS-63: the guard speaks on arrival (no wait for Jiub) and his hint is the script's text
        self.assertIn('guard_state==20 && AW_IntroSpeak(2,"chargenwalk1")', intro)
        self.assertNotIn('jiub_state>=50 && AW_IntroSpeak(2,"chargenwalk1")', intro)
        self.assertIn('move forward and back. A and D move side to side', intro)
        # CHARGENSTATE-START-VALUE-63: a new game leaves the CharGen script's 10
        self.assertIn('"CharGenState",10);', (ROOT / 'engine/aga/src/aw_story.c').read_text(encoding='utf-8'))

    def test_the_dock_post_and_the_ship_blocker_are_the_scripts(self):
        # The dock guard's walk after the race (PIER-GUARD-WALKS-INTO-DOOR-65, the maintainer's design of 12 November
        # 2026): CharGenRaceNPC's second travel in two measured legs, to the front of the census office door and then a
        # step aside to his post beside it (left of the door, the doorway clear, facing the dock); the first travel is
        # still the script's own point before the plank. CharGenDisable's 23rd blocker inside the ship.
        opening = (ROOT / 'engine/aga/src/aw_opening.c').read_text(encoding='utf-8')
        self.assertIn('goal[0]=second?(post_leg?AW_PIER_GUARD_POST_X:AW_PIER_GUARD_FRONT_X):(-8914.f+11264)*.25f;', opening)
        self.assertIn('g->v.angles[1]=225;', opening)
        barrier = (ROOT / 'engine/aga/src/aw_barrier.c').read_text(encoding='utf-8')
        self.assertIn('"intro/barriers-ship.awb"', barrier)
        self.assertIn('if(!strcmp(sv.name,"prison")){for(i=0;i<ship_count;i++)', barrier)
        conv = (ROOT / 'tools/prepare_character.py').read_text(encoding='utf-8')
        self.assertIn("barriers(master, SHIP_CELL)", conv)
        self.assertIn('id1/intro/barriers-ship.awb', (ROOT / 'config/release-features.json').read_text(encoding='utf-8'))
        self.assertTrue(all(e['verdict'] == 'same' for e in self.doc['entries']))   # every opening row the same

    def test_the_page_shows_the_section_and_the_count(self):
        page = (ROOT / 'docs' / 'MWSCRIPT_FEATURES.md').read_text(encoding='utf-8')
        self.assertIn('## Carried by AmiWind\'s own code', page)
        self.assertIn('are carried by AmiWind\'s own code**', page)
        for e in self.doc['entries']:
            self.assertIn('### %s' % e['script'], page)


if __name__ == '__main__':
    unittest.main()
