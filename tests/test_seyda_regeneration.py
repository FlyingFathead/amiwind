# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-SEYDA-REGEN-30: the image build must give the Seyda partition its
canonical terrain source while terrain culling is enabled."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_seyda_regions  # noqa: E402


class SeydaRegenerationTests(unittest.TestCase):
    def test_image_build_passes_canonical_land_source(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--canonical-land-source'", text)
        self.assertIn("canonical_land_source=getattr(args,'canonical_land_source',None)", text)

    def test_enabled_culling_without_source_stops_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'maps'
            with self.assertRaisesRegex(ValueError, 'requires --canonical-land-source'):
                prepare_seyda_regions.convert(Path(tmp) / 'missing.bsp', destination,
                                              source_map=Path(tmp) / 'missing.map',
                                              palette=Path(tmp) / 'missing.lmp',
                                              ericw_bin=Path(tmp), terrain_visual_cull=True)
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
