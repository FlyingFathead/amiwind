# SPDX-License-Identifier: GPL-3.0-only
"""The Heart chamber's strike sequence as a scripted scene (DAGOTH-UR-NO-ANIMATIONS-65, docs/SCRIPTED_ACTORS.md).

Two scripts written for this test (our own words, the same rules as the original chamber's two scripts): the Heart
counts Keening strikes only after a Sunder strike, plays Idle2 to Idle5 on the first four and Death1 on the fifth,
then sets the global HeartDestroyed; Dagoth Ur's health is set back whenever it falls under 1,000 while the Heart
lives, and capped low once it is destroyed, so he can die only then. The scripts go through our compiler and the
script interpreter (aw_mwvm.c) with stub hosts; the stub answers HitOnMe as the combat hook would after a blow with
the named weapon (aw_mwhost.c hit_on_me), and keeps each actor's health. Checked frame by frame: Keening before
Sunder counts nothing; the five strikes play Idle2, Idle3, Idle4, Idle5 and Death1 in that order, once each;
HeartDestroyed is 0 until the fifth and 1 after; Dagoth Ur's health is back at 1,000 after every blow before it
and falls to death after it.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

HEART = '''Begin TestHeartScene
short struck
short strikes
if ( HitOnMe "test_sunder" == 1 )
    set struck to 1
endif
if ( struck == 1 )
    if ( HitOnMe "test_keening" == 1 )
        set strikes to ( strikes + 1 )
        if ( strikes == 1 )
            PlayGroup Idle2 1
        elseif ( strikes == 2 )
            PlayGroup Idle3 1
        elseif ( strikes == 3 )
            PlayGroup Idle4 1
        elseif ( strikes == 4 )
            PlayGroup Idle5 1
        elseif ( strikes == 5 )
            PlayGroup Death1 1
            set TestHeartGone to 1
        endif
    endif
endif
End TestHeartScene
'''

DAGOTH = '''Begin TestDagothScene
if ( TestHeartGone == 0 )
    if ( GetHealth < 1000 )
        SetHealth 1000
    endif
elseif ( GetHealth > 50 )
    SetHealth 50
endif
End TestDagothScene
'''

# The stub host: tick T's blows (env BLOWS "T:weapon,..."), each a HitOnMe answer on the Heart's instance once; the
# player's blows on Dagoth Ur (env DAGOTH_DAMAGE per tick) take health off; every PlayGroup and the global printed.
HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_mwvm.h"
#include "aw_mwcode.h"
static int tick,fn_hit,fn_play,heart_inst=-1;static unsigned sunder,keening,heart_ref;
static char blows[64];          /* blows[tick]: 's' Sunder, 'k' Keening, 0 none (taken by the first matching HitOnMe) */
static float health[64];
static void h_sound(int i,int t,int s,int how,float v,float p){}
static int h_playing(int i,int t,int s){return 0;}
static void h_say(int i,int t,int v,int x){}
static int h_saydone(int i,int t){return 1;}
static void h_music(int m){}
static float h_distance(int i,int t){return 100.0f;}
static int h_menu(void){return 0;}
static int32_t h_query(int i,int q,int o){return 0;}
static int32_t h_jget(int t){return 0;}
static void h_jset(int t,int32_t v,int adv){}
static void h_notyet(int n,int s){printf("%d notyet %d\n",tick,n);}
static void h_warn(const char *w,int s){}
static int32_t h_object(int i,int t,int op,int32_t v){return 0;}
static void h_message(int i,int t,const float *v,int n,const unsigned char *b,int c){}
static int h_button(int i){return -1;}
static aw_mwcell_t h_actor(int i,int t,int verb,int stat,aw_mwcell_t v){
    aw_mwcell_t out;out.i=0;
    if(i<0 || i>=64 || stat!=35)return out;
    if(verb==0)out.f=health[i];
    else if(verb==1)health[i]=v.f;
    else if(verb==2)health[i]+=v.f;
    return out;
}
static int32_t h_item(int i,int t,int verb,int item,int32_t n){return 0;}
static int32_t h_spell(int i,int t,int verb,int s){return 0;}
static void h_combat(int i,int t,int verb,int o){}
static int32_t h_dead(int a){return 0;}
static void h_wander(int i,int t,const int32_t *v,int n){}
static int h_call(int i,int t,int fn,const aw_mwcell_t *v,int n,const unsigned char *s,int ns,aw_mwcell_t *r){
    unsigned k=ns>0?(unsigned)((s[0]<<8)|s[1]):0xffffu;
    if(fn==fn_hit){
        char want=k==sunder?'s':k==keening?'k':0;
        r->i=0;
        if(i==heart_inst && want && tick<64 && blows[tick]==want){blows[tick]=0;r->i=1;}
        return AW_MWVM_CALL_READ;
    }
    if(fn==fn_play){printf("%d play %d %u\n",tick,i,k);return 1;}
    return 0;
}
static int h_cell(int *x,int *y){*x=0;*y=0;return 2;}
static float h_pos(int i,int t,int axis){return 0.0f;}
static int h_move(int i,int kind,int map,const float *at,float yaw){return 1;}
static int32_t h_ai(int i,int t,int verb){return 0;}
static const aw_mwvm_host_t host={h_sound,h_playing,h_say,h_saydone,h_music,h_distance,h_menu,h_query,h_jget,h_jset,h_notyet,h_warn,h_object,h_message,h_button,
    h_actor,h_item,h_spell,h_combat,h_dead,h_wander,h_call,h_cell,h_pos,h_move,h_ai};
static unsigned char buf[1<<20];
int main(int argc,char **argv){
    FILE *f=fopen(argv[1],"rb");long n=fread(buf,1,sizeof(buf),f);uint32_t off,rows,bytes,r;
    int ticks=atoi(argv[2]),gone=atoi(getenv("GONE")),dagoth_inst=-1;float player[3]={0,0,0},damage=(float)atof(getenv("DAMAGE"));
    unsigned dagoth_ref=(unsigned)atoi(getenv("DAGOTH_REF"));const char *b=getenv("BLOWS");
    fclose(f);
    fn_hit=atoi(getenv("FN_HIT"));fn_play=atoi(getenv("FN_PLAY"));
    sunder=(unsigned)atoi(getenv("SUNDER"));keening=(unsigned)atoi(getenv("KEENING"));heart_ref=(unsigned)atoi(getenv("HEART_REF"));
    while(b && *b){int t=atoi(b);const char *c=strchr(b,':');if(!c)break;if(t>0 && t<64)blows[t]=c[1];b=strchr(c,',');if(b)b++;}
    if(!AW_MwvmLoad(buf,(unsigned long)n,&host)){printf("load failed\n");return 1;}
    AW_MwvmBeginMap();
    AW_MwvmSection("BIND",&off,&rows,&bytes);
    for(r=0;r<rows;r++){
        unsigned char *p=buf+off+24*r;float o[3]={0,0,0};
        unsigned ref=((unsigned)p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3];
        int k=AW_MwvmAttach(ref,(p[4]<<8)|p[5],(p[6]<<8)|p[7],-1,o);
        if(ref==heart_ref)heart_inst=k;
        if(ref==dagoth_ref)dagoth_inst=k;
    }
    printf("attached heart %d dagoth %d\n",heart_inst,dagoth_inst);
    if(heart_inst<0 || dagoth_inst<0 || dagoth_inst>=64)return 1;
    health[dagoth_inst]=1000;
    for(tick=1;tick<=ticks;tick++){
        health[dagoth_inst]-=damage;            /* the player's blow on Dagoth Ur this frame */
        AW_MwvmTick(0.1f,player);
        printf("%d health %.0f gone %d\n",tick,health[dagoth_inst],AW_MwvmGlobalInt(gone));
    }
    return 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class HeartStrikeScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_mwscript import master_bytes, SCRIPTS, record, sub, glob, ROOMS
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program, bindings
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript import awms
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-heart-scene-'))
        scripts = dict(SCRIPTS, TestHeartScene=HEART, TestDagothScene=DAGOTH)
        records = [glob('TestHeartGone', 's', 0),
                   record('WEAP', sub('NAME', 'test_sunder')), record('WEAP', sub('NAME', 'test_keening')),
                   record('CREA', sub('NAME', 'test_heart'), sub('SCRI', 'TestHeartScene')),
                   record('CREA', sub('NAME', 'test_dagoth'), sub('SCRI', 'TestDagothScene'))]
        (cls.tmp / 'Morrowind.esm').write_bytes(master_bytes(scripts, records, room_refs=[
            (501, 'test_heart', (0, 0, 0)), (502, 'test_dagoth', (100, 0, 0))]))
        data = GameData().load(cls.tmp)
        prog, compiled = compile_program(data, None, handwritten=(), rooms=ROOMS)
        binds = bindings(prog, compiled)
        raw, _ = awms.write(prog, compiled, binds, {'ops_per_run': 500})
        (cls.tmp / 'scene.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        cls.prog, cls.compiled, cls.binds = prog, compiled, binds
        cls.names = {c.name: c for c in compiled}

        def string(ident):
            for key, value in prog.strings.index.items():
                if key.casefold() == ident:
                    return value
            raise KeyError(ident)
        cls.env = {'FN_HIT': str(FUNCTION_NUMBERS['hitonme']), 'FN_PLAY': str(FUNCTION_NUMBERS['playgroup']),
                   'SUNDER': str(string('test_sunder')), 'KEENING': str(string('test_keening')),
                   'HEART_REF': '501', 'DAGOTH_REF': '502', 'GONE': str(prog.globals.index['testheartgone'])}
        cls.groups = {g: string(g) for g in ('idle2', 'idle3', 'idle4', 'idle5', 'death1')}
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_mwvm.c'), str(src / 'aw_ledger.c'),
                                '-o', str(cls.tmp / 'h')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_scene(self, ticks, blows, damage):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'scene.awm'), str(ticks)], capture_output=True,
                           text=True, env=dict(os.environ, BLOWS=blows, DAMAGE=str(damage), **self.env))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.splitlines()

    def test_the_scripts_compile_without_gaps(self):
        for name in ('TestHeartScene', 'TestDagothScene'):
            self.assertEqual(self.names[name].notyet, [], name)
        bound = {b['reference'] for b in self.binds}
        self.assertTrue({501, 502} <= bound)

    def test_sunder_then_five_keening_strikes(self):
        # tick 2 Keening before Sunder (nothing), 4 Sunder, then Keening at 6, 8, 10, 12, 14; Dagoth Ur takes 300 a frame
        out = self.run_scene(20, '2:k,4:s,6:k,8:k,10:k,12:k,14:k', 300)
        heart = next(l for l in out if l.startswith('attached')).split()[2]
        plays = [(int(l.split()[0]), int(l.split()[3])) for l in out if l.split()[1:2] == ['play']]
        self.assertTrue(all(l.split()[2] == heart for l in out if l.split()[1:2] == ['play']))
        g = self.groups
        self.assertEqual(plays, [(6, g['idle2']), (8, g['idle3']), (10, g['idle4']), (12, g['idle5']),
                                 (14, g['death1'])])
        state = {int(l.split()[0]): (float(l.split()[2]), int(l.split()[4])) for l in out if l.split()[1:2] == ['health']}
        for t in range(1, 14):
            self.assertEqual(state[t], (1000.0, 0), t)      # set back every frame while the Heart lives
        self.assertEqual(state[14][1], 1)                    # HeartDestroyed on the fifth strike
        # after it: capped at 50 once, then the blows take him under 0 (he can die)
        later = [state[t][0] for t in range(15, 21)]
        self.assertLessEqual(later[0], 50.0)
        self.assertLess(min(later), 0.0)

    def test_keening_without_sunder_counts_nothing(self):
        out = self.run_scene(12, '2:k,4:k,6:k,8:k,10:k', 300)
        self.assertFalse([l for l in out if l.split()[1:2] == ['play']])
        self.assertTrue(all(l.split()[4] == '0' for l in out if l.split()[1:2] == ['health']))


if __name__ == '__main__':
    unittest.main()
