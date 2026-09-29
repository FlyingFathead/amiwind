/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
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
 char *shortform[]={"debug","reset","location","0"};
 char *longform[]={"amiwind","debug","reset","location","0"};
 char *toggle[]={"DeBuG","coords","TrUe"};
 char *abbr[]={"DbG","coords","on"};
 char *bad[]={"debug","coords","on;quit"};
 char *missing[]={"debug","reset"};
 char *help[]={"debug","help"};
 char *picker[]={"dbg","scene","change"};
 char *fog[]={"dbg","fog","distance","400"};
 char *distance[]={"debug","draw","distance","500"};
 char *view[]={"debug","view","-20","30","40","90","-60"};
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
 assert(AW_DebugTranslate(4,fog,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 400\n"));
 assert(AW_DebugTranslate(4,distance,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 500\n"));
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
 argc=2;args[0]="aw_console_font";args[1]="readable";draw_chars=atlas;
 memset(atlas,99,sizeof(atlas));font_command();assert(atlas[0]==99);
 font_size=8;font_command();assert(atlas[0]==99);
 font_size=sizeof(atlas);font_command();for(i=0;i<sizeof(atlas);i++)assert(atlas[i]==i%251);
 args[1]="retro";memset(atlas,99,sizeof(atlas));font_command();assert(atlas[500]==500%251);
 return 0;
}
