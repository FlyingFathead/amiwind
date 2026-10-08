# SPDX-License-Identifier: GPL-3.0-only
"""No released source file carries unresolved merge-conflict markers.

The preflight checks bytes and whitespace, not merge leftovers, and Markdown or JSON with markers still
passes the other tests (a journal once reached a green gate that way). Setext heading lines made of '='
are legitimate in Markdown, so only the unambiguous '<<<<<<< ' and '>>>>>>> ' markers are refused.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(rb'^(<<<<<<< |>>>>>>> )', re.M)


class MergeMarkerTests(unittest.TestCase):
    def test_released_files_have_no_merge_markers(self):
        names = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        bad = [n for n in names if (ROOT / n).is_file() and MARKER.search((ROOT / n).read_bytes())]
        self.assertEqual(bad, [], 'unresolved merge markers in: ' + ', '.join(bad))

    def test_marker_pattern_catches_both_sides(self):
        self.assertTrue(MARKER.search(b'x\n<<<<<<< HEAD\na\n=======\nb\n>>>>>>> branch\n'))
        self.assertIsNone(MARKER.search(b'Title\n=======\ntext\n'))


if __name__ == '__main__':
    unittest.main()
