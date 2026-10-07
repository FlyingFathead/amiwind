# SPDX-License-Identifier: GPL-3.0-only
"""The public console command page must match the catalogue the game reads."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import console_commands_doc as doc


class ConsoleCommandPageTests(unittest.TestCase):
    def test_page_matches_catalogue(self):
        page = doc.render(doc.CATALOGUE.read_text(encoding='utf-8'))
        self.assertEqual(doc.PAGE.read_bytes().decode('utf-8'), page,
                         'run tools/console_commands_doc.py render')

    def test_aliases_share_one_row(self):
        page = doc.render('AWDC1\nG|luma indoor|h|<0..4>\nG|indoor luma|h|old\nG|luma|s|\n')
        self.assertIn('| `dbg luma indoor` | `dbg indoor luma` | <0..4> |', page)
        self.assertIn('| `dbg luma` | - | - |', page)

    def test_catalogue_is_sorted_with_each_group_once(self):
        text = doc.CATALOGUE.read_text(encoding='utf-8')
        self.assertEqual(text, doc.sorted_text(text), 'run tools/console_commands_doc.py sort')
        groups = [g for g, _, _, _ in doc.entries(text)]
        seen = []
        for g in groups:
            if not seen or seen[-1] != g:
                self.assertNotIn(g, seen, 'group split: ' + g); seen.append(g)

    def test_no_two_entries_share_words(self):
        words = [w.lower() for _, w, _, _ in doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))]
        self.assertEqual(sorted({w for w in words if words.count(w) > 1}), [])

    def test_every_handler_is_registered_in_the_engine(self):
        names = doc.registered_names(ROOT / 'engine/aga/src')
        rows = doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))
        self.assertEqual(sorted({h for _, _, h, _ in rows if h not in names}), [])

    def test_sort_orders_groups_by_first_appearance_and_words_alphabetically(self):
        out = doc.sorted_text('AWDC1\n# head\nB|zeta|z|\nA|beta|b|\nB|alpha|a|\nA|Alpha|c|\n')
        self.assertEqual(out, 'AWDC1\n# head\nB|alpha|a|\nB|zeta|z|\nA|Alpha|c|\nA|beta|b|\n')

    def test_rejects_malformed_catalogue(self):
        with self.assertRaises(ValueError):
            doc.render('AWDC0\n')
        with self.assertRaises(ValueError):
            doc.render('AWDC1\nG|words|\n')


if __name__ == '__main__':
    unittest.main()
