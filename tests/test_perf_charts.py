# SPDX-License-Identifier: GPL-3.0-only
"""The committed performance charts match tools/perf_charts.py and are valid SVG."""
import tempfile, unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import perf_charts

ROOT = Path(__file__).resolve().parents[1]


class PerfChartTests(unittest.TestCase):
    def test_committed_charts_are_current(self):
        self.assertEqual(perf_charts.main(['check', '--out', str(ROOT / 'docs/images')]), 0)

    def test_charts_are_well_formed_svg_with_every_row(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(perf_charts.main(['write', '--out', d]), 0)
            vis = ET.parse(Path(d) / 'amiwind-perf-visibility-by-map.svg').getroot()
            faces = ET.parse(Path(d) / 'amiwind-perf-faces-world-vs-funcwall.svg').getroot()
            ET.parse(Path(d) / 'amiwind-perf-seyda-crossing-load.svg')
        texts = [t.text for t in vis.iter('{http://www.w3.org/2000/svg}text')]
        for name, pct in perf_charts.VISIBILITY:
            self.assertIn(name, texts); self.assertIn('%d%%' % pct, texts)
        self.assertEqual(sum(1 for t in faces.iter('{http://www.w3.org/2000/svg}text') if 'in func_walls' in (t.text or '')),
                         len(perf_charts.FACES))


if __name__ == '__main__':
    unittest.main()
