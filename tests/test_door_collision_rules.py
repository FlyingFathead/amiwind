# SPDX-License-Identifier: GPL-3.0-only
"""The three converter rules of DOOR-USE-COLLISION-FILLED-53 (the region-frame entrances the converted collision
blocked), on small synthetic shapes:

- the standing-room rule (mesh_geometry.collision_parts standing_room): a convex piece may not fill the room a player
  stands in over an authored floor (the Redoran guard towers' top rooms over their trapdoors);
- the plate-bevels rule (chim.build.model_exact_bevels): a CHIM model whose converter asked for exact standing bevels
  on some of its pieces takes them for the whole model (the Daedric shrine entry steps);
- the door detail tiles (chim.build.door_detail_tiles): the original LAND samples at a load door the coarse terrain
  tiles bury (the Dwemer doors of Nchuleft and Bthungthumz).
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import mesh_geometry  # noqa: E402
import mesh_geometry_env  # noqa: E402
from chim.build import door_detail_tiles, door_detail_on, model_exact_bevels  # noqa: E402


def room(size=256., height=192.):
    """A closed room (Morrowind units): floor, four walls and a roof, every face turned inward (the floor up), one
    connected component; the convex hull of it is the whole room."""
    s, h = size / 2, height
    p = np.array([[-s, -s, 0], [s, -s, 0], [s, s, 0], [-s, s, 0], [-s, -s, h], [s, -s, h], [s, s, h], [-s, s, h]],
                 float)
    # x, y, z and a texture mapping (u, v), as the converter's vertex arrays hold them
    v = np.column_stack([p, (p[:, 0] + p[:, 2]) / 64, (p[:, 1] + p[:, 2]) / 64])
    quads = [(0, 1, 2, 3),        # floor, up
             (7, 6, 5, 4),        # roof, down
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]     # walls, inward
    f = []
    for a, b, c, d in quads:
        f += [(a, b, c, 0), (a, c, d, 0)]
    return v, np.array(f, int)


def inside_any(pieces, point, depth=1.):
    for points, hull, _, _ in pieces:
        eq = hull.equations
        if ((np.asarray(point) @ eq[:, :3].T + eq[:, 3]) < -depth).all():
            return True
    return False


class StandingRoom(unittest.TestCase):
    def test_a_piece_closing_a_room_over_a_floor_is_split(self):
        v, f = room()
        centre = (0., 0., 20.)            # converter units (x 0.25): 20 over the floor, under the 48-unit roof
        before = mesh_geometry.collision_parts(v, f, 2, plates=[])
        self.assertTrue(inside_any(before, centre), 'the plain convex proxy fills the room')
        plates = []
        after = mesh_geometry.collision_parts(v, f, 2, plates=plates, standing_room=mesh_geometry.STANDING_ROOM_DEPTH)
        self.assertFalse(inside_any(after, centre), 'a player stands in the room over its floor')
        # the authored surfaces are still there: the floor holds a player up
        floor = [p for p, _, _, _ in after if np.ptp(p[:, 2]) < 1 and p[:, 2].max() < 1]
        self.assertTrue(floor)

    def test_a_solid_block_and_a_flight_are_left_alone(self):
        # a closed box turned outward (a crate): its walkable top is the hull's boundary, nothing over it is filled
        v, f = room(256., 64.)
        f = f[:, [0, 2, 1, 3]]                # every face turned outward: the top faces up, the bottom down
        plain = mesh_geometry.collision_parts(v, f, 2, plates=[])
        rule = mesh_geometry.collision_parts(v, f, 2, plates=[], standing_room=mesh_geometry.STANDING_ROOM_DEPTH)
        self.assertEqual(len(plain), len(rule))
        # floor samples under a hull that reaches less than a step over them are not caught
        samples = np.array([[0., 0., 0.]])
        from scipy.spatial import ConvexHull
        low = ConvexHull(np.array([[x, y, z] for x in (-8, 8) for y in (-8, 8) for z in (-4, 8.)]))
        self.assertFalse(mesh_geometry._closes_over_floor(low, samples, 1.))
        high = ConvexHull(np.array([[x, y, z] for x in (-8, 8) for y in (-8, 8) for z in (-4, 40.)]))
        self.assertTrue(mesh_geometry._closes_over_floor(high, samples, 1.))

    def test_the_measured_table_is_the_default_and_checked(self):
        with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: ''}):
            self.assertEqual(mesh_geometry_env.standing_room_mode('0.0.54-dev1'), 'table')
        for mode in ('all', 'off'):
            with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: mode}):
                self.assertEqual(mesh_geometry_env.standing_room_mode('0.0.54-dev1'), mode)
        with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: 'maybe'}):
            with self.assertRaises(ValueError):
                mesh_geometry_env.standing_room_mode()
        table = mesh_geometry_env.standing_room_meshes()
        self.assertIn('meshes/x/ex_redoran_tower_01.nif', table)
        applies = mesh_geometry_env.standing_room_applies
        self.assertTrue(applies('meshes\\x\\Ex_Redoran_Tower_01.nif', 'table', table))
        self.assertFalse(applies('meshes/x/ex_hlaalu_b_01.nif', 'table', table))
        self.assertTrue(applies('meshes/x/ex_hlaalu_b_01.nif', 'all', table))
        self.assertFalse(applies('meshes/x/ex_redoran_tower_01.nif', 'off', table))
        # the CHIM model builder reads the table
        text = (ROOT / 'tools/chim/build.py').read_text(encoding='utf-8')
        self.assertIn("standing_room_applies(model['source'], standing_room, standing_meshes)", text)


class ReleaseTakesTheDefaults(unittest.TestCase):
    """The methods before are debug only: a release build (rc or final VERSION) refuses them, so a shipped image is
    built with the repository's rules whatever the machine's environment (the public builder builds what we ship)."""

    def test_a_release_version_refuses_the_debug_methods(self):
        cases = ((mesh_geometry_env.STANDING_ROOM_VARIABLE, 'off', mesh_geometry_env.standing_room_mode),
                 (mesh_geometry_env.STANDING_ROOM_VARIABLE, 'all', mesh_geometry_env.standing_room_mode),
                 (mesh_geometry_env.PLATE_BEVELS_VARIABLE, 'drop', mesh_geometry_env.plate_bevels_mode))
        for variable, old, mode in cases:
            with patch.dict(os.environ, {variable: old}):
                self.assertEqual(mode('0.0.54-dev1'), old)                  # a dev build may A/B
                for release in ('0.0.54', '0.0.54-rc1'):
                    with self.assertRaises(ValueError):
                        mode(release)
            with patch.dict(os.environ, {variable: ''}):
                self.assertNotEqual(mode('0.0.54'), old)                   # the default always passes
        # the build entry refuses them for rc and final before any stage (the converters never read the version: a
        # version change may not re-key the CHIM world)
        from project_version import require_private_test_version
        with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: 'off',
                                     mesh_geometry_env.PLATE_BEVELS_VARIABLE: 'drop'}):
            waivers = mesh_geometry_env.debug_collision_waivers()
            self.assertEqual(len(waivers), 2)
            require_private_test_version('0.0.54-dev1', waivers)
            for release in ('0.0.54', '0.0.54-rc1'):
                with self.assertRaises(ValueError):
                    require_private_test_version(release, waivers)
        with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: '',
                                     mesh_geometry_env.PLATE_BEVELS_VARIABLE: ''}):
            self.assertEqual(mesh_geometry_env.debug_collision_waivers(), [])
        text = (ROOT / 'tools/build_exclusions.py').read_text(encoding='utf-8')
        self.assertIn('waivers = debug_collision_waivers()', text)
        self.assertNotIn("'VERSION'", (ROOT / 'tools/mesh_geometry_env.py').read_text(encoding='utf-8'))
        self.assertEqual(mesh_geometry_env.refuse_in_release('terrain_door_detail', 'on', 'on', '0.0.54'), 'on')
        with self.assertRaises(ValueError):
            mesh_geometry_env.refuse_in_release('terrain_door_detail', 'off', 'on', '0.0.54')


class PlateBevels(unittest.TestCase):
    def test_pieces_that_asked_for_exact_bevels_make_the_model_exact(self):
        self.assertTrue(model_exact_bevels({'collision_bevels': 'exact standing-box convex sum'}, 'drop'))
        self.assertTrue(model_exact_bevels({'collision_bevels_pieces': [3, 7]}, 'mesh'))
        self.assertFalse(model_exact_bevels({'collision_bevels_pieces': [3, 7]}, 'drop'))   # the method before
        self.assertFalse(model_exact_bevels({}, 'mesh'))
        self.assertFalse(model_exact_bevels({'collision_bevels_pieces': []}, 'mesh'))

    def test_the_mode_is_mesh_by_default_and_checked(self):
        with patch.dict(os.environ, {mesh_geometry_env.PLATE_BEVELS_VARIABLE: ''}):
            self.assertEqual(mesh_geometry_env.plate_bevels_mode(), 'mesh')
            self.assertTrue(model_exact_bevels({'collision_bevels_pieces': [1]}))
        with patch.dict(os.environ, {mesh_geometry_env.PLATE_BEVELS_VARIABLE: 'drop'}):
            self.assertFalse(model_exact_bevels({'collision_bevels_pieces': [1]}))
        with patch.dict(os.environ, {mesh_geometry_env.PLATE_BEVELS_VARIABLE: 'axial'}):
            with self.assertRaises(ValueError):
                mesh_geometry_env.plate_bevels_mode()

    def test_the_chim_variant_reads_the_rule(self):
        # chim.build's variant task takes the model's exact flag through model_exact_bevels, not the mesh-wide lod
        # flag alone (the positions were dropped before)
        text = (ROOT / 'tools/chim/build.py').read_text(encoding='utf-8')
        self.assertIn('exact = model_exact_bevels(prepared[mi][4])', text)
        self.assertNotIn("exact = bool(prepared[mi][4].get('collision_bevels'))", text)


class SeydaTakesTheChimRules(unittest.TestCase):
    """The Seyda Neen frame converted its models with its legacy scenery profiles, without the CHIM model builder's
    collision rules: the tall house's outdoor flight closed a path-grid point (AMBIENT-WALK-STUCK-COLLISION-54)."""

    def test_the_rules_are_added_to_a_legacy_profile(self):
        from chim.build import chim_collision_rules, seyda_collision_mode
        with patch.dict(os.environ, {mesh_geometry_env.STANDING_ROOM_VARIABLE: ''}):
            p = chim_collision_rules({'ratio': .5}, 'meshes/x/ex_common_house_tall_02.nif', flight=True)
            self.assertTrue(p['stair_plates'] and p['visible_treads'])
            self.assertEqual(p['ratio'], .5)
            self.assertNotIn('standing_room', p)
            t = chim_collision_rules({}, 'meshes/x/ex_redoran_tower_01.nif')
            self.assertEqual(t['standing_room'], mesh_geometry.STANDING_ROOM_DEPTH)
            self.assertNotIn('stair_collision', t)
        self.assertEqual(seyda_collision_mode(None), 'chim')
        self.assertEqual(seyda_collision_mode({'seyda_collision': 'legacy'}), 'legacy')
        with self.assertRaises(ValueError):
            seyda_collision_mode({'seyda_collision': 'maybe'})
        text = (ROOT / 'tools/chim/seyda.py').read_text(encoding='utf-8')
        self.assertIn("chim_collision_rules(profile, model['source'], mi in flight_meshes)", text)


class DoorDetail(unittest.TestCase):
    SETTINGS = {'centre': [0., 0.], 'scale': .25}

    @staticmethod
    def door(x, y, z, destination='Test Tomb'):
        # Morrowind units; the frame is the centre at 0 and scale 0.25
        return {'type': 'DOOR', 'destination': destination, 'position': [x * 4, y * 4, z * 4]}

    def tiles(self, refs, original):
        heights = [[100.] * 4 for _ in range(4)]       # coarse corners every 128 units from (0, 0): all at 100
        return door_detail_tiles(refs, self.SETTINGS, original, heights, [0, 0], [384, 384], 128)

    def test_a_door_in_a_dip_the_coarse_tiles_bury_keeps_the_original_samples(self):
        dip = lambda x, y: 0. if abs(x - 192) < 40 and abs(y - 192) < 40 else 100.
        got = self.tiles([self.door(192, 192, 2)], dip)
        self.assertIn((128, 128), got)                 # the door's own tile
        self.assertTrue(all(0 <= x < 384 and 0 <= y < 384 for x, y in got))

    def test_doors_on_the_coarse_ground_up_high_or_without_a_destination_change_nothing(self):
        flat = lambda x, y: 100.
        self.assertEqual(self.tiles([self.door(192, 192, 101)], flat), set())          # coarse ground holds it
        dip = lambda x, y: 0.
        self.assertEqual(self.tiles([self.door(192, 192, 400)], dip), set())           # a tower door
        self.assertEqual(self.tiles([self.door(192, 192, 2, destination=None)], dip), set())   # no load door
        self.assertEqual(self.tiles([self.door(900, 192, 2)], dip), set())             # outside the ground
        mound = lambda x, y: 200.
        self.assertEqual(self.tiles([self.door(192, 192, 200)], mound), set())   # the coarse ground under the door

    def test_the_mode_is_on_by_default_and_checked(self):
        self.assertTrue(door_detail_on(None))
        self.assertFalse(door_detail_on({'terrain_door_detail': 'off'}))
        with self.assertRaises(ValueError):
            door_detail_on({'terrain_door_detail': 'maybe'})


if __name__ == '__main__':
    unittest.main()
