"""Generic town import: Balmora outputs identical to the pre-generic code, the
Arena config, the runtime town table and the registry checks.

Uses synthetic terrain, placements and BSP payloads only; no game data.
"""
import copy
import importlib.util
import json
import math
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from town_config import load_settings, load_registry, runtime_towns, validate_town  # noqa: E402
from town_regions import regions, owner  # noqa: E402

CONVERTER = importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL')


def synthetic_grids(settings, seed=7):
    """Deterministic heights and materials for every cell under the frame.

    Repaired tiles carry their recorded source material, as the owned data does.
    """
    rng = random.Random(seed)
    low, high = settings['bounds']
    cells = {(math.floor((settings['centre'][0] + x / settings['scale']) / 8192),
              math.floor((settings['centre'][1] + y / settings['scale']) / 8192))
             for x in (low[0], high[0] - 1) for y in (low[1], high[1] - 1)}
    xs = range(min(c[0] for c in cells), max(c[0] for c in cells) + 1)
    ys = range(min(c[1] for c in cells), max(c[1] for c in cells) + 1)
    grids = {}
    for cx in xs:
        for cy in ys:
            materials = [[rng.choice((8, 14, 34, 35)) for _ in range(16)] for _ in range(16)]
            grids[cx, cy] = {'heights': [[rng.randrange(-64, 2400) for _ in range(65)] for _ in range(65)],
                             'materials': materials}
    for repair in settings.get('terrain_material_repairs', []):
        grids[tuple(repair['cell'])]['materials'][repair['tile'][1]][repair['tile'][0]] = repair['source_material']
    return grids


def bsp(text):
    from player_hull import pack_lumps
    return pack_lumps([text.encode('cp1252') + b'\0'] + [bytes(4 * (i + 1)) for i in range(14)])


def door_references(settings, count=9, seed=3):
    rng = random.Random(seed)
    low, high = settings['bounds']
    references, index = [], {'references': []}
    for n in range(count):
        x = rng.uniform(low[0] + 64, high[0] - 64); y = rng.uniform(low[1] + 64, high[1] - 64)
        source = [settings['centre'][0] + x / settings['scale'], settings['centre'][1] + y / settings['scale'], rng.uniform(0, 900)]
        number = 1000 + n
        ref = {'number': number, 'type': 'DOOR' if n % 4 else 'STAT', 'position': source,
               'destination': {'position': [1, 2, 3]} if n % 3 else None,
               'destination_cell': ('Balmora, Lucky Lockup' if n % 2 else None)}
        references.append(ref)
        if n != 5:
            index['references'].append({'number': number, 'bounds': [[v - 40 for v in source], [v + 40 for v in source]]})
    return references, index


class BalmoraMatchesLegacy(unittest.TestCase):
    """Balmora's config-derived outputs from the generic code equal v0.0.31-dev5's."""

    def test_region_partition_and_names(self):
        import town_legacy_reference as legacy
        settings = load_settings('balmora')
        self.assertEqual(regions(settings), legacy.regions(copy.deepcopy(settings)))
        plain = {k: v for k, v in settings.items() if k != 'town'}
        self.assertEqual(regions(plain), legacy.regions(copy.deepcopy(plain)))
        for variant in ({'region_core_overrides': {}}, {'bounds': [[-1536, -768], [1536, 3840]], 'region_core_overrides': {}}):
            s = {**settings, **variant}
            self.assertEqual(regions(s), legacy.regions(copy.deepcopy(s)))
        entries = regions(settings)
        self.assertEqual([e['name'] for e in entries], [f'bm{i:03d}' for i in range(64)])
        for point in ([0, 0], [-3072, -3072], [3072, 3072], [100.5, -2000], [-1, 767]):
            self.assertEqual(owner(point, entries), legacy.owner(point, entries))

    @unittest.skipUnless(CONVERTER, 'optional conversion dependencies')
    def test_map_text_for_every_region(self):
        import town_legacy_reference as legacy
        import import_town
        import prepare_balmora
        settings = load_settings('balmora'); grids = synthetic_grids(settings)
        timings = '"aw_eye_height" "22"\n"aw_hand_idle" "0.5"'
        for entry in regions(settings):
            spawn = [(entry['core'][0][i] + entry['core'][1][i]) / 2 for i in range(2)]
            spawn.append(legacy.terrain_at(grids, settings, *spawn)[0] + 40)
            self.assertEqual(import_town.terrain_at(grids, settings, *spawn[:2]), legacy.terrain_at(grids, settings, *spawn[:2]))
            old = legacy.terrain_map(entry, grids, copy.deepcopy(settings), spawn, timings)
            self.assertEqual(import_town.terrain_map(entry, grids, settings, spawn, timings), old, entry['name'])
            self.assertEqual(prepare_balmora.terrain_map(entry, grids, settings, spawn, timings), old)
            self.assertIn('"message" "Balmora"', old)

    @unittest.skipUnless(CONVERTER, 'optional conversion dependencies')
    def test_published_maps_region_and_door_files(self):
        import town_legacy_reference as legacy
        import import_town
        settings = load_settings('balmora'); entries = regions(settings)
        references, index = door_references(settings)
        arrival, yaw = [412.25, -903.5, 90.875], 271.5
        returning, return_yaw = [-60.5, 1180.25, 52.875], 12.0
        npcs = ['{\n"classname" "aw_npc"\n"aw_ref" "77"\n}']
        outputs = []
        with tempfile.TemporaryDirectory() as tmp:
            for name, publish in (('legacy', legacy.publish), ('generic', import_town.publish)):
                root = Path(tmp) / name; scene = root / 'scene'; out = root / 'work'
                (scene / 'id1/maps').mkdir(parents=True)
                for entry in entries:
                    (out / entry['name']).mkdir(parents=True)
                    (out / entry['name'] / 'scene.bsp').write_bytes(bsp('{\n"classname" "worldspawn"\n"message" "' + entry['name'] + '"\n}\n'))
                publish(scene, out, copy.deepcopy(settings), entries, references, index, npcs, arrival, yaw, returning, return_yaw)
                outputs.append({p.relative_to(scene).as_posix(): p.read_bytes() for p in sorted(scene.rglob('*')) if p.is_file()})
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(len(outputs[0]), 64 + 3)
        self.assertIn('id1/maps/balmora.bsp', outputs[1])
        self.assertTrue(outputs[1]['id1/scene-doors-balmora.txt'].startswith(b'AWD3\nbalmora - 100'))

    @unittest.skipUnless(CONVERTER, 'optional conversion dependencies')
    def test_travel_points_and_cli(self):
        import town_legacy_reference as legacy
        import import_town
        import prepare_balmora
        balmora = load_settings('balmora')
        seyda = json.loads((ROOT / 'config/seyda_area.json').read_text())
        def dodt(settings, x, y, z, rz):
            return ('DODT', struct.pack('<6f', settings['centre'][0] + x / settings['scale'],
                                        settings['centre'][1] + y / settings['scale'], z, 0, 0, rz))
        kinds = {'NPC_': {'darvame hleran': [('NAME', b'x'), dodt(balmora, 400, -900, 300, 1.25), dodt(seyda, 99999, 0, 0, 0)],
                          'selvil sareloth': [dodt(seyda, -60, 1100, 140, 4.5)]}}
        self.assertEqual(import_town.arrival_point(kinds, balmora), legacy.travel_point(kinds, 'darvame hleran', balmora))
        self.assertEqual(import_town.return_point(kinds, balmora), legacy.travel_point(kinds, 'selvil sareloth', seyda))
        args = prepare_balmora.parser(town=False).parse_args(['--data-files', 'd', '--scene', 's', '--out', 'o', '--qbsp', 'q', '-j', '3'])
        self.assertEqual((args.vis_mode, args.jobs, args.collect_only, args.ffmpeg), ('fast', 3, False, 'ffmpeg'))
        with self.assertRaises(SystemExit):
            import_town.parser().parse_args(['--data-files', 'd', '--scene', 's', '--out', 'o'])


class ArenaConfig(unittest.TestCase):
    def test_frame_regions_and_registry(self):
        s = load_settings('vivec_arena')
        entries = regions(s)
        self.assertEqual([e['name'] for e in entries], [f'va{i:03d}' for i in range(16)])
        self.assertEqual((s['core_size'], s['overlap'], s['draw_distance'], s['model_budget']), (768, 896, 540, 220))
        # Centred on the canton centre piece within one terrain material tile.
        self.assertLessEqual(abs(s['centre'][0] - 36544), 256)
        self.assertLessEqual(abs(s['centre'][1] - -86912), 256)
        self.assertEqual([v % 512 for v in s['centre']], [0, 0])
        self.assertEqual([math.floor(v / 8192) for v in s['centre']], s['source_cell'])
        # The audited source square covers the whole frame.
        for x in s['bounds'][0][0], s['bounds'][1][0]:
            cell = math.floor((s['centre'][0] + x / s['scale']) / 8192)
            self.assertLessEqual(abs(cell - s['source_cell'][0]), s['source_radius'])
        for y in s['bounds'][0][1], s['bounds'][1][1]:
            cell = math.floor((s['centre'][1] + y / s['scale']) / 8192)
            self.assertLessEqual(abs(cell - s['source_cell'][1]), s['source_radius'])
        self.assertIsNone(s['town']['return'])

    @unittest.skipUnless(CONVERTER, 'optional conversion dependencies')
    def test_explicit_arrival_frame_filter_and_texts(self):
        import import_town
        s = load_settings('vivec_arena')
        point, yaw = import_town.arrival_point({'NPC_': {}}, s)
        self.assertEqual(point, [48.0, 431.25, 490.625])
        self.assertAlmostEqual(yaw, 270, places=4)
        self.assertIsNotNone(owner(point, regions(s)))
        self.assertEqual(import_town.return_point({}, s), ([0, 0, 0], 0))
        inside = {'position': [36352 + 6144, -87040 - 6144, 0]}
        outside = {'position': [36352 + 6145, -87040, 0]}
        self.assertTrue(import_town.in_frame(inside, s))
        self.assertFalse(import_town.in_frame(outside, s))
        self.assertTrue(import_town.in_frame(outside, load_settings('balmora')))
        grids = synthetic_grids(s)
        text = import_town.terrain_map(regions(s)[5], grids, s, point, '')
        self.assertIn('"message" "Vivec, Arena"', text)
        header = import_town.region_directory_text(s, regions(s), point, yaw, [0, 0, 0], 0).splitlines()[0]
        self.assertTrue(header.startswith('AWBR1 16 96 540 48.0 431.25 490.625 '))
        self.assertTrue(header.endswith(' 0 0 0 0'))
        references, index = door_references(s)
        self.assertTrue(import_town.door_bank_text(s, references, index).startswith('AWD3\nvivec_arena - '))


class ArenaFootprint(unittest.TestCase):
    """VIVEC-ARENA-ACTORS-32: residents inside the frame stand on neighbouring
    canton walkways whose origin lies outside it; the frame keeps every object
    whose footprint reaches in, and exterior architecture keeps the authored
    collision surfaces a convex proxy would bury."""

    def reference(self, number, origin, low, high, kind='STAT', model='x/ex_test.nif'):
        to_source = lambda x, y: [36352 + x * 4, -87040 + y * 4]
        return {'number': number, 'type': kind, 'model': model, 'position': [*to_source(*origin), 0],
                'bounds': [[*to_source(*low), 0], [*to_source(*high), 100]]}

    def test_footprint_reaches_into_frame(self):
        import import_town
        s = load_settings('vivec_arena')
        canton = self.reference(1, (-1808, 32), (-2700, -737), (-917, 801))
        far = self.reference(2, (-2600, 32), (-2700, -737), (-1600, 801))
        self.assertFalse(import_town.in_frame(canton, s))
        self.assertTrue(import_town.footprint_in_frame(canton, s))
        self.assertFalse(import_town.footprint_in_frame(far, s))
        self.assertTrue(import_town.footprint_in_frame(far, load_settings('balmora')))

    @unittest.skipUnless(CONVERTER, 'optional conversion dependencies')
    def test_frame_selection_measures_every_audited_visible_placement(self):
        import import_town
        s = load_settings('vivec_arena')
        placements = [self.reference(1, (-1808, 32), (-2700, -737), (-917, 801)),
                      self.reference(2, (-2600, 32), (-2700, -737), (-1600, 801)),
                      self.reference(3, (40, 40), (30, 30), (50, 50)),
                      self.reference(4, (-1146, -452), (-1146, -452), (-1146, -452), 'NPC_', ''),
                      self.reference(5, (-1700, 0), (-1700, 0), (-1700, 0), 'NPC_', '')]
        seen = {}

        def export(data, out, refs, groups, centre, metadata=None, jobs=None):
            seen['refs'] = [r['number'] for r in refs]
            out.mkdir(parents=True)
            (out / 'scenery-index.json').write_text(json.dumps({'references': refs}))
            return {'errors': []}
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(import_town, 'export_refs', export):
            out = Path(tmp)
            numbers = import_town.footprint_references(None, out, placements, s, 1)
            self.assertEqual(seen['refs'], [1, 2, 3])  # residents are points: never exported
            self.assertEqual(numbers, {1, 3})
            self.assertFalse((out / 'frame-footprint').exists())
            (out / 'audit').mkdir(); (out / 'scenery').mkdir()
            (out / 'audit/placements.json').write_text(json.dumps(placements))
            (out / 'scenery/scenery-index.json').write_text(json.dumps(
                {'references': [p for p in placements if p['number'] in numbers]}))
            # Resume: the frame is the origin test plus the converted footprint.
            self.assertEqual([r['number'] for r in import_town.frame_references(out, s)], [1, 3, 4])

    def test_exterior_architecture_profile(self):
        from town_regions import visual_profile
        from player_hull import STEP_HEIGHT
        self.assertEqual(visual_profile('meshes/x/ex_vivec_c_04.nif', 6000)['surface_collision_beyond'], STEP_HEIGHT)
        listed = visual_profile('meshes/x/ex_hlaalu_b_01.nif', 100)
        self.assertTrue(listed['hollow_collision'])
        self.assertNotIn('surface_collision_beyond', listed)
        for organic in ('meshes/f/terrain_rock_wg_13.nif', 'meshes/f/flora_bc_tree_02.nif'):
            self.assertNotIn('surface_collision_beyond', visual_profile(organic, 500))


class TownTable(unittest.TestCase):
    def test_checked_in_engine_table_matches_configs(self):
        import town_table
        self.assertTrue(town_table.check(), 'run tools/town_table.py --write')
        rows = runtime_towns()
        self.assertEqual([r['name'] for r in rows][:3], ['seyda', 'balmora', 'vivec_arena'])
        self.assertEqual([r['world_slot'] for r in rows], [0, 1] + [-1] * (len(rows) - 2))
        arena = rows[2]
        self.assertEqual(arena['origin'], [9088.0, -21760.0, 0.0])
        self.assertEqual(arena['core'], [[-1440, -1440], [1440, 1440]])

    def test_registry_rejects_unsafe_towns(self):
        good = dict(load_settings('vivec_arena')['town'])
        settings = load_settings('vivec_arena')
        validate_town(good, settings)
        for change in ({'map_prefix': 'vf'}, {'map_prefix': 'v1'}, {'map': 'Vivec'}, {'map': 'a' * 16},
                       {'region_cap': 65}, {'region_cap': 0}, {'door_file': 'doors.txt'},
                       {'message': 'x"y'}, {'arrival': {}}, {'arrival': {'travel_npc': 'a', 'source_position': [0, 0, 0]}},
                       {'return': {'travel_npc': 'a'}}, {'region_file': '../x.txt'}, {'map': 'va001'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_town({**good, **change}, settings)

    def test_registry_order_and_uniqueness(self):
        registry = load_registry()
        self.assertEqual([t['id'] for t in registry['towns']][:2], ['seyda', 'balmora'])
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; shutil.copytree(ROOT / 'config', config)
            data = json.loads((config / 'towns.json').read_text())
            data['towns'][2]['world_slot'] = 1
            (config / 'towns.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runtime_towns(tmp)
            data['towns'][2]['world_slot'] = -1
            arena = json.loads((config / 'vivec_arena.json').read_text())
            arena['town']['map_prefix'] = 'bm'
            (config / 'towns.json').write_text(json.dumps(data))
            (config / 'vivec_arena.json').write_text(json.dumps(arena))
            with self.assertRaises(ValueError):
                runtime_towns(tmp)
            data['towns'][0], data['towns'][1] = data['towns'][1], data['towns'][0]
            (config / 'towns.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_registry(tmp)


if __name__ == '__main__':
    unittest.main()
