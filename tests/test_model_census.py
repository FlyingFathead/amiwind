# SPDX-License-Identifier: GPL-3.0-only
"""tools/model_census.py (MODEL-CENSUS-TOOL-67), on synthetic data only (no game file): who places what where, the
texture repeat catcher, the quality measures (mesh_methods.reduction_quality), one space's columns and method in use
through the builder's own code (method table, recipe row, method 2, a scenery group), the schema check, the build to
build diff, the files, and the build step that never fails a build."""
import argparse
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))          # src before tools (TEST-WORKER-SYSPATH-32)

import model_census as mc  # noqa: E402

try:
    import numpy as np
except ImportError:                       # the measures need numpy (as the builder does)
    np = None
try:
    import scipy  # noqa: F401
except ImportError:
    scipy = None

SOURCE = 'meshes/x/test_box.nif'
# a 64-unit box (Morrowind units), two triangles per side, outward winding, one material
BOX_V = [(x, y, z, x / 64.0, z / 64.0) for x in (0, 64) for y in (0, 64) for z in (0, 64)]
BOX_F = [(0, 1, 3, 0), (0, 3, 2, 0), (4, 6, 7, 0), (4, 7, 5, 0), (0, 4, 5, 0), (0, 5, 1, 0),
         (2, 3, 7, 0), (2, 7, 6, 0), (0, 2, 6, 0), (0, 6, 4, 0), (1, 5, 7, 0), (1, 7, 3, 0)]
MATERIALS = [{'texture_source': 'textures\\tx_box.dds', 'diffuse': [1, 1, 1]}]


def tables(**extra):
    out = {'methods': {'format': 'amiwind-mesh-methods-1', 'default': 'merge', 'meshes': {}},
           'recipes': {'format': 1, 'everywhere': 'e', 'recipes': {'e': {'models': {}}}}, 'everywhere': 'e',
           'everywhere_in_rooms': True, 'method2': {'format': 1, 'models': {}}, 'model_method': 2,
           'flatten': {'outdoors': {}, 'rooms': {}}, 'groups': {}}
    out.update(extra)
    return out


def method2_row(triangles, sha='ab' * 32, method=2):
    return {'source_sha256': sha, 'kind': 'conservative', 'method': method, 'recipe': {}, 'source': {}, 'ab': {},
            'counts': {'triangles': triangles, 'faces_rooms': triangles - 1, 'faces_outdoors': triangles - 2,
                       'open_edges_before': 0, 'open_edges': 0}}


def column(faces, triangles, **quality):
    return dict({'faces': faces, 'triangles': triangles, 'new_open': 0, 'lost_open': 0, 'seam_torn': 0.0,
                 'rim_torn': 0.0, 'shape_error': 0.0}, **quality)


def space(in_use, columns, original, default=None):
    default = default or in_use
    t = columns[in_use]['triangles']
    return {'profile': {'ratio': 1.0, 'texture_size': 32}, 'in_use': in_use, 'default': default, 'columns': columns,
            'today': {'faces': columns[in_use]['faces'], 'triangles': t}, 'heavier_than_original': t > original,
            'row_heavier': in_use != default and t > columns[default]['triangles']}


def row(model, original, spaces, placements):
    return {'model': model, 'status': 'ok', 'file': 'Morrowind.bsa', 'nif_bytes': 100, 'nif_sha256': 'cd' * 32,
            'original': {'triangles': original, 'size_mw': [1, 1, 1], 'repeat_max': 1.0, 'repeat_texture': None,
                         'repeat_over_16': 0, 'repeat_over_64': 0},
            'spaces': spaces, 'placements': placements, 'placed': mc.space_totals(placements),
            'record_count': 1, 'records': [{'id': 'r', 'type': 'STAT', 'name': ''}]}


def document(rows):
    doc = {'format': mc.FORMAT, 'code_sha256': '0' * 64, 'code': {}, 'tables_sha256': '1' * 64, 'tables': {},
           'inputs': {'Morrowind.esm': '2' * 64}, 'settings': {'quality': True}, 'build': None, 'models': rows}
    doc['summary'] = mc.summarise(rows)
    return doc


def sample_rows():
    return [row('meshes/x/a.nif', 12, {'outdoors': space('merge', {'current': column(6, 12), 'merge': column(6, 12)}, 12)},
                {'Vvardenfell outdoors': 10}),
            row('meshes/i/b.nif', 100, {'rooms': space('current', {'current': column(150, 180), 'merge': column(120, 180)},
                                                       100)}, {'Mournhold rooms': 3}),
            row('meshes/o/c.nif', 50, {'outdoors': space('row', {'current': column(40, 50), 'merge': column(40, 50),
                                                                 'row': dict(column(30, 60), kind='ratio')}, 50, 'merge')},
                {'Solstheim outdoors': 2}),
            {'model': 'meshes/editormarker.nif', 'status': 'special',
             'special': {'kind': 'editor marker', 'why': 'invisible'}, 'placements': {'Vvardenfell rooms': 4},
             'placed': {'outdoors': 0, 'rooms': 4}, 'record_count': 0, 'records': []}]


class PlacementTests(unittest.TestCase):
    def test_lands_spaces_and_what_is_left_out(self):
        lamp = {'type': 'LIGH', 'model': 'meshes/l/lamp.nif', 'deleted': False}
        masters = {
            'Morrowind.esm': {'objects': {'lamp': lamp, 'gone': dict(lamp, deleted=True),
                                          'bare': {'type': 'MISC', 'model': '', 'deleted': False}},
                              'cells': [{'interior': True, 'name': 'Room A', 'x': 0, 'y': 0, 'deleted': False,
                                         'refs': [{'id': 'lamp'}, {'id': 'lamp', 'del': 1}, {'id': 'gone'}, {'id': 'bare'}]},
                                        {'interior': False, 'name': '', 'x': 1, 'y': 2, 'deleted': False,
                                         'refs': [{'id': 'lamp'}]},
                                        {'interior': False, 'name': '', 'x': 5, 'y': 5, 'deleted': True,
                                         'refs': [{'id': 'lamp'}]}]},
            'Tribunal.esm': {'objects': {},
                             'cells': [{'interior': True, 'name': 'room a', 'x': 0, 'y': 0, 'deleted': False,
                                        'refs': [{'id': 'lamp'}]},              # the base cell again: left out
                                       {'interior': True, 'name': 'Hall', 'x': 0, 'y': 0, 'deleted': False,
                                        'refs': [{'id': 'lamp'}, {'id': 'lamp'}]}]}}
        placed, users = mc.placements_of(masters, {'lamp': 'Lantern'})
        self.assertEqual(dict(placed), {'meshes/l/lamp.nif': {'Vvardenfell rooms': 1, 'Vvardenfell outdoors': 1,
                                                              'Mournhold rooms': 2}})
        self.assertEqual(users['meshes/l/lamp.nif'], {'lamp': ('LIGH', 'Lantern')})
        self.assertEqual(mc.space_totals(placed['meshes/l/lamp.nif']), {'outdoors': 1, 'rooms': 3})

    def test_special_kinds(self):
        self.assertEqual(mc.special_kind('meshes/editormarker_box.nif', 'x')[0], 'editor marker')
        self.assertEqual(mc.special_kind('meshes/e/steam_vent.nif', 'x')[0], 'particle effect')
        self.assertEqual(mc.special_kind('meshes/r/guar.nif', 'ValueError: no static triangles')[0], 'animated or skinned')
        self.assertEqual(mc.special_kind('meshes/x/odd.nif', 'ValueError: bad block'), ('unreadable', 'ValueError: bad block'))
        self.assertTrue(set(k for k in mc.SPECIAL_KINDS) >= {'editor marker', 'particle effect', 'missing'})


@unittest.skipUnless(np is not None, 'numpy unavailable')
class RepeatTests(unittest.TestCase):
    def test_the_largest_repeat_and_the_counts(self):
        v = np.array([(0, 0, 0, 0, 0), (1, 0, 0, 1, 0), (0, 1, 0, 0, 1),           # repeats once
                      (0, 0, 1, 0, 0), (1, 0, 1, 20, 0), (0, 1, 1, 0, 3),          # 20 along u
                      (0, 0, 2, 0, 0), (1, 0, 2, 2, 0), (0, 1, 2, 0, 999)], float)  # 999 along v
        f = np.array([(0, 1, 2, 0), (3, 4, 5, 0), (6, 7, 8, 1)])
        out = mc.texture_repeats(v, f, [{'texture_source': 'textures\\a.dds'}, {'texture_source': 'Textures\\Rope.TGA'}])
        self.assertEqual(out, {'repeat_max': 999.0, 'repeat_texture': 'rope.tga', 'repeat_over_16': 2, 'repeat_over_64': 1})


@unittest.skipUnless(np is not None and scipy is not None, 'numpy or scipy unavailable')
class QualityTests(unittest.TestCase):
    def test_an_unchanged_mesh_is_intact(self):
        import mesh_methods
        v, f = np.array(BOX_V, float), np.array(BOX_F, int)
        q = mesh_methods.reduction_quality(v, f, v.copy(), f.copy())
        self.assertEqual((q['new_open'], q['lost_open'], q['seam_torn'], q['rim_torn']), (0, 0, 0.0, 0.0))
        self.assertEqual(q['shape_error'], 0.0)

    def test_a_missing_triangle_opens_three_edges(self):
        import mesh_methods
        v, f = np.array(BOX_V, float), np.array(BOX_F, int)
        q = mesh_methods.reduction_quality(v, f, v.copy(), f[1:].copy())
        self.assertEqual((q['new_open'], q['lost_open']), (3, 0))
        again = mesh_methods.reduction_quality(v, f, v.copy(), f[1:].copy())
        self.assertEqual(q, again)                                       # a fixed seed: the same numbers every time

    def test_shape_error_is_a_share_of_the_diagonal(self):
        import mesh_methods
        v, f = np.array(BOX_V, float), np.array(BOX_F, int)
        moved = v.copy()
        moved[7, :3] += 32                                               # one corner pulled out by 32 units
        q = mesh_methods.reduction_quality(v, f, moved, f.copy())
        self.assertGreater(q['shape_error'], 0.05)
        # at most the corner's own move (32 units on each axis) over the box's diagonal
        self.assertLessEqual(q['shape_error'], np.linalg.norm([32, 32, 32]) / np.linalg.norm([64, 64, 64]) + 1e-5)

    def test_the_sweep_measure_keeps_its_numbers(self):
        # mesh_methods.measure now takes its shape error from shape_error(): the same sampling and seed as before
        import mesh_methods
        v, f = np.array(BOX_V, float), np.array(BOX_F, int)
        h, mean = mesh_methods.shape_error(v, f, v, f)
        self.assertAlmostEqual(h, 0.0, places=9)
        self.assertAlmostEqual(mean, 0.0, places=9)
        self.assertEqual(mesh_methods.shape_error(v, f, v, f), (h, mean))     # the fixed seed: the same samples


@unittest.skipUnless(np is not None and scipy is not None, 'numpy or scipy unavailable')
class SpaceRowTests(unittest.TestCase):
    def setUp(self):
        self.v, self.f = np.array(BOX_V, float), np.array(BOX_F, int)
        self.model = {'source': SOURCE, 'sha256': 'packet', 'source_sha256': 'ab' * 32}

    def run_space(self, space, t, quality=True):
        return mc.space_row(self.v, self.f, MATERIALS, self.model, space, t, quality)

    def test_outdoors_takes_the_method_table_and_rooms_the_converter(self):
        out = self.run_space('outdoors', tables())
        self.assertEqual(out['in_use'], 'merge')
        self.assertEqual(out['today'], {'faces': 6, 'triangles': 12})                 # coplanar pairs: one face each
        self.assertNotIn('meshopt+merge', out['columns'])                             # the profile does not reduce it
        self.assertFalse(out['heavier_than_original'] or out['row_heavier'])
        self.assertEqual(out['columns']['merge']['new_open'], 0)
        rooms = self.run_space('rooms', tables())
        self.assertEqual((rooms['in_use'], rooms['default']), ('current', 'current'))
        converter = self.run_space('outdoors', tables(methods={'format': 'amiwind-mesh-methods-1', 'default': 'merge',
                                                               'meshes': {SOURCE: {'method': 'converter'}}}))
        self.assertEqual(converter['in_use'], 'current')

    def test_method_2_wins_where_its_row_matches_the_nif(self):
        t = tables(method2={'format': 1, 'models': {SOURCE: method2_row(8)}})
        out = self.run_space('outdoors', t)
        self.assertEqual(out['in_use'], 'method 2')
        self.assertEqual(out['today'], {'faces': 6, 'triangles': 8})                  # the row's recorded counts
        self.assertEqual(out['default'], 'merge')
        self.assertEqual(self.run_space('rooms', t)['today']['faces'], 7)
        # a method-1 row, or the build's method 1, keeps method 1 in use; the row stays a column
        for t2 in (tables(method2={'format': 1, 'models': {SOURCE: method2_row(8, method=1)}}),
                   dict(t, model_method=1)):
            out = self.run_space('outdoors', t2)
            self.assertEqual(out['in_use'], 'merge')
            self.assertIn('method 2', out['columns'])
        # another NIF (another SHA-256): no row at all
        other = tables(method2={'format': 1, 'models': {SOURCE: method2_row(8, sha='ef' * 32)}})
        self.assertNotIn('method 2', self.run_space('outdoors', other)['columns'])

    def test_heavier_than_the_original_and_than_without_the_row(self):
        out = self.run_space('outdoors', tables(method2={'format': 1, 'models': {SOURCE: method2_row(20)}}))
        self.assertTrue(out['heavier_than_original'])                               # 20 > 12 source triangles
        self.assertTrue(out['row_heavier'])                                         # 20 > 12 with merge alone

    def test_a_scenery_group_profile_is_read_alone_outdoors(self):
        out = self.run_space('outdoors', tables(groups={SOURCE: ('g', {'ratio': 1.0, 'texture_size': 64})}))
        self.assertEqual(out['profile'], {'ratio': 1.0, 'texture_size': 64, 'group': 'g'})
        self.assertNotIn('group', self.run_space('rooms', tables(groups={SOURCE: ('g', {})}))['profile'])

    def test_without_quality_only_counts(self):
        out = self.run_space('outdoors', tables(), quality=False)
        self.assertEqual(set(out['columns']['merge']), {'faces', 'triangles'})


class SchemaTests(unittest.TestCase):
    def test_a_good_census_holds(self):
        doc = json.loads(json.dumps(document(sample_rows())))
        self.assertEqual(mc.check(doc), [])
        s = doc['summary']
        self.assertEqual(s['special'], {'editor marker': 1})
        self.assertEqual(s['total'], {'placements': 15, 'original': 12 * 10 + 100 * 3 + 50 * 2,
                                      'today': 12 * 10 + 180 * 3 + 60 * 2})
        self.assertEqual([(h['model'], h['space']) for h in s['heavier_than_original']],
                         [('meshes/i/b.nif', 'rooms'), ('meshes/o/c.nif', 'outdoors')])
        self.assertEqual(s['row_heavier'][0]['without'], 50)
        self.assertEqual(s['lands']['Mournhold'], {'placements': 3, 'original': 300, 'today': 540})

    def test_every_impossible_count_is_named(self):
        cases = {
            'missing field': lambda d: d.pop('inputs'),
            'not counts': lambda d: d['models'][0]['placements'].update({'Vvardenfell outdoors': -1}),
            'does not add up': lambda d: d['models'][0]['placed'].update(outdoors=11),
            'cannot make': lambda d: d['models'][0]['spaces']['outdoors']['columns']['merge'].update(triangles=5),
            'heavier_than_original': lambda d: d['models'][1]['spaces']['rooms'].update(heavier_than_original=False),
            'row_heavier': lambda d: d['models'][2]['spaces']['outdoors'].update(row_heavier=False),
            'not one of its columns': lambda d: d['models'][0]['spaces']['outdoors'].update(in_use='nope'),
            'unknown method': lambda d: d['models'][0]['spaces']['outdoors']['columns'].update(bogus=column(1, 1)),
            'special case without a known kind': lambda d: d['models'][3]['special'].update(kind='odd'),
            'summary total differs': lambda d: d['summary']['total'].update(today=1),
            'lower-case meshes/': lambda d: d['models'][0].update(model='Meshes/X/A.nif'),
            'measured': lambda d: d['models'][0]['placements'].update({'Vvardenfell rooms': 1}) or
            d['models'][0]['placed'].update(rooms=1),
            'today differs': lambda d: d['models'][0]['spaces']['outdoors']['today'].update(faces=7),
        }
        for words, change in cases.items():
            doc = json.loads(json.dumps(document(sample_rows())))
            change(doc)
            problems = mc.check(doc)
            self.assertTrue(any(words in p for p in problems), '%s: %s' % (words, problems))

    def test_not_a_census(self):
        self.assertEqual(len(mc.check({'format': 'other'})), 1)


class DiffTests(unittest.TestCase):
    def test_gained_new_heavier_new_and_gone(self):
        before = document(sample_rows())
        rows = copy.deepcopy(sample_rows())
        rows[0]['spaces']['outdoors'] = space('merge', {'current': column(6, 14), 'merge': column(7, 14)}, 12)
        rows[2]['spaces']['outdoors'] = space('merge', {'current': column(40, 50), 'merge': column(40, 40)}, 50)
        rows.append(row('meshes/x/new.nif', 5, {'outdoors': space('merge', {'merge': column(5, 5)}, 5)},
                        {'Vvardenfell outdoors': 1}))
        del rows[3]
        after = document(rows)
        out = mc.diff(before, after)
        self.assertEqual([(g['model'], g['before'], g['after']) for g in out['gained']], [('meshes/x/a.nif', 12, 14)])
        self.assertEqual([c['model'] for c in out['changed']], ['meshes/o/c.nif', 'meshes/x/a.nif'])
        self.assertEqual([h['model'] for h in out['new_heavier']], ['meshes/x/a.nif'])
        self.assertEqual((out['new_models'], out['gone_models']), (['meshes/x/new.nif'], ['meshes/editormarker.nif']))
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            a.write_text(json.dumps(before))
            b.write_text(json.dumps(after))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mc.main(['diff', str(a), str(b)]), 1)
                self.assertEqual(mc.main(['diff', str(a), str(a)]), 0)
                self.assertEqual(mc.main(['check', str(a)]), 0)
            b.write_text(json.dumps(dict(before, format='x')))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mc.main(['check', str(b)]), 1)


class FileTests(unittest.TestCase):
    def test_three_files_deterministic_and_plain(self):
        doc = document(sample_rows())
        with tempfile.TemporaryDirectory() as tmp:
            first = {k: p.read_bytes() for k, p in mc.write(doc, Path(tmp) / 'a').items()}
            second = {k: p.read_bytes() for k, p in mc.write(doc, Path(tmp) / 'b').items()}
        self.assertEqual(first, second)
        for data in first.values():
            self.assertNotIn(b'\r', data)
        lines = first['csv'].decode().splitlines()
        self.assertEqual(lines[0].split(','), list(mc.CSV_COLUMNS))
        self.assertEqual(len(lines), 1 + 3 + 1)                     # a line per model and space, one per special case
        md = first['md'].decode()
        for heading in ('## Placed triangles, original against today', '## Heavier than the original (2',
                        '## Special cases (1)', '## Texture repeats over 64'):
            self.assertIn(heading, md)
        self.assertEqual(json.loads(first['json']), json.loads(json.dumps(doc)))


class BuildStepTests(unittest.TestCase):
    def test_never_fails_a_build(self):
        lines = []
        with tempfile.TemporaryDirectory() as tmp:
            result = mc.build_step(Path(tmp) / 'run', Path(tmp) / 'no-data-files', jobs=1, log=lines.append)
        self.assertIsNone(result)
        self.assertTrue(any(line.startswith('Model census: not made:') for line in lines), lines)

    def test_the_switch_skips_it(self):
        lines = []
        with mock.patch.dict(os.environ, {mc.SWITCH: 'off'}):
            self.assertIsNone(mc.build_step('/nowhere', '/nowhere', log=lines.append))
        self.assertEqual(lines, ['Model census: skipped (AMIWIND_MODEL_CENSUS=off)'])

    def test_the_builder_runs_it_after_a_passed_image(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertLess(text.index('        container_count_step(args, run)\n'),
                        text.index('        model_census_step(args, run)\n'))
        self.assertIn("cache_dir=Path(args.workspace) / 'cache' / 'model-census-v1'", text)
        import build
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(build.model_census_step(argparse.Namespace(stage='aga', dry_run=True, data_files='/d'),
                                                      Path('/run')))
            with mock.patch.dict(os.environ, {'AMIWIND_MODEL_CENSUS': ''}):
                self.assertIsNone(build.model_census_step(
                    argparse.Namespace(stage='aga', dry_run=False, data_files='/d', miniwind=True), Path('/run')))
        self.assertIn('Model census: skipped (--dry-run)', out.getvalue())
        self.assertIn('Model census: skipped (a MiniWind build', out.getvalue())

    def test_the_code_and_tables_it_names_exist(self):
        for name in mc.CODE + mc.TABLES:
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
