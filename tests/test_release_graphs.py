# SPDX-License-Identifier: GPL-3.0-only
"""tools/release_graphs.py: honesty rules, PNG output, and the committed release graphs."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import release
import release_graphs

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).with_name('release_graphs_fixture.json')
MEASUREMENTS = ROOT / 'docs/performance/CHIM-v0.0.33-MEASUREMENTS.json'
HAVE_PIL = importlib.util.find_spec('PIL') is not None


def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


class RuleTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertTrue(release_graphs.validate(fixture()))
        self.assertEqual(release_graphs.main(['check', str(FIXTURE)]), 0)

    def broken(self, change):
        data = fixture()
        change(data)
        with self.assertRaises(release_graphs.GraphError):
            release_graphs.validate(data)

    def test_a_series_cannot_be_left_out_of_a_row(self):
        self.broken(lambda d: d['charts'][0]['panels'][0]['rows'][0]['values'].pop())
        self.broken(lambda d: d['charts'][0]['panels'][0]['rows'][1]['missing'].pop())

    def test_emulator_and_timing_panels_must_name_the_host_load(self):
        def emu(d):
            d['charts'][0]['panels'][1]['host'] = 'n/a'
        self.broken(emu)

        def timing(d):
            p = d['charts'][0]['panels'][0]
            p['unit'], p['host'] = 's', 'n/a'
        self.broken(timing)

    def test_mixed_host_needs_a_label_on_every_measured_bar(self):
        self.broken(lambda d: d['charts'][0]['panels'][1]['rows'][0]['hosts'].__setitem__(1, None))
        self.broken(lambda d: d['charts'][0]['panels'][1]['rows'][0].pop('hosts'))

    def test_values_are_non_negative_numbers_or_null(self):
        self.broken(lambda d: d['charts'][0]['panels'][0]['rows'][0]['values'].__setitem__(0, -1))
        self.broken(lambda d: d['charts'][0]['panels'][0]['rows'][0]['values'].__setitem__(0, '12'))
        self.broken(lambda d: d['charts'][0]['panels'][0]['rows'][0]['values'].__setitem__(0, True))

    def test_file_names_and_ids(self):
        self.broken(lambda d: d['charts'][0].__setitem__('file', 'tiny.png'))
        self.broken(lambda d: d['charts'].append(copy.deepcopy(d['charts'][0])))
        self.broken(lambda d: d.__setitem__('schema', 'other'))

    def test_ratio_wording_is_less_or_more_never_better(self):
        self.assertEqual(release_graphs._ratio([100, 10], True), '10x less')
        self.assertEqual(release_graphs._ratio([40, 60], True), '1.5x more')
        self.assertEqual(release_graphs._ratio([40, 40], True), 'same')
        self.assertEqual(release_graphs._ratio([40, None], True), '')

    def test_axis_tops(self):
        self.assertEqual(release_graphs._nice_max(97), 100)
        self.assertEqual(release_graphs._nice_max(101), 120)
        self.assertEqual(release_graphs._nice_max(0), 1.0)

    def test_unknown_only_id_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(release_graphs.main(['write', str(FIXTURE), '--out', d, '--only', 'nope']), 1)


@unittest.skipUnless(HAVE_PIL, 'Pillow is not installed')
class RenderTests(unittest.TestCase):
    def test_fixture_renders_a_small_palette_png(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(release_graphs.main(['write', str(FIXTURE), '--out', d]), 0)
            path = Path(d) / 'amiwind-v0.0.0-tiny.png'
            with Image.open(path) as im:
                self.assertEqual(im.format, 'PNG')
                self.assertEqual(im.mode, 'P')
                self.assertEqual(im.width, release_graphs.WIDTH)
                self.assertLessEqual(len(im.getcolors(256)), 32)
            self.assertLess(path.stat().st_size, 60_000)


class CommittedGraphTests(unittest.TestCase):
    def test_measurements_are_valid(self):
        self.assertEqual(release_graphs.main(['check', str(MEASUREMENTS)]), 0)

    def test_every_graph_is_committed_and_listed(self):
        data = release_graphs.load(MEASUREMENTS)
        listed = set(json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8')))
        ignore = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
        self.assertIn('docs/performance/CHIM-v0.0.33-MEASUREMENTS.json', listed)
        for chart in data['charts']:
            name = 'docs/images/' + chart['file']
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertIn(name, release.DOCUMENTATION_IMAGES)
                self.assertIn(name, listed)
                self.assertIn('!/' + name, ignore)


if __name__ == '__main__':
    unittest.main()
