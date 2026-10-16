# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's CHIM frame (format 0.5, chim.seyda): the frame box, cell and origin agree with the
legacy scene stage, and the ground is the scene stage's own triangles plus the same sampler around
them, covering every tile of the frame once. Synthetic LAND, no game data."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import seyda  # noqa: E402


def grids():
    """Nine synthetic LAND cells around Seyda Neen's cell (-2, -9): 65 x 65 heights (world units), a
    coast where the ground dips below the water, 16 x 16 materials."""
    out = []
    for cy in range(-10, -7):
        for cx in range(-3, 0):
            heights = [[40.0 * math.sin((cx * 64 + i) / 23.0) + 30.0 * math.cos((cy * 64 + j) / 17.0) - 10.0
                        for i in range(65)] for j in range(65)]
            materials = [[(i + j + cx) % 3 + 1 for i in range(16)] for j in range(16)]
            out.append({'cell': [cx, cy], 'heights': heights, 'materials': materials})
    return out


class SeydaFrameTests(unittest.TestCase):
    def test_frame_agrees_with_the_scene_stage(self):
        from prepare_quake import CENTRE, GROUND_BOUNDS, TERRAIN_APRON
        self.assertEqual(seyda.TERRAIN_APRON, TERRAIN_APRON)
        self.assertEqual(seyda.ground_bounds(), GROUND_BOUNDS)
        self.assertEqual(seyda.centre(), tuple(float(v) for v in CENTRE))
        self.assertEqual(seyda.source_cell(), (-2, -9))
        (lx, ly), (hx, hy) = seyda.frame_box()
        (gx0, gy0), (gx1, gy1) = GROUND_BOUNDS
        self.assertTrue(lx <= gx0 and ly <= gy0 and hx >= gx1 and hy >= gy1)
        # Whole3x3 sectors; large frames already shard into groups of64.
        # Preserve the real FFS72-per-directory and engine32-byte path limits.
        from collections import Counter
        from pathlib import PurePosixPath
        from chim.world import sector_path, frame_dir
        from chim import format as F
        self.assertEqual(((hx - lx) % 768, (hy - ly) % 768), (0, 0))
        count=((hx-lx)//768)*((hy-ly)//768)
        paths=[PurePosixPath(frame_dir(seyda.source_cell()))/sector_path(i,count) for i in range(count)]
        self.assertEqual(len(set(paths)),count)
        directories=Counter(str(p.parent) for p in paths)
        frame=PurePosixPath(frame_dir(seyda.source_cell()))
        directories[str(frame)]+=1+len({p.parent for p in paths if p.parent!=frame})
        for entries in directories.values():self.assertLessEqual(entries,F.FFS_MAX_DIRECTORY_ENTRIES)
        for path in paths:
            self.assertLess(len(str(path).encode('ascii')),32)
            self.assertTrue(all(len(part)<=F.FFS_NAME_CHARS for part in path.parts))
        self.assertEqual({p.name for p in paths},{F.sector_name(i) for i in range(count)})

    def test_seyda_and_balmora_frames_do_not_overlap(self):
        from chim.areas import area_problems
        self.assertEqual(area_problems(['seyda', 'balmora']), [])

    def test_ground_covers_every_tile_once_and_keeps_the_scene_triangles(self):
        from chim.ground import TriangleGround
        from prepare_quake import GROUND_BOUNDS, town_ground_triangles
        g = grids()
        low, high = seyda.frame_box()
        tris = seyda.ground_triangles(g, low, high)
        size = ((high[0] - low[0]) // 128, (high[1] - low[1]) // 128)
        ground = TriangleGround(tris, 128, low, size)       # raises on a tile without triangles
        inside = [(t, m) for t, m in town_ground_triangles(g)]
        self.assertEqual(tris[:len(inside)], [(t, int(m)) for t, m in inside])
        # every tile's triangles tile it exactly (area), none crosses a tile edge
        for (i, j), items in ground.tiles.items():
            x0, y0 = low[0] + i * 128, low[1] + j * 128
            area = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
                       for (a, b, c), _ in items)
            self.assertAlmostEqual(area, 128 * 128, places=3, msg=(i, j))
            for tri, _ in items:
                for p in tri:
                    self.assertTrue(x0 - 1e-6 <= p[0] <= x0 + 128 + 1e-6 and y0 - 1e-6 <= p[1] <= y0 + 128 + 1e-6)
        # the port's fine 32-unit patch is kept (prepare_quake.town_ground_triangles)
        port = ground.tile_list(*ground.clamp_tile(64, 320))
        self.assertEqual(len(port), 32)
        (gx0, gy0), _ = GROUND_BOUNDS
        self.assertLess(low[0], gx0 + 1)



class StoryHiddenTests(unittest.TestCase):
    """Format 0.5: a placement the opening story hides carries FLAG_STORY_HIDDEN (the legacy
    aw_story_hidden key), checked by the validator against the source manifest."""

    def test_flag_round_trips_and_the_validator_checks_it(self):
        import tempfile
        from chim import format as F
        from chim.validate import validate
        from test_chim_format import fixture
        with tempfile.TemporaryDirectory() as tmp:
            from unittest import mock
            from chim import build as CB
            original = CB.frame_input

            def hide_13(**kw):
                for ref in kw['references']:
                    if ref['number'] == 13:
                        ref['_story_hidden'] = True
                return original(**kw)
            with mock.patch.object(CB, 'frame_input', side_effect=hide_13):
                _, source = fixture(Path(tmp))
            fails, world = validate(tmp, dict(source, story_hidden=[13]))
            self.assertEqual(fails, [])
            flags = {r['ref']: r['flags'] for c in world['chunks'] for r in c['records']}
            self.assertTrue(flags[13] & F.FLAG_STORY_HIDDEN)
            self.assertFalse(any(v & F.FLAG_STORY_HIDDEN for k, v in flags.items() if k != 13))
            fails, _ = validate(tmp, dict(source, story_hidden=[]))
            self.assertTrue(any('story-hidden' in f for f in fails))

    def test_a_model_with_an_empty_own_profile_builds(self):
        # the tutorial barrel's profile is static_lod.rock_profile's {} (regression: KeyError)
        import tempfile
        from chim.validate import validate
        from test_chim_format import fixture
        with tempfile.TemporaryDirectory() as tmp:
            _, source = fixture(Path(tmp), own_profiles=True)
            self.assertEqual(validate(tmp, source)[0], [])

    def test_opening_references_are_one_reading_of_the_master(self):
        import inspect
        import prepare_opening_refs as O
        self.assertIn('opening_references(data_files)', inspect.getsource(O.prepare))
        self.assertIn('opening_references', inspect.getsource(seyda.prepare_area))



class OriginalReferenceMetadataTest(unittest.TestCase):
    def fixture(self, root):
        import json
        settings = {'source_cell': [0, 0], 'source_radius': 1, 'centre': [0, 0], 'scale': .25,
                    'bounds': [[0, 0], [4096, 2048]], 'handoff_core': [[0, 0], [4096, 2048]],
                    'owned_cells': [[0, 0], [2, 1]]}
        def ref(number, kind, position, cell):
            return {'number': number, 'type': kind, 'position': position, 'cell': cell}
        refs = [ref(1, 'STAT', [100, 100, 0], [0, 0]),
                ref(2, 'NPC_', [8300, 100, 0], [1, 0]),
                ref(3, 'STAT', [-10, 100, 0], [-1, 0]),
                ref(4, 'LEVC', [-100, -100, 0], [-1, -1]),
                ref(5, 'CONT', [200, 100, 0], [0, 0]),
                ref(6, 'ACTI', [300, 100, 0], [0, 1])]
        audit = {'area': {'center': [0, 0], 'radius_cells': 1,
                         'cells': [{'x': x, 'y': y, 'references': sum(ref['cell'] == [x, y] for ref in refs)}
                                   for x in range(-1, 2) for y in range(-1, 2)]}}
        for path, value in [('work/generated/seyda-neen/audit.json', audit),
                            ('work/generated/seyda-neen/placements.json', refs),
                            ('scenery/scenery-index.json', {'references': [refs[0], refs[2]]})]:
            p = root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value))
        return settings, refs

    def test_original_types_physical_owners_dependencies_and_harvest_are_distinct(self):
        import tempfile
        import cell_progress_chim as CH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings, refs = self.fixture(root / 'legacy')
            receipt, cat = seyda.write_source_metadata(root/'legacy', root/'work/seyda',
                                                      [refs[0], refs[2]], {5}, settings)
            self.assertEqual([r['number'] for r in cat['references']], [1, 2, 3, 5, 6])
            self.assertEqual([r['number'] for r in cat['deferred']], [2, 6])
            self.assertEqual([r['number'] for r in cat['separate_gameplay']['harvest']], [5])
            self.assertEqual(len(cat['ownership']['owned_references']), 4)
            self.assertEqual(cat['ownership']['dependency_references'][0]['reference'], 3)
            # Exercise the real tracker reader, including a declared-vs-physical CELL disagreement.
            fr = {'cell': [0, 0], 'centre': [0, 0], 'low': [-256, -256], 'grain': 256,
                  'nx': 18, 'ny': 10}
            declared, counts, notes = CH._declared_ownership(root, {'areas': ['seyda'], 'frames': [{'frame': fr}]})
            self.assertEqual(declared[(0, 0)], {(0, 0), (1, 0)})
            self.assertEqual(counts[(0, 0)][(1, 0)]['deferred_by_type'], {'NPC_': 1})
            self.assertEqual(counts[(0, 0)][(0, 0)]['owned_by_type']['ACTI'], 1)
            self.assertEqual(notes[0]['dependency_references'], 1)
            self.assertEqual(len(receipt['files']), 3)

    def test_incomplete_audit_is_rejected_before_writing_receipts(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings, refs = self.fixture(root/'legacy')
            p = root/'legacy/work/generated/seyda-neen/audit.json'; data = json.loads(p.read_text())
            data['area']['cells'] = [c for c in data['area']['cells'] if (c['x'], c['y']) != (1, 0)]
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'omits'):
                seyda.write_source_metadata(root/'legacy', root/'out', [refs[0]], (), settings)
            self.assertFalse((root/'out').exists())

    def test_missing_unconverted_reference_cannot_be_reported_as_zero(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings, refs = self.fixture(root/'legacy')
            p = root/'legacy/work/generated/seyda-neen/placements.json'
            p.write_text(json.dumps([r for r in refs if r['number'] != 2]))
            with self.assertRaisesRegex(ValueError, 'counts differ'):
                seyda.write_source_metadata(root/'legacy', root/'out', [refs[0]], (), settings)
            self.assertFalse((root/'out').exists())

    def test_unaudited_or_duplicate_placement_cannot_be_counted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings, refs = self.fixture(root/'legacy')
            for selected in [[refs[0], refs[0]], [dict(refs[0], number=999)]]:
                with self.assertRaisesRegex(ValueError, 'unaudited'):
                    seyda.write_source_metadata(root/'legacy', root/'out', selected, (), settings)
            self.assertFalse((root/'out').exists())

    def test_audit_scope_and_duplicate_originals_cannot_silently_change_counts(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings, refs = self.fixture(root/'legacy')
            with self.assertRaisesRegex(ValueError, 'scope differs'):
                seyda.write_source_metadata(root/'legacy', root/'out', [refs[0]], (),
                                            dict(settings, source_radius=2))
            p = root/'legacy/work/generated/seyda-neen/placements.json'
            p.write_text(json.dumps(refs+[refs[0]]))
            with self.assertRaisesRegex(ValueError, 'Duplicate original'):
                seyda.write_source_metadata(root/'legacy', root/'out', [refs[0]], (), settings)
            self.assertFalse((root/'out').exists())




class AuthoredCollisionSupplement(unittest.TestCase):
    def test_appended_authored_hull_keeps_carrier_and_visual_bytes(self):
        import hashlib
        import tempfile
        import copy
        from unittest.mock import patch
        from mwad.scene import pack_geometry, read_asset
        import numpy as np
        from types import SimpleNamespace
        packet = pack_geometry([(*v, 0., 0., 255, 255, 255, 255)
                                for v in ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.))],
                               [(0, 1, 2, 0)], 1)
        model = {'source': 'meshes/f/rock.nif', 'source_sha256': 'source',
                 'sha256': 'visual', 'collision': None,
                 'skipped_shapes': [{'reason': 'collision_node'}]}
        index = {'models': [model]}; original = copy.deepcopy(index)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root/'carrier.mwpak'; archive.write_bytes(b'original visual bytes')
            with patch('mwad.paths.child_ci', return_value=root/'Morrowind.bsa'), \
                 patch('mwad.audit.BSA', return_value=SimpleNamespace(path='original', entries={model['source']: {}})), \
                 patch.object(seyda, '_authored_collision_packet', return_value=(packet, [], [[0,0,0],[1,1,0]], [])):
                args = (root, index, archive, [{'model_index': 0}], root/'work', 1)
                result, out = seyda.retain_authored_collision(*args)
                self.assertEqual(index, original)
                self.assertEqual(archive.read_bytes(), b'original visual bytes')
                self.assertTrue(out.read_bytes().startswith(archive.read_bytes()))
                with out.open('rb') as stream:
                    self.assertEqual(read_asset(stream, result['models'][0]['collision']), packet)
                self.assertEqual(seyda.retain_authored_collision(*args), (result, out))
                out.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError, 'supplement differs'):
                    seyda.retain_authored_collision(*args)

    def test_source_identity_mismatch_fails_before_output(self):
        import hashlib
        from unittest.mock import patch
        packet = b'visual'
        model = {'source': 'meshes/f/rock.nif', 'source_sha256': hashlib.sha256(b'original').hexdigest(),
                 'sha256': hashlib.sha256(packet).hexdigest()}
        response = (model['source'], b'changed', ((packet, [], [], []), []), (b'collision', [], [], []), None)
        with patch('prepare_scenery._read_model', return_value=response):
            with self.assertRaisesRegex(ValueError, 'source differs'):
                seyda._authored_collision_packet((model, 'source', {}))


class GiantMushroomsKeptInTownFrame(unittest.TestCase):
    def test_giant_mushrooms_are_placed_with_closed_seams_and_declared(self):
        from unittest.mock import patch
        models = [{'source': name, 'triangles': 428} for name in
                  ('meshes/f/flora_emp_parasol_01.nif', 'meshes/f/flora_t_mushroom_02.nif',
                   'meshes/f/flora_bc_fern_04.nif')]
        refs = [{'number': n+1, 'model_index': n} for n in range(3)]
        index = {'models': models, 'references': refs}
        with patch('scenery_selection.select_runtime_refs', return_value=(refs, {'selected_groups': [], 'omitted': []})),              patch('surface_flatten.load_profiles', return_value={}):
            selected, omitted, profiles = seyda.placements(index)
            self.assertEqual([r['number'] for r in selected], [1, 2])
            self.assertEqual([r['reference'] for r in omitted['omitted']], [3])
            self.assertTrue(profiles['meshes/f/flora_emp_parasol_01.nif']['preserve_shared_seams'])
            self.assertEqual(profiles['meshes/f/flora_emp_parasol_01.nif']['visual_triangle_target'], 160)
            self.assertEqual(seyda.added_dressing_refs(index, selected), [1, 2])
            self.assertEqual(seyda.check_dressing_additions(index, [1, 2]), [1, 2])


class OriginalKelpOwnership(unittest.TestCase):
    def test_kelp_retained_but_other_deferred_dressing_stays_deferred(self):
        from unittest.mock import patch
        models = [{'source': name, 'triangles': 20} for name in
                  ('meshes/f/flora_kelp_01.nif', 'meshes/f/flora_bc_lilypad_01.nif',
                   'meshes/x/marker_01.nif', 'meshes/f/terrain_rock_bc_14.nif')]
        refs = [{'number': n+1, 'model_index': n} for n in range(4)]
        index = {'models': models, 'references': refs}
        with patch('scenery_selection.select_runtime_refs', return_value=(refs, {'selected_groups': [], 'omitted': []})), \
             patch('surface_flatten.load_profiles', return_value={}):
            selected, omitted, _ = seyda.placements(index)
            self.assertEqual([r['number'] for r in selected], [1, 4])
            self.assertEqual([r['reference'] for r in omitted['omitted']], [2, 3])
            self.assertEqual(seyda.check_dressing_additions(index, [1]), [1])
            for invalid in ([], [1, 1], [2], [1, 4]):
                with self.assertRaisesRegex(ValueError, 'differ'):
                    seyda.check_dressing_additions(index, invalid)
        import chim_town
        refused, record = chim_town.seyda_static_check({'region': []}, ['region'], [1],
                                                      {'source_dressing_added': [1]})
        self.assertEqual(refused, [])
        self.assertEqual(record['chim_only'], [])




class OpeningOriginalCellTests(unittest.TestCase):
    def original(self):
        return dict(number=172851, cell=[-2, -9], id='tutorial barrel', type='CONT',
                    model='o/barrel.nif', position=[-12000., -71000., 40.],
                    rotation_radians=[0., 0., 1.], scale=1.)

    def test_missing_cell_is_recovered_before_ownership_capture(self):
        from chim.ownership import capture
        authored = self.original()
        exported = dict(authored, model_index=3, scene_groups=['opening_barrel'])
        del exported['cell']
        bound = seyda.opening_reference(exported, authored)
        self.assertEqual(capture(bound)['_chim_original']['cell'], [-2, -9])
        self.assertEqual(bound['model_index'], 3)
        self.assertEqual(bound['scene_groups'], ['opening_barrel'])
        self.assertNotIn('cell', exported)
        self.assertEqual(seyda.opening_reference(bound, authored), bound)

    def test_different_originals_and_transforms_are_rejected(self):
        authored = self.original()
        for field, value in [('cell', [1, -10]), ('number', 172852),
                             ('position', [-12001., -71000., 40.]),
                             ('model', 'o/different.nif'), ('scale', 2.)]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, 'original audit'):
                    seyda.opening_reference(dict(authored, **{field: value}), authored)

    def test_missing_audited_cell_is_rejected(self):
        authored = self.original(); authored['cell'] = []
        with self.assertRaisesRegex(ValueError, 'original audit'):
            seyda.opening_reference(authored, authored)


if __name__ == '__main__':
    unittest.main()
