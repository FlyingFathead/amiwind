/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <sys/stat.h>
#include <unistd.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest;double realtime;double host_frametime=.02;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static char *directory;
static cvar_t *loading_parameter,*region_parameter;
static int queued_prison;
void AW_StoryReset(int new_game){}
void AW_CharacterReset(void){}
void AW_SaveReset(void){}
void IN_AWClearButtons(void){}
int AW_MusicStartTrack(int track){assert(track==4);return 1;}
void Cbuf_AddText(char *text){assert(!strcmp(text,"map prison\n"));queued_prison=1;}
int COM_FOpenFile(char *name,FILE **f){char p[1024];int n;sprintf(p,"%s/%s",directory,name);*f=fopen(p,"rb");if(!*f)return -1;fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return n;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);if(!strcmp(c->name,"aw_loading_style"))loading_parameter=c;else if(!strcmp(c->name,"aw_region_loading"))region_parameter=c;}
int AW_LoadingScreen(void){return 1;}
int AW_MenuFrontEnd(void){return 0;}
void Cvar_SetValue(char *s,float v){if(region_parameter && !strcmp(s,region_parameter->name))region_parameter->value=v;}
void Cmd_AddCommand(char *s,void(*f)(void)){}
char *Cmd_Argv(int i){return "";}
int Cmd_Argc(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int main(int argc,char **argv){
 byte raw[2057],before[3];const char *p;char line[9],temporary[]="/tmp/aw-ui-XXXXXX",path[128];int i;FILE *f;
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
