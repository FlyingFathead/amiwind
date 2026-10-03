import configparser
import contextlib
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from emulator_configs import write_configs, launcher, print_outputs, VERSION
import run_fs_uae


class EmulatorConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='amiwind multi disk ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / f'AmiWind-v{VERSION}.hdf'
        self.image.write_bytes(b'boot fixture')
        self.world = self.root / f'AmiWind-v{VERSION}-world-01.hdf'
        self.world.write_bytes(b'world fixture')
        self.record = dict(version=VERSION, hdf_file=self.image.name, hdf_files=[
            dict(file=self.image.name, bytes=self.image.stat().st_size, bootable=True, readback='passed'),
            dict(file=self.world.name, bytes=self.world.stat().st_size, bootable=False, readback='passed')])
        self.save()

    def save(self):
        (self.root / 'build.json').write_text(json.dumps(self.record), encoding='utf-8')

    def test_both_configs_mount_all_disks_and_use_lf(self):
        names = write_configs(self.image)
        fs, win = [self.root / name for name in names]
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(fs, encoding='utf-8')
        self.assertEqual(parser['config']['hard_drive_0'], str(self.image.resolve()))
        self.assertEqual(parser['config']['hard_drive_1'], str(self.world.resolve()))
        self.assertEqual(parser['config']['hard_drive_1_type'], 'hdf')
        lines = [line for line in win.read_text(encoding='utf-8').splitlines() if line.startswith('hardfile2=')]
        self.assertEqual(len(lines), 2)
        self.assertIn(str(self.image.resolve()), lines[0])
        self.assertIn(str(self.world.resolve()), lines[1])
        self.assertTrue(lines[0].endswith('uae0'))
        self.assertTrue(lines[1].endswith('uae1'))
        for p in (fs, win): self.assertNotIn(b'\r', p.read_bytes())
        self.assertEqual(write_configs(self.image), names)
        launched = run_fs_uae.configuration(self.image, self.root / 'owned.rom')
        self.assertIn('hard_drive_1 = ' + str(self.world.resolve()), launched)

    def test_terminal_footer_lists_all_disks_and_both_runners(self):
        self.record['emulator_configs'] = write_configs(self.image)
        self.save()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            paths = print_outputs(self.image)
        self.assertEqual(len(paths['hdf_files']), 2)
        self.assertEqual([p['emulator'] for p in paths['emulator_configs']], ['FS-UAE', 'WinUAE'])
        text = output.getvalue()
        for path in paths['hdf_files']: self.assertIn(path, text)
        for entry in paths['emulator_configs']: self.assertIn(entry['emulator'] + ': ' + entry['path'], text)
        self.assertIn('Your .hdf file(s):', text)
        self.assertIn('FS-UAE and WinUAE runners:', text)
        self.assertEqual(sum(line.startswith('---') for line in text.splitlines()), 2)

    def test_asset_free_output_also_has_both_configs(self):
        (self.root / 'build.json').unlink()
        self.world.unlink()
        (self.root / 'dry-run-build.json').write_text(json.dumps(dict(version=VERSION, hdf=self.image.name)), encoding='utf-8')
        names = write_configs(self.image)
        self.assertEqual(len(names), 2)
        self.assertTrue(all((self.root / name).is_file() for name in names))

    def test_host_export_configs_preserve_container_configs(self):
        old = self.root / (self.image.stem + '-FS-UAE.fs-uae')
        old.write_text('[config]\nhard_drive_0 = /work/container/disk.hdf\n', encoding='utf-8')
        names = write_configs(self.image, config_suffix='-Host')
        self.assertIn('/work/container/disk.hdf', old.read_text(encoding='utf-8'))
        self.assertIn(str(self.image.resolve()), (self.root / names[0]).read_text(encoding='utf-8'))
        self.assertIn(str(self.world.resolve()), (self.root / names[0]).read_text(encoding='utf-8'))

    def test_real_cli_generates_configs_and_prints_footer(self):
        script = Path(__file__).resolve().parents[1] / 'tools/emulator_configs.py'
        result = subprocess.run([sys.executable, '-B', str(script), '--image', str(self.image)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Your .hdf file(s):', result.stdout)
        self.assertIn('FS-UAE and WinUAE runners:', result.stdout)
        self.assertIn(str(self.world.resolve()), result.stdout)
        self.assertEqual(len(json.loads((self.root / 'build.json').read_text(encoding='utf-8'))['emulator_configs']), 2)

    def test_world_disk_is_never_selected_as_boot_image(self):
        portable = launcher()
        with self.assertRaisesRegex(ValueError, 'boot HDF'):
            portable.select_image(self.root, str(self.world))
        self.image.unlink()
        with self.assertRaisesRegex(ValueError, 'No AmiWind'):
            portable.select_image(self.root)

    def test_single_disk_receipt_is_compatible(self):
        self.record['hdf_files'] = self.record['hdf_files'][:1]
        self.save()
        names = write_configs(self.image)
        self.assertNotIn('hard_drive_1 =', (self.root / names[0]).read_text(encoding='utf-8'))
        self.assertEqual((self.root / names[1]).read_text(encoding='utf-8').count('hardfile2='), 1)

    def test_missing_required_world_fails_before_configs(self):
        self.world.unlink()
        with self.assertRaisesRegex(ValueError, 'Required HDF missing'):
            write_configs(self.image)
        self.assertEqual(list(self.root.glob('*.uae')), [])
        self.assertEqual(list(self.root.glob('*.fs-uae')), [])

    def test_traversal_duplicate_and_changed_size_rejected(self):
        for name in ('../escape.hdf', 'C:escape.hdf', self.image.name):
            with self.subTest(name=name):
                self.record['hdf_files'][1]['file'] = name
                self.save()
                with self.assertRaises(ValueError): write_configs(self.image)
        self.record['hdf_files'][1]['file'] = self.world.name
        self.record['hdf_files'][1]['bytes'] += 1
        self.save()
        with self.assertRaisesRegex(ValueError, 'verified layout'): write_configs(self.image)

    def test_missing_receipt_with_world_companion_is_not_single_disk(self):
        (self.root / 'build.json').unlink()
        with self.assertRaisesRegex(ValueError, 'layout receipt'):
            launcher().image_disks(self.image)

    def test_stale_mounts_replaced_and_custom_config_preserved(self):
        portable = launcher()
        text = '[config]\nhard_drive_0 = old\nhard_drive_1 = old\nhard_drive_5 = obsolete\nhard_drive_5_type = hdf\ncustom_option = keep\n'
        content = portable.configured_text(text, self.image, self.root / 'owned.rom')
        self.assertNotIn('hard_drive_5', content)
        self.assertIn('custom_option = keep', content)
        names = write_configs(self.image)
        win = self.root / names[1]
        win.write_text('user customization\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'preserved'): write_configs(self.image)
        self.assertEqual(win.read_text(encoding='utf-8'), 'user customization\n')


if __name__ == '__main__':
    unittest.main()
