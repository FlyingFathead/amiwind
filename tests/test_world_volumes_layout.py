import tempfile
import unittest
from pathlib import Path
from world_volumes import (balanced, partition_batches, hardfile_groups, partition_starts, drive_order,
                           require_mountable, PARTITION_START_LIMIT, RDB_BYTES)

MIB = 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]

class WorldVolumeLayoutTests(unittest.TestCase):
    def maps(self, root, sizes):
        result = []
        for i, size in enumerate(sizes):
            p = root / f'vf{i:04d}.bsp'
            p.write_bytes(b'x' * size)
            result.append(p)
        return result

    def test_small_layout_preserves_existing_balance(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.maps(Path(directory), [10] * 6)
            kept, additional = balanced(paths, 20, 100)
            self.assertEqual(partition_batches(paths, 20, 100), (kept, [additional]))

    def test_large_layout_retains_every_map_once_with_bounded_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.maps(Path(directory), [30] * 10)
            kept, batches = partition_batches(paths, 40, 100)
            self.assertEqual(kept + [p for batch in batches for p in batch], paths)
            self.assertLessEqual(40 + sum(p.stat().st_size for p in kept), 100)
            self.assertTrue(all(sum(p.stat().st_size for p in batch) <= 100 for batch in batches))
            self.assertGreater(len(batches), 1)

    def test_drives_include_header_and_keep_all_partitions(self):
        worlds = [dict(bytes=40000, volume=f'AW_WORLD{i}') for i in range(3)]
        groups = hardfile_groups(40000, worlds, 130000)
        self.assertEqual([p for group in groups for p in group], worlds)
        self.assertEqual(len(groups), 2)
        for i, group in enumerate(groups):
            self.assertLess(32768 + (40000 if i == 0 else 0) + sum(p['bytes'] for p in group), 130000)
        with self.assertRaises(ValueError):
            hardfile_groups(97232, [], 130000)

class PartitionStartLimitTests(unittest.TestCase):
    """BUILD-WORLD-PARTITION-MOUNT-33: Kickstart 3.1 does not mount a partition that starts at or
    beyond 2 GiB of its drive (FS-UAE 3.1.66: "Not a DOS disk in device DW3")."""
    # v0.0.33-dev1 full image: boot DH0 1920 MiB; DW0, DW1 1920 MiB; DW2 256 MiB; DW3 (CHIM) 128 MiB.
    BOOT = 1920 * MIB
    DEV1 = [dict(bytes=b * MIB, partition='DW%d' % i) for i, b in enumerate((1920, 1920, 256, 128))]

    def assert_mountable(self, boot, groups):
        for index, group in enumerate(groups):
            base = boot + RDB_BYTES if index == 0 else RDB_BYTES
            for start in partition_starts(base, group):
                self.assertLess(start, PARTITION_START_LIMIT)
            self.assertLess(base + sum(p['bytes'] for p in group), 4 * 1024**3)

    def test_dev1_layout_no_longer_puts_dw3_beyond_2_gib(self):
        # The old packer wrote DW1, DW2, DW3 on drive 2: DW3 started at 2,281,734,144 bytes.
        self.assertEqual(partition_starts(RDB_BYTES, self.DEV1[1:])[2], 2281734144)
        groups = hardfile_groups(self.BOOT, self.DEV1)
        self.assertEqual([[p['partition'] for p in g] for g in groups], [['DW0'], ['DW2', 'DW3', 'DW1']])
        self.assert_mountable(self.BOOT, groups)

    def test_layout_that_fits_keeps_its_order(self):
        big, small = dict(bytes=1536 * MIB, partition='DW0'), dict(bytes=256 * MIB, partition='DW1')
        # Every start below 2 GiB in the given order: unchanged (byte-identical older layouts).
        self.assertEqual(hardfile_groups(128 * MIB, [big, small]), [[big, small]])
        # In order DW1 would start at 2 GiB + 32 KiB: the largest partition moves last.
        self.assertEqual(hardfile_groups(512 * MIB, [big, small]), [[small, big]])

    def test_largest_last_only_when_needed_and_none_when_nothing_fits(self):
        a, b, c = (dict(bytes=1900 * MIB), dict(bytes=200 * MIB), dict(bytes=100 * MIB))
        self.assertEqual(drive_order(RDB_BYTES, [b, c]), [b, c])
        self.assertEqual(drive_order(RDB_BYTES, [a, b, c]), [b, c, a])
        # Below 4 GiB, but the last start is past 2 GiB in either order.
        self.assertIsNone(drive_order(RDB_BYTES, [dict(bytes=1500 * MIB), dict(bytes=1500 * MIB), dict(bytes=600 * MIB)]))
        self.assertIsNone(drive_order(RDB_BYTES, [dict(bytes=2000 * MIB), dict(bytes=2000 * MIB), dict(bytes=100 * MIB)]))

    def test_every_generated_layout_is_mountable(self):
        import random
        rng = random.Random(33)
        for _ in range(500):
            boot = rng.choice((128, 512, 1920)) * MIB
            worlds = [dict(bytes=rng.choice((128, 256, 1024, 1536, 1920)) * MIB, partition='DW%d' % i)
                      for i in range(rng.randint(1, 8))]
            groups = hardfile_groups(boot, worlds)
            self.assertEqual(sorted(p['partition'] for g in groups for p in g), sorted(p['partition'] for p in worlds))
            self.assert_mountable(boot, groups)

    def test_gate_refuses_a_partition_written_beyond_2_gib(self):
        ok = [dict(partition='DW2', offset_bytes=2013298688), dict(partition='DW1', offset_bytes=PARTITION_START_LIMIT - RDB_BYTES)]
        self.assertTrue(require_mountable(ok)['ok'])
        with self.assertRaisesRegex(ValueError, 'DW3 at 2281734144'):
            require_mountable(ok + [dict(partition='DW3', offset_bytes=2281734144, hdf_file='w.hdf')])

    def test_image_step_gates_every_written_drive(self):
        # The image step writes its drives with world_volumes.assemble_drives, which gates each as written.
        self.assertIn('assemble_drives(args.rdbtool,drive_plans,out,part,boot_files,jobs=jobs,run=run)',
                      (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        self.assertIn('require_mountable(checked)', (ROOT / 'tools/world_volumes.py').read_text(encoding='utf-8'))

    def test_disk_layout_gate_checks_all_four_amiga_limits(self):
        # BUILD-WORLD-PARTITION-MOUNT-33: start and size of every partition below 2 GiB, files well under
        # 2 GiB, drives below 4 GiB; each violation names the drive, partition or file and the limit.
        from world_volumes import (require_disk_layout, PARTITION_SIZE_LIMIT, FILE_SIZE_LIMIT,
                                   DRIVE_SIZE_LIMIT)
        parts = [dict(partition='DH0', files=[dict(path='id1/pak0.pak', bytes=900 * 1024**2)]),
                 dict(partition='DW1', files=[dict(path='id1/maps/a.bsp', bytes=5)])]
        good = [dict(partition='DH0', offset_bytes=RDB_BYTES, bytes=1024**3),
                dict(partition='DW1', offset_bytes=RDB_BYTES + 1024**3, bytes=512 * 1024**2)]
        record = require_disk_layout('boot.hdf', 3 * 1024**3, good, parts)
        self.assertTrue(record['ok'])
        self.assertEqual([(r['partition'], r['start_bytes'], r['largest_file']) for r in record['partitions']],
                         [('DH0', RDB_BYTES, 'id1/pak0.pak'), ('DW1', RDB_BYTES + 1024**3, 'id1/maps/a.bsp')])
        with self.assertRaisesRegex(ValueError, 'DW3 starts at 2281734144'):
            require_disk_layout('w.hdf', 2415951872, good + [dict(partition='DW3', offset_bytes=2281734144,
                                                                     bytes=128 * 1024**2)], parts)
        with self.assertRaisesRegex(ValueError, 'DW1 is %d bytes' % PARTITION_SIZE_LIMIT):
            require_disk_layout('w.hdf', 3 * 1024**3, [dict(partition='DW1', offset_bytes=RDB_BYTES,
                                                           bytes=PARTITION_SIZE_LIMIT)], parts)
        big = [dict(partition='DH0', files=[dict(path='id1/pak9.pak', bytes=FILE_SIZE_LIMIT)])]
        with self.assertRaisesRegex(ValueError, 'file id1/pak9.pak is %d bytes' % FILE_SIZE_LIMIT):
            require_disk_layout('boot.hdf', 2 * 1024**3, good[:1], big)
        with self.assertRaisesRegex(ValueError, 'drive boot.hdf is %d bytes' % DRIVE_SIZE_LIMIT):
            require_disk_layout('boot.hdf', DRIVE_SIZE_LIMIT, good, parts)

    def test_image_step_records_the_layout_of_every_drive(self):
        self.assertIn('disk_layout.append(require_disk_layout(drive.name, drive.stat().st_size, checked, partitions))',
                      (ROOT / 'tools/world_volumes.py').read_text(encoding='utf-8'))
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('layout,drive_receipts,disk_layout=assemble_drives(', source)
        self.assertIn("'disk_layout':disk_layout", source)

    def test_planned_drives_sit_where_rdbtool_puts_them(self):
        # The plan gate measures what assemble_drives will write: one 32 KiB RDB cylinder, then the
        # partitions back to back; the drive is the sum of its partitions plus that cylinder.
        from world_volumes import plan_drives, planned_partition
        boot = planned_partition('DH0', [dict(path='id1/pak0.pak', bytes=10)], 'AMIWIND')
        worlds = [dict(partition='DW0', bytes=1920 * MIB, files=[]), dict(partition='DW1', bytes=256 * MIB, files=[])]
        plans = plan_drives(boot, worlds, name=lambda i: 'd%d.hdf' % i)
        self.assertEqual([p['file'] for p in plans], ['d0.hdf'])
        self.assertEqual([r['start_bytes'] for r in plans[0]['layout']['partitions']],
                         [RDB_BYTES, RDB_BYTES + 128 * MIB, RDB_BYTES + 384 * MIB])
        self.assertEqual(plans[0]['layout']['partitions'][1]['partition'], 'DW1')  # largest moved last
        self.assertEqual(plans[0]['bytes'], (128 + 256 + 1920) * MIB + RDB_BYTES)
        with self.assertRaisesRegex(ValueError, r'd0\.hdf \(planned\) DW0 starts at'):
            plan_drives(boot, worlds, name=lambda i: 'd%d.hdf' % i, groups=[[worlds[1], worlds[0], worlds[0]]])


if __name__ == '__main__':
    unittest.main()
