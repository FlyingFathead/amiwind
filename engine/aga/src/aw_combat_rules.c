/* SPDX-License-Identifier: GPL-2.0-or-later
 * Melee rules as pure functions (aw_combat.h, docs/COMBAT.md). No engine
 * state: host tests run them as they are. Each step names the function of
 * the reference implementation it follows (OpenMW 0.51, see aw_combat.h).
 * All rolls come from the encounter's own generator, so a seed replays a
 * fight swing for swing.
 */
#include <string.h>
#include <math.h>
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
    "fNPCHealthBarTime","fNPCHealthBarFade","fWeaponDamageMult",
    "fCombatAngleXY","fCombatAngleZ","fCombatInvisoMult"
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
 * down or unaware; none at all below zero fatigue). Not clamped.
 * HIT-CHANCE-CHECK-62: with the effects as OpenMW 0.51 counts them: the evasion holds Sanctuary (getEvasion, at most
 * 100), the Chameleon and Invisibility defence counts whenever the victim's fatigue is not below 0, and the attack term
 * gains Fortify Attack and loses Blind after the fatigue factor. */
int AW_CombatHitChance(const aw_combat_settings_t *s,const aw_fighter_t *a,const aw_fighter_t *v) {
    float defense=0,attack;
    if(v->fatigue>=0){
        if(!v->knocked && v->aware)
            defense=(v->attributes[AW_AGI]/5.0f+v->attributes[AW_LUC]/10.0f)*AW_CombatFatigueTerm(s,v)+
                    (v->sanctuary<100?v->sanctuary:100);
        defense+=v->unseen;
    }
    attack=(skill_of(a)+a->attributes[AW_AGI]/5.0f+a->attributes[AW_LUC]/10.0f)*AW_CombatFatigueTerm(s,a)+a->attack_mod;
    return rounded(attack-defense);
}
unsigned char AW_CombatUnseen(const aw_combat_settings_t *s,float chameleon,float invisibility) {
    float c=s->fCombatInvisoMult*(chameleon>0?chameleon:0),i=s->fCombatInvisoMult*(invisibility>0?invisibility:0);
    if(!(c==c))c=0;
    if(!(i==i))i=0;
    return (unsigned char)rounded((c<100?c:100)+(i<100?i:100));
}
/* getHitContact for the player (one candidate; the caller keeps the nearest): isInMeleeReach, in front, the side
 * angle by the perp dot product's sine, the vertical tolerance at the feet and the head. */
int AW_CombatContact(const aw_combat_settings_t *s,const float to[3],float eye,float height,float gap,float dz,
                     float reach,float dz_extra,const float forward[3]) {
    float xy=(float)sqrt(to[0]*to[0]+to[1]*to[1]),fxy=(float)sqrt(forward[0]*forward[0]+forward[1]*forward[1]);
    float ux,uy,fx,fy,feet[3],head[3],n,angle_z=s->fCombatAngleZ/90.0f;
    if(!(gap<reach) || !(dz<reach+dz_extra && dz>-reach-dz_extra))return 0;
    if(xy<.001f)return 1;                                  /* right over the attacker's feet: in front of it */
    if(fxy<.001f)return 0;
    ux=to[0]/xy;uy=to[1]/xy;fx=forward[0]/fxy;fy=forward[1]/fxy;
    if(ux*fx+uy*fy<=0)return 0;                            /* behind */
    n=ux*fy-uy*fx;if((n<0?-n:n)>s->fCombatAngleXY/90.0f)return 0;
    feet[0]=head[0]=to[0];feet[1]=head[1]=to[1];feet[2]=to[2]-eye;head[2]=feet[2]+height;
    n=(float)sqrt(feet[0]*feet[0]+feet[1]*feet[1]+feet[2]*feet[2]);if(n>0)feet[2]/=n;
    n=(float)sqrt(head[0]*head[0]+head[1]*head[1]+head[2]*head[2]);if(n>0)head[2]/=n;
    if(forward[2]-head[2]>angle_z || forward[2]-feet[2]<-angle_z)return 0;
    return 1;
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
 * two-handed weapons hide it), ready to block (block_off: the player not guarding
 * under the AmiWind held block), facing the attacker, not down, staggered,
 * swinging or dead (combat.cpp blockMeleeAttack, npcanimation.cpp). */
int AW_CombatCanBlock(const aw_combat_settings_t *s,const aw_fighter_t *v,float angle) {
    if(!v->shield || v->block_off || AW_TWO_HANDED(v->weapon) || v->knocked || v->staggered || v->attacking || v->dead)return 0;
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
/* GODMODE-COMBAT-DAMAGE-61 (OpenMW 0.51 npc.cpp hit/onHit, combat.cpp applyFatigueLoss and reduceWeaponCondition): a
 * god-mode player takes no damage and is not knocked down by a blow, and the player's own swings cost no fatigue and
 * wear no weapon. The swing was resolved on the sheets as usual; these put back what god mode keeps. */
void AW_CombatGodVictim(aw_fighter_t *v,const aw_fighter_t *before,aw_swing_t *out) {
    v->health=before->health;v->fatigue=before->fatigue;v->knocked=before->knocked;v->dead=before->dead;
    if(out){out->damage=0;out->knockdown=0;}
}
void AW_CombatGodAttacker(aw_fighter_t *a,const aw_fighter_t *before,aw_swing_t *out) {
    a->fatigue=before->fatigue;a->weapon_health=before->weapon_health;
    a->weapon=before->weapon;a->weapon_skill=before->weapon_skill;
    if(out){out->weapon_wear=0;out->weapon_broke=0;}
}
/* GODMODE-LAVA-DEATH-62: world damage (lava, a fall, drowning) to a god-mode player is held back (1, and added to
 * *HELD); 0: it lands. */
int AW_CombatGodWorldDamage(int god,float damage,float *held) {
    if(!god || !(damage>0))return 0;
    if(held)*held+=damage;
    return 1;
}
/* GODMODE-LAVA-DEATH-62: the player's health after a change of a script or a spell effect (SetHealth, ModCurrentHealth,
 * Damage Health, poison, the elements): in god mode it never falls below BEFORE (a heal still lands); MAXIMUM caps
 * what is kept when the maximum itself fell (never below 1); MAXIMUM 0: the maximum did not fall, nothing is capped.
 * Not in god mode: AFTER as it is. */
float AW_CombatGodHealth(int god,float before,float after,float maximum) {
    if(!god || !(after<before))return after;
    if(maximum>0 && before>maximum)before=maximum<1?1:maximum;
    return after>before?after:before;
}
int AW_CombatIsNormalWeapon(int flags,int enchanted) {
    return !(flags&(AW_WEAPON_MAGICAL|AW_WEAPON_SILVER)) && !enchanted;
}
float AW_CombatNormalWeaponFactor(int normal,float resist,int *no_effect) {
    if(no_effect)*no_effect=0;
    if(!normal || !(resist==resist))return 1;
    if(resist>=1){if(no_effect)*no_effect=1;return 0;}
    return 1-resist;                    /* a weakness (resist < 0) makes the blow stronger */
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
        /* OpenMW npc.cpp hit: a miss also passes resistNormalWeapon, so the full resistance is told on a miss too */
        (void)AW_CombatNormalWeaponFactor(a->weapon && a->weapon_normal,v->resist_normal*.01f,&out->no_effect);
        out->miss_style=AW_CombatCanBlock(s,v,angle)?2:1;
        return;
    }
    if(a->weapon){
        /* Npc::hit + adjustWeaponDamage: condition ratio, strength modifier */
        int lo=a->damage[attack][0],hi=a->damage[attack][1];
        d=(lo+(hi-lo)*strength)*ratio(a->weapon_health,a->weapon_health_max)*
            (s->fDamageStrengthBase+a->attributes[AW_STR]*s->fDamageStrengthMult*.1f);
        /* Npc::hit: resistNormalWeapon right after the weapon damage (RESIST-NORMAL-WEAPONS-61); the wear stays the
         * full blow's, as OpenMW wears the weapon before that step */
        wear(s,a,d,out);
        d*=AW_CombatNormalWeaponFactor(a->weapon_normal,v->resist_normal*.01f,&out->no_effect);
        if(out->no_effect)d=0;
        health=1;
    }else if(a->creature==1){
        /* Creature::hit without a weapon: its own attack, min + (max - min) x strength, health damage */
        int lo=a->damage[attack][0],hi=a->damage[attack][1];
        d=lo+(hi-lo)*strength;
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
/* ---- the aggro and flee ratings (aw_combat.h) ---- */
static const char *const ai_names[AW_COMBAT_AI_COUNT]={
    "iFightDistanceBase","fFightDistanceMultiplier","fFightDispMult",
    "fAIFleeHealthMult","fAIFleeFleeMult","fAIMeleeWeaponMult","fAIMeleeArmorMult"
};
const char *AW_CombatAiName(int index) {return index>=0 && index<AW_COMBAT_AI_COUNT?ai_names[index]:0;}
int AW_CombatAiSet(aw_combat_ai_t *a,const char *name,float value) {
    int i;
    for(i=0;i<AW_COMBAT_AI_COUNT;i++){
        const char *x=ai_names[i],*y=name;
        while(*x && (*x|32)==(*y|32)){x++;y++;}
        if(!*x && !*y){((float *)a)[i]=value;return 1;}
    }
    return 0;
}
/* combat.cpp getFightDistanceBias */
static float distance_bias(const aw_combat_ai_t *a,float distance) {
    return a->iFightDistanceBase-a->fFightDistanceMultiplier*distance;
}
/* mechanicsmanagerimp.cpp isAggressive: Fight + static_cast<int>(distance bias + disposition bias) */
int AW_CombatFightRating(const aw_combat_ai_t *a,int fight,int disposition,float distance) {
    return fight+(int)(distance_bias(a,distance)+(50.0f-(float)disposition)*a->fFightDispMult);
}
/* aicombataction.cpp vanillaRateFlee */
float AW_CombatFleeRating(const aw_combat_ai_t *a,const aw_fighter_t *f,float distance) {
    float ratio,rating;
    if(f->flee>=100)return (float)f->flee;
    ratio=f->health_max!=0?f->health/f->health_max:1;
    rating=(1.0f-ratio)*a->fAIFleeHealthMult+f->flee*a->fAIFleeFleeMult;
    if(rating!=0)rating+=distance_bias(a,distance);
    return rating;
}
/* weaponpriority.cpp vanillaRateWeaponAndAmmo (melee); hand to hand: the empty weapon rates 0 */
float AW_CombatAntiFleeRating(const aw_combat_ai_t *a,const aw_fighter_t *f) {
    float skill,best=0;int i;
    if(!f->weapon)return 0;
    skill=f->skills[f->weapon_skill<27?f->weapon_skill:AW_SK_H2H]*.01f;
    for(i=0;i<3;i++)if(f->damage[i][1]*skill*a->fAIMeleeWeaponMult>best)best=f->damage[i][1]*skill*a->fAIMeleeWeaponMult;
    return f->armor*a->fAIMeleeArmorMult+best;
}
/* aicombataction.cpp makeFleeDecision */
int AW_CombatFleeDecision(const aw_combat_ai_t *a,const aw_fighter_t *f,float distance) {
    float rating=AW_CombatFleeRating(a,f,distance);
    if(rating<100.0f)rating=0;
    return rating>AW_CombatAntiFleeRating(a,f);
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

/* aw_combat.h AW_CombatCreatureSheet (OpenMW mwclass/creature.cpp hit, getSkill, getArmorRating). */
int AW_CombatCreatureSheet(const aw_actor_base_t *b,const char *id,aw_fighter_t *o) {
    int i;
    memset(o,0,sizeof(*o));
    if(!b || b->kind!=1 || !b->health || !id || !*id || strlen(id)>=sizeof(o->id))return 0;
    strcpy(o->id,id);strcpy(o->name,id);
    o->level=b->level;
    for(i=0;i<8;i++)o->attributes[i]=(unsigned char)(b->attributes[i]>255?255:b->attributes[i]);
    for(i=0;i<27;i++)o->skills[i]=b->skills[i];
    o->health=o->health_max=b->health;o->fatigue=o->fatigue_max=b->fatigue;o->magicka=b->magicka;
    o->fight=b->fight;o->flee=b->flee;
    o->weapon=0;o->weapon_skill=AW_SK_H2H;
    for(i=0;i<6;i++)o->damage[i/2][i%2]=(unsigned char)(b->attack[i]>255?255:b->attack[i]);
    o->creature=(unsigned char)(b->flags&AWR_BIPEDAL?2:1);
    o->armor=0;o->aware=1;
    return 1;
}
/* local.lua pickRandomArmor: the band each slot ends at (cuirass, helmet, greaves, boots, left and right pauldron,
 * left and right gauntlet, shield). */
int AW_CombatArmorHitSlot(int roll100) {
    static const unsigned char ends[AW_ARMOR_HIT_SLOTS]={30,40,50,60,70,80,85,90,100};
    int i;
    for(i=0;i<AW_ARMOR_HIT_SLOTS-1;i++)if(roll100<ends[i])return i;
    return AW_ARMOR_HIT_SLOTS-1;
}
/* The swing's sounds (aw_combat.h): character.cpp playSwishSound, combat.cpp blockMeleeAttack and
 * getHandToHandDamage, local.lua applyArmor and onHit, npc.cpp hit. The roll is a cosmetic one (not the fight's
 * generator), so a seed still replays a fight. */
int AW_CombatSwingSounds(const aw_swing_t *out,const aw_fighter_t *victim,int by_player,unsigned long roll,int *sounds) {
    int n=0,c;
    sounds[n++]=AW_SND_SWISH;
    if(!out)return n;
    if(out->outcome==AW_HIT_BLOCKED){
        c=victim?victim->shield_class:0;sounds[n++]=AW_SND_LIGHT+(c<=2?c:0);
    }else if(out->outcome==AW_HIT_MISS){
        if(by_player)sounds[n++]=AW_SND_MISS;
    }else if(out->outcome==AW_HIT_FATIGUE){
        sounds[n++]=(roll>>7)&1?AW_SND_PUNCH2:AW_SND_PUNCH;
    }else{
        c=victim?AW_HIT_CLASS(victim,AW_CombatArmorHitSlot((int)(roll%100))):0;
        if(c>=1 && c<=3)sounds[n++]=AW_SND_LIGHT+c-1;
        sounds[n++]=AW_SND_HEALTH;
        if(out->critical)sounds[n++]=AW_SND_CRITICAL;
    }
    return n;
}
