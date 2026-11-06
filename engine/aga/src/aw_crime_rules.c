/* SPDX-License-Identifier: GPL-2.0-or-later
 * The crime rules as pure functions (aw_crime.h); host tested by tests/aga_crime_rules_test.c. */
#include <string.h>
#include "aw_crime.h"

static const char *const names[AW_CRIME_SETTING_COUNT]={
    "fAlarmRadius","fCrimeStealing","fDispStealing","fFightStealing",
    "fSneakSkillMult","fSneakBootMult","fSneakDistanceBase","fSneakDistanceMultiplier","fSneakNoViewMult",
    "fSneakViewMult","iCrimeThreshold"};
const char *AW_CrimeSettingName(int index){return index>=0 && index<AW_CRIME_SETTING_COUNT?names[index]:NULL;}
int AW_CrimeSettingSet(aw_crime_settings_t *s,const char *name,float value){
    float *field=(float *)s;int i;
    if(!s || !name)return 0;
    for(i=0;i<AW_CRIME_SETTING_COUNT;i++)if(!strcmp(names[i],name)){field[i]=value;return 1;}
    return 0;
}

/* OpenMW 0.51 mechanicsmanagerimp.cpp awarenessCheck: the thief's term x (sneaking: skill, agility, luck and the boots'
 * weight, scaled by the distance and its fatigue; Chameleon adds, Invisibility adds 100) less the observer's term y
 * (Sneak, agility, luck less Blind, by its fatigue, x fSneakViewMult in view or fSneakNoViewMult from behind). */
float AW_CrimeAwarenessTarget(const aw_crime_settings_t *s,const aw_crime_thief_t *t,const aw_crime_observer_t *o,
                              float distance){
    float sneak_term=0,dist_term,x,obs_term,y;
    if(t->sneaking)
        sneak_term=s->fSneakSkillMult*t->sneak+0.2f*t->agility+0.1f*t->luck+t->boot_weight*s->fSneakBootMult;
    dist_term=s->fSneakDistanceBase+s->fSneakDistanceMultiplier*distance;
    x=sneak_term*dist_term*t->fatigue_term+t->chameleon;
    if(t->invisibility>0)x+=100;
    obs_term=o->sneak+0.2f*o->agility+0.1f*o->luck-o->blind;
    y=obs_term*o->fatigue_term*(o->behind?s->fSneakNoViewMult:s->fSneakViewMult);
    return x-y;
}

/* reportCrime OT_Theft: bounty = arg x fCrimeStealing, at least 1 (a theft of a worthless item still counts) */
int AW_CrimeTheftBounty(const aw_crime_settings_t *s,int value){
    int bounty=(int)((float)value*s->fCrimeStealing);
    return bounty<1?1:bounty;
}

/* reportCrime, a witness that is not an alarmed guard: fight = fFightStealing (read as a whole number, getInteger) x
 * arg; + getFightDispositionBias(dispTerm), dispTerm = fDispStealing x arg; + getFightDistanceBias; x Alarm / 100;
 * kept within 0 .. 100 - Fight */
float AW_CrimeTheftFight(const aw_crime_settings_t *s,int value,int fight,int alarm,float distance,
                         float fight_disp_mult,float distance_base,float distance_mult){
    float disp=s->fDispStealing*(float)value;
    float term=(float)((int)s->fFightStealing*value);
    term+=(50.0f-disp)*fight_disp_mult;
    term+=distance_base-distance_mult*distance;
    term*=0.01f*(float)alarm;
    if((float)fight+term>100)term=(float)(100-fight);
    return term<0?0:term;
}
