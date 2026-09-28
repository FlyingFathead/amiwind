"""Portable launcher tests with synthetic disks/ROMs and a fake emulator."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/AmiWind-FS-UAE-launcher.py'
spec = importlib.util.spec_from_file_location('portable_launcher', SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='amiwind-launcher-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.add_image('0.0.19')
        (self.root / 'roms').mkdir()
        self.rom = self.root / 'roms/owned.rom'
        self.rom.write_bytes(b'R' * 524288)

    def add_image(self, version):
        path = self.root / ('AmiWind-v' + version + '.hdf')
        path.write_bytes(b'synthetic HDF fixture')
        return path

    def run_main(self, args=(), answers=('',)):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), \
             patch('builtins.input', side_effect=answers):
            status = launcher.main(['--directory', str(self.root)] + list(args))
        return status, output.getvalue()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_numeric_latest_and_prerelease_order(self):
        for v in ('0.0.9', '0.0.20-rc10', '0.0.20-dev2', '0.0.20', '0.0.20-beta3'):
            self.add_image(v)
        self.assertEqual(launcher.select_image(self.root)[1], '0.0.20')
        self.assertGreater(launcher.version_key('0.0.20-rc10'), launcher.version_key('0.0.20-rc2'))
        self.assertGreater(launcher.version_key('0.1.0'), launcher.version_key('0.0.999'))
        self.assertGreater(launcher.version_key('0.0.21-dev1'), launcher.version_key('0.0.20'))

    def test_interactive_latest_older_and_invalid_answer(self):
        newest = self.add_image('0.0.20')
        with patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(launcher.select_image(self.root, ask=True)[0], newest)
        self.assertIn('(suggested latest)', out.getvalue())
        with patch('builtins.input', side_effect=['bad', '3', '2']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.select_image(self.root, ask=True)[0], self.image)

    def test_cancel_and_eof_change_nothing(self):
        before = self.snapshot()
        for answer in ('n', EOFError()):
            status, output = self.run_main(answers=(answer,))
            self.assertEqual(status, 0)
            self.assertIn('Cancelled', output)
            self.assertEqual(self.snapshot(), before)

    def test_dates_break_ties_but_do_not_override_numeric_versions(self):
        a = self.add_image('0.0.20-dev-soandso')
        b = self.add_image('0.0.20-dev-experiment')
        os.utime(a, (100, 100))
        os.utime(b, (200, 200))
        os.utime(self.image, (300, 300))
        self.assertEqual(launcher.select_image(self.root)[0], b)
        os.utime(a, (400, 400))
        self.assertEqual(launcher.select_image(self.root)[0], a)
        numeric = self.add_image('0.0.20-dev10')
        os.utime(numeric, (50, 50))
        self.assertEqual(launcher.select_image(self.root)[0], numeric)
        release = self.add_image('0.0.20')
        os.utime(release, (25, 25))
        self.assertEqual(launcher.select_image(self.root)[0], release)

    def test_numbered_test_suffix_and_natural_filename_fallback(self):
        self.add_image('0.0.20-test-9')
        newest = self.add_image('0.0.20-test-10')
        self.assertEqual(launcher.select_image(self.root)[0], newest)
        self.assertGreater(launcher.natural_key('experiment10'), launcher.natural_key('experiment9'))

    def test_working_copy_only_selected_explicitly(self):
        working = self.root / 'AmiWind-v0.0.20-play.hdf'
        working.write_bytes(b'working copy')
        self.assertEqual(launcher.select_image(self.root)[0], self.image)
        self.assertEqual(launcher.select_image(self.root, working.name), (working, '0.0.20'))

    def test_empty_or_missing_hdf_fails_without_mutation(self):
        self.add_image('0.0.20').write_bytes(b'')
        before = self.snapshot()
        self.assertEqual(self.run_main(['--configure-only'])[0], 1)
        self.assertEqual(self.snapshot(), before)
        self.image.unlink()
        (self.root / 'AmiWind-v0.0.20.hdf').unlink()
        self.assertEqual(self.run_main(['--configure-only'])[0], 1)

    def test_reference_rom_recognized_under_any_name(self):
        renamed = self.rom.with_name('renamed-kickstart.dump')
        self.rom.rename(renamed)
        (self.root / 'roms/other.rom').write_bytes(b'X' * 524288)
        with patch.object(launcher, 'REFERENCE_ROM_SHA256', hashlib.sha256(renamed.read_bytes()).hexdigest()), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(launcher.select_rom(self.root), renamed)
        self.assertIn('SHA-256 matches', output.getvalue())

    def test_unknown_rom_warns_and_configures(self):
        status, output = self.run_main(['--configure-only'])
        self.assertEqual(status, 0)
        self.assertIn('[warn]', output)
        self.assertIn(launcher.REFERENCE_ROM_SHA256, output)
        self.assertIn(hashlib.sha256(self.rom.read_bytes()).hexdigest(), output)

    def test_ambiguous_roms_need_explicit_selection(self):
        other = self.root / 'roms/other.rom'
        other.write_bytes(b'O' * 524288)
        before = self.snapshot()
        self.assertEqual(self.run_main(['--configure-only'])[0], 1)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.run_main(['--configure-only', '--rom', 'roms/other.rom'])[0], 0)

    def test_missing_or_invalid_rom_preserves_files(self):
        self.rom.write_bytes(b'not a ROM')
        before = self.snapshot()
        self.assertEqual(self.run_main(['--configure-only'])[0], 1)
        self.assertEqual(self.snapshot(), before)

    def test_missing_rom_prompts_then_remembers_selection(self):
        alternate = self.root / 'alternate roms'
        alternate.mkdir()
        self.rom.rename(alternate / self.rom.name)
        with patch.object(launcher.shutil, 'which', return_value='/fake/fs-uae'), \
             patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            status, output = self.run_main(answers=('', '"alternate roms"'))
        self.assertEqual(status, 0, output)
        settings = json.loads((self.root / launcher.SETTINGS_NAME).read_text())
        self.assertEqual(settings['kickstart_rom'], 'alternate roms/owned.rom')

    def test_rom_prompt_cancel_writes_nothing(self):
        self.rom.unlink()
        before = self.snapshot()
        self.assertEqual(self.run_main(answers=('', ''))[0], 0)
        self.assertEqual(self.snapshot(), before)

    def test_saved_settings_use_latest_and_relative_rom(self):
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        settings = json.loads((self.root / launcher.SETTINGS_NAME).read_text())
        self.assertEqual(settings['hdf'], 'latest')
        self.assertEqual(settings['kickstart_rom'], 'roms/owned.rom')
        self.assertTrue(settings['confirm_launch'])
        self.add_image('0.0.20')
        status, output = self.run_main(['--configure-only'])
        self.assertEqual(status, 0)
        self.assertIn('AmiWind v0.0.20', output)

    def test_one_time_image_choice_does_not_pin_default(self):
        self.add_image('0.0.20')
        self.assertEqual(self.run_main(['--configure-only', '--hdf', self.image.name])[0], 0)
        self.assertEqual(json.loads((self.root / launcher.SETTINGS_NAME).read_text())['hdf'], 'latest')
        self.assertIn('AmiWind v0.0.20', self.run_main(['--configure-only'])[1])

    def test_edited_settings_can_pin_image_and_skip_confirmation(self):
        self.add_image('0.0.20')
        (self.root / launcher.SETTINGS_NAME).write_text(json.dumps({
            'hdf': self.image.name, 'confirm_launch': False, 'kickstart_rom': 'roms/owned.rom'}))
        with patch.object(launcher.shutil, 'which', return_value='/fake/fs-uae'), \
             patch.object(launcher.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            status, output = self.run_main(answers=())
        self.assertEqual(status, 0)
        self.assertIn('AmiWind v0.0.19', output)

    def test_invalid_settings_preserved(self):
        path = self.root / launcher.SETTINGS_NAME
        for text in ('{', '[]', '{"hdf": "latest", "hdf": "other"}',
                     '{"unknown": 1}', '{"format": true}', '{"confirm_launch": "false"}',
                     '{"kickstart_rom": 42}'):
            path.write_text(text)
            before = self.snapshot()
            self.assertEqual(self.run_main(['--configure-only'])[0], 1)
            self.assertEqual(self.snapshot(), before)

    def test_existing_configs_not_rewritten_on_rerun(self):
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        paths = [self.root / launcher.SETTINGS_NAME, self.root / 'AmiWind-v0.0.19-FS-UAE.fs-uae']
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in paths], before)
        self.assertFalse((self.root / 'resources/emulators/backups').exists())

    def test_template_custom_options_and_legacy_repair(self):
        template = self.root / 'resources/emulators/AmiWind-v0.0.19-FS-UAE.fs-uae'
        template.parent.mkdir(parents=True)
        template.write_text('# custom comment\n[config]\nfullscreen = 1\nuae_address_space_24 = false\n'
                            'kickstart_file = /old.rom\nhard_drive_0 = /old.hdf\n[other]\nvalue = keep\n')
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        result = (self.root / template.name).read_text()
        self.assertIn('fullscreen = 1', result)
        self.assertIn('# custom comment', result)
        self.assertIn('[other]\nvalue = keep', result)
        self.assertIn('uae_cpu_24bit_addressing = false', result)
        self.assertNotIn('uae_address_space_24', result)
        self.assertIn('hard_drive_0 = ' + str(self.image), result)

    def test_moved_directory_repairs_paths_keeps_old_config(self):
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        config_name = 'AmiWind-v0.0.19-FS-UAE.fs-uae'
        before = (self.root / config_name).read_bytes()
        moved = self.root / 'moved folder'
        moved.mkdir()
        for p in list(self.root.iterdir()):
            if p != moved:
                shutil.move(str(p), moved / p.name)
        self.root = moved
        self.assertEqual(self.run_main(['--configure-only'])[0], 0)
        self.assertIn(str(moved / self.image.name), (moved / config_name).read_text())
        backups = list((moved / 'resources/emulators/backups').glob('*.bak'))
        self.assertEqual([p.read_bytes() for p in backups], [before])

    def test_bad_existing_emulator_config_is_preserved(self):
        cfg = self.root / 'AmiWind-v0.0.19-FS-UAE.fs-uae'
        for text in ('no section\n', '[config]\nx=1\nx=2\n',
                     '[config]\nkickstart_file = /old\n  continuation\n',
                     '[config]\nuae_address_space_24 = false\n  continuation\n',
                     '[DEFAULT]\nx=1\n[config]\n'):
            cfg.write_text(text)
            before = self.snapshot()
            self.assertEqual(self.run_main(['--configure-only'])[0], 1)
            self.assertEqual(self.snapshot(), before)

    def test_symlink_config_and_settings_are_not_replaced(self):
        for name in (launcher.SETTINGS_NAME, 'AmiWind-v0.0.19-FS-UAE.fs-uae'):
            target = self.root / 'target'
            target.write_text('{}' if name.endswith('.json') else '[config]\n')
            link = self.root / name
            link.symlink_to(target)
            before = target.read_bytes()
            self.assertEqual(self.run_main(['--configure-only'])[0], 1)
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(link.is_symlink())
            link.unlink()

    def test_missing_emulator_changes_nothing(self):
        before = self.snapshot()
        with patch.object(launcher.shutil, 'which', return_value=None):
            status, output = self.run_main(['--yes'])
        self.assertEqual(status, 1)
        self.assertIn('FS-UAE was not found', output)
        self.assertEqual(self.snapshot(), before)

    def test_failed_config_replace_retains_original_and_backup(self):
        cfg = self.root / 'AmiWind-v0.0.19-FS-UAE.fs-uae'
        before = b'[config]\nfullscreen = 1\n'
        cfg.write_bytes(before)
        with patch.object(launcher.os, 'replace', side_effect=OSError('simulated replace failure')):
            self.assertEqual(self.run_main(['--configure-only'])[0], 1)
        self.assertEqual(cfg.read_bytes(), before)
        backups = list((self.root / 'resources/emulators/backups').glob('*.bak'))
        self.assertEqual([p.read_bytes() for p in backups], [before])
        self.assertFalse(list(self.root.glob('.amiwind-config-*.tmp')))

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_actual_process_spaces_literal_argv_and_exit_status(self):
        root = self.root / 'playable $(touch NEVER_CREATED); space'
        root.mkdir()
        shutil.copy2(self.image, root / self.image.name)
        (root / 'roms').mkdir()
        shutil.copy2(self.rom, root / 'roms/owned.rom')
        script = root / SCRIPT.name
        shutil.copy2(SCRIPT, script)
        executable = root / 'fake emulator'
        executable.write_text('#!' + sys.executable + '\nimport json, os, sys\n'
                              'from pathlib import Path\n'
                              'Path("launch.json").write_text(json.dumps({"argv":sys.argv[1:],"cwd":os.getcwd()}))\n'
                              'sys.exit(7)\n')
        executable.chmod(0o755)
        for args in (['--fs-uae', './fake emulator'], []):
            run = subprocess.run([sys.executable, str(script), '--yes'] + args,
                                 cwd=self.root, capture_output=True, text=True)
            self.assertEqual(run.returncode, 7, run.stdout + run.stderr)
            self.assertIn('[warn]', run.stdout)
            record = json.loads((root / 'launch.json').read_text())
            self.assertEqual(record, {'argv': [str(root / 'AmiWind-v0.0.19-FS-UAE.fs-uae')], 'cwd': str(root)})
        self.assertFalse((self.root / 'NEVER_CREATED').exists())
        self.assertEqual((root / self.image.name).read_bytes(), self.image.read_bytes())
        self.assertEqual((root / 'roms/owned.rom').read_bytes(), self.rom.read_bytes())


if __name__ == '__main__':
    unittest.main()
