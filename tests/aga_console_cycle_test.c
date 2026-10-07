/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest=key_game;
client_static_t cls;
char key_lines[32][256];
int edit_line,key_linepos;
extern int con_fullscreen;
void Con_CycleConsole_f(void);
void Con_ToggleConsole_f(void);
void SCR_EndLoadingPlaque(void){}
void M_Menu_Main_f(void){key_dest=key_menu;}
int AW_RemoteLogging(void){return 0;}
const char *AW_RemoteConsoleLog(void){return "";}
int main(void){
    cls.state=ca_connected;
    Con_CycleConsole_f();assert(key_dest==key_console && !con_fullscreen);
    Con_CycleConsole_f();assert(key_dest==key_console && con_fullscreen);
    Con_CycleConsole_f();assert(key_dest==key_game);
    Con_CycleConsole_f();assert(key_dest==key_console && !con_fullscreen);
    Con_ToggleConsole_f();assert(key_dest==key_game); /* Escape closes half too. */
    Con_CycleConsole_f();Con_CycleConsole_f();Con_ToggleConsole_f();assert(key_dest==key_game);
    return 0;
}
