# SPDX-License-Identifier: GPL-3.0-only
"""Editor markers are filtered at the builder input (COLLISION-NC-FLAGS-32); synthetic data only."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mwad.markers import (HIDDEN_MARKER_IDS, MARKER_BYTES, is_hidden_marker, is_marker_shape,  # noqa: E402
                          may_carry_marker)


def nif(shapes, marker=b'MRK', collision=0, particles=False):
    """A synthetic TES3 NIF: a root with optional root string, named box shapes, optional collision box."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    root = N.NiNode()
    root.name = b'Root'
    if marker:
        extra = N.NiStringExtraData()
        extra.string_data = marker
        root.extra_data = extra

    def box(name, offset):
        shape = N.NiTriShape()
        shape.name = name
        data = N.NiTriShapeData()
        V = [(0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0)]
        data.num_vertices = 4
        data.has_vertices = True
        data.vertices.update_size()
        for v, p in zip(data.vertices, V):
            v.x, v.y, v.z = p[0] + offset, p[1], p[2]
        data.num_uv_sets = 1
        data.has_uv = True
        data.uv_sets.update_size()
        for uv, p in zip(data.uv_sets[0], V):
            uv.u, uv.v = p[0] / 8, p[1] / 8
        T = [(0, 1, 2), (0, 2, 3)]
        data.num_triangles = 2
        data.num_triangle_points = 6
        data.has_triangles = True
        data.triangles.update_size()
        for t, p in zip(data.triangles, T):
            t.v_1, t.v_2, t.v_3 = p
        shape.data = data
        return shape
    children = [box(name, 16 * i) for i, name in enumerate(shapes)]
    if collision:
        rcn = N.RootCollisionNode()
        rcn.num_children = collision
        rcn.children.update_size()
        for i in range(collision):
            rcn.children[i] = box(b'', 100 + 16 * i)
        children.append(rcn)
    if particles:
        p = N.NiAutoNormalParticles()
        p.name = b'Mist'
        children.append(p)
    root.num_children = len(children)
    root.children.update_size()
    for i, c in enumerate(children):
        root.children[i] = c
    d.roots = [root]
    stream = io.BytesIO()
    d.write(stream)
    return stream.getvalue()


class RuleTests(unittest.TestCase):
    def test_hidden_markers_follow_openmw(self):
        self.assertEqual(HIDDEN_MARKER_IDS, {'prisonmarker', 'divinemarker', 'templemarker', 'northmarker'})
        self.assertTrue(is_hidden_marker('NorthMarker'))
        self.assertFalse(is_hidden_marker('travelmarker'))
        self.assertFalse(is_hidden_marker(None))

    def test_marker_shape_needs_the_root_flag(self):
        self.assertTrue(is_marker_shape('Tri EditorMarker 0', True))
        self.assertTrue(is_marker_shape('tri editormarker_box_01', True))
        self.assertFalse(is_marker_shape('Tri EditorMarker 0', False))
        self.assertFalse(is_marker_shape('Tri seat19', True))

    def test_quick_byte_test(self):
        self.assertTrue(may_carry_marker(nif([b'Tri EditorMarker'])))
        self.assertFalse(may_carry_marker(nif([b'Tri hull'], marker=None)))
        self.assertTrue(may_carry_marker(b'xx' + MARKER_BYTES))


class GeometryTests(unittest.TestCase):
    def test_model_geometry_drops_marker_shapes_only(self):
        from prepare_scenery import model_geometry, nif_reader
        from mwad.scene import unpack_geometry
        N = nif_reader()
        packet, materials, _, skipped = model_geometry(nif([b'Tri EditorMarker', b'Tri hull']), N)
        self.assertEqual([m['source_shape'] for m in materials], ['Tri hull'])
        self.assertEqual(len(unpack_geometry(packet)[1]), 2)
        self.assertEqual([s['reason'] for s in skipped], ['editor_marker'])
        # without the root MRK the same name is an ordinary shape (OpenMW checks the flag)
        _, materials, _, _ = model_geometry(nif([b'Tri EditorMarker', b'Tri hull'], marker=b'sgoKeep'), N)
        self.assertEqual(len(materials), 2)

    def test_marker_only_model_names_itself(self):
        from prepare_scenery import EDITOR_MARKER_ONLY, model_geometry, nif_reader
        N = nif_reader()
        with self.assertRaises(ValueError) as caught:
            model_geometry(nif([b'Tri EditorMarker 0']), N)
        self.assertEqual(str(caught.exception), EDITOR_MARKER_ONLY)

    def test_marker_box_keeps_its_collision(self):
        from prepare_scenery import model_geometry, nif_reader
        from mwad.scene import unpack_geometry
        N = nif_reader()
        packet, _, _, _ = model_geometry(nif([b'Tri EditorMarker_box_01'], collision=1), N, collision=True)
        self.assertEqual(len(unpack_geometry(packet)[1]), 2)


class ClassifierTests(unittest.TestCase):
    def info(self, raw):
        from editor_markers import model_marker_info
        return model_marker_info(raw)

    def test_kinds(self):
        from editor_markers import marker_kind
        self.assertIsNone(self.info(nif([b'Tri hull'], marker=None)))
        sound = self.info(nif([b'Tri EditorMarker 0']))
        self.assertEqual(sound['drawn_shapes'], 0)
        self.assertEqual(marker_kind('sound_boat_creak00', 'ACTI', sound,
                                     'begin x\nPlayLoopSound3DVP "Boat Creak" 1.0 1.0\nend'), 'sound emitter')
        self.assertEqual(marker_kind('script_x', 'ACTI', sound, 'begin x\nend'), 'script marker')
        self.assertEqual(marker_kind('mist', 'ACTI', self.info(nif([b'Tri EditorMarker'], particles=True))),
                         'effect emitter')
        self.assertEqual(marker_kind('wall', 'STAT', self.info(nif([b'Tri EditorMarker_box_01'], collision=1))),
                         'collision marker')
        self.assertEqual(marker_kind('northmarker', 'STAT', None), 'hidden marker')
        # an MRK model that still draws something is an ordinary model with its marker shapes removed
        self.assertIsNone(marker_kind('boat', 'STAT', self.info(nif([b'Tri EditorMarker', b'Tri hull']))))

    def test_split_keeps_the_placement_as_a_record(self):
        from editor_markers import split_markers

        class Fake:
            def kind(self, ref):
                return {'sound_boat_hull00': 'sound emitter', 'northmarker': 'hidden marker'}.get(ref['id'].casefold())
        refs = [{'number': 465744, 'id': 'Sound_Boat_Hull00', 'position': [1, 2, 3]},
                {'number': 313081, 'id': 'Ex_longboat02', 'position': [4, 5, 6]},
                {'number': 7, 'id': 'NorthMarker', 'position': [0, 0, 0]}]
        kept, deferred = split_markers(refs, Fake())
        self.assertEqual([r['number'] for r in kept], [313081])
        self.assertEqual([(r['number'], r['editor_marker']) for r in deferred],
                         [(465744, 'sound emitter'), (7, 'hidden marker')])
        self.assertEqual(deferred[0]['position'], [1, 2, 3])
        self.assertTrue(deferred[0]['status'].startswith('editor marker (not drawn)'))


class EmitterTableTests(unittest.TestCase):
    def table(self):
        from editor_markers import emitter_row, emitter_table
        objects = {'sound_x': {'type': 'ACTI', 'model': 'EditorMarker.NIF', 'script': 'sound_x'},
                   'mist_x': {'type': 'ACTI', 'model': 'x\\mist.nif', 'script': ''}}
        scripts = {'sound_x': 'begin sound_x\nPlayLoopSound3DVP "Test Hum" 0.5 1.0\nend'}
        sounds = {'test hum': {'file': 'fx/hum.wav', 'volume': 200, 'min_range': 10, 'max_range': 120}}
        rows = [emitter_row({'number': 1, 'id': 'Sound_X', 'position': [1., 2., 3.]}, 'sound emitter',
                            objects['sound_x'], scripts, sounds, [0, 0], 'Test.esm'),
                emitter_row({'number': 2, 'id': 'Mist_X', 'position': [4., 5., 6.]}, 'effect emitter',
                            objects['mist_x'], scripts, sounds, 'Some Room', 'Test.esm')]
        return emitter_table(rows, 'synthetic')

    def test_rows_and_schema(self):
        from editor_markers import validate_emitters
        doc = self.table()
        self.assertEqual(doc['counts'], {'effect emitter': 1, 'sound emitter': 1})
        sound, mist = doc['emitters']
        self.assertEqual((sound['sound'], sound['sound_file'], sound['volume'], sound['min_range'], sound['max_range']),
                         ('Test Hum', 'fx/hum.wav', 200, 10, 120))
        self.assertEqual(mist['effect_mesh'], 'x/mist.nif')
        validate_emitters(json.loads(json.dumps(doc)))

    def test_schema_refuses_bad_rows(self):
        from editor_markers import validate_emitters
        for change in ({'kind': 'flying marker'}, {'position': [1, 2]}, {'reference': '1'}, {'volume': 300},
                       {'effect_mesh': None, 'kind': 'effect emitter'}):
            doc = self.table()
            doc['emitters'][0].update(change)
            doc['counts'] = {}
            from collections import Counter
            doc['counts'] = dict(sorted(Counter(r['kind'] for r in doc['emitters']).items()))
            with self.assertRaises(ValueError, msg=str(change)):
                validate_emitters(doc)
        doc = self.table()
        doc['counts'] = {'sound emitter': 2}
        with self.assertRaises(ValueError):
            validate_emitters(doc)


class BuiltCheckTests(unittest.TestCase):
    def test_check_built_finds_drawn_markers(self):
        from editor_markers import check_built
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            good = run / 'a' / 'scenery'
            good.mkdir(parents=True)
            index = {'models': [{'source': 'meshes/x/ex_longboat02.nif', 'materials': [{'source_shape': 'Tri hull'}]}],
                     'references': [{'number': 313081, 'id': 'Ex_longboat02', 'model_index': 0}]}
            (good / 'scenery-index.json').write_text(json.dumps(index))
            census = {'mrk_models': {'meshes/editormarker.nif': {'drawn_shapes': 0}}}
            self.assertEqual(check_built(run, census), (1, []))
            bad = run / 'b' / 'scenery'
            bad.mkdir(parents=True)
            index = {'models': [{'source': 'meshes/editormarker.nif',
                                 'materials': [{'source_shape': 'Tri EditorMarker 0'}]}],
                     'references': [{'number': 481808, 'id': 'sound_boat_creak00', 'model_index': 0, 'cell': [-9, 14]},
                                    {'number': 9, 'id': 'NorthMarker', 'model_index': 0}]}
            (bad / 'scenery-index.json').write_text(json.dumps(index))
            files, problems = check_built(run, census)
            self.assertEqual(files, 2)
            self.assertEqual(sorted(p['check'] for p in problems),
                             ['Tri EditorMarker shape kept in a converted model',
                              'editor marker placed in the drawn scenery', 'editor marker placed in the drawn scenery'])


    def test_require_none_drawn_stops_the_stage(self):
        from editor_markers import require_none_drawn

        class Fake:
            def kind(self, ref):
                return 'sound emitter' if ref['model'] == 'meshes/editormarker.nif' else None
        good = {'models': [{'source': 'meshes/x/ex_longboat02.nif', 'materials': [{'source_shape': 'Tri hull'}]}],
                'references': [{'number': 313081, 'id': 'Ex_longboat02', 'model_index': 0}]}
        self.assertEqual(require_none_drawn(good, Fake(), 'Khuul'), 1)
        bad = {'models': good['models'] + [{'source': 'meshes/editormarker.nif', 'materials': []}],
               'references': good['references'] + [{'number': 465744, 'id': 'Sound_Boat_Hull00', 'model_index': 1}]}
        with self.assertRaises(ValueError) as caught:
            require_none_drawn(bad, Fake(), 'Khuul')
        self.assertIn('465744', str(caught.exception))


class InputLayerTests(unittest.TestCase):
    def test_converters_use_the_shared_rule(self):
        import inspect
        import import_town
        from mwad.interior import omission_reason
        self.assertIn('data', inspect.signature(import_town.split_references).parameters)
        self.assertEqual(omission_reason({'number': 1, 'id': 'NorthMarker', 'type': 'STAT', 'model': 'x/plain.nif'}),
                         'editor marker')
        # the shared export drops hidden markers for every caller (v0.0.43-dev4), never converts them
        from prepare_scenery import drop_hidden_markers
        self.assertEqual(drop_hidden_markers([{'number': 5, 'id': 'PrisonMarker', 'model': 'marker_prison.nif'}]), [])
        source = (ROOT / 'tools' / 'survey_vvardenfell.py').read_text(encoding='utf-8')
        self.assertIn('EditorMarkers', source)


class SeydaInputTests(unittest.TestCase):
    def test_seyda_scenery_input_drops_hidden_markers(self):
        # v0.0.43-dev4 build: the Seyda scenery stage read its placements unfiltered and the guard refused
        # references 474482, 270728, 270729 (COLLISION-NC-FLAGS-32).
        from prepare_scenery import drop_hidden_markers
        refs = [{'id': 'NorthMarker', 'number': 1}, {'id': 'ex_common_house_01', 'number': 2}]
        self.assertEqual([r['number'] for r in drop_hidden_markers(refs)], [2])
        source = (ROOT / 'tools/prepare_scenery.py').read_text(encoding='utf-8')
        self.assertIn('refs = drop_hidden_markers(refs)', source)
        self.assertIn('dropped %d hidden editor marker(s)', source)


if __name__ == '__main__':
    unittest.main()
