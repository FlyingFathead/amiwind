"""CHIM interiors (docs/chim/INTERIOR_STORE.md): the room record reader (C, chim_format.c) and how a room map's
placements are loaded, linked and collided (chim_room.c through chim_world.c's hooks)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga'))) / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class RoomRecordNativeTests(unittest.TestCase):
    def test_reader_and_refusals(self):
        with tempfile.TemporaryDirectory() as scratch:
            executable = Path(scratch) / 'room-record-check'
            command = ['cc', '-std=gnu89', '-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all',
                       '-I' + str(SOURCE), str(ROOT / 'tests/aga_chim_room_record_test.c'),
                       str(SOURCE / 'chim/chim_format.c'), '-lm', '-o', str(executable)]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('room record:', result.stdout)


class RoomLoaderSourceTests(unittest.TestCase):
    def setUp(self):
        self.room = (SOURCE / 'chim/chim_room.c').read_text()
        self.world = (SOURCE / 'chim/chim_world.c').read_text()

    def test_a_room_map_loads_whole_without_frames(self):
        begin = self.world[self.world.index('static void MapBeginWork (const char *entities, double spike_t0)\n{'):]
        begin = begin[:begin.index('\n}\n')]
        self.assertIn('WorldspawnKey (entities, "_chim_room"', begin)
        self.assertIn('Chim_StoreSelect (store)', begin)
        # the room returns before any frame, terrain, far layer or graft
        at = begin.index('ChimRoom_Begin (room_name)')
        for frame_only in ('ChimChunks_Begin', 'ChimFar_Begin', 'ChimGraft_Begin', 'ChimStatics_Begin'):
            self.assertGreater(begin.index(frame_only), at, frame_only)
        self.assertIn('ChimModels_Step (id, &budget)', self.room)
        self.assertIn('ChimZone_Lock (cm);', self.room)

    def test_placements_collide_and_draw_as_chunk_placements(self):
        self.assertIn('ChimChunks_ClipPlace (p, room.rot + 9*i, start, mins, maxs, end, best);', self.room)
        self.assertIn('R_SplitEntityOnNode (cl.worldmodel->nodes);', self.room)
        self.assertIn('p->ent.aw_light = ChimFormat_RecordLight (h.minor, rec.flags);', self.room)
        self.assertIn('ChimRoom_Clip (start, mins, maxs, end, best);', self.world)
        self.assertIn('ChimRoom_Link ();', self.world)

    def test_everything_goes_at_the_next_map(self):
        end = self.world[self.world.index('static void MapEnd (void)'):]
        end = end[:end.index('\n}\n')]
        self.assertIn('ChimRoom_End ();', end)
        self.assertIn('ChimZone_Unlock (room.model[i]);', self.room)

    def test_built_and_shipped(self):
        self.assertIn('chim/chim_room.c', (ROOT / 'engine/aga/Makefile').read_text())
        import json
        self.assertIn('engine/aga/src/chim/chim_room.c',
                      json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
