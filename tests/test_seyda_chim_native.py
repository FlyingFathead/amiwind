"""Seyda Neen CHIM-native (v0.0.36-dev5, BUILD-LEGACY-TOWN-MAPS-SHIPPED-36): no legacy Seyda Neen map is made; the
frame and the opening scenes' frames take their entities from the scene stage's town (the game data)."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import chim_town  # noqa: E402
from player_hull import pack_lumps  # noqa: E402
import env_guard  # noqa: E402,F401

BARREL = '172851'   # aw_activated.h AW_REF_COURTYARD_BARREL


def town_map():
    """A complete converted town as the scene stage leaves it: worldspawn, start, two residents (one on the intro
    route, one far from it), the courtyard barrel (activated) and one static, both brush models."""
    text = ('{\n"classname" "worldspawn"\n"aw_hull" "h"\n"message" "Seyda Neen"\n}\n'
            '{\n"classname" "info_player_start"\n"origin" "16.0 44.0 74.0"\n"angle" "90"\n}\n'
            '{\n"classname" "aw_npc"\n"origin" "400 -300 20"\n"aw_ref" "172852"\n"aw_intro_role" "5"\n}\n'
            '{\n"classname" "aw_npc"\n"origin" "-1800 1800 20"\n"aw_ref" "128960"\n}\n'
            '{\n"classname" "func_wall"\n"model" "*1"\n"origin" "120 -45 46"\n"aw_ref" "%s"\n}\n'
            '{\n"classname" "func_wall"\n"model" "*2"\n"origin" "-500 -500 0"\n"aw_ref" "4242"\n}\n' % BARREL)
    data = [bytearray() for _ in range(15)]
    data[0] = bytearray(text.encode('ascii') + b'\0')
    world = struct.pack('<9f7i', -2000, -2000, -100, 2000, 2000, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    barrel = struct.pack('<9f7i', -8, -8, -9, 8, 8, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    static = struct.pack('<9f7i', -16, -16, 0, 16, 16, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    data[14] = bytearray(world + barrel + static)
    return bytes(pack_lumps(data))


class SeydaMaps(unittest.TestCase):
    def test_regions_and_opening_scenes_come_from_the_town_not_compiled_maps(self):
        maps, entries, models = chim_town.seyda_maps(town_map())
        from prepare_seyda_regions import regions
        names = [e['name'] for e in regions()]
        self.assertEqual([e['name'] for e in entries], names + ['intro_docks', 'sncourt'])
        refs = lambda name: sorted(e.get('aw_ref') for e in maps[name] if e.get('classname') == 'aw_npc')
        # every region keeps every actor (the runtime prunes them), as the legacy cut did
        self.assertEqual(refs(names[0]), ['128960', '172852'])
        # the intro docks keep the route's actor only (prepare_intro_docks.keep_entity, same rule as derive)
        self.assertEqual(refs('intro_docks'), ['172852'])
        rows, report = chim_town.seyda_frame_rows(maps, ['intro_docks'], 'intro_docks')
        self.assertEqual(rows[0]['classname'], 'worldspawn')
        self.assertEqual(rows[1]['origin'], '16.0 44.0 74.0')
        self.assertEqual(report['refused'], [])
        self.assertFalse(any(e.get('model', '').startswith('*') for e in rows))   # statics are CHIM placements
        from prepare_seyda_regions import default_region
        town, _ = chim_town.seyda_frame_rows(maps, names, default_region(regions())['name'])
        self.assertEqual(sorted(e['aw_ref'] for e in town if e.get('classname') == 'aw_npc'), ['128960', '172852'])

    def test_activated_barrel_takes_its_box_from_the_town(self):
        maps, _, models = chim_town.seyda_maps(town_map())
        found, refused = chim_town.seyda_activated(maps, models, ['sncourt'])
        self.assertEqual(refused, [])
        self.assertEqual([r['aw_ref'] for r in found], [BARREL])
        self.assertEqual(found[0]['_box'], [[-8, -8, -9], [8, 8, 9]])
        from chim.frame_map import native_activated_rows
        self.assertEqual(native_activated_rows(found)[0]['_box'], ((-8, -8, -9), (8, 8, 9)))

    def test_static_check_both_ways(self):
        maps, entries, _ = chim_town.seyda_maps(town_map())
        names = [e['name'] for e in entries[:-2]]
        ok, record = chim_town.seyda_static_check(maps, names, {4242: (0, 0, 0), int(BARREL): (0, 0, 0)}, {})
        self.assertEqual(ok, [])
        self.assertEqual(record['chim_only'], [])
        missing, _ = chim_town.seyda_static_check(maps, names, {int(BARREL): None}, {})
        self.assertIn('not in the CHIM world', missing[0])
        removed, _ = chim_town.seyda_static_check(maps, names, {int(BARREL): None}, {'harvest_removed': [4242]})
        self.assertEqual(removed, [])


class WalkReference(unittest.TestCase):
    def test_special_maps_walk_against_the_measured_legacy_reach(self):
        # no legacy special map to walk: the reach measured on it (v0.0.35 release, v0.0.36-dev3) is the reference
        from chim.frame_map import DOCK_ROUTE, LEGACY_WALK_REFERENCE
        self.assertEqual(LEGACY_WALK_REFERENCE['intro_docks']['route'], (6.9, 107.2))
        self.assertEqual(len(LEGACY_WALK_REFERENCE['intro_docks']['route']), len(DOCK_ROUTE))
        self.assertEqual(LEGACY_WALK_REFERENCE['sncourt']['reachable'], 603)
        source = (ROOT / 'tools/chim/frame_map.py').read_text(encoding='utf-8')
        self.assertIn("elif name in LEGACY_WALK_REFERENCE:", source)


class NoLegacySeydaInTheImage(unittest.TestCase):
    def test_image_step_cuts_no_seyda_region_maps_when_native(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("seyda_native='seyda' in chim_native_towns(args)", source)
        self.assertIn("if not mini and not seyda_native:\n        shutil.copyfile(out/'seyda.bsp',boot/'id1/maps/seyda.bsp')",
                      source)
        actor = (ROOT / 'tools/check_scene_actors.py').read_text(encoding='utf-8')
        self.assertIn('if seyda_chim_native:', actor)

    def test_never_built_maps_include_the_opening_scenes(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'seyda-regions.txt').write_text('AWBR1 1 96 540 0 0 64 90 0 0 64 90\nsn000 0 0 1 1 0 0 1 1\n',
                                                   encoding='ascii')
            names = build_aga.never_built_maps(id1, ['seyda'])
        self.assertEqual(names[:3], ['maps/seyda.bsp', 'maps/intro_docks.bsp', 'maps/sncourt.bsp'])
        self.assertIn('maps/sn000.bsp', names)

    def test_legacy_claims_name_seyda_specials(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'maps').mkdir()
            for name in ('seyda', 'intro_docks', 'sncourt', 'sn007'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'x')
            self.assertEqual(sorted(chim_town.legacy_claims(id1, 'seyda')),
                             ['maps/intro_docks.bsp', 'maps/seyda.bsp', 'maps/sn007.bsp', 'maps/sncourt.bsp'])


class PooledRewrite(unittest.TestCase):
    def test_a_read_only_pool_link_is_replaced_not_written(self):
        # BUILD-POOL-READONLY-SCENE-WRITE-35 (persisting): the area stage rewrote seyda.bsp, a read-only pool link
        import os
        from mwad.paths import replace_bytes, replace_copy
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pooled, staged = tmp / 'object', tmp / 'seyda.bsp'
            pooled.write_bytes(b'old')
            os.link(pooled, staged)
            os.chmod(staged, 0o444)
            replace_bytes(staged, b'new')
            self.assertEqual(staged.read_bytes(), b'new')
            self.assertEqual(pooled.read_bytes(), b'old')        # the pooled object is untouched
            os.link(pooled, tmp / 'copy.bsp')
            replace_copy(staged, tmp / 'copy.bsp')
            self.assertEqual((tmp / 'copy.bsp').read_bytes(), b'new')
            self.assertEqual(pooled.read_bytes(), b'old')
            self.assertEqual(sorted(p.name for p in tmp.iterdir()), ['copy.bsp', 'object', 'seyda.bsp'])
        from mwad.paths import unshare_tree
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'scene/id1').mkdir(parents=True)
            pooled, staged = tmp / 'object', tmp / 'scene/id1/doors-balmora.txt'
            pooled.write_bytes(b'doors')
            os.link(pooled, staged)
            os.chmod(staged, 0o444)
            (tmp / 'scene/id1/own.txt').write_bytes(b'own')
            self.assertEqual(unshare_tree(tmp / 'scene'), (1, 5))
            staged.write_bytes(b'rewritten in place')         # the stage's own write now works
            self.assertEqual(pooled.read_bytes(), b'doors')
            self.assertEqual(unshare_tree(tmp / 'scene'), (0, 0))  # only the first in-place stage copies
        for tool in ('prepare_census.py', 'prepare_area.py', 'prepare_door_audio.py', 'prepare_character.py',
                     'prepare_reading.py', 'prepare_opening_refs.py', 'import_town.py', 'prepare_balmora_interiors.py'):
            self.assertIn('unshare_tree(scene)', (ROOT / 'tools' / tool).read_text(encoding='utf-8'), tool)
        for tool in ('prepare_area.py', 'prepare_opening_refs.py'):
            source = (ROOT / 'tools' / tool).read_text(encoding='utf-8')
            self.assertNotIn("path.write_bytes(pack_lumps(b))", source)
            self.assertNotIn("shutil.copyfile(path,scene/'seyda.bsp')", source)


class SeydaPlan(unittest.TestCase):
    def test_default_plan_has_the_stage_after_the_scene_chain(self):
        import build_parallel
        from test_build_builder import plan
        steps = plan(['--jobs', '4'])
        deps = build_parallel.stage_dependencies(steps)['chim-town-seyda']
        # the complete town is finished by the area and opening-references stages (they write maps/seyda.bsp)
        for stage in ('chim', 'census', 'area', 'opening-references'):
            self.assertIn(stage, deps)
        command = [str(p) for p in dict(steps)['chim-town-seyda']]
        self.assertIn('--flora', command)
        self.assertIn('--town-scene-report', command)


class SeydaMiniWind(unittest.TestCase):
    def test_a_seyda_sandbox_keeps_its_rooms_and_the_survey(self):
        import miniwind
        for stage in ('area', 'world-survey'):
            self.assertIsNone(miniwind.omitted(stage, town='seyda'))
            self.assertIsNotNone(miniwind.omitted(stage))          # a Balmora sandbox still leaves them out
        self.assertIsNotNone(miniwind.omitted('world-terrain', town='seyda'))

    def test_preset_starts_at_seyda_neen(self):
        recipe = json.loads((ROOT / 'config/recipes/miniwind/seyda-chim.json').read_text(encoding='utf-8'))
        self.assertTrue(recipe['options']['miniwind'])
        self.assertEqual(recipe['options']['direct_to_game_map'], 'seyda_neen')
        import direct_start
        self.assertEqual(direct_start.AREA_ALIASES['seyda_neen'], 'seyda')

    def test_seyda_is_a_miniwind_town(self):
        import miniwind
        self.assertEqual(miniwind.check_town('seyda'), 'seyda')
        kept, prefix = miniwind.kept_maps(town='seyda')
        self.assertEqual(prefix, 'sn')
        self.assertIn('fargoth', kept)
        self.assertNotIn('census', kept)
        self.assertNotIn('prison', kept)


if __name__ == '__main__':
    unittest.main()
