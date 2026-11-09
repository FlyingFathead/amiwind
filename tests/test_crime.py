# SPDX-License-Identifier: GPL-3.0-only
"""Crime (STEAL-WITNESSED-NO-CRIME-61, CRIME-59) and the dialogue's item notices (DIALOGUE-ITEM-NOTICE-MISSING-61): the
rules in host C, the builder's settings lines in the engine's order, and the source contracts that wire every take
path (a placed item, a container's content, an owned plant) to the crime rules and a script's AddItem / RemoveItem
on the player to the conversation."""
import json
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(name, start):
    text = code(name)
    at = text.index(start)
    depth, i = 0, text.index('{', at)
    for j in range(i, len(text)):
        depth += {'{': 1, '}': -1}.get(text[j], 0)
        if depth == 0:
            return text[at:j + 1]
    raise AssertionError('unbalanced ' + start)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class CrimeNativeTests(unittest.TestCase):
    def test_rules_awareness_bounty_and_the_witness_reaction(self):
        native.NativeSourceTests().compile_run('aga_crime_rules_test.c', [SRC / 'aw_crime_rules.c'], cflags=UBSAN)


class CrimeBuilderTests(unittest.TestCase):
    def test_the_crime_settings_are_the_engines_names_in_its_order(self):
        import prepare_combat
        names = re.findall(r'"(\w+)"', code('aw_crime_rules.c').split('names[AW_CRIME_SETTING_COUNT]={', 1)[1]
                           .split('};', 1)[0])
        self.assertEqual(tuple(names), prepare_combat.CRIME_SETTINGS)
        self.assertEqual(int(re.search(r'AW_CRIME_SETTING_COUNT (\d+)', code('aw_crime.h')).group(1)), len(names))
        self.assertIn('sCrimeMessage', prepare_combat.TEXT_SETTINGS)
        self.assertIn("lines += [f'crime {name} {settings[name]:.6g}' for name in CRIME_SETTINGS]",
                      (ROOT / 'tools/prepare_combat.py').read_text(encoding='utf-8'))

    def test_the_dialogue_notices_are_written_with_the_levelling_lines(self):
        import prepare_levelup
        for name in ('sNotifyMessage60', 'sNotifyMessage61', 'sNotifyMessage62', 'sNotifyMessage63'):
            self.assertIn(name, prepare_levelup.TEXTS)
            self.assertIn('"%s"' % name, code('aw_mwhost.c'))


class CrimeSourceTests(unittest.TestCase):
    def test_every_take_path_asks_the_crime_rules(self):
        inv = code('aw_inventory.c')
        self.assertIn('if(stolen)theft(owner,faction,item.id,1,item.value);', body('aw_inventory.c', 'static int take_row(focus_row_t *row)'))
        take = body('aw_inventory.c', 'int AW_ContainerTake(')
        self.assertIn('if(container_owner(reference,owner,&faction))theft(owner,faction,item.id,moved,item.value);', take)
        self.assertIn('if(aw_inventory_theft)aw_inventory_theft(owner,faction,id,count,value);', inv)
        self.assertIn('aw_harvest_theft(AW_HarvestOwner(&harvest,i),', code('aw_harvest_runtime.c'))
        init = body('aw_crime.c', 'void AW_CrimeInit(void)')
        self.assertIn('aw_inventory_theft=inventory_theft;aw_harvest_theft=harvest_theft;', init)
        self.assertIn('aw_crime_witness=crime_witness;aw_crime_attack=crime_attack;aw_crime_thief=crime_thief;',
                      body('aw_mwhost.c', 'void AW_MwscriptInit(void)'))
        self.assertIn('AW_CrimeInit();', body('aw_mwhost.c', 'void AW_MwscriptInit(void)'))
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_pcstanding.c aw_crime_rules.c aw_crime.c', make)

    def test_commit_crime_sees_reports_and_reacts_as_openmw(self):
        commit = body('aw_crime.c', 'static int commit(')
        report = body('aw_crime.c', 'static void report(')
        self.assertIn('return crime(AW_CRIME_THEFT,NULL,owner,faction,value,0,0);', code('aw_crime.c'))
        # the maintainer's rule: only at the moment of a crime, never per frame: the take paths are the only callers
        callers = [p.name for p in SRC.glob('*.c') if re.search(r'\bAW_CrimeTheft\s*\(', code(p.name))]
        self.assertEqual(sorted(callers), ['aw_crime.c'])
        self.assertIn('seen=commit(kind,victim,owner,faction,arg,victim_aware,dry);', body('aw_crime.c', 'static int crime('))
        # AngleVectors writes forward, right and up: a NULL one stopped the game at the first witness (in game, s1-s3)
        self.assertNotRegex(code('aw_crime.c'), r'AngleVectors\([^)]*NULL')
        # the witnesses: the alarm radius (or the victim anywhere), canReportCrime, the line of sight, the roll; the
        # assault's victim knows and a murder is heard (no trace for those)
        self.assertIn('if(dist>radius && !is_victim)continue;', commit)
        self.assertIn('if(!aw_crime_witness(e,&w) || !w.can_report)continue;', commit)
        self.assertIn('if((los=sees(p,e))!=0){roll=roll100();noticed=(float)roll>=aim;}', commit)
        self.assertIn('heard=AW_CrimeWitness(kind,is_victim,victim_aware,0);', commit)
        self.assertIn('AW_GlutSay(e,AW_GLUT_THIEF,0)', commit)
        # nobody saw it: no report, no bounty; an unseen assault on a guard is reported by the guard
        self.assertIn('if(seen){crimes++;report(kind,victim?victim:owner_npc,owner,faction,arg,radius);return seen;}', commit)
        self.assertNotIn('AW_StandingModCrime', commit)
        # reported only when an NPC in the radius has Alarm 100 (each says Intruder for trespass); the game's line
        self.assertIn('if(!aw_crime_witness(e,&w) || !w.can_report || !AW_CRIME_REPORTS(w.alarm))continue;', report)
        self.assertIn('AW_GlutSay(e,AW_GLUT_INTRUDER,0)', report)
        self.assertLess(report.index('if(reporter){'), report.index('AW_StandingModCrime(last.bounty);'))
        self.assertIn('last.bounty=AW_CrimeBounty(&settings,kind,arg);', report)
        self.assertIn('if(crime_text[0])AW_MsgBoxShow(crime_text,NULL,0);', report)
        # every NPC in the radius reacts by the pure rule: the disposition, the pursuit, the attack, the crime's number
        self.assertIn('AW_CrimeReact(&settings,kind,arg,&in,', report)
        self.assertIn('if(out.attack && aw_crime_attack && aw_crime_attack(e,out.fight))', report)
        # the guard means to arrest even where it cannot walk (the census office's guards): the talk comes when near
        self.assertIn('if(row && !row->pursue){if(aw_crime_pursue)aw_crime_pursue(e,1);row->pursue=1;'
                      'row->walk_edict=NUM_FOR_EDICT(e);}', report)
        self.assertIn('AW_StandingSetExpelled(f,1);', report)

    def test_assault_and_murder_come_from_the_combat_layer(self):
        combat = code('aw_combat.c')
        strike = body('aw_combat.c', 'static void player_strike(')
        # actorAttacked before the fight starts, then the strike as before; actorKilled at the killing blow
        self.assertLess(strike.index('if(aw_combat_assault)aw_combat_assault(t);'), strike.index('AW_CombatEngage(t,&sheet,NULL)'))
        # the murder after the whole strike: its witnesses may take a fallen fighter's slot (the victim's)
        self.assertIn('killed=s->e;', strike)
        self.assertLess(strike.index('aw_combat_strike_enchant(p,t);'),
                        strike.index('if(killed && aw_combat_killed)aw_combat_killed(killed);'))
        spell = body('aw_combat.c', 'int AW_CombatSpellHit(')
        self.assertIn('if(aw_combat_assault)aw_combat_assault(e);', spell)
        self.assertIn('if(harmful && aw_combat_killed)aw_combat_killed(s->e);', spell)
        self.assertIn('void (*aw_combat_assault)(struct edict_s *victim);', combat)
        init = body('aw_crime.c', 'void AW_CrimeInit(void)')
        self.assertIn('aw_combat_assault=combat_assault;aw_combat_killed=combat_killed;', init)
        self.assertIn('aw_rest_bed_crime=bed_crime;', init)
        # canCommitCrimeAgainst before the assault; the murder only by the rule (a crime's number or a fair target)
        self.assertIn('if(!AW_CrimeCanCommit(victim) || !full())return 0;', body('aw_crime.c', 'int AW_CrimeAssault('))
        self.assertIn('if(!AW_CrimeIsMurder(1,1,can_commit,row?row->crime_id:-1))return 0;', body('aw_crime.c', 'int AW_CrimeKilled('))
        # dbg kill crime: the pick, canCommit before the kill, actorKilled after it
        act = body('aw_companion.c', 'static void pick_act(')
        self.assertLess(act.index('can=AW_CrimeCanCommit(e);'), act.index('AW_CombatTestEngage(e,1)'))
        self.assertIn('AW_CrimeKilled(e,can)', act)
        self.assertIn('" actors killpick crime\\n"', code('aw_console.c'))

    def test_the_scripts_and_the_dialogue_reach_the_crime_rules(self):
        host = body('aw_mwhost.c', 'static int host_call(')
        for line in ('case AWF_ONMURDER:', 'AW_CrimePayFine(function==AWF_PAYFINE);', 'case AWF_GOTOJAIL:AW_CrimeGoToJail();',
                     'case AWF_GETPCINJAIL:result->i=AW_CrimeInJail();'):
            self.assertIn(line, host)
        from mwscript.functions import FUNCTION_NUMBERS, HOST, HOST_EFFECTS
        for name in ('onmurder', 'payfine', 'payfinethief', 'gotojail', 'getpcinjail'):
            self.assertIn(name, HOST)
            self.assertIn('#define AWF_%s %d' % (name.upper(), FUNCTION_NUMBERS[name]), code('aw_mwcode.h'))
        self.assertTrue({'payfine', 'payfinethief', 'gotojail'} <= HOST_EFFECTS)
        live = body('aw_mwhost.c', 'static int live_function(')
        self.assertIn('if(fn==49){', live)                       # Alarmed: the speaker's mark
        self.assertIn('AW_CrimeAlarmed(', live)
        facts = body('aw_mwhost.c', 'void AW_MwscriptDispositionFacts(')
        self.assertIn('AW_CrimeDialogueGlobals(crime_set_global,', facts)
        self.assertIn('f->base+=AW_CrimeDispositionOf(reference);', facts)
        self.assertIn('AW_CrimeTick(dt);', body('aw_mwhost.c', 'void AW_MwscriptTick(float dt)'))
        self.assertIn('aw_crime_pursue=pursue;', body('aw_ambient.c', 'void AW_AmbientInit(void)'))
        # the guards: pursuit checked four times a second, the sight once a second, only past the threshold
        tick = body('aw_crime.c', 'void AW_CrimeTick(float dt)')
        self.assertIn('pursuers();', tick)
        self.assertIn('if(!act || realtime-sight_at<1)return;', body('aw_crime.c', 'static void guards_on_sight('))
        self.assertIn('if(!any || realtime-pursue_at<.25)return;', body('aw_crime.c', 'static void pursuers('))
        # an owned bed: the refusal only when the trespass was seen (sleepInBed)
        self.assertIn('if(!aw_rest_bed_crime || aw_rest_bed_crime(bed_reference,', code('aw_wait.c'))

    def test_the_arrest_talk_opens_for_an_opening_scene_guard(self):
        # STEAL-WITNESSED-NO-CRIME-61 (v0.0.62-dev1: the census office's guards were alarmed but never came): AiPursue
        # opens the conversation whatever the talk prompt's rules; the census office's guards are opening-scene roles
        # the general rule refuses, so the arrest opens the window itself, and a guard that cannot walk still means
        # to arrest (it talks when the player is near)
        greet = body('aw_mwhost.c', 'static int crime_greet(edict_t *e){')
        self.assertLess(greet.index('if(force_greeting(e))return 1;'), greet.index('AW_DialWindowOpen(e,"",0)'))
        self.assertIn('if(!a || (a->flags&AWL_DEAD) || f || AW_DialWindowActive())return 0;', greet)
        self.assertIn('aw_crime_greet=crime_greet;', body('aw_mwhost.c', 'void AW_MwscriptInit(void)'))
        self.assertIn('else{if(aw_crime_pursue)aw_crime_pursue(e,1);row->pursue=1;row->walk_edict=NUM_FOR_EDICT(e);}',
                      body('aw_crime.c', 'static void guards_on_sight('))
        # the dialogue's Alarmed is the speaker's mark (the guard's "What are you doing!" greeting needs it)
        self.assertIn('AW_CrimeAlarmed(', body('aw_mwhost.c', 'static int live_function('))

    def test_a_conversations_answers_start_their_fight(self):
        # GUARD-RESIST-ARREST-NOTHING-61, DIALOGUE-AGGRO-62: an answer runs with the speaker's reference but no entity:
        # its StartCombat finds the speaker by its reference; a SetFight 100 with no StartCombat (a robber's refused
        # demand) takes effect when the talk closes, with the Fight the actor has now
        self.assertIn('if(!e)e=speaker_edict(ref);', body('aw_mwhost.c', 'static aw_actor_t *actor_of('))
        closed = body('aw_dialwin.c', 'static void closed(void)')
        self.assertIn('AW_MwscriptSpeakerAggro(e,dispo);', closed)
        aggro = body('aw_mwhost.c', 'int AW_MwscriptSpeakerAggro(')
        self.assertIn('if(AW_CombatFighter(e))return 0;', aggro)
        self.assertLess(aggro.index('to_fighter(a,&sheet);'), aggro.index('AW_ActorStat(a,AWA_FIGHT)'))

    def test_every_answer_that_starts_a_fight_has_its_path(self):
        # DIALOGUE-AGGRO-62, world-wide: every dialogue answer of the three masters that starts or changes a fight
        # (StartCombat, SetFight, ModFight, on the speaker or on a reference, before or after Goodbye), as the
        # scripting tracker measured them with the builder's compiler, goes down a path the engine carries out. The
        # one kind not carried out is a fight between two actors (COMBAT-ACTOR-VS-ACTOR-62: the combat layer fights
        # the player only), held to its measured five answers: any other answer off a handled path fails here.
        import mwscript_features as mf
        from mwscript import dialogue_combat as dc
        doc = json.loads((ROOT / 'docs' / 'mwscript-features.json').read_text(encoding='utf-8'))
        mf.use(doc)
        paths = mf.combat_paths(doc['dialogue_results'])
        self.assertEqual(sum(paths.values()), 293, paths)
        self.assertEqual({k: paths.get(k, 0) for k in dc.HANDLED},
                         {'speaker-startcombat': 124, 'other-startcombat': 9, 'speaker-fight': 148, 'other-fight': 7})
        unhandled = {k: v for k, v in paths.items() if k not in dc.HANDLED}
        self.assertEqual(unhandled, {'startcombat-actor': 5}, 'an answer that starts a fight is not carried out')
        # the engine side of each path
        self.assertIn('if(!e)e=speaker_edict(ref);', body('aw_mwhost.c', 'static aw_actor_t *actor_of('))
        self.assertIn('AW_MwscriptSpeakerAggro(e,dispo);', body('aw_dialwin.c', 'static void closed(void)'))
        self.assertIn('aw_ambient_fight_now=ambient_fight_now;', body('aw_mwhost.c', 'void AW_MwscriptInit(void)'))
        aggro = body('aw_ambient.c', 'static void aggro(slot_t *s) {')
        self.assertIn('(now=aw_ambient_fight_now(s->e))>=0', aggro)
        self.assertIn('if(now>=0)sheet.fight=', aggro)

    def test_the_fight_calls_of_an_answer(self):
        from mwscript import dialogue_combat as dc
        self.assertEqual(dc.calls('Goodbye\nStartCombat Player'), [['startcombat', 'speaker', 'player']])
        self.assertEqual(dc.calls('"some guard"->StartCombat player ; a comment'),
                         [['startcombat', 'other', 'player']])
        self.assertEqual(dc.calls('SetFight 100\nModFight, -20\nsomeone->setfight 30'),
                         [['setfight', 'speaker', '100'], ['modfight', 'speaker', '-20'], ['setfight', 'other', '30']])
        self.assertEqual(dc.calls('; StartCombat Player\nJournal X 10'), [])
        self.assertEqual(dc.path(dc.calls('StartCombat Player\nGoodbye')), 'speaker-startcombat')
        self.assertEqual(dc.path(dc.calls('a->StartCombat Player')), 'other-startcombat')
        self.assertEqual(dc.path(dc.calls('SetFight 100\nGoodbye')), 'speaker-fight')
        self.assertEqual(dc.path(dc.calls('a->SetFight 100')), 'other-fight')
        self.assertEqual(dc.path(dc.calls('a->StartCombat "b"')), 'startcombat-actor')
        self.assertEqual(dc.path(dc.calls('StartCombat Player'), runs=False), 'not-run')
        self.assertIsNone(dc.path(dc.calls('Goodbye')))

    def test_the_crime_marks_and_pursuers_are_saved(self):
        # CRIME-SAVE-PURSUERS-62: the AWCR block after AWFS in the actors block (pack and unpack tested by number in
        # tests/aga_crime_rules_test.c); a save without it starts with none; a loaded pursuer walks again
        export = body('aw_mwhost.c', 'static int actors_export(')
        self.assertLess(export.index('forced_export('), export.index('AW_CrimeActorsExport('))
        self.assertLess(export.index('AW_CrimeActorsExport('), export.index('aw_mwscript_packages_export('))
        imp = body('aw_mwhost.c', 'static void actors_import(')
        self.assertIn('AW_CrimeActorsReset();', imp)
        self.assertLess(imp.index('"AWFS"'), imp.index('"AWCR"'))
        self.assertLess(imp.index('"AWCR"'), imp.index('"AWPK"'))
        self.assertIn('if(r->walk_edict!=NUM_FOR_EDICT(e)){r->walk_edict=NUM_FOR_EDICT(e);'
                      'if(aw_crime_pursue)aw_crime_pursue(e,1);}', body('aw_crime.c', 'static void pursuers(void){'))

    def test_the_release_from_jail_shows_every_changed_skill(self):
        # CRIME-RELEASE-LINE-CUT-62: each changed skill on a line of its own (OpenMW's jail screen), and the message box
        # draws every line it has room for (aw_msgbox_rules.c AW_MsgBoxLinesShown), not the first three
        serve = body('aw_crime.c', 'static void serve(void){')
        self.assertIn("jail.text[o++]='\\n';", serve)
        # the lines are counted and capped in box_frame, the frame the drawing and the pointer's hit test share
        # (MSGBOX-NO-CURSOR-62); the drawing shows as many as box_frame says
        frame = body('aw_msgbox.c', 'static int box_frame(int frame[4],int *shown) {')
        draw = body('aw_msgbox.c', 'void AW_MsgBoxDraw(void) {')
        self.assertIn('n=AW_MsgBoxLinesShown(n,rows,(int)vid.height,lh);', frame)
        self.assertIn('AW_UILine(rest,w-12-16,line,sizeof(line))', frame)
        self.assertIn('lines=box_frame(f,&shown);', draw)
        self.assertIn('AW_UICenteredLinesUpTo(f[0]+6,f[1]+4,f[2]-12,lines+8,box.text,shown);', draw)
        self.assertIn('AW_UICenteredLinesUpTo(x,y,w,h,text,3);', code('aw_ui.c'))

    def test_prison_markers_and_their_evidence_chests(self):
        import world_doors
        markers = [{'reference': 474482, 'position': [-11264.5, -71680.25, 64.0], 'yaw': 272.383, 'chest': 1234,
                    'prison': 'Seyda Neen, Census and Excise Office'}]
        text = world_doors.prison_markers_text(markers)
        self.assertEqual(text.splitlines(), ['AWPM1', '474482 -11264.500 -71680.250 64.000 272.383 1234|Seyda Neen, '
                                             'Census and Excise Office'])
        with self.assertRaises(ValueError):
            world_doors.prison_markers_text([dict(markers[0], prison='x' * 200)])
        self.assertIn('write_prison_markers(args,boot/\'id1\',out)', (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8'))
        self.assertIn('COM_FOpenFile("prison-markers.txt",&f)', code('aw_crime.c'))

    def test_prison_markers_read_from_a_master(self):
        import math
        import struct
        import world_doors

        def sub(tag, data):
            return tag.encode() + struct.pack('<I', len(data)) + data

        def rec(tag, subs):
            data = b''.join(subs)
            return tag.encode() + struct.pack('<III', len(data), 0, 0) + data

        def z(text):
            return text.encode('cp1252') + b'\0'
        door = rec('DOOR', [sub('NAME', z('PrisonMarker')), sub('MODL', z('marker.nif'))])
        prison = rec('CELL', [sub('NAME', z('Test Prison')), sub('DATA', struct.pack('<Iii', 1, 0, 0)),
                              sub('FRMR', struct.pack('<I', 77)), sub('NAME', z('stolen_goods')),
                              sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0))])
        outside = rec('CELL', [sub('NAME', z('')), sub('DATA', struct.pack('<Iii', 0, 2, 3)),
                               sub('FRMR', struct.pack('<I', 5)), sub('NAME', z('PrisonMarker')),
                               sub('DATA', struct.pack('<6f', 100.5, 200.0, 30.0, 0, 0, math.pi / 2)),
                               sub('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0)), sub('DNAM', z('Test Prison'))])
        self.assertEqual(world_doors.prison_markers(door + prison + outside),
                         [{'reference': 5, 'position': [100.5, 200.0, 30.0], 'yaw': 90.0, 'prison': 'Test Prison',
                           'chest': 77}])

    def test_a_scripts_item_change_on_the_player_is_told_in_the_conversation(self):
        notice = body('aw_mwhost.c', 'static void item_notice(')
        self.assertIn('if(count<1 || !AW_DialWindowActive())return;', notice)
        self.assertIn('AW_DialWindowMessage(line);', notice)
        item = body('aw_mwhost.c', 'static int32_t host_item(')
        self.assertIn('item_notice(id,count,1);', item)
        self.assertIn('if(have>0)item_notice(id,have>count?count:have,0);', item)
        self.assertIn('void AW_DialWindowMessage(const char *text){if(active && text && text[0])append(text,PARA_MESSAGE);}',
                      code('aw_dialwin.c'))


if __name__ == '__main__':
    unittest.main()
