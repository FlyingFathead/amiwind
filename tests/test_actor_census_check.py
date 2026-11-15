"""The actor placement check (OUTDOOR-CREATURES-MISSING-66): it fails on the v0.0.65 release numbers (a town map's
creatures never placed) and passes once the town cells join the actor table."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools', 'chim'))
import actor_census_check as acc  # noqa: E402

# measured on the v0.0.65 release run (2026_11_12_v0.0.65_full-v0.0.65-release_20c6b9c), town join off
V065 = {
    'exterior-region': {'CREA': {'original': 325, 'placed': 325}, 'LEVC': {'original': 4970, 'placed': 4970},
                        'NPC_': {'original': 527, 'placed': 527}, 'corpse': {'original': 8, 'placed': 8}},
    'exterior-town': {'CREA': {'original': 4, 'placed': 0}, 'LEVC': {'original': 112, 'placed': 0},
                      'NPC_': {'original': 34, 'placed': 34}, 'corpse': {'original': 1, 'placed': 1}},
}


class ActorCensusCheck(unittest.TestCase):
    def test_v065_numbers_fail(self):
        bad = acc.verdict(V065, {})
        self.assertEqual(len(bad), 2)
        self.assertTrue(any('exterior-town LEVC: 0 of 112' in b for b in bad))

    def test_fixed_numbers_pass(self):
        fixed = {a: {k: {'original': r['original'], 'placed': r['original']} for k, r in v.items()} for a, v in V065.items()}
        self.assertEqual(acc.verdict(fixed, {}), [])

    def test_allowlist_tracks_a_known_drop(self):
        allow = {'exterior-town/CREA': {'missing': 4, 'register': 'X'}, 'exterior-town/LEVC': {'missing': 112, 'register': 'X'}}
        self.assertEqual(acc.verdict(V065, allow), [])

    def test_town_core_rule(self):
        # Seyda Neen's slot of the v0.0.65 regions.awr: origin (-2816, -17920), core (-3328, -4608, 4864, 3584)
        awr = b'AWR2' + struct.pack('<I', 1) + struct.pack('<7f', -2816, -17920, 0, -3328, -4608, 4864, 3584) + \
            struct.pack('<7f', -5120, -3072, 0, -3072, -3072, 3072, 3072)
        cores = acc.town_cores(awr)
        self.assertEqual(len(cores), 2)
        self.assertEqual(acc.area_of((-2, -9), cores), 'exterior-town')     # Seyda Neen
        self.assertEqual(acc.area_of((0, -7), cores), 'exterior-region')    # the Ascadian Isles


if __name__ == '__main__':
    unittest.main()
