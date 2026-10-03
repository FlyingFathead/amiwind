import csv
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from audit_gallery_budgets import model_allowance, write_allowances
from prepare_gallery import inspection_table


class GalleryBudgetTests(unittest.TestCase):
    def test_allowance_binds_exact_bytes_and_hard_ceiling(self):
        raw=bytearray(84);raw[:8]=b'IDPO\x06\0\0\0';struct.pack_into('<ii',raw,60,2295,765)
        receipt={'sha256':hashlib.sha256(raw).hexdigest()}
        self.assertEqual(model_allowance('test',raw,receipt)['triangles'],765)
        raw[20]=1
        with self.assertRaisesRegex(ValueError,'receipt'):model_allowance('test',raw,receipt)
        struct.pack_into('<ii',raw,60,3036,1012);receipt['sha256']=hashlib.sha256(raw).hexdigest()
        self.assertEqual(model_allowance('test',raw,receipt)['triangles'],1012)
        struct.pack_into('<ii',raw,60,3075,1025);receipt['sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError,'ceiling'):model_allowance('test',raw,receipt)
        struct.pack_into('<ii',raw,60,1998,666);receipt['sha256']=hashlib.sha256(raw).hexdigest()
        self.assertIsNone(model_allowance('test',raw,receipt))

    def test_allowance_file_preserves_lf_bytes_across_hosts(self):
        raw = bytearray(84)
        raw[:8] = b'IDPO\x06\0\0\0'
        struct.pack_into('<ii', raw, 60, 2295, 765)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'test.mdl').write_bytes(raw)
            result = dict(status='ready', sha256=hashlib.sha256(raw).hexdigest())
            report = write_allowances(root, {'test': result}, [], root / 'allowances.txt')
            self.assertFalse(report['unresolved'])
            written = (root / 'allowances.txt').read_bytes()
            self.assertNotIn(b'\r', written)
            self.assertTrue(written.startswith(b'AWPB1\ngallery/test.mdl '))
            self.assertEqual(written.count(b'\n'), 2)

    def test_changed_model_never_inherits_inspection(self):
        entries=[dict(number=4,kind='NPC_',id='source',name='Friendly',models=['shared','shared'])]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'review.tsv'
            results={'shared':dict(status='ready',sha256='new')}
            inspection_table(entries,results,path,{'shared':dict(status='accepted',sha256='old')})
            with path.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
            self.assertEqual([r['inspection'] for r in rows],['unreviewed','unreviewed'])
            self.assertEqual([r['shared_uses'] for r in rows],['2','2'])
            inspection_table(entries,results,path,{'shared':dict(status='accepted',sha256='new')})
            with path.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
            self.assertEqual([r['inspection'] for r in rows],['accepted','accepted'])
