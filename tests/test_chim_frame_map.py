# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM frame map (maps/<town>-chim.bsp): content, accounting, refusals, legacy untouched."""
import ast
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import frame_map as M  # noqa: E402
from chim.validate import hull_contents  # noqa: E402
from entity_tracker import bsp_refs  # noqa: E402
from test_chim_format import CENTRE, LOW, ROWS, SPAN, STEP, fixture, height  # noqa: E402
from chim.validate import ground_max, terrain_height  # noqa: E402
from player_hull import MINS  # noqa: E402
from unittest.mock import patch  # noqa: E402

ORIGIN = [CENTRE[0] * 0.25, CENTRE[1] * 0.25, 0.0]       # the fixture town's region-map origin
ORIGINS = {r['ref']: r['origin'] for r in ROWS}

WORLDSPAWN = {'classname': 'worldspawn', 'message': 'Balmora', 'aw_hull': 'tes3-humanoid-v1'}
# the fixture's ground (its tile corner heights), for actors and the arrival standing on it
GROUND = {'terrain_step': STEP, 'terrain_low': list(LOW),
          'terrain_heights': [[float(height(x, y)) for x in range(int(LOW[0]), int(LOW[0]) + SPAN[0] + 1, STEP)]
                              for y in range(int(LOW[1]), int(LOW[1]) + SPAN[1] + 1, STEP)]}
NPC = {'classname': 'aw_npc', 'origin': '10 20 %.4f' % terrain_height(GROUND, 10, 20), 'angles': '0 90 0',
       'aw_ref': '900001', 'aw_voice': 'x', 'aw_source_id': 'heddvild', 'model': 'progs/test.mdl'}
ARRIVAL = (300.0, 300.0, ground_max(GROUND, 284, 284, 316, 316) - MINS[2] + 0.25)   # dry ground in bm001


def alias():
    # an actor model: three foot vertices at z 0, eight idle poses (tests/test_actor_ground.py)
    raw = bytearray(struct.pack('<4si3f3ff3f8if', b'IDPO', 6, 1, 1, 1, 0, 0, 0, 4, 0, 0, 0, 1, 4, 4, 3, 1, 8, 0, 0, 1))
    raw += struct.pack('<i', 0) + bytes(16) + bytes(3 * 12) + struct.pack('<4i', 1, 0, 1, 2)
    for _ in range(8):
        raw += struct.pack('<i4B4B16s', 0, 0, 0, 0, 0, 2, 2, 0, 0, b'idle')
        raw += bytes((0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0))
    return bytes(raw)


def sprite(radius=20.0, side=8):
    """A one-frame Quake sprite (IDSP version 1) of side x side pixels with the given bounding radius."""
    raw = struct.pack('<4siifiiifi', b'IDSP', 1, 2, radius, side, side, 1, 0.0, 0)
    return raw + struct.pack('<i4i', 0, -side // 2, side // 2, side, side) + bytes(side * side)


def bsp(rows):
    lumps = M.empty_world((-64.0, -64.0, -64.0), (64.0, 64.0, 64.0))
    lumps[0] = M.entity_text(rows)
    return F.brush_image(lumps)[0]


def town(root, chim_refs, extra=None, drop=None, shift=0.0, harvest='AWH4'):
    """id1 with balmora-regions.txt and two region maps holding the fixture statics."""
    id1 = root / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    # default point (the arrival, 300 300) lies in bm001's core
    (id1 / 'progs').mkdir()
    (id1 / 'progs/test.mdl').write_bytes(alias())
    (id1 / 'balmora-regions.txt').write_text('AWBR1 2 96 540 %g %g %g 0 0 0 0 0\n' % ARRIVAL
                                             + 'bm000 -512 -512 0 512 -600 -600 100 600\n'
                                             + 'bm001 0 -512 512 512 -100 -600 600 600\n', encoding='ascii')
    refs = sorted(chim_refs)
    for k, name in enumerate(('bm000', 'bm001')):
        rows = [dict(WORLDSPAWN),
                {'classname': 'info_player_start', 'origin': '%d 0 40' % (k * 300), 'angle': '0'},
                dict(NPC)]
        rows += [{'classname': 'func_wall', 'model': '*%d' % (i + 1), 'aw_ref': str(r),
                  'origin': '%g %g %g' % (ORIGINS[r][0] + shift, ORIGINS[r][1], ORIGINS[r][2])}
                 for i, r in enumerate(refs) if r != drop]
        rows += (extra or {}).get(name, [])
        (id1 / 'maps' / (name + '.bsp')).write_bytes(bsp(rows))
    (id1 / 'harvest-bm001.txt').write_text(harvest + ' 1 0 1 1 ' + '0' * 63 + '1 1\n')
    return id1


def maps_digest(id1):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((id1 / 'maps').iterdir())}


class FrameMapTests(unittest.TestCase):
    def setUp(self):
        for mock in (patch('harvest_build.town_origin', return_value=list(ORIGIN)),
                     patch('town_config.load_settings', return_value={'source_cell': [0, 0]})):
            mock.start()
            self.addCleanup(mock.stop)

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        cls.receipt, cls.source = fixture(cls.world)
        cls.refs = {r['ref'] for r in ROWS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_frame_map_content_and_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), self.refs)
            before = maps_digest(id1)
            record = M.build(id1, 'balmora', self.world)
            after = maps_digest(id1)
            self.assertEqual(set(after) - set(before), {'balmora-chim.bsp'})
            self.assertEqual({k: v for k, v in after.items() if k in before}, before)   # region maps untouched
            data = (id1 / 'maps/balmora-chim.bsp').read_bytes()
        rows = M.entities(data)
        self.assertEqual([r['classname'] for r in rows], ['worldspawn', 'info_player_start', 'aw_npc'])
        self.assertEqual(rows[0][M.FRAME_KEY], '0 0')
        self.assertEqual(rows[0]['message'], 'Balmora')
        self.assertEqual(rows[1]['origin'], '300 0 40')          # the default region's (bm001) start
        self.assertEqual(rows[2], NPC)
        self.assertEqual(bsp_refs(data), {900001})               # the entity tracker's reader
        self.assertEqual(record['tracker_refs'], 1)
        classes = record['classes']
        self.assertEqual((classes['func_wall']['in_regions'], classes['func_wall']['written']), (2 * len(self.refs), 0))
        self.assertTrue(classes['func_wall']['rule'].startswith('static objects: in the CHIM chunks'))
        self.assertEqual((classes['aw_npc']['in_regions'], classes['aw_npc']['written']), (2, 1))
        self.assertEqual((classes['info_player_start']['in_regions'], classes['info_player_start']['written']), (2, 1))
        self.assertEqual(record['statics_in_chunks'], len(self.refs))
        self.assertEqual((record['refused'], record['default_region'], record['frame']), ([], 'bm001', [0, 0]))
        self.assertEqual(record['origin_check']['frame_origin'], ORIGIN[:2])
        self.assertEqual(record['origin_check']['statics_compared'], 2 * len(self.refs))
        self.assertLess(record['origin_check']['largest_offset'], 1e-3)
        self.assertEqual(record['harvest_check'], {'catalogues': 1, 'by_header': {'AWH4': 1}, 'representation': 4})
        lo, hi = record['bounds']
        self.assertEqual((lo[0], lo[1], hi[0], hi[1]), (-512.0, -512.0, 512.0, 512.0))

    def test_empty_world_is_empty_everywhere(self):
        lumps = F.read_brush_image(bsp([dict(WORLDSPAWN)]))
        model = struct.unpack_from('<9f7i', lumps[14])
        self.assertEqual(model[9:13], (0, 0, 0, 0))
        for p in ((-60, -60, 0), (60, 60, 60), (0, 0, -64)):
            self.assertEqual(hull_contents(lumps, model[10], p), -1)
        leafs = list(struct.iter_unpack('<2i6h2H4B', lumps[10]))
        self.assertEqual([lf[0] for lf in leafs], [-2, -1, -1])
        node = struct.unpack_from('<ihh6h2H', lumps[5])
        self.assertEqual(node[1:3], (-3, -2))
        self.assertEqual(len(lumps[7]), 0)                       # no faces

    def test_anything_it_cannot_carry_is_refused(self):
        door = {'classname': 'func_door', 'model': '*90', 'origin': '0 0 0'}
        changed_npc = dict(NPC, aw_voice='y')
        cases = {
            'brush entity': dict(extra={'bm001': [door]}),
            'static missing from the CHIM world': dict(extra={'bm000': [
                {'classname': 'func_wall', 'model': '*91', 'aw_ref': '777777', 'origin': '0 0 0'}]}),
            'CHIM static missing from the maps': dict(drop=sorted(self.refs)[0]),
            'same ref, different keys': dict(extra={'bm001': [changed_npc]}),
            'different worldspawn': dict(extra={}),
            'statics elsewhere (town coordinates differ)': dict(shift=0.5),
            'brush harvest catalogue': dict(harvest='AWH3'),
        }
        for label, kw in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                id1 = town(Path(tmp), self.refs, **kw)
                if label == 'different worldspawn':
                    rows = M.entities((id1 / 'maps/bm001.bsp').read_bytes())
                    rows[0]['message'] = 'Elsewhere'
                    (id1 / 'maps/bm001.bsp').write_bytes(bsp(rows))
                before = maps_digest(id1)
                with self.assertRaises(ValueError):
                    M.build(id1, 'balmora', self.world)
                self.assertEqual(maps_digest(id1), before)       # nothing written

    def test_frame_origin_must_be_the_towns(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), self.refs)
            with patch('harvest_build.town_origin', return_value=[ORIGIN[0] + 64, ORIGIN[1], 0.0]), \
                    self.assertRaisesRegex(ValueError, 'frame origin'):
                M.build(id1, 'balmora', self.world)

    def test_written_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), self.refs)
            M.build(id1, 'balmora', self.world)
            with self.assertRaisesRegex(ValueError, 'already present'):
                M.build(id1, 'balmora', self.world)

    def test_only_a_chim_image_writes_frame_maps(self):
        # Legacy builds write no -chim map: the only writer is chim_frame_maps, which the image step
        # calls (directly for a pure CHIM image, or through add_chim_volume) only with --chim-world
        # (tools/build.py passes it only for --builder chim).
        tree = ast.parse((ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        callers = [f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
                   and any(isinstance(n, ast.Name) and n.id == 'build_frame_map' for n in ast.walk(f))]
        self.assertEqual(callers, ['chim_frame_maps'])
        image = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == 'finalize_image')
        for name in ('add_chim_volume', 'chim_frame_maps'):
            calls = [n for n in ast.walk(image) if isinstance(n, ast.Call) and getattr(n.func, 'id', '') == name]
            self.assertEqual(len(calls), 1, name)
            guards = [n for n in ast.walk(image) if isinstance(n, ast.If) and calls[0] in list(ast.walk(n))]
            self.assertTrue(guards and 'chim_world' in ast.unparse(guards[-1].test), name)

    @unittest.skipUnless(shutil.which('xdftool'), 'xdftool (amitools) not installed')
    def test_image_volume_writes_the_frame_map(self):
        import build_aga
        from chim.stats import main as stats
        from chim.validate import main as validate
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'chim-world'
            shutil.copytree(self.world / 'chim', world / 'chim')
            (world / 'chim-source.json').write_text(json.dumps(self.source))
            (world / 'chim-receipt.json').write_text(json.dumps(dict(self.receipt, town='balmora')))
            with contextlib.redirect_stdout(io.StringIO()):
                validate([str(world), '--json', str(world / 'chim-validate.json')])
                stats([str(world)])
            id1 = town(Path(tmp) / 'boot', self.refs)
            out = Path(tmp) / 'out'
            out.mkdir()
            _, record = build_aga.add_chim_volume(world, id1, out, 0, shutil.which('xdftool'), mib=8)
            self.assertEqual([m['map'] for m in record['frame_maps']], ['maps/balmora-chim.bsp'])
            self.assertTrue((id1 / 'maps/balmora-chim.bsp').is_file())



class PerMapKeyTests(unittest.TestCase):
    def test_region_only_worldspawn_keys_are_left_out(self):
        # aw_render_pool names a region map's own pool of culled faces; CHIM draws models whole
        maps = {'sn000': [dict(WORLDSPAWN, aw_render_pool='*3'), {'classname': 'info_player_start', 'origin': '0 0 0'}],
                'sn001': [dict(WORLDSPAWN, aw_render_pool='*9'), {'classname': 'info_player_start', 'origin': '1 0 0'}]}
        rows, report = M.frame_entities(maps, set(), 'sn000')
        self.assertEqual(report['refused'], [])
        self.assertNotIn('aw_render_pool', rows[0])
        self.assertEqual(report['per_map_worldspawn_keys_left_out'], ['aw_render_pool'])


class StreamedStaticsTests(unittest.TestCase):
    """Static models of a frame map stream with their chunks (CHIM-SEYDA-MEMORY-33): aw_static and
    aw_flora carry the owner chunk and their drawn box, every key PF_makestatic reads unchanged; the
    worldspawn counts them and its Hunk rest leaves their models out."""
    SHARED = 'progs/aw_flora/f_shared.spr'
    LAMP = 'progs/aw_static/s_lamp.spr'
    # (classname, model, origin, aw_scale): one sprite in two chunks, a second sprite, an alias model
    PLACED = (('aw_flora', SHARED, (-400, -400, 10), '2'), ('aw_flora', SHARED, (400, 400, 12), '1'),
              ('aw_static', LAMP, (100, -300, 30), '1'), ('aw_static', 'progs/test.mdl', (-300, 300, 5), '1.5'))

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        fixture(cls.world)
        refs = {r['ref'] for r in ROWS}
        cls.source = [{'classname': c, 'model': m, 'origin': '%d %d %d' % o, 'angles': '0 %d 0' % (30 * k),
                       'frame': '0', 'skin': '0', 'aw_scale': sc, 'aw_ref': str(800 + k)}
                      for k, (c, m, o, sc) in enumerate(cls.PLACED)]
        with patch('harvest_build.town_origin', return_value=list(ORIGIN)), \
                patch('town_config.load_settings', return_value={'source_cell': [0, 0]}), \
                patch.dict('os.environ', {M.STREAM_VARIABLE: '1'}):
            cls.id1 = town(Path(cls.tmp.name) / 'town', refs,
                           extra={'bm000': [dict(e) for e in cls.source], 'bm001': [dict(e) for e in cls.source]})
            for d in ('aw_flora', 'aw_static'):
                (cls.id1 / 'progs' / d).mkdir()
            (cls.id1 / cls.SHARED).write_bytes(sprite(20.0))
            (cls.id1 / cls.LAMP).write_bytes(sprite(12.5, 16))
            cls.record = M.build(cls.id1, 'balmora', cls.world)
            cls.data = (cls.id1 / 'maps/balmora-chim.bsp').read_bytes()
        cls.rows = M.entities(cls.data)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def statics(self):
        return sorted((e for e in self.rows if e['classname'] in M.STREAMED_CLASSES), key=lambda e: e['aw_ref'])

    def test_every_makestatic_key_is_kept_and_tagged(self):
        got = self.statics()
        self.assertEqual(len(got), len(self.PLACED))
        for e, src in zip(got, self.source):
            self.assertEqual({k: v for k, v in e.items() if k not in (M.CHUNK_KEY, M.BOX_KEY)}, src)
            self.assertIn(M.CHUNK_KEY, e)
            self.assertIn(M.BOX_KEY, e)

    def test_owner_chunk_holds_the_origin(self):
        chunks, low, grain, nx, ny = M.frame_grid(self.world, (0, 0))
        cell_of = {c['index']: (c['cx'], c['cy']) for c in chunks}
        owners = []
        for e in self.statics():
            x, y, _ = map(float, e['origin'].split())
            cx, cy = cell_of[int(e[M.CHUNK_KEY])]
            self.assertTrue(low[0] + cx * grain <= x < low[0] + (cx + 1) * grain, e)
            self.assertTrue(low[1] + cy * grain <= y < low[1] + (cy + 1) * grain, e)
            owners.append(int(e[M.CHUNK_KEY]))
        self.assertEqual(len(set(owners[:2])), 2)              # the shared sprite in two chunks

    def test_drawn_box_is_origin_plus_scaled_radius(self):
        flora, _, lamp, alias_static = self.statics()
        self.assertEqual(flora[M.BOX_KEY], '-440 -440 -30 -360 -360 50')        # radius 20 x aw_scale 2
        self.assertEqual(lamp[M.BOX_KEY], '87 -313 17 113 -287 43')             # radius 12.5, rounded outwards
        # aw_static: aw_scale is ignored (PF_makestatic sends scale 1): alias header radius 4
        self.assertEqual(alias_static[M.BOX_KEY], '-304 296 1 -296 304 9')

    def test_aw_flora_must_be_a_sprite_with_a_positive_scale(self):
        rows = [{'classname': 'aw_flora', 'model': 'progs/test.mdl', 'origin': '0 0 0', 'aw_scale': '1', 'aw_ref': '9'}]
        chunks, low, grain, nx, ny = M.frame_grid(self.world, (0, 0))
        with self.assertRaisesRegex(ValueError, 'not a sprite'):
            M.stream_statics(self.id1, rows, chunks, low, grain, nx, ny)
        rows = [{'classname': 'aw_flora', 'model': self.SHARED, 'origin': '0 0 0', 'aw_scale': '0', 'aw_ref': '9'}]
        with self.assertRaisesRegex(ValueError, 'positive aw_scale'):
            M.stream_statics(self.id1, rows, chunks, low, grain, nx, ny)

    def test_worldspawn_count_and_hunk_rest(self):
        from engine_limits import MEASURED_HUNK
        client = MEASURED_HUNK['client_per_map_bytes']
        self.assertEqual(self.rows[0][M.COUNT_KEY], str(len(self.PLACED)))
        # every sprite streams: the client's own per-map Hunk and the margin are left (alias models: Cache)
        rest = client + M.HUNK_REST_MARGIN
        self.assertEqual(self.rows[0][M.HUNK_KEY], str(rest))
        sizes = sum((self.id1 / m).stat().st_size for m in (self.SHARED, self.LAMP)) + len(alias())
        self.assertEqual(self.record['streamed_statics'], {'count': 4, 'model_bytes': sizes, 'hunk_rest': rest})

    def test_margin_covers_the_measured_loads_after_the_zone(self):
        # CHIM-ZONE-RESERVE-EARLY-33: what the engine measured after the zone, beyond the client and sprites
        from engine_limits import MEASURED_HUNK, chim_memory, whole_map_zone
        client = MEASURED_HUNK['client_per_map_bytes']
        self.assertGreaterEqual(client + M.HUNK_REST_MARGIN, 1609600 + 4096)   # Balmora measured after the zone
        # ... without costing Balmora its full zone (one 16 KiB step less and its ring no longer fits)
        memory = chim_memory(heap_mb=11)
        self.assertEqual(whole_map_zone(793504, client + M.HUNK_REST_MARGIN, memory), memory['zone_kib'] * 1024)
        self.assertGreaterEqual(M.SPRITE_HUNK_OVERHEAD, (964624 - 954414) / 26)

    def test_without_streaming_nothing_is_tagged_and_the_rest_counts_every_sprite(self):
        from engine_limits import MEASURED_HUNK
        with patch('harvest_build.town_origin', return_value=list(ORIGIN)), \
                patch('town_config.load_settings', return_value={'source_cell': [0, 0]}), \
                patch.dict('os.environ', {M.STREAM_VARIABLE: '0'}):
            (self.id1 / 'maps/balmora-chim.bsp').unlink()
            record = M.build(self.id1, 'balmora', self.world)
            rows = M.entities((self.id1 / 'maps/balmora-chim.bsp').read_bytes())
        (self.id1 / 'maps/balmora-chim.bsp').write_bytes(self.data)            # the tagged map for the others
        self.assertFalse([e for e in rows if M.CHUNK_KEY in e or M.BOX_KEY in e])
        self.assertNotIn(M.COUNT_KEY, rows[0])
        sprites = sum((self.id1 / m).stat().st_size + M.SPRITE_HUNK_OVERHEAD for m in (self.SHARED, self.LAMP))
        self.assertEqual(rows[0][M.HUNK_KEY], str(MEASURED_HUNK['client_per_map_bytes'] + M.HUNK_REST_MARGIN + sprites))
        self.assertEqual(record['streamed_statics']['count'], 0)

    def test_streaming_is_off_unless_the_build_says_so(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertFalse(M.stream_enabled())
        with patch.dict('os.environ', {M.STREAM_VARIABLE: 'yes'}):
            with self.assertRaises(ValueError):
                M.stream_enabled()

    def test_hunk_rest_counts_sprites_that_do_not_stream(self):
        from engine_limits import MEASURED_HUNK
        rows = [{'classname': 'worldspawn'},
                {'classname': 'aw_flora', 'model': self.SHARED, M.CHUNK_KEY: '0'},
                {'classname': 'aw_fx', 'model': self.LAMP}, {'classname': 'aw_fx', 'model': self.LAMP},
                {'classname': 'aw_npc', 'model': 'progs/test.mdl'}]
        lamp = (self.id1 / self.LAMP).stat().st_size + M.SPRITE_HUNK_OVERHEAD
        self.assertEqual(M.hunk_rest(self.id1, rows), MEASURED_HUNK['client_per_map_bytes'] + M.HUNK_REST_MARGIN + lamp)

    def test_written_the_same_twice(self):
        # the frame map the engine's streamed-statics fixture is cut from: deterministic
        with patch('harvest_build.town_origin', return_value=list(ORIGIN)), \
                patch('town_config.load_settings', return_value={'source_cell': [0, 0]}), \
                patch.dict('os.environ', {M.STREAM_VARIABLE: '1'}):
            (self.id1 / 'maps/balmora-chim.bsp').unlink()
            M.build(self.id1, 'balmora', self.world)
        self.assertEqual((self.id1 / 'maps/balmora-chim.bsp').read_bytes(), self.data)


class DocksFrameMapTests(unittest.TestCase):
    """The intro docks as Seyda Neen's second frame map (format 0.5): statics one way, the docks'
    own entities copied, the route boundary as four clip walls."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        fixture(cls.world)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def docks(self, refs):
        root = Path(tempfile.mkdtemp(dir=self.tmp.name))
        (root / 'maps').mkdir()
        (root / 'progs/aw_flora').mkdir(parents=True)
        (root / 'progs/aw_flora/f_0123456789abcdef.spr').write_bytes(sprite())
        rows = [dict(WORLDSPAWN), {'classname': 'info_player_start', 'origin': '0 0 40', 'angle': '90'}, dict(NPC),
                {'classname': 'aw_flora', 'model': 'progs/aw_flora/f_0123456789abcdef.spr', 'origin': '5 5 5',
                 'aw_ref': '700', 'aw_scale': '1', 'angles': '0 0 0'}]
        rows += [{'classname': 'func_wall', 'model': '*%d' % (i + 1), 'aw_ref': str(r),
                  'origin': '%g %g %g' % tuple(ORIGINS[r]) if r in ORIGINS else '0 0 0'} for i, r in enumerate(refs)]
        (root / 'maps' / 'intro_docks.bsp').write_bytes(bsp(rows))
        return root

    def build(self, id1, walk=([], {'checked': 'mocked'})):
        # the fixture world is far smaller than the docks' bounds: the walkable-area gate has its own tests
        with patch('chim.seyda.source_cell', return_value=(0, 0)), \
                patch('harvest_build.town_origin', return_value=ORIGIN), \
                patch('chim.frame_map.walk_check', return_value=walk) as walk_check:
            record = M.build_docks(id1, self.world)
            self.assertEqual(walk_check.call_count, 1)
            return record

    def test_a_walkable_area_refusal_stops_the_docks_map(self):
        id1 = self.docks([11])
        with self.assertRaisesRegex(ValueError, 'a hole'):
            self.build(id1, walk=(['intro_docks: 3 places next to a hole in the CHIM collision'], {}))
        self.assertFalse((id1 / 'maps' / 'intro_docks-chim.bsp').exists())

    def test_docks_map_keeps_a_subset_of_the_frame_and_its_own_entities(self):
        id1 = self.docks([11, 12])                       # two of the frame's six statics
        record = self.build(id1)
        data = (id1 / 'maps' / 'intro_docks-chim.bsp').read_bytes()
        rows = M.entities(data)
        classes = [e['classname'] for e in rows]
        self.assertEqual(rows[0][M.FRAME_KEY], '0 0')
        self.assertEqual(classes.count('info_player_start'), 1)
        self.assertEqual(classes.count('aw_npc'), 1)
        self.assertEqual(classes.count('aw_flora'), 1)
        walls = [e for e in rows if e.get('aw_clip')]
        self.assertEqual(len(walls), 4)
        self.assertNotIn('aw_ref', ''.join(e.get('aw_ref', '') for e in rows if e['classname'] == 'func_wall'))
        self.assertEqual(record['clip_walls'], 4)
        self.assertEqual(record['statics_in_chunks'], 2)

    def test_clip_walls_bound_the_route(self):
        from prepare_intro_docks import BOUNDS
        id1 = self.docks([11])
        self.build(id1)
        lumps = F.read_brush_image((id1 / 'maps' / 'intro_docks-chim.bsp').read_bytes())
        models = list(struct.iter_unpack('<9f7i', lumps[14]))
        x0, y0, x1, y1 = BOUNDS
        inside = ((x0 + x1) / 2, (y0 + y1) / 2, 0.0)
        for k, (outside, mid) in enumerate((((x0 - 40, inside[1], 0.0), None), ((x1 + 40, inside[1], 0.0), None),
                                             ((inside[0], y0 - 40, 0.0), None), ((inside[0], y1 + 40, 0.0), None))):
            root = models[k + 1][10]
            self.assertEqual(hull_contents(lumps, root, outside), -2, k)        # standing hull: solid wall
            self.assertEqual(hull_contents(lumps, root, inside), -1, k)         # the route is open
        self.assertEqual(sum(models[k][15] for k in range(len(models))), 0)    # no faces anywhere

    def test_a_docks_static_missing_from_the_frame_is_refused(self):
        id1 = self.docks([11, 99])
        with self.assertRaisesRegex(ValueError, 'not in the CHIM world'):
            self.build(id1)


class BoxScene:
    """A collision scene of axis-aligned solid boxes (x0, y0, z0, x1, y1, z1) with the trace contract
    of audit_walkability.Scene / chim.collision.FrameScene: None, or the first hit's fraction and normal."""

    def __init__(self, boxes):
        self.boxes = boxes

    def trace(self, start, end):
        best = None
        for box in self.boxes:
            t0, t1, normal = 0.0, 1.0, None
            for k in range(3):
                d = end[k] - start[k]
                lo, hi = box[k], box[k + 3]
                if abs(d) < 1e-9:
                    if not lo < start[k] < hi:
                        break
                    continue
                a, b = (lo - start[k]) / d, (hi - start[k]) / d
                n = [0.0, 0.0, 0.0]
                n[k] = -1.0 if d > 0 else 1.0
                if a > b:
                    a, b = b, a
                if a > t0:
                    t0, normal = a, tuple(n)
                t1 = min(t1, b)
                if t0 >= t1:
                    break
            else:
                if best is None or t0 < best['fraction']:
                    best = {'fraction': t0, 'normal': normal or (0.0, 0.0, 0.0), 'reference': box}
        return best


class WalkableAreaTests(unittest.TestCase):
    """The special maps' walkable-area gate (walkable_area, nearest_reach) on a box scene."""
    BOUNDS = (0.0, 0.0, 256.0, 256.0)
    GROUND = (-16, -16, -64, 272, 272, 0)
    WALLS = [(-16, -16, 0, 0, 272, 200), (256, -16, 0, 272, 272, 200),       # the four clip walls
             (-16, -16, 0, 272, 0, 200), (-16, 256, 0, 272, 272, 200)]
    DIVIDER = (60, 0, 0, 84, 200, 120)          # a wall with a way round it at y > 200
    DECK = (160, 0, 0, 256, 64, 8)              # one step up (STEP_HEIGHT 8.5)
    LEDGE = (0, 224, 0, 40, 256, 40)            # too high to step onto
    START = (24.0, 24.0, 0.0)

    def area(self, boxes):
        return M.walkable_area(BoxScene(boxes), self.BOUNDS, self.START)

    def test_floor_round_a_wall_and_up_a_step_is_reached(self):
        got = self.area([self.GROUND, *self.WALLS, self.DIVIDER, self.DECK, self.LEDGE])
        reach = got['reachable']
        self.assertEqual(got['holes'], [])
        self.assertEqual(reach[(1, 1)], 0.0)
        self.assertIn((7, 2), reach)                                   # behind the divider: walked round it
        self.assertEqual(reach[(12, 2)], 8.0)                          # the deck, one step up
        self.assertNotIn((1, 15), reach)                               # the ledge: too high
        self.assertNotIn((4, 5), reach)                                # inside the divider

    def test_a_wall_without_a_way_round_closes_the_far_side(self):
        closed = (60, -16, 0, 84, 272, 120)             # edges off the 16-unit sample grid
        reach = self.area([self.GROUND, *self.WALLS, closed])['reachable']
        self.assertFalse([k for k in reach if k[0] * 16 > 84])

    def test_a_hole_in_the_floor_is_reported(self):
        floor = [(-16, -16, -64, 120, 272, 0), (136, -16, -64, 272, 272, 0), (120, -16, -64, 136, 120, 0),
                 (120, 136, -64, 136, 272, 0)]                         # missing: x 120..136, y 120..136
        got = self.area([*floor, *self.WALLS])
        self.assertEqual(got['holes'], [(8, 8)])

    def test_a_start_off_the_floor_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'no walkable floor'):
            M.walkable_area(BoxScene(self.WALLS), self.BOUNDS, self.START)

    def test_nearest_reach(self):
        reach = {(0, 0): 0.0, (3, 4): 0.0}
        self.assertEqual(M.nearest_reach(reach, (0.0, 0.0, 0, 0), (48.0, 64.0)), 0.0)
        self.assertAlmostEqual(M.nearest_reach(reach, (10.0, 10.0, 0, 0), (10.0, 13.0)), 3.0)
        self.assertEqual(M.nearest_reach({}, (0.0, 0.0, 0, 0), (0.0, 0.0)), float('inf'))


class StaticLimitTests(unittest.TestCase):
    def test_limit_is_read_from_the_engine(self):
        from engine_limits import limits
        self.assertEqual(M.static_entity_limit(), limits()['max_static_entities'])

    def test_frame_map_statics_must_fit(self):
        rows = [{'classname': 'worldspawn'}] + [{'classname': 'aw_flora', 'origin': '%d 0 0' % k} for k in range(3)] \
            + [{'classname': 'aw_static', 'origin': '0 %d 0' % k} for k in range(2)] + [dict(NPC)]
        self.assertEqual(M.static_check(rows, limit=5)[0], [])
        refused, record = M.static_check(rows, limit=4)
        self.assertTrue(refused and 'MAX_STATIC_ENTITIES' in refused[0])
        self.assertEqual((record['static_entities'], record['headroom']), (5, -1))

    def test_sncourt_is_a_special_map_too(self):
        from prepare_seyda_regions import COURTYARD
        self.assertEqual(M.special_bounds('sncourt'), tuple(COURTYARD))
        self.assertIn('sncourt', M.SPECIALS)
        with self.assertRaises(ValueError):
            M.special_bounds('sn001')


class TerrainBrushTests(unittest.TestCase):
    def test_converted_terrain_brush_entities_are_the_chunks_ground(self):
        # the recorded Seyda Neen regions carry their ground as a func_wall with a reference >= TERRAIN_REF
        terrain = {'classname': 'func_wall', 'model': '*7', 'aw_ref': str(M.TERRAIN_REF),
                   'message': 'Canonical terrain visual and collision'}
        maps = {'sn000': [dict(WORLDSPAWN), {'classname': 'info_player_start', 'origin': '0 0 0'}, terrain]}
        rows, report = M.frame_entities(maps, set(), 'sn000')
        self.assertEqual(report['refused'], [])
        self.assertEqual(report['terrain_brush_entities'], 1)
        self.assertNotIn('func_wall', [e['classname'] for e in rows])


class SeydaImageTests(unittest.TestCase):
    def test_a_seyda_world_writes_its_special_frame_maps_too(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'w'
            (world / 'chim').mkdir(parents=True)
            for name in ('chim/world.cwi', 'chim-validate.json', 'chim-stats.json'):
                (world / name).write_text('{"ok": true, "source_checked": true}')
            (world / 'chim-receipt.json').write_text(json.dumps({'builder': 'chim', 'areas': ['balmora', 'seyda']}))
            calls = []
            with patch('chim.frame_map.build', side_effect=lambda id1, area, w: calls.append(area) or {'map': area}),                     patch('chim.frame_map.build_docks', side_effect=lambda id1, w, name: calls.append(name) or {'map': name}),                     patch('chim.disk.pack_partition', side_effect=RuntimeError('stop after the frame maps')):
                with self.assertRaisesRegex(RuntimeError, 'stop after'):
                    build_aga.add_chim_volume(world, Path(tmp) / 'id1', Path(tmp), 0, 'xdftool')
            self.assertEqual(calls, ['balmora', 'seyda', 'intro_docks', 'sncourt'])


class ParityOnFrameTests(unittest.TestCase):
    """M3 parity gates on the frame's own collision: actors stand, the arrival is a standing spot, a
    frame that joins no open world is closed with clip walls."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        fixture(cls.world)
        cls.refs = {r['ref'] for r in ROWS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        for mock in (patch('harvest_build.town_origin', return_value=list(ORIGIN)),
                     patch('town_config.load_settings', return_value={'source_cell': [0, 0]})):
            mock.start()
            self.addCleanup(mock.stop)

    def test_actors_and_arrival_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = M.build(town(Path(tmp), self.refs), 'balmora', self.world)
        self.assertEqual((record['actor_contact']['actors'], record['actor_contact']['grounded']), (1, 1))
        self.assertTrue(record['arrival_check']['standing'])
        self.assertFalse(record['closed_edge'])                  # Balmora joins the open world

    def test_a_floating_actor_is_refused(self):
        # farther off than the refit reaches (CHIM-SEYDA-ACTOR-CONTACT-33: REFIT_DZ)
        floating = dict(NPC, origin='10 20 %.4f' % (terrain_height(GROUND, 10, 20) + M.REFIT_DZ + 6))
        with tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), self.refs)
            for name in ('bm000', 'bm001'):
                rows = [floating if r.get('classname') == 'aw_npc' else r
                        for r in M.entities((id1 / 'maps' / (name + '.bsp')).read_bytes())]
                (id1 / 'maps' / (name + '.bsp')).write_bytes(bsp(rows))
            with self.assertRaisesRegex(ValueError, 'does not stand on the CHIM frame'):
                M.build(id1, 'balmora', self.world)

    def test_a_slightly_off_actor_is_refit_on_the_frame(self):
        """CHIM-SEYDA-ACTOR-CONTACT-33: a height baked on the legacy terrain triangulation a few units off
        the frame's terrain is refit (height only, within REFIT_LIMIT) and written into the frame map."""
        ground = terrain_height(GROUND, 10, 20)
        for dz in (2.5, -1.5):
            off = dict(NPC, origin='10 20 %.4f' % (ground + dz), aw_ground_baked='10 20 %.4f' % (ground + dz))
            with self.subTest(dz=dz), tempfile.TemporaryDirectory() as tmp:
                id1 = town(Path(tmp), self.refs)
                for name in ('bm000', 'bm001'):
                    rows = [off if r.get('classname') == 'aw_npc' else r
                            for r in M.entities((id1 / 'maps' / (name + '.bsp')).read_bytes())]
                    (id1 / 'maps' / (name + '.bsp')).write_bytes(bsp(rows))
                record = M.build(id1, 'balmora', self.world)
                contact = record['actor_contact']
                self.assertEqual((contact['grounded'], contact['refitted']), (1, 1))
                row = next(r for r in contact['rows'] if r['status'] == 'refitted')
                self.assertLessEqual(abs(row['refit_dz']), M.REFIT_LIMIT)
                npc = next(e for e in M.entities((id1 / 'maps/balmora-chim.bsp').read_bytes())
                           if e.get('classname') == 'aw_npc')
                x, y, z = map(float, npc['origin'].split())
                self.assertEqual((x, y), (10.0, 20.0))
                self.assertAlmostEqual(z, ground + dz + row['refit_dz'], places=4)
                self.assertEqual(npc['aw_ground_baked'], npc['origin'])
                # the legacy region maps keep their baked height
                legacy = next(e for e in M.entities((id1 / 'maps/bm000.bsp').read_bytes())
                              if e.get('classname') == 'aw_npc')
                self.assertEqual(legacy['origin'], off['origin'])

    def test_an_arrival_inside_a_placement_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = town(Path(tmp), self.refs)
            table = (id1 / 'balmora-regions.txt').read_text(encoding='ascii').splitlines()
            head = table[0].split()
            head[4:7] = ['130', '70', '%g' % (terrain_height(GROUND, 130, 70) + 30)]   # inside the large box (ref 12)
            (id1 / 'balmora-regions.txt').write_text('\n'.join([' '.join(head)] + table[1:]) + '\n',
                                                     encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'not a standing spot'):
                M.build(id1, 'balmora', self.world)

    def test_a_frame_without_an_open_world_is_closed(self):
        from chim.validate import hull_contents
        with tempfile.TemporaryDirectory() as tmp, patch.object(M, 'closed_edge', return_value=True):
            id1 = town(Path(tmp), self.refs)
            record = M.build(id1, 'balmora', self.world)
            data = (id1 / 'maps/balmora-chim.bsp').read_bytes()
        self.assertTrue(record['closed_edge'])
        rows = M.entities(data)
        self.assertEqual(rows[0][M.EDGE_KEY], 'closed')
        walls = [r for r in rows if r.get('aw_clip')]
        self.assertEqual(len(walls), 4)
        lumps = F.read_brush_image(data)
        models = list(struct.iter_unpack('<9f7i', lumps[14]))
        lo, hi = record['bounds']
        roots = [models[int(w['model'][1:])][10] for w in walls]
        outside = [(lo[0] - 30, 0, 0), (hi[0] + 30, 0, 0), (0, lo[1] - 30, 0), (0, hi[1] + 30, 0)]
        self.assertTrue(all(any(hull_contents(lumps, r, p) == -2 for r in roots) for p in outside))
        self.assertTrue(all(hull_contents(lumps, r, (0, 0, 0)) == -1 for r in roots))

    def test_closed_edge_follows_the_town_table(self):
        self.assertTrue(M.closed_edge('vivec_arena'))            # world_slot -1: no open world around it
        self.assertFalse(M.closed_edge('balmora'))


if __name__ == '__main__':
    unittest.main()


class ActivatedObjectTests(unittest.TestCase):
    """CHIM-COURT-BARREL-USE-33: an object the engine activates by its aw_ref (the courtyard barrel with
    Fargoth's ring) keeps a func_wall edict in the frame map; the engine and the builder read one list."""

    REFS = {11: 'AW_REF_TEST_BARREL'}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.world = Path(cls.tmp.name) / 'world'
        fixture(cls.world)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def region(self, root, name, ref=11, box=((-8.0, -8.0, -9.0), (8.0, 8.0, 9.0)), origin=None):
        """A region map whose func_wall `ref` has a real brush model (*1) of the given box."""
        lumps, numbers = M.add_clip_models(M.empty_world((-64.0, -64.0, -64.0), (64.0, 64.0, 64.0)), [box])
        o = origin or ORIGINS[ref]
        rows = [dict(WORLDSPAWN), {'classname': 'info_player_start', 'origin': '0 0 40', 'angle': '90'}, dict(NPC),
                {'classname': 'func_wall', 'model': '*%d' % numbers[0], 'aw_ref': str(ref),
                 'origin': '%g %g %g' % tuple(o)}]
        lumps[0] = M.entity_text(rows)
        (root / 'maps').mkdir(exist_ok=True)
        (root / 'maps' / (name + '.bsp')).write_bytes(F.brush_image(lumps)[0])

    def test_engine_header_is_the_one_list(self):
        refs = M.activated_refs()
        self.assertEqual(refs[172851], 'AW_REF_COURTYARD_BARREL')       # the barrel with Fargoth's ring
        source = (ROOT / 'engine/aga/src/aw_opening.c').read_text(encoding='utf-8')
        self.assertIn('#include "aw_activated.h"', source)
        for number, name in refs.items():
            self.assertNotIn(str(number), source, 'aw_opening.c must use %s, not the number' % name)
            self.assertIn(name, source)

    def test_docks_map_keeps_the_activated_object_as_a_faceless_marker(self):
        root = Path(tempfile.mkdtemp(dir=self.tmp.name))
        self.region(root, M.DOCKS)
        with patch('chim.frame_map.activated_refs', return_value=self.REFS), \
                patch('chim.seyda.source_cell', return_value=(0, 0)), \
                patch('harvest_build.town_origin', return_value=ORIGIN), \
                patch('chim.frame_map.walk_check', return_value=([], {})):
            record = M.build_docks(root, self.world)
        data = (root / 'maps' / (M.DOCKS + '-chim.bsp')).read_bytes()
        kept = [e for e in M.entities(data) if e.get('aw_ref') == '11']
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]['classname'], 'func_wall')
        self.assertEqual(kept[0]['origin'], '%g %g %g' % tuple(ORIGINS[11]))
        self.assertEqual(record['activated']['kept'][0]['ref'], 11)
        lumps = F.read_brush_image(data)
        model = struct.unpack_from('<9f7i', lumps[14], 64 * int(kept[0]['model'][1:]))
        m = M.ACTIVATED_MARGIN
        self.assertEqual([round(v, 3) for v in model[:6]], [-8 - m, -8 - m, -9 - m, 8 + m, 8 + m, 9 + m])
        self.assertEqual(model[15], 0)                                          # nothing drawn
        self.assertEqual(hull_contents(lumps, model[10], (0.0, 0.0, 0.0)), -2)  # standing hull: solid
        self.assertIn(11, bsp_refs(data))                                       # the entity tracker sees it

    def test_without_the_fix_the_object_had_no_edict(self):
        # frame_entities alone puts every func_wall + aw_ref into the chunks (the regression's cause)
        root = Path(tempfile.mkdtemp(dir=self.tmp.name))
        self.region(root, 'r0')
        rows, _ = M.frame_entities({'r0': M.entities((root / 'maps/r0.bsp').read_bytes())}, {11}, 'r0')
        found, refused = M.activated_entities(root, ['r0'], self.REFS)
        self.assertEqual(refused, [])
        self.assertEqual(M.activated_check(rows, found), ['activated object 11 has no edict in the frame map'])
        _, record = M.keep_activated(M.empty_world((-64.0,) * 3, (64.0,) * 3), rows, found, self.REFS)
        self.assertEqual(M.activated_check(rows, found), [])
        self.assertEqual(record['kept'][0]['name'], 'AW_REF_TEST_BARREL')

    def test_regions_that_disagree_on_an_activated_object_are_refused(self):
        root = Path(tempfile.mkdtemp(dir=self.tmp.name))
        self.region(root, 'r0')
        self.region(root, 'r1', box=((-8.0, -8.0, -9.0), (8.0, 8.0, 12.0)))
        found, refused = M.activated_entities(root, ['r0', 'r1'], self.REFS)
        self.assertEqual(len(found), 1)
        self.assertRegex(refused[0], 'r1: activated object 11 .* differs between regions')
        self.region(root, 'r1')
        self.assertEqual(M.activated_entities(root, ['r0', 'r1'], self.REFS)[1], [])
