"""Dependency consent, input corruption, discovery and version boundaries."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import build
import build_versions
import fetch_toolchain
import install_dependencies
import setup_build
import fetch_native
from build_aga import check_quakec, validate_quakec
from mwad import input_check
from mwad.paths import ensure_external, installed_game_path, is_wsl
from test_workflow import synthetic_install


class BuildSetupTests(unittest.TestCase):
    def test_package_detection_handles_native_foreign_and_all_architectures(self):
        for statuses, missing in (
            ('amd64\tinstall ok installed\ni386\tinstall ok installed\n', []),
            ('i386\tinstall ok installed\n', ['libgmp10']),
            ('amd64\tdeinstall ok config-files\ni386\tinstall ok installed\n', ['libgmp10']),
            ('all\tinstall ok installed\n', []),
        ):
            results = [subprocess.CompletedProcess([], 0, 'amd64\n'),
                       subprocess.CompletedProcess([], 0, statuses)]
            with patch.object(install_dependencies.subprocess, 'run', side_effect=results):
                self.assertEqual(install_dependencies.missing_packages(['libgmp10']), missing)

    def test_no_missing_packages_skips_both_apt_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--autoinstall', '--tools-dir', temp])
            with patch.object(setup_build, 'supported_host'), \
                 patch.object(setup_build, 'missing_packages', return_value=[]):
                commands, _, _ = setup_build.proposal(args)
            self.assertFalse(any('apt-get' in command for command in commands))

    def test_existing_environment_repairs_missing_setuptools(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); venv = root/'venv'; (venv/'bin').mkdir(parents=True)
            (venv/'pyvenv.cfg').write_text('fixture'); (venv/'bin/python').touch()
            args = build.parser().parse_args(['--autoinstall', '--tools-dir', temp])
            with patch.object(setup_build, 'supported_host'), \
                 patch.object(setup_build, 'missing_packages', return_value=[]), \
                 patch.object(setup_build.importlib.util, 'find_spec', side_effect=lambda name: None if name == 'setuptools' else object()):
                commands, missing_python, _ = setup_build.proposal(args)
            self.assertEqual(missing_python, ['setuptools'])
            pip = next(command for command in commands if 'pip' in command)
            self.assertIn('setuptools>=68', pip)
            self.assertEqual(pip[0], str(venv/'bin/python'))
            self.assertFalse(any('venv' in command for command in commands))

    def test_empty_managed_tools_forces_fresh_setup_despite_ambient_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--autoinstall', '--tools-dir', temp])
            with patch.object(setup_build, 'supported_host'), \
                 patch.object(setup_build, 'missing_packages', return_value=[]), \
                 patch.object(setup_build.importlib.util, 'find_spec', return_value=object()), \
                 patch.object(build_versions, 'find_quake_tools', return_value=None), \
                 patch.object(build_versions, 'find_qcc', return_value='/usr/bin/fteqcc'), \
                 patch.object(setup_build.shutil, 'which', side_effect=lambda value: None if 'Quake-Tools' in value else '/usr/bin/'+value):
                commands, missing_python, downloads = setup_build.proposal(args)
            self.assertTrue(missing_python)
            self.assertEqual(commands[0][:3], ['/usr/bin/python3', '-m', 'venv'])
            self.assertEqual([item[0] for item in downloads], ['sdk', 'ericw', 'qcc'])
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_relative_tool_probe_uses_absolute_path_after_chdir(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix='probe space ') as temp:
            tool = Path(temp)/'version-tool'
            tool.write_text('#!/bin/sh\necho "tool 1.2.3"\n'); tool.chmod(0o755)
            relative = tool.relative_to(Path.cwd())
            result = build_versions.probe('fixture', str(relative),
                        {'version':'1.2.3', 'arguments':['--version'], 'pattern':r'tool (\S+)'})
            self.assertEqual(result['status'], 'matching')
            self.assertEqual(result['path'], str(tool))

    def test_sdk_flag_works_alone_and_preview_decline_do_not_install(self):
        with tempfile.TemporaryDirectory() as temp:
            for extra, answer in ((['--plan'], 'yes'), ([], 'no')):
                with patch('builtins.input', return_value=answer) as prompt, \
                     patch.object(fetch_toolchain, 'fetch') as fetch, \
                     patch.object(install_dependencies, 'install') as host, \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(build.main(['--install-sdk', '--tools-dir', temp, *extra]), 0)
                    fetch.assert_not_called(); host.assert_not_called()
                    if extra: prompt.assert_not_called()
            self.assertFalse((Path(temp)/'sdk').exists())

    def test_qcc_discovery_honors_explicit_compiler_and_finds_fte(self):
        with tempfile.TemporaryDirectory() as temp:
            tool = Path(temp)/'fteqcc'; tool.write_text('fixture'); tool.chmod(0o755)
            args = build.parser().parse_args(['--tools-dir', temp])
            with patch.dict(os.environ, {'PATH':temp}):
                self.assertEqual(build_versions.find_qcc(args), str(tool))
                row = build_versions.probe('qcc', str(tool), {'version':'reference', 'sha256':'0'*64})
                self.assertEqual(row['status'], 'alternative')
                args.qcc = '/explicit/compiler'
                self.assertEqual(build_versions.find_qcc(args), '/explicit/compiler')

    def test_disk_tools_use_help_without_claiming_package_version(self):
        with tempfile.TemporaryDirectory() as temp:
            tool = Path(temp)/'xdftool'
            tool.write_text('#!/bin/sh\n[ "$1" = "--help" ] || exit 1\necho "usage: xdftool"\n'); tool.chmod(0o755)
            specs = json.loads(build_versions.REFERENCE.read_text())
            row = build_versions.probe('xdftool', str(tool), specs['tools']['xdftool'])
            self.assertEqual(row['status'], 'available')
            self.assertIn('no version flag', row['detected'])

    def test_incompatible_quakec_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'progs.dat'
            # A minimal structurally valid container, no game code/data.
            header = [6,5927,60,1,68,1,76,1,84,1,120,1,121,1,1]
            valid = struct.pack('<15i', *header) + bytes(65)
            path.write_bytes(valid); validate_quakec(path)
            for change in (struct.pack('<i',7)+valid[4:], valid[:4]+struct.pack('<i',0)+valid[8:],
                           valid[:60]+struct.pack('<H',66)+valid[62:], valid[:-1]):
                path.write_bytes(change)
                with self.assertRaises(ValueError): validate_quakec(path)

    def test_autoinstall_preview_and_decline_never_execute(self):
        args = build.parser().parse_args(['--autoinstall'])
        for preview, answer in ((True,'yes'), (False,'no')):
            with patch.object(setup_build, 'proposal', return_value=([['fake-installer']], [], [])), \
                 patch.object(setup_build.subprocess, 'run') as run, \
                 patch('builtins.input', return_value=answer) as prompt, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(setup_build.setup(args, [], preview=preview))
                run.assert_not_called()
                if preview: prompt.assert_not_called()

    def test_confirmed_setup_continues_into_build_without_second_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sdk = root/'tools/sdk'; output = root/'output'
            create_sdk = (
                'from pathlib import Path\n'
                f'p=Path({str(sdk)!r})\n'
                "for name in ('bin/m68k-amigaos-gcc','bin/vasmm68k_mot','m68k-amigaos/ndk-include/exec/exec_lib.i'):\n"
                " f=p/name; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('#!/bin/sh\\necho fixture\\n'); f.chmod(0o755)\n")
            def steps(args, run):
                return [('fixture-build', [sys.executable, '-c',
                         f'from pathlib import Path; Path({str(run/"finished")!r}).write_text("built"); '
                         f'p=Path({str(run/"image"/f"AmiWind-v{build.VERSION}-dry-run.hdf")!r}); '
                         'p.parent.mkdir(); p.write_bytes(b"fixture output")'])]
            with patch.object(setup_build, 'proposal', return_value=([[sys.executable, '-c', create_sdk]], [], [])), \
                 patch.object(build, 'dry_run_commands', side_effect=steps), \
                 patch.object(build_versions, 'report', return_value=[]), \
                 patch.object(build.importlib.util, 'find_spec', return_value=object()), \
                 patch('builtins.input', return_value='yes') as prompt, \
                 contextlib.redirect_stdout(io.StringIO()):
                result = build.main(['--autoinstall', '--dry-run', '--tools-dir', str(root/'tools'),
                                     '--workspace', str(output), '--name', 'test'])
            self.assertEqual(result, 0)
            prompt.assert_called_once()
            self.assertEqual((output/'build/test/finished').read_text(), 'built')
            self.assertTrue((output/'build/test/build-state.json').is_file())

    def test_environment_restart_retains_arguments_and_venv_interpreter(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--tools-dir', temp])
            venv = Path(temp)/'venv'; (venv/'bin').mkdir(parents=True)
            (venv/'pyvenv.cfg').write_text('fixture'); (venv/'bin/python').symlink_to(sys.executable)
            argv = ['--autoinstall', '--data-files', '/a game folder', '--workspace', '/separate output']
            with patch.dict(os.environ, {}, clear=True), patch.object(setup_build.os, 'execve') as restart, \
                 contextlib.redirect_stdout(io.StringIO()):
                setup_build.use_environment(args, argv)
            self.assertEqual(restart.call_args.args[0], str(venv/'bin/python'))
            self.assertEqual(restart.call_args.args[1][2:], argv)
            self.assertTrue(restart.call_args.args[2]['PATH'].startswith(str(venv/'bin')))

    def test_qcc_source_hash_failure_never_installs_final_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root/'bad.tar.gz'
            with tarfile.open(archive, 'w:gz') as bundle:
                item = tarfile.TarInfo('source/qcc/qcc.c'); item.size = fetch_native.QCC_FILES['qcc.c'][0]
                bundle.addfile(item, io.BytesIO(bytes(item.size)))
            with patch.object(fetch_native, 'download', side_effect=lambda url, path, limit: path.write_bytes(archive.read_bytes())), \
                 patch.object(fetch_native.subprocess, 'run') as compile:
                with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                    fetch_native.fetch('qcc', root/'installed')
                compile.assert_not_called()
            self.assertFalse((root/'installed').exists())

    def test_sdk_checks_decline_and_plans_do_not_download(self):
        with tempfile.TemporaryDirectory() as temp:
            for flags, answers in ((['--check'], ['']), (['--check'], ['install', 'no']),
                                   (['--plan'], ['install'])):
                with self.subTest(flags=flags, answers=answers):
                    args = build.parser().parse_args([*flags, '--tools-dir', str(Path(temp)/'tools')])
                    with patch('builtins.input', side_effect=answers), \
                         patch.object(fetch_toolchain, 'fetch') as fetch, \
                         contextlib.redirect_stdout(io.StringIO()):
                        self.assertIsNone(build.select_sdk(args, interactive=True))
                    fetch.assert_not_called()
                    self.assertFalse(args.tools_dir.exists())

    def test_confirmed_sdk_install_checks_archive_before_using_it(self):
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w:xz') as archive:
            for name in ('bin/m68k-amigaos-gcc', 'bin/vasmm68k_mot', 'm68k-amigaos/ndk-include/exec/exec_lib.i'):
                item = tarfile.TarInfo(fetch_toolchain.SPEC['directory']+'/'+name)
                content = b'synthetic SDK fixture\n'
                item.size = len(content)
                item.mode = 0o755 if name.startswith('bin/') else 0o644
                archive.addfile(item, io.BytesIO(content))
        raw = payload.getvalue()
        for valid in (True, False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory(prefix='sdk setup ') as temp:
                args = build.parser().parse_args(['--check', '--tools-dir', str(Path(temp)/'tools')])
                spec = {**fetch_toolchain.SPEC, 'bytes':len(raw),
                        'sha256':hashlib.sha256(raw).hexdigest() if valid else '0'*64}
                with patch.dict(fetch_toolchain.SPEC, spec), \
                     patch.object(fetch_toolchain.sys, 'platform', 'linux'), \
                     patch.object(fetch_toolchain.platform, 'machine', return_value='x86_64'), \
                     patch.object(fetch_toolchain.urllib.request, 'urlopen', return_value=io.BytesIO(raw)), \
                     patch('builtins.input', side_effect=['install', 'yes']), \
                     contextlib.redirect_stdout(io.StringIO()):
                    if valid:
                        self.assertEqual(build.select_sdk(args, True), args.tools_dir/'sdk')
                        self.assertTrue((args.tools_dir/'sdk/amiwind-download.json').is_file())
                    else:
                        with self.assertRaisesRegex(ValueError, 'pinned size/SHA-256'):
                            build.select_sdk(args, True)
                        self.assertFalse((args.tools_dir/'sdk').exists())

    def test_sdk_discovery_preserves_explicit_path_and_existing_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--tools-dir', temp])
            sdk = Path(temp)/'sdk'
            for name in ('bin/m68k-amigaos-gcc', 'bin/vasmm68k_mot', 'm68k-amigaos/ndk-include/exec/exec_lib.i'):
                path = sdk/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')
            with patch.object(fetch_toolchain, 'fetch') as fetch, \
                 patch('builtins.input') as prompt, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build.select_sdk(args, True), sdk)
                args.sdk = Path(temp)/'chosen'
                self.assertEqual(build.select_sdk(args, True), args.sdk)
            fetch.assert_not_called(); prompt.assert_not_called()
            args.sdk = None
            (sdk/'bin/m68k-amigaos-gcc').unlink()
            with patch.object(fetch_toolchain, 'fetch') as fetch, \
                 patch('builtins.input', return_value='install'), contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(build.select_sdk(args, True))
            fetch.assert_not_called()
            self.assertTrue((sdk/'bin/vasmm68k_mot').is_file())

    def test_ctrl_c_at_sdk_prompt_exits_quietly(self):
        with tempfile.TemporaryDirectory() as temp:
            err = io.StringIO()
            with patch.object(build.sys.stdin, 'isatty', return_value=True), \
                 patch('builtins.input', side_effect=KeyboardInterrupt), \
                 contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()), \
                 self.assertRaises(SystemExit) as caught:
                build.main(['--dry-run', '--tools-dir', temp])
            self.assertEqual(caught.exception.code, 130)
            self.assertIn('Cancelled.', err.getvalue())
            self.assertNotIn('Traceback', err.getvalue())

    def test_parent_search_validates_only_the_nested_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root/'Morrowind/Morrowind/Data Files'
            data.parent.mkdir(parents=True)
            synthetic_install(data)
            (root/'unrelated.bin').write_bytes(b'outside game inputs')
            reference = {p.name.casefold():{'bytes':p.stat().st_size, 'sha256':input_check.digest(p)} for p in data.iterdir()}
            notices = []
            report = input_check.inspect(root, 'terrain', reference=reference, notify=notices.append)
            self.assertEqual(report['data_files'], str(data))
            self.assertEqual(report['loose_files'], 2)
            self.assertEqual(report['fingerprints']['matching'], 2)
            self.assertEqual(report['errors'], [])
            self.assertTrue(any('Looking in subdirectories' in text for text in notices))

    def test_multiple_installs_require_selection_before_hashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root/'first', root/'second'
            synthetic_install(first); synthetic_install(second)
            with patch.object(input_check, 'digest') as digest, self.assertRaisesRegex(ValueError, 'Multiple Morrowind'):
                input_check.inspect(root, 'terrain', reference={})
            digest.assert_not_called()
            with patch('builtins.input', side_effect=['invalid', '2']), contextlib.redirect_stdout(io.StringIO()):
                report = input_check.inspect(root, 'terrain', reference={}, choose=build.choose_installation)
            self.assertEqual(report['data_files'], str(second))

    def test_missing_game_stops_before_inventory_and_sdk_setup(self):
        with tempfile.TemporaryDirectory() as temp:
            args = build.parser().parse_args(['--data-files', temp])
            with patch.object(input_check, 'fingerprints') as fingerprints, \
                 patch.object(build, 'select_sdk') as sdk, contextlib.redirect_stdout(io.StringIO()), \
                 self.assertRaisesRegex(ValueError, 'Game inputs need attention'):
                build.prerequisites(args)
            fingerprints.assert_not_called(); sdk.assert_not_called()

    def test_subdirectory_search_has_limits_and_ignores_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'search'; root.mkdir()
            other = Path(temp)/'game'; synthetic_install(other)
            (root/'linked').symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'No folder containing'):
                input_check.locate_data_files(root)
            deep = root/'one/two/three'; deep.parent.mkdir(parents=True); synthetic_install(deep)
            with self.assertRaisesRegex(ValueError, 'within 1 levels'):
                input_check.locate_data_files(root, max_depth=1)
            with self.assertRaisesRegex(ValueError, 'reached 1 folders'):
                input_check.locate_data_files(root, max_dirs=1)

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

    def test_transfer_archives_are_ignored_but_real_video_conflicts_still_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=root/'Data Files';synthetic_install(data)
            reference={p.name.casefold():{'bytes':p.stat().st_size,'sha256':input_check.digest(p)} for p in data.iterdir()}
            for name in ('Morrowind_Video.zip','Morrowind_video.zip','backup.ZIP',
                         'Morrowind_fonts.zip','Morrowind_bookart.zip','Morrowind_icons.zip',
                         'Morrowind_meshes.zip','Morrowind_music.zip','Morrowind_sound.zip',
                         'Morrowind_splash.zip','Morrowind_textures.zip'):
                (data/name).write_bytes(b'personal transfer archive, not a game input')
            video=data/'Video';video.mkdir();(video/'mw_intro.bik').write_bytes(b'real loose video fixture')
            report=input_check.inspect(root,'terrain',reference=reference)
            self.assertEqual(report['errors'],[])
            self.assertEqual(report['ignored_non_game_files'],11)
            self.assertEqual(report['loose_files'],3)
            self.assertEqual(report['loose_categories']['video'],1)
            args=build.parser().parse_args(['--data-files',str(data)])
            source=root/'source';source.mkdir();(source/'VERSION').write_text('fixture')
            with patch.object(build,'ROOT',source):receipt=build.provenance(args,{})
            self.assertIn('Video/mw_intro.bik',receipt['input_sha256'])
            self.assertFalse(any(name.casefold().endswith('.zip') for name in receipt['input_sha256']))
            (video/'MW_INTRO.BIK').write_bytes(b'conflicting actual video')
            report=input_check.inspect(root,'terrain',reference=reference)
            self.assertTrue(any('video/mw_intro.bik' in error for error in report['errors']))
            self.assertFalse(any('zip' in error for error in report['errors']))

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
