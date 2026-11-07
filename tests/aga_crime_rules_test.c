/* SPDX-License-Identifier: GPL-2.0-or-later
 * The crime rules (aw_crime_rules.c, STEAL-WITNESSED-NO-CRIME-61) against OpenMW 0.51's mechanicsmanagerimp.cpp:
 * the awareness check (a player who does not sneak is always noticed; sneaking, distance, facing and the effects
 * move the target), the theft bounty (value x fCrimeStealing, at least 1) and a witness's theft reaction (fFightStealing
 * x value with the disposition and distance biases, x Alarm / 100, capped at 100 - Fight). The settings are the
 * shipped game's values, as a fixture. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_crime.h"

static int near(float a,float b){float d=a-b;return d<.01f && d>-.01f;}
int main(void)
{
    aw_crime_settings_t s;aw_crime_thief_t t;aw_crime_observer_t o;float target,term;int i;
    memset(&s,0,sizeof(s));
    assert(AW_CrimeSettingSet(&s,"fAlarmRadius",2000) && AW_CrimeSettingSet(&s,"fCrimeStealing",1));
    assert(AW_CrimeSettingSet(&s,"fDispStealing",-.5f) && AW_CrimeSettingSet(&s,"fFightStealing",50));
    assert(AW_CrimeSettingSet(&s,"fSneakSkillMult",1) && AW_CrimeSettingSet(&s,"fSneakBootMult",-1));
    assert(AW_CrimeSettingSet(&s,"fSneakDistanceBase",.5f) && AW_CrimeSettingSet(&s,"fSneakDistanceMultiplier",.002f));
    assert(AW_CrimeSettingSet(&s,"fSneakNoViewMult",.5f) && AW_CrimeSettingSet(&s,"fSneakViewMult",1.5f));
    assert(AW_CrimeSettingSet(&s,"iCrimeThreshold",1000) && !AW_CrimeSettingSet(&s,"fNoSuch",1));
    for(i=0;i<AW_CRIME_SETTING_COUNT;i++)assert(AW_CrimeSettingName(i));
    assert(!AW_CrimeSettingName(AW_CRIME_SETTING_COUNT) && s.iCrimeThreshold==1000 && s.fAlarmRadius==2000);

    /* awareness: not sneaking, no effects: x = 0, y = (30 + 0.2 x 40 + 0.1 x 40) x 1.25 x 1.5 = 78.75 in view */
    memset(&t,0,sizeof(t));memset(&o,0,sizeof(o));
    t.sneak=50;t.agility=50;t.luck=50;t.fatigue_term=1.25f;
    o.sneak=30;o.agility=40;o.luck=40;o.fatigue_term=1.25f;
    target=AW_CrimeAwarenessTarget(&s,&t,&o,500);
    assert(near(target,-78.75f));        /* every roll 0..99 is at least the target: always noticed */
    o.behind=1;assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),-26.25f));   /* from behind: x 0.5 */
    /* sneaking at 500 units: x = (50 + 10 + 5) x (0.5 + 1) x 1.25 = 121.875; less y in view */
    o.behind=0;t.sneaking=1;
    assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),121.875f-78.75f));
    /* heavy boots lower the thief's term (fSneakBootMult -1 x weight) */
    t.boot_weight=20;assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),(45*1.5f*1.25f)-78.75f));
    t.boot_weight=0;
    /* farther is harder to notice; Chameleon adds its magnitude; Invisibility adds 100 */
    assert(AW_CrimeAwarenessTarget(&s,&t,&o,1500)>AW_CrimeAwarenessTarget(&s,&t,&o,500));
    t.sneaking=0;t.chameleon=30;assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),30-78.75f));
    t.chameleon=0;t.invisibility=1;assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),100-78.75f));
    /* a blind observer sees less: Blind lowers its term */
    t.invisibility=0;o.blind=40;assert(near(AW_CrimeAwarenessTarget(&s,&t,&o,500),-(2*1.25f*1.5f)));

    /* the bounty: value x fCrimeStealing, at least 1 */
    assert(AW_CrimeTheftBounty(&s,100)==100 && AW_CrimeTheftBounty(&s,0)==1 && AW_CrimeTheftBounty(&s,1)==1);
    s.fCrimeStealing=.5f;assert(AW_CrimeTheftBounty(&s,3)==1 && AW_CrimeTheftBounty(&s,10)==5);s.fCrimeStealing=1;
    assert(AW_CRIME_REPORTS(100) && AW_CRIME_REPORTS(120) && !AW_CRIME_REPORTS(99) && !AW_CRIME_REPORTS(0));

    /* the reaction of Arrille (Fight 30, Alarm 100) to a theft worth 1 at 100 units: 50 x 1 + (50 + 0.5) x 0.2 +
     * (20 - 0.005 x 100) = 79.6, capped at 100 - 30 = 70: he attacks */
    term=AW_CrimeTheftFight(&s,1,30,100,100,.2f,20,.005f);
    assert(near(term,70) && 30+term>=100);
    /* Alarm 0 (Raflod the Braggart): no reaction at all */
    assert(AW_CrimeTheftFight(&s,100,30,0,100,.2f,20,.005f)==0);
    /* Alarm 40 at the alarm radius: (50 + 10.1 + 20 - 10) x 0.4 = 28.04: Fight 40 + 28 stays under 100 */
    term=AW_CrimeTheftFight(&s,1,40,40,2000,.2f,20,.005f);
    assert(near(term,(50+50.5f*.2f+10)*.4f) && 40+term<100);
    /* never negative: a far witness of a worthless theft with a negative distance bias */
    assert(AW_CrimeTheftFight(&s,0,30,100,100000,.2f,20,.005f)==0);
    /* GetDetected's kept roll (MWSCRIPT-SMALL-FUNCTIONS-62; creaturestats.cpp getAwarenessRoll / updateAwareness): an
     * observer's roll holds for 5 seconds, then it rolls again; other observers have their own; a clock that went
     * back (a new map) finds none; a full table gives the oldest slot */
    {
        aw_crime_roll_t rolls[3];
        for(i=0;i<3;i++){rolls[i].key=0;rolls[i].roll=-1;rolls[i].at=0;}
        assert(AW_CrimeRollFind(rolls,3,7,1)==-1);
        AW_CrimeRollKeep(rolls,3,7,42,1);AW_CrimeRollKeep(rolls,3,9,5,2);
        assert(AW_CrimeRollFind(rolls,3,7,5.9)==42 && AW_CrimeRollFind(rolls,3,9,5.9)==5);
        assert(AW_CrimeRollFind(rolls,3,7,6)==-1 && AW_CrimeRollFind(rolls,3,7,.5)==-1);
        AW_CrimeRollKeep(rolls,3,7,80,6);assert(AW_CrimeRollFind(rolls,3,7,6.5)==80);   /* rolled again, same slot */
        AW_CrimeRollKeep(rolls,3,11,1,6.6);AW_CrimeRollKeep(rolls,3,12,2,6.7);         /* full: 9's slot (oldest) */
        assert(AW_CrimeRollFind(rolls,3,12,6.8)==2 && AW_CrimeRollFind(rolls,3,9,6.8)==-1 &&
               AW_CrimeRollFind(rolls,3,7,6.8)==80 && AW_CrimeRollFind(rolls,3,11,6.8)==1);
    }
    printf("crime rules ok\n");
    return 0;
}
