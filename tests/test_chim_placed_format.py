# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.8 (EXPERIMENTAL, build setting placement_format 0.8; tools/chim/placed.py): one stored model per
mesh + scale, the full rotation in a 56-byte placement record, collision from the mesh's own pieces placed at run time.

The same synthetic placements (box meshes, tilted, yawed and scaled) are built through the real CHIM units into a 0.7
world and a 0.8 world (chim.build.build_frame), then compared like for like: the drawn vertices of every placement
(the 0.7 model of its own variant turned by the record's yaw, against the shared untilted 0.8 model turned by the
record's three angles), the collision of every placement (the 0.7 variant's stored hulls traced by world.c
SV_ClipMoveToEntity, against the 0.8 piece table traced by chim_placed_clip.c ChimPlaced_TraceTable), and the bytes.
Synthetic data only.
"""
import math
import os
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
SRC = ROOT / 'engine/aga/src'

try:
    import numpy as np
except ImportError:  # pragma: no cover - the gate image has it
    np = None

# (ref, model index, frame-local origin, TES3 rotation in radians (x, y, z), scale)
REFS = [
    (21, 0, (-300.0, -300.0, 4.0), (0.0, 0.0, -math.radians(30)), 1.0),       # yaw only
    (22, 0, (-100.0, -300.0, 4.0), (0.3, 0.0, 0.0), 1.0),                       # tilt about x, no yaw
    (23, 0, (100.0, -300.0, 4.0), (0.2, -0.25, 0.0), 1.0),                      # tilt about x and y, no yaw
    (24, 0, (300.0, -300.0, 4.0), (0.4, 0.1, 1.1), 1.0),                        # tilt and yaw
    (25, 1, (-250.0, 150.0, 4.0), (0.1, 0.0, 0.7), 1.0),                        # the large box, tilt and yaw
    (26, 0, (100.0, 0.0, 4.0), (0.0, 0.35, 0.0), 1.5),                          # scaled and tilted
    (27, 2, (300.0, 0.0, 4.0), (0.0, 0.0, -math.pi / 2), 1.0),                  # the copy mesh, yaw 90
    (28, 1, (250.0, 300.0, 4.0), (0.0, 0.0, 0.0), 1.0),                         # the large box, unturned
    (29, 0, (-100.0, 300.0, 4.0), (0.2, -0.25, 0.0), 1.0),                      # the same tilt as 23 again
]


def build(out, fmt, extra=None):
    """The REFS through chim.build.build_frame (the fixture of tests/test_chim_format.py, boxes with exact collision
    bevels so the 0.7 hulls are the exact expansion of their pieces). extra: more build settings."""
    from chim.build import build_frame
    from test_chim_format import CENTRE, LOW, PALETTE, SPAN, STEP, TEXSIZE, box_prepared, height, material, \
        solid_miptex
    models = [dict(source='meshes/x/small.nif', materials=[dict(texture_index=None, diffuse=[1, 1, 1])], flames=[]),
              dict(source='meshes/x/large.nif', materials=[dict(texture_index=None, diffuse=[0.5, 1, 1])], flames=[]),
              dict(source='meshes/x/small-copy.nif', materials=[dict(texture_index=None, diffuse=[1, 1, 1])],
                   flames=[])]
    exact = lambda prepared: (*prepared[:4], {'collision_bevels': True})    # noqa: E731
    prepared = {0: exact(box_prepared(20, 40)), 1: exact(box_prepared(100, 64)), 2: exact(box_prepared(20, 40))}
    refs = [{'number': n, 'model_index': mi, 'scale': s, 'cell': [0, 0],
             'position': [CENTRE[0] + o[0] * 4, CENTRE[1] + o[1] * 4, o[2] * 4], 'rotation_radians': list(r)}
            for n, mi, o, r, s in REFS]
    xs = range(int(LOW[0]), int(LOW[0]) + SPAN[0] + 1, STEP)
    ys = range(int(LOW[1]), int(LOW[1]) + SPAN[1] + 1, STEP)
    heights = [[float(height(x, y)) for x in xs] for y in ys]
    materials = [[material(x + STEP / 2, y + STEP / 2) for x in xs[:-1]] for y in ys[:-1]]
    settings = {'grain': 256, 'sector_chunks': 2, **({'placement_format': fmt} if fmt else {}), **(extra or {})}
    return build_frame(out, frame={'cell': (0, 0), 'centre': CENTRE, 'low': LOW, 'span': SPAN}, centre=CENTRE,
                       models=models, references=refs, prepared=prepared,
                       profiles={m['source']: {'texture_size': TEXSIZE} for m in models},
                       mesh_fps={0: 'small', 1: 'large', 2: 'small-copy'}, texture_records=[], archive=None,
                       palette=PALETTE, heights=heights, materials=materials, step=STEP, floor=-1024, ceiling=2048,
                       ground_textures={'g1': solid_miptex('g1', 32, 10), 'g2': solid_miptex('g2', 32, 20),
                                        '*water': solid_miptex('*water', 64, 30)},
                       jobs=1, settings=settings)


def read_world(out):
    """(version, {ref: owned record}, {model id: brush lumps}, bytes by kind) of a written world."""
    from chim import format as F
    from chim import placed as P
    root = Path(out) / 'chim'
    index = (root / 'world.cwi').read_bytes()
    version = F.read_header(index)['version']
    _, files, models, _ = F.read_index(index)
    records, lumps, sizes = {}, {}, {'files': 0, 'MODL': 0, 'records': 0}
    blobs = {i: (root / f['path']).read_bytes() for i, f in enumerate(files)}
    sizes['files'] = sum(len(b) for b in blobs.values()) + len(index)
    for i, f in enumerate(files):
        if f['kind'] != b'SECT':
            continue
        for r in F.read_sector(blobs[i]):
            if r['kind'] == b'MODL':
                sizes['MODL'] += r['bytes']
            if r['kind'] != b'CHNK':
                continue
            chunk = P.read_chunk(r['data'])
            sizes['records'] += (len(chunk['owned']) + len(chunk['reach'])) * P.record_size(r['data'])
            for rec in chunk['owned']:
                records[rec['ref']] = rec
    for mid, m in enumerate(models):
        lumps[mid] = F.read_brush_image(blobs[m['file']][m['offset']:m['offset'] + m['bytes']])
    return version, records, lumps, sizes


def vertices(lumps):
    v = lumps[3]
    return np.array(struct.unpack('<%df' % (len(v) // 4), v), float).reshape(-1, 3)


def turned(points, origin, angles):
    from chim.placed import place_points
    return place_points(points, origin, angles)


def exact_rows(table, angles):
    """(planes, point chain, standing chain) of the pieces of a 0.8 piece table turned by the angles and expanded
    by the builder's exact Minkowski sum (prepare_mesh_bsp.standing_planes exact), as the 0.7 builder's chain:
    outside a plane goes on to the next piece, inside every plane of a piece is solid. Placement-relative."""
    from scipy.spatial import ConvexHull
    from prepare_mesh_bsp import standing_planes
    from chim.placed import model_matrix, read_piece_table
    m = model_matrix(angles)
    planes, chains = [], []
    pieces = [np.array(c, float) @ m.T for _, c, _, _ in read_piece_table(table)]
    for standing in (False, True):
        rows, first = [], len(planes)
        eqs = []
        for pts in pieces:
            eq = np.unique(np.round(ConvexHull(pts).equations, 5), axis=0)
            eqs.append(standing_planes(pts, eq, exact=True) if standing else eq)
        at = 0
        for k, eq in enumerate(eqs):
            nxt = at + len(eq) if k + 1 < len(eqs) else -1
            for j, e in enumerate(eq):
                planes.append((float(e[0]), float(e[1]), float(e[2]), float(-e[3])))
                rows.append((len(planes) - 1, nxt, at + j + 1 if j + 1 < len(eq) else -2))
            at += len(eq)
        chains.append((0, rows))
        del first
    return planes, chains[0], chains[1]


def hull_rows(lumps):
    """(planes [(n, d)], point hull (root, [(plane, child, child)]), standing hull (root, [...])) of a model image,
    children as the engine reads them (contents < 0)."""
    planes = [struct.unpack_from('<4f', lumps[1], k) for k in range(0, len(lumps[1]), 20)]
    leaves = [struct.unpack_from('<i', lumps[10], k)[0] for k in range(0, len(lumps[10]), 28)]
    nodes = []
    for k in range(0, len(lumps[5]), 24):
        p, a, b = struct.unpack_from('<ihh', lumps[5], k)
        nodes.append((p, *[c if c >= 0 else leaves[-1 - c] for c in (a, b)]))
    clips = []
    for k in range(0, len(lumps[9]), 8):
        p, a, b = struct.unpack_from('<iHH', lumps[9], k)
        clips.append((p, *[c - 65536 if c >= 32768 else c for c in (a, b)]))
    heads = struct.unpack_from('<4i', lumps[14], 36)
    return planes, (heads[0], nodes), (heads[1], clips)


@unittest.skipIf(np is None, 'numpy is required')
class PlacedFormatBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-placed-format-')
        cls.out07, cls.out08 = Path(cls.tmp.name) / 'w07', Path(cls.tmp.name) / 'w08'
        cls.receipt07 = build(cls.out07, None)
        cls.receipt08 = build(cls.out08, '0.8')
        cls.w07 = read_world(cls.out07)
        cls.w08 = read_world(cls.out08)
        # the large-model cut by tiles (cut_models_over, chim.cut): the 0.8 tiles of the untilted model
        cls.out07t, cls.out08t = Path(cls.tmp.name) / 'w07t', Path(cls.tmp.name) / 'w08t'
        build(cls.out07t, None, {'cut_models_over': 128})
        build(cls.out08t, '0.8', {'cut_models_over': 128})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_default_writes_the_old_format(self):
        version, records, _, sizes = self.w07
        self.assertEqual(version, (0, 5))
        self.assertTrue(all('angles' not in r for r in records.values()))
        self.assertEqual(sizes['records'] % 48, 0)

    def test_08_world_validates(self):
        from chim.validate import validate
        for out in (self.out07, self.out08, self.out07t, self.out08t):
            fails, _ = validate(out)
            self.assertEqual(list(fails), [], out.name)

    def test_08_records_and_models(self):
        from prepare_scenery import reference_rotation
        from chim.placed import model_matrix
        version, records, models, sizes = self.w08
        self.assertEqual(version, (0, 8))
        self.assertEqual(sizes['records'] % 56, 0)
        for n, mi, o, rot, s in REFS:
            r = records[n]
            want = reference_rotation({'rotation_radians': list(rot)})
            self.assertLess(float(np.abs(model_matrix(r['angles']) - want).max()), 1e-5, n)
            # a yaw-only record keeps the 0.7 record's yaw exactly
            if not (rot[0] or rot[1]):
                self.assertEqual(r['angles'][0], 0.0)
                self.assertEqual(r['angles'][2], 0.0)
                self.assertEqual(r['angles'][1], self.w07[1][n]['yaw'])
        # one model per mesh + scale: small at 1 and 1.5, large; small-copy has small's bytes (stored once)
        self.assertEqual(len({records[n]['model'] for n, *_ in REFS}), 3)
        self.assertLess(len(models), len(self.w07[2]))
        # every 0.8 model carries its piece table
        from chim.placed import read_piece_table, table_usable
        for mid in {records[n]['model'] for n, *_ in REFS}:
            self.assertTrue(table_usable(bytes(models[mid][4])))
            self.assertEqual(len(read_piece_table(bytes(models[mid][4]))), 1)

    def test_08_draws_what_07_draws(self):
        """Every placement's drawn vertices: the 0.7 variant turned by the yaw against the shared 0.8 model turned
        by the three angles (both as the records store them)."""
        _, r07, m07, _ = self.w07
        _, r08, m08, _ = self.w08
        worst = 0.0
        for n, *_ in REFS:
            a, b = r07[n], r08[n]
            pa = turned(vertices(m07[a['model']]), a['origin'], (0.0, a['yaw'], 0.0))
            pb = turned(vertices(m08[b['model']]), b['origin'], b['angles'])
            self.assertEqual(len(pa), len(pb), n)
            d = np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=2)
            worst = max(worst, float(d.min(axis=1).max()), float(d.min(axis=0).max()))
            # the drawn box (efrags, broadphase): 0.8 turns the untilted model's bounds, so it holds every vertex
            # but is looser than 0.7's box of the tilted model by up to the turn of a corner
            lo, hi = np.array(b['box'][0], float), np.array(b['box'][1], float)
            self.assertTrue(((pb >= lo - 1e-3) & (pb <= hi + 1e-3)).all(), n)
        self.assertLess(worst, 0.02)

    def test_08_tiles(self):
        """Tiled large models (cut_models_over): every 0.8 tile record turns with the placement's angles and its
        model carries a usable piece table; the tiles of the 0.7 tilted variant and of the 0.8 untilted model are
        cut along other lines, so their counts may differ."""
        from chim.cut import source_ref
        from chim.placed import table_usable
        _, r07, m07, _ = read_world(self.out07t)
        version, r08, m08, _ = read_world(self.out08t)
        self.assertEqual(version, (0, 8))
        tiled = [r for r in r08.values() if r['ref'] >> 24]
        self.assertTrue(tiled)
        for r in tiled:
            n = source_ref(r['ref'])
            whole = next(x for x in REFS if x[0] == n)
            self.assertEqual(whole[1], 1)                    # only the large box is cut
            self.assertTrue(table_usable(bytes(m08[r['model']][4])))
            self.assertEqual(r['angles'], self.w08[1][n]['angles'])
        self.assertEqual({source_ref(r['ref']) for r in tiled}, {source_ref(r['ref']) for r in r07.values() if r['ref'] >> 24})

    def test_08_bytes(self):
        s07, s08 = self.w07[3], self.w08[3]
        n = len(self.w08[1])
        self.assertEqual(s08['records'] - s07['records'], 8 * (s08['records'] // 56))
        self.assertLess(s08['MODL'], s07['MODL'])
        if os.environ.get('AW_PLACED_FORMAT_REPORT'):
            Path(os.environ['AW_PLACED_FORMAT_REPORT']).write_text(
                'placements %d\n0.7 files %d MODL %d records %d models %d\n0.8 files %d MODL %d records %d models %d\n'
                % (n, s07['files'], s07['MODL'], s07['records'], len(self.w07[2]), s08['files'], s08['MODL'],
                   s08['records'], len(self.w08[2])), encoding='ascii', newline='\n')

    def test_option_refusals(self):
        from chim.placed import placement_format
        self.assertEqual(placement_format({}), '0.7')
        self.assertEqual(placement_format({'placement_format': '0.8'}), '0.8')
        with self.assertRaises(ValueError):
            placement_format({'placement_format': '0.9'})
        with tempfile.TemporaryDirectory() as tmp:
            from test_chim_format import fixture
            for bad in ({'cut_mode': 'partition', 'cut_models_over': 128}, {'model_bevels': 'tol:2'}):
                with self.assertRaises(ValueError):
                    fixture(Path(tmp) / 'x', settings={'grain': 256, 'sector_chunks': 2, 'placement_format': '0.8',
                                                        **bad})

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_08_collides_as_07_traces_it(self):
        """Point traces agree on every placement; box traces agree where the 0.7 record has no yaw. With a yaw, 0.7
        turns the player box with the model (CHIM-YAW-PLAYER-BOX-TURNS-46) and 0.8 keeps it world-aligned: those
        differ by that finding, counted, not asserted."""
        from test_aga_native_source import NativeSourceTests
        from test_chim_engine_native import WARN
        _, r07, m07, _ = self.w07
        _, r08, m08, _ = self.w08
        rng = np.random.default_rng(47)
        lines = []
        for n, *_ in REFS:
            a, b = r07[n], r08[n]
            table = bytes(m08[b['model']][4])
            pts = turned(vertices(m08[b['model']]), b['origin'], b['angles'])
            lo, hi = pts.min(axis=0) - 25, pts.max(axis=0) + 25
            traces = []
            r = lambda: lo + rng.random(3) * (hi - lo)        # noqa: E731
            for _ in range(120):
                traces.append((0, r(), r()))
            for _ in range(60):
                p = r()
                q = p.copy()
                p[2], q[2] = hi[2], lo[2]
                traces.append((0, p, q))
            for _ in range(60):
                p = r()
                t = rng.random() * 2 * math.pi
                traces.append((0, p, p + 40 * np.array([math.cos(t), math.sin(t), 0])))
            for _ in range(60):
                traces.append((1, r(), r()))
            lines.append('r%d %.7f %.6f %.6f %.6f %.6f %.6f %.6f %.7f %.7f %.7f' % (
                n, a['yaw'], *a['origin'], *b['origin'], *b['angles']))
            for planes, (root0, nodes), (root1, clips) in (hull_rows(m07[a['model']]), exact_rows(table, b['angles'])):
                lines.append(str(len(planes)))
                lines += ['%.8f %.8f %.8f %.8f' % p[:4] for p in planes]
                lines.append('%d %d' % (root0, len(nodes)))
                lines += ['%d %d %d' % x for x in nodes]
                lines.append('%d %d' % (root1, len(clips)))
                lines += ['%d %d %d' % x for x in clips]
            lines.append('%d %s' % (len(table), table.hex()))
            lines.append(str(len(traces)))
            lines += ['%d %.5f %.5f %.5f %.5f %.5f %.5f' % (k, *p, *q) for k, p, q in traces]
        with tempfile.TemporaryDirectory(prefix='amiwind-placed-format-c-') as tmp:
            cases, out = Path(tmp) / 'cases.txt', Path(tmp) / 'out.txt'
            cases.write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')
            NativeSourceTests.compile_run(
                self, 'aga_chim_placed_format_test.c',
                [SRC / 'world.c', SRC / 'mathlib.c', SRC / 'chim/chim_placed_clip.c', SRC / 'chim/chim_format.c'],
                cflags=[*WARN, '-O1'], arguments=[str(cases), str(out)])
            text = out.read_text(encoding='ascii')
        if os.environ.get('AW_PLACED_FORMAT_CLIP_REPORT'):
            Path(os.environ['AW_PLACED_FORMAT_CLIP_REPORT']).write_text(text, encoding='ascii', newline='\n')
        rows = {}
        for line in text.splitlines():
            if line and not line.startswith('#'):
                w = line.split()
                rows[w[0]] = {w[k]: float(w[k + 1]) for k in range(1, len(w) - 1, 2)}
        self.assertEqual(len(rows), len(REFS))
        for n, mi, o, rot, s in REFS:
            row = rows['r%d' % n]
            with self.subTest(ref=n):
                self.assertEqual(row['usable'], 1)
                # the placed method is the exact expansion of the turned pieces on every trace
                self.assertEqual(row['exact_solid_diff'], 0)
                self.assertEqual(row['exact_match'], row['point'] + row['box'])
                self.assertEqual(row['point_solid_diff'], 0)
                self.assertEqual(row['point_match'], row['point'])
                if abs(r07[n]['yaw']) < 1e-9:
                    self.assertEqual(row['box_solid_diff'], 0)
                    self.assertEqual(row['box_match'], row['box'])


class PlacedFormatKeyTests(unittest.TestCase):
    def test_default_kinds_never_reach_the_08_module(self):
        """The 0.8 units have their own kinds; the default kinds' code never reaches chim.placed (their cache keys
        stay as they were)."""
        from chim import units
        for kind in ('variant', 'tiles', 'cut', 'terrain', 'texture', 'mesh', 'ocean', 'pvs'):
            self.assertNotIn('tools/chim/placed.py', units.TOOLS.get(kind, []), kind)
            reach = units.unit_code_key(kind)
            self.assertFalse(any('chim/placed.py' in str(u) for u in reach.get('units', reach.get('reach', []))),
                             kind)
        self.assertEqual(units.CODE_ENTRIES['variant-placed'], [('tools/chim/placed.py', 'variant_unit_placed')])
        self.assertEqual(units.CODE_ENTRIES['tiles-placed'], [('tools/chim/placed.py', 'tile_unit_placed')])


if __name__ == '__main__':
    unittest.main()
