/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include "aw_boolean.h"
viddef_t vid;
int scr_copyeverything;
void Con_CheckResize(void){}
void Draw_Character(int x,int y,int c){}
byte *host_basepal;
byte *draw_chars;
static int font_size=-1;
int COM_FOpenFile(char *name,FILE **f){
 int i;if(font_size<0){*f=NULL;return -1;}
 *f=tmpfile();assert(*f);for(i=0;i<font_size;i++)fputc(i%251,*f);
 rewind(*f);return font_size;
}
static byte pixels[64],palette[768];
static cvar_t *colour;
static void (*color_command)(void),(*debug_command)(void),(*font_command)(void),(*dbg_command)(void);
static char *args[12];static int argc;
static char queued[160];
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int n){return n<argc?args[n]:"";}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int Q_strncasecmp(char *a,char *b,int n){return strncasecmp(a,b,n);}
void Con_Printf(char *fmt,...){}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void Cvar_RegisterVariable(cvar_t *p){colour=p;p->value=atof(p->string);}
void Cvar_SetValue(char *name,float v){assert(!strcmp(name,colour->name));colour->value=v;}
void Cmd_AddCommand(char *name,void (*fn)(void)){
 if(!strcmp(name,"aw_console_color"))color_command=fn;
 if(!strcmp(name,"debug"))debug_command=fn;
 if(!strcmp(name,"dbg"))dbg_command=fn;
 if(!strcmp(name,"aw_console_font"))font_command=fn;
}
int main(void){
 char output[160];byte atlas[16384];int i;
 char *compass[]={"dbg","compass","true"};
 {
  char *tracker[]={"dbg","shroomtracker","reset"};
  assert(AW_DebugTranslate(2,tracker,output,sizeof(output))==1 && !strcmp(output,"aw_shroomtracker\n"));
  assert(!AW_DebugTranslate(3,tracker,output,sizeof(output))); /* Query only, no reset. */
  tracker[0]="debug";assert(AW_DebugTranslate(2,tracker,output,sizeof(output))==1);
  assert(!AW_DebugTranslate(2,tracker,output,8));
 }

 {
  char *radius[]={"dbg","torch","radius","192"};
  char *flame[]={"dbg","torch","flame","brightbase"};
  assert(AW_DebugTranslate(4,radius,output,sizeof(output))==1 && !strcmp(output,"aw_torch_radius_set 192\n"));
  assert(AW_DebugTranslate(4,flame,output,sizeof(output))==1 && !strcmp(output,"aw_torch_flame_set brightbase\n"));
 }
 {
  char *scene[]={"dbg","tpscene","headselection"};
  assert(AW_DebugTranslate(2,scene,output,sizeof(output))==1 && !strcmp(output,"aw_tpscene\n"));
  assert(AW_DebugTranslate(3,scene,output,sizeof(output))==1 && !strcmp(output,"aw_tpscene headselection\n"));
  scene[2]="headselection;quit";assert(!AW_DebugTranslate(3,scene,output,sizeof(output)));
 }
 char *exact[]={"dbg","set","time","0630"};
 char *sky[]={"dbg","sky","off"};
 char *skytype[]={"dbg","skytype","2"};
 char *sun[]={"dbg","sun","on"};
 char *clouds[]={"dbg","clouds","on"};
 char *guardtorch[]={"dbg","guardtorch","auto"};
 char *starsky[]={"dbg","starsky","on"};
 char *nightsky[]={"dbg","nightsky","on"};
 char *cycle[]={"dbg","daynightcycle","on"};
 char *inputtrace[]={"dbg","inputtrace","on"};
 char *daygallery[]={"dbg","daycycle","gallery","off"};
 char *nightgallery[]={"dbg","nightgallery","here"};
 char *skyspeed[]={"dbg","skyspeed","0.0333333333"};
 const char *booleans[]={"1","0","true","false","on","off","TrUe","FaLsE"};
 char *hud_type[]={"dbg","hud","type","2"};
 char *gallery[]={"dbg","gallery","exit"};
 char *hors[]={"dbg","aw","hors","0"};
 char *hud[]={"dbg","hud","on"};
 char *shortform[]={"debug","reset","location","0"};
 char *longform[]={"amiwind","debug","reset","location","0"};
 char *toggle[]={"DeBuG","coords","TrUe"};
 char *abbr[]={"DbG","coords","on"};
 char *bad[]={"debug","coords","on;quit"};
 char *missing[]={"debug","reset"};
 char *help[]={"debug","help"};
 char *picker[]={"dbg","scene","change"};
 char *tp_map[]={"dbg","tp","map"};
 char *map_tp[]={"dbg","map","tp"};
 char *tp[]={"dbg","tp","balmora"};
 char *tp_menu[]={"amiwind","debug","tp","menu"};
 char *tp_xy[]={"dbg","tp","-14231","-76109"};
 char *tp_extra[]={"dbg","tp","-14231","-76109","extra"};
 char *tp_bad[]={"dbg","tp","balmora;quit"};
 char *fog[]={"dbg","fog","distance","400"};
 char *distance[]={"debug","draw","distance","500"};
 char *view[]={"debug","view","-20","30","40","90","-60"};
 char *playvid[]={"dbg","playvid","15"};
 assert(AW_DebugTranslate(2,nightgallery,output,sizeof(output))==1 && !strcmp(output,"aw_nightgallery\n"));
 assert(AW_DebugTranslate(3,nightgallery,output,sizeof(output))==1 && !strcmp(output,"aw_nightgallery here\n"));
 nightgallery[2]="off";assert(AW_DebugTranslate(3,nightgallery,output,sizeof(output))==1 && !strcmp(output,"aw_nightgallery off\n"));
 nightgallery[2]="here;quit";assert(AW_DebugTranslate(3,nightgallery,output,sizeof(output))==0);
 assert(AW_DebugTranslate(3,skyspeed,output,sizeof(output))==1 && !strcmp(output,"aw_skyspeed_set 0.0333333333\n"));
 assert(AW_DebugTranslate(3,daygallery,output,sizeof(output))==1 && !strcmp(output,"aw_daycycle_gallery\n"));
 assert(AW_DebugTranslate(4,daygallery,output,sizeof(output))==1 && !strcmp(output,"aw_daycycle_gallery off\n"));
 assert(AW_DebugTranslate(3,compass,output,sizeof(output))==1 && !strcmp(output,"amiwind_debug_compass true\n"));
 assert(AW_DebugTranslate(2,compass,output,sizeof(output))==1 && !strcmp(output,"amiwind_debug_compass\n"));
 assert(AW_BooleanCvar("aw_compass") && AW_BooleanCvar("aw_daynight") && AW_BooleanCvar("aw_daynightcycle"));
 assert(AW_BooleanCvar("aw_input_trace"));
 assert(AW_DebugTranslate(2,inputtrace,output,sizeof(output))==1 && !strcmp(output,"aw_input_trace\n"));
 assert(AW_BooleanCvar("aw_sun") && AW_BooleanCvar("aw_clouds"));
 assert(AW_BooleanCvar("aw_starsky") && AW_BooleanCvar("aw_nightsky"));
 assert(AW_BooleanCvar("guards_torch_cycle"));
 assert(AW_DebugTranslate(3,guardtorch,output,sizeof(output))==1 && !strcmp(output,"aw_guardtorch auto\n"));
 guardtorch[2]="on";assert(AW_DebugTranslate(3,guardtorch,output,sizeof(output))==1 && !strcmp(output,"aw_guardtorch on\n"));
 guardtorch[2]="off";assert(AW_DebugTranslate(3,guardtorch,output,sizeof(output))==1 && !strcmp(output,"aw_guardtorch off\n"));
 assert(AW_DebugTranslate(2,starsky,output,sizeof(output))==1 && !strcmp(output,"aw_starsky\n"));
 assert(AW_DebugTranslate(2,nightsky,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky\n"));
 for(i=0;i<8;i++){
  char expected[80];cycle[2]=(char *)booleans[i];sprintf(expected,"aw_daynightcycle %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,cycle,output,sizeof(output))==1 && !strcmp(output,expected));
  assert(AW_ParseBoolean(cycle[2])==(i%2==0));
  inputtrace[2]=(char *)booleans[i];sprintf(expected,"aw_input_trace %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,inputtrace,output,sizeof(output))==1 && !strcmp(output,expected));
  starsky[2]=nightsky[2]=(char *)booleans[i];sprintf(expected,"aw_starsky %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,starsky,output,sizeof(output))==1 && !strcmp(output,expected));
  sprintf(expected,"aw_nightsky %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,nightsky,output,sizeof(output))==1 && !strcmp(output,expected));
  sun[2]=clouds[2]=(char *)booleans[i];sprintf(expected,"aw_sun %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,sun,output,sizeof(output))==1 && !strcmp(output,expected));
  sprintf(expected,"aw_clouds %s\n",booleans[i]);
  assert(AW_DebugTranslate(3,clouds,output,sizeof(output))==1 && !strcmp(output,expected));
 }
 assert(AW_DebugTranslate(4,exact,output,sizeof(output))==1 && !strcmp(output,"aw_set_time 0630\n"));
 assert(AW_DebugTranslate(3,sky,output,sizeof(output))==1 && !strcmp(output,"aw_daynight off\n"));
 {
  char *cloudtype[]={"dbg","cloudtype","veil"};
  assert(AW_DebugTranslate(2,cloudtype,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_type_set\n"));
  assert(AW_DebugTranslate(3,cloudtype,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_type_set veil\n"));
  cloudtype[2]="classic";
  assert(AW_DebugTranslate(3,cloudtype,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_type_set classic\n"));
  cloudtype[2]="veil;quit";assert(!AW_DebugTranslate(3,cloudtype,output,sizeof(output)));
 }
 {
  char *control[]={"dbg","cloudcontrol","new"};
  char *night[]={"dbg","nightclouds","partial"};
  char *day[]={"dbg","dayclouds","60"};
  char *mode[]={"dbg","nightskymode","clear"};
  assert(AW_DebugTranslate(2,mode,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky_mode_set\n"));
  assert(AW_DebugTranslate(3,mode,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky_mode_set clear\n"));
  mode[2]="legacy";assert(AW_DebugTranslate(3,mode,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky_mode_set legacy\n"));
  mode[2]="0";assert(AW_DebugTranslate(3,mode,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky_mode_set 0\n"));
  mode[2]="1";assert(AW_DebugTranslate(3,mode,output,sizeof(output))==1 && !strcmp(output,"aw_nightsky_mode_set 1\n"));
  mode[2]="clear;quit";assert(!AW_DebugTranslate(3,mode,output,sizeof(output)));
  assert(AW_DebugTranslate(2,control,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_control_set\n"));
  assert(AW_DebugTranslate(3,control,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_control_set new\n"));
  control[2]="legacy";
  assert(AW_DebugTranslate(3,control,output,sizeof(output))==1 && !strcmp(output,"aw_cloud_control_set legacy\n"));
  assert(AW_DebugTranslate(2,night,output,sizeof(output))==1 && !strcmp(output,"aw_night_clouds_set\n"));
  assert(AW_DebugTranslate(3,night,output,sizeof(output))==1 && !strcmp(output,"aw_night_clouds_set partial\n"));
  assert(AW_DebugTranslate(2,day,output,sizeof(output))==1 && !strcmp(output,"aw_day_clouds_set\n"));
  assert(AW_DebugTranslate(3,day,output,sizeof(output))==1 && !strcmp(output,"aw_day_clouds_set 60\n"));
  day[2]="60;quit";assert(!AW_DebugTranslate(3,day,output,sizeof(output)));
 }
 assert(AW_DebugTranslate(3,skytype,output,sizeof(output))==1 && !strcmp(output,"aw_sky_type_set 2\n"));
 skytype[2]="V3";assert(AW_DebugTranslate(3,skytype,output,sizeof(output))==1 && !strcmp(output,"aw_sky_type_set V3\n"));
 assert(AW_DebugTranslate(3,gallery,output,sizeof(output))==1 && !strcmp(output,"aw_charplane exit\n"));
 assert(AW_DebugTranslate(4,shortform,output,sizeof(output))==1);
 assert(!strcmp(output,"amiwind_debug_reset_location 0\n"));
 assert(AW_DebugTranslate(5,longform,output,sizeof(output))==1);
 assert(!strcmp(output,"amiwind_debug_reset_location 0\n"));
 assert(AW_DebugTranslate(3,toggle,output,sizeof(output))==1);
 assert(!strcmp(output,"amiwind_debug_coords TrUe\n"));
 assert(!AW_DebugTranslate(3,bad,output,sizeof(output)));
 assert(!AW_DebugTranslate(2,missing,output,sizeof(output)));
 assert(!AW_DebugTranslate(4,shortform,output,8));
 assert(AW_DebugTranslate(2,help,output,sizeof(output))==2);
 assert(AW_DebugTranslate(1,help,output,sizeof(output))==2);
 assert(AW_DebugTranslate(1,picker,output,sizeof(output))==2);
 assert(AW_DebugTranslate(7,view,output,sizeof(output))==1);
 assert(!strcmp(output,"aw_view -20 30 40 90 -60\n"));
 assert(AW_DebugTranslate(3,playvid,output,sizeof(output))==1);
 assert(!strcmp(output,"playvid 15\n"));
 playvid[2]="01";assert(AW_DebugTranslate(3,playvid,output,sizeof(output))==1);
 assert(!strcmp(output,"playvid 01\n"));
 playvid[2]="mw_logo";assert(AW_DebugTranslate(3,playvid,output,sizeof(output))==1);
 assert(!strcmp(output,"playvid mw_logo\n"));
 playvid[2]="../quit";assert(!AW_DebugTranslate(3,playvid,output,sizeof(output)));
 assert(AW_DebugTranslate(3,abbr,output,sizeof(output))==1);
 assert(!strcmp(output,"amiwind_debug_coords on\n"));
 assert(AW_DebugTranslate(3,picker,output,sizeof(output))==1);
 assert(!strcmp(output,"aw_scene_menu\n"));
 assert(AW_DebugTranslate(3,tp_map,output,sizeof(output))==1 && !strcmp(output,"aw_teleport_map\n"));
 assert(AW_DebugTranslate(3,map_tp,output,sizeof(output))==1 && !strcmp(output,"aw_teleport_map\n"));
 assert(AW_DebugTranslate(2,tp,output,sizeof(output))==1 && !strcmp(output,"aw_teleport\n"));
 assert(AW_DebugTranslate(3,tp,output,sizeof(output))==1 && !strcmp(output,"aw_teleport balmora\n"));
 tp[2]="seydaneen";
 assert(AW_DebugTranslate(3,tp,output,sizeof(output))==1 && !strcmp(output,"aw_teleport seydaneen\n"));
 tp[0]="DeBuG";tp[2]="prisonship";
 assert(AW_DebugTranslate(3,tp,output,sizeof(output))==1 && !strcmp(output,"aw_teleport prisonship\n"));
 assert(AW_DebugTranslate(4,tp_menu,output,sizeof(output))==1 && !strcmp(output,"aw_scene_menu\n"));
 assert(AW_DebugTranslate(4,tp_xy,output,sizeof(output))==1 && !strcmp(output,"aw_teleport -14231 -76109\n"));
 assert(!AW_DebugTranslate(5,tp_extra,output,sizeof(output)));
 assert(!AW_DebugTranslate(3,tp_bad,output,sizeof(output)));
 tp_bad[2]="../prison";assert(!AW_DebugTranslate(3,tp_bad,output,sizeof(output)));
 assert(!AW_DebugTranslate(3,tp,output,8));
 assert(AW_DebugTranslate(4,fog,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 400\n"));
 assert(AW_DebugTranslate(4,distance,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 500\n"));
 assert(AW_DebugTranslate(3,hud,output,sizeof(output))==1);
 assert(!strcmp(output,"amiwind_show_debug on\n"));
 assert(AW_DebugTranslate(4,hud_type,output,sizeof(output))==1 && !strcmp(output,"aw_debug_hud_type 2\n"));
 assert(AW_DebugTranslate(4,hors,output,sizeof(output))==1 && !strcmp(output,"aw_debug_hors 0\n"));
 assert(AW_ParseBoolean("TRUE")==1 && AW_ParseBoolean("on")==1 && AW_ParseBoolean("1")==1);
 assert(AW_ParseBoolean("FALSE")==0 && AW_ParseBoolean("off")==0 && AW_ParseBoolean("0")==0);
 assert(AW_ParseBoolean("2")==-1 && AW_ParseBoolean("truth")==-1);
 assert(AW_BooleanCvar("aw_fog") && !AW_BooleanCvar("aw_drawdistance"));
 assert(!AW_BooleanCvar("aw_dialogue_box_layout") && !AW_BooleanCvar("aw_ui_font"));
 AW_ConsoleInit();assert(colour->value==255);assert(dbg_command==debug_command);
 memset(pixels,17,sizeof(pixels));vid.conbuffer=pixels+4;
 vid.conwidth=8;vid.conrowbytes=12;vid.conheight=4;
 AW_ConsoleBackground(2);assert(scr_copyeverything);
 for(i=0;i<64;i++)assert(pixels[i]==((i>=4&&i<12)||(i>=16&&i<24)?255:17));
 AW_ConsoleBackground(100);assert(pixels[47]==255&&pixels[48]==17);
 memset(palette,200,sizeof(palette));palette[255*3]=palette[255*3+1]=palette[255*3+2]=0;
 palette[7*3]=16;palette[7*3+1]=24;palette[7*3+2]=48;host_basepal=palette;
 argc=2;args[0]="aw_console_color";args[1]="blue";color_command();assert(colour->value==7);
 args[1]="black";color_command();assert(colour->value==255);
 argc=4;args[1]="256";args[2]="0";args[3]="0";color_command();assert(colour->value==255);
 args[1]="16";args[2]="24";args[3]="48";color_command();assert(colour->value==7);
 argc=4;for(i=0;i<4;i++)args[i]=shortform[i];debug_command();
 assert(!strcmp(queued,"amiwind_debug_reset_location 0\n"));
 argc=3;args[0]="dbg";args[1]="tp";args[2]="map";debug_command();assert(!strcmp(queued,"aw_teleport_map\n"));
 argc=2;args[0]="aw_console_font";args[1]="readable";draw_chars=atlas;
 memset(atlas,99,sizeof(atlas));font_command();assert(atlas[0]==99);
 font_size=8;font_command();assert(atlas[0]==99);
 font_size=sizeof(atlas);font_command();for(i=0;i<sizeof(atlas);i++)assert(atlas[i]==i%251);
 args[1]="retro";memset(atlas,99,sizeof(atlas));font_command();assert(atlas[500]==500%251);
 memset(pixels,17,sizeof(pixels));vid.buffer=pixels+4;vid.width=8;vid.rowbytes=12;vid.height=4;
 AW_ConsoleSetSmall(0);AW_SmallString(-1,-1,"oooo");
 for(i=0;i<64;i++)if(i<4 || i>=48 || (i-4)%12>=8)assert(pixels[i]==17);
 assert(AW_ConsoleCharWidth()==8); /* HUD cannot change console mode. */
 return 0;
}

void AW_HeapAuditReport(const char *scene){}

server_t sv;
