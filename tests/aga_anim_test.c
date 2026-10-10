/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_anim.c pure part: layout parsing (groups, events, sounds, unknown words
 * skipped, invalid layouts fall back to the previous frames), group choice by
 * speed with a speed-matched rate, loop and one-shot stepping, and the
 * footstep events crossed. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_anim.h"

static const char *layout =
    "idle:0:8:0.3333 walk:8:8:0.1250:38.52 run:16:6:0.1556:55.71 swim:22:6:0.2778:26.25 "
    "swimidle:28:4:0.5000 hit:32:3:0.3333 knock:35:4:0.6667 death:39:6:0.3333 attack:45:8:0.1167:0.714 "
    "@walk:1:right @walk:5:left @run:2:right @run:5:left @swim:3:left @swim:5:right "
    "~left:aw/fx/footmedleft.wav:aw/fx/footwaterleft.wav:aw/fx/swimleft.wav "
    "~right:aw/fx/footmedright.wav:aw/fx/footwaterright.wav:aw/fx/swimright.wav future:1:2:3\n";

static int heard[2];
static void emit(void *context,int kind) {(void)context;heard[kind]++;}

int main(void) {
    aw_anim_t a;aw_anim_play_t p;float rate;unsigned long crossed;int g,f,i;
    /* parsing */
    assert(AW_AnimParse(&a,layout,53));
    assert(a.from_layout && a.events==6);
    assert(a.g[AW_ANIM_WALK].base==8 && a.g[AW_ANIM_WALK].count==8);
    assert(a.g[AW_ANIM_WALK].x>38.5f && a.g[AW_ANIM_WALK].x<38.53f);
    assert(a.g[AW_ANIM_ATTACK].x>.713f && a.g[AW_ANIM_ATTACK].x<.715f);
    assert(a.g[AW_ANIM_DEATH].base==39 && a.g[AW_ANIM_DEATH].count==6);
    assert(!strcmp(a.sound[AW_ANIM_LEFT][AW_ANIM_DRY],"aw/fx/footmedleft.wav"));
    assert(!strcmp(a.sound[AW_ANIM_RIGHT][AW_ANIM_SWIMMING],"aw/fx/swimright.wav"));
    /* a group beyond the model's frames, or no idle: the previous layout */
    assert(!AW_AnimParse(&a,layout,40) && !a.from_layout && a.g[AW_ANIM_IDLE].count==8 && a.g[AW_ANIM_WALK].present==0);
    assert(!AW_AnimParse(&a,"walk:8:8:0.125",21) && a.g[AW_ANIM_WALK].base==13);
    assert(!AW_AnimParse(&a,NULL,1) && a.g[AW_ANIM_IDLE].count==1);
    assert(!AW_AnimParse(&a,"idle:0:8:0.3 @walk:1:left",16));   /* event on a missing group */
    /* only one sound given: every medium uses it */
    assert(AW_AnimParse(&a,"idle:0:8:0.3 walk:8:8:0.125:38 @walk:1:left ~left:a.wav",16));
    assert(!strcmp(a.sound[AW_ANIM_LEFT][AW_ANIM_SWIMMING],"a.wav"));

    /* block and the dodge extension are groups like any other; dodgel does not match dodger */
    assert(AW_AnimParse(&a,"idle:0:8:0.3 block:8:5:0.2:0.4 dodgel:13:3:0.3:20 dodger:16:3:0.3:20",19));
    assert(a.g[AW_ANIM_BLOCK].base==8 && a.g[AW_ANIM_BLOCK].x>.39f && a.g[AW_ANIM_DODGEL].base==13 && a.g[AW_ANIM_DODGER].base==16);
    memset(&p,0,sizeof(p));p.group=255;
    AW_AnimAdvance(&a,&p,AW_ANIM_DODGEL,0,1,&crossed);f=AW_AnimAdvance(&a,&p,AW_ANIM_DODGEL,5,1,&crossed);
    assert(f==15 && AW_AnimDone(&a,&p));                     /* one-shot: holds its last frame */

    /* voice lines: first match (OpenMW Filter::search), conditions on Random100 and health */
    assert(AW_AnimParse(&a,"idle:0:8:0.3 !attack:0123456789abcdef:rg75 !attack:fedcba9876543210:rg25 "
                         "!attack:00112233445566ff !hit:aaaaaaaaaaaaaaaa:hl30 !hit:bbbbbbbbbbbbbbbb !flee:XYZ",8));
    assert(a.voices[AW_VOICE_ATTACK_LINE]==3 && a.voices[AW_VOICE_HIT_LINE]==2 && a.voices[AW_VOICE_FLEE_LINE]==0);
    assert(a.voice[0][0].hash[0]==0x01 && a.voice[0][0].hash[7]==0xef && a.voice[0][0].kind[0]=='r' && a.voice[0][0].value[0]==75);
    assert(AW_VoicePick(&a,AW_VOICE_ATTACK_LINE,100,100,90,0,0)==0);          /* Random100 90 >= 75 */
    assert(AW_VoicePick(&a,AW_VOICE_ATTACK_LINE,100,100,50,0,0)==1);
    assert(AW_VoicePick(&a,AW_VOICE_ATTACK_LINE,100,100,10,0,0)==2);          /* the unconditional line */
    assert(AW_VoicePick(&a,AW_VOICE_HIT_LINE,20,100,0,0,0)==0);               /* health 20 <= 30 */
    assert(AW_VoicePick(&a,AW_VOICE_HIT_LINE,80,100,0,0,0)==1);
    assert(AW_VoicePick(&a,AW_VOICE_FLEE_LINE,100,100,0,0,0)==-1);
    assert(AW_VoicePick(&a,AW_VOICE_ATTACK_LINE,100,100,90,1,1)==1);          /* random among the 3 matches */
    {int seen[3]={0,0,0};for(i=0;i<30;i++)seen[AW_VoicePick(&a,AW_VOICE_ATTACK_LINE,100,100,90,1,i)]++;
     assert(seen[0] && seen[1] && seen[2]);}

    /* the mover model token */
    assert(AW_AnimParse(&a,"idle:0:8:0.3 hit:8:3:0.33 >progs/a_0123456789ab_m.mdl",16));
    assert(!strcmp(a.mover,"progs/a_0123456789ab_m.mdl"));
    assert(AW_AnimParse(&a,"idle:0:8:0.3 >progs/not-a-model.txt",16) && !a.mover[0]);
    assert(AW_AnimParse(&a,layout,53) && !a.mover[0]);

    /* group choice and rate */
    assert(AW_AnimParse(&a,layout,53));
    assert(AW_AnimMoveGroup(&a,0,0,&rate)==AW_ANIM_IDLE && rate==1);
    g=AW_AnimMoveGroup(&a,38.52f,0,&rate);assert(g==AW_ANIM_WALK && rate>.99f && rate<1.01f);
    g=AW_AnimMoveGroup(&a,46,0,&rate);assert(g==AW_ANIM_WALK);          /* below the midpoint 47.1 */
    g=AW_AnimMoveGroup(&a,60,0,&rate);assert(g==AW_ANIM_RUN && rate>1.07f && rate<1.08f);
    g=AW_AnimMoveGroup(&a,1000,0,&rate);assert(g==AW_ANIM_RUN && rate==4);
    g=AW_AnimMoveGroup(&a,2,0,&rate);assert(g==AW_ANIM_WALK && rate==.25f);
    assert(AW_AnimMoveGroup(&a,0,1,&rate)==AW_ANIM_SWIMIDLE);
    assert(AW_AnimMoveGroup(&a,26.25f,1,&rate)==AW_ANIM_SWIM && rate>.99f);

    /* stepping: walk at rate 1, 0.125 s per frame */
    memset(&p,0,sizeof(p));p.group=255;
    f=AW_AnimAdvance(&a,&p,AW_ANIM_WALK,.1f,1,&crossed);assert(f==8 && crossed==1);
    f=AW_AnimAdvance(&a,&p,AW_ANIM_WALK,.125f,1,&crossed);assert(f==9 && crossed==(1UL<<1));
    heard[0]=heard[1]=0;AW_AnimEvents(&a,AW_ANIM_WALK,crossed,emit,NULL);assert(heard[1]==1 && heard[0]==0);
    /* a long step crosses several frames, wrapping the loop */
    f=AW_AnimAdvance(&a,&p,AW_ANIM_WALK,.125f*8,1,&crossed);assert(f==9 && crossed==0xff);
    heard[0]=heard[1]=0;AW_AnimEvents(&a,AW_ANIM_WALK,crossed,emit,NULL);assert(heard[0]==1 && heard[1]==1);
    for(i=0,heard[0]=heard[1]=0;i<80;i++){AW_AnimAdvance(&a,&p,AW_ANIM_WALK,.1f,1,&crossed);AW_AnimEvents(&a,AW_ANIM_WALK,crossed,emit,NULL);}
    assert(heard[0]==8 && heard[1]==8);     /* 8 s, one cycle per second, one step per foot */
    /* double rate: twice the steps */
    for(i=0,heard[0]=heard[1]=0;i<80;i++){AW_AnimAdvance(&a,&p,AW_ANIM_WALK,.1f,2,&crossed);AW_AnimEvents(&a,AW_ANIM_WALK,crossed,emit,NULL);}
    assert(heard[0]==16 && heard[1]==16);
    /* death holds its final pose */
    f=AW_AnimAdvance(&a,&p,AW_ANIM_DEATH,0,1,&crossed);assert(f==39 && !AW_AnimDone(&a,&p));
    f=AW_AnimAdvance(&a,&p,AW_ANIM_DEATH,10,1,&crossed);assert(f==44 && AW_AnimDone(&a,&p));
    f=AW_AnimAdvance(&a,&p,AW_ANIM_DEATH,10,1,&crossed);assert(f==44 && crossed==0);
    /* a missing group plays idle */
    assert(AW_AnimParse(&a,"idle:0:8:0.3",8));
    f=AW_AnimAdvance(&a,&p,AW_ANIM_RUN,.1f,1,&crossed);assert(f==0 && p.group==AW_ANIM_IDLE);
    puts("aga_anim_test: ok");
    return 0;
}
