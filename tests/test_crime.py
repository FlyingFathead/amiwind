# SPDX-License-Identifier: GPL-3.0-only
"""Crime (STEAL-WITNESSED-NO-CRIME-61, CRIME-59) and the dialogue's item notices (DIALOGUE-ITEM-NOTICE-MISSING-61): the
rules in host C, the builder's settings lines in the engine's order, and the source contracts that wire every take
path (a placed item, a container's content, an owned plant) to the crime rules and a script's AddItem / RemoveItem
on the player to the conversation."""
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
        theft = body('aw_crime.c', 'static int crime_run(')
        self.assertIn('return crime(owner,faction,value,0);', code('aw_crime.c'))
        # the maintainer's rule: only at the moment of a crime, never per frame: the take paths are the only callers
        callers = [p.name for p in SRC.glob('*.c') if re.search(r'\bAW_CrimeTheft\s*\(', code(p.name))]
        self.assertEqual(sorted(callers), ['aw_crime.c'])
        self.assertIn('seen=crime_run(owner,faction,value,dry);', body('aw_crime.c', 'static int crime('))
        # AngleVectors writes forward, right and up: a NULL one stopped the game at the first witness (in game, s1-s3)
        self.assertNotRegex(code('aw_crime.c'), r'AngleVectors\([^)]*NULL')
        # the witnesses: the alarm radius (or the victim anywhere), canReportCrime, the line of sight, the roll
        self.assertIn('if(dist>radius && !victim)continue;', theft)
        self.assertIn('if(!aw_crime_witness(e,&w) || !w.can_report)continue;', theft)
        self.assertIn('if((los=sees(p,e))!=0){roll=roll100();noticed=(float)roll>=aim;}', theft)
        self.assertIn('AW_GlutSay(e,AW_GLUT_THIEF,0)', theft)
        # nobody saw it: no crime, no bounty
        self.assertLess(theft.index('if(!seen || dry)return seen;'), theft.index('AW_StandingModCrime(last.bounty);'))
        # reported only when an NPC in the radius has Alarm 100; the game's line
        self.assertIn('if(AW_CRIME_REPORTS(w.alarm))reporter=1;', theft)
        self.assertIn('if(crime_text[0])AW_MsgBoxShow(crime_text,NULL,0);', theft)
        self.assertIn('if(w.fight+term>=100 && aw_crime_attack && aw_crime_attack(e,w.fight+(int)term))', theft)

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
