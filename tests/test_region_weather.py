# SPDX-License-Identifier: GPL-3.0-only
"""Region weather (SKY-REDMOUNTAIN-BLUE-44, docs/DAY_NIGHT_AND_SKY.md "Region weather"): the engine rules (host C) and the source
contracts that keep the sky tables, the region lookup, the build and the console wired in. The builder side
(region-weather.aww) is tested in test_world_ui_assets.py."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class WeatherRuleTests(unittest.TestCase):
    def test_roll_period_table_and_blend(self):
        native.NativeSourceTests().compile_run('aga_weather_rules_test.c', [SRC / 'aw_weather_rules.c'], cflags=UBSAN)


class WeatherWiringTests(unittest.TestCase):
    def test_sky_tables_follow_the_weather_and_clear_keeps_the_old_tables(self):
        sky = code('r_sky.c')
        frame = sky[sky.index('void R_SetSkyFrame'):]
        # The weather is read before the tables are checked, and a new weather rebuilds them.
        self.assertLess(frame.index('R_SkyWeather(clock_days,clock_ms);'), frame.index('R_SkyColourTables(sky_phase)'))
        self.assertIn('sky_weather_key!=sky_table_weather', frame)
        tables = sky[sky.index('static void R_SkyColourTables'):sky.index('const unsigned char *R_DayNightFogColours')]
        self.assertIn('sky_table_weather=sky_weather_key', tables)
        self.assertIn('R_SkyWeatherFog(aa,bb,mix,fog)', tables)
        self.assertIn('if(sky_weather_strength)', tables)
        # Strength 0 (clear) mixes nothing in: the clear tables are those of before.
        self.assertIn('#define SKY_WEATHER_MIX(value,target) (((value)*(AW_WEATHER_STEPS-sky_weather_strength)+'
                      '(target)*sky_weather_strength)/AW_WEATHER_STEPS)', (SRC / 'r_sky.c').read_text(encoding='utf-8'))
        self.assertIn('sky_made_weather==sky_table_weather', sky)
        self.assertIn('AW_WeatherInit();', sky)

    def test_region_index_comes_from_the_region_name_lookup(self):
        world = code('aw_world.c')
        self.assertIn('int AW_RegionIndexAt(const float *position)', world)
        self.assertIn('region_index=(int)index;', world)
        weather = code('aw_weather.c')
        self.assertIn('AW_RegionIndexAt(source)', weather)
        self.assertIn('AW_WeatherOfRegion(&table,*region,days,milliseconds)', weather)

    def test_build_payload_and_console(self):
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_weather_rules.c aw_weather.c', makefile)
        features = (ROOT / 'config' / 'release-features.json').read_text(encoding='utf-8')
        self.assertIn('id1/world/region-weather.aww', features)
        commands = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('|weather|aw_weather_set|', commands)
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        from prepare_world_ui import WORLD_UI_FILES
        self.assertIn('region-weather.aww', WORLD_UI_FILES)
        self.assertIn('"world/region-weather.aww"', (SRC / 'aw_weather.h').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
