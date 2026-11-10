# SPDX-License-Identifier: GPL-3.0-only
"""Tree type 2 for the Solstheim test frames (TREES-DEPTH-56): the star prism (route D, tools/chim_tree_star.py),
the baked copies' outline (tools/chim_tree_copies.py), the opt-in stage wiring and that no base stage reads any of it."""
import argparse
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import numpy as np  # noqa: E402

import build  # noqa: E402
import build_cache  # noqa: E402
import chim_tree_copies  # noqa: E402
import chim_tree_star  # noqa: E402

SETTINGS = {'tiers': 3, 'point_depth': 0.45, 'crown_bottom_share': 0.15, 'tier_overlap': 0.3,
            'trunk_half_width_share': 0.06, 'inner_shade': 0.3, 'texture_units': 128}


def cone(height=400.0, radius=120.0, sides=24):
    """A spruce-like source: a cone of needles (material 0, textured) on a thin trunk (material 1, textured)."""
    v = [[0, 0, height, 0, 0, 255, 255, 255, 255]]
    for k in range(sides):
        a = 2 * math.pi * k / sides
        v.append([radius * math.cos(a), radius * math.sin(a), 60, 0, 0, 255, 255, 255, 255])
    f = [[0, 1 + k, 1 + (k + 1) % sides, 0] for k in range(sides)]
    base = len(v)
    v += [[-8, -8, 0, 0, 0, 255, 255, 255, 255], [8, -8, 0, 0, 0, 255, 255, 255, 255], [8, 8, 60, 0, 0, 255, 255, 255, 255]]
    f.append([base, base + 1, base + 2, 1])
    return np.array(v, float), np.array(f, int), [{'texture_index': 0}, {'texture_index': 1}]


class StarPrism(unittest.TestCase):
    def test_counts_and_settings(self):
        v, f, mats = cone()
        sv, sf, rep = chim_tree_star.star_prism(v, f, mats, SETTINGS)
        # per tier 8 side faces (two triangles each, the top tier closes on one point: one each), a hexagonal trunk
        # of 6 sides (two triangles each, no caps); undersides (8 triangles per tier) only when asked
        self.assertEqual(rep['triangles'], 2 * 16 + 8 + 12)
        self.assertEqual(rep['trunk']['sides'], 6)
        self.assertEqual(len(sf), rep['triangles'])
        two = chim_tree_star.star_prism(v, f, mats, dict(SETTINGS, tiers=2))[2]['triangles']
        self.assertEqual(two, 16 + 8 + 12)
        under = chim_tree_star.star_prism(v, f, mats, dict(SETTINGS, undersides=True))[2]['triangles']
        self.assertEqual(under, 2 * 16 + 8 + 3 * 8 + 12)

    def test_the_crown_starts_at_the_lowest_needle_and_the_trunk_follows_the_bark(self):
        v, f, mats = cone()
        sv, sf, rep = chim_tree_star.star_prism(v, f, mats, SETTINGS)
        self.assertEqual(rep['crown_bottom'], 60.0)               # the cone's lowest needle vertex
        self.assertEqual(rep['bark_material'], 1)
        needles = sv[np.unique(sf[sf[:, 3] == 0, :3]), 2]
        self.assertGreaterEqual(needles.min(), 60.0 - 1e-6)
        bark = sv[np.unique(sf[sf[:, 3] == 1, :3])]
        self.assertAlmostEqual(bark[:, 2].min(), 0.0)              # the trunk stands on the model's foot
        r = np.hypot(bark[:, 0], bark[:, 1])                      # the cone stands on the origin
        self.assertTrue(np.all(r < 20))                           # bark-sized, not crown-sized
        self.assertEqual(rep['material'], 0)                        # the needles: the larger textured area
        self.assertTrue(set(sf[:, 3].tolist()) <= {0, 1})           # only the model's own materials

    def test_faces_point_outward_and_stay_inside_the_model(self):
        v, f, mats = cone()
        sv, sf, _ = chim_tree_star.star_prism(v, f, mats, dict(SETTINGS, trunk_sides=0, undersides=True))
        lo, hi = v[:, :3].min(0), v[:, :3].max(0)
        self.assertTrue(np.all(sv[:, :3] >= lo - 1e-6) and np.all(sv[:, :3] <= hi + 1e-6))
        for a, b, c, _ in sf:
            p = sv[[a, b, c], :3]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            if np.linalg.norm(n) < 1e-9:
                continue
            mid = p.mean(0)
            if abs(n[2]) > 0.99 * np.linalg.norm(n):               # an underside: faces down
                self.assertLess(n[2], 0)
            else:                                                   # a side: faces away from the trunk
                self.assertGreater(n[0] * mid[0] + n[1] * mid[1], 0)

    def test_star_has_four_points(self):
        ring = chim_tree_star.star_ring(0, 0, 0, 10, 5.5)
        radii = [round(math.hypot(x, y), 6) for x, y, _ in ring]
        self.assertEqual(radii, [10, 5.5] * 4)

    def test_config_refusals(self):
        settings, patterns = chim_tree_star.load_star()
        self.assertIn(settings['tiers'], (2, 3, 4))
        self.assertTrue(chim_tree_star.is_star_model('meshes\\f\\Flora_Tree_BM_01.NIF', patterns))
        self.assertFalse(chim_tree_star.is_star_model('meshes/f/flora_tree_ac_01.nif', patterns))   # Vvardenfell
        angles, _, points = chim_tree_copies.load_config()
        self.assertEqual(angles, [0, 45, 90, 135])
        self.assertTrue(3 <= points <= 64)


class Outline(unittest.TestCase):
    def test_silhouette_of_a_triangle_mask(self):
        mask = np.zeros((40, 41), bool)
        for y in range(40):
            mask[y, 20 - y // 2:21 + y // 2] = True
        out = chim_tree_copies.silhouette(mask, 8)
        self.assertLessEqual(out['corners'], 8)
        self.assertEqual(out['triangles_per_side'], out['corners'] - 2)
        self.assertGreater(out['covered_share'], 0.85)
        self.assertLessEqual(out['covered_share'], 1.2)


class Wiring(unittest.TestCase):
    def steps_for(self, copies):
        args = argparse.Namespace(chim_sol_test='-23,20:l', chim_sol_tree_copies=copies, data_files=Path('/d'),
                                  workspace=Path('/w'), sdk=Path('/sdk'))
        tool = lambda script, *rest: [script, *map(str, rest)]  # noqa: E731
        base = [('chim', ['chim_build.py', '--out', 'run/chim']), ('image', ['build_aga.py'])]
        from unittest.mock import patch
        with patch.object(build, 'chim_stage_options', lambda a: []):
            return build.chim_sol_test_commands(args, list(base), tool, Path('run'), {'qbsp': 'qbsp'}, 8), base

    def test_off_is_the_old_path_and_base_steps_are_untouched(self):
        off, base = self.steps_for('off')
        star, _ = self.steps_for('star')
        self.assertEqual(off[0], base[0])
        self.assertEqual(star[0], base[0])                          # the base chim stage: the same command
        self.assertEqual([n for n, _ in off], ['chim', 'chim-sol-data', 'chim-sol', 'image'])
        self.assertEqual([n for n, _ in star], ['chim', 'chim-sol-data', 'chim-sol-trees', 'chim-sol', 'image'])
        self.assertEqual(dict(off)['chim-sol'][0], 'chim_build.py')
        self.assertEqual(dict(star)['chim-sol'][:2], ['chim_tree_star.py', '--tree-star'])
        self.assertEqual(dict(star)['chim-sol'][3:], dict(off)['chim-sol'][1:])   # the same chim_build arguments

    def test_the_tree_stage_reads_bloodmoon_and_no_base_stage_reads_the_tree_tools(self):
        self.assertEqual(set(build_cache.STAGE_GAME_INPUTS['chim-sol-trees']),
                         {'morrowind.esm', 'morrowind.bsa', 'bloodmoon.esm', 'bloodmoon.bsa'})
        self.assertEqual(build_cache.stage_layers_left_out('chim'), {'bloodmoon', 'tribunal'})
        index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        selected, _ = index.selection((ROOT / 'tools/chim_build.py').resolve())
        names = {Path(str(k)).as_posix() for k in selected}
        for own in ('tools/chim_tree_star.py', 'tools/chim_tree_copies.py', 'tools/tree_star_site/sitecustomize.py',
                    'config/tree-copies.json'):
            self.assertFalse(any(n.endswith(own) for n in names), own)


if __name__ == '__main__':
    unittest.main()
