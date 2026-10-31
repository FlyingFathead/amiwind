# SPDX-License-Identifier: GPL-3.0-only
"""The meshopt seam gate (MESHOPT-HOT-MODELS-57, tools/meshopt.py seam_check): a simplified model never opens a seam,
a crack or a gap where parts or neighbouring models meet. Open edges (by exact position) before and after: no new one,
no lost one; simplify_locked keeps a part whole when its result would fail. The hot-model recipe rows and the room
that uses them are checked too."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import meshopt  # noqa: E402
from test_mesh_methods import grid  # noqa: E402


def wavy(x, y):
    return 4.0 * np.sin(x / 9.0) * np.cos(y / 7.0)


def two_parts():
    """Two grids with different materials meeting along x = 64 (the shared line is a seam, not an open edge)."""
    v1, f1 = grid(12, 64.0, 0, wavy)
    v2, f2 = grid(12, 64.0, 1, wavy)
    v2 = v2.copy()
    v2[:, 0] += 64.0
    v2[:, 2] = wavy(v2[:, 0], v2[:, 1])
    f2 = f2.copy()
    f2[:, :3] += len(v1)
    return np.vstack((v1, v2)), np.vstack((f1, f2))


class OpenEdgeTests(unittest.TestCase):
    def test_two_triangles(self):
        v = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
        f = np.array([[0, 1, 2, 0], [0, 2, 3, 0]])
        self.assertEqual(len(meshopt.open_edges(v, f)), 4)

    def test_shared_line_between_parts_is_not_open(self):
        v, f = two_parts()
        # the outline of the 128 x 64 sheet only: 12 + 12 + 12 + 12 + 12 + 12 edges; the line at x = 64 is shared
        self.assertEqual(len(meshopt.open_edges(v, f)), 72)

    def test_a_crack_and_a_gap_fail(self):
        v, f = two_parts()
        crack = np.delete(f, 100, axis=0)
        self.assertGreater(meshopt.seam_check(v, f, crack)['new_open'], 0)
        self.assertFalse(meshopt.seam_ok(v, f, crack))
        # a rim moved: the right part's left column shifted off the shared line (a gap to the neighbour)
        moved = v.copy()
        left = (moved[:, 0] == 64.0) & (np.arange(len(v)) >= len(v) // 2)
        moved[left, 0] += 0.5
        self.assertFalse(meshopt.seam_ok(np.vstack((v, moved)), f, f + np.array([len(v), len(v), len(v), 0])))


class WholeModelGateTests(unittest.TestCase):
    """POLYCOUNT-CAMPS-ALDRUHN-57: an edge where two parts meet is closed in the source; a re-cut part that opens it
    passes its own part check but not the whole model's, and is put back whole."""

    def test_a_part_that_opens_a_shared_edge_is_put_back(self):
        v, f = two_parts()
        left, right = f[f[:, 3] == 0], f[f[:, 3] == 1]
        # the right part 're-cut': its triangles along the shared line x = 64 dropped (a gap to the left part)
        on_line = np.any(v[right[:, :3], 0] == 64.0, axis=1)
        cut = right[~on_line]
        out = [left, cut]
        result = meshopt._whole_model_gate(v, f, out, [(1, right)])
        s = meshopt.seam_check(v, f, result)
        self.assertEqual((s['new_open'], s['lost_open']), (0, 0), s)
        self.assertEqual(len(result), len(f))

    def test_a_passing_model_is_unchanged(self):
        v, f = two_parts()
        left, right = f[f[:, 3] == 0], f[f[:, 3] == 1]
        result = meshopt._whole_model_gate(v, f, [left, right], [(1, right)])
        self.assertTrue(np.array_equal(result, np.vstack((left, right))))


@unittest.skipUnless(meshopt.available(), 'no C++ compiler for the vendored meshoptimizer')
class SimplifiedSeamTests(unittest.TestCase):
    def test_simplified_parts_keep_every_seam(self):
        v, f = two_parts()
        rv, rf = meshopt.simplify_locked(v, f, 0.25, error_share=0.01)
        self.assertLess(len(rf), len(f))
        s = meshopt.seam_check(v, f, rf)
        self.assertEqual((s['new_open'], s['lost_open']), (0, 0), s)

    def test_neighbouring_models_still_meet(self):
        # two models side by side, simplified on their own: the line where they meet keeps every edge on both sides
        v1, f1 = grid(12, 64.0, 0, wavy)
        v2, f2 = grid(12, 64.0, 0, wavy)
        v2 = v2.copy()
        v2[:, 0] += 64.0
        v2[:, 2] = wavy(v2[:, 0], v2[:, 1])
        r1 = meshopt.simplify_locked(v1, f1, 0.2, error_share=0.02)[1]
        r2 = meshopt.simplify_locked(v2, f2, 0.2, error_share=0.02)[1]
        v = np.vstack((v1, v2))
        before = np.vstack((f1, f2 + np.array([len(v1)] * 3 + [0])))
        after = np.vstack((r1, r2 + np.array([len(v1)] * 3 + [0])))
        self.assertLess(len(after), len(before))
        s = meshopt.seam_check(v, before, after)
        self.assertEqual((s['new_open'], s['lost_open']), (0, 0), s)


class HotModelConfigTests(unittest.TestCase):
    # POLYCOUNT-CAMPS-ALDRUHN-57: the camps' and Ald'ruhn's models have stronger rows (bound picked per model from a
    # sweep, docs/chim/MESH_METHODS.md 'Stronger rows for the camps and Ald'ruhn'); every other row the default bound
    STRONGER = {'meshes/x/ex_ashl_tent_01.nif', 'meshes/x/ex_ashl_tent_02.nif',
                'meshes/x/ex_ashl_tent_04.nif', 'meshes/o/contain_tramaroot_02.nif', 'meshes/x/ex_siltstrider_01.nif',
                'meshes/x/ex_redoran_hut_01.nif', 'meshes/x/ex_redoran_hut_02.nif', 'meshes/d/ex_redoran_hut_01_a.nif',
                'meshes/x/ex_redoran_tavern_01.nif', 'meshes/x/ex_redoran_building_01.nif',
                'meshes/x/ex_redoran_building_02.nif', 'meshes/x/ex_redoran_steps_01.nif',
                'meshes/x/ex_redoran_window_02.nif', 'meshes/x/ex_redwall_corner_02.nif', 'meshes/o/contain_urn_02.nif',
                'meshes/o/contain_urn_01.nif', 'meshes/o/contain_urn_03.nif', 'meshes/o/contain_urn_05.nif',
                'meshes/x/ex_redoran_barracks_01.nif', 'meshes/x/ex_redoran_window_01.nif',
                # the second set: Ald Velothi, Bal Isra, Tel Aruhn
                'meshes/x/ex_de_shack_01.nif', 'meshes/x/ex_de_shack_04.nif',
                'meshes/x/ex_de_shack_05.nif', 'meshes/x/ex_longboat.nif', 'meshes/x/ex_longboat02.nif',
                'meshes/x/ex_de_scaffold_01.nif', 'meshes/x/ex_de_scaffold_03.nif', 'meshes/x/ex_redwall_corner_01.nif',
                'meshes/o/contain_tramaroot_01.nif', 'meshes/o/contain_tramaroot_03.nif', 'meshes/x/ex_t_menhir_l_01.nif',
                'meshes/x/ex_t_root_hook.nif', 'meshes/x/ex_t_root_02.nif', 'meshes/x/ex_t_root_03.nif',
                'meshes/x/ex_t_root_spikes_01.nif', 'meshes/x/ex_t_doorway_01.nif', 'meshes/x/ex_t_manor_01.nif',
                'meshes/x/ex_t_tunnel.nif', 'meshes/l/light_paper_lantern_01.nif',
                # the third set: the six places the v0.0.57-dev2 settlement sweep measured over 50 ms
                'meshes/x/ex_dae_ruin_02_skew.nif', 'meshes/x/ex_dae_ruin_04_skew_02.nif', 'meshes/x/ex_dae_ruin_03.nif',
                'meshes/x/ex_dae_ruin_entry.max.nif', 'meshes/x/ex_dae_pillar_03.nif', 'meshes/x/ex_holamayan_01.nif',
                'meshes/x/ex_holamayan_cover_01.nif', 'meshes/x/ex_t_rock_coastal_02.nif', 'meshes/x/ex_t_menhir_01.nif',
                'meshes/x/terrain_lava_ventlg.nif', 'meshes/x/terrain_lava_vent.nif', 'meshes/x/ex_dwrv_ruin_tower00.nif',
                'meshes/x/ex_dwrv_ruin00.nif', 'meshes/x/ex_dwrv_ruin10.nif', 'meshes/x/ex_dwrv_ruin30.nif',
                'meshes/x/ex_dwrv_ruin60.nif', 'meshes/x/ex_dwrv_ruin80.nif', 'meshes/x/ex_dwrv_steamstack00.nif',
                'meshes/x/ex_dwrv_header00.nif', 'meshes/x/ex_dwrv_enter00.nif', 'meshes/x/ex_ropebridge_2048_01.nif',
                # the fourth set: the next hot cells after the first three sets
                'meshes/x/ex_common_tower_thatch.nif', 'meshes/x/ex_common_house_tall_02.nif',
                'meshes/x/ex_nord_house_02.nif', 'meshes/x/ex_t_tower_strght_lrg.nif', 'meshes/x/ex_t_turret_01.nif',
                'meshes/x/ex_t_doorway_02.nif', 'meshes/x/ex_t_manor_02.nif', 'meshes/x/ex_t_slavemarket.nif',
                'meshes/x/ex_t_root_xl_02.nif', 'meshes/x/ex_skiff.nif', 'meshes/x/ex_longboat01.nif',
                'meshes/x/ex_de_shack_02.nif', 'meshes/x/ex_de_shack_03.nif', 'meshes/x/ex_de_shack_door.nif',
                'meshes/x/ex_de_shack_awning_06.nif', 'meshes/x/ex_hlaalu_wall_curve_01.nif'}

    def test_recipe_rows_use_their_error_bound(self):
        from visual_recipes import load_recipes
        doc = load_recipes()
        rows = {k: e for k, e in doc['recipes']['everywhere-v1']['models'].items() if 'ratio' in e}
        self.assertIn('meshes/x/ex_ashl_tent_02.nif', rows)
        self.assertLessEqual(self.STRONGER, set(rows))
        for source, entry in rows.items():
            self.assertEqual(len(entry['sha256']), 64, source)
            limit = 0.02 if source in self.STRONGER else meshopt.ERROR_SHARE
            self.assertLessEqual(entry['error_share'], limit, source)

    def test_rows_leave_hull_surface_meshes_alone(self):
        # RECIPE-ROW-MOVES-COLLISION-57: a reduction row changes what the converter's visible-tread rule sees, so a
        # mesh whose collision was measured to depend on its drawn surface under another recipe
        # (config/collision-hull-surface.json recipe_meshes) gets no everywhere row unless the table lists it for the
        # everywhere recipe too: ex_de_ship's row put its deck 64 units over its pieces and stopped the dev4 build.
        from visual_recipes import load_recipes
        doc = load_recipes()
        rows = {k for k, e in doc['recipes']['everywhere-v1']['models'].items() if 'ratio' in e}
        table = json.loads((ROOT / 'config/collision-hull-surface.json').read_text(encoding='utf-8'))
        listed = table.get('recipe_meshes', {})
        sensitive = {m for name, ms in listed.items() if name != 'everywhere-v1' for m in ms}
        allowed = set(listed.get('everywhere-v1', ()))
        self.assertEqual(sorted((rows & sensitive) - allowed), [])

    def test_manor_district_room_only(self):
        from chim.interior import room_recipe
        self.assertEqual(room_recipe('rie242a8d69e'), 'everywhere-v1')
        self.assertIsNone(room_recipe('vai000'))
        self.assertIsNone(room_recipe('rifb2f6f7131'))
        data = json.loads((ROOT / 'config/chim-rooms.json').read_text(encoding='utf-8'))
        self.assertNotIn('rie242a8d69e', data['rooms'])      # no tiles, no budget: only the recipe


if __name__ == '__main__':
    unittest.main()
