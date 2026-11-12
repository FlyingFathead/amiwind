/* SPDX-License-Identifier: GPL-2.0-or-later
 * READY-MAGIC-SHOWS-WEAPON-65: the weapon key (F) and the magic key (R) are exclusive stances (aw_hands.c
 * AW_HandReadyPress / AW_HandShowsWeapon, built with -DAW_HANDS_HOST_TEST). R shows the spell stance (hands up, no
 * weapon); F shows the weapon; switching between them keeps the hands up and swaps what they hold. */
#include <stdio.h>
#include <stdlib.h>
#include "../engine/aga/src/aw_hand_models.h"

static int failures;
#define CHECK(c) do{if(!(c)){printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#c);failures++;}}while(0)

int main(void) {
    int goal=0,magic=0;
    /* R from nothing: the hands come up, magic ready, no weapon */
    AW_HandReadyPress(AW_READY_MAGIC_KEY,&goal,&magic);
    CHECK(goal==1 && magic==1 && !AW_HandShowsWeapon(goal,magic));
    /* F from the spell stance: the magic goes, the hands stay up, the weapon shows */
    AW_HandReadyPress(AW_READY_WEAPON_KEY,&goal,&magic);
    CHECK(goal==1 && magic==0 && AW_HandShowsWeapon(goal,magic));
    /* R from the weapon stance: the weapon goes, the hands stay up, magic ready */
    AW_HandReadyPress(AW_READY_MAGIC_KEY,&goal,&magic);
    CHECK(goal==1 && magic==1 && !AW_HandShowsWeapon(goal,magic));
    /* R again: the magic and the hands go down */
    AW_HandReadyPress(AW_READY_MAGIC_KEY,&goal,&magic);
    CHECK(goal==0 && magic==0 && !AW_HandShowsWeapon(goal,magic));
    /* F from nothing: the weapon; F again: down */
    AW_HandReadyPress(AW_READY_WEAPON_KEY,&goal,&magic);
    CHECK(goal==1 && magic==0 && AW_HandShowsWeapon(goal,magic));
    AW_HandReadyPress(AW_READY_WEAPON_KEY,&goal,&magic);
    CHECK(goal==0 && magic==0 && !AW_HandShowsWeapon(goal,magic));
    /* the shared flag the engine reads starts lowered */
    CHECK(aw_magic_readied==0);
    if(failures)return 1;
    printf("ready magic: 7 checks passed\n");
    return 0;
}
