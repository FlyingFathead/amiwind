# SPDX-License-Identifier: GPL-3.0-only
"""Collision census (tools/collision_census.py): drawing / collision split of a brush image, the ratio, the warning,
the size ledger entry and the build summary section; the Toolkit's JavaScript reader gives the same figures.
Synthetic brush images only."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_digest  # noqa: E402
import collision_census as C  # noqa: E402
from chim import format as F  # noqa: E402


def image(clipnodes=2, pieces=5):
    """One face on plane 0, one node on plane 1, CLIPNODES clipnodes on plane 2 (a chain from hull 1), and a piece
    table of PIECES pieces."""
    lumps = [b''] * 15
    lumps[1] = b''.join(struct.pack('<4fi', 0, 0, 1, 0, 0) for _ in range(3))
    lumps[7] = struct.pack('<Hhihh4Bi', 0, 0, 0, 4, 0, 0, 0, 0, 0, -1)
    lumps[5] = struct.pack('<ihh6hHH', 1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0)
    lumps[9] = b''.join(struct.pack('<ihh', 2, i + 1 if i + 1 < clipnodes else -1, -2) for i in range(clipnodes))
    lumps[4] = b'PCS1' + struct.pack('>III', pieces, 16, 0) + bytes(36 * pieces)
    lumps[14] = struct.pack('<9f4i3i', *([0.0] * 9), 0, 0, -1, -1, 0, 0, 1)
    return F.brush_image(lumps)[0]


class Stats(unittest.TestCase):
    def test_split(self):
        data = image()
        s = C.model_stats(data)
        self.assertEqual((s['faces'], s['triangles'], s['planes'], s['clipnodes'], s['pieces']), (1, 2, 3, 2, 5))
        self.assertEqual((s['face_planes'], s['node_planes'], s['clip_only_planes']), (1, 1, 1))
        self.assertEqual((s['hull1_clipnodes'], s['deepest_chain']), (2, 2))
        self.assertEqual(s['collision_bytes'], 16 + 16 + 36 * 5 + 20)
        self.assertEqual(s['draw_bytes'] + s['collision_bytes'], len(data))
        self.assertAlmostEqual(s['ratio_bytes'], round(s['collision_bytes'] / s['draw_bytes'], 3))
        self.assertEqual(s['ratio_counts'], 7.0)

    def test_warning_needs_ratio_and_bytes(self):
        heavy = {'name': 'a', 'store': 'rooms', 'ratio_bytes': C.WARN_RATIO + 1, 'collision_bytes': C.WARN_MIN_BYTES,
                 'draw_bytes': 1, 'faces': 1, 'clipnodes': 1, 'pieces': 1}
        small = dict(heavy, name='b', collision_bytes=C.WARN_MIN_BYTES - 1)
        low = dict(heavy, name='c', ratio_bytes=C.WARN_RATIO)
        self.assertEqual([r['name'] for r in C.warnings([heavy, small, low])], ['a'])
        self.assertTrue(C.warning_line(heavy).startswith('WARNING: collision-heavy model a'))

    def test_shape_warning_on_chain_or_counts(self):
        base = {'store': 'rooms', 'faces': 10, 'clipnodes': 20, 'pieces': 1, 'deepest_chain': C.WARN_CHAIN,
                'ratio_counts': C.WARN_COUNTS}
        deep = dict(base, name='deep', deepest_chain=C.WARN_CHAIN + 1)
        dense = dict(base, name='dense', ratio_counts=C.WARN_COUNTS + 0.5)
        fine = dict(base, name='fine')
        bare = dict(base, name='bare', ratio_counts=None)
        warned = C.shape_warnings([fine, dense, deep, bare])
        self.assertEqual([r['name'] for r in warned], ['deep', 'dense'])
        lines = C.shape_summary(warned, shown=1)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('WARNING: 2 model(s)'))
        self.assertIn('collision shape deep', lines[1])
        self.assertEqual(C.shape_summary([]), [])
        # a chain image over the limit warns by its deepest chain
        s = dict(C.model_stats(image(clipnodes=C.WARN_CHAIN + 1)), name='m', store='rooms')
        self.assertEqual([r['name'] for r in C.shape_warnings([s])], ['m'])

    def test_unsigned_children_long_chain(self):
        n = 33000
        lumps = [b''] * 15
        lumps[1] = struct.pack('<4fi', 0, 0, 1, 0, 0)
        lumps[9] = b''.join(struct.pack('<iHH', 0, i + 1 if i + 1 < n else 0xFFFF, 0xFFFE) for i in range(n))
        lumps[14] = struct.pack('<9f4i3i', *([0.0] * 9), 0, 0, -1, -1, 0, 0, 0)
        s = C.model_stats(F.brush_image(lumps)[0])
        self.assertEqual(s['deepest_chain'], n)

    def test_collision_sources(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'scenery'
            p.mkdir()
            (p / 'scenery-index.json').write_text(json.dumps({
                'groups': {'g': {'visual_profiles': {'meshes/x/ex_a.nif': {'ratio': 0.5}}}},
                'models': [{'source': 'meshes/x/ex_a.nif'},
                           {'source': 'meshes/i/in_b.nif', 'collision': {'source': 'NIF RootCollisionNode'}}]}))
            src = C.collision_sources(Path(d))
        self.assertEqual(src, {'ex_a': ('visual', True), 'in_b': ('rcn', False)})
        rows = [{'name': 'x/ex_a@s1', 'collision_bytes': 5, 'draw_bytes': 9},
                {'name': 'i/in_b@s1@tile0,1#2', 'collision_bytes': 3, 'draw_bytes': 4},
                {'name': 'o/other@s1', 'collision_bytes': 1, 'draw_bytes': 1}]
        total = C.source_summary(rows, src)
        self.assertEqual(sorted(total), ['rcn/full', 'unknown', 'visual/reduced'])
        self.assertTrue(rows[0]['drawn_reduced'])

    def test_no_store_no_entry(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(C.ledger_entry(Path(d)))
            with self.assertRaises(SystemExit):
                C.census(Path(d))

    def test_markdown_and_summary(self):
        rows = []
        for i, n in enumerate((2, 40, 8)):
            r = dict(C.model_stats(image(clipnodes=n)), id=i, name='m%d' % i, file='p', store='rooms')
            rows.append(r)
        rows.sort(key=lambda r: -r['ratio_bytes'])
        record = {'folder': 'run', 'threshold': {'ratio_bytes': C.WARN_RATIO, 'min_collision_bytes': C.WARN_MIN_BYTES},
                  'total': {'draw_bytes': 1, 'collision_bytes': 2, 'ratio_bytes': 2.0},
                  'spread': {'models': 3, 'median': 1, 'p90': 1, 'p99': 1, 'max': 1}, 'warned': [], 'models': rows}
        md = C.markdown(record)
        self.assertIn('| 1 | m1 |', md)
        top = C.top_rows(record, 2)
        self.assertEqual([r['name'] for r in top], ['m1', 'm2'])
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'size-ledger.json').write_text(json.dumps({'collision': {
                'top': top, 'total': record['total'], 'warned': ['m1'], 'threshold': record['threshold']}}))
            rec = build_digest.digest(Path(d), receipt={})
            page = build_digest.markdown(rec)
        self.assertIn('## Collision-heavy models', page)
        self.assertIn('| m1 |', page)
        self.assertIn('collision-heavy', [a['key'] for a in rec['needs_attention']])


@unittest.skipUnless(shutil.which('node'), 'node not available')
class JavaScriptReader(unittest.TestCase):
    def test_same_figures(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'm.img'
            f.write_bytes(image(clipnodes=6, pieces=3))
            js = ("const R=require(%s);const fs=require('fs');"
                  "process.stdout.write(JSON.stringify(R.collisionStats(new Uint8Array(fs.readFileSync(%s)))))"
                  % (json.dumps(str(ROOT / 'amiwind-toolkit' / 'chim-reader.js')), json.dumps(str(f))))
            out = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout), C.model_stats(f.read_bytes()))


if __name__ == '__main__':
    unittest.main()
