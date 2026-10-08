"""Vivec canton towns, explicit handoff cores and town interiors (door banks).

Synthetic configs, doors and BSP bytes only; no game data.
"""
import copy
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from town_config import (handoff_core, interiors, load_registry, load_settings, runtime_towns,  # noqa: E402
                         town_interiors, validate_town)
from town_regions import owner, regions  # noqa: E402
import town_interiors as ti  # noqa: E402

CANTONS = ('vivec_foreign', 'vivec_hlaalu', 'vivec_redoran', 'vivec_telvanni', 'vivec_temple', 'vivec_delyn',
           'vivec_olms')


def global_rect(settings, rect):
    """Frame-local rectangle to original coordinates."""
    return [[settings['centre'][k] + rect[0][k] / settings['scale'] for k in range(2)],
            [settings['centre'][k] + rect[1][k] / settings['scale'] for k in range(2)]]


class CantonConfigs(unittest.TestCase):
    def test_registry_appends_the_cantons_after_the_arena(self):
        ids = [t['id'] for t in load_registry()['towns']]
        self.assertEqual(ids[:3], ['seyda', 'balmora', 'vivec_arena'])
        self.assertEqual(tuple(ids[3:3 + len(CANTONS)]), CANTONS)
        for row in load_registry()['towns'][3:]:
            self.assertEqual(row['world_slot'], -1)
            self.assertIsNone(row['travel'])

    def test_blocked_towns_stay_in_the_table_but_not_in_the_build(self):
        import importlib.util
        blocked = [t['id'] for t in load_registry()['towns'] if t.get('blocked')]
        self.assertTrue(set(blocked) <= set(CANTONS))
        self.assertTrue(set(blocked) <= {r['id'] for r in runtime_towns()})
        if blocked and importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL'):
            import import_town
            with self.assertRaisesRegex(ValueError, 'blocked'):
                import_town.prepare(blocked[0], '/nonexistent', '/nonexistent', '/nonexistent', 'q', 'v', 'l')
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; shutil.copytree(ROOT / 'config', config)
            data = json.loads((config / 'towns.json').read_text())
            data['towns'][3]['blocked'] = ' '
            (config / 'towns.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runtime_towns(tmp)

    def test_frames_cores_and_sources(self):
        prefixes = set()
        for town in CANTONS:
            with self.subTest(town=town):
                s = load_settings(town)
                entries = regions(s)
                self.assertLessEqual(len(entries), s['town']['region_cap'])
                self.assertEqual((s['core_size'], s['overlap'], s['draw_distance'], s['model_budget']), (768, 896, 540, 220))
                self.assertEqual([v % 512 for v in s['centre']], [0, 0])
                prefixes.add(s['town']['map_prefix'])
                # The frame edge stays beyond draw distance + 32 from the core.
                core = handoff_core(s)
                for k in range(2):
                    self.assertGreaterEqual(core[0][k] - s['bounds'][0][k], s['draw_distance'] + 32)
                    self.assertGreaterEqual(s['bounds'][1][k] - core[1][k], s['draw_distance'] + 32)
                # The audited source square covers the whole frame.
                for k in range(2):
                    for v in (s['bounds'][0][k], s['bounds'][1][k] - 1):
                        cell = math.floor((s['centre'][k] + v / s['scale']) / 8192)
                        self.assertLessEqual(abs(cell - s['source_cell'][k]), s['source_radius'])
                # Arrival: inside the town's own handoff core and region set.
                position = s['town']['arrival']['source_position']
                local = [(position[k] - s['centre'][k]) * s['scale'] for k in range(2)]
                self.assertTrue(all(core[0][k] <= local[k] <= core[1][k] for k in range(2)))
                self.assertIsNotNone(owner(local, entries))
        self.assertEqual(len(prefixes), len(CANTONS))

    def test_canton_handoff_cores_tile_without_overlap(self):
        rects = [global_rect(load_settings(t), handoff_core(load_settings(t))) for t in CANTONS]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(all(max(a[0][k], b[0][k]) < min(a[1][k], b[1][k]) for k in range(2)), (a, b))

    def test_runtime_rows_use_the_explicit_handoff_core(self):
        rows = {r['id']: r for r in runtime_towns()}
        self.assertEqual(rows['vivec_arena']['core'], [[-1440, -1440], [1440, 1440]])
        for town in CANTONS:
            s = load_settings(town)
            self.assertEqual(rows[town]['core'], s['handoff_core'])
            self.assertEqual(rows[town]['origin'], [v * .25 for v in s['centre']] + [0.])

    def test_interiors_are_unique_and_named_by_position(self):
        rooms = town_interiors()
        self.assertEqual(len({r['map'] for r in rooms}), len(rooms))
        self.assertEqual(len({r['cell'].casefold() for r in rooms}), len(rooms))
        for town in CANTONS:
            s = load_settings(town)
            listed = interiors(s)
            self.assertTrue(listed, town)
            self.assertEqual([r['map'] for r in listed], [s['town']['map_prefix'] + 'i%03d' % i for i in range(len(listed))])
            for room in listed:
                self.assertEqual(room['exclude'] is None, 'exclude' not in s['interiors'][listed.index(room)])


class HandoffAndInteriorValidation(unittest.TestCase):
    def settings(self):
        return copy.deepcopy(load_settings('vivec_redoran'))

    def test_handoff_core_default_and_margin(self):
        arena = load_settings('vivec_arena')
        self.assertEqual(handoff_core(arena), [[-1440, -1440], [1440, 1440]])
        s = self.settings()
        margin = s['draw_distance'] + 32
        s['handoff_core'] = [[s['bounds'][0][0] + margin, -100], [100, s['bounds'][1][1] - margin]]
        self.assertEqual(handoff_core(s), s['handoff_core'])
        for core in ([[s['bounds'][0][0] + margin - 1, -100], [100, 100]], [[0, 0], [0, 10]], [[0, 0]],
                     [[0, 0], [10, 'x']], [[10, 10], [0, 0]], [[0, 0], [10, float('nan')]]):
            with self.subTest(core=core), self.assertRaises(ValueError):
                validate_town(s['town'], {**s, 'handoff_core': core})

    def test_interior_rows(self):
        s = self.settings()
        ok = {**s, 'interiors': [{'cell': 'Room A'}, {'cell': 'Room B', 'exclude': 'too big'}]}
        self.assertEqual(interiors(ok), [
            {'map': s['town']['map_prefix'] + 'i000', 'cell': 'Room A', 'exclude': None},
            {'map': s['town']['map_prefix'] + 'i001', 'cell': 'Room B', 'exclude': 'too big'}])
        for rows in ([{'cell': 'A'}, {'cell': 'a'}], [{'cell': ''}], [{'cell': 'x"y'}], [{'cell': 'A', 'exclude': ' '}],
                     [{'cell': 'A', 'map': 'x'}], [{'name': 'A'}], [{'cell': 'A\nB'}], [{'cell': 'x' * 64}], {'cell': 'A'}):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_town(s['town'], {**s, 'interiors': rows})

    def test_resident_exclusions(self):
        from town_config import resident_exclusions
        s = self.settings()
        self.assertEqual(resident_exclusions(s), resident_exclusions({**s, 'resident_exclusions': {}}))
        self.assertEqual(resident_exclusions({**s, 'resident_exclusions': {'Some NPC': 'bake budget'}}), {'some npc'})
        for rows in ({'a': ''}, {'': 'x'}, {'a"b': 'x'}, ['a'], {'a': 3}):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_town(s['town'], {**s, 'resident_exclusions': rows})

    def test_a_room_belongs_to_one_town(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; shutil.copytree(ROOT / 'config', config)
            first = json.loads((config / 'vivec_foreign.json').read_text())
            second = json.loads((config / 'vivec_hlaalu.json').read_text())
            second['interiors'].append({'cell': first['interiors'][0]['cell'].upper()})
            (config / 'vivec_hlaalu.json').write_text(json.dumps(second))
            with self.assertRaises(ValueError):
                town_interiors(tmp)


def door(number, source, target, destination, rotation=0.0, interior=True):
    return {'number': number, 'source_cell': source, 'destination_cell': target, 'destination_interior': interior,
            'destination': {'position': destination, 'rotation_radians': [0, 0, rotation]}}


class DoorBanks(unittest.TestCase):
    def towns(self):
        a = {'centre': [1000, 2000], 'scale': .25}
        b = {'centre': [9000, 2000], 'scale': .25}
        # Overlapping cores: the earlier frame wins, as in aw_world.c.
        return [('ta', 'Town A', a, [[-500, -500], [500, 500]]), ('tb', 'Town B', b, [[-2500, -500], [500, 500]])]

    def test_exit_town_is_first_in_table_order(self):
        towns = self.towns()
        self.assertEqual(ti.exit_town([1000, 2000, 0], towns)[0], 'ta')
        self.assertEqual(ti.exit_town([3100, 2000, 0], towns)[0], 'tb')  # outside A, inside B
        self.assertEqual(ti.exit_town([2000, 2000, 0], towns)[0], 'ta')  # in both: A first
        self.assertIsNone(ti.exit_town([90000, 2000, 0], towns))

    def test_room_bank_links_rooms_exits_and_unavailable_doors(self):
        towns = self.towns()
        rooms = {'room b': 'tai001'}
        doors = [door(12, 'Room A', 'Room B', [40, -80, 8], math.pi / 2),
                 door(11, 'Room A', '', [1400, 2000, 100], 0.0, interior=False),
                 door(13, 'Room A', 'Room C', [1, 2, 3]),
                 door(14, 'Room A', '', [90000, 0, 0], 0.0, interior=False)]
        bounds = {n: [[-8, -8, 0], [8, 8, 120]] for n in (11, 12, 13, 14)}
        rows = ti.room_bank('tai000', doors, rooms, towns, bounds)
        self.assertEqual([r.split(' ')[2] for r in rows], ['11', '12', '13', '14'])
        exit_, inner, missing, outside = (r.split('\t') for r in rows)
        self.assertEqual(exit_[1], 'Town A')
        self.assertEqual(exit_[0].split(' ')[:3], ['tai000', 'ta', '11'])
        values = list(map(float, exit_[0].split(' ')[3:]))
        self.assertEqual(values[:6], [-2.5, -2.5, -.5, 2.5, 2.5, 30.5])
        self.assertEqual(values[6:], [100.0, 0.0, 25 + 16.875, 90.0])
        self.assertEqual(inner[0].split(' ')[:2], ['tai000', 'tai001'])
        self.assertEqual(list(map(float, inner[0].split(' ')[9:])), [10.0, -20.0, 2 + 16.875, 0.0])
        self.assertEqual(inner[1], 'Room B')
        self.assertEqual(missing[0].split(' ')[1], '-')
        self.assertEqual(list(map(float, missing[0].split(' ')[9:])), [0, 0, 0, 0])
        self.assertEqual((outside[0].split(' ')[1], outside[1]), ('-', 'Exterior world'))
        text = ti.bank_text(rows)
        self.assertTrue(text.startswith('AWD3\ntai000 ta 11 ') and text.endswith('\n'))
        with self.assertRaises(ValueError):
            ti.bank_text(rows * 40)

    def test_exterior_bank_links_listed_rooms_only(self):
        import importlib.util
        if not (importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL')):
            self.skipTest('optional conversion dependencies')
        import import_town
        s = load_settings('vivec_redoran')
        x, y = s['centre']
        references = [
            {'number': 5, 'type': 'DOOR', 'position': [x, y, 0], 'destination_cell': 'Room A',
             'destination': {'position': [100, -40, 12], 'rotation_radians': [0, 0, math.pi]}},
            {'number': 6, 'type': 'DOOR', 'position': [x + 40, y, 0], 'destination_cell': 'Room B',
             'destination': {'position': [1, 2, 3], 'rotation_radians': [0, 0, 0]}}]
        index = {'references': [{'number': n, 'bounds': [[x - 8, y - 8, 0], [x + 8, y + 8, 96]]} for n in (5, 6)]}
        plain = import_town.door_bank_text(s, references, index).splitlines()
        linked = import_town.door_bank_text(s, references, index, {'room a': 'vri000'}).splitlines()
        self.assertEqual(plain[2], linked[2])
        self.assertTrue(plain[1].startswith('vivec_redoran - 5 '))
        self.assertTrue(linked[1].startswith('vivec_redoran vri000 5 '))
        self.assertTrue(linked[1].endswith(' 25.0 -10.0 19.875 270.0 Room A'), linked[1])
        many = references[:1] * (ti.BANK_ROWS + 1)
        with self.assertRaises(ValueError):
            import_town.door_bank_text(s, many, index)

    def test_available_rooms_skip_excluded_and_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config'; shutil.copytree(ROOT / 'config', config)
            data = json.loads((config / 'vivec_redoran.json').read_text())
            data['interiors'] = [{'cell': 'Room A'}, {'cell': 'Room B', 'exclude': 'over a limit'}, {'cell': 'Room C'}]
            (config / 'vivec_redoran.json').write_text(json.dumps(data))
            rooms = ti.available_rooms(tmp, {'room c': False})
            self.assertEqual(rooms['room a'], data['town']['map_prefix'] + 'i000')
            self.assertNotIn('room b', rooms)
            self.assertNotIn('room c', rooms)
            names = [t[0] for t in ti.frame_towns(tmp)]
            self.assertEqual(names[:2], ['vivec_arena', 'vivec_foreign'])

    def test_bsp_extent(self):
        from player_hull import pack_lumps
        model = struct.pack('<6f', -10, -20, -30, 4100.5, 20, 30) + bytes(40)
        raw = pack_lumps([b'\0'] + [bytes(4)] * 13 + [model])
        self.assertEqual(ti.bsp_extent(raw), 4100.5)
        self.assertGreaterEqual(ti.bsp_extent(raw), ti.COORD_LIMIT)


class TownTableInteriors(unittest.TestCase):
    def test_header_lists_every_room_with_its_town(self):
        import town_table
        header = town_table.render_header()
        rooms = town_interiors()
        self.assertIn('#define AW_TOWN_INTERIOR_COUNT %d' % len(rooms), header)
        for room in rooms:
            self.assertIn('"%s"' % room['map'], header)
        ids = [r['id'] for r in runtime_towns()]
        block = header.split('#define AW_TOWN_INTERIOR_TOWNS {')[1].split('}')[0]
        values = [int(v) for v in block.replace('\\', ' ').replace(',', ' ').split()]
        self.assertEqual(values, [ids.index(r['town']) for r in rooms])

    def test_cli_has_dry_run(self):
        import importlib.util
        if not (importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL')):
            self.skipTest('optional conversion dependencies')
        import import_town
        args = import_town.parser().parse_args(['--town', 'vivec_redoran', '--data-files', 'd', '--scene', 's',
                                                '--out', 'o', '--dry-run'])
        self.assertTrue(args.dry_run)


if __name__ == '__main__':
    unittest.main()
