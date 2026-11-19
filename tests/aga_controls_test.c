/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include <assert.h>
static int locked,character,debug;
client_state_t cl;
int AW_OpeningLocked(void){return locked;}
void AW_OpeningDockStatus(void){}
int AW_OpeningDockRouteArg(const char *word){return 0;}   /* PIER-GUARD-POST-STUCK-67 */
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
    {   /* MWSCRIPT-PLAYER-CONTROL-62: the scripts' switches over a released game, and beside the opening's rule */
        usercmd_t cmd;
        AW_StoryReset(0);
        cmd.forwardmove=cmd.sidemove=cmd.upmove=200;AW_IntroMove(&cmd);assert(cmd.forwardmove==200);
        assert(AW_ControlSet(AW_CONTROL_PLAYER,0));
        AW_IntroMove(&cmd);assert(!cmd.forwardmove && !cmd.sidemove && !cmd.upmove);
        assert(!AW_IntroButtons(3) && !AW_IntroImpulse(202) && AW_IntroImpulse(201)==201);
        assert(AW_ControlSet(AW_CONTROL_PLAYER,1) && AW_ControlSet(AW_CONTROL_JUMPING,0));
        assert(AW_IntroButtons(3)==1 && AW_IntroImpulse(202)==202);           /* jumping off: no jump */
        assert(AW_ControlSet(AW_CONTROL_JUMPING,1) && AW_ControlSet(AW_CONTROL_FIGHTING,0));
        assert(AW_IntroButtons(3)==2 && !AW_IntroImpulse(202));               /* fighting off: no attack, no readying */
        assert(AW_ControlSet(AW_CONTROL_FIGHTING,1) && AW_ControlSet(AW_CONTROL_LOOKING,0));
        cl.viewangles[0]=30;cl.viewangles[1]=120;cmd.forwardmove=100;AW_IntroMove(&cmd);
        assert(cl.viewangles[0]==0 && cl.viewangles[1]==0 && cmd.forwardmove==100);   /* rotation 0, still walks */
        cl.viewangles[1]=45;AW_IntroMove(&cmd);assert(cl.viewangles[1]==0);    /* the mouse does not turn */
        assert(AW_ControlSet(AW_CONTROL_LOOKING,1));cl.viewangles[1]=45;AW_IntroMove(&cmd);assert(cl.viewangles[1]==45);
        /* in the registration the opening's rule still holds when every script switch is on */
        AW_StoryReset(1);assert(!AW_ControlsDisabled() && !AW_IntroButtons(3) && !AW_IntroImpulse(202));
        AW_StoryReset(0);debug=1;assert(AW_ControlSet(AW_CONTROL_PLAYER,0) && AW_IntroButtons(3)==3);   /* the test input wins */
        debug=0;
    }
    {   /* OPENING-FIGHTING-ON-BEFORE-PAPERS-66: the carried CharGen's switches (the compiler's NGCS row) at the new game's
         * start, and only then; the opening's own rule stays beside them */
        const int chargen=AW_CONTROL_PLAYER|AW_CONTROL_FIGHTING|AW_CONTROL_JUMPING|AW_CONTROL_MAGIC|
                          AW_CONTROL_VIEWSWITCH|AW_CONTROL_VANITY;
        AW_StoryReset(1);assert(AW_StoryNewGameControls(chargen,0) && AW_ControlsDisabled()==chargen);
        assert(!AW_ControlAllowed(AW_CONTROL_FIGHTING) && !AW_IntroButtons(3) && !AW_IntroImpulse(202));
        /* the papers' own script (OnPCAdd) switches fighting and magic on again; the rest stays off */
        assert(AW_ControlSet(AW_CONTROL_FIGHTING,1) && AW_ControlSet(AW_CONTROL_MAGIC,1));
        assert(AW_ControlsDisabled()==(chargen&~(AW_CONTROL_FIGHTING|AW_CONTROL_MAGIC)));
        /* a quick start or a demo (no opening): none */
        AW_StoryReset(0);assert(!AW_StoryNewGameControls(chargen,0) && !AW_ControlsDisabled());
        /* an opening past the ship (a debug scene that begins on the pier): none */
        AW_StoryReset(1);assert(AW_StoryTransition(AW_STAGE_DOCK));
        assert(!AW_StoryNewGameControls(chargen,0) && !AW_ControlsDisabled());
        /* CharGenState -1 (released, or OpenMW's new game that skips the character generation): none */
        AW_StoryReset(1);assert(AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1));
        assert(!AW_StoryNewGameControls(chargen,0) && !AW_ControlsDisabled());
        /* the row's second mask switches on */
        AW_StoryReset(1);assert(AW_ControlSet(AW_CONTROL_LEVITATION,0));
        assert(AW_StoryNewGameControls(AW_CONTROL_FIGHTING,AW_CONTROL_LEVITATION) && AW_ControlsDisabled()==AW_CONTROL_FIGHTING);
        /* New Game clears them again, as at a fresh boot */
        AW_StoryReset(1);assert(!AW_ControlsDisabled());
    }
    return 0;
}
