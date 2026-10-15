/* SPDX-License-Identifier: GPL-2.0-or-later
 * Include the real formatter; resolve live no-dice outcomes through real rules.
 * No duplicate formatter or simulated combat implementation. */
#include <assert.h>
#include <stdarg.h>
#include "aw_combat.c"
static char output[2048];static int used;
void Con_Printf(char *format,...){
    va_list ap;int n;va_start(ap,format);
    n=vsnprintf(output+used,sizeof(output)-used,format,ap);va_end(ap);
    assert(n>=0 && n<(int)sizeof(output)-used);used+=n;
}
static void clear_output(void){used=0;output[0]=0;}
int main(void){
    aw_combat_settings_t settings;aw_fighter_t a,v,as,vs;
    aw_combat_rng_t random;aw_swing_t swing,saved;float before;
    memset(&settings,0,sizeof(settings));memset(&a,0,sizeof(a));memset(&v,0,sizeof(v));
    settings.fFatigueBase=1.25f;settings.fFatigueMult=.5f;
    settings.fMinHandToHandMult=.1f;settings.fMaxHandToHandMult=.5f;
    settings.fFatigueAttackBase=2;settings.fDamageStrengthBase=1;
    settings.fCombatArmorMinMult=.25f;settings.fCombatCriticalStrikeMult=1;
    a.skills[AW_SK_H2H]=30;a.fatigue=a.fatigue_max=200;
    v.health=v.health_max=1000;v.fatigue=v.fatigue_max=1000;v.aware=1;
    AW_CombatSeed(&random,123);aw_combat_dice=0;readout.value=1;
    before=v.fatigue;AW_CombatSwing(&settings,&a,&v,0,1,0,1,&random,&swing);
    assert(swing.roll==-2 && swing.outcome==AW_HIT_FATIGUE && v.fatigue<before);
    saved=swing;as=a;vs=v;clear_output();print_swing("You","Living",0,&swing);
    assert(strstr(output,"no dice fatigue") && strstr(output,"15.0 fatigue"));
    assert(!strstr(output,"already down") && !memcmp(&saved,&swing,sizeof(swing)));
    assert(!memcmp(&as,&a,sizeof(a)) && !memcmp(&vs,&v,sizeof(v)));
    a.weapon=2;a.weapon_skill=AW_SK_LONG;a.weapon_health=a.weapon_health_max=100;
    a.damage[0][0]=a.damage[0][1]=10;
    before=v.health;AW_CombatSwing(&settings,&a,&v,0,1,0,1,&random,&swing);
    assert(swing.roll==-2 && swing.outcome==AW_HIT_HEALTH && v.health<before);
    clear_output();print_swing("You","Living",0,&swing);
    assert(strstr(output,"no dice HIT") && strstr(output,"10.0 health") && !strstr(output,"already down"));
    v.dead=1;AW_CombatSwing(&settings,&a,&v,0,1,0,1,&random,&swing);
    assert(swing.roll==-1);clear_output();print_swing("You","Dead",0,&swing);
    assert(strstr(output,"already down") && !strstr(output,"no dice"));
    /* Ordinary resolved hit/miss/block formatting retains its outcome and roll. */
    memset(&swing,0,sizeof(swing));swing.blocked_roll=-1;swing.roll=7;swing.chance=55;swing.outcome=AW_HIT_MISS;
    clear_output();print_swing("You","Living",0,&swing);assert(strstr(output,"chance 55 roll 7 miss"));
    swing.outcome=AW_HIT_HEALTH;swing.damage=3.5f;
    clear_output();print_swing("You","Living",0,&swing);assert(strstr(output,"chance 55 roll 7 HIT") && strstr(output,"3.5 health"));
    swing.outcome=AW_HIT_BLOCKED;swing.blocked_roll=27;swing.block_chance=50;swing.damage=0;
    clear_output();print_swing("You","Living",0,&swing);assert(strstr(output,"BLOCKED") && strstr(output,"block 27/50"));
    readout.value=0;clear_output();print_swing("You","Living",0,&swing);assert(!output[0]);
    puts("real no-dice readout, dead, normal outcome and disabled controls pass");return 0;
}
