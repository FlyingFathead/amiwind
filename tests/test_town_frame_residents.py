# SPDX-License-Identifier: GPL-3.0-only
"""Town frame residents: one owner per resident, original LAND under ground residents, the wide support
search ring (CHIM-VIVEC-FRAME-WIDE-41)."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import town_grid                                    # noqa: E402
from town_config import load_settings               # noqa: E402

# Original positions (Morrowind units) of the three residents the v0.0.41-dev2 image gate refused.
NELS = {'number': 204678, 'id': 'nels llendo', 'type': 'NPC_', 'position': [6582.37, -68928.76, 536.10]}
DREAMER = {'number': 297836, 'id': 'Dreamer_Talker11', 'type': 'NPC_', 'position': [35166.36, -69269.32, 581.05]}
PILUS = {'number': 388940, 'id': 'pilus amatius', 'type': 'NPC_', 'position': [14780.32, -102581.55, 699.51]}


class ResidentOwnership(unittest.TestCase):
    def test_town_frames_see_each_others_owned_cells(self):
        self.assertEqual(town_grid.foreign_owned_cells('vivec_city'), [('seyda', (-3, -11), (1, -7)),
                                                                       ('balmora', (-4, -3), (-1, 0))])
        self.assertEqual(town_grid.foreign_owned_cells('seyda'), [('balmora', (-4, -3), (-1, 0)),
                                                                  ('vivec_city', (1, -14), (7, -8))])

    def test_a_resident_in_a_neighbours_owned_cell_is_left_to_that_town(self):
        from import_town import resident_cast
        vivec = load_settings('vivec_city')
        self.assertEqual(town_grid.physical_cell(NELS), (0, -9))
        cast, left = resident_cast([NELS, DREAMER, PILUS], vivec)
        self.assertEqual([r['number'] for r in cast], [297836, 388940])
        self.assertEqual(left, [{'reference': 204678, 'id': 'nels llendo', 'cell': [0, -9], 'owner': 'seyda'}])

    def test_unowned_apron_cells_and_exclusions_are_unchanged(self):
        from import_town import resident_cast
        settings = dict(load_settings('vivec_city'), resident_exclusions={'pilus amatius': 'test reason'})
        apron = dict(NELS, number=1, position=[7 * 8192 + 100., -12 * 8192 + 100., 0.])   # cell 7,-12: no town
        cast, left = resident_cast([apron, PILUS, dict(PILUS, number=2, type='STAT')], settings)
        self.assertEqual([r['number'] for r in cast], [1])
        self.assertEqual(left, [])

    def test_no_resident_is_placed_by_two_town_frames(self):
        """Seyda Neen, Balmora and Vivec own disjoint cells, so resident_owner gives every cell at most one town."""
        owners = {}
        for town in ('seyda', 'balmora', 'vivec_city'):
            for other, low, high in town_grid.foreign_owned_cells(town):
                for x in range(low[0], high[0]):
                    for y in range(low[1], high[1]):
                        owners.setdefault((x, y), set()).add(other)
        self.assertTrue(all(len(v) == 1 for v in owners.values()))
        self.assertEqual(len(owners), 16 + 9 + 36)


class ResidentLandDetail(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings('vivec_city')
        self.low, self.high = [-6912, -6400], [6912, 7424]   # frame_ground_bounds of vivec_city

    def local(self, ref):
        return [(ref['position'][k] - self.settings['centre'][k]) * self.settings['scale'] for k in range(2)]

    def tiles(self, refs, ground):
        from chim.build import resident_detail_tiles
        return resident_detail_tiles(None, self.settings, ground, self.low, self.high, 128, references=refs)

    def test_ground_residents_get_the_tiles_of_their_support_search(self):
        x, y = self.local(PILUS)
        tiles = self.tiles([PILUS], lambda gx, gy: PILUS['position'][2] * .25 - 20)
        reach = range(math.floor((x - 48 + 6912) / 128), math.floor((x + 48 + 6912) / 128) + 1)
        reach_y = range(math.floor((y - 48 + 6400) / 128), math.floor((y + 48 + 6400) / 128) + 1)
        self.assertEqual(tiles, {(-6912 + i * 128, -6400 + j * 128) for i in reach for j in reach_y})
        self.assertTrue(all(t[0] <= x + 48 and t[0] + 128 >= x - 48 for t in tiles))

    def test_raised_or_foreign_residents_keep_the_plain_tiles(self):
        on_roof = self.tiles([PILUS], lambda gx, gy: PILUS['position'][2] * .25 - 33)
        self.assertEqual(on_roof, set())
        self.assertEqual(self.tiles([NELS], lambda gx, gy: NELS['position'][2] * .25), set())   # Seyda Neen's
        self.assertTrue(self.tiles([DREAMER], lambda gx, gy: DREAMER['position'][2] * .25 - 5))

    def test_detail_tiles_take_the_original_samples(self):
        from chim.build import shoreline_ground

        def sample(x, y):            # dry ground whose 32-unit samples a 128-unit tile misses
            return 400. + 8 * ((x // 32) % 4) * ((y // 32) % 4), 0
        plain = shoreline_ground(sample, [[0, 0]], (0, 0), (256, 128), 128, shoreline=False)
        detail = shoreline_ground(sample, [[0, 0]], (0, 0), (256, 128), 128, shoreline=False, detail={(0, 0)})
        self.assertEqual(plain.refined, set())
        self.assertEqual(detail.refined, {(0, 0), (1, 0)})
        self.assertEqual(plain.height(96, 96), 400.)
        self.assertEqual(detail.height(96, 96), sample(96, 96)[0])
        self.assertEqual(detail.height(192, 64), plain.height(192, 64))

    def test_the_switch_keeps_the_previous_method(self):
        from chim.build import resident_detail_on
        self.assertTrue(resident_detail_on(None))
        self.assertTrue(resident_detail_on({'terrain_resident_detail': 'on'}))
        self.assertFalse(resident_detail_on({'terrain_resident_detail': 'off'}))
        with self.assertRaises(ValueError):
            resident_detail_on({'terrain_resident_detail': 'maybe'})


class WideSupportSearch(unittest.TestCase):
    """The wide ring (32 to 48 units) runs only after the 32-unit search (project decision, CHIM-VIVEC-FRAME-WIDE-41)."""

    def fitter(self, fits):
        import actor_grounding

        class Scene:
            def floor(self, point, drop):
                return {'status': 'supported', 'height': 0.}

        class Fitter(actor_grounding._Fitter):
            def __init__(self):
                pass

            def _setup(self, name, e, authored, angles):
                return [(0., 0., 0.)], Scene(), {'status': 'supported', 'height': 0.}

            def owned(self, name, candidate):
                return True

            @staticmethod
            def contact(s, point, samples):
                return fits(point)

            @staticmethod
            def path_clear(s, old, new, base):
                return True
        return Fitter()

    def fit(self, mode, fits):
        from unittest.mock import patch
        with patch.dict('os.environ', {'AMIWIND_ACTOR_SEARCH': mode}):
            return self.fitter(fits).fit('frame', {}, [0., 0., 0.], (0., 0., 0.))

    def test_the_ring_follows_the_32_unit_search(self):
        import actor_grounding as g
        self.assertTrue(all(32 < math.hypot(*p) <= 48 for p in g.WIDE_RING))
        self.assertFalse(set(g.WIDE_RING) & set(g.OFFSETS))
        self.assertEqual(g.WIDE_RING, sorted(g.WIDE_RING, key=lambda p: (p[0]*p[0]+p[1]*p[1], p)))
        from unittest.mock import patch
        with patch.dict('os.environ', {'AMIWIND_ACTOR_SEARCH': ''}):
            self.assertEqual(g.search_offsets()[:len(g.OFFSETS)], g.OFFSETS)
            self.assertEqual(len(g.search_offsets()), len(g.OFFSETS) + len(g.WIDE_RING))
        with patch.dict('os.environ', {'AMIWIND_ACTOR_SEARCH': 'near'}):
            self.assertEqual(g.search_offsets(), g.OFFSETS)
        with patch.dict('os.environ', {'AMIWIND_ACTOR_SEARCH': 'far'}), self.assertRaises(ValueError):
            g.search_offsets()

    def test_an_actor_the_32_unit_search_places_never_moves(self):
        near = self.fit('near', lambda p: p[0] >= 10)
        wide = self.fit('wide', lambda p: p[0] >= 10)
        self.assertEqual(near, wide)
        self.assertEqual(wide['placed_origin'][:2], [10.0, 0.0])

    def test_only_the_wide_ring_places_a_steep_slope_actor(self):
        import actor_grounding as g
        near = self.fit('near', lambda p: p[0] >= 38)
        self.assertEqual((near['status'], near['attempts']), ('unresolved-mesh-contact', len(g.OFFSETS)))
        wide = self.fit('wide', lambda p: p[0] >= 38)
        self.assertEqual(wide['mesh_contact'], 'fitted')
        self.assertEqual(wide['placed_origin'][:2], [38.0, 0.0])
        self.assertGreater(wide['attempts'], len(g.OFFSETS))


if __name__ == '__main__':
    unittest.main()
