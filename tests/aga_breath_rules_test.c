/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_breath_rules.c alone (UNDERWATER-BREATH-62): the head under water, the breath falling and filling again, the
 * drowning damage once it is gone, Water Breathing, the bar, the settings. */
#include <assert.h>
#include <math.h>
#include "aw_breath.h"

static int near(float a,float b){return fabsf(a-b)<1e-4f;}

int main(void){
    aw_breath_settings_t s;float left=-1,taken=0;int i;
    AW_BreathSettingsDefault(&s);
    assert(s.hold==20 && s.suffocation==3);
    assert(AW_BreathSettingSet(&s,"fholdbreathtime",15) && s.hold==15);
    assert(AW_BreathSettingSet(&s,"fSuffocationDamage",4) && s.suffocation==4);
    assert(!AW_BreathSettingSet(&s,"fSwimRunBase",1) && !AW_BreathSettingSet(&s,"fHoldBreathTime",-1));
    assert(!AW_BreathSettingSet(&s,"fHoldBreathTime",NAN) && s.hold==15);
    AW_BreathSettingsDefault(&s);
    /* the head: the eyes in water or slime (waterlevel 3); lava, the feet or the waist are not */
    assert(AW_BreathSubmerged(-3,3) && AW_BreathSubmerged(-4,3));
    assert(!AW_BreathSubmerged(-3,2) && !AW_BreathSubmerged(-5,3) && !AW_BreathSubmerged(-1,3));
    /* full on the surface, the bar hidden */
    left=AW_BreathStep(left,s.hold,0,0,.1f);
    assert(left==20 && !AW_BreathBarShown(left,s.hold) && !AW_BreathBarShown(-1,s.hold));
    assert(AW_BreathFraction(-1,s.hold)==1);
    /* 19.875 seconds under water in 1/8 s frames (exact in binary): the bar shows, no damage yet */
    for(i=0;i<159;i++){left=AW_BreathStep(left,s.hold,1,0,.125f);taken+=AW_BreathDamage(left,s.suffocation,.125f);}
    assert(left==.125f && taken==0 && AW_BreathBarShown(left,s.hold));
    assert(near(AW_BreathFraction(left,s.hold),.00625f));
    /* the breath is gone on the next frame; from it on 3 health a second, continuously: 8 frames = 1 s = 3 */
    for(i=0;i<8;i++){left=AW_BreathStep(left,s.hold,1,0,.125f);taken+=AW_BreathDamage(left,s.suffocation,.125f);}
    assert(left==0 && taken==3.0f && AW_BreathFraction(left,s.hold)==0 && AW_BreathBarShown(left,s.hold));
    /* surfacing fills it at once */
    left=AW_BreathStep(left,s.hold,0,0,.1f);
    assert(left==20 && AW_BreathDamage(left,s.suffocation,.1f)==0);
    /* Water Breathing (a race's ability, a potion, a spell, a worn item): never falls */
    for(i=0;i<500;i++)left=AW_BreathStep(left,s.hold,1,1,.1f);
    assert(left==20 && !AW_BreathBarShown(left,s.hold));
    /* from "full" (-1) under water at once; a paused frame changes nothing */
    left=AW_BreathStep(-1,s.hold,1,0,1);
    assert(left==19 && AW_BreathStep(left,s.hold,1,0,0)==19);
    /* no damage for a zero or negative frame or no breath setting; a zero hold drowns at once */
    assert(AW_BreathDamage(0,3,0)==0 && AW_BreathDamage(0,3,-1)==0 && AW_BreathDamage(0,0,1)==0);
    assert(AW_BreathStep(5,0,1,0,.1f)==0 && AW_BreathDamage(AW_BreathStep(5,0,1,0,.1f),3,.5f)==1.5f);
    assert(!AW_BreathBarShown(0,0) && AW_BreathFraction(3,0)==0);
    return 0;
}
