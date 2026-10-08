"""Streamed BSP lumps decode from bounded slices into the same structures.

Synthetic BSP29 maps (no game data) are loaded through the actual engine
Mod_LoadBrushModel twice: from a complete in-memory file image (Quake's own
path) and streamed from the file in 16 KiB slices, with and without a partial
prefetch cache and with music-paced 4 KiB reads. File reads are the staged
loader's: 16 KiB chunks from each lump's start. The decoded Hunk and every
model slot must be byte-identical; the streamed peak may exceed the decoded
map by one slice only. Lumps larger than a slice, all three node layouts
(certified prefix, generic, failed certification) and malformed input are
covered.
"""
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
SLICE = 16384
PREFIX = 2064  # the texture lump spans windows: its directory prefix is the largest


def synthetic_bsp(layout, seed=7):
    """A structurally valid BSP29 whose large lumps each span several slices."""
    rnd = random.Random(seed)
    nvert, nedge, nface, nplane, ntexinfo = 4000, 5000, 3000, 1500, 600
    nleaf, nmark, nworld, ninline, nclip = 800, 9000, 900, 30, 3000
    planes = b''.join(struct.pack('<4fi', *((1.0, 0.0, 0.0) if i % 3 == 0 else
                                           (0.0, 1.0, 0.0) if i % 3 == 1 else (0.0, 0.0, -1.0)),
                                  float(i % 200), i % 3) for i in range(nplane))
    vertexes = b''.join(struct.pack('<3f', rnd.uniform(0, 200), rnd.uniform(0, 200), rnd.uniform(0, 200))
                        for _ in range(nvert))
    edges = struct.pack('<2H', 0, 0) + b''.join(
        struct.pack('<2H', rnd.randrange(nvert), rnd.randrange(nvert)) for _ in range(nedge - 1))
    surfedges = b''.join(struct.pack('<i', rnd.randrange(1, nedge) * rnd.choice((1, -1)))
                         for _ in range(nface * 3))
    names = [b'wall', b'sky1', b'+0lava', b'+1lava', None, b'*water', b'bigwall']
    directory, payload = [], b''
    base = 4 + 4 * len(names)
    for k, name in enumerate(names):
        if name is None:
            directory.append(-1)
            continue
        width, height = (32, 16) if name == b'sky1' else (128, 128) if name == b'bigwall' else (16, 16)
        pixels = width * height // 64 * 85
        directory.append(base + len(payload))
        offsets = (40, 40 + width * height, 40 + width * height * 5 // 4, 40 + width * height * 21 // 16)
        payload += name.ljust(16, b'\0') + struct.pack('<2I4I', width, height, *offsets)
        payload += bytes((k * 37 + i) & 255 for i in range(pixels))
    textures = struct.pack('<i', len(names)) + b''.join(struct.pack('<i', d) for d in directory) + payload
    texinfo = b''
    for i in range(ntexinfo):
        miptex = i % len(names)
        s, t = ((1, 0, 0), (0, 1, 0)) if i % 2 else ((0, 1, 0), (0, 0, 1))
        texinfo += struct.pack('<8f2i', *s, float(i % 16), *t, 0.0, miptex, 0)
    lighting = bytes(rnd.randrange(256) for _ in range(30000))
    faces = b''
    for i in range(nface):
        light = -1 if i % 5 == 0 else rnd.randrange(0, 20000)
        faces += struct.pack('<hhihh4Bi', rnd.randrange(nplane), i & 1, i * 3, 3,
                             rnd.randrange(ntexinfo), 0, 255, 255, 255, light)
    marks = b''.join(struct.pack('<H', rnd.randrange(nface)) for _ in range(nmark))
    visibility = bytes(rnd.randrange(256) for _ in range(20000))
    leafs = struct.pack('<ii6hHH4B', -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    for i in range(1, nleaf):
        first = rnd.randrange(nmark - 20)
        leafs += struct.pack('<ii6hHH4B', -1, rnd.randrange(19000), -8, -8, -8, 8, 8, 8,
                             first, rnd.randrange(20), 1, 2, 3, 4)
    world_faces = nface - 2 * ninline
    nodes = b''
    for i in range(nworld):
        kids = [2 * i + 1, 2 * i + 2]
        kids = [k if k < nworld else -1 - rnd.randrange(1, nleaf) for k in kids]
        first = rnd.randrange(world_faces - 4)
        nodes += struct.pack('<i2h6h2H', rnd.randrange(nplane), *kids, -8, -8, -8, 8, 8, 8, first, 3)
    tail = ninline + (1 if layout == 'orphan' else 0)
    for i in range(tail):
        kids = (-1 - rnd.randrange(1, nleaf), -1)
        nodes += struct.pack('<i2h6h2H', rnd.randrange(nplane), *kids, -4, -4, -4, 4, 4, 4, 0, 0)
    clipnodes = b''
    for i in range(nclip):
        kids = [i + 1 if i + 1 < nclip and i % 7 else -1, -2]
        clipnodes += struct.pack('<i2h', rnd.randrange(nplane), *kids)
    models = struct.pack('<9f7i', 0, 0, 0, 200, 200, 200, 0, 0, 0, 0, 0, 0, 0, nleaf - 1, 0, world_faces)
    for i in range(ninline):
        root = 0 if layout == 'generic' else nworld + i
        models += struct.pack('<9f7i', -4, -4, -4, 4, 4, 4, 10.0 * i, 0, 0,
                              root, rnd.randrange(nclip), -1, 0, 0, world_faces + 2 * i, 2)
    entities = (b'{\n"classname" "worldspawn"\n}\n' * 200) + b'\0'
    lumps = [entities, planes, textures, vertexes, visibility, nodes, texinfo, faces,
             lighting, clipnodes, leafs, marks, edges, surfedges, models]
    header, body, offset = struct.pack('<i', 29), b'', 4 + 15 * 8
    for lump in lumps:
        header += struct.pack('<ii', offset, len(lump))
        body += lump
        offset += len(lump)
    return header + body


@unittest.skipIf(os.name == 'nt', 'Owner workflow: no generated Windows test executables; run this native oracle on Linux')
@unittest.skipUnless(COMPILER, 'install a host C compiler or set CC')
class SliceLoadTests(unittest.TestCase):
    def test_lumps_span_several_slices(self):
        data = synthetic_bsp('prefix')
        lengths = [struct.unpack_from('<ii', data, 4 + 8 * i)[1] for i in range(15)]
        for index in (1, 2, 3, 5, 7, 11, 12, 13):
            self.assertGreater(lengths[index], SLICE)

    def test_streamed_slices_match_file_image_and_bound_the_peak(self):
        # A deliberately long temp path: the harness must pass short relative names, because
        # Quake model names are 64 bytes (TEST-NATIVE-TMPDIR-32).
        with tempfile.TemporaryDirectory(prefix='amiwind-slice-load-' + 'long-temp-path-' * 5) as temp:
            temp = Path(temp)
            exe = temp / 'slices'
            command = [COMPILER, '-std=gnu89', '-O2', '-Wall', '-Werror', '-Wno-unused-function',
                       '-Wno-unused-variable', '-Wno-unused-but-set-variable', '-fwhole-program',
                       '-DAW_TEST_WRAP_FREAD', '-Wl,--wrap=fread',
                       '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
                       '-I' + str(ROOT / 'engine/aga/src'),
                       str(ROOT / 'tests/aga_bsp_slice_load_test.c'), '-lm', '-o', str(exe)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            paths = []
            for layout in ('prefix', 'generic', 'orphan'):
                path = temp / (layout + '.bsp')
                path.write_bytes(synthetic_bsp(layout))
                paths.append(path.name)
            self.assertGreater(len(str(temp / paths[0])), 63)
            result = subprocess.run([str(exe), 'check', *paths], cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = {Path(line.split()[0]).stem: dict(field.split('=') for field in line.split()[1:])
                    for line in result.stdout.splitlines()}
            self.assertEqual(set(rows), {'prefix', 'generic', 'orphan'})
            self.assertEqual(rows['prefix']['direct_hull0'], '1')
            self.assertEqual(rows['generic']['direct_hull0'], '0')
            self.assertEqual(rows['orphan']['direct_hull0'], '0')
            for name, row in rows.items():
                with self.subTest(map=name):
                    self.assertEqual(int(row['slice']), PREFIX + SLICE)
                    self.assertEqual(row['sky'], '1')
                    # The old staged loader held the largest lump beside the map.
                    self.assertGreater(int(row['largest_staged_lump']), 3 * SLICE)
                    self.assertLessEqual(int(row['stream_peak']), int(row['low']) + 16 + PREFIX + SLICE)
                    self.assertLessEqual(int(row['stream_peak']), int(row['low']) + 16 + int(row['slice']))


if __name__ == '__main__':
    unittest.main()
