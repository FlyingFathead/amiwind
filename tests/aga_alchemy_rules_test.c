/* SPDX-License-Identifier: GPL-2.0-or-later
 * Alchemy's rules (aw_alchemy_rules.c, ALCHEMY-61) against the original's rules as OpenMW 0.51 implements them
 * (apps/openmw/mwmechanics/alchemy.cpp, spellutil.cpp rollIngredientEffect): what the skill reveals, the effects the
 * slots share and their order, the potion's magnitude, duration and value with every apparatus setup, the checks
 * before Create, the roll, the weight, eating, the best apparatus. The settings are the masters' values, written here
 * as a fixture (the engine reads them from the image). */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_alchemy.h"

static aw_alchemy_settings_t set;
static void settings(void){
    memset(&set,0,sizeof(set));
    assert(AW_AlchemySetting(&set,"fWortChanceValue",15));
    assert(AW_AlchemySetting(&set,"FPOTIONSTRENGTHMULT",.5f));   /* the game's names, any case */
    assert(AW_AlchemySetting(&set,"iAlchemyMod",2));
    assert(AW_AlchemySetting(&set,"fPotionT1MagMult",1.5f));
    assert(set.loaded!=AW_ALCHEMY_SETTINGS_ALL);
    assert(AW_AlchemySetting(&set,"fPotionT1DurMult",.5f));
    assert(!AW_AlchemySetting(&set,"fWortChance",1));
    assert(set.loaded==AW_ALCHEMY_SETTINGS_ALL && set.alchemy_mod==2 && set.wort==15);
}
/* the magic effects of the fixture: 77 Restore Fatigue (cost 1), 27 Poison (cost 9, harmful), 0 Water Breathing (no
 * magnitude, cost 5), 17 Drain Attribute (cost 1, harmful), 1 Swift Swim (cost 2), 74 Restore Attribute (cost 3) */
static int mgef(void *ctx,int effect,uint32_t *flags,float *cost){
    (void)ctx;
    switch(effect){
    case 77:*flags=0;*cost=1;return 1;
    case 27:*flags=AW_ALCHEMY_MGEF_HARMFUL;*cost=9;return 1;
    case 0:*flags=AW_ALCHEMY_MGEF_NO_MAGNITUDE;*cost=5;return 1;
    case 17:*flags=2|AW_ALCHEMY_MGEF_HARMFUL;*cost=1;return 1;
    case 1:*flags=0;*cost=2;return 1;
    case 74:*flags=2;*cost=3;return 1;
    }
    return 0;
}
static void slot(aw_alchemy_slot_t *s,float weight,int e0,int a0,int e1,int a1,int e2,int a2,int e3,int a3){
    int e[4]={e0,e1,e2,e3},a[4]={a0,a1,a2,a3},i;
    memset(s,0,sizeof(*s));s->used=1;s->weight=weight;
    for(i=0;i<4;i++){s->e[i].effect=(unsigned char)(e[i]<0?AW_ALCHEMY_NO_EFFECT:e[i]);s->e[i].arg=(unsigned char)(a[i]<0?0xFF:a[i]);}
}
#define NO -1,-1

static void visibility(void){
    assert(!AW_AlchemyIngredientVisible(14,15,0));
    assert(AW_AlchemyIngredientVisible(15,15,0) && !AW_AlchemyIngredientVisible(15,15,1));
    assert(AW_AlchemyIngredientVisible(30,15,1) && !AW_AlchemyIngredientVisible(30,15,2));
    assert(AW_AlchemyIngredientVisible(60,15,3) && !AW_AlchemyIngredientVisible(100,15,4));
    assert(!AW_AlchemyPotionVisible(14,15,0));
    assert(AW_AlchemyPotionVisible(15,15,0) && AW_AlchemyPotionVisible(15,15,1) && !AW_AlchemyPotionVisible(15,15,2));
    assert(AW_AlchemyPotionVisible(30,15,3) && !AW_AlchemyPotionVisible(30,15,4));
    assert(AW_AlchemyPotionVisible(60,15,7));
    assert(AW_AlchemyArgKind(79)==1 && AW_AlchemyArgKind(83)==2 && AW_AlchemyArgKind(77)==0);
}
static void shared_effects(void){
    aw_alchemy_slot_t s[4];aw_alchemy_effect_t out[AW_ALCHEMY_OUT];int n;
    memset(s,0,sizeof(s));
    slot(&s[0],.5f,17,2,74,0,1,-1,NO);
    slot(&s[1],.5f,1,-1,17,2,NO,NO);
    slot(&s[2],.5f,74,0,41,-1,17,3,NO);   /* Drain Attribute of another attribute is another effect */
    n=AW_AlchemyListEffects(s,out);
    assert(n==3);
    assert(out[0].effect==17 && out[0].arg==2);   /* slot 1 against 2, in slot 1's order */
    assert(out[1].effect==1 && out[1].arg==0xFF);
    assert(out[2].effect==74 && out[2].arg==0);   /* slot 1 against 3 */
    assert(AW_AlchemyCount(s)==3);
    s[0].used=0;
    n=AW_AlchemyListEffects(s,out);
    assert(n==0);                                  /* 2 and 3 share nothing */
}
static void brew(void){
    aw_alchemy_slot_t s[4];aw_alchemy_effect_t out[AW_ALCHEMY_OUT];float q[4]={.5f,0,0,0};int n,value;
    float factor=AW_AlchemyFactor(50,40,40);
    assert(fabsf(factor-58)<1e-4f);
    memset(s,0,sizeof(s));
    slot(&s[0],.5f,77,-1,NO,NO,NO);slot(&s[1],1,77,-1,NO,NO,NO);
    /* x = 58 x 0.5 x 0.5 = 14.5; value (int)29; magnitude 14.5 / 1.5 = 9.67 -> 10, duration 14.5 / 0.5 = 29 */
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && value==29 && out[0].effect==77 && out[0].magnitude==10 && out[0].duration==29);
    q[AW_APPARATUS_RETORT]=.5f;      /* the retort alone: + 0.5 to each */
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].magnitude==10 && out[0].duration==30);   /* 29.5 rounds up */
    q[AW_APPARATUS_CALCINATOR]=.5f;  /* retort and calcinator: + 2 x 0.5 + 0.5 */
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].magnitude==11 && out[0].duration==31);
    /* a harmful effect: the alembic divides; with the calcinator 2 a + 3 c; the calcinator alone adds */
    slot(&s[0],.5f,27,-1,NO,NO,NO);slot(&s[1],1,27,-1,NO,NO,NO);
    q[AW_APPARATUS_RETORT]=0;q[AW_APPARATUS_CALCINATOR]=0;q[AW_APPARATUS_ALEMBIC]=.5f;
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].magnitude==1 && out[0].duration==2);     /* 1.07 / 1.5, 3.22 / 1.5 */
    q[AW_APPARATUS_ALEMBIC]=0;q[AW_APPARATUS_CALCINATOR]=.5f;
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].magnitude==2 && out[0].duration==4);     /* 1.07 + 0.5, 3.22 + 0.5 */
    q[AW_APPARATUS_ALEMBIC]=.5f;
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==0);                                                  /* 1.07 / 2.5 rounds to 0: no effect kept */
    /* an effect without magnitude: magnitude 1, its duration with the tools (the retort: + quality + 0.5) */
    slot(&s[0],.5f,0,-1,NO,NO,NO);slot(&s[1],1,0,-1,NO,NO,NO);
    q[AW_APPARATUS_ALEMBIC]=0;q[AW_APPARATUS_CALCINATOR]=0;q[AW_APPARATUS_RETORT]=.5f;
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].magnitude==1 && out[0].duration==7);     /* 29 / 5 = 5.8, + 1.0 -> 6.8 -> 7 */
    /* no mortar, or one ingredient: no potion */
    q[AW_APPARATUS_MORTAR]=0;
    assert(AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value)==-1);
    q[AW_APPARATUS_MORTAR]=1;s[1].used=0;
    assert(AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value)==-1);
    /* an effect whose record is unknown is left out */
    slot(&s[0],.5f,99,-1,77,-1,NO,NO);slot(&s[1],1,99,-1,77,-1,NO,NO);
    n=AW_AlchemyBrew(&set,s,q,factor,mgef,NULL,out,&value);
    assert(n==1 && out[0].effect==77);
}
static void checks(void){
    aw_alchemy_slot_t s[4];float q[4]={0,0,0,0};
    memset(s,0,sizeof(s));
    slot(&s[0],.5f,77,-1,NO,NO,NO);
    assert(AW_AlchemyReady(s,q)==AW_ALCHEMY_NO_MORTAR);
    q[0]=.5f;
    assert(AW_AlchemyReady(s,q)==AW_ALCHEMY_TOO_FEW);
    slot(&s[1],1,1,-1,NO,NO,NO);
    assert(AW_AlchemyReady(s,q)==AW_ALCHEMY_NO_EFFECTS);
    slot(&s[1],1,77,-1,NO,NO,NO);
    assert(AW_AlchemyReady(s,q)==AW_ALCHEMY_OK);
    assert(fabsf(AW_AlchemyWeight(s)-.75f)<1e-6f);
    assert(AW_AlchemySucceeds(58,58,1) && !AW_AlchemySucceeds(58,59,1) && !AW_AlchemySucceeds(100,0,0));
}
static void eat(void){
    unsigned short m=0,d=0;
    /* x = 30 + 0.2 x 50 + 0.1 x 40 = 44 */
    assert(!AW_AlchemyEat(30,50,40,1,45,0,1,&m,&d));
    assert(AW_AlchemyEat(30,50,40,1,22,0,1,&m,&d) && d==5 && m==2);            /* y = 22 / 44 x 11 = 5.5 */
    assert(AW_AlchemyEat(30,50,40,1,22,0,10,&m,&d) && d==5 && m==1);           /* at least 1 */
    assert(AW_AlchemyEat(30,50,40,1,22,AW_ALCHEMY_MGEF_NO_DURATION,5,&m,&d) && d==1 && m==11);   /* 5.5 / 0.5 */
    assert(AW_AlchemyEat(30,50,40,1,22,AW_ALCHEMY_MGEF_NO_MAGNITUDE,1,&m,&d) && d==5 && m==1);
    assert(AW_AlchemyEat(100,100,100,1,99,0,1,&m,&d) && d==32);                /* x 130 > 100: y = 0.99 x 32.5 */
    assert(!AW_AlchemyEat(30,50,40,.5f,23,0,1,&m,&d));                         /* tired: x 22 */
}
static void tools(void){
    int type[4]={0,0,3,2},best[4];float quality[4]={.5f,1.5f,1,.5f},q[4];
    AW_AlchemyBestTools(type,quality,4,q,best);
    assert(best[0]==1 && q[0]==1.5f && best[1]==-1 && q[1]==0 && best[2]==3 && best[3]==2 && q[3]==1);
}
int main(void){
    settings();visibility();shared_effects();brew();checks();eat();tools();
    puts("alchemy rules: ok");
    return 0;
}
