# SPDX-License-Identifier: GPL-3.0-only
"""CHIM placement-visibility units keyed in the frame's own numbering (BUILD-CHIM-VIS-RECOMPUTED-48).

Placement ids run on across the frames of a world, so one placement more in an earlier frame renumbered every later
frame; keyed by those ids, every placement-visibility unit of the island was computed again (the v0.0.48-dev2 try 5
build spent 1 h 20 min in visibility rows). Synthetic frame only."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

from chim import units as U  # noqa: E402
from chim.world import World, chunk_visibility  # noqa: E402

GRAIN = 256
SPAN = 2048.0


def wall(x0, y0, x1, y1, z1):
    return np.array([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (0.0, z1)], float)


def frame(base):
    """(world, terrain, by_chunk, variants, visibility) of an 8 x 8 chunk frame whose placement ids start at BASE."""
    world = World({'cell': (0, 0), 'centre': (SPAN / 2, SPAN / 2), 'low': (0.0, 0.0), 'span': (SPAN, SPAN)},
                  {'grain': GRAIN, 'sector_chunks': 2})
    variants = {'post': {'lo': [-8.0, -8.0, 0.0], 'hi': [8.0, 8.0, 96.0], 'occluders': []},
                'wall': {'lo': [-16.0, -600.0, 0.0], 'hi': [16.0, 600.0, 400.0],
                         'occluders': [wall(-16.0, -600.0, 16.0, 600.0, 400.0)]}}
    rows = [('wall', (1024.0, 1024.0))] + [('post', (x + 40.0, y + 40.0)) for x in range(0, 2048, 384)
                                            for y in range(0, 2048, 512)]
    by_chunk = {c: {'owned': [], 'reach': []} for c in world.order}
    placed = []
    for ref, (variant, (x, y)) in enumerate(rows):
        v = variants[variant]
        box = ((int(x + v['lo'][0]) - 1, int(y + v['lo'][1]) - 1, -1), (int(x + v['hi'][0]) + 1, int(y + v['hi'][1]) + 1,
                                                                         int(v['hi'][2]) + 1))
        p = {'ref': ref, 'variant': variant, 'origin': (x, y, 0.0), 'yaw': 0.0, '_box': box,
             '_owner': world.chunk_of(x, y), '_touched': world.touched(*box) | {world.chunk_of(x, y)}}
        by_chunk[p['_owner']]['owned'].append(p)
        placed.append(p)
    pid = base
    for c in world.order:
        for p in sorted(by_chunk[c]['owned'], key=lambda q: q['ref']):
            p['_pid'] = pid
            pid += 1
            for t in sorted(p['_touched'] - {c}):
                by_chunk[t]['reach'].append(p)
    terrain = {c: {'info': {'zmax': 0.0}} for c in world.order}
    visibility = {'heights': np.zeros((33, 33)), 'step': 64.0, 'low': (0.0, 0.0)}
    return world, terrain, by_chunk, variants, visibility


def visible(base, cache):
    world, terrain, by_chunk, variants, visibility = frame(base)
    return chunk_visibility(world, terrain, by_chunk, variants, visibility, jobs=1, cache=cache)


class PlacementVisibilityKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_renumbered_frame_reuses_every_visibility_unit(self):
        cache = U.UnitCache(self.temp.name)
        chunks, pvl, stats = visible(0, cache)
        self.assertGreater(stats['placements_blocked'], 0)          # the wall hides some posts
        self.assertGreater(cache.stats['pvs']['built'], 0)
        cache.stats = {}
        chunks2, pvl2, _ = visible(500, cache)                      # an earlier frame grew: ids start 500 later
        self.assertEqual(cache.stats['pvs'].get('built', 0), 0, cache.stats)
        self.assertEqual(chunks2, chunks)
        self.assertEqual(pvl2, {c: {p + 500 for p in ids} for c, ids in pvl.items()})
        fresh, _, _ = visible(500, U.UnitCache(Path(self.temp.name) / 'fresh'))
        self.assertEqual(visible(500, None)[1], pvl2)                # the same rows computed without a cache
        self.assertEqual(fresh, chunks2)

    def test_units_keyed_before_are_reused_once(self):
        # the units the earlier key form stored (frame-wide ids) are found, renumbered and stored in the new form
        cache = U.UnitCache(self.temp.name)
        real, keys = U.fingerprint, []

        def spy(kind, *parts):
            key = real(kind, *parts)
            if parts and isinstance(parts[0], str) and parts[0] in ('placements', 'placements local'):
                keys.append((parts[0], key))
            return key
        with patch.object(U, 'fingerprint', spy):
            _, pvl, _ = visible(7, cache)
        new = [key for label, key in keys if label == 'placements local']
        old = [key for label, key in keys if label == 'placements']
        self.assertEqual(len(new), len(old))
        for n, o in zip(new, old):
            value = cache.get('pvs', n)
            cache.put('pvs', o, {'visible': {k: [p + 7 for p in v] for k, v in value['visible'].items()},
                                 'stats': value['stats']})
            cache._path('pvs', n).unlink()
        cache.stats = {}
        _, again, _ = visible(7, cache)
        self.assertEqual(again, pvl)
        self.assertEqual(cache.stats['pvs'].get('built', 0), 0, cache.stats)
        self.assertEqual(cache.stats['pvs']['reused_earlier_key'], len(new))
        self.assertTrue(all(cache._path('pvs', n).is_file() for n in new))


if __name__ == '__main__':
    unittest.main()
