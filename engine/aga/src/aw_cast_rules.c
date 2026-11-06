/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_cast_rules.c: the casting rules, pure (aw_cast.h). No engine headers. */
#include <math.h>
#include "aw_cast.h"
#include "aw_effects.h"

/* the schools' skills in the original's skill order: Alteration 11, Conjuration 13, Destruction 10, Illusion 12,
 * Mysticism 14, Restoration 15 */
int AW_CastSchoolSkill(int school){
    static const int school_skill[AW_CAST_SCHOOLS]={11,13,10,12,14,15};
    return school>=0 && school<AW_CAST_SCHOOLS?school_skill[school]:11;
}
float AW_CastBaseChance(const aw_spell_effect_t *e,const aw_mgef_t *m,int n,const float skills[27],float willpower,
                        float luck,int cost,float effect_cost_mult,int *school){
    float y=3.0e38f,lowest=0;int i;
    if(school)*school=0;
    for(i=0;i<n;i++){
        /* the original's own cost term here differs a little from the spell's cost (no minimum magnitude of 1) */
        float x=(float)e[i].duration,s;
        if(AW_EffectPerSecond(e[i].effect) && x<1)x=1;      /* at least 1 unless applied once */
        x*=0.1f*m[i].base_cost;
        x*=0.5f*(float)(e[i].magnitude_min+e[i].magnitude_max);
        x+=(float)e[i].area*0.05f*m[i].base_cost;
        if(e[i].range==AW_RANGE_TARGET)x*=1.5f;
        x*=effect_cost_mult;
        s=2.0f*skills[AW_CastSchoolSkill(m[i].school)];
        if(s-x<y){y=s-x;lowest=s;if(school)*school=m[i].school;}
    }
    return lowest-(float)cost+0.2f*willpower+0.1f*luck;
}
float AW_CastChance(float base,int type,int power_ready,int always,float silence,float sound,float fatigue_term,
                    float magicka,int cost,int check_magicka){
    float c;
    if(type==AW_SPELL_TYPE_POWER)return power_ready?100.0f:0.0f;
    if(silence>0)return 0;
    if(type!=AW_SPELL_TYPE_SPELL)return 100.0f;
    if(check_magicka && cost>0 && magicka<(float)cost)return 0;
    if(always)return 100.0f;
    c=(base-sound)*fatigue_term;
    return c<0?0:c>100?100:c;
}
float AW_CastFatigueTerm(float base,float mult,float current,float maximum){
    float normalised=floor(maximum)==0?1.0f:current/maximum;
    if(normalised<0)normalised=0;
    return base-mult*(1.0f-normalised);
}
float AW_CastMagnitude(int lo,int hi,float r){
    float m;
    if(hi<lo)hi=lo;
    if(!(r>=0))r=0;
    m=(float)lo+(float)floor(r*(float)(hi-lo+1));
    return m>(float)hi?(float)hi:m;
}
float AW_CastDuration(const aw_spell_effect_t *e,const aw_mgef_t *m){
    return m->flags&AW_MGEF_NO_DURATION?1.0f:(float)e->duration;
}
int AW_CastRanges(const aw_spell_effect_t *e,int n){
    int i,bits=0;
    for(i=0;i<n;i++)if(e[i].range<=AW_RANGE_TARGET)bits|=1<<e[i].range;
    return bits;
}

/* ---- magic items (OpenMW 0.51 spellutil.cpp getEffectiveEnchantmentCastCost, spellcasting.cpp CastSpell::cast) ---- */
int AW_CastItemCost(float cast_cost,float enchant_skill){
    float r=cast_cost-(cast_cost/100.0f)*(enchant_skill-10.0f);   /* a point of Enchant over 10 takes 1 % off */
    return r<1?1:(int)r;
}
float AW_CastItemCharge(float charge,int cost){return charge<(float)cost?-1.0f:charge-(float)cost;}

/* ---- the starting spells (OpenMW 0.51 autocalcspell.cpp autoCalcPlayerSpells, attrSkillCheck, calcWeakestSchool,
 * calcAutoCastChance; our own code) ---- */
#define MGEF_TARGET_SKILL 0x1
#define MGEF_TARGET_ATTRIBUTE 0x2
#define MGEF_APPLIED_ONCE 0x1000
static int start_skill_check(const aw_start_spell_t *s,const float skills[27],const float attributes[8],int minimum){
    int i;
    for(i=0;i<s->n;i++){
        if((s->m[i].flags&MGEF_TARGET_SKILL) && (s->e[i].skill<0 || s->e[i].skill>=27 || skills[s->e[i].skill]<(float)minimum))return 0;
        if((s->m[i].flags&MGEF_TARGET_ATTRIBUTE) &&
           (s->e[i].attribute<0 || s->e[i].attribute>=8 || attributes[s->e[i].attribute]<(float)minimum))return 0;
    }
    return 1;
}
/* the skill term of the weakest school: 2 x the school's skill of the effect whose term minus its cost is lowest (the
 * original's own cost formula here: magnitudes at least 1, 1 + duration, the area at least 1) */
static float start_skill_term(const aw_start_spell_t *s,const float skills[27],float cost_mult){
    float low=3.0e38f,term=0;int i;
    for(i=0;i<s->n;i++){
        int lo=1,hi=1,duration=0;float x,k;
        if(!(s->m[i].flags&AW_MGEF_NO_MAGNITUDE)){lo=s->e[i].magnitude_min;hi=s->e[i].magnitude_max;}
        if(!(s->m[i].flags&AW_MGEF_NO_DURATION))duration=s->e[i].duration;
        if(!(s->m[i].flags&MGEF_APPLIED_ONCE) && duration<1)duration=1;
        x=0.5f*(float)((lo>1?lo:1)+(hi>1?hi:1));
        x*=0.1f*s->m[i].base_cost;
        x*=(float)(1+duration);
        x+=0.05f*(float)(s->e[i].area>1?s->e[i].area:1)*s->m[i].base_cost;
        x*=cost_mult;
        if(s->e[i].range==AW_RANGE_TARGET)x*=1.5f;
        k=2.0f*skills[AW_CastSchoolSkill(s->m[i].school)];
        if(k-x<low){low=k-x;term=k;}
    }
    return term;
}
float AW_CastStartChance(const aw_start_spell_t *s,const float skills[27],const float attributes[8],float cost_mult){
    if(s->flags&4)return 100.0f;                    /* always succeeds */
    return start_skill_term(s,skills,cost_mult)-(float)s->cost+0.2f*attributes[2]+0.1f*attributes[7];
}
int AW_CastStartSpells(const aw_start_spell_t *s,int count,const aw_start_settings_t *set,const float skills[27],
                       const float attributes[8],const int *race,int nrace,int *out,int max){
    int n=0,i,j,reached=0,weakest=-1,min_cost=0x7FFFFFFF;
    float magicka=set->magicka_mult*attributes[1];  /* the base Intelligence */
    for(i=0;i<count;i++){
        int cost=s[i].cost;
        if(reached && cost<=min_cost)continue;
        for(j=0;j<nrace && race[j]!=s[i].row;j++);
        if(j<nrace)continue;                        /* the race gives it already */
        if(magicka<(float)cost)continue;
        if(AW_CastStartChance(&s[i],skills,attributes,set->cost_mult)<set->chance)continue;
        if(!start_skill_check(&s[i],skills,attributes,set->skill_min))continue;
        if(n>=max)break;
        out[n++]=i;
        if(reached){
            for(j=0;j<n && out[j]!=weakest;j++);
            if(j<n){for(;j<n-1;j++)out[j]=out[j+1];n--;}
            min_cost=0x7FFFFFFF;
            for(j=0;j<n;j++)if(s[out[j]].cost<min_cost){min_cost=s[out[j]].cost;weakest=out[j];}
        }else{
            if(cost<min_cost){weakest=i;min_cost=cost;}
            if(n==set->max)reached=1;
        }
    }
    for(i=0;i<n;i++)out[i]=s[out[i]].row;
    return n;
}
