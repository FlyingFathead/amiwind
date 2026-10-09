/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_combat_rules.c alone: the settings table, fatigue term, hit chance,
 * weapon and hand-to-hand damage, armour, block, knockdown, knockout,
 * fatigue return and the seeded generator. Values are worked by hand from
 * the formulas cited in aw_combat.h with the original game's settings. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "aw_combat.h"

static aw_combat_settings_t s;
static int near(float a,float b){return fabsf(a-b)<.01f;}
static void settings(void) {
    static const struct {const char *n;float v;} rows[]={
        {"fFatigueBase",1.25f},{"fFatigueMult",.5f},{"fCombatDistance",128},{"fHandToHandReach",1},
        {"fMinHandToHandMult",.1f},{"fMaxHandToHandMult",.5f},{"fHandtoHandHealthPer",.1f},
        {"fDamageStrengthBase",.5f},{"fDamageStrengthMult",.1f},{"fCombatArmorMinMult",.25f},{"fCombatKODamageMult",1.5f},
        {"fCombatCriticalStrikeMult",4},{"fKnockDownMult",.5f},{"iKnockDownOddsBase",50},{"iKnockDownOddsMult",50},
        {"fFatigueAttackBase",2},{"fFatigueAttackMult",0},{"fWeaponFatigueMult",.25f},
        {"fFatigueReturnBase",2.5f},{"fFatigueReturnMult",.02f},{"fUnarmoredBase1",.1f},{"fUnarmoredBase2",.065f},
        {"iBlockMinChance",10},{"iBlockMaxChance",50},{"fSwingBlockBase",1},{"fSwingBlockMult",1},{"fBlockStillBonus",1.25f},
        {"fFatigueBlockBase",4},{"fFatigueBlockMult",0},{"fWeaponFatigueBlockMult",1},
        {"fCombatBlockLeftAngle",-90},{"fCombatBlockRightAngle",30},{"fCombatDelayNPC",.1f},
        {"fNPCHealthBarTime",3},{"fNPCHealthBarFade",.5f}};
    int i;
    assert(sizeof(aw_combat_settings_t)==AW_COMBAT_SETTING_COUNT*sizeof(float));
    assert(sizeof(rows)/sizeof(*rows)==AW_COMBAT_SETTING_COUNT);
    memset(&s,0,sizeof(s));
    for(i=0;i<AW_COMBAT_SETTING_COUNT;i++){
        assert(AW_CombatSettingSet(&s,rows[i].n,rows[i].v));
        assert(AW_CombatSettingIndex(rows[i].n)==i && !strcmp(AW_CombatSettingName(i),rows[i].n));
    }
    assert(AW_CombatSettingIndex("FFATIGUEBASE")==0);       /* case-insensitive, as GMST names */
    assert(!AW_CombatSettingSet(&s,"fNoSuchSetting",1) && !AW_CombatSettingName(AW_COMBAT_SETTING_COUNT));
    assert(s.fNPCHealthBarFade==.5f && s.fCombatDelayNPC==.1f && s.iBlockMaxChance==50);
}
/* Mevil Molor's sheet (fixed stats; steel mace, chitin shield). */
static aw_fighter_t mevil(void) {
    static const unsigned char a[8]={62,56,36,63,78,47,35,40};
    static const unsigned char k[27]={47,15,15,15,32,37,32,32,52,6,16,6,6,6,11,6,6,38,6,6,38,11,33,11,19,6,38};
    aw_fighter_t f;memset(&f,0,sizeof(f));strcpy(f.id,"mevil molor");strcpy(f.name,"Mevil Molor");f.level=9;
    memcpy(f.attributes,a,8);memcpy(f.skills,k,27);
    f.health=f.health_max=94;f.fatigue=f.fatigue_max=208;f.weapon=4;f.weapon_skill=AW_SK_BLUNT;
    f.damage[0][0]=3;f.damage[0][1]=14;f.damage[1][0]=3;f.damage[1][1]=14;f.damage[2][0]=1;f.damage[2][1]=2;
    f.reach=1;f.speed=1.3f;f.weight=15;f.armor=8.814f;f.shield=1;f.aware=1;
    return f;
}
static aw_fighter_t player(void) {
    aw_fighter_t f;int i;memset(&f,0,sizeof(f));strcpy(f.name,"You");
    for(i=0;i<8;i++)f.attributes[i]=50;
    f.attributes[AW_LUC]=40;
    for(i=0;i<27;i++)f.skills[i]=10;
    f.skills[AW_SK_H2H]=30;
    f.health=f.health_max=60;f.fatigue=f.fatigue_max=200;f.weapon_skill=AW_SK_H2H;f.aware=1;
    f.armor=AW_CombatUnarmoredRating(&s,&f);
    return f;
}
/* A generator whose rolls are all low (hits) or all high (misses). */
static aw_combat_rng_t seeded_for(int low) {
    aw_combat_rng_t r,probe;unsigned long seed;int i,ok;
    for(seed=1;;seed++){
        AW_CombatSeed(&r,seed);probe=r;ok=1;
        for(i=0;i<4 && ok;i++){int v=AW_CombatRoll100(&probe);ok=low?v<5:v>95;}
        if(ok)return r;
    }
}
int main(void) {
    aw_fighter_t m,y;aw_swing_t out;aw_combat_rng_t r,q;int i,seen[100]={0},counts[3]={0};float before;
    settings();m=mevil();y=player();

    /* the generator: same seed, same rolls; range and spread */
    AW_CombatSeed(&r,1234);AW_CombatSeed(&q,1234);
    for(i=0;i<1000;i++){int a=AW_CombatRoll100(&r),b=AW_CombatRoll100(&q);assert(a==b && a>=0 && a<100);seen[a]=1;}
    for(i=0;i<100;i++)assert(seen[i]);
    AW_CombatSeed(&q,1235);assert(AW_CombatRoll100(&r)!=AW_CombatRoll100(&q) || AW_CombatRoll100(&r)!=AW_CombatRoll100(&q));
    AW_CombatSeed(&r,0);assert(r.state);                      /* zero seed remapped */
    for(i=0;i<1000;i++){float v=AW_CombatRoll01(&r);assert(v>=0 && v<=1);}
    assert(sizeof(aw_combat_rng_t)<=8);

    /* fatigue term: 1.25 at full, 0.75 at none, not below at negative */
    assert(near(AW_CombatFatigueTerm(&s,&m),1.25f));
    m.fatigue=104;assert(near(AW_CombatFatigueTerm(&s,&m),1.0f));
    m.fatigue=-20;assert(near(AW_CombatFatigueTerm(&s,&m),.75f));
    m.fatigue_max=0;assert(near(AW_CombatFatigueTerm(&s,&m),1.25f));   /* floor(max) 0: treated as full */
    m=mevil();

    /* hit chance: (32 + 63/5 + 40/10) * 1.25 - (50/5 + 40/10) * 1.25 = 60.75 - 17.5 -> 43 */
    assert(AW_CombatHitChance(&s,&m,&y)==43);
    y.knocked=1;assert(AW_CombatHitChance(&s,&m,&y)==61);y.knocked=0;     /* no evasion while down */
    y.aware=0;assert(AW_CombatHitChance(&s,&m,&y)==61);y.aware=1;
    y.fatigue=-1;assert(AW_CombatHitChance(&s,&m,&y)==61);y.fatigue=200;  /* evasion needs fatigue >= 0 */
    /* the player's punch: (30 + 10 + 4) * 1.25 - (63/5 + 4) * 1.25 = 55 - 20.75 -> 34 */
    assert(AW_CombatHitChance(&s,&y,&m)==34);

    /* reach in original units */
    assert(near(AW_CombatReach(&s,&m),128) && near(AW_CombatReach(&s,&y),128));
    /* unarmoured: (0.1 x 10) x (0.065 x 10) = 0.65 */
    assert(near(y.armor,.65f));

    /* a weapon hit: chop 3..14 at half swing 8.5, x (0.5 + 62 x 0.1 x 0.1) = 9.52, armour 0.65 -> 8.911 */
    r=seeded_for(1);m.skills[AW_SK_BLUNT]=200;
    before=m.fatigue;
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.outcome==AW_HIT_HEALTH && near(out.raw,9.52f) && near(out.damage,8.911f) && near(y.health,60-8.911f));
    assert(near(before-m.fatigue,2+15*.5f*.25f));             /* fFatigueAttackBase + weight x swing x mult */
    assert(!out.knockdown && !y.knocked);                       /* 50 x 0.5 = 25 > 8.9: no knockdown */
    m=mevil();y=player();

    /* a miss still costs the attacker fatigue; nothing else changes */
    r=seeded_for(0);
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,180,1,&r,&out);
    assert(out.outcome==AW_HIT_MISS && near(y.fatigue,198) && near(m.health,94) && near(m.fatigue,208));

    /* the punch: fatigue damage 30 x (0.1 + 0.4 x 0.5) = 9; to health only while down */
    r=seeded_for(1);y.skills[AW_SK_H2H]=200;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,180,1,&r,&out);
    assert(out.outcome==AW_HIT_FATIGUE && near(out.damage,60) && near(m.fatigue,148) && near(m.health,94));
    m.knocked=1;r=seeded_for(1);
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,180,1,&r,&out);
    /* 60 x 0.1 = 6, x 1.5 (down) = 9, armour 8.814: 9 x 9/17.814 = 4.547 */
    assert(out.outcome==AW_HIT_HEALTH && near(out.damage,4.547f) && near(m.health,94-4.547f));
    m=mevil();y=player();

    /* critical strike on an unaware victim: x4 (here then reduced by armour) */
    r=seeded_for(1);y.skills[AW_SK_H2H]=200;m.aware=0;m.shield=0;m.knocked=1;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,1,180,1,&r,&out);
    assert(out.critical && out.outcome==AW_HIT_HEALTH);
    m=mevil();y=player();

    /* blocking: shield, facing (-90..30), not busy; chance clamped 10..50 */
    r=seeded_for(1);y.skills[AW_SK_H2H]=200;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.block_chance==10 && out.outcome==AW_HIT_BLOCKED);  /* a 200-skill attacker: the minimum chance; low rolls still block */
    m=mevil();y=player();m.skills[AW_SK_BLOCK]=100;
    r=seeded_for(1);y.skills[AW_SK_H2H]=60;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.outcome==AW_HIT_BLOCKED && out.block_chance==50 && near(out.damage,0) && near(m.fatigue,204));
    m=mevil();y=player();m.skills[AW_SK_BLOCK]=100;
    r=seeded_for(1);y.skills[AW_SK_H2H]=60;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,90,1,&r,&out);      /* from his right side: no block */
    assert(out.blocked_roll<0 && out.outcome==AW_HIT_FATIGUE);
    m=mevil();y=player();m.skills[AW_SK_BLOCK]=100;m.attacking=1;
    r=seeded_for(1);y.skills[AW_SK_H2H]=60;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);       /* swinging: no block */
    assert(out.blocked_roll<0);
    m=mevil();y=player();

    /* knockdown: health damage at least agility x 0.5 and a roll at or above the odds */
    {
        aw_fighter_t weak=player();weak.attributes[AW_AGI]=0;      /* odds 50: rolls >= 50 knock down */
        aw_combat_rng_t probe;unsigned long seed;
        m.skills[AW_SK_BLUNT]=200;
        for(seed=1;;seed++){
            AW_CombatSeed(&r,seed);probe=r;
            if(AW_CombatRoll100(&probe)<5 && AW_CombatRoll100(&probe)>=60)break;
        }
        AW_CombatSwing(&s,&m,&weak,AW_ATTACK_CHOP,1,0,1,&r,&out);
        assert(out.outcome==AW_HIT_HEALTH && out.knockdown && weak.knocked==1);
    }
    m=mevil();y=player();

    /* death and knockout */
    r=seeded_for(1);m.skills[AW_SK_BLUNT]=200;y.health=1;
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_SLASH,1,0,1,&r,&out);
    assert(y.dead && y.health==0 && !y.knocked);
    r=seeded_for(1);AW_CombatSwing(&s,&m,&y,AW_ATTACK_SLASH,1,0,1,&r,&out);
    assert(out.outcome==AW_HIT_MISS && out.roll<0);               /* the dead take no hits */
    m=mevil();y=player();
    r=seeded_for(1);y.skills[AW_SK_H2H]=200;m.fatigue=10;m.shield=0;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,1,180,1,&r,&out);
    assert(m.knocked==2 && m.fatigue<0);
    /* fatigue return: 2.5 + 0.02 x 47 = 3.44 per second; up again above zero */
    before=m.fatigue;
    assert(!AW_CombatRecover(&s,&m,1) || m.fatigue>=0);
    assert(near(m.fatigue-before,3.44f) || m.fatigue>=0);
    for(i=0;i<100 && m.knocked;i++)AW_CombatRecover(&s,&m,1);
    assert(!m.knocked && m.fatigue>=0);
    m.fatigue=m.fatigue_max-1;AW_CombatRecover(&s,&m,10);assert(near(m.fatigue,m.fatigue_max));
    m.dead=1;m.fatigue=0;assert(!AW_CombatRecover(&s,&m,1) && m.fatigue==0);
    m=mevil();

    /* the attack pick weighs average damage: slash 8, chop 8, thrust 1 */
    AW_CombatSeed(&r,99);
    for(i=0;i<1700;i++)counts[AW_CombatBestAttack(&m,&r)]++;
    assert(counts[AW_ATTACK_THRUST]>20 && counts[AW_ATTACK_THRUST]<220);
    assert(counts[AW_ATTACK_CHOP]>600 && counts[AW_ATTACK_SLASH]>600);

    /* a fighter sheet stays small (bytes per actor) */
    assert(sizeof(aw_fighter_t)<=160);
    printf("combat rules ok: fighter %lu bytes, settings %lu bytes\n",(unsigned long)sizeof(aw_fighter_t),(unsigned long)sizeof(s));
    return 0;
}
