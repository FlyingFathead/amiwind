"""Catalogue output and provenance must describe the same final normal bytes."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_SOURCE', ROOT))
sys.path[:0] = [str(ROOT / 'tools'), str(SOURCE / 'src'), str(SOURCE / 'tools')]
import prepare_hand_catalog as catalog
import prepare_hand_normals as normals
from test_hand_normals import model


class CatalogNormalTests(unittest.TestCase):
    def generate(self, topology='reduced', normal_mode='auto'):
        raw = model()
        table = normals.normal_table(SOURCE / 'engine/aga/src/anorms.h')
        original_hash = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            palette = root / 'palette.lmp'
            palette.write_bytes(bytes(768))
            output = root / 'output'

            def hands(*args):
                return raw, {'sha256': original_hash, 'bytes': len(raw), 'clips': {'idle': 8}}

            def torch(data, stage, **kwargs):
                (stage / 'progs').mkdir()
                (stage / 'progs/v_torch.mdl').write_bytes(raw)
                (stage / 'gfx/torch.awt').write_bytes(b'fixture-emitter')
                return {'files': {'progs/v_torch.mdl': original_hash}}

            with patch.object(catalog, 'TorchSource') as source, \
                 patch.object(catalog, 'first', return_value=struct.pack('<16xI', 1)), \
                 patch.object(catalog, 'bake_appearance', side_effect=hands), \
                 patch.object(catalog, 'prepare_torch', side_effect=torch), \
                 patch.object(catalog, 'normal_table', return_value=table) as load_table:
                source.return_value.kinds = {'RACE': {'nord': object()}}
                result = catalog.prepare(root / 'owned', palette, output, topology=topology, normal_mode=normal_mode)
            expected = normals.rewrite(raw, table)[0] if topology == 'source' and normal_mode == 'auto' else raw
            expected_hash = hashlib.sha256(expected).hexdigest()
            for entry in result['entries']:
                for kind in ('hand', 'torch'):
                    self.assertEqual((output / entry[kind + '_model']).read_bytes(), expected)
                    self.assertEqual(entry[kind + '_sha256'], expected_hash)
                    self.assertEqual(entry[kind + '_bytes'], len(expected))
                stem = Path(entry['hand_model']).stem
                report = json.loads((output / 'reports' / (stem + '.json')).read_text())
                self.assertEqual(report['hands']['sha256'], expected_hash)
                self.assertEqual(report['torch']['files']['progs/v_torch.mdl'], expected_hash)
                self.assertEqual((output / 'reports' / (stem + '-torch/progs/v_torch.mdl')).read_bytes(), expected)
                if result['normal_mode'] == 'surface':
                    for kind in ('hands', 'torch'):
                        normal_report = report[kind]['lighting_normals']
                        self.assertEqual(normal_report['input_sha256'], original_hash)
                        self.assertEqual(normal_report['output_sha256'], expected_hash)
                        self.assertTrue(normal_report['geometry_texture_animation_byte_identical'])
            self.assertEqual((output / 'gfx/hand-torch.awt').read_bytes(), b'fixture-emitter')
            self.assertEqual(json.loads((output / 'hand-catalog-report.json').read_text()), result)
            self.assertEqual(load_table.call_count, int(result['normal_mode'] == 'surface'))
            return result['normal_mode'], expected != raw

    def test_source_outputs_and_every_hash_use_surface_normal_bytes(self):
        self.assertEqual(self.generate('source'), ('surface', True))

    def test_default_reduced_output_remains_byte_identical(self):
        self.assertEqual(self.generate(), ('legacy', False))

    def test_source_legacy_mode_is_an_explicit_byte_identical_rollback(self):
        self.assertEqual(self.generate('source', 'legacy'), ('legacy', False))


if __name__ == '__main__':
    unittest.main()
