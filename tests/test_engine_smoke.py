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

    def test_a_running_game_is_not_read_as_waiting(self):
        """STALL-PROBE-RUNNING-GAME-66: the v0.0.66-dev4 and dev6 journey stops: every sample in game code, the game
        the running task (in neither exec list), its stale wait mask still holding SIGF_DOS; the probe said "game
        waits on SIGF_DOS" or "game task not found". Now: the running task is read from ExecBase, a wait is reported
        only for a task in the Wait list, the state file's age is given, and every handler's wait is named."""
        classify = self.stall_classify()
        busy = [0x401FEA88, 0x401FEA88, 0x401B71EE, 0x40200C0A, 0x40200C58]
        dh0 = 0x40010618
        handlers = [('DH0', dh0, 0x40000100, True, 'wait', 8), ('AWCTL', 0x40020000, 0x40000100, True, 'wait', 8)]
        game = ('Initial CLI', 0x4000F8A8, 0x100, True, 'running', 8)
        kind, details = classify(busy, [game] + handlers, [], {}, 'Initial CLI', 0.4)
        self.assertEqual(kind, 'busy')
        self.assertIn('game is the running task, not in a file call', details)
        self.assertNotIn('waits on SIGF_DOS', details)
        self.assertIn('state file written 0 s before the examination', details)
        self.assertIn('handlers: DH0 idle on its port (waits $40000100), AWCTL idle on its port (waits $40000100)', details)
        # between two frames the game sits in the Ready list: running too, whatever its last wait mask was
        kind, details = classify(busy, [('Initial CLI', 0x4000F8A8, 0x100, True, 'ready', 8)] + handlers, [], {},
                                 'input.device', 1.0)
        self.assertEqual(kind, 'busy')
        self.assertIn('game is ready to run, not in a file call', details)
        # the lists walked without the game and ThisTask names it: the running task, not a missing one
        kind, details = classify(busy, handlers, [], {}, 'Initial CLI', None)
        self.assertEqual(kind, 'busy')
        self.assertIn('game is the running task, not in a file call; pending: the game runs; no request pending', details)
        self.assertNotIn('state file written', details)
        # a wait on another signal than SIGF_DOS is said with its mask
        kind, details = classify(busy, [('Initial CLI', 0x4000F8A8, 0x1010, True, 'wait', 8)] + handlers, [], {})
        self.assertIn('game waits on $00001010, not in a file call', details)
        # the stall proper: every sample idle, the game in the Wait list on SIGF_DOS, and DH0 waiting on something
        # that is not its packet port: it holds the request and the layer below it has not answered
        idle = [0xF81476, 0xF81478, 0xF81478]
        waiting = ('Initial CLI', 0x4000F8A8, 0x100, True, 'wait', 8)
        kind, details = classify(idle, [waiting, ('DH0', dh0, 0x00001000, True, 'wait', 8), handlers[1]], [], {})
        self.assertEqual(kind, 'emulator-disk')
        self.assertIn('game waits on SIGF_DOS', details)
        self.assertIn('handlers: DH0 busy (waits $00001000, not its port bit 8), AWCTL idle on its port (waits $40000100)',
                      details)
        # every handler idle on its port and nothing else named: unknown, as before
        self.assertEqual(classify(idle, [waiting] + handlers, [], {})[0], 'unknown')
        # a handler whose mask is exactly its port bit: idle on its port, no mask repeated
        self.assertIn('handlers: DH0 idle on its port,', classify(idle, [waiting, ('DH0', dh0, 0x100, True, 'wait', 8),
                                                                           handlers[1]], [], {})[1])
        # the examination reads ThisTask and the port signal bits, and the load trace ring whenever the console names it
        self.assertIn('be32(base, 0x114)', engine_smoke.STALL_PY)
        self.assertIn("port[0x0F] if len(port) > 0x0F else None", engine_smoke.STALL_PY)
        self.assertNotIn("os.environ.get('LOADTRACE') != '1'", engine_smoke.STALL_PY)
        self.assertIn('state file written', engine_smoke.STALL_PY)

    def test_the_packet_the_handler_masks_and_the_units_are_named(self):
        """CHIM-SEYDA-BALMORA-LOAD-HANG-43, the repeat2 stop of 15 November 2026: every traced call had finished, the
        remote folder's unit (DH2) read "idle on its port" although the emulator's directory-drive handler waits for
        its port and the host side alike, and the game's packet was not read. Now: the packet off the game's stack,
        every handler's whole mask, the unit that serves the remote folder named, a signalled task that sleeps said."""
        space = {'__name__': 'stall'}
        exec(compile(engine_smoke.STALL_PY, 'stall.py', 'exec'), space)
        stack_packet, packet_text, unit_labels, classify = (space[k] for k in
                                                            ('stack_packet', 'packet_text', 'unit_labels', 'classify'))
        base, reply = 0x4000E000, 0x4000F8A8 + 0x5C
        # a StandardPacket at stack offset 0x100: sp_Msg (ln_Name -> sp_Pkt), then sp_Pkt (dp_Link -> sp_Msg, dp_Port)
        s = bytearray(3072)
        msg, pkt = 0x100, 0x114
        s[msg + 10:msg + 14] = (base + pkt).to_bytes(4, 'big')
        s[pkt:pkt + 4] = (base + msg).to_bytes(4, 'big')
        s[pkt + 4:pkt + 8] = reply.to_bytes(4, 'big')
        for k, v in ((8, 87), (12, 0), (16, 0), (20, 0x40031000), (24, 0x40040000), (28, 8192)):
            s[pkt + k:pkt + k + 4] = v.to_bytes(4, 'big')
        pk = stack_packet(bytes(s), base, reply)
        self.assertEqual(pk, (87, 0, 0, 0x40031000, 0x40040000, 8192))
        self.assertEqual(packet_text(pk), "the game's packet on its stack: WRITE (arg1 $40031000, arg2 $40040000, "
                                          "arg3 8192; res1 0, res2 0)")
        self.assertIn("FINDOUTPUT of 'AWCTL:console.log'", packet_text((1006, 0, 0, 1, 2, 3), 'AWCTL:console.log'))
        self.assertIn('res1 -1, res2 205', packet_text((82, 0xFFFFFFFF, 205, 1, 2, 3)))
        self.assertIsNone(stack_packet(bytes(s), base, reply + 4))      # another task's reply port: not the game's
        self.assertIsNone(packet_text(None))
        # the name of an open, lock or delete is a BCPL pointer: the address is the value times 4 (the A/B's stop of 16
        # November 2026, FINDINPUT with arg3 $106D9863, printed no name while the raw value was read as the address)
        name_addr, bstr = space['name_addr'], space['bstr']
        self.assertEqual(name_addr((1005, 0, 205, 0x106D978F, 0, 0x106D9863)), 0x41B6618C)
        self.assertEqual(name_addr((8, 0, 0, 0x1000, 0x2000, 0)), 0x8000)          # LOCATE_OBJECT names arg2
        self.assertIsNone(name_addr((87, 0, 0, 1, 2, 3)))                          # a WRITE names no file
        self.assertIsNone(name_addr(None))
        self.assertEqual(bstr(b'\x0dAWCTL:cmd.txt' + bytes(20)), 'AWCTL:cmd.txt')
        self.assertIsNone(bstr(b'\x00abc'))
        self.assertIsNone(bstr(b'\x40short'))                                      # the length runs past the bytes
        self.assertIsNone(bstr(b''))
        # the handler's word for the command (sp_Msg + 4, the directory-drive handler's queue state; 16 November 2026):
        # -1 = the host side finished it and the reply pass never came, the lost interrupt request of the two stops
        stack_message_status, status_text = space['stack_message_status'], space['status_text']
        self.assertEqual(stack_message_status(bytes(s), base, reply), 0)
        s[msg + 4:msg + 8] = (0xFFFFFFFF).to_bytes(4, 'big')
        self.assertEqual(stack_message_status(bytes(s), base, reply), -1)
        self.assertIsNone(stack_message_status(bytes(s), base, reply + 4))
        self.assertIn("the handler's word for it is -1: the emulator's host side finished the request and the handler "
                      "was never told", packet_text(pk, None, -1))
        self.assertTrue(packet_text(pk, None, 0).endswith("handed to the emulator's host side, not finished"))
        self.assertIn('is 1: queued by the handler, not started', status_text(1))
        self.assertIn('$40031000 (not a directory-drive queue word)', status_text(0x40031000))
        self.assertEqual(status_text(None), '')
        self.assertEqual(packet_text(pk), packet_text(pk, None, None))
        self.assertIn('packet_text(pk, pname, stack_message_status(s, sbase, node + 0x5C))', engine_smoke.STALL_PY)
        labels = unit_labels('FS: mounted virtual unit DH2 (/out/awctl)\nFS: AWCTL (flags=00000002) starting..\n')
        self.assertEqual(labels, {'DH2': 'the remote-console folder /out/awctl'})
        idle = [0xF81476, 0xF81478, 0xF81478]
        game = ('Initial CLI', 0x4000F8A8, 0x100, True, 'wait', 8, 0)
        dh2 = ('DH2', 0x40020000, 0x80000100, True, 'wait', 8, 0)
        ramlib = ('ramlib', 0x40021000, 0x10, True, 'wait', 8, 0)
        kind, details = classify(idle, [game, dh2, ramlib], [], {}, None, 96.0, labels, packet_text(pk))
        self.assertIn("the game's packet on its stack: WRITE", details)
        self.assertIn('handlers: DH2 (the remote-console folder /out/awctl) idle on its port (waits $80000100), '
                      'ramlib busy (waits $00000010, not its port bit 8)', details)
        # a task that holds the very signal it waits on was never woken by the scheduler: said on the task and the game
        kind, details = classify(idle, [('Initial CLI', 0x4000F8A8, 0x100, True, 'wait', 8, 0x100),
                                        ('DH2', 0x40020000, 0x80000100, True, 'wait', 8, 0x80000000)], [], {})
        self.assertIn('game waits on SIGF_DOS SIGNALLED BUT ASLEEP ($00000100 received)', details)
        self.assertIn('DH2 idle on its port (waits $80000100) SIGNALLED BUT ASLEEP ($80000000 received)', details)
        # STALL-PROBE-PROMPT-LOG-LINE-66 (repeat3): a prompt with an emulator log line after it on the same line is a
        # prompt; the echo of the command just sent is not; a debugger that activated without a readable prompt is resumed
        prompts, state_note = space['prompts'], space['state_note']
        self.assertEqual(len(prompts('WARNING: Activated debugger\n>need_metadata_file 6 WF_ALWAYS WF_EXISTS\n')), 1)
        self.assertEqual(len(prompts('>d\n00F81478 2080 MOVE.L D0,(A0)\n>', sent='d')), 1)
        self.assertEqual(prompts('>d\n00F81478 2080 MOVE.L D0,(A0)\n', sent='d'), [])
        self.assertEqual(len(prompts('>m $00000004 !1\n00000004 4000 0924\n>', sent='m $00000004 !1')), 1)
        self.assertEqual(prompts('some other output\n', sent=None), [])
        self.assertIn("if 'Activated debugger' in tail_from(pos):\n        paused = True\n        resume()", engine_smoke.STALL_PY)
        # the state file's content, not its modification time, says whether the game runs
        self.assertIn('the game runs', state_note(('100.00', '10'), ('100.52', '41')))
        self.assertIn('unchanged: the game is stopped', state_note(('100.00', '10'), ('100.00', '10')))
        self.assertIn('no end line', state_note(None, None))
        self.assertNotIn('os.path.getmtime', engine_smoke.STALL_PY)
        kind, details = classify(idle, [game, dh2], [], {}, None, state_note(None, None))
        self.assertIn('state file unreadable (no end line', details)
        # the write op of the load trace ring decodes, and the examine script step logs a baseline without failing
        self.assertEqual(space['LT_OPS'][5], 'write')
        # stall.py's stderr is kept, never dropped
        self.assertNotIn("stall check could not run') 2>/dev/null", engine_smoke.PROBE)
        self.assertEqual(engine_smoke.PROBE.count("2>>$R/logs/stall-errors.txt"), 3)

    def test_a_failed_examination_resumes_the_emulator_and_says_why(self):
        """STALL-PROBE-PROMPT-LOG-LINE-66 (repeat4, 15 November 2026): the examination failed after its break-in, its
        error went to /dev/null and the emulator stayed paused in the debugger. Now: whatever fails after a break-in,
        the emulator is resumed in the end, the STALL line names the exception, and the traceback goes to stderr."""
        import contextlib
        import io
        import types
        from unittest import mock
        space = {'__name__': 'stall'}
        exec(compile(engine_smoke.STALL_PY, 'stall.py', 'exec'), space)
        calls = []
        space['subprocess'] = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout='1234'))
        space['size'] = lambda: 0
        space['tail_from'] = lambda pos: ''
        space['wait_prompt'] = lambda pos, timeout=20, sent=None: '>'       # the break-in answers
        space['state_values'] = lambda: None

        def cmd(text, timeout=20):
            raise RuntimeError('boom')

        def resume():
            calls.append('g')
            space['paused'] = False
        space['cmd'], space['resume'] = cmd, resume
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(sys, 'argv', ['stall.py', '1']):
            space['main']()
        self.assertEqual(calls, ['g'])
        self.assertFalse(space['paused'])
        self.assertTrue(out.getvalue().startswith('STALL unknown: the examination failed after a break-in: RuntimeError: boom'),
                        out.getvalue())
        self.assertIn('RuntimeError: boom', err.getvalue())
        # no break-in at all (no emulator window): nothing to resume, the line says so
        calls.clear()
        space['subprocess'] = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=''))
        space['state_values'] = lambda: (_ for _ in ()).throw(ValueError('bad state'))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), mock.patch.object(sys, 'argv', ['stall.py', '1']):
            space['main']()
        self.assertEqual(calls, [])
        self.assertIn('failed after no break-in: ValueError: bad state', out.getvalue())
        self.assertIn('examine\\ *) S=$(', engine_smoke.PROBE)
        self.assertIn('log "examine ${line#examine }: $S"', engine_smoke.PROBE)
        self.assertIn('unit_labels(f.read(4 << 20)', engine_smoke.STALL_PY)

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

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_engine_error_lines_fail_a_pass(self):
        """ENGINE-REGRESSION-GUARDS-67: a packet overflow, a Message overflow, a dropped or unreadable frame update and any
        Host_Error in the console fail the run (the maintainer's game of 17 November 2026 ended on such lines); a clean
        console passes; --allow-engine-errors (ENGERR=allow) only counts them; an earlier FAIL stays the result."""
        text = engine_smoke.PROBE
        start = text.index('zonefull(){')
        body = text[start:text.index('exit 0; }', start) + len('exit 0; }')]

        def verdict(lines, allow='fail', result='PASS boot'):
            with tempfile.TemporaryDirectory() as tmp:
                awctl = Path(tmp, 'awctl')
                awctl.mkdir()
                (awctl / 'console.log').write_text('Scene ready: seyda, 1089 ms\nSaved Autosave 1 (13037 bytes, '
                                                   'generation 7).\n' + ''.join(l + '\n' for l in lines),
                                                   encoding='utf-8', newline='\n')
                stubs = ('st(){ case "$1" in efrags_bad) echo 0;; screen) echo game;; esac; }\n'
                         'alive(){ return 1; }\nsleep(){ :; }\nlog(){ echo "$*"; }\nFP=999999\nXP=999999\n')
                script = Path(tmp, 'finish.sh')
                script.write_text('R=%s\nFASTMB=32\nENGERR=%s\n%s%s\nfinish "%s"\n'
                                  % (Path(tmp).as_posix(), allow, stubs, body, result), encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60)
                return done.stdout.strip().splitlines()[-1]
        self.assertEqual(verdict([]), 'smoke RESULT PASS boot')
        for bad in ('packet overflow', 'SZ_GetSpace: overflowHost_Error: CL_ParseServerMessage: Illegible server message',
                    'Message overflow caught (3 so far): the entity updates, 1490 bytes; not sent',
                    'Frame update dropped (1 so far): an entity update past the end of the message',
                    'Host_Error: ED_ParseEntity: unclosed render metadata', 'SZ_GetSpace: overflow'):
            got = verdict([bad, bad])
            self.assertTrue(got.startswith('smoke RESULT FAIL 2 engine error lines in the console '
                                           '(ENGINE-REGRESSION-GUARDS-67), the first: '), got)
            self.assertIn(bad[:40], got)
        self.assertEqual(verdict(['packet overflow'] * 5, allow='allow'), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(['packet overflow'], result='FAIL music not reading'),
                         'smoke RESULT FAIL music not reading')
        # an ordinary line that only mentions an overflow in other words is not one of them
        self.assertEqual(verdict(['Explored map: 0 cells and 0 rooms did not fit the save']), 'smoke RESULT PASS boot')
        self.assertIn("'--allow-engine-errors'", Path(engine_smoke.__file__).read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_a_netstat_reading_over_the_ceiling_or_with_updates_not_sent_fails_a_pass(self):
        """ENGINE-REGRESSION-GUARDS-67 (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66): a dbg netstat reading in the console whose
        fullest frame since the map started wanted more than the game's own connection carries, or that counts a frame
        update not sent, fails the run; clean readings pass; ENGERR=allow only logs it; an earlier FAIL stays."""
        text = engine_smoke.PROBE
        start = text.index('zonefull(){')
        body = text[start:text.index('exit 0; }', start) + len('exit 0; }')]

        def reading(where, fullest, dropped):
            return ("Frame update on %s: 212 entities in sight want 6120 bytes, room 8000 (a network packet 1024, the "
                    "game's own connection up to 8192, its buffer 16388); 212 sent in 6120 bytes, 0 wait for the next "
                    "frames\nSince the map started: 812 frames, 4 with updates waiting, 300 over 1024 bytes; the fullest "
                    "wanted %d bytes for 260 entities (room 8000, 9 waited); %d frame updates not sent\n"
                    "  4410 bytes: 120 x vivec/static_0012.mdl\n" % (where, fullest, dropped))

        def verdict(console, allow='fail', result='PASS boot'):
            with tempfile.TemporaryDirectory() as tmp:
                awctl = Path(tmp, 'awctl')
                awctl.mkdir()
                (awctl / 'console.log').write_text('Scene ready: seyda, 1089 ms\n' + console, encoding='utf-8',
                                                   newline='\n')
                stubs = ('st(){ case "$1" in efrags_bad) echo 0;; screen) echo game;; esac; }\n'
                         'alive(){ return 1; }\nsleep(){ :; }\nlog(){ echo "$*"; }\nFP=999999\nXP=999999\n')
                script = Path(tmp, 'finish.sh')
                script.write_text('R=%s\nFASTMB=32\nENGERR=%s\n%s%s\nfinish "%s"\n'
                                  % (Path(tmp).as_posix(), allow, stubs, body, result), encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60)
                return done.stdout.strip().splitlines()[-1]
        self.assertEqual(verdict(''), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(reading('seyda', 3120, 0) + reading('vivec', 8192, 0)), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(reading('seyda', 3120, 0) + reading('vivec', 9420, 0)),
                         'smoke RESULT FAIL dbg netstat in vivec: the fullest frame wanted 9420 bytes against the '
                         'ceiling 8192, 0 frame updates not sent (ENGINE-REGRESSION-GUARDS-67)')
        self.assertEqual(verdict(reading('vivec', 7410, 3)),
                         'smoke RESULT FAIL dbg netstat in vivec: the fullest frame wanted 7410 bytes against the '
                         'ceiling 8192, 3 frame updates not sent (ENGINE-REGRESSION-GUARDS-67)')
        self.assertEqual(verdict(reading('vivec', 9420, 3), allow='allow'), 'smoke RESULT PASS boot')
        self.assertEqual(verdict(reading('vivec', 9420, 3), result='FAIL music not reading'),
                         'smoke RESULT FAIL music not reading')
        # each stop of the plain route takes its reading
        for where in ('netstat_at "Seyda Neen"', 'netstat_at "$(st server)"', 'netstat_at "the wild stop"'):
            self.assertIn(where, text)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_guards_an_autosave_on_every_map_change_and_creatures_outdoors(self):
        """ENGINE-REGRESSION-GUARDS-67: on the plain route (the gate's smoke) every map change must write its autosave
        within AUTOSAVE_WAIT s, the outdoor stops must have creatures alive, and the save status must hold nothing at
        the end; each failure names itself. The game's answers are written into a fake console by a fake rc."""
        text = engine_smoke.PROBE
        helpers = ''.join(line + '\n' for line in text.splitlines()
                          if line.startswith(('clines(){', 'since(){')))
        start = text.index('# GUARDS-BEGIN')
        guards = text[start:text.index('\nif [ "$SAVES" = check ]; then\n', start) + 1]
        self.assertIn('autosaved(){', guards)
        self.assertIn('creatures(){', guards)
        self.assertIn('M=$(clines); rc "dbg tp $TP"', text)                     # every load of the route is marked
        self.assertIn('autosaved "$M" "the load of $(st server) ($r of $REPEAT)"', text)
        self.assertIn('autosaved "$M" "$MAP1 again (before load $r of $REPEAT)"', text)
        self.assertIn('creatures "the wild stop ($(st server))"', text)
        self.assertIn('[ "$h" = nothing ] || finish "FAIL the save status at the end', text)

        def run(console, call, answers='', extra=''):
            with tempfile.TemporaryDirectory() as tmp:
                awctl = Path(tmp, 'awctl')
                awctl.mkdir()
                (awctl / 'console.log').write_text(console, encoding='utf-8', newline='\n')
                Path(tmp, 'answers.txt').write_text(answers, encoding='utf-8', newline='\n')
                stubs = ('K=1\nMAP1=seyda\nTP="-21800 -12300"\nalive(){ return 0; }\nsleep(){ :; }\n'
                         'log(){ echo "LOG $*"; }\nfinish(){ echo "RESULT $1"; exit 0; }\n'
                         'st(){ case "$1" in server) echo vf0877;; esac; }\n'
                         # the fake game: every answer at the first command, or with ROWS=1 one line per command
                         'rc(){ echo "RC $1"; [ -s $R/answers.txt ] || return 0\n'
                         '  if [ "${ROWS:-0}" = 1 ]; then head -n 1 $R/answers.txt >> $R/awctl/console.log\n'
                         '    tail -n +2 $R/answers.txt > $R/answers.next; mv $R/answers.next $R/answers.txt\n'
                         '  else cat $R/answers.txt >> $R/awctl/console.log; : > $R/answers.txt; fi; }\n')
                script = Path(tmp, 'guards.sh')
                script.write_text('R=%s\n%s%s%s%s\n%s\necho RESULT returned\n'
                                  % (Path(tmp).as_posix(), extra, stubs, helpers, guards, call),
                                  encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60)
                return [l for l in done.stdout.splitlines() if l.startswith(('RESULT', 'LOG', 'RC '))]
        loads = 'Scene ready: seyda, 1089 ms\n'
        # an autosave after the mark: the step goes on and says which
        out = run(loads + 'Scene ready: balmora, 900 ms\nSaved Autosave 2 (13037 bytes, generation 8).\n',
                  'autosaved 1 "the load of balmora"', extra='AUTOSAVE_WAIT=2\n')
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG autosave after the load of balmora: Saved Autosave 2 (13037 bytes, generation 8).', out)
        # an autosave only before the mark does not count; the failure names the last save line after it
        out = run('Saved Autosave 1 (12000 bytes, generation 7).\n' + loads +
                  'Save queued: Autosave 2 is written when the running script step ends.\n',
                  'autosaved 2 "the load of balmora"', extra='AUTOSAVE_WAIT=2\n')
        self.assertEqual(out[-1], 'RESULT FAIL no autosave within 2 s after the load of balmora '
                                  '(ENGINE-REGRESSION-GUARDS-67); the last save line: Save queued: Autosave 2 is written '
                                  'when the running script step ends.', out)
        # SAVES=off (a MiniWind, a script, another route): nothing is asked
        out = run(loads, 'autosaved 1 "a load"', extra='SAVES=off\n')
        self.assertEqual(out[-1], 'RESULT returned', out)
        table = ('chim actors table 1 (actors join from the actor table): joins 9, records 120, queued 40, without a model '
                 '0, not an actor 0, queue full 0; levelled 12 (kept picks 3, nothing 0, no model 0; player level 1, seed 7); '
                 'town cells joined 4, home cells joined 2\n')
        alive = 'Creatures on: 4 alive, 0 released now, 0 spawns skipped while off (outdoor creatures; not saved)\n'
        none = 'Creatures on: 0 alive, 0 released now, 0 spawns skipped while off (outdoor creatures; not saved)\n'
        sweep = ('Sweep of vf0877 (the loaded area; containers have no runtime class yet):\n'
                 ' actors: map 3, live 3; corpses: map 0, live 0; 0 without a model, 0 without animation; hidden on '
                 'purpose: 0 disabled by a script, 0 by the opening\nSWEEP RESULT ok failures=0 ms=12 map=vf0877\n')
        out = run(loads, 'creatures "the wild stop"', answers=alive + table + sweep)
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG creatures at the wild stop: 4 alive after 1 s; the actor table: 12 levelled, 0 rolled nothing, '
                      '40 actors queued; dbg sweep actors: map 3, live 3 (ok failures=0)', out)
        # an engine without the sweep's answer: the count still stands
        out = run(loads, 'creatures "the wild stop"', answers=alive + table)
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG creatures at the wild stop: 4 alive after 1 s; the actor table: 12 levelled, 0 rolled nothing, '
                      '40 actors queued; dbg sweep actors: no answer ()', out)
        out = run(loads, 'creatures "the wild stop"', answers=none + table)
        self.assertEqual(out[-1], 'RESULT FAIL no outdoor creature alive at the wild stop within 60 s '
                                  '(ENGINE-REGRESSION-GUARDS-67, OUTDOOR-CREATURES-MISSING-66); the actor table: 12 '
                                  'levelled, 0 rolled nothing, 40 actors queued', out)
        # gate 11306: none alive at the first count, the queued actors join later: the count is asked again
        # (the fake rc answers each call with the next line of the file)
        out = run(loads, 'creatures "Seyda Neen"',
                  answers=table + 'SWEEP RESULT ok failures=0 ms=4 map=seyda\n' + none + none + alive, extra='ROWS=1\n')
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG creatures at Seyda Neen: 4 alive after 11 s; the actor table: 12 levelled, 0 rolled nothing, '
                      '40 actors queued; dbg sweep actors: no answer (ok failures=0)', out)
        self.assertEqual(sum(1 for l in out if l == 'RC chim actors creatures on'), 3, out)
        # a known gap (the form ACTOR-TABLE-SAME-MAP-RELOAD-67 had until its fix: no cell joined again when the preset
        # reloaded the map in play): asked for 10 s, logged, never failing; a count above none says the gap passes now
        out = run(loads, 'creatures "Seyda Neen after the reload" GAP-ONE-67', answers=none + table)
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG known gap GAP-ONE-67 at Seyda Neen after the reload: still no creature alive', out)
        self.assertEqual(sum(1 for l in out if l == 'RC chim actors creatures on'), 2, out)
        out = run(loads, 'creatures "Seyda Neen after the reload" GAP-ONE-67', answers=alive + table)
        self.assertIn('LOG known gap GAP-ONE-67 passes now at Seyda Neen after the reload: check the register', out)
        # Seyda Neen's hard count is the map's first load, before the preset reloads it; the count after the reload is a
        # hard check too since the engine joins a map spawned again under its own name (ACTOR-TABLE-SAME-MAP-RELOAD-67):
        # no known gap left on it
        self.assertLess(text.index('  creatures "Seyda Neen"\n'), text.index('rc "aw_debug_hors 0"'))
        self.assertIn('  creatures "Seyda Neen after the preset\'s reload"\n', text)
        self.assertNotIn('ACTOR-TABLE-SAME-MAP-RELOAD-67\n', text)
        out = run(loads, 'creatures "Seyda Neen after the preset\'s reload"', answers=none + table)
        self.assertTrue(out[-1].startswith('RESULT FAIL no outdoor creature alive at Seyda Neen after the preset\'s '
                                           'reload within 60 s'), out)
        out = run(loads, 'creatures "the wild stop"', answers=none + table, extra='CREATURES=known-gap\n')
        self.assertEqual(out[-1], 'RESULT returned', out)
        # a stop's dbg netstat reading is logged (finish judges it, netover)
        out = run(loads, 'netstat_at "the wild stop"',
                  answers='Since the map started: 90 frames, 0 with updates waiting, 0 over 1024 bytes; the fullest '
                          'wanted 812 bytes for 30 entities (room 8000, 0 waited); 0 frame updates not sent\n')
        self.assertEqual(out[-1], 'RESULT returned', out)
        self.assertIn('LOG netstat at the wild stop: Since the map started: 90 frames, 0 with updates waiting, 0 over '
                      '1024 bytes; the fullest wanted 812 bytes for 30 entities (room 8000, 0 waited); 0 frame updates '
                      'not sent', out)
        self.assertIn("'ENGERR=%s' % ('allow' if args.allow_engine_errors else 'fail')",
                      Path(engine_smoke.__file__).read_text(encoding='utf-8'))

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

    def test_a_session_script_asks_for_its_emulator_lines(self):
        """CHIM-SEYDA-BALMORA-LOAD-HANG-43 (16 November 2026): a session script's "emu KEY=VALUE" lines are extra emulator
        lines like --emu-option, derived by the probe itself when the run brings no emu-options.txt (the session tool
        copies the script and writes probe.sh and stall.py alone), checked in the start-up log without judge.py, and
        refused for a key the smoke sets itself. tests/sessions/load_repeat_hops_det.txt asks for deterministic=1."""
        self.assertEqual(engine_smoke.script_emu_options('# a comment\nemu deterministic=1\ncmd dbg hud on\nemu x = y\n'),
                         ['deterministic=1', 'x=y'])
        self.assertEqual(engine_smoke.script_emu_options('wait 8\n'), [])
        det = Path(engine_smoke.HERE.parent, 'tests', 'sessions', 'load_repeat_hops_det.txt').read_text(encoding='utf-8')
        self.assertEqual(engine_smoke.parse_emu_options(engine_smoke.script_emu_options(det)), [('deterministic', '1')])
        plain = Path(engine_smoke.HERE.parent, 'tests', 'sessions', 'load_repeat_hops.txt').read_text(encoding='utf-8')
        self.assertEqual([l for l in det.splitlines() if not l.startswith('#') and l != 'emu deterministic=1'],
                         [l for l in plain.splitlines() if not l.startswith('#')])      # the same session otherwise
        probe = engine_smoke.PROBE
        self.assertNotIn('@EMU_MANAGED@', probe)
        self.assertNotIn('@EMU_PROOF', probe + engine_smoke.JUDGE_PY)
        self.assertIn(engine_smoke.EMU_PROOF_LINE, engine_smoke.JUDGE_PY)
        self.assertIn('else v=$(emucheck_sh); fi', probe)
        with tempfile.TemporaryDirectory() as tmp:
            engine, roms = self.setup_dirs(tmp)
            script = Path(tmp, 's.txt')
            script.write_text('emu jit_compiler=0\nwait 8\n', encoding='utf-8', newline='\n')
            common = ['--engine', str(engine), '--volume', 'v', '--image-dir', 'i', '--scratch', 's', '--roms',
                      str(roms), '--out', str(Path(tmp, 'o')), '--script', str(script)]
            with unittest.mock.patch.object(engine_smoke, 'docker') as docker:
                code, text = self.run_main(*common)
            self.assertEqual(code, 2)
            self.assertIn('the smoke sets jit_compiler itself', text)
            docker.assert_not_called()
        if not shutil.which('sh'):
            self.skipTest('a POSIX shell is required')
        start = probe.index('if [ ! -s $R/emu-options.txt ] && [ -s $R/script.txt ]')
        block = probe[start:probe.index('\nfi\n', start) + 4]
        fn = probe[probe.index('emucheck_sh(){'):]
        fn = fn[:fn.index('; fi; }\n') + 8]
        for lines, want_options, want_result in (
                ('# twin\nemu deterministic=1\nwait 8\n', 'deterministic = 1\n', None),
                ('emu deterministic = 1\nemu cpu_idle=0\n', 'deterministic = 1\ncpu_idle = 0\n', None),
                ('emu jit_compiler=0\nwait 8\n', None, 'names a key the smoke sets itself: jit_compiler'),
                ('emu Bad Line\n', None, 'malformed'),
                ('wait 8\n', None, None)):
            with tempfile.TemporaryDirectory() as tmp:
                r = Path(tmp)
                (r / 'logs').mkdir()
                (r / 'script.txt').write_text(lines, encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', '-c', 'R=%s\n%s' % (r.as_posix(), block)], capture_output=True, text=True,
                                      timeout=30)
                self.assertEqual(done.returncode, 0, done.stderr)
                if want_options is None:
                    self.assertFalse((r / 'emu-options.txt').exists(), lines)
                else:
                    self.assertEqual((r / 'emu-options.txt').read_text(encoding='utf-8'), want_options)
                steps = (r / 'logs' / 'steps.log').read_text(encoding='utf-8') if (r / 'logs' / 'steps.log').exists() else ''
                if want_result:
                    self.assertIn('smoke RESULT FAIL', steps)
                    self.assertIn(want_result, steps)
                    self.assertTrue((r / 'finished').exists())
                else:
                    self.assertEqual(steps, '')
            # a run that brought its own emu-options.txt keeps it: the script's lines are not added twice
            with tempfile.TemporaryDirectory() as tmp:
                r = Path(tmp)
                (r / 'logs').mkdir()
                (r / 'script.txt').write_text('emu deterministic=1\n', encoding='utf-8', newline='\n')
                (r / 'emu-options.txt').write_text('cpu_idle = 0\n', encoding='utf-8', newline='\n')
                subprocess.run(['sh', '-c', 'R=%s\n%s' % (r.as_posix(), block)], capture_output=True, text=True, timeout=30)
                self.assertEqual((r / 'emu-options.txt').read_text(encoding='utf-8'), 'cpu_idle = 0\n')
        # the probe's own check of the taken options, for a run without judge.py
        for options, log, want in (
                ('deterministic = 1\n', 'x\n%s\n' % engine_smoke.EMU_PROOF_LINE, 'EMUOPT ok deterministic=1 taken (emulator log)'),
                ('deterministic = 1\n', 'nothing\n', 'EMUOPT missing deterministic=1 (not in the emulator log)'),
                ('cpu_idle = 0\n', 'cpu_idle = 0\n', 'EMUOPT ok cpu_idle=0 taken (emulator log)'),
                ('cpu_idle = 0\ndeterministic = 1\n', 'cpu_idle = 1\n', 'EMUOPT missing cpu_idle=0 deterministic=1 (not in the emulator log)')):
            with tempfile.TemporaryDirectory() as tmp:
                r = Path(tmp)
                (r / 'logs').mkdir()
                (r / 'emu-options.txt').write_text(options, encoding='utf-8', newline='\n')
                (r / 'logs' / 'fsuae.log').write_text(log, encoding='utf-8', newline='\n')
                done = subprocess.run(['sh', '-c', 'R=%s\n%s\nemucheck_sh' % (r.as_posix(), fn)], capture_output=True,
                                      text=True, timeout=30)
                self.assertEqual(done.stdout.strip(), want, done.stderr)

    def test_warp_is_never_an_option_and_marks_its_result(self):
        """The maintainer's rule (17 November 2026): warp is off for every performance and bench test. No extra option
        and no script line can switch FS-UAE's warp on, so a smoke is never a warp run by accident; a session runner
        asks for it with WARP=1, which writes the config's last line, and the run's result line then says that its
        times are no verdict."""
        for bad in ('warp_mode=1', 'uae_warp=true', 'uae_warp_limit=500'):
            with self.assertRaises(ValueError, msg=bad):
                engine_smoke.parse_emu_options([bad])
        probe = engine_smoke.PROBE
        self.assertNotIn('@WARP_MARK@', probe)
        self.assertIn('log "smoke RESULT $1${WM:-}"', probe)
        if not shutil.which('sh'):
            self.skipTest('a POSIX shell is required')
        # a script's own emu line naming warp is refused before the emulator starts
        start = probe.index('if [ ! -s $R/emu-options.txt ] && [ -s $R/script.txt ]')
        block = probe[start:probe.index('\nfi\n', start) + 4]
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / 'logs').mkdir()
            (r / 'script.txt').write_text('emu warp_mode=1\nwait 8\n', encoding='utf-8', newline='\n')
            done = subprocess.run(['sh', '-c', 'R=%s\n%s' % (r.as_posix(), block)], capture_output=True, text=True,
                                  timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)
            steps = (r / 'logs' / 'steps.log').read_text(encoding='utf-8')
            self.assertIn('smoke RESULT FAIL', steps)
            self.assertIn('names a key the smoke sets itself: warp_mode', steps)
            self.assertFalse((r / 'emu-options.txt').exists())
        # WARP=1: the warp line comes after the extra options and the mark is set; without it, neither
        line = next(l for l in probe.splitlines() if l.startswith('WM=; if [ "${WARP:-0}" = 1 ]'))
        # WARPLIMIT=N (digits) adds FS-UAE's warp limit after the warp line, only with WARP=1 (EMU-WARP-STARVES-GAME-CPU-67)
        for warp, limit, want_mark, want_lines in (
                ('1', None, engine_smoke.WARP_MARK, 'warp_mode = 1\n'),
                ('1', '100', engine_smoke.WARP_MARK, 'warp_mode = 1\nuae_warp_limit = 100\n'),
                ('1', '10x', engine_smoke.WARP_MARK, 'warp_mode = 1\n'),
                ('1', '', engine_smoke.WARP_MARK, 'warp_mode = 1\n'),
                ('0', '100', '', ''), (None, '100', '', ''), (None, None, '', '')):
            with tempfile.TemporaryDirectory() as tmp:
                r = Path(tmp)
                (r / 'smoke.fs-uae').write_text('jit_compiler = 1\n', encoding='utf-8', newline='\n')
                (r / 'emu-options.txt').write_text('cpu_idle = 0\n', encoding='utf-8', newline='\n')
                env = {'PATH': '/usr/bin:/bin'}
                if warp is not None:
                    env['WARP'] = warp
                if limit is not None:
                    env['WARPLIMIT'] = limit
                done = subprocess.run(['sh', '-c', 'R=%s\n[ -s $R/emu-options.txt ] && cat $R/emu-options.txt >> '
                                       '$R/smoke.fs-uae\n%s\nprintf "%%s" "$WM"' % (r.as_posix(), line)],
                                      capture_output=True, text=True, timeout=30, env=env)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(done.stdout, want_mark, (warp, limit))
                self.assertEqual((r / 'smoke.fs-uae').read_text(encoding='utf-8'),
                                 'jit_compiler = 1\ncpu_idle = 0\n' + want_lines, (warp, limit))
        # the readers of the result line still see PASS and FAIL with the mark at its end
        self.assertTrue(engine_smoke.WARP_MARK.startswith(' [warp run'))

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


class WalkerStepTests(unittest.TestCase):
    """JOURNEY-WALK-DIALOGUE-DESYNC-66: the script steps that wait for the game and stop at the first wrong turn
    (walkto, waitfor, boxes, mark / saw, topic, face, aimed), run in a POSIX shell against a fake game: a console log
    and a state file that change as the fake clock (sleep) moves."""

    STUBS = ('K=1\nN=0\nlog(){ echo "log $*"; }\nalive(){ return 0; }\nshot(){ echo "shot $1"; }\n'
             'finish(){ echo "finish $1"; exit 0; }\nkey(){ echo "key $1"; [ "$1" = Return ] && : > $R/nobox; }\n'
             'xdo(){ echo "xdo $1"; }\nrc(){ echo "rc $1"; }\n'
             'st(){ case "$1" in screen) if [ -e $R/box ] && [ ! -e $R/nobox ]; then echo messagebox; else cat $R/screen 2>/dev/null || echo game; fi;; '
             'local) echo "10 20 30";; map) echo maps/census.bsp;; *) echo 1;; esac; }\n')

    def walker(self):
        text = engine_smoke.PROBE
        return text[text.index('# WALKER-STEPS-BEGIN'):text.index('# WALKER-STEPS-END')]

    def run_sh(self, tmp, body, sleep='sleep(){ N=$((N+1)); }\n', console=''):
        Path(tmp, 'awctl').mkdir(exist_ok=True)
        Path(tmp, 'awctl', 'console.log').write_text(console, encoding='utf-8', newline='\n')
        script = 'R=%s\n%s%s%s\n%s\necho done\n' % (Path(tmp).as_posix(), self.STUBS, sleep, self.walker(), body)
        done = subprocess.run(['sh', '-c', script], capture_output=True, text=True, timeout=60)
        return done.stdout.splitlines()

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_walkto_waits_for_the_engine_and_answers_a_box_on_the_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'box').write_text('')
            sleep = ('sleep(){ N=$((N+1)); [ $N = 3 ] && echo "Walk to: reached." >> $R/awctl/console.log; :; }\n')
            lines = self.run_sh(tmp, 'walk_to 47 100 20', sleep, console='Walk to: reached.\n')
        # an older "reached" line before the step does not count; the box is answered; the new line ends the step
        self.assertIn('rc aw_view walk 47 100', lines)
        self.assertIn('key Return', lines)
        self.assertIn('log walkto 47 100: a message box on the way, Enter', lines)
        self.assertIn('log walkto 47 100: reached after 3 s at local 10 20 30', lines)
        self.assertEqual(lines[-1], 'done')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_walkto_not_reached_stops_the_run_with_the_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = self.run_sh(tmp, 'walk_to 47 100 5')
        self.assertIn('rc aw_view walk off', lines)
        self.assertIn('shot walkto-stuck-47_100', lines)
        self.assertEqual(lines[-1], 'finish FAIL walkto 47 100: not reached in 5 s; the player stands at local 10 20 30 '
                                    '(screen game, map maps/census.bsp)')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_waitfor_reads_the_state_until_it_holds_the_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'screen').write_text('game\n')
            sleep = 'sleep(){ N=$((N+1)); [ $N = 2 ] && echo dialogue > $R/screen; :; }\n'
            lines = self.run_sh(tmp, 'wait_for screen 10 dialogue', sleep)
            self.assertEqual(lines[-2:], ['log waitfor screen dialogue: after 2 s', 'done'])
            Path(tmp, 'screen').write_text('persuasion\n')
            lines = self.run_sh(tmp, 'wait_for screen 3 dialogue')
        self.assertEqual(lines[-1], "finish FAIL waitfor screen dialogue: read 'persuasion' after 3 s (map maps/census.bsp, "
                                    'screen persuasion, local 10 20 30)')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_saw_looks_only_after_the_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = 'M0=$(clines)\nsaw 3 source ref: 172859'
            lines = self.run_sh(tmp, body, console='source ref: 172859\n')
            self.assertTrue(lines[-1].startswith("finish FAIL saw: no console line 'source ref: 172859' within 3 s"),
                            lines)
            sleep = 'sleep(){ N=$((N+1)); echo "source ref: 172859" >> $R/awctl/console.log; }\n'
            lines = self.run_sh(tmp, body, sleep, console='source ref: 1\n')
        self.assertEqual(lines[-2:], ["log saw 'source ref: 172859' after 1 s", 'done'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_aimed_takes_the_crosshair_pick_or_the_use_keys_focus(self):
        with tempfile.TemporaryDirectory() as tmp:
            sleep = 'sleep(){ N=$((N+1)); echo "source ref: 113889 / cell -2,-9" >> $R/awctl/console.log; }\n'
            lines = self.run_sh(tmp, 'aimed 113889', sleep)
            self.assertEqual(lines[:2], ['rc aw_placed aim', 'rc aw_inspect'])
            self.assertEqual(lines[-2:], ["log aimed 113889: the crosshair's pick (aw_inspect; the focus row none not in "
                                          "the report), try 1", 'done'])
            # the v0.0.66-dev2 papers: the pick hit the desk under the flat scroll, the game's focus is on the scroll
            focus = ('aw_placed aim: reach 48, 30 rows (room), eye 20 -30 79, aimed row 5\n'
                     '  4 B 406345 sc_paper plain: at 52 -44 65, edict 0 drawn 3 disabled 0, dist 35.0\n'
                     '  5 B 172859 chargen statssheet: at 37 -46 65, edict 40 drawn 0 disabled 0, dist 23.0\n'
                     'source ref: 119515\n')
            sleep = "sleep(){ N=$((N+1)); [ $N = 2 ] && printf '%s' \"$FOCUS\" >> $R/awctl/console.log; :; }\n"
            lines = self.run_sh(tmp, 'FOCUS=\'%s\'\naimed 172859' % focus, sleep)
            self.assertEqual(lines[-2:], ["log aimed 172859: the use key's focus row 5 (aw_placed aim), try 1", 'done'])
            # the pick lands on the papers only after a nudge of the aim (the third try: 1.5 degrees less pitch)
            sleep = ('sleep(){ N=$((N+1)); [ -n "$(grep -c "aw_aim" $R/turns 2>/dev/null)" ] && '
                     '[ "$(grep -c aw_aim $R/turns)" -ge 2 ] && echo "source ref: 172859" >> $R/awctl/console.log; :; }\n'
                     'rc(){ echo "rc $1"; echo "$1" >> $R/turns; }\n')
            lines = self.run_sh(tmp, 'st(){ case "$1" in angles) echo "28.7 317.8";; local) echo "20 -30 79";; *) echo 1;; esac; }\n'
                                     'aimed 172859', sleep)
            self.assertIn('rc aw_aim 317.8 30.2', lines)
            self.assertIn('rc aw_aim 317.8 27.2', lines)
            self.assertEqual(lines[-2:], ["log aimed 172859: the crosshair's pick (aw_inspect; the focus row none not in "
                                          "the report), try 3", 'done'])
            # the v0.0.66-dev2 crab meat: the pick names it, but the focus row the report prints is the plate under it,
            # and the use key takes the focus: never accepted
            plate = ("sleep(){ N=$((N+1)); printf 'aw_placed aim: reach 48, 154 rows (room), eye 141 192 79, aimed row 43\\n"
                     "  43 I 119580 Silverware Plate: at 145 176 63, edict 0 drawn 0 disabled 0, dist 23.6\\n"
                     "source ref: 454283\\n' >> $R/awctl/console.log; }\n")
            lines = self.run_sh(tmp, 'aimed 454283 2', plate)
            self.assertFalse([l for l in lines if l.startswith('log aimed')], lines)
            self.assertEqual(lines[-1], "finish FAIL aimed 454283: neither the use key's focus (aw_placed aim, aimed row 43) "
                                        "nor the crosshair's pick (aw_inspect: 454283) is on it in 13 tries around pitch 1 "
                                        "yaw 0 (local 10 20 30)")
            # aimed at the desk itself: neither names the reference in any of the thirteen tries
            sleep = ("sleep(){ N=$((N+1)); printf 'aw_placed aim: reach 48, 154 rows (room), eye 20 -30 79, aimed row 92\\n"
                     "source ref: 119515\\n' >> $R/awctl/console.log; }\n")
            lines = self.run_sh(tmp, 'aimed 172860 2', sleep)
        self.assertEqual(lines[-2], 'shot aimed-missing-172860')
        self.assertEqual(lines[-1], "finish FAIL aimed 172860: neither the use key's focus (aw_placed aim, aimed row 92) "
                                    "nor the crosshair's pick (aw_inspect: 119515) is on it in 13 tries around pitch 1 yaw 0 "
                                    "(local 10 20 30)")

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_aimed_refuses_a_door_whose_use_goes_to_an_actor(self):
        # JOURNEY-DOOR-USE-GOES-TO-ACTOR-66 (the v0.0.66-dev6 journey): the focus row is the census street door, the
        # Guard killed a step before lies in front of it, and the game says the use key goes to the actor: E would
        # search the body, not open the door. The focus row is not accepted; the step fails naming the actor.
        with tempfile.TemporaryDirectory() as tmp:
            corpse = ("sleep(){ N=$((N+1)); printf 'aw_placed aim: reach 48, 381 rows (outdoors), eye 266 36 70, aimed row 164\\n"
                      "  164 D 113833 Seyda Neen, Census and Excise Office: at 247 11 65, edict 0 drawn 0 disabled 0, dist 32.1\\n"
                      "aw_placed aim: use goes to the actor; actor Guard box 0.0..45.0, item -1.0, plant -1.0\\n"
                      "source ref: unavailable\\n' >> $R/awctl/console.log; }\n")
            lines = self.run_sh(tmp, 'aimed 113833 2', corpse)
        self.assertIn('log aimed 113833: the focus row 164 is on it, but the use key goes to the actor Guard standing in '
                      'front of it, try 1', lines)
        self.assertFalse([l for l in lines if l.startswith("log aimed 113833: the use key's focus row")], lines)
        self.assertEqual(lines[-2], 'shot aimed-missing-113833')
        self.assertEqual(lines[-1], 'finish FAIL aimed 113833: the use key goes to the actor Guard standing in front of it '
                                    '(the focus row 164 is on it) in 13 tries around pitch 1 yaw 0 (local 10 20 30); the '
                                    'use key would search or talk, not use it')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_aimed_accepts_the_focus_row_when_the_use_goes_to_no_actor(self):
        # the same door with nobody in front of it (the v0.0.66-dev4 journey's line): accepted at the first try
        with tempfile.TemporaryDirectory() as tmp:
            clear = ("sleep(){ N=$((N+1)); printf 'aw_placed aim: reach 48, 381 rows (outdoors), eye 266 36 70, aimed row 164\\n"
                     "  164 D 113833 Seyda Neen, Census and Excise Office: at 247 11 65, edict 0 drawn 0 disabled 0, dist 32.1\\n"
                     "aw_placed aim: use goes to no actor; actor none box -1.0..-1.0, item -1.0, plant -1.0\\n' >> $R/awctl/console.log; }\n")
            lines = self.run_sh(tmp, 'aimed 113833 2', clear)
        self.assertEqual(lines[-2:], ["log aimed 113833: the use key's focus row 164 (aw_placed aim), try 1", 'done'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_aimed_answers_a_message_box_first(self):
        # the v0.0.66-dev4 journey: the release's "Press J" notice was still up when E was pressed at the door; the box
        # took the key as its button and the journey waited 45 s for a load it never asked for
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'box').write_text('')
            sleep = 'sleep(){ N=$((N+1)); echo "source ref: 113833" >> $R/awctl/console.log; }\n'
            lines = self.run_sh(tmp, 'aimed 113833', sleep)
        self.assertEqual(lines[:2], ['key Return', 'log aimed 113833: a message box was up, Enter'])
        self.assertEqual(lines[-2:], ["log aimed 113833: the crosshair's pick (aw_inspect; the focus row none not in the "
                                      "report), try 1", 'done'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_aim_is_computed_from_the_eye_as_it_is_now(self):
        # JOURNEY-AIM-RETRY-YAW-66, the v0.0.66-dev5 journey: the turn to door 113833 (242.6 10.3 61) was made from local
        # 247 8 70 (aw_aim 152.4 61.1), the eye then read 266 36 70 and the thirteen tries ran round yaw 45.0 while the
        # door lies at yaw 227.7 from there (the v0.0.66-dev4 journey's "face ... from local 266 36 70: aw_aim 227.7 14.5")
        with tempfile.TemporaryDirectory() as tmp:
            sleep = ('sleep(){ N=$((N+1)); grep -q "aw_aim 227.7" $R/turns 2>/dev/null && '
                     'echo "source ref: 113833 / cell -2,-9" >> $R/awctl/console.log; :; }\n'
                     'rc(){ echo "rc $1"; echo "$1" >> $R/turns; }\n')
            body = ('st(){ case "$1" in local) cat $R/loc;; angles) echo "0.0 45.0";; *) echo 1;; esac; }\n'
                    'printf "247 8 70" > $R/loc\nface 242.6 10.3 61\nprintf "266 36 70" > $R/loc\naimed 113833')
            lines = self.run_sh(tmp, body, sleep)
        aims = [l for l in lines if l.startswith('rc aw_aim')]
        self.assertEqual(aims, ['rc aw_aim 152.4 61.1', 'rc aw_aim 227.7 14.5'], lines)
        self.assertIn('log aimed 113833: the eye moved from 247 8 70 to 266 36 70 since the turn, aiming again: '
                      'aw_aim 227.7 14.5', lines)
        self.assertEqual(lines[-2:], ["log aimed 113833: the crosshair's pick (aw_inspect; the focus row none not in the "
                                      "report), try 1", 'done'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_the_tries_are_centred_on_the_aim_from_the_current_eye(self):
        # the door is only found 1.5 degrees to one side of the exact aim: every try is a turn round 227.7 14.5 (from the
        # eye read at that moment), never round the view the player happened to have (yaw 45.0)
        with tempfile.TemporaryDirectory() as tmp:
            sleep = ('sleep(){ N=$((N+1)); grep -q "aw_aim 227.7 16.0" $R/turns 2>/dev/null && '
                     'echo "source ref: 113833" >> $R/awctl/console.log; :; }\n'
                     'rc(){ echo "rc $1"; echo "$1" >> $R/turns; }\n')
            body = ('st(){ case "$1" in local) echo "266 36 70";; angles) echo "0.0 45.0";; *) echo 1;; esac; }\n'
                    'face 242.6 10.3 61\naimed 113833')
            lines = self.run_sh(tmp, body, sleep)
        aims = [l for l in lines if l.startswith('rc aw_aim')]
        self.assertEqual(aims, ['rc aw_aim 227.7 14.5', 'rc aw_aim 227.7 16.0'], lines)
        self.assertEqual(lines[-1], 'done')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_a_face_is_forgotten_after_its_aimed_step(self):
        # a later aimed without a face of its own takes the view as it is, as before
        with tempfile.TemporaryDirectory() as tmp:
            sleep = 'sleep(){ N=$((N+1)); echo "source ref: 7" >> $R/awctl/console.log; }\n'
            lines = self.run_sh(tmp, 'face 20 30 20\naimed 7\naimed 7', sleep)
        self.assertEqual([l for l in lines if l.startswith('rc aw_aim')], ['rc aw_aim 45.0 35.3'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_lookat_turns_to_the_nearest_placed_items_until_one_is_the_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            # aw_placed.c look_command: the plate first (nearest), then the crab meat on it
            sleep = ('rc(){ echo "rc $1"; case "$1" in "aw_placed look 0") r=119580;; "aw_placed look 1") r=454283;; '
                     '*) r=;; esac; [ -n "$r" ] && echo "aw_placed look: reference $r at 37 units." >> $R/awctl/console.log; :; }\n'
                     'sleep(){ N=$((N+1)); }\n')
            lines = self.run_sh(tmp, 'look_at 454283', sleep)
            self.assertEqual([l for l in lines if l.startswith('rc ')], ['rc aw_placed look 0', 'rc aw_placed look 1'])
            self.assertEqual(lines[-2:], ['log lookat 454283: the nearest drawn placed item number 1', 'done'])
            # the list runs out: the game says how many there are, and the step stops naming what it saw
            sleep = ('rc(){ echo "rc $1"; case "$1" in "aw_placed look 0") echo "aw_placed look: reference 119580 at 37 units." '
                     '>> $R/awctl/console.log;; *) echo "aw_placed look: 1 drawn placed items near here." >> $R/awctl/console.log;; '
                     'esac; }\nsleep(){ N=$((N+1)); }\n')
            lines = self.run_sh(tmp, 'look_at 454283', sleep)
        self.assertEqual(lines[-2], 'shot lookat-missing-454283')
        self.assertEqual(lines[-1], 'finish FAIL lookat 454283: not among the nearest drawn placed items (saw: 119580; '
                                    'local 10 20 30)')

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_boxes_answers_every_box_showing(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'box').write_text('')
            lines = self.run_sh(tmp, 'boxes')
        self.assertEqual([l for l in lines if l.startswith(('key', 'log'))], ['key Return', 'log boxes: Enter on message box 1'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_topic_types_the_name_into_the_open_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = self.run_sh(tmp, 'topic duties')
            self.assertEqual(lines[0], 'shot topic-no-window')
            self.assertTrue(lines[-1].startswith('finish FAIL topic duties: the dialogue window is not open (screen game'))
            Path(tmp, 'screen').write_text('dialogue\n')
            lines = self.run_sh(tmp, 'topic Caius Cosades')
        # the Find box ignores spaces (aw_listbox_rules.c fold): the name is typed without them, then Enter
        self.assertEqual(lines[:3], ['xdo type --delay 60 CaiusCosades', 'key Return', 'log topic Caius Cosades (typed CaiusCosades, Enter)'])
        # then the search box is cleared, one BackSpace per typed letter (a name not offered stays in the box)
        self.assertEqual(lines[3:-1], ['key BackSpace'] * len('CaiusCosades'))

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_face_turns_the_view_to_a_point_from_the_eye(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = self.run_sh(tmp, 'face 20 30 20\nface 0 20 30')
        aims = [l for l in lines if l.startswith('rc ')]
        # from the eye at 10 20 30: up and to the right, down 35.3 degrees; due west (yaw 180), level
        self.assertEqual(aims, ['rc aw_aim 45.0 35.3', 'rc aw_aim 180.0 0.0'])

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_face_steps_back_from_a_point_too_close_or_too_steep(self):
        # JOURNEY-AIM-RETRY-YAW-66: a target straight above the eye cannot be aimed at (pitch is clamped to 70 up): the
        # player first steps back 12 units on the floor plane (here straight along -x, the eye being right under it),
        # the engine says it arrived, and the turn is computed from where the eye stands then
        with tempfile.TemporaryDirectory() as tmp:
            sleep = 'sleep(){ N=$((N+1)); [ $N = 1 ] && echo "Walk to: reached." >> $R/awctl/console.log; :; }\n'
            lines = self.run_sh(tmp, 'face 10 20 90', sleep)
        self.assertIn('rc aw_view walk -2.0 20.0', lines)
        self.assertEqual([l for l in lines if l.startswith('rc aw_aim')], ['rc aw_aim 0.0 -70.0'])
        self.assertTrue(any('stepping back to -2.0 20.0' in l for l in lines), lines)
        # a target 1 unit away on the floor plane and 4 below the eye is too close as well
        with tempfile.TemporaryDirectory() as tmp:
            lines = self.run_sh(tmp, 'face 11 20 26', sleep)
        self.assertIn('rc aw_view walk -2.0 20.0', lines)

    @unittest.skipUnless(shutil.which('sh'), 'a POSIX shell is required')
    def test_the_script_loop_dispatches_the_walker_steps(self):
        text = engine_smoke.PROBE
        start = text.index('if [ -s $R/script.txt ]; then')
        block = text[start:text.index('\nfi\n', start) + 4]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'script.txt').write_text('walkto 1 2 3\nwaitfor screen 5 dialogue box\nboxes\nmark\nsaw 4 a b\n'
                                              'topic my trade\nface 1 2 3\naimed 42 7\n', encoding='utf-8', newline='\n')
            stubs = ('R=%s\nlog(){ :; }\nrc(){ :; }\nalive(){ return 0; }\nclines(){ echo 7; }\n'
                     'walk_to(){ echo "walk_to $*"; }\nwait_for(){ echo "wait_for $*"; }\nboxes(){ echo boxes; }\n'
                     'saw(){ echo "saw $* after $M0"; }\ntopic(){ echo "topic $*"; }\nface(){ echo "face $*"; }\n'
                     'aimed(){ echo "aimed $*"; }\n'
                     'st(){ case "$1" in screen) echo game;; signon) echo 4;; *) echo 1;; esac; }\n'
                     'finish(){ echo "finish $1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            done = subprocess.run(['sh', '-c', stubs + block], capture_output=True, text=True, timeout=30, input='')
        self.assertEqual(done.stdout.splitlines()[:7],
                         ['walk_to 1 2 3', 'wait_for screen 5 dialogue box', 'boxes', 'saw 4 a b after 7',
                          'topic my trade', 'face 1 2 3', 'aimed 42 7'], done.stderr)
