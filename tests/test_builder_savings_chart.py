# SPDX-License-Identifier: GPL-3.0-only
"""The builder savings chart is drawn from its JSON (tools/builder_savings_chart.py): every value is
labelled measured or estimated, the chart in docs/images exists and is release-listed, and the
renderer draws a PNG of the same size from the same numbers."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
READY = importlib.util.find_spec('PIL') is not None


class BuilderSavingsChart(unittest.TestCase):
    def data(self):
        return json.loads((ROOT / 'docs/performance/builder-savings.json').read_text(encoding='utf-8'))

    def test_every_value_says_measured_or_estimated(self):
        data = self.data()
        self.assertTrue(data['items'])
        for item in data['items']:
            for key in ('before', 'after'):
                self.assertGreater(item[key], 0, item['label'])
                self.assertIn(item[key + '_kind'], ('measured', 'estimated'), item['label'])
            self.assertTrue(item['source'] and item['fixes'], item['label'])
        self.assertTrue(data['caption'])

    def test_chart_is_published_with_its_data(self):
        listed = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for name in ('docs/images/amiwind-builder-savings.png', 'docs/performance/builder-savings.json',
                     'tools/builder_savings_chart.py'):
            self.assertIn(name, listed)
        png = (ROOT / 'docs/images/amiwind-builder-savings.png').read_bytes()
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        self.assertIn('amiwind-builder-savings.png', (ROOT / 'docs/performance/BUILDER_PROFILE.md').read_text(encoding='utf-8'))

    @unittest.skipUnless(READY, 'Pillow required')
    def test_renderer_draws_the_same_size(self):
        import io
        from PIL import Image
        import builder_savings_chart
        drawn = Image.open(io.BytesIO(builder_savings_chart.render(self.data())))
        stored = Image.open(ROOT / 'docs/images/amiwind-builder-savings.png')
        self.assertEqual(drawn.size, stored.size)


if __name__ == '__main__':
    unittest.main()
