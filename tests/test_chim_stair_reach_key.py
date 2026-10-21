# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM stair walk's scope, reach key, watch list and targeted walks (BUILD-STAIR-WALK-SCOPE-KEY-46).

Scope: the CHIM gate walks only flight steps by default (before, it walked every step and ramp whatever the scope),
and a flights walk gives exactly the flight rows of an all walk. Reach key: what a walk reads changes the key (the
stair's own model, the ground under it, a placement moved into reach); collision out of every walk's reach does not
(a placement's walls and underside far from the stair), and a walk traced step by step reads nothing outside its
key's reach. Watch list: its frames are walked again even when reused; a frame off it is not. Targeted walks walk
only the named places and store nothing.
"""
import copy
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import collision  # noqa: E402
from chim import format as F  # noqa: E402
from test_chim_stair_key import replace_lump  # noqa: E402


def bumped(image, k):
    data = bytearray(F.read_brush_image(image)[k])
    data[0] ^= 0x01
    return replace_lump(image, k, bytes(data))


class World(unittest.TestCase):
    """The two-placement world of tests/test_chim_stairs.py: ref 21 a small flight at (-300, -300), ref 22 a large
    stair model at (300, 200) whose own steps are not items of the walk (its refs never appear in the rows)."""

    @classmethod
    def setUpClass(cls):
        from test_chim_stairs import world_of
        from chim.validate import Failures, load_world
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'world'
        cls.out.mkdir()
        world_of(cls.out, False)
        world = load_world(cls.out, Failures())
        cls.frames, cls.models = world[5], world[4]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.env = dict(os.environ)
        self.cache = tempfile.TemporaryDirectory()
        for name in ('AMIWIND_STAIR_WALK_REUSE', 'AMIWIND_STAIR_WALK_AREA', 'AMIWIND_STAIR_WALK_KEY',
                     'AMIWIND_STAIR_WALK_PLACES', 'AMIWIND_RUN_CHIM_VERSION', 'AMIWIND_AW_REQUEST'):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_PASS_CACHE=str(Path(self.cache.name) / 'cache'), AMIWIND_STAIR_WALK_CACHE='cached',
                          AMIWIND_STAIR_WALK_SAMPLE='0', AMIWIND_STAIR_WALK='flights', AMIWIND_STAIR_WATCH='off',
                          AMIWIND_RUN_VERSION='0.0.46-dev1', AMIWIND_RUN_NAME='2026_10_20_v0.0.46-dev1_full_abc1234')
        collision._STAIR_CACHE.clear()

    def tearDown(self):
        collision._STAIR_CACHE.clear()
        os.environ.clear()
        os.environ.update(self.env)
        self.cache.cleanup()

    def key(self, frames=None, models=None):
        # the worlds changed here live in memory only: the items workers read the files on disk, so their check of
        # the frame data key is left out (the items of the disk world; every change below that changes the items
        # also changes what the walk reads, which the key holds by itself)
        with mock.patch.object(collision, 'frame_stair_key', return_value=None):
            return collision.reach_keys(self.out, frames or self.frames, self.models if models is None else models,
                                        {}, 'flights', None)[1][0]

    def placement(self, ref):
        for at, c in enumerate(self.frames[0][2]):
            for k, r in enumerate(c['owned']):
                if collision.source_ref(r['ref']) == ref:
                    return at, k, r
        raise AssertionError(ref)

    def gate(self, frames=None):
        return collision.stair_gate(self.out, frames or self.frames, 1, models=self.models)


class Scope(World):
    def test_flights_walk_gives_the_flight_rows_of_an_all_walk(self):
        tasks = collision.stair_tasks(self.out, self.frames)
        os.environ['AMIWIND_STAIR_WALK'] = 'all'
        every = [r for t in tasks for r in collision.stair_task(t)]
        os.environ['AMIWIND_STAIR_WALK'] = 'flights'
        flights = [r for t in tasks for r in collision.stair_task(t)]
        self.assertTrue(flights)
        self.assertEqual(json.dumps(flights, sort_keys=True, default=str),
                         json.dumps([r for r in every if r.get('flight')], sort_keys=True, default=str))

    def test_the_gate_honours_the_scope_and_says_it(self):
        items = [dict(kind='step', flight=True, point=(0, 0, 0)), dict(kind='ramp', point=(1, 0, 0))]
        with mock.patch.dict(os.environ, {'AMIWIND_STAIR_WALK': 'flights'}):
            self.assertEqual(collision.scoped_items(items), items[:1])
            self.assertEqual(self.gate()['scope'], 'flights')
        with mock.patch.dict(os.environ, {'AMIWIND_STAIR_WALK': 'all'}):
            self.assertEqual(collision.scoped_items(items), items)
        with mock.patch.dict(os.environ, {'AMIWIND_STAIR_WALK': ''}):
            self.assertEqual(collision.scoped_items(items), items[:1])      # flights by default

    def test_flights_and_all_keep_separate_records(self):
        first = self.gate()
        os.environ['AMIWIND_STAIR_WALK'] = 'all'
        other = self.gate()
        self.assertEqual((first['pass_cache']['walked'], other['pass_cache']['walked']), (1, 1))


class ReachKey(World):
    def test_collision_out_of_reach_does_not_rekey_and_the_frame_key_does(self):
        base, frame_base = self.key(), collision.frame_stair_key(self.frames[0], self.models)
        _, _, far = self.placement(22)
        models = copy.deepcopy(self.models)
        for k in (9, 5, 1):           # clipnodes, point-hull nodes, planes: walls and undersides
            models[far['model']]['image'] = bumped(models[far['model']]['image'], k)
            self.assertEqual(self.key(models=models), base, F.LUMPS[k])
        self.assertNotEqual(collision.frame_stair_key(self.frames[0], models), frame_base)
        # moved within the core but out of reach: the items are found again, the same, the key stays
        frames = copy.deepcopy(self.frames)
        at, k, _ = self.placement(22)
        frames[0][2][at]['owned'][k]['origin'] = (320.0, 260.0, 40.0)
        self.assertEqual(self.key(frames), base)

    def test_what_the_walk_reads_rekeys(self):
        base = self.key()
        seen = {base}

        def differs(frames=None, models=None, what=''):
            k = self.key(frames, models)
            self.assertNotIn(k, seen, what)
            seen.add(k)
        _, _, near = self.placement(21)
        for k in (9, 1, 5, 3):         # the stair's own collision, planes, point hull and vertexes
            models = copy.deepcopy(self.models)
            models[near['model']]['image'] = bumped(models[near['model']]['image'], k)
            differs(models=models, what='stair model %s' % F.LUMPS[k])
        # the ground under the stair (the chunk's standing hull)
        frames = copy.deepcopy(self.frames)
        frames[0][2][0]['image'] = bumped(frames[0][2][0]['image'], 9)
        differs(frames, what='chunk clipnodes')
        # another placement moved into the stair's reach
        frames = copy.deepcopy(self.frames)
        at, k, _ = self.placement(22)
        frames[0][2][at]['owned'][k]['origin'] = (-300.0, -100.0, 40.0)
        differs(frames, what='placement moved into reach')
        # the stair placement's own fields, the frame path, grid and the scope
        for field, value in (('origin', (-301.0, -300.0, 40.0)), ('yaw', 10.0),
                             ('box', ((-400, -400, 0), (-200, -200, 100)))):
            frames = copy.deepcopy(self.frames)
            at, k, _ = self.placement(21)
            frames[0][2][at]['owned'][k][field] = value
            differs(frames, what='stair placement ' + field)
        frames = copy.deepcopy(self.frames)
        frames[0] = ('frames/x+01/y+00/frame.ccf',) + tuple(frames[0][1:])
        differs(frames, what='frame path')
        other = collision.reach_keys(self.out, self.frames, self.models, {}, 'all', None)[1][0]
        self.assertNotIn(other, seen)

    def test_a_traced_walk_stays_in_its_reach(self):
        """Every trace, ground, headroom and contents query of the walks lies in the boxes the key covers, for a flight
        that passes and one that fails (a convex fill over it), in both scopes."""
        import numpy as np
        import stair_walk
        from test_chim_stairs import world_of
        from chim.validate import Failures, load_world
        points = []
        real_trace = collision.FrameScene.trace
        real_contents = collision.FrameScene.contents

        def trace(scene, start, end):
            points.extend([start, end])
            return real_trace(scene, start, end)

        def contents(scene, p):
            points.append(p)
            return real_contents(scene, p)
        heads = {}
        for name in ('ground', 'free', 'box_free'):
            def query(room, *a, _real=getattr(stair_walk.Headroom, name), _name=name, **k):
                c = a[0] if _name == 'box_free' else (a[0], a[1])
                half = (max(collision.MAXS[0], collision.MAXS[1]) + stair_walk.SHELL_MARGIN
                        if _name == 'box_free' else 0.)
                points.extend([(c[0] - half, c[1] - half), (c[0] + half, c[1] + half)])
                return _real(room, *a, **k)
            heads[name] = query
        walked = 0
        for fill in (False, True):
            for scope in ('flights', 'all'):
                with tempfile.TemporaryDirectory() as tmp:
                    world_of(tmp, fill)
                    world = load_world(Path(tmp), Failures())
                    frames, models = world[5], world[4]
                    os.environ['AMIWIND_STAIR_WALK'] = scope
                    src = collision.reach_sources(frames[0], models, {})
                    boxes = []
                    for _, _, core in collision.stair_tasks(tmp, frames):
                        _, picked = collision.core_items_key(src, core, None, scope, 'code')
                        _, found = collision.stair_items_task((tmp, 0, [core], None, scope, None))
                        owners = picked[np.isin(src['sref'][picked], np.array(found[0][2], np.int64))]
                        boxes += collision.reach_boxes(src, owners, collision.walk_reach())
                    del points[:]
                    collision._STAIR_CACHE.clear()
                    with mock.patch.object(collision.FrameScene, 'trace', trace),                             mock.patch.object(collision.FrameScene, 'contents', contents),                             mock.patch.multiple(stair_walk.Headroom, **heads):
                        rows = [r for t in collision.stair_tasks(tmp, frames) for r in collision.stair_task(t)]
                    collision._STAIR_CACHE.clear()
                    walked += len(rows)
                    self.assertTrue(points)
                    outside = [p for p in points
                               if not any(b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] for b in boxes)]
                    self.assertEqual(outside, [], 'fill %s, %s: walk queries outside the reach key: %s'
                                     % (fill, scope, outside[:5]))
        self.assertTrue(walked)

    def test_items_are_kept_and_a_warm_gate_reads_no_frame_to_count(self):
        cold = self.gate()
        self.assertEqual(cold['pass_cache']['key_method'], 'reach')
        root = Path(os.environ['AMIWIND_PASS_CACHE'])
        self.assertTrue(list((root / collision.ITEMS_FOLDER).glob('*/*.json')))
        with mock.patch.object(collision, 'stair_items_task', side_effect=AssertionError('frame read')):
            warm = self.gate()
        self.assertEqual((warm['pass_cache']['walked'], warm['pass_cache']['reused']), (0, 1))
        strip = lambda r: {k: v for k, v in r.items() if k != 'pass_cache'}  # noqa: E731
        self.assertEqual(json.dumps(strip(warm), sort_keys=True), json.dumps(strip(cold), sort_keys=True))

    def test_frame_key_stays_selectable(self):
        with mock.patch.dict(os.environ, {'AMIWIND_STAIR_WALK_KEY': 'frame'}):
            self.assertEqual(collision.walk_key_method(), 'frame')
            self.assertEqual(self.gate()['pass_cache']['key_method'], 'frame')
        self.assertEqual(collision.walk_key_method('cached'), 'reach')
        self.assertEqual(collision.walk_key_method('records'), 'frame')
        with mock.patch.dict(os.environ, {'AMIWIND_STAIR_WALK_KEY': 'other'}):
            with self.assertRaises(ValueError):
                collision.walk_key_method()


class WatchAndPlaces(World):
    def watch(self, places):
        path = Path(self.cache.name) / 'watch.json'
        path.write_text(json.dumps({'format': collision.WATCH_FORMAT, 'places': places}), encoding='utf-8')
        return str(path)

    def test_a_watched_place_is_walked_again_and_a_place_off_the_list_is_not(self):
        self.gate()
        os.environ['AMIWIND_STAIR_WATCH'] = self.watch([{'id': 'TEST-STAIR-99', 'refs': [21]}])
        watched = self.gate()
        how = watched['pass_cache']['frames'][self.frames[0][0]]
        self.assertTrue(how.startswith('walked again: watch list (TEST-STAIR-99)'), how)
        self.assertEqual(watched['pass_cache']['watched'], {self.frames[0][0]: ['TEST-STAIR-99']})
        os.environ['AMIWIND_STAIR_WATCH'] = self.watch([{'id': 'TEST-STAIR-98', 'refs': [999999]}])
        off = self.gate()
        self.assertEqual((off['pass_cache']['walked'], off['pass_cache']['reused'], off['pass_cache']['watched']),
                         (0, 1, {}))

    def test_targeted_walk_walks_only_the_named_place_and_stores_nothing(self):
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = 'ref:21'
        report = self.gate()
        self.assertTrue(report['tested'])
        self.assertEqual({r['ref'] for r in report['failures'] + report['advisory_failures']} - {21}, set())
        self.assertEqual(report['targeted']['frames'], {self.frames[0][0]: {'places': ['ref:21'], 'refs': [21]}})
        self.assertEqual(report['pass_cache']['stored'], [])
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = 'ref:22'        # placed, but none of its steps is an item
        self.assertEqual(self.gate()['tested'], 0)
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = '7:7'           # a cell no frame holds
        nothing = self.gate()
        self.assertEqual((nothing['tested'], nothing['targeted']['frames']), (0, {}))
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = 'no such place'
        with self.assertRaises(ValueError):
            self.gate()

    def test_places_by_id_cell_frame_and_ref(self):
        watch = [{'id': 'TEST-STAIR-97', 'cells': [[0, 0]]}]
        places = collision.parse_places('TEST-STAIR-97,3:-4,frames/x+00/y+00/frame.ccf,ref:21,42', watch)
        self.assertEqual([p['id'] for p in places],
                         ['TEST-STAIR-97', '3:-4', 'frames/x+00/y+00/frame.ccf', 'ref:21', '42'])
        self.assertEqual(places[1]['cells'], [[3, -4]])
        self.assertIsNone(collision.parse_places('', watch))
        found = collision.match_places(self.frames, places)
        self.assertEqual(list(found), [0])
        self.assertIsNone(found[0][1])        # a cell or frame place: the whole frame


class ImageStepWalk(unittest.TestCase):
    """The image step's walk of the maps (tools/stair_parallel.py): CHIM frame maps are left to the CHIM gate, the
    watch list's maps are walked again, a targeted walk walks only the named maps and stores nothing."""

    def setUp(self):
        from test_stair_walk import build
        self.env = dict(os.environ)
        self.tmp = tempfile.TemporaryDirectory()
        self.id1 = Path(self.tmp.name) / 'id1'
        maps = self.id1 / 'maps'
        maps.mkdir(parents=True)
        (maps / 'hall.bsp').write_bytes(build(fill=False))
        (maps / 'tall.bsp').write_bytes(build(rise=7.))
        for name in ('AMIWIND_STAIR_WALK_PLACES', 'AMIWIND_STAIR_WALK_FRAME_MAPS'):
            os.environ.pop(name, None)
        os.environ.update(AMIWIND_PASS_CACHE=str(Path(self.tmp.name) / 'cache'), AMIWIND_STAIR_WALK_CACHE='cached',
                          AMIWIND_STAIR_WALK_SAMPLE='0', AMIWIND_STAIR_WALK='all', AMIWIND_STAIR_WATCH='off')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def test_frame_maps_are_left_to_the_chim_gate(self):
        import map_files
        import stair_walk
        frame = lambda p: Path(p).stem == 'tall'  # noqa: E731
        with mock.patch.object(map_files, 'is_chim_frame', side_effect=frame):
            self.assertEqual([Path(t[0]).stem for t in stair_walk.map_tasks(self.id1)], ['hall'])
            os.environ[stair_walk.FRAME_MAPS_ENV] = 'on'
            self.assertEqual([Path(t[0]).stem for t in stair_walk.map_tasks(self.id1)], ['hall', 'tall'])

    def watch(self, places):
        path = Path(self.tmp.name) / 'watch.json'
        path.write_text(json.dumps({'format': collision.WATCH_FORMAT, 'places': places}), encoding='utf-8')
        os.environ['AMIWIND_STAIR_WATCH'] = str(path)

    def test_watched_map_is_walked_again(self):
        import stair_parallel
        self.watch([{'id': 'TEST-STAIR-96', 'maps': ['hall']}])
        report = stair_parallel.check(self.id1, jobs=1)
        self.assertEqual(report['pass_cache']['walked_again'], ['hall'])
        self.watch([{'id': 'TEST-STAIR-95', 'maps': ['nothere']}])
        self.assertEqual(stair_parallel.check(self.id1, jobs=1)['pass_cache']['walked_again'], [])

    def test_targeted_walk_walks_only_the_named_map(self):
        import stair_parallel
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = 'map:hall'
        report = stair_parallel.check(self.id1, jobs=1)
        self.assertEqual({r['map'] for r in report['rows']}, {'hall'})
        self.assertNotIn('pass_cache', report)                       # nothing reused or stored
        os.environ['AMIWIND_STAIR_WALK_PLACES'] = '7:7'              # a place of the CHIM gate only
        self.assertEqual(stair_parallel.check(self.id1, jobs=1)['maps'], 0)


class ShippedWatchList(unittest.TestCase):
    def test_every_place_is_a_registered_stair_bug(self):
        places = collision.load_watch(str(collision.watch_file()))
        self.assertTrue(places)
        ids = set()
        for path in [ROOT / 'docs/bugs/bugs.json'] + sorted((ROOT / 'docs/bugs/archive').glob('*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            ids |= {b['id'] for b in (data.get('bugs', []) if isinstance(data, dict) else data)}
        for p in places:
            self.assertIn(p['id'], ids)
            self.assertTrue((ROOT / 'docs/bugs' / (p['id'] + '.md')).is_file(), p['id'])
            for ref in p.get('refs') or ():
                self.assertIsInstance(ref, int)
        self.assertEqual(collision.load_watch('off'), [])
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'w.json'
            bad.write_text(json.dumps({'format': collision.WATCH_FORMAT, 'places': [{'id': 'X'}]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                collision.load_watch(str(bad))

    def test_watch_file_is_released(self):
        listed = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        self.assertIn('config/stair-watch.json', listed)


class Guard(unittest.TestCase):
    def test_walk_scenes_use_a_fixed_guard(self):
        text = (ROOT / 'tools/chim/collision.py').read_text(encoding='utf-8')
        self.assertIn('standing.full_nodes = points.full_nodes = WALK_GUARD_NODES', text)
        self.assertGreaterEqual(collision.WALK_GUARD_NODES, 65536)
        self.assertTrue(struct)


if __name__ == '__main__':
    unittest.main()
