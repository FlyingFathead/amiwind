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
        {"fNPCHealthBarTime",3},{"fNPCHealthBarFade",.5f},{"fWeaponDamageMult",.1f},
        {"fCombatAngleXY",60},{"fCombatAngleZ",60},{"fCombatInvisoMult",.2f}};
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
    /* HIT-CHANCE-CHECK-62, the effects OpenMW 0.51 getHitChance counts: Fortify Attack 10 less Blind 3 on the attacker:
     * 60.75 + 7 - 17.5 = 50.25 -> 50 */
    m.attack_mod=7;assert(AW_CombatHitChance(&s,&m,&y)==50);m.attack_mod=0;
    /* Sanctuary 20 on the victim is evasion: 60.75 - (17.5 + 20) -> 23; at most 100: 60.75 - 117.5 -> -57; none while down */
    y.sanctuary=20;assert(AW_CombatHitChance(&s,&m,&y)==23);
    y.sanctuary=150;assert(AW_CombatHitChance(&s,&m,&y)==-57);
    y.knocked=1;assert(AW_CombatHitChance(&s,&m,&y)==61);y.knocked=0;y.sanctuary=0;
    /* Chameleon 50 x fCombatInvisoMult 0.2 = 10; Invisibility 1000 x 0.2 capped at 100 */
    assert(AW_CombatUnseen(&s,50,0)==10 && AW_CombatUnseen(&s,50,1000)==110 && AW_CombatUnseen(&s,-5,0)==0);
    y.unseen=AW_CombatUnseen(&s,50,0);
    assert(AW_CombatHitChance(&s,&m,&y)==33);                         /* 60.75 - 27.5 -> 33 */
    y.knocked=1;assert(AW_CombatHitChance(&s,&m,&y)==51);y.knocked=0;  /* down: no evasion, the unseen part stays */
    y.fatigue=-1;assert(AW_CombatHitChance(&s,&m,&y)==61);y.fatigue=200;y.unseen=0;   /* below 0 fatigue: no defence */
    /* the hit contact (OpenMW getHitContact, isInMeleeReach; angles 60 = sine 0.667): in front within reach */
    {float fw[3]={1,0,0},up[3]={.6f,0,.8f},down[3]={.5f,0,-.866f},to[3];
     to[0]=30;to[1]=0;to[2]=0;assert(AW_CombatContact(&s,to,39,33,15,0,32,0,fw));
     assert(AW_CombatContact(&s,to,39,33,15,0,32,0,down));            /* looking down at it: its body is in the cone */
     assert(!AW_CombatContact(&s,to,39,33,40,0,32,0,fw));             /* out of reach */
     assert(!AW_CombatContact(&s,to,39,33,15,40,32,0,fw));            /* feet 40 above: out of reach */
     to[0]=-30;assert(!AW_CombatContact(&s,to,39,33,15,0,32,0,fw));   /* behind */
     to[0]=20;to[1]=25;assert(!AW_CombatContact(&s,to,39,33,15,0,32,0,fw));   /* sine 0.78 to the side */
     to[0]=25;to[1]=15;assert(AW_CombatContact(&s,to,39,33,15,0,32,0,fw));    /* sine 0.51 */
     /* a flyer whose feet are 60 above (the flyer's 64 allowance): struck when looked up at, not when looking level */
     to[0]=20;to[1]=0;to[2]=60;
     assert(!AW_CombatContact(&s,to,39,20,10,60,32,0,up));            /* no allowance: out of reach */
     assert(!AW_CombatContact(&s,to,39,20,10,60,32,64,fw));
     assert(AW_CombatContact(&s,to,39,20,10,60,32,64,up));
     to[0]=0;to[2]=0;assert(AW_CombatContact(&s,to,39,33,0,0,32,0,fw));}   /* right over the feet */

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

    /* --- weapon and shield rules (see docs/COMBAT.md) --- */
    /* fists and two-handed weapons cannot block (OpenMW: hand to hand counts as two-handed) */
    m=mevil();
    assert(AW_CombatCanBlock(&s,&m,0) && !AW_CombatCanBlock(&s,&m,-91) && !AW_CombatCanBlock(&s,&m,31));
    m.weapon=0;assert(!AW_CombatCanBlock(&s,&m,0));                     /* fists */
    m.weapon=3;assert(!AW_CombatCanBlock(&s,&m,0));                     /* long blade two-handed */
    m.weapon=9;assert(!AW_CombatCanBlock(&s,&m,0));                     /* two-handed axe */
    m.weapon=8;assert(AW_CombatCanBlock(&s,&m,0));                      /* one-handed axe */
    m.weapon=4;m.staggered=1;assert(!AW_CombatCanBlock(&s,&m,0));       /* hit recovery */
    m=mevil();
    {   /* RESIST-NORMAL-WEAPONS-61: OpenMW 0.51 combat.cpp resistNormalWeapon / isNormalWeapon */
        int no;aw_fighter_t at=mevil(),gh=mevil();aw_swing_t o;aw_combat_rng_t rr;float full;
        assert(AW_CombatIsNormalWeapon(0,0) && !AW_CombatIsNormalWeapon(AW_WEAPON_SILVER,0) &&
               !AW_CombatIsNormalWeapon(AW_WEAPON_MAGICAL,0) && !AW_CombatIsNormalWeapon(0,1));
        assert(AW_CombatNormalWeaponFactor(1,0,&no)==1 && !no);
        assert(AW_CombatNormalWeaponFactor(1,.5f,&no)==.5f && !no);
        assert(AW_CombatNormalWeaponFactor(1,1,&no)==0 && no);
        assert(AW_CombatNormalWeaponFactor(1,2.5f,&no)==0 && no);          /* min(1, ...) */
        assert(AW_CombatNormalWeaponFactor(1,-.25f,&no)==1.25f && !no);    /* a weakness: stronger */
        assert(AW_CombatNormalWeaponFactor(0,1,&no)==1 && !no);            /* silver, magical, enchanted: untouched */
        /* a swing with dice off: the full blow, then the same blow on a ghost that resists fully and half */
        aw_combat_dice=0;
        at.weapon=2;at.damage[0][0]=at.damage[0][1]=20;at.weapon_health=at.weapon_health_max=100;at.weapon_normal=1;
        gh.armor=0;gh.health=gh.health_max=1000;gh.aware=1;gh.resist_normal=0;
        AW_CombatSeed(&rr,7);AW_CombatSwing(&s,&at,&gh,0,1,0,0,&rr,&o);full=o.damage;assert(full>0 && !o.no_effect);
        gh.health=1000;gh.knocked=0;gh.resist_normal=100;at.weapon_health=100;          /* percent */
        AW_CombatSwing(&s,&at,&gh,0,1,0,0,&rr,&o);assert(o.damage==0 && o.no_effect && gh.health==1000);
        gh.resist_normal=50;gh.knocked=0;at.weapon_health=100;
        AW_CombatSwing(&s,&at,&gh,0,1,0,0,&rr,&o);assert(!o.no_effect && o.damage>0 && o.damage<full);
        at.weapon_normal=0;gh.resist_normal=100;gh.health=1000;gh.knocked=0;at.weapon_health=100;     /* a silver blade */
        AW_CombatSwing(&s,&at,&gh,0,1,0,0,&rr,&o);assert(!o.no_effect && o.damage==full);
        at.weapon=0;at.weapon_normal=0;gh.knocked=0;                                   /* fists: never resisted */
        AW_CombatSwing(&s,&at,&gh,0,1,0,0,&rr,&o);assert(!o.no_effect);
        aw_combat_dice=1;
    }
    {   /* GODMODE-COMBAT-DAMAGE-61: a god-mode player keeps health, fatigue and standing; its own swings are free */
        aw_fighter_t at=mevil(),pl=mevil(),before;aw_swing_t o;aw_combat_rng_t rr;
        aw_combat_dice=0;
        at.weapon=2;at.damage[0][0]=at.damage[0][1]=200;at.weapon_health=at.weapon_health_max=100;
        pl.armor=0;pl.health=pl.health_max=50;pl.aware=1;before=pl;
        AW_CombatSeed(&rr,3);AW_CombatSwing(&s,&at,&pl,0,1,0,0,&rr,&o);
        assert(o.damage>0 && pl.health<50);                                    /* the blow as resolved */
        AW_CombatGodVictim(&pl,&before,&o);
        assert(pl.health==50 && pl.fatigue==before.fatigue && !pl.knocked && !pl.dead && o.damage==0 && !o.knockdown);
        before=at;AW_CombatSwing(&s,&at,&pl,0,1,0,0,&rr,&o);
        assert(at.fatigue<before.fatigue && at.weapon_health<before.weapon_health);
        AW_CombatGodAttacker(&at,&before,&o);
        assert(at.fatigue==before.fatigue && at.weapon_health==before.weapon_health && at.weapon==2 && o.weapon_wear==0);
        aw_combat_dice=1;
    }
    {   /* GODMODE-LAVA-DEATH-62: world damage (lava, falls, drowning) is held back in god mode and counted; a script's
         * or a spell's loss of health never takes a god-mode player below what he had, a heal still lands */
        float held=0;
        assert(!AW_CombatGodWorldDamage(0,20,&held) && held==0);
        assert(AW_CombatGodWorldDamage(1,20,&held) && held==20);
        assert(AW_CombatGodWorldDamage(1,3.5f,&held) && held==23.5f);
        assert(!AW_CombatGodWorldDamage(1,0,&held) && held==23.5f);
        assert(AW_CombatGodWorldDamage(1,1,NULL));
        assert(AW_CombatGodHealth(0,50,0,100)==0);              /* SetHealth 0 without god mode: dead */
        assert(AW_CombatGodHealth(1,50,0,100)==50);             /* with it: kept */
        assert(AW_CombatGodHealth(1,50,-30,100)==50);
        assert(AW_CombatGodHealth(1,50,80,100)==80);            /* a heal lands */
        assert(AW_CombatGodHealth(1,50,40,40)==40);             /* the maximum drained to 40: capped there */
        assert(AW_CombatGodHealth(1,50,0,0.5f)==1);             /* never below 1 */
        /* v0.0.63-dev3: health 100 over an unchanged maximum 40 (the caller passes 0: the maximum did not fall);
         * ModCurrentHealth -50 and -20 are held back */
        assert(AW_CombatGodHealth(1,100,50,0)==100);
        assert(AW_CombatGodHealth(1,99,79,0)==99);
        assert(AW_CombatGodHealth(0,100,50,0)==50);
    }
    /* bow 10 and crossbow 11 are two-handed (weapontype.cpp), thrown 12 is not */
    for(i=1;i<=12;i++)assert(AW_TWO_HANDED(i)==(i==3 || i==5 || i==6 || i==7 || i==9 || i==10 || i==11));
    /* the player's attack type by movement (forward/back beats sideways by 0.2) and best attack */
    assert(AW_CombatMovementAttack(1,0)==AW_ATTACK_THRUST && AW_CombatMovementAttack(-1,0)==AW_ATTACK_THRUST);
    assert(AW_CombatMovementAttack(0,1)==AW_ATTACK_SLASH && AW_CombatMovementAttack(0,-.5f)==AW_ATTACK_SLASH);
    assert(AW_CombatMovementAttack(0,0)==AW_ATTACK_CHOP && AW_CombatMovementAttack(1,1)==AW_ATTACK_CHOP);
    assert(AW_CombatMovementAttack(.5f,.35f)==AW_ATTACK_CHOP && AW_CombatMovementAttack(.6f,.35f)==AW_ATTACK_THRUST);
    /* best attack: steel longsword chop 2-14 (16), slash 1-20 (21), thrust 4-18 (22) -> thrust */
    {aw_fighter_t w=mevil();w.weapon=2;w.damage[0][0]=2;w.damage[0][1]=14;w.damage[1][0]=1;w.damage[1][1]=20;w.damage[2][0]=4;w.damage[2][1]=18;
     assert(AW_CombatBestAttackPlayer(&w)==AW_ATTACK_THRUST);
     w.damage[2][1]=10;assert(AW_CombatBestAttackPlayer(&w)==AW_ATTACK_SLASH);
     w.damage[0][1]=30;assert(AW_CombatBestAttackPlayer(&w)==AW_ATTACK_CHOP);
     w.damage[0][0]=w.damage[1][0]=w.damage[2][0]=1;w.damage[0][1]=w.damage[1][1]=w.damage[2][1]=9;
     assert(AW_CombatBestAttackPlayer(&w)==AW_ATTACK_SLASH);              /* all equal */
     w.weapon=0;assert(AW_CombatBestAttackPlayer(&w)==AW_ATTACK_CHOP);}   /* no best attack for fists */
    /* condition: damage x condition ratio; wear max(1, 0.1 x damage) per hit; a miss in reach wears 1 */
    m=mevil();y=player();m.skills[AW_SK_BLUNT]=200;m.weapon_health=900;m.weapon_health_max=1800;
    r=seeded_for(1);
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(near(out.raw,9.52f*.5f) && near(out.weapon_wear,1) && near(m.weapon_health,899));
    m.weapon_health=m.weapon_health_max=1800;m.damage[0][1]=200;r=seeded_for(1);y=player();
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_CHOP,1,0,1,&r,&out);              /* 200 x 1.12 = 224 -> wear 22 */
    assert(near(out.weapon_wear,22) && near(m.weapon_health,1778));
    m=mevil();y=player();m.weapon_health=m.weapon_health_max=1800;r=seeded_for(0);
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_CHOP,1,0,1,&r,&out);
    assert(out.outcome==AW_HIT_MISS && near(m.weapon_health,1799));
    m.weapon_health=1;m.skills[AW_SK_BLUNT]=200;r=seeded_for(1);y=player();
    AW_CombatSwing(&s,&m,&y,AW_ATTACK_CHOP,1,0,1,&r,&out);
    assert(out.weapon_broke && !m.weapon && m.weapon_skill==AW_SK_H2H);     /* broken: unequipped, fists */
    /* shield wear on a block: loses the blocked damage; at 0 it is gone */
    m=mevil();y=player();m.skills[AW_SK_BLOCK]=100;m.shield_health=m.shield_health_max=5;
    y.weapon=2;y.weapon_skill=AW_SK_LONG;y.skills[AW_SK_LONG]=60;y.damage[0][0]=20;y.damage[0][1]=20;y.weight=20;
    r=seeded_for(1);
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,1,0,1,&r,&out);
    assert(out.outcome==AW_HIT_BLOCKED && out.shield_broke && !m.shield && near(m.shield_health,0));
    assert(near(m.fatigue,208-4-20*1*1));                                 /* fFatigueBlockBase + weight x swing x mult */
    /* a miss is classified for the AmiWind style: block-like with a usable shield, else dodge */
    m=mevil();y=player();r=seeded_for(0);
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.outcome==AW_HIT_MISS && out.miss_style==2);
    m.shield=0;r=seeded_for(0);AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.outcome==AW_HIT_MISS && out.miss_style==1);
    /* dice off (AmiWind extension): every swing in reach hits, no block, knockdown by threshold only */
    aw_combat_dice=0;
    m=mevil();y=player();m.skills[AW_SK_BLOCK]=100;r=seeded_for(0);       /* rolls that would all miss */
    y.skills[AW_SK_H2H]=1;y.attributes[AW_AGI]=0;
    AW_CombatSwing(&s,&y,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&out);
    assert(out.outcome==AW_HIT_FATIGUE && out.roll==-2 && out.blocked_roll<0);
    {aw_fighter_t weak=player();weak.attributes[AW_AGI]=10;m=mevil();m.skills[AW_SK_BLUNT]=5;r=seeded_for(0);
     AW_CombatSwing(&s,&m,&weak,AW_ATTACK_CHOP,1,0,1,&r,&out);           /* 14 x 1.12 = 15.7 vs 10 x 0.5: down */
     assert(out.outcome==AW_HIT_HEALTH && out.knockdown && weak.knocked==1);}
    aw_combat_dice=1;
    m=mevil();y=player();

    /* aggro and flee (the combat playground): the original settings iFightDistanceBase 20, fFightDistanceMultiplier
     * 0.005, fFightDispMult 0.2, fAIFleeHealthMult 7, fAIFleeFleeMult 0.3, fAIMeleeWeaponMult 2, fAIMeleeArmorMult 1 */
    {
        static const float values[AW_COMBAT_AI_COUNT]={20,.005f,.2f,7,.3f,2,1};
        aw_combat_ai_t a;memset(&a,0,sizeof(a));
        assert(sizeof(a)==AW_COMBAT_AI_COUNT*sizeof(float));
        for(i=0;i<AW_COMBAT_AI_COUNT;i++)assert(AW_CombatAiSet(&a,AW_CombatAiName(i),values[i]));
        assert(!AW_CombatAiSet(&a,"fNoSuchSetting",1) && !AW_CombatAiName(AW_COMBAT_AI_COUNT));
        assert(AW_CombatAiSet(&a,"IFIGHTDISTANCEBASE",20) && a.fAIMeleeArmorMult==1);
        /* Fight + (int)(20 - 0.005 x distance + (50 - disposition) x 0.2); hostile at 100 */
        assert(AW_CombatFightRating(&a,90,50,600)==107);
        assert(AW_CombatFightRating(&a,90,50,2000)==100);
        assert(AW_CombatFightRating(&a,90,50,4000)==90);
        assert(AW_CombatFightRating(&a,90,30,4000)==94);           /* a low disposition raises it */
        assert(AW_CombatFightRating(&a,90,70,2000)==96);           /* a high one lowers it */
        assert(AW_CombatFightRating(&a,30,50,0)==50);              /* a townsperson never attacks on sight */
        /* flee: Mevil (steel mace, Blunt 32, armour 8.814) rates his weapon 14 x 0.32 x 2 + 8.814 = 17.77 */
        m=mevil();
        assert(near(AW_CombatAntiFleeRating(&a,&m),17.774f));
        m.flee=30;m.health=18.8f;                                  /* 20 % health: 0.8 x 7 + 9 + 18 at 400 = 32.6 */
        assert(near(AW_CombatFleeRating(&a,&m,400),32.6f) && !AW_CombatFleeDecision(&a,&m,400));
        m.flee=0;m.health=m.health_max;
        assert(AW_CombatFleeRating(&a,&m,400)==0);                 /* no distance term on a zero rating */
        m.flee=100;assert(AW_CombatFleeRating(&a,&m,400)==100 && AW_CombatFleeDecision(&a,&m,400));
        m.weapon=0;m.armor=0;m.flee=30;m.health=1;                 /* hand to hand rates 0, a low rating counts as 0 */
        assert(AW_CombatAntiFleeRating(&a,&m)==0 && !AW_CombatFleeDecision(&a,&m,400));
        m=mevil();
    }

    {   /* the swing's sounds (OpenMW 0.51 character.cpp playSwishSound, combat.cpp blockMeleeAttack and
         * getHandToHandDamage, local.lua pickRandomArmor, applyArmor and onHit) */
        aw_swing_t o;aw_fighter_t v=mevil();int list[4],n;
        static const int bands[][2]={{0,0},{29,0},{30,1},{39,1},{40,2},{50,3},{60,4},{70,5},{80,6},{84,6},{85,7},{89,7},{90,8},{99,8}};
        for(n=0;n<(int)(sizeof(bands)/sizeof(bands[0]));n++)assert(AW_CombatArmorHitSlot(bands[n][0])==bands[n][1]);
        v.hit_classes=1u|(3u<<2)|(2u<<16);                         /* light cuirass, heavy helmet, medium shield; rest empty */
        n=AW_CombatSwingSounds(NULL,NULL,1,0,list);assert(n==1 && list[0]==AW_SND_SWISH);   /* reached nobody */
        memset(&o,0,sizeof(o));o.outcome=AW_HIT_MISS;
        n=AW_CombatSwingSounds(&o,&v,1,0,list);assert(n==2 && list[0]==AW_SND_SWISH && list[1]==AW_SND_MISS);
        n=AW_CombatSwingSounds(&o,&v,0,0,list);assert(n==1);       /* an NPC's miss: the swing only */
        o.outcome=AW_HIT_BLOCKED;v.shield_class=1;
        n=AW_CombatSwingSounds(&o,&v,0,0,list);assert(n==2 && list[1]==AW_SND_MEDIUM);
        o.outcome=AW_HIT_FATIGUE;
        n=AW_CombatSwingSounds(&o,&v,1,0,list);assert(n==2 && list[1]==AW_SND_PUNCH);
        n=AW_CombatSwingSounds(&o,&v,1,128,list);assert(n==2 && list[1]==AW_SND_PUNCH2);
        o.outcome=AW_HIT_HEALTH;
        n=AW_CombatSwingSounds(&o,&v,1,10,list);                   /* roll 10: the cuirass, light */
        assert(n==3 && list[1]==AW_SND_LIGHT && list[2]==AW_SND_HEALTH);
        n=AW_CombatSwingSounds(&o,&v,1,35,list);assert(n==3 && list[1]==AW_SND_HEAVY);   /* the helmet */
        n=AW_CombatSwingSounds(&o,&v,1,55,list);assert(n==2 && list[1]==AW_SND_HEALTH);  /* bare boots: no armour sound */
        o.critical=1;n=AW_CombatSwingSounds(&o,&v,1,95,list);
        assert(n==4 && list[1]==AW_SND_MEDIUM && list[2]==AW_SND_HEALTH && list[3]==AW_SND_CRITICAL);
    }

    {   /* creatures (COMBAT-DAEDROTH-NO-HIT-51; OpenMW mwclass/creature.cpp hit, getSkill, getArmorRating) */
        aw_actor_base_t b;aw_fighter_t c,m=mevil();aw_swing_t o;aw_combat_rng_t r;int i;
        memset(&b,0,sizeof(b));
        b.kind=0;b.health=10;assert(!AW_CombatCreatureSheet(&b,"npc",&c));           /* an NPC row: not here */
        b.kind=1;b.level=16;b.health=180;b.fatigue=400;b.fight=90;
        for(i=0;i<8;i++)b.attributes[i]=300;                                          /* clamped to 255 */
        for(i=0;i<27;i++)b.skills[i]=70;
        b.attack[0]=15;b.attack[1]=35;b.attack[2]=10;b.attack[3]=20;b.attack[4]=300;b.attack[5]=400;
        assert(AW_CombatCreatureSheet(&b,"daedroth",&c) && c.creature==1 && c.attributes[0]==255 && c.armor==0);
        assert(c.damage[0][0]==15 && c.damage[0][1]==35 && c.damage[2][0]==255 && !c.weapon && c.health==180);
        /* its own attack: min + (max - min) x strength as health damage, no strength modifier (dice off: a hit) */
        aw_combat_dice=0;AW_CombatSeed(&r,1);m.armor=0;m.aware=1;
        AW_CombatSwing(&s,&c,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&o);
        assert(o.outcome==AW_HIT_HEALTH && near(o.raw,25));
        m=mevil();
        b.flags=AWR_BIPEDAL;assert(AW_CombatCreatureSheet(&b,"bip",&c) && c.creature==2);
        AW_CombatSwing(&s,&c,&m,AW_ATTACK_CHOP,.5f,0,1,&r,&o);
        assert(o.outcome==AW_HIT_FATIGUE);                                            /* bipedal: hand to hand */
        m=mevil();
        /* the creature as the victim: no armour, so the whole blow lands */
        b.flags=0;AW_CombatCreatureSheet(&b,"daedroth",&c);
        AW_CombatSwing(&s,&m,&c,AW_ATTACK_CHOP,1,0,1,&r,&o);
        assert(o.outcome==AW_HIT_HEALTH && near(o.damage,o.raw) && near(c.health,180-o.damage));
        aw_combat_dice=1;m=mevil();
    }

    /* a fighter sheet stays small (bytes per actor) */
    assert(sizeof(aw_fighter_t)<=184);   /* +4 since v0.0.63: the hit chance's effect terms (HIT-CHANCE-CHECK-62) */
    printf("combat rules ok: fighter %lu bytes, settings %lu bytes\n",(unsigned long)sizeof(aw_fighter_t),(unsigned long)sizeof(s));
    return 0;
}
