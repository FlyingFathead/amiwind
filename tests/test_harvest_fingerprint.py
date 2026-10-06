# SPDX-License-Identifier: GPL-3.0-only
"""The converter's indexed catalogues participate in the actual save namespace."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_aga import harvest_fingerprint_entries, write_content_fingerprint
from prepare_harvest import prepare
from test_prepare_harvest import source, inputs


class HarvestFingerprintTests(unittest.TestCase):
    def seed(self, root):
        names = ['maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt',
                 'balmora-regions.txt', 'progs.dat', 'character/catalog.awc',
                 'world/map.awm', 'world/journal.awj', 'world/entries.dat',
                 'world/quests.awq', 'world/region-names.awn']
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode('ascii'))
        return names

    def fingerprint(self, root):
        # Region-table parsing has its own fixtures; keep the real save hash
        # composition, harvest discovery, generated rows and BSP bytes here.
        with patch('area_config.SCENES', []), patch('build_aga.town_region_map_names', return_value=[]):
            write_content_fingerprint(root)
        return (root / 'save-content.bin').read_bytes()

    def test_generated_catalogue_sorted_raw_bytes_and_bsp_bind_save_namespace(self):
        raw = source(); region, bsp = inputs(raw)
        payload, receipt = prepare(raw, region, bsp)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); names = self.seed(root)
            baseline = self.fingerprint(root)
            expected = hashlib.sha256()
            for name in names:
                expected.update(name.encode() + b'\0' + hashlib.sha256((root/name).read_bytes()).digest())
            self.assertEqual(baseline, expected.digest())
            paths = [root/'harvest-sncourt.txt', root/'harvest-intro_docks.txt']
            for path in paths:
                path.write_bytes(payload)
            (root/'maps/sncourt.bsp').write_bytes(bsp)
            (root/'maps/intro_docks.bsp').write_bytes(bsp)
            entries = harvest_fingerprint_entries(root)
            self.assertEqual(entries, [(p.name, receipt['catalogue_sha256']) for p in reversed(paths)])
            first = self.fingerprint(root)
            expected = hashlib.sha256()
            for name in names:
                expected.update(name.encode() + b'\0' + hashlib.sha256((root/name).read_bytes()).digest())
            for name, digest in entries:
                expected.update(name.encode() + b'\0' + bytes.fromhex(digest))
            self.assertEqual(first, expected.digest())
            self.assertNotEqual(first, baseline)
            paths[0].unlink(); paths[0].write_bytes(payload)
            self.assertEqual(first, self.fingerprint(root))
            paths[0].write_bytes(payload.replace(b'Luminous Russula', b'Luminous russula'))
            self.assertNotEqual(first, self.fingerprint(root))
            paths[0].write_bytes(payload)
            (root/'maps/sncourt.bsp').write_bytes(bsp+b'changed')
            self.assertNotEqual(first, self.fingerprint(root))

    def test_legacy_formats_preserve_exact_raw_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.seed(root)
            self.assertEqual(harvest_fingerprint_entries(root), [])
            for version, name in ((1, 'sncourt'), (2, 'intro_docks')):
                (root/f'harvest-{name}.txt').write_bytes(f'AWH{version} 0 0 0\n'.encode())
            self.assertEqual(harvest_fingerprint_entries(root), [
                (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
                for path in sorted(root.glob('harvest-*.txt'))])

    def test_global_index_bounds_and_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.seed(root); path=root/'harvest-sncourt.txt'
            for slots in (1, 4096):
                path.write_text(f'AWH3 0 0 0 {slots} '+ 'a'*64+'\n')
                self.assertEqual(len(harvest_fingerprint_entries(root)), 1)
            invalid = [f'AWH3 0 0 0 {slots} '+ 'a'*64 for slots in ('0','4097','-1')]
            invalid += ['AWH3 0 0 0 1 '+v for v in ('0'*64,'A'*64,'g'*64,'a'*63,'a'*65)]
            invalid += ['AWH3 0 0 0', 'AWH2 0 0 0 1 '+'a'*64,
                        'AWH3 0 0 1 1 '+'a'*64, 'AWH3 65 0 0 1 '+'a'*64]
            for header in invalid:
                with self.subTest(header=header):
                    path.write_text(header+'\n')
                    with self.assertRaises(ValueError): harvest_fingerprint_entries(root)

    def test_reject_mixed_or_mismatched_map_catalogues_in_both_orders(self):
        indexed='AWH3 0 0 0 1 '+'a'*64+'\n'
        others = ['AWH1 0 0 0\n', 'AWH2 0 0 0\n',
                  'AWH3 0 0 0 2 '+'a'*64+'\n', 'AWH3 0 0 0 1 '+'b'*64+'\n']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.seed(root)
            for other in others:
                for first, second in ((indexed, other), (other, indexed)):
                    with self.subTest(first=first, second=second):
                        (root/'harvest-intro_docks.txt').write_text(first)
                        (root/'harvest-sncourt.txt').write_text(second)
                        with self.assertRaises(ValueError): harvest_fingerprint_entries(root)


if __name__=='__main__': unittest.main()
