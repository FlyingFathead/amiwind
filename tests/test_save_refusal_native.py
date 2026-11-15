"""SAVE-EXPORT-FAILURE-ACCEPTED-65: the real save path with every export forced to fail in turn, and with rows the
world change list refused while an export reported success (tests/aga_save_refusal_test.c): each save is refused,
the previous generation stays byte for byte, nothing else is written, the line names the part; then a save works."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == 'nt', 'Native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'C compiler required')
class SaveRefusalTests(unittest.TestCase):
    def test_every_export_failure_refuses_the_save(self):
        src = ROOT / 'engine/aga/src'
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / 'saves/p00000002').mkdir(parents=True)
            binary = work / 'save-refusal'
            built = subprocess.run(['cc', '-std=gnu99', '-O1', '-g', '-ffunction-sections', '-fdata-sections',
                                    '-Wl,--gc-sections', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                                    '-I' + str(src), str(ROOT / 'tests/aga_save_refusal_test.c'),
                                    *(str(src / n) for n in ('aw_character.c', 'aw_state.c', 'aw_save_codec.c',
                                                             'aw_ledger.c', 'aw_jhist.c')),
                                    '-lm', '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(binary), str(work)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = run.stdout.splitlines()
        # twelve refusals, each naming its part
        self.assertEqual(len([line for line in lines if line.startswith('refused ')]), 12, lines)
        for part in ("the scripts' state", 'the quest stages', 'a row of the world change list',
                     "the references' identities", "the actors' changes", "the objects' changes", 'the actor block',
                     'the filled soul gems', 'the dated journal', 'the generation number'):
            self.assertTrue(any(part in line for line in lines), part)
        # a part named on the short block try, then fitting the grown block, does not name a later refusal
        grown = [line for line in lines if line.startswith('refused 10:')]
        self.assertEqual(len(grown), 1, lines)   # the fixture's ACTORS_GROWN_ROW case
        self.assertIn('a row of the world change list', grown[0])
        self.assertNotIn('soul gems', grown[0])
        self.assertIn('Every export refused in turn: no generation written, the previous kept, the part named; then saved; '
                      'a save inside a script step waits for the settled frame.', lines)

    def test_a_save_inside_a_script_step_is_queued_for_the_settled_frame(self):
        """SAVE-INSIDE-SCRIPT-STEP-66: the host marks its script tick and the dialogue result run as busy; AW_SaveWrite
        queues the slot and returns 2 there; AW_SaveTick writes the queued save first when not busy and no load waits;
        the save menu and the recorder say so."""
        save = (ROOT / 'engine/aga/src/aw_save.c').read_text(encoding='utf-8')
        self.assertIn('if(busy()){\n        queued_slot=slot;\n        Con_Printf("Save queued: %s is written when the running '
                      'script step ends.\\n",label);return 2;\n    }', save)
        self.assertIn('if(AW_RecorderActive())return;\n    /* SAVE-INSIDE-SCRIPT-STEP-66', save)   # no save during a recording
        self.assertIn('if(queued_slot>=0 && !busy() && !loading){', save)
        self.assertIn('if(busy()){Con_Printf("Recorder: the game is inside a script step; start the recording from a settled '
                      'frame.\\n");return NULL;}', save)
        self.assertIn('scene_id()<0 || loading || busy() ||', save)
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('script_depth++;AW_MwvmTick(dt,player);script_depth--;', host)
        self.assertIn('script_depth++;ran=AW_MwvmRunDialogue(chosen,(uint32_t)reference,row_speaker);script_depth--;', host)
        self.assertIn('aw_save_busy=save_busy;', host)
        menu = (ROOT / 'engine/aga/src/aw_savemenu.c').read_text(encoding='utf-8')
        self.assertEqual(menu.count('if(ok==2){strcpy(notice,QUEUED);active=0;}') +
                         menu.count('if(!load_mode && ok==2){strcpy(notice,QUEUED);active=0;}'), 2)

    def test_every_part_of_the_actor_block_names_itself(self):
        """aw_mwhost.c actors_export: every export in the block goes through ACTOR_PART with its name, and the block's
        writer clears the name once a grown block fits (SAVE-EXPORT-FAILURE-ACCEPTED-65)."""
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        body = host[host.index('static int actors_export(unsigned char *out,int capacity){'):]
        body = body[:body.index('#undef ACTOR_PART')]
        for export in ('AW_EffectsExport', 'AW_SoldExport', 'AW_MadeExport(', 'AW_GemsExport(', 'AW_DialReactionsExport',
                       'AW_RevealedExport', 'AW_DialHeardExport', 'forced_export', 'AW_WeatherScriptSave',
                       'AW_CrimeActorsExport', 'forced_run_export', 'were_export', 'AW_MoverExport',
                       'AW_MadeExportMore', 'AW_GemsExportMore', 'aw_mwscript_packages_export(out'):
            self.assertIn('ACTOR_PART(' + export, body, export)
        self.assertNotIn('if(k<0)return -1;', body)
        self.assertIn('AW_SaveRefusePart("the dead counts")', body)
        self.assertIn('AW_SaveRefusePart("the factions\' standing")', body)
        self.assertIn('AW_SaveRefusePart("the known topics")', body)
        save = (ROOT / 'engine/aga/src/aw_save.c').read_text(encoding='utf-8')
        self.assertIn('            block=grown;\n        }\n        refused_part=NULL;', save)


if __name__ == '__main__':
    unittest.main()
