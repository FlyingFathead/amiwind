# SPDX-License-Identifier: GPL-3.0-only
"""CENSUS-INTRO-SCRIPTS-62: the census office runs the original's own scripts, one at a time off the hand-written list
(config/mwscript.json). Every script taken off the list is one the engine holds while the old hand-written opening is
chosen (aw_census_legacy 1, aw_mwhost.c census_scripts), so nothing runs twice on either path."""
import re
import sys
import unittest
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

# the census office's scripts (Morrowind.esm), in the order they come off the list
OFF_THE_LIST = ('chargendoorentercaptain', 'chargendoorexit', 'chargendoorexitcaptain', 'chargenfatiguebarrel',
               'chargendoorguardtalker', 'chargenclassnpc', 'chargenstatssheet', 'chargen_ring_keley')
STILL_HANDWRITTEN = ('chargen', 'chargenboatnpc', 'chargenboatwomen',
                     'chargendialoguemessage', 'chargendisable', 'chargennamenpc',
                     'chargenracenpc', 'chargenwalknpc')
# v0.0.63 (the tracker's parity check, config/mwscript-counterparts.json): the engine's own opening never carried
# these message boxes, the bed's rest or the dagger's equip hint, so they run as the game's scripts
RUN_SINCE_63 = ('chargenbed', 'chargencustomsdoor', 'chargendagger', 'chargenjournalmessage', 'chargenstuffroom')
CENSUS = ()


def engine_list():
    host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
    block = re.search(r'census_scripts\[\]=\{(.*?)NULL\};', host, re.S).group(1)
    return set(re.findall(r'"([a-z_]+)"', block))


class CensusScripts(unittest.TestCase):
    def setUp(self):
        from mwscript.compiler import handwritten_patterns
        self.patterns = handwritten_patterns()

    def handwritten(self, name):
        return any(fnmatchcase(name, p) for p in self.patterns)

    def test_the_scripts_off_the_list_run(self):
        self.assertEqual([n for n in OFF_THE_LIST if self.handwritten(n)], [])

    def test_the_rest_of_the_opening_stays_handwritten(self):
        self.assertEqual([n for n in STILL_HANDWRITTEN if not self.handwritten(n)], [])
        # nothing else of the original's chargen* names slipped off: only the counted ones run
        self.assertEqual([n for n in RUN_SINCE_63 if self.handwritten(n)], [])
        running = [n for n in OFF_THE_LIST + CENSUS + STILL_HANDWRITTEN + RUN_SINCE_63 if not self.handwritten(n)]
        self.assertEqual(len(running), len(OFF_THE_LIST) + len(RUN_SINCE_63) +
                         len([n for n in CENSUS if not self.handwritten(n)]))

    def test_every_script_off_the_list_is_held_on_the_old_path(self):
        held = engine_list()
        self.assertEqual([n for n in OFF_THE_LIST if n not in held], [])
        self.assertEqual([n for n in CENSUS if not self.handwritten(n) and n not in held], [])
        self.assertEqual(len(held), 8)   # the eight census office scripts this item moves


if __name__ == '__main__':
    unittest.main()
