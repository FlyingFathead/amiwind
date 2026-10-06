"""Temple merged-face planes remain stable without changing other maps."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from player_hull import pack_lumps
from prepare_mesh_bsp import append_meshes
from prepare_scenery import reference_rotation


def assemble(root, identity, polygon=None, rotation=(0, 0, 0), scale=1):
    # A merged floor can retain three nearly collinear leading vertices.
    # Their tiny height error must not turn its plane into a vertical wall.
    if polygon is None:
        polygon = np.array([[0., 0, 0], [64, 0, 0], [128, 0, .000001],
                            [128, 64, 0], [0, 64, 0]])
    axes = np.array([[1/128, 0], [0, 1/128], [0, 0.]])
    data = (np.column_stack((polygon * 4, np.zeros((len(polygon), 2)))),
            np.array([[0, 1, 3, 0]]),
            [(polygon, 0, axes, np.zeros(2), np.array([0., 0, 1]))], [], {})
    ref = dict(number=1, model_index=0, scale=scale, position=[0, 0, 0],
               rotation_radians=list(rotation))
    model = dict(source='synthetic-floor.nif', triangles=3,
                 materials=[dict(texture_index=None, diffuse=[1, 1, 1])])
    (root / 'scenery-index.json').write_text(json.dumps(dict(
        cell='Synthetic interior', models=[model], textures=[], references=[ref])))
    (root / 'scenery.mwpak').write_bytes(b'')
    (root / 'palette.lmp').write_bytes(bytes(range(256)) * 3)
    sections = [b''] * 15
    sections[0] = b'{\n"classname" "worldspawn"\n}\n\0'
    sections[2] = struct.pack('<i', 0)
    sections[10] = struct.pack('<i', -1) + bytes(24)
    sections[14] = bytes(64)
    (root / 'base.bsp').write_bytes(pack_lumps(sections))
    # Deliberately use this filename for all identities: basename inference
    # must not silently enable the map-specific repair.
    output = root / 'bmtemple.bsp'
    append_meshes(root / 'base.bsp', output, root, root / 'palette.lmp',
                  centre=(0, 0), jobs=1, references=[1], prepared_models={0: data},
                  map_identity=identity)
    return output.read_bytes()


def face(raw):
    lumps = [raw[o:o+n] for o, n in struct.iter_unpack('<ii', raw[4:124])]
    record, = struct.iter_unpack('<Hhihh4Bi', lumps[7])
    n = np.array(struct.unpack_from('<4fi', lumps[1], record[0] * 20)[:4])
    vertices = np.array(list(struct.iter_unpack('<3f', lumps[3])))
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    indices = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    points = np.array([vertices[edges[k][0] if k >= 0 else edges[-k][1]]
                       for k in indices[record[2]:record[2]+record[3]]])
    return n, points, lumps


class TempleFacePlaneTests(unittest.TestCase):
    def test_room_builder_explicitly_selects_only_temple(self):
        from unittest.mock import patch
        from prepare_area import build_room
        cell = dict(name='Synthetic interior', lighting={}, refs=[],
                    entrances=[dict(destination=dict(position=[0, 0, 0],
                                                     rotation_radians=[0, 0, 0]))])
        ref = dict(number=1, model='i/synthetic-floor.nif', bounds=[[0, 0, 0], [512, 256, 4]])
        def export(data, parts, *args, **kwargs):
            parts.mkdir()
            (parts/'scenery-index.json').write_text(json.dumps(dict(errors=[], references=[ref])))
        def compile_room(command, cwd, **kwargs):
            (cwd/'room.bsp').write_bytes(b'compiler boundary fixture')
        class ReachedAssembly(Exception):
            pass
        for slug, expected in (('bmtemple', 'bmtemple'), ('census', None)):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'Morrowind.esm').write_bytes(b'')
                (root/'id1/gfx').mkdir(parents=True)
                (root/'id1/gfx/palette.lmp').write_bytes(bytes(range(256))*3)
                with patch('prepare_area.read_interior', return_value=cell), \
                     patch('prepare_area.select_geometry', return_value=([ref], [])), \
                     patch('prepare_area.export_refs', side_effect=export), \
                     patch('prepare_area.subprocess.run', side_effect=compile_room), \
                     patch('prepare_area.rebuild_world_hull'), \
                     patch('prepare_area.append_meshes', side_effect=ReachedAssembly) as assembly:
                    with self.assertRaises(ReachedAssembly):
                        build_room((root, root, dict(map=slug, cell=cell['name']),
                                    'qbsp', 'vis', 'light', ''))
                    self.assertEqual(assembly.call_args.kwargs.get('map_identity'), expected)

    def test_merged_floor_serialized_plane_contains_all_vertices(self):
        with tempfile.TemporaryDirectory() as directory:
            n, points, _ = face(assemble(Path(directory), 'bmtemple'))
        self.assertLess(float(np.max(np.abs(points @ n[:3] - n[3]))), .00001)
        self.assertGreater(n[2], .99999)
        self.assertEqual(len(points), 5)

    def test_nonplanar_polygon_is_rejected_before_output(self):
        polygon = np.array([[0., 0, 0], [128, 0, 0], [128, 64, 2], [0, 64, 0]])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'Nonplanar'):
                assemble(root, 'bmtemple', polygon)
            self.assertFalse((root / 'bmtemple.bsp').exists())

    def test_explicit_temple_gate_preserves_other_map_bytes(self):
        # Filled from the frozen pre-repair serializer; compares whole output,
        # including vertex order, UVs, planes, entities and collision records.
        expected = 'afdb39f87b430207184f39281115d62d3c6769613ffc3918c9cfe1d884f74252'
        for identity in (None, 'census', 'other', 'BmTemple'):
            with self.subTest(identity=identity), tempfile.TemporaryDirectory() as directory:
                raw = assemble(Path(directory), identity)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)

    def test_tilt_scale_winding_and_uv_mapping_are_retained(self):
        rotation = (.35, -.2, .7)
        with tempfile.TemporaryDirectory() as directory:
            n, points, lumps = face(assemble(Path(directory), 'bmtemple',
                                            rotation=rotation, scale=2))
        self.assertLess(float(np.max(np.abs(points @ n[:3] - n[3]))), .00005)
        # Compose the inline model yaw with its inverse bake.
        co, si = np.cos(-rotation[2]), np.sin(-rotation[2])
        yaw = np.array([[co, -si, 0], [si, co, 0], [0, 0, 1]])
        np.testing.assert_allclose(yaw @ n[:3],
                                   reference_rotation(dict(rotation_radians=rotation)) @ [0, 0, 1],
                                   atol=.000001)
        # BSP writer reverses each surface winding. Full-polygon area remains
        # opposite the outward plane, matching the existing renderer contract.
        area = np.cross(points - points[0], np.roll(points, -1, axis=0) - points[0]).sum(axis=0)
        self.assertLess(float(area @ n[:3]), 0)
        tex = struct.unpack_from('<8fii', lumps[6])
        uv = points @ np.array([tex[:3], tex[4:7]]).T + [tex[3], tex[7]]
        np.testing.assert_allclose(np.sort(uv, axis=0),
                                   [[0, 0], [0, 0], [32, 0], [64, 32], [64, 32]], atol=.00001)
