# SPDX-License-Identifier: GPL-3.0-only
"""A script's ForceGreeting opens the conversation past the use key's talk rule (MWSCRIPT-FORCEGREETING-TALK-RULES-68).

The original opens the dialogue for any enabled actor a script calls ForceGreeting on, whatever the use key would do
with that actor, refuses only a dead one, and holds the greeting back while the player is a werewolf unless the
actor's own script declares the variable AllowWerewolfForceGreeting (OpenMW 0.51 mwscript/dialogueextensions.cpp
OpForceGreeting; mwdialogue/dialoguemanagerimp.cpp startDialogue). The engine greeted only an actor its talk rule
allows, so a person in a fight (Toralf of Raven Rock, who is to talk after the player's blow), knocked down, or asked
in the frame its fight ended opened nothing, and a werewolf player was greeted by anyone.

The behaviour runs natively: aw_mwhost.c's own werewolf_greeting and script_greeting are cut out of the file into a
harness that gives the talk rule's answer, the dialogue table's rows, the window and a script's variable keys as the
builder writes them. AMIWIND_RUNTIME_SOURCE selects another engine tree: against the engine before the change the
functions do not exist and the harness greets by the talk rule alone, so its checks fail."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga')))
SRC = ENGINE / 'src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))

from mwscript import awms  # noqa: E402

WERE = 'static int werewolf_greeting(uint32_t ref){'
GREET = 'static int script_greeting(edict_t *e){'

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "aw_mwvm.h"
#include "aw_talk.h"
typedef struct edict_s {int free;struct {int classname;} v;uint32_t ref;int talk,dead,role,row;} edict_t;
char *pr_strings="\0aw_npc\0aw_creature\0aw_flora";
#define S_NPC 1
#define S_CREATURE 8
#define S_FLORA 20
uint32_t AW_LedgerNameHash(const char *id){            /* aw_ledger.c, the same rule */
    uint32_t h=2166136261u;
    for(;id && *id;id++){unsigned char c=(unsigned char)*id;if(c>='A' && c<='Z')c=(unsigned char)(c+32);h=(h^c)*16777619u;}
    return h?h:1;
}
/* two script rows: 0 declares AllowWerewolfForceGreeting second, 1 has variables but not that one */
static uint32_t keys0[3]={KEYS0},keys1[2]={KEYS1};
static int locn_reads,names_closed,locn_now_script=-1;
static const uint32_t *locn_keys(int s,int *count){
    locn_reads++;
    if(s==0){*count=3;return keys0;}
    if(s==1){*count=2;return keys1;}
    *count=0;return NULL;
}
static void script_names_done(void){names_closed++;}
static uint32_t ref_of_edict(edict_t *e){return e?e->ref:0;}
static int is_actor(const edict_t *e){
    return e && !e->free && (e->v.classname==S_NPC || e->v.classname==S_CREATURE);
}
static aw_mwvm_instance_t inst[3];
int AW_MwvmLoaded(void){return 1;}
int AW_MwvmInstanceCount(void){return 3;}
aw_mwvm_instance_t *AW_MwvmInstance(int k){return k>=0 && k<3?&inst[k]:NULL;}
static edict_t player,*sv_player=&player;int aw_move_werewolf;
/* the talk rule (aw_talk.c) and the talk's own greeting (QC aw_greet) */
int AW_TalkFacts(edict_t *e,aw_talk_facts_t *f){
    memset(f,0,sizeof(*f));
    if(!e || e->free)return 0;
    f->actor=e->v.classname==S_NPC && !e->role;f->dead=(unsigned char)e->dead;f->dialogue=e->row>=0;
    return 1;
}
static int talks;
static int talk_greeting(edict_t *e){
    if(!e || e->free || e==sv_player || e->v.classname!=S_NPC || !e->talk)return 0;
    talks++;return 1;
}
/* the dialogue table's row of the actor, and the window */
int AW_GlutNpcOf(edict_t *e){return e?e->row:-1;}
static int window_active,window_refuses,opens,row_asks;static edict_t *opened_for;static const char *opened_text;
int AW_DialWindowActive(void){return window_active;}
int AW_DialWindowOpen(edict_t *e,const char *greeting,int again){
    row_asks++;
    if(window_active || window_refuses || again)return 0;
    opens++;opened_for=e;opened_text=greeting;return 1;
}
static unsigned long greetings,greetings_missed,greetings_forced,greetings_werewolf,greetings_norow;
#ifdef HAVE_SCRIPT_GREETING
#define WEREGREET_MEMO 8
static struct {int script,allowed;} weregreet_memo[WEREGREET_MEMO];static int weregreet_count,weregreet_next;
SLICE
#else
/* the engine before: the talk rule alone */
static int script_greeting(edict_t *e){
    (void)is_actor;(void)ref_of_edict;(void)locn_keys;(void)script_names_done;(void)keys0;(void)keys1;
    if(talk_greeting(e)){greetings++;return 1;}
    greetings_missed++;return 0;
}
#endif
static void line(const char *what,int r){
    printf("%s %d talks %d opens %d forced %lu werewolf %lu norow %lu missed %lu\n",what,r,talks,opens,greetings_forced,
           greetings_werewolf,greetings_norow,greetings_missed);
}
int main(void){
    edict_t toralf={0,{S_NPC},100,0,0,0,5},calm={0,{S_NPC},101,1,0,0,6},dead={0,{S_NPC},102,0,1,0,7},
            role={0,{S_NPC},103,0,0,6,8},raven={0,{S_CREATURE},104,0,0,0,-1},mute={0,{S_NPC},105,0,0,0,-1},
            flora={0,{S_FLORA},106,0,0,0,-1},plain={0,{S_NPC},107,0,0,0,9},gone={1,{S_NPC},108,1,0,0,9};
    inst[0].flags=AWI_USED|AWI_GLOBAL;inst[0].reference=101;inst[0].script=0;   /* a global script: never an actor's */
    inst[1].flags=AWI_USED;inst[1].reference=100;inst[1].script=0;              /* Toralf's declares the variable */
    inst[2].flags=AWI_USED;inst[2].reference=101;inst[2].script=1;              /* the calm one's does not */
    /* a person the talk rule refuses (in a fight): the window opens directly, the greeting picked from the table */
    line("fighting",script_greeting(&toralf));
    printf("window for toralf %d empty greeting %d\n",opened_for==&toralf,opened_text && !*opened_text);
    /* a person the rule allows: the talk's own greeting, no second open */
    line("calm",script_greeting(&calm));
    /* never: a dead actor, an opening-scene role, a freed edict, no actor, the player, something that is no actor */
    script_greeting(&dead);script_greeting(&role);script_greeting(&gone);script_greeting(NULL);script_greeting(&player);
    line("refused",script_greeting(&flora));
    /* no row in the dialogue table (a creature, a person the table lacks): counted, the window is not asked */
    row_asks=0;script_greeting(&raven);line("no row",script_greeting(&mute));
    printf("window asked %d\n",row_asks);
    /* a window already open, and a window that cannot open now */
    window_active=1;script_greeting(&toralf);window_active=0;
    window_refuses=1;line("window",script_greeting(&toralf));window_refuses=0;
    /* the player is a werewolf: held back, unless the actor's own script declares AllowWerewolfForceGreeting; the
     * names table is read once per script */
    aw_move_werewolf=1;
    line("werewolf allowed",script_greeting(&toralf));
    line("werewolf held",script_greeting(&calm));
    script_greeting(&toralf);script_greeting(&calm);
    line("werewolf no script",script_greeting(&plain));
    printf("names read %d closed %d\n",locn_reads,names_closed);
    aw_move_werewolf=0;
    line("man again",script_greeting(&plain));
    printf("counts greetings %lu\n",greetings);
    return 0;
}
'''


def function(text, head):
    """The C definition starting at HEAD, to its closing brace at column 0."""
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


def keys(names):
    return ','.join('0x%08Xu' % awms.local_key(name, letter) for name, letter in names)


def run_harness(test):
    host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8', errors='replace')
    have = WERE in host and GREET in host
    source = HARNESS.replace('KEYS0', keys((('OnPCHitMe', 's'), ('AllowWerewolfForceGreeting', 's'), ('timer', 'f'))))
    source = source.replace('KEYS1', keys((('doOnce', 's'), ('allowwerewolfforcegreeting_not', 'l'))))
    source = source.replace('SLICE', function(host, WERE) + function(host, GREET) if have else '')
    with tempfile.TemporaryDirectory(prefix='amiwind-forcegreeting-') as tmp:
        tmp = Path(tmp)
        (tmp / 'h.c').write_text(source, encoding='utf-8')
        cmd = [COMPILER, '-std=gnu89', '-Wall', '-fsanitize=undefined', '-fno-sanitize-recover=all', '-I' + str(SRC),
               str(tmp / 'h.c'), '-o', str(tmp / 'h')] + (['-DHAVE_SCRIPT_GREETING'] if have else [])
        built = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        run = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, timeout=60)
        test.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run.stdout.splitlines()


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class ForceGreetingNativeTests(unittest.TestCase):
    def test_the_greeting_opens_past_the_talk_rule_and_waits_for_a_werewolf(self):
        out = run_harness(self)
        # a person in a fight: the window opens directly, for that actor, with the table's own greeting
        self.assertEqual(out[0], 'fighting 1 talks 0 opens 1 forced 1 werewolf 0 norow 0 missed 0')
        self.assertEqual(out[1], 'window for toralf 1 empty greeting 1')
        # a person the talk rule allows: the talk's greeting as before, the window is not opened a second time
        self.assertEqual(out[2], 'calm 1 talks 1 opens 1 forced 1 werewolf 0 norow 0 missed 0')
        # dead, an opening-scene role, a freed edict, nothing, the player, flora: six misses, nothing opened
        self.assertEqual(out[3], 'refused 0 talks 1 opens 1 forced 1 werewolf 0 norow 0 missed 6')
        # a creature and a person without a row in the dialogue table: counted, and the window is never asked (it
        # would print its refusal every frame a script repeats the call)
        self.assertEqual(out[4], 'no row 0 talks 1 opens 1 forced 1 werewolf 0 norow 2 missed 8')
        self.assertEqual(out[5], 'window asked 0')
        # a window already open (not asked) and a window that cannot open now: two more misses
        self.assertEqual(out[6], 'window 0 talks 1 opens 1 forced 1 werewolf 0 norow 2 missed 10')
        # a werewolf player: greeted only by an actor whose own script declares the variable (a global script of the
        # same row on another actor's reference does not count, nor a name that only starts the same)
        self.assertEqual(out[7], 'werewolf allowed 1 talks 1 opens 2 forced 2 werewolf 0 norow 2 missed 10')
        self.assertEqual(out[8], 'werewolf held 0 talks 1 opens 2 forced 2 werewolf 1 norow 2 missed 11')
        # an actor with no script is held back too; the names of a script are read once and closed again
        self.assertEqual(out[9], 'werewolf no script 0 talks 1 opens 3 forced 3 werewolf 3 norow 2 missed 13')
        self.assertEqual(out[10], 'names read 2 closed 2')
        # the player a man again: the same actor is greeted
        self.assertEqual(out[11], 'man again 1 talks 1 opens 4 forced 4 werewolf 3 norow 2 missed 13')
        self.assertEqual(out[12], 'counts greetings 5')


class ForceGreetingContractTests(unittest.TestCase):
    def test_the_script_call_and_the_console_call_take_the_new_path(self):
        host = code('aw_mwhost.c')
        call = host[host.index('case AWF_FORCEGREETING:{'):]
        call = call[:call.index('return 1;}')]
        self.assertIn('script_greeting(n>0?edict_of(n):NULL);', call)
        self.assertIn('script_greeting(e)?"greeting played":"not possible"', host)
        # the arrest keeps the talk rule's greeting first and its own open after it (STEAL-WITNESSED-NO-CRIME-61)
        arrest = function(host, 'static int crime_greet(edict_t *e){')
        self.assertIn('if(force_greeting(e))return 1;', arrest)
        # the rule's order: the werewolf rule before any greeting, the talk's own greeting before the direct open,
        # no open for a dead actor, an opening-scene role or an actor the table has no row for
        greet = function(host, GREET)
        self.assertLess(greet.index('aw_move_werewolf'), greet.index('talk_greeting(e)'))
        self.assertLess(greet.index('talk_greeting(e)'), greet.index('AW_DialWindowOpen(e,"",0)'))
        self.assertLess(greet.index('f.dead'), greet.index('AW_DialWindowOpen(e,"",0)'))
        self.assertLess(greet.index('AW_GlutNpcOf(e)<0'), greet.index('AW_DialWindowOpen(e,"",0)'))
        # the variable by its name key, the type bits left out; an actor's own instance, never a global script
        were = function(host, WERE)
        self.assertIn('AW_LedgerNameHash("allowwerewolfforcegreeting")&0x3FFFFFFFu', were)
        self.assertIn('(in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference==ref', were)

    def test_the_key_is_the_builders_and_the_effect_class_and_the_page_say_it(self):
        self.assertEqual(awms.local_key('AllowWerewolfForceGreeting', 's') & 0x3FFFFFFF,
                         awms.name_hash('allowwerewolfforcegreeting') & 0x3FFFFFFF)
        import json
        effects = json.loads((ROOT / 'config' / 'mwscript-effects.json').read_text(encoding='utf-8'))
        row = effects['functions']['forcegreeting']
        # full since the creatures that have lines got their rows in the dialogue table (tools/greeting_lut.py, the
        # creature's rule) and the greeting opens for any speaker with a row; read from the source, not yet seen in
        # play (MWSCRIPT-EFFECT-PARITY-69: the row was "in part: a creature opens no conversation" until then)
        self.assertEqual(row['effect'], 'full')
        self.assertEqual(row['basis'], 'source')
        self.assertEqual(row['missing'], '')
        self.assertEqual(row['register'], ['DIALOGUE-CREATURE-SPEAKERS-66', 'MWSCRIPT-FORCEGREETING-TALK-RULES-68'])
        self.assertIn('CreatureContext', (ROOT / 'tools' / 'greeting_lut.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
