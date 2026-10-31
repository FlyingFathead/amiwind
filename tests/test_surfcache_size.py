# SPDX-License-Identifier: GPL-3.0-only
"""RENDER-SURFCACHE-THRASH-32: the surface cache holds the heaviest measured view. The method before gave every screen
under 128,000 pixels 512 KB (an integer division), while the prison ship's hold draws 1.62 MB of surface texels in
one frame, so it redrew its surfaces every frame. The default must stay at or above that view plus a margin, the
-surfcachesize override must stay, and the method before stays as the fallback when the memory is not free."""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'engine' / 'aga' / 'src' / 'vid_amiga.c'
HOLD_PEAK = 1620000          # texels drawn in one frame, prison ship hold, v0.0.57-dev1 (aw_rcount 1)


class SurfaceCacheSize(unittest.TestCase):
    def setUp(self):
        self.text = SRC.read_text(encoding='utf-8', errors='replace')

    def test_default_holds_the_heaviest_view(self):
        m = re.search(r'#define AW_SURFCACHE_DEFAULT \((\d+)\*(\d+)\)', self.text)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)) * int(m.group(2)), HOLD_PEAK * 1.2)

    def test_override_and_fallback_kept(self):
        self.assertIn('COM_CheckParm ("-surfcachesize")', self.text)
        self.assertIn('AW_SurfaceCacheBefore (width, height)', self.text)
        self.assertIn('D_InitCaches (surfcache, surfcache_bytes)', self.text)


    def test_extra_bytes_come_from_the_system_margin(self):
        # measured at 32 MB Fast: without this the CHIM cache went 7 -> 5 MiB and the gate smoke saw the zone full
        self.assertIn('aw_surfcache_extra = surfcache_bytes - AW_SurfaceCacheBefore', self.text)
        world = (SRC.parent / 'chim' / 'chim_world.c').read_text(encoding='utf-8', errors='replace')
        self.assertIn('memory_free += (unsigned long)aw_surfcache_extra', world)


if __name__ == '__main__':
    unittest.main()
