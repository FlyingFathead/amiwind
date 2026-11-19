# SPDX-License-Identifier: GPL-3.0-only
"""tools/mesh_convert.py (MESH-EXPORT-FULL-67), on synthetic models only (no game file): units both ways (Morrowind,
Quake, any scale; the header names them and is read back), the round trip NIF -> OBJ -> the builder's mesh form within
1e-5 in either unit, the texture V and winding conventions, OBJ input (fans, negative indices, materials), the
AmiWind side (a BSP29-shaped map model, a Quake alias model), record ids through the merged masters, and the
refusals."""
import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))          # src before tools (TEST-WORKER-SYSPATH-32)

import mesh_convert as C  # noqa: E402

try:
    import numpy as np
except ImportError:
    np = None


def pyffi_ready():
    try:
        from prepare_scenery import nif_reader
        nif_reader()
        return np is not None
    except Exception:  # noqa: BLE001 - the NIF library is not in every environment
        return False


# a box of awkward sizes (Morrowind units, float32-exact values), two triangles per side, outward (counter-clockwise)
X, Y, Z = (-12.5, 37.25), (3.125, 41.0), (0.0, 77.75)
BOX = [(x, y, z) for x in X for y in Y for z in Z]
UV = [((i % 4) / 4.0 + 0.125, (i // 4) / 2.0 + 0.0625) for i in range(8)]
TRIS = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
        (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]


def box_nif():
    """A synthetic NIF of the box: one shape, one texture (the builder's own NIF library writes it)."""
    from prepare_scenery import nif_reader
    N = nif_reader()
    data = N.Data(version=0x04000002)
    root = N.NiNode()
    root.name = b'Synthetic root'
    data.roots = [root]
    shape = N.NiTriShape()
    shape.name = b'Synthetic box'
    root.add_child(shape)
    g = N.NiTriShapeData()
    shape.data = g
    g.num_vertices = len(BOX)
    g.has_vertices = True
    g.vertices.update_size()
    for target, xyz in zip(g.vertices, BOX):
        target.x, target.y, target.z = xyz
    g.num_uv_sets = 1
    g.has_uv = True
    g.uv_sets.update_size()
    for target, coords in zip(g.uv_sets[0], UV):
        target.u, target.v = coords
    g.num_triangles = len(TRIS)
    g.num_triangle_points = 3 * len(TRIS)
    g.triangles.update_size()
    for target, (a, b, c) in zip(g.triangles, TRIS):
        target.v_1, target.v_2, target.v_3 = a, b, c
    texture = N.NiSourceTexture()
    texture.use_external = 1
    texture.file_name = b'Textures\\Tx_Synthetic.TGA'
    prop = N.NiTexturingProperty()
    prop.has_base_texture = True
    prop.base_texture.source = texture
    shape.add_property(prop)
    buffer = io.BytesIO()
    data.write(buffer)
    return buffer.getvalue()


def corners(mesh):
    """[(x y z u v of each corner)] of every triangle, in face order."""
    v, f = mesh['vertices'], mesh['faces']
    return np.array([[v[i] for i in face[:3]] for face in f])


class UnitTests(unittest.TestCase):
    def test_units_and_scales(self):
        self.assertEqual(C.scale_of('quake'), ('quake', 0.25))
        self.assertEqual(C.scale_of('morrowind'), ('morrowind', 1.0))
        self.assertEqual(C.scale_of(scale=0.25), ('quake', 0.25))
        self.assertEqual(C.scale_of(scale=2.54), ('scaled', 2.54))
        self.assertEqual(C.scale_of(), (None, None))
        for bad in ({'units': 'feet'}, {'units': 'quake', 'scale': 1.0}, {'scale': 0.0}, {'scale': -1.0}):
            with self.assertRaises(C.ConvertError, msg=bad):
                C.scale_of(**bad)

    def test_forms(self):
        self.assertEqual(C.form_of('meshes/l/light_com_lantern_02.nif'), 'game')
        self.assertEqual(C.form_of('light_com_lantern_02'), 'record')
        for name, form in (('a.obj', 'obj'), ('x/b.BSP', 'bsp'), ('c.chim', 'bsp'), ('d.mdl', 'mdl'), ('e.mwg', 'mwg')):
            self.assertEqual(C.form_of(name), form)
        with self.assertRaises(C.ConvertError):
            C.form_of('notes.txt')

    def test_record_ids_through_the_merged_masters(self):
        masters = {'Morrowind.esm': {'objects': {'lamp': {'type': 'LIGH', 'model': 'meshes/l/a.nif'},
                                                 'rock': {'type': 'STAT', 'model': 'meshes/r/x.nif'},
                                                 'idea': {'type': 'MISC', 'model': ''}}},
                   'Tribunal.esm': {'objects': {'lamp': {'type': 'LIGH', 'model': 'meshes/l/b.nif'},
                                                'rock': {'type': 'STAT', 'model': 'meshes/r/x.nif', 'deleted': True}}}}
        self.assertEqual(C.model_of_record(masters, 'Lamp'), 'meshes/l/b.nif')        # the later master wins
        for record in ('rock', 'idea', 'nothing'):
            with self.assertRaises(C.ConvertError, msg=record):
                C.model_of_record(masters, record)


@unittest.skipUnless(pyffi_ready(), 'the NIF library or numpy is unavailable')
class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.nif = self.dir / 'box.nif'
        self.nif.write_bytes(box_nif())
        self.source = C.from_nif(self.nif.read_bytes(), 'box.nif')

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_reader_is_the_builders(self):
        np.testing.assert_allclose(self.source['vertices'][:, :3], np.array(BOX), atol=1e-6)
        np.testing.assert_allclose(self.source['vertices'][:, 3:5], np.array(UV), atol=1e-6)
        self.assertEqual([tuple(f[:3]) for f in self.source['faces']], TRIS)
        self.assertEqual(self.source['materials'], [{'name': 'm0', 'texture': 'Tx_Synthetic.TGA'}])

    def test_nif_to_obj_to_the_builders_form_in_either_unit(self):
        for units, scale in (('morrowind', 1.0), ('quake', 0.25), (None, 2.5)):
            obj = self.dir / ('box-%s.obj' % (units or 'scaled'))
            rec = C.convert(str(self.nif), obj, units=units, scale=None if units else scale)
            self.assertEqual((rec['triangles'], rec['units']), (12, units or 'scaled'))
            text = obj.read_text()
            self.assertIn('%s format=1 units=%s scale=%s up=z v=up winding=ccw' % (
                C.HEADER, units or 'scaled', C._num(scale, 12)), text)
            # the OBJ itself: positions at the scale, V counted from the bottom
            v = np.array([[float(x) for x in l.split()[1:]] for l in text.splitlines() if l.startswith('v ')])
            vt = np.array([[float(x) for x in l.split()[1:]] for l in text.splitlines() if l.startswith('vt ')])
            np.testing.assert_allclose(v, self.source['vertices'][:, :3] * scale, atol=1e-5)
            np.testing.assert_allclose(vt[:, 1], 1.0 - self.source['vertices'][:, 4], atol=1e-6)
            self.assertIn('map_Kd Tx_Synthetic.TGA', obj.with_suffix('.mtl').read_text())
            # back: the header says the units, so nothing is given by hand
            back = C.from_obj(obj)
            mwg = obj.with_suffix('.mwg')
            C.convert(str(obj), mwg)
            form = C.from_mwg(mwg)
            for mesh in (back, form):
                got, want = corners(mesh), corners(self.source)
                np.testing.assert_allclose(got[..., :3], want[..., :3], atol=1e-5)          # Morrowind units
                np.testing.assert_allclose(got[..., :3] * scale, want[..., :3] * scale, atol=1e-5)
                np.testing.assert_allclose(got[..., 3:5], want[..., 3:5], atol=1e-6)
                self.assertEqual(mesh['materials'][0]['texture'], 'Tx_Synthetic.TGA')
            # and out again: the same OBJ, byte for byte
            again = self.dir / ('again-%s.obj' % (units or 'scaled'))
            C.convert(str(mwg), again, units=units, scale=None if units else scale)
            body = lambda t: [l for l in t.splitlines() if not l.startswith(('# AmiWind mesh:', 'mtllib'))]  # noqa: E731
            self.assertEqual(body(again.read_text()), body(text))                       # all but the names

    def test_the_same_convention_as_the_lantern_rebuild(self):
        # tools/lantern_rebuild.py converts the builder's form to its recipe frame (Quake units, OBJ texture V) at one
        # place: this converter's Quake OBJ is that frame
        import lantern_rebuild
        points, uvs = lantern_rebuild.to_recipe_frame(self.source['vertices'])
        obj = self.dir / 'q.obj'
        C.convert(str(self.nif), obj, units='quake')
        lines = obj.read_text().splitlines()
        v = np.array([[float(x) for x in l.split()[1:]] for l in lines if l.startswith('v ')])
        vt = np.array([[float(x) for x in l.split()[1:]] for l in lines if l.startswith('vt ')])
        np.testing.assert_allclose(v, points, atol=1e-5)
        np.testing.assert_allclose(vt, uvs, atol=1e-6)

    def test_textures_beside_the_obj_named_by_the_game_texture(self):
        from PIL import Image
        data = self.dir / 'Data Files'
        (data / 'Textures').mkdir(parents=True)
        Image.new('RGB', (4, 2), (200, 100, 50)).save(data / 'Textures' / 'tx_synthetic.tga')    # a loose texture
        out = self.dir / 'pictures' / 'box.obj'
        rec = C.convert(str(self.nif), out, data_files=str(data), units='quake', textures=True)
        self.assertEqual(rec['missing'], [])
        self.assertIn('tx_synthetic.png', rec['files'])                 # the texture's own stem: brought back, it
        self.assertIn('map_Kd tx_synthetic.png', out.with_suffix('.mtl').read_text())   # still names the game's
        with Image.open(out.parent / 'tx_synthetic.png') as picture:
            self.assertEqual(picture.size, (4, 2))
        self.assertTrue((out.parent / 'box.PRIVATE.txt').is_file())
        self.assertIn('# private: made from your own game files', out.read_text())

    def test_faces_stay_counter_clockwise_seen_from_outside(self):
        obj = self.dir / 'w.obj'
        C.convert(str(self.nif), obj)
        mesh = C.from_obj(obj)
        centre = np.array(BOX).mean(axis=0)
        for p in corners(mesh)[..., :3]:
            n = np.cross(p[1] - p[0], p[2] - p[0])
            self.assertGreater(float(n @ (p.mean(axis=0) - centre)), 0)

    def test_refusals(self):
        obj = self.dir / 'r.obj'
        C.convert(str(self.nif), obj)
        cases = [
            (lambda: C.convert(str(self.nif), obj), 'exists'),
            (lambda: C.convert(str(self.nif), self.dir / 'r.mwg', units='quake'), 'Morrowind units'),
            (lambda: C.convert(str(self.nif), self.dir / 's.mwg', textures=True), 'beside an OBJ'),
            (lambda: C.convert(str(self.nif), self.dir / 't.obj', in_units='quake'), 'do not apply'),
            (lambda: C.convert(str(self.nif), self.dir / 'u.ply'), '.obj'),
            (lambda: C.convert('meshes/x/box.nif', self.dir / 'v.obj'), '--data-files'),
            (lambda: C.convert(str(obj), self.dir / 'w.mwg', in_units='quake'), 'says its units'),
            (lambda: C.convert(str(self.nif), self.dir / 'x.obj', textures=True), '--data-files'),
        ]
        for call, words in cases:
            with self.assertRaises(C.ConvertError) as caught:
                call()
            self.assertIn(words, str(caught.exception))
        out = io.StringIO()
        with contextlib.redirect_stderr(out):
            self.assertEqual(C.main([str(self.nif), str(obj)]), 2)
        self.assertIn('exists', out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(C.main([str(self.nif), str(obj), '--overwrite', '--units', 'quake']), 0)


@unittest.skipUnless(np is not None, 'numpy unavailable')
class ObjInputTests(unittest.TestCase):
    QUAD = ('mtllib q.mtl\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n'
            'usemtl stone\nf 1/1 2/2 3/3 4/4\nusemtl wood\nf -4/-4 -2/-2 -1/-1\n')

    def test_a_hand_made_obj(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = Path(tmp) / 'q.obj'
            obj.write_text(self.QUAD)
            (Path(tmp) / 'q.mtl').write_text('newmtl wood\nmap_Kd wood.png\nnewmtl stone\nKd 1 1 1\nmap_Kd -s 1 1 1 stone.dds\n')
            with self.assertRaisesRegex(C.ConvertError, 'does not say its units'):
                C.from_obj(obj)
            mesh = C.from_obj(obj, in_scale=0.25)                       # a hand-made model in Quake units
        np.testing.assert_allclose(mesh['vertices'][:, :3].max(axis=0), [4, 4, 0])
        self.assertEqual(len(mesh['faces']), 3)                         # the quad fanned into two, then the triangle
        self.assertEqual([m['name'] for m in mesh['materials']], ['wood', 'stone'])     # the MTL's order
        self.assertEqual([m['texture'] for m in mesh['materials']], ['wood.png', 'stone.dds'])
        self.assertEqual([int(f[3]) for f in mesh['faces']], [1, 1, 0])
        np.testing.assert_allclose(sorted(set(mesh['vertices'][:, 4])), [0.0, 1.0])  # V from the top again

    def test_a_broken_index_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = Path(tmp) / 'b.obj'
            obj.write_text('v 0 0 0\nv 1 0 0\nf 1 2 3\n')
            with self.assertRaisesRegex(C.ConvertError, 'line 3'):
                C.from_obj(obj, in_scale=1.0)


def bsp29(path):
    """A BSP29 map with one model: one 16 x 16 quad at z = 8, clockwise seen from above (the engine's front), on a
    64 x 32 texture with s = x, t = y."""
    verts = [(0, 0, 8), (0, 16, 8), (16, 16, 8), (16, 0, 8)]
    edges = [(0, 0), (0, 1), (1, 2), (2, 3), (3, 0)]
    lumps = [b''] * 15
    lumps[1] = struct.pack('<4fi', 0, 0, 1, 8, 2)
    miptex = b'tx_test'.ljust(16, b'\0') + struct.pack('<II4I', 64, 32, 0, 0, 0, 0)
    lumps[2] = struct.pack('<ii', 1, 8) + miptex
    lumps[3] = b''.join(struct.pack('<3f', *p) for p in verts)
    lumps[6] = struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0)
    lumps[7] = struct.pack('<HhihH4Bi', 0, 0, 0, 4, 0, 0, 0, 0, 0, -1)
    lumps[12] = b''.join(struct.pack('<2H', *e) for e in edges)
    lumps[13] = struct.pack('<4i', 1, 2, 3, 4)
    lumps[14] = struct.pack('<9f7i', 0, 0, 8, 16, 16, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
    out, at = bytearray(), 4 + 8 * 15
    directory = []
    for lump in lumps:
        directory.append((at, len(lump)))
        out += lump
        at += len(lump)
    path.write_bytes(struct.pack('<i', 29) + b''.join(struct.pack('<ii', *d) for d in directory) + bytes(out))


def alias_model(path):
    """A Quake alias model: one 4 x 4 skin, three vertices, one triangle clockwise seen from +z (the engine's front),
    one frame; scale 1, origin (0, 0, 0)."""
    head = struct.pack('<4si3f3ff3f8if', b'IDPO', 6, 1, 1, 1, 0, 0, 0, 10, 0, 0, 0, 1, 4, 4, 3, 1, 1, 0, 0, 1.0)
    skin = struct.pack('<i', 0) + bytes(16)
    st = struct.pack('<3i', 0, 0, 0) + struct.pack('<3i', 0, 2, 0) + struct.pack('<3i', 0, 0, 2)
    tri = struct.pack('<4i', 1, 0, 2, 1)
    frame = struct.pack('<i4B4B16s', 0, 0, 0, 0, 0, 8, 8, 0, 0, b'pose') + bytes((0, 0, 0, 0, 8, 0, 0, 0, 0, 8, 0, 0))
    path.write_bytes(head + skin + st + tri + frame)


@unittest.skipUnless(np is not None, 'numpy unavailable')
class AmiWindSideTests(unittest.TestCase):
    def test_a_map_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            bsp = Path(tmp) / 'room.bsp'
            bsp29(bsp)
            mesh = C.from_bsp(bsp)
            with self.assertRaisesRegex(C.ConvertError, 'models'):
                C.from_bsp(bsp, model=3)
            out = Path(tmp) / 'room.obj'
            rec = C.convert(str(bsp), out, units='quake')
        self.assertEqual((rec['form'], rec['triangles']), ('bsp', 2))
        np.testing.assert_allclose(mesh['vertices'][:, :3].max(axis=0), [64, 64, 32])   # Quake units x 4
        for p in corners(mesh)[..., :3]:
            self.assertGreater(np.cross(p[1] - p[0], p[2] - p[0])[2], 0)               # turned: facing +z
        uv = {tuple(np.round(r[:2] * 0.25, 3)): tuple(r[3:5]) for r in mesh['vertices']}
        self.assertEqual(uv[(16.0, 16.0)], (0.25, 0.5))                                   # s / 64, t / 32
        self.assertEqual(mesh['materials'], [{'name': 'tx_test', 'texture': 'tx_test'}])

    def test_an_alias_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            mdl = Path(tmp) / 'npc.mdl'
            alias_model(mdl)
            mesh = C.from_mdl(mdl)
            with self.assertRaisesRegex(C.ConvertError, 'frames'):
                C.from_mdl(mdl, frame=2)
            (Path(tmp) / 'bad.mdl').write_bytes(b'IDPO')
            with self.assertRaisesRegex(C.ConvertError, 'alias model'):
                C.from_mdl(Path(tmp) / 'bad.mdl')
        np.testing.assert_allclose(mesh['vertices'][:, :3].max(axis=0), [32, 32, 0])    # Quake units x 4
        p = corners(mesh)[0][..., :3]
        self.assertGreater(np.cross(p[1] - p[0], p[2] - p[0])[2], 0)                     # turned: facing +z
        np.testing.assert_allclose(sorted(set(mesh['vertices'][:, 3])), [0.125, 0.625])  # (s + 0.5) / 4


if __name__ == '__main__':
    unittest.main()
