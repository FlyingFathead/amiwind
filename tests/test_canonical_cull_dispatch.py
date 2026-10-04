# SPDX-License-Identifier: GPL-3.0-only
"""Required canonical input gates run before any private geometry or build."""
import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from cull_bsp_terrain import cull_bsp
from prepare_seyda_regions import convert
class CanonicalDispatchTests(unittest.TestCase):
    def test_off_is_exact_without_canonical_input(self):
        raw=b'OFF original';out,receipt=cull_bsp(raw,{'enabled':False,'overlap':.5},require_canonical=True)
        self.assertIs(out,raw);self.assertTrue(receipt['disabled'])
    def test_enabled_requires_npz(self):
        with self.assertRaisesRegex(ValueError,'direct canonical'):
            cull_bsp(b'',{'enabled':True,'overlap':.5})
    def test_origin_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'origin'):
            cull_bsp(b'',{'enabled':True,'overlap':.5},canonical_land_source='synthetic.npz')
    def test_canonical_dispatch_passes_policy_and_origin(self):
        policy={'enabled':True,'overlap':2.5}
        with patch('canonical_land_reference.CanonicalLand') as land,patch('canonical_bsp_cull.cull_bsp',return_value=(b'new',{'fixture':True})) as invoke:
            result=cull_bsp(b'old',policy,canonical_land_source='fixture.npz',canonical_origin=[1,2,3],require_canonical=True)
            land.assert_called_once_with('fixture.npz',[1,2,3]);invoke.assert_called_once_with(b'old',land.return_value,policy)
            self.assertEqual(result[0],b'new')
    def test_seyda_missing_input_blocks_before_build_or_write(self):
        with tempfile.TemporaryDirectory() as tmp,patch('prepare_bounded_world.build_candidate') as build:
            target=Path(tmp)/'new-maps'
            with self.assertRaisesRegex(ValueError,'canonical-land-source'):
                convert(Path(tmp)/'old.bsp',target,source_map='unused',palette='unused',ericw_bin='unused',terrain_cull_config={'default':True,'overlap':.5})
            build.assert_not_called();self.assertFalse(target.exists())
if __name__=='__main__':unittest.main()
