# SPDX-License-Identifier: GPL-3.0-only
"""Generated AWH4 raw model closure participates in the complete save hash."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

import build_aga
import test_harvest_fingerprint as legacy
from test_prepare_harvest_alias import sample
from prepare_harvest_alias import convert_plan


class SharedHarvestFingerprintTests(unittest.TestCase):
    def test_generated_shared_bytes_are_unique_ordered_and_bound_to_full_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);args,bsp=sample(base/'input')
            output=base/'converted';convert_plan(**args,output=output)
            root=base/'id1';root.mkdir();helper=legacy.HarvestFingerprintTests();helper.seed(root)
            baseline=helper.fingerprint(root)
            raw=(output/'harvest-town.txt').read_bytes()
            for name in ('intro_docks','sncourt'):
                (root/f'harvest-{name}.txt').write_bytes(raw)
                (root/f'maps/{name}.bsp').write_bytes(bsp)
            shutil.copytree(output/'progs',root/'progs')
            first=build_aga.harvest_fingerprint_entries(root)
            models=list((root/'progs/harvest').glob('*.mdl'))
            self.assertEqual(len(models),1);self.assertEqual(len(first),3)
            model=models[0];name=model.relative_to(root).as_posix();original=model.read_bytes()
            self.assertEqual(first[-1],(name,hashlib.sha256(original).hexdigest()))
            original_fp=helper.fingerprint(root);self.assertNotEqual(original_fp,baseline)
            self.assertEqual(original_fp,helper.fingerprint(root))
            changed=bytearray(original);changed[88]^=1;model.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                helper.fingerprint(root)
            old=hashlib.sha256(original).hexdigest();new=hashlib.sha256(changed).hexdigest()
            for path in root.glob('harvest-*.txt'):
                path.write_bytes(path.read_bytes().replace(old.encode(),new.encode()))
            self.assertNotEqual(original_fp,helper.fingerprint(root))
            model.unlink()
            with self.assertRaisesRegex(ValueError,'Missing'):
                helper.fingerprint(root)

    def test_mixed_indexed_representations_require_same_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);args,bsp=sample(base/'input')
            output=base/'converted';convert_plan(**args,output=output)
            root=base/'id1';root.mkdir();legacy.HarvestFingerprintTests().seed(root)
            raw=(output/'harvest-town.txt').read_bytes()
            (root/'harvest-sncourt.txt').write_bytes(raw)
            shutil.copytree(output/'progs',root/'progs')
            header=raw.decode().splitlines()[0].split();slots,digest=header[4:6]
            other=root/'harvest-intro_docks.txt'
            other.write_text(f'AWH3 0 0 0 {slots} {digest}\n')
            self.assertEqual(len(build_aga.harvest_fingerprint_entries(root)),3)
            for bad in ('AWH2 0 0 0\n',f'AWH3 0 0 0 {int(slots)+1} {digest}\n',
                        f'AWH3 0 0 0 {slots} '+('a'*64 if digest!='a'*64 else 'b'*64)+'\n'):
                other.write_text(bad)
                with self.assertRaises(ValueError):build_aga.harvest_fingerprint_entries(root)


if __name__=='__main__':
    unittest.main()
