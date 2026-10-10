"""Emulator launch boundaries; synthetic files and a harmless stub executable."""
import contextlib
import errno
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build
import run_fs_uae as runner
import setup_build
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ (env_guard) when run as a file
import env_guard  # noqa: E402


def symlink_or_skip(link, target, **kwargs):
    """Retain real symlink coverage wherever the host permits creation."""
    try:
        link.symlink_to(target, **kwargs)
    except NotImplementedError as exc:
        raise unittest.SkipTest('Host does not support symlink creation: ' + str(exc))
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314 or exc.errno in (errno.EACCES, errno.EPERM, errno.ENOTSUP):
            raise unittest.SkipTest('Host cannot create test symlinks: ' + str(exc))
        raise


@env_guard.isolated  # build.main exports AMIWIND_* switches (TEST-ENV-LEAK-HULL-33)
class FsUaeTests(unittest.TestCase):
    def test_missing_emulator_stops_before_setup_or_conversion(self):
        output = io.StringIO()
        with patch.object(runner.shutil, 'which', return_value=None), \
             patch.object(setup_build, 'use_environment') as environment, \
             patch.object(build, 'prerequisites') as prerequisites, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as error:
                build.main(['--autoinstall', '--autorun-fs-uae', '--builder', 'legacy'])
        self.assertEqual(error.exception.code, 1)
        environment.assert_not_called()
        prerequisites.assert_not_called()
        self.assertIn(runner.FS_UAE_URL, output.getvalue())

    def test_default_rom_and_matching_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            rom = home / '.roms/kickstart-3.1-a1200.rom'
            rom.parent.mkdir()
            rom.write_bytes(b'synthetic ROM fixture')
            output = io.StringIO()
            with patch.object(runner.Path, 'home', return_value=home), \
                 patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 patch.object(runner, 'REFERENCE_ROM_SHA256', hashlib.sha256(rom.read_bytes()).hexdigest()), \
                 contextlib.redirect_stdout(output):
                _, selected = runner.prepare_launch()
            self.assertEqual(selected, rom)
            self.assertIn('matches the owner-tested', output.getvalue())
            self.assertEqual(list(home.rglob('*.fs-uae')), [])

    def test_missing_rom_fails_and_different_rom_warns(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            rom = Path(tmp) / 'owned.rom'
            with self.assertRaisesRegex(ValueError, '--kickstart-file PATH'):
                runner.prepare_launch(rom)
            rom.write_bytes(b'unrecognized fixture')
            runner.prepare_launch(rom)
            self.assertIn('compatibility is unverified', output.getvalue())

    def test_missing_default_rom_prompts_and_fills_selected_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            rom = home / 'ROMs/my Kickstart.rom'
            rom.parent.mkdir()
            rom.write_bytes(b'synthetic owned ROM')
            with patch.object(runner.Path, 'home', return_value=home), \
                 patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 patch('builtins.input', return_value=f'"{rom}"') as prompt, \
                 contextlib.redirect_stdout(io.StringIO()):
                _, selected = runner.prepare_launch(interactive=True)
            prompt.assert_called_once()
            self.assertEqual(selected, rom)
            config = runner.configuration(Path('/private/demo.hdf'), selected)
            self.assertIn(f'kickstart_file = {rom}\n', config)
            self.assertNotIn('/path/to/your/', config)

    def test_directory_finds_renamed_reference_without_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rom = directory / 'renamed.bin'
            rom.write_bytes(b'R' * (512 * 1024))
            (directory / 'other.rom').write_bytes(b'X' * (512 * 1024))
            with patch.object(runner, 'REFERENCE_ROM_SHA256', runner.rom_sha256(rom)), \
                 patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 patch('builtins.input') as prompt, contextlib.redirect_stdout(io.StringIO()):
                _, selected = runner.prepare_launch(directory, interactive=True)
            self.assertEqual(selected, rom)
            prompt.assert_not_called()

    def test_directory_no_match_prompts_for_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            rom = directory / 'other.rom'
            rom.write_bytes(b'unrecognized owned ROM')
            with patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 patch('builtins.input', return_value=str(rom)) as prompt, \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, '--kickstart-file PATH'):
                    runner.prepare_launch(directory)
                _, selected = runner.prepare_launch(directory, interactive=True)
            self.assertEqual(selected, rom)
            prompt.assert_called_once()
            self.assertIn('Directory or file', prompt.call_args.args[0])

    def test_default_directory_and_duplicate_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            directory = home / '.roms'
            directory.mkdir()
            rom = directory / 'a.rom'
            rom.write_bytes(b'R' * (512 * 1024))
            (directory / 'b.rom').write_bytes(rom.read_bytes())
            with patch.object(runner.Path, 'home', return_value=home), \
                 patch.object(runner, 'REFERENCE_ROM_SHA256', runner.rom_sha256(rom)), \
                 patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                _, selected = runner.prepare_launch()
            self.assertEqual(selected, rom)
            self.assertIn('byte-identical', output.getvalue())

    def test_directory_scan_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'nested').mkdir()
            rom = directory / 'nested/owned.rom'
            rom.write_bytes(b'R' * (512 * 1024))
            symlink_or_skip(directory / 'linked.rom', rom)
            with patch.object(runner, 'REFERENCE_ROM_SHA256', runner.rom_sha256(rom)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(runner.select_rom(directory))

    def test_directory_scan_skips_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); (directory / 'nested').mkdir()
            rom = directory / 'nested/owned.rom'; rom.write_bytes(b'R' * (512 * 1024))
            with patch.object(runner, 'REFERENCE_ROM_SHA256', runner.rom_sha256(rom)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(runner.select_rom(directory))

    def test_explicit_kickstart_file_is_accepted_without_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom = Path(tmp) / 'owned.rom'
            rom.write_bytes(b'synthetic owned ROM')
            args = build.parser().parse_args(['--autorun-fs-uae', '--kickstart-file', str(rom)])
            with patch.object(runner.shutil, 'which', return_value='/usr/bin/fs-uae'), \
                 patch('builtins.input') as prompt, contextlib.redirect_stdout(io.StringIO()):
                _, selected = runner.prepare_launch(args.kickstart_file, interactive=True)
            prompt.assert_not_called()
            self.assertEqual(selected, rom)

    @unittest.skipUnless(os.name == 'posix', 'POSIX executable script integration')
    def test_launch_uses_documented_preset_and_preserves_space_paths(self):
        with tempfile.TemporaryDirectory(prefix='amiwind launch ') as tmp:
            base = Path(tmp)
            image, rom = base / 'demo image.hdf', base / 'owned ROM.rom'
            image.write_bytes(b'synthetic HDF')
            rom.write_bytes(b'synthetic ROM')
            stub = base / 'fs-uae'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$0.args"\n')
            stub.chmod(0o755)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.launch(image, str(stub), rom), 0)
            config = image.with_suffix('.fs-uae')
            self.assertEqual(Path(str(stub) + '.args').read_text().splitlines(), [str(config)])
            text = config.read_text()
            self.assertIn(f'hard_drive_0 = {image}\n', text)
            self.assertIn(f'kickstart_file = {rom}\n', text)
            self.assertIn('cpu = 68040-NOMMU\n', text)
            self.assertIn('zorro_iii_memory = 16384\n', text)
            # Reuse identical generated config; preserve a user's later edits.
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.launch(image, str(stub), rom), 0)
            config.write_text('my custom config\n')
            with self.assertRaisesRegex(ValueError, 'preserved unchanged'):
                runner.launch(image, str(stub), rom)
            self.assertEqual(config.read_text(), 'my custom config\n')

    def test_disappeared_emulator_leaves_hdf_and_config(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as output:
            image = Path(tmp) / 'demo.hdf'
            image.write_bytes(b'synthetic HDF')
            self.assertEqual(runner.launch(image, str(Path(tmp) / 'missing'), Path(tmp) / 'owned.rom'), 1)
            self.assertTrue(image.is_file())
            self.assertTrue(image.with_suffix('.fs-uae').is_file())
            self.assertIn('launch skipped', output.getvalue())

    def test_check_and_plan_do_not_launch_or_write_config(self):
        for mode in ('--check', '--plan'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(runner, 'prepare_launch', return_value=('/fs-uae', Path('/owned.rom'))), \
                 patch.object(runner, 'launch') as launch, \
                 patch.object(setup_build, 'use_environment'), \
                 patch.object(build, 'prerequisites', return_value={}), \
                 patch.object(build, 'commands', return_value=[]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build.main([mode, '--autorun-fs-uae', '--workspace', tmp, '--builder', 'legacy']), 0)
                launch.assert_not_called()
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_build_failure_never_launches(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runner, 'prepare_launch', return_value=('/fs-uae', Path('/owned.rom'))), \
             patch.object(runner, 'launch') as launch, \
             patch.object(setup_build, 'use_environment'), \
             patch.object(build, 'prerequisites', return_value={}), \
             patch.object(build, 'commands', return_value=[]), \
             patch.object(build, 'provenance', return_value={}), \
             patch.object(build, 'execute', side_effect=RuntimeError('fixture failure')), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                build.main(['--autorun-fs-uae', '--workspace', tmp])
            self.assertEqual(error.exception.code, 1)
            launch.assert_not_called()

    def test_success_launches_new_image_and_launch_failure_keeps_build_success(self):
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(runner, 'prepare_launch', return_value=('/fs-uae', Path('/owned.rom'))), \
                 patch.object(runner, 'launch', return_value=1) as launch, \
                 patch.object(setup_build, 'use_environment'), \
                 patch.object(build, 'prerequisites', return_value={}), \
                 patch.object(build, 'dry_run_prerequisites', return_value={}), \
                 patch.object(build, 'commands', return_value=[]), \
                 patch.object(build, 'dry_run_commands', return_value=[]), \
                 patch.object(build, 'provenance', return_value={}), \
                 patch.object(build, 'execute') as execute, contextlib.redirect_stdout(io.StringIO()) as output:
                argv = ['--autorun-fs-uae', '--workspace', tmp, '--name', 'fixture', '--any-run-name', '--builder', 'legacy']
                if dry_run:
                    argv.append('--dry-run')
                suffix = '-dry-run' if dry_run else ''
                image = Path(tmp) / 'build/fixture/image' / f'AmiWind-v{build.VERSION}{suffix}.hdf'
                def complete(*args):
                    image.parent.mkdir(parents=True)
                    image.write_bytes(b'synthetic completed HDF')
                execute.side_effect = complete
                self.assertEqual(build.main(argv), 0)
                launch.assert_called_once_with(Path(tmp) / 'build/fixture/image' /
                    f'AmiWind-v{build.VERSION}{suffix}.hdf', '/fs-uae', Path('/owned.rom'))
                self.assertIn('Build succeeded', output.getvalue())


if __name__ == '__main__':
    unittest.main()
