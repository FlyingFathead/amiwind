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



class DefaultFastRamTests(unittest.TestCase):
    """The maintainer, 27 October 2026: the game runs at 32 MB of Fast RAM by default from now on."""
    def test_smoke_runs_at_32_mb_by_default(self):
        self.assertEqual(engine_smoke.DEFAULT_FAST_MB, 32)
        self.assertIn('FASTMB=${FASTMB:-32}', engine_smoke.PROBE)
        self.assertIn("'--fast-mb', type=int, default=DEFAULT_FAST_MB", (ROOT / 'tools/engine_smoke.py').read_text())
        with unittest.mock.patch.object(engine_smoke, 'docker') as docker, \
                contextlib.redirect_stdout(io.StringIO()):
            code = engine_smoke.main(['--engine', '/nonexistent', '--volume', 'v', '--image-dir', 'i',
                                      '--scratch', 's', '--roms', '/nonexistent', '--out', '/nonexistent'])
        self.assertEqual(code, 2)
        docker.assert_not_called()

    def test_boot_ends_the_logo_before_typing(self):
        # SMOKE-M-KEY-SKIPS-CHIM-CACHE-57: the m of a command typed onto the start-up logo answered its memory notice
        # (CHIM cache off for that start); Escape ends the logo before the first console line
        # PERSISTING in v0.0.59: on a busy host the logo began after that Escape; the boot loop now only presses Escape
        # (the play copy's autoexec turns the remote on) and types the command only after 90 s
        # REGRESSION v0.0.60 (gate 6418): the logo came after 90 s on a loaded host; nothing is typed before ready now
        a = engine_smoke.PROBE.index('# BOOT-WAIT-BEGIN')
        boot = engine_smoke.PROBE[a:engine_smoke.PROBE.index('# BOOT-WAIT-END')]
        boot = '\n'.join(l for l in boot.splitlines() if not l.lstrip().startswith('#'))
        self.assertNotIn('con ', boot)
        self.assertNotIn('rc ', boot)
        self.assertNotIn('key ', boot)    # gate 6810: an early Escape held the AmigaDOS preflight
        with open(engine_smoke.__file__, encoding='utf-8') as f:
            self.assertIn("printf 'aw_remote 1", f.read())    # the autoexec the boot loop relies on

    @unittest.skipUnless(shutil.which('bash'), 'bash needed')
    def test_late_logo_gets_no_typed_key_before_ready(self):
        # Simulated loaded host: the logo shows at 100 s and 200 s of the wait (past the old 90 s fallback) and the
        # remote answers at 240 s. Every input the loop sends is logged; nothing may reach the screen before ready.
        a = engine_smoke.PROBE.index('# BOOT-WAIT-BEGIN')
        boot = engine_smoke.PROBE[a:engine_smoke.PROBE.index('# BOOT-WAIT-END')]
        with tempfile.TemporaryDirectory() as d:
            script = '''set -e
R=%s; K=1; T=0; mkdir -p $R/awctl
alive(){ return 0; }
finish(){ echo "FINISH $1" >> $R/sent; exit 0; }
sleep(){ T=$((T+$1)); [ $T -ge 240 ] && echo up > $R/awctl/state.txt; return 0; }
key(){ echo "key $1 at $T" >> $R/sent; }
con(){ echo "con $1 at $T" >> $R/sent; }
rc(){ echo "rc $1 at $T" >> $R/sent; }
%s
[ -s $R/awctl/state.txt ] && echo "READY at $T" >> $R/sent
''' % (d, boot)
            subprocess.run(['bash', '-c', script], check=True, timeout=30)
            sent = (Path(d) / 'sent').read_text().splitlines()
        self.assertEqual(len(sent), 1, sent)
        self.assertTrue(int(sent[0].split()[-1]) >= 240, sent)
        self.assertTrue(sent[0].startswith('READY at '), sent)

    def test_zone_full_names_a_skipped_cache(self):
        self.assertIn('SMOKE-M-KEY-SKIPS-CHIM-CACHE-57', engine_smoke.PROBE)
        self.assertIn('CHIM cache off (skipped for this start)', engine_smoke.PROBE)

    def test_sweep_step_is_logged_and_can_fail_the_smoke(self):
        """ENTITY-SWEEP-AB: dbg sweep's SWEEP RESULT line in the smoke; --sweep fail makes a FAIL result fatal."""
        self.assertIn('rc "aw_sweep"', engine_smoke.PROBE)
        self.assertIn('FAIL dbg sweep', engine_smoke.PROBE)


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
        for needle in ('jit_compiler = 1', 'hard_drive_1_read_only = 1',
                       # CHIM-SEYDA-BALMORA-LOAD-HANG-43: the disks on the emulated A1200 IDE, not uaehf.device
                       'hard_drive_0_controller = ide0', 'hard_drive_1_controller = ide1','rc "map $MAP1"', 'aw_music_status off',
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

    def test_music_checks_wait_for_a_fresh_answer_and_a_silent_game_is_a_stall(self):
        # SMOKE-MUSIC-REREAD-FLAKY-57: the game stopped taking commands a few seconds after a load (state.txt no longer
        # written) and the music check failed on the previous status line; now a command not taken in RC_WAIT is a
        # stall (examined, an emulator disk stall retried once), and each music value is a NEW status answer
        text = engine_smoke.PROBE
        rc = next(l for l in text.splitlines() if l.startswith('rc(){'))
        self.assertIn('RC_WAIT:-60', rc)
        self.assertIn('stall "the game stopped taking commands', text)
        self.assertIn("grep -c 'reads='", text)                        # status waits for a new line
        self.assertIn('MUSIC_WAIT:-45', text)                            # a window, not one fixed sleep
        self.assertNotIn('rc "aw_music_status"; sleep $((3*K)); c=$(reads)', text)
        self.assertIn('[ -e $R/finished ] && exit 0', text)              # the first result stands
        self.assertIn('FAIL music did not read again after dbg music on', text)   # still strict on a real stall

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
        # ARRIVAL-LONG-FRAME-DEV6-59: three samples or more, none idle: the processor works (a long frame), even with
        # the game in a file call; a real deadlock (every sample idle, a request held) stays the disk stall
        self.assertEqual(classify([0x00F811BC, 0x00FA838C, 0x00F828D2, 0x00F811BC], tasks, stack)[0], 'busy')
        self.assertEqual(classify(idle, tasks, stack)[0], 'emulator-disk')
        self.assertEqual(classify([0x00F811BC, 0x00FA838C], tasks, stack)[0], 'unknown')
        self.assertIn('FAIL long frame (busy)', engine_smoke.PROBE)

    def test_every_stop_is_examined_and_names_the_pending_request(self):
        """SMOKE-INPLAY-UNSAMPLED-63: the not-in-play stop goes through the examination too, any other FAIL is
        examined before the run ends, and the examination names the queued request and its handler."""
        text = engine_smoke.PROBE
        start = text.index('inplay(){')
        body = text[start:text.index('# stall:', start)]
        self.assertIn('stall "$1 is not in play', body)
        self.assertNotIn('finish "FAIL $1 is not in play', body)
        self.assertIn('stall "map ${TP#map:} did not load a map', text)
        self.assertIn('stall(){ : > $R/examined;', text)
        self.assertIn('log "examined at the stop:', text)
        classify = self.stall_classify()
        game = ('Initial CLI', 0x4000F8A8, 0x100, True)
        tasks = [game, ('DH0', 0x40010618, 0x40000100, True), ('AWCTL', 0x40020000, 0x40000100, True)]
        idle = [0xF81476, 0xF81478, 0xF81478]
        reply = game[1] + 0x5C
        kind, details = classify(idle, tasks, [], {'AWCTL': [(0x40030000, reply, 87, 0x40031000)]})
        self.assertEqual(kind, 'emulator-disk')
        self.assertIn("request WRITE (arg1 $40031000, packet $40030000) queued on AWCTL's port, not taken", details)
        kind, details = classify(idle, tasks, [], {'Initial CLI': [(0x40030000, reply, 82, 0x1234)]})
        self.assertEqual(kind, 'emulator-disk')
        self.assertIn('completion signal was lost', details)
        # another process's packet on a handler port is not the game's; nothing named, no stack holder: unknown
        kind, details = classify(idle, tasks, [], {'DH0': [(0x40030000, 0x40099999, 82, 0)]})
        self.assertEqual(kind, 'unknown')
        self.assertIn('no request of the game queued', details)
        self.assertIn('ports not read', classify(idle, tasks, [])[1])

    def test_ide_trace_is_left_out_unless_asked(self):
        """SMOKE-IDE-TRACE-LOG-63: the IDE transfer lines (compiled into the emulator package) leave the kept logs by
        default; --ide-trace keeps them."""
        self.assertIn('idetrim $R/logs/fs-uae.log.txt $R/logs/fsuae.log', engine_smoke.PROBE)
        self.assertIn("f'IDETRACE={int(args.ide_trace)}'", (ROOT / 'tools/engine_smoke.py').read_text())
        text = engine_smoke.PROBE
        start = text.index('idetrim(){')
        body = text[start:text.index('done; }', start) + len('done; }')]
        if not shutil.which('sh'):
            self.skipTest('a POSIX shell is required')
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, 'fs-uae.log.txt')
            for trace, kept, said in (('0', 2, '2 lines left out'), ('1', 4, '')):
                log.write_text('IDE0 read finished\nkeep one\nIDE INT 80 -> 08\nkeep two\n', encoding='utf-8')
                script = Path(tmp, 't.sh')
                script.write_text('log(){ echo "$*"; }\nIDETRACE=%s\n%s\nidetrim %s\n' % (trace, body, log.as_posix()),
                                  encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(len(log.read_text(encoding='utf-8').splitlines()), kept)
                self.assertIn(said, done.stdout)

    def test_load_trace_is_a_separate_switch_and_its_ring_is_read_at_a_stop(self):
        """LOAD-HANG-WATCHDOG-62: --load-trace (off by default) puts aw_loadtrace 1 into the play copy's autoexec and
        LOADTRACE=1 into the run; the examination decodes the engine's ring (aw_loadtrace.c layout) and names the
        calls that never finished."""
        source = (ROOT / 'tools/engine_smoke.py').read_text()
        self.assertIn("trace_line = 'aw_loadtrace 1\\\\n' if args.load_trace else ''", source)
        self.assertIn("printf 'aw_remote 1\\\\n{trace_line}' > /tmp/autoexec.cfg", source)
        self.assertIn("f'LOADTRACE={int(args.load_trace)}'", source)
        self.assertIn("default=os.environ.get('AW_SMOKE_LOAD_TRACE') == '1'", source)
        self.assertIn('trace = load_trace()', engine_smoke.STALL_PY)
        space = {'__name__': 'stall'}
        exec(compile(engine_smoke.STALL_PY, 'stall.py', 'exec'), space)
        ring_lines = space['ring_lines']

        def entry(t0, t1, nbytes, result, op, stage, name):
            return (t0.to_bytes(4, 'big') + t1.to_bytes(4, 'big') + (nbytes & 0xFFFFFFFF).to_bytes(4, 'big')
                    + (result & 0xFFFFFFFF).to_bytes(4, 'big') + bytes([op]) + stage.encode().ljust(11, b'\0')
                    + name.encode().ljust(36, b'\0'))
        entries = [entry(0, 0, 0, 0, 0, '', '')] * 4
        # 6 calls through a 4-entry ring: calls 3..6 kept, call N in entry (N - 1) mod 4
        entries[2] = entry(100, 110, 0, -1, 1, 'after-bsp', 'id1/combat/settings.txt')     # call 3
        entries[3] = entry(120, 130, 4096, 4096, 2, 'after-bsp', 'maps/balmora.chim')        # call 4
        entries[0] = entry(140, 141, 0, 0, 4, 'after-bsp', 'maps/balmora.chim')              # call 5
        entries[1] = entry(150, 0xFFFFFFFF, 512, 0, 2, 'after-actor', 'progs/a.mdl')         # call 6
        raw = b'AWLTRACE' + (6).to_bytes(4, 'big') + (4).to_bytes(4, 'big') + (64).to_bytes(4, 'big') + bytes(4)
        lines, unfinished = ring_lines(raw + b''.join(entries))
        self.assertEqual(lines, ['LT 3 after-bsp open id1/combat/settings.txt 0 bytes -> -1, at 100 ms, 10 ms',
                                 'LT 4 after-bsp read maps/balmora.chim 4096 bytes -> 4096, at 120 ms, 10 ms',
                                 'LT 5 after-bsp close maps/balmora.chim 0 bytes -> 0, at 140 ms, 1 ms',
                                 'LT 6 after-actor read progs/a.mdl 512 bytes, at 150 ms, NOT FINISHED'])
        self.assertEqual(unfinished, lines[-1:])
        self.assertEqual(ring_lines(b'NOTARING' + raw[8:]), ([], []))
        self.assertEqual(ring_lines(raw[:20]), ([], []))

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
    def test_a_window_with_ticks_moving_is_not_a_stall(self):
        """LOAD-STALL-SESSIONS-59: realtime standing while the engine's ticks move and a window is open (screen not
        game) passes the wait; neither moving, or the game screen with only ticks moving, is a stall as before."""
        text = engine_smoke.PROBE
        start = text.index('play(){')
        end = text.index('(realtime $r1 -> $r2)"; }', start) + len('(realtime $r1 -> $r2)"; }')
        body = text[start:end]

        def verdict(before, after):
            stubs = ('P=1\nK=1\nst(){ if [ $P = 1 ]; then set -- "$1" %s; else set -- "$1" %s; fi\n'
                     '  case "$1" in realtime) echo "$2";; ticks) echo "$3";; screen) echo "$4";; esac; }\n'
                     'alive(){ return 0; }\nsleep(){ P=2; }\nlog(){ echo "log $*"; }\n'
                     'finish(){ echo "$1"; exit 0; }\n') % (before, after)
            done = subprocess.run(['sh', '-c', stubs + body + '\nplay 3 "a script"\necho ok\n'],
                                  capture_output=True, text=True, timeout=60)
            return done.stdout.strip().splitlines()[-1]
        self.assertEqual(verdict('71.20 10 game', '74.20 50 game'), 'ok')
        self.assertEqual(verdict('71.20 10 inventory', '71.20 14 inventory'), 'ok')
        self.assertEqual(verdict('71.20 10 inventory', '71.20 10 inventory'),
                         'FAIL game stalled during a script (realtime 71.20 -> 71.20)')
        # ARRIVAL-LONG-FRAME-DEV6-59: the game screen with only the ticks moving is a long frame (busy): it gets the
        # grace and, when realtime never moves again, fails as a long frame, never as a stall
        self.assertEqual(verdict('71.20 10 game', '71.20 14 game'),
                         'FAIL long frame (busy) during a script: realtime stood at 71.20 for 3 s and 60 s more while '
                         'the engine ran (ticks 10 -> 14), not a disk stall')
        # ... and passes, named a long frame, when realtime moves again inside the grace
        stubs = ('K=1\nN=0\nst(){ case "$1" in realtime) [ $N -ge 6 ] && echo 75.00 || echo 71.20;; '
                 'ticks) echo $((10+N));; screen) echo game;; esac; }\n'
                 'alive(){ return 0; }\nsleep(){ N=$((N+1)); }\nlog(){ echo "log $*"; }\nfinish(){ echo "$1"; exit 0; }\n')
        done = subprocess.run(['sh', '-c', stubs + body + '\nplay 3 "a script"\necho ok\n'],
                              capture_output=True, text=True, timeout=60)
        lines = done.stdout.strip().splitlines()
        self.assertEqual(lines[-1], 'ok')
        self.assertTrue(lines[-2].startswith('log long frame (busy) during a script: realtime stood at 71.20'), lines)
        # an engine without the ticks line: as before
        self.assertEqual(verdict('71.20 "" menu', '71.20 "" menu'),
                         'FAIL game stalled during a script (realtime 71.20 -> 71.20)')
        # the session patch (fsuae_session.py STALL_FROM) still finds its line exactly once
        self.assertEqual(text.count('|| finish "FAIL game stalled during $2 (realtime $r1 -> $r2)"; }'), 1)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_a_frame_without_heartbeat_gets_a_grace_before_the_stall(self):
        """SESSION-STALL-AFTER-LONG-FRAME-62: the state file is written between frames and on the heartbeat only, so a
        frame of several seconds without a heartbeat left realtime and ticks standing over a 1 s wait, and the session
        was called stalled while the game was still working. Both standing now get STALL_GRACE seconds; a frame that
        ends inside it is logged and the wait passes; a game that never moves again is still a stall."""
        text = engine_smoke.PROBE
        self.assertIn('STALL_GRACE:-30', text)
        start = text.index('play(){')
        end = text.index('(realtime $r1 -> $r2)"; }', start) + len('(realtime $r1 -> $r2)"; }')
        body = text[start:end]

        def run(moves_at, what, grace=''):
            # sleep() is one second; from the sleep numbered moves_at on, realtime and/or the ticks move
            stubs = ('K=1\nN=0\n%s'
                     'st(){ case "$1" in realtime) [ %d -ge 0 ] && [ $N -ge %d ] && [ %s = 1 ] && echo 76.00 || echo 69.21;; '
                     'ticks) [ %d -ge 0 ] && [ $N -ge %d ] && echo $((14441+N)) || echo 14441;; screen) echo game;; esac; }\n'
                     'alive(){ return 0; }\nsleep(){ N=$((N+1)); }\nlog(){ echo "log $*"; }\n'
                     'finish(){ echo "$1 after $N s"; exit 0; }\n') % (
                         grace, moves_at, moves_at, 1 if what == 'clock' else 0, moves_at, moves_at)
            done = subprocess.run(['sh', '-c', stubs + body + '\nplay 1 "a script"\necho "ok after $N s"\n'],
                                  capture_output=True, text=True, timeout=60)
            return done.stdout.strip().splitlines()
        # the frame ends 8 s in (as the 6.8 s script-file frame of the talk session): logged, passes
        lines = run(8, 'clock')
        self.assertEqual(lines[-1], 'ok after 8 s', lines)
        self.assertEqual(lines[-2], 'log long frame during a script: realtime 69.21 and ticks 14441 stood for 1 s and '
                                    '7 s more, then went on (realtime 76.00, ticks 14449)')
        # nothing moves again: the stall verdict, after the grace (STALL_GRACE, 30 s by default)
        self.assertEqual(run(-1, 'clock')[-1], 'FAIL game stalled during a script (realtime 69.21 -> 69.21) after 31 s')
        self.assertEqual(run(-1, 'clock', grace='STALL_GRACE=5\n')[-1],
                         'FAIL game stalled during a script (realtime 69.21 -> 69.21) after 6 s')
        # only the ticks move after a while (a heartbeat inside the frame): the long-frame (busy) rules take over
        self.assertTrue(run(4, 'ticks')[-1].startswith('FAIL long frame (busy) during a script: realtime stood at 69.21'),
                        run(4, 'ticks'))

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
    def test_a_quoted_id_with_a_space_reaches_the_command_file_unchanged(self):
        """TEST-HARNESS-MINIWIND-62: cmd dbg npcs talk "agronian guy" goes into the game's command file as written,
        quotes kept (the engine's debug translator keeps it one argument)."""
        text = engine_smoke.PROBE
        start = text.index('if [ -s $R/script.txt ]; then')
        block = text[start:text.index('\nfi\n', start) + 4]
        rc = text[text.index('rc(){ '):text.index('log "cmd $1"; }') + len('log "cmd $1"; }')]
        line = 'cmd dbg npcs talk "agronian guy"'
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'awctl').mkdir()
            Path(tmp, 'script.txt').write_text(line + '\n', encoding='utf-8', newline='\n')
            stubs = ('R=%s\nK=1\nlog(){ :; }\nstall(){ echo "stall $1"; exit 0; }\nplay(){ :; }\nalive(){ return 0; }\n'
                     'st(){ case "$1" in screen) echo game;; signon) echo 4;; *) echo 1;; esac; }\n'
                     'finish(){ echo "finish $1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            done = subprocess.run(['sh', '-c', stubs + rc + '\n' + block], capture_output=True, text=True, timeout=30,
                                  input='')
            written = Path(tmp, 'awctl', 'cmd.txt').read_text(encoding='utf-8')
        self.assertEqual(written, line[len('cmd '):] + '\n', done.stdout + done.stderr)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_start_map_any_takes_the_map_the_image_starts_on(self):
        """TEST-HARNESS-MINIWIND-62: MAP1 any with START enter waits for whichever map the image loads (a MiniWind's
        one map), not a named one it does not hold."""
        text = engine_smoke.PROBE
        start = text.index('if [ "${START:-map}" = enter ]')
        block = text[start:text.index('\nelse rc "map $MAP1"', start)] + '\nfi\n'
        stubs = ('K=1\nSTART=enter\nMAP1=any\nkey(){ :; }\nsleep(){ :; }\nalive(){ return 0; }\nlog(){ echo "log $*"; }\n'
                 'loaded(){ echo "loaded $1"; }\nstall(){ echo "stall $1"; exit 0; }\nfinish(){ echo "finish $1"; exit 0; }\n'
                 'st(){ case "$1" in server) echo seyda;; map) echo maps/seyda-chim.chim;; local) echo "1 2 3";; esac; }\n')
        done = subprocess.run(['sh', '-c', stubs + block], capture_output=True, text=True, timeout=30)
        lines = done.stdout.splitlines()
        self.assertIn('log start map from the game: seyda', lines, done.stdout + done.stderr)
        self.assertIn('loaded seyda', lines)
        self.assertFalse([l for l in lines if l.startswith(('stall', 'finish'))], done.stdout)

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


class LoadHangExperimentTests(unittest.TestCase):
    """CHIM-SEYDA-BALMORA-LOAD-HANG-43, experiments E2 (remote console off against on) and E3 (extra emulator lines,
    e.g. deterministic = 1): what can be checked without the emulator."""

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = engine_smoke.main(list(argv))
        return code, out.getvalue()

    def setup_dirs(self, tmp):
        engine = Path(tmp, 'AmiWind')
        engine.write_bytes(b'x')
        roms = Path(tmp, 'roms')
        roms.mkdir()
        Path(roms, 'kickstart-3.1-a1200.rom').write_bytes(b'k')
        return engine, roms

    def test_route_autoexec(self):
        text = engine_smoke.route_autoexec('seyda', '-21800 -12300', 120, load_trace=True)
        lines = text.splitlines()
        self.assertEqual(lines[:3], ['dbg all on', 'dbg coords on', 'aw_loadtrace 1'])
        self.assertNotIn('aw_remote', text)
        self.assertEqual(lines[3], 'alias aw_e2w "%s"' % ';'.join(['wait'] * 50))
        self.assertEqual(lines[4], 'alias aw_e2p "aw_e2w;aw_e2w;aw_e2w"')        # 120 frames -> 3 x 50
        self.assertEqual(lines[5], 'alias aw_e2b "dbg tp -21800 -12300;aw_e2p;aw_e2s"')
        self.assertEqual(lines[6], 'alias aw_e2s "map seyda;aw_e2p;aw_e2b"')
        self.assertEqual(lines[7], 'aw_e2s')
        self.assertTrue(all(len(l) < 1000 for l in lines))
        self.assertNotIn('aw_loadtrace', engine_smoke.route_autoexec('seyda', '1 2', 1))
        for bad in (('seyda;quit', '1 2', 10), ('seyda', '1 2;quit', 10), ('seyda', '1 2', 0)):
            with self.assertRaises(ValueError):
                engine_smoke.route_autoexec(*bad)

    def test_emulator_options_parse_and_lines(self):
        opts = engine_smoke.parse_emu_options(['deterministic=1', 'cpu_idle = 0'])
        self.assertEqual(opts, [('deterministic', '1'), ('cpu_idle', '0')])
        self.assertEqual(engine_smoke.emu_config_lines(opts), 'deterministic = 1\ncpu_idle = 0\n')
        self.assertEqual(engine_smoke.parse_emu_options(['none']), [])
        for bad in ('deterministic', 'Bad=1', 'x=1\nhard_drive_9=y', 'zorro_iii_memory=1', 'hard_drive_2=/x',
                    'jit_compiler=0', 'x=a b'):
            with self.assertRaises(ValueError, msg=bad):
                engine_smoke.parse_emu_options([bad])

    def test_emulator_option_is_checked_in_the_log(self):
        log = 'something\nlibamiga enabling net play mode\n'
        self.assertEqual(engine_smoke.emu_check([('deterministic', '1')], [log]), [])
        self.assertEqual(engine_smoke.emu_check([('deterministic', '1')], ['nothing']), ['deterministic=1'])
        self.assertEqual(engine_smoke.emu_check([('cpu_idle', '0')], ['cpu_idle = 0']), [])
        self.assertEqual(engine_smoke.emu_check([('cpu_idle', '0')], ['cpu_idle = 1']), ['cpu_idle=0'])
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'judge.py').write_text(engine_smoke.JUDGE_PY, encoding='utf-8')
            Path(tmp, 'o.txt').write_text('deterministic = 1\n', encoding='utf-8')
            Path(tmp, 'a.log').write_text(log, encoding='utf-8')
            run = subprocess.run([sys.executable, str(Path(tmp, 'judge.py')), 'emucheck', str(Path(tmp, 'o.txt')),
                                  str(Path(tmp, 'missing.log')), str(Path(tmp, 'a.log'))], capture_output=True, text=True)
        self.assertEqual(run.stdout.strip(), 'EMUOPT ok deterministic=1 taken (emulator log)')
        probe = engine_smoke.PROBE
        self.assertIn('[ -s $R/emu-options.txt ] && cat $R/emu-options.txt >> $R/smoke.fs-uae', probe)
        self.assertIn('shot menu; emucheck', probe)              # remote on: checked once the game answers
        self.assertIn('[ $i = 1 ] && emucheck', probe)           # remote off: at the first screenshot

    def test_frozen_clock_from_a_list_of_frames(self):
        judge = engine_smoke.judge_frames
        moving = [(t, 'd%d' % t) for t in range(0, 300, 10)]
        self.assertEqual(judge(moving, 150, final=True)[0], 'PASS')
        self.assertEqual(judge(moving, 150)[0], 'RUN')
        # a 60 s loading picture, then play again: no stop
        load = [(t, 'L' if 100 <= t <= 160 else 'd%d' % t) for t in range(0, 300, 10)]
        self.assertEqual(judge(load, 150, final=True)[0], 'PASS')
        # frozen from 100 s to the end (270 s): a stop, live and final
        frozen = [(t, 'F' if t >= 100 else 'd%d' % t) for t in range(0, 280, 10)]
        verdict, details = judge(frozen, 150)
        self.assertEqual(verdict, 'STOP')
        self.assertIn('from 100 s to 270 s', details)
        self.assertEqual(judge(frozen, 150, final=True)[0], 'STOP')
        # live judges only the newest run; final any run
        past = [(t, 'F' if 50 <= t <= 210 else 'd%d' % t) for t in range(0, 300, 10)]
        self.assertEqual(judge(past, 150)[0], 'RUN')
        self.assertEqual(judge(past, 150, final=True)[0], 'STOP')
        # a picture that never moved under the limit still fails the route
        self.assertEqual(judge([(0, 'a'), (10, 'a'), (20, 'b')], 150, final=True)[0], 'FAIL')
        self.assertEqual(judge([], 150, final=True)[0], 'FAIL')

    def test_remote_off_drops_the_folder_and_runs_the_route(self):
        probe = engine_smoke.PROBE
        cfg = probe[probe.index('cat > $R/smoke.fs-uae <<CFG'):probe.index('\nCFG\n')]
        self.assertNotIn('hard_drive_2', cfg)                  # only added with the remote on
        self.assertIn('[ "${REMOTE:-1}" = 0 ] || printf \'hard_drive_2 = %s', probe)
        block = probe[probe.index('# ROUTE-OFF-BEGIN'):probe.index('# ROUTE-OFF-END')]
        self.assertNotIn('rc ', block)
        self.assertNotIn('key ', block)
        self.assertIn('stall "frozen clock', block)            # a stop is examined like any other
        self.assertLess(probe.index('# ROUTE-OFF-END'), probe.index('# BOOT-WAIT-BEGIN'))
        with tempfile.TemporaryDirectory() as tmp:
            engine, roms = self.setup_dirs(tmp)
            sha = engine_smoke.sha256(engine)
            calls = []

            def fake(*args, **kw):
                calls.append(args)
                if '/out/probe.sh' in args:
                    out = Path(next(a for a in args if str(a).endswith(':/out'))[:-5])
                    (out / 'logs').mkdir(parents=True, exist_ok=True)
                    (out / 'logs' / 'steps.log').write_text('00:00 smoke RESULT PASS remote console off, route x\n',
                                                            encoding='utf-8')
                return subprocess.CompletedProcess(args, 0, 'world=\nreadback=%s\n' % sha, '')
            o = Path(tmp, 'o')
            with unittest.mock.patch.object(engine_smoke, 'docker', side_effect=fake):
                code, text = self.run_main('--engine', str(engine), '--volume', 'v', '--image-dir', 'build/image',
                                           '--scratch', 'workspaces/s', '--roms', str(roms), '--out', str(o),
                                           '--remote', 'off', '--emu-option', 'deterministic=1')
            self.assertEqual(code, 0, text)
            self.assertIn('alias aw_e2s "map seyda;aw_e2p;aw_e2b"', (o / 'autoexec.cfg').read_text())
            self.assertEqual((o / 'emu-options.txt').read_text(), 'deterministic = 1\n')
            self.assertTrue((o / 'judge.py').is_file())
            self.assertIn('remote console off', (o / 'engine.txt').read_text())
            prep = next(a for a in calls if '-prep' in ' '.join(map(str, a)))
            self.assertIn('cp /t/autoexec.cfg /tmp/autoexec.cfg', prep[-1])
            self.assertNotIn('aw_remote', prep[-1])
            run = next(a for a in calls if '/out/probe.sh' in a)
            self.assertIn('REMOTE=0', run)
            # remote on (default): the old autoexec, REMOTE=1
            calls.clear()
            with unittest.mock.patch.object(engine_smoke, 'docker', side_effect=fake):
                self.run_main('--engine', str(engine), '--volume', 'v', '--image-dir', 'build/image',
                              '--scratch', 'workspaces/s', '--roms', str(roms), '--out', str(o))
            prep = next(a for a in calls if '-prep' in ' '.join(map(str, a)))
            self.assertIn("printf 'aw_remote 1\\n' > /tmp/autoexec.cfg", prep[-1])
            self.assertIn('REMOTE=1', next(a for a in calls if '/out/probe.sh' in a))
            self.assertFalse((o / 'emu-options.txt').exists())

    def test_bad_options_exit_2_before_any_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine, roms = self.setup_dirs(tmp)
            common = ['--engine', str(engine), '--volume', 'v', '--image-dir', 'i', '--scratch', 's', '--roms',
                      str(roms), '--out', str(Path(tmp, 'o'))]
            for extra in (['--remote', 'maybe'], ['--emu-option', 'hard_drive_0=/x'],
                          ['--remote', 'off', '--tp', 'same 1 2'], ['--remote', 'off', '--start', 'enter'],
                          ['--alternate', 'emu']):
                with unittest.mock.patch.object(engine_smoke, 'docker') as docker:
                    code, _text = self.run_main(*common, *extra)
                self.assertEqual(code, 2, extra)
                docker.assert_not_called()
            with unittest.mock.patch.dict('os.environ', {'AW_SMOKE_EMU_OPTION': 'kickstart_file=/x'}), \
                    unittest.mock.patch.object(engine_smoke, 'docker'):
                self.assertEqual(self.run_main(*common)[0], 2)

    def test_alternating_counts(self):
        self.assertEqual(engine_smoke.count_class('PASS boot'), 'pass')
        self.assertEqual(engine_smoke.count_class('FAIL emulator disk stall (X) y'), 'stop')
        self.assertEqual(engine_smoke.count_class('FAIL frozen clock on the route, remote console off: z'), 'stop')
        self.assertEqual(engine_smoke.count_class('FAIL dbg music off not confirmed'), 'fail')
        self.assertEqual(engine_smoke.strip_options(['--a', '1', '--b=2', '--c', '3'], ('--a', '--b')), ['--c', '3'])
        with tempfile.TemporaryDirectory() as tmp:
            engine, roms = self.setup_dirs(tmp)
            seen = []

            def fake_main(argv):
                o = Path(argv[argv.index('--out') + 1])
                seen.append(argv)
                (o / 'logs').mkdir(parents=True)
                off = argv[argv.index('--remote') + 1] == 'off'
                (o / 'logs' / 'steps.log').write_text('smoke RESULT %s\n' % (
                    'FAIL frozen clock x' if off and len(seen) == 2 else 'PASS y'), encoding='utf-8')
                return 0
            argv = ['--engine', str(engine), '--volume', 'v', '--image-dir', 'i', '--scratch', 's', '--roms', str(roms),
                    '--out', str(Path(tmp, 'o')), '--alternate', 'remote', '--runs', '2', '--emu-option', 'deterministic=1']
            real = engine_smoke.main

            def route(a=None):
                return real(a) if '--alternate' in a else fake_main(a)
            with unittest.mock.patch.object(engine_smoke, 'main', side_effect=route):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = engine_smoke.main(argv)
            self.assertEqual(code, 0)
            self.assertEqual([a[a.index('--remote') + 1] for a in seen], ['on', 'off', 'on', 'off'])   # alternating
            self.assertTrue(all('--no-stall-retry' in a and a.count('--emu-option') == 1 for a in seen))
            self.assertNotIn('--alternate', seen[0])
            self.assertIn('COUNTS remote-on: 2 pass, 0 stop, 0 other fail of 2; '
                          'remote-off: 1 pass, 1 stop, 0 other fail of 2', out.getvalue())
            self.assertIn('1\tremote-off\tstop\tFAIL frozen clock x', Path(tmp, 'o', 'counts.tsv').read_text())
            # emu: plain (no option) then with it, the remote on in both
            seen.clear()
            argv[argv.index('remote')] = 'emu'
            with unittest.mock.patch.object(engine_smoke, 'main', side_effect=route):
                with contextlib.redirect_stdout(io.StringIO()):
                    engine_smoke.main(argv)
            self.assertEqual([a[a.index('--emu-option') + 1] for a in seen], ['none', 'deterministic=1'] * 2)
            self.assertTrue(all(a[a.index('--remote') + 1] == 'on' for a in seen))

    def test_judge_script_runs_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'judge.py').write_text(engine_smoke.JUDGE_PY, encoding='utf-8')
            Path(tmp, 'frames.txt').write_text(''.join('%d %s route-%03d\n' % (t, 'F' if t >= 50 else 'x%d' % t, t)
                                                       for t in range(0, 300, 10)), encoding='utf-8')
            run = subprocess.run([sys.executable, str(Path(tmp, 'judge.py')), 'live', str(Path(tmp, 'frames.txt')),
                                  '150'], capture_output=True, text=True)
        self.assertTrue(run.stdout.startswith('STOP the same picture from 50 s to 290 s'), run.stdout)
