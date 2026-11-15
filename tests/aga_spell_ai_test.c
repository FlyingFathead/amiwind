/* SPDX-License-Identifier: GPL-2.0-or-later
 * NPC-NO-SPELLCASTING-65: a fighter's choice between its weapon and its spells (aw_cast.h AW_SpellAi*, rules
 * from OpenMW 0.51 aicombataction.cpp prepareNextAction, spellpriority.cpp rateSpell / rateEffect, weaponpriority.cpp
 * rateWeapon, spellutil.cpp calcEffectCost). Built with aw_cast_rules.c and aw_effects.c only. */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../engine/aga/src/aw_cast.h"

static int failures,checks;
#define CHECK(c) do{checks++;if(!(c)){printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#c);failures++;}}while(0)
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<1e-3)

static float summon_on,enemy_resist;static int spell_on_enemy=-1;
static float has(void *ctx,int who,int effect){(void)ctx;return who==0 && effect==102?summon_on:0;}
static float resist(void *ctx,int effect){(void)ctx;(void)effect;return enemy_resist;}
static int active(void *ctx,int who,int spell){(void)ctx;return who==1 && spell==spell_on_enemy;}
/* the effects a Dispel or a cure would remove: [who][negative] for spells (effect -1), poison and paralysis on itself */
static int dispel_count[2][2],poisoned,paralyzed;static float bound_on[6];
static int dispel(void *ctx,int who,int effect,int negative){
    (void)ctx;
    if(effect==27)return who==0 && negative?poisoned:0;
    if(effect==45)return who==0 && negative?paralyzed:0;
    return effect<0?dispel_count[who][negative!=0]:0;
}
static float has_bound(void *ctx,int who,int effect){(void)ctx;return who==0 && effect>=120 && effect<=125?bound_on[effect-120]:has(ctx,who,effect);}

static void effect(aw_spell_effect_t *e,aw_mgef_t *m,int id,int range,int lo,int hi,int dur,float base,unsigned flags){
    memset(e,0,sizeof(*e));memset(m,0,sizeof(*m));
    e->effect=(int16_t)id;e->range=(unsigned char)range;e->magnitude_min=(unsigned short)lo;e->magnitude_max=(unsigned short)hi;
    e->duration=(unsigned short)dur;e->skill=-1;e->attribute=-1;m->base_cost=base;m->flags=flags;
}

int main(void) {
    aw_spell_ai_t c;aw_spell_effect_t e[2];aw_mgef_t m[2];float r,weapon;int i;
    static const unsigned char sword[3][2]={{5,9},{6,12},{3,9}};   /* chop, slash, thrust */
    static const unsigned char fists[3][2]={{0,0},{0,0},{0,0}};
    memset(&c,0,sizeof(c));
    c.npc=1;c.health=c.health_max=100;c.fatigue=c.fatigue_max=100;c.enemy=1;c.enemy_npc=1;c.enemy_ready=1;
    for(i=0;i<8;i++)c.enemy_attributes[i]=40;
    for(i=0;i<27;i++){c.enemy_skills[i]=30;c.skills[i]=30;}
    c.enemy_magicka=50;c.has=has;c.resist=resist;c.active=active;
    c.spell_mult=3;c.range_spell_mult=5;c.effect_cost_mult=.5f;c.inviso_mult=.2f;

    /* calcEffectCost: fire 10-20 for 1 s, base 5: 0.5 x 30 x 0.5 x 1 x 0.5 = 3.75 */
    effect(&e[0],&m[0],14,AW_RANGE_TARGET,10,20,1,5,AW_MGEF_HARMFUL);
    CHECK(NEAR(AW_SpellAiEffectCost(&e[0],&m[0],.5f),3.75f));
    /* a harmful effect on the enemy rates its cost; x fAIRangeMagicSpellMult 5 x the chance 80 % = 15 */
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[0],&m[0]),3.75f));
    r=AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_SPELL,e,m,1,80);
    CHECK(NEAR(r,15.0f));
    /* no chance, a power, a spell still on the enemy, a full resistance, a target under water: 0 */
    CHECK(AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_SPELL,e,m,1,0)==0);
    CHECK(AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_POWER,e,m,1,80)==0);
    spell_on_enemy=7;CHECK(AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_SPELL,e,m,1,80)==0);spell_on_enemy=-1;
    enemy_resist=100;CHECK(AW_SpellAiRateEffect(&c,&e[0],&m[0])==0);enemy_resist=50;
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[0],&m[0]),1.875f));enemy_resist=0;
    c.enemy_underwater=1;CHECK(AW_SpellAiRateEffect(&c,&e[0],&m[0])==0);c.enemy_underwater=0;
    /* the same harmful effect on itself rates below 0 */
    e[0].range=AW_RANGE_SELF;CHECK(AW_SpellAiRateEffect(&c,&e[0],&m[0])<0);e[0].range=AW_RANGE_TARGET;

    /* the weapon (rateWeapon): means 7, 9, 6: (49 + 81 + 36) / 22 = 7.545 x hit 0.7 x speed 1.25 x 2 = 13.20 */
    weapon=AW_SpellAiRateWeapon(sword,1,1,70,1.25f,30,2);
    CHECK(NEAR(weapon,166.0f/22*.7f*1.25f*2));
    /* the choice: the fire bolt at 80 % (15) beats the sword (13.2); at 60 % (11.25) the sword stays */
    CHECK(AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_SPELL,e,m,1,80)>weapon);
    CHECK(AW_SpellAiRateSpell(&c,7,AW_SPELL_TYPE_SPELL,e,m,1,60)<weapon);
    /* hand to hand and a weapon skill of 0 rate 0: any useful spell wins */
    CHECK(AW_SpellAiRateWeapon(fists,1,1,70,1,30,2)==0 && AW_SpellAiRateWeapon(sword,1,1,70,1,0,2)==0);
    /* the hit chance is clamped to 0.01 .. 1 */
    CHECK(NEAR(AW_SpellAiRateWeapon(sword,1,1,0,1,30,2),166.0f/22*.01f*2));

    /* never cast: Light, Levitate, the fortify effects, the resistances */
    effect(&e[1],&m[1],41,AW_RANGE_SELF,10,10,30,1,0);CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    e[1].effect=10;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    e[1].effect=80;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    e[1].effect=90;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    /* a summon on itself: 3 x its cost (no magnitude: 1; 30 s; base 10: 0.5 x 2 x 1 x 30 x 0.5 = 15) = 45; none while
     * one stands by */
    effect(&e[1],&m[1],102,AW_RANGE_SELF,0,0,30,10,AW_MGEF_NO_MAGNITUDE);
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),45.0f));
    summon_on=1;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);summon_on=0;
    /* Restore Health on itself: below 0 at full health, above 0 when hurt */
    effect(&e[1],&m[1],75,AW_RANGE_SELF,10,10,1,5,0);
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])<0);
    c.health=20;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])>0);c.health=100;
    /* Blind only on an enemy with its weapon ready; Silence only on one with magic ready */
    effect(&e[1],&m[1],47,AW_RANGE_TARGET,10,10,10,1,AW_MGEF_HARMFUL);
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])>0);
    c.enemy_ready=2;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    e[1].effect=46;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])>0);
    c.enemy_ready=1;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    /* no enemy: nothing aimed at one */
    c.enemy=0;CHECK(AW_SpellAiRateEffect(&c,&e[0],&m[0])==0);c.enemy=1;
    /* two effects sum: fire on target (3.75 x 5) and a summon on itself (45 x 3), at 100 % */
    effect(&e[1],&m[1],102,AW_RANGE_SELF,0,0,30,10,AW_MGEF_NO_MAGNITUDE);
    CHECK(NEAR(AW_SpellAiRateSpell(&c,8,AW_SPELL_TYPE_SPELL,e,m,2,100),3.75f*5+45*3));
    /* the range it casts from: a touch spell from fCombatDistance 128; others 4 x 128 x max(2, reach 1) = 1024 */
    CHECK(NEAR(AW_SpellAiCombatRange(1<<AW_RANGE_TOUCH,128,1),128));
    CHECK(NEAR(AW_SpellAiCombatRange(1<<AW_RANGE_TARGET,128,1),1024));
    CHECK(NEAR(AW_SpellAiCombatRange(1<<AW_RANGE_SELF,128,3),1536));

    /* v0.0.66: the kinds that rated 0 before, as OpenMW 0.51 spellpriority.cpp rates them */
    c.dispel=dispel;c.magicka=c.magicka_max=100;
    /* Burden (7) on the enemy: 3 x its cost when its mean magnitude overburdens the enemy (load 200 of 250: 50 left) */
    effect(&e[1],&m[1],7,AW_RANGE_TARGET,40,80,10,1,AW_MGEF_HARMFUL);
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);                  /* no inventory known */
    c.enemy_inventory=1;c.enemy_encumbrance=200;c.enemy_capacity=250;
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),3*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    e[1].magnitude_max=40;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);   /* mean 40: not enough */
    e[1].magnitude_max=80;c.enemy_encumbrance=260;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);   /* overburdened already */
    /* Feather (8) on itself: only when overburdened, and enough to lift it */
    effect(&e[1],&m[1],8,AW_RANGE_SELF,20,20,10,1,0);
    c.inventory=1;c.encumbrance=100;c.capacity=200;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    c.encumbrance=215;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),3*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    c.encumbrance=230;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    c.inventory=0;c.encumbrance=215;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);c.encumbrance=0;
    /* Dispel (57) on itself: (harmful - helpful) / 5 x its cost; none when it would lose more than it gains */
    effect(&e[1],&m[1],57,AW_RANGE_SELF,50,50,1,5,0);
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    dispel_count[0][1]=3;dispel_count[0][0]=1;
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),2/5.0f*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    dispel_count[0][0]=3;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);dispel_count[0][0]=dispel_count[0][1]=0;
    /* on the enemy: its helpful effects over its harmful ones */
    e[1].range=AW_RANGE_TOUCH;dispel_count[1][0]=4;dispel_count[1][1]=1;
    CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),3/5.0f*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    c.enemy=0;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);c.enemy=1;dispel_count[1][0]=dispel_count[1][1]=0;
    /* the cures: 1001 for each such effect on itself, before Dispel; the disease cures never */
    effect(&e[1],&m[1],72,AW_RANGE_SELF,0,0,0,5,AW_MGEF_NO_MAGNITUDE);
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);poisoned=2;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),2002));poisoned=0;
    e[1].effect=73;paralyzed=1;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),1001));paralyzed=0;
    e[1].effect=69;poisoned=1;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);poisoned=0;
    /* Restore Magicka (76) on itself: priority 2 with a spell it cannot pay now (the restore formula), else below 0 */
    effect(&e[1],&m[1],76,AW_RANGE_SELF,20,20,1,5,0);
    c.magicka=10;c.magicka_need=0;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])<0);
    c.magicka_need=2;r=AW_SpellAiRateEffect(&c,&e[1],&m[1]);
    /* (2-1)/2 x (0.9+0.6)^4 + 2 x 20 / 100 - 0.5 = 2.53125 + 0.4 - 0.5 */
    CHECK(NEAR(r,(.5f*1.5f*1.5f*1.5f*1.5f+.4f-.5f)*AW_SpellAiEffectCost(&e[1],&m[1],.5f)) && r>0);
    /* Absorb Magicka (87) on an enemy with no magicka left: 0.5 x the need, as a harmful effect on the enemy */
    effect(&e[1],&m[1],87,AW_RANGE_TOUCH,10,10,1,5,AW_MGEF_HARMFUL);
    c.enemy_magicka=0;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),1.0f*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    c.magicka_need=0;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    c.enemy_magicka=50;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    c.magicka=c.magicka_max=100;
    /* the bound longbow (125): only with arrows, 2 x (50 + Marksman) / 100 x its cost; not while a bound weapon is out */
    effect(&e[1],&m[1],125,AW_RANGE_SELF,0,0,60,2,AW_MGEF_NO_MAGNITUDE);c.has=has_bound;
    CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);
    c.ammo=1;c.skills[23]=50;CHECK(NEAR(AW_SpellAiRateEffect(&c,&e[1],&m[1]),2*1.0f*AW_SpellAiEffectCost(&e[1],&m[1],.5f)));
    bound_on[0]=1;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);bound_on[0]=0;   /* a bound dagger out */
    /* a bound bow out: a bound dagger only while there are arrows (OpenMW's code) */
    bound_on[5]=1;c.ammo=1;e[1].effect=120;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])>0);
    c.ammo=0;CHECK(AW_SpellAiRateEffect(&c,&e[1],&m[1])==0);bound_on[5]=0;c.has=has;
    if(failures)return 1;
    printf("spell ai: %d checks passed\n",checks);
    return 0;
}
