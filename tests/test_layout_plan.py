# SPDX-License-Identifier: GPL-3.0-only
"""The disk layout planner (tools/layout_plan.py): the fewest partitions with a fixed headroom, the FFS size
estimate against xdftool, the gates, the plan the image step follows, the parallel partition writer and the
engine's search path finding the frame maps in both layouts (BUILD-PARTITION-GROWTH-UNGATED-36)."""
import hashlib
import json
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

import layout_plan as L  # noqa: E402
import world_volumes as W  # noqa: E402

MIB = L.MIB
GIB = 1024 ** 3
XDFTOOL = shutil.which('xdftool')


def boot_payload(total, files=200):
    """{path: bytes} of TOTAL bytes in FILES files over a few folders."""
    each = total // files
    rows = {'id1/f%02d/file%05d.bin' % (i % 9, i): each for i in range(files - 1)}
    rows['id1/last.bin'] = total - each * (files - 1)
    return rows


def frame_maps(count=1348, size=850):
    return [('id1/maps/vf%04d.chim' % i, size) for i in range(count)]


def chim_payload(total, files=500):
    each = total // files
    return [('frames/x%02d/f%04d.ccs' % (i % 40, i), each) for i in range(files)]


class PlannerTests(unittest.TestCase):
    def test_release_shaped_payload_is_two_partitions_with_headroom(self):
        # v0.0.46: DH0 1,457,977,095 B, CHIM world 1,328,723,736 B, 1,348 frame maps of 1,141,356 B in all
        plan = L.plan_compact(boot_payload(1457977095), frame_maps(1348, 847), chim_payload(1328723736))
        rows = plan['partitions']
        self.assertEqual([(r['partition'], r['volume'], r['role']) for r in rows],
                         [('DH0', 'AMIWIND', 'boot'), ('DW0', 'AW_WORLD0', 'chim')])
        self.assertEqual(len(rows[1]['maps']), 1348)          # the frame maps go with the CHIM world
        self.assertEqual(rows[0]['maps'], [])
        for r in rows:
            self.assertGreaterEqual(r['free_bytes'], 100 * MIB)
            self.assertLess(r['free_bytes'], 101 * MIB)      # sized to the MiB: never more than headroom + 1 MiB
            self.assertLess(r['bytes'], 2 * GIB)
        self.assertEqual(plan['world_volumes'], 1)
        L.require_minimal(plan)

    def test_headroom_is_absolute_and_boot_can_have_its_own(self):
        plan = L.plan_compact(boot_payload(50 * MIB), [], None, headroom_mib=100, boot_headroom_mib=300)
        self.assertGreaterEqual(plan['partitions'][0]['free_bytes'], 300 * MIB)
        self.assertEqual(plan['partitions'][0]['headroom_mib'], 300)
        self.assertEqual(plan['world_volumes'], 0)

    def test_maps_fill_the_chim_volume_then_boot_then_a_new_volume(self):
        big = 1800 * MIB
        maps = [('id1/maps/vf%04d.bsp' % i, 40 * MIB) for i in range(8)]
        plan = L.plan_compact(boot_payload(big), maps, chim_payload(big))
        rows = {r['partition']: r for r in plan['partitions']}
        self.assertEqual(rows['DW1']['role'], 'maps')
        self.assertEqual(len(rows['DW0']['maps']) + len(rows['DH0']['maps']) + len(rows['DW1']['maps']), 8)
        self.assertTrue(rows['DW0']['maps'], 'the CHIM volume takes maps first')
        for r in plan['partitions']:
            self.assertLess(r['bytes'], 2 * GIB)
            self.assertGreaterEqual(r['free_bytes'], 100 * MIB)
        # the drives keep every partition starting below 2 GiB and every drive below 4 GiB
        drives = W.plan_drives(dict(partition='DH0', bytes=rows['DH0']['bytes'], files=[]),
                               [dict(partition=r['partition'], bytes=r['bytes'], files=[])
                                for r in plan['partitions'][1:]])
        for drive in drives:
            self.assertTrue(all(p['start_bytes'] < 2 * GIB for p in drive['layout']['partitions']))
            self.assertLess(drive['bytes'], 4 * GIB)

    def test_headroom_is_never_shrunk_to_avoid_a_partition(self):
        # fits below 2 GiB with 10 MiB headroom, not with 100: a further partition opens instead
        room = 1900
        maps = [('id1/maps/vf0000.bsp', 30 * MIB)]
        small = L.plan_compact(boot_payload(room * MIB), maps, None, headroom_mib=10)
        self.assertEqual(len(small['partitions']), 1)
        large = L.plan_compact(boot_payload(room * MIB), maps, None, headroom_mib=100)
        self.assertEqual([r['partition'] for r in large['partitions']], ['DH0', 'DW0'])
        self.assertEqual(large['partitions'][1]['maps'], ['vf0000.bsp'])

    def test_payload_over_the_limit_is_refused_with_its_sizes(self):
        with self.assertRaisesRegex(ValueError, r'Boot payload 2039937109 bytes in 200 files \+ 100 MiB headroom'):
            L.plan_compact(boot_payload(1945 * MIB + 456789), [], None)
        with self.assertRaisesRegex(ValueError, r'CHIM world payload \d+ bytes'):
            L.plan_compact(boot_payload(MIB), [], chim_payload(1990 * MIB))

    def test_minimal_check_refuses_a_partition_the_payload_does_not_need(self):
        maps = [('id1/maps/vf%04d.bsp' % i, 2 * MIB) for i in range(10)]
        plan = L.plan_compact(boot_payload(100 * MIB), maps, chim_payload(100 * MIB), headroom_mib=10,
                              limit=113 * MIB)
        self.assertEqual([r['role'] for r in plan['partitions']], ['boot', 'chim', 'maps'])
        with self.assertRaisesRegex(ValueError, r'More partitions than the payload needs: DW1 \(10 maps, payload '
                                                r'20971520 bytes\) fits into DH0'):
            L.require_minimal(plan)
        # the released v0.0.46 layout: DW0 held only the frame maps (1,141,356 bytes) next to the CHIM world on DW1
        released = dict(partitions=[
            dict(partition='DH0', role='boot', used_blocks=2914000, payload=1457977095, headroom_mib=100, maps=[]),
            dict(partition='DW0', role='maps', used_blocks=2800, payload=1141356, headroom_mib=100, maps=['m'] * 1348),
            dict(partition='DW1', role='chim', used_blocks=2678000, payload=1328723736, headroom_mib=100, maps=[])])
        with self.assertRaisesRegex(ValueError, r'DW0 \(1348 maps, payload 1141356 bytes\) fits into DH0'):
            L.require_minimal(released)

    def test_follow_refuses_drift_beyond_headroom_and_moved_maps(self):
        planned = L.plan_compact(boot_payload(500 * MIB), frame_maps(20), chim_payload(300 * MIB))
        same = L.plan_compact(boot_payload(500 * MIB + 50 * MIB), frame_maps(20), chim_payload(300 * MIB))
        self.assertTrue(L.require_follows(planned, same))
        grown = L.plan_compact(boot_payload(500 * MIB + 101 * MIB), frame_maps(20), chim_payload(300 * MIB))
        with self.assertRaisesRegex(ValueError, r'DH0 payload \d+ bytes, planned \d+ bytes: \+\d+ bytes, more than '
                                                r'its 100 MiB headroom'):
            L.require_follows(planned, grown)
        other = L.plan_compact(boot_payload(500 * MIB), frame_maps(21), chim_payload(300 * MIB))
        with self.assertRaisesRegex(ValueError, 'DW0 holds other maps than planned'):
            L.require_follows(planned, other)
        no_chim = L.plan_compact(boot_payload(500 * MIB), frame_maps(20), None)
        with self.assertRaisesRegex(ValueError, 'Layout plan has partitions'):
            L.require_follows(planned, no_chim)
        # payload stored once after the plan (tools/payload_share.py): the bytes it removed are added back
        shrunk = L.plan_compact(boot_payload(500 * MIB - 150 * MIB), frame_maps(20), chim_payload(300 * MIB))
        with self.assertRaisesRegex(ValueError, 'more than its 100 MiB headroom'):
            L.require_follows(planned, shrunk)
        self.assertTrue(L.require_follows(planned, shrunk, shrink={'DH0': 150 * MIB}))

    def test_headroom_gate_on_written_partitions(self):
        plan = L.plan_compact(boot_payload(500 * MIB), [], chim_payload(300 * MIB))
        ok = [dict(partition='DH0', bytes=700 * MIB, payload_bytes=1, free_bytes=150 * MIB),
              dict(partition='DW0', bytes=500 * MIB, payload_bytes=1, free_bytes=100 * MIB)]
        self.assertTrue(L.require_headroom(ok, plan)['ok'])
        low = [dict(ok[0]), dict(ok[1], free_bytes=99 * MIB)]
        with self.assertRaisesRegex(ValueError, r'DW0 has 103809024 bytes free, below its headroom of 104857600 bytes'):
            L.require_headroom(low, plan)
        empty = [dict(ok[0]), dict(ok[1], free_bytes=360 * MIB)]
        with self.assertRaisesRegex(ValueError, r'DW0 is mostly empty: 377487360 of 524288000 bytes free'):
            L.require_headroom(empty, plan)
        # small partitions (16 MiB or less) are not judged mostly empty
        tiny = L.plan_compact(boot_payload(MIB), [], None, headroom_mib=4)
        self.assertTrue(L.require_headroom([dict(partition='DH0', bytes=16 * MIB, payload_bytes=1,
                                                 free_bytes=15 * MIB)], tiny)['ok'])

    def test_settings_cli_over_config_over_defaults(self):
        self.assertEqual(L.resolve(), dict(mode='compact', headroom_mib=100, boot_headroom_mib=100))
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'c.json'
            config.write_text(json.dumps({'partition_headroom_mib': 64, 'boot_partition_headroom_mib': 200}))
            self.assertEqual(L.resolve(config=config), dict(mode='compact', headroom_mib=64, boot_headroom_mib=200))
            self.assertEqual(L.resolve('legacy', 32, None, config),
                             dict(mode='legacy', headroom_mib=32, boot_headroom_mib=200))
        with self.assertRaisesRegex(ValueError, 'disk_layout'):
            L.resolve('spanned')
        with self.assertRaisesRegex(ValueError, 'headroom_mib'):
            L.resolve(None, -1)

    def test_the_plan_is_made_before_the_image_step_and_followed_by_it(self):
        import inspect
        import build_aga
        import payload_preflight
        # the payload preflight (run first by the image step, and again at its finalize start) plans the layout
        # and writes it to the run; the compact layout reads that plan and refuses a payload that left it
        wrapper = inspect.getsource(build_aga.payload_preflight)
        self.assertIn("out/'layout-plan.json'", wrapper)
        self.assertIn('layout=disk_layout_settings(args)', wrapper)
        image = inspect.getsource(build_aga.image)
        self.assertLess(image.index('payload_preflight(args, out, excluded, jobs'), image.index('finalize_image(args)'))
        compact = inspect.getsource(build_aga.compact_layout)
        self.assertIn("planned_path = out/'layout-plan.json'", compact)
        self.assertIn('layout_plan.require_follows(planned, plan, shrink=shrink)', compact)
        self.assertLess(compact.index('require_follows'), compact.index('write_layout('))
        self.assertIn('compact_disk_layout', inspect.getsource(payload_preflight.check_disk_layout))

    def test_build_config_keys_are_known_and_checked(self):
        from build_font_options import _read
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'c.json'
            config.write_text(json.dumps({'disk_layout': 'legacy', 'partition_headroom_mib': 50,
                                          'boot_partition_headroom_mib': None}))
            self.assertEqual(_read(config)[0]['disk_layout'], 'legacy')
            config.write_text(json.dumps({'partition_headroom_mib': 'lots'}))
            with self.assertRaisesRegex(ValueError, 'partition_headroom_mib'):
                _read(config)
        shipped = json.loads((ROOT / 'config/build-defaults.json').read_text())
        self.assertEqual((shipped['disk_layout'], shipped['partition_headroom_mib']), ('compact', 100))


def awr(count):
    """A region directory naming COUNT maps (every row its own: no aliases)."""
    head = b'AWR2' + struct.pack('<I', count) + bytes(56)
    return head + b''.join(struct.pack('<II', i, 0) + struct.pack('<I', i + 1) + bytes(40) for i in range(count))


def engine_find(volumes, count, rel):
    """The engine's search path (common.c): the boot volume's id1 first, then AW_WORLD0..count-1:id1."""
    for volume in ['AMIWIND'] + ['AW_WORLD%d' % i for i in range(count)]:
        if rel in volumes.get(volume, set()):
            return volume
    return None


def volume_layout(hdf):
    """{path: (SHA-256 of the data, its block numbers)} of every file on the volume, with its free bytes: the layout
    as written, without the timestamps xdftool stamps (two writes of one payload differ only in those)."""
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.FSString import FSString
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    _, found, free = read_volume(hdf)
    device = BlkDevFactory().open(str(hdf), read_only=True)
    try:
        volume = ADFSVolume(device)
        volume.open()
        rows = {}
        for path in sorted(found):
            node = volume.get_file_path_name(FSString(path))
            rows[path] = (hashlib.sha256(volume.read_file(FSString(path))).hexdigest(), tuple(node.get_block_nums()))
        return rows, free, Path(hdf).stat().st_size
    finally:
        device.close()


def read_volume(hdf, partition=None):
    from amitools.fs.ADFSVolume import ADFSVolume
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    device = BlkDevFactory().open(str(hdf), read_only=True, options={'part': partition} if partition else None)
    try:
        volume = ADFSVolume(device)
        volume.open()
        name = volume.get_volume_name()
        found = set()

        def walk(node, prefix):
            for entry in node.get_entries():
                path = prefix + str(entry.get_file_name().get_name())
                if entry.is_dir():
                    entry.read()
                    walk(entry, path + '/')
                else:
                    found.add(path)
        root = volume.get_root_dir()
        walk(root, '')
        return str(name), found, volume.bitmap.get_num_free() * device.block_bytes
    finally:
        device.close()


@unittest.skipUnless(XDFTOOL, 'xdftool (amitools) not installed')
class WrittenLayoutTests(unittest.TestCase):
    def test_size_estimate_equals_xdftool(self):
        sizes = [0, 1, 511, 512, 513, 72 * 512, 72 * 512 + 1, 144 * 512 + 7, 200000, 3000]
        with tempfile.TemporaryDirectory() as tmp:
            boot = Path(tmp) / 'boot'
            rows = []
            for i, size in enumerate(sizes):
                path = boot / ('id1/d%d/sub/f%02d.bin' % (i % 3, i))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes([i]) * size)
                rows.append((path.relative_to(boot).as_posix(), size))
            part = L.Part('DH0', 'T', 'boot', 1)
            part.add(rows)
            mib = part.mib_with()
            W.write_boot_partition(XDFTOOL, Path(tmp) / 'p.hdf', boot, mib)
            _, found, free = read_volume(Path(tmp) / 'p.hdf')
        self.assertEqual(found, {p for p, _ in rows})
        self.assertEqual(free, L.free_bytes(mib, part.blocks))
        self.assertGreaterEqual(free, MIB)

    def fixture(self, root):
        """A staged payload: boot files, a region directory of 6 frame maps, a CHIM world."""
        from test_chim_format import fixture
        boot = root / 'boot'
        for i in range(5):
            path = boot / ('id1/progs/p%d.mdl' % i)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes([i]) * (3000 + i))
        (boot / 'id1/world').mkdir(parents=True)
        (boot / 'id1/world/regions.awr').write_bytes(awr(6))
        (boot / 'id1/maps').mkdir(parents=True)
        for i in range(6):
            (boot / ('id1/maps/vf%04d.chim' % i)).write_bytes(b'C' * (700 + i))
        world = root / 'chimworld'
        fixture(world)
        return boot, world / 'chim'

    def write(self, root, jobs):
        boot, chim = self.fixture(root)
        maps = W.region_map_paths(boot / 'id1')
        rows = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*')
                if p.is_file() and p not in set(maps)}
        plan = L.plan_compact(rows, [(p.relative_to(boot).as_posix(), p.stat().st_size) for p in maps],
                              L.walk(chim), headroom_mib=1)
        out = root / 'out'
        out.mkdir()
        boot_check, worlds, _ = W.write_layout(plan, boot, out, XDFTOOL, out / 'partition.hdf', chim, jobs=jobs,
                                               log=lambda line: None)
        return plan, boot, out, worlds

    def test_parallel_partitions_equal_serial(self):
        # every file with the same bytes in the same blocks, the same free space and partition size: the partitions
        # are the same written at once or one by one (xdftool's timestamps differ between any two writes)
        digests = []
        for jobs in (1, 3):
            with tempfile.TemporaryDirectory() as tmp:
                plan, boot, out, worlds = self.write(Path(tmp), jobs)
                digests.append([volume_layout(out / name)
                                for name in ['partition.hdf'] + [w['file'] for w in worlds]])
                self.assertFalse((out / 'world-maps-staging').exists())
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(len(digests[0]), 2)

    def test_engine_search_path_finds_the_frame_maps_in_both_layouts(self):
        names = ['maps/vf%04d.chim' % i for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            plan, boot, out, worlds = self.write(Path(tmp), 2)
            volumes = {}
            for part in [out / 'partition.hdf'] + [out / w['file'] for w in worlds]:
                name, found, free = read_volume(part)
                volumes[name] = {p[4:] for p in found if p.startswith('id1/')}
                self.assertGreaterEqual(free, MIB)
            count = (boot / 'id1/world/volumes.awv').read_bytes()
            self.assertEqual(count, b'AWV1\x01')
            self.assertEqual(set(volumes), {'AMIWIND', 'AW_WORLD0'})
            for rel in names + ['chim/world.cwi']:
                self.assertEqual(engine_find(volumes, count[4], rel), 'AW_WORLD0', rel)
            self.assertFalse(any(p.startswith('maps/vf') for p in volumes['AMIWIND']))
        # the legacy layout (world_volumes.pack + the CHIM volume): the maps on AW_WORLD0, the world on AW_WORLD1
        with tempfile.TemporaryDirectory() as tmp:
            boot, chim = self.fixture(Path(tmp))
            out = Path(tmp) / 'out'
            out.mkdir()
            images = W.pack(boot / 'id1', out, 'test', XDFTOOL, jobs=1)
            from chim.disk import IMAGE_BASE, pack_partition
            packed = pack_partition(chim, out / 'world1-partition.hdf', 'AW_WORLD1', None, XDFTOOL, IMAGE_BASE)
            W.write_volumes_file(boot / 'id1', 2)
            volumes = {}
            for part in [out / images[0]['file'], out / packed['file']]:
                name, found, _ = read_volume(part)
                volumes[name] = {p[4:] for p in found if p.startswith('id1/')}
            volumes['AMIWIND'] = {p.relative_to(boot / 'id1').as_posix() for p in (boot / 'id1').rglob('*')
                                  if p.is_file()}
            for rel in names:
                self.assertEqual(engine_find(volumes, 2, rel), 'AW_WORLD0', rel)
            self.assertEqual(engine_find(volumes, 2, 'chim/world.cwi'), 'AW_WORLD1')

    def test_a_failed_write_puts_the_maps_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            boot, chim = self.fixture(Path(tmp))
            maps = W.region_map_paths(boot / 'id1')
            rows = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*')
                    if p.is_file() and p not in set(maps)}
            plan = L.plan_compact(rows, [(p.relative_to(boot).as_posix(), p.stat().st_size) for p in maps],
                                  L.walk(chim), headroom_mib=1)
            out = Path(tmp) / 'out'
            out.mkdir()
            (out / 'world0-partition.hdf').write_bytes(b'')       # CHIM partitions are written once
            with self.assertRaises(Exception):
                W.write_layout(plan, boot, out, XDFTOOL, out / 'partition.hdf', chim, jobs=1, log=lambda line: None)
            self.assertEqual(sorted(p.name for p in (boot / 'id1/maps').iterdir()),
                             ['vf%04d.chim' % i for i in range(6)])
            self.assertFalse((out / 'world-maps-staging').exists())


if __name__ == '__main__':
    unittest.main()
