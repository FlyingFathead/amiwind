# SPDX-License-Identifier: GPL-3.0-only
import hashlib
from pathlib import Path
import sys
import tempfile
import struct
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from hand_metadata import hand_fields, stamp, stamp_staged_hands
from player_hull import lumps, pack_lumps


class HandMetadata(unittest.TestCase):
    def model(self):
        raw = bytearray(84); raw[:8] = b'IDPO\x06\x00\x00\x00'
        struct.pack_into('<3i', raw, 60, 3, 1, 28)
        return bytes(raw)

    def report(self):
        return {'model': 'progs/v_nord.mdl', 'frames': 28,
                'sha256': hashlib.sha256(self.model()).hexdigest(), 'vertices': 3, 'triangles': 1,
                'eye_above_origin': 16.25,
                'clips': {name: {'first': first, 'count': count, 'duration': duration}
                          for name, first, count, duration in
                          [('idle', 0, 8, 2.7), ('draw', 8, 6, .47),
                           ('lower', 14, 4, .27), ('punch', 18, 10, 1.07)]}}

    def map_bytes(self, fields=b''):
        return pack_lumps([b'{\n"classname" "worldspawn"\n"_aw_sky_mode" "exterior"\n' + fields +
                           b'}\n{\n"classname" "aw_flora"\n"origin" "-4 9 2"\n}\n\0'] +
                          [bytes([n])*n for n in range(1, 15)])

    def test_missing_region_metadata_and_all_other_bytes_preserved(self):
        raw = self.map_bytes()
        fixed = stamp(raw, hand_fields(self.report()))
        self.assertEqual(lumps(raw)[1:], lumps(fixed)[1:])
        self.assertEqual(bytes(lumps(raw)[0]).split(b'}', 1)[1],
                         bytes(lumps(fixed)[0]).split(b'}', 1)[1])
        self.assertIn(b'"_aw_sky_mode" "exterior"', lumps(fixed)[0])
        for key, value in hand_fields(self.report()).items():
            self.assertIn(('"'+key+'" "'+value+'"').encode(), lumps(fixed)[0])
        self.assertEqual(stamp(fixed, hand_fields(self.report())), fixed)

    def test_existing_metadata_is_updated_without_duplicate_fields(self):
        raw = self.map_bytes(b'"aw_hand_draw" "0.1"\n')
        fixed = stamp(raw, hand_fields(self.report()))
        self.assertEqual(bytes(lumps(fixed)[0]).count(b'"aw_hand_draw"'), 1)
        self.assertIn(b'"aw_hand_draw" "0.47"', lumps(fixed)[0])

    def test_invalid_source_timing_and_frame_contract_are_rejected(self):
        for value in (0, -1, 61, float('nan'), float('inf'), True, '0.4'):
            report = self.report(); report['clips']['draw']['duration'] = value
            with self.assertRaises(ValueError): hand_fields(report)
        report = self.report(); report['clips']['punch']['first'] = 17
        with self.assertRaises(ValueError): hand_fields(report)
        report = self.report(); report['eye_above_origin'] = float('nan')
        with self.assertRaises(ValueError): hand_fields(report)

    def test_malformed_and_duplicate_map_metadata_are_rejected(self):
        raw = self.map_bytes(b'"aw_hand_draw" "1"\n"aw_hand_draw" "2"\n')
        with self.assertRaises(ValueError): stamp(raw, hand_fields(self.report()))
        raw = self.map_bytes().replace(b'worldspawn', b'info_start')
        with self.assertRaises(ValueError): stamp(raw, hand_fields(self.report()))

    def test_all_map_families_are_stamped_and_model_mismatch_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp); (id1/'maps').mkdir(); (id1/'progs').mkdir()
            model = id1/'progs/v_nord.mdl'; model.write_bytes(b'wrong model')
            raw = self.map_bytes()
            for name in ('seyda', 'sn045', 'bm001', 'vf1340', 'prison'):
                (id1/'maps'/(name+'.bsp')).write_bytes(raw)
            with self.assertRaises(ValueError): stamp_staged_hands(id1, self.report())
            self.assertTrue(all(path.read_bytes() == raw for path in (id1/'maps').iterdir()))
            model.write_bytes(self.model())
            result = stamp_staged_hands(id1, self.report())
            self.assertEqual(len(result['changed_maps']), 5)
            self.assertEqual(result['map_count'], 5)
            self.assertEqual(stamp_staged_hands(id1, self.report())['changed_maps'], [])

    def test_invalid_later_map_stops_batch_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp); (id1/'maps').mkdir(); (id1/'progs').mkdir()
            (id1/'progs/v_nord.mdl').write_bytes(self.model())
            first = id1/'maps/aa.bsp'; first.write_bytes(self.map_bytes())
            (id1/'maps/zz.bsp').write_bytes(b'invalid bsp')
            with self.assertRaises(ValueError): stamp_staged_hands(id1, self.report())
            self.assertEqual(first.read_bytes(), self.map_bytes())

    def test_explicit_gameplay_maps_preserve_special_gallery_camera(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp); (id1/'maps').mkdir(); (id1/'progs').mkdir()
            (id1/'progs/v_nord.mdl').write_bytes(self.model())
            raw = self.map_bytes()
            for name in ('vf1340', 'charplane'):
                (id1/'maps'/(name+'.bsp')).write_bytes(raw)
            report = stamp_staged_hands(id1, self.report(), {'vf1340'})
            self.assertEqual(report['changed_maps'], ['vf1340.bsp'])
            self.assertEqual((id1/'maps/charplane.bsp').read_bytes(), raw)
            with self.assertRaises(ValueError):
                stamp_staged_hands(id1, self.report(), {'../elsewhere'})
