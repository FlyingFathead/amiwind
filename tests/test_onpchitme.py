# SPDX-License-Identifier: GPL-3.0-only
"""The script variable OnPCHitMe is set when the player strikes the actor (MWSCRIPT-ONPCHITME-NEVER-SET-68).

The original sets the variable OnPCHitMe of an NPC's or creature's own script to 1 when the player's blow reaches for
it, a hit or a miss, and leaves it to the script to set it back (OpenMW 0.51 mwclass/npc.cpp and creature.cpp onHit:
setVarByInt(script, "onpchitme", 1)). 32 scripts of the three masters declare it, 19 of them Solstheim's (Toralf's band
and the other Raven Rock colony scripts, Hroldar, the Glenmoril raven, Ulfgar's ghost), and 31 test it. Nothing in the
engine set it, so those scripts waited for a blow for ever.

The engine finds the variable's slot by its name's key among the script's LOCN keys (tools/mwscript/awms.py local_key,
the table a save names the variables by), so no table is added to the script file. The behaviour runs natively:
aw_mwhost.c's own pchit_slot and pc_hit are cut out of the file into a harness that gives the interpreter's calls and a
script's keys as the builder writes them. AMIWIND_RUNTIME_SOURCE selects another engine tree: against the engine before
the change the functions do not exist and the harness sets nothing, so its checks fail."""
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

SLOT = 'static int pchit_slot(int script){'
HIT = 'static void pc_hit(edict_t *e){'

HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "aw_mwvm.h"
typedef struct edict_s {uint32_t ref;} edict_t;
uint32_t AW_LedgerNameHash(const char *id){            /* aw_ledger.c, the same rule */
    uint32_t h=2166136261u;
    for(;id && *id;id++){unsigned char c=(unsigned char)*id;if(c>='A' && c<='Z')c=(unsigned char)(c+32);h=(h^c)*16777619u;}
    return h?h:1;
}
/* three script rows: 0 declares OnPCHitMe third (after two others), 1 has variables but not that one, 2 has no row in
 * the names table (an older file's script) */
static uint32_t keys0[4]={KEYS0},keys1[2]={KEYS1};
static int locn_reads,names_closed,locn_now_script=-1;
static const uint32_t *locn_keys(int s,int *count){
    locn_reads++;
    if(s==0){*count=4;return keys0;}
    if(s==1){*count=2;return keys1;}
    *count=0;return NULL;
}
static void script_names_done(void){names_closed++;}
static uint32_t ref_of_edict(edict_t *e){return e?e->ref:0;}
static aw_mwvm_instance_t inst[4];static int loaded=1,changed;
int AW_MwvmLoaded(void){return loaded;}
int AW_MwvmInstanceCount(void){return 4;}
aw_mwvm_instance_t *AW_MwvmInstance(int k){return k>=0 && k<4?&inst[k]:NULL;}
static int32_t locals[3][4];static int sets;
int AW_MwvmLocalSet(uint32_t reference,int script,int slot,uint32_t bits){
    if(reference<100 || reference>102 || script!=(int)(reference-100) || slot<0 || slot>3)return 0;
    locals[script][slot]=(int32_t)bits;sets++;return 1;
}
void AW_MwvmStateChanged(void){changed++;}
static unsigned long pchit_blows,pchit_set,pchit_unnamed;static int pchit_count;
#ifdef HAVE_PCHIT
#define PCHIT_MEMO 16
static struct {int script,slot;} pchit_memo[PCHIT_MEMO];static int pchit_next;
SLICE
#else
static void pc_hit(edict_t *e){(void)e;}              /* the engine before: nothing sets the variable */
#endif
int main(void){
    edict_t toralf={100},guard={101},old={102},plain={555},none={0};int i;
    inst[0].flags=AWI_USED|AWI_GLOBAL;inst[0].reference=0;inst[0].script=0;        /* a global script: never an actor's */
    inst[1].flags=AWI_USED;inst[1].reference=100;inst[1].script=0;
    inst[2].flags=AWI_USED;inst[2].reference=101;inst[2].script=1;
    inst[3].flags=AWI_USED;inst[3].reference=102;inst[3].script=2;
    pc_hit(&toralf);
    printf("first %d %d %d %d reads %d closed %d woke %d\n",locals[0][0],locals[0][1],locals[0][2],locals[0][3],locn_reads,
           names_closed,changed);
    locals[0][2]=0;                                    /* the script sets it back */
    for(i=0;i<3;i++)pc_hit(&toralf);
    printf("again %d reads %d sets %d\n",locals[0][2],locn_reads,sets);
    pc_hit(&guard);pc_hit(&guard);
    printf("no variable %d %d reads %d sets %d\n",locals[1][0],locals[1][1],locn_reads,sets);
    pc_hit(&old);pc_hit(&plain);pc_hit(&none);
    printf("unnamed %lu reads %d sets %d\n",pchit_unnamed,locn_reads,sets);
    loaded=0;pc_hit(&toralf);loaded=1;
    printf("counts blows %lu set %lu scripts %d\n",pchit_blows,pchit_set,pchit_count);
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
    have = SLOT in host and HIT in host
    source = HARNESS.replace('KEYS0', keys((('nolore', 's'), ('attackinit', 's'), ('OnPCHitMe', 's'), ('timer', 'f'))))
    source = source.replace('KEYS1', keys((('doOnce', 's'), ('onpchitme_not', 'l'))))
    source = source.replace('SLICE', function(host, SLOT) + function(host, HIT) if have else '')
    with tempfile.TemporaryDirectory(prefix='amiwind-onpchitme-') as tmp:
        tmp = Path(tmp)
        (tmp / 'h.c').write_text(source, encoding='utf-8')
        cmd = [COMPILER, '-std=gnu89', '-Wall', '-fsanitize=undefined', '-fno-sanitize-recover=all', '-I' + str(SRC),
               str(tmp / 'h.c'), '-o', str(tmp / 'h')] + (['-DHAVE_PCHIT'] if have else [])
        built = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        run = subprocess.run([str(tmp / 'h')], capture_output=True, text=True, timeout=60)
        test.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run.stdout.splitlines()


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class OnPCHitMeNativeTests(unittest.TestCase):
    def test_a_blow_sets_the_variable_of_the_actors_own_script(self):
        out = run_harness(self)
        # the third variable of the actor's script (the global script of the same row is not the actor's), 1; the names
        # table read once and closed again; the scripts woken
        self.assertEqual(out[0], 'first 0 0 1 0 reads 1 closed 1 woke 1')
        # the script set it back: the next blows set it again, with no further read of the names (kept per script)
        self.assertEqual(out[1], 'again 1 reads 1 sets 4')
        # a script without the variable: nothing set, looked up once; a name that only starts the same is not it
        self.assertEqual(out[2], 'no variable 0 0 reads 2 sets 4')
        # a script the file names no variables of (counted), an actor with no script and an edict with no reference
        self.assertEqual(out[3], 'unnamed 1 reads 3 sets 4')
        # every blow counted, also the one while no script file is loaded; three scripts looked up in all
        self.assertEqual(out[4], 'counts blows 10 set 4 scripts 3')


class OnPCHitMeContractTests(unittest.TestCase):
    def test_the_blow_in_reach_and_the_harmful_spell_call_the_hook(self):
        combat = code('aw_combat.c')
        strike = function(combat, 'static void player_strike(edict_t *p) {')
        # on every attempt in reach, a hit or a miss: after the reach test, before the swing is rolled
        self.assertIn('if(aw_combat_pc_hit)aw_combat_pc_hit(t);', strike)
        self.assertLess(strike.index('gap_to(p,t,&dz)>reach'), strike.index('aw_combat_pc_hit(t)'))
        self.assertLess(strike.index('aw_combat_pc_hit(t)'), strike.index('AW_CombatSwing('))
        spell = function(combat, 'int AW_CombatSpellHit(edict_t *e,float health,int harmful) {')
        self.assertIn('if(harmful && aw_combat_pc_hit)aw_combat_pc_hit(e);', spell)
        host = code('aw_mwhost.c')
        self.assertIn('aw_combat_pc_hit=pc_hit;', host)
        # the slot by the variable's name key, its type bits left out; an actor's own instance, never a global script
        self.assertIn('AW_LedgerNameHash("onpchitme")&0x3FFFFFFFu', function(host, SLOT))
        self.assertIn('(in->flags&(AWI_USED|AWI_GLOBAL))==AWI_USED && in->reference==ref', function(host, HIT))
        # declared by its user: aw_combat.h is keyed by the CHIM world stage
        self.assertNotIn('aw_combat_pc_hit', (SRC / 'aw_combat.h').read_text(encoding='utf-8'))

    def test_the_key_is_the_builders_and_the_scripts_are_counted_in_the_docs(self):
        # the engine's key of the name is the builder's (the name hash's low 30 bits; bits 30-31 the type)
        self.assertEqual(awms.local_key('OnPCHitMe', 's') & 0x3FFFFFFF, awms.name_hash('onpchitme') & 0x3FFFFFFF)
        self.assertEqual(awms.local_key('OnPCHitMe', 's') >> 30, 0)
        page = (ROOT / 'docs' / 'COMBAT.md').read_text(encoding='utf-8')
        self.assertIn('### The script variable OnPCHitMe', page)
        self.assertIn('32 scripts of the game declare it and 31 test it', page)


if __name__ == '__main__':
    unittest.main()
