/* SPDX-License-Identifier: GPL-2.0-or-later
 * Exercise the actual client button handlers with console-release sequences.
 */
#include "quakedef.h"
#include <assert.h>
int AW_SceneUse(void){return 0;}
extern void IN_AWUseDown(void), IN_AWUseUp(void);
extern int in_impulse;
extern kbutton_t in_up, in_attack, in_forward, in_mlook;
keydest_t key_dest;
char *Cmd_Argv(int n) {return "101";}
void Con_Printf(char *fmt, ...) {}
int main(void) {
    key_dest=key_game;IN_AWUseDown();
    assert(in_impulse==201 && (in_up.state&1));
    in_impulse=0;IN_AWUseDown();assert(!in_impulse);
    key_dest=key_console;IN_AWUseUp();
    assert(!in_impulse && !(in_up.state&1));
    /* Typing E in a console has no button-down but still delivers key-up. */
    IN_AWUseUp();assert(!in_impulse && !(in_up.state&1));
    IN_AWUseDown();assert(!in_impulse && !(in_up.state&1));
    key_dest=key_game;IN_AWUseDown();assert(in_impulse==201);
    in_impulse=0;IN_AWUseUp();assert(!in_impulse && !(in_up.state&1));
    in_forward.state=in_attack.state=in_mlook.state=1;in_impulse=202;
    IN_AWClearButtons();assert(!in_forward.state && !in_attack.state && !in_up.state && !in_impulse);
    assert(in_mlook.state==1);
    return 0;
}

int AW_IntroUse(void){return 0;}
