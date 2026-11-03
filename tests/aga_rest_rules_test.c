/* SPDX-License-Identifier: GPL-2.0-or-later
 * The rest and wait rules (aw_rest_rules.c, REST-WAIT-59) against OpenMW 0.51's: restoration by mode and rate, the
 * fortified fatigue left alone, the load on fatigue, stunted magicka, Until Healed, the wilderness interruption's
 * arithmetic, the refusals and a bed's ownership. The settings are the shipped game's values, as a fixture. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_rest.h"

static int near(float a,float b){float d=a-b;return d<.01f && d>-.01f;}
int main(void)
{
    aw_rest_settings_t s;aw_rest_body_t b,c;int h;
    memset(&s,0,sizeof(s));
    assert(AW_RestSettingSet(&s,"fRestMagicMult",.15f) && AW_RestSettingSet(&s,"fEndFatigueMult",.04f));
    assert(AW_RestSettingSet(&s,"fFatigueReturnBase",2.5f) && AW_RestSettingSet(&s,"fFatigueReturnMult",.02f));
    assert(AW_RestSettingSet(&s,"fsleeprandmod",.25f) && AW_RestSettingSet(&s,"fSleepRestMod",.3f));
    assert(AW_RestSettingSet(&s,"fEncumbranceStrMult",5) && !AW_RestSettingSet(&s,"fNoSuch",1));
    memset(&b,0,sizeof(b));
    b.health=10;b.health_max=100;b.magicka=0;b.magicka_max=100;b.fatigue=0;b.fatigue_max=1000000;
    b.endurance=50;b.intelligence=40;b.strength=50;b.carried=0;
    /* rest, 2 hours: health 0.1 x 50 x 2, magicka 0.15 x 40 x 2, fatigue (2.5 + 0.02) x 0.04 x 50 x 3600 x 2 */
    c=b;AW_RestRestore(&s,&c,2,1);
    assert(near(c.health,20) && near(c.magicka,12) && near(c.fatigue,2.52f*2*3600*2));
    /* wait: fatigue only */
    c=b;AW_RestRestore(&s,&c,2,0);assert(c.health==10 && c.magicka==0 && near(c.fatigue,2.52f*2*3600*2));
    /* fully loaded: the 0.02 term is gone; over the capacity counts as full */
    c=b;c.carried=1000;AW_RestRestore(&s,&c,1,0);assert(near(c.fatigue,2.5f*2*3600));
    /* fortified fatigue stays; everything stops at its maximum */
    c=b;c.fatigue=c.fatigue_max+5;AW_RestRestore(&s,&c,1,0);assert(c.fatigue==c.fatigue_max+5);
    c=b;c.fatigue_max=100;AW_RestRestore(&s,&c,24,1);assert(c.health==100 && c.magicka==100 && c.fatigue==100);
    /* stunted magicka (the Atronach): no magicka, health and fatigue still */
    c=b;c.stunted=1;AW_RestRestore(&s,&c,2,1);assert(c.magicka==0 && near(c.health,20));
    /* Until Healed: health 90 short at 5 an hour = 18; magicka 100 at 6 = 16.7: 18; full: 0; stunted ignores magicka */
    assert(AW_RestUntilHealed(&s,&b)==18);
    c=b;c.health=100;assert(AW_RestUntilHealed(&s,&c)==17);
    c.stunted=1;assert(AW_RestUntilHealed(&s,&c)==1);
    c.magicka=100;c.stunted=0;assert(AW_RestUntilHealed(&s,&c)==0);
    /* the interruption: 8 hours, rolls 0 and 1 (under 2.0) stop after hour 6; 2..7 do not; 3 hours never */
    assert(AW_RestInterruptAt(&s,8,0)==6 && AW_RestInterruptAt(&s,8,1)==6 && !AW_RestInterruptAt(&s,8,2));
    assert(AW_RestInterruptAt(&s,24,5)==17 && !AW_RestInterruptAt(&s,24,6));
    for(h=1;h<=3;h++)assert(!AW_RestInterruptAt(&s,h,0));
    assert(!AW_RestInterruptAt(&s,8,8) && !AW_RestInterruptAt(&s,8,-1));
    /* refusals: water always; air unless a bed; enemies always */
    assert(AW_RestRefusal(1,1,0,0,1)==AW_REST_WATER && AW_RestRefusal(0,0,0,0,0)==AW_REST_AIR);
    assert(AW_RestRefusal(0,1,1,0,0)==AW_REST_AIR && !AW_RestRefusal(0,0,1,0,1));
    assert(AW_RestRefusal(0,0,0,1,0)==(AW_REST_AIR|AW_REST_ENEMIES) && !AW_RestRefusal(0,1,0,0,0));
    /* beds: an owner's refuses, the player's and an unowned one allow, a rented one allows, a faction's at rank */
    assert(!AW_RestBedAllowed("arrille","-",-2,0,-1) && AW_RestBedAllowed("player","-",-2,0,-1));
    assert(AW_RestBedAllowed("-","-",-2,0,-1) && AW_RestBedAllowed("arrille","-",-2,1,-1));
    assert(!AW_RestBedAllowed("-","fighters guild",2,0,-1) && !AW_RestBedAllowed("-","fighters guild",2,0,1));
    assert(AW_RestBedAllowed("-","fighters guild",2,0,2) && AW_RestBedAllowed("","",0,0,-1));
    puts("rest rules ok: restoration, load, stunted, until healed, interruption, refusals, beds");
    return 0;
}
