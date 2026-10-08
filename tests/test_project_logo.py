# SPDX-License-Identifier: GPL-3.0-only
"""The README logo and the name-only logo are the current project media."""
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOGO = 'resources/media/AmiWind_logo.png'
NAME = 'resources/media/AmiWind_logo_name_only.png'
WORDMARK = 'resources/media/AmiWind_wordmark.png'
REMOVED = ('AmiWind_logo_clear_background.png',)


def png_header(path):
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise ValueError(f'not a PNG: {path}')
    width, height, depth, colour = struct.unpack('>IIBB', data[16:26])
    return width, height, depth, colour


def frozen(name):
    return (name.startswith('docs/PATCH-') or name.startswith('docs/journals/')
            or name.startswith('docs/RELEASE-v') or name.startswith('docs/validation/')
            or name in ('docs/BUGS-v0.0.29-RC1.md', 'docs/RC2_ISSUE_CHECKPOINT.md',
                        'tests/test_project_logo.py'))


class ProjectLogoTests(unittest.TestCase):
    def test_readme_shows_the_project_logo(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn(f'<img src="{LOGO}"', readme.splitlines()[1])

    def test_logo_files_are_rgba_pngs(self):
        self.assertEqual(png_header(ROOT / LOGO), (2172, 724, 8, 6))
        width, height, depth, colour = png_header(ROOT / NAME)
        self.assertEqual((depth, colour), (8, 6))
        self.assertGreater(width, 4 * height)
        self.assertEqual(png_header(ROOT / WORDMARK)[2:], (8, 6))

    def test_logo_files_ship_and_are_the_builder_inputs(self):
        shipped = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        self.assertIn(LOGO, shipped)
        self.assertIn(NAME, shipped)
        self.assertIn(WORDMARK, shipped)
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("logo=ROOT/'resources/media/AmiWind_wordmark.png'", build)
        toolkit = (ROOT / 'amiwind-toolkit' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('src="../resources/media/AmiWind_logo_name_only.png"', toolkit)

    def test_removed_logo_files_stay_removed(self):
        shipped = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        for old in REMOVED:
            self.assertFalse((ROOT / 'resources' / 'media' / old).exists(), old)
            self.assertFalse(any(name.endswith('/' + old) for name in shipped), old)
        for name in shipped:
            path = ROOT / name
            if frozen(name) or not path.is_file() or path.suffix not in ('.md', '.py', '.html', '.json', '.txt', '.sh', ''):
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for old in REMOVED:
                self.assertNotIn(old, text, f'{name} still references {old}')
        ignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
        for old in REMOVED:
            self.assertNotIn(old, ignore)

    def test_startup_lines_name_the_engine(self):
        source = (ROOT / 'tools' / 'prepare_logo.py').read_text(encoding='utf-8')
        self.assertIn("STARTUP_LINES = ('An open-source RPG engine', 'for the Commodore Amiga')", source)
        self.assertNotIn('demake', source)


if __name__ == '__main__':
    unittest.main()
