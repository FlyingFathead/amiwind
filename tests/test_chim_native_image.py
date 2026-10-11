# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-CHIM-NATIVE-TOWN-36: a CHIM-native town (--chim-native-towns on, tools/chim_town.py) has
no legacy region maps, and the image step takes its area from the chim-town output alone.

The v0.0.36-dev1 full build with the Bitter Coast test area failed at the end of its image step: the CHIM
frame map of the CHIM-native town read its activated objects from legacy region maps (maps/bc000.bsp)
that the CHIM-native chain never builds. Also checked: the collision check of the payload preflight
(a legacy-chain file and a CHIM-native output claiming the same area are refused, naming both sources).
Synthetic data only (no game files).
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import chim_town  # noqa: E402
from chim import frame_map  # noqa: E402
import payload_preflight  # noqa: E402

REGIONS = ('AWBR1 1 96 540 0 0 64 90 0 0 0 0\n'
           'bm000 -3072 -3072 -1536 -2304 -3072 -3072 -640 -1408\n')
ROWS = [{'classname': 'worldspawn', 'message': 'Balmora'},
        {'classname': 'info_player_start', 'origin': '0 0 0'},
        {'classname': 'aw_npc', 'aw_ref': '42', 'origin': '1 2 3'}]


def town_dir(root, regions=REGIONS, model=b'MDL', name='chim-town-balmora'):
    town = Path(root) / name
    (town / 'id1/progs').mkdir(parents=True)
    (town / 'id1/progs/a_1.mdl').write_bytes(model)
    (town / 'id1/balmora-regions.txt').write_text(regions, newline='\n')
    (town / 'door-bank.txt').write_text('AWD3\n', newline='\n')
    record = {'format': chim_town.FORMAT, 'town': 'balmora', 'map': 'balmora', 'door_file': 'doors-balmora.txt',
              'rows': ROWS}
    (town / 'entities.json').write_text(json.dumps(record))
    return town


def id1_dir(root):
    id1 = Path(root) / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    return id1


class FrameMapTests(unittest.TestCase):
    def build(self, id1, placed):
        lo, hi = (-3072.0, -3072.0, -512.0), (3072.0, 3072.0, 2048.0)
        with patch.multiple(frame_map, chim_placements=lambda *a, **k: dict(placed),
                            frame_record=lambda *a, **k: (None, None, None, None, (0.0, 0.0)),
                            frame_world=lambda *a, **k: (None, None),
                            actor_contact=lambda *a, **k: ([], {}), arrival_check=lambda *a, **k: ([], {}),
                            frame_bounds=lambda *a, **k: ((-3, -2), lo, hi), stream_enabled=lambda: False,
                            hunk_rest=lambda *a, **k: 0, closed_edge=lambda town: False):
            return frame_map.build(id1, 'balmora', Path('/no/chim-world'), entity_rows=[dict(r) for r in ROWS])

    def test_a_chim_native_frame_map_reads_no_legacy_region_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = id1_dir(tmp)
            (id1 / 'balmora-regions.txt').write_text(REGIONS, newline='\n')    # the table names bm000, no bm000.bsp
            record = self.build(id1, {1001: (0.0, 0.0, 0.0)})
            self.assertEqual(record['map'], 'maps/balmora-chim.chim')
            self.assertEqual(record['activated']['kept'], [])
            self.assertFalse((id1 / 'maps/bm000.bsp').exists())

    def test_an_activated_object_in_a_chim_native_frame_is_refused(self):
        refs = frame_map.activated_refs()
        ref = sorted(refs)[0]
        self.assertEqual(frame_map.native_activated_check({1001: None}), [])
        refused = frame_map.native_activated_check({ref: (0.0, 0.0, 0.0)})
        self.assertEqual(len(refused), 1)
        self.assertIn(refs[ref], refused[0])
        self.assertIn('--legacy-area', refused[0])
        with tempfile.TemporaryDirectory() as tmp:
            id1 = id1_dir(tmp)
            (id1 / 'balmora-regions.txt').write_text(REGIONS, newline='\n')
            with self.assertRaisesRegex(ValueError, 'CHIM-native town'):
                self.build(id1, {ref: (0.0, 0.0, 0.0)})


class CollisionTests(unittest.TestCase):
    def test_a_clean_chim_native_area_is_assembled_with_no_legacy_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            town, id1 = town_dir(tmp), id1_dir(tmp)
            self.assertEqual(chim_town.collisions(id1, [town], ['balmora']), [])
            self.assertEqual(payload_preflight.check_chim_native(id1, None, []), 0)
            chim_town.install(town, id1)
            # installed again over identical bytes (a resumed image): the same stored file, no conflict
            self.assertEqual(chim_town.collisions(id1, [town], ['balmora']), [])
            # after the install the image passes rewrite models in place: the later preflight does not compare
            (id1 / 'progs/a_1.mdl').write_bytes(b'MDL rewritten by a pass')
            self.assertEqual(len(chim_town.collisions(id1, [town], ['balmora'])), 1)
            self.assertEqual(chim_town.collisions(id1, [town], ['balmora'], installed=True), [])
            self.assertEqual(sorted(p.relative_to(id1).as_posix() for p in id1.rglob('*') if p.is_file()),
                             ['balmora-regions.txt', 'doors-balmora.txt', 'progs/a_1.mdl'])
            self.assertEqual(chim_town.legacy_claims(id1, 'balmora'), [])

    def test_legacy_chain_files_of_a_chim_native_town_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            town, id1 = town_dir(tmp), id1_dir(tmp)
            for name in ('bm000', 'balmora', 'balmora-chim'):
                (id1 / 'maps' / (name + '.bsp')).write_bytes(b'BSP')
            (id1 / 'balmora-regions.txt').write_text('AWBR1 legacy\n', newline='\n')
            found = chim_town.collisions(id1, [town], ['balmora'])
            for rel in ('maps/bm000.bsp', 'maps/balmora.bsp', 'maps/balmora-chim.bsp', 'balmora-regions.txt'):
                self.assertTrue(any(line.startswith(rel + ':') and 'chim-town-balmora' in line for line in found), rel)
            self.assertTrue(any('legacy chain' in line for line in found))
            self.assertTrue(any('other bytes' in line for line in found))
            with self.assertRaisesRegex(ValueError, 'maps/bm000.bsp'):
                chim_town.install(town, id1)
            self.assertEqual((id1 / 'balmora-regions.txt').read_text(), 'AWBR1 legacy\n')   # nothing installed

    def test_two_outputs_and_a_town_off_the_chim_world_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = id1_dir(tmp)
            a = town_dir(tmp, name='a')
            b = town_dir(tmp, model=b'OTHER', name='b')
            found = chim_town.collisions(id1, [a, b], ['seyda'])
            self.assertTrue(any('not an area of the CHIM world' in line for line in found))
            self.assertTrue(any('listed twice' in line for line in found))
            c = Path(tmp) / 'c'
            (c / 'id1/progs').mkdir(parents=True)
            (c / 'id1/progs/a_1.mdl').write_bytes(b'OTHER')
            record = json.loads((a / 'entities.json').read_text())
            record['town'] = 'seyda'
            (c / 'entities.json').write_text(json.dumps(record))
            found = chim_town.collisions(id1, [a, c], ['balmora', 'seyda'])
            self.assertEqual(len(found), 1)
            self.assertIn('progs/a_1.mdl', found[0])
            self.assertIn('chim-town output a', found[0])
            self.assertIn('chim-town output c', found[0])

    def test_the_payload_preflight_runs_the_collision_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            town, id1 = town_dir(tmp), id1_dir(tmp)
            (id1 / 'maps/bm000.bsp').write_bytes(b'BSP')
            with patch('build_aga.chim_world_receipt', lambda world: ({}, ['balmora'])):
                with self.assertRaisesRegex(ValueError, r'maps/bm000\.bsp: legacy chain file staged in the image and '
                                                        r'chim-town output chim-town-balmora'):
                    payload_preflight.check_chim_native(id1, Path('/w'), [town])
                (id1 / 'maps/bm000.bsp').unlink()
                self.assertEqual(payload_preflight.check_chim_native(id1, Path('/w'), [town]), 1)


if __name__ == '__main__':
    unittest.main()
