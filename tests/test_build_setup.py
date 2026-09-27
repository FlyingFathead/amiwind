"""Dependency consent, input corruption, discovery and version boundaries."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import build
import build_versions
import install_dependencies
from mwad import input_check
from mwad.paths import ensure_external, installed_game_path, is_wsl
from test_workflow import synthetic_install


class BuildSetupTests(unittest.TestCase):
    def test_dependency_preview_and_decline_never_install_or_create(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--install-dependencies', '--tools-dir', str(Path(temp)/'tools')])
            for plan in (True, False):
                args.plan = plan
                with patch.object(install_dependencies, 'supported_host'), \
                     patch.object(install_dependencies, 'missing_packages', return_value=['ffmpeg']), \
                     patch.object(install_dependencies.os, 'geteuid', return_value=0), \
                     patch.object(install_dependencies.subprocess, 'check_output', return_value='3.12'), \
                     patch.object(install_dependencies.subprocess, 'run') as run, \
                     contextlib.redirect_stdout(io.StringIO()):
                    install_dependencies.install(args, confirm=lambda prompt:'no')
                    run.assert_not_called()
                self.assertFalse(args.tools_dir.exists())

    def test_confirmed_install_targets_only_the_selected_venv(self):
        with tempfile.TemporaryDirectory(prefix='amiwind tools ') as temp:
            args = build.parser().parse_args(['--install-dependencies', '--tools-dir', str(Path(temp)/'tools')])
            with patch.object(install_dependencies, 'supported_host'), \
                 patch.object(install_dependencies, 'missing_packages', return_value=[]), \
                 patch.object(install_dependencies.subprocess, 'check_output', return_value='3.12'), \
                 patch.object(install_dependencies.subprocess, 'run') as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                install_dependencies.install(args, confirm=lambda prompt:'yes')
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0][-1], str(args.tools_dir/'venv'))
            self.assertEqual(commands[1][0], str(args.tools_dir/'venv/bin/python'))
            self.assertNotIn('sudo', commands[1])

    def test_existing_unrelated_environment_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'venv').mkdir()
            args = build.parser().parse_args(['--install-dependencies', '--tools-dir', temp])
            with patch.object(install_dependencies, 'supported_host'), self.assertRaisesRegex(ValueError, 'non-venv'):
                install_dependencies.install(args)

    def test_version_order_and_unknown_suffix_are_not_optimistic(self):
        for actual, expected, status in [('2.10.0','2.9.0','newer'), ('2.8.9','2.9.0','older'),
                                         ('1.9d','1.9d','matching'), ('2.0f','1.9d','newer'),
                                         ('16.2.0b other','16.2.0b ref','unknown'),
                                         (None,'1.0','missing')]:
            self.assertEqual(build_versions.compare(actual, expected), status)

    def test_failed_version_probe_is_unknown(self):
        spec = {'version':'1.0','arguments':['--version'],'pattern':r'tool (\S+)'}
        with tempfile.TemporaryDirectory() as temp:
            tool = Path(temp)/'tool';tool.write_text('placeholder')
            with patch.object(build_versions.shutil, 'which', return_value=str(tool)), \
                 patch.object(build_versions.subprocess, 'run', side_effect=subprocess.TimeoutExpired('tool',10)):
                self.assertEqual(build_versions.probe('tool', str(tool), spec)['status'], 'unknown')

    def test_wsl_translation_preserves_spaces_and_is_not_a_shell(self):
        with patch('mwad.paths.is_wsl', return_value=True), \
             patch('mwad.paths.subprocess.check_output', return_value='/mnt/c/GOG Games/Morrowind\n') as command:
            value = installed_game_path(r'C:\GOG Games\Morrowind')
        self.assertEqual(value, Path('/mnt/c/GOG Games/Morrowind'))
        self.assertEqual(command.call_args.args[0], ['wslpath','-u',r'C:\GOG Games\Morrowind'])

    def test_explicit_path_overrides_discovery_and_noninteractive_never_guesses(self):
        with patch.object(build, 'gog_installation') as detect:
            self.assertEqual(build.game_input('/chosen/game', True), '/chosen/game')
            self.assertIsNone(build.game_input(None, False))
            detect.assert_not_called()

    def test_detected_folder_requires_size_and_checksum_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);data = root/'Data Files';synthetic_install(data)
            with patch.object(build, 'is_wsl', return_value=True), \
                 patch.object(build, 'installed_game_path', return_value=root), \
                 patch.object(input_check, 'matches_core', return_value=False):
                self.assertIsNone(build.gog_installation())
            with patch.object(build, 'is_wsl', return_value=True), \
                 patch.object(build, 'installed_game_path', return_value=root), \
                 patch.object(input_check, 'matches_core', return_value=True):
                self.assertEqual(build.gog_installation(),root)

    def test_installed_root_is_checked_and_same_size_change_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);data = root/'Data Files';synthetic_install(data)
            reference = {p.name.casefold():{'bytes':p.stat().st_size,'sha256':input_check.digest(p)} for p in data.iterdir()}
            report = input_check.inspect(root, 'terrain', reference=reference)
            self.assertEqual(report['fingerprints']['matching'],2)
            self.assertEqual(report['errors'],[])
            p = data/'MORROWIND.BSA';raw=p.read_bytes();p.write_bytes(raw[:-1]+b'X')
            report = input_check.inspect(root, 'terrain', reference=reference)
            self.assertEqual(report['fingerprints']['different'],['morrowind.bsa'])
            self.assertTrue(report['errors'])

    def test_override_does_not_accept_truncated_containers(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'game';synthetic_install(data)
            p=data/'MORROWIND.BSA';p.write_bytes(p.read_bytes()[:-1])
            report=input_check.inspect(data,'terrain',allow_differences=True,reference={})
            self.assertTrue(any('overruns' in e for e in report['errors']))

    def test_default_output_is_allowed_but_source_and_symlink_escape_are_not(self):
        self.assertEqual(build.parser().parse_args([]).workspace,build.ROOT/'out')
        self.assertEqual(ensure_external(build.ROOT/'out/build/example'),build.ROOT/'out/build/example')
        with self.assertRaises(ValueError):ensure_external(build.ROOT/'src/private')
        with tempfile.TemporaryDirectory() as temp:
            fake=Path(temp)/'amiwind';fake.mkdir()
            (fake/'pyproject.toml').write_text('[project]\nname = "amiwind"\n')
            (fake/'out').symlink_to(build.ROOT/'src',target_is_directory=True)
            with self.assertRaises(ValueError):ensure_external(fake/'out/private')

    def test_dry_run_rejects_game_path_and_builds_no_conversion_stages(self):
        args=build.parser().parse_args(['--dry-run','--data-files','/private/game'])
        with self.assertRaisesRegex(ValueError,'does not accept'):build.dry_run_prerequisites(args)
        args.data_files=None;args.sdk=Path('/sdk')
        steps=build.dry_run_commands(args,Path('/output'))
        self.assertEqual([name for name,_ in steps],['engine','dry-run-image'])
        self.assertFalse(any('--data-files' in command for _,command in steps))
