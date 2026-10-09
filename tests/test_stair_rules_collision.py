"""The universal stair rule in the shared collision layer (COLLISION-STAIR-SLOPE-32).

Synthetic meshes only (source units; the converter scales by 0.25):
- a flight inside a C-shaped wall: one convex proxy closes the flight, the rule
  restores the authored surfaces so no tread stays buried;
- a walkable ramp: no treads, the proxy is unchanged;
- risers above the step height: not a staircase, a wall stays a wall;
- the switch: off keeps the proxy; the builder exports the setting.
"""
import importlib.util
import os
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))
if READY:
    import numpy as np


def quad(v, f, corners):
    """Append a quad (4 corners, counter-clockwise seen from its front)."""
    start = len(v)
    v.extend(corners)
    f.extend([[start, start + 1, start + 2, 0], [start, start + 2, start + 3, 0]])


def staircase(rise=16., run=40., steps=4, width=160., wall=True):
    """Treads and risers along +x (source units), optionally inside a C wall."""
    v, f = [], []
    for k in range(steps):
        x0, z0, z1 = k * run, k * rise, (k + 1) * rise
        quad(v, f, [(x0, 0, z0), (x0, width, z0), (x0, width, z1), (x0, 0, z1)])          # riser, faces -x
        quad(v, f, [(x0, 0, z1), (x0 + run, 0, z1), (x0 + run, width, z1), (x0, width, z1)])  # tread, faces up
    if wall:
        top = (steps + 3) * rise
        length = steps * run
        quad(v, f, [(-8, -8, 0), (length, -8, 0), (length, -8, top), (-8, -8, top)])
        quad(v, f, [(length, width + 8, 0), (-8, width + 8, 0), (-8, width + 8, top), (length, width + 8, top)])
        quad(v, f, [(length, -8, 0), (length, width + 8, 0), (length, width + 8, top), (length, -8, top)])
    v = np.array(v, float)
    return np.hstack((v, np.zeros((len(v), 2)))), np.array(f)


def buried(pieces, v, f):
    """Treads whose centre (+0.5) lies inside a piece, more than a step below its top."""
    from mesh_geometry import stair_treads, _top_face
    from player_hull import STEP_HEIGHT, WALKABLE_Z
    tris = v[f[:, :3], :3] * .25
    out = []
    for i in stair_treads(v, f):
        c = tris[i].mean(axis=0)
        for points, hull, ids, error in pieces:
            if (hull.equations[:, :3] @ (c + [0, 0, .5]) + hull.equations[:, 3]).max() < -.01:
                top = _top_face(hull.equations, c)
                if top and (top[1] < WALKABLE_Z or top[0] - c[2] > STEP_HEIGHT + .5):
                    out.append(int(i))
    return out


@unittest.skipUnless(READY, 'numpy and scipy required')
class StairRuleTests(unittest.TestCase):
    def test_buried_flight_gets_authored_surfaces(self):
        from mesh_geometry import collision_parts, collision_pieces, stair_treads
        v, f = staircase()
        self.assertEqual(len(stair_treads(v, f)), 8)  # every tread of the flight
        before = collision_parts(v, f, 2)
        self.assertTrue(buried(before, v, f), 'the C wall proxy closes the flight')
        pieces, exact, note = collision_pieces(v, f, {}, stairs='on')
        self.assertFalse(buried(pieces, v, f))
        self.assertTrue(exact)
        self.assertIn('authored plates', note)

    def test_ramp_variant_keeps_flight_climbable(self):
        from mesh_geometry import collision_pieces
        v, f = staircase()
        pieces, exact, note = collision_pieces(v, f, {}, stairs='ramps')
        self.assertFalse(buried(pieces, v, f))

    def test_walkable_ramp_is_unchanged(self):
        from mesh_geometry import collision_parts, collision_pieces, stair_treads
        v, f = [], []
        quad(v, f, [(0, 0, 0), (200, 0, 100), (200, 160, 100), (0, 160, 0)])  # 26.6 degrees
        quad(v, f, [(0, 0, 0), (0, 160, 0), (200, 160, 0), (200, 0, 0)])
        v = np.hstack((np.array(v, float), np.zeros((len(v), 2)))); f = np.array(f)
        self.assertEqual(len(stair_treads(v, f)), 0)
        convex = collision_parts(v, f, 2)
        pieces, exact, note = collision_pieces(v, f, {}, stairs='on')
        self.assertEqual([(list(p[2]), p[3]) for p in pieces], [(list(p[2]), p[3]) for p in convex])
        self.assertEqual((exact, note), (False, None))

    def test_steps_above_the_step_height_stay_a_wall(self):
        from mesh_geometry import collision_parts, collision_pieces, stair_treads
        v, f = staircase(rise=48.)  # 12 units per riser > 8.5
        self.assertEqual(len(stair_treads(v, f)), 0)
        convex = collision_parts(v, f, 2)
        pieces, exact, note = collision_pieces(v, f, {}, stairs='on')
        self.assertEqual([(list(p[2]), p[3]) for p in pieces], [(list(p[2]), p[3]) for p in convex])
        self.assertIsNone(note)

    def test_surface_plates_of_a_mesh_with_stairs_get_exact_bevels(self):
        from mesh_geometry import collision_pieces
        v, f = staircase(wall=False)
        hollow = {'hollow_collision': True}
        pieces, exact, note = collision_pieces(v, f, hollow, stairs='on')
        self.assertIs(exact, True)
        self.assertIn('stairs', note)
        self.assertEqual(collision_pieces(v, f, hollow, stairs='off')[1:], (False, None))
        # A plate mesh without steps keeps its profile's bevels.
        flat, ff = [], []
        quad(flat, ff, [(0, 0, 0), (0, 160, 0), (200, 160, 0), (200, 0, 0)])
        flat = np.hstack((np.array(flat, float), np.zeros((4, 2))))
        self.assertEqual(collision_pieces(flat, np.array(ff), hollow, stairs='on')[1:], (False, None))

    def test_switch_off_keeps_the_proxy(self):
        from mesh_geometry import collision_parts, collision_pieces
        v, f = staircase()
        convex = collision_parts(v, f, 2)
        pieces, exact, note = collision_pieces(v, f, {}, stairs='off')
        self.assertEqual([(list(p[2]), p[3]) for p in pieces], [(list(p[2]), p[3]) for p in convex])
        self.assertIsNone(note)

    def test_build_option_changes_the_collision_output(self):
        # BUILD-STAIR-FLAG-INERT-32: v0.0.32 had follow_original_stair_rules in the builder
        # configuration, but no converter read it. The resolved option, exported the way
        # tools/build.py does, must change what the shared collision function builds.
        import mesh_geometry_env as env
        from mesh_geometry import collision_pieces
        v, f = staircase()
        saved = os.environ.get(env.VARIABLE)
        try:
            env.export_stair_rules(True)
            on = collision_pieces(v, f, {})
            env.export_stair_rules(False)
            off = collision_pieces(v, f, {})
        finally:
            if saved is None:
                os.environ.pop(env.VARIABLE, None)
            else:
                os.environ[env.VARIABLE] = saved
        self.assertFalse(buried(on[0], v, f))
        self.assertTrue(buried(off[0], v, f))
        self.assertNotEqual(on[1:], off[1:])

    def test_build_setting_reaches_the_shared_function(self):
        import mesh_geometry_env as env
        from mesh_geometry import stair_mitigation_mode
        saved = os.environ.get(env.VARIABLE)
        try:
            self.assertEqual(env.export_stair_rules(False), 'off')
            self.assertEqual(stair_mitigation_mode(), 'off')
            self.assertFalse(env.stair_rules_enabled())
            self.assertEqual(env.export_stair_rules(True), 'on')
            self.assertEqual(stair_mitigation_mode(), 'on')
            os.environ[env.VARIABLE] = 'bogus'
            with self.assertRaises(ValueError):
                env.stair_mode()
        finally:
            if saved is None:
                os.environ.pop(env.VARIABLE, None)
            else:
                os.environ[env.VARIABLE] = saved


class StairRulePlumbingTests(unittest.TestCase):
    def test_builder_exports_follow_original_stair_rules(self):
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('export_stair_rules(args.font_options["follow_original_stair_rules"])', source)
        self.assertLess(source.index('args.font_options = resolve_font_options(args)'),
                        source.index('export_stair_rules('))

    def test_image_step_runs_the_stair_gate_when_the_rules_are_on(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        call = source.index("require_stairs(boot/'id1', out/'stair-walk.json'")
        self.assertLess(source.rindex('if stair_rules_enabled():', 0, call), call)
        # On the final maps, after the last map rewrite (optimizer) and before the image.
        self.assertLess(source.index("verify_optimized_maps(boot/'id1/maps', optimization, jobs=jobs)"), call)

    def test_no_converter_builds_collision_outside_the_shared_function(self):
        """Collision proxies come from mesh_geometry.collision_pieces only; a new
        path would bypass the stair rule. prepare_bsp.py builds the legacy
        whole-town Seyda Neen preview proxies (COLLISION-SEYDA-PREVIEW-BYPASS-32;
        shipped images use the recorded Seyda stage instead). routed_hull.py only
        expands the pieces collision_pieces made by the standing box (the
        collider's own step, INTERIOR-HULL-CHAIN / COLLISION-HULL-CHAINS-33)."""
        allowed = {'mesh_geometry.py', 'prepare_bsp.py', 'routed_hull.py'}
        offenders = []
        for path in sorted((ROOT / 'tools').glob('*.py')):
            text = path.read_text(encoding='utf-8')
            if path.name in allowed:
                continue
            if re.search(r'\b(shell_)?collision_parts\(', text) or 'standing_planes(points' in text and 'collision_pieces' not in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [])
        users = sorted(p.name for p in (ROOT / 'tools').glob('*.py')
                       if 'collision_pieces(' in p.read_text(encoding='utf-8') and p.name != 'mesh_geometry.py')
        self.assertEqual(users, ['asset_census.py', 'prepare_mesh_bsp.py', 'world_estimate_data.py'])
        # Every map converter (towns, world, interiors, census, prison) assembles through prepare_mesh_bsp.
        for name in ('import_town.py', 'prepare_world_scenery.py', 'prepare_area.py', 'prepare_census.py',
                     'prepare_interior.py'):
            self.assertIn('append_meshes', (ROOT / 'tools' / name).read_text(encoding='utf-8'), name)


if __name__ == '__main__':
    unittest.main()
