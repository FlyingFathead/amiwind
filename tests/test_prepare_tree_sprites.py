# SPDX-License-Identifier: GPL-3.0-only
import math
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_tree_sprites import select_census, validate_sprite

class PrepareTreeSpritesTests(unittest.TestCase):
    def test_census_subset_is_explicit_and_retains_different_sizes(self):
        refs = [{'model': 'f/Flora_tree_01.NIF', 'type': 'STAT', 'scale': scale,
                 'number': i, 'position': [1, 2, 3], 'rotation_radians': [.1, .2, .3], 'cell': [0, 0]}
                for i, scale in enumerate((.5, 1, 2.37))]
        census = {'master_sha256': 'a' * 64, 'references': refs}
        master, selected = select_census(census, ['meshes/f/flora_tree_01.nif'])
        self.assertEqual([r['scale'] for r in selected], [.5, 1, 2.37])
        self.assertEqual(selected[2]['rotation_radians'], refs[2]['rotation_radians'])
        self.assertEqual(refs[0]['model'], 'f/Flora_tree_01.NIF')
        with self.assertRaisesRegex(ValueError, 'absent'):
            select_census(census, ['f/flora_tree_02.nif'])

    def test_census_rejects_street_false_positive_and_unsupported_semantics(self):
        with self.assertRaises(ValueError):
            select_census({'master_sha256': 'a' * 64, 'references': [{'model': 'l/light_streetlight.nif'}]})
        with self.assertRaises(ValueError):
            select_census({'master_sha256': 'a' * 64, 'references': [{'model': 'f/flora_tree.nif', 'type': 'NPC_'}]})

    def test_sprite_dimensions_match_pixels_and_reject_malformed_output(self):
        raw = struct.pack('<4siifiiifi', b'IDSP', 1, 2, 10., 4, 8, 1, 0., 0)
        raw += struct.pack('<5i', 0, -2, 6, 4, 8) + bytes(32)
        self.assertEqual(validate_sprite(raw)['pixel_bytes'], 32)
        self.assertEqual(validate_sprite(raw)['frame_origin'], [-2, 6])
        for invalid in (raw[:-1], b'bad', raw + b'\0'):
            with self.assertRaises(ValueError): validate_sprite(invalid)
        bad = bytearray(raw);struct.pack_into('<f', bad, 12, math.nan)
        with self.assertRaises(ValueError): validate_sprite(bad)

if __name__ == '__main__': unittest.main()
