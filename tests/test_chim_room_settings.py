# SPDX-License-Identifier: GPL-3.0-only
"""CHIM room settings (config/chim-rooms.json, tools/chim/interior.py room_settings; PERF-ARENA-PIT-SLOW-48): a room
model wider than cut_models_over is stored as tiles (chim.cut tile mode, the exterior's large-model cut), so the
Vivec Arena Pit's bowl (one model over the whole room, about 1,000 x 740 local units) is culled tile by tile instead
of being drawn whole from anywhere in the room; house-size models stay whole; 0 keeps every model whole (the method
up to v0.0.54-dev1); a named detail budget applies to room meshes as chim.build applies an area's."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chim import interior as I  # noqa: E402
from chim.build import cut_candidate  # noqa: E402


def variant(width, depth, name='i/in_v_arena_01@s1'):
    return {'name': name, 'lo': [-width / 2, -depth / 2, -100.0], 'hi': [width / 2, depth / 2, 300.0]}


class RoomSettings(unittest.TestCase):
    def test_only_the_arena_pit_gets_tiles_and_the_budget(self):
        # the maintainer, 2026-10-28 (blank walls in a dev2 room): "we can't have walls like that except in the vivec
        # arena pit": every other room is built as v0.0.53 built it, every model whole, no budget
        import json as _json
        listed = _json.loads((ROOT / 'config/chim-rooms.json').read_text(encoding='utf-8'))['rooms']
        self.assertEqual(listed, ['vai000'])
        for other in ('ric5e9a38a4d', 'bai001', 'vti012', 'rifa4ef181ed', None):
            s = I.room_settings(other)
            self.assertEqual((s['cut_models_over'], s['detail_budget']), (0.0, {}), other)
        self.assertGreater(I.room_settings('vai000')['cut_models_over'], 0)

    def test_default_cuts_the_arena_bowl_and_keeps_house_models_whole(self):
        s = I.room_settings('vai000')
        self.assertGreater(s['cut_models_over'], 0)
        self.assertTrue(cut_candidate(variant(998, 740), s['cut_models_over']))
        # a table, a door, a whole house interior shell under the width: whole
        self.assertFalse(cut_candidate(variant(120, 60, 'f/furn_de_table_01'), s['cut_models_over']))
        self.assertFalse(cut_candidate(variant(s['cut_models_over'], 300, 'i/in_hlaalu_room_01'), s['cut_models_over']))
        # flora stays whole as outdoors (CUT_KEEP_WHOLE)
        self.assertFalse(cut_candidate(variant(998, 740, 'f/flora_tree_01'), s['cut_models_over']))
        # the Arena Pit's bowl (the only room that places it, 14,872 source triangles) gets fewer visual triangles
        target = s['detail_budget'].get('meshes/i/in_v_arena_01.nif')
        self.assertTrue(target and target < 14872)

    def test_the_arena_pit_is_built_in_its_three_types(self):
        # the maintainer, 2026-10-28: the Pit's methods behind one saved setting (aw_vivec_arena_pit_type)
        types = I.room_types()['vai000']
        # the maintainer, 2026-10-28: the original as type 0, type 1, type 2; 2 the default (type 4 not built)
        self.assertEqual(sorted(types['types']), [0, 1, 2])
        self.assertEqual(types['default'], 2)
        self.assertEqual(types['types'][0]['cut_models_over'], 0)          # the bowl whole, the earlier method
        self.assertEqual(types['types'][0]['detail_budget'], {})
        self.assertGreater(types['types'][1]['cut_models_over'], 0)
        self.assertEqual(types['types'][1]['detail_budget'], {})
        self.assertTrue(types['types'][2]['detail_budget'].get('meshes/i/in_v_arena_01.nif'))
        # the engine's record name for a type fits its room name limit (chim_format.h CHIM_ROOM_NAME_CHARS 22)
        self.assertLessEqual(len('vai000' + I.TYPE_SUFFIX + '9'), 22)
        source = (ROOT / 'engine/aga/src/chim/chim_world.c').read_text(encoding='utf-8')
        self.assertIn('"aw_vivec_arena_pit_type"', source)
        self.assertIn('"_chim_room_types"', source)

    def config(self, data):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        (root / 'config').mkdir()
        (root / 'config' / 'chim-rooms.json').write_text(json.dumps(data), encoding='utf-8')
        (root / 'config' / 'chim-detail-budgets.json').write_text(json.dumps(
            {'format': 1, 'budgets': {'rooms-test': {'meshes\\i\\in_v_arena_01.nif': 4000}}}), encoding='utf-8')
        real = Path

        class Rooted(type(real())):
            def resolve(self):
                p = real.resolve(self)
                return root / 'tools' / 'chim' / p.name if p.name in ('interior.py', 'build.py') else p
        return mock.patch.object(I, 'Path', Rooted), mock.patch('chim.build.Path', Rooted)

    def test_zero_keeps_every_model_whole_and_a_named_budget_applies(self):
        a, b = self.config({'rooms': ['vai000'], 'cut_models_over': 0, 'detail_budget': 'rooms-test'})
        with a, b:
            s = I.room_settings('vai000')
        self.assertEqual(s['cut_models_over'], 0)
        self.assertFalse(cut_candidate(variant(998, 740), s['cut_models_over']))
        self.assertEqual(s['detail_budget'], {'meshes/i/in_v_arena_01.nif': 4000})

    def test_negative_width_refused(self):
        a, b = self.config({'rooms': ['vai000'], 'cut_models_over': -1, 'detail_budget': None})
        with a, b, self.assertRaises(ValueError):
            I.room_settings('vai000')


if __name__ == '__main__':
    unittest.main()
