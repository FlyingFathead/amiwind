# SPDX-License-Identifier: GPL-3.0-only
"""The stable reference ids (tools/ref_identity.py, CELL-CHANGES-59): the key of the engine's world change list and
the saved games, made at build time from (content file, reference number). Synthetic numbers only; no game data."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ref_identity as R  # noqa: E402


class RefIdentityTests(unittest.TestCase):
    def test_morrowind_numbers_are_their_own_ids(self):
        # every save made before the table keeps its keys
        for n in (1, 172851, 484475, 484481, R.NUMBER_LIMIT - 1):
            self.assertEqual(R.stable_ref('Morrowind.esm', n), n)
        self.assertEqual(R.stable_ref('morrowind.ESM', 7), 7)

    def test_the_masters_never_collide(self):
        ids = {}
        for name in R.CONTENT_FILES:
            for n in (1, 2, 26408, 33635, 484481):
                ref = R.stable_ref(name, n)
                self.assertNotIn(ref, ids, (name, n, ids.get(ref)))
                ids[ref] = (name, n)
                self.assertLess(ref, 0x800000)           # below the old saves' builder-made roles
                self.assertEqual(R.split(ref), (name, n))
        self.assertEqual(R.stable_ref('Tribunal.esm', 5), (1 << 20) + 5)
        self.assertEqual(R.stable_ref('Bloodmoon.esm', 5), (2 << 20) + 5)

    def test_the_fixed_order_is_by_name_not_build_order(self):
        self.assertEqual(R.CONTENT_FILES[:3], ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'))
        self.assertLessEqual(len(R.CONTENT_FILES), 8)    # FILE_INDEX * 2**20 stays below 2**23

    def test_a_plugins_reference_to_its_master(self):
        masters = ('Morrowind.esm',)
        # high byte 0: the plugin's own; 1: its first master's (the same object as there)
        self.assertEqual(R.stable_ref_of_frmr(42, 'Tribunal.esm', masters), R.stable_ref('Tribunal.esm', 42))
        self.assertEqual(R.stable_ref_of_frmr((1 << 24) | 42, 'Tribunal.esm', masters), 42)
        # a high byte past the master list counts as the plugin's own (tools/door_graph.py's rule)
        self.assertEqual(R.stable_ref_of_frmr((5 << 24) | 42, 'Tribunal.esm', masters), R.stable_ref('Tribunal.esm', 42))

    def test_refusals(self):
        with self.assertRaises(R.RefIdentityError):
            R.stable_ref('Unknown.esp', 1)
        with self.assertRaises(R.RefIdentityError):
            R.stable_ref('Morrowind.esm', 0)
        with self.assertRaises(R.RefIdentityError):
            R.stable_ref('Morrowind.esm', R.NUMBER_LIMIT)
        for bad in (0, 0x800000, 3 << 20, (1 << 20)):
            with self.assertRaises(R.RefIdentityError):
                R.split(bad)

    def test_the_lists_use_it(self):
        focus = (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8')
        items = (ROOT / 'tools/prepare_item_models.py').read_text(encoding='utf-8')
        self.assertIn('from ref_identity import stable_ref', focus)
        self.assertIn('from ref_identity import stable_ref', items)


if __name__ == '__main__':
    unittest.main()
