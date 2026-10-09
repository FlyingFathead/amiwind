"""CHIM engine pieces compiled on the host with synthetic data (no game data).

- aga_chim_zone_test.c: the non-moving model zone (allocation, LRU, locks,
  banks, a random stress run with integrity checks).
- aga_chim_brush_test.c: model.c's section decoders into a CHIM arena, from
  a file image and streamed one section per step, against the Hunk decode;
  the decoded-size bound; one-submodel images only.
- aga_chim_world_test.c: a synthetic CHIM world (chim/world.cwi, texture,
  model and frame packs in the format 0.1 layout) through the engine's
  start-up probe, map hooks, ring scheduler, shared models, placements,
  efrags and collision; and the legacy path with no CHIM data.
"""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
WARN = ['-Wall', '-Werror', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-but-set-variable',
        '-Wno-pointer-sign', '-Wno-format-truncation', '-Wno-stringop-truncation',
        '-Wno-pointer-to-int-cast', '-Wno-int-to-pointer-cast']


def compile_and_run(test, fixture, sources, arguments_sets=((),), extra=(), cwd=None):
    with tempfile.TemporaryDirectory(prefix='amiwind-chim-') as tmp:
        tmp = Path(tmp)
        from project_version import generate_native
        generate_native(ROOT / 'VERSION', tmp)
        exe = tmp / 'check'
        cmd = [COMPILER, '-std=gnu89', '-O1', '-g', *WARN, '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
               '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
               '-include', str(ROOT / 'tests/aga_test_files.h'), '-I' + str(tmp), '-I' + str(SRC),
               str(ROOT / 'tests' / fixture), *map(str, sources), *extra, '-lm', '-o', str(exe)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = []
        for argv in arguments_sets:
            result = subprocess.run([str(exe), *map(str, argv)], cwd=cwd or tmp, capture_output=True, text=True,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'), timeout=300)
            test.assertEqual(result.returncode, 0, ' '.join(map(str, argv)) + ': ' + result.stdout + result.stderr)
            outputs.append(result.stdout)
        return outputs


class ChimHookContractTests(unittest.TestCase):
    """The hooks CHIM needs in the legacy files stay small and in place; each
    is a NULL pointer test unless chim/world.cwi exists."""

    def test_physics_freezes_only_non_clients_before_any_work(self):
        text = (SRC / 'sv_phys.c').read_text()
        loop = text[text.index('void SV_Physics (void)'):]
        loop = loop[:loop.index('sv.time += host_frametime;')]
        free = loop.index('if (ent->free)')
        frozen = loop.index('if (aw_chim_frozen && i > svs.maxclients && aw_chim_frozen (ent))')
        self.assertLess(free, frozen)
        self.assertLess(frozen, loop.index('force_retouch'))
        self.assertLess(frozen, loop.index('SV_Physics_Client'))

    def test_towns_with_a_frame_map_cross_no_regions(self):
        text = (SRC / 'aw_region.c').read_text()
        for fn, hook in (('const char *AW_RegionWorldModel', 'chim_map(name))!=NULL){'),
                         ('int AW_RegionCrossing', 'if(chim_running())return 0;'),
                         ('const char *AW_RegionAhead', 'chim_running())return NULL;'),
                         ('int AW_RegionContains', 'chim_running())return 1;')):
            body = text[text.index(fn):]
            body = body[:body.index('\n}')]
            self.assertIn(hook, body, fn)

    def test_spawn_loads_the_ring_before_placing_the_player(self):
        text = (SRC / 'aw_scene.c').read_text()
        spawn = text[text.index('void AW_SceneSpawn(edict_t *p) {'):]
        first = spawn.index('if(aw_chim_spawn)aw_chim_spawn(')
        # Arrivals are placed through arrival_place (AW_MapPlace and the interior clearance).
        self.assertLess(first, spawn.index('arrival_place('))
        self.assertLess(first, spawn.index('AW_InteriorPlace('))
        self.assertIn('next.arrival:p->v.origin', spawn[first:first + 120])

    def test_hook_pointers_are_defined_once(self):
        defined = {}
        for path in SRC.glob('*.c'):
            for name in ('aw_chim_map_begin', 'aw_chim_map_end', 'aw_chim_link', 'aw_chim_clip',
                         'aw_chim_player', 'aw_chim_frozen', 'aw_chim_spawn'):
                text = path.read_text(errors='replace')
                if ('(*%s)(' % name) in text and 'extern' not in text.split('(*%s)(' % name)[0].splitlines()[-1]:
                    defined.setdefault(name, []).append(path.name)
        self.assertEqual({k: len(v) for k, v in defined.items()},
                         {k: 1 for k in ('aw_chim_map_begin', 'aw_chim_map_end', 'aw_chim_link', 'aw_chim_clip',
                                         'aw_chim_player', 'aw_chim_frozen', 'aw_chim_spawn')})


@unittest.skipIf(os.name == 'nt', 'native helper fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'install a host C compiler')
class ChimZoneTests(unittest.TestCase):
    def test_zone_fit_lru_locks_banks_and_stress(self):
        out = compile_and_run(self, 'aga_chim_zone_test.c', [SRC / 'chim/chim_zone.c'])
        self.assertIn('chim zone ok', out[0])


def boxes(n, size=48, step=128):
    return [((i % 20 * step, i // 20 * step, 0), (i % 20 * step + size, i // 20 * step + size, size)) for i in range(n)]


@unittest.skipIf(os.name == 'nt', 'native helper fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'install a host C compiler')
class ChimBrushTests(unittest.TestCase):
    """model.c's decoders into a CHIM arena (the test includes model.c)."""

    def run_mode(self, mode, images):
        from chim_fixture import box_bsp
        with tempfile.TemporaryDirectory(prefix='amiwind-chim-bsp-') as tmp:
            paths = []
            for k, kwargs in enumerate(images):
                path = Path(tmp) / ('m%d.bsp' % k)
                path.write_bytes(box_bsp(**kwargs))
                paths.append(path)
            return compile_and_run(self, 'aga_chim_brush_test.c', [], [(mode, *paths)], cwd=tmp)[0]

    def test_arena_decode_matches_hunk_image_and_stream(self):
        # One box, and 300 boxes whose large lumps span several 16 KiB slices.
        out = self.run_mode('miptex', [dict(boxes=boxes(1)), dict(boxes=boxes(300), lighting=40000,
                                                                     entities=b'{\n"classname" "func_wall"\n}\n\0')])
        self.assertEqual(out.count(' ok'), 2, out)
        for line in out.splitlines():
            fields = dict(f.split('=') for f in line.split() if '=' in f)
            # The bound holds and is not wildly above the decoded size.
            self.assertLessEqual(int(fields['used']), int(fields['bound']))
            self.assertLess(int(fields['bound']), 3 * int(fields['used']) + 4096, line)

    def test_texture_references_resolve_through_the_arena(self):
        out = self.run_mode('refs', [dict(boxes=boxes(1), texture_ids=[3]),
                                     dict(boxes=boxes(200), texture_ids=[5], lighting=20000)])
        self.assertEqual(out.count(' ok'), 2, out)

    def test_chained_point_hull_decodes_into_hull0_only(self):
        from chim_fixture import chain_bsp
        with tempfile.TemporaryDirectory(prefix='amiwind-chim-chain-') as tmp:
            path = Path(tmp) / 'chain.bsp'
            path.write_bytes(chain_bsp([((i * 100, 0, 0), (i * 100 + 48, 48, 48)) for i in range(40)]))
            out = compile_and_run(self, 'aga_chim_brush_test.c', [], [('dag', path)], cwd=tmp)[0]
        self.assertIn('chain decoded', out)

    def test_more_than_one_submodel_is_refused(self):
        out = self.run_mode('reject', [dict(boxes=boxes(2), models=2)])
        self.assertIn('rejected', out)

    def test_frame_map_loads_as_a_world_with_the_frame_bounds(self):
        """The frame map's world as tools/chim/frame_map.py writes it (docs/chim/WORLD_FORMAT.md,
        "Activation") loads in the engine with the frame's bounds."""
        from chim import format as F
        from chim.frame_map import FRAME_KEY, empty_world, entity_text, frame_bounds
        with tempfile.TemporaryDirectory(prefix='amiwind-chim-map-') as tmp:
            write_test_world(tmp)
            cell, lo, hi = frame_bounds(tmp)
            lumps = empty_world(lo, hi)
            lumps[0] = entity_text([{'classname': 'worldspawn', FRAME_KEY: '%d %d' % cell},
                                    {'classname': 'info_player_start', 'origin': '64 64 40'}])
            data = F.brush_image(lumps)[0]
            lumps = F.read_brush_image(data)
            self.assertIn(b'"_chim_frame" "0 0"', lumps[0])
            self.assertIn(b'"classname" "info_player_start"', lumps[0])
            mins = struct.unpack_from('<3f', lumps[14])
            maxs = struct.unpack_from('<3f', lumps[14], 12)
            self.assertEqual(mins[:2], (LOW, LOW))
            self.assertEqual(maxs[:2], (LOW + GRAIN * NX, LOW + GRAIN * NX))
            path = Path(tmp) / 'chimtest.bsp'
            path.write_bytes(data)
            out = compile_and_run(self, 'aga_chim_brush_test.c', [], [('miptex', path)], cwd=tmp)[0]
            self.assertIn(' ok', out)

    def test_arena_overflow_stops_instead_of_overwriting(self):
        out = self.run_mode('overflow', [dict(boxes=boxes(50))])
        self.assertIn('overflow stopped', out)


LOW, GRAIN, NX, SECTOR = -384.0, 128, 6, 3
# pid, model, origin, yaw. Model 0 is placed twice (shared); placement 1
# reaches into the chunk east of its owner, placement 4 into the one west.
PLACEMENTS = [(0, 0, (32.0, 32.0, 0.0), 0.0), (1, 1, (124.0, 64.0, 0.0), 0.0), (2, 0, (-200.0, -200.0, 0.0), 90.0),
              (3, 1, (64.0, -64.0, 0.0), 45.0), (4, 1, (0.0, 32.0, 0.0), 0.0), (5, 2, (-330.0, -330.0, 0.0), 0.0)]
MODEL_BOXES = [[((-16, -16, 0), (16, 16, 64))], [((-8, -40, 0), (8, 40, 32))], [((-20, -20, 0), (20, 20, 40))]]


def chunk_of(x, y):
    clamp = lambda v: min(NX - 1, max(0, int((v - LOW) // GRAIN)))
    return clamp(x), clamp(y)


def placed_box(origin, yaw, lo, hi):
    """The engine's drawn box of a yawed placement (aw_scenery.c, chim_chunks.c)."""
    import math
    s, c = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    xs, ys = [], []
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            xs.append(origin[0] + cx * c - cy * s)
            ys.append(origin[1] + cx * s + cy * c)
    return (min(xs) - 1, min(ys) - 1), (max(xs) + 1, max(ys) + 1)


def set_world_version(root, major, minor):
    """Every CHIM file's header version (bytes 8..11, big-endian major and minor)."""
    for path in sorted((Path(root) / 'chim').rglob('*')):
        if path.is_file():
            data = bytearray(path.read_bytes())
            assert data[:4] == b'CHIM'
            struct.pack_into('>HH', data, 8, major, minor)
            path.write_bytes(bytes(data))


def write_test_world(root, first=0, story=(), rows=False):
    """first: the world's placement ids before this frame (an earlier frame); story: placement ids flagged
    story hidden (format 0.5)."""
    from chim_fixture import box_bsp, miptex, pack_order, placement, terrain_bsp, write_world
    models = [box_bsp(MODEL_BOXES[0], texture_ids=[0]), box_bsp(MODEL_BOXES[1], texture_ids=[1]),
              box_bsp(MODEL_BOXES[2], texture_ids=[2], lighting=40000)]
    textures = [miptex('surface%d' % i, seed=i) for i in range(4)]
    order = pack_order(NX, NX, SECTOR)
    index = {c: i for i, c in enumerate(order)}
    owned = {c: [] for c in order}
    reach = {c: [] for c in order}
    for pid, model, origin, yaw in PLACEMENTS:
        lo, hi = placed_box(origin, yaw, *MODEL_BOXES[model][0])
        owner = chunk_of(*origin[:2])
        a, b = chunk_of(*lo), chunk_of(*hi)
        touched = {(x, y) for x in range(a[0], b[0] + 1) for y in range(a[1], b[1] + 1)} - {owner}
        rec = placement(pid + first, 1000 + pid, model, origin, yaw, index[owner],
                        (lo + (origin[2] + MODEL_BOXES[model][0][0][2] - 1,),
                         hi + (origin[2] + MODEL_BOXES[model][0][1][2] + 1,)), story_hidden=pid in story)
        owned[owner].append(rec)
        for c in sorted(touched):
            reach[c].append(rec)
    chunks = {}
    for cx, cy in order:
        x0, y0 = LOW + cx * GRAIN, LOW + cy * GRAIN
        # Flat ground at 0; the south-west corner chunk is a pond (ground -40, water 0).
        terrain = terrain_bsp((x0, y0, x0 + GRAIN, y0 + GRAIN), -40.0 if (cx, cy) == (0, 0) else 0.0, 0.0)
        chunks[(cx, cy)] = (owned[(cx, cy)], reach[(cx, cy)], terrain)

    # Each chunk sees the chunks next to it (and itself), as the builder's rows always do.
    def sees(a, b):
        return max(abs(order[a][0] - order[b][0]), abs(order[a][1] - order[b][1])) <= 1
    # Placement lists: a view from the chunk at (64, 64) does not see placement 3.
    view = index[chunk_of(64.0, 64.0)]

    def sees_placement(a, pid):
        return not (a == view and pid == 3 + first)
    write_world(root, (0, 0), (LOW, LOW), GRAIN, NX, NX, chunks, models, textures, len(PLACEMENTS),
                dict(draw_distance=200.0, hysteresis=32.0, prefetch_margin=64.0, collision_margin=48.0), sees, SECTOR,
                {0: (0,), 1: (1,), 2: (2,)}, sees_placement=sees_placement,
                lead=((5, 5), first) if first else None, rows=rows)
    if rows:
        set_world_version(root, 0, 6)
    return sum(len(r) for r in reach.values())


@unittest.skipIf(os.name == 'nt', 'native helper fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'install a host C compiler')
def write_big_world(root):
    """24 x 24 chunks of 128 units (Balmora's 576), 400 placements of 40 models."""
    from chim_fixture import box_bsp, miptex, pack_order, placement, terrain_bsp, write_world
    nx, grain, low = 24, 128, -1536.0
    models = [box_bsp([((-12, -12, 0), (12, 12, 24 + m))], texture_ids=[m % 3]) for m in range(40)]
    textures = [miptex('surface%d' % i, seed=i) for i in range(4)]
    order = pack_order(nx, nx, 3)
    index = {c: i for i, c in enumerate(order)}
    chunks = {c: ([], [], None) for c in order}
    owned = {c: [] for c in order}
    for pid in range(400):
        x = low + 40 + (pid % 20) * 150.0
        y = low + 40 + (pid // 20) * 150.0
        c = (int((x - low) // grain), int((y - low) // grain))
        owned[c].append(placement(pid, pid, pid % 40, (x, y, 0.0), 0.0, index[c],
                                  ((x - 13, y - 13, -1), (x + 13, y + 13, 25 + pid % 40))))
    for cx, cy in order:
        x0, y0 = low + cx * grain, low + cy * grain
        chunks[(cx, cy)] = (owned[(cx, cy)], [], terrain_bsp((x0, y0, x0 + grain, y0 + grain), 0.0))
    # The builder's ring settings (draw 540 + hysteresis 96, prefetch 256).
    write_world(root, (0, 0), (low, low), grain, nx, nx, chunks, models, textures, 400, None, None, 3,
                {m: (m % 3,) for m in range(40)})


def write_seam_world(root):
    """A 4 x 4 chunk frame written by the CHIM builder (tests/test_chim_format.py's fixture) on
    ground that steps up in every other chunk column and row, so near most chunk borders the
    highest ground under the standing box is the neighbour's. Writes seam.txt (x y stand) for
    points near every inner border and visits.txt (x y z) for points over the whole frame.
    Returns how many seam samples stand on the neighbour's ground."""
    import random
    import numpy as np
    from test_chim_format import fixture
    from chim.validate import ground_max
    from player_hull import MINS, MAXS

    # Vertex heights every 128 units (two tiles per chunk): at each inner border the ground
    # falls gently towards it and rises steeply after it, in x and in y.
    steps = (0.0, 5.0, 0.0, 90.0, 80.0, 170.0, 160.0, 250.0, 240.0)
    vertex = [-512.0 + 128.0 * i for i in range(len(steps))]

    def ground(x, y):
        return float(np.interp(x, vertex, steps) + 0.5 * np.interp(y, vertex, steps))

    _, source = fixture(Path(root), heights_of=ground)
    rows, neighbour = [], 0
    for border in (-256, 0, 256):
        for along in (-470.3, -301.7, -130.9, 41.3, 207.7, 388.1):
            for d in (-7.0, -3.5, -1.0, 1.0, 3.5, 7.0):
                for x, y in ((border + d, along), (along, border + d)):
                    lo, hi = (x + MINS[0], y + MINS[1]), (x + MAXS[0], y + MAXS[1])
                    top = ground_max(source, lo[0], lo[1], hi[0], hi[1])
                    # the highest ground inside the point's own chunk alone
                    cx0, cy0 = (x + 512) // 256 * 256 - 512, (y + 512) // 256 * 256 - 512
                    own = ground_max(source, max(lo[0], cx0), max(lo[1], cy0),
                                     min(hi[0], cx0 + 256), min(hi[1], cy0 + 256))
                    neighbour += top > own + 1.0
                    rows.append('%.3f %.3f %.4f' % (x, y, top - MINS[2]))
    (Path(root) / 'seam.txt').write_text('\n'.join(rows) + '\n')
    rng = random.Random(33)
    pts = []
    for _ in range(4000):
        x, y = rng.uniform(-500, 500), rng.uniform(-500, 500)
        pts.append('%.3f %.3f %.3f' % (x, y, ground(x, y) + rng.uniform(-30, 40)))
    (Path(root) / 'visits.txt').write_text('\n'.join(pts) + '\n')
    return neighbour


class ChimWorldTests(unittest.TestCase):
    """The CHIM world through aw_scenery.c's hooks, world.c and r_efrag.c."""

    SOURCES = [SRC / 'chim' / n for n in ('chim_format.c', 'chim_zone.c', 'chim_models.c', 'chim_chunks.c', 'chim_graft.c',
                                          'chim_world.c', 'chim_statics.c', 'chim_far.c')] + \
        [SRC / n for n in ('aw_scenery.c', 'world.c', 'r_efrag.c', 'mathlib.c', 'aw_format.c', 'aw_harvest.c',
                           'aw_harvest_runtime.c', 'aw_harvest_proxy.c', 'aw_state.c')]

    def run_world(self, modes, with_data=True, env=None, big=False, seam=False, first=0, story=(), rows=False,
                  far=False):
        with tempfile.TemporaryDirectory(prefix='amiwind-chim-world-') as tmp:
            if far:
                # The frame map's far terrain (tools/chim/far.py), frame 0 0 (centre 0 0): 9 x 7 samples.
                import numpy as np
                from chim.far import encode
                grid = np.fromfunction(lambda j, i: i * 4 + j * 5, (7, 9)).astype(np.int16)
                (Path(tmp) / 'maps').mkdir()
                (Path(tmp) / 'maps/chimtest.far').write_bytes(encode((0, 0), -4096, -3072, 1024, grid, 4))
            if seam:
                self.assertGreater(write_seam_world(tmp), 20)
            elif big:
                write_big_world(tmp)
            elif with_data:
                self.assertGreater(write_test_world(tmp, first, story, rows), 0)
                if rows:
                    self.assertTrue(list(Path(tmp).glob('chim/frames/*/*/r*/s*.ccs')))
            old = dict(os.environ)
            os.environ.update(env or {})
            try:
                return compile_and_run(self, 'aga_chim_world_test.c', self.SOURCES, [(m,) for m in modes], cwd=tmp)
            finally:
                os.environ.clear()
                os.environ.update(old)

    def test_legacy_data_sets_no_hook_and_loads_nothing(self):
        out = self.run_world(['legacy'], with_data=False)
        self.assertIn('legacy ok', out[0])

    def test_map_without_a_frame_stays_legacy(self):
        out = self.run_world(['inactive'])
        self.assertIn('inactive ok', out[0])

    def test_ring_sharing_placements_collision_streaming_and_map_change(self):
        out = self.run_world(['ring'])[0]
        self.assertIn('reach copies ok', out)
        self.assertIn('ring ok', out)
        # Three distinct models were placed six times: each read once.
        walk = [l for l in out.splitlines() if l.startswith('walk:')][0]
        self.assertIn('model loads 1,', walk)

    def test_small_zone_evicts_reloads_and_the_frame_world_catches_up(self):
        out = self.run_world(['evict'], env={'CHIM_ZONE_KIB': '150', 'CHIM_VERBOSE': '1'})[0]
        self.assertIn('evict ok', out)
        # A rebuild without room is said once per run of failures, then retried.
        self.assertLessEqual(out.count('no room for the frame world'), 3, out)

    def test_full_zone_never_leaves_the_player_without_ground(self):
        # CHIM-CHUNK-LOAD-FAIL-33: a model with no room keeps neither its chunk's ground nor its other
        # placements out (partial activation), loads do not chase each other, and the model follows
        # when there is room. The first method (chim_release 0, chim_partial 0) leaves the hole.
        out = self.run_world(['fullzone'])[0]
        self.assertIn('fullzone ok', out)
        self.assertIn('fullzone default: 0 of', out)
        first = self.run_world(['fullzone'], env={'CHIM_FIRST_METHOD': '1'})[0]
        self.assertIn('fullzone ok', first)
        line = [l for l in first.splitlines() if l.startswith('fullzone first method:')][0]
        holes, steps = map(int, line.split(': ')[1].split(' steps')[0].split(' of '))
        self.assertEqual(holes, steps)

    def test_balmora_sized_frame_primes_in_linear_work(self):
        out = self.run_world(['bigframe'], big=True)[0]
        self.assertIn('bigframe ok', out)

    def test_spawn_grafts_the_ring_before_any_trace(self):
        out = self.run_world(['spawn'])[0]
        self.assertIn('spawn ok', out)

    def test_chunk_borders_stand_on_the_neighbours_ground(self):
        # Format 0.4 (seamless standing hull) through the engine's frame world, on a world the
        # CHIM builder wrote. Before 0.4 the neighbour's ground under the box was not felt.
        out = self.run_world(['seam'], seam=True)[0]
        self.assertIn('seam ok', out)
        print([l for l in out.splitlines() if l.startswith('seam:')][-1])

    def test_a_jump_across_a_full_zone_lands(self):
        out = self.run_world(['jump'], env={'CHIM_ZONE_KIB': '150'})[0]
        self.assertIn('jump ok', out)
        print([l for l in out.splitlines() if l.startswith('jump pool')])

    def test_standing_still_in_a_small_zone_reads_nothing(self):
        out = self.run_world(['still'], env={'CHIM_ZONE_KIB': '150'})[0]
        self.assertIn('still ok', out)
        print([l for l in out.splitlines() if l.startswith('still room')])

    def test_frame_world_slots_reserved_at_map_start_and_ring_overrides(self):
        out = self.run_world(['slots'])[0]
        self.assertIn('slots ok', out)

    def test_cache_bank_keeps_models_across_a_map_change(self):
        out = self.run_world(['cache'])[0]
        self.assertIn('cache ok', out)

    # CHIM-REBUILD-COST-33 ("don't block the traffic"): the incremental frame world.
    def test_incremental_frame_world_equals_the_full_rebuild(self):
        # Frame by frame on a walk with a jump: the same leaves, contents, vis rows, ground,
        # placement and static efrags and edict leaves as the full rebuild (chim_graft_mode 0),
        # with only the chunks that join copied (one layout when the ring arrives).
        out = self.run_world(['graftmodes'])[0]
        self.assertIn('graftmodes ok', out)
        print([l for l in out.splitlines() if l.startswith('graftmodes ')])

    def test_incremental_frame_world_equals_the_full_rebuild_in_a_balmora_sized_frame(self):
        out = self.run_world(['graftmodes'], big=True, env={'CHIM_BIG': '1'})[0]
        self.assertIn('graftmodes ok', out)
        print([l for l in out.splitlines() if l.startswith('graftmodes ')])

    def test_chunks_join_within_the_frame_budget_and_the_ground_stays(self):
        out = self.run_world(['budget'])[0]
        self.assertIn('budget ok', out)

    def test_a_ring_outgrowing_its_block_in_a_full_zone_keeps_the_nearest_ground(self):
        # CHIM-GRAFT-REPACK-EMPTY-33: v0.0.33 final3 dropped every chunk ("repacked (marks full): 0 chunks")
        # and the player fell under Seyda Neen. The default keeps the nearest chunks that fit the block;
        # the first method (chim_graft_trim 0) still empties the world.
        out = self.run_world(['trim'], big=True, env={'CHIM_BIG': '1'})[0]
        self.assertIn('trim ok', out)
        print([l for l in out.splitlines() if l.startswith('trim ')])
        first = self.run_world(['trim'], big=True, env={'CHIM_BIG': '1', 'CHIM_FIRST_METHOD': '1'})[0]
        self.assertIn('trim ok', first)

    def test_chunks_join_within_the_frame_budget_in_a_balmora_sized_frame(self):
        # One chunk a frame while walking: chunks wait, the nearest chunk without ground stays
        # farther than the collision margin, nothing is rebuilt whole.
        out = self.run_world(['budget'], big=True, env={'CHIM_BIG': '1'})[0]
        self.assertIn('budget ok', out)
        print([l for l in out.splitlines() if l.startswith('budget:')])

    # World format 0.5 (M2 Seyda Neen): the engine reads 0.4 and 0.5, refuses others with a line.
    def test_far_terrain_loads_with_the_frame_map_and_goes_with_it(self):
        # CHIM-FAR-TERRAIN-33: maps/<frame map>.far, low Hunk, fog hook; without it nothing is drawn.
        out = self.run_world(['far'], far=True)
        self.assertIn('far: the frame map', out[0])

    def test_world_formats_read_and_refused(self):
        out = self.run_world(['formats'])[0]
        self.assertIn('formats ok', out)

    def test_format_06_sector_row_folders(self):
        # Format 0.6 (M3 stage B): sector files in one folder per sector row, named by the index's file
        # table; the whole ring scenario runs on such a world.
        out = self.run_world(['ring'], rows=True)[0]
        self.assertIn('ring ok', out)

    def test_the_engine_reads_the_format_the_builder_writes(self):
        # The writer is never ahead of the reader: same major, the engine's newest minor at least the
        # builder's (chim/__init__.py FORMAT_VERSION; they change in the same merge).
        import re
        from chim import FORMAT_VERSION
        header = (SRC / 'chim' / 'chim_format.h').read_text()
        major = int(re.search(r'#define CHIM_FORMAT_MAJOR\s+(\d+)', header).group(1))
        minor = int(re.search(r'#define CHIM_FORMAT_MINOR\s+(\d+)', header).group(1))
        oldest = int(re.search(r'#define CHIM_FORMAT_MINOR_OLDEST\s+(\d+)', header).group(1))
        self.assertEqual(major, FORMAT_VERSION[0])
        self.assertLessEqual(oldest, FORMAT_VERSION[1])
        self.assertGreaterEqual(minor, FORMAT_VERSION[1])

    def test_placement_ids_of_a_later_frame_of_a_world(self):
        # Ids run on across frames: this frame's ids start at 1,000 (an earlier frame in the index);
        # the whole ring scenario (placements once, reach copies, lists, collision) holds.
        out = self.run_world(['ring'], first=1000)[0]
        self.assertIn('ring ok', out)

    def test_streamed_statics_load_with_their_chunk(self):
        # CHIM-SEYDA-HUNK-GAP-33: tagged aw_static/aw_flora are taken by their chunk, not spawned; one sprite
        # block shared and locked while a placing chunk is active; aw_static keeps scale 1.
        out = self.run_world(['statics'])[0]
        self.assertIn('statics ok', out)

    def test_the_zone_leaves_room_for_what_the_map_loads_after_it(self):
        # CHIM-ZONE-RESERVE-EARLY-33: the frame map's stated figure, the post-load check, the
        # measured figure on the next load.
        out = self.run_world(['rest'])[0]
        self.assertIn('rest ok', out)

    def test_a_closed_frame_edge_says_the_area_is_unavailable(self):
        out = self.run_world(['edge'])[0]
        self.assertIn('edge ok', out)

    def test_story_hidden_placements_stay_out_while_the_story_hides_them(self):
        out = self.run_world(['story'], story=(0,))[0]
        self.assertIn('story ok', out)

    def test_prefetch_ahead_and_the_ring_follows_the_view_distance(self):
        out = self.run_world(['ahead'])[0]
        self.assertIn('ahead ok', out)


if __name__ == '__main__':
    unittest.main()
