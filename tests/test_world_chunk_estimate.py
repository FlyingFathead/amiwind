# SPDX-License-Identifier: GPL-3.0-only
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_chunk_estimate as wce  # noqa: E402

SIZES = {'hunk': 16, 'mvertex': 12, 'medge': 4, 'mplane': 20, 'mtexinfo': 44, 'msurface': 48, 'pointer': 4,
         'mleaf': 60, 'mnode': 40, 'clipnode': 8, 'dmodel': 64, 'texture': 64, 'scenery': 200}


def miptex(name, pixel):
    head = name.encode().ljust(16, b'\0') + struct.pack('<II4I', 8, 8, 40, 104, 120, 124)
    return head + bytes([pixel]) * (64 + 16 + 4 + 1)


def make_map(world_squares, objects, texname='t0', pixel=7, nodes=None):
    """world_squares: [(x0, y0, x1, y1)]; objects: [(ref, x, y)] each a 32-unit square
    submodel. One texture; no lightmaps, no collision hulls."""
    verts, edges, surfedges, faces = [], [(0, 0)], [], []

    def square(x0, y0, x1, y1):
        base = len(verts)
        verts.extend([(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)])
        first = len(surfedges)
        for i in range(4):
            edges.append((base + i, base + (i + 1) % 4)); surfedges.append(len(edges) - 1)
        faces.append(struct.pack('<HhiHH4Bi', 0, 0, first, 4, 0, 255, 255, 255, 255, -1))
    for sq in world_squares:
        square(*sq)
    models = [struct.pack('<9f7i', -4096, -4096, -64, 4096, 4096, 64, 0, 0, 0, -1, -1, -1, -1, 0, 0,
                          len(world_squares))]
    ents = ['{\n"classname" "worldspawn"\n}\n']
    for i, (ref, x, y) in enumerate(objects):
        first = len(faces)
        square(-16, -16, 16, 16)
        models.append(struct.pack('<9f7i', -16, -16, -1, 16, 16, 1, 0, 0, 0, -1, -1, -1, -1, 0, first, 1))
        ents.append('{\n"classname" "func_wall"\n"model" "*%d"\n"aw_ref" "%s"\n"origin" "%g %g 0"\n}\n'
                    % (i + 1, ref, x, y))
    tex = struct.pack('<ii', 1, 8) + miptex(texname, pixel)
    lumps = [''.join(ents).encode() + b'\0', struct.pack('<4fi', 0, 0, 1, 0, 2), tex,
             b''.join(struct.pack('<3f', *v) for v in verts), b'',
             b''.join(struct.pack('<i2h6h2H', *n) for n in (nodes or [])),
             struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0), b''.join(faces), b'', b'',
             struct.pack('<2i6h2H4B', -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), b'',
             b''.join(struct.pack('<2H', *e) for e in edges), b''.join(struct.pack('<i', s) for s in surfedges),
             b''.join(models)]
    header = bytearray(struct.pack('<i', 29)); body = bytearray(); offset = wce.HEADER
    for lump in lumps:
        header.extend(struct.pack('<ii', offset + len(body), len(lump))); body.extend(lump)
        body.extend(b'\0' * (-len(body) % 4))
    return bytes(header + body)


REGIONS = 'ra 0 0 512 512 0 0 1024 512\nrb 512 0 1024 512 0 0 1024 512\n'


def two_regions():
    world = [(0, 0, 256, 256), (600, 0, 856, 256)]
    a = make_map(world, [('7', 100, 100), ('8', 700, 100)], texname='aa', pixel=7)
    b = make_map(world, [('8', 700, 100), ('7', 100, 100)], texname='zz', pixel=7)
    return {'ra': wce.Map(a), 'rb': wce.Map(b)}, wce.read_regions(REGIONS)


class WorldChunkEstimateTests(unittest.TestCase):
    def test_repeated_placements_are_counted_once_and_textures_by_pixels(self):
        maps, regions = two_regions()
        placements, variants, terrain, texbytes, today = wce.collect(maps, regions)
        self.assertEqual(sorted(placements), ['7', '8'])
        self.assertEqual(sum(len(p['maps']) for p in placements.values()), 4)
        self.assertEqual(len(variants), 1)           # same geometry, differently named texture
        self.assertEqual(len(texbytes), 1)
        self.assertEqual([len(t['faces']) for t in terrain.values()], [1, 1])  # each world face once

    def test_objects_go_to_the_chunk_of_their_origin(self):
        maps, regions = two_regions()
        placements, variants, terrain, _, _ = wce.collect(maps, regions)
        chunks = wce.build_chunks(placements, variants, terrain, (0, 0), 1024, 512)
        self.assertEqual(chunks[(0, 0)].placements, 1)
        self.assertEqual(chunks[(1, 0)].placements, 1)
        self.assertEqual(chunks[(0, 1)].placements, 0)
        self.assertEqual(chunks[(0, 0)].render['faces'], 2)   # its terrain face plus the object face
        lib = wce.build_chunks(placements, variants, terrain, (0, 0), 1024, 512, mode='library')
        self.assertEqual(lib[(0, 0)].render['faces'], 1)      # library keeps the object outside the chunk
        self.assertEqual(wce.price(lib, variants, SIZES, 'library').__len__(), 1)

    def test_origin_rule_grows_the_content_box_bounds_rule_does_not(self):
        maps, regions = two_regions()
        placements, variants, terrain, _, _ = wce.collect(maps, regions)
        placements['7']['hi'] = [600, 120, 1]
        grown = wce.build_chunks(placements, variants, terrain, (0, 0), 1024, 512, rule='origin')
        flat = wce.build_chunks(placements, variants, terrain, (0, 0), 1024, 512, rule='bounds')
        self.assertEqual(grown[(0, 0)].cbox[2], 600)
        self.assertEqual(flat[(0, 0)].cbox[2], 512)

    def test_draw_distance_ring_uses_euclidean_gap(self):
        chunks = {(i, j): wce.Chunk((i, j), (i * 100, j * 100, i * 100 + 100, j * 100 + 100))
                  for i in range(5) for j in range(5)}
        self.assertEqual(len(wce.ring(chunks, (2, 2), 120, 100)), 21)   # corners at 141 excluded
        self.assertEqual(len(wce.ring(chunks, (2, 2), 150, 100)), 25)
        self.assertEqual(len(wce.ring(chunks, (2, 2), 50, 100)), 9)

    def test_crossing_reads_only_new_chunks_and_new_textures(self):
        chunks = {(i, 0): wce.Chunk((i, 0), (i * 100, 0, i * 100 + 100, 100)) for i in range(3)}
        for i, ch in chunks.items():
            ch.disk, ch.cdisk = 1000, 10
            ch.textures = {'shared', 'own%d' % i[0]}
        tex = {'shared': 500, 'own0': 1, 'own1': 2, 'own2': 4}
        got = wce.crossing(chunks, [(0, 0), (1, 0)], [(1, 0), (2, 0)], [(0, 0)], [(1, 0)], tex)
        self.assertEqual(got, 1000 + 10 + 4)

    def test_shared_subtrees_are_counted_once(self):
        nodes = [(0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0), (0, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0)]
        m = wce.Map(make_map([(0, 0, 1, 1)], [], nodes=nodes))
        got_nodes, got_leafs = m.render_tree(0)
        self.assertEqual(sorted(got_nodes), [0, 1])
        self.assertEqual(got_leafs, [0])

    def test_heap_record_matches_hunk_rounding(self):
        rec = {k: 0 for k in wce.NUM}
        rec.update(faces=1, vertexes=4, edges=4, surfedges=4, planes=1, texinfo=1)
        rec['models'] = 1
        expect = (16 + 48) + (16 + 32) + (16 + 16) + (16 + 32) + (16 + 48) + (16 + 48) + (16 + 64)
        self.assertEqual(wce.heap_bytes(rec, SIZES), expect)

    def test_estimate_and_command_line(self):
        maps, regions = two_regions()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, m in maps.items():
                (tmp / (name + '.bsp')).write_bytes(m.data)
            (tmp / 'regions.txt').write_bytes(REGIONS.encode())
            (tmp / 'sizes.json').write_bytes(json.dumps(SIZES).encode())
            out = tmp / 'out.json'
            self.assertEqual(wce.main([str(tmp), str(tmp / 'regions.txt'), '--sizes', str(tmp / 'sizes.json'),
                                       '--grain', '256', '--draw-distance', '0', '--hysteresis', '0',
                                       '--collision-margin', '0', '--out', str(out)]), 0)
            raw = out.read_bytes()
            self.assertNotIn(b'\r', raw)
            result = json.loads(raw)
            self.assertEqual(result['duplication_factor'], 2.0)
            self.assertEqual(result['chunks'], 16)
            self.assertEqual(result['today_disk'], sum(len(m.data) for m in maps.values()))
            self.assertGreater(result['valid_centres'], 0)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            wce.Map(b'not a map')
        with self.assertRaises(ValueError):
            wce.read_regions('nothing here\n')
        maps, regions = two_regions()
        placements, variants, terrain, _, _ = wce.collect(maps, regions)
        with self.assertRaises(ValueError):
            wce.build_chunks(placements, variants, terrain, (0, 0), 1000, 300)


if __name__ == '__main__':
    unittest.main()
