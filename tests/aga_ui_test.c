/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <sys/stat.h>
#include <unistd.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest;double realtime;double host_frametime=.02;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static char *directory;
static cvar_t *loading_parameter,*region_parameter,*delay_parameter;
static double loading_clock;
double Sys_FloatTime(void){return loading_clock;}
static int queued_prison;
void AW_StoryReset(int new_game){}
void AW_CharacterReset(void){}
void AW_SaveReset(void){}
void IN_AWClearButtons(void){}
int AW_MusicStartTrack(int track){assert(track==4);return 1;}
void Cbuf_AddText(char *text){assert(!strcmp(text,"map prison\n"));queued_prison=1;}
int COM_FOpenFile(char *name,FILE **f){char p[1024];int n;sprintf(p,"%s/%s",directory,name);*f=fopen(p,"rb");if(!*f)return -1;fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return n;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_loading_style"))loading_parameter=c;else if(!strcmp(c->name,"aw_region_loading"))region_parameter=c;else if(!strcmp(c->name,"aw_region_loading_delay"))delay_parameter=c;}
int AW_LoadingScreen(void){return 1;}
int AW_MenuFrontEnd(void){return 0;}
void Cvar_SetValue(char *s,float v){if(region_parameter && !strcmp(s,region_parameter->name))region_parameter->value=v;}
void Cmd_AddCommand(char *s,void(*f)(void)){}
char *Cmd_Argv(int i){return "";}
int Cmd_Argc(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int main(int argc,char **argv){
 byte raw[2057],before[3];const char *p;char line[9],temporary[]="aw-ui-XXXXXX",path[128];int i;FILE *f;
 directory=argc>1?argv[1]:".";
 memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=16;raw[5]=18;raw[6]=1;
 assert(AW_UIValidateFont(raw,sizeof(raw)));raw[8+2]=32;raw[8+3]=32;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 raw[8+2]=raw[8+3]=0;raw[8+6]=255;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 /* Three coverage levels expose gold fringes around explicitly black text. */
 assert(mkdtemp(temporary));directory=temporary;
 sprintf(path,"%s/gfx",directory);assert(!mkdir(path,0700));
 memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=14;raw[5]=16;raw[6]=1;
 raw[8+'A'*8+2]=3;raw[8+'A'*8+3]=1;raw[8+'A'*8+6]=3;raw[2056]=0x6c;
 sprintf(path,"%s/gfx/magic14.awf",directory);f=fopen(path,"wb");assert(f);assert(fwrite(raw,1,sizeof(raw),f)==sizeof(raw));fclose(f);
 raw[4]=12;raw[5]=14;
 sprintf(path,"%s/gfx/book12.awf",directory);f=fopen(path,"wb");assert(f);assert(fwrite(raw,1,sizeof(raw),f)==sizeof(raw));fclose(f);
 for(i=0;i<256;i++)pal[i*3]=pal[i*3+1]=pal[i*3+2]=i;
 memset(frame,137,sizeof(frame));vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
 AW_UIInit();AW_UIBox(-12,-12,80,80);AW_UIBox(300,190,80,80);
 AW_UIScrollbar(276,54,133,9,7,0);AW_UIScrollbar(315,190,100,100,6,94);
 assert(AW_UIScrollHit(280,55,276,54,133,9,7,1)==0);
 assert(AW_UIScrollHit(280,186,276,54,133,9,7,1)==2);
 assert(AW_UIScrollHit(275,100,276,54,133,9,7,0)==-1);
 assert(AW_UIScrollHit(280,100,276,54,133,7,7,0)==-1);
 for(i=64;i<177;i++){int top=AW_UIScrollHit(280,i,276,54,133,100,7,0);assert(top>=0 && top<=93);}
 AW_UIText(-40,-10,"Bounds: Wgjpq 123",-1);AW_UIText(315,195,"offscreen",-1);
 assert(frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
 p="A verylongword and more";i=0;
 while(*p){const char *next=AW_UILine(p,32,line,sizeof(line));assert(next>p && strlen(line)<sizeof(line));p=next;assert(++i<30);}
 p="abc";assert(AW_UILine(p,0,line,sizeof(line))>p);
 AW_UIText(20,20,"A",0);memcpy(before,vid.buffer+20*320+20,3);
 AW_UIBookBegin();AW_UIText(20,20,"A",0);
 assert(vid.buffer[20*320+20]==170 && vid.buffer[20*320+21]==85 && vid.buffer[20*320+22]==0);
 AW_UIBookEnd();AW_UIText(20,20,"A",0);assert(!memcmp(before,vid.buffer+20*320+20,3));
 /* Only the small top box changes; padded rows and repeated reconnect plaques
  * preserve the original pixels after the live buffer has been overwritten. */
 {
  byte padded[64804];int x,y,left,w,h;
  assert(region_parameter && region_parameter->archive && AW_RegionLoadingFrozen());
  AW_RegionLoadingToggle();assert(!AW_RegionLoadingFrozen());AW_RegionLoadingToggle();
  memset(padded,137,sizeof(padded));vid.buffer=padded+2;vid.rowbytes=324;
  for(y=0;y<200;y++)for(x=0;x<320;x++)vid.buffer[y*324+x]=(x+y)%251+1;
  AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_BeginLoadingStyle();assert(AW_LoadingFrozen());
  for(y=0;y<200;y++)memset(vid.buffer+y*324,0,320);
  AW_BeginLoadingStyle();AW_UILoading();assert(!AW_UIMenuPalette());
  w=AW_UIWidth("Loading...")+20;h=AW_UIHeight()+8;left=(320-w)/2;
  for(y=0;y<200;y++)for(x=0;x<324;x++){
   if(x>=320)assert(vid.buffer[y*324+x]==137);
   else if(y<6 || y>=6+h || x<left || x>=left+w)assert(vid.buffer[y*324+x]==(x+y)%251+1);
  }
  AW_UILoading();assert(vid.buffer[150*324+88]==(150+88)%251+1);
  assert(padded[0]==137 && padded[64803]==137);
  vid.height=199;AW_UILoading();assert(!AW_LoadingFrozen());
  assert(AW_UIMenuPalette() && !AW_UIMenuPalette()[100]);
  AW_EndLoadingStyle();assert(!AW_LoadingFrozen());
  vid.buffer=NULL;AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_BeginLoadingStyle();
  assert(!AW_LoadingFrozen());AW_EndLoadingStyle();
  vid.buffer=frame+2;vid.rowbytes=320;vid.height=200;
 }
 /* Short automatic crossings leave every live framebuffer byte untouched.
  * Reconnect cannot restart the clock; completion cancels a pending display. */
 assert(delay_parameter && delay_parameter->archive && delay_parameter->value==2);
 memset(vid.buffer,137,64000);loading_clock=10;
 AW_SetNextLoadingStyle(AW_LOADING_FROZEN);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(AW_LoadingDelayed());AW_UILoading();
 for(i=0;i<64000;i++)assert(vid.buffer[i]==137);
 loading_clock=11.999;assert(!AW_LoadingDelayExpired());AW_BeginLoadingStyle();
 loading_clock=12;assert(AW_LoadingDelayExpired());assert(!AW_LoadingDelayExpired());
 AW_UILoading();assert(vid.buffer[150*320+88]==137);AW_EndLoadingStyle();
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(AW_LoadingDelayed());AW_EndLoadingStyle();loading_clock=100;
 assert(!AW_LoadingDelayed() && !AW_LoadingDelayExpired());
 AW_BeginLoadingStyle();assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=0;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=-1;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 assert(!AW_LoadingDelayed());AW_EndLoadingStyle();
 delay_parameter->value=1000;AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 loading_clock=159.999;assert(!AW_LoadingDelayExpired());
 loading_clock=160;assert(AW_LoadingDelayExpired());AW_EndLoadingStyle();delay_parameter->value=2;
 /* Automatic black mode gains its indicator after the deadline while
  * explicit/movie blank mode below retains a completely black palette. */
 memset(vid.buffer,137,64000);loading_clock=200;
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_SetNextLoadingDelay();AW_BeginLoadingStyle();
 AW_UILoading();for(i=0;i<64000;i++)assert(vid.buffer[i]==137);
 loading_clock=202;assert(AW_LoadingDelayExpired());AW_UILoading();
 assert(AW_UIMenuPalette()==host_basepal && vid.buffer[150*320+88]==0);
 for(i=0;i<64000 && !vid.buffer[i];i++){}assert(i<64000);AW_EndLoadingStyle();
 /* Blank is a complete black frame/palette, then normal art resumes. */
 assert(loading_parameter && !strcmp(loading_parameter->string,"normal"));
 AW_SetNextLoadingStyle(AW_LOADING_BLANK);AW_BeginLoadingStyle();AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 assert(AW_UIMenuPalette());for(i=0;i<768;i++)assert(!AW_UIMenuPalette()[i]);
 assert(frame[0]==137 && frame[64003]==137);
 AW_EndLoadingStyle();AW_BeginLoadingStyle();AW_UILoading();assert(!AW_UIMenuPalette());
 for(i=0;i<64000 && !vid.buffer[i];i++){}assert(i<64000);
 AW_EndLoadingStyle();loading_parameter->string="blank";AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 AW_EndLoadingStyle();AW_SetNextLoadingStyle(AW_LOADING_NORMAL);AW_BeginLoadingStyle();assert(!AW_UIMenuPalette());
 /* Movie finish may draw before its queued map command. Even an earlier
  * normal plaque must not leak artwork into that frame. */
 AW_IntroBegin();assert(queued_prison);AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 for(i=0;i<768;i++)assert(!AW_UIMenuPalette()[i]);
 AW_BeginLoadingStyle();AW_UILoading();
 for(i=0;i<64000;i++)assert(!vid.buffer[i]);
 sprintf(path,"%s/gfx/magic14.awf",directory);unlink(path);sprintf(path,"%s/gfx/book12.awf",directory);unlink(path);
 sprintf(path,"%s/gfx",directory);rmdir(path);rmdir(directory);return 0;
}

double AW_SpeechRemaining(void){return 0;}
