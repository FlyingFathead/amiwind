# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-HULL-CHAIN-COST-33: a placed model with many convex pieces gets a routed standing hull. It
classifies every point like the one chain of all pieces (the legacy form, still selectable), and a
point test visits far fewer clipnodes."""
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.models import MODEL_ROUTE_PIECES, model_image_lumps  # noqa: E402


def boxes(n):
    """n box pieces in a row-and-column pattern, as a large canton body's convex parts."""
    out = []
    for k in range(n):
        x, y = (k % 8) * 40.0, (k // 8) * 40.0
        lo, hi = (x, y, 0.0), (x + 30.0, y + 30.0, 20.0 + (k % 3) * 10)
        pts = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
        out.append((pts, None, [], 0.))
    return out


def walk(lumps, root, p):
    """Contents and clipnodes visited, as SV_HullPointContents walks them."""
    planes, clips = lumps[1], lumps[9]
    num, visits = root, 0
    while num >= 0:
        visits += 1
        pi, front, back = struct.unpack_from('<iHH', clips, 8 * num)
        n0, n1, n2, dist = struct.unpack_from('<4f', planes, 20 * pi)
        child = front if n0 * p[0] + n1 * p[1] + n2 * p[2] - dist >= 0 else back
        num = child - 65536 if child >= 0xFFF0 else child
    return num, visits


class ModelHullTests(unittest.TestCase):
    def build(self, hull, n=40):
        parts = boxes(n)
        lo = np.min([p for p, *_ in parts], axis=0).min(axis=0)
        hi = np.max([p for p, *_ in parts], axis=0).max(axis=0)
        lumps = [bytes(x) for x in model_image_lumps([], parts, lo, hi, lambda m: 0, False, None, b'', hull)[0]]
        root = struct.unpack_from('<9f7i', lumps[14])[10]
        return lumps, root

    def test_routed_hull_classifies_like_the_chain_with_fewer_visits(self):
        chain, croot = self.build('chain')
        routed, rroot = self.build('routed')
        rnd = np.random.default_rng(11)
        chain_visits = routed_visits = 0
        for p in rnd.uniform((-30, -30, -30), (350, 230, 70), (3000, 3)):
            a, va = walk(chain, croot, p)
            b, vb = walk(routed, rroot, p)
            self.assertEqual(a, b, p)
            chain_visits += va
            routed_visits += vb
        self.assertLess(routed_visits * 3, chain_visits)

    def test_auto_routes_only_large_models(self):
        # BUILD-CHIM-HULL-RING-33: a house-size model's hull is the chain, byte for byte (every byte of it is
        # in each ring that holds the model; Balmora's south-west ring has 2,528 B of headroom)
        self.assertEqual(MODEL_ROUTE_PIECES, 256)
        self.assertEqual(self.build('auto', 60)[0], self.build('chain', 60)[0])
        small = self.build('auto', MODEL_ROUTE_PIECES)[0]
        self.assertEqual(small, self.build('chain', MODEL_ROUTE_PIECES)[0])
        self.assertNotEqual(self.build('auto', MODEL_ROUTE_PIECES + 1)[0],
                            self.build('chain', MODEL_ROUTE_PIECES + 1)[0])


if __name__ == '__main__':
    unittest.main()
