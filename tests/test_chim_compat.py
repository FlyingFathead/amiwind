# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM compatibility table (tools/chim_compat.py, config/chim-compatibility.json; BUILD-CHIM-LABEL-IN-KEYS-48)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import chim_compat  # noqa: E402

ROWS = [{'version': '0.2.1', 'line': '0.2.1', 'reason': 'output change'},
        {'version': '0.2.2', 'line': '0.2.1', 'reason': 'label only'},
        {'version': '0.3.0', 'line': '0.3.0', 'reason': 'new world format'}]


class ChimCompatTests(unittest.TestCase):
    def test_the_repository_table_is_valid_and_rendered(self):
        self.assertEqual(chim_compat.problems(ROOT), [])

    def test_the_current_label_is_listed(self):
        rows = chim_compat.load(ROOT)
        self.assertIn(chim_compat.label(ROOT), [row['version'] for row in rows])

    def test_0_2_2_reads_what_0_2_1_built(self):
        rows = chim_compat.load(ROOT)
        self.assertEqual(chim_compat.line_of('0.2.2', rows), '0.2.1')
        self.assertEqual(chim_compat.reads('0.2.2', rows), ['0.2.1', '0.2.2'])
        self.assertEqual(chim_compat.reads('0.2.1', rows), ['0.2.1'])

    def test_key_bytes_replace_the_label_by_its_line(self):
        self.assertEqual(chim_compat.key_bytes(b'0.2.2\n', ROWS), b'0.2.1\n')
        self.assertEqual(chim_compat.key_bytes(b'0.2.1\n', ROWS), b'0.2.1\n')
        self.assertEqual(chim_compat.key_bytes(b'0.3.0\n', ROWS), b'0.3.0\n')
        with self.assertRaises(ValueError):
            chim_compat.key_bytes(b'0.4.0\n', ROWS)

    def problems(self, rows, label='0.2.2'):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            (root / 'config' / 'chim-compatibility.json').write_text(json.dumps({'versions': rows}))
            (root / 'CHIM_VERSION').write_text(label + '\n')
            return chim_compat.problems(root)

    def test_table_rules(self):
        self.assertEqual(self.problems(ROWS), [])
        self.assertTrue(self.problems(ROWS, label='0.2.3'))                                   # bump without a row
        self.assertTrue(self.problems([ROWS[1], ROWS[0]]))                                    # not oldest first
        self.assertTrue(self.problems(ROWS[:1] + [dict(ROWS[1], line='0.2.5')]))              # line newer than it
        self.assertTrue(self.problems([dict(ROWS[0], line='0.2.0'), ROWS[1]]))                # line not a row
        self.assertTrue(self.problems(ROWS[:1] + [dict(ROWS[1], reason='')]))                 # no reason
        self.assertTrue(self.problems(ROWS + [dict(ROWS[2], version='0.3.1', line='0.2.2')]))  # line not its own


if __name__ == '__main__':
    unittest.main()
