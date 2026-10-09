/* SPDX-License-Identifier: GPL-2.0-or-later
 * Photo mode (dbg photomode / dbg killhud) and dbg crosshair(s): the real
 * engine module with a small cvar store. Entry hides the HUD settings, kills
 * the fog and gives a free camera; exit restores every setting exactly and
 * puts the player back where photo mode started. */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
#include "aw_world.h"
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;viddef_t vid;
keydest_t key_dest;qboolean noclip_anglehack;int scr_copyeverything;vec3_t vec3_origin;
static cvar_t *vars[32];static char strings[32][64];static int nvars;
void Cvar_RegisterVariable(cvar_t *v){assert(nvars<32);vars[nvars]=v;strcpy(strings[nvars],v->string);v->string=strings[nvars];v->value=atof(v->string);nvars++;}
cvar_t *Cvar_FindVar(char *name){int i;for(i=0;i<nvars;i++)if(!strcmp(vars[i]->name,name))return vars[i];return NULL;}
void Cvar_Set(char *name,char *value){cvar_t *v=Cvar_FindVar(name);assert(v);strcpy(v->string,value);v->value=atof(value);}
void Cvar_SetValue(char *name,float value){char s[32];sprintf(s,"%g",value);Cvar_Set(name,s);}
float Cvar_VariableValue(char *name){cvar_t *v=Cvar_FindVar(name);return v?v->value:0;}
static const char *str(const char *name){return Cvar_FindVar((char *)name)->string;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
float Q_atof(char *s){return (float)atof(s);}
static void (*photo)(void),(*crosshair)(void);
void Cmd_AddCommand(char *name,void (*fn)(void)){
 if(!strcmp(name,"aw_photomode"))photo=fn;else if(!strcmp(name,"aw_crosshair"))crosshair=fn;else assert(0);
}
static int argc;static char *argv[3];
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int n){return n<argc?argv[n]:"";}
static void run(void (*fn)(void),char *a){argv[1]=a;argc=a?2:1;fn();}
static char printed[4096];
void Con_Printf(char *fmt,...){va_list a;size_t n=strlen(printed);va_start(a,fmt);vsnprintf(printed+n,sizeof(printed)-n,fmt,a);va_end(a);}
/* dbg hud = amiwind_show_debug: the overlay and coordinates follow it. */
void Cbuf_AddText(char *text){
 if(!strcmp(text,"amiwind_show_debug 1\n")){Cvar_Set("_aw_debug_all","1");Cvar_Set("_aw_debug_coords","1");}
 else if(!strcmp(text,"amiwind_show_debug 0\n")){Cvar_Set("_aw_debug_all","0");Cvar_Set("_aw_debug_coords","0");}
 else assert(0);
}
int AW_DebugOverlaysEnabled(void){return Cvar_VariableValue("_aw_debug_all")!=0;}
/* AmiWind's message box (AW_UISubtitle), the box of the Wait refusal. */
double realtime=100;
static char center[256],speaker[80];static double center_seconds=-1;static int centers;
void AW_UISubtitle(const char *name,const char *text,double seconds){strcpy(speaker,name);strcpy(center,text);center_seconds=seconds;centers++;}
int AW_UISubtitleIs(const char *text){return !speaker[0] && !strcmp(center,text);}
static int stops,links,teleports,solid;static float teleported[3];
void V_StopPitchDrift(void){stops++;}
void SV_LinkEdict(edict_t *e,qboolean touch){links++;}
edict_t *SV_TestEntityPosition(edict_t *e){return solid?e:NULL;}
int AW_WorldToSource(const char *name,const float *p,float *out){int i;if(strcmp(name,"seyda"))return 0;for(i=0;i<3;i++)out[i]=p[i]*4;return 1;}
int AW_MapTeleport(const float *p){int i;teleports++;for(i=0;i<3;i++)teleported[i]=p[i];return 1;}
static edict_t player;static client_t local;
static const char *names[]={"crosshair","aw_fog","_aw_debug_all","_aw_debug_coords","aw_ui_hud","aw_compass","aw_ui_frame","r_drawviewmodel"};
static const char *before[]={"1","0.75","1","0","1","1","1","1"};
#define NAMES 8
#define HANDS 7
static void settings(void){int i;for(i=0;i<NAMES;i++)Cvar_Set((char *)names[i],(char *)before[i]);}
static void assert_restored(void){int i;for(i=0;i<NAMES;i++)assert(!strcmp(str(names[i]),before[i]));}
static void assert_hidden(int fog){int i;for(i=0;i<NAMES;i++)if(i!=1)assert(!strcmp(str(names[i]),"0"));
 assert(fog?!strcmp(str("aw_fog"),"0"):!strcmp(str("aw_fog"),"0.75"));}
static void scene(void){
 memset(&player,0,sizeof(player));memset(&local,0,sizeof(local));
 sv.active=true;svs.maxclients=1;svs.clients=&local;local.edict=&player;strcpy(sv.name,"seyda");sv.time=10;
 sv.worldmodel=(model_t *)&local;cls.state=ca_connected;cls.signon=SIGNONS;key_dest=key_game;
 player.v.origin[0]=10;player.v.origin[1]=20;player.v.origin[2]=30;player.v.movetype=MOVETYPE_WALK;
 player.v.velocity[0]=5;cl.viewangles[0]=12;cl.viewangles[1]=90;noclip_anglehack=false;
}
static void fly(void){
 player.v.origin[0]=500;player.v.origin[1]=600;player.v.origin[2]=700;player.v.velocity[2]=40;
 cl.viewangles[0]=-30;cl.viewangles[1]=200;sv.time=25;
}
int main(void){
 cvar_t extra[]={{"crosshair","0",true},{"aw_fog","1",true},{"_aw_debug_all","0",true},{"_aw_debug_coords","0",true},
  {"aw_ui_hud","1",true},{"aw_compass","0",true},{"aw_ui_frame","0",true},{"r_drawviewmodel","1"}};
 int i;
 for(i=0;i<NAMES;i++)Cvar_RegisterVariable(&extra[i]);
 AW_PhotoInit();assert(photo && crosshair);
 assert(Cvar_FindVar("aw_photomode_nofog")->value==1 && Cvar_FindVar("aw_photomode_nofog")->archive);
 assert(Cvar_FindVar("aw_photomode_noclip")->value==1 && Cvar_FindVar("aw_photomode_noclip")->archive);
 assert(Cvar_FindVar("aw_photomode_hands")->value==0 && Cvar_FindVar("aw_photomode_hands")->archive);
 settings();
 /* No local scene: refused, nothing changed. */
 run(photo,NULL);assert(!AW_PhotoModeActive() && strstr(printed,"start the local scene"));assert_restored();
 assert(!AW_PhotoModeAvailable());
 /* Entry: HUD settings off, fog off, noclip, full-screen view, notice once gameplay has the screen. */
 scene();assert(AW_PhotoModeAvailable());printed[0]=0;key_dest=key_console;vid.recalc_refdef=false;
 run(photo,NULL);assert(AW_PhotoModeActive() && vid.recalc_refdef);assert_hidden(1);
 assert(player.v.movetype==MOVETYPE_NOCLIP && noclip_anglehack && !player.v.velocity[0]);
 assert(strstr(printed,"You are in photo mode.") && strstr(printed,"dbg photomode off") && strstr(printed,"Ctrl+F") && strstr(printed,"Ctrl+H"));
 AW_PhotoDraw();assert(!centers); /* typed in the console: the notice waits for gameplay */
 printed[0]=0;AW_PhotoConsoleReminder();assert(strstr(printed,"You are in photo mode.")); /* F10 says it */
 assert(!AW_PhotoNoticeShowing());
 key_dest=key_game;AW_PhotoDraw();assert(centers==1 && center_seconds>=3 && center_seconds<=5 && !speaker[0]);
 assert(AW_PhotoNoticeShowing()); /* the box is drawn over the hidden HUD while the notice lasts */
 assert(strstr(center,"You are in photo mode.") && strstr(center,"dbg photomode off") && strstr(center,"Ctrl+F") && strstr(center,"Ctrl+H"));
 {const char *p=center;int lines=1,n=0;for(;*p;p++){if(*p=='\n'){assert(n<=44);n=0;lines++;}else n++;}assert(n<=44 && lines==3);} /* three short rows: no paging */
 AW_PhotoDraw();assert(centers==1); /* shown once */
 realtime+=center_seconds+1.01;assert(!AW_PhotoNoticeShowing());realtime-=center_seconds+1.01; /* then the frames are clean */
 AW_UISubtitle("Fargoth","Speech during photo mode.",5);assert(!AW_PhotoNoticeShowing()); /* game speech never shows */
 /* Ctrl+F fog and Ctrl+H dbg hud, gameplay only. */
 assert(AW_PhotoKey('f') && !strcmp(str("aw_fog"),"1") && !strcmp(center,"Fog on") && center_seconds<=2 && AW_PhotoNoticeShowing());
 assert(AW_PhotoKey('F') && !strcmp(str("aw_fog"),"0") && !strcmp(center,"Fog off"));
 assert(AW_PhotoKey('f'));
 assert(AW_PhotoKey('h') && AW_DebugOverlaysEnabled() && !strcmp(str("_aw_debug_coords"),"1") && !strcmp(center,"Debug HUD on"));
 assert(AW_PhotoKey('H') && !AW_DebugOverlaysEnabled() && !strcmp(center,"Debug HUD off"));
 assert(AW_PhotoKey('h'));
 assert(!AW_PhotoKey('x') && !AW_PhotoKey('e'));
 key_dest=key_console;assert(!AW_PhotoKey('f'));key_dest=key_game;
 /* Repeated on is harmless; bad words change nothing. */
 run(photo,"on");assert(AW_PhotoModeActive() && player.v.movetype==MOVETYPE_NOCLIP);
 run(photo,"maybe");assert(AW_PhotoModeActive());
 argv[1]="off";argv[2]="now";argc=3;photo();assert(AW_PhotoModeActive());
 /* Exit: exact settings (fog and dbg hud as before, whatever Ctrl+F/Ctrl+H did), pose and movement. */
 fly();links=stops=0;printed[0]=0;
 run(photo,"OFF");assert(!AW_PhotoModeActive());assert_restored();
 assert(player.v.origin[0]==10 && player.v.origin[1]==20 && player.v.origin[2]==30);
 assert(!player.v.velocity[0] && !player.v.velocity[1] && !player.v.velocity[2]);
 assert(player.v.movetype==MOVETYPE_WALK && !noclip_anglehack && player.v.fixangle);
 assert(cl.viewangles[0]==12 && cl.viewangles[1]==90 && player.v.angles[0]==12 && player.v.angles[1]==90);
 assert(links==1 && stops==1 && strstr(printed,"Photo mode off"));
 assert(!AW_PhotoNoticeShowing());AW_PhotoDraw();assert(!strcmp(center,"Photo mode off"));
 assert(!AW_PhotoKey('f') && !AW_PhotoKey('h')); /* outside photo mode Ctrl+F / Ctrl+H keep their bindings */
 printed[0]=0;AW_PhotoConsoleReminder();assert(!printed[0]);
 /* killhud toggles the same state; a noclip player stays in noclip after. */
 scene();player.v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;
 run(photo,NULL);assert(AW_PhotoModeActive());fly();run(photo,NULL);
 assert(!AW_PhotoModeActive() && player.v.movetype==MOVETYPE_NOCLIP && noclip_anglehack && player.v.origin[0]==10);
 /* The crosshair preference: toggle, words, and changes during photo mode apply to the restored value. */
 scene();Cvar_Set("crosshair","1");
 run(crosshair,NULL);assert(!strcmp(str("crosshair"),"0") && !AW_CrosshairShown());
 run(crosshair,"TRUE");assert(AW_CrosshairShown() && Cvar_VariableValue("crosshair")==1);
 run(crosshair,"0");assert(!AW_CrosshairShown());run(crosshair,"on");assert(AW_CrosshairShown());
 run(crosshair,"sideways");assert(AW_CrosshairShown());
 run(photo,"on");assert(!strcmp(str("crosshair"),"0") && AW_CrosshairShown());
 run(crosshair,"off");assert(!strcmp(str("crosshair"),"0") && !AW_CrosshairShown());
 AW_CrosshairSet(1);assert(AW_CrosshairShown() && !strcmp(str("crosshair"),"0"));AW_CrosshairSet(0);
 run(photo,"off");assert(!strcmp(str("crosshair"),"0") && !AW_CrosshairShown());
 AW_CrosshairSet(1);assert(!strcmp(str("crosshair"),"1"));
 /* Switches: fog kept and no free camera. */
 settings();scene();Cvar_Set("aw_photomode_nofog","0");Cvar_Set("aw_photomode_noclip","0");
 run(photo,"on");assert_hidden(0);assert(player.v.movetype==MOVETYPE_WALK && !noclip_anglehack);
 player.v.origin[0]=77;run(photo,"off");assert_restored();assert(player.v.origin[0]==77 && player.v.movetype==MOVETYPE_WALK);
 Cvar_Set("aw_photomode_nofog","1");Cvar_Set("aw_photomode_noclip","1");
 /* aw_photomode_hands 1 keeps the first-person hands; everything else still hides. */
 settings();scene();Cvar_Set("aw_photomode_hands","1");
 run(photo,"on");assert(!strcmp(str("r_drawviewmodel"),"1") && !strcmp(str("crosshair"),"0") && !strcmp(str("aw_ui_hud"),"0"));
 run(photo,"off");assert_restored();
 /* Default: hands hidden; an r_drawviewmodel the player had off stays off afterwards. */
 Cvar_Set("aw_photomode_hands","0");scene();Cvar_Set("r_drawviewmodel","0");
 run(photo,"on");assert(!strcmp(str("r_drawviewmodel"),"0"));run(photo,"off");assert(!strcmp(str("r_drawviewmodel"),"0"));
 settings();
 /* A region crossing carried the free camera into another map: back by global coordinate. */
 scene();run(photo,"on");strcpy(sv.name,"bc012");fly();teleports=0;
 run(photo,"off");assert(teleports==1 && teleported[0]==40 && teleported[1]==80 && teleported[2]==120);
 assert(player.v.movetype==MOVETYPE_WALK && !noclip_anglehack);assert_restored();
 /* A load or new game (fresh server time) already placed the player: left alone. */
 scene();run(photo,"on");player.v.movetype=MOVETYPE_WALK;fly();teleports=links=0;
 run(photo,"off");assert(!teleports && !links && player.v.origin[0]==500);assert_restored();
 /* Unknown start point and still inside solid: noclip stays so the player can fly clear. */
 scene();strcpy(sv.name,"census");run(photo,"on");strcpy(sv.name,"census2");solid=1;printed[0]=0;
 run(photo,"off");assert(player.v.movetype==MOVETYPE_NOCLIP && noclip_anglehack && strstr(printed,"inside solid"));solid=0;
 assert_restored();
 /* Disconnecting ends it; config.cfg is written with the pre-photo settings. */
 scene();run(photo,"on");assert_hidden(1);cls.state=ca_disconnected;
 assert(!AW_PhotoModeActive());assert_restored();
 scene();run(photo,"on");fly();AW_PhotoConfigRestore();assert(!AW_PhotoModeActive());assert_restored();
 assert(player.v.origin[0]==500); /* shutdown: settings only */
 puts("photo mode: hide, notice, Ctrl+F/Ctrl+H, exact restore, start point, switches, crosshair");
 return 0;
}
