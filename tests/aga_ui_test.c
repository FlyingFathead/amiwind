/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
viddef_t vid;refdef_t r_refdef;keydest_t key_dest;double realtime;double host_frametime=.02;
client_static_t cls;server_t sv;server_static_t svs;int scr_copyeverything;
byte pal[768],glyphs[16384],frame[64004];byte *host_basepal=pal,*draw_chars=glyphs;
static char *directory;
int COM_FOpenFile(char *name,FILE **f){char p[1024];int n;sprintf(p,"%s/%s",directory,name);*f=fopen(p,"rb");if(!*f)return -1;fseek(*f,0,SEEK_END);n=ftell(*f);rewind(*f);return n;}
void Con_Printf(char *fmt,...){}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cvar_SetValue(char *s,float v){}
void Cmd_AddCommand(char *s,void(*f)(void)){}
char *Cmd_Argv(int i){return "";}
int Cmd_Argc(void){return 0;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int main(int argc,char **argv){
 byte raw[2057];const char *p;char line[9];int i;
 directory=argc>1?argv[1]:".";
 memset(raw,0,sizeof(raw));memcpy(raw,"AWF1",4);raw[4]=16;raw[5]=18;raw[6]=1;
 assert(AW_UIValidateFont(raw,sizeof(raw)));raw[8+2]=32;raw[8+3]=32;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 raw[8+2]=raw[8+3]=0;raw[8+6]=255;assert(!AW_UIValidateFont(raw,sizeof(raw)));
 memset(frame,137,sizeof(frame));vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=frame+2;
 AW_UIInit();AW_UIBox(-12,-12,80,80);AW_UIBox(300,190,80,80);
 AW_UIText(-40,-10,"Bounds: Wgjpq 123",-1);AW_UIText(315,195,"offscreen",-1);
 assert(frame[0]==137 && frame[1]==137 && frame[64002]==137 && frame[64003]==137);
 p="A verylongword and more";i=0;
 while(*p){const char *next=AW_UILine(p,32,line,sizeof(line));assert(next>p && strlen(line)<sizeof(line));p=next;assert(++i<30);}
 p="abc";assert(AW_UILine(p,0,line,sizeof(line))>p);
 assert(AW_UIWidth("abc")>0);return 0;
}

double AW_SpeechRemaining(void){return 0;}
