# SPDX-License-Identifier: GPL-3.0-only
"""The rally-game trees for the Solstheim test frames (SOLSTHEIM-TREES-THREE-LOD-68, tools/chim_tree_rally.py): the
trunk in polygons and the crown as see-through picture planes rendered from the original; the atlas as a see-through
texture; several alternative methods in one store (tools/chim/alt_models.py merge_many); the opt-in stage wiring,
and that no base stage reads any of it."""
import argparse
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import numpy as np  # noqa: E402

import build  # noqa: E402
import build_cache  # noqa: E402
import build_parallel  # noqa: E402
import chim_tree_rally as R  # noqa: E402

SETTINGS = {'planes': 4, 'first_angle_degrees': 0, 'pane_texture': 'silhouette', 'trunk': 'original',
            'trunk_sides': 6, 'texels_per_unit': 1.0, 'supersample': 2, 'coverage': 0.34, 'outline_corners': 8}


def spruce(height=400.0, radius=120.0, sides=16):
    """A spruce-like source: a cone of needles (material 0, a texture half see-through) on a trunk prism of 6 sides
    (material 1, an opaque bark texture); vertex rows x y z u v r g b a."""
    v = [[0, 0, height, 0.5, 0, 255, 255, 255, 255]]
    for k in range(sides):
        a = 2 * math.pi * k / sides
        v.append([radius * math.cos(a), radius * math.sin(a), 60, k / sides * 4, 4, 255, 255, 255, 255])
    f = [[0, 1 + k, 1 + (k + 1) % sides, 0] for k in range(sides)]
    base = len(v)
    for k in range(6):
        a = 2 * math.pi * k / 6
        v.append([10 * math.cos(a), 10 * math.sin(a), 0, k / 6, 0, 255, 255, 255, 255])
        v.append([4 * math.cos(a), 4 * math.sin(a), 300, k / 6, 3, 255, 255, 255, 255])
    for k in range(6):
        j = (k + 1) % 6
        a0, a1, b0, b1 = base + 2 * k, base + 2 * j, base + 2 * k + 1, base + 2 * j + 1
        f += [[a0, a1, b1, 1], [a0, b1, b0, 1]]
    needles = np.zeros((16, 16, 4), np.uint8)
    needles[:, :, 1] = 120
    needles[:, :, 3] = 255
    needles[::2, :, 3] = 0                                    # half the texels see-through
    bark = np.full((16, 16, 4), 90, np.uint8)
    bark[:, :, 3] = 255
    mats = [{'texture_index': 0, 'diffuse': [1, 1, 1], 'alpha': 1}, {'texture_index': 1, 'diffuse': [1, 1, 1], 'alpha': 1}]
    return np.array(v, float), np.array(f, int), mats, {0: needles, 1: bark}


class RallyTree(unittest.TestCase):
    def test_parts(self):
        v, f, mats, tex = spruce()
        parts = R.tree_parts(v, f, mats, tex)
        self.assertEqual((parts['crown'], parts['bark'], parts['trunk']), ([0], 1, [1]))
        self.assertAlmostEqual(parts['centre'][0], 0, places=6)

    def test_planes_outline_and_both_sides(self):
        v, f, mats, tex = spruce()
        rv, rf, atlas, rep = R.rally_tree(v, f, mats, tex, SETTINGS, 64)
        self.assertEqual(rep['planes'], 4)
        self.assertEqual(rep['angles'], [0, 45, 90, 135])
        self.assertTrue(all(3 <= c <= SETTINGS['outline_corners'] + 4 for c in rep['pane_corners']))
        # each pane a fan of corners - 2 triangles, front and mirrored back
        self.assertEqual(rep['pane_triangles'], 2 * sum(c - 2 for c in rep['pane_corners']))
        self.assertEqual(rep['trunk']['triangles'], 12)              # the bark triangles as the model has them
        self.assertEqual(len(rf), rep['pane_triangles'] + 12)
        self.assertTrue(set(rf[:, 3].tolist()) <= {0, 1})          # only the model's own materials
        self.assertEqual(rep['pane_material'], 0)
        self.assertEqual(atlas.shape[2], 4)
        self.assertEqual((atlas.shape[0] % 16, atlas.shape[1] % 16), (0, 0))
        self.assertTrue((atlas[:, :, 3] == 255).any() and (atlas[:, :, 3] == 0).any())
        # every pane triangle stands in its plane, on the front or back side of it
        panes = rf[rf[:, 3] == 0]
        fronts = 0
        for a, b, c, _ in panes:
            p = rv[[a, b, c], :3]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            n /= np.linalg.norm(n)
            self.assertAlmostEqual(abs(n[2]), 0, places=6)             # vertical planes
            # a plane at angle d lies along (cos d, -sin d); its front looks along -(sin d, cos d)
            d = round(math.degrees(math.atan2(-n[0], -n[1]))) % 360
            self.assertIn(d % 180, rep['angles'])
            fronts += d < 180
        self.assertEqual(fronts, len(panes) // 2)                       # half front, half the mirrored back
        # pane texture coordinates fall inside the atlas (texels = uv x texture size)
        uv = rv[np.unique(panes[:, :3]), 3:5] * 64
        self.assertTrue(np.all(uv[:, 0] >= -1e-6) and np.all(uv[:, 0] <= atlas.shape[1] + 1e-6))
        self.assertTrue(np.all(uv[:, 1] >= -1e-6) and np.all(uv[:, 1] <= atlas.shape[0] + 1e-6))
        # the crown stays within the model's own reach (and one picture texel: 4 source units at 1 texel a map unit)
        lo, hi = v[:, :3].min(0), v[:, :3].max(0)
        self.assertTrue(np.all(rv[:, :3] >= lo - 4.01) and np.all(rv[:, :3] <= hi + 4.01))

    def test_pane_faces_cover_their_solid_texels(self):
        """Every solid texel of a pane's picture lies inside that pane's face (the outline only grows)."""
        v, f, mats, tex = spruce()
        rv, rf, atlas, rep = R.rally_tree(v, f, mats, tex, SETTINGS, 64)
        panes = rf[rf[:, 3] == 0]
        ys, xs = np.nonzero(atlas[:, :, 3] == 255)
        centres = np.column_stack((xs + .5, ys + .5))
        inside = np.zeros(len(centres), bool)
        for a, b, c, _ in panes:
            t = rv[[a, b, c], 3:5] * 64
            d = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
            if abs(d) < 1e-9:
                continue
            w0 = ((t[1, 1] - t[2, 1]) * (centres[:, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (centres[:, 1] - t[2, 1])) / d
            w1 = ((t[2, 1] - t[0, 1]) * (centres[:, 0] - t[2, 0]) + (t[0, 0] - t[2, 0]) * (centres[:, 1] - t[2, 1])) / d
            inside |= (w0 >= -1e-6) & (w1 >= -1e-6) & (1 - w0 - w1 >= -1e-6)
        self.assertTrue(inside.all())

    def test_slice_shows_each_needle_once_and_prism_trunk(self):
        v, f, mats, tex = spruce()
        _, _, _, rep = R.rally_tree(v, f, mats, tex, dict(SETTINGS, pane_texture='slice', trunk='prism'), 64)
        self.assertEqual(sum(rep['triangles_shown']), int((f[:, 3] == 0).sum()))
        self.assertEqual(rep['trunk']['kind'], 'prism')
        self.assertEqual(rep['trunk']['triangles'], 12)              # 6 sides, two triangles each, no caps
        self.assertLessEqual(rep['trunk']['radius_top'], rep['trunk']['radius_bottom'])
        silhouette = R.rally_tree(v, f, mats, tex, SETTINGS, 64)[3]
        self.assertEqual(silhouette['triangles_shown'], [int((f[:, 3] == 0).sum())] * 4)

    def test_slice_owner(self):
        xy = np.array([[1, 0], [-1, 0], [0, 1], [0, -1], [1, -1], [-1, 1]], float)
        # planes at 0 (along x) and 90 (along y); the diagonal goes to the plane at 45 when there is one
        self.assertEqual(R.slice_owner(xy, [0, 90]).tolist()[:4], [0, 0, 1, 1])
        self.assertEqual(R.slice_owner(xy, [0, 45, 90, 135]).tolist()[4:], [1, 1])

    def test_covering_polygon_holds_the_points(self):
        rng = np.random.default_rng(7)
        pts = rng.normal(size=(300, 2)) * (40, 90)
        poly = R.covering_polygon(pts, 6)
        self.assertLessEqual(len(poly), 6)
        q = np.array(poly)
        for i in range(len(q)):
            a, b = q[i], q[(i + 1) % len(q)]
            cross = (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0])
            self.assertTrue(np.all(cross >= -1e-6))                   # every point on the inner side
        clipped = R.clip_to_rect(poly, -50, -100, 50, 100)
        self.assertTrue(all(-50 - 1e-9 <= x <= 50 + 1e-9 and -100 - 1e-9 <= y <= 100 + 1e-9 for x, y in clipped))

    def test_atlas_texture_is_see_through(self):
        rgba = np.zeros((16, 32, 4), np.uint8)
        rgba[:, :16, 1] = 200
        rgba[:, :16, 3] = 255
        palette = bytes(range(256)) * 3
        task = {'kind': 'flatten', 'flat_rgb': rgba, 'palette': palette, 'glow': 0}
        self.assertTrue(R.is_rally_atlas(task))
        out = R.pane_texture_unit(task)
        self.assertEqual(out['kind'], 'fence')
        mip = out['miptex']
        self.assertEqual(mip[:1], b'{')
        w, h, o0 = struct.unpack_from('<3I', mip, 16)
        pix = np.frombuffer(mip[o0:o0 + w * h], np.uint8).reshape(h, w)
        self.assertTrue(np.all(pix[:, 16:] == 255))
        self.assertTrue(np.all(pix[:, :16] != 255))
        self.assertFalse(R.is_rally_atlas(dict(task, flat_rgb=rgba[:, :, :3])))
        self.assertFalse(R.is_rally_atlas(dict(task, kind='surface')))

    def test_config_and_methods(self):
        settings, patterns = R.load_rally()
        self.assertIn(settings['pane_texture'], R.PANE_TEXTURES)
        self.assertIn(settings['trunk'], R.TRUNKS)
        self.assertTrue(R.is_rally_model('meshes\\f\\Flora_Tree_BM_01.NIF', patterns))
        self.assertFalse(R.is_rally_model('meshes/f/flora_tree_ac_01.nif', patterns))
        self.assertEqual(R.load_rally(pane_texture='slice', trunk='prism')[0]['trunk'], 'prism')
        methods = R.rally_methods()
        self.assertEqual([m[0] for m in methods], [2, 3, 4, 5])
        self.assertEqual({(p, t) for _, p, t in methods},
                         {(p, t) for p in R.PANE_TEXTURES for t in R.TRUNKS})
        self.assertEqual(R.take_args(['--tree-rally', 'c.json', '--trunk', 'prism', '--pane-texture', 'slice', '--x']),
                         ('c.json', 'slice', 'prism', ['--x']))
        with self.assertRaises(SystemExit):
            R.take_args(['--tree-rally', 'c.json', '--trunk', 'oak'])


class PlacedSeeThrough(unittest.TestCase):
    """FENCE-PLACED-ORIGIN-68: the see-through pass clips and projects a placed model's face from the world origin
    unless aw_seethrough_placed is 1; the panes need 1, the default stays 0 until the maintainer has seen it."""

    def test_the_entity_origin_goes_into_modelorg_before_the_rotation(self):
        src = (ROOT / 'engine/aga/src/d_fence.c').read_text(encoding='utf-8')
        self.assertIn('cvar_t\taw_seethrough_placed = {"aw_seethrough_placed", "0"};', src)
        self.assertIn('Cvar_RegisterVariable (&aw_seethrough_placed);', src)
        branch = src[src.index('if (f->ent != &cl_entities[0])'):]
        branch = branch[:branch.index('FenceDrawFace (f);')]
        self.assertLess(branch.index('VectorSubtract (r_origin, f->ent->origin, local);'),
                        branch.index('VectorCopy (local, modelorg);'))
        self.assertLess(branch.index('if (aw_seethrough_placed.value)'), branch.index('VectorCopy (local, modelorg);'))
        self.assertLess(branch.index('VectorCopy (local, modelorg);'), branch.index('R_RotateBmodel ();'))

    def test_the_setting_is_in_the_console_catalogue(self):
        lines = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8').splitlines()
        self.assertTrue(any(line.startswith('VIDEO|seethroughplaced|aw_seethrough_placed|') for line in lines))


class AltMethods(unittest.TestCase):
    def test_merge_many_keeps_methods_apart(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('_alt_store_helpers', ROOT / 'tests' / 'test_chim_alt_models.py')
        helpers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helpers)
        base_and_alt, store = helpers.base_and_alt, helpers.store
        from chim import alt_models as A
        from chim import format as F
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            base, alt = base_and_alt(d, b'TEXC' * 4 + b'TEXD' * 4)
            alt2 = store(d / 'alt2', struct.pack('<3f', 0, 0, 70), [1, 0], b'TEXE' * 4 + b'TEXF' * 4)
            one = A.merge(base, alt, d / 'one', 2)
            records = A.merge_many(base, [(2, alt), (3, alt2)], d / 'out')
            self.assertEqual(records[0], one)
            _, files, models, textures = F.read_index((d / 'out' / 'world.cwi').read_bytes())
            paths = [f['path'] for f in files]
            self.assertIn('frames/x+1977/y+20/s00.ccs', paths)
            self.assertIn('frames/x+2977/y+20/s00.ccs', paths)
            self.assertEqual([m['name'] for m in models], ['rock', 'tree', 'tree#alt2', 'tree#alt3'])
            self.assertEqual(A.read_alt_map((d / 'out' / A.ALT_FILE).read_bytes()), {2: [(1, 2)], 3: [(1, 3)]})
            # the first method's sector file is the single merge's, byte for byte
            self.assertEqual((d / 'out/frames/x+1977/y+20/s00.ccs').read_bytes(),
                             (d / 'one/frames/x+1977/y+20/s00.ccs').read_bytes())
            with self.assertRaises(ValueError):
                A.merge_many(base, [(2, alt), (2, alt2)], d / 'again')


class Wiring(unittest.TestCase):
    def steps_for(self, copies):
        args = argparse.Namespace(chim_sol_test='-23,20:l', chim_sol_tree_copies=copies, data_files=Path('/d'),
                                  workspace=Path('/w'), sdk=Path('/sdk'))
        tool = lambda script, *rest: [script, *map(str, rest)]  # noqa: E731
        base = [('chim', ['chim_build.py', '--out', 'run/chim']), ('image', ['build_aga.py'])]
        from unittest.mock import patch
        # the Solstheim test image is a -devN option (project_version.require_private_test_version refuses it on an rc
        # or final VERSION): the wiring is checked under a dev version, so the test holds on a release line too
        with patch.object(build, 'chim_stage_options', lambda a: []), patch.object(build, 'VERSION', '0.0.0-dev1'):
            return build.chim_sol_test_commands(args, list(base), tool, Path('run'), {'qbsp': 'qbsp'}, 8), base

    def test_rally_switch_builds_every_method_before_the_original(self):
        steps, base = self.steps_for('rally-switch')
        off, _ = self.steps_for('off')
        self.assertEqual(steps[0], base[0])                          # the base chim stage: the same command
        names = [n for n, _ in steps]
        self.assertEqual(names, ['chim', 'chim-sol-data', 'chim-sol-alt2', 'chim-sol-alt3', 'chim-sol-alt4',
                                 'chim-sol-alt5', 'chim-sol', 'image'])
        cmds = dict(steps)
        self.assertEqual(cmds['chim-sol'], dict(off)['chim-sol'])       # the original trees: the runner, as before
        alt3 = cmds['chim-sol-alt3']
        self.assertEqual(alt3[:2], ['chim_tree_rally.py', '--tree-rally'])
        self.assertEqual(alt3[3:7], ['--pane-texture', 'slice', '--trunk', 'original'])
        runner = [x if x != 'run/chim-sol' else 'run/chim-sol-alt3' for x in dict(off)['chim-sol'][1:]]
        self.assertEqual(alt3[7:], runner)                              # the runner's own arguments after them
        image = cmds['image']
        alts = [image[i + 1] for i, x in enumerate(image) if x == '--chim-sol-alt']
        self.assertEqual(alts, ['%d=run/chim-sol-alt%d' % (n, n) for n in (2, 3, 4, 5)])
        for n in (2, 3, 4, 5):
            self.assertEqual(set(build_cache.STAGE_GAME_INPUTS['chim-sol-alt%d' % n]),
                             {'morrowind.esm', 'morrowind.bsa', 'bloodmoon.esm', 'bloodmoon.bsa'})

    def test_the_image_waits_for_every_method(self):
        """The rally stages have no rule of their own in the scheduler: each waits for the stage before it, and
        chim-sol (which the image waits for) comes after them."""
        from unittest.mock import patch
        steps, _ = self.steps_for('rally-switch')
        self.assertFalse({'chim-sol', *('chim-sol-alt%d' % n for n in range(2, 16))} & set(build_parallel.DEPENDENCIES))
        steps = [('census', ['census.py'])] + steps
        with patch.object(build_parallel, 'DEPENDENCIES', {'chim': ('census',), 'image': ('chim',)}):
            deps = build_parallel.stage_dependencies(steps)

        def before(name, seen=None):
            seen = set() if seen is None else seen
            for d in deps.get(name, ()):
                if d not in seen:
                    seen.add(d)
                    before(d, seen)
            return seen
        self.assertTrue({'chim-sol-alt%d' % n for n in (2, 3, 4, 5)} <= before('image'))

    def test_rally_alone_and_refusals(self):
        steps, _ = self.steps_for('rally')
        self.assertEqual([n for n, _ in steps], ['chim', 'chim-sol-data', 'chim-sol', 'image'])
        self.assertEqual(dict(steps)['chim-sol'][:2], ['chim_tree_rally.py', '--tree-rally'])
        self.assertNotIn('--chim-sol-alt', dict(steps)['image'])
        star, _ = self.steps_for('switch')                            # the star switch: as before
        self.assertEqual([n for n, _ in star], ['chim', 'chim-sol-data', 'chim-sol-trees', 'chim-sol', 'chim-sol-star',
                                                'image'])
        args = argparse.Namespace(chim_sol_test='-23,20:l', chim_sol_tree_copies='rally-switch', data_files=Path('/d'),
                                  workspace=Path('/w'), sdk=Path('/sdk'), chim_mesh_method_set='E')
        from unittest.mock import patch
        with self.assertRaises(SystemExit), patch.object(build, 'VERSION', '0.0.0-dev1'):   # a -devN option (above)
            build.chim_sol_test_commands(args, [('chim', []), ('image', [])], lambda *a: list(a), Path('run'), {}, 8)

    def test_no_base_stage_reads_the_rally_tools(self):
        index = build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)
        selected, _ = index.selection((ROOT / 'tools/chim_build.py').resolve())
        names = {Path(str(k)).as_posix() for k in selected}
        for own in ('tools/chim_tree_rally.py', 'tools/tree_rally_site/sitecustomize.py'):
            self.assertFalse(any(n.endswith(own) for n in names), own)


if __name__ == '__main__':
    unittest.main()
