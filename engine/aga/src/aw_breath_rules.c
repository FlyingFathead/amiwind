/* SPDX-License-Identifier: GPL-2.0-or-later
 * Breath and drowning rules as pure functions (aw_breath.h, UNDERWATER-BREATH-62). No engine state: the host test
 * runs them as they are (tests/aga_breath_rules_test.c). */
#include "aw_breath.h"

void AW_BreathSettingsDefault(aw_breath_settings_t *s) {
    s->hold=AW_BREATH_HOLD_DEFAULT;s->suffocation=AW_BREATH_SUFFOCATION_DEFAULT;
}
static int same(const char *a,const char *b) {
    while(*a && *b && (*a|32)==(*b|32)){a++;b++;}
    return !*a && !*b;
}
int AW_BreathSettingSet(aw_breath_settings_t *s,const char *name,float value) {
    if(!s || !name || !(value>=0) || value>1e6f)return 0;
    if(same(name,"fHoldBreathTime")){s->hold=value;return 1;}
    if(same(name,"fSuffocationDamage")){s->suffocation=value;return 1;}
    return 0;
}
int AW_BreathSubmerged(int watertype,int waterlevel) {
    return waterlevel>=3 && (watertype==AW_BREATH_WATER || watertype==AW_BREATH_SLIME);
}
float AW_BreathStep(float left,float hold,int submerged,int breathing,float dt) {
    if(!(hold>0))hold=0;
    if(!submerged || breathing)return hold;
    if(left<0 || left>hold)left=hold;
    if(dt>0)left-=dt;
    return left>0?left:0;
}
float AW_BreathDamage(float left,float suffocation,float dt) {
    float d;
    if(left>0 || !(dt>0) || !(suffocation>0))return 0;
    d=suffocation*dt;
    return d>0?d:0;
}
int AW_BreathBarShown(float left,float hold) {
    return left>=0 && hold>0 && left<hold;
}
float AW_BreathFraction(float left,float hold) {
    float f;
    if(!(hold>0))return 0;
    if(left<0)return 1;
    f=left/hold;
    return f<0?0:f>1?1:f;
}
