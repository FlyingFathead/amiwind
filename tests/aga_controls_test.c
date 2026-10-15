/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include <assert.h>
static int locked,character,debug;
int AW_OpeningLocked(void){return locked;}
int AW_CharacterActive(void){return character;}
int AW_DebugTestInputActive(void){return debug;}
int main(void)
{
    AW_StoryReset(1);
    assert(!AW_StoryDoor(119513));
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    assert(AW_StoryTransition(AW_STAGE_DOCK));
    assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    aw_story.stage=AW_STAGE_OFFICE;assert(!AW_StoryDoor(119513));
    aw_story.stage=AW_STAGE_PAPERS;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    assert(AW_ItemAdd(&aw_state,"chargen statssheet",1));
    assert(AW_StoryTransition(AW_STAGE_COURTYARD));
    assert(!aw_story.hall && !AW_StoryDoor(119513));
    assert(AW_IntroButtons(3)==1 && AW_IntroImpulse(202)==202); /* pickup, before guard */
    aw_story.hall=1;
    assert(AW_StoryRestricted() && AW_IntroButtons(3)==1 && AW_IntroImpulse(202)==202);
    locked=1;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));locked=0;
    character=1;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));character=0;
    aw_story.stage=AW_STAGE_CAPTAIN;
    assert(AW_CaptainDuties() && AW_StoryTransition(AW_STAGE_RELEASED));
    assert(AW_StoryDoor(119513));
    assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    AW_StoryReset(0);assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    AW_StoryReset(1);debug=1;assert(AW_IntroButtons(3)==3 && AW_IntroImpulse(202)==202);
    character=1;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));character=0;
    debug=0;assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202));
    return 0;
}
