# SPDX-License-Identifier: GPL-3.0-only
"""The gameplay recorder's contracts in the engine source (GAME-RECORDER-61, docs/GAME_RECORDER.md); no compiler.

A replay retraces a recording only when the recorder sees every input at the same point of the frame as the live
game, the frame's length and the random rolls follow the game's frames, and nothing writes during play. These checks
keep those hooks where they are.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def source(name):
    text = (SRC / name).read_text(encoding='utf-8')
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def body(text, name):
    start = re.search(r'\b' + name + r'\s*\([^;{}]*\)\s*\{', text).end()
    depth = 1
    for end in range(start, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if not depth:
            return text[start:end]
    raise AssertionError('unclosed function: ' + name)


def order(text, *calls):
    """Positions of CALLS in TEXT, each after the one before."""
    at, found = 0, []
    for call in calls:
        i = text.find(call, at)
        if i < 0:
            raise AssertionError('%s not found after %s' % (call, found[-1] if found else 'the start'))
        found.append(call)
        at = i + len(call)


class GameRecorderSource(unittest.TestCase):
    def test_host_frame_order(self):
        frame = body(source('host.c'), '_Host_Frame')
        # the per-wall-clock roll only while the recorder is off; the frame's length right after it is decided; the
        # replay's keys and lines after the live input and the remote poll, before the command buffer runs
        self.assertRegex(frame, r'if\s*\(\s*!\s*AW_RecorderActive\s*\(\s*\)\s*\)\s*rand\s*\(\s*\)')
        order(frame, 'Host_FilterTime', 'AW_RecorderFrame', 'Sys_SendKeyEvents', 'IN_Commands', 'AW_RemotePoll',
              'AW_RecorderInput', 'Cbuf_Execute', 'CL_SendCmd', 'Host_ServerFrame')

    def test_keys_seen_first(self):
        event = body(source('keys.c'), 'Key_Event')
        first = event.find('AW_RecorderKey')
        self.assertGreater(first, 0)
        for later in ('keydown[key]', 'AW_MovieKey', 'Cbuf_AddText', 'K_ALTM'):
            self.assertLess(first, event.find(later), later)

    def test_move_after_mouse(self):
        send = body(source('cl_main.c'), 'CL_SendCmd')
        order(send, 'CL_BaseMove', 'IN_Move', 'AW_RecorderMove', 'CL_SendMove')

    def test_remote_lines_kept_before_they_run(self):
        run = body(source('aw_remote.c'), 'run_commands')
        order(run, 'AW_RecorderLine', 'Cbuf_AddText')

    def test_no_autosave_while_running(self):
        tick = body(source('aw_save.c'), 'AW_SaveTick')
        self.assertRegex(tick, r'if\s*\([^;]*AW_RecorderActive\s*\(\s*\)\s*\)\s*return')
        self.assertLess(tick.find('AW_RecorderActive'), tick.find('AW_SaveWrite'))

    def test_save_write_and_recorder_share_one_encoder(self):
        save = source('aw_save.c')
        self.assertIn('encode_world(label,1,', body(save, 'AW_SaveWrite'))
        self.assertIn('encode_world("Recording",0,', body(save, 'AW_SaveEncodeNow'))
        self.assertIn('load_decoded(&candidate)', body(save, 'AW_SaveRead'))
        self.assertIn('load_decoded(&candidate)', body(save, 'AW_SaveLoadBytes'))

    def test_no_file_access_in_the_frame_hooks(self):
        rec = source('aw_recorder.c')
        for hook in ('AW_RecorderFrame', 'AW_RecorderInput', 'AW_RecorderKey', 'AW_RecorderLine', 'AW_RecorderMove',
                     'AW_RecorderDraw', 'commit', 'add_check', 'compare', 'read_frame'):
            self.assertNotRegex(body(rec, hook), r'\bf(open|write|read)\s*\(', hook)
        # the one write is at the stop, the one read at the start of a playback
        self.assertRegex(body(rec, 'write_file'), r'fopen\s*\(\s*path\s*,\s*"wb"\s*\)')
        self.assertRegex(body(rec, 'play_start'), r'fopen\s*\(\s*path\s*,\s*"rb"\s*\)')

    def test_version_line_words(self):
        rec = source('aw_recorder.c')
        self.assertIn('" (RECORDING)"', rec)
        self.assertIn('" (PLAYBACK)"', rec)
        self.assertIn('"AmiWind v" AMIWIND_VERSION "%s"', body(rec, 'AW_RecorderDraw'))
        self.assertIn('AW_RecorderSuffix()', body(source('aw_hud.c'), 'Sbar_Draw'))
        # the console's notify lines start below it
        self.assertIn('AW_RecorderLineShown', body(source('console.c'), 'Con_DrawNotify'))

    def test_ctrl_r_taken_in_every_key_destination(self):
        # GAME-RECORDER-HOTKEY-DIALOGUE-61: Ctrl+R while armed or running is the recorder's in a window too (it typed into
        # the dialogue's Find field and the recording carried on); a recording starts only in play
        key = body(source('aw_recorder.c'), 'AW_RecorderKey')
        taken = re.search(r"if\s*\(\s*down\s*&&\s*\(\s*key\s*==\s*'r'\s*\|\|\s*key\s*==\s*'R'\s*\)\s*&&\s*real_ctrl\s*\)", key)
        self.assertTrue(taken, 'Ctrl+R must not depend on key_dest')
        branch = key[taken.end():key.find('return 1;', taken.end())]
        self.assertRegex(branch, r'if\s*\(\s*key_dest\s*==\s*key_game\s*\)\s*record_start\s*\(\s*\)')
        self.assertIn('record_stop("Ctrl+R")', branch)
        self.assertIn('play_end()', branch)
        self.assertLess(key.find('if(!armed && mode==IDLE)return 0;'), taken.start())   # never taken while not armed
        # its line is drawn over the windows, so the state and the saved file show with the dialogue open
        update = body(source('screen.c'), 'SCR_UpdateScreen')
        self.assertLess(update.find('M_Draw ()'), update.find('AW_RecorderDraw()'))

    def test_every_random_stream_follows_the_recording(self):
        # GAME-RECORDER-FIGHT-SEED-61: a fight recorded replayed 1 of 8 checkpoints (its seed came from the replaying
        # game's own count of fights); every stream the game logic draws from is set from the recording's seed
        rec = source('aw_recorder.c')
        streams = body(rec, 'seed_streams')
        for call in ('AW_CombatRecorderSeed(', 'AW_MwvmSeed(', 'aw_levelled_seed='):
            self.assertIn(call, streams)
        frame = body(rec, 'AW_RecorderFrame')
        order(frame, 'seed_streams()', 'mode==RECORDING', 'frame_seed(frames)', 'read_frame()', 'frame_seed(frames)', 'frames++')
        self.assertNotRegex(frame, r'\bsrand\s*\(\s*seed\s*\)')
        self.assertRegex(body(rec, 'frame_seed'), r'srand\s*\(')
        self.assertIn('AW_CombatRecorderSeed(0)', body(rec, 'release'))
        combat = source('aw_combat.c')
        begin = body(combat, 'begin_encounter')
        self.assertLess(begin.find('recorder_seed'), begin.find('encounters+1'))
        self.assertIn('AW_CombatSeed(&rng', body(combat, 'AW_CombatRecorderSeed'))
        self.assertRegex(body(source('aw_mwvm.c'), 'AW_MwvmSeed'), r'vm\.rng\s*=')

    def test_catalogue_route_and_makefile(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertRegex(catalogue, r'(?m)^PLAYTESTING\|recorder\|aw_recorder\|')
        self.assertIn('aw_recorder.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        self.assertIn('Cmd_AddCommand("aw_recorder"', source('aw_recorder.c'))


if __name__ == '__main__':
    unittest.main()
