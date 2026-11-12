/* SPDX-License-Identifier: GPL-2.0-or-later
 * OPENING-VANITY-CAMERA-64: a New Game through the game-state reset (aw_reset.c, the story module first as aw_loadfail.c
 * registers it, then the later modules) leaves the opening restricted: on the prison ship and on the Seyda Neen pier,
 * before the race is chosen, the view switch and the idle orbit are not allowed (aw_view.c returns before both while
 * AW_StoryViewAllowed is 0). The bug: a later module reset the story again in its restart form. */
#include <assert.h>
#include <string.h>
#include "aw_story.h"
#include "aw_state.h"
#include "aw_reset.h"


static void reset_story(int new_game){AW_StoryReset(new_game);}
static int later_resets;
static void reset_later(int new_game){(void)new_game;later_resets++;}   /* the modules after it: none touches the story */
static void reset_last(int new_game){(void)new_game;later_resets++;}

int main(void){
    assert(AW_ResetRegister("story and globals",reset_story,NULL));
    assert(AW_ResetRegister("scene loads",reset_later,NULL));
    assert(AW_ResetRegister("scripts and actors",reset_last,NULL));
    /* New Game: the prison ship */
    assert(AW_ResetAll(1)==3 && later_resets==2);
    assert(aw_story.stage==AW_STAGE_SHIP);
    assert(AW_StateGet(&aw_state,AW_GLOBAL,"CharGenState")==10);
    assert(AW_StoryRestricted());
    assert(!AW_StoryViewAllowed());                 /* no view switch, no idle orbit on the ship */
    /* the pier, still before the race is chosen */
    assert(AW_StoryTransition(AW_STAGE_DOCK) && aw_story.stage==AW_STAGE_DOCK);
    assert(AW_StoryRestricted() && !AW_StoryViewAllowed());
    /* dbg restartgame's form (the main menu, no opening): nothing restricted */
    AW_ResetAll(0);
    assert(aw_story.stage==AW_STAGE_DEMO && !AW_StoryRestricted() && AW_StoryViewAllowed());
    /* and the bug's sequence, for the record: the story reset again in its restart form after the New Game form frees
     * the opening, which is what the scene module did before the fix */
    AW_ResetAll(1);AW_StoryReset(0);
    assert(!AW_StoryRestricted() && AW_StoryViewAllowed());
    return 0;
}
