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
    /* v0.0.62 (CRIME-59): the other crimes, as reportCrime works them out with the shipped game's settings */
    {
        static const struct {const char *name;float v;} more[]={
            {"iCrimeAttack",40},{"iCrimeKilling",1000},{"iCrimeTresspass",5},{"iCrimePickPocket",25},
            {"iDispAttackMod",-50},{"fDispAttacking",-10},{"iDispKilling",-50},{"iDispTresspass",-20},
            {"fDispPickPocketMod",-25},{"iFightAttack",100},{"iFightAttacking",50},{"iFightKilling",50},
            {"iFightTrespass",25},{"iFightPickpocket",25},{"iDaysinPrisonMod",100},{"iCrimeThresholdMultiplier",10},
            {"fCrimeGoldDiscountMult",.5f},{"fCrimeGoldTurnInMult",.75f}};
        aw_crime_react_in_t in;aw_crime_react_t out;int g[5];
        aw_crime_actor_t table[3];aw_crime_actor_t *a,*b;
        for(i=0;i<(int)(sizeof(more)/sizeof(more[0]));i++)assert(AW_CrimeSettingSet(&s,more[i].name,more[i].v));
        assert(AW_CRIME_THEFT_SETTINGS==11 && AW_CRIME_SETTING_COUNT==29 && !strcmp(AW_CrimeSettingName(28),"fCrimeGoldTurnInMult"));
        assert(!strcmp(AW_CrimeKindName(AW_CRIME_MURDER),"murder") && !strcmp(AW_CrimeKindName(99),"?"));
        /* the bounties */
        assert(AW_CrimeBounty(&s,AW_CRIME_ASSAULT,0)==40 && AW_CrimeBounty(&s,AW_CRIME_MURDER,0)==1000);
        assert(AW_CrimeBounty(&s,AW_CRIME_TRESPASS,0)==5 && AW_CrimeBounty(&s,AW_CRIME_BED,0)==5);
        assert(AW_CrimeBounty(&s,AW_CRIME_PICKPOCKET,0)==25 && AW_CrimeBounty(&s,AW_CRIME_THEFT,30)==30);
        /* an assault's victim (not a guard, Alarm 0): its disposition falls by fDispAttacking for good, it keeps the
         * crime's number; Alarm 0 adds no Fight (it fights back because it was hit: actorAttacked) */
        memset(&in,0,sizeof(in));in.fight=30;in.disposition=50;in.distance=100;in.victim=1;
        AW_CrimeReact(&s,AW_CRIME_ASSAULT,0,&in,.2f,20,.005f,&out);
        assert(out.disposition==-10 && out.permanent && out.crime_id && !out.attack && !out.pursue);
        /* a bystander with Alarm 100: iDispAttackMod for a while; (50 + 20 + 19.5) x 1 capped at 70: it attacks */
        in.victim=0;in.alarm=100;
        AW_CrimeReact(&s,AW_CRIME_ASSAULT,0,&in,.2f,20,.005f,&out);
        assert(out.disposition==-50 && !out.permanent && out.attack && out.fight==100 && out.alarmed && out.crime_id);
        /* the same as a guard: alarmed, it pursues to arrest, it does not attack */
        in.guard=1;AW_CrimeReact(&s,AW_CRIME_ASSAULT,0,&in,.2f,20,.005f,&out);
        assert(out.pursue && out.alarmed && out.crime_id && !out.attack && out.disposition==-50);
        /* Alarm 50: the disposition change only if it turns hostile; 89.5 x 0.5 = 44.75 keeps it under 100 */
        in.guard=0;in.alarm=50;AW_CrimeReact(&s,AW_CRIME_ASSAULT,0,&in,.2f,20,.005f,&out);
        assert(!out.attack && !out.disposition && !out.crime_id);
        /* a murder heard by Alarm 90: (50 + 20 + 19.5) x 0.9 capped at 70: it attacks; no disposition change */
        in.alarm=90;AW_CrimeReact(&s,AW_CRIME_MURDER,0,&in,.2f,20,.005f,&out);
        assert(out.attack && out.fight==100 && !out.disposition);
        /* trespass: no disposition change, 25 + 14 + 19.5 under 70: nothing */
        in.alarm=100;AW_CrimeReact(&s,AW_CRIME_TRESPASS,0,&in,.2f,20,.005f,&out);
        assert(!out.attack && !out.disposition && !out.crime_id);
        /* pickpocketing's victim with Alarm 0 counts as 100: x 4 Fight, attacks; its disposition falls for good */
        in.alarm=0;in.victim=1;in.disposition=40;AW_CrimeReact(&s,AW_CRIME_PICKPOCKET,0,&in,.2f,20,.005f,&out);
        assert(out.attack && out.permanent && out.disposition==-25);
        /* a bystander who would not arrest does not care about pickpocketing */
        in.victim=0;in.alarm=50;AW_CrimeReact(&s,AW_CRIME_PICKPOCKET,0,&in,.2f,20,.005f,&out);
        assert(!out.attack && !out.disposition && !out.crime_id);
        /* a theft through the general rule matches the theft's own (Arrille, above) */
        in.alarm=100;in.disposition=50;AW_CrimeReact(&s,AW_CRIME_THEFT,1,&in,.2f,20,.005f,&out);
        assert(out.attack && out.fight==30+(int)AW_CrimeTheftFight(&s,1,30,100,100,.2f,20,.005f));
        /* STEAL-WITNESSED-NO-CRIME-61, the census office of the opening: the Silverware Plate (value 17) taken in view of
         * the door guard Ganciele Douar (class Guard, Alarm 100, Fight 10), Sellus Gravius (Guard, Alarm 100, Fight 40)
         * and the census clerk Socucius Ergalla (not a guard, Alarm 0, Fight 30), the game data's numbers: reported, bounty 17; each guard is
         * Alarmed, keeps the crime's number, pursues to arrest and does not attack, his disposition down by
         * int(-0.5 x 17) = -8 for a while; Socucius does nothing. The guard's greeting for an Alarmed speaker during
         * character creation ("Greeting 0": Alarmed 1, CharGenState not -1) then runs Goodbye, SetFight 10, PayFine,
         * SetPCCrimeLevel 0: the plate goes back, the bounty to 0. */
        assert(AW_CRIME_REPORTS(100) && AW_CrimeBounty(&s,AW_CRIME_THEFT,17)==17);
        memset(&in,0,sizeof(in));in.alarm=100;in.fight=10;in.guard=1;in.disposition=50;in.distance=200;
        AW_CrimeReact(&s,AW_CRIME_THEFT,17,&in,.2f,20,.005f,&out);
        assert(out.alarmed && out.pursue && out.crime_id && !out.attack && out.disposition==-8 && !out.permanent);
        in.fight=40;AW_CrimeReact(&s,AW_CRIME_THEFT,17,&in,.2f,20,.005f,&out);
        assert(out.alarmed && out.pursue && !out.attack && out.disposition==-8);
        in.alarm=0;in.fight=30;in.guard=0;AW_CrimeReact(&s,AW_CRIME_THEFT,17,&in,.2f,20,.005f,&out);
        assert(!out.alarmed && !out.pursue && !out.attack && !out.disposition && !out.crime_id);
        /* a disposition change never leaves 0..100 */
        in.alarm=100;in.disposition=20;AW_CrimeReact(&s,AW_CRIME_ASSAULT,0,&in,.2f,20,.005f,&out);
        assert(out.disposition==-20);
        /* who witnesses: the assault's victim always, a murder by hearing (not its victim), else by sight */
        assert(AW_CrimeWitness(AW_CRIME_ASSAULT,1,0,0) && AW_CrimeWitness(AW_CRIME_MURDER,0,0,0));
        assert(!AW_CrimeWitness(AW_CRIME_MURDER,1,0,0) && !AW_CrimeWitness(AW_CRIME_THEFT,0,0,0));
        assert(AW_CrimeWitness(AW_CRIME_THEFT,0,0,1) && AW_CrimeWitness(AW_CRIME_THEFT,1,1,0) && !AW_CrimeWitness(AW_CRIME_THEFT,1,0,0));
        /* canCommitCrimeAgainst and actorKilled: an aggressive or fighting NPC is fair game; a creature never a crime;
         * an NPC that reacted to the player's crime (a crime's number) is murdered even while it fights */
        assert(AW_CrimeCanCommitAgainst(1,0,0,0,0,0) && !AW_CrimeCanCommitAgainst(1,1,0,0,0,0) &&
               !AW_CrimeCanCommitAgainst(1,0,1,0,0,0) && !AW_CrimeCanCommitAgainst(1,0,0,1,0,0) &&
               !AW_CrimeCanCommitAgainst(0,0,0,0,0,0) && !AW_CrimeCanCommitAgainst(1,0,0,0,0,1));
        assert(AW_CrimeIsMurder(1,1,1,-1) && AW_CrimeIsMurder(1,1,0,3) && !AW_CrimeIsMurder(1,1,0,-1) &&
               !AW_CrimeIsMurder(0,1,1,3) && !AW_CrimeIsMurder(1,0,1,3));
        /* jail: max(1, bounty / 100) days; Security and Sneak rise, the others fall, within 0..100 */
        assert(AW_CrimeJailDays(&s,40)==1 && AW_CrimeJailDays(&s,250)==2 && AW_CrimeJailDays(&s,1000)==10);
        assert(AW_CrimeJailSkill(19,30)==1 && AW_CrimeJailSkill(18,100)==0 && AW_CrimeJailSkill(5,30)==-1 &&
               AW_CrimeJailSkill(5,0)==0);
        /* the crime gold globals (updateDialogueGlobals) */
        AW_CrimeGoldGlobals(&s,100,60,g);assert(!g[0] && g[1] && g[2]==50 && g[3]==75 && !g[4]);
        AW_CrimeGoldGlobals(&s,0,0,g);assert(g[0] && g[1] && !g[2] && !g[3] && g[4]);
        AW_CrimeGoldGlobals(&s,1,0,g);assert(!g[0] && !g[1] && g[2]==1 && g[3]==1 && !g[4]);
        /* the guards on sight: pursue at 1000, attack at 10,000 */
        assert(!AW_CrimeGuardSight(&s,999) && AW_CrimeGuardSight(&s,1000)==1 && AW_CrimeGuardSight(&s,9999)==1 &&
               AW_CrimeGuardSight(&s,10000)==2);
        /* the NPCs' rows: made once per reference, the paid crimes calmed, the newer ones kept, a calm row reused */
        memset(table,0,sizeof(table));
        a=AW_CrimeActorMake(table,3,5);b=AW_CrimeActorMake(table,3,6);
        assert(a && b && a!=b && a->crime_id==-1 && AW_CrimeActorMake(table,3,5)==a && !AW_CrimeActorMake(table,3,0));
        a->crime_id=3;a->alarmed=1;a->disposition=-50;a->pursue=1;b->crime_id=7;b->murdered=1;
        {aw_crime_actor_t *c=AW_CrimeActorMake(table,3,8);assert(c);c->alarmed=1;}     /* alarmed without a crime */
        assert(!AW_CrimeActorMake(table,3,9));                                          /* full: no calm row */
        assert(AW_CrimeActorsCalm(table,3,5)==1 && a->crime_id==-1 && !a->alarmed && !a->disposition && !a->pursue);
        assert(b->crime_id==7 && AW_CrimeActorFind(table,3,6)==b);
        assert(AW_CrimeActorMake(table,3,9)!=NULL && !AW_CrimeActorFind(table,3,5) && AW_CrimeActorFind(table,3,6)==b);
    }
    /* CRIME-SAVE-PURSUERS-62: the rows in a saved game. The Seyda Neen guard of session s9 (reference 128967)
     * alarmed and pursuing for crime 3 with the disposition change -8; Fargoth (128964) murdered (no crime of his
     * own, crime id -1); a calm row left out. 6 + 2 x 12 = 30 bytes; read back the same, the pursuit's walk not kept. */
    {
        aw_crime_actor_t table[4],back[4];unsigned char block[64];int n;
        memset(table,0,sizeof(table));
        table[0].ref=128967;table[0].crime_id=3;table[0].disposition=-8;table[0].alarmed=1;table[0].pursue=1;
        table[0].walk_edict=17;
        table[1].ref=128964;table[1].crime_id=-1;table[1].murdered=1;
        table[2].ref=5;table[2].crime_id=-1;                                   /* calm: not saved */
        n=AW_CrimeActorsPack(table,4,block,sizeof(block));
        assert(n==30 && !memcmp(block,"AWCR",4) && block[4]==1 && block[5]==2);
        assert(block[6]==0 && block[7]==0x01 && block[8]==0xF7 && block[9]==0xC7);         /* 128967 = 0x0001F7C7 */
        assert(block[10]==0 && block[13]==3 && block[14]==0xFF && block[15]==0xF8 && block[16]==(1|4));   /* -8 */
        assert(block[22]==0xFF && block[25]==0xFF && block[28]==2);                        /* crime -1, murdered */
        assert(AW_CrimeActorsPack(table,4,block,29)==-1);                                  /* short */
        assert(AW_CrimeActorsUnpack(back,4,block,n)==30);
        assert(back[0].ref==128967 && back[0].crime_id==3 && back[0].disposition==-8 && back[0].alarmed &&
               back[0].pursue && !back[0].murdered && !back[0].attacked && back[0].walk_edict==0);
        assert(back[1].ref==128964 && back[1].crime_id==-1 && back[1].murdered && !back[1].pursue);
        assert(!back[2].ref && back[2].crime_id==-1 && !back[3].ref);
        /* unreadable: the table left empty */
        assert(AW_CrimeActorsUnpack(back,4,block,29)==-1 && !back[0].ref && back[0].crime_id==-1);
        block[4]=2;assert(AW_CrimeActorsUnpack(back,4,block,n)==-1 && !back[0].ref);
        assert(AW_CrimeActorsUnpack(back,4,NULL,0)==-1 && !back[1].ref);
        /* none to keep: the block is its 6 bytes */
        memset(table,0,sizeof(table));table[0].ref=5;table[0].crime_id=-1;
        assert(AW_CrimeActorsPack(table,4,block,sizeof(block))==6 && block[5]==0);
    }
    printf("crime rules ok\n");
    return 0;
}
