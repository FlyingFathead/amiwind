"""Diagnostic logs stay in memory during play and are written at Exit game, on a fatal error or
with dbg savelogs; aw_logs_live / dbg logs live / builder --live-logs write them as they happen
for benchmarks (BOOT-VOLUME-NOT-VALIDATED-33)."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
sys.path.insert(0, str(ROOT / 'tools'))

LOG_FILES = ('DEBUG.TXT', 'walk-profile.csv', 'frame-stalls.csv', 'frame-profile.txt', 'heap-audit.log',
             'cell-load-profile.tsv', 'cell-visible-profile.tsv', 'bsp-load-profile.txt', 'music-events.csv',
             'music-profile.txt', 'console-history.txt')


def section(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]


class EngineSourceTests(unittest.TestCase):
    def test_no_engine_source_writes_a_diagnostic_log_itself(self):
        log = (SRC / 'aw_log.c').read_text(encoding='utf-8')
        for name in LOG_FILES:
            self.assertIn('"%s"' % name, log)
        for path in sorted(SRC.glob('*.c')):
            if path.name == 'aw_log.c':
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for name in LOG_FILES:
                self.assertNotRegex(text, r'fopen\s*\(\s*"%s"' % re.escape(name), path.name)
            self.assertNotIn('Sys_FileOpenWrite("DEBUG.TXT")', text, path.name)

    def test_switch_is_bound_before_the_first_write_and_logs_are_flushed_at_exit_and_on_fatal_errors(self):
        text = (SRC / 'sys_amiga.c').read_text(encoding='utf-8')
        main = section(text, 'int main(int argc', 'RunGameLoop();')
        self.assertLess(main.index('AW_LogUseSwitch(&aw_logs_live.value);'), main.index('Sys_Init('))
        quit_ = section(text, 'void Sys_Quit(void)', 'void Sys_Error (')
        self.assertLess(quit_.index('Host_Shutdown();'), quit_.index('AW_LogFlushAll();'))
        fatal = section(text, 'void Sys_Error (', 'void Sys_SendKeyEvents(')
        self.assertLess(fatal.index('Open("ERROR.TXT",MODE_NEWFILE)'), fatal.index('AW_LogFlushAll();'))
        self.assertLess(fatal.index('Host_Shutdown();'), fatal.index('AW_LogFlushAll();'))
        printf = section(text, 'void Sys_Printf (char *message', '#endif')
        self.assertIn('AW_LogWrite(AW_LOG_DEBUG, text);', printf)
        self.assertNotIn('Sys_Error', printf)

    def test_live_switch_default_off_saved_only_when_the_player_sets_it(self):
        text = (SRC / 'aw_debug.c').read_text(encoding='utf-8')
        self.assertIn('cvar_t aw_logs_live={"aw_logs_live","0",false};', text)
        command = section(text, 'static void logs_live_command(void)', '\n}\n')
        self.assertIn('aw_logs_live.archive=true;', command)
        init = section(text, 'void AW_DebugInit(void) {', '\n}\n')
        for registered in ('Cvar_RegisterVariable(&aw_logs_live);', 'Cmd_AddCommand("aw_logs_live_set",logs_live_command);',
                           'Cmd_AddCommand("aw_savelogs",savelogs_command);'):
            self.assertIn(registered, init)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('DIAGNOSTICS|logs live|aw_logs_live_set|', catalogue)
        self.assertIn('DIAGNOSTICS|savelogs|aw_savelogs|', catalogue)
        self.assertNotIn('aw_logs_live', (ROOT / 'config/game.cfg').read_text(encoding='utf-8'))
        self.assertIn('aw_log.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))


class BuilderOptionTests(unittest.TestCase):
    def test_stage_game_config_live_logs(self):
        from build_aga import stage_game_config
        with tempfile.TemporaryDirectory() as tmp:
            record = stage_game_config(tmp)
            plain = (Path(tmp) / 'default-game.cfg').read_bytes()
            self.assertEqual(record, {'diagnostic_logs': 'memory'})
            self.assertNotIn(b'aw_logs_live', plain)
            record = stage_game_config(tmp, live_logs=True)
            live = (Path(tmp) / 'default-game.cfg').read_bytes()
            self.assertEqual(record, {'diagnostic_logs': 'live'})
            self.assertTrue(live.startswith(plain))
            self.assertTrue(live.endswith(b'aw_logs_live 1\n'))
            self.assertNotIn(b';', live[len(plain):])  # a semicolon in a comment runs (CFG-01)

    def test_builder_passes_live_logs_only_when_asked(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        import test_build_defaults as defaults
        self.assertNotIn('--live-logs', dict(defaults.steps())['image'])
        self.assertIn('--live-logs', dict(defaults.steps('--live-logs'))['image'])
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("i.add_argument('--live-logs',action='store_true'", source)


@unittest.skipIf(os.name == 'nt', 'Native helper fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'A host C compiler is required')
class BufferAndReaderTests(unittest.TestCase):
    def build(self, temp):
        exe = Path(temp) / 'aw-log-check'
        result = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-fsanitize=undefined,address',
                                 '-fno-sanitize-recover=all', '-I' + str(SRC), str(ROOT / 'tests/aga_log_test.c'),
                                 str(SRC / 'aw_log.c'), '-o', str(exe)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return exe

    def test_bounded_ordered_flushed_and_switched(self):
        with tempfile.TemporaryDirectory(prefix='amiwind-log-') as temp:
            exe = self.build(temp)
            run = Path(temp) / 'run'
            run.mkdir()
            result = subprocess.run([str(exe)], cwd=run, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('aw_log ok', result.stdout)

    def test_benchmark_reader_reads_live_and_flushed_logs(self):
        from profile_aga import summarize
        context = {key: 'x' for key in ('emulator_sha256', 'rom_sha256', 'effective_machine', 'host_class', 'route',
                                         'source_assets_sha256', 'view_settings', 'storage_mode')}
        with tempfile.TemporaryDirectory(prefix='amiwind-log-') as temp:
            exe = self.build(temp)
            counts = {}
            for mode in ('live', 'memory'):
                run = Path(temp) / mode
                run.mkdir()
                result = subprocess.run([str(exe), 'profile', mode], cwd=run, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = summarize(run, context)
                self.assertEqual(report['frame']['frames'], 3000)
                self.assertEqual(report['music']['track_history'], '4,11,42')
                counts[mode] = report['sample_count']
            # Live (benchmark images): every sample; memory: the newest ones that fit the buffer.
            self.assertEqual(counts['live'], 300)
            self.assertGreater(counts['memory'], 50)
            self.assertLess(counts['memory'], 300)


if __name__ == '__main__':
    unittest.main()
