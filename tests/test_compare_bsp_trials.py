# SPDX-License-Identifier: GPL-3.0-only
import json
from datetime import datetime, timedelta
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from compare_bsp_trials import compare_trials, measure_bsp, STATUS


def fixture(faces=2, vertices=4):
    parts = [b''] * 15
    parts[3] = bytes(vertices * 12)
    parts[7] = b''.join(struct.pack('<Hhihh4Bi', 0, 0, 0, 4, 0, 255, 255, 255, 255, -1) for _ in range(faces))
    header = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for i, part in enumerate(parts):
        struct.pack_into('<ii', header, 4 + i * 8, 124 + len(body), len(part))
        body.extend(part)
    return bytes(header + body)


class TrialTests(unittest.TestCase):
    def test_file_accounting_includes_header_and_trailing_padding(self):
        raw = fixture() + bytes(5)
        measured = measure_bsp(raw)
        self.assertEqual(measured['non_lump_bytes'], 129)
        sections = sum(v for k, v in measured.items() if k.startswith('lump.') and k.endswith('.bytes'))
        self.assertEqual(sections + measured['non_lump_bytes'], len(raw))

    def test_concurrent_output_directory_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            real_mkdir = Path.mkdir
            def race(path, *args, **kwargs):
                if path == root / 'ledger':
                    real_mkdir(path)
                    (path / 'foreign.txt').write_text('preserve')
                return real_mkdir(path, *args, **kwargs)
            with patch.object(Path, 'mkdir', race), self.assertRaises(FileExistsError):
                compare_trials(original=a, before=b, after=c, out_dir=root / 'ledger', method='race')
            self.assertEqual((root / 'ledger/foreign.txt').read_text(), 'preserve')
            self.assertFalse((root / 'ledger/comparison.json').exists())
            self.assertFalse(any(p.name.startswith('.ledger-trial-') for p in root.iterdir()))

    def setup_paths(self, root):
        paths = [root / (name + '.bsp') for name in ('original', 'before', 'after')]
        for path, count in zip(paths, (3, 2, 1)):
            path.write_bytes(fixture(count))
        return paths

    def test_original_and_immediate_deltas_and_unknown_created_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            originals = [p.read_bytes() for p in (a, b, c)]
            report = compare_trials(original=a, before=b, after=c, out_dir=root / 'ledger', method='fixture')
            self.assertEqual(report['status'], STATUS)
            utc = datetime.fromisoformat(report['created_at_utc'])
            local = datetime.fromisoformat(report['created_at_local'])
            self.assertEqual(utc.utcoffset(), timedelta(0))
            self.assertIsNotNone(local.utcoffset())
            self.assertEqual(utc, local)
            self.assertEqual(report['deltas']['after_vs_original']['stored.faces.records']['saving_reference_minus_output'], 2)
            self.assertEqual(report['deltas']['after_vs_before']['stored.faces.records']['saving_reference_minus_output'], 1)
            self.assertEqual(report['phases']['after']['metrics']['stored.faces.fan_triangle_count'], 2)
            self.assertIsNone(report['unsupported_metrics']['created_vertices'])
            self.assertEqual([p.read_bytes() for p in (a, b, c)], originals)
            self.assertEqual(json.loads((root / 'ledger/comparison.json').read_text())['status'], STATUS)

    def test_external_resource_flips_bsp_saving_to_increase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            asset = root / 'sky.lmp'
            asset.write_bytes(bytes(32768))
            report = compare_trials(original=a, before=b, after=c, after_assets=[asset], out_dir=root / 'ledger', method='sky')
            metrics = report['deltas']['after_vs_original']
            self.assertEqual(metrics['bsp_file_bytes']['saving_reference_minus_output'], 40)
            self.assertEqual(metrics['included_storage.bytes']['saving_reference_minus_output'], 40 - 32768)
            self.assertEqual(metrics['included_storage.bytes']['interpretation'], 'increase')
            self.assertIn('none explicitly listed', report['phases']['original']['external_asset_scope'])

    def test_increased_record_counts_are_increases_not_created_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            c.write_bytes(fixture(5, 8))
            report = compare_trials(original=a, before=b, after=c, out_dir=root / 'ledger', method='growth')
            delta = report['deltas']['after_vs_original']['stored.vertices.records']
            self.assertEqual(delta['change_output_minus_reference'], 4)
            self.assertEqual(delta['saving_reference_minus_output'], -4)
            self.assertIsNone(report['unsupported_metrics']['created_vertices'])

    def test_malformed_input_leaves_no_output_or_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            c.write_bytes(b'invalid')
            with self.assertRaises(ValueError):
                compare_trials(original=a, before=b, after=c, out_dir=root / 'ledger', method='bad')
            self.assertFalse((root / 'ledger').exists())
            self.assertEqual(len(list(root.iterdir())), 3)
        raw = bytearray(fixture())
        struct.pack_into('<i', raw, 4 + 7 * 8 + 4, 39)
        with self.assertRaises(ValueError):
            measure_bsp(raw)

    def test_same_readonly_inputs_allowed_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'same.bsp'
            source.write_bytes(fixture())
            report = compare_trials(original=source, before=source, after=source, out_dir=root / 'ledger', method='same')
            self.assertEqual(report['deltas']['after_vs_before']['included_storage.bytes']['saving_reference_minus_output'], 0)
            saved = (root / 'ledger/comparison.json').read_bytes()
            with self.assertRaises(ValueError):
                compare_trials(original=source, before=source, after=source, out_dir=root / 'ledger', method='same')
            self.assertEqual((root / 'ledger/comparison.json').read_bytes(), saved)
            with self.assertRaises(ValueError):
                compare_trials(original=source, before=source, after=source, out_dir=source, method='alias')

    def test_invalid_polygon_fan_unknown_and_assets_not_double_counted(self):
        raw = bytearray(fixture())
        offset = struct.unpack_from('<i', raw, 4 + 7 * 8)[0]
        struct.pack_into('<h', raw, offset + 8, 2)
        self.assertIsNone(measure_bsp(raw)['stored.faces.fan_triangle_count'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, c = self.setup_paths(root)
            with self.assertRaises(ValueError):
                compare_trials(original=a, before=b, after=c, after_assets=[c], out_dir=root / 'ledger', method='double')


if __name__ == '__main__':
    unittest.main()
