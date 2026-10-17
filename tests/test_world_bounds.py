# SPDX-License-Identifier: GPL-3.0-only
"""World bounds: the cell lookup (edge ring, sides, drift), the field, the builder option (default on, off
leaves the game as before) and the engine wiring; the engine's rules are checked against the reference."""
import os
import shutil
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_bounds as wb  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
C = wb.CELL
# A test island: cells 0..4 x 0..3, the north-east corner cut out (3,3) (4,3), a one-cell peninsula (2,4)
# to the north, and one sea cell (1,1) enclosed inside.
ISLAND = {(x, y) for x in range(5) for y in range(4)} - {(3, 3), (4, 3), (1, 1)} | {(2, 4)}


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


class LookupTests(unittest.TestCase):
    def test_ring_sides_and_drift(self):
        ring = wb.ring(ISLAND)
        self.assertEqual(ring[(0, 0)], ['west', 'south'])
        self.assertEqual(ring[(2, 4)], ['east', 'north', 'west'])
        self.assertEqual(ring[(4, 2)], ['east', 'north'])
        self.assertEqual(ring[(2, 2)], ['corner'])              # open only at corners (3,3) and (1,1)
        self.assertEqual(ring[(1, 2)], ['south'])               # the enclosed sea cell below it
        normal, drift = wb.drift_of(['east'])
        self.assertEqual((normal, drift), ((1.0, 0.0), (-0.0, 1.0)))   # east edge: drift north (anticlockwise)
        normal, drift = wb.drift_of(['north'])
        self.assertEqual(drift, (-1.0, 0.0))                             # north edge: drift west
        self.assertIsNone(wb.drift_of(['corner']))
        self.assertIsNone(wb.drift_of(['east', 'west']))                 # a one-cell strip: no single normal
        self.assertEqual(wb.box(ISLAND), (0, 0, 4, 4))
        self.assertEqual(wb.enclosed_holes(ISLAND), [(1, 1)])

    def test_directory_cells_are_the_core_cells(self):
        rows = [((1024.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0)),           # cell 0,0 whole
                *[((-2048 + 512.0 + 1024 * i, 512.0 + 1024 * j, 0.0), (-512.0, -512.0, 512.0, 512.0))
                  for i in range(2) for j in range(2)]]                                 # cell -1,0 in four maps
        raw = bytearray(b'AWR2' + struct.pack('<I', len(rows)) + bytes(56))
        for i, (origin, core) in enumerate(rows):
            raw += b'vf%04d\0' % i + bytes(1) + struct.pack('<3f', *origin) + struct.pack('<4f', *core) + bytes(16)
        self.assertEqual(wb.cells_from_directory(bytes(raw)), {(0, 0), (-1, 0)})
        with self.assertRaises(ValueError):
            wb.cells_from_directory(bytes(raw[:-1]))

    def test_public_reference_land_cells(self):
        cells, source = wb.cells_from_progress(ROOT / 'docs' / 'chim' / 'cell-progress-reference.json')
        if source != 'LAND cells':
            self.skipTest('the reference now records open-world maps')
        out = wb.report(set(cells), cells, source)
        # 1,193 land cells and 197 seabed cells (LAND without heights, measured as empty sea; the 98 of
        # CHIMPORT-OCEAN-LAND-41 counted as LAND cells since their CHIMport run of 17 October 2026)
        self.assertEqual(out['cells'], 1390)
        self.assertEqual(out['box']['cells'], [-18, -19, 23, 27])
        self.assertEqual(out['ring']['cells'], sum(out['ring']['by_kind'].values()))
        self.assertEqual(set(out['ring']['by_kind']), {'land', 'seabed'})
        self.assertEqual(out['enclosed_holes'], [])


class FieldTests(unittest.TestCase):
    def test_inside_edge_outside_far(self):
        self.assertIsNone(wb.field(ISLAND, 0.5 * C, 2.5 * C))               # an edge cell, 1024 from its edge
        self.assertIsNone(wb.field(ISLAND, 3.5 * C, 1.5 * C))               # deep inside
        depth, n = wb.field(ISLAND, 5 * C - 100, 1.5 * C)                   # 100 inside the east edge
        self.assertAlmostEqual(depth, -100)
        self.assertEqual(n, (1.0, 0.0))
        depth, n = wb.field(ISLAND, 5 * C + 300, 1.5 * C)                   # 300 past it
        self.assertAlmostEqual(depth, 300)
        self.assertEqual(n, (1.0, 0.0))
        depth, n = wb.field(ISLAND, 5 * C + 300, 3 * C + 400)               # round the outer corner: diagonal
        self.assertAlmostEqual(depth, 500)
        self.assertAlmostEqual(n[0], .6)
        self.assertAlmostEqual(n[1], .8)
        depth, n = wb.field(ISLAND, 20 * C, 2 * C)                          # far out: back to the middle
        self.assertEqual(depth, wb.FAR)
        self.assertGreater(n[0], .9)

    def test_push_turns_a_swimmer_along_the_edge(self):
        x, y = 5 * C + wb.FULL + 10, 1.5 * C                                # past FULL on the east side
        (vx, vy), (dx, dy) = wb.push(ISLAND, x, y, 140.0, 0.0, 3)
        self.assertEqual((vx, vy), (0.0, 0.0))                              # swimming out: faded to nothing
        self.assertAlmostEqual(dx, -wb.INWARD)                              # back in
        self.assertAlmostEqual(dy, wb.CURRENT)                              # and along: north, Quake's 150
        (vx, vy), (dx, dy) = wb.push(ISLAND, x, y, -100.0, 50.0, 0)          # walking in, out of water
        self.assertEqual((vx, vy), (-100.0, 50.0))                          # inward motion is never touched
        self.assertAlmostEqual(dy, 0.0)                                     # no current out of the water
        (vx, vy), (dx, dy) = wb.push(ISLAND, 5 * C + wb.HARD + 50, y, 0.0, 0.0, 0)
        self.assertAlmostEqual(dx, -4 * wb.INWARD)                          # past HARD: four times as strong
        self.assertEqual(wb.push(ISLAND, 3.5 * C, 1.5 * C, 10.0, 0.0, 3), ((10.0, 0.0), (0.0, 0.0)))
        self.assertLess(wb.HARD + 16, wb.OVERLAP)                           # the push acts before the wall

    def test_never_trapped(self):
        """From every point of the band round the test island, following only the drift (no input) leads
        back inside the world within a bounded time."""
        for x0 in range(-1, 7):
            for y0 in range(-1, 7):
                for fx, fy in ((.1, .1), (.5, .5), (.9, .3)):
                    x, y = (x0 + fx) * C, (y0 + fy) * C
                    f = wb.field(ISLAND, x, y)
                    if f is None or f[0] <= 0 or f[0] > wb.OVERLAP:
                        continue
                    for _ in range(2000):                                   # 0.05 s steps, 100 s
                        f = wb.field(ISLAND, x, y)
                        if f is None or f[0] <= 0:
                            break
                        _, (dx, dy) = wb.push(ISLAND, x, y, 0.0, 0.0, 3)
                        x, y = x + dx * .05, y + dy * .05
                    self.assertTrue(f is None or f[0] <= 0, (x0, y0, fx, fy))

    def test_engine_rules_match_the_reference(self):
        if os.name == 'nt' or not shutil.which('cc'):
            self.skipTest('native fixtures run inside Linux Docker')
        import test_aga_native_source as native
        args = [str(len(ISLAND))] + [str(v) for c in sorted(ISLAND) for v in c]
        for x in range(-6, 31):
            for y in range(-6, 31):
                px, py = x * C / 5 + 37, y * C / 5 + 11
                for water, vx, vy in ((3, 140.0, -30.0), (0, -60.0, 90.0)):
                    f = wb.field(ISLAND, px, py)
                    (ovx, ovy), (dx, dy) = wb.push(ISLAND, px, py, vx, vy, water)
                    args += [repr(px), repr(py), str(water), repr(vx), repr(vy), '1' if f else '0',
                             repr(f[0] if f else 0), repr(f[1][0] if f else 0), repr(f[1][1] if f else 0),
                             repr(ovx), repr(ovy), repr(dx), repr(dy)]
        native.NativeSourceTests().compile_run('aga_bounds_test.c', [SRC / 'aw_bounds_rules.c'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'],
                                               arguments=args)


class BuilderTests(unittest.TestCase):
    def test_default_on_and_off_adds_nothing(self):
        self.assertEqual(wb.DEFAULT, 'on')
        rec = wb.configure(types.SimpleNamespace(world_bounds=None))
        self.assertEqual(rec, {'on': True, 'source': 'default'})
        self.assertEqual(wb.image_arguments(rec), ['--world-bounds'])
        off = wb.configure(types.SimpleNamespace(world_bounds='off'))
        self.assertEqual(off, {'on': False, 'source': '--world-bounds off'})
        self.assertEqual(wb.image_arguments(off), [])
        self.assertEqual(wb.image_arguments(None), [])

    def test_image_step_writes_the_setting_only_when_on(self):
        import build_aga
        shipped = (ROOT / 'config' / 'game.cfg').read_bytes()
        self.assertNotIn(b'aw_world_bounds', shipped)                       # off == the game as before
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / 'default-game.cfg'
            cfg.write_bytes(shipped)
            self.assertIsNone(build_aga.stage_world_bounds(types.SimpleNamespace(world_bounds=False), tmp))
            self.assertEqual(cfg.read_bytes(), shipped)
            rec = build_aga.stage_world_bounds(types.SimpleNamespace(world_bounds=True), tmp)
            self.assertEqual(rec['line'], 'aw_world_bounds 1')
            self.assertTrue(cfg.read_bytes().startswith(shipped))
            self.assertTrue(cfg.read_bytes().endswith(b'\naw_world_bounds 1\n'))
            self.assertNotIn(b'\r', cfg.read_bytes())

    def test_default_build_passes_it_to_the_image_step_and_off_does_not(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_build_defaults import steps
        self.assertIn('--world-bounds', dict(steps())['image'])
        self.assertIn('--world-bounds', dict(steps('--world-bounds', 'on'))['image'])
        self.assertNotIn('--world-bounds', dict(steps('--world-bounds', 'off'))['image'])

    def test_builder_wiring(self):
        build = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("add_world_bounds_option(p)", build)
        self.assertIn("args.world_bounds_record = __import__('world_bounds').configure(args)", build)
        self.assertIn('"world_bounds": getattr(args, \'world_bounds_record\', None)', build)
        image = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--world-bounds',action='store_true'", image)
        self.assertIn("stage_world_bounds(args, boot/'id1')", image)


class EngineWiringTests(unittest.TestCase):
    def test_physics_hook_walk_and_fly_not_noclip(self):
        physics = code('sv_phys.c')
        client = physics[physics.index('void SV_Physics_Client'):physics.index('SV_Physics_None')]
        walk = client[client.index('case MOVETYPE_WALK'):client.index('case MOVETYPE_TOSS')]
        fly = client[client.index('case MOVETYPE_FLY'):client.index('case MOVETYPE_NOCLIP')]
        noclip = client[client.index('case MOVETYPE_NOCLIP'):client.index('default:')]
        for part in (walk, fly):
            self.assertIn('aw_bounds_player (ent, drift)', part)
            self.assertIn('VectorSubtract (ent->v.velocity, drift, ent->v.velocity)', part)  # basevelocity form
        self.assertNotIn('aw_bounds', noclip)

    def test_cvar_command_and_sources(self):
        glue = code('aw_bounds.c')
        self.assertIn('cvar_t aw_world_bounds={"aw_world_bounds","0"}', glue)   # the builder turns it on
        self.assertIn('Cmd_AddCommand("aw_worldbounds",command)', glue)
        self.assertIn('ent->v.movetype==MOVETYPE_NOCLIP', glue)
        self.assertIn('AW_BoundsInit();', code('aw_debug.c'))
        self.assertIn('AW_WorldRegionCentres', code('aw_world.c'))
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_bounds_rules.c aw_bounds.c', makefile)
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'\nWORLD / TRAVEL\|worldbounds\|aw_worldbounds\|')
        rules = code('aw_bounds.h')
        for name in ('PRE', 'FULL', 'HARD', 'CURRENT', 'INWARD'):
            value = float(rules.split('#define AW_BOUNDS_%s ' % name)[1].split('f')[0])
            self.assertEqual(value, getattr(wb, name), name)
        self.assertEqual(float(rules.split('#define AW_BOUNDS_CELL ')[1].split('f')[0]), wb.CELL)


if __name__ == '__main__':
    unittest.main()
