# SPDX-License-Identifier: GPL-3.0-only
"""ROOM-AKULAKHAN-HEAP-52: what a CHIM room map really has and needs.

A room map holds nothing but its room. Akulakhan's Chamber needs about 19.1 MB with its activators kept (148 models,
five of 1 to 2.2 MB): more than the zone and the automatic cache bank of the 32 MB minimum (14.3 MB). The engine now
lets a room that does not fit grow (engine/aga/src/chim/chim_world.c Chim_RoomGrow, chim_room.c ChimRoom_Begin): a
bank of the free Fast RAM (its largest block less 2 MiB in 64 KiB steps; measured in a room map at 32 MiB after Balmora:
5,512 KiB, so 3,456 KiB; CHIM-ROOM-HEART-CHAMBER-LOAD-50), then
the Hunk's rest past the zone. The builder's room model (tools/chim/heap.py room_zone_limits, room_blocks, room_heap)
counts the same steps and the engine's own blocks, and a room past one bank is loaded through the engine's own
allocator (tools/chim/room_zone.py). The early check (room_store_heap, the chim-interiors stage) stops a build whose
room cannot fit seconds after the store is written. The engine's side: tests/aga_chim_world_test.c roomgrow."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import engine_limits as EL  # noqa: E402
from chim import heap as H  # noqa: E402

SRC = ROOT / 'engine/aga/src'
MIB = 1 << 20
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')


def struct_body(text, name):
    """The member lines of a C typedef struct ending in NAME (comments and blank space dropped)."""
    end = text.index('} %s;' % name)
    start = text.rindex('{', 0, end)
    body = re.sub(r'/\*.*?\*/', '', text[start + 1:end], flags=re.S)
    return [' '.join(line.split()) for line in body.splitlines() if line.strip()]


class EngineBlocks(unittest.TestCase):
    """The engine structures the room model counts (chim/heap.py ROOM_*): a change here must change the model."""

    def test_the_counted_structures_are_the_engines(self):
        local = (SRC / 'chim/chim_local.h').read_text(encoding='utf-8')
        self.assertEqual(struct_body(local, 'chim_place_t'), [
            'entity_t ent;', 'vec3_t mins, maxs;', 'float s, c;', 'unsigned pid, model;', 'int owner;',
            'int linked;', 'int flags;', 'int leaves;'])
        self.assertEqual(H.ROOM_PLACE_EXTRA, 2 * 12 + 2 * 4 + 6 * 4)
        self.assertEqual(struct_body(local, 'chim_file_row_t'), [
            'char kind[5];', 'signed char group;', 'unsigned char digits;', 'unsigned char kept;', 'short cx, cy;',
            'unsigned short sector;', 'unsigned bytes, crc, entries;'])
        self.assertGreaterEqual(H.ROOM_INDEX_ROW, 5 + 3 + 3 * 2 + 3 * 4)
        self.assertEqual(struct_body(local, 'chim_model_t'), [
            'model_t model;', 'aw_brush_arena_t arena;', 'unsigned id;', 'int kind;', 'int leafs;', 'long piece_bytes;',
            'int pieces;'])
        arena = struct_body((SRC / 'model.h').read_text(encoding='utf-8'), 'aw_brush_arena_t')
        # base, size and used, slice, slice_bytes, texture, context, point_hull_only: 8 words on 7 lines
        self.assertEqual(arena, ['byte *base;', 'int size, used;', 'byte *slice;', 'int slice_bytes;',
                                 'struct texture_s *(*texture)(void *context, int id);', 'void *context;',
                                 'int point_hull_only;'])
        self.assertGreaterEqual(H.ROOM_MODEL_EXTRA, 8 * 4 + 5 * 4)
        fmt = (SRC / 'chim/chim_format.h').read_text(encoding='utf-8')
        self.assertEqual(struct_body(fmt, 'chim_asset_t'), ['unsigned short file, width, height, pad;',
                                                             'unsigned offset, bytes, render;'])
        self.assertEqual(H.ROOM_INDEX_ASSET, 4 * 2 + 3 * 4 + 4)
        zone = (SRC / 'chim/chim_zone.c').read_text(encoding='utf-8')
        self.assertEqual(struct_body(zone, 'chim_block_t'), [
            'int size;', 'unsigned char kind, bank;', 'short locks;', 'unsigned id;', 'chim_user_t *user;',
            'struct chim_block_s *prev, *next;', 'struct chim_block_s *lru_prev, *lru_next;'])
        self.assertEqual(H.ROOM_BLOCK_HEADER, (4 + 2 + 2 + 4 + 5 * 4 + 15) & ~15)
        prefetch = (SRC / 'chim/chim_prefetch.c').read_text(encoding='utf-8')
        self.assertIn('#define SLOTS\t\t\t(1 << 12)', prefetch)
        self.assertEqual(struct_body(prefetch, 'slot_t'), ['unsigned id;', 'void *data;'])
        self.assertEqual(H.ROOM_PREFETCH_TABLE, 4096 * 8)
        room = (SRC / 'chim/chim_room.c').read_text(encoding='utf-8')
        self.assertIn('size = ((pack.bytes + 3) & ~3L) + (long)h.count*(long)sizeof(chim_place_t) + '
                      '9L*h.count*(long)sizeof(float) +\n\t\t(long)room.models*(long)sizeof(chim_model_t *);', room)


class RoomGrowthModel(unittest.TestCase):
    """The builder's figures for Chim_RoomGrow, read from the engine source."""

    def test_the_room_step_is_the_engines(self):
        keep = 2 * MIB
        self.assertEqual(EL.room_step(6222 * 1024), 4160 * 1024)   # a first map at 32 MiB: 64 KiB steps
        self.assertEqual(EL.room_step(5512 * 1024), 3456 * 1024)   # after Balmora (CHIM-ROOM-HEART-CHAMBER-LOAD-50)
        self.assertEqual(EL.room_step(keep + MIB + 65535), MIB)
        self.assertEqual(EL.room_step(keep + MIB + 65536), MIB + 65536)
        self.assertEqual(EL.room_step(keep), 0)
        self.assertEqual(EL.room_step(keep + MIB - 1), 0)          # under CHIM_ROOM_LEAST
        self.assertEqual(EL.room_step(keep + MIB), MIB)
        self.assertEqual(EL.room_step(100 * MIB + 5), 98 * MIB)
        self.assertEqual(EL.room_step(0), 0)

    @unittest.skipIf(os.name == 'nt' or not COMPILER, 'a Linux C compiler is required')
    def test_the_room_step_matches_the_compiled_engine(self):
        import ctypes
        from chim.zone_sim import build_library
        with tempfile.TemporaryDirectory() as tmp:
            lib = ctypes.CDLL(str(build_library(Path(tmp))))
            lib.ChimZone_RoomStep.restype = ctypes.c_ulong
            lib.ChimZone_RoomStep.argtypes = [ctypes.c_ulong]
            for largest in (0, 1, 2 * MIB, 3 * MIB - 1, 3 * MIB, 3 * MIB + 65535, 3 * MIB + 65536, 5512 * 1024,
                            6222 * 1024, 6371328, 64 * MIB + 12345):
                self.assertEqual(lib.ChimZone_RoomStep(largest), EL.room_step(largest), largest)

    def test_the_measured_32mb_room_and_the_start_up_model(self):
        at32 = EL.fast_ram_memory(32)
        self.assertEqual(at32['room_largest_bytes'], EL.MEASURED_ROOM['largest_kib'] * 1024)
        self.assertEqual(at32['room_bank_bytes'], 3456 * 1024)
        # 16 MiB: no bank and no free Fast RAM worth a room bank
        at16 = EL.fast_ram_memory(16)
        self.assertEqual((at16['bank_bytes'], at16['room_bank_bytes']), (0, 0))
        # more Fast RAM: the start-up model less what the game took after the start at 32 MiB (measured)
        at64 = EL.fast_ram_memory(64)
        model = (at64['free_after_heap_mib'] - at64['bank_bytes'] // MIB) * MIB
        delta = (at32['free_after_heap_mib'] - at32['bank_bytes'] // MIB) * MIB - at32['room_largest_bytes']
        self.assertEqual(at64['room_largest_bytes'], max(0, model - delta))

    def test_the_hunk_rest_keeps_the_reserve_and_what_loads_after(self):
        memory = EL.chim_memory(heap_mb=13)
        before, after = 820512, 1590272
        free = 13 * MIB - memory['gap_bytes'] - before - after - EL.ZONE_HEADER_BYTES
        self.assertEqual(EL.room_hunk_rest(before, after, memory), (free - memory['zone_kib'] * 1024 - 16) & ~15)
        # the 16 MiB baseline's 11 MiB heap: the whole-map rule binds, the zone takes it all
        self.assertEqual(EL.room_hunk_rest(before, after, EL.chim_memory(heap_mb=11)), 0)
        self.assertEqual(EL.define('chim/chim_zone.h', 'CHIM_ROOM_REST_KIB'),
                         -(-EL.MEASURED_HUNK['client_per_map_bytes'] // 1024))

    def test_akulakhans_chamber_figures(self):
        """The room of the stopped v0.0.52-dev1 image step (2026_10_25_v0.0.52-dev1_dev1-try2_d27706d6): its room map
        sits 820,512 bytes into the Hunk; 32 MB gives a room 20,625,040 bytes (was 14,336,000), the room needs
        19,093,616 (its models 18,569,120, textures 212,672, record 131,664, store index 147,328, prefetch table and the
        buffer header)."""
        limits = H.room_zone_limits(820512, 1589344)
        self.assertEqual(limits['zone_32mb_zone_bytes'] - limits['buffer_bytes'] + limits['bank_bytes'], 14336000)
        # the room's bank: 3,456 KiB of the 5,512 KiB block measured after Balmora (CHIM-ROOM-HEART-CHAMBER-LOAD-50)
        self.assertEqual(limits['min_fast_room_bytes'], 14336000 + 3456 * 1024 + 2094736)
        self.assertEqual(limits['block_bytes_min_fast'], 7 * MIB)
        # 16 MB: the zone alone, as before
        self.assertEqual((limits['zone_bytes'], limits['hunk_rest_bytes']), (7012352, 0))


def blocks(models, textures=None, record=4096, index=8192):
    return {'record': record, 'record_file_bytes': record, 'models': models, 'textures': textures or {},
            'index': index, 'buffer': 32768, 'prefetch_table': H.ROOM_PREFETCH_TABLE}


@unittest.skipIf(os.name == 'nt' or not COMPILER, 'a Linux C compiler is required')
class RoomWalk(unittest.TestCase):
    """chim/room_zone.py: a room loaded through the engine's allocator as chim_room.c loads it."""

    @classmethod
    def setUpClass(cls):
        from chim.room_zone import library
        cls.lib = library()

    def walk(self, room, bank, zone, steps):
        from chim.room_zone import walk
        return walk(room, bank, zone, steps, 64 * 1024, self.lib)

    def test_a_room_in_its_banks_takes_nothing(self):
        room = blocks([(1, 3 * MIB, [1]), (2, 2 * MIB, [1, 2])], {1: 21000, 2: 5440})
        w = self.walk(room, 7 * MIB, 7 * MIB, [('free Fast RAM', 4 * MIB), ('Hunk rest', 2 * MIB)])
        self.assertTrue(w['ok'])
        self.assertEqual((w['grown'], w['tries'], w['untextured']), ([], 1, 0))

    def test_a_room_past_its_banks_grows_step_by_step(self):
        # 7 + 7 MiB of banks, 3.25 MiB models: two per bank; the fifth needs the Fast RAM bank, the sixth the Hunk
        room = blocks([(i, 3 * MIB + MIB // 4, [i]) for i in range(6)], {i: 21000 for i in range(6)})
        w = self.walk(room, 7 * MIB, 7 * MIB, [('free Fast RAM', 4 * MIB), ('Hunk rest', 4 * MIB)])
        self.assertTrue(w['ok'], w)
        self.assertEqual(w['grown'], ['free Fast RAM', 'Hunk rest'])
        self.assertEqual(w['tries'], 3)
        # a step of no bytes is passed over (16 MB: no free Fast RAM), as Chim_RoomGrow does
        w = self.walk(blocks([(i, 3 * MIB, []) for i in range(3)]), 0, 7 * MIB,
                      [('free Fast RAM', 0), ('Hunk rest', 4 * MIB)])
        self.assertTrue(w['ok'], w)
        self.assertEqual(w['grown'], ['Hunk rest'])

    def test_the_sum_fits_but_the_blocks_do_not(self):
        """Three 4.5 MiB models in 7 + 7 MiB: 13.5 MiB of 14 by the sum, but one block each bank holds two of."""
        room = blocks([(i, 4 * MIB + MIB // 2, []) for i in range(3)])
        w = self.walk(room, 7 * MIB, 7 * MIB, [])
        self.assertFalse(w['ok'])
        self.assertIn('model', w['failed'])
        limits = {'zone_bytes': 7 * MIB, 'hunk_rest_bytes': 0, 'zone_room_bytes': 7 * MIB - 32768, 'buffer_bytes': 32768,
                  'zone_32mb_zone_bytes': 7 * MIB, 'bank_bytes': 7 * MIB, 'room_bank_bytes': 0,
                  'hunk_rest_32mb_bytes': 0, 'min_fast_room_bytes': 14 * MIB - 32768, 'block_bytes_min_fast': 7 * MIB}
        report = H.room_heap(room, limits, walk=True, lib=self.lib)
        self.assertLess(report['need_bytes'], limits['min_fast_room_bytes'])
        self.assertFalse(report['ok'])
        self.assertIn('the load through the engine\'s allocator: model', H.room_failure_text('gate', report))

    def test_a_room_within_one_bank_is_decided_by_its_sum(self):
        room = blocks([(1, MIB, [1])], {1: 21000})
        limits = H.room_zone_limits(820512, 1589344)
        report = H.room_heap(room, limits, walk=True, lib=self.lib)
        self.assertTrue(report['ok'] and report['fits_zone'])
        self.assertEqual((report['walk_16mb'], report['walk_32mb']), ('one bank: the sum decides',) * 2)

    def test_a_texture_without_room_is_never_ok(self):
        # the zone holds the models, not every texture: the engine draws those untextured (ResolveTexture)
        room = blocks([(1, 7 * MIB - 200000, [1, 2])], {1: 150000, 2: 150000})
        w = self.walk(room, 0, 7 * MIB, [])
        self.assertFalse(w['ok'] and not w['untextured'])


class RoomGateWording(unittest.TestCase):
    def test_the_early_check_runs_in_the_interiors_stage_with_the_sdk(self):
        build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        stage = build[build.index("steps.insert(at, ('chim-interiors', tool("):]
        stage = stage[:stage.index('return [(name, command')]
        self.assertIn("*(['--sdk', args.sdk] if getattr(args, 'sdk', None) else [])", stage)
        interior = (ROOT / 'tools/chim/interior.py').read_text(encoding='utf-8')
        main = interior[interior.index('def main('):]
        self.assertLess(main.index('receipt = build('), main.index('early_room_heap(args.out, args.sdk, args.jobs)'))

    def test_without_an_sdk_the_early_check_is_recorded_as_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = H.require_room_store_heap(tmp, report_path=Path(tmp) / 'early.json')
            self.assertIsNone(report['ok'])
            self.assertIn('not run', (Path(tmp) / 'early.json').read_text())


if __name__ == '__main__':
    unittest.main()
