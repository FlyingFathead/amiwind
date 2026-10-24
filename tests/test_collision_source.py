# SPDX-License-Identifier: GPL-3.0-only
"""One collision-source rule for every mesh converter (COLLISION-RCN-SCOPE-32, COLLISION-NC-FLAGS-32); synthetic NIFs.

The rule (tools/collision_source.py, from OpenMW 0.51 bulletnifloader.cpp): the root RootCollisionNode when present,
else the drawn triangles; NC* and NCC nonsolid for the player; MRK marker shapes and AvoidNode subtrees never collide;
an empty root RootCollisionNode is nonsolid. AMIWIND_COLLISION_SOURCE=profile keeps the rule before for A/B.
"""
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

READY = all(importlib.util.find_spec(m) for m in ('numpy', 'pyffi'))
QUAD = ([(0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0)], [(0, 1, 2), (0, 2, 3)])


def shape(N, name, mesh=QUAD, offset=0.):
    vertices, triangles = mesh
    s = N.NiTriShape()
    s.name = name
    data = N.NiTriShapeData()
    data.num_vertices = len(vertices)
    data.has_vertices = True
    data.vertices.update_size()
    for v, p in zip(data.vertices, vertices):
        v.x, v.y, v.z = p[0] + offset, p[1], p[2]
    data.num_uv_sets = 1
    data.has_uv = True
    data.uv_sets.update_size()
    for uv, p in zip(data.uv_sets[0], vertices):
        uv.u, uv.v = p[0] / 8., p[1] / 8.
    data.num_triangles = len(triangles)
    data.num_triangle_points = 3 * len(triangles)
    data.has_triangles = True
    data.triangles.update_size()
    for t, p in zip(data.triangles, triangles):
        t.v_1, t.v_2, t.v_3 = p
    s.data = data
    return s


def node(N, kind, name, children):
    n = getattr(N, kind)()
    n.name = name
    n.num_children = len(children)
    n.children.update_size()
    for i, c in enumerate(children):
        n.children[i] = c
    return n


def nif(build, string=None):
    """A synthetic TES3 NIF: build(N) gives the root's children; optional root NiStringExtraData."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    d = N.Data(version=0x04000002)
    root = node(N, 'NiNode', b'Root', build(N))
    if string is not None:
        extra = N.NiStringExtraData()
        extra.string_data = string
        root.extra_data = extra
    d.roots = [root]
    stream = io.BytesIO()
    d.write(stream)
    return stream.getvalue()


def drawn(N):
    return [shape(N, b'Tri drawn')]


def with_rcn(N):
    return [shape(N, b'Tri drawn'), node(N, 'RootCollisionNode', b'RootCollisionNode',
                                         [shape(N, b'Tri coll', offset=100.)])]


def deep_rcn(N):
    return [shape(N, b'Tri drawn'), node(N, 'NiNode', b'Group', [
        node(N, 'RootCollisionNode', b'RootCollisionNode', [shape(N, b'Tri coll', offset=100.)])])]


def empty_rcn(N):
    return [shape(N, b'Tri drawn'), node(N, 'RootCollisionNode', b'RootCollisionNode', [])]


def with_avoid(N):
    return [shape(N, b'Tri drawn'), node(N, 'AvoidNode', b'AvoidNode', [shape(N, b'Tri avoid', offset=50.)])]


def rcn_with_avoid(N):
    return [shape(N, b'Tri drawn'), node(N, 'RootCollisionNode', b'RootCollisionNode', [
        shape(N, b'Tri coll', offset=100.), node(N, 'AvoidNode', b'AvoidNode', [shape(N, b'Tri avoid', offset=50.)])])]


def marker_rcn(N):
    return [shape(N, b'Tri drawn'), node(N, 'RootCollisionNode', b'RootCollisionNode',
                                         [shape(N, b'Tri EditorMarker', offset=100.)])]


@unittest.skipUnless(READY, 'numpy and PyFFI required')
class RuleTests(unittest.TestCase):
    def setUp(self):
        from prepare_scenery import nif_reader
        self.N = nif_reader()
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop('AMIWIND_COLLISION_SOURCE', None)

    def tearDown(self):
        self.env.stop()

    def collide(self, raw, collision='root_node_or_visual'):
        from collision_source import model_collision
        from mwad.scene import unpack_geometry
        source, result, _ = model_collision(raw, self.N, collision)
        if result is None:
            return source, None
        v, f, _ = unpack_geometry(result[0])
        return source, (round(min(x[0] for x in v)), [m['source_shape'] for m in result[1]], len(f))

    def meta(self, raw):
        from prepare_scenery import source_collision_metadata
        return source_collision_metadata(raw, self.N)

    def test_default_is_the_authored_rule(self):
        from collision_source_env import collision_source_mode
        self.assertEqual(collision_source_mode(), 'authored')
        with patch.dict(os.environ, {'AMIWIND_COLLISION_SOURCE': 'nope'}):
            with self.assertRaises(ValueError):
                collision_source_mode()

    def test_root_rcn_is_the_collision(self):
        source, got = self.collide(nif(with_rcn))
        self.assertEqual(source, 'rcn')
        self.assertEqual(got[1:], (['Tri coll'], 2))
        self.assertEqual(got[0], 100)

    def test_no_rcn_means_the_drawn_triangles(self):
        self.assertEqual(self.collide(nif(drawn)), ('visual', None))

    def test_rcn_below_the_root_does_not_count(self):
        # OpenMW: a RootCollisionNode deeper in an autogenerated mesh is a plain node (the Dagoth bridges)
        self.assertEqual(self.collide(nif(deep_rcn)), ('visual', None))

    def test_strict_root_node_needs_a_root_rcn(self):
        with self.assertRaises(ValueError):
            self.collide(nif(deep_rcn), 'root_node')
        self.assertEqual(self.collide(nif(with_rcn), 'root_node')[0], 'rcn')

    def test_empty_root_rcn_is_nonsolid(self):
        self.assertEqual(self.collide(nif(empty_rcn))[0], 'none')
        meta = self.meta(nif(empty_rcn))
        self.assertEqual(meta['mode'], 'nonsolid')
        self.assertIn('empty', meta['reason'])
        # editor-marker shapes under it do not count (MRK)
        self.assertEqual(self.meta(nif(marker_rcn, b'MRK'))['mode'], 'nonsolid')

    def test_nc_and_ncc_are_nonsolid(self):
        for string, kind in ((b'NCO', 'NC'), (b'NC', 'NC'), (b'nco', 'NC'), (b'NCC', 'NCC'), (b'NCCamera', 'NCC')):
            with self.subTest(string=string):
                meta = self.meta(nif(drawn, string))
                self.assertEqual(meta['mode'], 'nonsolid')
                self.assertEqual(meta['no_collision_markers'], [string.decode()])
                self.assertEqual(self.collide(nif(drawn, string))[0], 'none')
        from collision_source import string_flags
        self.assertEqual(string_flags(['NCC'])[0], 'NCC')
        self.assertEqual(string_flags(['Ncc'])[0], 'NC')       # NCC needs an upper-case third letter (OpenMW)
        self.assertEqual(string_flags(['MRK', 'sgoKeep'])[0], None)
        self.assertEqual(self.meta(nif(drawn, b'MRK'))['mode'], 'unchanged')

    def test_avoid_node_never_collides(self):
        source, got = self.collide(nif(with_avoid))
        # the drawn shape's two triangles only (x from 0), the AvoidNode subtree's (x from 50) left out
        self.assertEqual((source, got[0], got[2]), ('visual', 0, 2))
        source, got = self.collide(nif(rcn_with_avoid))
        self.assertEqual((source, got[0], got[2]), ('rcn', 100, 2))

    def test_mrk_marker_shapes_never_collide(self):
        from mwad.scene import unpack_geometry
        from prepare_scenery import model_geometry
        packet, materials, _, _ = model_geometry(nif(lambda N: [shape(N, b'Tri EditorMarker'), shape(N, b'Tri hull')],
                                                     b'MRK'), self.N)
        self.assertEqual([m['source_shape'] for m in materials], ['Tri hull'])
        self.assertEqual(len(unpack_geometry(packet)[1]), 2)

    def test_profile_rule_is_kept_for_ab(self):
        from collision_source import export_collision
        with patch.dict(os.environ, {'AMIWIND_COLLISION_SOURCE': 'profile'}):
            self.assertEqual(self.meta(nif(drawn, b'NCC'))['mode'], 'unchanged')     # NCC was solid
            self.assertEqual(self.meta(nif(drawn, b'NCO'))['mode'], 'nonsolid')
            self.assertIsNone(export_collision(None))                                   # visual unless opted in
            self.assertEqual(export_collision('root_node_or_visual'), 'root_node_or_visual')
        self.assertEqual(export_collision(None), 'root_node_or_visual')                 # the rule: every model
        self.assertEqual(export_collision('root_node'), 'root_node')
        self.assertIsNone(export_collision('visual'))


@unittest.skipUnless(READY, 'numpy and PyFFI required')
class ExportTests(unittest.TestCase):
    """prepare_scenery._read_model, the reader every converter's export uses (export_refs)."""

    def read(self, raw, collision):
        from prepare_scenery import _read_model
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'model.bin'
            path.write_bytes(b'pad' + raw)
            return _read_model(('meshes/x/test.nif', str(path), {'offset': 3, 'bytes': len(raw)}, collision))

    def test_every_model_reads_its_rcn_by_default(self):
        from collision_source import export_collision
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_COLLISION_SOURCE', None)
            # a room's furniture or x/ piece had no collision_source in its profile: now the rule applies
            name, raw, result, collision, error = self.read(nif(with_rcn), export_collision(None))
            self.assertIsNone(error)
            self.assertIsNotNone(collision)
            self.assertTrue(all(m['source_visibility']['collision_node'] for m in collision[1]))
        with patch.dict(os.environ, {'AMIWIND_COLLISION_SOURCE': 'profile'}):
            # the rule before: no profile opt-in, no RootCollisionNode read (the drawn triangles collide)
            _, _, _, collision, error = self.read(nif(with_rcn), export_collision(None))
            self.assertIsNone(error)
            self.assertIsNone(collision)

    def test_report_row(self):
        from prepare_scenery import collision_source_row, collision_source_report
        rows = {'a': collision_source_row({'collision': {'source': 'NIF RootCollisionNode'},
                                           'source_collision': {'mode': 'unchanged', 'no_collision_markers': []}}),
                'b': collision_source_row({'collision': None,
                                           'source_collision': {'mode': 'nonsolid', 'no_collision_markers': ['NCC']}}),
                'c': collision_source_row({'collision': None, 'source_collision': {'mode': 'unchanged'}})}
        self.assertEqual([rows[k]['source'] for k in 'abc'], ['rcn', 'none', 'visual'])
        self.assertEqual(rows['b']['markers'], ['NCC'])
        self.assertEqual(collision_source_report(rows)['counts'], {'none': 1, 'rcn': 1, 'visual': 1})


class ConverterScopeTests(unittest.TestCase):
    """No converter limits the source to meshes/i/ any more: the export's default is the rule."""

    def test_room_profiles_leave_the_source_to_the_rule(self):
        from collision_source import export_collision
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_COLLISION_SOURCE', None)
            # interior_visual_profile gives None for furniture, doors, lights and x/ pieces in rooms
            self.assertEqual(export_collision(None), 'root_node_or_visual')

    def test_source_receipt_names_the_rule(self):
        text = (ROOT / 'tools/import_town.py').read_text(encoding='utf-8')
        self.assertIn("'collision_source': collision_source_receipt()", text)


if __name__ == '__main__':
    unittest.main()
