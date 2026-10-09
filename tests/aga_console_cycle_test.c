/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest=key_game;
client_static_t cls;
char key_lines[32][256];
int edit_line,history_line,key_linepos;
extern int con_fullscreen;
void Con_CycleConsole_f(void);
void Con_ToggleConsole_f(void);
void SCR_EndLoadingPlaque(void){}
void M_Menu_Main_f(void){key_dest=key_menu;}
static int terminal=1;
int Q_strlen(char *s){return strlen(s);} void Q_strcpy(char *a,char *b){strcpy(a,b);}
int Key_ConsoleTerminal(void){return terminal;}
double realtime;
extern int con_linewidth,con_vislines;
extern float con_cursorspeed;
static char drawn[64];
int AW_ConsoleCharHeight(void){return 8;} int AW_ConsoleCharWidth(void){return 4;}
void AW_ConsoleCharacter(int x,int y,int c){if(x/4-1<(int)sizeof drawn)drawn[x/4-1]=(char)c;}
void Con_DrawInput(void);
/* Draw the input line at a blink phase; returns the drawn characters. */
static const char *draw(double time){
    realtime=time;memset(drawn,0,sizeof drawn);Con_DrawInput();return drawn;
}
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
    /* Opening or closing starts the next Up from the newest command
     * (CONSOLE-HISTORY-EMPTY-32), not from where a history walk stopped. */
    edit_line=5;history_line=2;Con_CycleConsole_f();assert(key_dest==key_console && history_line==5);
    history_line=3;Con_ToggleConsole_f();assert(key_dest==key_game && history_line==5);
    /* Terminal drawing keeps the text after the cursor (aw_console_mode 1);
     * the cursor blinks over the character under it. Classic id drawing
     * ends the line at the cursor. */
    key_dest=key_console;con_linewidth=12;con_vislines=100;con_cursorspeed=4;
    strcpy(key_lines[edit_line],"]echo hi");key_linepos=3;
    assert(!memcmp(draw(0),"]echo hi    ",12));
    assert(!memcmp(draw(0.25),"]ec\vo hi    ",12));	/* 11: block cursor */
    assert(!strcmp(key_lines[edit_line],"]echo hi"));
    key_linepos=8;assert(!memcmp(draw(0),"]echo hi\n   ",12));	/* 10 at the end */
    strcpy(key_lines[edit_line],"]a long command line");key_linepos=20;	/* scrolls with the cursor */
    assert(!memcmp(draw(0),"ommand line\n",12) && !strcmp(key_lines[edit_line],"]a long command line"));
    terminal=0;key_linepos=3;draw(0);
    assert(!strcmp(key_lines[edit_line],"]a "));
    return 0;
}
void AW_PhotoConsoleReminder(void){}
