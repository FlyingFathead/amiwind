/* SPDX-License-Identifier: GPL-2.0-or-later
 * The levelling rules (aw_levelup_rules.c, LEVEL-UP-58) against the original's rules as OpenMW 0.51 implements
 * them: the skill progress requirement, a skill rising with use, the level progress and the attribute and
 * specialization counts, the multiplier table, the level-up itself (attributes, health, counters), the level-up
 * picture by specialization and the box's coins. The numbers are the shipped game settings' values, written here
 * as a fixture (the engine reads them from the image). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_levelup.h"

static aw_levelup_rules_t rules;
static void settings(void)
{
    static const struct {const char *name;float value;} rows[]={
        {"fMajorSkillBonus",.75f},{"fMinorSkillBonus",1},{"fMiscSkillBonus",1.25f},{"fSpecialSkillBonus",.8f},
        {"fLevelUpHealthEndMult",.1f},{"iLevelupTotal",10},{"iLevelupMajorMult",1},{"iLevelupMinorMult",1},
        {"iLevelupMajorMultAttribute",1},{"iLevelupMinorMultAttribute",1},{"iLevelupMiscMultAttriubte",1},
        {"iLevelupSpecialization",1},{"iLevelUp01Mult",2},{"iLevelUp02Mult",2},{"iLevelUp03Mult",2},{"iLevelUp04Mult",2},
        {"iLevelUp05Mult",3},{"iLevelUp06Mult",3},{"iLevelUp07Mult",3},{"iLevelUp08Mult",4},{"iLevelUp09Mult",4},
        {"iLevelUp10Mult",5}};
    /* governing attribute and specialization of each skill (the SKIL records' order) */
    static const int attribute[27]={5,5,5,0,0,0,0,5,4,1,2,2,6,1,2,2,1,4,1,3,0,3,4,3,6,6,4};
    static const int special[27]={0,0,0,0,0,0,0,0,2,1,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,2};
    float use[4]={1,1,1,1};int i;
    memset(&rules,0,sizeof(rules));
    assert(!AW_LevelupRulesComplete(&rules));
    for(i=0;i<(int)(sizeof(rows)/sizeof(rows[0]));i++)assert(AW_LevelupSettingSet(&rules,rows[i].name,rows[i].value));
    assert(!AW_LevelupSettingSet(&rules,"fNoSuchSetting",1));
    assert(!strcmp(AW_LevelupSettingName(21),"iLevelUp10Mult") && !*AW_LevelupSettingName(22));
    assert(!AW_LevelupRulesComplete(&rules));                        /* no skill rows yet */
    for(i=0;i<27;i++){use[0]=i==5?2.f:1.f;assert(AW_LevelupSkillRow(&rules,i,attribute[i],special[i],use));}
    assert(!AW_LevelupSkillRow(&rules,27,0,0,use) && !AW_LevelupSkillRow(&rules,0,8,0,use) && !AW_LevelupSkillRow(&rules,0,0,3,use));
    assert(AW_LevelupRulesComplete(&rules));rules.loaded=1;
}
int main(void)
{
    aw_class_t k;aw_character_t c;int i,picks[3];float need;aw_levelup_box_t b;
    settings();
    /* A combat class: majors Long Blade (5), Block (0), Heavy Armor (3), Athletics (8), Armorer (1);
     * minors Axe (6), Spear (7), Blunt (4), Medium (2), Hand-to-hand (26). CLDT pairs: even minor, odd major. */
    memset(&k,0,sizeof(k));k.special=0;
    {static const unsigned char pairs[10]={6,5,7,0,4,3,2,8,26,1};memcpy(k.skills,pairs,10);}
    assert(AW_LevelupSkillClass(&k,5)==2 && AW_LevelupSkillClass(&k,6)==1 && AW_LevelupSkillClass(&k,22)==0);
    memset(&c,0,sizeof(c));c.valid=1;c.level=1;
    for(i=0;i<8;i++)c.attributes[i]=40;
    for(i=0;i<27;i++)c.skills[i]=10;
    c.skills[5]=30;c.maximum[0]=c.current[0]=40;
    /* the requirement: (base + 1) x class factor x specialization factor */
    need=AW_LevelupRequirement(&rules,&k,5,30);assert(need>18.59f && need<18.61f);       /* 31 x .75 x .8 */
    need=AW_LevelupRequirement(&rules,&k,6,10);assert(need>8.79f && need<8.81f);         /* 11 x 1 x .8 */
    need=AW_LevelupRequirement(&rules,&k,12,10);assert(need>13.74f && need<13.76f);      /* 11 x 1.25, magic skill */
    /* Long Blade's use value is 2 here: 9 hits leave it short (18 of 18.6), the 10th raises it */
    for(i=0;i<9;i++)assert(AW_LevelupSkillUsed(&rules,&k,&c,5,AW_USE_HIT,1)==0);
    assert(c.skills[5]==30 && c.progress[5]>.96f && c.progress[5]<.97f);
    assert(AW_LevelupSkillUsed(&rules,&k,&c,5,AW_USE_HIT,1)==1);
    assert(c.skills[5]==31 && c.progress[5]==0 && c.level_progress==1 && c.raises[0]==1 && c.special[0]==1);
    /* scale, a use value of 0 and the cap */
    assert(AW_LevelupSkillUsed(&rules,&k,&c,6,AW_USE_HIT,0)==0 && c.progress[6]==0);
    c.skills[7]=100;assert(AW_LevelupSkillUsed(&rules,&k,&c,7,AW_USE_HIT,1)==-1 && !AW_LevelupSkillRaise(&rules,&k,&c,7,AW_RAISE_USAGE));
    c.skills[7]=10;assert(AW_LevelupSkillUsed(&rules,&k,&c,7,4,1)==-1);
    /* a misc skill: no level progress, but its attribute counts (iLevelupMiscMultAttriubte) */
    assert(AW_LevelupSkillRaise(&rules,&k,&c,22,AW_RAISE_USAGE) && c.skills[22]==11 && c.level_progress==1 && c.raises[4]==1 && c.special[2]==1);
    /* a trainer's raise keeps the skill's own progress */
    c.progress[0]=.5f;assert(AW_LevelupSkillRaise(&rules,&k,&c,0,AW_RAISE_TRAINER) && c.progress[0]==.5f && c.level_progress==2);
    /* nine more major/minor raises: the level-up is due at iLevelupTotal */
    for(i=0;i<7;i++)assert(AW_LevelupSkillRaise(&rules,&k,&c,i%2?3:4,AW_RAISE_USAGE));
    assert(c.level_progress==9 && !AW_LevelupDue(&rules,&c));
    assert(AW_LevelupSkillRaise(&rules,&k,&c,8,AW_RAISE_USAGE) && c.level_progress==10 && AW_LevelupDue(&rules,&c));
    /* the multipliers: Strength had Long Blade, Heavy Armor x3, Blunt x4 = 8 raises -> iLevelUp08Mult 4;
     * Endurance Block 1 -> 2; Speed Short Blade + Athletics 2 -> 2; Intelligence none -> 1 */
    assert(c.raises[0]==8 && AW_LevelupMultiplier(&rules,&c,0)==4);
    assert(c.raises[5]==1 && AW_LevelupMultiplier(&rules,&c,5)==2);
    assert(c.raises[4]==2 && AW_LevelupMultiplier(&rules,&c,4)==2 && AW_LevelupMultiplier(&rules,&c,1)==1);
    c.raises[6]=14;assert(AW_LevelupMultiplier(&rules,&c,6)==5);c.raises[6]=0;
    assert(AW_LevelupMultiplier(&rules,&c,8)==1);
    /* the box: three coins; a click picks, a second click takes it back, a fourth replaces the last */
    AW_LevelupBoxOpen(&c,&b);assert(b.coins==3 && b.count==0 && !AW_LevelupBoxReady(&b));
    assert(AW_LevelupBoxClick(&c,&b,0) && AW_LevelupBoxClick(&c,&b,5) && AW_LevelupBoxClick(&c,&b,1));
    assert(AW_LevelupBoxReady(&b) && AW_LevelupBoxPicked(&b,5));
    assert(AW_LevelupBoxClick(&c,&b,5) && b.count==2 && !AW_LevelupBoxPicked(&b,5) && b.picks[1]==1);
    assert(AW_LevelupBoxClick(&c,&b,4) && AW_LevelupBoxClick(&c,&b,5) && b.count==3 && b.picks[2]==5 && !AW_LevelupBoxPicked(&b,4));
    assert(AW_LevelupBoxValue(&rules,&c,&b,0)==44 && AW_LevelupBoxValue(&rules,&c,&b,5)==42 && AW_LevelupBoxValue(&rules,&c,&b,7)==40);
    c.attributes[7]=100;assert(!AW_LevelupBoxClick(&c,&b,7));
    c.attributes[0]=98;assert(AW_LevelupBoxValue(&rules,&c,&b,0)==100);
    /* the level-up: Strength 98 + 4 caps at 100, Intelligence + 1, Endurance + 2; health + 42 x .1 */
    picks[0]=0;picks[1]=1;picks[2]=0;assert(!AW_LevelupApply(&rules,&c,picks,3));          /* not distinct */
    for(i=0;i<3;i++)picks[i]=b.picks[i];
    c.current[0]=30;
    assert(AW_LevelupApply(&rules,&c,picks,3)==2 && c.level==2);
    assert(c.attributes[0]==100 && c.attributes[1]==41 && c.attributes[5]==42);
    assert(c.maximum[0]>44.19f && c.maximum[0]<44.21f && c.current[0]>34.19f && c.current[0]<34.21f);
    assert(c.level_progress==0 && !c.raises[0] && !c.raises[5] && !c.special[0] && !AW_LevelupDue(&rules,&c));
    /* progress past the total carries over (OpenMW NpcStats::levelUp) */
    c.level_progress=12;assert(AW_LevelupApply(&rules,&c,picks,0)==3 && c.level_progress==2);
    /* fewer coins when attributes are at 100 */
    for(i=0;i<7;i++)c.attributes[i]=100;
    c.attributes[7]=60;
    AW_LevelupBoxOpen(&c,&b);assert(b.coins==1);
    /* Mercantile_Success (OpenMW tradewindow.cpp): the scale is the share haggled, floored; the merchant's own
     * price trains nothing; one accepted trade is one use, so a trade at the offer adds no progress at all */
    assert(AW_LevelupMercantileScale(1,100,100)==0 && AW_LevelupMercantileScale(0,100,100)==0);
    assert(AW_LevelupMercantileScale(1,90,100)==10 && AW_LevelupMercantileScale(1,67,100)==33);
    assert(AW_LevelupMercantileScale(0,120,100)==16);                      /* floor(100 x 20 / 120) */
    assert(AW_LevelupMercantileScale(1,110,100)==0 && AW_LevelupMercantileScale(0,80,100)==0);  /* a worse deal */
    assert(AW_LevelupMercantileScale(1,-90,-100)==10 && AW_LevelupMercantileScale(1,0,0)==0);
    {float before=c.progress[AW_LU_MERCANTILE];int skill=c.skills[AW_LU_MERCANTILE];
     assert(AW_LevelupSkillUsed(&rules,&k,&c,AW_LU_MERCANTILE,AW_USE_MERCANTILE_SUCCESS,AW_LevelupMercantileScale(1,50,50))==0);
     assert(c.progress[AW_LU_MERCANTILE]==before && c.skills[AW_LU_MERCANTILE]==skill);
     /* a 10 % haggle: use value 1 x 10 over the misc requirement (skill + 1) x 1.25 x .8, exactly one use's worth */
     need=AW_LevelupRequirement(&rules,&k,AW_LU_MERCANTILE,skill);
     assert(AW_LevelupSkillUsed(&rules,&k,&c,AW_LU_MERCANTILE,AW_USE_MERCANTILE_SUCCESS,AW_LevelupMercantileScale(1,90,100))>=0);
     assert(c.skills[AW_LU_MERCANTILE]>skill || (c.progress[AW_LU_MERCANTILE]>before+10/need-.001f && c.progress[AW_LU_MERCANTILE]<before+10/need+.001f));}
    /* the level-up picture by the specialization shares (getLevelupClassImage) */
    assert(!strcmp(AW_LevelupClassImage(0,0,0),"acrobat"));
    assert(!strcmp(AW_LevelupClassImage(10,0,0),"warrior"));
    assert(!strcmp(AW_LevelupClassImage(0,10,0),"mage") && !strcmp(AW_LevelupClassImage(0,0,10),"thief"));
    assert(!strcmp(AW_LevelupClassImage(6,0,1),"warrior"));                /* 8.5 combat: over 7 */
    assert(!strcmp(AW_LevelupClassImage(6,3,1),"barbarian"));              /* 6, 3, 1 */
    assert(!strcmp(AW_LevelupClassImage(6,1,3),"crusader"));
    assert(!strcmp(AW_LevelupClassImage(2,6,2),"sorcerer"));
    assert(!strcmp(AW_LevelupClassImage(5,5,0),"witchhunter"));
    assert(!strcmp(AW_LevelupClassImage(3,3,3),"bard"));
    /* DBG-STATS-COMMANDS-62: the sheet before and after. setlvl 50 from level 1 with Endurance 50: health + 49 x 50 x
     * .1 = 245, nothing else raised; down to 10 takes 40 x 5 = 200 off again; out of range refused; restore fills the
     * three; maxstats: attributes and skills 100, level 83, health 100 + 82 x 10 = 920, magicka 100 x 1.5 (+10
     * Intelligence modifier: 165), fatigue 400 (+5 Strength modifier: 405), all full */
    {aw_character_t s,before;
     memset(&s,0,sizeof(s));s.valid=1;s.level=1;for(i=0;i<8;i++)s.attributes[i]=50;
     s.maximum[0]=50;s.current[0]=20;s.maximum[1]=100;s.current[1]=3;s.maximum[2]=200;s.current[2]=7;s.level_progress=4;s.raises[2]=3;
     before=s;
     assert(AW_LevelupSetLevel(&rules,&s,50)==50 && s.level==50 && s.level_progress==0 && !s.raises[2]);
     assert(s.maximum[0]>294.9f && s.maximum[0]<295.1f && s.current[0]>264.9f && s.current[0]<265.1f);
     assert(!memcmp(s.attributes,before.attributes,sizeof(s.attributes)) && s.current[1]==3 && s.current[2]==7);
     assert(AW_LevelupSetLevel(&rules,&s,10)==10 && s.maximum[0]>94.9f && s.maximum[0]<95.1f && s.current[0]<=s.maximum[0]);
     before=s;assert(!AW_LevelupSetLevel(&rules,&s,0) && !AW_LevelupSetLevel(&rules,&s,AW_LEVEL_MAX+1) && !memcmp(&s,&before,sizeof(s)));
     assert(AW_LevelupSetLevel(&rules,&s,AW_LEVEL_MAX)==83);
     s.current[0]=1;AW_LevelupRestore(&s);assert(s.current[0]==s.maximum[0] && s.current[1]==100 && s.current[2]==200);
     s.current[2]=250;AW_LevelupRestore(&s);assert(s.current[2]==250);           /* above the maximum: kept */
     /* PLAYER-HEALTH-OVER-MAX-63: health above its maximum (Quake's spawn 100 of 40) restores to the maximum */
     {float m=s.maximum[0];s.current[0]=m+60;AW_LevelupRestore(&s);assert(s.current[0]==m);}
     s.modifiers[1]=10;s.modifiers[0]=5;s.damage[3]=20;s.skills[4]=12;s.progress[4]=.5f;
     AW_LevelupMax(&rules,&s,1.5f);
     for(i=0;i<8;i++)assert(s.attributes[i]==100 && !s.damage[i]);
     for(i=0;i<27;i++)assert(s.skills[i]==100 && s.progress[i]==0);
     assert(s.level==AW_LEVEL_MAX && s.maximum[0]>919.9f && s.maximum[0]<920.1f);
     assert(s.maximum[1]>164.9f && s.maximum[1]<165.1f && s.maximum[2]==405);
     for(i=0;i<3;i++)assert(s.current[i]==s.maximum[i]);
     printf("dbg stats: setlvl 50 health 50 -> %.0f, maxstats health %.0f magicka %.0f fatigue %.0f\n",
            before.maximum[0],s.maximum[0],s.maximum[1],s.maximum[2]);}
    puts("levelling rules ok: requirement, use, raises, level progress, multipliers, box, level-up, picture");
    return 0;
}
