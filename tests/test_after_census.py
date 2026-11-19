# SPDX-License-Identifier: GPL-3.0-only
"""The bare 'dbg aw hors' (DBG-HORS-AFTER-CENSUS-67): the script AW_AfterCensus read from the game's own chargen scripts
(tools/mwscript/aftercensus.py, config/after-census.json) on small stand-ins of those scripts, and the engine's route:
New Game's own reset, Hors, the script started after the new game's own start, the arrival at the census exit door;
'dbg aw hors 0' unchanged."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
from mwscript import aftercensus as A  # noqa: E402
from mwscript.gamedata import Script  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'

SCRIPTS = {
    'CharGenClassNPC': 'begin CharGenClassNPC\nshort state\nfloat timer\nif ( state == 0 )\n"CharGen Boat"->Disable\n'
                       'DisablePlayerControls\nset state to 10\nelseif ( state == 10 )\nEnableClassMenu\n'
                       'set state to 17\nelseif ( state == 17 )\nset timer to 0\nEnableStatsMenu\n'
                       'EnablePlayerControls\nStartScript RaceCheck\nset state to -1\nendif\nend',
    'CharGenStatsSheet': 'begin CharGenStatsSheet\nshort state\nshort OnPCAdd\nif ( OnPCAdd == 1 )\n'
                         'EnableInventoryMenu\nset state to 20\nendif\nend',
    'CharGenDoorGuardTalker': 'begin CharGenDoorGuardTalker\nshort done\n"CharGen Door Hall"->Unlock\n'
                              '"CharGen Door Hall"->PlaySound3D, "Open Lock"\nenableplayerfighting\nset done to 1\nend',
    'CharGenDagger': 'begin CharGenDagger\nshort done\nshort OnPCEquip\nset done to 1\nset done to 2\nend',
    'CharGen_ring_keley': 'begin CharGen_ring_keley\nshort state\nEnableMagicMenu\nset state to 30\nend',
    'CharGenDialogueMessage': 'begin CharGenDialogueMessage\nshort done\nshort state\nset done to 1\nend',
    'CharGenDoorExitCaptain': 'begin CharGenDoorExitCaptain\nshort done\nset done to 1\nset CharGenState to -1\n'
                              'enablemapmenu ; safety\nend',
}
CONFIG = {'scripts': list(SCRIPTS), 'local_values': {}, 'speaker': 'chargen captain', 'skip_functions': ['showmap'],
          'window_openers': ['enableclassmenu']}


class Data:
    """The parts of mwscript.gamedata.GameData the generator reads."""

    def __init__(self):
        self.scripts = {k.casefold(): Script(k, 'Morrowind.esm', v, len(v), len(v), {}, []) for k, v in SCRIPTS.items()}
        self.globals = {'chargenstate': ('s', 0, 'CharGenState')}
        self.bases = {'chargen class': ('NPC_', 'chargenclassnpc'), 'chargen statssheet': ('BOOK', 'chargenstatssheet'),
                      'chargen door guard': ('NPC_', 'chargendoorguardtalker'),
                      'chargen dagger': ('WEAP', 'chargendagger'), 'ring_keley': ('CLOT', 'chargen_ring_keley'),
                      'chargen captain': ('NPC_', 'chargendialoguemessage'),
                      'chargen exit door': ('DOOR', 'chargendoorexitcaptain')}
        self.references = [{'id': i, 'reference': n, 'script': self.bases[i.casefold()][1]} for n, i in enumerate(
            ['chargen class', 'chargen statssheet', 'chargen door guard', 'chargen dagger', 'chargen captain',
             'CharGen Exit Door'], 1)]
        self.holder_refs = [{'reference': 172851, 'id': 'barrel_01_ring', 'type': 'CONT'}]
        self.holdings = {'barrel_01_ring': ['ring_keley']}
        self.results = {
            ('chargen captain', ';if pc does not have stats sheet'): None,
            ('chargen captain', 'player->removeitem "chargen statssheet", 1\r\nset state to -1'): None,
            ('chargen captain', 'Journal, "A1_1_FindSpymaster", 1\r\nplayer->AddItem, "bk_a1_1_caiuspackage", 1\r\n'
                                'player->Additem, "Gold_001", 87\r\naddtopic "Caius Cosades"'): None,
            ('chargen captain', 'ShowMap Balmora'): None,
            ('fargoth', 'player->AddItem "something" 1'): None}


class Generated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.report = A.generate(Data(), CONFIG)
        cls.lines = cls.text.splitlines()

    def test_framed_and_run_once(self):
        self.assertEqual(self.lines[0], 'begin AW_AfterCensus')
        self.assertEqual(self.lines[-2:], ['StopScript AW_AfterCensus', 'end AW_AfterCensus'])

    def test_the_release_value_of_chargenstate(self):
        self.assertIn('set CharGenState to -1', self.lines)

    def test_locals_end_where_the_scripts_end(self):
        for line in ('set "chargen class".state to -1', 'set "chargen door guard".done to 1',
                     'set "chargen captain".done to 1', 'set "CharGen Exit Door".done to 1'):
            self.assertIn(line, self.lines)
        self.assertFalse(any('timer' in l or 'OnPCAdd' in l for l in self.lines))      # ends at 0; the engine's own
        self.assertFalse(any('"chargen dagger".' in l or 'ring_keley".' in l for l in self.lines))   # items: with them

    def test_lasting_switches_on_and_the_windows_left_out(self):
        for word in ('EnableStatsMenu', 'EnablePlayerControls', 'EnableInventoryMenu', 'enableplayerfighting',
                     'EnableMagicMenu', 'enablemapmenu'):
            self.assertIn(word, self.lines)
        self.assertNotIn('EnableClassMenu', self.lines)
        self.assertNotIn('DisablePlayerControls', self.lines)                      # the later Enable is the last word
        self.assertEqual(self.report['switches_left_off'], [])

    def test_doors_objects_and_script_starts(self):
        self.assertIn('"CharGen Door Hall"->Unlock', self.lines)
        self.assertIn('"CharGen Boat"->Disable', self.lines)
        self.assertIn('StartScript RaceCheck', self.lines)
        self.assertFalse(any('PlaySound3D' in l for l in self.lines))

    def test_the_dagger_taken_the_papers_handed_in_the_ring_by_its_container(self):
        self.assertIn('player->AddItem "chargen dagger" 1', self.lines)
        self.assertIn('"chargen dagger"->Disable', self.lines)
        self.assertIn('"chargen statssheet"->Disable', self.lines)
        self.assertFalse(any('AddItem "chargen statssheet"' in l or 'removeitem "chargen statssheet"' in l
                             for l in self.lines))
        self.assertFalse(any('ring_keley' in l for l in self.lines))
        self.assertIn('ring_keley', json.dumps(self.report['taken_elsewhere']))

    def test_the_speakers_results_run_as_he_runs_them(self):
        for line in ('set "chargen captain".state to -1', 'Journal, "A1_1_FindSpymaster", 1',
                     'player->AddItem, "bk_a1_1_caiuspackage", 1', 'player->Additem, "Gold_001", 87',
                     'addtopic "Caius Cosades"'):
            self.assertIn(line, self.lines)
        self.assertFalse(any('ShowMap' in l or 'something' in l for l in self.lines))

    def test_missing_game_data_stops_the_build(self):
        with self.assertRaises(ValueError):
            A.generate(Data(), dict(CONFIG, scripts=CONFIG['scripts'] + ['CharGenNoSuch']))
        with self.assertRaises(ValueError):
            A.generate(Data(), dict(CONFIG, local_values={'CharGenDagger.done': 'set done to 9'}))
        with self.assertRaises(ValueError):
            A.generate(Data(), dict(CONFIG, speaker='nobody'))

    def test_the_shipped_config_names_the_path(self):
        cfg = A.load_config()
        self.assertEqual(cfg['scripts'][-1], 'CharGenDoorExitCaptain')
        self.assertIn('CharGen_ring_keley', cfg['scripts'])
        self.assertEqual(cfg['speaker'], 'chargen captain')

    def test_inject_adds_it_once_and_leaves_data_without_the_opening(self):
        data = Data()
        self.assertIsNotNone(A.inject(data, CONFIG))
        self.assertIn('aw_aftercensus', data.scripts)
        empty = Data()
        empty.scripts = {}
        self.assertIsNone(A.inject(empty, CONFIG))


class Engine(unittest.TestCase):
    def test_the_bare_command_resets_presets_starts_and_walks_out(self):
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        census = scene[scene.index('static void hors_census(void)'):scene.index('static void hors_command(void)')]
        order = [census.index(s) for s in ('aw_game_reset(1)', 'AW_CharacterHorsCensus()', 'AW_MwscriptAfterCensus()',
                                           'read_links_for("census")', 'CENSUS_EXIT_DOOR', 'load_scene(&links[i],1)')]
        self.assertEqual(order, sorted(order))
        command = scene[scene.index('static void hors_command(void)'):]
        command = command[:command.index('\n}\n')]
        self.assertIn('if(Cmd_Argc()==1 && sv.active && svs.clients){hors_census();return;}', command)
        self.assertIn('hors_after_start=Cmd_Argc()==1;', command)                      # from the main menu too
        self.assertIn('AW_CharacterHors()', command)                                    # 'dbg aw hors 0' as before
        self.assertIn('r.arrival[2]=64;r.yaw=90;', command)
        # HORS-IN-PLAY-NO-NEW-GAME-RESET-67: 'dbg aw hors 0' in play takes New Game's reset before its preset
        in_play = command[command.index('if(sv.active && svs.clients && aw_game_reset)aw_game_reset(1);'):]
        self.assertLess(in_play.index('aw_game_reset(1)'), in_play.index('AW_CharacterHors()'))
        self.assertIn('if(hors_after_start){hors_after_start=0;Cbuf_AddText("aw_debug_hors\\n");}', scene)
        self.assertIn('#define CENSUS_EXIT_DOOR 119659u', scene)

    def test_the_script_starts_after_the_new_games_own_start(self):
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('static void new_game_hook(void){new_game_pending=1;new_game_started=0;after_census_row=-1;}', host)
        tick = host[host.index('void AW_MwscriptTick(float dt)'):]
        self.assertLess(tick.index('new_game_controls();'), tick.index('after_census_start();'))
        start = host[host.index('static void after_census_start(void)'):]
        self.assertIn('if(after_census_row<0 || new_game_pending)return;', start)

    def test_the_preset_leaves_the_duties_to_the_script(self):
        text = (SRC / 'aw_character.c').read_text(encoding='utf-8')
        self.assertIn('AW_CourtyardTakeRing();if(duties)AW_CaptainDuties();', text)
        self.assertIn('int AW_CharacterHorsCensus(void){return preset("nord","barbarian","charioteer",0,"Hors",0);}',
                      text)
        self.assertIn('return preset(race,clas,birth,female,name,1);', text)


if __name__ == '__main__':
    unittest.main()
