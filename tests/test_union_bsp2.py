# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-COLLISION-UNION-FALLBACK-41: collision unions the compiler refuses in BSP29 are compiled in BSP2 by their own unit
kinds (tools/chim/union_bsp2.py), for the meshes config/collision-union-bsp2.json lists. The default kinds never reach
that code, the swap of collision_bsp.compile_standing_checked never outlives its unit, and the copied brush text and
packing stay the originals'."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from itertools import product
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import collision_bsp  # noqa: E402
from chim import union_bsp2 as U  # noqa: E402

QBSP = os.environ.get('AMIWIND_TEST_QBSP')


def pieces_of(boxes, tilt=0.0):
    out = []
    for i, (lo, hi) in enumerate(boxes):
        points = np.array(list(product(*zip(lo, hi))), dtype=float)
        if tilt:
            points[:, 2] += (points[:, 0] - lo[0]) * tilt
        out.append((points, ConvexHull(points), [], 0))
    return out


ARCH = [((-40, -8, 0), (-24, 8, 72)), ((24, -8, 0), (40, 8, 72)), ((-40, -8, 56), (40, 8, 72)), ((55, -12, 0), (90, 12, 2))]


def box_parts(n):
    out = []
    for k in range(n):
        x, y = (k % 8) * 40.0, (k // 8) * 40.0
        lo, hi = (x, y, 0.0), (x + 30.0, y + 30.0, 20.0 + (k % 3) * 10)
        pts = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
        out.append((pts, None, [], 0.))
    return out


class KindTests(unittest.TestCase):
    def test_the_default_kinds_never_reach_the_new_module_or_its_list(self):
        from chim import units
        self.assertEqual(units.CODE_ENTRIES['variant-bsp2'], [('tools/chim/union_bsp2.py', 'variant_unit_bsp2')])
        self.assertEqual(units.CODE_ENTRIES['tiles-budget-union'], [('tools/chim/union_bsp2.py', 'budget_tile_unit_union')])
        for kind in ('variant', 'tiles', 'tiles-budget', 'tiles-budget-placed', 'variant-placed', 'mesh', 'terrain'):
            files = units.unit_code_key(kind)['files']
            self.assertNotIn('tools/chim/union_bsp2.py', files, kind)
            self.assertNotIn('config/collision-union-bsp2.json', files, kind)
        self.assertIn('tools/chim/union_bsp2.py', units.unit_code_key('variant-bsp2')['files'])


class SwapTests(unittest.TestCase):
    def test_the_compiler_function_is_the_original_again_after_every_unit(self):
        original = collision_bsp.compile_standing_checked
        seen = []

        def passing(task):
            seen.append(collision_bsp.compile_standing_checked)
            return {'collision_fallback': None}

        def refusing(task):
            seen.append(collision_bsp.compile_standing_checked)
            try:
                collision_bsp.compile_standing_checked([], 'qbsp', 'cache')
            except ValueError as error:
                return {'collision_fallback': str(error)[:400]}
            raise AssertionError('the swapped function should refuse here')

        def breaking(task):
            raise RuntimeError('the unit breaks')
        with patch('chim.models.variant_unit', side_effect=passing):
            self.assertEqual(U.variant_unit_bsp2({})['collision_form'], 'bsp2')
        self.assertIs(collision_bsp.compile_standing_checked, original)
        with patch('chim.models.variant_unit', side_effect=refusing), \
                patch.object(U, 'compile_standing_bsp2', side_effect=ValueError('Collision compiler failed in BSP2 (exit 1); '
                                                                               'its last lines:\nERROR at the end')):
            res = U.variant_unit_bsp2({})
        self.assertIs(collision_bsp.compile_standing_checked, original)
        self.assertIn('ERROR at the end', res['collision_compiler_tail'])
        with patch('chim.models.variant_unit', side_effect=breaking):
            with self.assertRaises(RuntimeError):
                U.variant_unit_bsp2({})
        self.assertIs(collision_bsp.compile_standing_checked, original)
        self.assertTrue(all(f is not original for f in seen))

    @unittest.skipUnless(QBSP, 'requires external qbsp')
    def test_a_plain_variant_after_bsp2_units_gives_the_bytes_it_gave_before(self):
        from chim.models import variant_unit
        parts = box_parts(12)
        ref = {'scale': 1., 'rotation_radians': [0., 0., 0.], 'position': [0., 0., 0.]}
        with tempfile.TemporaryDirectory() as tmp, \
                patch('prepare_mesh_bsp._prepare_placement', return_value=([], parts, (0., 0., 0.), (330., 70., 50.))), \
                patch('prepare_mesh_bsp.flame_entities', return_value=[]):
            task = {'ref': ref, 'data': None, 'texsize': 64, 'centre': [0., 0.],
                    'model': {'source': 'meshes/x/bm_ex_iceberg_shard01.nif'}, 'exact': True, 'hollow': False,
                    'qbsp': QBSP, 'hull_patch': True, 'collision_cache': tmp}
            before = variant_unit(task)
            bsp2 = U.variant_unit_bsp2(task)
            with patch.object(U, 'compile_standing_bsp2', side_effect=ValueError('refused')):
                U.variant_unit_bsp2(task)
            after = variant_unit(task)
        self.assertEqual(collision_bsp.compile_standing_checked.__qualname__, 'compile_standing_checked')
        self.assertEqual(collision_bsp.compile_standing_checked.__module__, 'collision_bsp')
        self.assertEqual(before['lumps'], after['lumps'])
        self.assertEqual(before.get('collision_fallback'), after.get('collision_fallback'))
        self.assertEqual(bsp2['hull_form'], before['hull_form'])
        self.assertEqual(bsp2['lumps'], before['lumps'])          # a union that compiles in BSP29: the same bytes


class CopyTests(unittest.TestCase):
    def map_text_of_the_original(self, pieces, merge_coplanar):
        written = []

        def fake_run(cmd, cwd=None, **kw):
            written.append(Path(cwd, 'collision.map').read_text())
            return subprocess.CompletedProcess(cmd, 1, stdout=b'************ ERROR ************\nstub')
        with tempfile.TemporaryDirectory() as tmp:
            compiler = Path(tmp, 'qbsp')
            compiler.write_bytes(b'stub compiler')
            with patch.object(collision_bsp.subprocess, 'run', side_effect=fake_run):
                with self.assertRaises(ValueError):
                    collision_bsp.compile_standing_checked_once(pieces, compiler, Path(tmp, 'cache'),
                                                                merge_coplanar=merge_coplanar)
        return written[0]

    def test_the_brush_text_is_the_originals(self):
        for pieces in (pieces_of(ARCH), pieces_of(ARCH, tilt=0.37)):
            for merge in (False, True):
                self.assertEqual(U.brush_source(pieces, merge_coplanar=merge), self.map_text_of_the_original(pieces, merge))

    @unittest.skipUnless(QBSP, 'requires external qbsp')
    def test_a_union_that_compiles_in_bsp29_packs_the_same_in_bsp2(self):
        for pieces in (pieces_of(ARCH), pieces_of(ARCH, tilt=0.37)):
            with tempfile.TemporaryDirectory() as tmp:
                old = collision_bsp.compile_standing_checked_once(pieces, Path(QBSP), Path(tmp, 'a'))
                new = U.compile_standing_bsp2_once(pieces, Path(QBSP), Path(tmp, 'b'))
                self.assertEqual(old, new)
                self.assertEqual(new, U.compile_standing_bsp2_once(pieces, Path(QBSP), Path(tmp, 'b')))   # cached

    def test_a_refusal_keeps_the_compilers_last_lines_whole(self):
        text = '\n'.join('line %d %s' % (i, 'x' * 90) for i in range(100))
        error = str(U._refusal(1, text))
        self.assertIn('line 99 ' + 'x' * 90, error)
        self.assertIn('line 60 ', error)
        self.assertNotIn('line 59 ', error)


class ChoiceTests(unittest.TestCase):
    LISTED = {'x/bm_ex_iceberg_shard01': {'reason': 'r'}, 'x/bm_ex_iceberg': {'tiles': True, 'reason': 'r'}}

    def item(self, source, qbsp='qbsp'):
        return ('fp', {'model': {'source': source}, 'qbsp': qbsp})

    def test_only_a_listed_fallback_with_the_compiler_runs_again(self):
        results = [{'collision_fallback': 'refused'}, {'collision_fallback': 'refused'}, {'collision_fallback': None},
                   {'collision_fallback': 'refused'}, {'collision_fallback': 'refused'}]
        items = [self.item('meshes/x/bm_ex_iceberg_shard01.nif'), self.item('meshes/x/ex_vivec_c_02.nif'),
                 self.item('meshes/x/bm_ex_iceberg_shard01.nif'), self.item('meshes/x/bm_ex_iceberg_shard01.nif', None),
                 self.item('meshes/x/bm_ex_iceberg.nif')]
        self.assertEqual(U.redo_indices(results, items, self.LISTED), [0])
        self.assertEqual(U.redo_indices(results, items, {}), [])

    def test_tiles_by_listed_model_only(self):
        self.assertTrue(U.tiles_listed('meshes/x/BM_Ex_Iceberg.nif', self.LISTED))
        self.assertFalse(U.tiles_listed('meshes/x/bm_ex_iceberg_shard01.nif', self.LISTED))
        self.assertFalse(U.tiles_listed('meshes/i/in_akulacave00.nif', self.LISTED))

    def test_the_shipped_list_and_its_layer_keys(self):
        import build_cache
        text = U.UNION_LIST.read_text(encoding='utf-8')
        doc = json.loads(text)
        self.assertEqual(json.dumps(doc, indent=1) + '\n', text)                  # written as the layer views are
        listed = U.union_list()
        self.assertEqual(set(listed), {'x/bm_ex_iceberg_shard01', 'x/bm_ex_iceberg', 'x/bm_ex_iceberg_collapsed'})
        self.assertFalse(listed['x/bm_ex_iceberg_shard01'].get('tiles'))
        self.assertTrue(listed['x/bm_ex_iceberg']['tiles'] and listed['x/bm_ex_iceberg_collapsed']['tiles'])
        for row in listed.values():
            self.assertTrue(row['reason'])
        # every row is Bloodmoon's: a base stage keys the list without them, so they re-key no base stage
        self.assertEqual(sorted(doc['layers']['bloodmoon']), sorted(listed))
        self.assertIn('config/collision-union-bsp2.json', build_cache.LAYER_ROW_TABLES)
        indent, field = build_cache.LAYER_ROW_TABLES['config/collision-union-bsp2.json']
        base = json.loads(build_cache.layer_table_view(text, {'bloodmoon', 'tribunal'}, indent, field))
        self.assertEqual(base['meshes'], {})
        self.assertNotIn('layers', base)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, 'list.json')
            bad.write_text(json.dumps({'format': 'other', 'meshes': {}}))
            with self.assertRaises(ValueError):
                U.union_list(bad)
            self.assertEqual(U.union_list(Path(tmp, 'missing.json')), {})


if __name__ == '__main__':
    unittest.main()
