# SPDX-License-Identifier: GPL-2.0-or-later
"""AREA-CHANGE-MEMORY-64, the area memory rule: what is kept across an area change is a purgeable cache. The cached
tables of areas left (aw_inventory.c, the "tables" tier) are given back whole by a releaser of aw_fastrelease.c before
a room sizes its growth from the free Fast RAM (chim_world.c Chim_RoomGrow), and the place's own areas and the world
change list are never touched (AW_AreaCacheTrim walks only the cache slots)."""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'engine/aga/src'


class AreaCacheRelease(unittest.TestCase):
    def setUp(self):
        self.inv = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')

    def test_the_cache_is_a_registered_releaser(self):
        self.assertIn('#include "aw_fastrelease.h"', self.inv)
        self.assertRegex(self.inv, r'AW_FastReleaseRegister\("cached area tables",area_cache_release\);')
        body = re.search(r'static unsigned long area_cache_release\(void\)\{(.*?)\n\}', self.inv, re.S).group(1)
        self.assertIn('AW_AreaCacheTrim(LONG_MAX)', body)

    def test_the_trim_walks_only_the_cache_slots(self):
        body = re.search(r'long AW_AreaCacheTrim\(long wanted\)\{(.*?)\n\}', self.inv, re.S).group(1)
        self.assertIn('for(slot=-1,i=AREA_MAX;i<AREA_SLOTS;i++)', body)    # never the place's own areas 0..AREA_MAX-1
        self.assertNotIn('change', body)                                    # the world change list is not touched

    def test_a_room_growth_runs_the_releasers_first(self):
        world = (SRC / 'chim/chim_world.c').read_text(encoding='utf-8')
        grow = world[world.index('int Chim_RoomGrow'):]
        self.assertLess(grow.index('AW_FastReleaseAll'), grow.index('ChimZone_RoomStep'))


if __name__ == '__main__':
    unittest.main()
