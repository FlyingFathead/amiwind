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

    def test_weather_lights_the_land_through_the_scene_ambient(self):
        # WEATHER-AMBIENT-SUN-UNUSED-51: the weather's ambient + sun light (AWW2) tones the scene ambient before it is
        # split into daylight and hue, and toned daylight leaves the plain daytime table; aw_weather 2 keeps the
        # land's light of before (no new setting).
        sky = code('r_sky.c')
        tables = sky[sky.index('static void R_SkyColourTables'):sky.index('const unsigned char *R_DayNightFogColours')]
        self.assertLess(tables.index('toned=R_SkyWeatherAmbient(aa,bb,'), tables.index('R_SkyNightLight(ambient);'))
        self.assertIn('(sky_frame_type==1 || phase==0) && !toned?i:', tables)
        self.assertIn('sky_table_weather_light=R_SkyWeatherLightPercent();', tables)
        self.assertIn('AW_WeatherLightTone(&sky_weather_blend,a,b,mix,tone);', sky)
        self.assertIn('R_SkyWeatherLightPercent()!=sky_table_weather_light', sky)
        weather = code('aw_weather.c')
        self.assertIn('return aw_weather.value<1.5f;', weather)
        self.assertIn('Cvar_SetValue(aw_weather.name,2)', weather)
        self.assertIn('20+AW_WEATHER_LOOK_V2*AW_WEATHERS+10*AW_WEATHER_REGIONS', weather)

    def test_region_index_comes_from_the_region_name_lookup(self):
        world = code('aw_world.c')
        self.assertIn('int AW_RegionIndexAt(const float *position)', world)
        self.assertIn('region_index=(int)index;', world)
        weather = code('aw_weather.c')
        self.assertIn('AW_RegionIndexAt(source)', weather)
        self.assertIn('AW_WeatherOfRegion(&table,*region,days,milliseconds)', weather)

    def test_crossings_are_no_arrivals_and_transitions_queue(self):
        # SKY-REDMOUNTAIN-BLUE-44 reported again with v0.0.46: a walked crossing into another frame map (a map
        # change, a load of over 2 s) was taken for an arrival and switched the weather at once.
        weather = code('aw_weather.c')
        frame = weather[weather.index('int AW_WeatherFrame'):weather.index('static void weather_command')]
        self.assertNotIn('sv.name', frame)
        self.assertNotIn('now-last_time>2.0', frame)
        self.assertIn('AW_WeatherIsArrival(have_last,source[0]-last_source[0],source[1]-last_source[1],hour-last_hour)', frame)
        self.assertIn('if(target!=last_target)AW_WeatherAddTransition(&state,target);', frame)
        self.assertIn('AW_WeatherAdvance(&state,&table,seconds);', frame)
        # Off the exterior nothing is forgotten (no reset of the last position or the weather).
        self.assertIn('if(!player_source(source)){last_time=-1;return 0;}', frame)
        self.assertIn('AW_WeatherRegionKeep(&state,AW_RegionIndexAt(source))', weather)

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


class InteriorFogWiringTests(unittest.TestCase):
    """INTERIOR-FOG-UNUSED-51: the interior fog pass reads its room's row from world/interior-fog.awf (the builder's
    table) and fogs linearly from the viewing distance x (1 - density) to the viewing distance (rule from OpenMW
    mwrender/fogmanager.cpp); aw_fog 2 keeps the interiors of before."""

    def test_interior_fog_pass(self):
        fog = code('aw_fog.c')
        draw = fog[fog.index('void AW_FogDraw'):]
        self.assertIn('if(AW_Interior()){interior_fog_draw();return;}', draw)
        self.assertIn('#define INTERIOR_FOG_PATH "world/interior-fog.awf"', (SRC / 'aw_fog.c').read_text(encoding='utf-8'))
        self.assertIn('#define INTERIOR_FOG_VIEW 1792', (SRC / 'aw_fog.c').read_text(encoding='utf-8'))
        self.assertIn('if(!aw_fog.value || aw_fog.value>=2 || !sv.active)return;', fog)
        self.assertIn('start=INTERIOR_FOG_VIEW-INTERIOR_FOG_VIEW*interior_fog_density/255;', fog)
        self.assertIn('AW_FogDepthRange(depths,start,INTERIOR_FOG_VIEW);', fog)
        # the exterior table is rebuilt after an interior used the shared depth table
        self.assertIn('old_distance=-1;', fog)
        sky = code('r_sky.c')
        self.assertIn('const unsigned char *R_InteriorFogColours(int r,int g,int b)', sky)
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        from prepare_world_ui import WORLD_UI_FILES, INTERIOR_FOG_ROW
        self.assertIn('interior-fog.awf', WORLD_UI_FILES)
        self.assertIn('#define INTERIOR_FOG_ROW %d' % INTERIOR_FOG_ROW, (SRC / 'aw_fog.c').read_text(encoding='utf-8'))
        features = (ROOT / 'config' / 'release-features.json').read_text(encoding='utf-8')
        self.assertIn('id1/world/interior-fog.awf', features)


if __name__ == '__main__':
    unittest.main()
