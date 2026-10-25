# SPDX-License-Identifier: GPL-3.0-only
"""CHIM rooms that need 32 MB of Fast RAM (CHIM-ROOM-16MB-REFUSAL-48): the image step's room heap gate
(tools/chim/heap.py require_room_map_heap) sorts every CHIM room into the 16 MB baseline (its zone alone, less the
loading buffer) or the 32 MB minimum (the measured big-rooms model, CHIM-ROOM-ESTIMATE-48: the zone at the 32 MB
machine's heap plus its automatic cache bank, the largest model within one block), fails only a room that fits
neither, and marks the 32 MB rooms' maps with "_chim_room_fast_mb" "32" in their worldspawn, which the engine reads at
the door (engine/aga/src/aw_scene.c AW_SceneRoomFastMb; tests/aga_scene_test.c). The marking and the door graph's
room model (tools/door_graph.py room_limits, the room plan's 'fits_16mb' and 'zone_over_16mb') are the same model."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chim import format as F  # noqa: E402
from chim import heap as H  # noqa: E402
from chim.frame_map import empty_world, entities, entity_text  # noqa: E402

ZONE_16, ROOM_32, BLOCK_32 = 7 << 20, 15 << 20, 8 << 20     # stand-ins: the 16 MB room, the 32 MB room, one block


def write_room(id1, name):
    lumps = empty_world((-64.0, -64.0, -64.0), (64.0, 64.0, 64.0))
    lumps[0] = entity_text([{'classname': 'worldspawn', '_chim_world': 'chimi', '_chim_room': name},
                            {'classname': 'info_player_start', 'origin': '0 0 0'}])
    path = Path(id1) / 'maps' / (name + '.chim')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(F.brush_image(lumps)[0])
    return path


def fake_heap(needs):
    """room_map_heap's report for rooms of the given (need, largest model) bytes."""
    def heap(id1, sizes, heap_mb=None, stems=None):
        return {n: {'map': n + '.chim', 'room': n, 'need_bytes': need, 'zone_bytes': ZONE_16 + 4096,
                    'zone_room_bytes': ZONE_16, 'min_fast_room_bytes': ROOM_32, 'block_bytes_min_fast': BLOCK_32,
                    'largest_model_bytes': largest, 'heap_mb': heap_mb or 11, 'fits_zone': need <= ZONE_16,
                    'ok': need <= ROOM_32 and largest <= BLOCK_32}
                for n, (need, largest) in needs.items() if stems is None or n in stems}
    return heap


class RoomFastRam(unittest.TestCase):
    def test_rooms_are_sorted_and_the_32mb_ones_marked(self):
        needs = {'small': (3 << 20, 1 << 20), 'big': (ZONE_16 + (1 << 20), 2 << 20), 'huge': (ROOM_32 + 1, 1 << 20),
                 'block': (ZONE_16 + 1, BLOCK_32 + 1)}
        with tempfile.TemporaryDirectory() as tmp:
            for n in needs:
                write_room(tmp, n)
            before = {n: (Path(tmp) / 'maps' / (n + '.chim')).read_bytes() for n in needs}
            with mock.patch.object(H, 'room_map_heap', fake_heap(needs)):
                for bad in ('huge', 'block'):
                    with self.assertRaises(ValueError) as e:
                        H.require_room_map_heap(tmp, sizes={'hunk': 16})
                    self.assertIn(bad + '.chim', str(e.exception))
                    del needs[bad]
                    (Path(tmp) / 'maps' / (bad + '.chim')).unlink()
                report = H.require_room_map_heap(tmp, sizes={'hunk': 16}, report_path=Path(tmp) / 'r.json')
            self.assertTrue(report['ok'])
            self.assertEqual(report['marked_32mb'], ['big'])
            # the rooms marked for 32 MB are exactly the rooms over the 16 MB zone
            self.assertEqual(report['marked_32mb'], report['over_16mb_zone'])
            rooms = report['rooms']
            self.assertEqual((rooms['small']['fast_mb'], rooms['small']['fits_16mb']), (16, True))
            self.assertEqual((rooms['big']['fast_mb'], rooms['big']['fits_16mb']), (32, False))
            self.assertEqual(rooms['big']['zone_32mb_bytes'], ROOM_32)
            big = (Path(tmp) / 'maps' / 'big.chim').read_bytes()
            self.assertEqual(entities(big)[0][H.ROOM_FAST_KEY], '32')
            self.assertNotIn(H.ROOM_FAST_KEY, entities(big)[1])
            # only the worldspawn changed: every other lump is the same bytes
            self.assertEqual(F.read_brush_image(big)[1:], F.read_brush_image(before['big'])[1:])
            self.assertEqual((Path(tmp) / 'maps' / 'small.chim').read_bytes(), before['small'])

    def test_marking_and_the_big_rooms_model_agree(self):
        """The heap gate's limits are the door graph's room limits (the room plan's 'fits_16mb' and the 32 MB
        limit) when the whole-map rule does not bind: one model, so the rooms the build marks for 32 MB are the
        plan's rooms with the note 'zone_over_16mb'."""
        import door_graph as G
        plan = G.room_limits()
        gate = H.room_zone_limits(0, 0)
        self.assertEqual(gate['zone_room_bytes'], plan['zone_room_bytes'])
        self.assertEqual(gate['min_fast_room_bytes'], plan['room_bytes_min_fast'])
        self.assertEqual(gate['block_bytes_min_fast'], plan['block_bytes_min_fast'])
        self.assertEqual(gate['min_fast_ram_mib'], H.SAFE_FAST_MB)
        # the measured figures (docs/chim/DOOR_GRAPH.md): the 32 MB room holds 14,336,000 bytes (the zone and the
        # 7 MiB bank of the v0.0.50 measurement; 15,384,576 with the 8 MiB bank assumed before CHIM-AUTO-BANK-CLIFF-51);
        # the 16 MB zone alone (7,012,352 when the plan was made) follows the engine's built heap and the Hunk it keeps,
        # so it is read from the sources (6,995,968 with the hinged doors' engine), never pinned here
        self.assertEqual(plan['room_bytes_min_fast'], 14336000)
        self.assertTrue(6 << 20 < plan['zone_room_bytes'] < plan['room_bytes_min_fast'], plan['zone_room_bytes'])
        # the door graph's room plan note and the gate's 16 MB test use the same comparison
        need = plan['zone_room_bytes'] + 1
        room = {'kept_placements': 1, 'actors': 0, 'lights': 0, 'load_doors': 0}
        sizes = {'bytes': need, 'need_bytes': need, 'largest_model_vertexes': 1, 'largest_model_zone_bytes': 1}
        self.assertEqual(G.over_limit(room, plan, sizes), [])
        self.assertFalse(need <= gate['zone_room_bytes'])

    def test_the_engine_reads_the_same_key(self):
        scene = (ROOT / 'engine/aga/src/aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('#define ROOM_FAST_KEY "\\"%s\\""' % H.ROOM_FAST_KEY, scene)
        self.assertIn('if(AW_SceneRoomRefuse(links[i].target))return 1;', scene)
        # the refusal comes before the door sound and the map command: nothing loads
        use = scene[scene.index('int AW_SceneUse(void) {'):]
        self.assertLess(use.index('AW_SceneRoomRefuse('), use.index('AW_DoorSound(links[i].reference,0)'))
        self.assertIn('"Sorry, but this interior cannot be run with 16MB of Fast RAM."', scene)
        self.assertIn('"Press ENTER to return."', scene)
        amiga = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        self.assertIn('aw_fast_ram_found_mb = aw_fast_ram_short_mb > 0 ? aw_fast_ram_short_mb : 1;', amiga)

    def test_every_entry_goes_through_the_check(self):
        # CHIM-32MB-SAVE-ENTRY-48: a save load, a start, dbg tp and a raw map/changelevel/load ask the same check
        # before anything is left or queued (the behaviour: tests/aga_scene_test.c, tests/aga_chim_save_test.c).
        src = ROOT / 'engine/aga/src'
        save = (src / 'aw_save.c').read_text(encoding='utf-8')
        read = save[save.index('int AW_SaveRead('):save.index('void AW_SaveSchedule(')]
        self.assertLess(read.index('aw_save_entry_refuse(candidate.scene,candidate.position))return 2;'),
                        read.index('Cbuf_InsertText(map)'))
        self.assertIn('aw_save_entry_refuse=AW_SceneSaveEntryRefuse;', (src / 'aw_debug.c').read_text(encoding='utf-8'))
        host = (src / 'host_cmd.c').read_text(encoding='latin-1')
        for start, end, before in (('void Host_Map_f (void)', 'Host_Changelevel_f', 'CL_Disconnect ();'),
                                   ('void Host_Changelevel_f (void)', 'Host_Restart_f', 'SV_SpawnServer (level);'),
                                   ('void Host_Loadgame_f (void)', 'SaveGamestate', 'CL_Disconnect_f ();')):
            body = host[host.index(start):]
            body = body[:body.index(end, len(start))]
            self.assertLess(body.index('AW_SceneMapRefuse ('), body.index(before), start)
        scene = (src / 'aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('if(!region_crossing && AW_SceneEntryRefuse(link->target,link->arrival,0))return;', scene)
        self.assertIn('if(AW_SceneEntryRefuse(r->target,r->arrival,1))return;', scene)


if __name__ == '__main__':
    unittest.main()
