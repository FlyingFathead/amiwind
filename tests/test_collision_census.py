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
