/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
void AW_UIHud(void){}
void AW_NpcLodDrawLabels(void){}
static int photo_mode;int AW_PhotoModeActive(void){return photo_mode;}
static int fill_x=-1,fill_w=-1,hint_draws;
int AW_Interior(void){return 0;}
int AW_FpsTenths(void){return 123;}
static int clock_ok=1,clock_hour=23,clock_minute=59;
int AW_ClockEnsure(void){return clock_ok;}
void AW_ClockDate(int *y,int *m,int *d,int *h,int *n){
 *y=427;*m=8;*d=16;*h=clock_hour;*n=clock_minute;
}
int fps_draws;
float anglemod(float v){return v-floorf(v/360)*360;}
int AW_GalleryActive(void){return 0;}
/* The CHIM Balmora frame: centre -20480 -12288 (aw_hud.c owns the hook). */
extern int (*aw_chim_source)(const float *,float *);
static int chim_source(const float *p,float *world){world[0]=p[0]*4-20480;world[1]=p[1]*4-12288;world[2]=p[2]*4;return 1;}
int AW_WorldToSource(const char *name,const float *p,float *world){
 int i;if(strcmp(name,"seyda"))return 0;
 for(i=0;i<3;i++)world[i]=p[i]*4;world[0]-=11264;world[1]-=71680;return 1;
}
const char *AW_RegionNameAt(const float *p){return "Bitter Coast Region";}
keydest_t key_dest;
viddef_t vid;
int scr_copyeverything;
client_state_t cl;
client_static_t cls;
server_t sv;
server_static_t svs;
entity_t cl_entities[MAX_EDICTS];
cvar_t scr_showram={"showram","0"};
cvar_t *settings[6];int settings_count;
void (*cell_command)(void),(*command)(void),(*master)(void),(*ram)(void),(*sea)(void),(*fps)(void),(*hud_type)(void),(*compass_command)(void);
int argc=2,fill_y=-1,text_y=-1,text_x=-1;
char *arg="on",last[128],title[128];
int Cmd_Argc(void) {return argc;}
char *Cmd_Argv(int n) {return arg;}
static char printed[256];
void Con_Printf(char *fmt,...) {va_list v;va_start(v,fmt);vsnprintf(printed,sizeof printed,fmt,v);va_end(v);}
static int light_gallery,light_draws;
int AW_LightGalleryDraw(void){if(!light_gallery)return 0;light_draws++;return 1;}
int Q_strcasecmp(char *a,char *b) {return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *p) {settings[settings_count++]=p;p->value=atof(p->string);}
void Cvar_SetValue(char *name,float v) {int i;if(!strcmp(name,"showram")){scr_showram.value=v;return;}for(i=0;i<settings_count;i++)if(!strcmp(name,settings[i]->name)){settings[i]->value=v;return;}assert(0);}
void Cmd_AddCommand(char *name,void (*fn)(void)) {if(!strcmp(name,"aw_cell"))cell_command=fn;else if(!strcmp(name,"amiwind_debug_compass"))compass_command=fn;else if(!strcmp(name,"amiwind_debug_coords"))command=fn;else if(!strcmp(name,"amiwind_show_debug"))master=fn;else if(!strcmp(name,"amiwind_debug_showram"))ram=fn;else if(!strcmp(name,"amiwind_debug_sealevel"))sea=fn;else if(!strcmp(name,"amiwind_debug_fps"))fps=fn;else if(!strcmp(name,"aw_debug_hud_type"))hud_type=fn;}
void Draw_Fill(int x,int y,int w,int h,int c) {fill_y=y;fill_x=x;fill_w=w;if(y+h==vid.height)assert(photo_mode?x==0 && w==vid.width:x==88);assert(y+h==vid.height || (y==19 && h==10 && x==8 && w==80));}
void Draw_String(int x,int y,char *s) {text_x=x;text_y=y;strcpy(last,s);if(!strncmp(s,"FPS:",4)){assert(!strcmp(s,"FPS:12.3"));fps_draws++;}}
static int small_draws,compass_draws;static char global_line[80],local_line[80],bearing[96];
void AW_SmallString(int x,int y,const char *s){
 if(y==8){assert(x==8);strcpy(title,s);small_draws++;return;}
 if(!strcmp(s,"WASD / F10 console")){hint_draws++;return;}
 assert(x>=88 && x+strlen(s)*4<=312);
 if(y==174){strcpy(bearing,s);compass_draws++;}
 else if(y==184)strcpy(global_line,s);
 else if(y==192)strcpy(local_line,s);
 else assert(0);
}
int main(void) {
 client_t local;edict_t player;
 Sbar_Init();assert(!AW_DebugCoordsEnabled() && !AW_DebugOverlaysEnabled());
 assert(compass_command && settings_count==6 && !strcmp(settings[5]->name,"aw_compass"));
 assert(settings[5]->archive && settings[5]->value==0);
 vid.width=320;vid.height=200;cls.state=ca_connected;key_dest=key_game;
 Sbar_Draw();assert(compass_draws==0); /* Default is hidden, even in gameplay. */
 arg="on";master();Sbar_Draw();assert(compass_draws==0); /* Independent switch. */
 small_draws=0;arg="on";compass_command();
 arg="on";master();assert(AW_DebugOverlaysEnabled() && AW_DebugCoordsEnabled());
 assert(AW_SeaLevelEnabled());arg="off";sea();assert(!AW_SeaLevelEnabled());arg="on";sea();
 command();assert(AW_DebugCoordsEnabled() && vid.recalc_refdef);
 vid.width=320;vid.height=200;cls.state=ca_connected;cl.viewentity=1;
 cl_entities[1].origin[0]=-12;cl_entities[1].origin[1]=42;cl_entities[1].origin[2]=66;
 Sbar_Draw();assert(fill_y==182 && !strcmp(bearing,"E 090 / REGION: unavailable"));
 assert(small_draws==1);arg="1";hud_type();Sbar_Draw();assert(small_draws==1);arg="2";hud_type();Sbar_Draw();assert(small_draws==2);
 assert(!strcmp(local_line,"LOCAL XYZ: -12 42 66 E 090 P:0") && scr_copyeverything);
 assert(strstr(global_line,"unavailable"));
 memset(&local,0,sizeof(local));memset(&player,0,sizeof(player));
 sv.active=true;strcpy(sv.name,"seyda");svs.maxclients=1;svs.clients=&local;local.edict=&player;
 player.v.movetype=MOVETYPE_NONE;player.v.flags=0;
 player.v.origin[0]=540;player.v.origin[1]=-200;player.v.origin[2]=65;
 Sbar_Draw();assert(!strcmp(local_line,"LOCAL XYZ: 540 -200 65 E 090 P:0 CELL -2,-9"));
 assert(!strcmp(global_line,"GLOBAL XYZ: -9104 -72480 260 TIME 23:59"));
 assert(strstr(title," Vvardenfell / Bitter Coast Region") && !strncmp(title,"AmiWind v",9));
 player.v.origin[0]=497;Sbar_Draw();assert(!strcmp(local_line,"LOCAL XYZ: 497 -200 65 E 090 P:0 CELL -2,-9"));
 /* noclip / god mode on the same rows while active, gone when off. */
 player.v.movetype=MOVETYPE_NOCLIP;Sbar_Draw();
 assert(strstr(global_line,"NOCLIP: ON") || strstr(local_line,"NOCLIP: ON"));
 player.v.flags=FL_GODMODE;Sbar_Draw();
 assert(strstr(local_line,"NOCLIP GOD") || strstr(global_line,"NOCLIP GOD") ||
        strstr(local_line,"NOCLIP: ON GOD: ON") || strstr(global_line,"NOCLIP: ON GOD: ON"));
 player.v.movetype=MOVETYPE_NONE;player.v.flags=0;Sbar_Draw();
 assert(!strstr(global_line,"NOCLIP") && !strstr(local_line,"NOCLIP") && !strstr(local_line,"GOD") && !strstr(global_line,"GOD"));
 /* V2 carries the clock and all eight compass headings even if the separate
  * compass is disabled; V1 retains its legacy raw engine yaw and no clock. */
 {
  int i;const char *expected[]={"N 000","NE 045","E 090","SE 135","S 180","SW 225","W 270","NW 315"};
  arg="off";compass_command();
  for(i=0;i<8;i++){cl.viewangles[YAW]=90-i*45;Sbar_Draw();assert(strstr(local_line,expected[i]));}
  clock_hour=0;clock_minute=0;Sbar_Draw();assert(strstr(global_line,"TIME 00:00"));
  clock_hour=9;clock_minute=7;Sbar_Draw();assert(strstr(global_line,"TIME 09:07"));
  clock_ok=0;Sbar_Draw();assert(strstr(global_line,"TIME --:--"));clock_ok=1;
  cl.viewangles[YAW]=0;arg="1";hud_type();Sbar_Draw();
  assert(!strcmp(local_line,"LOCAL XYZ: 497 -200 65 DEG:0 P:0"));assert(!strstr(global_line,"TIME"));
  /* V1: the GLOBAL row is now the shorter one, so the cell goes there. */
  assert(!strcmp(global_line,"GLOBAL XYZ: -9276 -72480 260 CELL -2,-9"));
  arg="2";hud_type();Sbar_Draw();assert(strstr(local_line,"E 090"));
  player.v.origin[0]=10000000;player.v.origin[1]=-10000000;Sbar_Draw();
  assert(strlen(global_line)<=54 && strlen(local_line)<=54);
  assert(!strstr(global_line,"CELL") && !strstr(local_line,"CELL")); /* outside the world: no cell */
  player.v.origin[0]=497;player.v.origin[1]=-200;arg="on";compass_command();
 }

 /* A disk without the world directory (MiniWind): the active CHIM frame
  * gives the GLOBAL row and the cell; no frame, no transform. */
 {
  strcpy(sv.name,"balmora");player.v.origin[0]=1023.75f;player.v.origin[1]=-200;
  Sbar_Draw();assert(strstr(global_line,"unavailable") && !strstr(local_line,"CELL"));
  aw_chim_source=chim_source;Sbar_Draw();
  assert(!strncmp(global_line,"GLOBAL XYZ: -16385 -13088 260",29) && !strcmp(local_line+strlen(local_line)-11," CELL -3,-2"));
  player.v.origin[0]=1024;Sbar_Draw();assert(!strcmp(local_line+strlen(local_line)-11," CELL -2,-2"));
  aw_chim_source=NULL;strcpy(sv.name,"seyda");player.v.origin[0]=497;
 }
 /* Original cell readout: the exterior grid cell (floor of global/8192) on both sides
  * of zero and exactly on the cell edges, the compact form when the full one
  * does not fit, and the interior number from worldspawn keys. */
 {
  int i;const struct {float x,y;const char *cell;} edge[]={
   {768,-200,"CELL -1,-9"},      /* global x -8192: first unit of cell -1 */
   {767.75f,-200,"CELL -2,-9"},  /* global x -8193 */
   {2816,-200,"CELL 0,-9"},      /* global x 0 */
   {2815.75f,-200,"CELL -1,-9"}, /* global x -1 */
   {4863.75f,-200,"CELL 0,-9"},  /* global x 8191 */
   {4864,-200,"CELL 1,-9"},      /* global x 8192 */
   {497,-512,"CELL -2,-9"},      /* global y -73728: first unit of cell -9 */
   {497,-512.25f,"CELL -2,-10"}, /* global y -73729 */
   {497,17920,"CELL -2,0"},      /* global y 0 */
   {497,17919.75f,"CELL -2,-1"}};/* global y -1 */
  char want[64];
  for(i=0;i<(int)(sizeof edge/sizeof edge[0]);i++){
   player.v.origin[0]=edge[i].x;player.v.origin[1]=edge[i].y;Sbar_Draw();
   snprintf(want,sizeof want," %s",edge[i].cell);
   assert(strlen(local_line)>=strlen(want) && !strcmp(local_line+strlen(local_line)-strlen(want),want));
   assert(!strstr(global_line,"CELL"));
  }
  /* A narrow screen: the full form no longer fits the shorter row, the compact one does. */
  player.v.origin[0]=497;player.v.origin[1]=-200;vid.width=264;Sbar_Draw();
  assert(!strcmp(local_line,"LOCAL XYZ: 497 -200 65 E 090 P:0 C -2,-9") && !strstr(global_line,"C -2"));
  vid.width=200;Sbar_Draw();assert(!strstr(local_line,"-2,-9") && !strstr(global_line,"-2,-9")); /* no room: omitted */
  vid.width=320;
  argc=1;cell_command();assert(strstr(printed,"Cell: CELL -2,-9 (exterior grid; global -9276 -72480)"));
  assert(strstr(printed,"Bitter Coast Region") && strstr(printed,"scene seyda"));argc=2;
  /* Interior: no exterior transform; number and full ID from worldspawn. */
  {
   static model_t room,other;
   static char entities[]="{\n\"classname\" \"worldspawn\"\n\"message\" \"Census and Excise Office\"\n"
    "\"_aw_cell_int\" \"763\"\n\"_aw_cell_id\" \"Seyda Neen, Census and Excise Office\"\n}\n"
    "{\n\"classname\" \"info_player_start\"\n\"_aw_cell_int\" \"9\"\n}\n";
   static char plain[]="{\n\"classname\" \"worldspawn\"\n}\n";
   strcpy(sv.name,"census");strcpy(room.name,"maps/census.bsp");room.entities=entities;cl.worldmodel=&room;
   Sbar_Draw();assert(!strcmp(local_line+strlen(local_line)-8," INT 763"));
   assert(strstr(global_line,"unavailable") && !strstr(global_line,"INT"));
   argc=1;cell_command();assert(!strcmp(printed,"Cell: INT 763 = \"Seyda Neen, Census and Excise Office\" / map census\n"));argc=2;
   vid.width=248;Sbar_Draw();assert(!strcmp(local_line+strlen(local_line)-6," I 763"));vid.width=320;
   /* The same model slot reused for another map re-reads its keys. */
   strcpy(room.name,"maps/plain.bsp");room.entities=plain;Sbar_Draw();assert(!strstr(local_line,"INT"));
   argc=1;cell_command();assert(strstr(printed,"Cell: unknown for map census"));argc=2;
   strcpy(other.name,"maps/bad.bsp");other.entities="{\n\"_aw_cell_int\" \"-4\"\n}\n";cl.worldmodel=&other;
   Sbar_Draw();assert(!strstr(local_line,"INT"));
   cl.worldmodel=NULL;strcpy(sv.name,"seyda");
  }
  player.v.origin[0]=497;player.v.origin[1]=-200;
 }
 assert(!fps_draws);arg="on";fps();Sbar_Draw();assert(fps_draws==1);
 arg="off";ram();assert(!scr_showram.value);
 arg="0";master();assert(!AW_DebugOverlaysEnabled() && !AW_DebugCoordsEnabled());
 assert(settings[0]->value==0);
 assert(AW_SeaLevelEnabled());
 fill_y=-1;Sbar_Draw();assert(fill_y==-1 && fps_draws==1);
 {int i,n=compass_draws;const char *expected[]={"N 000","W 270","S 180","E 090","NE 045"};
  float yaw[]={90,180,270,360,45};
  for(i=0;i<5;i++){cl.viewangles[YAW]=yaw[i];Sbar_Draw();assert(!strncmp(bearing,expected[i],strlen(expected[i])));assert(strstr(bearing," / REGION: Bitter Coast Region"));}
  assert(compass_draws==n+5);key_dest=key_menu;Sbar_Draw();assert(compass_draws==n+5);key_dest=key_game;
 }
 /* PHOTO-DEBUG-STRIP-33: Ctrl+H in photo mode (dbg hud over a full-screen view)
  * blacks out the coordinate strip across the whole width, not from x=88;
  * the input hint never draws over the photo-mode view. */
 {int n=hint_draws;
  arg="on";master();photo_mode=1;Sbar_Draw();assert(fill_y==182 && fill_x==0 && fill_w==320);
  photo_mode=0;Sbar_Draw();assert(fill_x==88 && fill_w==232);
  arg="off";command();photo_mode=1;Sbar_Draw();assert(hint_draws==n);
  photo_mode=0;Sbar_Draw();assert(hint_draws==n+1);
  arg="0";master();
 }
 /* The light gallery strip: shown normally (it replaces the bottom HUD), hidden in
  * photo mode, back with Ctrl+H (dbg hud), shown again after photo mode. */
 {int n=small_draws;
  light_gallery=1;light_draws=0;
  Sbar_Draw();assert(light_draws==1 && small_draws==n);
  photo_mode=1;Sbar_Draw();assert(light_draws==1);
  arg="on";master();Sbar_Draw();assert(light_draws==2 && small_draws==n); /* Ctrl+H: strip, as with dbg hud normally */
  arg="0";master();Sbar_Draw();assert(light_draws==2);
  photo_mode=0;Sbar_Draw();assert(light_draws==3);
  light_gallery=0;
 }
 strcpy(sv.name,"census");strcpy(cl.levelname,"Census and Excise Office");
 arg="1";master();assert(AW_DebugCoordsEnabled() && !scr_showram.value);
 Sbar_Draw();assert(strstr(title," / Census and Excise Office") && !strstr(title,"Bitter Coast"));
 arg="on";ram();assert(scr_showram.value);
 arg="false";command();assert(!AW_DebugCoordsEnabled());
 arg="TrUe";command();assert(AW_DebugCoordsEnabled());
 arg="nonsense";command();assert(AW_DebugCoordsEnabled());
 argc=1;command();assert(AW_DebugCoordsEnabled());
 argc=3;arg="off";command();assert(AW_DebugCoordsEnabled());
 argc=2;command();assert(!AW_DebugCoordsEnabled());
 /* Queries and rejected values preserve an explicit coordinate override. */
 argc=1;master();assert(!AW_DebugCoordsEnabled());
 argc=2;arg="nonsense";master();assert(!AW_DebugCoordsEnabled());
 argc=3;arg="on";master();assert(!AW_DebugCoordsEnabled());
 /* Every explicit enable restores coordinates, including when already on. */
 argc=2;arg="TrUe";master();assert(AW_DebugCoordsEnabled());
 arg="off";command();master();assert(!AW_DebugOverlaysEnabled());
 arg="1";master();assert(AW_DebugOverlaysEnabled() && AW_DebugCoordsEnabled());
 {int i,n;char *values[]={"on","off","1","0","TrUe","FaLsE"};
  for(i=0;i<6;i++){
   argc=2;arg=values[i];scr_copyeverything=0;compass_command();assert(scr_copyeverything);
   n=compass_draws;Sbar_Draw();assert(compass_draws==n+(i%2==0));
  }
  n=compass_draws;argc=1;compass_command();Sbar_Draw();assert(compass_draws==n);
  argc=2;arg="invalid";compass_command();Sbar_Draw();assert(compass_draws==n);
  argc=3;arg="on";compass_command();Sbar_Draw();assert(compass_draws==n);
 }
 return 0;
}
