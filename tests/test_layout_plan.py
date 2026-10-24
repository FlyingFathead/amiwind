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

    def test_a_payload_that_only_grew_is_laid_out_from_the_staged_files(self):
        # IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48: the room actor bake writes about 310 MB of actor models after the preflight
        # plan; a grown payload is laid out anew (the headroom gate still decides), anything else still stops
        planned = L.plan_compact(boot_payload(500 * MIB), frame_maps(20), chim_payload(300 * MIB))
        self.assertIsNone(L.follows_or_grew(planned, planned))
        grown = L.plan_compact(boot_payload(500 * MIB + 101 * MIB), frame_maps(20), chim_payload(300 * MIB))
        bytes_grown, why = L.follows_or_grew(planned, grown)
        self.assertGreater(bytes_grown, 100 * MIB)
        self.assertIn('more than its 100 MiB headroom', why)
        # rc1-try4: payload sharing took 156 MB off after the plan; a payload that shrank is laid out anew too
        shrunk = L.plan_compact(boot_payload(500 * MIB - 150 * MIB), frame_maps(20), chim_payload(300 * MIB))
        bytes_changed, why = L.follows_or_grew(planned, shrunk)
        self.assertLess(bytes_changed, -100 * MIB)
        self.assertIn('more than its 100 MiB headroom', why)
        # a partition role the plan had and the payload lost still stops it
        no_chim = L.plan_compact(boot_payload(500 * MIB), frame_maps(20), None)
        with self.assertRaisesRegex(ValueError, 'Layout plan has partitions'):
            L.follows_or_grew(planned, no_chim)
        # a mismatch with no change of payload is a planning bug and still stops it
        moved = L.plan_compact(boot_payload(500 * MIB), frame_maps(21), chim_payload(300 * MIB))
        if sum(r['payload'] for r in moved['partitions']) == sum(r['payload'] for r in planned['partitions']):
            with self.assertRaisesRegex(ValueError, 'other maps than planned'):
                L.follows_or_grew(planned, moved)

    def test_a_final_plan_packs_by_the_rule_require_minimal_checks(self):
        # rc1-try5: the packer kept twice the headroom free in DH0 and spilled ~100 MB to a third partition that
        # require_minimal then refused; a plan from the finished staging folder packs with one headroom (margin=1)
        boot = boot_payload(int((2048 - 100 - 150) * MIB))   # fits DH0 with one headroom, not with two
        early = L.plan_compact(boot, frame_maps(20), chim_payload(300 * MIB))
        final = L.plan_compact(boot, frame_maps(20), chim_payload(300 * MIB), margin=1)
        self.assertLessEqual(len(final['partitions']), len(early['partitions']))
        self.assertTrue(L.require_minimal(final))

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
        # followed, or laid out from the staged files when the payload only grew (IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48)
        self.assertIn('layout_plan.follows_or_grew(planned, plan, shrink=shrink)', compact)
        self.assertLess(compact.index('follows_or_grew'), compact.index('write_layout('))
        self.assertIn('compact_disk_layout', inspect.getsource(payload_preflight.check_disk_layout))

    def test_the_plan_counts_the_actor_library_the_image_step_installs(self):
        # IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48: finalize_image installs the actor library stage (148.8 MB in the MiniWind
        # Balmora build) after the payload preflight planned DH0; the plan left it out and the layout check refused
        # the staged payload (+145 MB, more than the 100 MiB headroom). The plan counts it, over the files it replaces.
        import build_aga
        import inspect
        import payload_preflight
        from types import SimpleNamespace
        layout = dict(mode='compact', headroom_mib=1, boot_headroom_mib=1)
        with tempfile.TemporaryDirectory() as tmp:
            boot = Path(tmp) / 'image/boot'
            (boot / 'id1/progs').mkdir(parents=True)
            (boot / 'AmiWind').write_bytes(b'e' * 4096)
            (boot / 'id1/progs/n_shared.mdl').write_bytes(b's' * 1000)
            library = Path(tmp) / 'actor-library'
            (library / 'id1/progs').mkdir(parents=True)
            (library / 'id1/progs/n_shared.mdl').write_bytes(b'S' * 3000)   # replaces the staged file
            (library / 'id1/progs/c_creature.mdl').write_bytes(b'c' * (3 * MIB))
            without = payload_preflight.check_disk_layout(boot, set(), [], None, layout)['layout_plan']
            planned = payload_preflight.check_disk_layout(boot, set(), [], None, layout,
                                                          actor_library=library)['layout_plan']
            # the image step installs the library (actor_library.install copies id1/ over id1/), then plans again
            shutil.copytree(library / 'id1', boot / 'id1', dirs_exist_ok=True)
            staged = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*') if p.is_file()}
            actual = L.plan_compact(staged, [], None, 1, 1)
        self.assertEqual(planned['partitions'][0]['payload'], actual['partitions'][0]['payload'])
        self.assertEqual(planned['partitions'][0]['files'], actual['partitions'][0]['files'])
        self.assertTrue(L.require_follows(planned, actual))
        with self.assertRaisesRegex(ValueError, 'no longer matches the layout plan: DH0 payload'):
            L.require_follows(without, actual)
        # the image step passes the library it installs, and only when it installs it (the actor table on)
        self.assertIn('actor_library=installed_actor_library(args)', inspect.getsource(build_aga.payload_preflight))
        self.assertIn('installed_actor_library(args)', inspect.getsource(build_aga.finalize_image))
        self.assertEqual(build_aga.installed_actor_library(SimpleNamespace(chim_actor_table='on', actor_library=library)),
                         library)
        self.assertIsNone(build_aga.installed_actor_library(SimpleNamespace(chim_actor_table='off', actor_library=library)))
        self.assertIsNone(build_aga.installed_actor_library(SimpleNamespace(chim_actor_table='on', actor_library=None)))

    def test_movable_units_are_the_search_path_files(self):
        # IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: files the engine opens only through its search path, grouped as they load
        self.assertEqual(L.movable_unit('id1/chimi/rooms/vci000.crm'), 'id1/chimi/')
        self.assertEqual(L.movable_unit('id1/chimi/world.cwi'), 'id1/chimi/')
        self.assertEqual(L.movable_unit('id1/maps/vci000.chim'), 'id1/maps/vci000')
        self.assertEqual(L.movable_unit('id1/maps/vf0001.cut'), 'id1/maps/vf0001')
        for name in ('a_0123456789ab.mdl', 'a_0123456789ab.anm', 'a_0123456789ab.tag', 'a_0123456789ab_m.mdl',
                     'a_0123456789ab_m.anm', 'a_0123456789ab_m.tag'):
            self.assertEqual(L.movable_unit('id1/progs/' + name), 'id1/progs/a_0123456789ab', name)
        # music is opened by its own path (aw_music.c), the rest of DH0 stays where the engine expects it
        for path in ('id1/music/track04.awm', 'id1/progs/player.mdl', 'id1/progs/body/b.mdl', 'id1/world/volumes.awv',
                     'id1/default-game.cfg', 'AmiWind', 'id1/chimi', 'id1/maps/sub/x.bsp'):
            self.assertIsNone(L.movable_unit(path), path)

    def split_payload(self):
        """A boot payload over 2 GiB: 1,700 MiB that stays, a 250 MiB interior store, 40 actors of 8 MiB, 6 maps."""
        rows = boot_payload(1700 * MIB)
        rows.update({'id1/chimi/world.cwi': 50 * MIB, 'id1/chimi/p00.ccs': 200 * MIB, 'id1/chimi/rooms/r.crm': 1000})
        for i in range(40):
            stem = 'id1/progs/a_%012x' % i
            rows.update({stem + '.mdl': 3 * MIB, stem + '_m.mdl': 5 * MIB, stem + '.anm': 900, stem + '_m.anm': 1200,
                         stem + '.tag': 1300})
        for i in range(6):
            rows.update({'id1/maps/room%02d.chim' % i: 2 * MIB, 'id1/maps/room%02d.cut' % i: 700})
        return rows

    def test_boot_over_the_limit_moves_the_largest_units_to_the_chim_volume(self):
        rows = self.split_payload()
        plan = L.plan_compact(rows, frame_maps(20), chim_payload(300 * MIB))
        L.require_minimal(plan)
        boot, chim = plan['partitions']
        self.assertEqual([r['role'] for r in plan['partitions']], ['boot', 'chim'])
        self.assertLess(boot['bytes'], 2 * GIB)
        self.assertGreaterEqual(boot['free_bytes'], 100 * MIB)
        moved = set(chim['moved'])
        self.assertIn('id1/chimi/', moved)                               # the largest unit first
        actors = [k for k in moved if k.startswith('id1/progs/a_')]
        self.assertTrue(0 < len(actors) < 40, len(actors))             # only as many as DH0 needs
        # DH0 would not fit with one unit fewer moved: the split is the smallest one in that order
        fewer = L.Part('DH0', 'AMIWIND', 'boot', 200)       # planned with room for one headroom of drift
        fewer.add(sorted((k, v) for k, v in rows.items() if L.movable_unit(k) not in moved - {sorted(actors)[-1]}))
        self.assertFalse(L.fits(fewer, ()))
        self.assertEqual(chim['moved_bytes'], sum(v for k, v in rows.items() if L.movable_unit(k) in moved))
        self.assertEqual(plan['split']['units'], len(moved))
        self.assertEqual(plan['split']['kinds']['store'], dict(units=1, bytes=250 * MIB + 1000))
        self.assertEqual(plan['payload'], sum(rows.values()) + L.VOLUMES_BYTES + 20 * 850 +
                         sum(b for _, b in chim_payload(300 * MIB)))
        # a unit moves whole: every file of a moved actor (model, mover, layouts, tags) goes with it
        on_chim = {p for p, _ in L.assign_units(plan, sorted(rows))['DW0']}
        for key in actors:
            self.assertEqual({p for p in rows if L.movable_unit(p) == key} - on_chim, set())
        self.assertTrue(any('boot units' in line for line in L.lines(plan)))
        self.assertTrue(any('moved to world volumes' in line for line in L.lines(plan)))
        # one drive: DH0 and the CHIM volume each below 2 GiB, both starting below 2 GiB, the drive below 4 GiB
        drives = W.plan_drives(dict(partition='DH0', bytes=boot['bytes'], files=[]),
                               [dict(partition='DW0', bytes=chim['bytes'], files=[])])
        self.assertEqual(len(drives), 1)

    def test_units_open_a_store_volume_when_no_world_volume_has_room(self):
        plan = L.plan_compact(self.split_payload(), [], None)
        self.assertEqual([(r['partition'], r['volume'], r['role']) for r in plan['partitions']],
                         [('DH0', 'AMIWIND', 'boot'), ('DW0', 'AW_WORLD0', 'store')])
        self.assertEqual(plan['world_volumes'], 1)
        self.assertIn('id1/chimi/', plan['partitions'][1]['moved'])
        L.require_minimal(plan)
        # the store volume holding too little next to a boot volume with room is refused like a maps volume
        small = dict(partitions=[
            dict(partition='DH0', role='boot', used_blocks=1000, payload=1, headroom_mib=100, maps=[]),
            dict(partition='DW0', role='store', used_blocks=10, payload=2, headroom_mib=100, maps=[], moved=['k'])])
        with self.assertRaisesRegex(ValueError, r'DW0 \(0 maps, 1 moved units, payload 2 bytes\) fits into DH0'):
            L.require_minimal(small)

    def test_a_payload_that_cannot_split_names_its_folders(self):
        rows = boot_payload(2200 * MIB)
        rows['id1/chimi/world.cwi'] = 10 * MIB
        with self.assertRaisesRegex(ValueError, r'Boot payload \d+ bytes in \d+ files \+ 100 MiB headroom needs a '
                                                r'\d+ MiB partition .*moving 1 of the 1 units .*largest boot folders: '
                                                r'id1/f0\d \d+ bytes in \d+ files'):
            L.plan_compact(rows, [], None)

    def test_the_image_step_follows_the_planned_units(self):
        rows = self.split_payload()
        planned = L.plan_compact(rows, frame_maps(20), chim_payload(300 * MIB))
        # the image step's payload changed a little (and differently): it still puts the planned units where planned
        grown = dict(rows)
        grown['id1/f00/extra.bin'] = 30 * MIB
        for key in [k for k in grown if k.startswith('id1/progs/a_%012x' % 39)]:
            grown[key] += 1
        actual = L.plan_compact(grown, frame_maps(20), chim_payload(300 * MIB), follow=planned)
        self.assertEqual(actual['partitions'][1]['moved'], planned['partitions'][1]['moved'])
        self.assertTrue(L.require_follows(planned, actual))
        # a unit stored once after the plan (tools/payload_share.py: gone from the payload) is not a mismatch
        shared = {k: v for k, v in rows.items() if L.movable_unit(k) != planned['partitions'][1]['moved'][-1]}
        removed = sum(rows.values()) - sum(shared.values())
        actual = L.plan_compact(shared, frame_maps(20), chim_payload(300 * MIB), follow=planned)
        self.assertTrue(L.require_follows(planned, actual, shrink={'DH0': removed}))
        # a unit on another partition than planned is refused
        stray = dict(actual, partitions=[dict(actual['partitions'][0]),
                                         dict(actual['partitions'][1], moved=actual['partitions'][1]['moved'] + ['x'])])
        with self.assertRaisesRegex(ValueError, 'DW0 holds boot units not planned there'):
            L.require_follows(planned, stray)
        # without the plan the image step plans the same split itself
        self.assertEqual(L.plan_compact(rows, frame_maps(20), chim_payload(300 * MIB))['partitions'][1]['moved'],
                         planned['partitions'][1]['moved'])

    def test_the_plan_counts_the_room_batches_and_the_interior_store(self):
        # IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: the image step copies the room batches in after its first preflight and
        # installs the CHIM interior store (id1/chimi/, each held room's .bsp made a small .chim) after finalize's
        # preflight; both plans left them out (1.66 GB of residents, the 321 MB store in v0.0.48-dev2)
        import build_aga
        import inspect
        import payload_preflight as P
        layout = dict(mode='compact', headroom_mib=1, boot_headroom_mib=1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            boot = tmp / 'image/boot'
            (boot / 'id1/maps').mkdir(parents=True)
            (boot / 'AmiWind').write_bytes(b'e' * 4096)
            bsp = struct.pack('<i', 29) + struct.pack('<ii', 124, 3000) + bytes(2 * MIB)
            (boot / 'id1/maps/held.bsp').write_bytes(bsp)
            batches = tmp / 'chim-room-batches'
            (batches / 'id1/maps').mkdir(parents=True)
            (batches / 'id1/progs').mkdir(parents=True)
            (batches / 'id1/maps/batch.bsp').write_bytes(bsp)
            (batches / 'id1/progs/a_000000000001.mdl').write_bytes(b'm' * (3 * MIB))
            (batches / 'room-batches.json').write_text(json.dumps({'files': {'maps/batch.bsp': 'x',
                                                                             'progs/a_000000000001.mdl': 'y'}}))
            interiors = tmp / 'chim-interiors'
            (interiors / 'chimi/rooms').mkdir(parents=True)
            (interiors / 'chimi/world.cwi').write_bytes(b'w' * (5 * MIB))
            for room in ('held', 'batch', 'absent'):
                (interiors / 'chimi/rooms' / (room + '.crm')).write_bytes(b'r' * 1000)
            (interiors / 'chim-rooms-receipt.json').write_text(json.dumps(
                {'rooms': [{'room': 'held'}, {'room': 'batch'}, {'room': 'absent'}]}))
            plan = P.check_disk_layout(boot, set(), [], None, layout, room_batches=batches,
                                       chim_interiors=interiors)['layout_plan']
        rows = plan['partitions'][0]
        self.assertEqual(rows['files'], 7)   # AmiWind, the batch model, 2 room maps, world.cwi, 2 held room records
        expected = 4096 + 3 * MIB + 2 * (3000 + P.ROOM_MAP_SHELL_BYTES) + 5 * MIB + 2 * 1000
        self.assertEqual(rows['payload'], expected)
        wrapper = inspect.getsource(build_aga.payload_preflight)
        self.assertIn("room_batches=getattr(args, 'chim_room_batches', None)", wrapper)
        self.assertIn("chim_interiors=getattr(args, 'chim_interiors', None)", wrapper)

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

    def split_fixture(self, root):
        """The fixture with boot units over a 4 MiB partition limit: an interior store and three actors."""
        boot, chim = self.fixture(root)
        units = {'id1/chimi/world.cwi': 400000, 'id1/chimi/p00.ccs': 800000, 'id1/chimi/rooms/vci000.crm': 3000}
        for i in range(3):
            units.update({'id1/progs/a_%012x.mdl' % i: 200000 + i, 'id1/progs/a_%012x_m.mdl' % i: 300000,
                          'id1/progs/a_%012x.anm' % i: 900})
        for rel, size in units.items():
            (boot / rel).parent.mkdir(parents=True, exist_ok=True)
            (boot / rel).write_bytes(bytes([len(rel) % 251]) * size)
        maps = W.region_map_paths(boot / 'id1')
        rows = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*')
                if p.is_file() and p not in set(maps)}
        plan = L.plan_compact(rows, [(p.relative_to(boot).as_posix(), p.stat().st_size) for p in maps],
                              L.walk(chim), headroom_mib=1, limit=4 * MIB)
        return boot, chim, plan, units

    def test_engine_search_path_finds_the_moved_boot_units(self):
        # IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: the units the plan moves are written on their world volume at their boot
        # path, DH0 is written without them, and the engine's search path finds each one there
        with tempfile.TemporaryDirectory() as tmp:
            boot, chim, plan, units = self.split_fixture(Path(tmp))
            moved = {k for row in plan['partitions'][1:] for k in row['moved']}
            self.assertIn('id1/chimi/', moved)
            before = {p.relative_to(boot).as_posix() for p in boot.rglob('*') if p.is_file()}
            out = Path(tmp) / 'out'
            out.mkdir()
            boot_check, worlds, _ = W.write_layout(plan, boot, out, XDFTOOL, out / 'partition.hdf', chim, jobs=2,
                                                   log=lambda line: None)
            volumes = {}
            for part in [out / 'partition.hdf'] + [out / w['file'] for w in worlds]:
                name, found, free = read_volume(part)
                volumes[name] = {p[4:] for p in found if p.startswith('id1/')}
                self.assertGreaterEqual(free, MIB)
            count = (boot / 'id1/world/volumes.awv').read_bytes()[4]
            self.assertEqual(count, plan['world_volumes'])
            for rel in sorted(before):
                if not rel.startswith('id1/') or rel == L.VOLUMES_FILE or rel.startswith('id1/maps/vf'):
                    continue
                where = engine_find(volumes, count, rel[4:])
                if L.movable_unit(rel) in moved:
                    self.assertTrue(where and where.startswith('AW_WORLD'), rel)
                    self.assertNotIn(rel[4:], volumes['AMIWIND'])
                else:
                    self.assertEqual(where, 'AMIWIND', rel)
            self.assertFalse((out / 'world-maps-staging').exists())

    def test_a_failed_write_puts_the_boot_units_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            boot, chim, plan, units = self.split_fixture(Path(tmp))
            before = sorted(p.relative_to(boot).as_posix() for p in boot.rglob('*') if p.is_file())
            out = Path(tmp) / 'out'
            out.mkdir()
            (out / 'world0-partition.hdf').write_bytes(b'')       # partitions are written once
            with self.assertRaises(Exception):
                W.write_layout(plan, boot, out, XDFTOOL, out / 'partition.hdf', chim, jobs=1, log=lambda line: None)
            after = sorted(p.relative_to(boot).as_posix() for p in boot.rglob('*') if p.is_file())
            self.assertEqual([p for p in after if p != L.VOLUMES_FILE], [p for p in before if p != L.VOLUMES_FILE])
            self.assertFalse((out / 'world-maps-staging').exists())

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
