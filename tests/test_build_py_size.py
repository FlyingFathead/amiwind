# SPDX-License-Identifier: GPL-3.0-only
"""tools/build.py keeps room under the release text size limit (BUILD-PY-AT-TEXT-LIMIT-49).

build.py stood a few bytes under the limit of tools/release.py, so the next builder change would have stopped the
release preflight. Its command-line option groups moved to tools/build_parser.py. This test fails while there is
still a tenth of the limit left, so the next split happens in a normal change, not on a release day.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import release  # noqa: E402

SHARE = 0.90


class BuildPySizeTests(unittest.TestCase):
    def test_build_py_leaves_a_tenth_of_the_limit(self):
        limit = release.text_limit('tools/build.py')
        size = (ROOT / 'tools' / 'build.py').stat().st_size
        self.assertLessEqual(size, int(limit * SHARE),
                             'tools/build.py is %d bytes, over %d %% of the %d-byte release text limit: move a '
                             'cohesive part (option groups: tools/build_parser.py) out of it' % (size, SHARE * 100, limit))

    def test_the_option_groups_stay_in_their_module(self):
        limit = release.text_limit('tools/build_parser.py')
        self.assertLessEqual((ROOT / 'tools' / 'build_parser.py').stat().st_size, int(limit * SHARE))


if __name__ == '__main__':
    unittest.main()
