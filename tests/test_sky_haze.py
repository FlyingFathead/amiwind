# SPDX-License-Identifier: GPL-3.0-only
"""Sky haze (FOG-SKY-UNFOGGED-57): with a short draw distance the sky fades toward the fog colour so fogged buildings
and sky meet in one haze. Kept: the level by distance (none at 540 and beyond: the HORSTATOR APPROVED horizon), no
per-pixel work in the fog pass (RENDER-FOG-PASS-COST-33), the haze folded into the sky's colour tables at their
rebuild, exteriors only, and the aw_sky_haze switch."""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def level(distance, clear=540, thick=260, full=13):
    """The rule of aw_fog.c AW_SkyHazeLevel."""
    if distance >= clear:
        return 0
    if distance <= thick:
        return full
    return (clear - distance) * full // (clear - thick)


class SkyHazeTests(unittest.TestCase):
    def test_level_by_distance(self):
        c = code('aw_fog.c')
        for name, value in (('SKY_HAZE_CLEAR', 540), ('SKY_HAZE_THICK', 260), ('SKY_HAZE_FULL', 13)):
            self.assertIn('#define %s %d' % (name, value), c)
        self.assertEqual(level(540), 0)
        self.assertEqual(level(4096), 0)          # far distances: the sky as before
        self.assertEqual(level(300), 11)          # the v0.0.57 default
        self.assertEqual(level(100), 13)
        self.assertTrue(all(level(d) >= level(d + 10) for d in range(100, 600)))

    def test_no_per_pixel_work_in_the_fog_pass(self):
        c = code('aw_fog.c')
        draw = c.split('void AW_FogDraw(void) {')[1].split('\n}')[0]
        self.assertNotIn('haze', draw.lower())

    def test_folded_into_the_sky_tables_and_switchable(self):
        c = code('aw_fog.c')
        self.assertIn('static cvar_t aw_sky_haze={"aw_sky_haze","1",true};', (SRC / 'aw_fog.c').read_text(encoding='utf-8'))
        self.assertIn('Cvar_RegisterVariable(&aw_sky_haze)', c)
        now = c.split('int AW_SkyHazeNow(void) {')[1].split('}')[0]
        self.assertIn('AW_Interior()', now)
        self.assertIn('aw_sky_haze.value<=0', now)
        s = code('r_sky.c')
        tables = s.split('static void R_SkyColourTables(int phase)')[1].split('\n}')[0]
        self.assertIn('sky_table_haze=AW_SkyHazeNow();', tables)
        self.assertIn('sky_gradient[i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);', tables)
        self.assertIn('AW_SkyHazeNow()!=sky_table_haze)R_SkyColourTables(sky_phase);', s)


if __name__ == '__main__':
    unittest.main()
