# SPDX-License-Identifier: GPL-3.0-only
"""tools/container_census.py: the world-wide container count (CONTAINER-WINDOW-59): the box count
(OUTDOOR-CONTAINER-AIM-66), the engine rules it judges by against the engine's source, the area records' keys, the
verdict, and the committed measurement (docs/performance/CONTAINERS.json): a container that stops opening fails here."""
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

MEASUREMENT = ROOT / 'docs' / 'performance' / 'CONTAINERS.json'


class ContainerCensusTests(unittest.TestCase):
    def test_box_field_is_told_from_a_record_id(self):
        import container_census as cc
        box = struct.pack('<7f', 30, 20, 10, 1, 0, 0, 0) + bytes(4)
        self.assertTrue(cc.is_box(box))
        self.assertFalse(cc.is_box(b'contain_com_sack_01'.ljust(32, b'\0')))
        self.assertFalse(cc.is_box(bytes(32)))

    def test_window_counts_boards_and_boxed_containers(self):
        import container_census as cc
        import prepare_focus as pf
        box = struct.pack('<7f', 30, 20, 10, 1, 0, 0, 0) + bytes(4)

        def row(kind, action, field):
            return bytes([ord(kind), 0, action, 0]) + bytes(60) + field

        cells = [(pf.exterior_key(0, 0), [row('C', 1, box), row('N', 0, box), row('C', 1, b'odd'.ljust(32, b'\0'))]),
                 (pf.exterior_key(5, 5), [row('C', 1, box)])]
        index, body, at = [], [], 0
        for key, rows in cells:
            index.append(struct.pack('<III', key, at, len(rows))); body += rows; at += len(rows)
        payload = b'AWF3' + struct.pack('<I', len(cells)) + b''.join(index) + b''.join(body)
        got = cc.window_boxes(payload)
        self.assertEqual((got['exterior_containers_boxed'], got['exterior_containers_unboxed']), (2, 1))
        self.assertEqual(got['most_boxes_in_a_window'], 2)

    def test_engine_holds_the_most_boxes_counted(self):
        # the census of the original data (13 November 2026): at most 154 boards and boxed containers in a 3 x 3 window
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('#define FOCUS_BOARDS 256', inventory)
        self.assertIn('#define FOCUS_ROWS 1536', inventory)

    def test_the_rules_judged_by_are_the_engines(self):
        # the count judges by this tree's engine: each rule the census names is the one the engine source has
        import container_census as cc
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        room = (ROOT / 'engine/aga/src/chim/chim_room.c').read_text(encoding='utf-8')
        self.assertTrue(cc.CONTAINER_EDICT_ROWS_KEPT)
        self.assertIn("else if(focus_rows[j].kind=='C' && focus_rows[j].reference!=AW_REF_COURTYARD_BARREL)"
                      "focus_rows[j].live=1;", inventory)
        self.assertIn("if((row->kind=='I' || row->kind=='C') && row->live && view_ref && row->reference==view_ref){",
                      inventory)
        self.assertTrue(cc.CONTAINER_KEY_OPENS)
        self.assertIn('aw_lock_pass(row->reference,AW_AreaContainerKey(row->reference,key,sizeof(key))?key:NULL)',
                      inventory)
        self.assertTrue(cc.ROOM_STABLE_IDS)
        self.assertEqual(room.count('RoomRefIs (i, reference)'), 3)     # ChimRoom_Has, ChimRoom_RayRef, ChimRoom_Hide
        self.assertEqual((cc.FOCUS_ROWS, cc.FOCUS_BOARDS), (1536, 256))

    def test_merged_room_numbers_read_as_stable_ids(self):
        # REF-IDENTITY-MERGED-MASTER-66: a room record's merged number (2^22 x master + number) is the stable id
        # (2^20 x master + number) of tools/ref_identity.py; the base game's numbers are both
        import container_census as cc
        from ref_identity import stable_ref
        self.assertEqual(cc.stable_of_merged((1 << 22) | 1003), (1 << 20) | 1003)
        self.assertEqual(cc.stable_of_merged((2 << 22) | 26190), stable_ref('Bloodmoon.esm', 26190))
        self.assertEqual(cc.stable_of_merged(484481), 484481)
        self.assertEqual(cc.stable_of_merged((1 << 24) | 1002), 1002)      # a cut piece's bits left out

    def test_area_record_names_the_containers_key(self):
        # LOCKED-CONTAINERS-NEVER-OPEN-67: the key of a container travels in its area record (index + 1, 0 none)
        import container_census as cc
        import prepare_area_tables as pat
        rows = [bytes([ord('C'), 0, 1, 40]) + struct.pack('<I', ref) + bytes(88) for ref in (7000, 7001)]
        items = {}
        for ident in ('chest_key', 'gold_001'):
            row = bytearray(pat.ITEM_ROW); row[0:len(ident)] = ident.encode(); row[64:68] = b'Name'
            items[ident] = bytes(row)
        containers = {7000: (0, [('gold_001', 5)]), 7001: (0, [('gold_001', 1)])}
        record, _ = pat.area(rows, {}, containers, {}, {'7000': [0, 'chest_key']}, items, {})
        index, at = pat.pack_index([(11, record)], 24 + 12)
        payload = b'AWA1' + struct.pack('<IIIII', 1, 0, 0, 0, 0) + index + record
        got = cc.read_area_containers(payload)[1]
        self.assertEqual(got[7000][:3], (1, 0, 40))
        self.assertEqual(got[7000][3], sorted(items).index('chest_key') + 1)
        self.assertEqual(got[7001][3], 0)

    def test_verdict_refuses_a_new_gap_and_a_larger_one(self):
        import container_census as cc
        known = {'locked': ('LOCKED-CONTAINERS-NEVER-OPEN-67', 10)}
        self.assertEqual(cc.verdict({'gaps': {'locked': {'containers': 10}}}, known), [])
        self.assertEqual(len(cc.verdict({'gaps': {'locked': {'containers': 11}}}, known)), 1)
        self.assertEqual(len(cc.verdict({'gaps': {'drawn as a brush': {'containers': 1}}}, known)), 1)

    def test_committed_measurement_holds(self):
        # the newest measurement of docs/performance/CONTAINERS.json: every gap has its register entry and stays
        # within its count (a container that stops opening, or a new reason, fails the gate)
        import container_census as cc
        data = json.loads(MEASUREMENT.read_text(encoding='utf-8'))
        newest = data['measurements'][-1]
        self.assertEqual(newest['schema'], cc.SCHEMA)
        self.assertEqual(cc.verdict(newest), [])
        bugs = {b['id'] for b in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for reason, (ids, _count) in cc.KNOWN_GAPS.items():
            for ident in ids.split():
                self.assertIn(ident, bugs, reason)
        # the totals add up: what opens is aimable, what is aimable is drawn, what is drawn is in the build
        for master, sides in newest['totals'].items():
            for side, v in sides.items():
                self.assertTrue(v['opens'] <= v['aimable'] <= v['drawn'] <= v['in_build'] <= v['to_open'],
                                (master, side))

    def test_a_frames_own_exports_count_as_drawn(self):
        # SEYDA-CONTAINERS-NOT-DRAWN-67: Seyda Neen's frame places the containers it exports beside its scenery
        import tempfile
        import container_census as cc
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / cc.REGIONS / 'seyda'
            for name, number in (('opening-barrel-source', 172851), ('open-containers-source', 297457)):
                (work / name).mkdir(parents=True)
                (work / name / 'scenery-index.json').write_text(json.dumps(
                    {'references': [{'number': number, 'type': 'CONT'}, {'number': 5, 'type': 'STAT'}]}))
            self.assertEqual(cc.exterior_scenery(tmp), {cc.stable_ref(cc.pf.MASTER, 172851),
                                                       cc.stable_ref(cc.pf.MASTER, 297457)})

    def test_open_container_ids_leave_out_plants_and_unnamed(self):
        import open_containers as oc

        def sub(tag, data):
            return tag.encode() + struct.pack('<I', len(data)) + data

        def cont(ident, name, flag):
            body = sub('NAME', ident.encode() + b'\0') + (sub('FNAM', name.encode() + b'\0') if name else b'') + \
                sub('FLAG', struct.pack('<I', flag))
            return b'CONT' + struct.pack('<III', len(body), 0, 0) + body

        raw = cont('Crate_01', 'Crate', 8) + cont('flora_kelp', 'Kelp', 9) + cont('hidden', '', 8)
        self.assertEqual(oc.open_container_ids(raw), frozenset({'crate_01'}))


if __name__ == '__main__':
    unittest.main()
