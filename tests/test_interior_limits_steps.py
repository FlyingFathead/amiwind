# SPDX-License-Identifier: GPL-3.0-only
"""Interiors over a limit (docs/INTERIOR_SECTIONS.md): plants as sprites (tools/interior_plants.py) and room
recentring (town_interiors.room_offsets / recentre_cell)."""
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import interior_plants as plants
import town_config
import town_interiors


def sprite(width=2, height=2, pixels=b'\x10\xff\x20\xe0'):
    head = struct.pack('<4siifiiifi', b'IDSP', 1, 2, 1., width, height, 1, 0., 0)
    return head + struct.pack('<5i', 0, -width // 2, height, width, height) + pixels


class PlantSpriteTests(unittest.TestCase):
    def test_flora_meshes_only_trees_and_logs_stay(self):
        self.assertTrue(plants.is_flora_mesh('f/flora_bc_mushroom_07.nif'))
        self.assertTrue(plants.is_flora_mesh('meshes/f/flora_grass_01.nif'))
        self.assertFalse(plants.is_flora_mesh('f/flora_tree_bc_01.nif'))
        self.assertFalse(plants.is_flora_mesh('f/flora_bc_log_01.nif'))
        self.assertFalse(plants.is_flora_mesh('f/furn_de_tapestry_02.nif'))

    def test_candidates_keep_harvestables_and_solid_plants(self):
        refs = [{'number': 1, 'type': 'STAT', 'model': 'f\\Flora_grass_01.nif'},
                {'number': 2, 'type': 'CONT', 'model': 'f/flora_bc_mushroom_01.nif'},
                {'number': 3, 'type': 'STAT', 'model': 'f/flora_bc_mushroom_07.nif'},
                {'number': 4, 'type': 'STAT', 'model': 'f/furn_de_chair_01.nif'}]
        modes = {'f/flora_grass_01.nif': 'nonsolid', 'f/flora_bc_mushroom_07.nif': 'authored'}
        chosen, rows = plants.candidates(refs, lambda m: {'mode': modes[m], 'reason': modes[m]})
        self.assertEqual(chosen, [1])
        kept = {r['reference']: r['kept'] for r in rows}
        self.assertEqual(kept, {1: 'sprite', 2: 'mesh', 3: 'mesh'})

    def test_shade_row_follows_the_surface_rule(self):
        # bright light: the brightest rows, no light: the darkest; normal light near the identity row 32
        self.assertEqual(plants.shade_row(255), 0)
        self.assertEqual(plants.shade_row(0), 63)
        self.assertIn(plants.shade_row(128), (30, 31, 32))

    def test_shade_keeps_transparency_and_header(self):
        colormap = bytes((i + row) % 255 for row in range(64) for i in range(256))
        raw = sprite()
        out = plants.shade_sprite(raw, colormap, 128)
        row = plants.shade_row(128)
        self.assertEqual(out[:56], raw[:56])
        self.assertEqual(out[56:], bytes([(0x10 + row) % 255, 255, (0x20 + row) % 255, (0xe0 + row) % 255]))

    def test_names_are_stable_and_per_light(self):
        raw = sprite()
        a = plants.sprite_name('meshes/f/flora_grass_01.nif', 64, raw)
        self.assertEqual(a, plants.sprite_name('meshes/f/flora_grass_01.nif', 64, raw))
        self.assertNotEqual(a, plants.sprite_name('meshes/f/flora_grass_01.nif', 80, raw))
        self.assertRegex(a, r'^progs/aw_flora/f_[0-9a-f]{16}\.spr$')

    def test_light_level_steps(self):
        lighting = {'ambient': [64, 64, 64], 'lights': []}
        self.assertEqual(plants.light_level([0, 0, 0], lighting), 64)
        self.assertEqual(plants.light_level([0, 0, 0], {'ambient': [70, 70, 70], 'lights': []}) % plants.LIGHT_STEP, 0)

    def test_mode_switch(self):
        with mock.patch.dict(os.environ, {plants.PLANTS_ENV: ''}):
            self.assertEqual(plants.plant_mode(), 'auto')
        with mock.patch.dict(os.environ, {plants.PLANTS_ENV: 'meshes'}):
            self.assertEqual(plants.plant_mode(), 'meshes')
        with mock.patch.dict(os.environ, {plants.PLANTS_ENV: 'all'}):
            with self.assertRaises(ValueError):
                plants.plant_mode()


class RecentreTests(unittest.TestCase):
    def test_config_accepts_three_numbers_only(self):
        rows = town_config.interiors({'interiors': [{'cell': 'A', 'recentre': [0, -1024, 0]}, {'cell': 'B'}]})
        self.assertEqual(rows[0]['recentre'], [0., -1024., 0.])
        self.assertNotIn('recentre', rows[1])
        for bad in ([1, 2], [1, 2, 'x'], [True, 0, 0], [1e9, 0, 0]):
            with self.assertRaises(ValueError):
                town_config.interiors({'interiors': [{'cell': 'A', 'recentre': bad}]})

    def test_config_plants_row(self):
        rows = town_config.interiors({'interiors': [{'cell': 'A', 'plants': 'sprites'}, {'cell': 'B'}]})
        self.assertEqual(rows[0]['plants'], 'sprites')
        self.assertNotIn('plants', rows[1])
        with self.assertRaises(ValueError):
            town_config.interiors({'interiors': [{'cell': 'A', 'plants': 'all'}]})

    def test_recentre_moves_refs_entrances_and_water(self):
        cell = {'name': 'A', 'water_height': 10., 'refs': [{'number': 1, 'position': [100, 200, 30]}],
                'entrances': [{'destination': {'position': [110, 210, 40], 'rotation_radians': [0, 0, 0]}}]}
        out = town_interiors.recentre_cell(cell, [100, 1000, 10])
        self.assertEqual(out['refs'][0]['position'], [0, -800, 20])
        self.assertEqual(out['entrances'][0]['destination']['position'], [10, -790, 30])
        self.assertEqual(out['water_height'], 0.)
        self.assertEqual(cell['refs'][0]['position'], [100, 200, 30])  # the original stays
        self.assertIs(town_interiors.recentre_cell(cell, [0, 0, 0]), cell)

    def test_arrivals_and_door_boxes_follow_the_offset(self):
        destination = {'position': [4000, 0, 0], 'rotation_radians': [0, 0, 0]}
        moved, _ = town_interiors.local_arrival(destination, offset=[4000, 0, 0])
        plain, _ = town_interiors.local_arrival(destination)
        self.assertAlmostEqual(plain[0] - moved[0], 1000.)
        door = {'number': 7, 'destination_interior': True, 'destination_cell': 'B', 'destination': destination}
        rows = town_interiors.room_bank('r1', [door], {'b': 'r2'}, [], {7: [[4000, 0, 0], [4004, 4, 4]]},
                                        {'b': [4000, 0, 0]}, [4000, 0, 0])
        fields = rows[0].split('\t')[0].split()
        self.assertEqual(fields[1], 'r2')
        self.assertAlmostEqual(float(fields[3]), -.5)      # door box x moved by the room's own offset
        self.assertAlmostEqual(float(fields[9]), 0.)       # arrival x moved by the target room's offset


class RoomSpawnTests(unittest.TestCase):
    def cell(self, water):
        def arrival(z):
            return {'destination': {'position': [0, 0, z], 'rotation_radians': [0, 0, 0]}}
        return {'water_height': water, 'entrances': [arrival(-141), arrival(96)]}

    def test_the_spawn_is_the_first_dry_arrival(self):
        import prepare_area
        with mock.patch.dict(os.environ, {prepare_area.ROOM_SPAWN_ENV: ''}):
            self.assertEqual(prepare_area.spawn_entrance(self.cell(0))['destination']['position'][2], 96)
            # no water, or every arrival under it: the first arrival as before
            self.assertEqual(prepare_area.spawn_entrance(self.cell(None))['destination']['position'][2], -141)
            self.assertEqual(prepare_area.spawn_entrance(self.cell(500))['destination']['position'][2], -141)
        with mock.patch.dict(os.environ, {prepare_area.ROOM_SPAWN_ENV: 'first'}):
            self.assertEqual(prepare_area.spawn_entrance(self.cell(0))['destination']['position'][2], -141)


if __name__ == '__main__':
    unittest.main()
