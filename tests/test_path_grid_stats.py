"""Path grid statistics on synthetic TES3 masters (no game data).

One interior room with a three-node grid, one exterior cell with a two-node
grid near its edge, one exterior cell with an actor and a levelled spawn but
no grid; a second master replaces the room's grid, as a later master does.
"""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import path_grid_stats as P  # noqa: E402


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def rec(tag, *subs):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, 0) + body


def name(text):
    return text.encode('cp1252') + b'\0'


def cell(cell_name, flags, x, y, refs=()):
    out = [sub('NAME', name(cell_name)), sub('DATA', struct.pack('<Iii', flags, x, y))]
    for number, ident in enumerate(refs, 1):
        out += [sub('FRMR', struct.pack('<I', number)), sub('NAME', name(ident))]
    return rec('CELL', *out)


def grid(cell_name, x, y, points, links):
    pgrp = b''.join(struct.pack('<iiiBBH', px, py, pz, 0, len(lk), 0) for (px, py, pz), lk in zip(points, links))
    pgrc = b''.join(struct.pack('<i', j) for lk in links for j in lk)
    return rec('PGRD', sub('NAME', name(cell_name)), sub('DATA', struct.pack('<iiHH', x, y, 1024, len(points))),
               sub('PGRP', pgrp), sub('PGRC', pgrc))


def actor(ident, distance=None):
    subs = [sub('NAME', name(ident))]
    if distance is not None:
        subs.append(sub('AI_W', struct.pack('<HHB8BB', distance, 5, 0, *([10] * 8), 1)))
    return rec('NPC_', *subs)


class PathGridStats(unittest.TestCase):
    def masters(self, folder):
        first = b''.join([
            actor('guard', 512), actor('statue'), rec('LEVC', sub('NAME', name('lev'))),
            cell('Room', 1, 0, 0, ['guard']),
            grid('Room', 0, 0, [(0, 0, 0), (300, 0, 0), (300, 400, 0)], [[1], [0, 2], [1]]),
            cell('', 0, 1, 2),
            grid('', 1, 2, [(100, 100, 0), (100, 4000, 0)], [[1], [0]]),
            cell('', 0, 5, 5, ['statue', 'lev']),
        ])
        second = grid('Room', 0, 0, [(0, 0, 0), (0, 2000, 0)], [[1], [0]])
        a, b = Path(folder) / 'a.esm', Path(folder) / 'b.esm'
        a.write_bytes(first); b.write_bytes(second)
        return a, b

    def test_counts_one_master(self):
        with tempfile.TemporaryDirectory() as d:
            a, _ = self.masters(d)
            r = P.measure([a])
        self.assertEqual(r['cells'], {'interior': 1, 'exterior': 2})
        self.assertEqual(r['cells_with_grid'], {'interior': 1, 'exterior': 1})
        self.assertEqual(r['all']['nodes'], 5)
        self.assertEqual(r['all']['edges'], 3)
        self.assertEqual(r['all']['directed_links'], 6)
        self.assertEqual(r['all']['one_way_links'], 0)
        self.assertEqual(r['interior']['nodes_per_grid']['max'], 3)
        self.assertEqual(r['interior']['edge_length']['max'], 400)
        self.assertEqual(r['all']['esm_bytes'], 16 * 5 + 4 * 6)
        self.assertEqual(r['all']['compact_bytes'], 7 * 5 + 2 * 3)
        self.assertEqual(r['exterior']['edges_longer_than_1024'], 1)
        # Both exterior nodes lie within 256 units of the cell's low x edge; the neighbour has no grid.
        self.assertEqual(r['exterior_borders']['border_nodes'], 2)
        self.assertEqual(r['exterior_borders']['border_nodes_facing_a_gridded_cell'], 0)
        acts = r['actors']
        self.assertEqual(acts['placed_actors'], {'interior': 1, 'exterior': 1})
        self.assertEqual(acts['cells_with_actors_but_no_grid'], {'exterior': 1})
        self.assertEqual(acts['placed_levelled_spawns'], {'interior': 0, 'exterior': 1})
        self.assertEqual(acts['levelled_spawns_in_cells_without_grid'], {'exterior': 1})
        self.assertEqual(acts['placed_ai_packages'], {'wander': 1})
        self.assertEqual(acts['placed_actors_without_package'], 1)
        self.assertEqual(acts['placed_wander_distance']['median'], 512)

    def test_later_master_replaces_grid(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = self.masters(d)
            r = P.measure([a, b])
        self.assertEqual(r['interior']['nodes'], 2)
        self.assertEqual(r['interior']['edge_length']['max'], 2000)
        self.assertEqual(r['interior']['edges_longer_than_1024'], 1)

    def test_patch_and_details_stay_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            a, _ = self.masters(d)
            plain = P.measure([a]); detailed = P.measure([a], details=True)
        self.assertNotIn('grids', plain)            # names only with --details (private use)
        self.assertEqual(detailed['grids'][0]['nodes'], 3)
        # Room nodes: within 512 units of each other (0,0)-(300,0)-(300,400): 2, 3, 2 nodes.
        self.assertEqual(plain['interior']['patch_nodes']['512']['max'], 3)

    def test_bad_point_count_refused(self):
        bad = rec('PGRD', sub('NAME', name('X')), sub('DATA', struct.pack('<iiHH', 0, 0, 1024, 2)),
                  sub('PGRP', struct.pack('<iiiBBH', 0, 0, 0, 0, 0, 0)))
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'bad.esm'; f.write_bytes(bad)
            with self.assertRaises(ValueError):
                P.measure([f])


if __name__ == '__main__':
    unittest.main()
