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
static void tap(int key){Key_Event(key,true);Key_Event(key,false);}
int main(void){
 FILE *f;char text[2048];size_t n;
 Key_Init();cls.state=ca_connected;key_dest=key_game;
 Key_SetBinding('m',"aw_worldmap");Key_SetBinding('n',"");
 Key_SetBinding('v',"aw_torch");
 queued[0]=0;tap('v');assert(!strcmp(queued,"aw_torch\n"));
 queued[0]=0;Key_Event(K_SHIFT,true);tap('v');Key_Event(K_SHIFT,false);
 assert(!strcmp(queued,"aw_viewdistance_cycle\n"));
 Key_SetBinding(K_ALTM,"aw_desktop");Key_SetBinding(K_CTRL,"+aw_fastflight");
 queued[0]=0;tap('m');assert(!strcmp(queued,"aw_worldmap\n"));
 queued[0]=0;Key_Event(K_ALT,true);tap('m');Key_Event(K_ALT,false);assert(!strcmp(queued,"aw_desktop\n"));
 queued[0]=0;tap(K_CTRL);assert(strstr(queued,"+aw_fastflight") && strstr(queued,"-aw_fastflight"));
 key_dest=key_console;queued[0]=0;tap('m');tap('n');assert(!queued[0]);
 assert(!strcmp(key_lines[edit_line],"]mn"));
 Key_Event(K_ALT,true);tap('m');Key_Event(K_ALT,false);assert(!queued[0] && !strcmp(key_lines[edit_line],"]mnm"));
 f=tmpfile();assert(f);Key_WriteBindings(f);rewind(f);n=fread(text,1,sizeof(text)-1,f);text[n]=0;fclose(f);
 assert(strstr(text,"unbindall\n") && strstr(text,"bind \"ALT+M\" \"aw_desktop\""));
 return 0;
}
