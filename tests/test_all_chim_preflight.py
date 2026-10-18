# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43: a world whose every open-world cell is a CHIM region frame (no legacy map
left) passes the payload preflight's disk layout with the frame maps in the plan, and the partition refusals
name their unit and numbers."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import payload_preflight
from world_volumes import PAYLOAD_LIMIT, PlannedMap, balanced, map_bytes, partition_batches, plan_partitions


ENGINE = 1 << 20        # a boot payload over half the payload: the boot partition keeps no world map


def awr_bytes(count):
    return 64 + 52 * count


def region_directory(path, count):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'AWR2' + struct.pack('<I', count) + bytes(56) + bytes(52 * count))


def files(root, sizes):
    out = []
    for i, size in enumerate(sizes):
        p = root / ('vf%04d.bsp' % i)
        p.write_bytes(b'x' * size)
        out.append(p)
    return out


class PartitionPlannedMapsTests(unittest.TestCase):
    def test_planned_maps_partition_like_files_of_the_same_size(self):
        sizes = [30, 10, 50, 20, 40, 30]
        with tempfile.TemporaryDirectory() as directory:
            real = files(Path(directory), sizes)
            planned = [PlannedMap(p.name, p.stat().st_size, bound=True) for p in real]
            for boot, limit in ((20, 200), (40, 100), (90, 100)):
                a_kept, a_batches = partition_batches(real, boot, limit)
                b_kept, b_batches = partition_batches(planned, boot, limit)
                self.assertEqual([p.name for p in a_kept], [p.name for p in b_kept])
                self.assertEqual([[p.name for p in b] for b in a_batches], [[p.name for p in b] for b in b_batches])
                self.assertEqual(plan_partitions(a_batches), plan_partitions(b_batches))
            self.assertEqual([p.name for p in balanced(real, 20, 200)[0]], [p.name for p in balanced(planned, 20, 200)[0]])

    def test_mixed_files_and_planned_maps_sort_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            real = files(Path(directory), [10, 10])
            mixed = [PlannedMap('vf0005.chim', 50, bound=True), real[1], real[0]]
            kept, batches = partition_batches(mixed, 0, 100)
            self.assertEqual([p.name for p in kept + [m for b in batches for m in b]],
                             ['vf0000.bsp', 'vf0001.bsp', 'vf0005.chim'])
            self.assertEqual(map_bytes(mixed[0]), 50)

    def test_refusals_name_the_unit(self):
        with self.assertRaisesRegex(ValueError, r'No world maps to partition.*boot payload 123 bytes'):
            partition_batches([], 123)
        maps = [PlannedMap('vf0000.chim', 812)]
        with self.assertRaisesRegex(ValueError, r'Boot payload %d bytes exceeds the partition budget of %d bytes '
                                                r'by 1 bytes' % (PAYLOAD_LIMIT + 1, PAYLOAD_LIMIT)):
            partition_batches(maps, PAYLOAD_LIMIT + 1)
        with self.assertRaisesRegex(ValueError, r'Invalid boot payload size: -1 bytes'):
            partition_batches(maps, -1)
        with self.assertRaisesRegex(ValueError, r'exceeds the partition budget of 100 bytes: vf0001.chim 101 bytes'):
            partition_batches([PlannedMap('vf0000.chim', 10), PlannedMap('vf0001.chim', 101)], 0, 100)


class AllChimDiskLayoutTests(unittest.TestCase):
    def world(self, root, count, sprites=None):
        boot = root / 'boot'
        id1 = boot / 'id1'
        region_directory(id1 / 'world/regions.awr', count)
        (id1 / 'maps').mkdir(parents=True)
        (boot / 'AmiWind').write_bytes(b'e' * ENGINE)
        chim = root / 'chim-world'
        (chim / 'far').mkdir(parents=True)
        (chim / 'chim').mkdir()
        (chim / 'chim' / 'world.chim').write_bytes(b'c' * 8192)
        frames = []
        for i in range(count):
            (chim / 'far' / ('%d_0.far' % i)).write_bytes(b'f' * 100)
            n = (sprites or {}).get(i, 0)
            frames.append({'cell': [i, 0], 'sprite_entities': [{'classname': 'aw_flora'}] * n,
                           'sprite_assets': [{'path': 'progs/aw_flora/f_%016x.spr' % i, 'bytes': 64}] if n else []})
        (chim / 'chim-source.json').write_text(json.dumps({'frames': frames}))
        names = {'vf%04d' % i: (i, 0) for i in range(count)}
        return boot, chim, names

    def layout(self, boot, chim, names, removed=()):
        def owned(id1, world, primary_only=False):
            return dict(names)
        with patch('chim.frame_map.region_map_names', side_effect=owned):
            return payload_preflight.check_disk_layout(boot, set(removed), [], chim)

    def test_every_cell_on_chim_plans_its_frame_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            boot, chim, names = self.world(Path(directory), 6, sprites={2: 3})
            result = self.layout(boot, chim, names)
        self.assertEqual(result['planned_frame_maps'], dict(count=6, bytes=6 * 1024 + 3 * 512, bound=6))
        parts = result['plan'][0]['partitions']
        self.assertEqual([p['partition'] for p in parts], ['DH0', 'DW0', 'DW1'])
        self.assertEqual(parts[1]['files'], 6)
        self.assertEqual(parts[1]['payload'], 6 * 1024 + 3 * 512)
        # boot: engine + six far sidecars + one recipe sprite asset (exact sizes from the CHIM world)
        self.assertEqual(parts[0]['payload'], ENGINE + awr_bytes(6) + 6 * 100 + 64)
        self.assertEqual(parts[2]['payload'], 8192)
        self.assertTrue(all(p['start'] < 2 * 1024 ** 3 for p in parts))

    def test_a_removed_or_written_frame_map_is_not_planned_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            boot, chim, names = self.world(Path(directory), 3)
            legacy = boot / 'id1/maps/vf0001.bsp'
            legacy.write_bytes(b'L' * 5000)          # a legacy map of an owned cell leaves (install_region)
            result = self.layout(boot, chim, names)
        self.assertEqual(result['planned_frame_maps']['count'], 3)
        self.assertEqual(result['plan'][0]['partitions'][1]['payload'], 3 * 1024)
        self.assertEqual(result['plan'][0]['partitions'][0]['payload'], ENGINE + awr_bytes(3) + 3 * 100)

    def test_legacy_world_without_chim_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            boot = Path(directory) / 'boot'
            id1 = boot / 'id1'
            region_directory(id1 / 'world/regions.awr', 3)
            (id1 / 'maps').mkdir(parents=True)
            files(id1 / 'maps', [1000, 2000, 3000])
            (boot / 'AmiWind').write_bytes(b'e' * ENGINE)
            result = payload_preflight.check_disk_layout(boot, set(), [], None)
        self.assertEqual(result['planned_frame_maps'], dict(count=0, bytes=0, bound=0))
        self.assertEqual((result['drives'], result['partitions']), (1, 2))
        self.assertEqual([p['files'] for p in result['plan'][0]['partitions']], [2, 3])

    def test_frame_map_bound_covers_the_recorded_sizes(self):
        # v0.0.43-dev2 region frame maps: 812 bytes with 2 rows (no sprites), 9,996 bytes with 41 rows (39 sprites)
        self.assertGreaterEqual(payload_preflight.frame_map_bound(0), 812)
        self.assertGreaterEqual(payload_preflight.frame_map_bound(39), 9996)


if __name__ == '__main__':
    unittest.main()
