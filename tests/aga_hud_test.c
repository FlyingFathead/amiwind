/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
void AW_UIHud(void){}
int AW_Interior(void){return 0;}
int AW_FpsTenths(void){return 123;}
int fps_draws;
float anglemod(float v){return v;}
keydest_t key_dest;
viddef_t vid;
int scr_copyeverything;
client_state_t cl;
client_static_t cls;
server_t sv;
server_static_t svs;
entity_t cl_entities[MAX_EDICTS];
cvar_t scr_showram={"showram","0"};
cvar_t *settings[4];int settings_count;
void (*command)(void),(*master)(void),(*ram)(void),(*sea)(void),(*fps)(void);
int argc=2,fill_y=-1,text_y=-1,text_x=-1;
char *arg="on",last[80];
int Cmd_Argc(void) {return argc;}
char *Cmd_Argv(int n) {return arg;}
void Con_Printf(char *fmt,...) {}
int Q_strcasecmp(char *a,char *b) {return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *p) {settings[settings_count++]=p;p->value=atof(p->string);}
void Cvar_SetValue(char *name,float v) {int i;if(!strcmp(name,"showram")){scr_showram.value=v;return;}for(i=0;i<4;i++)if(!strcmp(name,settings[i]->name)){settings[i]->value=v;return;}assert(0);}
void Cmd_AddCommand(char *name,void (*fn)(void)) {if(!strcmp(name,"amiwind_debug_coords"))command=fn;else if(!strcmp(name,"amiwind_show_debug"))master=fn;else if(!strcmp(name,"amiwind_debug_showram"))ram=fn;else if(!strcmp(name,"amiwind_debug_sealevel"))sea=fn;else if(!strcmp(name,"amiwind_debug_fps"))fps=fn;}
void Draw_Fill(int x,int y,int w,int h,int c) {fill_y=y;assert(y+h==vid.height || (y==19 && h==10 && x==8 && w==80));}
void Draw_String(int x,int y,char *s) {text_x=x;text_y=y;strcpy(last,s);if(!strncmp(s,"FPS:",4)){assert(!strcmp(s,"FPS:12.3"));fps_draws++;}}
int main(void) {
 client_t local;edict_t player;
 Sbar_Init();assert(!AW_DebugCoordsEnabled());
 assert(AW_SeaLevelEnabled());arg="off";sea();assert(!AW_SeaLevelEnabled());arg="on";sea();
 command();assert(AW_DebugCoordsEnabled() && vid.recalc_refdef);
 vid.width=320;vid.height=200;cls.state=ca_connected;cl.viewentity=1;
 cl_entities[1].origin[0]=-12;cl_entities[1].origin[1]=42;cl_entities[1].origin[2]=66;
 Sbar_Draw();assert(fill_y==188 && text_y==190 && text_x+strlen(last)*8==312);
 assert(!strcmp(last,"XYZ:-12 42 66 DEG:0 P:0") && scr_copyeverything);
 memset(&local,0,sizeof(local));memset(&player,0,sizeof(player));
 sv.active=true;svs.maxclients=1;svs.clients=&local;local.edict=&player;
 player.v.origin[0]=540;player.v.origin[1]=-200;player.v.origin[2]=65;
 Sbar_Draw();assert(!strcmp(last,"XYZ:540 -200 65 DEG:0 P:0"));
 player.v.origin[0]=497;Sbar_Draw();assert(!strcmp(last,"XYZ:497 -200 65 DEG:0 P:0"));
 assert(!fps_draws);arg="on";fps();Sbar_Draw();assert(fps_draws==1);
 arg="off";ram();assert(!scr_showram.value);
 arg="0";master();assert(!AW_DebugOverlaysEnabled() && !AW_DebugCoordsEnabled());
 assert(AW_SeaLevelEnabled());
 fill_y=-1;Sbar_Draw();assert(fill_y==-1 && fps_draws==1);
 arg="1";master();assert(AW_DebugCoordsEnabled() && !scr_showram.value);
 arg="on";ram();assert(scr_showram.value);
 arg="false";command();assert(!AW_DebugCoordsEnabled());
 arg="TrUe";command();assert(AW_DebugCoordsEnabled());
 arg="nonsense";command();assert(AW_DebugCoordsEnabled());
 argc=1;command();assert(AW_DebugCoordsEnabled());
 argc=3;arg="off";command();assert(AW_DebugCoordsEnabled());
 argc=2;command();assert(!AW_DebugCoordsEnabled());
 return 0;
}
