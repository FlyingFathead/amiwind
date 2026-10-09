/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
client_static_t cls;client_state_t cl; qboolean con_forcedup; double realtime;
char queued[1024];int con_backscroll;
static int warnings,menu_keys;
int Con_ScrollPage(void){return 10;}int Con_ScrollMax(void){return 100;}
void *Z_Malloc(int n){return calloc(1,n);} void Z_Free(void *p){free(p);}
int Q_strlen(char *s){return strlen(s);} void Q_strcpy(char *a,char *b){strcpy(a,b);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);} int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Con_Printf(char *fmt,...){if(strstr(fmt,"is unbound"))warnings++;} void S_LocalSound(char *s){}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
void Cbuf_AddText(char *s){strcat(queued,s);} void Cbuf_InsertText(char *s){strcat(queued,s);}
int Cmd_Argc(void){return 0;} char *Cmd_Argv(int n){return "";}
char *Cmd_CompleteCommand(char *s){return NULL;} char *Cvar_CompleteVariable(char *s){return NULL;}
void Sys_Error(char *s,...){assert(0);} void SCR_UpdateScreen(void){}
void M_Keydown(int key){menu_keys++;} void M_ToggleMenu_f(void){}
int AW_MovieKey(int k,int d){return 0;} int AW_WorldUIKey(int k,int d){return 0;}
int AW_GalleryKey(int k,int d,int s,int c){return 0;}
int AW_TravelKey(int k){return 0;} int AW_WaitKey(int k){return 0;} int AW_IntroKey(int k){return 0;}
int AW_ConsoleCharHeight(void){return 8;} int AW_ConsoleCharWidth(void){return 4;}
/* Photo mode stub: active, it claims Ctrl+F and Ctrl+H only. */
static int photo_active,photo_keys;
int AW_PhotoKey(int k){if(!photo_active || (k!='f' && k!='h'))return 0;photo_keys++;return 1;}
extern char *keybindings[256];extern char key_lines[32][256];extern int edit_line,key_linepos;
static void tap(int key){Key_Event(key,true);Key_Event(key,false);}
static void scroll_limits(void){
 int i,before=warnings;queued[0]=0;con_backscroll=0;
 for(i=0;i<120;i++){tap(K_MWHEELUP);assert(con_backscroll<=100);}
 assert(con_backscroll==100);tap(K_MWHEELDOWN);assert(con_backscroll==98);
 tap(K_MWHEELUP);assert(con_backscroll==100);
 for(i=0;i<120;i++){tap(K_MWHEELDOWN);assert(con_backscroll>=0);}
 assert(!con_backscroll);tap(K_MWHEELUP);assert(con_backscroll==2);
 tap(K_MWHEELDOWN);assert(!con_backscroll);
 assert(warnings==before && !queued[0]);
}
int main(void){
 FILE *f;char text[2048];size_t n;int before,mode;
 Key_Init();cls.state=ca_connected;key_dest=key_game;
 /* Unassigned game inputs still warn once per key-down, never on release. */
 assert(!keybindings[K_MWHEELUP] && !keybindings[K_MWHEELDOWN]);
 tap(K_MWHEELUP);tap(K_MWHEELDOWN);assert(warnings==2);
 Key_Event(K_MOUSE3,true);Key_Event(K_MOUSE3,true);Key_Event(K_MOUSE3,false);assert(warnings==3);
 key_dest=key_console;scroll_limits();
 key_dest=key_game;con_forcedup=true;scroll_limits();con_forcedup=false;
 key_dest=key_menu;before=warnings;tap(K_MWHEELUP);tap(K_MWHEELDOWN);assert(warnings==before && menu_keys==2);
 /* Explicitly empty slots and game bindings both retain console scrolling. */
 for(mode=0;mode<2;mode++){
  Key_SetBinding(K_MWHEELUP,mode?"impulse 1":"");Key_SetBinding(K_MWHEELDOWN,mode?"impulse 2":"");
  key_dest=key_console;scroll_limits();key_dest=key_game;con_forcedup=true;scroll_limits();con_forcedup=false;
  before=warnings;queued[0]=0;tap(K_MWHEELUP);tap(K_MWHEELDOWN);assert(warnings==before);
  assert(!strcmp(queued,mode?"impulse 1\nimpulse 2\n":"\n\n"));
 }
 /* Opening the console still releases a game action already held down. */
 Key_SetBinding(K_MOUSE1,"+attack");queued[0]=0;Key_Event(K_MOUSE1,true);
 key_dest=key_console;Key_Event(K_MOUSE1,false);assert(strstr(queued,"+attack") && strstr(queued,"-attack"));
 key_dest=key_game;
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
 /* Ctrl+F / Ctrl+H reach photo mode only while it is on and only with Ctrl;
  * plain F (hands) and Ctrl (fast flight) keep their bindings, F10 stays the console key. */
 key_dest=key_game;Key_SetBinding('f',"impulse 202");Key_SetBinding('h',"");
 queued[0]=0;Key_Event(K_CTRL,true);tap('f');Key_Event(K_CTRL,false);
 assert(!photo_keys && strstr(queued,"impulse 202") && strstr(queued,"+aw_fastflight"));
 photo_active=1;queued[0]=0;tap('f');assert(!photo_keys && !strcmp(queued,"impulse 202\n"));
 queued[0]=0;Key_Event(K_CTRL,true);tap('f');tap('h');Key_Event(K_CTRL,false);
 assert(photo_keys==2 && !strstr(queued,"impulse 202"));
 queued[0]=0;tap(K_F10);assert(!strcmp(queued,"aw_console_cycle\n") && photo_keys==2);
 key_dest=key_console;Key_Event(K_CTRL,true);tap('f');Key_Event(K_CTRL,false);assert(photo_keys==2);
 photo_active=0;key_dest=key_console;
 f=tmpfile();assert(f);Key_WriteBindings(f);rewind(f);n=fread(text,1,sizeof(text)-1,f);text[n]=0;fclose(f);
 assert(strstr(text,"unbindall\n") && strstr(text,"bind \"ALT+M\" \"aw_desktop\""));
 return 0;
}
