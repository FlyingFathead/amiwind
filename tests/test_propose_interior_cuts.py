# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import propose_interior_cuts as cuts


def room(folder, unlit=(), sprites=()):
    models = [{'source': 'meshes/i/in_v_s_int_wall_01.nif'}, {'source': 'meshes/d/in_velothismall_ndoor_01.nif'},
              {'source': 'meshes/f/flora_grass_01.nif'}]
    refs = []
    for n in range(10):  # five walls each side of x = 0, a door at x = 0
        x = -400 + n * 80 if n < 5 else 80 + (n - 5) * 80
        refs.append({'number': n, 'model_index': 0, 'scale': 1., 'bounds': [[x - 20, 0, 0], [x + 20, 40, 40]]})
    refs.append({'number': 10, 'model_index': 1, 'scale': 1., 'bounds': [[-10, 0, 0], [10, 40, 40]]})
    refs.append({'number': 11, 'model_index': 2, 'scale': 1., 'bounds': [[-300, 0, 0], [-290, 10, 10]]})
    refs.append({'number': 12, 'model_index': 2, 'scale': 1., 'bounds': [[-200, 0, 0], [-190, 10, 10]]})
    (folder / 'source').mkdir(parents=True)
    (folder / 'source/scenery-index.json').write_text(json.dumps({'models': models, 'references': refs}))
    (folder / 'conversion.json').write_text(json.dumps({
        'map': 'r1', 'cell': 'Test', 'shared_ambient': {'unlit_references': list(unlit)},
        'plant_sprites': {'sprites': [{'reference': n, 'sprite': 'progs/aw_flora/f_0.spr'} for n in sprites]}}))


class ProposeCutsTests(unittest.TestCase):
    def test_slots_follow_the_converter_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'r1'
            room(folder, unlit=[0, 1, 2], sprites=[11, 12])
            placements, _ = cuts.room_placements(folder)
            # 3 unlit walls share one model, 7 walls and the door own one, 2 sprites of one file
            self.assertEqual(cuts.side_slots(placements), 1 + 7 + 1 + 1)

    def test_cut_through_the_door_splits_evenly(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'r1'
            room(folder)
            row = cuts.propose(folder, limit=8)
            best = row['cuts'][0]
            self.assertEqual(best['axis'], 'x')
            self.assertEqual(best['through']['reference'], 10)
            self.assertTrue(best['fits'])
            self.assertLessEqual(max(best['slots']), 8)
            self.assertIn('PENDING', row['review'])


if __name__ == '__main__':
    unittest.main()
