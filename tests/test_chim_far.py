# SPDX-License-Identifier: GPL-3.0-only
"""CHIM far terrain (CHIM-FAR-TERRAIN-33): the builder's layer (tools/chim/far.py), the image step's
sidecar beside the frame map, and the engine's loader and rasterizer (native, tests/aga_chim_far_test.c)."""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import far  # noqa: E402

SRC = ROOT / 'engine/aga/src'


def vhgt(heights):
    """A VHGT subrecord body for 65 x 65 heights (multiples of 8): base, deltas, 3 pad bytes."""
    h = np.asarray(heights, dtype=np.int64) // 8
    base = float(h[0, 0])
    deltas = np.zeros((65, 65), dtype=np.int64)
    deltas[0, 0] = 0
    for y in range(65):
        deltas[y, 0] = h[y, 0] - (h[y - 1, 0] if y else h[0, 0])
        deltas[y, 1:] = np.diff(h[y])
    assert np.abs(deltas).max() < 128
    return struct.pack('<f', base) + deltas.astype(np.int8).tobytes() + b'\0\0\0'


def land_record(cx, cy, heights):
    sub = b'INTV' + struct.pack('<I', 8) + struct.pack('<ii', cx, cy)
    body = vhgt(heights)
    sub += b'VHGT' + struct.pack('<I', len(body)) + body
    return b'LAND' + struct.pack('<III', len(sub), 0, 0) + sub


def slope(cx, cy):
    """Heights of a cell on the plane z = x/16 + y/32 (world units, multiples of 8), floored at -512."""
    xs = cx * 8192 + np.arange(65) * 128
    ys = cy * 8192 + np.arange(65) * 128
    z = (xs[None, :] // 16) + (ys[:, None] // 32)
    return np.maximum(z, -512) // 8 * 8


class FarLayerBuilderTests(unittest.TestCase):
    def test_area_grows_the_frame_by_the_margin_and_snaps_to_the_step(self):
        # Balmora-like frame: centre on a cell corner, 3 x 3 cells (6144 local units) from -3072.
        x0, y0, nx, ny = far.area((-20480.0, -12288.0), (-3072.0, -3072.0), (6144.0, 6144.0), 2, 1024)
        self.assertEqual((x0, y0), (-20480 - 12288 - 16384, -12288 - 12288 - 16384))
        self.assertEqual((nx, ny), (57, 57))
        self.assertEqual(far.area((100.0, 0.0), (0.0, 0.0), (10.0, 10.0), 0, 1024)[:2], (0, 0))
        with self.assertRaises(ValueError):
            far.area((0, 0), (0, 0), (1, 1), 1, 1000)

    def test_samples_are_exact_land_with_the_neighbour_edge_and_water(self):
        lands = {(0, 0): slope(0, 0).astype(float), (1, 0): slope(1, 0).astype(float)}
        self.assertEqual(far.sample(lands, 1024, 2048), float(slope(0, 0)[16, 8]))
        # x = 16384 is sample 0 of cell 2 (no LAND) and sample 64 of cell 1: the neighbour's.
        self.assertEqual(far.sample(lands, 16384, 0), float(slope(1, 0)[0, 64]))
        self.assertIsNone(far.sample(lands, 16384 + 1024, 0))
        g = far.heights(lands, 0, 0, 3, 2, 8192)
        self.assertEqual(g.dtype, np.int16)
        self.assertEqual(int(g[0, 1]), max(0, int(round(slope(1, 0)[0, 0] * 0.25))))
        self.assertEqual(int(g[0, 2]), max(0, int(round(slope(1, 0)[0, 64] * 0.25))))
        # y = 8192 is sample 0 of cell (0, 1) (no LAND) and sample 64 of cell (0, 0): the neighbour's.
        self.assertEqual(int(g[1, 0]), max(0, int(round(slope(0, 0)[64, 0] * 0.25))))
        self.assertEqual(int(far.heights(lands, 0, 9216, 1, 1, 1024)[0, 0]), 0)     # no LAND: the water level
        lands[(0, 0)][:] = -800                     # under water: the water level
        self.assertEqual(int(far.heights(lands, 0, 0, 1, 1, 1024)[0, 0]), 0)

    def test_file_round_trip_and_refusals(self):
        grid = (np.arange(12, dtype=np.int16).reshape(3, 4) * 37 - 100).astype(np.int16)
        data = far.encode((-3, -2), -36864, -28672, 1024, grid, 8)
        self.assertEqual(len(data), 40 + 2 * 12)
        self.assertEqual(data[:4], b'CHFL')
        head, back, st = far.decode(data)
        self.assertEqual((head['version'], st), (2, []))
        self.assertEqual(head['cell'], (-3, -2))
        self.assertEqual(head['size'], (4, 3))
        self.assertEqual((head['step'], head['scale'], head['block']), (1024, 0.25, 8))
        self.assertTrue((back == grid).all())
        self.assertEqual(struct.unpack_from('>h', data, 40)[0], -100)        # big-endian heights
        bad = bytearray(data)
        bad[45] ^= 1
        with self.assertRaises(ValueError):
            far.decode(bytes(bad))
        with self.assertRaises(ValueError):
            far.decode(data[:-2])
        with self.assertRaises(ValueError):
            far.encode((0, 0), 0, 0, 1024, grid, 17)
        self.assertEqual(far.sidecar_name('maps/balmora-chim.bsp'), 'maps/balmora-chim.far')
        self.assertEqual(far.file_name((-3, -2)), '-3_-2.far')

    def test_object_stamps_raise_large_boxes_only_and_round_trip(self):
        grid = np.zeros((5, 5), dtype=np.int16)          # samples every 128 local units from (0, 0)
        boxes = [((100, 100, 0), (300, 300, 180)),        # a house: samples (1..2, 1..2) -> 180
                 ((390, 10, 0), (420, 40, 300)),          # narrow (30 wide): flora, left out
                 ((440, 440, 0), (470, 500, 40)),         # low: left out
                 ((480, 200, 0), (550, 270, 120))]        # between samples: the nearest one (4, 2)
        st = far.stamps(grid, 0.0, 0.0, 128.0, boxes)
        self.assertEqual(st, [(1 * 5 + 1, 180), (1 * 5 + 2, 180), (2 * 5 + 1, 180), (2 * 5 + 2, 180), (2 * 5 + 4, 120)])
        data = far.encode((0, 0), 0, 0, 512, grid, 4, st)
        self.assertEqual(len(data) % 2, 0)
        head, back, st2 = far.decode(data)
        self.assertEqual((head['stamps'], st2), (5, st))
        self.assertTrue((back == grid).all())
        # version 1 (no stamps) is still read
        v1 = bytearray(far.encode((0, 0), 0, 0, 512, grid, 4))
        struct.pack_into('>H', v1, 4, 1)
        self.assertEqual(far.decode(bytes(v1))[0]['version'], 1)
        bad = far.encode((0, 0), 0, 0, 512, grid, 4, [(6, 50), (6, 60)])
        with self.assertRaises(ValueError):
            far.decode(bad)                               # indices must ascend

    def test_write_layers_reads_land_from_the_master(self):
        frame = {'cell': (0, 0), 'centre': (4096.0, 4096.0), 'low': (-1024.0, -1024.0), 'span': (2048.0, 2048.0)}
        cells = sorted(far.cells_needed([frame], 1, 1024))
        self.assertIn((-1, -1), cells)
        self.assertIn((1, 1), cells)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            esm = b''.join(land_record(cx, cy, slope(cx, cy)) for cx in range(-1, 2) for cy in range(-1, 2))
            (tmp / 'data').mkdir()
            (tmp / 'data/Morrowind.esm').write_bytes(esm)
            rows = far.write_layers(tmp / 'out', [frame], tmp / 'data', margin=1, step=1024)
            self.assertEqual(len(rows), 1)
            head, grid, _ = far.decode((tmp / 'out' / rows[0]['file']).read_bytes())
            self.assertEqual(head['origin'], (-8192.0, -8192.0))
            self.assertEqual(head['size'], (25, 25))
            self.assertEqual(rows[0]['samples_without_land'], 0)
            for j, i in ((0, 0), (12, 20), (24, 24), (8, 9)):
                x, y = -8192 + i * 1024, -8192 + j * 1024
                expect = max(0, int(round(far.sample({k: slope(*k).astype(float) for k in cells}, x, y) * 0.25)))
                self.assertEqual(int(grid[j, i]), expect)
            again = far.write_layers(tmp / 'out2', [frame], tmp / 'data', margin=1, step=1024)
            self.assertEqual(again[0]['sha256'], rows[0]['sha256'])          # deterministic


class FarLayerImageTests(unittest.TestCase):
    def test_sidecar_beside_each_frame_map_checked_against_its_frame(self):
        from build_aga import chim_far_sidecar
        grid = np.zeros((3, 3), dtype=np.int16)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'world/far').mkdir(parents=True)
            (tmp / 'id1/maps').mkdir(parents=True)
            (tmp / 'world/far' / far.file_name((-3, -2))).write_bytes(far.encode((-3, -2), 0, 0, 1024, grid))
            rec = chim_far_sidecar(tmp / 'world', tmp / 'id1', {'map': 'maps/balmora-chim.bsp', 'frame': [-3, -2]})
            self.assertEqual(rec['file'], 'maps/balmora-chim.far')
            self.assertTrue((tmp / 'id1/maps/balmora-chim.far').is_file())
            with self.assertRaises(ValueError):            # already there
                chim_far_sidecar(tmp / 'world', tmp / 'id1', {'map': 'maps/balmora-chim.bsp', 'frame': [-3, -2]})
            self.assertIsNone(chim_far_sidecar(tmp / 'world', tmp / 'id1', {'map': 'maps/x-chim.bsp', 'frame': [9, 9]}))
            (tmp / 'world/far' / far.file_name((5, 5))).write_bytes(far.encode((4, 5), 0, 0, 1024, grid))
            with self.assertRaises(ValueError):            # names another frame
                chim_far_sidecar(tmp / 'world', tmp / 'id1', {'map': 'maps/y-chim.bsp', 'frame': [5, 5]})

    def test_on_by_default_with_a_loud_debugging_opt_out(self):
        import inspect
        from chim.build import build_areas
        self.assertIs(inspect.signature(build_areas).parameters['far_terrain'].default, True)
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        self.assertIn("'--no-far-terrain'", text)
        self.assertIn('DEBUGGING ONLY', text)
        self.assertIn('chim_far_sidecar(chim_world, id1, record)', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))


class FarLayerEngineContractTests(unittest.TestCase):
    def test_fog_pass_hook_and_first_method_kept(self):
        fog = (SRC / 'aw_fog.c').read_text()
        self.assertIn('void (*aw_chim_far_draw)(byte colour,int distance);', fog)
        body = fog[fog.index('void AW_FogDraw(void)'):]
        body = body[:body.index('\n}\n')]
        # after the fog pass, only with fog on, in the full fog colour, as the LAND pass
        self.assertGreater(body.index('if(fog && aw_chim_far_draw)aw_chim_far_draw(ramp[15<<8],distance);'),
                           body.index('for(y=r_refdef.vrect.y;'))
        far_c = (SRC / 'chim/chim_far.c').read_text()
        self.assertIn('cvar_t\tchim_far = {"chim_far", "1"};', far_c)       # default on; 0 = no far land
        self.assertIn('cvar_t\tchim_far_reach = {"chim_far_reach", "896"};', far_c)       # the legacy overlap depth
        self.assertIn('cvar_t\tchim_far_objects = {"chim_far_objects", "0"};', far_c)   # object stamps: experimental
        world = (SRC / 'chim/chim_world.c').read_text()
        self.assertIn('ChimFar_Begin (sv.worldmodel->name', world)
        self.assertIn('ChimFar_End ();\n\tChimGraft_End ();', world)
        self.assertIn('ChimFar_Hook ();', world)
        self.assertIn('chim/chim_far.c', (ROOT / 'engine/aga/Makefile').read_text())
        # the skyline methods are untouched (HORSTATOR APPROVED default, silhouetting kept)
        self.assertIn('static cvar_t aw_skyline_fill={"aw_skyline_fill","1",true};', fog)
        self.assertIn('aw_skyline_fill 0', (ROOT / 'config/game.cfg').read_text())


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class FarLayerNativeTests(unittest.TestCase):
    SOURCES = [SRC / 'aw_horizon.c', SRC / 'mathlib.c', SRC / 'chim/chim_far.c', SRC / 'chim/chim_format.c']

    def test_grid_rasterizer_matches_ray_geometry_and_culls_exactly(self):
        from test_chim_engine_native import compile_and_run
        out = compile_and_run(self, 'aga_chim_far_test.c', self.SOURCES, [('grid',)])
        self.assertIn('culling exact', out[0])

    def test_loader_reads_the_writers_file_and_refuses_damaged_ones(self):
        from test_chim_engine_native import compile_and_run
        nx, ny = 21, 17
        grid = np.fromfunction(lambda j, i: 3 * i + 2 * j, (ny, nx)).astype(np.int16)
        ok = far.encode((-3, -2), -36864, -28672, 1024, grid, 8)
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            (maps / 'far-ok.far').write_bytes(ok)
            bad = bytearray(ok)
            bad[60] ^= 4
            (maps / 'far-crc.far').write_bytes(bytes(bad))
            (maps / 'far-frame.far').write_bytes(far.encode((-2, -2), -36864, -28672, 1024, grid, 8))
            (maps / 'far-short.far').write_bytes(ok[:-1])
            (maps / 'far-obj.far').write_bytes(far.encode((-3, -2), -36864, -28672, 1024, grid, 8,
                                                          [(9 * nx + 4, 900), (9 * nx + 5, 901)]))
            x0, y0 = (-36864 + 20480) * 0.25, (-28672 + 12288) * 0.25
            out = compile_and_run(self, 'aga_chim_far_test.c', self.SOURCES,
                                  [('load', nx, ny, x0, y0, 256, 7, 5, int(grid[5, 7]), int(grid[ny // 2, nx // 4]),
                                    4, 9, 900, int(grid[9, 4]))],
                                  cwd=tmp)
            self.assertIn('refused files draw nothing', out[0])

    def test_terrain_floor_reads_the_resident_layer(self):
        # CHIM-GRAFT-REPACK-EMPTY-33 (second layer): the far layer is the terrain floor.
        from test_chim_engine_native import compile_and_run
        nx, ny = 21, 17
        grid = np.fromfunction(lambda j, i: 40 + 3 * i + 2 * j + (i * j % 5) * 7, (ny, nx)).astype(np.int16)
        grid[2:5, 3:7] = 0      # water: the layer keeps the water level there, not the bed
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            (maps / 'far-floor.far').write_bytes(far.encode((-3, -2), -36864, -28672, 1024, grid, 8))
            (maps / 'far-obj.far').write_bytes(far.encode((-3, -2), -36864, -28672, 1024, grid, 8,
                                                          [(12 * nx + 2, 900)]))
            out = compile_and_run(self, 'aga_chim_far_test.c', self.SOURCES, [('floor', nx, ny)], cwd=tmp)
            self.assertIn('terrain floor:', out[0])


class TerrainFloorContractTests(unittest.TestCase):
    """CHIM-GRAFT-REPACK-EMPTY-33, second layer: with noclip off the terrain is the lowest height. The
    floor reads only the resident far layer and the frame's chunk table (never the streamed chunks), runs
    for walking and free-falling bodies only, and says what it did in one console line."""

    def test_hooks_and_switch(self):
        far_c = (SRC / 'chim/chim_far.c').read_text()
        self.assertIn('cvar_t\tchim_terrain_floor = {"chim_terrain_floor", "1"};', far_c)   # on; 0 = the old fall
        self.assertIn('Cvar_RegisterVariable (&chim_terrain_floor);', far_c)
        self.assertIn('aw_chim_floor = Floor;', far_c)
        floor = far_c[far_c.index('static int Floor ('):far_c.index('int ChimFar_Floor (')]
        for streamed in ('ChimGraft', 'ChimModels', 'chim_graft', '.chunk.', 'terrain.data'):
            self.assertNotIn(streamed, floor)
        self.assertIn('extern int (*aw_chim_floor)(const vec3_t origin, float *lowest, float *surface);',
                      (SRC / 'chim/chim.h').read_text())

    def test_walk_and_free_fall_only(self):
        walk = (SRC / 'aw_walk.c').read_text()
        body = walk[walk.index('void AW_WalkPlayer(edict_t *p)'):walk.index('qboolean AW_ActorStep')]
        self.assertIn('if(!actor_step){if(swimming)floor_held=0;else AW_TerrainFloor(p,1);}', body)
        step = walk[walk.index('qboolean AW_ActorStep'):]
        self.assertLess(step.index('actor_step=1;'), step.index('AW_WalkPlayer(p);'))
        self.assertLess(step.index('AW_WalkPlayer(p);'), step.index('actor_step=0;'))
        floor = walk[walk.index('int AW_TerrainFloor(edict_t *e, int player)'):]
        self.assertIn('e->v.movetype==MOVETYPE_NOCLIP || e->v.movetype==MOVETYPE_FLY', floor)
        # the console line (regression: one line per lift, says who, how deep and where)
        self.assertIn('Con_Printf("Terrain floor: %s %ld units below the ground at %ld %ld, lifted onto it\\n",', floor)
        physics = (SRC / 'sv_phys.c').read_text()
        client = physics[physics.index('void SV_Physics_Client (edict_t\t*ent, int num)'):]
        client = client[:client.index('PlayerPostThink')]
        self.assertEqual(client.count('AW_WalkPlayer(ent);'), 1)
        self.assertNotIn('AW_TerrainFloor', client)          # noclip, fly and toss never ask
        walk_case = client[client.index('case MOVETYPE_WALK:'):client.index('case MOVETYPE_TOSS:')]
        self.assertIn('AW_WalkPlayer(ent);', walk_case)
        step_c = physics[physics.index('#else\nvoid SV_Physics_Step (edict_t *ent)'):]
        step_c = step_c[:step_c.index('SV_RunThink (ent);')]
        self.assertLess(step_c.index('SV_FlyMove (ent, host_frametime, NULL);'), step_c.index('AW_TerrainFloor (ent, 0);'))
        self.assertLess(step_c.index('AW_TerrainFloor (ent, 0);'), step_c.index('SV_LinkEdict (ent, true);'))


if __name__ == '__main__':
    unittest.main()
