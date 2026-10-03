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
 char *tp_bad[]={"dbg","tp","balmora;quit"};
 char *fog[]={"dbg","fog","distance","400"};
 char *distance[]={"debug","draw","distance","500"};
 char *view[]={"debug","view","-20","30","40","90","-60"};
 assert(AW_DebugTranslate(3,compass,output,sizeof(output))==1 && !strcmp(output,"amiwind_debug_compass true\n"));
 assert(AW_DebugTranslate(2,compass,output,sizeof(output))==1 && !strcmp(output,"amiwind_debug_compass\n"));
 assert(AW_BooleanCvar("aw_compass"));
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
