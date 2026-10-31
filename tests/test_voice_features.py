# SPDX-License-Identifier: GPL-3.0-only
"""The voices and sounds tracker (tools/voice_features.py, VOICE-COVERAGE-58): the json is valid, every bug it names
is in the register, the page is current, and every moment kind the voice table holds has a row."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import voice_features as V   # noqa: E402


class VoiceFeatures(unittest.TestCase):
    def setUp(self):
        self.doc = V.load()

    def test_valid_and_current(self):
        self.assertEqual(V.problems(self.doc), [])
        self.assertFalse(V.stale(self.doc), 'docs/VOICE_FEATURES.md stale: run tools/voice_features.py render')

    def test_problems_are_named(self):
        doc = {'schema': V.SCHEMA, 'rows': [
            {'id': 'a', 'part': 'p', 'moment': 'm', 'state': 'heard', 'mapped': '', 'proof': '', 'bugs': ['NOPE-1']},
            {'id': 'a', 'part': 'p', 'moment': 'm', 'state': 'loud', 'mapped': '', 'proof': '', 'bugs': []}]}
        found = '\n'.join(V.problems(doc, known=set()))
        for needle in ('needs its proof', 'NOPE-1 is not in the register', 'id used twice', "state 'loud'"):
            self.assertIn(needle, found)

    def test_every_moment_kind_has_a_row(self):
        text = ' '.join(r['moment'].casefold() for r in self.doc['rows'])
        for moment in ('hello', 'greeting', 'idle', 'attack', 'hit', 'flee', 'intruder', 'thief', 'alarm',
                       'moan', 'roar', 'scream', 'land', 'footsteps', 'swish', 'punch', 'spell', 'tribunal'):
            self.assertIn(moment, text)

    def test_out_of_scope_says_why(self):
        for row in self.doc['rows']:
            if row['state'] in ('out-of-scope', 'silent-by-design'):
                self.assertTrue(row['mapped'] or row['proof'], row['id'])


if __name__ == '__main__':
    unittest.main()
