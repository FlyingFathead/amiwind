# SPDX-License-Identifier: GPL-3.0-only
"""tools/engine_smoke.py (with its emulator-side PROBE script): the FS-UAE boot + map-load smoke (CHIM-DEV3-MAPLOAD-CRASH-36).

The emulator run itself needs Docker, an image and the maintainer's Kickstart, so it runs in the gate (step "smoke"), not
here. These checks keep the scripts runnable and the steps that caught the dev3 crash in place.
"""
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import engine_smoke  # noqa: E402



class EngineSmokeTests(unittest.TestCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = engine_smoke.main(list(argv))
        return code, out.getvalue()

    def test_setup_errors_exit_2_before_any_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp, 'AmiWind')
            engine.write_bytes(b'x')
            roms = Path(tmp, 'roms')
            roms.mkdir()
            common = ['--volume', 'v', '--image-dir', 'build/image', '--roms', str(roms), '--out', str(Path(tmp, 'o'))]
            with unittest.mock.patch.object(engine_smoke, 'docker') as docker:
                code, out = self.run_main('--engine', str(engine), '--scratch', '../x', *common)
                self.assertEqual((code, out.splitlines()[-1]), (2, 'smoke-exit=2'))
                code, out = self.run_main('--engine', str(engine), '--scratch', 'workspaces/s', *common)
                self.assertEqual((code, out.splitlines()[-1]), (2, 'smoke-exit=2'))   # no Kickstart
                docker.assert_not_called()

    def test_probe_steps(self):
        text = engine_smoke.PROBE
        self.assertNotIn('\r', text)
        for needle in ('jit_compiler = 1', 'hard_drive_1_read_only = 1', 'rc "map $MAP1"', 'aw_music_status off',
                       'aw_music_status on', 'rc "dbg tp $TP"', 'finish "PASS boot', 'FAIL emulator exited', 'FAIL music read while off',
                       # a one-area image (the whole-city Vivec MiniWind): --tp "same X Y" teleports inside --map
                       'rc "dbg tp ${TP#same }"', 'left $MAP1',
                       # --tp "view X Y Z [YAW]": the client view must arrive (wide network coordinates); --start enter;
                       # --log-illegal: FS-UAE logs unmapped accesses (JOB_PREAMBLE 53)
                       'rc "aw_view $1 $2 $3 ${4:-0} 0"', 'network coordinates', 'START:-map', 'uae_log_illegal_mem = 1',
                       # SMOKE-PASSES-WITHOUT-MAP-36: every map is proven in play, and the run must end in play
                       'inplay "$MAP1"', 'inplay "the second load', '[ "$(st screen)" = game ]', 'world_leafs',
                       'FAIL the run ended outside play'):
            self.assertIn(needle, text)

    def test_map_change_repeats(self):
        """CHIM-SEYDA-BALMORA-LOAD-HANG-43: one map change passed 3 of 5 runs; the smoke repeats it (default 3)."""
        text = engine_smoke.PROBE
        for needle in ('REPEAT=${REPEAT:-3}', '[ $r -ge $REPEAT ] && break', 'rc "map $MAP1"; loaded "$MAP1"',
                       'load $r of $REPEAT', 'map change ran $r times'):
            self.assertIn(needle, text)
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp, 'AmiWind')
            engine.write_bytes(b'x')
            roms = Path(tmp, 'roms')
            roms.mkdir()
            Path(roms, 'kickstart-3.1-a1200.rom').write_bytes(b'k')
            calls = []

            sha = engine_smoke.sha256(engine)

            def fake(*args, **kw):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0, 'world=\nreadback=%s\n' % sha, '')
            with unittest.mock.patch.object(engine_smoke, 'docker', side_effect=fake):
                self.run_main('--engine', str(engine), '--volume', 'v', '--image-dir', 'build/image', '--scratch', 'workspaces/s',
                              '--roms', str(roms), '--out', str(Path(tmp, 'o')), '--repeat', '5')
        run = next(c for c in calls if '/out/probe.sh' in c)
        self.assertIn('REPEAT=5', run)

    def test_stall_is_examined_with_the_monitor(self):
        """CHIM-SEYDA-BALMORA-LOAD-HANG-43: a load that does not finish is examined (stall.py), not only timed out."""
        text = engine_smoke.PROBE
        for needle in ('console_debugger = 1', 'modifier_key = key_lalt', 'mkfifo $R/dbg.in', 'python3 $R/stall.py',
                       'stall "dbg tp $TP did not load a map', 'stall "$1 did not load',
                       'FAIL emulator disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43)'):
            self.assertIn(needle, text)
        compile(engine_smoke.STALL_PY, 'stall.py', 'exec')

    def stall_classify(self):
        space = {'__name__': 'stall'}
        exec(compile(engine_smoke.STALL_PY, 'stall.py', 'exec'), space)
        return space['classify']

    def test_stall_classes(self):
        classify = self.stall_classify()
        dh0 = 0x40010618
        tasks = [('Initial CLI', 0x4000F8A8, 0x100, True), ('DH0', dh0, 0x40000100, True),
                 ('input.device', 0x40008CFA, 0xC0000000, False)]
        idle = [0xF81476, 0xF81478, 0xF81478]
        stack = [0x00F8161A, dh0 + 0x5C + 0x14, 0x4000F904]
        kind, details = classify(idle, tasks, stack)
        self.assertEqual(kind, 'emulator-disk')
        self.assertIn('request held by DH0', details)
        # the engine running (a loop in its own code), no request held, or the game not in a file call: unknown
        self.assertEqual(classify([0x400D85E2, 0xF81476], tasks, stack)[0], 'unknown')
        self.assertEqual(classify(idle, tasks, [0x00F8161A])[0], 'unknown')
        self.assertEqual(classify(idle, [('Initial CLI', 0x4000F8A8, 0x10, True)] + tasks[1:], stack)[0], 'unknown')
        self.assertEqual(classify([], tasks, stack)[0], 'unknown')

    def test_emulator_disk_stall_is_retried_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp, 'AmiWind')
            engine.write_bytes(b'x')
            roms = Path(tmp, 'roms')
            roms.mkdir()
            Path(roms, 'kickstart-3.1-a1200.rom').write_bytes(b'k')
            sha = engine_smoke.sha256(engine)
            results = iter(['FAIL emulator disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43) dbg tp: x',
                            'FAIL emulator disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43) dbg tp: y'])
            runs = []

            def fake(*args, **kw):
                if '/out/probe.sh' in args:
                    out = Path(next(a for a in args if str(a).endswith(':/out'))[:-5])
                    (out / 'logs').mkdir(parents=True, exist_ok=True)
                    (out / 'logs' / 'steps.log').write_text('00:00 smoke RESULT %s\n' % next(results), encoding='utf-8')
                    self.assertTrue((out / 'stall.py').is_file())   # the stall check goes with every run
                    runs.append(out)
                return subprocess.CompletedProcess(args, 0, 'world=\nreadback=%s\n' % sha, '')
            with unittest.mock.patch.object(engine_smoke, 'docker', side_effect=fake):
                code, text = self.run_main('--engine', str(engine), '--volume', 'v', '--image-dir', 'build/image',
                                           '--scratch', 'workspaces/s', '--roms', str(roms), '--out', str(Path(tmp, 'o')))
        self.assertEqual(len(runs), 2)                     # one retry, not more
        self.assertEqual(runs[1].name, 'retry')
        self.assertIn('retrying once on a fresh play copy', text)
        self.assertEqual((code, text.splitlines()[-1]), (1, 'smoke-exit=1'))

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_probe_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp, 'probe.sh')
            probe.write_text(engine_smoke.PROBE, encoding='utf-8', newline='\n')
            result = subprocess.run(['sh', '-n', str(probe)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_state_reads_wait_for_a_complete_file(self):
        """Gate 1907 flake: a state file caught mid-write gave an empty value; st() reads only complete copies."""
        text = engine_smoke.PROBE
        start = text.index('st(){')
        body = text[start:text.index('done; }', start) + len('done; }')]
        with tempfile.TemporaryDirectory() as tmp:
            awctl = Path(tmp, 'awctl')
            awctl.mkdir()
            script = Path(tmp, 'st.sh')
            # 10 tries x 0.2 s: the half-written case below completes after 1 s, well inside them
            script.write_text('R=%s\nSTATE_TRIES=10\n%s\nst realtime\n' % (Path(tmp).as_posix(), body),
                              encoding='utf-8', newline='\n')
            state = awctl / 'state.txt'
            state.write_text('commands 1\nrealtime 62.10\nmap seyda\nend\n', encoding='utf-8', newline='\n')
            done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=120)
            self.assertEqual(done.stdout.strip(), '62.10')
            # half written: no "end" line yet; the game finishes the write while st() waits
            state.write_text('commands 1\nreal', encoding='utf-8', newline='\n')
            proc = subprocess.Popen(['sh', str(script)], stdout=subprocess.PIPE, text=True)
            import time
            time.sleep(1.0)
            state.write_text('commands 2\nrealtime 63.40\nmap seyda\nend\n', encoding='utf-8', newline='\n')
            out, _ = proc.communicate(timeout=120)
            self.assertEqual(out.strip(), '63.40')
            # never completed: an empty value after the retries, never a partial one
            state.write_text('commands 3\nrealtime 6', encoding='utf-8', newline='\n')
            done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=120)
            self.assertEqual(done.stdout.strip(), '')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_zone_full_fails_a_pass_from_32_mb(self):
        """CHIM-ZONE-BUDGET-33 (v0.0.51): a CHIM chunk waiting for room in the zone fails the smoke from 32 MB of Fast
        RAM; at 16 MB the retries are the known cost; --allow-zone-full only counts them."""
        text = engine_smoke.PROBE
        start = text.index('zonefull(){')
        body = text[start:text.index('exit 0; }', start) + len('exit 0; }')]
        line = ('CHIM: chunk 395 not loaded: zone full (model 7530, 10896 bytes; largest free 4544, free 5792, '
                'locked 6696768 of 6720064); retrying\n')

        def verdict(fast_mb, lines, allow='fail', result='PASS boot'):
            with tempfile.TemporaryDirectory() as tmp:
                awctl = Path(tmp, 'awctl')
                awctl.mkdir()
                (awctl / 'console.log').write_text('Loading audio: 12 mixer updates\n' + line * lines,
                                                   encoding='utf-8', newline='\n')
                stubs = ('st(){ case "$1" in efrags_bad) echo 0;; screen) echo game;; esac; }\n'
                         'alive(){ return 1; }\nsleep(){ :; }\nlog(){ echo "$*"; }\nFP=999999\nXP=999999\n')
                script = Path(tmp, 'finish.sh')
                script.write_text('R=%s\nFASTMB=%d\nZONEFULL=%s\n%s%s\nfinish "%s"\n'
                                  % (Path(tmp).as_posix(), fast_mb, allow, stubs, body, result),
                                  encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60)
                return done.stdout.strip().splitlines()[-1]
        self.assertEqual(verdict(32, 0), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(32, 3), 'smoke RESULT FAIL CHIM zone full 3 times at 32 MB of Fast RAM (none '
                                         'allowed from 32 MB: CHIM-ZONE-BUDGET-33)')
        self.assertEqual(verdict(128, 1)[:32], 'smoke RESULT FAIL CHIM zone full')
        self.assertEqual(verdict(16, 405), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(32, 3, allow='allow'), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(32, 3, result='FAIL music not reading'), 'smoke RESULT FAIL music not reading')

if __name__ == '__main__':
    unittest.main()


class ScriptedSessionTests(unittest.TestCase):
    """--script: a scripted session (evidence shots, replays) instead of the music and second-load steps."""

    def test_script_option_copies_the_script(self):
        self.assertIn("'--script'", Path(engine_smoke.__file__).read_text(encoding='utf-8'))
        self.assertIn('if [ -s $R/script.txt ]; then', engine_smoke.PROBE)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_every_step_runs_although_a_step_reads_stdin(self):
        """ffmpeg (shot) reads standard input: the script is read on fd 3, so a shot does not swallow the next steps."""
        text = engine_smoke.PROBE
        start = text.index('if [ -s $R/script.txt ]; then')
        block = text[start:text.index('\nfi\n', start) + 4]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'script.txt').write_text('cmd noclip\nshot a\nwait 1\nkey Return\n# note\nxdo mousedown 1 mouseup 1\nstate local\ncmd aw_view 1 2 3 0 0\n',
                                              encoding='utf-8', newline='\n')
            stubs = ('R=%s\nlog(){ echo "log $*"; }\nrc(){ echo "rc $1"; }\nkey(){ :; }\nxdo(){ echo "xdo $1"; }\nplay(){ echo "play $1"; }\n'
                     'shot(){ cat > /dev/null; echo "shot $1"; }\nst(){ case "$1" in screen) echo game;; signon) echo 4;; *) echo 1;; esac; }\nalive(){ return 0; }\n'
                     'finish(){ echo "finish $1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            script = Path(tmp, 'run.sh')
            script.write_text(stubs + block, encoding='utf-8', newline='\n')
            done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60, input='')
        lines = done.stdout.splitlines()
        self.assertEqual([l for l in lines if l.startswith(('rc ', 'shot ', 'play ', 'xdo '))],
                         ['rc noclip', 'shot a', 'play 1', 'xdo mousedown 1 mouseup 1', 'rc aw_view 1 2 3 0 0'])
        self.assertTrue(lines[-1].startswith('finish PASS script'), done.stdout + done.stderr)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_rec_steps_start_and_stop_a_clip(self):
        """rec NAME / recstop (SKEL-ANIM-STAGE-52): an H.264 clip of the run while the script goes on; finish ends it."""
        text = engine_smoke.PROBE
        self.assertIn('-c:v libx264', text)
        self.assertIn('recstop; cp $R/home/Cache/Logs/fs-uae.log.txt', text)
        start = text.index('if [ -s $R/script.txt ]; then')
        block = text[start:text.index('\nfi\n', start) + 4]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'script.txt').write_text('rec cycle\nwait 1\nrecstop\nshot b\n', encoding='utf-8', newline='\n')
            stubs = ('R=%s\nlog(){ :; }\nrc(){ :; }\nplay(){ echo "play $1"; }\nrec(){ echo "rec $1"; }\n'
                     'recstop(){ echo recstop; }\nshot(){ echo "shot $1"; }\n'
                     'st(){ case "$1" in screen) echo game;; signon) echo 4;; *) echo 1;; esac; }\nalive(){ return 0; }\n'
                     'finish(){ echo "finish $1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            done = subprocess.run(['sh', '-c', stubs + block], capture_output=True, text=True, timeout=30, input='')
        self.assertEqual(done.stdout.splitlines()[:4], ['rec cycle', 'play 1', 'recstop', 'shot b'], done.stderr)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_script_rejects_disconnected_game_after_host_error(self):
        text = engine_smoke.PROBE
        start = text.index('if [ -s $R/script.txt ]; then')
        block = text[start:text.index('\nfi\n', start) + 4]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'script.txt').write_text('cmd dbg tp 77348 17749\nwait 1\n')
            # Reproduce Host_Error: emulator and realtime remain alive, but the map is gone.
            stubs = ('R=%s\nrc(){ :; }\nplay(){ :; }\nalive(){ return 0; }\n'
                     'st(){ case "$1" in screen) echo game;; map) echo none;; *) echo 0;; esac; }\n'
                     'finish(){ echo "$1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            result = subprocess.run(['sh', '-c', stubs + block], capture_output=True, text=True, timeout=30)
        self.assertIn('FAIL scripted run ended outside play', result.stdout)
        self.assertNotIn('PASS', result.stdout)
