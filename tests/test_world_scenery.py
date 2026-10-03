# SPDX-License-Identifier: GPL-3.0-only
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from world_scenery import inventory, region_references, scenery_kind
from build_aga import install_world_scenery


def sub(tag, value):
    return tag.encode() + struct.pack('<I', len(value)) + value


def record(tag, value):
    return tag.encode() + struct.pack('<III', len(value), 0, 0) + value


def reference(number, object_id, deleted=False):
    fields = sub('FRMR', struct.pack('<I', number)) + sub('NAME', object_id.encode() + b'\0')
    fields += sub('XSCL', struct.pack('<f', 2.0))
    fields += sub('DATA', struct.pack('<6f', 20, 30, 40, 0.2, 0.4, 0.6))
    return fields + (sub('DELE', b'\0') if deleted else b'')


class WorldSceneryTests(unittest.TestCase):
    def test_giant_parasols_are_not_lost_to_mushroom_keyword_or_collectibles(self):
        self.assertEqual(scenery_kind('flora_emp_parasol_01', {'type': 'STAT', 'model': r'f\Flora_emp_parasol_01.NIF'}), 'giant_mushroom')
        self.assertIsNone(scenery_kind('mushroom', {'type': 'ACTI', 'model': r'x\Flora_T_mushroom_01.nif'}))
        self.assertIsNone(scenery_kind('small_fungus', {'type': 'STAT', 'model': r'x\Flora_T_shelffungus_01.nif'}))
        self.assertIsNone(scenery_kind('tree', {'type': 'STAT', 'model': r'f\Flora_tree_GL_01.nif'}))
        self.assertEqual(scenery_kind('rock', {'type': 'STAT', 'model': r'f\Terrain_rocks_AI_01.nif'}), 'rock')

    def test_census_retains_transforms_excludes_deleted_and_separates_interiors(self):
        source = record('STAT', sub('NAME', b'rock\0') + sub('MODL', b'f\\Terrain_rock_BC_18.nif\0'))
        source += record('CELL', sub('NAME', b'\0') + sub('DATA', struct.pack('<Iii', 0, -2, -9)) + reference(1, 'rock') + reference(2, 'rock', True))
        source += record('CELL', sub('NAME', b'Cave\0') + sub('DATA', struct.pack('<Iii', 1, 0, 0)) + reference(1, 'rock'))
        census = inventory(source)
        self.assertEqual(census['counts']['exterior'], {'rock': 1})
        self.assertEqual(census['counts']['interior'], {'rock': 1})
        ref = census['references'][0]
        self.assertEqual(ref['cell'], [-2, -9])
        self.assertEqual(ref['scale'], 2)
        self.assertEqual(ref['position'], [20, 30, 40])
        self.assertAlmostEqual(ref['rotation_radians'][0], 0.2)
        self.assertEqual(census['interior_references'][0]['cell'], 'Cave')

    def test_bounds_overlap_selects_origin_outside_and_preserves_source(self):
        ref = {'number': 7, 'position': [9000, 9000, 120], 'bounds': [[-10, -10, 100], [10, 10, 140]], 'scale': 2, 'rotation_radians': [0.3, 0.4, 0.5]}
        index = {'references': [ref], 'chunk_size': 2048, 'chunks': {'0,0': [0], '-1,-1': [0]}}
        saved = copy.deepcopy(index)
        entry = {'origin': [0, 0, -32], 'coverage': [[-16, -16], [16, 16]]}
        selected = region_references(index, entry)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['position'], [9000, 9000, 248])
        self.assertEqual(selected[0]['bounds'], [[-10, -10, 228], [10, 10, 268]])
        self.assertEqual(selected[0]['rotation_radians'], ref['rotation_radians'])
        self.assertEqual(index, saved)
        self.assertEqual(region_references(index, {'origin': [10000, 10000, 0], 'coverage': [[0, 0], [10, 10]]}), [])



    def _overlay_fixture(self, root):
        id1 = root / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'world').mkdir()
        (id1 / 'gfx').mkdir()
        palette = b'palette-data'
        (id1 / 'gfx/palette.lmp').write_bytes(palette)
        names = ['vf0000', 'vf0001']
        packet = bytearray(b'AWR2' + struct.pack('<I', len(names)) + bytes(56))
        for name in names:
            packet.extend(struct.pack('<8s11f', name.encode(), *([0.0] * 11)))
        (id1 / 'world/regions.awr').write_bytes(packet)
        overlay = root / 'overlay'
        overlay.mkdir()
        references = [{'cell': [-2, -9], 'number': 7, 'kind': 'rock'}]
        rows = []
        for name in names:
            original = ('terrain-' + name).encode()
            baked = ('overlay-' + name).encode()
            selected = references if name == 'vf0000' else []
            (id1 / 'maps' / f'{name}.bsp').write_bytes(original)
            (overlay / name).mkdir()
            (overlay / name / 'scene.bsp').write_bytes(baked)
            rows.append({'name': name, 'instances': len(selected), 'source_references': selected,
                         'original_terrain_sha256': hashlib.sha256(original).hexdigest(),
                         'sha256': hashlib.sha256(baked).hexdigest(), 'bytes': len(baked)})
        receipt = {'format': 'AmiWind world scenery overlay 1', 'diagnostic_subset': False,
                   'palette_sha256': hashlib.sha256(palette).hexdigest(),
                   'covered_source_references': 1, 'regions': rows}
        (overlay / 'world-scenery.json').write_text(json.dumps(receipt), encoding='utf-8')
        return overlay, id1, receipt

    def test_legacy_empty_region_missing_size_requires_identical_terrain(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self._overlay_fixture(Path(temp))
            row = receipt['regions'][1]
            raw = (id1/'maps/vf0001.bsp').read_bytes()
            (overlay/'vf0001/scene.bsp').write_bytes(raw)
            row.pop('bytes')
            row.update(retained_terrain_only=True, unique_models=0,
                       sha256=hashlib.sha256(raw).hexdigest())
            (overlay/'world-scenery.json').write_text(json.dumps(receipt))
            self.assertEqual(install_world_scenery(overlay,id1)['status'],'passed')

    def test_populated_region_missing_size_still_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self._overlay_fixture(Path(temp))
            receipt['regions'][0].pop('bytes')
            (overlay/'world-scenery.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'size differs'):
                install_world_scenery(overlay,id1)
            self.assertEqual((id1/'maps/vf0000.bsp').read_bytes(),b'terrain-vf0000')

    def test_image_install_replaces_every_verified_region_and_deduplicates_references(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self._overlay_fixture(Path(temp))
            result = install_world_scenery(overlay, id1)
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['regions'], 2)
            self.assertEqual(result['covered_source_references'], 1)
            self.assertEqual((id1 / 'maps/vf0000.bsp').read_bytes(), b'overlay-vf0000')
            self.assertEqual((id1 / 'maps/vf0001.bsp').read_bytes(), b'overlay-vf0001')

    def test_image_install_rejects_bad_later_overlay_without_partial_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self._overlay_fixture(Path(temp))
            before = {name: (id1 / 'maps' / f'{name}.bsp').read_bytes() for name in ('vf0000', 'vf0001')}
            receipt['regions'][1]['sha256'] = '0' * 64
            (overlay / 'world-scenery.json').write_text(json.dumps(receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'missing or changed'):
                install_world_scenery(overlay, id1)
            self.assertEqual(before, {name: (id1 / 'maps' / f'{name}.bsp').read_bytes()
                                      for name in ('vf0000', 'vf0001')})

    def test_image_install_rejects_diagnostic_subset(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self._overlay_fixture(Path(temp))
            receipt['diagnostic_subset'] = True
            (overlay / 'world-scenery.json').write_text(json.dumps(receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'complete production'):
                install_world_scenery(overlay, id1)

if __name__ == '__main__':
    unittest.main()
