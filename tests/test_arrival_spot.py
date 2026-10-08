"""Town arrivals against converted collision (VIVEC-ARENA-TP-ARRIVAL-32).

Synthetic BSP29 payloads only: a floor, an optional wall over the requested
point and an optional water line. Real owned maps are checked by the image
step (tools/build_aga.py, arrival-check.json) with the same functions.
"""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from arrival_spot import Collision, standing_spot, standing, resolve, check, require  # noqa: E402
from player_hull import pack_lumps, PROFILE, STEP_HEIGHT  # noqa: E402


def payload(wall=None, water=-1000., spawn=(0, 0, 20)):
    """Floor at standing-origin z 0; wall: (low, high) box solid in hull 1."""
    data = [bytearray() for _ in range(15)]
    # World hull 1: one plane z=0, solid below.
    data[1] += struct.pack('<4fi', 0, 0, 1, 0, 2)
    data[9] += struct.pack('<ihh', 0, -1, -2)
    # World hull 0: water below the water line (contents only).
    data[1] += struct.pack('<4fi', 0, 0, 1, water, 2)
    data[5] += struct.pack('<ihh6h2H', 1, -1, -2, *([0] * 8))
    data[10] += b''.join(struct.pack('<ii6h2H4B', c, -1, *([0] * 12)) for c in (-1, -3))
    data[14] += struct.pack('<9f7i', *([0.] * 9), 0, 0, 0, 0, 2, 0, 0)
    entities = ['{\n"classname" "worldspawn"\n"aw_hull" "%s"\n}' % PROFILE,
                '{\n"classname" "info_player_start"\n"origin" "%s"\n}' % ' '.join(map(str, spawn))]
    if wall:
        low, high = wall
        root = len(data[9]) // 8
        for axis in range(3):
            for sign, bound in ((1, high[axis]), (-1, -low[axis])):
                normal = [0., 0., 0.]; normal[axis] = sign
                index = len(data[1]) // 20
                data[1] += struct.pack('<4fi', *normal, bound, 3)
                node = len(data[9]) // 8
                data[9] += struct.pack('<ihh', index, -1, node + 1 if node - root < 5 else -2)
        data[14] += struct.pack('<9f7i', *([0.] * 9), -1, root, -1, -1, 0, 0, 0)
        entities.append('{\n"classname" "func_wall"\n"model" "*1"\n"aw_ref" "171688"\n'
                        '"origin" "0 0 0"\n"angles" "0 0 0"\n}')
    data[0] = bytearray(('\n'.join(entities) + '\n\0').encode())
    return pack_lumps(data)


class ArrivalSpotTests(unittest.TestCase):
    def test_spot_is_the_engine_search_on_the_floor(self):
        c = Collision(payload())
        self.assertFalse(standing(c, (0, 0, 20)))           # 20 units above the floor
        spot = standing_spot(c, (0, 0, 20))
        self.assertEqual(spot[:2], (0, 0))
        self.assertAlmostEqual(spot[2], .25)
        self.assertTrue(standing(c, spot))
        self.assertTrue(standing(c, (0, 0, STEP_HEIGHT)))   # ground within a step
        self.assertFalse(standing(c, (0, 0, STEP_HEIGHT + 1)))

    def test_arrival_inside_a_wall_moves_to_the_first_clear_neighbour(self):
        # The Vivec case: the door exit point lies inside a building's standing hull.
        c = Collision(payload(wall=((-10, -10, -1), (10, 10, 100))))
        self.assertTrue(c.solid((0, 0, 20)))
        self.assertEqual(standing_spot(c, (0, 0, 20))[:2], (16, 0))
        c = Collision(payload(wall=((-100, -100, -1), (100, 100, 100))))
        self.assertIsNone(standing_spot(c, (0, 0, 20)))

    def test_water_is_never_a_spot(self):
        c = Collision(payload(water=10))
        self.assertFalse(c.dry((0, 0, .25)))
        self.assertIsNone(standing_spot(c, (0, 0, 20)))

    def test_importer_stores_the_resolved_spot_or_fails_closed(self):
        entries = [{'name': 'va010', 'core': [[-768, -768], [768, 768]]}]

        def owner(point, rows):
            return 0
        maps = {'va010': payload(wall=((-10, -10, -1), (10, 10, 100)))}
        self.assertEqual(resolve(maps.__getitem__, entries, (0, 0, 20), owner)[:2], [16, 0])
        maps['va010'] = payload(wall=((-100, -100, -1), (100, 100, 100)))
        with self.assertRaisesRegex(ValueError, 'no standing spot'):
            resolve(maps.__getitem__, entries, (0, 0, 20), owner)

    def test_importer_moves_the_arrival_regions_spawn(self):
        import importlib.util
        if not (importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL')):
            self.skipTest('optional conversion dependencies')
        import import_town
        text = '{\n"classname" "worldspawn"\n}\n{\n"classname" "info_player_start"\n"origin" "48.0 431.25 490.625"\n"angle" "90"\n}'
        moved = import_town.spawn_at(text, [48.0, 447.25, 465.075])
        self.assertIn('"origin" "48.0 447.25 465.075"', moved)
        self.assertIn('"angle" "90"', moved)
        self.assertEqual(import_town.spawn_at(text, [48.0, 431.25, 490.625]), text)

    def test_every_town_arrival_is_checked_on_its_converted_maps(self):
        towns = [{'name': 'arena', 'regions': 'arena-regions.txt', 'travel_target': '', 'travel_return': False}]
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp); (id1 / 'maps').mkdir()
            (id1 / 'maps/ar000.bsp').write_bytes(payload(wall=((-10, -10, -1), (10, 10, 100))))

            def directory(arrival):
                (id1 / 'arena-regions.txt').write_text(
                    'AWBR1 1 96 540 %s 270 0 0 0 0\nar000 -768 -768 768 768 -768 -768 768 768\n'
                    % ' '.join(map(str, arrival)))
            directory((0, 0, 20))                     # source pose: inside the wall
            report = check(id1, towns)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['rows'][0]['spot'][:2], [16, 0])
            with self.assertRaisesRegex(ValueError, 'arrival check failed'):
                require(id1, id1 / 'report.json', towns)
            directory((16, 0, .25))                   # the stored, resolved spot
            self.assertEqual(require(id1, None, towns)['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
