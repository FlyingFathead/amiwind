/* SPDX-License-Identifier: GPL-2.0-or-later
 * READY-MAGIC-SHOWS-WEAPON-65: the weapon key (F) and the magic key (R) are exclusive stances (aw_hands.c
 * AW_HandReadyPress / AW_HandShowsWeapon, built with -DAW_HANDS_HOST_TEST). R shows the spell stance (hands up, no
 * weapon); F shows the weapon; switching between them keeps the hands up and swaps what they hold. The arms drawn
 * (aw_hand_models.c AW_HandView, -DAW_BLOCK_HOST_TEST): R the spell stance whatever is equipped. */
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
    /* PLAYER-CASTING-59: the spell leaves on the cast clip's release frame (6 of 10): the first time the clip's frame
     * reaches it; the cast by range starts on target */
    {
        aw_hand_table_t t={{0,8,14,18},{8,6,4,10},{1.f,.5f,.4f,1.f}};
        float r=AW_HandCastRelease(&t);
        CHECK(r>.59f && r<.61f);
        CHECK(AW_HandClipFrame(&t,AW_HAND_PUNCH,r+.001f)==18+AW_HAND_CAST_RELEASE_FRAME);
        CHECK(AW_HandClipFrame(&t,AW_HAND_PUNCH,r-.01f)==18+AW_HAND_CAST_RELEASE_FRAME-1);
        CHECK(aw_magic_cast_range==2);
    }
    /* READY-MAGIC-SHOWS-WEAPON-65 (v0.0.66; aw_hand_models.c AW_HandView, AW_HandCarriesLeft, with -DAW_BLOCK_HOST_TEST):
     * R ignores whatever is equipped and shows the spell stance (the open hands): with the weapon drawn before, a torch
     * lit, a held light, or all of them; the left hand's torch, light or shield is put away while magic is ready. F
     * brings them back: the torch's arms, the held light's stance, else the weapon or the fists. v0.0.66-dev1 checked the
     * lit torch and the held light first: with either in the left hand, R showed the right hand's fist. */
    {
        int torch,light;
        goal=0;magic=0;
        AW_HandReadyPress(AW_READY_WEAPON_KEY,&goal,&magic);        /* F: the weapon drawn */
        AW_HandReadyPress(AW_READY_MAGIC_KEY,&goal,&magic);         /* R: the weapon goes */
        CHECK(magic==1 && !AW_HandShowsWeapon(goal,magic));
        for(torch=0;torch<2;torch++)for(light=0;light<2;light++)
            CHECK(AW_HandView(magic,torch,light)==AW_HAND_VIEW_SPELL);
        CHECK(!AW_HandCarriesLeft(magic));
        AW_HandReadyPress(AW_READY_WEAPON_KEY,&goal,&magic);        /* F: the magic goes, the left hand's light is back */
        CHECK(magic==0 && AW_HandCarriesLeft(magic));
        CHECK(AW_HandView(magic,1,0)==AW_HAND_VIEW_TORCH);
        CHECK(AW_HandView(magic,0,1)==AW_HAND_VIEW_LIGHT);
        CHECK(AW_HandView(magic,1,1)==AW_HAND_VIEW_TORCH);
        CHECK(AW_HandView(magic,0,0)==AW_HAND_VIEW_HANDS);
    }
    if(failures)return 1;
    printf("ready magic: 22 checks passed\n");
    return 0;
}
