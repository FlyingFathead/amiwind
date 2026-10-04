import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from install_world_flora import install


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class FloraInstallTests(unittest.TestCase):
    def fixture(self, root):
        overlay, id1 = root/'overlay', root/'id1'
        (id1/'maps').mkdir(parents=True)
        (id1/'gfx').mkdir()
        (id1/'gfx/palette.lmp').write_bytes(b'palette')
        (id1/'maps/vf0000.bsp').write_bytes(b'rocks and mushrooms')
        (overlay/'vf0000').mkdir(parents=True)
        (overlay/'vf0000/scene.bsp').write_bytes(b'rocks mushrooms and flora')
        name = 'progs/aw_flora/f_0123456789abcdef.spr'
        spr = b'IDSP\x01\0\0\0' + bytes(28)
        (overlay/name).parent.mkdir(parents=True)
        (overlay/name).write_bytes(spr)
        receipt = {'format':'AmiWind world flora overlay 1',
                   'diagnostic_subset':False,'base_world_scenery_receipt_sha256':'base-receipt',
                   'palette_sha256':sha(b'palette'), 'covered_unique_original_refs':1,
                   'regions':[{'name':'vf0000','base_sha256':sha(b'rocks and mushrooms'),
                               'sha256':sha(b'rocks mushrooms and flora'),'bytes':len(b'rocks mushrooms and flora'),
                               'retained_content':{'retained_content':'verified'},
                               'source_references':[{'source_key':[[1,2],3]}]}],
                   'assets':[{'sprite_asset_name':name,'sha256':sha(spr)}]}
        return overlay, id1, receipt

    def run_install(self, overlay, id1, receipt):
        (overlay/'world-flora.json').write_text(json.dumps(receipt), encoding='utf-8')
        return install(overlay, id1, {'regions':1,'receipt_sha256':'base-receipt'})

    def test_complete_install_preserves_source_and_stages_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self.fixture(Path(temp))
            result = self.run_install(overlay, id1, receipt)
            self.assertEqual(result['covered_unique_original_refs'], 1)
            self.assertEqual((id1/'maps/vf0000.bsp').read_bytes(), b'rocks mushrooms and flora')
            self.assertTrue((id1/receipt['assets'][0]['sprite_asset_name']).is_file())
            self.assertEqual(result['runtime_validation'], 'pending')

    def test_rejects_stale_assets_without_mutating_map(self):
        with tempfile.TemporaryDirectory() as temp:
            overlay, id1, receipt = self.fixture(Path(temp))
            receipt['assets'][0]['sha256'] = 'stale'
            with self.assertRaisesRegex(ValueError, 'shared sprite'):
                self.run_install(overlay, id1, receipt)
            self.assertEqual((id1/'maps/vf0000.bsp').read_bytes(), b'rocks and mushrooms')

    def test_rejects_subset_changed_base_missing_coverage_and_unsafe_path(self):
        cases = ('subset','base','coverage','path')
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                overlay, id1, receipt = self.fixture(Path(temp))
                if case == 'subset': receipt['diagnostic_subset'] = True
                if case == 'base': receipt['regions'][0]['base_sha256'] = 'stale'
                if case == 'coverage': receipt['covered_unique_original_refs'] = 2
                if case == 'path': receipt['assets'][0]['sprite_asset_name'] = '../escape.spr'
                with self.assertRaises(ValueError):
                    self.run_install(overlay, id1, receipt)
                self.assertEqual((id1/'maps/vf0000.bsp').read_bytes(), b'rocks and mushrooms')


if __name__ == '__main__':
    unittest.main()
