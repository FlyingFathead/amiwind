# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic original-record/mesh/staging boundary tests; no game assets."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from mwad.scene import pack_geometry
from player_hull import lumps, pack_lumps
from prepare_harvest import source_context, prepare, identity_key
from prepare_harvest_alias import (pin, convert_plan, materialize, alias_angles,
                                   budget_report, relative_path)
from harvest_alias_mesh import split_repeats
from prepare_scenery import world_bounds, reference_rotation
from test_prepare_harvest import source, inputs
from test_replace_bsp_world import fixture
from world_flora_policy import source_key


def sample(root, raw=None):
    raw = raw or source()
    context = source_context(raw)
    ref = copy.deepcopy(context['full']['references'][0])
    vertices = [[0, 0, 0, -.4, -.3, 255, 255, 255, 255],
                [7, 0, 1, 2.6, .2, 255, 255, 255, 255],
                [0, 5, 2, .2, 2.3, 255, 255, 255, 255]]
    geometry = pack_geometry(vertices, [[0, 1, 2, 0]], 1)
    texture = struct.pack('>4sHH', b'MWT1', 2, 2) + bytes([160, 90, 40, 255]) * 4
    offset = (len(geometry) + 511) & ~511
    packet = geometry + bytes(offset - len(geometry)) + texture
    model = dict(source='meshes/f/flora_bc_mushroom_01.nif', source_sha256='a' * 64,
                 **pin(geometry), offset=0, bounds=[[0, 0, 0], [7, 5, 2]],
                 materials=[dict(texture_index=0, alpha=1, diffuse=[1, 1, 1])])
    ref.update(model_index=0, bounds=world_bounds(model['bounds'], ref))
    index = dict(models=[model], textures=[dict(**pin(texture), offset=offset)], references=[ref])
    index_raw = json.dumps(index).encode()
    palette = bytes(range(256)) * 3
    key = identity_key(source_key(ref, context['full']['master_sha256']))
    data = lumps(fixture(inline=True)); data[0] = bytearray(b'{\n"classname" "worldspawn"\n}\n\0')
    bsp = pack_lumps(data)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'town.bsp').write_bytes(bsp); (root / 'packet').write_bytes(packet)
    plan = dict(format='AmiWind external harvest plan 1',
                inputs=dict(master=pin(raw), index=pin(index_raw), packet=pin(packet), palette=pin(palette)),
                global_slots=len(context['indices']), global_catalogue_sha256=context['catalogue'],
                maps=[dict(name='town', path='town.bsp', **pin(bsp), origin=[0, 0, 0],
                           coverage=[[-100, -100], [100, 100]], keys=[key])])
    return dict(plan=plan, master=raw, index_raw=index_raw, archive_path=root / 'packet',
                palette=palette, base_root=root), bsp


def budget(args, clearance=1000000):
    row = args['plan']['maps'][0]
    return dict(target_struct_sizes_bytes=dict(hunk=16, aliashdr=100, mdl=84, stvert=12,
                mtriangle=16, maliasskindesc=8, trivertx=4, cache_system=48),
                target_measurement_sha256='a' * 64, target_static_delta_bytes=5548,
                heap_budget_bytes=100000 + clearance,
                maps=[dict(map='town', bsp_sha256=row['sha256'], bsp_bytes=row['bytes'],
                           estimated_total_bytes=100000)])


class ExternalHarvestPreparationTests(unittest.TestCase):
    def test_legacy_payload_bytes_remain_at_original_compatibility_baseline(self):
        # Captured before graph extraction from the original synthetic fixtures.
        cases = [({}, 'e50d129480d79287b1aff5a82c8c2ead2865264d3b767b0fb2bfcc35c25689f1'),
                 ({'contents': 'missing'}, 'a13c76c08e2a2a18653711c03409c89c46d77d72b01306c260c6b95163570003'),
                 ({'count': 1}, 'bcc01d856724a2116d707967a4ce6aec1df3dec929e645615b07aa6c2beb86b1'),
                 ({'count': 64}, '0b897cfe0fec9c066d1e8527ef97d38b88b2f0820543e3674c1b348f7531d496')]
        for option, expected in cases:
            raw = source(**option); region, bsp = inputs(raw)
            payload, _ = prepare(raw, region, bsp)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)

    def test_source_packet_to_alias_preserves_bsp_and_full_state_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); args, bsp = sample(root / 'in')
            report = convert_plan(**args, output=root / 'out', budget=budget(args))
            self.assertEqual((root / 'in/town.bsp').read_bytes(), bsp)
            self.assertFalse((root / 'out/maps').exists())
            self.assertEqual(report['heap']['status'], 'pass')
            self.assertGreater(report['heap']['surcharge_bytes'], 5548)
            row = report['maps'][0]; plant = row['placements'][0]
            self.assertEqual(plant['container_state']['items'], [{'id': 'levelled', 'count': 2}])
            catalogue = (root / 'out/harvest-town.txt').read_text()
            self.assertTrue(catalogue.startswith('AWH4 2 2 1 1 '))
            self.assertIn('Original ingredient name', catalogue)
            self.assertIn('Luminous Russula', catalogue)
            self.assertIn(plant['key'], catalogue)
            self.assertEqual(report['pickup_sound']['status'], 'missing_output')
            receipt = materialize(report, root / 'out', root / 'in', root / 'installed')
            self.assertTrue(receipt['byte_identical_bsp_readback'])
            self.assertEqual((root / 'installed/maps/town.bsp').read_bytes(), bsp)
            with self.assertRaises(FileExistsError):
                materialize(report, root / 'out', root / 'in', root / 'installed')

    def test_mixed_legacy_graph_and_payload_revalidated_from_original(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); args, _ = sample(root / 'in')
            region, bsp = inputs(args['master']); raw, _ = prepare(args['master'], region, bsp)
            legacy = root / 'legacy'; legacy.mkdir()
            report_raw = json.dumps(region).encode()
            for path, data in (('map.bsp', bsp), ('catalogue.txt', raw), ('report.json', report_raw)):
                (legacy / path).write_bytes(data)
            args['plan']['legacy'] = [dict(name='world', bsp=dict(path='map.bsp', **pin(bsp)),
                catalogue=dict(path='catalogue.txt', **pin(raw)), report=dict(path='report.json', **pin(report_raw)))]
            report = convert_plan(**args, output=root / 'out', legacy_root=legacy)
            self.assertEqual((root / 'out/harvest-world.txt').read_bytes(), raw)
            self.assertEqual(report['legacy_maps'][0]['representation'], 'brush')
            altered = raw.replace(b'Original ingredient name', b'Invented ingredient')
            (legacy / 'catalogue.txt').write_bytes(altered)
            args['plan']['legacy'][0]['catalogue'].update(pin(altered))
            with self.assertRaisesRegex(ValueError, 'differs from original'):
                convert_plan(**args, output=root / 'bad', legacy_root=legacy)
            self.assertFalse((root / 'bad').exists())

    def test_wrong_master_packet_pose_contents_or_model_binding_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); original, _ = sample(root / 'in')
            with self.assertRaisesRegex(ValueError, 'digest'):
                convert_plan(**dict(original, master=original['master'] + b'x'), output=root / 'bad')
            mutations = [lambda i: i['references'][0]['position'].__setitem__(0, 4),
                         lambda i: i['references'][0]['container_state']['items'][0].__setitem__('count', 9),
                         lambda i: i['models'][0].__setitem__('source', 'meshes/wrong.nif'),
                         lambda i: i['references'][0]['bounds'][0].__setitem__(0, -1)]
            for mutate in mutations:
                args = copy.deepcopy(original); index = json.loads(args['index_raw']); mutate(index)
                args['index_raw'] = json.dumps(index).encode(); args['plan']['inputs']['index'] = pin(args['index_raw'])
                with self.assertRaises(ValueError):
                    convert_plan(**args, output=root / 'bad')
                self.assertFalse((root / 'bad').exists())

    def test_unsupported_original_state_rejected_in_external_representation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for number, option in enumerate((dict(script='script'), dict(owner=True), dict(count=-2))):
                args, _ = sample(root / str(number), source(**option))
                with self.assertRaises(ValueError):
                    convert_plan(**args, output=root / 'bad')
                self.assertFalse((root / 'bad').exists())

    def test_coverage_identity_existing_geometry_and_stale_bsp_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); original, bsp = sample(root / 'in')
            args = copy.deepcopy(original); args['plan']['maps'][0]['keys'] = []
            with self.assertRaisesRegex(ValueError, 'coverage'):
                convert_plan(**args, output=root / 'bad')
            args = copy.deepcopy(original); args['plan']['maps'][0]['coverage'] = [[500, 500], [600, 600]]
            with self.assertRaisesRegex(ValueError, 'coverage'):
                convert_plan(**args, output=root / 'bad')
            (root / 'in/town.bsp').write_bytes(bsp + b'bad')
            with self.assertRaisesRegex(ValueError, 'digest'):
                convert_plan(**original, output=root / 'bad')
            for entity in (b'"aw_ref" "42"', b'"classname" "aw_flora"\n"origin" "0.25 0.5 0.75"'):
                data = lumps(bsp); data[0] += b'\n{\n' + entity + b'\n}\n'
                collision = pack_lumps(data); (root / 'in/town.bsp').write_bytes(collision)
                args = copy.deepcopy(original); args['plan']['maps'][0].update(pin(collision))
                with self.assertRaisesRegex(ValueError, 'already binds|source pose'):
                    convert_plan(**args, output=root / 'bad')

    def test_budget_failure_never_becomes_production_admission(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); args, _ = sample(root / 'in')
            report = convert_plan(**args, output=root / 'out', budget=budget(args, clearance=0))
            self.assertEqual(report['heap']['status'], 'failed')
            self.assertLess(report['heap']['maps'][0]['clearance'], 0)
            with self.assertRaisesRegex(ValueError, 'heap admission'):
                materialize(report, root / 'out', root / 'in', root / 'blocked')
            self.assertFalse((root / 'blocked').exists())
            model = next((root / 'out/progs/harvest').glob('*.mdl')).read_bytes()
            wrong = budget(args); wrong['maps'][0]['bsp_sha256'] = 'b' * 64
            with self.assertRaisesRegex(ValueError, 'BSP binding'):
                budget_report([model], report['maps'], wrong)

    def test_installer_rechecks_model_digest_and_safe_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); args, _ = sample(root / 'in')
            report = convert_plan(**args, output=root / 'out', budget=budget(args))
            model = next((root / 'out/progs/harvest').glob('*.mdl')); model.write_bytes(model.read_bytes() + b'x')
            with self.assertRaisesRegex(ValueError, 'digest'):
                materialize(report, root / 'out', root / 'in', root / 'blocked')
            self.assertFalse((root / 'blocked').exists())
            for path in ('../x', '/x', 'maps/../../x', 'C:/x', 'maps\\x', 'maps//x'):
                with self.assertRaises(ValueError): relative_path(path)

    def test_alias_rotation_retains_original_tilt_and_scale(self):
        for angles in ([.1, .2, 3.01681185], [0, np.pi / 2, .4], [.3, -.1, -2]):
            ref = dict(rotation_radians=angles)
            pitch, yaw, roll = np.radians(alias_angles(ref))
            cp, sp, cy, sy, cr, sr = np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw), np.cos(roll), np.sin(roll)
            # Quake alias pitch is inverted when forming the actual renderer basis.
            matrix = np.array([[cp*cy, -sr*sp*cy-cr*sy, -cr*sp*cy+sr*sy],
                               [cp*sy, -sr*sp*sy+cr*cy, -cr*sp*sy-sr*cy],
                               [sp, sr*cp, cr*cp]])
            np.testing.assert_allclose(matrix, reference_rotation(ref), atol=1e-7)

    def test_repeated_uv_surface_coverage_without_gaps(self):
        vertices = np.array([[0, 0, 0, -.4, -.3], [7, 0, 0, 2.6, .2], [0, 5, 0, .2, 2.3]])
        triangles, areas = split_repeats(vertices, np.array([[0, 1, 2, 0]]))
        self.assertGreater(len(triangles), 4)
        area = sum(np.linalg.norm(np.cross(t[1, :3]-t[0, :3], t[2, :3]-t[0, :3])) / 2 for t, _, _ in triangles)
        self.assertAlmostEqual(area, areas[0], places=8)
        self.assertAlmostEqual(area, 17.5, places=8)


if __name__ == '__main__':
    unittest.main()
