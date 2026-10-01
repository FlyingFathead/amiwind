/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_static_t cls;client_state_t cl; qboolean con_forcedup; double realtime;
char queued[1024];int con_backscroll;
int Con_ScrollPage(void){return 10;}int Con_ScrollMax(void){return 100;}
void *Z_Malloc(int n){return calloc(1,n);} void Z_Free(void *p){free(p);}
int Q_strlen(char *s){return strlen(s);} void Q_strcpy(char *a,char *b){strcpy(a,b);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);} int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *fmt,...){} void S_LocalSound(char *s){}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
void Cbuf_AddText(char *s){strcat(queued,s);} void Cbuf_InsertText(char *s){strcat(queued,s);}
int Cmd_Argc(void){return 0;} char *Cmd_Argv(int n){return "";}
char *Cmd_CompleteCommand(char *s){return NULL;} char *Cvar_CompleteVariable(char *s){return NULL;}
void Sys_Error(char *s,...){assert(0);} void SCR_UpdateScreen(void){}
void M_Keydown(int key){} void M_ToggleMenu_f(void){}
int AW_MovieKey(int k,int d){return 0;} int AW_WorldUIKey(int k,int d){return 0;}
int AW_GalleryKey(int k,int d,int s,int c){return 0;}
int AW_TravelKey(int k){return 0;} int AW_WaitKey(int k){return 0;} int AW_IntroKey(int k){return 0;}
int AW_ConsoleCharHeight(void){return 8;} int AW_ConsoleCharWidth(void){return 4;}
extern char *keybindings[256];extern char key_lines[32][256];extern int edit_line,key_linepos;
extern qboolean keydown[256];
static void tap(int key){Key_Event(key,true);Key_Event(key,false);}
int main(void){
 Key_Init();cls.state=ca_connected;key_dest=key_console;
 /* Simulate missed Shift release: next native event's qualifiers repair it. */
 Key_Event(K_SHIFT,true);Key_AmigaQualifiers(0);
 tap('d');tap('b');tap('g');tap(' ');tap('1');
 assert(!strcmp(key_lines[edit_line],"]dbg 1"));
 Key_AmigaQualifiers(4);tap('a');tap('2'); /* Caps changes letters only. */
 assert(!strcmp(key_lines[edit_line],"]dbg 1A2"));
 Key_AmigaQualifiers(5);tap('a');tap('1'); /* Caps+Shift lowercases letters. */
 assert(!strcmp(key_lines[edit_line],"]dbg 1A2a!"));
 Key_AmigaQualifiers(3);assert(keydown[K_SHIFT]);
 Key_AmigaQualifiers(2);assert(keydown[K_SHIFT]);
 Key_AmigaQualifiers(0);assert(!keydown[K_SHIFT]);
 Key_AmigaQualifiers(0xc0);assert(!keydown[K_CTRL] && !keydown[K_SHIFT]);
 assert(Key_AmigaRaw(0x30)=='<' && Key_AmigaRaw(0x67)==0);
 Key_AmigaQualifiers(1);Key_ClearStates();assert(!keydown[K_SHIFT]);
 tap('3');assert(!strcmp(key_lines[edit_line],"]dbg 1A2a!3"));
 return 0;
}
