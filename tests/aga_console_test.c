/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
#include "aw_boolean.h"
viddef_t vid;
int scr_copyeverything;
int con_linewidth=38;
void Con_CheckResize(void){}
void Draw_Character(int x,int y,int c){}
byte *host_basepal;
byte *draw_chars;
static int font_size=-1,catalogue_opens,catalogue_missing,catalogue_size_adjust;
static const char *catalogue_path,*catalogue_override;
static char printed[20000];
/* The gallery marker check (aw_gallery.c) as seen by the listing code. */
static int gallery_omitted,gallery_checks;
int AW_GalleryOmitted(void){gallery_checks++;return gallery_omitted;}
int COM_FOpenFile(char *name,FILE **f){
 int i,n,c;FILE *source;
 if(!strcmp(name,"debug-commands.txt")){
  catalogue_opens++;*f=NULL;if(catalogue_missing)return -1;
  *f=tmpfile();assert(*f);
  for(i=0;i<137;i++)fputc(0xa5,*f); /* Simulate a PAK-member offset. */
  if(catalogue_override){n=(int)strlen(catalogue_override);fputs(catalogue_override,*f);}
  else {
   source=fopen(catalogue_path,"rb");assert(source);n=0;
   while((c=fgetc(source))!=EOF){fputc(c,*f);n++;}fclose(source);
  }
  if(!catalogue_size_adjust)fputs("NOT PART OF THIS PAK MEMBER\n",*f);
  fseek(*f,137,SEEK_SET);return n+catalogue_size_adjust;
 }
 if(font_size<0){*f=NULL;return -1;}
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
void Con_Printf(char *fmt,...){
 va_list args;size_t n=strlen(printed);va_start(args,fmt);
 vsnprintf(printed+n,sizeof(printed)-n,fmt,args);va_end(args);
}
void Cbuf_InsertText(char *s){strcpy(queued,s);}
void Cvar_RegisterVariable(cvar_t *p){colour=p;p->value=atof(p->string);}
void Cvar_SetValue(char *name,float v){assert(!strcmp(name,colour->name));colour->value=v;}
void Cmd_AddCommand(char *name,void (*fn)(void)){
 if(!strcmp(name,"aw_console_color"))color_command=fn;
 if(!strcmp(name,"debug"))debug_command=fn;
 if(!strcmp(name,"dbg"))dbg_command=fn;
 if(!strcmp(name,"aw_console_font"))font_command=fn;
}
cvar_t *Cvar_FindVar(char *n){static cvar_t c;return !strcmp(n,"aw_fog") || !strcmp(n,"aw_skyline_fill")?&c:NULL;}
static float cull_value=4;
float Cvar_VariableValue(char *n){assert(!strcmp(n,"aw_cull"));return cull_value;}
/* Every catalogue entry, typed with no arguments, must reach exactly its
 * handler through the engine's translator: a broken or shadowed entry fails. */
static void every_entry_translates(void){
 FILE *f=fopen(catalogue_path,"rb");char line[512],words[160],handler[96],expect[112],output[160],*argv[16],*w;int argc,checked=0;
 assert(f);
 while(fgets(line,sizeof line,f)){
  char *bar1,*bar2,*bar3;size_t n=strlen(line);
  while(n && (line[n-1]=='\n' || line[n-1]=='\r'))line[--n]=0;
  if(!n || line[0]=='#' || !strcmp(line,"AWDC1"))continue;
  bar1=strchr(line,'|');bar2=bar1?strchr(bar1+1,'|'):NULL;bar3=bar2?strchr(bar2+1,'|'):NULL;
  assert(bar1 && bar2 && bar3);
  *bar2=0;*bar3=0;snprintf(words,sizeof words,"%s",bar1+1);snprintf(handler,sizeof handler,"%s",bar2+1);
  argv[0]="dbg";argc=1;
  for(w=strtok(words," ");w && argc<16;w=strtok(NULL," "))argv[argc++]=w;
  /* dbg fog rule / dbg cut groups print aw_cull with no argument (switch bits) */
  snprintf(expect,sizeof expect,"%s%s\n",handler,
       !strcmp(bar1+1,"characterchange")?" appearance":!strcmp(bar1+1,"inventory grant")?" grant":
       !strcmp(bar1+1,"door roulette")?" roulette":!strcmp(bar1+1,"doorlocks")?" locks":
       !strcmp(bar1+1,"creatures")?" actors creatures":!strcmp(bar1+1,"mwscript")?" about":
       (!strcmp(bar1+1,"set race") || !strcmp(bar1+1,"set playerrace"))?" playerrace":"");
  if(AW_DebugTranslate(argc,argv,output,sizeof(output))!=1 || strcmp(output,expect)){
   printf("catalogue entry does not reach its handler: dbg %s -> %s (got %s)\n",bar1+1,handler,output);assert(0);
  }
  checked++;
 }
 fclose(f);assert(checked>=100);
 printf("every catalogue entry reaches its handler: %d\n",checked);
}
int main(int count,char **values){
 char output[160];byte atlas[16384];int i;
 char *compass[]={"dbg","compass","true"};
 assert(count==2);catalogue_path=values[1];
 every_entry_translates();
 { /* Numeric/name race aliases use one handler; quoted names retain one argument. */
   char *race[]={"dbg","set","race","1"};
   char *alias[]={"dbg","set","playerrace","High Elf"};
   char *split[]={"debug","set","race","High","Elf"};
   assert(AW_DebugTranslate(4,race,output,sizeof output)==1 && !strcmp(output,"aw_quickchar_set playerrace 1\n"));
   assert(AW_DebugTranslate(4,alias,output,sizeof output)==1 && !strcmp(output,"aw_quickchar_set playerrace \"High Elf\"\n"));
   assert(AW_DebugTranslate(5,split,output,sizeof output)==1 && !strcmp(output,"aw_quickchar_set playerrace High Elf\n"));
   alias[3]="Nord;quit";assert(AW_DebugTranslate(4,alias,output,sizeof output)==0);
 }
 {
  char *tracker[]={"dbg","shroomtracker","reset"};
  assert(AW_DebugTranslate(2,tracker,output,sizeof(output))==1 && !strcmp(output,"aw_shroomtracker\n"));
  { /* DBG-TOGGLE-WORDS-31: toggle words reach settings as 1/0; commands keep their words. */
    char *fog[3]={"dbg","fog","on"},*fill[4]={"dbg","skyline","fill","Off"},*guard[3]={"dbg","guardtorch","on"};
    assert(AW_DebugTranslate(3,fog,output,sizeof(output))==1 && !strcmp(output,"aw_fog 1\n"));
    fog[2]="off";assert(AW_DebugTranslate(3,fog,output,sizeof(output))==1 && !strcmp(output,"aw_fog 0\n"));
    fog[2]="0.5";assert(AW_DebugTranslate(3,fog,output,sizeof(output))==1 && !strcmp(output,"aw_fog 0.5\n"));
    assert(AW_DebugTranslate(4,fill,output,sizeof(output))==1 && !strcmp(output,"aw_skyline_fill 0\n"));
    assert(AW_DebugTranslate(3,guard,output,sizeof(output))==1 && !strcmp(output,"aw_guardtorch on\n"));
  }
  { /* CHIM-BRIDGE-POP-PIECES-44: the fog rule and whole-structure cuts are bits
     * of aw_cull (8, 16); the far test in the low bits is kept. */
    char *rule[4]={"dbg","fog","rule","on"},*groups[4]={"dbg","cut","groups","1"};
    cull_value=4;assert(AW_DebugTranslate(4,rule,output,sizeof(output))==1 && !strcmp(output,"aw_cull 12\n"));
    cull_value=12;assert(AW_DebugTranslate(4,groups,output,sizeof(output))==1 && !strcmp(output,"aw_cull 28\n"));
    cull_value=28;rule[3]="off";assert(AW_DebugTranslate(4,rule,output,sizeof(output))==1 && !strcmp(output,"aw_cull 20\n"));
    cull_value=1;groups[3]="false";assert(AW_DebugTranslate(4,groups,output,sizeof(output))==1 && !strcmp(output,"aw_cull 1\n"));
    rule[3]="maybe";assert(AW_DebugTranslate(4,rule,output,sizeof(output))==0);
    cull_value=4;
  }
  { /* dbg god / dbg godmode: one handler, the usual toggle words reach it unchanged. */
    char *god[3]={"dbg","god","true"},*mode[3]={"dbg","godmode","off"};
    assert(AW_DebugTranslate(3,god,output,sizeof(output))==1 && !strcmp(output,"aw_godmode true\n"));
    assert(AW_DebugTranslate(3,mode,output,sizeof(output))==1 && !strcmp(output,"aw_godmode off\n"));
    assert(AW_DebugTranslate(2,mode,output,sizeof(output))==1 && !strcmp(output,"aw_godmode\n"));
  }
  { /* dbg mwscript [on|off] (DBG-MWSCRIPT-SILENT-56): the status handler takes the switch and answers; alone: about */
    char *mw[3]={"dbg","mwscript","on"};
    assert(AW_DebugTranslate(3,mw,output,sizeof(output))==1 && !strcmp(output,"aw_mwscript_status on\n"));
    mw[2]="off";assert(AW_DebugTranslate(3,mw,output,sizeof(output))==1 && !strcmp(output,"aw_mwscript_status off\n"));
    assert(AW_DebugTranslate(2,mw,output,sizeof(output))==1 && !strcmp(output,"aw_mwscript_status about\n"));
    mw[2]="status";assert(AW_DebugTranslate(3,mw,output,sizeof(output))==1 && !strcmp(output,"aw_mwscript_status\n"));
  }
  { /* dbg music on|off (ENGINE-MUSIC-NO-OFF-SWITCH-36): the stream status handler takes the switch words. */
    char *music[3]={"dbg","music","off"};
    assert(AW_DebugTranslate(3,music,output,sizeof(output))==1 && !strcmp(output,"aw_music_status off\n"));
    music[2]="1";assert(AW_DebugTranslate(3,music,output,sizeof(output))==1 && !strcmp(output,"aw_music_status 1\n"));
    assert(AW_DebugTranslate(2,music,output,sizeof(output))==1 && !strcmp(output,"aw_music_status\n"));
  }
  { /* Photo mode (dbg photomode / dbg killhud) and dbg crosshair(s): one handler each, words kept. */
    char *photo[3]={"dbg","photomode","off"},*kill[3]={"dbg","killhud","on"},*cross[3]={"dbg","crosshairs","on"};
    assert(AW_DebugTranslate(3,photo,output,sizeof(output))==1 && !strcmp(output,"aw_photomode off\n"));
    assert(AW_DebugTranslate(2,photo,output,sizeof(output))==1 && !strcmp(output,"aw_photomode\n"));
    assert(AW_DebugTranslate(3,kill,output,sizeof(output))==1 && !strcmp(output,"aw_photomode on\n"));
    assert(AW_DebugTranslate(2,kill,output,sizeof(output))==1 && !strcmp(output,"aw_photomode\n"));
    assert(AW_DebugTranslate(3,cross,output,sizeof(output))==1 && !strcmp(output,"aw_crosshair on\n"));
    cross[1]="crosshair";cross[2]="off";
    assert(AW_DebugTranslate(3,cross,output,sizeof(output))==1 && !strcmp(output,"aw_crosshair off\n"));
    assert(AW_DebugTranslate(2,cross,output,sizeof(output))==1 && !strcmp(output,"aw_crosshair\n"));
  }
  assert(!AW_DebugTranslate(3,tracker,output,sizeof(output))); /* Query only, no reset. */
  tracker[0]="debug";assert(AW_DebugTranslate(2,tracker,output,sizeof(output))==1);
  assert(!AW_DebugTranslate(2,tracker,output,8));
 }
 {
  char *picker[]={"dbg","shroompicker","reset"};
  assert(AW_DebugTranslate(2,picker,output,sizeof(output))==1 && !strcmp(output,"aw_shroompicker\n"));
  assert(!AW_DebugTranslate(3,picker,output,sizeof(output)));
  assert(!AW_DebugTranslate(2,picker,output,8));
  picker[0]="debug";assert(AW_DebugTranslate(2,picker,output,sizeof(output))==1);
  picker[2]="1";assert(AW_DebugTranslate(3,picker,output,sizeof(output))==1 && !strcmp(output,"aw_shroompicker 1\n"));
  picker[2]="10";assert(AW_DebugTranslate(3,picker,output,sizeof(output))==1);
  picker[2]="list";assert(AW_DebugTranslate(3,picker,output,sizeof(output))==1);
  picker[2]="0";assert(!AW_DebugTranslate(3,picker,output,sizeof(output)));
  picker[2]="11";assert(!AW_DebugTranslate(3,picker,output,sizeof(output)));
  picker[2]="9999999999999999999999999999";assert(!AW_DebugTranslate(3,picker,output,sizeof(output)));
  picker[2]="1;quit";assert(!AW_DebugTranslate(3,picker,output,sizeof(output)));
 }

 {
  char *radius[]={"dbg","torch","radius","192"};
  char *flame[]={"dbg","torch","flame","brightbase"};
  char *strength[]={"dbg","torch","strength","0.7"};
  char *torchtest[]={"dbg","torchtest","npc","clagius","clanler"};
  assert(AW_DebugTranslate(4,radius,output,sizeof(output))==1 && !strcmp(output,"aw_torch_radius_set 192\n"));
  assert(AW_DebugTranslate(4,flame,output,sizeof(output))==1 && !strcmp(output,"aw_torch_flame_set brightbase\n"));
  assert(AW_DebugTranslate(4,strength,output,sizeof(output))==1 && !strcmp(output,"aw_torch_strength_set 0.7\n"));
  assert(AW_DebugTranslate(2,torchtest,output,sizeof(output))==1 && !strcmp(output,"aw_torchtest\n"));
  assert(AW_DebugTranslate(5,torchtest,output,sizeof(output))==1 && !strcmp(output,"aw_torchtest npc clagius clanler\n"));
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
 char *tp_extra[]={"dbg","tp","-14231","-76109","1200","extra"};
 char *tp_xyz[]={"dbg","tp","-14231","-76109","1200"};
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
  /* dbg daynight (clock hold at 12:00) is its own command, not the sky setting
   * aw_daynight and not daynightcycle; on/off reach the handler unchanged. */
  char *hold[]={"dbg","daynight","off"};
  assert(AW_DebugTranslate(2,hold,output,sizeof(output))==1 && !strcmp(output,"aw_daynight_set\n"));
  assert(AW_DebugTranslate(3,hold,output,sizeof(output))==1 && !strcmp(output,"aw_daynight_set off\n"));
  hold[2]="on";assert(AW_DebugTranslate(3,hold,output,sizeof(output))==1 && !strcmp(output,"aw_daynight_set on\n"));
  hold[2]="off;quit";assert(!AW_DebugTranslate(3,hold,output,sizeof(output)));
  hold[1]="daynightcycle";hold[2]="off";
  assert(AW_DebugTranslate(3,hold,output,sizeof(output))==1 && !strcmp(output,"aw_daynightcycle off\n"));
 }
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
 {
  const char *aliases[]={"playvid","vidplay","playvideo","videoplay"};int a;
  for(a=0;a<4;a++){
   playvid[1]=(char *)aliases[a];playvid[2]="15";
   assert(AW_DebugTranslate(3,playvid,output,sizeof(output))==1 && !strcmp(output,"playvid 15\n"));
   playvid[2]="mw_logo";
   assert(AW_DebugTranslate(3,playvid,output,sizeof(output))==1 && !strcmp(output,"playvid mw_logo\n"));
   playvid[2]="15;quit";assert(!AW_DebugTranslate(3,playvid,output,sizeof(output)));
  }
 }
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
 /* dbg tp X Y Z (DEBUG-TP-CHIM-33); a fourth number is refused. */
 assert(AW_DebugTranslate(5,tp_xyz,output,sizeof(output))==1 && !strcmp(output,"aw_teleport -14231 -76109 1200\n"));
 assert(!AW_DebugTranslate(6,tp_extra,output,sizeof(output)));
 assert(!AW_DebugTranslate(3,tp_bad,output,sizeof(output)));
 tp_bad[2]="../prison";assert(!AW_DebugTranslate(3,tp_bad,output,sizeof(output)));
 assert(!AW_DebugTranslate(3,tp,output,8));
 assert(AW_DebugTranslate(4,fog,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 400\n"));
 assert(AW_DebugTranslate(4,distance,output,sizeof(output))==1);assert(!strcmp(output,"aw_fog_distance 500\n"));
 assert(AW_DebugTranslate(3,hud,output,sizeof(output))==1);
 assert(!strcmp(output,"aw_debug_hud on\n"));
 assert(AW_DebugTranslate(4,hud_type,output,sizeof(output))==1 && !strcmp(output,"aw_debug_hud_type 2\n"));
 assert(AW_DebugTranslate(4,hors,output,sizeof(output))==1 && !strcmp(output,"aw_debug_hors 0\n"));
 assert(AW_ParseBoolean("TRUE")==1 && AW_ParseBoolean("on")==1 && AW_ParseBoolean("1")==1);
 assert(AW_ParseBoolean("FALSE")==0 && AW_ParseBoolean("off")==0 && AW_ParseBoolean("0")==0);
 assert(AW_ParseBoolean("2")==-1 && AW_ParseBoolean("truth")==-1);
 assert(AW_BooleanCvar("aw_fog") && !AW_BooleanCvar("aw_drawdistance"));
 assert(!AW_BooleanCvar("aw_cull")); /* a far-test selector 0..6 (cvar.c), not a boolean */
 assert(!AW_BooleanCvar("aw_dialogue_box_layout") && !AW_BooleanCvar("aw_ui_font"));
 {
  char *indoor[]={"dbg","indoor","luma","1.1"};
  char *interior[]={"dbg","interior","luma","1.3"};
  char *legacy[]={"dbg","interiorluma","1.2"};
  char *canonical[]={"dbg","luma","interior","1.3"};
  char *outside[]={"dbg","luma","exterior","1.1"};
  assert(AW_DebugTranslate(4,canonical,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set 1.3\n"));
  assert(AW_DebugTranslate(4,outside,output,sizeof(output))==1 && !strcmp(output,"aw_exteriorluma_set 1.1\n"));
  assert(AW_DebugTranslate(3,indoor,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set\n"));
  assert(AW_DebugTranslate(4,indoor,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set 1.1\n"));
  assert(AW_DebugTranslate(3,interior,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set\n"));
  assert(AW_DebugTranslate(4,interior,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set 1.3\n"));
  assert(AW_DebugTranslate(2,legacy,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set\n"));
  assert(AW_DebugTranslate(3,legacy,output,sizeof(output))==1 && !strcmp(output,"aw_interiorluma_set 1.2\n"));
 }
 {
  char *change[]={"dbg","characterchange"},*all[]={"dbg","characterchange","all"};
  char *grant[]={"dbg","inventory","grant","steel longsword","1"};
  assert(AW_DebugTranslate(2,change,output,sizeof(output))==1 && !strcmp(output,"aw_quickchar appearance\n"));
  assert(AW_DebugTranslate(3,all,output,sizeof(output))==1 && !strcmp(output,"aw_quickchar all\n"));
  assert(AW_DebugTranslate(5,grant,output,sizeof(output))==1 && !strcmp(output,"aw_inventory grant \"steel longsword\" 1\n"));
  grant[3]="steel;quit";assert(!AW_DebugTranslate(5,grant,output,sizeof(output)));
  { /* dbg door roulette [SEED]: the teleport command's roulette, no resident command of its own; plain dbg door
     * stays the hinged door */
   char *roulette[]={"dbg","door","roulette","1234"},*door[]={"dbg","door","status"};
   assert(AW_DebugTranslate(4,roulette,output,sizeof(output))==1 && !strcmp(output,"aw_teleport roulette 1234\n"));
   assert(AW_DebugTranslate(3,roulette,output,sizeof(output))==1 && !strcmp(output,"aw_teleport roulette\n"));
   assert(AW_DebugTranslate(3,door,output,sizeof(output))==1 && !strcmp(output,"aw_hinged_door status\n"));
  }
  grant[3]="steel\"quit";assert(!AW_DebugTranslate(5,grant,output,sizeof(output)));
 }
 i=catalogue_opens;
 AW_ConsoleInit();assert(colour->value==255);assert(dbg_command==debug_command);
 assert(i==catalogue_opens); /* Registering/opening does not load a catalogue. */
 argc=2;args[0]="dbg";args[1]="help";printed[0]=0;debug_command();
 /* Normal builds: the gallery commands are listed plainly. */
 assert(gallery_checks==1 && !strstr(printed,"(not in this build)"));
 assert(strstr(printed," npcgallery [number/name/ID]\n"));
 /* A --no-npc-gallery build marks every gallery route, and only those, in the
  * full list and in dbg help <word>; dispatch never checks the marker. */
 gallery_omitted=1;printed[0]=0;debug_command();
 assert(gallery_checks==2);
 assert(strstr(printed," npcgallery [number/name/ID] (not in this build)\n"));
 assert(strstr(printed," modelgallery [number/name/ID] (not in this build)\n"));
 assert(strstr(printed," gallery [number/name/ID; next/previous/body/browse/help/exit] (not in this build)\n"));
 assert(strstr(printed," aw charplane [number/name/ID; next/previous/body/exit] (not in this build)\n"));
 /* dbg combattest is the Vivec Arena (no gallery needed); its floor test explains itself. */
 assert(strstr(printed," combattest [opponent] same as arenapit; combattest gallery (or floor): the empty floor test, current hands, then idle/draw/lower/punch/center/help/exit\n"));
 assert(strstr(printed," arenapit [opponent / list / next / prev / here/pit/floor / seed N / rematch / setup / exit] Vivec Arena"));
 {char *p=printed;int marks=0;while((p=strstr(p,"(not in this build)"))){marks++;p++;}assert(marks==4);}
 assert(!strstr(printed,"Esc done (not in this build)") && !strstr(printed,"Esc returns) (not in this build)"));
 argc=3;args[1]="help";args[2]="npcgallery";printed[0]=0;debug_command();
 assert(gallery_checks==3 && !strcmp(printed," dbg npcgallery [number/name/ID] (not in this build)\n"));
 args[2]="lightgallery";printed[0]=0;debug_command();
 assert(gallery_checks==4 && strstr(printed," dbg lightgallery [off]") && !strstr(printed,"(not in this build)"));
 argc=2;args[1]="npcgallery";strcpy(queued,"untouched");debug_command();
 assert(gallery_checks==4 && !strcmp(queued,"aw_charplane\n"));
 gallery_omitted=0;argc=2;args[1]="help";printed[0]=0;debug_command();
 assert(strstr(printed,"AUDIO\n--------------------------------------\n"));
 assert(strstr(printed,"VIDEO\n--------------------------------------\n"));
 assert(strstr(printed,"PLAYTESTING\n--------------------------------------\n"));
 assert(strstr(printed,"shroompicker [1..10/list]"));
 assert(!strstr(printed,"NOT PART"));
 {
  char *query[]={"dbg","sample"};char badline[500];
  catalogue_override="AWDC1\nTEST|sample|aw_pos|first\n";
  assert(AW_DebugTranslate(2,query,output,sizeof(output))==1 && !strcmp(output,"aw_pos\n"));
  catalogue_override="AWDC1\nTEST|sample|aw_dimensions|changed on disk\n";
  assert(AW_DebugTranslate(2,query,output,sizeof(output))==1 && !strcmp(output,"aw_dimensions\n"));
  catalogue_override="AWDC1\nTEST|sample|aw_pos;quit|bad\n";
  assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1 && !*output);
  catalogue_override="AWDC1\nTEST|sample|aw_pos|ok\ninvalid trailing row\n";
  assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1 && !*output);
  catalogue_override="AWDC1\nTEST|sample|aw_pos|a\nTEST|sample|aw_view|duplicate\n";
  assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1);
  memset(badline,'x',sizeof(badline));memcpy(badline,"AWDC1\n",6);badline[499]=0;
  catalogue_override=badline;assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1);
  catalogue_override="AWDC0\n";assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1);
  catalogue_override="AWDC1\nTEST|sample|aw_pos|ok\n";
  catalogue_size_adjust=1;assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1);
  catalogue_size_adjust=65536;assert(AW_DebugTranslate(2,query,output,sizeof(output))==-1);
  catalogue_size_adjust=0;catalogue_override=NULL;catalogue_missing=1;
  argc=2;args[1]="coords";strcpy(queued,"untouched");printed[0]=0;debug_command();
  assert(!strcmp(queued,"untouched") && strstr(printed,"Debug catalogue missing/invalid"));
  catalogue_missing=0;
 }
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
 /* Inventory ink and field bounds reuse real glyph pixels without touching
  * console mode, surrounding pixels, or the framebuffer row padding. */
 memset(pixels,17,sizeof(pixels));
 AW_SmallStringColor(2,0,4,"MMMMMMMM",71);
 {int painted=0;
  for(i=0;i<64;i++){
   if(pixels[i]!=17){
    int local=i-4;assert(local>=0 && local/12<4 && local%12>=2 && local%12<5);
    assert(pixels[i]==71);painted++;
   }
  }
  assert(painted>0);
 }
 memset(pixels,17,sizeof(pixels));AW_SmallStringColor(0,0,3,"M",71);
 for(i=0;i<64;i++)assert(pixels[i]==17);
 AW_SmallStringColor(-2,-2,40,"MMMMMMMM",71);
 for(i=0;i<64;i++)if(i<4 || i>=48 || (i-4)%12>=8)assert(pixels[i]==17);
 assert(AW_ConsoleCharWidth()==8);

 return 0;
}

void AW_HeapAuditReport(const char *scene){}

server_t sv;
