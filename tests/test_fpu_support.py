"""Optional FPU support library (--amiga-libs), ENGINE-FPSP-MISSING-31.

Only synthetic bytes are used: a file named 68040.library here is a fake
library built by tests/synthetic_hunks.py (or a hunk header plus filler where
the content is not read), never a real support library."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import build
import build_aga
import build_summary
import fpu_support
from synthetic_hunks import fake_library

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = b'\x00\x00\x03\xf3' + b'AmiWind synthetic test bytes, not a library\n' * 4
FAKE_040 = fake_library(version=40, revision=2)
FAKE_MMU = fake_library(name=b'mmu.library', version=43, revision=11)
LOADER = b'\x00\x00\x03\xf3synthetic loader'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def find_sdk():
    for candidate in (os.environ.get('AMIWIND_SDK'), '/opt/amiwind-tools/sdk'):
        if candidate and (Path(candidate)/'bin/vasmm68k_mot').is_file():
            return Path(candidate)
    return None


class FindAndStageTests(unittest.TestCase):
    def test_finds_libraries_in_dir_or_libs_drawer_case_insensitively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'Libs').mkdir()
            (root/'Libs/68040.LIBRARY').write_bytes(SYNTHETIC)
            self.assertEqual(fpu_support.find(root), {'68040.library': root/'Libs/68040.LIBRARY'})
            (root/'68060.library').write_bytes(SYNTHETIC)
            (root/'Libs/MMU.library').write_bytes(SYNTHETIC)
            found = fpu_support.find(root)
            self.assertEqual(set(found), {'68040.library', '68060.library', 'mmu.library'})
            self.assertEqual(found['68060.library'], root/'68060.library')

    def test_no_library_is_not_an_error_but_a_missing_folder_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'mmu.library').write_bytes(SYNTHETIC)  # a companion alone installs nothing
            self.assertEqual(fpu_support.find(root), {})
            with self.assertRaisesRegex(ValueError, 'not a directory'):
                fpu_support.find(root/'absent')

    def test_stage_copies_records_and_installs_the_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            libs = root/'wb/LIBS'
            libs.mkdir(parents=True)
            (libs/'68040.library').write_bytes(FAKE_040)
            (libs/'mmu.library').write_bytes(FAKE_MMU)
            loader = root/'AmiWindFPU'
            loader.write_bytes(LOADER)
            boot = root/'boot'
            boot.mkdir()
            receipt = fpu_support.stage(root/'wb', boot, loader)
            self.assertEqual(receipt['status'], 'installed')
            row = receipt['libraries'][0]
            self.assertEqual({k: row[k] for k in ('name', 'bytes', 'sha256', 'version', 'verdict')},
                             {'name': '68040.library', 'bytes': len(FAKE_040), 'sha256': sha(FAKE_040),
                              'version': '40.2', 'verdict': 'unknown'})
            self.assertEqual(receipt['companions'][0]['name'], 'mmu.library')
            self.assertEqual((boot/'LIBS/68040.library').read_bytes(), FAKE_040)
            self.assertEqual((boot/'LIBS/mmu.library').read_bytes(), FAKE_MMU)
            self.assertEqual((boot/'AmiWindFPU').read_bytes(), LOADER)
            self.assertEqual(receipt['loader'], {'path': 'AmiWindFPU', 'sha256': sha(LOADER)})
            json.dumps(receipt)
            lines = fpu_support.summary_lines(receipt)
            self.assertEqual(lines[0], f'FPU support library: 68040.library v40.2 ({len(FAKE_040):,} bytes) SHA-256 '
                                       f'{sha(FAKE_040)}: unknown build of 68040.library v40.2 (not tested; used)')
            self.assertTrue(lines[1].startswith('  also copied: mmu.library v43.11'))

    def test_absent_option_or_library_continues_without_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            boot = root/'boot'
            boot.mkdir()
            for directory, status in ((None, 'not_requested'), (root, 'not_found')):
                receipt = fpu_support.stage(directory, boot, None)
                self.assertEqual(receipt['status'], status)
                self.assertEqual(receipt['summary'], 'no FPU support library')
                self.assertEqual(fpu_support.summary_lines(receipt),
                                 ['FPU support library: none (no FPU support library)'])
                self.assertFalse((boot/'LIBS').exists() or (boot/'AmiWindFPU').exists())

    def test_non_hunk_file_is_not_used_and_missing_loader_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'68040.library').write_bytes(b'not an amiga file')
            loader = root/'AmiWindFPU'
            loader.write_bytes(LOADER)
            (root/'boot').mkdir()
            receipt = fpu_support.stage(root, root/'boot', loader)
            self.assertEqual(receipt['status'], 'not_found')
            self.assertIn('no hunk header', receipt['rejected'][0]['message'])
            with self.assertRaisesRegex(ValueError, 'not an Amiga library'):
                fpu_support.stage(root, root/'boot', loader, policy='fail')
            (root/'68040.library').write_bytes(FAKE_040)
            with self.assertRaisesRegex(ValueError, 'rebuild the engine'):
                fpu_support.stage(root, root/'boot', None)

    def test_startup_sequence_runs_loader_only_when_installed(self):
        self.assertEqual(fpu_support.startup_sequence({'status': 'not_found'}),
                         'FailAt 10\nSYS:AmiWindCheck\nStack 300000\nSYS:AmiWind\n')
        self.assertEqual(fpu_support.startup_sequence({'status': 'installed'}),
                         'FailAt 10\nSYS:AmiWindFPU\nSYS:AmiWindCheck\nStack 300000\nSYS:AmiWind\n')

    def test_receipt_loader_for_older_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(fpu_support.load_receipt(Path(tmp)/'fpu-support.json')['status'], 'not_requested')
            (Path(tmp)/'fpu-support.json').write_text('{"status": "odd"}')
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                fpu_support.load_receipt(Path(tmp)/'fpu-support.json')


class BuilderWiringTests(unittest.TestCase):
    def test_image_stage_checks_loader_against_engine_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root/'engine/runtime/build/AmiQuakeGCC'
            engine.parent.mkdir(parents=True)
            engine.write_bytes(b'engine')
            (engine.parent/'AmiWindFPU').write_bytes(LOADER)
            (root/'wb').mkdir()
            (root/'wb/68040.library').write_bytes(FAKE_040)
            boot = root/'boot'
            boot.mkdir()
            args = SimpleNamespace(amiga_libs=root/'wb', engine=engine)
            with patch.object(build_aga, 'check_binary'), contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaisesRegex(ValueError, 'rebuild the engine'):
                    build_aga.stage_fpu_support(args, {'fpu_loader_sha256': 'stale'}, boot)
                receipt = build_aga.stage_fpu_support(args, {'fpu_loader_sha256': sha(LOADER)}, boot)
            self.assertEqual(receipt['status'], 'installed')
            self.assertIn('FPU support library: 68040.library', out.getvalue())
            self.assertEqual((boot/'AmiWindFPU').read_bytes(), LOADER)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                receipt = build_aga.stage_fpu_support(SimpleNamespace(amiga_libs=None, engine=engine), {}, root/'none')
            self.assertEqual(receipt['status'], 'not_requested')
            self.assertIn('none (no FPU support library)', out.getvalue())

    def test_engine_build_assembles_loader_and_records_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'out'
            tree = out/'runtime'
            (tree/'build').mkdir(parents=True)
            (tree/'build/AmiQuakeGCC').write_bytes(b'fixture engine')
            (tree/'build/AmiWindCheck').write_bytes(b'fixture checker')
            (tree/'build/awbench').write_bytes(b'fixture benchmark')
            (tree/'build/AmiWindFPU').write_bytes(LOADER)
            argv = ['build_aga.py', 'engine', '--sdk', tmp, '--out', str(out), '--jobs', '1']
            with patch.object(sys, 'argv', argv), patch.object(build_aga, 'check_native_versions'), \
                 patch.object(build_aga, 'new_output', return_value=out), \
                 patch.object(build_aga, 'stage_runtime', return_value=(tree, {})), \
                 patch.object(build_aga, 'run') as run, patch.object(build_aga, 'check_binary'), \
                 patch.object(build_aga, 'check_engine_fpu', return_value={'passed': True}), \
                 patch.object(build_aga, 'write_world_coverage'), \
                 patch.object(build_aga, 'executable_path', side_effect=str):
                build_aga.main()
            assembled = [call.args[0] for call in run.call_args_list if '-Fhunkexe' in call.args[0]]
            self.assertTrue(any(str(arg).endswith('boot/fpulib.asm') for command in assembled for arg in command))
            self.assertEqual(json.loads((out/'engine-build.json').read_text())['fpu_loader_sha256'], sha(LOADER))

    def test_option_reaches_image_and_dry_run_steps_only(self):
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        args = build.parser().parse_args(['--amiga-libs', '/owned/workbench'])
        args.data_files = Path('/owned/Data Files')
        args.sdk = Path('/sdk')
        steps = dict(build.commands(args, tools, Path('/private/run')))
        image = steps['image']
        self.assertEqual(image.count('--amiga-libs'), 1)
        self.assertEqual(Path(image[image.index('--amiga-libs') + 1]), Path('/owned/workbench'))
        for name, command in steps.items():
            if name != 'image':
                self.assertNotIn('--amiga-libs', command)
        dry = dict(build.dry_run_commands(args, Path('/out')))
        self.assertIn('--amiga-libs', dry['dry-run-image'])
        self.assertNotIn('--amiga-libs', dry['engine'])
        plain = build.parser().parse_args([])
        plain.data_files, plain.sdk = Path('/owned/Data Files'), Path('/sdk')
        self.assertFalse(any('--amiga-libs' in c for _, c in build.commands(plain, tools, Path('/private/run'))))

    def test_build_report_names_the_library_or_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            self.assertIsNone(build_summary.read_fpu_support(run))
            (run/'image').mkdir()
            (run/'image/build.json').write_text(json.dumps({'version': 'test'}))
            self.assertEqual(build_summary.read_fpu_support(run)['status'], 'not_requested')
            receipt = {'status': 'installed', 'libraries': [{'name': '68040.library', 'bytes': 9, 'sha256': 'ab'}],
                       'companions': []}
            (run/'image/build.json').write_text(json.dumps({'fpu_support': receipt}))
            self.assertEqual(build_summary.read_fpu_support(run), receipt)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                result = build_summary.BuildSummary(run, 'test', 'AGA image').finish('failed')
            self.assertEqual(result['fpu_support'], receipt)
            self.assertIn('FPU support library: 68040.library (9 bytes) SHA-256 ab', out.getvalue())


class BootSourceTests(unittest.TestCase):
    def test_boot_check_line_format_and_non_fatal_warning(self):
        asm = (ROOT/'engine/aga/boot/bootcheck.asm').read_text()
        lines = {}
        for line in asm.splitlines():
            if 'dc.b "' in line and ('[x] OK' in line or '[~] WARN' in line or '[!] WARN' in line):
                text = line.split('dc.b "', 1)[1].split('"', 1)[0]
                lines[text.split(':', 1)[0]] = text
        # Same columns as the existing checklist: label 22, value 27, then the marker.
        for text in (lines['CPU'], lines['Video timing'], lines['FPU support']):
            marker = text.index('[')
            self.assertEqual(marker, 49, text)
        self.assertIn('FPU support:          %-27s[x] OK', asm)
        self.assertIn('"FPU support:          none - see docs (optional) [~] WARN"', asm)
        self.assertTrue(all(ord(c) < 128 for c in asm))
        # The WARN branch prints and moves on; it never touches the failure code (d7).
        code = '\n'.join(line.split(';', 1)[0] for line in asm.splitlines())
        support = code.split('.support_check:', 1)[1].split('.video_check:', 1)[0]
        self.assertIn('.support_none:', support)
        self.assertNotIn('d7', support)
        self.assertIn('include "fpu_support_inc.asm"', asm)

    def test_loader_and_shared_probe_source(self):
        loader = (ROOT/'engine/aga/boot/fpulib.asm').read_text()
        shared = (ROOT/'engine/aga/boot/fpu_support_inc.asm').read_text()
        self.assertIn('include "fpu_support_inc.asm"', loader)
        # The only CloseLibrary closes dos.library: the support library stays open.
        self.assertEqual(loader.count('_LVOCloseLibrary'), 1)
        self.assertIn('move.l  dos_base,a1\n        jsr     _LVOCloseLibrary(a6)', loader)
        self.assertIn('$4e7a1808', shared)  # movec pcr,d1
        self.assertIn('$4e7a8801', shared)  # movec vbr,a0
        self.assertIn('LibList(a6)', shared)
        self.assertIn('_LVOForbid', shared)
        self.assertIn('"68060.library"', shared)
        self.assertIn('"68040.library"', shared)

    @unittest.skipIf(find_sdk() is None, 'Amiga SDK (vasmm68k_mot) not installed')
    def test_boot_programs_and_synthetic_library_assemble(self):
        sdk = find_sdk()
        vasm = str(sdk/'bin/vasmm68k_mot')
        ndk = str(sdk/'m68k-amigaos/ndk-include')
        from check_aga_binary import check_binary
        from project_version import generate_native
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            generate_native(ROOT/'VERSION', tmp/'gen')
            boot = ROOT/'engine/aga/boot'
            outputs = {}
            for name, source, extra in (('AmiWindCheck', boot/'bootcheck.asm', ['-kick1hunks', '-I', str(tmp/'gen')]),
                                        ('AmiWindFPU', boot/'fpulib.asm', ['-kick1hunks']),
                                        ('lib040', ROOT/'tests/fpu_test_library.asm', []),
                                        ('lib060', ROOT/'tests/fpu_test_library.asm', ['-DCPU060=1'])):
                target = tmp/name
                result = subprocess.run([vasm, '-m68000', '-Fhunkexe', '-nosym', '-I', ndk, '-I', str(boot), *extra,
                                         '-o', str(target), str(source)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('warning', (result.stdout + result.stderr).lower())
                outputs[name] = target.read_bytes()
                check_binary(outputs[name])
            for name, library in (('lib040', b'68040.library\0'), ('lib060', b'68060.library\0')):
                data = outputs[name]
                self.assertIn(b'\x4a\xfc', data)  # RTC_MATCHWORD
                self.assertIn(library, data)
                self.assertIn(b'amiwind test library 1.0 (does nothing)', data)


if __name__ == '__main__':
    unittest.main()
