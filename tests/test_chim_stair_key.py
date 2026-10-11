# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM stair gate's frame key covers exactly what the walk reads, and its scheduler changes no row
(BUILD-CHIM-STAIR-WALK-UNCACHED-36, persisting: the coast2 build walked all 330 frames again).

Both ways: a world-wide texture table entry, the world's model numbering, placement ids or reach records do NOT
rekey a frame (they are not read by the walk); any change to a lump the walk reads, the frame grid, the tile, a
placement's reference, origin, yaw or box, or a placed model's collision DOES. The walker key holds the frame
worker's code only: the known-findings table is not in it. The unit scheduler gives the rows of the per-core walk
byte for byte, and a warm run walks nothing and writes the same report as the cold one.
"""
import copy
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import collision  # noqa: E402
from chim import format as F  # noqa: E402


def replace_lump(image, k, data):
    """The brush image with lump K replaced (lumps rewritten in their file order, header updated)."""
    lumps = F.read_brush_image(image)
    lumps[k] = data
    order = sorted(range(15), key=lambda i: struct.unpack_from('<i', image, 4 + 8 * i)[0])
    body, offsets, at = b'', {}, F.BSP_HEADER
    for i in order:
        offsets[i] = (at, len(lumps[i]))
        body += lumps[i]
        at += len(lumps[i])
    head = struct.pack('<i', F.BSPVERSION) + b''.join(struct.pack('<ii', *offsets[i]) for i in range(15))
    return head + body


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_chim_stairs import world_of
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'world'
        cls.out.mkdir()
        world_of(cls.out, False)
        from chim.validate import Failures, load_world
        world = load_world(cls.out, Failures())
        cls.frame, cls.models = world[5][0], world[4]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def key(self, frame=None, models=None):
        return collision.frame_stair_key(frame or self.frame, self.models if models is None else models)

    def changed_chunk(self, change):
        frame = copy.deepcopy(self.frame)
        change(frame[2][0])
        return frame


class KeyCoversWhatTheWalkReads(Fixture):
    def test_not_read_by_the_walk_does_not_rekey(self):
        base = self.key()
        # the world's texture table entries in a chunk image (textures lump)
        frame = self.changed_chunk(lambda c: c.update(image=replace_lump(c['image'], 2, b'\x01\x00\x00\x00' * 3)))
        self.assertEqual(self.key(frame), base)
        # every other lump the walk never reads
        for k in (0, 4, 8, 11):
            frame = self.changed_chunk(lambda c: c.update(image=replace_lump(c['image'], k, F.read_brush_image(
                c['image'])[k] + (b'\x00\x00' if k == 11 else b'\x07'))))
            self.assertEqual(self.key(frame), base, F.LUMPS[k])
        # the world's model numbering and placement ids: a model inserted in front shifts every number
        models = [dict(self.models[0])] + list(self.models)
        frame = copy.deepcopy(self.frame)
        for c in frame[2]:
            for r in c['owned'] + c['reach']:
                r['model'] += 1
                r['pid'] = r.get('pid', 0) + 1000
        self.assertEqual(self.key(frame, models), base)
        # a placed model's textures lump
        models = copy.deepcopy(self.models)
        for m in models:
            m['image'] = replace_lump(m['image'], 2, b'\x02\x00\x00\x00')
        self.assertEqual(self.key(models=models), base)
        # reach records (a neighbour's placements reaching in) and frame bookkeeping fields
        frame = copy.deepcopy(self.frame)
        frame[2][0]['reach'] = frame[2][0]['reach'] + [{'model': 0, 'ref': 99, 'origin': (0, 0, 0)}]
        frame[1]['owned_total'] = (frame[1].get('owned_total') or 0) + 7
        self.assertEqual(self.key(frame), base)

    def test_everything_the_walk_reads_rekeys(self):
        base = self.key()
        seen = {base}

        def differs(frame=None, models=None, what=''):
            k = self.key(frame, models)
            self.assertNotIn(k, seen, what)
            seen.add(k)
        for k in collision.STAIR_WALK_LUMPS:
            def bump(c, k=k):
                data = bytearray(F.read_brush_image(c['image'])[k])
                if not data:
                    return
                data[0] ^= 0x01
                c['image'] = replace_lump(c['image'], k, bytes(data))
            frame = self.changed_chunk(bump)
            if F.read_brush_image(frame[2][0]['image'])[k]:
                differs(frame, what='chunk lump %s' % F.LUMPS[k])
        for field in collision.STAIR_FRAME_FIELDS:
            frame = copy.deepcopy(self.frame)
            value = frame[1][field]
            frame[1][field] = [v + 1 for v in value] if isinstance(value, (list, tuple)) else value + 1
            differs(frame, what='frame ' + field)
        frame = copy.deepcopy(self.frame)
        frame = ('frames/x+01/y+00/frame.ccf',) + frame[1:]
        differs(frame, what='frame path')
        owner = next(c for c in self.frame[2] if c['owned'])
        at = self.frame[2].index(owner)
        for field, value in (('ref', 12345), ('origin', (1.0, 2.0, 3.0)), ('yaw', 33.0), ('box', ((0, 0, 0), (1, 1, 1)))):
            frame = copy.deepcopy(self.frame)
            frame[2][at]['owned'][0][field] = value
            differs(frame, what='placement ' + field)
        # a placed model's collision (its clipnodes) and a different model placed
        models = copy.deepcopy(self.models)
        m = owner['owned'][0]['model']
        data = bytearray(F.read_brush_image(models[m]['image'])[9])
        data[0] ^= 0x01
        models[m]['image'] = replace_lump(models[m]['image'], 9, bytes(data))
        differs(models=models, what='model clipnodes')
        others = [i for i in range(len(self.models)) if F.read_brush_image(self.models[i]['image'])[9]
                  != F.read_brush_image(self.models[m]['image'])[9]]
        if others:
            frame = copy.deepcopy(self.frame)
            frame[2][at]['owned'][0]['model'] = others[0]
            differs(frame, what='another model placed')
        # the tile (a walker parameter) is in the frame part
        from unittest import mock
        with mock.patch.object(collision, 'STAIR_TILE', collision.STAIR_TILE * 2):
            differs(what='stair tile')

    def test_walker_key_is_the_frame_worker_without_the_known_findings_table(self):
        from build_cache import SourceIndex
        index = SourceIndex(ROOT, top_format=2)
        script = Path(collision.__file__).resolve()
        index.entry_digest(script, 'stair_task', frozenset({'tools/pass_cache.py'}))
        python, data, uncertain, _ = index._closures['%s::%s' % (script, 'stair_task')]
        reached = python | data
        self.assertFalse(uncertain)
        self.assertNotIn('config/known-stair-findings.json', reached)
        self.assertNotIn('tools/chim/known.py', reached)
        for walker in ('tools/chim/collision.py', 'tools/stair_walk.py', 'tools/player_hull.py',
                       'tools/audit_walkability.py'):
            self.assertIn(walker, reached)
        # the stair rule (options) is in the cache key next to the sources
        from pass_cache import PassCache
        a = PassCache('stair-walk', {'stair_mode': 'on', 'world': 'chim-frame', 'tile': 1024.0}, 's', '/x')
        b = PassCache('stair-walk', {'stair_mode': 'off', 'world': 'chim-frame', 'tile': 1024.0}, 's', '/x')
        c = PassCache('stair-walk', {'stair_mode': 'on', 'world': 'chim-frame', 'tile': 1024.0}, 't', '/x')
        self.assertEqual(len({a.key('k'), b.key('k'), c.key('k')}), 3)


class UnitsGiveThePerCoreRows(Fixture):
    def setUp(self):
        self.env = dict(os.environ)
        self.cache = tempfile.TemporaryDirectory()
        os.environ.update(AMIWIND_PASS_CACHE=str(Path(self.cache.name) / 'cache'), AMIWIND_STAIR_WALK_CACHE='cached',
                          AMIWIND_STAIR_WALK_SAMPLE='0')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.cache.cleanup()

    def gate(self, jobs):
        from chim.validate import Failures, load_world
        world = load_world(self.out, Failures())
        return collision.stair_gate(self.out, world[5], jobs, models=world[4])

    def test_units_skip_empty_cores_largest_first_in_core_order(self):
        cores = {0: ['a', 'b', 'c', 'd', 'e'], 1: ['f', 'g']}
        counts = {0: [5, 0, 5, 9, 0], 1: [0, 1]}
        units = collision.stair_units([0, 1], cores, counts, workers=1)       # budget ceil(20 / 4) = 5
        self.assertEqual(sorted(sum((u[2] for u in units), [])), ['a', 'c', 'd', 'g'])
        self.assertEqual([u[0] for u in units], sorted((u[0] for u in units), reverse=True))
        by_id = sorted(units, key=lambda u: u[3])
        self.assertEqual([c for u in by_id for c in u[2]], ['a', 'c', 'd', 'g'])
        self.assertEqual(collision.stair_units([0], {0: ['a']}, {0: [0]}, 4), [])

    def test_rows_byte_for_byte_and_warm_run_walks_nothing(self):
        import stair_records
        from stair_walk import rows_digest
        collision._STAIR_CACHE.clear()
        serial = [r for t in collision.stair_tasks(self.out, [self.frame]) for r in collision.stair_task(t)]
        cold = self.gate(2)
        self.assertEqual((cold['pass_cache']['walked'], cold['pass_cache']['reused']), (1, 0))
        self.assertTrue(cold['pass_cache']['frames'][self.frame[0]].startswith('walked: no earlier walk'))
        from pass_cache import PassCache
        cache = PassCache('stair-walk', {'stair_mode': cold['stair_rule'], 'world': 'chim-frame',
                                         'tile': collision.STAIR_TILE}, collision.stair_key_sources(),
                          os.environ['AMIWIND_PASS_CACHE'])
        stored = stair_records.lookup(cache, collision.frame_stair_key(self.frame, self.models))[0]['rows']
        self.assertEqual(rows_digest(stored), rows_digest(json.loads(json.dumps(serial, default=str))))
        self.assertTrue(serial)
        folder = Path(self.cache.name) / 'runs' / '2026_10_11_v0.0.36-dev5_full_abc1234'
        folder.mkdir(parents=True)
        (folder / 'chim-stairs.json').write_text(json.dumps(cold), encoding='utf-8')
        self.assertEqual(stair_records.promote(folder, 'req-1')['marked'], 1)
        warm = self.gate(2)
        self.assertEqual((warm['pass_cache']['walked'], warm['pass_cache']['reused'], warm['pass_cache']['units']),
                         (0, 1, 0))
        strip = lambda r: {k: v for k, v in r.items() if k != 'pass_cache'}  # noqa: E731
        self.assertEqual(json.dumps(strip(warm), sort_keys=True), json.dumps(strip(cold), sort_keys=True))

    def test_a_walked_frame_names_the_input_that_changed(self):
        cold = self.gate(1)
        import stair_records
        from chim.validate import Failures, load_world
        world = load_world(self.out, Failures())
        parts = collision.frame_stair_parts(world[5][0], world[4])
        moved = [(n, d if n != 'chunk 0,0 terrain' else '0' * 64) for n, d in parts]
        from pass_cache import PassCache
        cache = PassCache('stair-walk', {'stair_mode': cold['stair_rule'], 'world': 'chim-frame',
                                         'tile': collision.STAIR_TILE}, collision.stair_key_sources(),
                          os.environ['AMIWIND_PASS_CACHE'])
        why = collision.walk_reason(cache, world[5][0][0], collision._parts_key(moved), moved)
        self.assertEqual(why, 'inputs changed: 1 of %d (chunk 0,0 terrain)' % len(parts))
        self.assertIn('walker code changed', collision.walk_reason(
            PassCache('stair-walk', cache.options, 'other', cache.root), world[5][0][0], 'k', parts))
        self.assertIn('no check mark', collision.walk_reason(cache, 'x', 'k', parts, candidate=True))
        self.assertTrue(stair_records)


if __name__ == '__main__':
    unittest.main()
