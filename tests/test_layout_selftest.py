# SPDX-License-Identifier: GPL-3.0-only
"""End-to-end negative self-test of the disk-layout gate (BUILD-WORLD-PARTITION-MOUNT-33): dummy payloads
through the image step's packing code are refused at every Amiga limit, a layout just under every limit
passes, nothing is left behind, and the run costs seconds and almost no disk (sparse dummies)."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import layout_selftest  # noqa: E402
import world_volumes as wv  # noqa: E402

MIB = 1024 * 1024
TOOLS = Path(sys.executable).parent
XDFTOOL = shutil.which('xdftool') or (str(TOOLS / 'xdftool') if (TOOLS / 'xdftool').is_file() else None)
RDBTOOL = shutil.which('rdbtool') or (str(TOOLS / 'rdbtool') if (TOOLS / 'rdbtool').is_file() else None)
HAVE_AMITOOLS = bool(importlib.util.find_spec('amitools') and XDFTOOL and RDBTOOL)


def run(scratch, **kwargs):
    lines = []
    ok, results = layout_selftest.selftest(scratch, log=lines.append, **kwargs)
    return ok, {r['case']: r for r in results}, lines


class LayoutSelfTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.scratch = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def assert_clean(self):
        self.assertEqual(list(self.scratch.iterdir()), [], 'the self-test left files behind')

    def test_every_limit_is_refused_and_the_largest_legal_layout_passes(self):
        started = time.monotonic()
        ok, rows, lines = run(self.scratch, write=False)
        self.assertTrue(ok, '\n'.join(lines))
        for name in ('file-over-1gib', 'partition-over-2gib', 'start-past-2gib', 'drive-over-4gib'):
            with self.subTest(case=name):
                self.assertEqual(rows[name]['outcome'], 'refused')
                self.assertIn('Disk layout gate (Amiga limits)', rows[name]['message'])
        self.assertIn('file id1/maps/vf0000.bsp is 2500000000 bytes', rows['file-over-1gib']['message'])
        self.assertIn('DW0 is 2147483648 bytes', rows['partition-over-2gib']['message'])
        self.assertIn('DW1 starts at %d' % (2304 * MIB + wv.RDB_BYTES), rows['start-past-2gib']['message'])
        self.assertIn('drive selftest.hdf (planned) is %d bytes' % (4096 * MIB + wv.RDB_BYTES),
                      rows['drive-over-4gib']['message'])
        # Just under every limit: 1 GiB - 1 byte file, 1920 MiB partitions, a start at 1920 MiB + 32 KiB,
        # a 3840 MiB + 32 KiB drive (the largest the 128 MiB partition grid allows).
        legal = rows['largest-legal']
        self.assertEqual(legal['outcome'], 'passed')
        self.assertEqual(legal['drives'], [dict(file='selftest.hdf', bytes=3840 * MIB + wv.RDB_BYTES,
                                                starts=[wv.RDB_BYTES, 1920 * MIB + wv.RDB_BYTES],
                                                partitions=[1920 * MIB, 1920 * MIB])])
        self.assertEqual(rows['wiring']['outcome'], 'skipped')
        self.assertEqual(lines[-1], 'Disk layout self-test: cleaned 19 dummy files')
        self.assert_clean()
        # Seconds, and the dummies are holes: GiBs apparent, almost nothing on disk.
        self.assertLess(time.monotonic() - started, 30)
        for name, row in rows.items():
            if row.get('disk_bytes') is not None and name != 'wiring':
                with self.subTest(case=name):
                    self.assertGreater(row['apparent_bytes'], 1024**3)
                    self.assertLess(row['disk_bytes'], 4 * MIB)

    def test_the_cases_cover_all_four_limits_and_a_pass(self):
        expects = [c['expect'] or '' for c in layout_selftest.CASES]
        for limit in ('1 GiB', 'is %d bytes' % (2048 * MIB), 'starts at', '4 GiB'):
            self.assertTrue(any(limit in e for e in expects), limit)
        self.assertTrue(any(c['expect'] is None and not c['write'] for c in layout_selftest.CASES))

    def test_a_refused_plan_never_reaches_a_writer(self):
        # The same refusals with writing switched on: no partition, boot partition or drive is written.
        cases = [dict(copy.deepcopy(c), write=True) for c in layout_selftest.CASES if c['expect']]
        fail = AssertionError('a writer ran for a refused layout')
        with patch.object(wv, '_pack_batch', side_effect=fail), \
                patch.object(wv, 'write_boot_partition', side_effect=fail), \
                patch.object(wv, 'assemble_drives', side_effect=fail):
            ok, rows, lines = run(self.scratch, cases=cases, xdftool='xdftool', rdbtool='rdbtool')
        self.assertTrue(ok, '\n'.join(lines))
        self.assertTrue(all(r['outcome'] == 'refused' for r in rows.values()))
        self.assert_clean()

    def test_the_real_grouping_keeps_the_forced_layouts_legal(self):
        for spec in layout_selftest.CASES:
            if spec['groups'] is None:
                continue
            with self.subTest(case=spec['name']):
                with patch.object(wv, 'plan_drives', wraps=wv.plan_drives) as planned:
                    run(self.scratch, cases=[spec], write=False)
                # First call: the real grouping (passes); second: the forced one (refused).
                self.assertEqual(planned.call_count, 2)
                self.assertIsNone(planned.call_args_list[0].kwargs.get('groups'))
                self.assertIsNotNone(planned.call_args_list[1].kwargs.get('groups'))

    def test_dummies_are_removed_when_a_case_raises(self):
        for error in (RuntimeError('boom'), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                lines = []
                with patch.object(wv, 'plan_drives', side_effect=error), self.assertRaises(type(error)):
                    layout_selftest.selftest(self.scratch, write=False, log=lines.append)
                self.assert_clean()
                self.assertRegex(lines[-1], r'^Disk layout self-test: cleaned [1-9]\d* dummy files$')

    def test_world_partition_writer_refuses_a_large_file_before_writing(self):
        # partition_batches admits a 1.2 GiB map (its budget is 1.5 GiB); the writer's own plan gate
        # refuses it before xdftool copies a byte.
        big = layout_selftest.sparse(self.scratch / 'maps' / 'vf0000.bsp', 1200 * MIB)
        _, batches = wv.partition_batches([big], 1)
        with patch.object(wv, '_pack_batch', side_effect=AssertionError('written')), \
                self.assertRaisesRegex(ValueError, 'file id1/maps/vf0000.bsp is %d bytes' % (1200 * MIB)):
            wv.write_partitions(batches, self.scratch, 'xdftool')

    def test_builder_mode_runs_the_self_test(self):
        import build
        with patch.object(layout_selftest, 'main', return_value=0) as selftest:
            self.assertEqual(build.main(['--layout-selftest']), 0)
        selftest.assert_called_once()

    def test_command_line_reports_the_cleanup(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = layout_selftest.main(['--no-write', '--scratch', str(self.scratch)])
        self.assertEqual(code, 0)
        self.assertIn('Disk layout self-test: cleaned 19 dummy files', out.getvalue())
        self.assertIn('Disk layout self-test: passed', out.getvalue())
        self.assert_clean()

    @unittest.skipUnless(HAVE_AMITOOLS, 'needs amitools (xdftool, rdbtool)')
    def test_wiring_case_writes_reads_back_and_gates_real_drives(self):
        started = time.monotonic()
        spec = next(c for c in layout_selftest.CASES if c['name'] == 'wiring')
        ok, rows, lines = run(self.scratch, cases=[spec], xdftool=XDFTOOL, rdbtool=RDBTOOL)
        self.assertTrue(ok, '\n'.join(lines))
        layout = rows['wiring']['disk_layout']
        self.assertEqual(len(layout), 1)
        self.assertEqual([p['partition'] for p in layout[0]['partitions']], ['DH0', 'DW0'])
        self.assertEqual(layout[0]['partitions'][1]['start_bytes'], 128 * MIB + wv.RDB_BYTES)
        self.assertEqual(layout[0]['partitions'][1]['largest_file'], 'id1/maps/vf0000.bsp')
        self.assertEqual(layout[0]['bytes'], 256 * MIB + wv.RDB_BYTES)
        self.assert_clean()
        self.assertLess(time.monotonic() - started, 60)


class ImageStepUsesThePlanGate(unittest.TestCase):
    def test_image_step_gates_the_plan_before_writing_and_the_drives_as_written(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image('):]
        plan = finalize.index('drive_plans=plan_drives(')
        self.assertLess(finalize.index('world_images=pack_world_volumes('), plan)
        self.assertLess(plan, finalize.index('write_boot_partition('))
        self.assertLess(finalize.index('write_boot_partition('), finalize.index('assemble_drives('))
        self.assertIn('partition_mib=planned_mib(payload_bytes)', finalize)

    def test_planned_partitions_match_their_writers(self):
        # The plan and the writers size partitions with the same function.
        for payload in (0, 1, 100 * MIB, 1500 * MIB, 1588 * MIB):
            self.assertEqual(wv.planned_partition('DW0', [dict(path='a', bytes=payload)])['bytes'],
                             wv.partition_mib(payload) * MIB)
        self.assertEqual(wv.partition_mib(1500 * MIB), 1920)
        self.assertEqual(wv.partition_mib(1600 * MIB), 2048)
        source = (ROOT / 'tools/world_volumes.py').read_text(encoding='utf-8')
        self.assertIn('mib=partition_mib(payload)', source)



class DryRunImageLayout(unittest.TestCase):
    """The asset-free --dry-run HDF passes the same disk-layout gate and records disk_layout."""

    @unittest.skipUnless(HAVE_AMITOOLS, 'needs amitools (xdftool, rdbtool)')
    def test_dry_run_image_is_read_back_and_gated(self):
        import subprocess
        import build_dry_run
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            boot = root / 'boot'
            (boot / 'C').mkdir(parents=True)
            payload = [boot / 'C' / 'AmiWind', boot / 'README.txt']
            payload[0].write_bytes(b'engine' * 1000)
            payload[1].write_bytes(b'notice text')
            part, image = root / 'partition.hdf', root / 'dry-run.hdf'
            # The dry run's own geometry: an 8 MiB DH0 on a chs=257,1,64 drive.
            subprocess.run([XDFTOOL, str(part), 'create', 'size=8Mi', '+', 'format', 'AMIWINDTEST', 'ffs',
                            '+', 'makedir', 'C', '+', 'write', str(payload[0]), 'C/AmiWind',
                            '+', 'write', str(payload[1]), 'README.txt'], check=True, stdout=subprocess.DEVNULL)
            from amiga_fs import check_image
            check_image(part, normalize=True)  # as the dry run does before rdbtool
            subprocess.run([RDBTOOL, str(image), 'create', 'chs=257,1,64', '+', 'init', '+', 'addimg', str(part),
                            'name=DH0', 'bootable=1', 'pri=0'], check=True, stdout=subprocess.DEVNULL)
            record = build_dry_run.gate_dry_run_image(image, boot, sorted(payload))
            self.assertTrue(record['ok'])
            self.assertEqual(record['file'], 'dry-run.hdf')
            self.assertEqual(record['bytes'], 8 * MIB + wv.RDB_BYTES)
            self.assertEqual(record['partitions'][0]['partition'], 'DH0')
            self.assertEqual(record['partitions'][0]['start_bytes'], wv.RDB_BYTES)
            self.assertEqual(record['partitions'][0]['largest_file'], 'C/AmiWind')
            # Over a limit, the dry run is refused like any image (a limit lowered for the test).
            refusal = 'drive dry-run.hdf is %d bytes' % (8 * MIB + wv.RDB_BYTES)
            with patch.object(wv, 'DRIVE_SIZE_LIMIT', 4 * MIB), self.assertRaisesRegex(ValueError, refusal):
                build_dry_run.gate_dry_run_image(image, boot, sorted(payload))

    def test_dry_run_build_gates_its_image_and_records_the_layout(self):
        source = (ROOT / 'tools/build_dry_run.py').read_text(encoding='utf-8')
        build = source[source.index('def build('):]
        self.assertLess(build.index("'addimg'"),
                        build.index('disk_layout = [gate_dry_run_image(image, boot, payload)]'))
        self.assertIn("'disk_layout': disk_layout,", build)
        gate = source[source.index('def gate_dry_run_image('):source.index('def build(')]
        for call in ('verify_combined(', 'require_mountable(', 'require_disk_layout('):
            self.assertIn(call, gate)


if __name__ == '__main__':
    unittest.main()
