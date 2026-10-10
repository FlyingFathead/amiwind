# SPDX-License-Identifier: GPL-3.0-only
"""Near/far NPC models (tools/npc_lod.py, engine aw_npc_lod.c; docs/NPC_MODEL_CACHE.md)."""
import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

import numpy as np  # noqa: E402

import npc_lod  # noqa: E402
from npc_geometry import animated_mdl  # noqa: E402


def model(frames=8, faces=12, seed=0, names=None):
    """A small IDPO model in the bakers' format (animated_mdl)."""
    from PIL import Image
    rng = np.random.default_rng(seed)
    verts = faces * 3
    xyz = rng.random((frames, verts, 3)) * 10
    tris = np.arange(verts).reshape(faces, 3)
    uv = np.array([(i % 32 * 4, i // 32 * 4) for i in range(verts)], float)
    skin = Image.new('P', (128, 64))
    raw = bytearray(animated_mdl(xyz, tris, uv, skin))
    if names:
        # Rename frame i in place (the bakers write idle00, idle01, ...).
        at = 84 + 4 + 128 * 64 + verts * 12 + faces * 16
        for i, name in enumerate(names):
            start = at + i * (28 + verts * 4) + 12
            raw[start:start + 16] = name.encode().ljust(16, b'\0')
    return bytes(raw)


class FrameListIdentity(unittest.TestCase):
    def test_every_level_against_the_map_model(self):
        raws = {0: model(faces=40, seed=1), 1: model(), 2: model(faces=6, seed=2), 3: model(faces=3, seed=3)}
        self.assertEqual(npc_lod.levels_check(raws), ['idle%02d' % i for i in range(8)])
        raws[3] = model(frames=8, faces=3, names=['idle00', 'idle02'])
        with self.assertRaises(ValueError):
            npc_lod.levels_check(raws)

    def test_frame_names_read_in_order(self):
        self.assertEqual(npc_lod.frame_names(model(frames=3)), ['idle00', 'idle01', 'idle02'])

    def test_pair_with_same_frames_passes_whatever_the_triangles(self):
        far, near = model(faces=12), model(faces=40, seed=1)
        self.assertEqual(npc_lod.pair_check(far, near), ['idle%02d' % i for i in range(8)])
        self.assertLess(npc_lod.model_counts(far)['triangles'], npc_lod.model_counts(near)['triangles'])

    def test_frame_count_order_or_name_difference_is_refused(self):
        far = model()
        for near in (model(frames=7), model(names=['idle01', 'idle00']), model(names=['idle00', 'walk01'])):
            with self.assertRaises(ValueError):
                npc_lod.pair_check(far, near)

    def test_truncated_model_is_refused(self):
        with self.assertRaises(ValueError):
            npc_lod.frame_names(model()[:-4])


class LevelTable(unittest.TestCase):
    rows = [{'far': 'progs/a_bbbbbbbbbbbb.mdl', 'use': False, 'bytes': [9000, 7000, 3000, 0]},
            {'far': 'progs/a_aaaaaaaaaaaa.mdl', 'use': True, 'bytes': [8000, 6000, 2500, 1500]}]

    def test_text_is_sorted_and_round_trips(self):
        text = npc_lod.manifest_text(self.rows, (0, 1, 2, 3))
        self.assertEqual(text.splitlines()[0], 'AWNL2 2 0123')
        self.assertEqual(text.splitlines()[1], 'progs/a_aaaaaaaaaaaa.mdl 1 8000 6000 2500 1500')
        rows, levels = npc_lod.parse_manifest(text)
        self.assertEqual(levels, (0, 1, 2, 3))
        self.assertEqual(sorted(rows, key=lambda r: r['far']), sorted(self.rows, key=lambda r: r['far']))
        self.assertNotIn(chr(13), text)

    def test_paths_follow_ffs_and_engine_bounds(self):
        bad = [{'far': 'progs/' + 'x' * 31 + '.mdl', 'use': True, 'bytes': [1, 1, 0, 0]},
               {'far': 'progs/a b.mdl', 'use': True, 'bytes': [1, 1, 0, 0]},
               {'far': 'maps/a.mdl', 'use': True, 'bytes': [1, 1, 0, 0]},
               {'far': 'progs/x/a.mdl', 'use': True, 'bytes': [1, 1, 0, 0]},
               {'far': 'progs/a.mdl', 'use': True, 'bytes': [1, 0, 0, 0]},
               {'far': 'progs/a.mdl', 'use': True, 'bytes': [1, 1, 1, 0]}]   # level 2 not in a 2-level build
        for row in bad:
            with self.assertRaises(ValueError):
                npc_lod.manifest_text([row], (0, 1))
        with self.assertRaises(ValueError):
            npc_lod.manifest_text([self.rows[0], self.rows[0]], (0, 1, 2, 3))

    def test_level_paths(self):
        far = npc_lod.far_path('fargoth')
        self.assertEqual(far, 'progs/' + npc_lod.stem('fargoth') + '.mdl')
        self.assertEqual(npc_lod.level_path(far, 1), far)
        for level in (0, 2, 3):
            path = npc_lod.level_path(far, level)
            self.assertEqual(path, 'progs/l%d/' % level + npc_lod.stem('fargoth') + '.mdl')
            self.assertTrue(all(len(part) <= 30 for part in path.split('/')))
        self.assertEqual(npc_lod.LEVEL_SETS, {2: (0, 1), 3: (0, 1, 2), 4: (0, 1, 2, 3)})

    def test_merge_and_check_a_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            rows = []
            for name, use in (('fargoth', True), ('guard', False)):
                raws = {0: model(faces=30, seed=2), 1: model(), 2: model(faces=6, seed=3)}
                (id1 / npc_lod.far_path(name)).write_bytes(raws[1])
                rows.append(npc_lod.write_levels(id1, npc_lod.far_path(name), raws, use))
            npc_lod.merge_manifest(id1, rows[:1], (0, 1, 2))
            self.assertEqual(npc_lod.merge_manifest(id1, rows[1:], (0, 1, 2)), 2)
            with self.assertRaises(ValueError):
                npc_lod.merge_manifest(id1, rows[1:], (0, 1))      # one table, one level set
            report = npc_lod.check(id1)
            self.assertEqual((report['rows'], report['flagged'], report['levels']), (2, 1, [0, 1, 2]))
            self.assertEqual(report['level_bytes'][0], 2 * len(model(faces=30, seed=2)))
            path = id1 / npc_lod.level_path(npc_lod.far_path('guard'), 2)
            path.write_bytes(model(frames=7, faces=6))
            with self.assertRaises(ValueError):
                npc_lod.check(id1)

    def test_engine_parser_bounds_match(self):
        header = (ROOT / 'engine/aga/src/aw_npc_lod.h').read_text(encoding='utf-8')
        source = (ROOT / 'engine/aga/src/aw_npc_lod.c').read_text(encoding='utf-8')
        self.assertIn('#define AW_NPC_LOD_PATH 64', header)
        self.assertIn('#define AW_NPC_LOD_LEVELS %d' % npc_lod.LEVEL_COUNT, header)
        self.assertIn('#define AW_NPC_LOD_MAP_LEVEL %d' % npc_lod.MAP_LEVEL, header)
        self.assertEqual(npc_lod.PATH_CHARS, 63)
        self.assertIn('"%s"' % npc_lod.MANIFEST, header)
        self.assertIn('"%s ' % npc_lod.MAGIC, source)
        self.assertIn('"progs/l%d/%s"', source)
        self.assertEqual({npc_lod.LEVEL_SPECS[k]['dir'] for k in (0, 2, 3)}, {'progs/l0', 'progs/l2', 'progs/l3'})


class Retile(unittest.TestCase):
    def test_tiles_shrink_uvs_follow(self):
        from PIL import Image
        faces = 40
        tris = np.arange(faces * 3).reshape(faces, 3)
        uv = np.array([(f % 32 * 16 + dx, f // 32 * 16 + dy) for f in range(faces)
                       for dx, dy in ((0, 0), (15, 0), (0, 15))], float)
        skin = Image.new('P', (512, 32))
        palette = bytes(range(256)) * 3
        new_uv, new_skin = npc_lod.retile(tris, uv, skin, palette, [16] * 10 + [8] * 30)
        self.assertEqual(new_skin.size[0], 512)
        self.assertLessEqual(new_skin.size[1], 32)
        self.assertEqual(new_skin.size[1] % 4, 0)
        for f in range(faces):
            (x0, y0), (x1, _), (_, y2) = new_uv[f * 3:f * 3 + 3]
            self.assertEqual(x1 - x0 + 1, 16 if f < 10 else 8)
            self.assertEqual(y2 - y0 + 1, 16 if f < 10 else 8)
        same_uv, same_skin = npc_lod.retile(tris, uv, skin, palette, [16] * faces)
        self.assertIs(same_skin, skin)
        with self.assertRaises(ValueError):
            npc_lod.retile(tris, uv, skin, palette, [17] * faces)


class Policy(unittest.TestCase):
    def test_policies(self):
        metric = {'hausdorff': npc_lod.MEASURED_THRESHOLD}
        self.assertTrue(npc_lod.uses_near('all', 'x', None))
        self.assertTrue(npc_lod.uses_near('measured', 'x', metric))
        self.assertFalse(npc_lod.uses_near('measured', 'x', {'hausdorff': npc_lod.MEASURED_THRESHOLD - 0.01}))
        self.assertFalse(npc_lod.uses_near('measured', 'x', None))
        self.assertTrue(npc_lod.uses_near('named', 'fargoth', None, named={'fargoth'}))
        self.assertFalse(npc_lod.uses_near('named', 'guard', None, named={'fargoth'}))
        self.assertTrue(npc_lod.uses_near('list', 'guard', None, listed={'guard'}))
        with self.assertRaises(ValueError):
            npc_lod.uses_near('some', 'x', None)

    def test_named_means_a_display_name_no_other_record_has(self):
        def npc(name):
            return [('FNAM', name.encode() + b'\0')]
        kinds = {'NPC_': {'fargoth': npc('Fargoth'), 'g1': npc('Guard'), 'g2': npc('Guard')}}
        self.assertEqual(npc_lod.named_records(kinds), {'fargoth'})

    def test_list_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'faces.txt'
            path.write_text('# unique faces\nFargoth\n\ncaius cosades  # the spymaster\n', encoding='utf-8')
            self.assertEqual(npc_lod.read_list(path), {'fargoth', 'caius cosades'})


class DiskFit(unittest.TestCase):
    def test_coarse_levels_first_then_near_by_head_error(self):
        candidates = [('a', {0: 300, 2: 60, 3: 30}, 0.2), ('b', {0: 300, 2: 60}, 0.9), ('c', {2: 60, 3: 30}, 0.5)]
        chosen, dropped = npc_lod.fit_disk(candidates, 10 ** 6)
        self.assertEqual(chosen, {'a': {0, 1, 2, 3}, 'b': {0, 1, 2}, 'c': {1, 2, 3}})
        self.assertEqual(dropped, 0)
        chosen, dropped = npc_lod.fit_disk(candidates, 30 + 30 + 60 * 3 + 300)
        self.assertEqual(chosen, {'a': {1, 2, 3}, 'b': {0, 1, 2}, 'c': {1, 2, 3}})
        self.assertEqual(dropped, 1)
        chosen, dropped = npc_lod.fit_disk(candidates, 100, used=50)
        self.assertEqual(chosen, {'a': {1, 3}, 'b': {1}, 'c': {1}})

    def test_publish_ships_level_zero_only_for_the_policy_and_within_the_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            (id1 / 'progs').mkdir()
            def record(name, h):
                raws = {0: model(faces=30, seed=2), 1: model(), 2: model(faces=6, seed=3)}
                (id1 / npc_lod.far_path(name)).write_bytes(raws[1])
                return {'model': npc_lod.far_path(name), '_levels': raws, 'lod': {'head_error': {'hausdorff': h}}}
            models = {'fargoth': record('fargoth', 1.0), 'guard': record('guard', 0.1)}
            settings = dict(npc_lod.SETTINGS, mode='on', levels=3, policy='measured', pool=None)
            report = npc_lod.publish(id1, models, {'NPC_': {}}, settings)
            self.assertEqual((report['rows'], report['flagged'], report['dropped_for_disk']), (2, 1, 0))
            self.assertTrue((id1 / npc_lod.level_path(npc_lod.far_path('fargoth'), 0)).is_file())
            self.assertFalse((id1 / npc_lod.level_path(npc_lod.far_path('guard'), 0)).exists())
            self.assertTrue(models['fargoth']['near_use'] and not models['guard']['near_use'])
            self.assertNotIn('_levels', models['fargoth'])
            self.assertEqual(npc_lod.check(id1)['rows'], 2)


class Options(unittest.TestCase):
    def parse(self, *argv):
        parser = npc_lod.add_options(argparse.ArgumentParser())
        parser.add_argument('--build-config', type=Path)
        return parser.parse_args(list(argv))

    def test_defaults_and_default_command_lines_unchanged(self):
        options = npc_lod.resolve_options(self.parse())
        self.assertEqual(options, {'mode': npc_lod.DEFAULT_MODE, 'levels': npc_lod.DEFAULT_LEVELS,
                                   'policy': npc_lod.DEFAULT_POLICY, 'list': None,
                                   'disk_mib': npc_lod.DEFAULT_DISK_MIB})
        self.assertEqual(npc_lod.option_arguments(options), [])

    def test_shipped_defaults_come_from_the_config_file(self):
        # Owner (9 October 2026): no level becomes a default before he compares them in game; the
        # default is a config change (config/build-defaults.json), not code.
        import json
        shipped = json.loads((ROOT / 'config/build-defaults.json').read_text(encoding='utf-8'))
        self.assertEqual(shipped['npc_lod'], 'off')
        self.assertEqual(npc_lod.shipped_defaults()['mode'], 'off')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'defaults.json'
            path.write_text(json.dumps({'npc_lod': 'on', 'npc_lod_levels': 4}), encoding='utf-8')
            self.assertEqual(npc_lod.shipped_defaults(path)['levels'], 4)
            selected = Path(tmp) / 'mine.json'
            selected.write_text(json.dumps({'npc_lod': 'on', 'npc_face_lod': 'named'}), encoding='utf-8')
            options = npc_lod.resolve_options(self.parse('--build-config', str(selected)))
            self.assertEqual((options['mode'], options['policy']), ('on', 'named'))
            options = npc_lod.resolve_options(self.parse('--build-config', str(selected), '--npc-lod', 'off'))
            self.assertEqual(options['mode'], 'off')
            self.assertEqual(npc_lod.option_arguments(npc_lod.resolve_options(
                self.parse('--build-config', str(selected)))), ['--npc-lod', 'on', '--npc-face-lod', 'named'])
            selected.write_text(json.dumps({'npc_lod_levels': 5}), encoding='utf-8')
            with self.assertRaises(ValueError):
                npc_lod.resolve_options(self.parse('--build-config', str(selected)))
        from build_font_options import KNOWN_KEYS
        self.assertTrue(set(npc_lod.CONFIG_KEYS) <= KNOWN_KEYS)

    def test_off_and_list_reach_the_converters(self):
        options = npc_lod.resolve_options(self.parse('--npc-lod', 'on'))
        self.assertEqual(npc_lod.option_arguments(options), ['--npc-lod', 'on'])
        self.assertEqual(npc_lod.option_arguments(npc_lod.resolve_options(self.parse('--npc-lod-levels', '4'))),
                         ['--npc-lod-levels', '4'])
        options = npc_lod.resolve_options(self.parse('--npc-face-lod', 'measured'))
        self.assertEqual(npc_lod.option_arguments(options), ['--npc-face-lod', 'measured'])
        options = npc_lod.resolve_options(self.parse('--npc-face-lod', 'list', '--npc-face-lod-list', 'f.txt'))
        self.assertEqual(npc_lod.option_arguments(options), ['--npc-face-lod', 'list', '--npc-face-lod-list', 'f.txt'])
        with self.assertRaises(ValueError):
            npc_lod.resolve_options(self.parse('--npc-face-lod', 'list'))
        with self.assertRaises(ValueError):
            npc_lod.resolve_options(self.parse('--npc-face-lod-list', 'f.txt'))

    def test_build_passes_options_to_every_resident_converter(self):
        source = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn('npc_lod.add_options', source)
        for converter in ('prepare_area.py', 'prepare_balmora.py', 'prepare_balmora_interiors.py', 'import_town.py'):
            text = (ROOT / 'tools' / converter).read_text(encoding='utf-8')
            self.assertIn('npc_lod', text, converter)


    def test_stage_arguments_are_strings(self):
        # BUILD-NPCLOD-PATH-ARG-34: the pool folder went into the command as a Path and the
        # scheduler's build-state.json could not be written (area stage, first --npc-lod on build).
        import json
        import build
        args = argparse.Namespace(npc_lod='on', npc_lod_levels=4, npc_face_lod='all', npc_face_lod_list=None,
                                  npc_lod_disk_mib=None, build_config=None, no_media_cache=False,
                                  allow_release_reuse=True, workspace=Path('/w'))
        for stage in ('area', 'balmora', 'balmora-interiors', 'town-vivec'):
            items = build.npc_lod_arguments(args, Path('/w/build/r'), stage)
            self.assertIn('--npc-model-pool', items)
            self.assertTrue(all(isinstance(item, str) for item in items), items)
            json.dumps(items)
        self.assertEqual(build.npc_lod_arguments(args, Path('/w/build/r'), 'npcs'), [])


class HeadRule(unittest.TestCase):
    def shapes(self, head=300, others=(100, 80), name_clash=False):
        out = [{'name': 'head', 'part': 0, 'faces': np.zeros((head, 3), int)}]
        for i, n in enumerate(others):
            out.append({'name': 'head' if name_clash and i == 0 else 'part%d' % i, 'part': 3,
                        'faces': np.zeros((n, 3), int)})
        return out

    def test_whole_head_when_it_fits(self):
        self.assertEqual(npc_lod.near_head_faces(self.shapes()), {'head': 300})

    def test_share_and_clipped_head(self):
        self.assertEqual(npc_lod.near_head_faces(self.shapes(head=1000)), {'head': 666 - 8 - 8})
        self.assertEqual(npc_lod.near_head_faces(self.shapes(), share=0.5), {'head': 150})

    def test_ambiguous_names_are_not_protected(self):
        self.assertEqual(npc_lod.near_head_faces(self.shapes(name_clash=True)), {})


def grid(name, part, width, height, z0, frames=8):
    """A synthetic waved panel (no game assets), as tests/test_npc_head_detail.py builds them."""
    xs, zs = np.meshgrid(np.linspace(0, 4, width + 1), np.linspace(z0, z0 + 6, height + 1))
    points = np.column_stack((xs.ravel(), .3 * np.sin(xs.ravel() * 2 + zs.ravel()), zs.ravel()))
    faces = []
    for j in range(height):
        for i in range(width):
            a = j * (width + 1) + i
            faces += [(a, a + 1, a + width + 1), (a + 1, a + width + 2, a + width + 1)]
    positions = np.stack([points + [0, 0, k * .5] for k in range(frames)])
    uv = np.column_stack((xs.ravel() / 4, (zs.ravel() - z0) / 6))
    return {'name': name, 'part': part, 'positions': positions, 'faces': np.array(faces),
            'uv': uv, 'colours': np.ones((len(points), 4)), 'material': 0}


class LevelBakes(unittest.TestCase):
    """On/off reproducibility: the map model of --npc-lod on is the budget bake byte for byte, --npc-lod off
    is npc_geometry's default single model, every level has the map model's frames, and two bakes of
    the same inputs are byte-identical."""
    palette = bytes(range(256)) * 3
    materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]

    def shapes(self):
        return [grid('tri head', 0, 10, 10, 30), grid('tri chest', 3, 20, 12, 15), grid('tri foot', 15, 6, 4, 0)]

    def test_levels_on_and_off(self):
        try:
            import fast_simplification  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')
        shapes = self.shapes()
        args = (shapes, self.materials, {}, self.palette)
        on, record = npc_lod.bake_levels(*args, label='synthetic', levels=(0, 1, 2, 3))
        again, _ = npc_lod.bake_levels(self.shapes(), self.materials, {}, self.palette,
                                       label='synthetic', levels=(0, 1, 2, 3))
        self.assertEqual(on, again)
        self.assertEqual(sorted(on), [0, 1, 2, 3])
        budget = npc_lod.bake_far(*args, detail='budget')
        self.assertEqual(on[1], animated_mdl(*budget[:4]))
        off, _ = npc_lod.bake_levels(*args, label='synthetic', levels=(1,))
        self.assertEqual(off[1], animated_mdl(*npc_lod.bake_far(*args)[:4]))
        if not npc_lod.head_detail_supported():
            self.assertEqual(off[1], on[1])         # without the head switch both are the earlier bake
        names = npc_lod.levels_check(on)
        self.assertEqual(len(names), 8)
        tris = {k: npc_lod.model_counts(v)['triangles'] for k, v in on.items()}
        self.assertTrue(tris[0] > tris[1] > tris[2] > tris[3], tris)
        self.assertEqual(record['levels']['1']['triangles'], tris[1])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class EngineNative(unittest.TestCase):
    def test_selection_cap_hysteresis_and_fallback(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(self, 'aga_npc_lod_test.c', [Path(native.SOURCE) / 'src/aw_npc_lod.c'],
                                             cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])


class EngineWiring(unittest.TestCase):
    """The swap is render-only, in the one place the renderer picks an entity's model."""
    def test_render_only_swap_restores_the_entity_model(self):
        text = (ROOT / 'engine/aga/src/r_main.c').read_text(encoding='latin-1')
        block = text[text.index('case mod_alias:', text.index('void R_DrawEntitiesOnList')):]
        block = block[:block.index('default:')]
        self.assertIn('own = currententity->model', block)
        self.assertIn('currententity->model = AW_NpcLodModel (currententity)', block)
        self.assertIn('currententity->model = own', block)
        self.assertNotIn('continue', block)
        self.assertIn('AW_NpcLodFrame ()', text)

    def test_no_fatal_errors_and_reset_with_the_map(self):
        text = (ROOT / 'engine/aga/src/aw_npc_lod.c').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'\b(Sys_Error|Host_Error)\s*\(', text))
        host = (ROOT / 'engine/aga/src/host.c').read_text(encoding='latin-1')
        self.assertLess(host.index('AW_NpcLodReset();'), host.index('Mod_ClearAll ();', host.index('AW_NpcLodReset();') - 200))
        self.assertIn('AW_NpcLodInit ();', host)
        self.assertIn('aw_npc_lod.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='latin-1'))


if __name__ == '__main__':
    unittest.main()
