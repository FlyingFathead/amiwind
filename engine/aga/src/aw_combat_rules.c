/* SPDX-License-Identifier: GPL-2.0-or-later
 * Melee rules as pure functions (aw_combat.h, docs/COMBAT.md). No engine
 * state: host tests run them as they are. Each step names the function of
 * the reference implementation it follows (OpenMW 0.51, see aw_combat.h).
 * All rolls come from the encounter's own generator, so a seed replays a
 * fight swing for swing.
 */
#include <string.h>
#include "aw_combat.h"

static const char *const names[AW_COMBAT_SETTING_COUNT]={
    "fFatigueBase","fFatigueMult","fCombatDistance","fHandToHandReach",
    "fMinHandToHandMult","fMaxHandToHandMult","fHandtoHandHealthPer",
    "fDamageStrengthBase","fDamageStrengthMult","fCombatArmorMinMult","fCombatKODamageMult",
    "fCombatCriticalStrikeMult","fKnockDownMult","iKnockDownOddsBase","iKnockDownOddsMult",
    "fFatigueAttackBase","fFatigueAttackMult","fWeaponFatigueMult",
    "fFatigueReturnBase","fFatigueReturnMult","fUnarmoredBase1","fUnarmoredBase2",
    "iBlockMinChance","iBlockMaxChance","fSwingBlockBase","fSwingBlockMult","fBlockStillBonus",
    "fFatigueBlockBase","fFatigueBlockMult","fWeaponFatigueBlockMult",
    "fCombatBlockLeftAngle","fCombatBlockRightAngle","fCombatDelayNPC",
    "fNPCHealthBarTime","fNPCHealthBarFade","fWeaponDamageMult"
};
/* The struct holds the floats in the order of names[]. */
const char *AW_CombatSettingName(int index) {
    return index>=0 && index<AW_COMBAT_SETTING_COUNT?names[index]:0;
}
int AW_CombatSettingIndex(const char *name) {
    int i;
    for(i=0;i<AW_COMBAT_SETTING_COUNT;i++){
        const char *a=names[i],*b=name;
        while(*a && (*a|32)==(*b|32)){a++;b++;}
        if(!*a && !*b)return i;
    }
    return -1;
}
int AW_CombatSettingSet(aw_combat_settings_t *s,const char *name,float value) {
    int i=AW_CombatSettingIndex(name);
    if(i<0)return 0;
    ((float *)s)[i]=value;return 1;
}

/* xorshift32: 4 bytes of state, no multiply; a zero seed is remapped. */
void AW_CombatSeed(aw_combat_rng_t *r,unsigned long seed) {
    r->state=(seed&0xffffffffUL)?seed&0xffffffffUL:0x9e3779b9UL;
}
static unsigned long next(aw_combat_rng_t *r) {
    unsigned long x=r->state;
    x^=(x<<13)&0xffffffffUL;x^=x>>17;x^=(x<<5)&0xffffffffUL;
    r->state=x;return x;
}
int AW_CombatRoll100(aw_combat_rng_t *r) {return (int)((next(r)>>8)%100);}
float AW_CombatRoll01(aw_combat_rng_t *r) {return (float)((next(r)>>8)&0xffff)/65535.0f;}

static int rounded(float x) {return x>=0?(int)(x+.5f):-(int)(-x+.5f);}
static float clampf(float x,float lo,float hi) {return x<lo?lo:x>hi?hi:x;}

/* CreatureStats::getFatigueTerm */
float AW_CombatFatigueTerm(const aw_combat_settings_t *s,const aw_fighter_t *f) {
    float normal=1;
    if((int)f->fatigue_max!=0){normal=f->fatigue/f->fatigue_max;if(normal<0)normal=0;}
    return s->fFatigueBase-s->fFatigueMult*(1-normal);
}
static int skill_of(const aw_fighter_t *f) {
    return f->skills[f->weapon?f->weapon_skill:AW_SK_H2H];
}
/* getHitChance: attack term minus the victim's evasion (none while knocked
 * down or unaware; none at all below zero fatigue). Not clamped. */
int AW_CombatHitChance(const aw_combat_settings_t *s,const aw_fighter_t *a,const aw_fighter_t *v) {
    float defense=0,attack;
    if(v->fatigue>=0 && !v->knocked && v->aware)
        defense=(v->attributes[AW_AGI]/5.0f+v->attributes[AW_LUC]/10.0f)*AW_CombatFatigueTerm(s,v);
    attack=(skill_of(a)+a->attributes[AW_AGI]/5.0f+a->attributes[AW_LUC]/10.0f)*AW_CombatFatigueTerm(s,a);
    return rounded(attack-defense);
}
/* AiCombat chooseBestAttack: a damage-weighted pick of slash/thrust/chop. */
int AW_CombatBestAttack(const aw_fighter_t *f,aw_combat_rng_t *r) {
    int chop,slash,thrust;float roll;
    if(!f->weapon)return AW_CombatRoll100(r)%3;
    chop=(f->damage[0][0]+f->damage[0][1])/2;slash=(f->damage[1][0]+f->damage[1][1])/2;
    thrust=(f->damage[2][0]+f->damage[2][1])/2;
    roll=AW_CombatRoll01(r)*(float)(slash+chop+thrust);
    if(roll<=slash)return AW_ATTACK_SLASH;
    if(roll<=slash+thrust)return AW_ATTACK_THRUST;
    return AW_ATTACK_CHOP;
}
/* getMeleeWeaponReach */
float AW_CombatReach(const aw_combat_settings_t *s,const aw_fighter_t *f) {
    return s->fCombatDistance*(f->weapon?f->reach:s->fHandToHandReach);
}
/* Npc::getArmorRating with nothing worn: every slot unarmoured; the slot
 * weights (0.3 + 6 x 0.1 + 2 x 0.05) add up to one. */
float AW_CombatUnarmoredRating(const aw_combat_settings_t *s,const aw_fighter_t *f) {
    float u=f->skills[AW_SK_UNARMORED];
    return (s->fUnarmoredBase1*u)*(s->fUnarmoredBase2*u);
}
int aw_combat_dice=1;
/* Player attack type (character.cpp getMovementBasedAttackType): forward/back
 * beats sideways by 0.2 = thrust, sideways = slash, else chop. Inputs -1..1. */
int AW_CombatMovementAttack(float forward,float side) {
    float f=forward<0?-forward:forward,sd=side<0?-side:side;
    if(f>sd+.2f)return AW_ATTACK_THRUST;
    if(sd>f+.2f)return AW_ATTACK_SLASH;
    return AW_ATTACK_CHOP;
}
/* "Always use best attack" (character.cpp getBestAttack): the highest min+max;
 * all equal = slash; thrust wins ties with the others, then slash. */
int AW_CombatBestAttackPlayer(const aw_fighter_t *f) {
    int slash=f->damage[1][0]+f->damage[1][1],chop=f->damage[0][0]+f->damage[0][1],thrust=f->damage[2][0]+f->damage[2][1];
    if(!f->weapon)return AW_ATTACK_CHOP;               /* no best attack for hand to hand */
    if(slash==chop && slash==thrust)return AW_ATTACK_SLASH;
    if(thrust>=chop && thrust>=slash)return AW_ATTACK_THRUST;
    if(slash>=chop && slash>=thrust)return AW_ATTACK_SLASH;
    return AW_ATTACK_CHOP;
}
/* Can the victim block at all: a shield with a one-handed weapon (fists and
 * two-handed weapons hide it), facing the attacker, not down, staggered,
 * swinging or dead (combat.cpp blockMeleeAttack, npcanimation.cpp). */
int AW_CombatCanBlock(const aw_combat_settings_t *s,const aw_fighter_t *v,float angle) {
    if(!v->shield || AW_TWO_HANDED(v->weapon) || v->knocked || v->staggered || v->attacking || v->dead)return 0;
    return angle>=s->fCombatBlockLeftAngle && angle<=s->fCombatBlockRightAngle;
}
static float ratio(float now,float most) {return most>0?(now>0?now/most:0):1;}
/* blockMeleeAttack: the chance, the roll, the blocker's fatigue, the shield's wear. */
static int blocks(const aw_combat_settings_t *s,aw_fighter_t *a,aw_fighter_t *v,float strength,float angle,
                  int still,float damage,aw_combat_rng_t *r,aw_swing_t *out) {
    float blocker,attacker;int x;
    if(!AW_CombatCanBlock(s,v,angle))return 0;
    blocker=(v->skills[AW_SK_BLOCK]+.2f*v->attributes[AW_AGI]+.1f*v->attributes[AW_LUC])*
        (strength*s->fSwingBlockMult+s->fSwingBlockBase);
    if(still)blocker*=s->fBlockStillBonus;
    blocker*=AW_CombatFatigueTerm(s,v);
    attacker=(skill_of(a)+.2f*a->attributes[AW_AGI]+.1f*a->attributes[AW_LUC])*AW_CombatFatigueTerm(s,a);
    x=(int)(blocker-attacker);
    if(x<(int)s->iBlockMinChance)x=(int)s->iBlockMinChance;
    if(x>(int)s->iBlockMaxChance)x=(int)s->iBlockMaxChance;
    out->block_chance=x;out->blocked_roll=AW_CombatRoll100(r);
    if(out->blocked_roll>=x)return 0;
    v->fatigue-=s->fFatigueBlockBase+(a->weapon?a->weight*strength*s->fWeaponFatigueBlockMult:0);
    if(v->shield_health_max>0){
        v->shield_health-=v->shield_health<(int)damage?v->shield_health:(int)damage;
        if(v->shield_health<=0){v->shield_health=0;v->shield=0;out->shield_broke=1;}  /* unequipped */
    }
    return 1;
}
/* reduceWeaponCondition: max(1, fWeaponDamageMult x damage); a miss in reach costs 1. */
static void wear(const aw_combat_settings_t *s,aw_fighter_t *a,float damage,aw_swing_t *out) {
    float x;
    if(!a->weapon || a->weapon_health_max<=0)return;
    x=s->fWeaponDamageMult*damage;if(x<1)x=1;
    x=(float)(int)x;
    if(x>a->weapon_health)x=a->weapon_health;
    a->weapon_health-=x;out->weapon_wear=x;
    if(a->weapon_health<=0){a->weapon_health=0;a->weapon=0;a->weapon_skill=AW_SK_H2H;out->weapon_broke=1;}
}
void AW_CombatSwing(const aw_combat_settings_t *s,aw_fighter_t *a,aw_fighter_t *v,int attack,float strength,
                    float angle,int still,aw_combat_rng_t *r,aw_swing_t *out) {
    float d,agility;int health;
    memset(out,0,sizeof(*out));out->strength=strength=clampf(strength,0,1);out->blocked_roll=-1;
    /* applyFatigueLoss: every swing, hit or miss (no encumbrance yet). */
    a->fatigue-=s->fFatigueAttackBase+(a->weapon?a->weight*strength*s->fWeaponFatigueMult:0);
    if(v->dead){out->outcome=AW_HIT_MISS;out->roll=-1;return;}
    out->chance=AW_CombatHitChance(s,a,v);
    out->roll=aw_combat_dice?AW_CombatRoll100(r):-2;      /* dice off: every swing in reach hits */
    if(aw_combat_dice && out->roll>=out->chance){
        out->outcome=AW_HIT_MISS;wear(s,a,0,out);
        out->miss_style=AW_CombatCanBlock(s,v,angle)?2:1;
        return;
    }
    if(a->weapon){
        /* Npc::hit + adjustWeaponDamage: condition ratio, strength modifier */
        int lo=a->damage[attack][0],hi=a->damage[attack][1];
        d=(lo+(hi-lo)*strength)*ratio(a->weapon_health,a->weapon_health_max)*
            (s->fDamageStrengthBase+a->attributes[AW_STR]*s->fDamageStrengthMult*.1f);
        wear(s,a,d,out);
        health=1;
    }else{
        /* getHandToHandDamage: fatigue damage unless the victim is down
         * (strength does not count: the original rule, OpenMW's default) */
        d=a->skills[AW_SK_H2H]*(s->fMinHandToHandMult+(s->fMaxHandToHandMult-s->fMinHandToHandMult)*strength);
        health=v->knocked!=0;
        if(health)d*=s->fHandtoHandHealthPer;
    }
    out->raw=d;
    if(!v->aware){d*=s->fCombatCriticalStrikeMult;out->critical=1;}
    if(v->knocked)d*=s->fCombatKODamageMult;
    if(aw_combat_dice && blocks(s,a,v,strength,angle,still,d,r,out)){out->outcome=AW_HIT_BLOCKED;out->damage=0;return;}
    if(health && d>0){
        /* combat/local.lua adjustDamageForArmor, at least 1 */
        float x=d/(d+v->armor);
        d*=x>s->fCombatArmorMinMult?x:s->fCombatArmorMinMult;
        if(d<1)d=1;
    }
    out->damage=d;out->outcome=health?AW_HIT_HEALTH:AW_HIT_FATIGUE;
    if(health)v->health-=d;else v->fatigue-=d;
    /* Npc::onHit knockdown check (health damage only) */
    if(d>=.001f){
        agility=v->attributes[AW_AGI];
        if(health && agility*s->fKnockDownMult<=d &&
           (!aw_combat_dice || agility*s->iKnockDownOddsMult*.01f+s->iKnockDownOddsBase<=AW_CombatRoll100(r))){
            if(!v->knocked)v->knocked=1;
            out->knockdown=1;
        }
    }
    if(v->health<=0){v->health=0;v->dead=1;v->knocked=0;}
    else if(v->fatigue<0)v->knocked=2;
}
/* Actors::calculateRestoration (fatigue only) */
int AW_CombatRecover(const aw_combat_settings_t *s,aw_fighter_t *f,float seconds) {
    if(f->dead || seconds<=0)return 0;
    if(f->fatigue<f->fatigue_max){
        f->fatigue+=seconds*(s->fFatigueReturnBase+s->fFatigueReturnMult*f->attributes[AW_END]);
        if(f->fatigue>f->fatigue_max)f->fatigue=f->fatigue_max;
    }
    if(f->knocked==2 && f->fatigue>=0){f->knocked=0;return 1;}
    return 0;
}
