/* SPDX-License-Identifier: GPL-2.0-or-later
 * The rest and wait rules as pure functions (aw_rest.h; host tested by tests/aga_rest_rules_test.c). Rule from
 * OpenMW 0.51 mwmechanics/actors.cpp restoreDynamicStats, getRestorationPerHourOfSleep, getHoursToRest,
 * mwgui/waitdialog.cpp setPtr/startWaiting, mwworld/worldimp.cpp canRest, mechanicsmanagerimp.cpp isOwned;
 * independent code, numbers from the master file's game settings. */
#include <string.h>
#include "aw_rest.h"

static int same(const char *a,const char *b)
{
    for(;*a && *b;a++,b++){
        int x=*a>='A' && *a<='Z'?*a+32:*a,y=*b>='A' && *b<='Z'?*b+32:*b;
        if(x!=y)return 0;
    }
    return !*a && !*b;
}
int AW_RestSettingSet(aw_rest_settings_t *s,const char *name,float value)
{
    static const char *const names[AW_REST_SETTING_COUNT]={"fRestMagicMult","fEndFatigueMult","fFatigueReturnBase",
        "fFatigueReturnMult","fSleepRandMod","fSleepRestMod","fEncumbranceStrMult"};
    float *fields[AW_REST_SETTING_COUNT];int i;
    fields[0]=&s->rest_magic;fields[1]=&s->end_fatigue;fields[2]=&s->fatigue_base;fields[3]=&s->fatigue_mult;
    fields[4]=&s->sleep_rand;fields[5]=&s->sleep_rest;fields[6]=&s->enc_str;
    for(i=0;i<AW_REST_SETTING_COUNT;i++)if(same(name,names[i])){*fields[i]=value;return 1;}
    return 0;
}
void AW_RestRestore(const aw_rest_settings_t *s,aw_rest_body_t *b,float hours,int sleeping)
{
    float capacity,load,x;
    if(!(hours>0))return;
    if(sleeping){
        b->health+=.1f*b->endurance*hours;
        if(b->health>b->health_max)b->health=b->health_max;
        if(!b->stunted){
            b->magicka+=s->rest_magic*b->intelligence*hours;
            if(b->magicka>b->magicka_max)b->magicka=b->magicka_max;
        }
    }
    if(b->fatigue>=b->fatigue_max)return;          /* a fortified fatigue stays as it is */
    capacity=s->enc_str*b->strength;
    load=capacity>0?b->carried/capacity:0;
    if(load>1)load=1;
    if(load<0)load=0;
    x=(s->fatigue_base+s->fatigue_mult*(1-load))*(s->end_fatigue*b->endurance);
    b->fatigue+=3600*x*hours;
    if(b->fatigue>b->fatigue_max)b->fatigue=b->fatigue_max;
}
int AW_RestUntilHealed(const aw_rest_settings_t *s,const aw_rest_body_t *b)
{
    float hours=1,h,m,rate;
    int full=b->health>=b->health_max && b->magicka>=b->magicka_max;
    if(full)return 0;
    rate=.1f*b->endurance;
    h=rate>0?(b->health_max-b->health)/rate:1;
    if(h>hours)hours=h;
    rate=s->rest_magic*b->intelligence;
    m=!b->stunted && rate>0?(b->magicka_max-b->magicka)/rate:1;
    if(m>hours)hours=m;
    {int whole=(int)hours;return hours>whole?whole+1:whole;}
}
int AW_RestInterruptAt(const aw_rest_settings_t *s,int hours,int roll)
{
    int remaining;
    if(hours<1 || roll<0 || roll>=hours || !((float)roll<s->sleep_rand*hours))return 0;
    remaining=(int)(s->sleep_rest*hours);
    return remaining?hours-remaining:0;
}
int AW_RestRefusal(int in_water,int on_ground,int flying,int enemies,int bed)
{
    int r=0;
    if(in_water)r|=AW_REST_WATER;
    if(!bed && (!on_ground || flying))r|=AW_REST_AIR;
    if(enemies)r|=AW_REST_ENEMIES;
    return r;
}
static int none(const char *s){return !s || !*s || (s[0]=='-' && !s[1]);}
int AW_RestBedAllowed(const char *owner,const char *faction,int rank,int global_value,int player_rank)
{
    if(global_value)return 1;                     /* a rented room: the global lifts every ownership */
    if(!none(owner) && !same(owner,"player"))return 0;
    if(!none(faction) && (player_rank<0 || player_rank<rank))return 0;
    return 1;
}
