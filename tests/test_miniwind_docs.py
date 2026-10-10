# SPDX-License-Identifier: GPL-3.0-only
"""docs/MINIWIND.md lists every MiniWind preset (config/miniwind-presets.json) with its option and scene."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding='utf-8')


class MiniWindPageTests(unittest.TestCase):
    def setUp(self):
        page = read('docs/MINIWIND.md')
        start = page.index('<!-- presets start -->')
        self.table = page[start:page.index('<!-- presets end -->')]
        self.presets = json.loads(read('config/miniwind-presets.json'))['presets']

    def test_every_preset_is_listed_with_option_and_scene(self):
        for row in self.presets:
            with self.subTest(preset=row['name']):
                self.assertIn('| `%s` |' % row['name'], self.table)
                self.assertIn('`--miniwind-%s`' % row['name'], self.table)
                self.assertIn(row['description'], self.table)

    def test_page_lists_no_unknown_preset(self):
        listed = [line.split('|')[1].strip(' `') for line in self.table.splitlines() if line.startswith('| `')]
        self.assertEqual(sorted(listed), sorted(row['name'] for row in self.presets))

    def test_page_is_linked(self):
        for name in ('README.md', 'docs/MINIWIND_PLAYTESTER.md', 'docs/chim/build_guide/MINIWIND.md',
                     'docs/LINUX_BUILD.md'):
            with self.subTest(file=name):
                self.assertRegex(read(name), r'(?<![A-Z_])MINIWIND\.md')

    def test_page_is_in_the_release_files(self):
        files = json.loads(read('tools/release-files.json'))
        listed = files if isinstance(files, list) else sum((v for v in files.values() if isinstance(v, list)), [])
        self.assertIn('docs/MINIWIND.md', listed)
        self.assertIn('tests/test_miniwind_docs.py', listed)


if __name__ == '__main__':
    unittest.main()
