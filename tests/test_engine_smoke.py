# SPDX-License-Identifier: GPL-3.0-only
"""tools/engine_smoke.py (with its emulator-side PROBE script): the FS-UAE boot + map-load smoke (CHIM-DEV3-MAPLOAD-CRASH-36).

The emulator run itself needs Docker, an image and the owner's Kickstart, so it runs in the gate (step "smoke"), not
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
                     'shot(){ cat > /dev/null; echo "shot $1"; }\nst(){ echo 0; }\nalive(){ return 0; }\n'
                     'finish(){ echo "finish $1"; exit 0; }\nt0=0\n' % Path(tmp).as_posix())
            script = Path(tmp, 'run.sh')
            script.write_text(stubs + block, encoding='utf-8', newline='\n')
            done = subprocess.run(['sh', str(script)], capture_output=True, text=True, timeout=60, input='')
        lines = done.stdout.splitlines()
        self.assertEqual([l for l in lines if l.startswith(('rc ', 'shot ', 'play ', 'xdo '))],
                         ['rc noclip', 'shot a', 'play 1', 'xdo mousedown 1 mouseup 1', 'rc aw_view 1 2 3 0 0'])
        self.assertTrue(lines[-1].startswith('finish PASS script'), done.stdout + done.stderr)
