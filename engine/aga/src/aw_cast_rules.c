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
