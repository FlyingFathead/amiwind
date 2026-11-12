/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_reset.c alone (NEWGAME-STATE-RESET-62): every registered reset runs, in order, once per AW_ResetAll; a state
 * that a reset leaves behind differs from the boot mark and is named; a module re-registered is kept once. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_reset.h"

/* three modules: a story (new_game sets a stage), a fire table, an effects list that "forgets" to reset */
static int stage,fires[4],effects,calls[3],order[64],ordered;
static void reset_story(int new_game){stage=new_game?1:0;calls[0]++;order[ordered++]=0;}
static unsigned long digest_story(void){return AW_ResetHash(AW_RESET_SEED,&stage,sizeof(stage));}
static void reset_fires(int new_game){memset(fires,0,sizeof(fires));fires[2]=1;calls[1]++;order[ordered++]=1;}   /* lit at boot */
static unsigned long digest_fires(void){return AW_ResetHash(AW_RESET_SEED,fires,sizeof(fires));}
static int forget;
static void reset_effects(int new_game){if(!forget)effects=0;calls[2]++;order[ordered++]=2;}
static unsigned long digest_effects(void){return AW_ResetHash(AW_RESET_SEED,&effects,sizeof(effects));}

static int clobber;
static void reset_scene(int new_game){(void)new_game;if(clobber)stage=0;}   /* resets the story again, restart form */

int main(void){
    char names[128];
    assert(AW_ResetHash(AW_RESET_SEED,"a",1)!=AW_ResetHash(AW_RESET_SEED,"b",1));
    assert(AW_ResetCompareBoot(names,sizeof(names))==-1);                 /* no boot mark yet */
    assert(AW_ResetRegister("story",reset_story,digest_story));
    assert(AW_ResetRegister("fires",reset_fires,digest_fires));
    assert(AW_ResetRegister("effects",reset_effects,digest_effects));
    assert(AW_ResetRegister("effects again",reset_effects,digest_effects) && AW_ResetModules()==3);
    assert(!AW_ResetRegister("none",NULL,NULL));
    /* the boot: a fresh state, then the New Game form marked */
    reset_fires(0);effects=0;stage=0;
    stage=1;AW_ResetMarkBoot();stage=0;
    /* a game changes every state: the fire goes out, an effect stays, the story moves on */
    stage=5;fires[2]=0;effects=3;
    assert(AW_ResetCompareBoot(names,sizeof(names))==3);
    /* New Game: every reset once, in order; the state is the fresh boot's */
    ordered=0;assert(AW_ResetAll(1)==3 && calls[0]==1 && calls[1]==2 && calls[2]==1);
    assert(order[0]==0 && order[1]==1 && order[2]==2 && ordered==3);
    assert(AW_ResetCompareBoot(names,sizeof(names))==0 && !names[0]);
    assert(fires[2]==1);                                                   /* the fire lit again */
    /* a module whose reset leaves its state behind is caught and named */
    effects=7;forget=1;AW_ResetAll(1);
    assert(AW_ResetCompareBoot(names,sizeof(names))==1 && !strcmp(names,"effects again"));
    forget=0;AW_ResetAll(1);assert(AW_ResetCompareBoot(names,sizeof(names))==0);
    assert(AW_ResetModuleName(99)==NULL && AW_ResetModuleDigest(-1)==(unsigned long)-1);
    /* OPENING-VANITY-CAMERA-64: a later module that overwrites an earlier module's state (the scene reset set the story
     * back to its restart form). Marked after the whole run, the reference holds the overwrite and nothing is named;
     * marked interleaved (each module right after its own reset), the earlier module is named after a New Game. */
    clobber=1;assert(AW_ResetRegister("scene",reset_scene,NULL) && AW_ResetModules()==4);
    AW_ResetAll(1);AW_ResetMarkBoot();AW_ResetAll(1);
    assert(stage==0 && AW_ResetCompareBoot(names,sizeof(names))==0);      /* the old mark: blind to it */
    assert(AW_ResetMarkBootInterleaved(1)==4);AW_ResetAll(0);
    AW_ResetAll(1);
    assert(AW_ResetCompareBoot(names,sizeof(names))==1 && !strcmp(names,"story"));
    clobber=0;AW_ResetMarkBootInterleaved(1);AW_ResetAll(1);
    assert(stage==1 && AW_ResetCompareBoot(names,sizeof(names))==0);      /* fixed: the story keeps its New Game form */
    printf("reset registry ok\n");
    return 0;
}
