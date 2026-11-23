# SPDX-License-Identifier: GPL-3.0-only
"""The draw distance by region (REGIONAL-DRAW-DISTANCE-68): the table config/region-draw-distance.json (the repo
default), its writer tools/region_draw.py (world/region-draw.txt at the image step, in the image's region catalogue
order) and the engine's side of the same numbers (engine/aga/src/aw_fog.c). The engine's behaviour (one owner, every
order of events, no rule on quiet frames) is checked natively in tests/aga_drawdist_test.c."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine' / 'aga' / 'src'

import region_draw  # noqa: E402


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, *fields, flags=0):
    body = b''.join(fields)
    return tag.encode('ascii') + struct.pack('<IiI', len(body), 0, flags) + body


def regn(ident, name, deleted=False):
    fields = [sub('NAME', ident + b'\0'), sub('FNAM', name + b'\0'), sub('WEAT', bytes(8))]
    if deleted:
        fields.append(sub('DELE', bytes(4)))
    return record('REGN', *fields)


def master(*regions):
    return record('TES3', sub('HEDR', b'\0' * 300)) + b''.join(regions)


def fog_c():
    return (SRC / 'aw_fog.c').read_text(encoding='utf-8')


class RegionDrawTable(unittest.TestCase):
    def test_the_table_is_solstheim_at_540_on_trial(self):
        table = region_draw.load()
        self.assertEqual(table['universal'], 300)
        rows = {r['id']: r for r in table['regions']}
        # the game's own region ids of Solstheim, as the script tracker knows them (tools/mwscript_features.py)
        import mwscript_features
        solstheim = {r for r in mwscript_features.ADDON_REGIONS if r.endswith(' region')}
        self.assertEqual(set(rows), solstheim)
        self.assertEqual(len(rows), 6)
        for ident, row in rows.items():
            # behind the setting until the maintainer's yes on the measured frame rate: state trial
            self.assertEqual((row['distance'], row['state']), (540, 'trial'), ident)

    def test_one_universal_value(self):
        import build_aga
        self.assertEqual(region_draw.load()['universal'], build_aga.DEFAULT_FOG_DISTANCE)
        self.assertIn('#define DRAW_UNIVERSAL %d ' % build_aga.DEFAULT_FOG_DISTANCE, fog_c())
        self.assertIn('cvar_t aw_drawdistance = {"aw_drawdistance","%d",true};' % build_aga.DEFAULT_FOG_DISTANCE,
                      (SRC / 'r_main.c').read_text(encoding='latin-1'))

    def test_the_engine_reads_the_same_file_and_row_count(self):
        c = fog_c()
        self.assertIn('#define REGION_DRAW_PATH "%s"' % region_draw.OUTPUT, c)
        self.assertIn('#define REGION_ROWS %d' % region_draw.ENGINE_ROWS, c)
        # Auto on by default, the trial rows off by default, both saved
        self.assertIn('static cvar_t aw_drawdistance_auto={"aw_drawdistance_auto","1",true};', c)
        self.assertIn('static cvar_t aw_fog_region_trial={"aw_fog_region_trial","0",true};', c)

    def test_bad_tables_are_refused(self):
        import json
        import tempfile
        good = region_draw.load()
        bad = [dict(good, universal=50), dict(good, regions=good['regions'] * 3),
               dict(good, regions=[dict(good['regions'][0], id='Brodir Grove Region')]),
               dict(good, regions=[dict(good['regions'][0], state='on')]),
               dict(good, regions=[dict(good['regions'][0], distance=5000)]),
               dict(good, regions=[good['regions'][0], good['regions'][0]]), dict(good, format='x')]
        with tempfile.TemporaryDirectory() as tmp:
            for i, table in enumerate(bad):
                path = Path(tmp) / ('t%d.json' % i)
                path.write_text(json.dumps(table), encoding='utf-8')
                with self.subTest(i=i), self.assertRaises(ValueError):
                    region_draw.load(path)


class RegionDrawWriter(unittest.TestCase):
    MASTER = master(regn(b'Ashlands Region', b'Ashlands'), regn(b'Moesring Mountains Region', b'Moesring Mountains'),
                    regn(b'Ascadian Isles Region', b'Ascadian Isles'), regn(b'Brodir Grove Region', b'Brodir Grove'),
                    regn(b'Old Region', b'Old', deleted=True), regn(b'Thirsk Region', b'Thirsk'))

    def test_the_index_is_the_region_catalogues(self):
        # the same order as world/region-names.awn (tools/prepare_world_ui.py region_names): sorted folded ids
        from prepare_world_ui import region_names
        order = region_draw.region_order(self.MASTER)
        self.assertEqual(order, ['ascadian isles region', 'ashlands region', 'brodir grove region',
                                 'moesring mountains region', 'thirsk region'])
        raw = region_names(self.MASTER)
        names, = struct.unpack_from('<I', raw, 4)
        labels = [raw[16 + 64 * i:16 + 64 * (i + 1)].rstrip(b'\0').decode() for i in range(names)]
        self.assertEqual(labels, ['Ascadian Isles', 'Ashlands', 'Brodir Grove', 'Moesring Mountains', 'Thirsk'])

    def test_the_file_the_engine_parses(self):
        text, report = region_draw.table_text(region_draw.load(), region_draw.region_order(self.MASTER))
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith('#') and lines[1] == 'universal 300')
        rows = [line.split(' ', 3) for line in lines if line[:1].isdigit()]
        # aw_fog.c region_table_read: index, distance, then the state's first letter
        self.assertEqual([(int(i), int(d), s[0]) for i, d, s, _ in rows], [(2, 540, 't'), (3, 540, 't'), (4, 540, 't')])
        self.assertEqual({r[3] for r in rows}, {'brodir grove region', 'moesring mountains region', 'thirsk region'})
        self.assertEqual(sorted(report['not_in_masters']), ['felsaad coast region', 'hirstaang forest region',
                                                            'isinfier plains region'])
        self.assertTrue(all(len(line) < 96 for line in lines))          # the engine's line buffer
        # the base game alone: no Solstheim, no rows, the universal value everywhere
        base, report = region_draw.table_text(region_draw.load(), ['ascadian isles region', 'ashlands region'])
        self.assertEqual([line for line in base.splitlines() if line[:1].isdigit()], [])
        self.assertEqual(report['trial_rows'], 0)

    def test_written_at_the_image_step(self):
        aga = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("region_draw.write(args.data_files,boot/'id1')", aga)
        self.assertLess(aga.index('validate_world_ui(boot/\'id1\')'), aga.index('region_draw.write('))

    def test_another_starting_distance_turns_auto_off(self):
        import build_aga
        self.assertNotIn('aw_drawdistance_auto', build_aga.startup_config('map seyda\n'))
        self.assertIn('aw_drawdistance 448\naw_drawdistance_auto 0\n', build_aga.startup_config('map seyda\n', 448))


class RegionDrawEngineSide(unittest.TestCase):
    def test_one_owner_and_no_work_in_the_frame_path(self):
        c = re.sub(r'/\*.*?\*/', '', fog_c(), flags=re.S)
        # the renderer, the ring, the sky haze and the menu read one number
        self.assertIn('int AW_DrawDistance(void) {return effective;}', c)
        # only the rule writes it
        self.assertEqual(len(re.findall(r'\beffective=(?!DRAW_UNIVERSAL)', c)), 1)
        self.assertIn('effective=aw_fog_location_hook?aw_fog_location_hook(d):d;', c)
        # the watch runs once per rendered view, before the far plane is set
        cull = c.split('void AW_CullBegin(void) {')[1].split('\n}')[0]
        self.assertLess(cull.index('AW_DrawDistanceWatch();'), cull.index('AW_DrawDistance()'))
        # a map arrival sets it before the CHIM ring is primed
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        spawn = scene.split('void AW_SceneSpawn(edict_t *p) {')[1]
        self.assertLess(spawn.index('AW_DrawDistanceArrive('), spawn.index('aw_chim_spawn('))

    def test_menu_auto_row_in_the_place_of_reset(self):
        menu = (SRC / 'aw_menu.c').read_text(encoding='utf-8')
        self.assertIn('ROW_FOG,ROW_FOG_AUTO,ROW_FOG_INDOORS', menu)
        self.assertIn('"Fog distance auto: On":"Fog distance auto: Off"', menu)
        self.assertNotIn('Reset distance: 300', menu)

    def test_console_help_and_page(self):
        table = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(table, re.compile(r'^VIDEO\|fog auto\|aw_drawdistance_auto\|', re.M))
        self.assertRegex(table, re.compile(r'^VIDEO\|fog region trial\|aw_fog_region_trial\|', re.M))
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg fog auto`', page)
        self.assertIn('`dbg fog region trial`', page)
        boolean = (SRC / 'aw_boolean.h').read_text(encoding='utf-8')
        self.assertIn('"aw_drawdistance_auto"', boolean)
        self.assertIn('"aw_fog_region_trial"', boolean)


if __name__ == '__main__':
    unittest.main()
