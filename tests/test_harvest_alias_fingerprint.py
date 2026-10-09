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

    def test_catalogue_of_a_map_left_out_by_a_pure_chim_image(self):
        # CHIM-HARVEST-REMOVED-MAPS-33: a pure CHIM image removes the town's region maps (bm###.bsp) but
        # keeps their harvest catalogues, which the engine loads per region on the CHIM frame map.
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);args,bsp=sample(base/'input')
            output=base/'converted';convert_plan(**args,output=output)
            root=base/'id1';root.mkdir();legacy.HarvestFingerprintTests().seed(root)
            shutil.copytree(output/'progs',root/'progs')
            (root/'harvest-bm008.txt').write_bytes((output/'harvest-town.txt').read_bytes())
            with self.assertRaisesRegex(ValueError,'no matching map: harvest-bm008.txt'):
                build_aga.harvest_fingerprint_entries(root)
            names=[name for name,_ in build_aga.harvest_fingerprint_entries(root,removed={'maps/bm008.bsp'})]
            self.assertIn('harvest-bm008.txt',names)
            with self.assertRaisesRegex(ValueError,'no matching map'):
                build_aga.harvest_fingerprint_entries(root,removed={'maps/bm009.bsp'})
            # Callers without the removal list (the heap checks) see the town on CHIM: its region table
            # names bm008 and maps/balmora-chim.bsp is present.
            (root/'balmora-regions.txt').write_text('AWBR1 64 96 540 0 0 0 0 1 1 1 1\nbm008 0 0 1 1 0 0 1 1\n')
            with self.assertRaisesRegex(ValueError,'no matching map'):
                build_aga.harvest_fingerprint_entries(root)
            (root/'maps/balmora-chim.bsp').write_bytes(b'frame map')
            self.assertIn('harvest-bm008.txt',[name for name,_ in build_aga.harvest_fingerprint_entries(root)])

    def test_catalogue_of_a_special_map_on_chim_is_left_out(self):
        # CHIM-HARVEST-SPECIALS-33: the intro docks run as maps/intro_docks-chim.bsp; the engine would look for
        # harvest-intro_docks-chim.txt, so the legacy catalogue is left out instead of failing the image step.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'id1';(root/'maps').mkdir(parents=True)
            (root/'harvest-intro_docks.txt').write_text('AWH1 0 0 0\n')
            (root/'harvest-sn001.txt').write_text('AWH1 0 0 0\n')
            self.assertEqual(build_aga.retire_chim_special_catalogues(root),[])     # no CHIM frame map: kept
            (root/'maps/intro_docks-chim.bsp').write_bytes(b'frame map')
            (root/'maps/seyda-chim.bsp').write_bytes(b'frame map')
            (root/'seyda-regions.txt').write_text('AWBR1 64 96 540 0 0 0 0 1 1 1 1\nsn001 0 0 1 1 0 0 1 1\n')
            # every caller of the catalogue check (heap checks, interior sections) skips it before the image
            # step removes it
            self.assertNotIn('harvest-intro_docks.txt',[n for n,_ in build_aga.harvest_fingerprint_entries(root)])
            self.assertEqual(build_aga.retire_chim_special_catalogues(root),['harvest-intro_docks.txt'])
            self.assertFalse((root/'harvest-intro_docks.txt').exists())
            self.assertTrue((root/'harvest-sn001.txt').exists())                    # a CHIM town region: kept

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
