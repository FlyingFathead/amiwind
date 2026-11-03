"""KHUUL-HOP-STALL-59: every written drive is whole IDE cylinders (16 heads x 63 sectors), so an IDE port (the
emulated A1200 port, a real IDE drive) sees every block of the last partition. The v0.0.59-dev6 drive of 6,266,944
sectors showed 6217 cylinders (6,266,736 sectors) on IDE: Khuul's files at the end of AW_WORLD0 read as errors."""
import tempfile
import unittest
from pathlib import Path

from world_volumes import (IDE_CYLINDER_SECTORS, ide_cylinder_bytes, pad_to_ide_cylinders, require_ide_cylinders)

ROOT = Path(__file__).resolve().parents[1]
UNIT = IDE_CYLINDER_SECTORS * 512


class IdeCylinderTests(unittest.TestCase):
    def test_dev6_drive_size_rounds_up_past_its_last_partition(self):
        dev6 = 6266944 * 512                         # the v0.0.59-dev6 drive file
        dw0_end = 97920 * 64 * 512                   # its RDB's last cylinder (heads 1, sectors 64)
        self.assertGreater(dw0_end, dev6 // UNIT * UNIT)  # the fault: DW0 ended past the last whole IDE cylinder
        padded = ide_cylinder_bytes(dev6)
        self.assertEqual(padded % UNIT, 0)
        self.assertGreaterEqual(padded // UNIT * UNIT, dw0_end)
        self.assertLess(padded - dev6, UNIT)

    def test_pad_writes_zeros_and_keeps_the_data(self):
        with tempfile.TemporaryDirectory() as directory:
            drive = Path(directory) / 'd.hdf'
            drive.write_bytes(b'\x01' * (UNIT + 1000))
            added = pad_to_ide_cylinders(drive)
            data = drive.read_bytes()
            self.assertEqual(len(data), 2 * UNIT)
            self.assertEqual(added, UNIT - 1000)
            self.assertEqual(data[:UNIT + 1000], b'\x01' * (UNIT + 1000))
            self.assertEqual(set(data[UNIT + 1000:]), {0})
            self.assertEqual(pad_to_ide_cylinders(drive), 0)

    def test_gate_refuses_a_partition_past_the_last_cylinder(self):
        with self.assertRaises(ValueError):
            require_ide_cylinders('d.hdf', 6266944 * 512, [])
        with self.assertRaises(ValueError):
            require_ide_cylinders('d.hdf', 2 * UNIT, [dict(partition='DW0', offset_bytes=UNIT, bytes=UNIT + 512)])
        require_ide_cylinders('d.hdf', 2 * UNIT, [dict(partition='DW0', offset_bytes=UNIT, bytes=UNIT)])

    def test_plan_records_the_padded_size(self):
        from world_volumes import MIB, RDB_BYTES, plan_drives, planned_partition
        boot = planned_partition('DH0', [dict(path='a', bytes=MIB)])
        worlds = [planned_partition('DW0', [dict(path='b', bytes=3 * MIB)], volume='AW_WORLD0')]
        plan = plan_drives(boot, worlds, name=lambda i: 'd%d.hdf' % i)[0]
        self.assertEqual(plan['ide_bytes'] % UNIT, 0)
        self.assertGreaterEqual(plan['ide_bytes'], plan['bytes'])
        self.assertLess(plan['ide_bytes'] - plan['bytes'], UNIT)
        self.assertEqual(plan['layout']['bytes'], plan['ide_bytes'])
        self.assertGreaterEqual(plan['ide_bytes'] // UNIT * UNIT, RDB_BYTES + sum(m['bytes'] for m in plan['members']))

    def test_plan_stops_when_padding_crosses_the_4gib_limit(self):
        from unittest.mock import patch
        import world_volumes as wv
        boot = wv.planned_partition('DH0', [dict(path='a', bytes=wv.MIB)])
        worlds = [wv.planned_partition('DW0', [dict(path='b', bytes=3 * wv.MIB)], volume='AW_WORLD0')]
        base = wv.plan_drives(boot, worlds, name=lambda i: 'd%d.hdf' % i)[0]
        # a limit between the unpadded and the padded size: only the padded size breaks it
        limit = base['bytes'] + 1
        self.assertLess(limit, base['ide_bytes'])
        with patch.object(wv, 'DRIVE_SIZE_LIMIT', limit):
            with self.assertRaises(ValueError) as caught:
                wv.plan_drives(boot, worlds, name=lambda i: 'd%d.hdf' % i)
        self.assertIn('limit below', str(caught.exception))

    def test_assemble_drives_pads_and_gates_every_drive(self):
        source = (ROOT / 'tools' / 'world_volumes.py').read_text(encoding='utf-8')
        body = source[source.index('def assemble_drives('):]
        self.assertLess(body.index('run(command)'), body.index('pad_to_ide_cylinders(drive)'))
        self.assertLess(body.index('pad_to_ide_cylinders(drive)'), body.index('verify_combined('))
        self.assertIn('require_disk_layout(drive.name, drive.stat().st_size, checked, partitions)', body)
        self.assertNotIn('require_ide_cylinders(drive.name', body)     # one gate, not a separate late check

    def test_the_image_layout_gate_has_every_rule_and_names_every_failure(self):
        import world_volumes as wv
        parts = [dict(partition='DH0', files=[]), dict(partition='DW1', files=[])]
        # a drive of 4 GiB + 1 sector, DW1 starting at 2 GiB and ending past the last whole cylinder, one partition
        # missing from the table: every failing rule is named in the one refusal
        drive = wv.DRIVE_SIZE_LIMIT + 512
        receipts = [dict(partition='DW1', offset_bytes=wv.PARTITION_START_LIMIT, bytes=drive)]
        with self.assertRaises(ValueError) as caught:
            wv.require_disk_layout('d.hdf', drive, receipts, parts)
        text = str(caught.exception)
        for rule in ('limit below %d, 4 GiB' % wv.DRIVE_SIZE_LIMIT, 'starts at %d' % wv.PARTITION_START_LIMIT,
                     'the partition table holds', 'not whole IDE cylinders', 'past the last whole IDE cylinder'):
            self.assertIn(rule, text)
        # and a legal layout passes with the IDE rule in its record
        good = wv.ide_cylinder_bytes(3 * wv.MIB)
        record = wv.require_disk_layout('d.hdf', good, [dict(partition='DH0', offset_bytes=wv.RDB_BYTES,
                                                           bytes=2 * wv.MIB)], [dict(partition='DH0', files=[])])
        self.assertEqual(record['limits']['ide_cylinder_sectors'], IDE_CYLINDER_SECTORS)


class ImagePathTests(unittest.TestCase):
    """IMAGE-IDE-CYLINDER-TAIL-59: every path that writes, copies or accepts a drive file keeps it whole cylinders."""

    def source(self, *parts):
        return (ROOT.joinpath(*parts)).read_text(encoding='utf-8')

    def test_the_check_tool_judges_drive_files_and_folders(self):
        import ide_cylinders
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.assertEqual(ide_cylinders.check_drives([folder])['verdict'], 'no-drives')
            (folder / 'good.hdf').write_bytes(b'\0' * (2 * UNIT))
            result = ide_cylinders.check_drives([folder])
            self.assertEqual((result['verdict'], result['drives'][0]['cylinders']), ('passed', 2))
            (folder / 'bad.hdf').write_bytes(b'\0' * (UNIT + 512))
            result = ide_cylinders.check_drives([folder])
            self.assertEqual(result['verdict'], 'failed')
            self.assertIn('bad.hdf', result['failing'][0])
            self.assertEqual(ide_cylinders.main(['check', str(folder / 'good.hdf')]), 0)
            self.assertEqual(ide_cylinders.main(['check', str(folder), '--json']), 1)

    def test_the_dry_run_image_is_padded_and_gated(self):
        body = self.source('tools', 'build_dry_run.py')
        self.assertLess(body.index("'create', 'chs=257,1,64'"), body.index('pad_to_ide_cylinders(image)'))
        self.assertLess(body.index('pad_to_ide_cylinders(image)'), body.index('check_image(image'))
        gate = body[body.index('def gate_dry_run_image'):body.index('def build(')]
        self.assertIn('require_disk_layout(image.name, image.stat().st_size, checked, partitions)', gate)

    def test_the_dry_run_size_rounds_up(self):
        self.assertEqual(ide_cylinder_bytes(257 * 64 * 512) % UNIT, 0)
        self.assertLess(ide_cylinder_bytes(257 * 64 * 512) - 257 * 64 * 512, UNIT)

    def test_the_music_disk_writer_pads_and_gates(self):
        body = self.source('tools', 'disk_image.py')
        self.assertLess(body.index('subprocess.run(command, check=True'), body.index('pad_to_ide_cylinders(image)'))
        self.assertIn('require_ide_cylinders(image.name, image.stat().st_size, [])', body)

    def test_emulator_templates_state_no_geometry_and_the_drive_decides(self):
        # the generated WinUAE line leaves cylinders, heads and sectors at 0: the RDB of the (padded) drive decides
        body = self.source('tools', 'emulator_configs.py')
        self.assertIn("hardfile2=rw,DH{i}:{disk},0,0,0,512,0,,uae{i}", body)
        for template in (ROOT / 'resources' / 'emulators').glob('AmiWind-v0.0.59-dev6-*'):
            text = template.read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(?m)^(hardfile2|uaehf\d+)=.*,\d+,\d+,\d+,512', template.name)
            self.assertNotRegex(text.lower(), r'\bide\b', template.name)

    def test_the_pi_image_script_refuses_a_drive_that_is_not_whole_cylinders(self):
        body = self.source('tools', 'pi_image', 'make_pi_image.sh')
        self.assertIn('% 516096', body)
        self.assertEqual(UNIT, 516096)
        self.assertLess(body.index('% 516096'), body.index('cp "$HDF"'))

    def test_the_gate_smoke_refuses_a_fixture_that_is_not_whole_cylinders_before_booting(self):
        # tools/engine_smoke.py is what the gate's boot smoke runs: its prep step checks
        # every drive of the smoke image folder before the play copy is made (gate 6414, 3 November 2026)
        import engine_smoke
        body = self.source('tools', 'engine_smoke.py')
        self.assertEqual(engine_smoke.IDE_CYLINDER_BYTES, UNIT)
        self.assertLess(body.index('ide-cylinders=FAILED'), body.index('dd if="$B"'))
        self.assertLess(body.index('bad = re.search('), body.index("world = re.search("))
        self.assertIn("print('smoke-exit=2')", body[body.index('bad = re.search('):body.index("world = re.search(")])

    def test_the_master_builder_runs_the_check_on_every_built_image(self):
        body = self.source('tools', 'aw_service.py')
        self.assertIn("'tools/ide_cylinders.py', 'check', run_dir + '/image'", body)
        self.assertIn("steps['ide-cylinders'] = ide_cylinders_result(", body)
        self.assertIn("'ide-cylinders' if steps.get('ide-cylinders'", body)


if __name__ == '__main__':
    unittest.main()
