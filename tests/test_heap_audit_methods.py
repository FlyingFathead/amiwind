# SPDX-License-Identifier: GPL-3.0-only
"""The world map heap audit's array methods equal the earlier loops (BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36).

inspect_efrags (static entity leaf links) and the edge-cache prefix each have a 'vector' method (numpy,
the default) and the earlier 'python' loop (kept, AMIWIND_HEAP_AUDIT_METHOD=python). Random valid BSP
trees with axial and sloped planes, both static kinds and many poses must give equal reports; broken
trees must make both raise. The audit's chunks deal every map exactly once.
"""
from pathlib import Path
import os
import random
import struct
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import check_world_map_heap as heap  # noqa: E402
from edge_cache_heap import prefix  # noqa: E402
import sprite_heap  # noqa: E402
from sprite_heap import efrag_method, estimate_sprite, inspect_efrags  # noqa: E402

SIZES = {'hunk': 16, 'pointer': 4, 'float': 4, 'msprite': 32, 'mspriteframe': 32, 'mspritegroup': 12,
         'mspriteframedesc': 8, 'entity': 224, 'efrag': 16}
POLICY = {'base_links': 64, 'page_links': 32, 'max_links': 1 << 30, 'max_statics': 4096}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def sprite(w=8, h=8):
    return (struct.pack('<4siifiiifi', b'IDSP', 1, 2, 100, w, h, 1, 0, 0) + struct.pack('<5i', 0, -w // 2, h, w, h)
            + bytes([255]) * (w * h))


def random_table(rng, depth=7, statics=40):
    """A random valid BSP29 tree (lumps as the audit reads them) with aw_flora and aw_static entities."""
    planes, nodes, leaves = [], [], []

    def leaf():
        leaves.append(rng.choice((-1, -1, -2, -2, -1)))
        return -len(leaves)          # child -1-leaf

    def node(level):
        index = len(nodes)
        nodes.append(None)
        kind = rng.randrange(6)
        if kind < 3:
            normal = [0.0, 0.0, 0.0]
            normal[kind] = 1.0
        else:
            normal = [f32(rng.uniform(-1, 1)) for _ in range(3)]
        planes.append((normal, f32(rng.uniform(-900, 900)), kind))
        children = [node(level + 1) if level < depth and rng.random() < .8 else leaf() for _ in range(2)]
        nodes[index] = (len(planes) - 1, children)
        return index
    node(0)
    entities = [b'{"classname" "worldspawn"}']
    for _ in range(statics):
        x, y, z = (rng.uniform(-1000, 1000) for _ in range(3))
        if rng.random() < .5:
            entities.append(('{"classname" "aw_flora" "model" "tree.spr" "origin" "%.3f %.3f %.3f" "aw_scale" "%.4f"}'
                             % (x, y, z, rng.uniform(.2, 30))).encode())
        else:
            entities.append(('{"classname" "aw_static" "model" "*1" "origin" "%.5f %.5f %.5f"}' % (x, y, z)).encode())
    model = struct.pack('<9f7i', -40.5, -33.25, -8, 60, 41.75, 120.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    return {
        'entities': b'\n'.join(entities),
        'planes': b''.join(struct.pack('<4fi', *normal, dist, kind) for normal, dist, kind in planes),
        'nodes': b''.join(struct.pack('<i2h6h2H', plane, *children, *([0] * 6), 0, 0) for plane, children in nodes),
        'leafs': b''.join(struct.pack('<ii6h2H4B', contents, 0, *([0] * 12)) for contents in leaves),
        'models': model * 2,
    }


def sprites():
    return {'sprite_assets': [{'model': 'tree.spr', **estimate_sprite(sprite(), SIZES)}]}


class EfragMethodsTests(unittest.TestCase):
    def test_vector_equals_python_on_random_trees(self):
        rng = random.Random(36)
        links = 0
        for trial in range(60):
            table = random_table(rng, depth=rng.randrange(1, 9), statics=rng.randrange(0, 80))
            python = inspect_efrags(table, sprites(), SIZES, POLICY, 'python')
            vector = inspect_efrags(table, sprites(), SIZES, POLICY, 'vector')
            self.assertEqual(python, vector, trial)
            links += vector['required_links']
        self.assertGreater(links, 1000)   # the trees really link entities to many leaves

    def test_default_is_vector_and_env_selects_python(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_HEAP_AUDIT_METHOD', None)
            self.assertEqual(efrag_method(), 'vector')
            os.environ['AMIWIND_HEAP_AUDIT_METHOD'] = 'python'
            self.assertEqual(efrag_method(), 'python')
            os.environ['AMIWIND_HEAP_AUDIT_METHOD'] = 'nonsense'
            with self.assertRaisesRegex(ValueError, 'Unknown heap audit method'):
                efrag_method()

    def test_link_limit_raises_the_same_message(self):
        rng = random.Random(7)
        table = random_table(rng, depth=6, statics=60)
        total = inspect_efrags(table, sprites(), SIZES, POLICY, 'python')['required_links']
        policy = dict(POLICY, max_links=total - 1)
        messages = []
        for method in ('python', 'vector'):
            with self.assertRaises(ValueError) as caught:
                inspect_efrags(table, sprites(), SIZES, policy, method)
            messages.append(str(caught.exception))
        self.assertEqual(messages[0], messages[1])
        self.assertIn('leaf-link limit exceeded: %d' % total, messages[0])

    def test_broken_trees_raise_in_both_methods(self):
        rng = random.Random(3)
        base = random_table(rng, depth=3, statics=5)
        cyclic = dict(base, nodes=struct.pack('<i2h6h2H', 0, 0, 0, *([0] * 6), 0, 0) + base['nodes'][24:])
        bad_leaf = dict(base, nodes=struct.pack('<i2h6h2H', 0, -999, -999, *([0] * 6), 0, 0) + base['nodes'][24:])
        bad_plane = dict(base, nodes=struct.pack('<i2h6h2H', 9999, -1, -1, *([0] * 6), 0, 0) + base['nodes'][24:])
        bad_node = dict(base, nodes=struct.pack('<i2h6h2H', 0, 30000, 30000, *([0] * 6), 0, 0) + base['nodes'][24:])
        for name, table, text in (('cycle', cyclic, 'Cyclic'), ('leaf', bad_leaf, 'leaf'),
                                  ('plane', bad_plane, 'plane'), ('node', bad_node, 'node')):
            for method in ('python', 'vector'):
                with self.subTest(name=name, method=method), self.assertRaisesRegex(ValueError, text):
                    inspect_efrags(table, sprites(), SIZES, POLICY, method)


def random_edge_table(rng):
    faces = rng.randrange(1, 60)
    surfedges = [rng.randrange(-500, 500) for _ in range(rng.randrange(1, 400))]
    rows = []
    for _ in range(faces):
        first = rng.randrange(0, len(surfedges))
        rows.append(struct.pack('<Hhihh4Bi', 0, 0, first, rng.randrange(0, len(surfedges) - first + 1), 0,
                                255, 255, 255, 255, -1))
    world_first = rng.randrange(0, faces)
    model = struct.pack('<9f7i', *[0] * 9, 0, 0, 0, 0, 0, world_first, rng.randrange(0, faces - world_first + 1))
    nodes = b''
    for _ in range(rng.randrange(0, 20)):
        first = rng.randrange(0, faces)
        nodes += struct.pack('<i2h6h2H', 0, -1, -1, *[0] * 6, first, rng.randrange(0, faces - first + 1))
    marks = struct.pack('<%dH' % (n := rng.randrange(0, 30)), *(rng.randrange(0, faces) for _ in range(n)))
    return dict(faces=b''.join(rows), models=model, nodes=nodes, marksurfaces=marks,
                surfedges=struct.pack('<%di' % len(surfedges), *surfedges), edges=bytes(4 * 501))


class EdgePrefixMethodsTests(unittest.TestCase):
    def test_vector_equals_python_on_random_lumps(self):
        rng = random.Random(1036)
        for trial in range(300):
            table = random_edge_table(rng)
            self.assertEqual(prefix(table, 'python'), prefix(table, 'vector'), trial)

    def test_broken_spans_raise_in_both_methods(self):
        rng = random.Random(5)
        table = random_edge_table(rng)
        cases = (('face span', dict(table, marksurfaces=struct.pack('<H', 999))),
                 ('edge index', dict(table, edges=bytes(4))),
                 ('Missing edge-cache world model', dict(table, models=b'')))
        for text, broken in cases:
            for method in ('python', 'vector'):
                with self.subTest(text=text, method=method), self.assertRaisesRegex(ValueError, text):
                    prefix(broken, method)
        short = dict(table, faces=table['faces'][:-1])
        for method in ('python', 'vector'):
            with self.subTest(case='short lump', method=method), self.assertRaises(struct.error):
                prefix(short, method)


class AuditChunkTests(unittest.TestCase):
    def test_chunks_deal_every_map_once_and_spread_neighbours(self):
        for count in (1, 2, 9, 100, 2598):
            for jobs in (1, 3, 24):
                chunks = heap.map_chunks(count, jobs)
                flat = sorted(index for chunk in chunks for index in chunk)
                self.assertEqual(flat, list(range(count)))
                self.assertEqual(len(chunks), min(count, heap.CHUNKS_PER_WORKER * jobs))
                # neighbouring maps land in different chunks
                if len(chunks) > 1:
                    self.assertNotEqual(chunks[0][:2], [0, 1])

    def test_static_limit_read_once_per_audit(self):
        calls = []
        import engine_limits
        real = engine_limits.limits

        def counted(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs)
        from test_check_world_map_heap import SIZES as HEAP_SIZES, make_bsp
        import tempfile
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(engine_limits, 'limits', side_effect=counted):
            maps = Path(temp)
            for index in range(6):
                (maps / f'sn{index:03d}.bsp').write_bytes(make_bsp())
            report = heap.inspect_maps(maps, HEAP_SIZES, jobs=1)
        self.assertEqual(report['map_count'], 6)
        self.assertEqual(len(calls), 1)

    def test_sprite_static_limit_argument_matches_engine_read(self):
        entity = b'{"classname" "aw_static" "model" "progs/m001.spr"}\n'
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'progs').mkdir()
            (root / 'progs/m001.spr').write_bytes(sprite())
            limit = __import__('engine_limits').limits()['max_static_entities']
            self.assertEqual(sprite_heap.inspect_sprites(entity, root, SIZES),
                             sprite_heap.inspect_sprites(entity, root, SIZES, limit))
            with self.assertRaisesRegex(ValueError, 'Static sprite entity limit'):
                sprite_heap.inspect_sprites(entity * 2, root, SIZES, 1)


if __name__ == '__main__':
    unittest.main()
