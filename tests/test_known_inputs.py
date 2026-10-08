"""Known inputs and the input lock (tools/known_inputs.py), BUILD-INPUTS-UNVERIFIED-32.

Synthetic files only: fake hunk libraries, TES3 headers, BSA headers and a
Kickstart-shaped image built in tests/synthetic_hunks.py. No game data, ROM or
vendor library is read."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import build
import build_summary
import fpu_support
import known_inputs as ki
from mwad import input_check
import synthetic_hunks as sh

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table_with(*rows, editions=()):
    entries = []
    for kind, name, data, source, tested in rows:
        entries.append({'kind': kind, 'name': name, 'bytes': len(data), 'sha256': sha(data), 'version': '1',
                        'source': source, 'tested': tested, 'notes': 'synthetic'})
    table = {'schema': ki.TABLE_SCHEMA, 'revision': 1, 'entries': entries, 'editions': list(editions)}
    assert not ki.check_table(table), ki.check_table(table)
    return table


class HunkParserTests(unittest.TestCase):
    def test_version_from_data_table_id_string_and_ver(self):
        info = ki.amiga_library_info(sh.fake_library(version=40, revision=2, data_table_revision=7), '68040.library')
        self.assertTrue(info['valid'])
        self.assertEqual((info['version'], info['revision_source']), ('40.7', 'library data table'))
        info = ki.amiga_library_info(sh.fake_library(version=40, revision=2), '68040.LIBRARY')
        self.assertEqual((info['version'], info['revision_source']), ('40.2', 'RomTag id string'))
        self.assertEqual(info['id_string'], '68040.library 40.2 (1.1.99)')
        info = ki.amiga_library_info(sh.fake_library(id_string=b'support code', ver_string=b'68060.library 46.3 (2.2.02)',
                                                     name=b'68060.library', version=46), '68060.library')
        self.assertEqual((info['version'], info['revision_source']), ('46.3', '$VER string'))
        self.assertEqual(info['ver_string'], '68060.library 46.3 (2.2.02)')
        # A V.R whose V is not rt_Version is not taken; the version stays readable.
        info = ki.amiga_library_info(sh.fake_library(id_string=b'68040 37.30', version=40), '68040.library')
        self.assertEqual((info['version'], info['revision']), ('40', None))
        self.assertTrue(info['valid'])

    def test_short_relocations_data_hunk_strings_symbol_and_debug_hunks(self):
        for options in ({'short_relocs': True}, {'strings_in_data': True}, {'short_relocs': True, 'strings_in_data': True}):
            info = ki.amiga_library_info(sh.fake_library(version=43, revision=11, name=b'mmu.library', **options),
                                         'mmu.library')
            self.assertEqual(info['version'], '43.11', options)
            self.assertEqual(info['resident_name'], 'mmu.library', options)

    def test_invalid_files(self):
        cases = {
            'no hunk header': b'not an amiga file at all, just text....',
            'file ends inside a hunk': sh.fake_library()[:60],
            'no resident library': sh.fake_library(self_pointer=False),
            'is not 68040.library': sh.fake_library(name=b'68060.library'),
        }
        for reason, data in cases.items():
            info = ki.amiga_library_info(data, '68040.library')
            self.assertFalse(info['valid'], reason)
            self.assertIn(reason, info['reason'])
        # A resident that is not NT_LIBRARY (a device, say) is not a library.
        self.assertFalse(ki.amiga_library_info(sh.fake_library(node_type=3), '68040.library')['valid'])

    def test_match_word_needs_its_own_relocated_pointer(self):
        # A stray $4AFC in code without the self-pointing RELOC32 is not a RomTag.
        data = sh.fake_library(extras=b'\x4a\xfc\x00\x00\x00\x04' + bytes(22))
        hunks, relocs = ki.parse_hunks(data)
        self.assertEqual(len(ki.find_resident(hunks, relocs)), 1)

    @unittest.skipIf(not Path(os.environ.get('AMIWIND_SDK', '/opt/amiwind-tools/sdk'), 'bin/vasmm68k_mot').is_file(),
                     'Amiga SDK (vasmm68k_mot) not installed')
    def test_assembled_test_library_reads_as_version_1_0(self):
        import subprocess
        sdk = Path(os.environ.get('AMIWIND_SDK', '/opt/amiwind-tools/sdk'))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / '68040.library'
            subprocess.run([str(sdk / 'bin/vasmm68k_mot'), '-m68000', '-Fhunkexe', '-nosym', '-I',
                            str(sdk / 'm68k-amigaos/ndk-include'), '-o', str(target),
                            str(ROOT / 'tests/fpu_test_library.asm')], check=True, capture_output=True)
            info = ki.amiga_library_info(target.read_bytes(), '68040.library')
        self.assertTrue(info['valid'], info)
        self.assertEqual(info['version'], '1.0')
        self.assertEqual(info['id_string'], 'amiwind test library 1.0 (does nothing)')


class IdentityAndVerdictTests(unittest.TestCase):
    def test_tes3_bsa_and_kickstart_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'a.esm').write_bytes(sh.tes3_master(1.3, b'Someone', b'Line one\r\nline two', 12, [b'Morrowind.esm']))
            info = ki.tes3_master_info(tmp / 'a.esm')
            self.assertEqual((info['version'], info['author'], info['description'], info['records'], info['masters']),
                             ('1.30', 'Someone', 'Line one line two', 12, ['Morrowind.esm']))
            (tmp / 'b.esm').write_bytes(b'TES4' + bytes(40))
            self.assertFalse(ki.tes3_master_info(tmp / 'b.esm')['valid'])
            (tmp / 'a.bsa').write_bytes(sh.tes3_archive(3))
            self.assertEqual(ki.tes3_archive_info(tmp / 'a.bsa')['files'], 3)
            (tmp / 'b.bsa').write_bytes(b'BSA\0' + bytes(20))
            self.assertFalse(ki.tes3_archive_info(tmp / 'b.bsa')['valid'])
            (tmp / 'k.rom').write_bytes(sh.kickstart(40, 68))
            self.assertEqual(ki.kickstart_info(tmp / 'k.rom')['version'], '40.68')
            (tmp / 'e.rom').write_bytes(b'AMIROMTYPE1' + bytes(524288))
            self.assertEqual(ki.kickstart_info(tmp / 'e.rom')['version'], 'encrypted')
            (tmp / 'x.rom').write_bytes(bytes(1000))
            self.assertFalse(ki.kickstart_info(tmp / 'x.rom')['valid'])

    def test_known_unknown_invalid_messages(self):
        known = sh.fake_library(version=40, revision=2)
        table = table_with(('amiga-library', '68040.library', known, 'Synthetic OS 9 disk', True))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '68040.library'
            path.write_bytes(known)
            row = ki.classify('amiga-library', '68040.library', path, sha(known), table)
            self.assertEqual((row['verdict'], row['message']), ('known', 'known: Synthetic OS 9 disk (tested)'))
            other = sh.fake_library(version=40, revision=3)
            path.write_bytes(other)
            row = ki.classify('amiga-library', '68040.library', path, sha(other), table)
            self.assertEqual(row['message'], 'unknown build of 68040.library v40.3 (not tested; used)')
            path.write_bytes(b'junk')
            row = ki.classify('amiga-library', '68040.library', path, sha(b'junk'), table)
            self.assertEqual(row['verdict'], 'invalid')
            self.assertTrue(row['message'].startswith('invalid: not an Amiga library or version unreadable (not used)'))
            master = Path(tmp) / 'Morrowind.esm'
            master.write_bytes(sh.tes3_master())
            row = ki.classify('tes3-master', 'Morrowind.esm', master, ki.sha256_file(master), table)
            self.assertEqual(row['message'], 'unknown version of Morrowind.esm v1.30 (patched or modded? not tested; used)')
            row = ki.classify('tes3-master', 'Morrowind.esm', master, None, table)
            self.assertEqual(row['verdict'], 'unchecked')
            self.assertIn('SHA-256', ki.line(row))

    def test_rom_matches_by_hash_under_any_name(self):
        rom = sh.kickstart(40, 68)
        table = table_with(('kickstart-rom', 'kick.rom', rom, 'Synthetic ROM', True))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'renamed dump.bin'
            path.write_bytes(rom)
            row = ki.classify('kickstart-rom', path.name, path, sha(rom), table)
        self.assertEqual((row['verdict'], row['version']), ('known', '40.68'))

    def test_policies(self):
        rows = [{'verdict': v, 'required': r, 'name': n, 'bytes': 1, 'sha256': 'ab', 'version': '1', 'message': v}
                for v, r, n in (('known', False, 'a'), ('unknown', False, 'b'), ('invalid', False, 'c'))]
        self.assertEqual(len(ki.enforce(rows, 'warn', 'X')), 2)
        with self.assertRaisesRegex(ValueError, 'policy fail stops'):
            ki.enforce(rows, 'fail', 'X')
        self.assertEqual(len(ki.enforce(rows[:2], 'fail', 'X')), 1)
        with self.assertRaisesRegex(ValueError, 'require-known'):
            ki.enforce(rows[:2], 'require-known', 'X')
        self.assertEqual(ki.enforce(rows[:1], 'require-known', 'X'), [])
        required = [dict(rows[2], required=True)]
        with self.assertRaisesRegex(ValueError, 'policy warn stops'):
            ki.enforce(required, 'warn', 'X')
        with self.assertRaises(ValueError):
            ki.enforce(rows, 'lenient', 'X')


class GameDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'Data Files'
        self.data.mkdir()
        self.esm, self.bsa = sh.tes3_master(1.2, records=0), sh.tes3_archive(2)
        (self.data / 'morrowind.ESM').write_bytes(self.esm)
        (self.data / 'Morrowind.bsa').write_bytes(self.bsa)
        self.table = table_with(('tes3-master', 'Morrowind.esm', self.esm, 'Synthetic GOTY', True),
                                ('tes3-archive', 'Morrowind.bsa', self.bsa, 'Synthetic GOTY', True),
                                editions=[{'name': 'Synthetic GOTY (store A, reference)', 'masters_source': 'Synthetic GOTY',
                                           'bookart_ttf': 'all', 'reference': True},
                                          {'name': 'Synthetic GOTY (store B: bitmap fonts)', 'masters_source': 'Synthetic GOTY',
                                           'bookart_ttf': 'none', 'reference': False}])

    def tearDown(self):
        self.tmp.cleanup()

    def fonts(self, present):
        return {'font_sources': {'preferred_ttf': {name: present for name in ki.BOOKART_TTF},
                                 'families': {'magic': {'selected': 'ttf' if present else 'bitmap'}}},
                'loose_overrides': {'total': 3, 'by_folder': {'meshes': 2, 'textures': 1}}}

    def test_known_pair_names_the_edition_from_the_fonts(self):
        lock = ki.InputLock(None, 'full', self.table)
        report = ki.check_game_data(self.data, lock, 'require-known', input_report=self.fonts(True))
        self.assertEqual([r['verdict'] for r in report['files']], ['known', 'known'])
        self.assertEqual(report['absent'], ['Tribunal.esm', 'Tribunal.bsa', 'Bloodmoon.esm', 'Bloodmoon.bsa'])
        self.assertEqual(report['edition']['edition'], 'Synthetic GOTY (store A, reference)')
        self.assertTrue(report['edition']['reference'])
        self.assertEqual(report['warnings'], [])
        report = ki.check_game_data(self.data, lock, 'warn', input_report=self.fonts(False))
        self.assertEqual(report['edition']['edition'], 'Synthetic GOTY (store B: bitmap fonts)')
        self.assertEqual(report['warnings'], [])  # neither edition is a warning
        text = '\n'.join(ki.report_lines(report))
        self.assertIn('Edition: Synthetic GOTY (store B: bitmap fonts)', text)
        self.assertIn('Font sources: magic bitmap', text)
        self.assertIn('Loose files shadowing Morrowind.bsa copies: 3 (meshes 2, textures 1)', text)

    def test_modified_master_is_unknown_and_policies_apply(self):
        (self.data / 'morrowind.ESM').write_bytes(sh.tes3_master(1.2, records=1))
        (self.data / 'Tribunal.esm').write_bytes(b'garbage')
        lock = ki.InputLock(None, 'full', self.table)
        with self.assertRaisesRegex(ValueError, 'Tribunal.esm'):
            ki.check_game_data(self.data, lock, 'fail')
        (self.data / 'Tribunal.esm').unlink()
        report = ki.check_game_data(self.data, ki.InputLock(None, 'full', self.table), 'warn')
        self.assertEqual(report['files'][0]['verdict'], 'unknown')
        self.assertIn('patched or modded', report['warnings'][0])
        self.assertIn('unknown edition', report['edition']['edition'])
        with self.assertRaisesRegex(ValueError, 'require-known'):
            ki.check_game_data(self.data, ki.InputLock(None, 'full', self.table), 'require-known')
        (self.data / 'Morrowind.bsa').write_bytes(b'BSA?')
        with self.assertRaisesRegex(ValueError, 'policy warn stops'):  # an invalid required file always stops
            ki.check_game_data(self.data, ki.InputLock(None, 'full', self.table), 'warn')


class InputLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lock_path = self.root / 'ws' / ki.LOCK_NAME
        self.files = []
        for number in range(6):
            path = self.root / f'music/track{number}.mp3'
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b'synthetic %d' % number)
            self.files.append(path)
        self.core = self.root / 'Morrowind.esm'
        self.core.write_bytes(sh.tes3_master())
        self.table = table_with(('tes3-master', 'Morrowind.esm', self.core.read_bytes(), 'Synthetic', True))

    def tearDown(self):
        self.tmp.cleanup()

    def run_lock(self, mode, paths=None):
        lock = ki.InputLock(self.lock_path, mode, self.table, workers=4)
        lock.prepare(paths or self.files + [self.core])
        lock.save()
        return lock

    def test_first_run_writes_lock_and_unchanged_rerun_does_not_rehash(self):
        first = self.run_lock('auto')
        self.assertEqual(first.hash_calls, 7)
        record = json.loads(self.lock_path.read_text(encoding='utf-8'))
        self.assertEqual(record['schema'], ki.LOCK_SCHEMA)
        self.assertEqual(record['known_table']['revision'], 1)
        entry = record['files'][ki.lock_key(self.files[0])]
        self.assertEqual((entry['bytes'], entry['sha256']), (11, sha(b'synthetic 0')))
        self.assertIn('mtime_ns', entry)
        self.assertIn('birth_ns', entry)
        self.assertNotIn(b'\r', self.lock_path.read_bytes())
        again = self.run_lock('auto')
        self.assertEqual(again.hash_calls, 0)
        self.assertEqual(again.trusted, 7)
        self.assertEqual(again.sha256(self.files[2]), sha(b'synthetic 2'))

    def test_core_mode_always_hashes_core_inputs_only(self):
        self.run_lock('core')
        again = self.run_lock('core')
        self.assertEqual(again.hash_calls, 1)  # Morrowind.esm, by name
        self.assertEqual(again.current[ki.lock_key(self.core)]['checked'], 'hashed')
        lock = ki.InputLock(self.lock_path, 'core', self.table)
        lock.prepare(self.files[:1], core=True)
        self.assertEqual(lock.hash_calls, 1)
        # A core file first trusted as part of a big set is hashed when asked for as core.
        lock = ki.InputLock(self.lock_path, 'core', self.table)
        lock.prepare([self.files[1]])
        lock.prepare([self.files[1]], core=True)
        self.assertEqual((lock.hash_calls, lock.trusted), (1, 0))

    def test_changed_mtime_or_size_rehashes_only_that_file(self):
        self.run_lock('auto')
        stamp = os.stat(self.files[1])
        os.utime(self.files[1], ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 5_000_000_000))
        self.files[3].write_bytes(b'synthetic 3 longer')
        hashed = []
        lock = ki.InputLock(self.lock_path, 'auto', self.table, workers=4,
                            hasher=lambda path: hashed.append(Path(path).name) or ki.sha256_file(path))
        lock.prepare(self.files + [self.core])
        self.assertEqual(sorted(hashed), ['track1.mp3', 'track3.mp3'])
        self.assertEqual(sorted(Path(p).name for p in lock.changed), ['track1.mp3', 'track3.mp3'])
        text = '\n'.join(lock.messages)
        self.assertIn('track1.mp3; rehashed and verified again (content unchanged)', text)
        self.assertIn('track3.mp3; rehashed and verified again (content changed)', text)

    def test_full_always_rehashes(self):
        self.run_lock('auto')
        self.assertEqual(self.run_lock('full').hash_calls, 7)
        self.assertEqual(self.run_lock('full').hash_calls, 7)

    def test_off_hashes_nothing_and_warns(self):
        lock = self.run_lock('off')
        self.assertEqual(lock.hash_calls, 0)
        self.assertIsNone(lock.sha256(self.core))
        self.assertIn('NOT verified', '\n'.join(lock.summary_lines()))

    def test_corrupted_lock_is_moved_aside_and_rebuilt(self):
        self.lock_path.parent.mkdir()
        for broken in ('{not json', json.dumps({'schema': 'other', 'files': {}}),
                       json.dumps({'schema': ki.LOCK_SCHEMA, 'files': {'x': {'sha256': 'zz'}}})):
            self.lock_path.write_text(broken, encoding='utf-8')
            lock = self.run_lock('auto')
            self.assertEqual(lock.hash_calls, 7)
            self.assertIn('unreadable', lock.messages[0])
            self.assertEqual(json.loads(self.lock_path.read_text(encoding='utf-8'))['schema'], ki.LOCK_SCHEMA)
        self.assertEqual(len(list(self.lock_path.parent.glob(ki.LOCK_NAME + '.unreadable-*'))) >= 1, True)

    def test_table_change_is_reported(self):
        self.run_lock('auto')
        changed = dict(self.table, revision=2)
        lock = ki.InputLock(self.lock_path, 'auto', changed)
        self.assertIn('Known inputs table changed', '\n'.join(lock.messages))

    def test_birth_time_null_is_ignored_but_a_different_one_counts(self):
        old = {'bytes': 5, 'mtime_ns': 10, 'birth_ns': None}
        self.assertTrue(ki.same_stamp(old, {'bytes': 5, 'mtime_ns': 10, 'birth_ns': 99}))
        self.assertTrue(ki.same_stamp(dict(old, birth_ns=99), {'bytes': 5, 'mtime_ns': 10, 'birth_ns': None}))
        self.assertFalse(ki.same_stamp(dict(old, birth_ns=98), {'bytes': 5, 'mtime_ns': 10, 'birth_ns': 99}))
        self.assertFalse(ki.same_stamp(old, {'bytes': 6, 'mtime_ns': 10, 'birth_ns': None}))
        self.assertFalse(ki.same_stamp(old, {'bytes': 5, 'mtime_ns': 11, 'birth_ns': None}))
        stamp = ki.file_stamp(self.core)
        if os.name != 'nt' and not hasattr(os.stat(self.core), 'st_birthtime'):
            self.assertIsNone(stamp['birth_ns'])  # Linux: ctime is never used as a birth time

    def test_stat_and_rehash_run_in_a_thread_pool(self):
        threads, real = set(), ki.file_stamp

        def slow_stamp(path):
            threads.add(threading.get_ident())
            time.sleep(0.02)
            return real(path)
        with patch.object(ki, 'file_stamp', slow_stamp):
            lock = ki.InputLock(None, 'auto', self.table, workers=4)
            lock.prepare(self.files + [self.core])
        self.assertGreater(len(threads), 1)
        self.assertEqual(lock.hash_calls, 7)

    def test_stages_take_hashes_from_the_exported_lock(self):
        self.run_lock('full')
        ki._SHARED.clear()
        with patch.dict(os.environ, {ki.LOCK_ENV: str(self.lock_path)}), \
                patch.object(ki, 'sha256_file', side_effect=AssertionError('hashed again')):
            self.assertEqual(ki.input_sha256(self.core), sha(self.core.read_bytes()))
        self.files[0].write_bytes(b'changed content')
        with patch.dict(os.environ, {ki.LOCK_ENV: str(self.lock_path)}):
            self.assertEqual(ki.input_sha256(self.files[0]), sha(b'changed content'))
        ki._SHARED.clear()

    def test_reference_check_uses_the_lock_and_reports_unchecked(self):
        loose = {'music/track0.mp3': {'path': self.files[0], 'bytes': 11}}
        reference = {'music/track0.mp3': {'bytes': 11, 'sha256': sha(b'synthetic 0')}}
        lock = ki.InputLock(None, 'full', self.table)
        result = input_check.fingerprints(loose, 'aga', reference, lock)
        self.assertEqual((result['matching'], lock.hash_calls), (1, 1))
        input_check.fingerprints(loose, 'aga', reference, lock)
        self.assertEqual(lock.hash_calls, 1)  # one hash per input per build
        result = input_check.fingerprints(loose, 'aga', reference, ki.InputLock(None, 'off', self.table))
        self.assertEqual((result['matching'], result['unchecked'], result['different']), (0, 1, []))
        overrides = input_check.loose_overrides({'meshes/a.nif': {}, 'meshes/b.nif': {}, 'icons/c.dds': {}},
                                                {'meshes/a.nif': {}, 'icons/c.dds': {}})
        self.assertEqual(overrides['by_folder'], {'icons': 1, 'meshes': 1})


class AmigaLibraryStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.libs = self.root / 'wb/Libs'
        self.libs.mkdir(parents=True)
        self.known = sh.fake_library(version=40, revision=2)
        (self.libs / '68040.library').write_bytes(self.known)
        self.loader = self.root / 'AmiWindFPU'
        self.loader.write_bytes(b'\x00\x00\x03\xf3loader')
        self.table = table_with(('amiga-library', '68040.library', self.known, 'Synthetic OS disk', True))

    def tearDown(self):
        self.tmp.cleanup()

    def stage(self, policy, name='boot'):
        boot = self.root / name
        boot.mkdir()
        with patch.object(ki, 'load_table', return_value=self.table):
            return boot, fpu_support.stage(self.root / 'wb', boot, self.loader, policy=policy)

    def test_known_library_is_installed_with_its_verdict(self):
        boot, receipt = self.stage('require-known')
        row = receipt['libraries'][0]
        self.assertEqual((row['verdict'], row['version'], row['label']), ('known', '40.2', 'Synthetic OS disk'))
        self.assertEqual((boot / 'LIBS/68040.library').read_bytes(), self.known)
        line = fpu_support.summary_lines(receipt)[0]
        self.assertEqual(line, f'FPU support library: 68040.library v40.2 ({len(self.known):,} bytes) SHA-256 '
                               f'{sha(self.known)}: known: Synthetic OS disk (tested)')

    def test_unknown_used_with_warning_invalid_never_used(self):
        other = sh.fake_library(name=b'68060.library', version=43, revision=1)
        (self.libs / '68060.library').write_bytes(other)
        (self.libs / 'mmu.library').write_bytes(b'\x00\x00\x03\xf3 not really a library')
        boot, receipt = self.stage('warn')
        self.assertEqual([r['name'] for r in receipt['libraries']], ['68040.library', '68060.library'])
        self.assertEqual(receipt['libraries'][1]['message'], 'unknown build of 68060.library v43.1 (not tested; used)')
        self.assertEqual(len(receipt['warnings']), 2)
        self.assertEqual(receipt['rejected'][0]['name'], 'mmu.library')
        self.assertFalse((boot / 'LIBS/mmu.library').exists())
        self.assertIn('  not used: mmu.library', '\n'.join(fpu_support.summary_lines(receipt)))
        with self.assertRaisesRegex(ValueError, 'policy fail'):
            self.stage('fail', 'boot2')
        (self.libs / 'mmu.library').unlink()
        with self.assertRaisesRegex(ValueError, 'require-known'):
            self.stage('require-known', 'boot3')

    def test_only_invalid_support_libraries_install_nothing(self):
        (self.libs / '68040.library').write_bytes(b'\x00\x00\x03\xf3' + bytes(40))
        boot, receipt = self.stage('warn')
        self.assertEqual(receipt['status'], 'not_found')
        self.assertFalse((boot / 'AmiWindFPU').exists() or (boot / 'LIBS').exists())
        self.assertEqual(fpu_support.startup_sequence(receipt), 'FailAt 10\nSYS:AmiWindCheck\nStack 300000\nSYS:AmiWind\n')


class BuilderWiringTests(unittest.TestCase):
    def test_options_defaults_and_step_wiring(self):
        args = build.parser().parse_args([])
        self.assertEqual((args.check_hashes, args.game_data_policy, args.amiga_libs_policy), ('core', 'warn', 'warn'))
        args = build.parser().parse_args(['--amiga-libs', '/owned/wb', '--amiga-libs-policy', 'require-known',
                                          '--check-hashes', 'full'])
        args.data_files, args.sdk = Path('/owned/Data Files'), Path('/sdk')
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        image = dict(build.commands(args, tools, Path('/private/run')))['image']
        self.assertEqual(image[image.index('--amiga-libs-policy') + 1], 'require-known')
        dry = dict(build.dry_run_commands(args, Path('/out')))['dry-run-image']
        self.assertEqual(dry[dry.index('--amiga-libs-policy') + 1], 'require-known')

    def test_build_summary_prints_known_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = build_summary.BuildSummary(Path(tmp), 'test', 'AGA image')
            lock = ki.InputLock(None, 'off', table_with(('kickstart-rom', 'k.rom', b'x', 'Synthetic', True)))
            summary.known_inputs = {'check_hashes': lock.summary(), 'game_data': None, 'amiga_libs': None,
                                    'kickstart': None}
            with contextlib.redirect_stdout(io.StringIO()) as out:
                result = summary.finish('failed')
            self.assertEqual(result['known_inputs']['check_hashes']['mode'], 'off')
            self.assertIn('WARNING: --check-hashes off', out.getvalue())


class KnownTableTests(unittest.TestCase):
    def test_table_schema_and_seed_entries(self):
        table = ki.load_table()
        self.assertEqual(ki.check_table(table), [])
        names = {(e['kind'], e['name']): e for e in table['entries']}
        for name in ('Morrowind', 'Tribunal', 'Bloodmoon'):
            self.assertTrue(names[('tes3-master', name + '.esm')]['tested'])
            self.assertTrue(names[('tes3-archive', name + '.bsa')]['tested'])
        self.assertEqual(names[('amiga-library', '68040.library')]['version'], '37.30')
        self.assertEqual(names[('amiga-library', '68060.library')]['version'], '43.1')
        self.assertEqual(names[('amiga-library', 'mmu.library')]['version'], '43.11')
        # The ROM entry is the launcher's reference ROM: one truth, checked here.
        from run_fs_uae import REFERENCE_ROM_SHA256
        self.assertEqual(names[('kickstart-rom', 'kickstart-3.1-a1200.rom')]['sha256'], REFERENCE_ROM_SHA256)
        self.assertEqual({e['reference'] for e in table['editions']}, {True, False})
        raw = (ROOT / 'config/known-inputs.json').read_bytes()
        self.assertNotIn(b'\r', raw)
        self.assertFalse(any(line.endswith((b' ', b'\t')) for line in raw.split(b'\n')))

    def test_no_repository_file_is_a_listed_input(self):
        table = ki.load_table()
        listed = {e['sha256'] for e in table['entries']}
        sizes = {e['bytes'] for e in table['entries']}
        names = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        self.assertIn('config/known-inputs.json', names)
        self.assertIn('tools/known_inputs.py', names)
        for name in names:
            path = ROOT / name
            if path.is_file() and path.stat().st_size in sizes:
                self.assertNotIn(ki.sha256_file(path), listed, name)
            if path.is_file() and path.read_bytes()[:4] == b'\x00\x00\x03\xf3':
                self.fail('hunk executable in the repository: ' + name)


if __name__ == '__main__':
    unittest.main()
