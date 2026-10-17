"""Seyda Neen's scene without a BSP29 compile of its cell-aligned CHIM frame (BUILD-SEYDA-HULL2-32, v0.0.41-dev2).

The bsp stage makes a CHIM-native Seyda Neen's scene map as the source-only carrier (entities and exact model
boxes, no qbsp/vis/light); the opening objects the engine activates are checked at once (carrier) and again
per frame map (town frame, sncourt, intro_docks) before the CHIM frame is read. No original assets, compiler
or emulator."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import build
import chim_town
import prepare_mesh_bsp as mesh
import prepare_opening_refs as opening
import prepare_seyda_source as source
import retired_flags
from area_config import BOUNDS
from chim.frame_map import activated_expected, activated_missing, activated_refs
from player_hull import lumps, pack_lumps
from prepare_quake import CENTRE, SCALE
from test_build_builder import plan
from test_seyda_source_carrier import BARREL, fixture

PAPERS, HALL_DOOR = 172859, 172860


def exterior_refs(index, barrel=True):
    """opening_references' exterior references for the fixture: its placements (barrel included or not)."""
    rows = [dict(r) for r in index['references'] if barrel or r['number'] != BARREL]
    return rows


class CarrierSceneTests(unittest.TestCase):
    def carrier(self, root, drop_barrel_entity=False):
        alias, scenery, index, data = fixture(root)
        (alias / 'id1/progs').mkdir(parents=True)
        (alias / 'id1/progs/m000.mdl').write_bytes(b'alias static')
        barrel = next(r for r in index['references'] if r['number'] == BARREL)
        wanted = [dict(barrel)]
        out = root / 'bsp-scene'
        real_seed = source.seed

        def seed(*args, **kwargs):
            raw, record = real_seed(*args, **kwargs)
            if drop_barrel_entity:
                parts = lumps(raw)
                text = parts[0].decode('cp1252').replace('"aw_ref" "%d"' % BARREL, '"aw_ref" "1"')
                parts[0] = text.encode('cp1252')
                raw = pack_lumps(parts)
            return raw, record
        with patch.object(mesh, '_prepare_model', side_effect=lambda task: (task[0], data)), \
                patch('subprocess.run', side_effect=AssertionError('no compiler may run for the carrier')), \
                patch.object(mesh, 'compile_standing_hull', side_effect=AssertionError('no standing hull compile')), \
                patch('mwad.paths.resolve_data_files', side_effect=lambda p: Path(p)), \
                patch.object(opening, 'opening_references',
                             return_value=(exterior_refs(index), wanted, set())), \
                patch.object(source, 'seed', side_effect=seed), \
                contextlib.redirect_stdout(io.StringIO()):
            result = mesh.prepare_carrier(alias, out, scenery, root / 'data', jobs=1)
        return out, result, index

    def test_carrier_scene_needs_no_bsp29_compile_and_keeps_the_barrel(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, result, _ = self.carrier(Path(tmp))
            raw = (out / 'id1/maps/seyda.bsp').read_bytes()
            self.assertEqual(raw, (out / 'seyda.bsp').read_bytes())
            self.assertTrue(source.is_source_carrier(raw))
            self.assertFalse(any(lumps(raw)[k] for k in (3, 7, 8)))       # no vertices, faces or lightmaps
            self.assertEqual(result['format'], mesh.CARRIER_SCENE_FORMAT)
            self.assertFalse(result['terrain_compiled'])
            self.assertEqual(result['activated'], {'expected': [BARREL], 'present': [BARREL]})
            ready = json.loads((out / 'scene-ready.json').read_text())
            self.assertEqual(ready['standing_hull_profile'], mesh.PROFILE)
            self.assertFalse((out / 'id1/progs/m000.mdl').exists())      # alias statics left as in the compiled path
            self.assertNotIn('progs/m000.mdl', (out / 'seyda.map').read_text())
            # the scene record binds the source entities (SHA-256), as chim_town reads it
            self.assertEqual(chim_town.source_carrier_record(out, raw)['format'], mesh.CARRIER_SCENE_FORMAT)
            (out / 'source-entities.json').write_text('{"format": "tampered"}')
            with self.assertRaisesRegex(ValueError, 'source carrier'):
                chim_town.source_carrier_record(out, raw)

    def test_carrier_refuses_a_missing_activated_object_naming_it(self):
        with tempfile.TemporaryDirectory() as tmp, \
                self.assertRaisesRegex(ValueError, r'seyda: activated object 172851 \(AW_REF_COURTYARD_BARREL\)'):
            self.carrier(Path(tmp), drop_barrel_entity=True)

    def test_widened_cell_aligned_frame_is_the_shipped_seyda_area(self):
        # the frame stays cell-aligned seam to seam (v0.0.40): the carrier exists because of exactly this box
        area = json.loads((ROOT / 'config/seyda_area.json').read_text())
        self.assertEqual(area['bounds'], [[-3328, -4608], [4864, 3584]])
        self.assertEqual(area['handoff_core'], area['bounds'])
        self.assertEqual([list(b) for b in BOUNDS], area['bounds'])

    def test_opening_stage_binds_by_reference_and_never_appends_to_a_carrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _, index = self.carrier(Path(tmp))
            barrel = next(r for r in index['references'] if r['number'] == BARREL)
            moved = dict(barrel, position=[barrel['position'][0] + 400, *barrel['position'][1:]])
            with patch('mwad.paths.unshare_tree'), patch.object(opening, 'resolve_data_files', side_effect=Path), \
                    patch.object(opening, 'opening_references', return_value=([], [moved], set())), \
                    patch.object(opening, 'append_meshes', side_effect=AssertionError('append refused')):
                result = opening.prepare(Path(tmp) / 'data', out)
            self.assertEqual(result['bound'], [BARREL])
            # without the barrel placement the carrier refuses (named), it never appends geometry
            parts = lumps((out / 'id1/maps/seyda.bsp').read_bytes())
            parts[0] = parts[0].decode('cp1252').replace('"aw_ref" "%d"' % BARREL, '"aw_ref" "7"').encode('cp1252')
            (out / 'id1/maps/seyda.bsp').write_bytes(pack_lumps(parts))
            with patch('mwad.paths.unshare_tree'), patch.object(opening, 'resolve_data_files', side_effect=Path), \
                    patch.object(opening, 'opening_references', return_value=([], [moved], set())), \
                    patch.object(opening, 'append_meshes', side_effect=AssertionError('append refused')), \
                    self.assertRaisesRegex(ValueError, 'seyda: source-only carrier is missing .* 172851'):
                opening.prepare(Path(tmp) / 'data', out)

    def test_frame_maps_activated_check_positive_and_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _, index = self.carrier(Path(tmp))
            raw = (out / 'id1/maps/seyda.bsp').read_bytes()
            maps, entries, models = chim_town.seyda_maps(raw)
            names = [e['name'] for e in entries[:-2]]
            with patch.object(opening, 'opening_references', return_value=(exterior_refs(index), [], set())), \
                    patch('mwad.paths.resolve_data_files', side_effect=lambda p: Path(p)):
                refused, record = chim_town.seyda_activated_check(Path(tmp), maps, models, names)
                self.assertEqual(refused, [])
                self.assertEqual(record['sncourt'], [BARREL])              # the Census courtyard sub-scene
                self.assertEqual(record['seyda'], [BARREL])                # the town frame
                maps['sncourt'] = [e for e in maps['sncourt'] if e.get('aw_ref') != str(BARREL)]
                refused, _ = chim_town.seyda_activated_check(Path(tmp), maps, models, names)
            self.assertEqual(refused, ["sncourt: activated object 172851 (AW_REF_COURTYARD_BARREL) is missing from "
                                       "the map's activated entities"])


class ActivatedRuleTests(unittest.TestCase):
    def ref(self, number, x, y):
        return {'number': number, 'position': [CENTRE[0] + x / SCALE, CENTRE[1] + y / SCALE, 0.0]}

    def test_every_engine_activated_reference_is_named(self):
        self.assertEqual(activated_refs(), {BARREL: 'AW_REF_COURTYARD_BARREL', PAPERS: 'AW_REF_CENSUS_PAPERS',
                                            HALL_DOOR: 'AW_REF_CENSUS_HALL_DOOR'})

    def test_expected_by_bounds_and_polygon(self):
        exterior = [self.ref(BARREL, 120, -45), self.ref(PAPERS, 2000, 2000), self.ref(42, 0, 0)]
        self.assertEqual(activated_expected(exterior, (-128, -384, 512, 256)), [BARREL])   # not 42: not activated
        self.assertEqual(activated_expected(exterior, (-4000, -4000, 4000, 4000)), [BARREL, PAPERS])
        square = [(-10, -10), (10, -10), (10, 10), (-10, 10)]                               # CCW, excludes BARREL
        self.assertEqual(activated_expected(exterior, (-4000, -4000, 4000, 4000), square), [])

    def test_missing_names_reference_and_map(self):
        rows = [{'classname': 'func_wall', 'aw_ref': str(BARREL), 'model': '*3'},
                {'classname': 'aw_npc', 'aw_ref': str(PAPERS)}]
        self.assertEqual(activated_missing('sncourt', [BARREL], rows), [])
        self.assertEqual(activated_missing('sncourt', [BARREL, PAPERS], rows),
                         ["sncourt: activated object 172859 (AW_REF_CENSUS_PAPERS) is missing from the map's "
                          "activated entities"])


class BuildPlanTests(unittest.TestCase):
    def bsp(self, argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return [str(p) for p in dict(plan(argv))['bsp']]

    def test_chim_native_seyda_takes_the_carrier_by_default(self):
        for argv in (['--jobs', '4'], ['--jobs', '4', '--dry-run']):
            with self.subTest(argv=argv):
                command = self.bsp(argv)
                self.assertEqual(command[command.index('--seyda-source') + 1], 'carrier')
                self.assertEqual(command[command.index('--data-files') + 1], str(Path('/owned')))

    def test_chim_miniwind_of_another_town_takes_the_carrier(self):
        # BUILD-MINIWIND-SEYDA-COMPILE-42: the whole town exceeds BSP29; the MiniWind image leaves Seyda Neen out
        for argv in (['--jobs', '4', '--miniwind', '--miniwind-town', 'vivec_city'],
                     ['--jobs', '4', '--miniwind-preset', 'vivec-palace'], ['--jobs', '4', '--miniwind']):
            with self.subTest(argv=argv):
                command = self.bsp(argv)
                self.assertEqual(command[command.index('--seyda-source') + 1], 'carrier')

    def test_legacy_chains_keep_the_compiled_town(self):
        for argv in (['--jobs', '4', '--builder', 'legacy'], ['--jobs', '4', '--legacy-area', 'seyda'],
                     ['--jobs', '4', '--chim-area', 'balmora'],
                     ['--jobs', '4', '--seyda-scene-source', 'compiled']):
            with self.subTest(argv=argv):
                self.assertNotIn('--seyda-source', self.bsp(argv))

    def test_carrier_refused_without_chim_native_seyda(self):
        with self.assertRaisesRegex(ValueError, 'needs a CHIM-native Seyda Neen'):
            self.bsp(['--jobs', '4', '--builder', 'legacy', '--seyda-scene-source', 'carrier'])

    def test_compiled_town_for_chim_native_seyda_is_a_retired_ab_option(self):
        args = build.parser().parse_args(['--seyda-scene-source', 'compiled'])
        self.assertIn('seyda-scene-compiled', [row['name'] for row in retired_flags.used(args)])
        self.assertEqual(retired_flags.used(build.parser().parse_args([])), [])

    def test_image_guard_takes_the_carrier_only_for_chim_native_seyda(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("if ready.get('format')==CARRIER_SCENE_FORMAT:", text)
        self.assertIn('if not seyda_native and not mini:', text)


if __name__ == '__main__':
    unittest.main()
